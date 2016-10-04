"""Houses the Pegasus parser class

Unicode characters not being read correctly?
Check out http://stackoverflow.com/a/844443/510036
"""
from __future__ import unicode_literals

import inspect
from itertools import chain as iterchain
from pegasus.rules import Seq, ParseError, BadRuleException


class EmptyRuleException(Exception):
    pass


class NoDefaultRuleException(Exception):
    pass


class NotARuleException(Exception):
    pass


def rule(*rules):
    """Marks a method as a rule"""
    def wrapper(fn):
        _rules = rules
        if len(_rules) == 0:
            raise EmptyRuleException('cannot supply an empty rule')

        _rules = Seq(*_rules)

        setattr(fn, '_rule', _rules)
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

        prule = getattr(rule, '_rule')

        itr = iterchain.from_iterable(iterable)
        c = None
        grule = None

        for c in itr:
            reconsume = True
            while reconsume:
                if grule is None:
                    grule = prule(lambda: c)

                result, reconsume = next(grule)

                if result:
                    if match:
                        raise ParseError(got='result (rule returned a result without fully exhausting input)')
                    else:
                        return result

        if grule:
            c = None
            reconsume = True
            result = None
            while reconsume:
                result, reconsume = next(grule)
            return result

        return None
