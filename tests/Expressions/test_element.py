'''
List indexes in paths, R[0].type. The parser used to drop them, so R[0].type read
as R.type and where R[1] == 'a' as where R == 'a', which never errored.
'''
import polars as pl
import pytest

from Hql.Compiler import HqlCompiler, KustoCompiler, LuceneCompiler, QueryDSLCompiler
from Hql.Config import Config
from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Expressions.References import Element, EscapedNamedReference, Path
from Hql.Parser import Parser


def pipes(query):
    parser = Parser(query, filename='test')
    parser.assemble()
    return parser.assembly.statements[-1].root.pipes


def deparse(query):
    parser = Parser(query, filename='test')
    parser.assemble()
    return parser.assembly.deparse()


def where_lh(query):
    return pipes(f'T | where {query}')[0].expr.lh


@pytest.mark.parametrize('query', [
    "T\n| where R[1] == 'a'",
    "T\n| where R[-1] == 'a'",
    "T\n| extend t=tostring(R[0].type)",
    "T\n| where R[0][2].a.b == 'a'",
    "T\n| where R.a[0] == 'a'",
    "T\n| where R[0]['a b'] == 'a'",
])
def test_indexes_round_trip(query):
    assert deparse(query) == query


def test_legacy_index_form():
    assert deparse("T | where R.[2] == 'a'") == "T\n| where R[2] == 'a'"


def test_index_is_kept():
    lh = where_lh("R[0].type == 'a'")
    assert isinstance(lh, Element)
    assert lh.index() == 'type'
    assert isinstance(lh.base, Element) and lh.base.index() == 0


def test_field_name_in_brackets_is_a_field():
    # R['a'] names the same field as R.a, so it stays a Path any backend can take
    lh = where_lh("R['a b'].c == 'x'")
    assert isinstance(lh, Path)
    assert lh.list() == ['R', 'a b', 'c']
    assert isinstance(lh.path[1], EscapedNamedReference)


def kusto(query):
    compiler = KustoCompiler()
    compiler.add_index('T')
    for op in pipes(f'T | {query}'):
        desc, _ = HqlCompiler(Config()).compile(op)
        _, rej = compiler.add_op(desc)
        assert rej is None
    return compiler.compile(None, prep=False)[0].removeprefix('T\n| ')


@pytest.mark.parametrize('query,kql', [
    ("where R[1] == 'a'", 'where R[1] == "a"'),
    ("where R[-1] == 'a'", 'where R[-1] == "a"'),
    ("where S[0][2].x.y startswith 'q'", 'where S[0][2].x.y startswith "q"'),
    ("where R[0]['a b'] == 'a'", "where R[0]['a b'] == \"a\""),
    ("extend t = tostring(R[0].type)", 'extend t = tostring(R[0].type)'),
])
def test_kusto_pushes_indexes(query, kql):
    assert kusto(query) == kql


@pytest.mark.parametrize('compiler', [LuceneCompiler, QueryDSLCompiler])
def test_backends_without_indexing_leave_it_to_hql(compiler):
    desc, _ = HqlCompiler(Config()).compile(pipes("T | where R[0] == 'a'")[0])
    assert not desc.compatible(compiler().attrs)


DF = pl.DataFrame({
    'id': [1, 2, 3],
    'R': [['a', 'b'], ['b', 'a', 'z'], []],
    'T': [[{'type': 'User', 'n': 1}], [{'type': 'Service Principal', 'n': 2}, {'type': 'Role', 'n': 3}], []],
})


def local(query):
    ctx = Context(Data([Table(df=DF, name='t')]))
    for op in pipes(f'x | {query}'):
        desc, _ = HqlCompiler(Config()).compile(op)
        ctx = desc.get_op().eval(ctx)
    return ctx.data['t'].to_dicts() if 't' in ctx.data else []


@pytest.mark.parametrize('query,ids', [
    ("where R[1] == 'a'", [2]),
    ("where R[0] == 'a'", [1]),
    ("where R[-1] == 'z'", [2]),
    ("where T[0].type == 'Service Principal'", [2]),
    ("where T[1]['type'] startswith 'Ro'", [2]),
    # Out of range is null, like Kusto
    ("where R[5] == 'a'", []),
])
def test_local_where(query, ids):
    assert [x['id'] for x in local(query)] == ids


def test_local_extend():
    rows = local('extend t = tostring(T[0].type), n = T[0].n | project id, t, n')
    assert rows == [
        {'id': 1, 't': 'User', 'n': 1},
        {'id': 2, 't': 'Service Principal', 'n': 2},
        {'id': 3, 't': None, 'n': None},
    ]


def test_missing_field_matches_nothing():
    assert local("where Missing[0] == 'a'") == []


def test_unsupported_index_is_an_error():
    lh = where_lh("R[id] == 'a'")
    with pytest.raises(Exception, match='Unsupported index'):
        lh.index()
