"""A basic functionality test"""
from __future__ import unicode_literals

from pegasus import Parser, rule
from pegasus.rules import Plus, Opt, Or, Discard, Star, ChrRange as CC, set_debug, EOF

set_debug()


class SimpleParser(Parser):
    @rule(Discard('hello', Opt(','), Plus(' ')), Plus(Or(CC('a', 'z'), CC('A', 'Z'))), Discard(Star('!')), EOF)
    def hello_world(self, name):
        print 'HELLO WORLD CALLED WITH:', name
        return 'flubber'


def test_simple_parser():
    parser = SimpleParser()
    assert 'Paul' == parser.parse(SimpleParser.hello_world, 'hello, Paul!')
    assert 'Sheila' == parser.parse(SimpleParser.hello_world, 'hello,     Sheila')
    assert 'Josh' == parser.parse(SimpleParser.hello_world, 'hello,     Josh!!!')

if __name__ == '__main__':
    parser = SimpleParser()
    result = parser.parse(SimpleParser.hello_world, 'hello, Paul!')
    print 'GRAND RESULT: ', result
