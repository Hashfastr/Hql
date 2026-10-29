import pytest

from Hql.Types.Elasticsearch import ESTypes
from Hql.Types.Hql import HqlTypes as hqlt


# ---------------------------------------------------------------------------
# workspace-qgw.38: Elasticsearch adapters
# ---------------------------------------------------------------------------

class TestElasticsearchTypes:
    @pytest.mark.parametrize('name', ['flattened', 'object', 'nested'])
    def test_schema_defaults(self, name):
        assert ESTypes.from_name(name)().hql_schema() == hqlt.object({})

    @pytest.mark.parametrize(('name', 'inner'), [
        ('integer_range', hqlt.int()),
        ('float_range', hqlt.float()),
        ('long_range', hqlt.long()),
        ('double_range', hqlt.double()),
        ('date_range', hqlt.datetime()),
        ('ip_range', hqlt.string()),
    ])
    def test_ranges(self, name, inner):
        hql = ESTypes.from_name(name)().hql_schema()
        assert isinstance(hql, hqlt.range)
        assert hql.inner == inner
