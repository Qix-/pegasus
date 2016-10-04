"""Pegasus parser rules, in all their glory"""


def pprint(*args):
    print args
    return True


def Seq(*rules):
    return lambda _, char: pprint('CHR: {}'.format(char))
