import operator
import inverter, shared

bin_ops = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "!=": operator.ne,
    "==": operator.eq
}

# The node currently being evaluated. (used in error reporting)
current_node = None

class Memory():
    """
    Stores variable names and values. One per function.

    Nothing more than a wrapper around two dictionaries,
    refs and consts, where consts is immutable.
    """

    def __init__(self, refs={}, consts={}):
        self.refs = dict(refs)
        self.consts = dict(consts)

    def update_refs(self, other):
        for key in other.refs:
            if key in self.refs:
                self.refs[key] = other.refs[key]

    def copy(self):
        return Memory(self.refs, self.consts)

    def __contains__(self, key):
        return key in self.refs or key in self.consts

    def __getitem__(self, name):
        if name in self.refs:
            return self.refs[name]
        if name in self.consts:
            return self.consts[name]

        # BROKEN
        raise shared.ArrowException(
            shared.Stages.evaluation,
            "{} not found in table.".format(name),
            current_node.token
            )

    def __setitem__(self, name, value):
        if name in self.consts:
            # BROKEN
            raise shared.ArrowException(
                shared.Stages.evaluation,
                "Modifying constant {} not allowed.".format(name),
                current_node.token
                )
        else:
            self.refs[name] = value

    def __repr__(self):
        return "refs: {}, consts: {}".format(self.refs, self.consts)

def check_index(index, array):
    """
    Validates the array reference index and returns
    the corresponding Python integer (not a Num object).
    """
    if index.bottom != 1:
        pass
        #Only access arrays with whole indices!
    elif index.top >= len(array):
        pass
        #Array out of bounds error!
    elif index.sign == -1:
        pass
        #Indexes can't be negative!

    return index.top

def expr_eval(node, table=Memory()):
    """
    Evaluates expression nodes.
    Returns a data value (right now, always a number).
    """

    if node.kind == "BIN_OP":
        # Evaluate both sides, then return (left <op> right).
        left = expr_eval(node.left, table)
        right = expr_eval(node.right, table)
        return bin_ops[node.op](left, right)

    elif node.kind == "NEGATE":
        return - expr_eval(node.expr, table)

    elif node.kind == "NUM":
        return node.number

    elif node.kind == "VAR_REF":
        return table[node.name]

    elif node.kind == "ARRAY_REF":
        # TODO: This code belongs in the Array datatype.

        # Fetch the array.
        array = table[node.name]
        # Compute the index (a Num object).
        index = expr_eval(node.expr, table)
        # Check it and convert it to a Python integer.
        index = check_index(index, array)

        return array[index]

    elif node.kind == "FUNCTION_CALL":
        # TODO: Replace with first-class function code.
        if node.backwards:
            function = shared.program.unfunctions[node.name]
        else:
            function = shared.program.functions[node.name]

        result = function_eval(
            node=function,
            ref_arg_vars=node.ref_args,
            ref_arg_vals=[expr_eval(arg, table) for arg in node.ref_args],
            const_arg_vals=[expr_eval(arg, table) for arg in node.const_args]
        )

        table.update_refs(result)
        return result["result"]

    elif node.kind == "ARRAY_EXPR":
        # Evaluate the expressions in order and create a list.
        return [expr_eval(entry, table) for entry in node.entries]

def mod_op_eval(node, table):
    """
    Evaluates mod-op nodes. Returns a memory table.
    """

    expr_value = expr_eval(node.expr, table)

    if node.var.kind == "ARRAY_REF":
        # TODO: Refactor to use the Array object's fetch.
        array = table[node.var.name]
        index = expr_eval(node.var.expr, table)
        index = check_index(index, array)

        # A[x] += 1 expands into A[x] = A[x] + 1.
        array[index] = bin_ops[node.op](array[index], expr_value)

    elif node.var.kind == "VAR_REF":
        # x += 1 expands into x = x + 1.
        old_value = table[node.var.name]
        table[node.var.name] = bin_ops[node.op](old_value, expr_value)

    return table

def swap_op_eval(node, table):
    """
    Evaluates swap-op nodes. Returns a memory table.
    """
    # TODO: This is a mess. Array object simplification?

    if node.left.kind == "VAR_REF" and node.right.kind == "VAR_REF":

        l, r = node.left.name, node.right.name
        table[l], table[r] = table[r], table[l]

    if node.left.kind == "ARRAY_REF" and node.right.kind == "VAR_REF":

        l_array, r = table[node.left.name], node.right.name
        l_index = expr_eval(node.left.expr, table)
        l_index = check_index(l_index, l_array)

        l_array[l_index], table[r] = table[r], l_array[l_index]

    if node.left.kind == "VAR_REF" and node.right.kind == "ARRAY_REF":

        l, r_array = node.left.name, table[node.right.name]
        r_index = expr_eval(node.right.expr, table)
        r_index = check_index(r_index, r_array)

        table[l], r_array[r_index] = r_array[r_index], table[l]

    if node.left.kind == "ARRAY_REF" and node.right.kind == "ARRAY_REF":

        L, R = left_array, right_array = table[node.left.name], table[node.right.name]
        i = left_index = expr_eval(node.left.expr, table)
        j = right_index = expr_eval(node.right.expr, table)

        i = check_index(i, L)
        j = check_index(j, R)

        L[i], R[j] = R[j], L[i]

    return table

def var_condition_eval(node, table):
    """
    Deallocates variables according to conditions.
    Returns a memory table.
    """

    if table.refs[node.name] == expr_eval(node.expr, table):
        del table.refs[node.name]
    else:
        # TODO: An error, not just a warning, should be thrown here.
        print(
            node.name, "is supposed to be",
            expr_eval(node.expr, table),
            "but it's actually",
            table.refs[node.name]
            )

    return table

def statement_eval(node, table):
    """
    Evaluates statement nodes. Returns a memory table.
    """

    if node.kind == "MOD_OP":
        table = mod_op_eval(node, table)

    elif node.kind == "SWAP_OP":
        table = swap_op_eval(node, table)

    elif node.kind == "FROM_LOOP":
        block_node = node.block

        # TODO: check start condition

        while True:
            # Execute the block.
            table = block_eval(block_node, table)

            # Continue until the end condition is satisfied.
            if expr_eval(node.end_condition, table):
                break

    elif node.kind == "FOR_LOOP":
        var_dec = node.var_declaration
        until_node = node.end_condition
        increment_node = node.increment_statement

        # Initialize the variable.
        table[var_dec.name] = expr_eval(var_dec.expr, table)

        while True:
            # Execute the block and increment statement.
            if not node.inc_at_end:
                table = mod_op_eval(increment_node, table)
            
            table = block_eval(node.block, table)

            if node.inc_at_end:
                table = mod_op_eval(increment_node, table)

            # Repeat until the end condition is satisfied.
            if table.refs[until_node.name] == expr_eval(until_node.expr, table):
                break

        table = var_condition_eval(until_node, table)

    elif node.kind == "IF":
        # Check the condition; if it fails, execute the
        # 'false' branch if it exists.

        if expr_eval(node.condition, table):
            table = block_eval(node.true, table)
        elif "false" in node.data:
            table = block_eval(node.false, table)

    elif node.kind == "DO/UNDO":
        # Do the action_block, then do the yielding block,
        # then undo the action block.
        table = block_eval(node.action_block, table)

        if "yielding_block" in node.data:
            table = block_eval(node.yielding_block, table)

        table = block_eval(inverter.unblock(node.action_block), table)

    elif node.kind == "RESULT":
        # Overwrites the variable 'result' with the given expression.
        table["result"] = expr_eval(node.expr, table)

    elif node.kind == "VAR_DEC":
        table[node.name] = expr_eval(node.expr, table)

    elif node.kind == "VAR_CONDITION":
        table = var_condition_eval(node, table)

    elif node.kind == "BLOCK":
        table = block_eval(node, table)

    elif node.kind == "FUNCTION_CALL":
        # Call the function, then update table with the results.

        # TODO: Use function object code here.
        if node.backwards:
            function = shared.program.unfunctions[node.name]
        else:
            function = shared.program.functions[node.name]

        table.update_refs(
            function_eval(
                node=function,
                ref_arg_vars=node.ref_args,
                ref_arg_vals=[expr_eval(arg, table) for arg in node.ref_args],
                const_arg_vals=[expr_eval(arg, table) for arg in node.const_args]
            )
        )

    elif node.kind == "UN":
        inverted_node = inverter.unstatement(node.statement)
        table = statement_eval(inverted_node, table)

    elif node.kind in ("ENTER", "EXIT"):
        print(node.kind, node.condition)

    return table

def block_eval(node, table=Memory()):
    """
    Evaluates blocks. Returns a memory table.
    """

    for statement in node.statements:
        table = statement_eval(statement, table)
    return table

def function_eval(node, ref_arg_vars, ref_arg_vals, const_arg_vals):
    """
    Given a list of reference and constant args, evaluates functions.
    Returns a memory table.
    """

    # Create a memory table for the function by zipping up
    # the arguments into (parameter, value) pairs.
    table = Memory(
        zip([var.name for var in node.ref_parameters], ref_arg_vals),
        zip([var.name for var in node.const_parameters], const_arg_vals)
        )

    result = block_eval(node.block, table)

    # Go through the variable names in the function's memory table
    # and change them to the new names.
    for arg, param in zip(ref_arg_vars, node.ref_parameters):
        result.refs[arg.name] = result.refs[param.name]

        # If a function like
        # 
        # f (ref x){
        #   ...
        # }
        # 
        # was called like
        # 
        # f(&x)
        # 
        # then we shouldn't delete 'x' from the resulting memory table.
        if arg.name != param.name:
            del result.refs[param.name]

    return result

def program_eval(node):
    """
    Evaluates the entire program.
    Returns a memory table of the main variables.
    """

    table = Memory(node.main_vars)
    return block_eval(node.main.block, table)