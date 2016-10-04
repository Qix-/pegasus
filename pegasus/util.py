"""A few utilities"""


def flatten(obj):
    for o in obj:
        if type(o) in [tuple, list]:
            for o2 in flatten(o):
                yield o2
        else:
            yield o
