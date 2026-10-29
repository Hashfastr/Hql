from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Expressions.Aggregation import ByExpression
from Hql.Expressions.References import NamedReference
from Hql.Functions.count import count


def grouped_ctx(rows, *by):
    ctx = Context(data=Data([Table(init_data=rows, name='t')]))
    return ByExpression([NamedReference(x) for x in by]).eval(ctx)


def test_default_name():
    ctx = grouped_ctx([{'f': 1}, {'f': 1}, {'f': 2}], 'f')
    out = count([]).eval(ctx)
    assert out['t'].df.columns == ['count_']
    assert out['t'].df['count_'].to_list() == [2, 1]


def test_collision_suffix_uses_base_name():
    rows = [{'count_': 1, 'count_1': 2}]
    ctx = grouped_ctx(rows, 'count_', 'count_1')

    name = count([]).get_count_name(ctx.data['t'].agg)

    # previously appended to the already-suffixed name (count_12)
    assert name.str() == 'count_2'
