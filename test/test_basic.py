"""A basic functionality test"""
from __future__ import unicode_literals

from pegasus import Parser, rule
from pegasus.rules import Plus, Opt, Or, Discard, Star, ChrRange as CC, EOF, Str


class SimpleParser(Parser):
    @rule('hello', Opt(','))
    def greeting(self, _):
        pass

    @rule(Plus(Or(CC('a', 'z'), CC('A', 'Z'))))
    def name(self, _):
        return _

    @rule(Discard(greeting, Plus(' ')), Str(name), Discard(Star('!')), EOF)
    def hello_world(self, (name,)):
        return name


def test_simple_parser():
    parser = SimpleParser()
    assert 'Paul' == parser.parse(SimpleParser.hello_world, 'hello, Paul!')[0]
    assert 'Sheila' == parser.parse(SimpleParser.hello_world, 'hello,     Sheila')[0]
    assert 'Josh' == parser.parse(SimpleParser.hello_world, 'hello,     Josh!!!')[0]
