import polars as pl

from Hql.Expressions.References import NamedReference
from Hql.Functions.isnotempty import isnotempty


def keep(df, *names):
    expr = isnotempty([NamedReference(x) for x in names]).polars()
    return df.filter(expr)


def test_empty_string_is_empty():
    df = pl.DataFrame({'s': ['', 'hi', None]})
    assert keep(df, 's')['s'].to_list() == ['hi']


def test_non_string_only_checks_null():
    df = pl.DataFrame({'n': [0, None, 3]})
    assert keep(df, 'n')['n'].to_list() == [0, 3]


def test_all_arguments_must_be_non_empty():
    df = pl.DataFrame({'s': ['', 'hi', 'yo'], 'n': [1, None, 3]})
    assert keep(df, 's', 'n')['s'].to_list() == ['yo']
