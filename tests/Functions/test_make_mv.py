from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Expressions.Aggregation import ByExpression
from Hql.Expressions.References import NamedReference
from Hql.Functions.make_mv import make_mv
from Hql.Types.Hql import HqlTypes as hqlt


def make_ctx():
    rows = [{'n': 1, 'f': 2}, {'n': 3, 'f': 2}, {'n': 5, 'f': 6}]
    return Context(data=Data([Table(init_data=rows, name='t')]))


def test_normal_eval_joins_fields_per_row():
    out = make_mv([NamedReference('n'), NamedReference('f')]).eval(make_ctx())

    table = out['t']
    assert table.df['mv'].to_list() == [[1, 2], [3, 2], [5, 6]]
    assert isinstance(table.get_type(NamedReference('mv')).strip(), hqlt.multivalue)


def test_normal_eval_as_value_returns_series_table():
    out = make_mv([NamedReference('n')]).eval(make_ctx(), as_value=True)

    assert out['t'].series.series.to_list() == [[1], [3], [5]]


def test_aggregate_eval_omits_group_keys():
    ctx = ByExpression([NamedReference('f')]).eval(make_ctx())

    out = make_mv([NamedReference('n')]).eval(ctx)

    table = out['t']
    assert table.df.columns == ['n']
    assert table.df['n'].to_list() == [[1, 3], [5]]
    assert isinstance(table.get_type(NamedReference('n')).strip(), hqlt.multivalue)
