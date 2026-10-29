import datetime
import decimal
import itertools
import os
import subprocess
import sys
from pathlib import Path as FsPath

import polars as pl
import pytest

from Hql.Data import Schema, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Python import PythonTypes as pyt


DT = datetime.datetime(2020, 1, 1, 12, 30)


def load(values, key='a'):
    return Table(init_data=[{key: v} for v in values])


# ---------------------------------------------------------------------------
# workspace-qgw.20: python int -> long
# ---------------------------------------------------------------------------

class TestPythonIntWidth:
    def test_int_maps_to_long(self):
        assert pyt.int().hql_schema() == hqlt.long()

    def test_large_int_does_not_empty_table(self):
        table = load([3000000000, 1])
        assert table.df.to_dicts() == [{'a': 3000000000}, {'a': 1}]
        assert table.df.schema['a'] == pl.Int64

    def test_epoch_ms_timestamps_survive(self):
        ms = 1_700_000_000_000
        assert load([ms]).df['a'].to_list() == [ms]

    def test_nested_large_int(self):
        table = Table(init_data=[{'a': {'b': 2 ** 40}}])
        assert table.df.to_dicts() == [{'a': {'b': 2 ** 40}}]

    def test_table_schema_reports_long(self):
        assert load([1]).get_schema() == {'a': 'long'}


# ---------------------------------------------------------------------------
# workspace-qgw.21: python float -> double
# ---------------------------------------------------------------------------

class TestPythonFloatWidth:
    def test_float_maps_to_double(self):
        assert pyt.float().hql_schema() == hqlt.double()

    def test_float_keeps_double_precision(self):
        table = load([123456789.123])
        assert table.df.to_dicts() == [{'a': 123456789.123}]
        assert table.df.schema['a'] == pl.Float64

    def test_list_of_floats(self):
        assert load([[0.1, 123456789.123]]).df['a'].to_list() == [[0.1, 123456789.123]]


# ---------------------------------------------------------------------------
# workspace-qgw.22: PythonTypes.resolve_conflict
# ---------------------------------------------------------------------------

class TestPythonResolveConflict:
    def test_equal_datetimes_stay_datetime(self):
        table = load([DT, DT])
        assert isinstance(table.schema.schema.schema['a'], hqlt.datetime)
        assert table.df['a'].to_list() == [DT, DT]

    def test_none_then_datetime(self):
        table = load([None, DT])
        assert isinstance(table.schema.schema.schema['a'], hqlt.datetime)
        assert table.df['a'].to_list() == [None, DT]

    def test_datetime_then_none(self):
        assert load([DT, None]).df['a'].to_list() == [DT, None]

    def test_bool_and_float_promote_to_double(self):
        table = load([True, 2.5, 0.0])
        assert isinstance(table.schema.schema.schema['a'], hqlt.double)
        assert table.df['a'].to_list() == [1.0, 2.5, 0.0]

    def test_bool_and_int_promote_to_long(self):
        assert load([True, 2]).df['a'].to_list() == [1, 2]

    def test_int_and_float_promote_to_double(self):
        assert load([1, 2.5]).df['a'].to_list() == [1.0, 2.5]

    def test_int_and_str_fall_back_to_string(self):
        table = load([1, 'a'])
        assert isinstance(table.schema.schema.schema['a'], hqlt.string)
        assert table.df['a'].to_list() == ['1', 'a']

    def test_int_and_datetime_keep_both_values(self):
        table = load([1, DT])
        assert isinstance(table.schema.schema.schema['a'], hqlt.dynamic)
        assert table.df['a'].to_list() == [1, DT]

    def test_dict_and_scalar_keep_both_values(self):
        table = load([{'b': 1}, 1])
        assert isinstance(table.schema.schema.schema['a'], hqlt.dynamic)
        assert table.df['a'].to_list() == [{'b': 1}, 1]

    def test_dicts_merge_keys(self):
        table = load([{'b': 1}, {'c': 'x'}])
        assert table.df['a'].to_list() == [{'b': 1, 'c': None}, {'b': None, 'c': 'x'}]

    def test_mixed_list_elements(self):
        assert load([[1, 'x']]).df['a'].to_list() == [['1', 'x']]

    def test_list_of_unloadable_mix_is_dynamic(self):
        # polars can't build a List column out of ints and datetimes
        assert isinstance(Schema(data=[{'a': [1, DT]}]).schema.schema['a'], hqlt.dynamic)

    def test_unregistered_type_is_dynamic(self):
        import uuid
        value = uuid.UUID(int=5)
        assert load([value]).df['a'].to_list() == [value]

    def test_all_none(self):
        assert isinstance(pyt.resolve_conflict([pyt.NoneType(), pyt.NoneType()]), pyt.NoneType)

    def test_empty_raises(self):
        with pytest.raises(hqle.CompilerException):
            pyt.resolve_conflict([])

    def test_from_value_list(self):
        assert isinstance(pyt.from_value([1, 2.5]), pyt.list)
        assert isinstance(pyt.from_value([1, 2.5]).inner, pyt.float)

    def test_order_independent(self):
        base = [pyt.bool, pyt.int, pyt.Decimal, pyt.float, pyt.str, pyt.date,
                pyt.datetime, pyt.timedelta, pyt.bytes, pyt.NoneType, pyt.object]
        for combo in itertools.combinations(base, 3):
            results = {
                pyt.resolve_conflict([c() for c in perm]).name
                for perm in itertools.permutations(combo)
            }
            assert len(results) == 1, (combo, results)


# ---------------------------------------------------------------------------
# workspace-qgw.23: HqlTypes.resolve_conflict
# ---------------------------------------------------------------------------

class TestHqlResolveConflict:
    @pytest.mark.parametrize('factory', [hqlt.long, hqlt.double, hqlt.datetime, hqlt.string, hqlt.int])
    def test_equal_types_resolve_to_themselves(self, factory):
        assert hqlt.resolve_conflict([factory(), factory()]) == factory()

    def test_int_and_string_is_string(self):
        assert hqlt.resolve_conflict([hqlt.int(), hqlt.string()]) == hqlt.string()

    def test_null_and_string_is_string(self):
        assert hqlt.resolve_conflict([hqlt.null(), hqlt.string()]) == hqlt.string()

    def test_null_and_datetime_is_datetime(self):
        assert hqlt.resolve_conflict([hqlt.datetime(), hqlt.null()]) == hqlt.datetime()

    def test_all_null(self):
        assert hqlt.resolve_conflict([hqlt.null(), hqlt.null()]) == hqlt.null()

    @pytest.mark.parametrize('types', [[hqlt.bool, hqlt.float], [hqlt.float, hqlt.bool]])
    def test_bool_and_float_is_float(self, types):
        assert hqlt.resolve_conflict([t() for t in types]) == hqlt.float()

    def test_int_and_long_is_long(self):
        assert hqlt.resolve_conflict([hqlt.int(), hqlt.long()]) == hqlt.long()

    def test_int_and_float_is_double(self):
        assert hqlt.resolve_conflict([hqlt.int(), hqlt.float()]) == hqlt.double()

    def test_uint_and_int_is_long(self):
        assert hqlt.resolve_conflict([hqlt.uint(), hqlt.int()]) == hqlt.long()

    def test_bool_and_decimal_casts(self):
        result = hqlt.resolve_conflict([hqlt.bool(), hqlt.decimal()])
        assert result == hqlt.decimal()
        assert result.cast(pl.Series([True, None])).to_list() == [decimal.Decimal(1), None]

    def test_datetime_and_int_is_string(self):
        assert hqlt.resolve_conflict([hqlt.datetime(), hqlt.int()]) == hqlt.string()

    def test_scalar_and_multivalue(self):
        result = hqlt.resolve_conflict([hqlt.int(), hqlt.multivalue(hqlt.long())])
        assert result == hqlt.multivalue(hqlt.long())

    def test_multivalues_resolve_inner(self):
        result = hqlt.resolve_conflict([hqlt.multivalue(hqlt.int()), hqlt.multivalue(hqlt.string())])
        assert result == hqlt.multivalue(hqlt.string())

    def test_objects_merge_keys(self):
        result = hqlt.resolve_conflict([
            hqlt.object({'a': hqlt.int(), 'n': {'x': hqlt.int()}}),
            hqlt.object({'a': hqlt.long(), 'b': hqlt.string(), 'n': {'x': hqlt.string()}}),
        ])
        assert result == hqlt.object({'a': hqlt.long(), 'b': hqlt.string(), 'n': {'x': hqlt.string()}})

    def test_object_and_scalar_is_string(self):
        assert hqlt.resolve_conflict([hqlt.object({'a': hqlt.int()}), hqlt.int()]) == hqlt.string()

    def test_decimals_widen(self):
        result = hqlt.resolve_conflict([hqlt.decimal(10, 2), hqlt.decimal(12, 6)])
        assert (result.precision, result.scale) == (14, 6)

    def test_dynamic_absorbs(self):
        assert hqlt.resolve_conflict([hqlt.int(), hqlt.dynamic()]) == hqlt.dynamic()

    def test_order_independent(self):
        base = [hqlt.bool, hqlt.byte, hqlt.short, hqlt.int, hqlt.long, hqlt.xlong,
                hqlt.ubyte, hqlt.ushort, hqlt.uint, hqlt.ulong, hqlt.uxlong, hqlt.decimal,
                hqlt.float, hqlt.double, hqlt.string, hqlt.datetime, hqlt.duration,
                hqlt.null, hqlt.binary, hqlt.guid, hqlt.ip4, hqlt.dynamic]
        for combo in itertools.combinations(base, 3):
            results = {
                hqlt.resolve_conflict([c() for c in perm]).name
                for perm in itertools.permutations(combo)
            }
            assert len(results) == 1, (combo, results)

    def test_promotion_targets_can_cast(self):
        samples = {
            'bool': [True], 'byte': [1], 'short': [1], 'int': [1], 'long': [1],
            'xlong': [1], 'ubyte': [1], 'ushort': [1], 'uint': [1], 'ulong': [1],
            'uxlong': [1], 'decimal': [1], 'float': [1.5], 'double': [1.5],
        }
        for name, values in samples.items():
            source = hqlt.from_name(name)
            series = source.cast(pl.Series(values))
            for target in source.promotes_to:
                hqlt.from_name(target).cast(series)

    def test_independent_of_hash_seed(self):
        code = (
            'from Hql.Types.Hql import HqlTypes as h\n'
            'print(h.resolve_conflict([h.bool(), h.float(), h.int()]).name,'
            ' h.resolve_conflict([h.multivalue(h.int()), h.multivalue(h.bool()), h.float()]).inner.name)'
        )
        root = str(FsPath(__file__).resolve().parents[2])
        outputs = set()
        for seed in ('1', '2', '3', '4'):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=root)
            outputs.add(subprocess.run(
                [sys.executable, '-c', code], env=env, cwd=root,
                capture_output=True, text=True, check=True
            ).stdout)
        assert outputs == {'double double\n'}


# ---------------------------------------------------------------------------
# workspace-qgw.33: python bytes/date/timedelta/Decimal
# ---------------------------------------------------------------------------

class TestPythonRegistrations:
    def test_bytes(self):
        table = load([b'x'])
        assert isinstance(table.schema.schema.schema['a'], hqlt.binary)
        assert table.df['a'].to_list() == [b'x']

    def test_date(self):
        table = load([datetime.date(2020, 1, 1)])
        assert table.df['a'].to_list() == [datetime.date(2020, 1, 1)]

    def test_timedelta(self):
        table = load([datetime.timedelta(days=1), None])
        assert isinstance(table.schema.schema.schema['a'], hqlt.duration)
        assert table.df['a'].to_list() == [datetime.timedelta(days=1), None]

    def test_decimal(self):
        table = load([decimal.Decimal('1.25'), None])
        assert isinstance(table.schema.schema.schema['a'], hqlt.decimal)
        assert table.df['a'].to_list() == [decimal.Decimal('1.25'), None]

    def test_decimal_mixed_with_numbers_is_double(self):
        table = load([decimal.Decimal('1.25'), 2, True])
        assert isinstance(table.schema.schema.schema['a'], hqlt.double)
        assert table.df['a'].to_list() == [1.25, 2.0, 1.0]
