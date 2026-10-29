import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Expressions.Literals import Float, Integer, Null, StringLiteral
from Hql.Expressions.References import NamedReference
from Hql.Functions.typecasting import todouble, tofloat, toint, tostring
from Hql.Types.Hql import HqlTypes as hqlt


def make_ctx():
    rows = [{'b': 'abc'}, {'b': '7'}, {'b': '1.5'}]
    return Context(data=Data([Table(init_data=rows, name='t')]))


def column(data, name='b'):
    return data['t'].df[name].to_list()


class TestStringLiteralCasts:
    def test_toint_string_literal_preprocesses(self, empty_ctx):
        assert toint([StringLiteral('5')]).preprocess(empty_ctx) == Integer(5)

    def test_toint_string_literal_eval_broadcasts(self):
        out = toint([StringLiteral('5')]).eval(make_ctx())
        assert out['t'].series.series.to_list() == [5]

    def test_unconvertible_literal_is_null(self, empty_ctx):
        assert isinstance(toint([StringLiteral('abc')]).preprocess(empty_ctx), Null)

    def test_tostring_integer_literal(self, empty_ctx):
        assert tostring([Integer(5)]).preprocess(empty_ctx) == StringLiteral('5')


class TestFieldCasts:
    def test_toint_nulls_unconvertible_values(self):
        out = toint([NamedReference('b')]).eval(make_ctx()).data
        assert column(out) == [None, 7, None]

    def test_todouble_nulls_unconvertible_values(self):
        out = todouble([NamedReference('b')]).eval(make_ctx()).data
        assert column(out) == [None, 7.0, 1.5]


class TestToFloat:
    def test_tofloat_is_64_bit(self):
        assert isinstance(tofloat([Float(1.1)]).cast_type, hqlt.double)

    def test_tofloat_keeps_precision(self, empty_ctx):
        assert tofloat([Float(1.1)]).preprocess(empty_ctx).value == pytest.approx(1.1, abs=1e-12)
