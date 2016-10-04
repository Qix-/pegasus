"""Houses the Pegasus parser class

Unicode characters not being read correctly?
Check out http://stackoverflow.com/a/844443/510036
"""
from __future__ import unicode_literals

import inspect
from itertools import chain as iterchain
from pegasus.rules import _build_rule, ParseError, Lazy


class EmptyRuleException(Exception):
    pass


class NoDefaultRuleException(Exception):
    pass


class NotARuleException(Exception):
    pass


def rule(*rules):
    stack = inspect.stack()[1]
    caller_module = stack[3]
    caller_file = stack[1]

    """Marks a method as a rule"""
    def wrapper(fn):
        _rules = rules
        if len(_rules) == 0:
            raise EmptyRuleException('cannot supply an empty rule')

        Lazy._LOOKUPS[(caller_file, caller_module, fn.__name__)] = fn

        setattr(fn, '_rule', rules)
        return fn

    return wrapper


class Parser(object):
    """The Pegasus Parser base class

    Extend this class and write visitor methods annotated with the @rule decorator,
    create an instance of the parser and call .parse('some str') on it.
    """

    def parse(self, rule, iterable, match=True):
        """Parses and visits an iterable"""
        if not hasattr(rule, '_rule') or not inspect.ismethod(rule):
            raise NotARuleException('the specified `rule\' value is not actually a rule: %r' % (rule,))

        prule = _build_rule(rule)

        itr = iterchain.from_iterable(iterable)
        c = None
        grule = None

        for c in itr:
            reconsume = True
            while reconsume:
                if grule is None:
                    grule = prule(lambda: c, self)

                result, reconsume = next(grule)

                if result is not None:
                    if match:
                        raise ParseError(got='result (rule returned a result without fully exhausting input)')
                    else:
                        return result[0]

        if grule:
            c = None
            reconsume = True
            result = None
            while reconsume:
                result, reconsume = next(grule)
                if result is not None and not match:
                    return result[0]
            return result[0]

        return None
