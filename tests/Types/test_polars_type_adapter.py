import datetime
import decimal

import polars as pl
import pytest

from Hql.Data import Table
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Polars import PolarsTypes as plt


DT = datetime.datetime(2020, 1, 1, 12, 30)


# ---------------------------------------------------------------------------
# workspace-qgw.32: PolarsTypes.from_pure_polars
# ---------------------------------------------------------------------------

class TestFromPurePolars:
    @pytest.mark.parametrize(('dtype', 'expected'), [
        (pl.Categorical(), hqlt.string()),
        (pl.Categorical, hqlt.string()),
        (pl.Enum(['a', 'b']), hqlt.string()),
        (pl.UInt128(), hqlt.uxlong()),
        (pl.Float16(), hqlt.float()),
        (pl.Object(), hqlt.dynamic()),
        (pl.Array(pl.Int64, 2), hqlt.multivalue(hqlt.long())),
        (pl.Int64, hqlt.long()),
        (pl.Date(), hqlt.date()),
    ])
    def test_resolves(self, dtype, expected):
        assert plt.from_pure_polars(dtype).hql_schema() == expected

    def test_datetime_keeps_unit_and_zone(self):
        hql = plt.from_pure_polars(pl.Datetime('ms', 'UTC')).hql_schema()
        assert hql.pl_schema() == pl.Datetime('ms', 'UTC')

    def test_duration_keeps_unit(self):
        assert plt.from_pure_polars(pl.Duration('ns')).hql_schema().pl_schema() == pl.Duration('ns')

    def test_polars_decimal_keeps_scale(self):
        hql = plt.from_pure_polars(pl.Decimal(10, 3)).hql_schema()
        assert hql == hqlt.decimal(10, 3)

    def test_polars_decimal_column_not_rounded(self):
        df = pl.DataFrame({'d': pl.Series([1.25]).cast(pl.Decimal(10, 3))})
        assert Table(df=df).df['d'].to_list() == [decimal.Decimal('1.250')]

    def test_datetime_units_widen(self):
        result = hqlt.resolve_conflict([hqlt.datetime('ms'), hqlt.datetime('ns')])
        assert result == hqlt.datetime('ns')

    def test_categorical_table(self):
        df = pl.DataFrame({'c': pl.Series(['a', None]).cast(pl.Categorical)})
        assert Table(df=df).df.to_dicts() == [{'c': 'a'}, {'c': None}]

    def test_tz_datetime_table_keeps_zone(self):
        df = pl.DataFrame({'t': pl.Series([DT]).cast(pl.Datetime('ms', 'UTC'))})
        assert Table(df=df).df.schema['t'] == pl.Datetime('ms', 'UTC')

    def test_array_table(self):
        df = pl.DataFrame({'a': pl.Series([[1, 2]], dtype=pl.Array(pl.Int64, 2))})
        assert Table(df=df).df.to_dicts() == [{'a': [1, 2]}]

    def test_object_table(self):
        df = pl.DataFrame({'o': pl.Series([{'x': 1}, 5], dtype=pl.Object)})
        assert Table(df=df).df['o'].to_list() == [{'x': 1}, 5]


# ---------------------------------------------------------------------------
# workspace-qgw.37: polars Int128 signedness
# ---------------------------------------------------------------------------

class TestPolarsInt128:
    def test_signed(self):
        assert plt.Int128().pl_schema() == pl.Int128
        assert plt.Int128().cast(pl.Series([-5], dtype=pl.Int128)).to_list() == [-5]
