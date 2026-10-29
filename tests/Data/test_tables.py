import polars as pl
import pytest

from Hql.Context import Context
from Hql.Data import Data, Schema
from Hql.Data.Tables import Table
from Hql.Expressions.References import NamedExpression, NamedReference as N, Path
from Hql.Types.Hql import HqlTypes as hqlt


def P(*names):
    return Path([N(x) for x in names])


def raw(table):
    # The raw str keyed dict wrapped by the table's hqlt.object schema
    return table.schema.schema.schema


class TestDataDrop:
    def test_drop_does_not_mutate_input_tables(self):
        table = Table(df=pl.DataFrame({'a': [5], 'z': [0]}), name='t')
        data = Data([table])

        out = data.drop(N('a'))

        assert out['t'].df.columns == ['z']
        assert data['t'].df.columns == ['a', 'z']
        assert 'a' in raw(data['t'])

    def test_extend_keeps_input_context(self):
        from Hql.Operators.Extend import Extend

        ctx = Context(Data([Table(df=pl.DataFrame({'a': [5], 'z': [0]}), name='t')]))
        out = Extend([
            NamedExpression([N('b')], N('a')),
            NamedExpression([N('a')], N('z')),
        ]).eval(ctx)

        assert ctx.data['t'].df.to_dicts() == [{'a': 5, 'z': 0}]
        assert out.data['t'].df.to_dicts() == [{'b': 5, 'a': 0, 'z': 0}]


class TestDataUnnamedTables:
    def test_unnamed_tables_are_kept_apart(self):
        data = Data([
            Table(df=pl.DataFrame({'x': [1]})),
            Table(df=pl.DataFrame({'y': [2]})),
        ])

        assert list(data.tables) == ['Table 0', 'Table 1']
        assert data['Table 0'].df.columns == ['x']
        assert data['Table 1'].df.columns == ['y']


class TestTableMerge:
    def test_merge_without_rows_concats_tables(self):
        a = Table(df=pl.DataFrame({'name': ['tri'], 'sides': [3]}), name='shapes')
        b = Table(df=pl.DataFrame({'sides': [3], 'word': ['three']}), name='names')

        merged = Table.merge([a, b], merge_rows=False)

        assert isinstance(merged.schema, Schema)
        assert merged.name == 'shapes'
        assert merged.df.to_dicts() == [
            {'name': 'tri', 'sides': 3, 'word': None},
            {'name': None, 'sides': 3, 'word': 'three'},
        ]
        assert set(raw(merged)) == {'name', 'sides', 'word'}

    def test_merge_without_rows_renames_conflicting_types(self):
        a = Table(df=pl.DataFrame({'v': ['tri']}), name='shapes')
        b = Table(df=pl.DataFrame({'v': [3]}), schema={'v': hqlt.long()}, name='names')

        merged = Table.merge([a, b], merge_rows=False)

        assert merged.df.to_dicts() == [
            {'v': 'tri', 'v_long': None},
            {'v': None, 'v_long': 3},
        ]
        assert isinstance(raw(merged)['v'], hqlt.string)
        assert isinstance(raw(merged)['v_long'], hqlt.long)

    def test_data_join_merges_multiple_right_tables(self):
        left = Data([Table(df=pl.DataFrame({'k': [1, 2], 'x': ['a', 'b']}), name='l')])
        right = Data([
            Table(df=pl.DataFrame({'k': [1], 'y': ['c']}), name='r1'),
            Table(df=pl.DataFrame({'k': [2], 'y': ['d']}), name='r2'),
        ])

        out = left.join(right, [N('k')], 'inner')

        assert sorted(out['l'].df.to_dicts(), key=lambda r: r['k']) == [
            {'k': 1, 'x': 'a', 'y': 'c'},
            {'k': 2, 'x': 'b', 'y': 'd'},
        ]


class TestTableMergeRows:
    def test_shared_column_becomes_multivalue(self):
        data = Data(tables=[
            Table(df=pl.DataFrame({'x': [1, 2], 'q': ['a', 'b']}), name='t'),
            Table(df=pl.DataFrame({'x': [3, 4]}), name='t'),
        ])

        table = data['t']
        assert table.df.to_dicts() == [
            {'x': [1, 3], 'q': 'a'},
            {'x': [2, 4], 'q': 'b'},
        ]
        assert isinstance(raw(table)['x'], hqlt.multivalue)
        assert isinstance(raw(table)['q'], hqlt.string)

    def test_multi_character_column_name(self):
        data = Data(tables=[
            Table(df=pl.DataFrame({'xyz': [1]}), name='t'),
            Table(df=pl.DataFrame({'xyz': [2]}), name='t'),
            Table(df=pl.DataFrame({'xyz': [3]}), name='t'),
        ])

        assert data['t'].df.to_dicts() == [{'xyz': [1, 2, 3]}]
        assert isinstance(raw(data['t'])['xyz'], hqlt.multivalue)

    def test_shared_struct_merges_fields(self):
        data = Data(tables=[
            Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 1}]}), name='t'),
            Table(df=pl.DataFrame({'a': [{'b': 2}]}), name='t'),
        ])

        table = data['t']
        assert table.df.to_dicts() == [{'a': {'b': [1, 2], 'c': 1}}]
        assert isinstance(raw(table)['a']['b'], hqlt.multivalue)
