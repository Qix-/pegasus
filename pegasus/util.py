"""A few utilities"""


def flatten(obj, depth=None, current_depth=0):
    if depth is not None and current_depth > depth:
        yield obj
    else:
        for o in obj:
            if type(o) in [tuple, list]:
                for o2 in flatten(o, depth, current_depth + 1):
                    yield o2
            else:
                yield o
