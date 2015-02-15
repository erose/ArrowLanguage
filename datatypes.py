import numbers, functools, evaluator, inverter, shared

@functools.total_ordering
class Num:
    """
    Because floating-point numbers lead to irreversibility, infinite-precision
    rational numbers are used in Arrow.
    """
    def __init__(self, top, bottom=None, sign=None):
        """
        Nums store a numerator, denominator, and sign (either 1 or -1).
        """

        if bottom is None:
            bottom = 1

        if sign is None:
            # If top and bottom's signs match, self.sign is positive.
            if (bottom > 0) == (top > 0):
                self.sign = 1
            # Otherwise it's negative.
            else:
                self.sign = -1
        else:
            self.sign = sign

        # Top and bottom are positive only, since +/- is stored in self.sign.
        self.top = abs(top)
        self.bottom = abs(bottom)

        # Because Nums are immutable, a reduction to lowest terms
        # in the constructor ensures they are always in lowest form.
        self.reduce()

    @staticmethod
    def gcd(a, b):
        # Euclid's algorithm.
        while True:
            a, b = b, a % b
            if b == 0:
                return a

    def reduce(self):
        """
        Reduce this fraction to lowest terms.
        """

        # While the top and bottom have a factor in common, divide it out.
        while True:
            d = Num.gcd(self.top, self.bottom)
            if d == 1:
                break

            # Integer division here because the whole point
            # is to remain within the integers!
            self.top, self.bottom = self.top // d, self.bottom // d

    def reciprocal(self):
        return Num(self.bottom, self.top, sign=self.sign)

    def __add__(self, other):
        # a/b + c/d = (ad)/(bd) + (bc)/(bd) = (ad + bc)/(bd)
        a, b, c, d = self.top, self.bottom, other.top, other.bottom
        return Num(a*self.sign*d + b*c*other.sign, b*d)

    def __sub__(self, other):
        return self + (-other)

    def __neg__(self):
        return Num(self.top, self.bottom, sign=-self.sign)

    def __mul__(self, other):
        return Num(self.top*other.top, self.bottom*other.bottom,
            sign=self.sign*other.sign)

    def __truediv__(self, other):
        return self * other.reciprocal()

    def __mod__(self, other):
        return Num(self.top % other.top)
            
    __rmul__ = __mul__
    __radd__ = __add__
    __rsub__ = lambda self, other: -self + other
    __rtruediv__ = lambda self, other: self.reciprocal() * other

    def __repr__(self):
        if self.bottom == 1:
            return str(self.top * self.sign)
        else:
            return "({}/{})".format(self.top * self.sign, self.bottom)

    def __eq__(self, other):
        return (
            self.top == other.top
            and self.bottom == other.bottom
            and self.sign == other.sign
            )

    def __lt__(self, other):
        return True if (self - other).sign == -1 else False

class Function:
    """
    Functions are first-class objects in Arrow.
    """

    def __init__(self, name, refs, consts, block):
        """
        Functions store
            - their name
            - their code
            - their parameters and those parameters' types, in L-to-R order.
            - a list of their entry conditions (in bottom-up order).
        """

        self.name = name
        self.block = block

        self.ref_parameters = refs
        self.const_parameters = consts

    def execute(self, backwards, table):
        # Go up from the bottom, looking for enter statements, in order to
        # find out where we should start executing.

        # The backwards flag tells us whether we are calling or uncalling.
        block = inverter.unblock(self.block) if backwards else self.block

        # TODO: this approach only finds un-nested enter statements.
        to_execute = []
        for node in reversed(block.statements):
            if node.kind == "ENTER":
                if evaluator.expr_eval(node.condition, table):
                    table["result"] = evaluator.expr_eval(node.value, table)
                    break
            to_execute.append(node)

        block_to_execute = self.block.replace(statements=to_execute[::-1])

        # Execute the block. If it returns, catch the return exception
        # and update the table accordingly.
        try:
            table = evaluator.block_eval(block_to_execute, table)
        
        except shared.ReturnException as e:
            table["result"] = e.value

    def evaluate(self, backwards, ref_arg_vars, ref_arg_vals, const_arg_vals):
        """
        Given a list of reference and constant args, evaluates functions.
        Returns a memory table.
        """

        # Create a memory table for the function by zipping up
        # the arguments into (parameter, value) pairs.
        table = evaluator.Memory(
            zip(self.ref_parameters, ref_arg_vals),
            zip(self.const_parameters, const_arg_vals)
            )

        self.execute(backwards, table)

        # Go through the variable names in the function's memory table
        # and change them to the new names.
        for arg, param_name in zip(ref_arg_vars, self.ref_parameters):
            table.refs[arg.name] = table.refs[param_name]

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
            if arg.name != param_name:
                del table.refs[param_name]

        return table

class BuiltinFunction(Function):
    """
    """

    def __init__(self, name, refs, consts, python_function, inverse_function):
        self.name = name
        self.python_function = python_function

        self.ref_parameters = refs
        self.const_parameters = consts
        self.inverse_function = inverse_function

    def execute(self, backwards, table):
        # Run the appropriate underlying Python function.
        if backwards:
            table["result"] = self.inverse_function(table)
        else:
            table["result"] = self.python_function(table)

class List:
    """
    Arrow's list/array datatype, also serving as a stack.
    """

    def __init__(self, contents):
        self.contents = contents

        self._push = self.push
        self._pop = self.pop

        self.push = BuiltinFunction("push", [], ["data"], self.push, self._pop)
        self.pop = BuiltinFunction("pop", [], [], self.pop, self._push)

    # @builtin_method(consts=["data"])
    def push(self, table):
        self.contents.append(table["data"])
        return table

    # @builtin_method()
    def pop(self, table):
        return self.contents.pop()

    # @builtin_method()
    def empty(self, table):
        return len(self.contents) == 0

    def check_index(self, index):
        """
        Raises an error if the index isn't valid.
        """

        if index.bottom != 1:
            pass
            #Only access arrays with whole indices!
        elif index.top >= len(self):
            pass
            #Array out of bounds error!
        elif index.sign == -1:
            pass
            #Indexes can't be negative!

    def __getitem__(self, index):
        self.check_index(index)
        # After checking, we know the index is n/1 so we just grab index.top
        return self.contents[index.top]

    def __setitem__(self, index, value):
        self.check_index(index)
        # Again, the index is n/1 at this point.
        self.contents[index.top] = value

    def __len__(self):
        return len(self.contents)

    def __repr__(self):
        return self.contents.__repr__()

class String:
    """
    Arrow's string datatype.
    """

    def __init__(self, python_str):
        self.str = python_str

    def __add__(self, other):
        return self.str + other.str

    def __repr__(self):
        return self.str

if __name__ == "__main__":
    x = Num(-1)
    y = Num(1, 2)

    print(x)
    print(-y)
    print(y - x)
    print(x / y)