import shared, parser, datatypes

op_inverses = {
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*"
}

def unexpression(node):
    if node.kind == "FUNCTION_CALL":
        return node.replace(backwards= not (node.backwards))

    if node.kind == "BIN_OP":
        return node.replace(
            left=unexpression(node.left),
            right=unexpression(node.right)
            )

    elif node.kind == "NEGATE":
        return node.replace(expr=unexpression(node.expr))

    elif node.kind == "NUM":
        return node

    elif node.kind == "VAR_REF":
        return node

    elif node.kind == "ARRAY_REF":
        return node.replace(expr=unexpression(node.expr))

    elif node.kind == "ARRAY_EXPR":
        return node.replace(
            entries=[unexpression(entry) for entry in node.entries])

def unstatement(node):
    if node.kind == "MOD_OP":
        return node.replace(
            op=op_inverses[node.op],
            expr=unexpression(node.expr)
            )

    elif node.kind == "FROM_LOOP":
        return node.replace(
            start_condition=node.end_condition,
            block=unblock(node.block),
            end_condition=node.start_condition
            )

    elif node.kind == "FOR_LOOP":
        return node.replace(
            inc_at_end = not node.inc_at_end,
            var_declaration=unstatement(node.end_condition),
            increment_statement=unstatement(node.increment_statement),
            block=unblock(node.block),
            end_condition=unstatement(node.var_declaration)
            )

    elif node.kind == "BLOCK":
        return unblock(node)

    elif node.kind == "VAR_DEC":
        return parser.ParseNode("VAR_CONDITION",
            name=node.name, expr=node.expr
            )

    elif node.kind == "VAR_CONDITION":
        return parser.ParseNode("VAR_DEC",
            name=node.name, expr=node.expr
            )

    elif node.kind == "IF":
        if "false" in node.data:
            return node.replace(
                condition=node.result,
                true=unblock(node.true),
                false=unblock(node.false),
                result=node.condition
                )
        else:
            return node.replace(
                condition=node.result,
                true=unblock(node.true),
                result=node.condition
                )

    elif node.kind == "DO/UNDO":
        if "yielding_block" in node.data:
            return parser.ParseNode("DO/UNDO",
                action_block=node.action_block,
                yielding_block=unblock(node.yielding_block)
                )
        else:
            return parser.ParseNode("DO/UNDO",
                action_block=node.action_block
                )

    elif node.kind == "FUNCTION_CALL":
        return node.replace(backwards= not node.backwards)

    elif node.kind == "EXIT":
        return node.replace("ENTER")

    elif node.kind == "ENTER":
        return node.replace("EXIT")

    elif node.kind in ("SWAP_OP", "RESULT"):
        return node

    elif node.kind == "UN":
        return node.statement

def unblock(node):
    inverted = parser.ParseNode("BLOCK")
    inverted.statements = (
        [unstatement(s) for s in reversed(node.statements)]
        )

    return inverted

def unfunction(f):
    return datatypes.Function(
        f.name,
        f.ref_parameters,
        f.const_parameters,
        unblock(f.block)
        )