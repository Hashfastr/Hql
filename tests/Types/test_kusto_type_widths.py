from types import SimpleNamespace

import pytest

from Hql.Data import Table
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Kusto import KustoTypes


# ---------------------------------------------------------------------------
# workspace-qgw.35: Kusto dynamic
# ---------------------------------------------------------------------------

class FakeResult(list):
    def __init__(self, rows, columns):
        super().__init__(rows)
        self.columns = [SimpleNamespace(column_name=n, column_type=t) for n, t in columns]


class TestKustoDynamic:
    def test_dynamic_values_survive(self):
        from Hql.Database.Kusto import Kusto

        rows = [[{'a': 1}, 1], [[1, 2], 2], ['x', 3], [None, 4]]
        response = SimpleNamespace(primary_results=[FakeResult(rows, [('dyn', 'dynamic'), ('n', 'int')])])
        schema = Kusto._response_schema(response)
        table = Table(init_data=Kusto._response_rows(response), schema=schema)
        assert table.to_dicts() == [
            {'dyn': {'a': 1}, 'n': 1},
            {'dyn': [1, 2], 'n': 2},
            {'dyn': 'x', 'n': 3},
            {'dyn': None, 'n': 4},
        ]

    def test_dynamic_maps_back_to_dynamic(self):
        assert KustoTypes.from_hql(hqlt.dynamic()).deparse() == 'dynamic'


# ---------------------------------------------------------------------------
# workspace-qgw.36: Kusto uint/ip4/ulong widths
# ---------------------------------------------------------------------------

class TestKustoWidths:
    @pytest.mark.parametrize(('hql_type', 'kusto_name'), [
        (hqlt.uint(), 'long'),
        (hqlt.ip4(), 'long'),
        (hqlt.ulong(), 'decimal'),
        (hqlt.int(), 'int'),
        (hqlt.ushort(), 'int'),
    ])
    def test_mapping(self, hql_type, kusto_name):
        assert KustoTypes.from_hql(hql_type).deparse() == kusto_name

    def test_ip4_value_fits(self):
        value = hqlt.ip4().cast_single('192.168.1.1')
        assert value is not None and value > 2 ** 31 - 1
        assert isinstance(KustoTypes.from_hql(hqlt.ip4()).hql_schema(), hqlt.long)
