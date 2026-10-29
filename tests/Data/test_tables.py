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


class TestTableInitData:
    def test_large_ints_are_not_dropped(self):
        table = Table(init_data=[{'ts': 1730000000000, 'host': 'a'}])

        assert table.df.to_dicts() == [{'ts': 1730000000000, 'host': 'a'}]
        assert set(raw(table)) == {'ts', 'host'}

    def test_mixed_dict_and_str_values_are_not_dropped(self):
        table = Table(init_data=[{'a': {'b': 1}}, {'a': 's'}])

        assert table.df.shape == (2, 1)
        assert table.df['a'].to_list()[1] == 's'
        assert isinstance(raw(table)['a'], hqlt.string)

    def test_scalars_wrapped_in_mixed_multivalue(self):
        table = Table(init_data=[{'a': 1}, {'a': [2, 3]}, {'a': None}])

        assert table.df.to_dicts() == [{'a': [1]}, {'a': [2, 3]}, {'a': None}]
        assert isinstance(raw(table)['a'], hqlt.multivalue)

    def test_nested_scalars_wrapped_in_mixed_multivalue(self):
        table = Table(init_data=[{'n': {'m': 1}}, {'n': {'m': [2, 3]}}])

        assert table.df.to_dicts() == [{'n': {'m': [1]}}, {'n': {'m': [2, 3]}}]
        assert isinstance(raw(table)['n']['m'], hqlt.multivalue)


class TestTableStrip:
    def test_single_multi_field_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}]}), name='t').strip()

        assert table.df.to_dicts() == [{'b': 1, 'c': 2}]
        assert set(raw(table)) == {'b', 'c'}

    def test_extend_with_struct_value(self):
        from Hql.Operators.Extend import Extend

        ctx = Context(Data([Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}], 'z': [0]}), name='t')]))
        out = Extend([NamedExpression([N('y')], N('a'))]).eval(ctx)

        assert out.data['t'].df.to_dicts() == [{'y': {'b': 1, 'c': 2}, 'a': {'b': 1, 'c': 2}, 'z': 0}]


class TestTableUnnest:
    def test_single_key_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1}], 'z': [0]}), name='t').unnest(N('a'))

        assert table.df.to_dicts() == [{'b': 1}]
        assert list(raw(table)) == ['b']

    def test_stops_at_requested_level(self):
        df = pl.DataFrame({'a': [{'b': {'c': 1, 'd': 2}}], 'z': [0]})
        table = Table(df=df, name='t').unnest(N('a'))

        assert table.df.columns == ['b']
        assert set(raw(table)['b']) == {'c', 'd'}

    def test_multivalue_of_structs(self):
        df = pl.DataFrame({'a': [[{'b': 1, 'c': 2}], [{'b': 3, 'c': 4}]]})
        table = Table(df=df, name='t').unnest(N('a'))

        assert table.df.to_dicts() == [{'b': 1, 'c': 2}, {'b': 3, 'c': 4}]
        assert set(raw(table)) == {'b', 'c'}


class TestDropThroughScalar:
    def test_table_drop_keeps_scalar(self):
        table = Table(df=pl.DataFrame({'a': [1], 'z': [0]}), name='t')
        table.drop(P('a', 'b'))

        assert table.df.columns == ['a', 'z']
        assert set(raw(table)) == {'a', 'z'}

    def test_schema_drop_keeps_scalar(self):
        schema = Schema(schema={'a': hqlt.long(), 'z': hqlt.long()})
        schema.drop(P('a', 'b'))

        assert set(schema.schema.schema) == {'a', 'z'}


class TestZeroRowTables:
    def test_assert_field(self):
        table = Table(df=pl.DataFrame({'x': pl.Series([], dtype=pl.Int64)}))

        assert table.assert_field(N('x'))

    def test_keeps_explicit_schema(self):
        df = pl.DataFrame({'x': pl.Series([], dtype=pl.Int64)})
        table = Table(df=df, schema={'x': hqlt.string()})

        assert table.df.schema == pl.Schema({'x': pl.String})
        assert isinstance(raw(table)['x'], hqlt.string)

    def test_drop_keeps_struct(self):
        df = pl.DataFrame({'a': pl.Series([], dtype=pl.Struct({'b': pl.Int64, 'c': pl.Int64}))})
        table = Table(df=df)
        table.drop(P('a', 'b'))

        assert table.df.schema == pl.Schema({'a': pl.Struct({'c': pl.Int64})})
        assert list(raw(table)['a']) == ['c']


class TestTableInsert:
    def test_does_not_mutate_reference(self):
        ref = N('x')
        first = Table(df=pl.DataFrame({'x': [1]}), name='a')
        second = Table(df=pl.DataFrame({'y': [1]}), name='b')

        first.insert(ref, pl.Series([5]), hqlt.long())
        second.insert(ref, pl.Series([6]), hqlt.long())

        assert ref.name == 'x'
        assert first.df.to_dicts() == [{'x_0': 5, 'x': 1}]
        assert second.df.to_dicts() == [{'x': 6, 'y': 1}]

    def test_does_not_mutate_path(self):
        ref = P('a', 'b')
        table = Table(df=pl.DataFrame({'a': [1]}))

        table.insert(ref, pl.Series([5]), hqlt.long())

        assert ref.list() == ['a', 'b']

    def test_nested_under_scalar(self):
        table = Table(df=pl.DataFrame({'a': [1], 'z': [0]}))

        table.insert(P('a', 'b'), pl.Series([5]), hqlt.long())
        assert table.df.to_dicts() == [{'a_0': {'b': 5}, 'a': 1, 'z': 0}]
        assert set(raw(table)['a_0']) == {'b'}

        # second insert merges into the renamed struct
        table.insert(P('a', 'c'), pl.Series([6]), hqlt.long())
        assert table.df.to_dicts() == [{'a_0': {'c': 6, 'b': 5}, 'a': 1, 'z': 0}]
        assert set(raw(table)['a_0']) == {'b', 'c'}

    def test_into_existing_single_field_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1}], 'z': [0]}))

        table.insert(P('a', 'c'), pl.Series([6]), hqlt.long())

        assert table.df.to_dicts() == [{'a': {'c': 6, 'b': 1}, 'z': 0}]
        assert set(raw(table)['a']) == {'b', 'c'}


class TestTableRemovePopRename:
    def test_remove_keeps_siblings_out_of_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}], 'z': [0]}))

        assert table.remove(P('a', 'b')).to_dicts() == [{'z': 0, 'a': {'c': 2}}]

    def test_remove_last_field_drops_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1}], 'z': [0]}))

        assert table.remove(P('a', 'b')).to_dicts() == [{'z': 0}]

    def test_pop_removes_from_df_and_schema(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}], 'z': [0]}))

        value = table.pop(P('a', 'b'))

        assert value.df.to_dicts() == [{'a': {'b': 1}}]
        assert table.df.to_dicts() == [{'z': 0, 'a': {'c': 2}}]
        assert list(raw(table)['a']) == ['c']

    def test_rename_moves_value(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}], 'z': [0]}))

        table.rename(P('a', 'b'), N('q'))

        assert table.df.to_dicts() == [{'q': 1, 'z': 0, 'a': {'c': 2}}]
        assert set(raw(table)) == {'q', 'z', 'a'}
        assert isinstance(raw(table)['q'], hqlt.long)

    def test_rename_struct(self):
        table = Table(df=pl.DataFrame({'a': [{'b': 1, 'c': 2}], 'z': [0]}))

        table.rename(N('a'), P('n', 'm'))

        assert table.df.to_dicts() == [{'n': {'m': {'b': 1, 'c': 2}}, 'z': 0}]
        assert set(raw(table)['n']['m']) == {'b', 'c'}


class TestTableCastInPlace:
    def test_missing_field_returns_table(self):
        table = Table(df=pl.DataFrame({'a': [1]}))

        assert table.cast_in_place(N('q'), hqlt.string()) is table

    def test_to_clause_on_partial_tables(self):
        from Hql.Expressions import ToClause

        ctx = Context(Data([
            Table(df=pl.DataFrame({'a': [1]}), name='t1'),
            Table(df=pl.DataFrame({'b': [2]}), name='t2'),
        ]))

        out = ToClause(N('a'), hqlt.string()).eval(ctx)

        assert out.data['t1'].df.to_dicts() == [{'a': '1'}]
        assert out.data['t2'].df.to_dicts() == [{'b': 2}]


class TestSchemaPopRename:
    def test_pop(self):
        schema = Schema(schema={'x': hqlt.long(), 'y': hqlt.string()})

        assert isinstance(schema.pop(N('x')), hqlt.long)
        assert list(schema.schema.schema) == ['y']

    def test_pop_nested(self):
        schema = Schema(schema={'a': {'b': hqlt.long(), 'c': hqlt.string()}})

        assert isinstance(schema.pop(P('a', 'b')), hqlt.long)
        assert list(schema.schema.schema['a']) == ['c']

    def test_rename(self):
        schema = Schema(schema={'x': hqlt.long(), 'a': {'b': hqlt.string()}})

        schema.rename(P('a', 'b'), P('c', 'd'))

        assert set(schema.schema.schema) == {'x', 'c'}
        assert isinstance(schema.schema.schema['c']['d'], hqlt.string)
