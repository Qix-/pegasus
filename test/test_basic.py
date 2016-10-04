"""A basic functionality test"""
from __future__ import unicode_literals

from pegasus import Parser, rule


class SimpleParser(Parser):
    @rule('hello')
    def hello_world(self):
        return True


def test_simple_parser():
    parser = SimpleParser()
    result = parser.parse('hello', rule=SimpleParser.hello_world)
    assert result is True
