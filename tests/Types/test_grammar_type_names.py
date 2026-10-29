import pytest

from Hql.Expressions.Literals import TypeExpression
from Hql.Types.Hql import HqlTypes as hqlt


# ---------------------------------------------------------------------------
# workspace-qgw.34: grammar type names
# ---------------------------------------------------------------------------

class TestGrammarTypeNames:
    @pytest.mark.parametrize(('name', 'expected'), [
        ('bool', hqlt.bool), ('boolean', hqlt.bool),
        ('date', hqlt.datetime), ('datetime', hqlt.datetime),
        ('decimal', hqlt.decimal), ('double', hqlt.double), ('real', hqlt.double),
        ('dynamic', hqlt.dynamic), ('float', hqlt.float),
        ('guid', hqlt.guid), ('uniqueid', hqlt.guid),
        ('int', hqlt.int), ('int8', hqlt.byte), ('int16', hqlt.short),
        ('int32', hqlt.int), ('int64', hqlt.long), ('long', hqlt.long),
        ('uint', hqlt.uint), ('uint8', hqlt.ubyte), ('uint16', hqlt.ushort),
        ('uint32', hqlt.uint), ('uint64', hqlt.ulong), ('ulong', hqlt.ulong),
        ('string', hqlt.string), ('time', hqlt.time), ('timespan', hqlt.duration),
        ('ip4', hqlt.ip4), ('ip6', hqlt.ip6),
    ])
    def test_name_resolves(self, name, expected):
        assert isinstance(hqlt.from_name(name), expected)
        assert isinstance(TypeExpression(name).hql_type, expected)

    def test_datatable_parses_with_aliases(self):
        from Hql.Parser import Parser

        Parser('datatable (a:real, b:int64, c:timespan, d:boolean) [1.0, 1, 1, true]').assemble()
