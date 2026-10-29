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


JOIN_KINDS = [
    'inner', 'innerunique', 'leftsemi', 'rightsemi',
    'leftouter', 'rightouter', 'fullouter', 'leftanti', 'rightanti',
]


def join_tables():
    left = Table(
        df=pl.DataFrame({
            'k': [1, 2],
            'v': ['a', 'b'],
            'a': [{'b': 1, 'c': 1}, {'b': 2, 'c': 2}],
            's': [1, 2],
        }),
        name='t',
    )
    right = Table(
        df=pl.DataFrame({
            'k': [2, 3],
            'v': [5, 6],
            'a': [{'b': 2, 'd': 'x'}, {'b': 3, 'd': 'y'}],
            's': [{'q': 1}, {'q': 2}],
            'y': ['c', 'd'],
        }),
        name='t',
    )
    return left, right


class TestTableJoin:
    @pytest.mark.parametrize('kind', JOIN_KINDS)
    @pytest.mark.parametrize('on', [
        [N('k')],
        [P('a', 'b')],
        [N('k'), P('a', 'b')],
    ], ids=['name', 'path', 'mixed'])
    def test_schema_matches_df(self, kind, on):
        left, right = join_tables()
        joined = left.join(right, on, kind)

        assert set(raw(joined)) == set(joined.df.columns)
        assert dict(joined.schema.gen_pl_schema()) == dict(joined.df.schema)
        # schema paths must all be selectable
        for path, _ in joined.schema:
            joined.df.select(path.polars_value())

    @pytest.mark.parametrize('kind', JOIN_KINDS)
    def test_schema_not_aliased(self, kind):
        left, right = join_tables()
        joined = left.join(right, [N('k')], kind)

        assert joined.schema is not left.schema
        assert joined.schema is not right.schema
        joined.schema.drop(N('k'))
        assert 'k' in raw(left)
        assert 'k' in raw(right)

    def test_rightanti_keeps_unmatched_right_rows(self):
        left = Table(df=pl.DataFrame({'k': [1, 2], 'x': ['a', 'b']}), name='t')
        right = Table(df=pl.DataFrame({'k': [2, 3], 'y': ['c', 'd']}), name='t')

        assert left.join(right, [N('k')], 'rightanti').df.to_dicts() == [{'k': 3, 'y': 'd'}]
        assert left.join(right, [N('k')], 'leftanti').df.to_dicts() == [{'k': 1, 'x': 'a'}]

    def test_semi_joins_only_keep_one_side(self):
        left = Table(df=pl.DataFrame({'k': [1, 2], 'x': ['a', 'b']}), name='t')
        right = Table(df=pl.DataFrame({'k': [2, 3], 'y': ['c', 'd']}), name='t')

        semi = left.join(right, [N('k')], 'leftsemi')
        assert semi.df.to_dicts() == [{'k': 2, 'x': 'b'}]
        assert set(raw(semi)) == {'k', 'x'}

        semi = left.join(right, [N('k')], 'rightsemi')
        assert semi.df.to_dicts() == [{'k': 2, 'y': 'c'}]
        assert set(raw(semi)) == {'k', 'y'}

    def test_rightouter_suffixes_left_conflict_on_right(self):
        left = Table(
            df=pl.DataFrame({'k': [1, 2], 'v': ['a', 'b']}),
            schema={'k': hqlt.long(), 'v': hqlt.string()},
            name='t',
        )
        right = Table(
            df=pl.DataFrame({'k': [2, 3], 'v': [5, 6]}),
            schema={'k': hqlt.long(), 'v': hqlt.long()},
            name='t',
        )

        joined = left.join(right, [N('k')], 'rightouter')

        assert sorted(joined.df.to_dicts(), key=lambda r: r['k']) == [
            {'v': 'b', 'k': 2, 'v_right': 5},
            {'v': None, 'k': 3, 'v_right': 6},
        ]
        assert isinstance(raw(joined)['v'], hqlt.string)
        assert isinstance(raw(joined)['v_right'], hqlt.long)

    def test_fullouter_keeps_both_keys(self):
        left = Table(df=pl.DataFrame({'k': [1, 2], 'x': ['a', 'b']}), name='t')
        right = Table(df=pl.DataFrame({'k': [2, 3], 'y': ['c', 'd']}), name='t')

        joined = left.join(right, [N('k')], 'fullouter')

        assert set(raw(joined)) == {'k', 'x', 'k_right', 'y'}
        assert joined.df.select(N('k_right').polars()).to_series().to_list().count(None) == 1

    def test_join_on_nested_path(self):
        left = Table(df=pl.DataFrame({'a': [{'b': 1}, {'b': 2}], 'x': ['l1', 'l2']}), name='t')
        right = Table(df=pl.DataFrame({'a': [{'b': 2}, {'b': 3}], 'y': ['r2', 'r3']}), name='t')

        joined = left.join(right, [P('a', 'b')], 'inner')

        assert joined.df.to_dicts() == [
            {'a': {'b': 2}, 'x': 'l2', 'a_right': {'b': 2}, 'y': 'r2'},
        ]
        assert set(raw(joined)) == {'a', 'x', 'a_right', 'y'}
