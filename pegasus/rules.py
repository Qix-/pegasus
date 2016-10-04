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

        got = repr(got)
        if got is not None and expected is None or len(expected) == 0:
            message = 'unexpected: {}'.format(got)
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
                message = 'got: {}, expected: {}'.format(got, expected[0])
            else:
                message = 'got: {}, expected one of:'.format(got)
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


def _build_rule(rule):
    if callable(rule):
        return rule

    if type(rule) in [str, unicode]:
        return Literal(rule)

    if type(rule) == list:
        return Or(*rule)

    if type(rule) == tuple:
        return Seq(*rule)

    raise BadRuleException('rule has invalid type: {}'.format(repr(rule)))


@debuggable('EOF')
def EOF(char):
    """Fails if the given character is not None"""
    if char() is not None:
        raise ParseError(got=char(), expected=['<EOF>'])

    yield (), False


def Literal(utf):
    """Matches an exact string literal"""
    if type(utf) == str:
        utf = unicode(utf)

    length = len(utf)

    @debuggable('Literal')
    def _iter(char):
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
    def _iter(char):
        remaining = [_build_rule(rule)(char) for rule in rules]
        errors = []

        while len(remaining):
            for rule in list(remaining):
                try:
                    result, reconsume = next(rule, False)
                    if result is not None:
                        yield result, reconsume
                        raise StopIteration()
                except ParseError as e:
                    errors.append(e)
                    remaining.remove(rule)

        raise ParseError.combine(errors)

    return _iter


def Seq(*rules):
    total = len(rules)

    @debuggable('Seq')
    def _iter(char):
        results = ()

        counter = 0
        for rule in (_build_rule(rule)(char) for rule in rules):
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


def ChrRange(begin, end):
    rng = xrange(ord(unicode(begin)[0]), ord(unicode(end)[0]) + 1)

    @debuggable('ChrRange')
    def _iter(char):
        if char() and ord(char()) in rng:
            yield (char(),), False
        raise ParseError(got=char() or '<EOF>', expected=['character in class [{}-{}]'.format(repr(unicode(begin)[0]), repr(unicode(end)[0]))])

    return _iter


def Opt(*rules):
    rule = Seq(*rules) if len(rules) > 1 else _build_rule(*rules)

    @debuggable('Opt')
    def _iter(char):
        grule = rule(char)

        try:
            while True:
                result, reconsume = next(grule)
                if result is not None:
                    yield result, reconsume
                    break

                yield None, reconsume
        except ParseError:
            yield (), False

    return _iter


def Plus(*rules):
    rule = Seq(*rules) if len(rules) > 1 else _build_rule(*rules)

    @debuggable('Plus')
    def _iter(char):
        results = []

        try:
            while True:
                grule = rule(char)

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
    rule = Seq(*rules) if len(rules) > 1 else _build_rule(*rules)

    @debuggable('Discard')
    def _iter(char):
        grule = rule(char)

        while True:
            result, reconsume = next(grule)
            if result is not None:
                yield (), reconsume
                break
            yield None, reconsume

    return _iter
