import re, collections, shared
Token = collections.namedtuple(
    'Token', ['kind', 'string', 'line_num', 'char_num'])

def tokenizer(kind):
    """
    Returns a function which generates tokens for a given regexp.
    """
    return lambda scanner, string: Token(kind, string, scanner.line_num, None)

def raise_error(token):
    raise shared.ArrowException(
        shared.Stages.scanning,
        "Unrecognized symbol '{}'.".format(token.string),
        token)

class Scanner:
    def __init__(self, file_string):
        self.file_string = file_string
        self.scanner = re.Scanner([
            # Skip whitespace.
            (r"\s+", tokenizer("SKIPPABLE")),
            # Skip comments, which are either hashtags or C-style /* ... */.
            (r"#.*|\/\*.*\*\/", tokenizer("SKIPPABLE")),
            # String literals.
            (r"\".*?\"", tokenizer("STRING")),
            # Keywords.
            (r"\bexit\b|\benter\b|\bdo/undo\b|\byielding\b|\bresult\b|\buntil\b|\bconst\b|\bfrom\b|\bfor\b|\bref\b|\bif\b", tokenizer("KEYWORD")),
            # Identifiers.
            # (though the '.' technically isn't allowed in identifiers,
            #  it's considered part of an identifier internally.)
            (r"[a-zA-Z_]+(\d|[a-zA-Z_]|\.)*", tokenizer("ID")),
            # Number literals.
            (r"\d+", tokenizer("DIGITS")),
            # Symbols.
            (r"\.|\*=|/=|\^=|\+=|-=|%|&|\+|-|\/|\*|<=>|<=|>=|==|!=|:=|=>|>|<|=|:|\[|\]|\(|\)|{|}|,",
                tokenizer("SYMBOL")),
            # We don't recognize anything else.
            (r".*", tokenizer("UNRECOGNIZED"))
        ])

    def tokens(self):
        with open(self.file_string, "r") as f:
            # Store the entire file. 
            shared.code = [line.rstrip() for line in f.readlines()]

            for line_num, line in enumerate(shared.code):
                self.scanner.line_num = line_num
                results, remainder = self.scanner.scan(line)

                # In order for each token to know where it is on the line,
                # we keep track of how far we are into the current line.
                current_char = 0
                for token in results:
                    token = token._replace(char_num=current_char)
                    
                    if token.kind == "UNRECOGNIZED":
                        raise_error(token)
                    elif token.kind == "SKIPPABLE":
                        pass
                    else:
                        yield token

                    current_char += len(token.string.expandtabs())

        yield Token("EOF", "", line_num, current_char)

if __name__ == "__main__":
    scanner = Scanner("test.txt")
    for kind, string in scanner.tokens():
        print(kind, string)