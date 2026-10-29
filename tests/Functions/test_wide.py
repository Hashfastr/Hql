import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Expressions.References import NamedReference
from Hql.Functions.wide import wide


def test_ascii(empty_ctx):
    out = wide([StringLiteral('hi')]).preprocess(empty_ctx)
    assert out.value == 'hi'.encode('utf-16le')


def test_non_ascii(empty_ctx):
    out = wide([StringLiteral('é')]).preprocess(empty_ctx)
    assert out.value == b'\xe9\x00'


def test_backslash_not_escaped(empty_ctx):
    out = wide([StringLiteral('a\\b')]).preprocess(empty_ctx)
    assert out.value == 'a\\b'.encode('utf-16le')


def test_resolves_let_variable():
    ctx = Context(data=Data(), symbol_table={'v': StringLiteral('hi')})
    assert wide([NamedReference('v')]).preprocess(ctx).value == 'hi'.encode('utf-16le')


def test_rejects_non_string():
    with pytest.raises(hqle.ArgumentException):
        wide([Integer(1)])


def test_eval_returns_data():
    ctx = Context(data=Data([Table(init_data=[{'x': 1}], name='t')]))
    out = wide([StringLiteral('é')]).eval(ctx)
    assert isinstance(out, Data)
    assert out['t'].series.series.to_list() == [b'\xe9\x00']
