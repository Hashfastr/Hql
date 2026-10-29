import decimal

import polars as pl
import pytest

from Hql.Data import Schema, Table
from Hql.Types.Elasticsearch import ESTypes
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Kusto import KustoTypes


# ---------------------------------------------------------------------------
# workspace-qgw.28: decimal precision and scale
# ---------------------------------------------------------------------------

class TestDecimal:
    def test_default_keeps_fraction(self):
        out = hqlt.decimal().cast(pl.Series([1.25, 2.75]))
        assert out.to_list() == [decimal.Decimal('1.25'), decimal.Decimal('2.75')]

    def test_explicit_precision_scale(self):
        assert hqlt.decimal(10, 3).pl_schema() == pl.Decimal(10, 3)

    def test_params_distinguish(self):
        assert hqlt.decimal(10, 2) != hqlt.decimal(10, 3)
        assert hqlt.decimal(10, 2) == hqlt.decimal(10, 2)

    def test_es_scaled_float_is_double(self):
        assert ESTypes.from_name('scaled_float')().hql_schema() == hqlt.double()

    def test_kusto_decimal_keeps_fraction(self):
        hql = KustoTypes.decimal().hql_schema()
        assert hql.cast(pl.Series([0.5])).to_list() == [decimal.Decimal('0.5')]


# ---------------------------------------------------------------------------
# workspace-qgw.29: guid
# ---------------------------------------------------------------------------

class TestGuid:
    def test_cast_string(self):
        guid = '6f9619ff-8b86-d011-b42d-00c04fc964ff'
        assert hqlt.guid().cast(pl.Series([guid, None])).to_list() == [guid, None]

    def test_normalizes_and_rejects_invalid(self):
        out = hqlt.guid().cast(pl.Series(['{6F9619FF-8B86-D011-B42D-00C04FC964FF}', 'nope']))
        assert out.to_list() == ['6f9619ff-8b86-d011-b42d-00c04fc964ff', None]

    def test_kusto_guid_column(self):
        guid = '6f9619ff-8b86-d011-b42d-00c04fc964ff'
        schema = Schema(schema={'g': KustoTypes.guid().hql_schema()})
        assert Table(init_data=[{'g': guid}], schema=schema).df['g'].to_list() == [guid]


# ---------------------------------------------------------------------------
# workspace-qgw.30: ip6
# ---------------------------------------------------------------------------

class TestIP6:
    def test_unsigned_proto(self):
        assert hqlt.ip6().pl_schema() == pl.UInt128

    def test_cast_strings(self):
        out = hqlt.ip6().cast(pl.Series(['::1', 'fe80::1', 'ff02::1', 'bogus', None]))
        assert out.to_list() == [1, 0xfe80 << 112 | 1, 0xff02 << 112 | 1, None, None]

    def test_human_round_trip(self):
        ip6 = hqlt.ip6()
        out = ip6.human(ip6.cast(pl.Series(['fe80::1', None])))
        assert out.to_list() == ['fe80::1', None]


# ---------------------------------------------------------------------------
# workspace-qgw.31: ip4 validation
# ---------------------------------------------------------------------------

class TestIP4Validation:
    @pytest.mark.parametrize('ip', ['1.2.3.300', '1.2.3.4.5', 'hello', '1.2.3', '', '::1'])
    def test_invalid_is_none(self, ip):
        assert hqlt.ip4().cast_single(ip) is None

    def test_valid(self):
        assert hqlt.ip4().cast_single('1.2.3.4') == 0x01020304

    def test_series_cast(self):
        assert hqlt.ip4().cast(pl.Series(['1.2.3.4', '1.2.3.300', None])).to_list() == [0x01020304, None, None]
