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
    def __init__(self, ref_vars={}, const_vars={}):
        self.refs = dict(ref_vars)
        self.consts = dict(const_vars)

    def __contains__(self, key):
        return key in self.refs or key in self.consts

    def __getitem__(self, name):
        if name in self.refs:
            return self.refs[name]
        if name in self.consts:
            return self.consts[name]

        print(self.refs, name)

        # BROKEN
        raise shared.ArrowException(
            "evaluation",
            "{} not found in table.".format(name),
            current_node.token
            )

    def __setitem__(self, name, value):
        if name in self.consts:
            # BROKEN
            raise shared.ArrowException(
                "evaluation",
                "Modifying constant {} not allowed.".format(name),
                current_node.token
                )
        else:
            self.refs[name] = value

    def initialize(self, v_node, value):
        self.refs[v_node.name] = value

    def update_refs(self, other):
        for key in other.refs:
            if key in self.refs:
                self.refs[key] = other.refs[key]

    def __repr__(self):
        return "refs: {}, consts: {}".format(self.refs, self.consts)

    def copy(self):
        return Memory(self.refs, self.consts)

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
    global current_node
    current_node = node

    if node.kind == "BIN_OP":
        left = expr_eval(node.left, table)
        right = expr_eval(node.right, table)
        return bin_ops[node.op](left, right)

    elif node.kind == "NEGATE":
        return -expr_eval(node.expr, table)

    elif node.kind == "NUM":
        return node.number

    elif node.kind == "VAR_REF":
        return table[node.name]

    elif node.kind == "ARRAY_REF":
        array = table[node.name]
        index = expr_eval(node.expr, table)
        index = check_index(index, array)

        return array[index]

    elif node.kind == "FUNCTION_CALL":
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
        return [expr_eval(entry, table) for entry in node.entries]

def mod_op_eval(node, table):
    """
    Evaluates mod-op nodes. Returns a memory table.
    """
    global current_node
    current_node = node

    expr_value = expr_eval(node.expr, table)
    old_value = table[node.var.name]

    if node.var.kind == "ARRAY_REF":
        array = table[node.var.name]
        index = expr_eval(node.var.expr, table)
        index = check_index(index, array)

        new_value = bin_ops[node.op](array[index], expr_value)
        array[index] = new_value

    elif node.var.kind == "VAR_REF":
        new_value = bin_ops[node.op](table[node.var.name], expr_value)
        table[node.var.name] = new_value

    return table

def var_condition_eval(node, table):
    """
    Tests and executes var conditions. Returns a memory table.
    """
    global current_node
    current_node = node

    if table.refs[node.name] == expr_eval(node.expr, table):
        del table.refs[node.name]
    else:
        print(
            node.name, "is supposed to be",
            expr_eval(node.expr, table),
            "but it's actually",
            table.refs[node.name]
            )
        #Local variable deassignment condition not met error.

    return table

def statement_eval(node, table):
    """
    Evaluates statement nodes. Returns a memory table.
    """
    global current_node
    current_node = node

    new = table.copy()

    if node.kind == "MOD_OP":
        new = mod_op_eval(node, new)

    elif node.kind == "SWAP_OP":
        if node.left.kind == "VAR_REF" and node.right.kind == "VAR_REF":

            l, r = node.left.name, node.right.name
            new[l], new[r] = new[r], new[l]

        if node.left.kind == "ARRAY_REF" and node.right.kind == "VAR_REF":

            l_array, r = table[node.left.name], node.right.name
            l_index = expr_eval(node.left.expr, table)
            l_index = check_index(l_index, l_array)

            l_array[l_index], new[r] = new[r], l_array[l_index]

        if node.left.kind == "VAR_REF" and node.right.kind == "ARRAY_REF":

            l, r_array = node.left.name, table[node.right.name]
            r_index = expr_eval(node.right.expr, table)
            r_index = check_index(r_index, r_array)

            new[l], r_array[r_index] = r_array[r_index], new[l]

        if node.left.kind == "ARRAY_REF" and node.right.kind == "ARRAY_REF":

            L, R = left_array, right_array = table[node.left.name], table[node.right.name]
            i = left_index = expr_eval(node.left.expr, table)
            j = right_index = expr_eval(node.right.expr, table)

            i = check_index(i, L)
            j = check_index(j, R)

            L[i], R[j] = R[j], L[i]

    elif node.kind == "FROM_LOOP":
        block_node = node.block
        until_node = node.end_condition

        # TODO: check start condition

        new = block_eval(block_node, new)
        while not expr_eval(until_node, new):
            new = block_eval(block_node, new)

    elif node.kind == "FOR_LOOP":
        var_dec = node.var_declaration
        block_node = node.block
        until_node = node.end_condition
        increment_node = node.increment_statement

        new.initialize(var_dec, expr_eval(var_dec.expr, table))

        while new.refs[until_node.name] != expr_eval(until_node.expr, new):
            if not node.inc_at_end:
                new = mod_op_eval(increment_node, new)
            
            new = block_eval(block_node, new)

            if node.inc_at_end:
                new = mod_op_eval(increment_node, new)

        new = var_condition_eval(until_node, new)

    elif node.kind == "IF":
        condition_node = node.condition

        if expr_eval(condition_node, table):
            new = block_eval(node.true, new)
        elif "false" in node.data:
            new = block_eval(node.false, new)

    elif node.kind == "DO/UNDO":
        new = block_eval(node.action_block, new)

        if "yielding_block" in node.data:
            new = block_eval(node.yielding_block, new)

        new = block_eval(inverter.unblock(node.action_block), new)

    elif node.kind == "RESULT":
        new["result"] = expr_eval(node.expr, new)

    elif node.kind == "VAR_DEC":
        new.initialize(node, expr_eval(node.expr, table))

    elif node.kind == "VAR_CONDITION":
        new = var_condition_eval(node, new)

    elif node.kind == "BLOCK":
        new = block_eval(node, new)

    elif node.kind == "FUNCTION_CALL":
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

        new.update_refs(result)

    elif node.kind == "UN":
        inverted_node = inverter.unstatement(node.statement)
        new = statement_eval(inverted_node, table)

    return new

def block_eval(node, table=Memory()):
    """
    Evaluates blocks. Returns a memory table.
    """
    global current_node
    current_node = node

    if node.kind == "BLOCK":
        for statement in node.statements:
            table = statement_eval(statement, table)
    return table

def function_eval(node, ref_arg_vars, ref_arg_vals, const_arg_vals):
    """
    Given a list of reference and constant args, evaluates functions.
    Returns a memory table.
    """
    global current_node
    current_node = node

    table = Memory(
        zip([var.name for var in node.ref_parameters], ref_arg_vals),
        zip([var.name for var in node.const_parameters], const_arg_vals)
        )

    result = block_eval(node.block, table)

    for arg, param in zip(ref_arg_vars, node.ref_parameters):
        result.refs[arg.name] = result.refs[param.name]
        if arg.name != param.name:
            del result.refs[param.name]

    return result

def program_eval(node):
    """
    Evaluates the entire program.
    Returns a memory table of the main variables.
    """
    global current_node
    current_node = node

    table = Memory(node.main_vars)
    return block_eval(node.main.block, table)