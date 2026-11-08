import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Aggregation import ByExpression
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Expressions.References import NamedReference, Path
from Hql.Functions.make_list import make_list
from Hql.Types.Hql import HqlTypes as hqlt


def grouped_ctx(rows, *by):
    ctx = Context(data=Data([Table(init_data=rows, name='t')]))
    return ByExpression([NamedReference(x) for x in by]).eval(ctx)


ROWS = [{'n': 1, 'f': 2}, {'n': 3, 'f': 2}, {'n': 5, 'f': 6}, {'n': None, 'f': 6}]


def test_lists_values_per_group_and_skips_nulls():
    out = make_list([NamedReference('n')]).eval(grouped_ctx(ROWS, 'f'))

    table = out['t']
    assert table.df.columns == ['list_n']
    assert table.df['list_n'].to_list() == [[1, 3], [5]]
    assert isinstance(table.get_type(NamedReference('list_n')).strip(), hqlt.multivalue)


def test_max_size_caps_each_list():
    out = make_list([NamedReference('n'), Integer(1)]).eval(grouped_ctx(ROWS, 'f'))

    assert out['t'].df['list_n'].to_list() == [[1], [5]]


def test_nested_field_name_joins_path():
    rows = [{'p': {'q': 1}, 'f': 2}, {'p': {'q': 3}, 'f': 2}]
    field = Path([NamedReference('p'), NamedReference('q')])

    out = make_list([field]).eval(grouped_ctx(rows, 'f'))

    assert out['t'].df['list_p_q'].to_list() == [[1, 3]]


def test_collision_suffix_uses_base_name():
    rows = [{'n': 1, 'list_n': 2, 'list_n1': 3}]
    ctx = grouped_ctx(rows, 'list_n', 'list_n1')

    assert make_list([NamedReference('n')]).get_list_name(ctx.data['t'].agg).str() == 'list_n2'


def test_requires_an_aggregation():
    ctx = Context(data=Data([Table(init_data=ROWS, name='t')]))

    with pytest.raises(hqle.QueryException, match='aggregation function'):
        make_list([NamedReference('n')]).eval(ctx)


@pytest.mark.parametrize('args', [
    [StringLiteral('n')],
    [NamedReference('n'), Integer(0)],
    [NamedReference('n'), StringLiteral('5')],
])
def test_rejects_bad_arguments(args):
    with pytest.raises(hqle.ArgumentException):
        make_list(args)
