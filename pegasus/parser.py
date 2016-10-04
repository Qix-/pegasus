"""Houses the Pegasus parser class"""
from __future__ import unicode_literals

import inspect
from itertools import chain as iterchain
from pegasus.rules import Seq


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

    def parse(self, iterable, rule=None):
        """Parses and visits an iterable"""
        if rule is None:
            if not hasattr(self, '__default'):
                raise NoDefaultRuleException('starting rule was not provided and no default rule was found')
            rule = self.__default
        else:
            if not hasattr(rule, '_rule') or not inspect.ismethod(rule):
                raise NotARuleException('the specified `rule\' value is not actually a rule: %r' % (rule,))

            rule = getattr(rule, '_rule')

        for c in iterchain.from_iterable(iterable):
            rule(self, c)

        return rule(self, None)  # signal EOF
