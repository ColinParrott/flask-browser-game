from enum import Enum


def to_enum(s: str):
    if s == str(Choice.FIRST):
        return Choice.FIRST
    elif s == str(Choice.SECOND):
        return Choice.SECOND
    elif s == str(Choice.THIRD):
        return Choice.THIRD
    else:
        return None


class Choice(Enum):

    def __str__(self):
        return str(self.value)

    FIRST = 'first'
    SECOND = 'second'
    THIRD = 'third'
