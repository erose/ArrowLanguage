from enum import Enum

# The program node.
program = None

# A list of lines of the Arrow code currently being processed.
code = None

# The possible states the interpreter can be in.
class Stages(Enum):
  scanning = 1
  parsing = 2
  evaluation = 3

class ArrowException(Exception):
    """
    A base class for exceptions thrown by the interpreter.
    Takes
      -- the stage in which the error occurred.
      -- the error message.
      -- the token it occurred on (containing line number information).
    """
    def __init__(self, stage, message, token):
        self.stage = stage
        self.message = message
        self.token = token