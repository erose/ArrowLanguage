import scanner, parser, sys, evaluator, inverter, shared

def colorize(s, desired_color):
    """
    Wraps string s in the appropriate ANSI color codes.
    """
    
    termcolors = {
    "PURPLE" : '\033[95m',
    "BLUE" : '\033[94m',
    "GREEN" : '\033[92m',
    "YELLOW" : '\033[93m',
    "RED" : '\033[91m',
    "ENDC" : '\033[0m'
    }

    return "{}{}{}".format(
        termcolors[desired_color],
        s,
        termcolors["ENDC"])

def print_state(program_node):
    """
    Given the program node, prints out the main vars in VAR --> VALUE format.
    """

    for var, value in program_node.main_vars.items():
        print("{} --> {}".format(var, value))

def handle_errors(e):
    """
    Takes an exception, prints an appropriate message and exits the program.
    """

    # Prints a 'window' around the code we're interested in.
    line_num, char_num = e.token.line_num, e.token.char_num
    prev_line_num, next_line_num = line_num - 1, line_num + 1
    prev_line, line, next_line = (
        shared.code[line_num - 1] if prev_line_num >= 0 else "",
        shared.code[line_num],
        shared.code[line_num + 1] if next_line_num < len(shared.code) else ""
        )

    # The header's is as long as it needs to be, plus some wiggle room.
    tab = " " * 4
    header = "-" * (
        max(len(prev_line), len(line), len(next_line)) + len(tab) + 4)

    print("Error occurred in file '{}' on line {} during {}.".format(
        filename, line_num, e.stage))

    # Line number and line are separated by a tab.
    print()
    print(header)
    print(prev_line_num, tab, prev_line, sep="")
    print(line_num, tab, line, sep="")

    # Pointer's position = how far along the line the target is + preamble.
    offset = len(str(line_num)) + len(tab)
    print(" " * (char_num + offset) + colorize("^", "RED"))

    print(next_line_num, tab, next_line, sep="")
    print(header)
    print()

    print(e.message)
    exit(1)

if __name__ == "__main__":
    try:
        filename = sys.argv[1]
        scanner = scanner.Scanner(filename)
        parser = parser.ArrowParser(scanner.tokens())
        program = parser.program()
    except shared.ArrowException as e:
        handle_errors(e)

    print("Starting out... ")
    print()
    print_state(program)

    # direction == 1 means forwards, direction == -1 means backwards
    direction = 1

    while True:
        input("Going {}... ".format(
            "forwards" if direction > 0 else "backwards"))

        # Update the main vars according to the result of the program.
        result = evaluator.program_eval(program)
        program.main_vars.update(result.refs)

        print_state(program)

        # Invert the main function.
        program.main.block = inverter.unblock(program.main.block)

        # Now we're going the other way.
        direction *= -1