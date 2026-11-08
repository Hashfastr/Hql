import polars as pl

from Hql.Expressions.References import NamedReference, Path
from Hql.Functions.exists import exists


def frame():
    df = pl.DataFrame({'a': [1, None, 3], 's': [{'b': 1}, {'b': None}, None]})
    # dynamic columns from Log Analytics are polars Objects, which can't go in a struct
    return df.with_columns(o=pl.Series([{'x': 1}, None, 2], dtype=pl.Object))


def matches(ref):
    expr = exists([ref]).polars()
    df = frame()
    return df.filter(expr)['a'].to_list(), df.filter(~expr)['a'].to_list()


def test_present_column():
    assert matches(NamedReference('a')) == ([1, 3], [None])


def test_missing_column_is_false_not_an_error():
    assert matches(NamedReference('missing')) == ([], [1, None, 3])


def test_object_column():
    assert matches(NamedReference('o')) == ([1, 3], [None])


def test_nested_path():
    assert matches(Path([NamedReference('s'), NamedReference('b')])) == ([1], [None, 3])
    assert matches(Path([NamedReference('s'), NamedReference('nope')])) == ([], [1, None, 3])
    assert matches(Path([NamedReference('a'), NamedReference('x')])) == ([], [1, None, 3])
