import numbers, functools

@functools.total_ordering
class Num:
    def __init__(self, top, bottom=None, sign=None):
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
        while True:
            d = Num.gcd(self.top, self.bottom)
            if d == 1: break

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


if __name__ == "__main__":
    x = Num(-1)
    y = Num(1, 2)

    print(x)
    print(-y)
    print(y - x)
    print(x / y)