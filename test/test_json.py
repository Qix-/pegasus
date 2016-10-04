"""A test JSON parser"""

import json
from pegasus import Parser, rule
from pegasus.rules import *
from pegasus.rules import ChrRange as C
from pegasus.rules import Discard as _
from pegasus.util import flatten


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
    @rule(Star(In(' \t\r\n\f')))
    def ws(self, *_):
        pass

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

    @rule([string, number, bool_literal, null_literal, Lazy('array'), Lazy('object')])
    def value(self, value):
        return value

    @rule(_('[', ws), Opt(value, Star(_(ws, ',', ws), value)), _(ws, ']'))
    def array(self, first=None, *rest):
        if first is None and (rest is None or not len(rest)):
            return []
        return list((first,) + tuple(flatten(rest, depth=1)))

    @rule(string, _(ws, ':', ws), value)
    def object_pair(self, key, val):
        return (key, val)

    @rule(_('{', ws), Opt(object_pair, Star(_(ws, ',', ws), object_pair)), _(ws, '}'))
    def object(self, first=None, *rest):
        if first is None and (rest is None or not len(rest)):
            return {}

        # ugh, don't we just love Python? I mean seriously... <3
        return dict((first,) + tuple(flatten(rest, depth=1)))

    @rule(ws, value, ws, EOF)
    def document(self, document):
        return document


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


def test_json_array():
    parser = JsonParser()
    assert parser.parse(JsonParser.array, '[1]', match=False) == [1]
    assert parser.parse(JsonParser.array, '[1, 2, 3]', match=False) == [1, 2, 3]
    assert parser.parse(JsonParser.array, '[1,2, \n3]', match=False) == [1, 2, 3]
    assert parser.parse(JsonParser.array, '[1, 2, \n3, true, false]', match=False) == [1, 2, 3, True, False]
    assert parser.parse(JsonParser.array, '[]', match=False) == []


def test_json_nested_array():
    parser = JsonParser()
    assert parser.parse(JsonParser.array, '[[]]', match=False) == [[]]
    assert parser.parse(JsonParser.array, '[[[]]]', match=False) == [[[]]]
    assert parser.parse(JsonParser.array, '[[[],[]]]', match=False) == [[[], []]]
    assert parser.parse(JsonParser.array, '[[1]]', match=False) == [[1]]
    assert parser.parse(JsonParser.array, '[[1],[2, 3]]', match=False) == [[1], [2, 3]]


def test_json_object():
    parser = JsonParser()
    assert parser.parse(JsonParser.object, '{}', match=False) == {}
    assert parser.parse(JsonParser.object, '{"foo": true}', match=False) == {'foo': True}
    assert parser.parse(JsonParser.object, '{"foo": true, "hello": 12345}', match=False) == {'foo': True, 'hello': 12345.0}
    assert parser.parse(JsonParser.object, '{"foo": true, "hello": 12345, "another": [1, 2, 3]}', match=False) == {'foo': True, 'hello': 12345.0, 'another': [1, 2, 3]}


def test_json_value():
    parser = JsonParser()
    assert parser.parse(JsonParser.value, 'null', match=False) == (None,)
    assert parser.parse(JsonParser.value, '"hello, there!"', match=False) == 'hello, there!'
    assert parser.parse(JsonParser.value, '1234.5678', match=False) == 1234.5678
    assert parser.parse(JsonParser.value, '.5678', match=False) == 0.5678
    assert parser.parse(JsonParser.value, '1234.', match=False) == 1234.0
    assert parser.parse(JsonParser.value, '1234', match=False) == 1234.0
    assert parser.parse(JsonParser.value, 'true', match=False) is True
    assert parser.parse(JsonParser.value, 'false', match=False) is False
    assert parser.parse(JsonParser.value, '[12345]', match=False) == [12345.0]
    assert parser.parse(JsonParser.value, '[[12345], true]', match=False) == [[12345.0], True]


def test_json_documents():
    parser = JsonParser()

    def validate(doc):
        return json.loads(doc) == parser.parse(JsonParser.document, doc)

    validate("""
        {
            "glossary": {
                "title": "example glossary",
                "GlossDiv": {
                    "title": "S",
                    "GlossList": {
                        "GlossEntry": {
                            "ID": "SGML",
                            "SortAs": "SGML",
                            "GlossTerm": "Standard Generalized Markup Language",
                            "Acronym": "SGML",
                            "Abbrev": "ISO 8879:1986",
                            "GlossDef": {
                                "para": "A meta-markup language, used to create markup languages such as DocBook.",
                                "GlossSeeAlso": ["GML", "XML"]
                            },
                            "GlossSee": "markup"
                        }
                    }
                }
            }
        }
    """)

    validate("""
        {"menu": {
          "id": "file",
          "value": "File",
          "popup": {
            "menuitem": [
              {"value": "New", "onclick": "CreateNewDoc()"},
              {"value": "Open", "onclick": "OpenDoc()"},
              {"value": "Close", "onclick": "CloseDoc()"}
            ]
          }
        }}
    """)

    validate("""
            {"widget": {
            "debug": "on",
            "window": {
                "title": "Sample Konfabulator Widget",
                "name": "main_window",
                "width": 500,
       	"height": 500
            },
            "image": {
                "src": "Images/Sun.png",
                "name": "sun1",
                "hOffset": 250,
                "vOffset": 250,
                "alignment": "center"
            },
            "text": {
                "data": "Click Here",
                "size": 36,
                "style": "bold",
                "name": "text1",
                "hOffset": 250,
                "vOffset": 100,
                "alignment": "center",
                "onMouseUp": "sun1.opacity = (sun1.opacity / 100) * 90;"
            }
        }}
    """)

    validate("""
{"web-app": {
  "servlet": [
    {
      "servlet-name": "cofaxCDS",
      "servlet-class": "org.cofax.cds.CDSServlet",
      "init-param": {
        "configGlossary:installationAt": "Philadelphia, PA",
        "configGlossary:adminEmail": "ksm@pobox.com",
        "configGlossary:poweredBy": "Cofax",
        "configGlossary:poweredByIcon": "/images/cofax.gif",
        "configGlossary:staticPath": "/content/static",
        "templateProcessorClass": "org.cofax.WysiwygTemplate",
        "templateLoaderClass": "org.cofax.FilesTemplateLoader",
        "templatePath": "templates",
        "templateOverridePath": "",
        "defaultListTemplate": "listTemplate.htm",
        "defaultFileTemplate": "articleTemplate.htm",
        "useJSP": false,
        "jspListTemplate": "listTemplate.jsp",
        "jspFileTemplate": "articleTemplate.jsp",
        "cachePackageTagsTrack": 200,
        "cachePackageTagsStore": 200,
        "cachePackageTagsRefresh": 60,
        "cacheTemplatesTrack": 100,
        "cacheTemplatesStore": 50,
        "cacheTemplatesRefresh": 15,
        "cachePagesTrack": 200,
        "cachePagesStore": 100,
        "cachePagesRefresh": 10,
        "cachePagesDirtyRead": 10,
        "searchEngineListTemplate": "forSearchEnginesList.htm",
        "searchEngineFileTemplate": "forSearchEngines.htm",
        "searchEngineRobotsDb": "WEB-INF/robots.db",
        "useDataStore": true,
        "dataStoreClass": "org.cofax.SqlDataStore",
        "redirectionClass": "org.cofax.SqlRedirection",
        "dataStoreName": "cofax",
        "dataStoreDriver": "com.microsoft.jdbc.sqlserver.SQLServerDriver",
        "dataStoreUrl": "jdbc:microsoft:sqlserver://LOCALHOST:1433;DatabaseName=goon",
        "dataStoreUser": "sa",
        "dataStorePassword": "dataStoreTestQuery",
        "dataStoreTestQuery": "SET NOCOUNT ON;select test='test';",
        "dataStoreLogFile": "/usr/local/tomcat/logs/datastore.log",
        "dataStoreInitConns": 10,
        "dataStoreMaxConns": 100,
        "dataStoreConnUsageLimit": 100,
        "dataStoreLogLevel": "debug",
        "maxUrlLength": 500}},
    {
      "servlet-name": "cofaxEmail",
      "servlet-class": "org.cofax.cds.EmailServlet",
      "init-param": {
      "mailHost": "mail1",
      "mailHostOverride": "mail2"}},
    {
      "servlet-name": "cofaxAdmin",
      "servlet-class": "org.cofax.cds.AdminServlet"},

    {
      "servlet-name": "fileServlet",
      "servlet-class": "org.cofax.cds.FileServlet"},
    {
      "servlet-name": "cofaxTools",
      "servlet-class": "org.cofax.cms.CofaxToolsServlet",
      "init-param": {
        "templatePath": "toolstemplates/",
        "log": 1,
        "logLocation": "/usr/local/tomcat/logs/CofaxTools.log",
        "logMaxSize": "",
        "dataLog": 1,
        "dataLogLocation": "/usr/local/tomcat/logs/dataLog.log",
        "dataLogMaxSize": "",
        "removePageCache": "/content/admin/remove?cache=pages&id=",
        "removeTemplateCache": "/content/admin/remove?cache=templates&id=",
        "fileTransferFolder": "/usr/local/tomcat/webapps/content/fileTransferFolder",
        "lookInContext": 1,
        "adminGroupID": 4,
        "betaServer": true}}],
  "servlet-mapping": {
    "cofaxCDS": "/",
    "cofaxEmail": "/cofaxutil/aemail/*",
    "cofaxAdmin": "/admin/*",
    "fileServlet": "/static/*",
    "cofaxTools": "/tools/*"},

  "taglib": {
    "taglib-uri": "cofax.tld",
    "taglib-location": "/WEB-INF/tlds/cofax.tld"}}}
    """)

    validate("""
{"menu": {
    "header": "SVG Viewer",
    "items": [
        {"id": "Open"},
        {"id": "OpenNew", "label": "Open New"},
        null,
        {"id": "ZoomIn", "label": "Zoom In"},
        {"id": "ZoomOut", "label": "Zoom Out"},
        {"id": "OriginalView", "label": "Original View"},
        null,
        {"id": "Quality"},
        {"id": "Pause"},
        {"id": "Mute"},
        null,
        {"id": "Find", "label": "Find..."},
        {"id": "FindAgain", "label": "Find Again"},
        {"id": "Copy"},
        {"id": "CopyAgain", "label": "Copy Again"},
        {"id": "CopySVG", "label": "Copy SVG"},
        {"id": "ViewSVG", "label": "View SVG"},
        {"id": "ViewSource", "label": "View Source"},
        {"id": "SaveAs", "label": "Save As"},
        null,
        {"id": "Help"},
        {"id": "About", "label": "About Adobe CVG Viewer..."}
    ]
}}
    """)
