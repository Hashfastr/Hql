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
