import shared, datatypes, inverter, evaluator, collections

class ParseNode:
    """
    A node in the abstract syntax tree.
    """

    def __init__(self, kind, **kwargs):
        self.kind = kind
        self.data = dict(**kwargs)

    def replace(self, kind=None, **kwargs):
        """
        Returns a node with updated data.
        """

        new_data = self.data.copy()
        new_data.update(kwargs)

        if kind is None:
            return ParseNode(self.kind, **new_data)
        else:
            return ParseNode(kind, **new_data)

    def __getattr__(self, attr):
        if attr in self.data:
            return self.data[attr]
        
        raise KeyError(attr)

    # def flatten(self, d=0):
    #     for item in self.data.values():
    #         if isinstance(item, ParseNode):
    #             yield item, d
    #             yield from item.flatten(d+1)
    #         elif isinstance(item, collections.Iterable):
    #             for a in item:
    #                 if isinstance(a, ParseNode):
    #                     yield a, d
    #                     yield from a.flatten(d+1)

    def __repr__(self):
        return "{}, {}".format(str(self.kind), str(self.data))

class Parser:
    """
    The base class for the ArrowParser object, providing utility and
    processing methods.
    """

    def __init__(self, tokens):
        self.token_iter = iter(tokens)
        self.current = next(self.token_iter)
        self.lookahead = next(self.token_iter)

    def raise_error(self, message):
        raise shared.ArrowException(
            shared.Stages.parsing,
            message,
            self.current)

    # 
    # These 8 methods are aliases for process() with various switches
    # on or off.
    # 

    def accept_kinds(self, *kinds):
        return self.process(kinds=kinds, boolean=False, necessary=False)

    def confirm_kinds(self, *kinds):
        return self.process(kinds=kinds, boolean=True, necessary=True)

    def check_kinds(self, *kinds):
        return self.process(kinds=kinds, boolean=True, necessary=False)

    def expect_kinds(self, *kinds):
        return self.process(kinds=kinds, boolean=False, necessary=True)

    def accept_strings(self, *strings):
        return self.process(strings=strings, boolean=False, necessary=False)

    def confirm_strings(self, *strings):
        return self.process(strings=strings, boolean=True, necessary=True)

    def check_strings(self, *strings):
        return self.process(strings=strings, boolean=True, necessary=False)

    def expect_strings(self, *strings):
        return self.process(strings=strings, boolean=False, necessary=True)

    def error_message(self, kinds, strings):
        message = "Expected {}, but found {}.".format(
            " or ".join(["'" + s + "'" for s in strings]) if strings
            else "something of kind {}".format(" or ".join(kinds)),
            "'" + self.current.string + "'"
            )
        return message

    def process(self, kinds=[], strings=[], boolean=None, necessary=None):
        """
        Checks input against the current token and consumes it.
        Return type varies depending on the arguments.
        """

        kind, string = self.current.kind, self.current.string

        if kind in kinds or string in strings:
            try:
                self.current = self.lookahead
                self.lookahead = next(self.token_iter)
            except StopIteration:
                pass

            if boolean:     return True
            if necessary:   return string
            else:           return True, string
        else:
            if necessary:
                self.raise_error(self.error_message(kinds, strings))
            if boolean:     return False
            else:           return False, None
            
class ArrowParser(Parser):
    def program(self):
        function_nodes = {}
        names = []
        vals = []

        while self.current.kind != "EOF":
            if self.check_strings("main"):
                self.confirm_strings("(")

                while not self.check_strings(")"):
                    var_dec = self.var_dec()
                    names.append(var_dec.name)
                    vals.append(var_dec.expr)

                    self.accept_strings(",")


                main = datatypes.Function("main",
                    names,
                    [],
                    self.block()
                    )

                function_nodes["main"] = main

            else:
                f = self.function()
                function_nodes[f.name] = f

        node = ParseNode(
            "PROGRAM",
            main_vars={name: evaluator.expr_eval(val)
                for name, val in zip(names, vals)
            },
            main=main,
            functions=function_nodes
            )

        shared.program = node
        return node

    def function(self):
        name = self.expect_kinds("ID")
        self.confirm_strings("(")
        ref_parameters = []
        const_parameters = []

        while True:
            if self.check_strings("ref"):
                var = self.V()
                ref_parameters.append(var.name)
            elif self.check_strings("const"):
                var = self.V()
                const_parameters.append(var.name)
            if self.current.string == ")":
                break
            self.confirm_strings(",")

        self.confirm_strings(")")

        block = self.block()
        return datatypes.Function(
            name, ref_parameters, const_parameters, block)

    def block(self):
        self.confirm_strings("{")
        node = ParseNode("BLOCK", statements=[])
        
        while self.current.string != "}":
            node.statements.append(self.statement())

        self.confirm_strings("}")
        return node

    def statement(self):
        if self.current.kind == "ID":
            if self.current.string == "un":
                return self.un()
            elif self.lookahead.string == "(":
                return self.function_call()
            elif self.lookahead.string == ":=":
                return self.var_dec()
            elif self.lookahead.string == "==":
                return self.var_condition()
            else:
                return self.mod_operation()

        if self.current.kind == "KEYWORD":
            if self.current.string == "from":
                return self.from_loop()
            if self.current.string == "for":
                return self.for_loop()
            if self.current.string == "if":
                return self.if_statement()
            if self.current.string == "do/undo":
                return self.do_undo_statement()
            if self.current.string == "result":
                return self.result_statement()
            if self.current.string in ("enter", "exit"):
                return self.enter_or_exit_statement()

        if self.current.string == "{":
            return self.block()

        self.raise_error(
            "Expected a statement, but found '{}'.".format(self.current.string))

    def enter_or_exit_statement(self):
        if self.check_strings("enter"):
            value_node = self.expression()
            self.confirm_strings("if")
            return ParseNode(
                "ENTER",
                value=value_node,
                condition=self.expression()
                )

        elif self.check_strings("exit"):
            value_node = self.expression()
            self.confirm_strings("if")
            return ParseNode(
                "EXIT",
                value=value_node,
                condition=self.expression()
                )

    def un(self):
        self.confirm_strings("un")
        self.confirm_strings("(")
        self.confirm_strings(":")
        statement_node = self.statement()
        self.confirm_strings(":")
        self.confirm_strings(")")
        return ParseNode("UN", statement=statement_node)

    def result_statement(self):
        self.confirm_strings("result")
        return ParseNode("RESULT", expr=self.expression())

    def var_dec(self):
        var_name = self.expect_kinds("ID")
        self.confirm_strings(":=")

        return ParseNode(
            "VAR_DEC", name=var_name, expr=self.init_expr())

    def init_expr(self):
        if self.check_strings("["):
            node = ParseNode("ARRAY_EXPR", entries=[])

            while not self.check_strings("]"):
                node.entries.append(self.expression())
                self.accept_strings(",")
            return node
            
        else:
            return self.expression()

    def var_condition(self):
        var_name = self.expect_kinds("ID")
        self.confirm_strings("==")

        return ParseNode("VAR_CONDITION", name=var_name, expr=self.init_expr())

    def mod_operation(self):
        v_node = self.V()
        op = self.expect_strings("+=", "-=", "^=", "*=", "/=", "<=>")
        if op == "<=>":
            if self.current.kind != "ID":
                self.raise_error(
                    "Can't swap '{}' with '{}' because '{}' is not a variable name.".format(
                        v_node.name, self.current.string, self.current.string
                        ))
            other_v_node = self.V()
            return ParseNode("SWAP_OP",
                left=v_node, right=other_v_node)

        expr_node = self.expression()

        return ParseNode("MOD_OP",
            op=op[0], #We only want the '+' from the '+='
            var=v_node, expr=expr_node
            )

    def for_loop(self):
        self.confirm_strings("for")
        self.accept_strings("(")
        var_declaration_node = self.var_dec()
        self.accept_strings(")")

        if self.check_strings(","):
            self.accept_strings("(")
            increment_statement_node = self.mod_operation()
            self.accept_strings(")")

            increment_at_end = False

        block_node = self.block()

        if not self.current.string == "until":
            self.accept_strings("(")
            increment_statement_node = self.mod_operation()
            self.accept_strings(")")

            increment_at_end = True
            self.confirm_strings(",")

        self.confirm_strings("until")
        self.accept_strings("(")
        end_condition_node = self.var_condition()
        self.accept_strings(")")

        return ParseNode("FOR_LOOP",
            inc_at_end=increment_at_end,
            var_declaration=var_declaration_node,
            increment_statement=increment_statement_node,
            block=block_node,
            end_condition=end_condition_node
            )

    def from_loop(self):
        self.confirm_strings("from")
        start_condition_node = self.expression()

        block_node = self.block()

        self.confirm_strings("until")
        end_condition_node = self.expression()

        return ParseNode("FROM_LOOP",
            start_condition=start_condition_node,
            block=block_node,
            end_condition=end_condition_node
            )

    def if_statement(self):
        beginning_line = self.current.line_num
        self.confirm_strings("if")
        
        condition_node = self.expression()

        block_node = self.block()

        if self.check_strings("=>"):
            result_node = self.expression()
        elif self.check_strings("<=>"):
            result_node = condition_node
        else:
            self.raise_error(
                ("If-statement starting on line {} "
                "missing post-condition or '<=>'.").format(beginning_line)
                )

        if self.check_strings("else"):
            else_node = self.block()

            return ParseNode("IF",
                condition=condition_node,
                true=block_node,
                result=result_node,
                false=else_node
                )

        return ParseNode("IF",
            condition=condition_node,
            true=block_node,
            result=result_node,
            )

    def do_undo_statement(self):
        self.confirm_strings("do/undo")
        action_block = self.block()

        if self.check_strings("yielding"):
            yielding_block = self.block()

            return ParseNode("DO/UNDO",
                action_block=action_block,
                yielding_block=yielding_block
                )

        return ParseNode("DO/UNDO",
            action_block=action_block)

    def expression(self):
        node = self.C()
        while self.current.string in ("<", ">", "<=", ">=", "==", "!="):
            op = self.expect_strings("<", ">", "<=", ">=", "==", "!=")
            other = self.C()
            node = ParseNode("BIN_OP",
                op=op,
                left=node, right=other)

        return node

    def C(self):
        node = self.A()
        while self.current.string == "%":
            op = self.expect_strings("%")
            other = self.A()
            node = ParseNode("BIN_OP",
                op=op,
                left=node, right=other)

        return node

    def A(self):
        node = self.M()
        while self.current.string in ("+", "-"):
            op = self.expect_strings("+", "-")
            other = self.M()
            node = ParseNode("BIN_OP",
                op=op,
                left=node, right=other)

        return node

    def M(self):
        node = self.P()
        while self.current.string in ("*", "/"):
            op = self.expect_strings("*", "/")
            other = self.P()
            node = ParseNode("BIN_OP",
                op=op,
                left=node, right=other)

        return node

    def P(self):
        if self.current.kind == "ID":
            if self.lookahead.string == "(":
                return self.function_call()
            else:
                return self.V()

        if self.current.string == "-":
            return self.unary()

        if self.current.kind == "DIGITS":
            return self.number()

        if self.current.kind == "STRING":
            string = self.expect_kinds("STRING")
            stripped_string = string[1:-1]
            return ParseNode(
                "STRING",
                string=datatypes.String(stripped_string)
                )

        if self.check_strings("("):
            node = self.expression()
            self.confirm_strings(")")
            return node

    def unary(self):
        if self.check_strings("-"):
            p = self.P()
            node = ParseNode("NEGATE", expr=p)
            return node

    def function_call(self):
        name = self.expect_kinds("ID")
        self.confirm_strings("(")
        ref_args = []
        const_args = []

        while True:
            if self.current.string == ")":
                break

            if self.check_strings("&"):
                var = self.V()
                ref_args.append(var)
            else:
                expr = self.expression()
                const_args.append(expr)

            if self.current.string == ")":
                break
            self.confirm_strings(",")

        self.confirm_strings(")")
        return ParseNode("FUNCTION_CALL", name=name, backwards=False,
            ref_args=ref_args,
            const_args=const_args)

    def V(self):
        string = self.expect_kinds("ID")
        if self.check_strings("["):
            expr_node = self.expression()
            self.confirm_strings("]")
            return ParseNode("ARRAY_REF", name=string, expr=expr_node)
        
        return ParseNode("VAR_REF", name=string)

    def number(self):
        base_numerator = int(self.expect_kinds("DIGITS"))

        if self.check_strings(".") and self.lookahead.kind == "DIGIT":
            after_point = self.expect_kinds("DIGITS").rstrip("0")

            power = 10 ** len(after_point)
            numerator = (base_numerator * power
                + (int(after_point) if after_point else 0))
            denominator = power

        else:
            numerator = base_numerator
            denominator = 1
        
        return ParseNode("NUM",
            number=datatypes.Num(numerator, denominator))