"""A test JSON parser"""

from pegasus import Parser, rule
from pegasus.rules import *
from pegasus.rules import ChrRange as C
from pegasus.rules import Discard as _


ESCAPES = {
    'r': '\r',
    'n': '\n',
    'v': '\v',
    't': '\t',
    'b': '\b',
    'a': '\a',
    'f': '\f',
    '0': '\0',
    '"': '"',
    '\\': '\\'
}


class JsonParser(Parser):
    @rule('null')
    def null_literal(self, *_):
        return (None,)

    @rule('true')
    def true_literal(self, *_):
        return True

    @rule('false')
    def false_literal(self, *_):
        return False

    @rule([true_literal, false_literal])
    def bool_literal(self, boolean):
        return boolean

    @rule(Plus(C['0':'9']))
    def digits(self, *digits):
        return digits

    @rule(Str(Opt(['+', '-']), [(digits, Opt('.', Opt(digits))), (Opt(digits), '.', digits)]))
    def number(self, number):
        return float(number)

    @rule([C['0':'9'], C['A':'F'], C['a':'f']])
    def hex_char(self, char):
        return char

    @rule(Str(hex_char, hex_char))
    def hex8(self, chars):
        return int(chars, 16)

    @rule(Str(hex_char, hex_char, hex_char, hex_char))
    def hex16(self, chars):
        return int(chars, 16)

    @rule(_('\\'), [In(ESCAPES.keys()), ('x', hex8), ('u', hex16)])
    def char_escape(self, seq, num=0):
        if seq in 'xu':
            return chr(num)

        return ESCAPES[seq]

    @rule(_('"'), Str(Star([char_escape, In('\\"', True)])), _('"'))
    def string(self, contents):
        return contents

    @rule([string, number, bool_literal, null_literal])
    def primitive(self, value):
        return value


def test_json_boolean():
    parser = JsonParser()
    assert parser.parse(JsonParser.true_literal, 'true', match=False) is True
    assert parser.parse(JsonParser.false_literal, 'false', match=False) is False
    assert parser.parse(JsonParser.bool_literal, 'true', match=False) is True
    assert parser.parse(JsonParser.bool_literal, 'false', match=False) is False


def test_json_number():
    parser = JsonParser()
    assert parser.parse(JsonParser.number, '1234', match=False) == 1234.0
    assert parser.parse(JsonParser.number, '1234.', match=False) == 1234.0
    assert parser.parse(JsonParser.number, '1234.5678', match=False) == 1234.5678
    assert parser.parse(JsonParser.number, '.1234', match=False) == 0.1234
    assert parser.parse(JsonParser.number, '+1234', match=False) == 1234.0
    assert parser.parse(JsonParser.number, '+1234.', match=False) == 1234.0
    assert parser.parse(JsonParser.number, '+.1234', match=False) == 0.1234
    assert parser.parse(JsonParser.number, '+1234.5678', match=False) == 1234.5678
    assert parser.parse(JsonParser.number, '-1234', match=False) == -1234.0
    assert parser.parse(JsonParser.number, '-1234.', match=False) == -1234.0
    assert parser.parse(JsonParser.number, '-.1234', match=False) == -0.1234
    assert parser.parse(JsonParser.number, '-1234.5678', match=False) == -1234.5678


def test_json_string():
    parser = JsonParser()
    assert parser.parse(JsonParser.string, '"hello"', match=False) == 'hello'
    assert parser.parse(JsonParser.string, '"hello there"', match=False) == 'hello there'
    assert parser.parse(JsonParser.string, '"\n"', match=False) == '\n'
    assert parser.parse(JsonParser.string, '"\\\\"', match=False) == '\\'
    assert parser.parse(JsonParser.string, '"\\\\\\""', match=False) == '\\"'
    assert parser.parse(JsonParser.string, '"\\v\\t\\n"', match=False) == '\v\t\n'


def test_json_null():
    parser = JsonParser()
    assert parser.parse(JsonParser.null_literal, 'null', match=False) == (None,)


def test_json_primitive():
    parser = JsonParser()
    assert parser.parse(JsonParser.primitive, 'null', match=False) == (None,)
    assert parser.parse(JsonParser.primitive, '"hello, there!"', match=False) == 'hello, there!'
    assert parser.parse(JsonParser.primitive, '1234.5678', match=False) == 1234.5678
    assert parser.parse(JsonParser.primitive, '.5678', match=False) == 0.5678
    assert parser.parse(JsonParser.primitive, '1234.', match=False) == 1234.0
    assert parser.parse(JsonParser.primitive, '1234', match=False) == 1234.0
    assert parser.parse(JsonParser.primitive, 'true', match=False) is True
    assert parser.parse(JsonParser.primitive, 'false', match=False) is False
