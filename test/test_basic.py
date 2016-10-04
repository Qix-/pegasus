"""A basic functionality test"""
from __future__ import unicode_literals

from pegasus import Parser, rule
from pegasus.rules import Plus, Opt, Discard, Star, ChrRange as C, EOF, Str


class SimpleParser(Parser):
    @rule(['hello', 'greetings', 'salutations', 'yo'])
    def greeting(self, *_):
        pass

    @rule(Str(Plus([C['a':'z'], C['A':'Z']])))
    def name(self, name):
        return name

    @rule(Discard(greeting, Opt(','), Plus(' ')), name, Discard(Star('!')), EOF)
    def hello_world(self, name):
        return name


def test_simple_parser():
    parser = SimpleParser()
    assert 'Paul' == parser.parse(SimpleParser.hello_world, 'hello, Paul!')
    assert 'Sheila' == parser.parse(SimpleParser.hello_world, 'hello,     Sheila')
    assert 'Josh' == parser.parse(SimpleParser.hello_world, 'hello,     Josh!!!')
    assert 'Paul' == parser.parse(SimpleParser.hello_world, 'greetings, Paul!')
    assert 'Sheila' == parser.parse(SimpleParser.hello_world, 'yo,   Sheila!')
    assert 'Josh' == parser.parse(SimpleParser.hello_world, 'salutations,     Josh')
