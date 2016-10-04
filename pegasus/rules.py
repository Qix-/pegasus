"""Pegasus parser rules, in all their glory

Here are how rules work:

    All rules are generators. If a rule by itself isn't a generator function,
    it's intended to be called with some configuration parameters, and thus
    returns a generator function (e.g. Seq and Or). Otherwise, it is to be called
    directly in order to get a parser generator (e.g. EOF).

    The generator returned should yield a two-element tuple, the first element being one of two things:
        - None in the event the rule is still consuming but hasn't succeeded
        - (result,) in the event the rule has succeeded and has garnered a result.
          In the event the rule succeeds but no result is to be returned (e.g. the rule
          is marked as discarded), then an empty tuple should be returned.

    In the event the rule fails, a ParseError should be raised.

    In the event the rule consumed a character it shouldn't have, the second tuple element should be True.

    Lastly, in the event the rule succeeds without question (e.g. a successful string literal), simply a single
    element tuple with the result or a tuple of `(<result>, False)` should be returned.

    In the event the rule expires (a StopIteration is thrown), the exception should be propagated
    upward in order to show the full stack.

    When creating the rule generators, a `char` value is passed. This value is a callable that takes
    no arguments and returns the current character. It is NOT a generator nor does it modify any value,
    so it can be safely called multiple times to return the same character. However, once the function
    yields, a subsequent call to char() upon reentry will NOT return the same character!

    It is expected that upon a rule generator being initialized that it should read the current character.
    This is why Seq() iterates through rules via a generator rather than a list.
"""
import inspect
from pegasus.util import flatten


DEBUG = False
__dbgdepth = 0


def set_debug(debug=True):
    global DEBUG
    DEBUG = debug


def debuggable(name=None):
    def _wrap(fn):
        if not DEBUG:
            return fn

        _name = name if name else fn.__name__

        def _inner(char, *args, **kwargs):
            global __dbgdepth

            gen = fn(char, *args, **kwargs)

            depth = ' ' * __dbgdepth
            while True:
                try:
                    print 'pegasus: {}\x1b[2;38;5;241menter {} -> {}\x1b[m'.format(depth, char(), _name)
                    __dbgdepth += 1
                    result, reconsume = next(gen)
                    if result is not None:
                        print 'pegasus: {}\x1b[1;38;5;126mresult {} -> {} ==> {} (reconsume={})\x1b[m'.format(depth, char(), _name, result, reconsume)
                    yield result, reconsume
                except Exception as e:
                    print 'pegasus: {}\x1b[38;5;88mfail {} -> {}\t{}\x1b[m'.format(depth, char(), _name, str(e))
                    raise
                finally:
                    print 'pegasus: {}\x1b[2;38;5;241mexit {} -> {}\x1b[m'.format(depth, char(), _name)
                    __dbgdepth -= 1

        return _inner
    return _wrap


class BadRuleException(Exception):
    """Thrown if a rule was invalid, due to a bad type usually"""
    pass


class ParseError(Exception):
    """Thrown in the event there was a problem parsing the input string"""
    def __init__(self, got=None, expected=None):
        self.got = got
        self.expected = expected if expected else []

        rgot = repr(got)
        if got is not None and expected is None or len(expected) == 0:
            message = 'unexpected: {}'.format(rgot)
        elif got is None and expected is not None and len(expected):
            if len(expected) == 1:
                message = 'expected: {}'.format(expected[0])
            else:
                message = 'expected one of the following:'
                for e in expected:
                    message += '\n- {}'.format(e)
        elif got is None and expected is None:
            message = 'unknown parse error'
        else:
            if len(expected) == 1:
                message = 'got: {}, expected: {}'.format(rgot, expected[0])
            else:
                message = 'got: {}, expected one of:'.format(rgot)
                for e in expected:
                    message += '\n- {}'.format(e)

        super(ParseError, self).__init__(message)

    @classmethod
    def combine(cls, errors):
        expected = []
        for error in errors:
            if not len(error.expected):
                continue
            for exp in error.expected:
                expected.append('{} but got \'{}\' instead'.format(exp, error.got))

        return ParseError(expected=expected)


class Lazy(object):
    _LOOKUPS = {}

    def __init__(self, name):
        self.name = name
        stack = inspect.stack()[1]
        self.module = stack[3]
        self.file = stack[1]

    def resolve(self):
        if (self.file, self.module, self.name) not in Lazy._LOOKUPS:
            raise BadRuleException('could not resolve lazily loaded rule: {}.{}'.format(self.module, self.name))

        return Lazy._LOOKUPS[(self.file, self.module, self.name)]


def _build_rule(rule):
    if isinstance(rule, Lazy):
        rule = rule.resolve()

    if callable(rule):
        if hasattr(rule, '_rule'):
            # it's a class rule that has a transformation step
            return ParserRule(rule, getattr(rule, '_rule'))
        return rule

    if type(rule) in [str, unicode]:
        return Literal(rule)

    if type(rule) == list:
        if len(rule) == 0:
            raise BadRuleException('Or() rules must have at least one condition')
        return _build_rule(rule[0]) if len(rule) == 1 else Or(*rule)

    if type(rule) == tuple:
        if len(rule) == 0:
            raise BadRuleException('Seq() rules must have at least one condition')
        return _build_rule(rule[0]) if len(rule) == 1 else Seq(*rule)

    raise BadRuleException('rule has invalid type: {}'.format(repr(rule)))


@debuggable('EOF')
def EOF(char, parser):
    """Fails if the given character is not None"""
    if char() is not None:
        raise ParseError(got=char(), expected=['<EOF>'])

    yield (), False


def ParserRule(class_rule, parse_rule):
    """Calls a transformation step class_rule if the parse_rule succeeds"""
    rule = _build_rule(parse_rule)

    @debuggable('ParserRule')
    def _iter(char, parser):
        grule = rule(char, parser)

        while True:
            result, reconsume = next(grule)
            if result is not None:
                result = class_rule(parser, *result)
                yield ((result,) if result is not None else ()), reconsume
                break

            yield None, reconsume

    return _iter


def Literal(utf):
    """Matches an exact string literal"""
    if type(utf) == str:
        utf = unicode(utf)

    length = len(utf)

    @debuggable('Literal')
    def _iter(char, parser):
        for i in xrange(length):
            c = utf[i]
            if char() and c == char():
                if i + 1 == length:
                    break
                yield None, None
            else:
                raise ParseError(got=char() or '<EOF>', expected=['\'{}\' (in literal \'{}\')'.format(c, utf)])

        yield (utf,), False

    return _iter


def Or(*rules):
    """Matches the first succeeding rule"""

    @debuggable('Or')
    def _iter(char, parser):
        remaining = [_build_rule(rule)(char, parser) for rule in rules]
        errors = []

        while len(remaining):
            for rule in list(remaining):
                reconsume = True
                while reconsume:
                    try:
                        result, reconsume = next(rule)
                        if result is not None:
                            yield result, reconsume
                            raise StopIteration()
                    except ParseError as e:
                        errors.append(e)
                        remaining.remove(rule)
                        break

            if len(remaining):
                yield None, False

        raise ParseError.combine(errors)

    return _iter


def Seq(*rules):
    total = len(rules)

    @debuggable('Seq')
    def _iter(char, parser):
        results = ()

        counter = 0
        for rule in (_build_rule(rule)(char, parser) for rule in rules):
            counter += 1
            while True:
                result, reconsume = next(rule)
                if result is None:
                    yield result, reconsume
                else:
                    break

            results += result

            if counter < total:
                yield None, reconsume

        yield results, reconsume

    return _iter


class __ChrRange(object):
    def __call__(self, begin, end, inverse=False):
        inverse = inverse is True
        rng = xrange(ord(unicode(begin)[0]), ord(unicode(end)[0]) + 1)

        @debuggable('ChrRange')
        def _iter(char, parser):
            if char() is not None and (ord(char()) in rng) is not inverse:
                yield (char(),), False
            raise ParseError(got=char() or '<EOF>', expected=['character in class [{}-{}]'.format(repr(unicode(begin)[0]), repr(unicode(end)[0]))])

        return _iter

    def __getitem__(self, slicee):
        if type(slicee) != slice:
            raise BadRuleException('character range subscripts must be slices of characters')

        return ChrRange(slicee.start, slicee.stop, slicee.step)

ChrRange = __ChrRange()


def Opt(*rules):
    rule = _build_rule(rules)

    @debuggable('Opt')
    def _iter(char, parser):
        grule = rule(char, parser)

        try:
            while True:
                result, reconsume = next(grule)
                if result is not None:
                    yield result, reconsume
                    break

                yield None, reconsume
        except ParseError:
            yield (), True

    return _iter


def Plus(*rules):
    rule = _build_rule(rules)

    @debuggable('Plus')
    def _iter(char, parser):
        results = []

        try:
            while True:
                grule = rule(char, parser)

                while True:
                    result, reconsume = next(grule)
                    if result is not None:
                        results.append(result)
                        break

                    yield None, reconsume

                yield None, reconsume
        except ParseError as e:
            if len(results) == 0:
                raise e  # don't pass the stack; make sure we see that it's from here.

            yield tuple(results), True

    return _iter


def Star(*rules):
    return Opt(Plus(*rules))


def Discard(*rules):
    rule = _build_rule(rules)

    @debuggable('Discard')
    def _iter(char, parser):
        grule = rule(char, parser)

        while True:
            result, reconsume = next(grule)
            if result is not None:
                yield (), reconsume
                break
            yield None, reconsume

    return _iter


def Str(*rules):
    rule = _build_rule(rules)

    @debuggable('Str')
    def _iter(char, parser):
        grule = rule(char, parser)
        while True:
            result, reconsume = next(grule)
            if result is not None:
                result = (''.join(flatten(result)),)
                yield result, reconsume
                break
            yield None, reconsume

    return _iter


@debuggable('Dot')
def Dot(char, parser):
    if char() is None:
        raise ParseError(got='<EOF>', expected=['any non-EOF character'])
    yield (char(),), False


def All(rule, *conditionals):
    if len(conditionals) == 0:
        raise BadRuleException('must supply at least one conditional')

    def _iter(char, parser):
        gconds = [_build_rule(cond)(char, parser) for cond in conditionals]
        grule = _build_rule(rule)(char, parser)

        while True:
            for gcond in gconds:
                reconsume = True
                while reconsume:
                    result, reconsume = next(gcond)
                    if result is not None:
                        raise ParseError(got='conditional result: {}'.format(result), expected=['never returning conditional rule'])

            reconsume = True
            while reconsume:
                result, reconsume = next(grule)
                if result is not None:
                    yield result, reconsume
                    raise StopIteration()

            yield None, False

    return _iter


def In(chars, inverse=False):
    if not chars:
        raise BadRuleException('must supply a string/iterable with at least one character')

    def _iter(char, parser):
        if char() is not None and (char() in chars) is not inverse:
            yield (char(),), False
        raise ParseError(got=char(), expected=['{}one of: {}'.format('not ' if inverse else '', ''.join(chars))])

    return _iter
