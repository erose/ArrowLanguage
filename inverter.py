import shared, parser

op_inverses = {
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*"
}

def unexpression(node):
    if node.kind == "FUNCTION_CALL":
        return parser.ParseNode("FUNCTION_CALL",
            name=node.name,
            backwards= not (node.backwards),
            ref_args=node.ref_args,
            const_args=node.const_args
            )

    if node.kind == "BIN_OP":
        return parser.ParseNode("BIN_OP",
            op=node.op,
            left=unexpression(node.left),
            right=unexpression(node.right))

    elif node.kind == "NEGATE":
        return parser.ParseNode("NEGATE", expr=unexpression(node.expr))

    elif node.kind == "NUM":
        return node

    elif node.kind == "VAR_REF":
        return node

    elif node.kind == "ARRAY_REF":
        return parser.ParseNode("ARRAY_REF",
            name=node.string, expr=unexpression(node.expr))

    elif node.kind == "ARRAY_EXPR":
        return parser.ParseNode("ARRAY_EXPR",
            entries=[unexpression(entry) for entry in node.entries])

def unstatement(node):
    if node.kind == "MOD_OP":
        return parser.ParseNode(
            "MOD_OP",
            op=op_inverses[node.op],
            var=node.var, expr=unexpression(node.expr))

    elif node.kind == "FROM_LOOP":
        return parser.ParseNode("FROM_LOOP",
            start_condition=node.end_condition,
            block=unblock(node.block),
            end_condition=node.start_condition
            )

    elif node.kind == "FOR_LOOP":
        return parser.ParseNode("FOR_LOOP",
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
            return parser.ParseNode("IF",
                condition=node.result,
                true=unblock(node.true),
                result=node.condition,
                false=unblock(node.false)
                )
        else:
           return parser.ParseNode("IF",
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
        return parser.ParseNode("FUNCTION_CALL",
            name=node.name,
            backwards= not (node.backwards),
            ref_args=node.ref_args,
            const_args=node.const_args
            )

    elif node.kind == "SWAP_OP":
        return node

    elif node.kind == "RESULT":
        return node

    elif node.kind == "UN":
        return node.statement

def unblock(node):
    inverted = parser.ParseNode("BLOCK")
    inverted.statements = (
        [unstatement(s) for s in reversed(node.statements)]
        )

    return inverted

def unfunction(node):
    inverted = parser.ParseNode("FUNCTION")
    inverted.ref_parameters = node.ref_parameters
    inverted.const_parameters = node.const_parameters
    inverted.name = node.name
    inverted.block = unblock(node.block)
    return inverted