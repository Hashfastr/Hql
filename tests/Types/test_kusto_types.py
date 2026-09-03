import pytest

from Hql.Context import get_type
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Kusto import KustoTypes


@pytest.mark.parametrize(
    ('hql_type', 'kusto_type'),
    [
        (hqlt.string(), KustoTypes.string),
        (hqlt.bool(), KustoTypes.bool),
        (hqlt.int(), KustoTypes.int),
        (hqlt.long(), KustoTypes.long),
        (hqlt.double(), KustoTypes.real),
        (hqlt.datetime(), KustoTypes.datetime),
        (hqlt.duration(), KustoTypes.timespan),
        (hqlt.object({}), KustoTypes.dynamic),
        (hqlt.multivalue(hqlt.string()), KustoTypes.dynamic),
    ],
)
def test_hql_types_resolve_to_registered_kusto_types(hql_type, kusto_type):
    resolved = KustoTypes.from_hql(hql_type)

    assert isinstance(resolved, kusto_type)
    assert get_type(f'kusto_{hql_type.name}') is kusto_type


@pytest.mark.parametrize(
    'name',
    [
        'bool',
        'int',
        'long',
        'real',
        'decimal',
        'datetime',
        'timespan',
        'dynamic',
        'guid',
        'string',
    ],
)
def test_native_kusto_types_are_registered(name):
    assert KustoTypes.from_name(name).__name__ == name


def test_non_hql_type_is_rejected():
    with pytest.raises(hqle.CompilerException, match='Cannot convert'):
        KustoTypes.from_hql(object())
