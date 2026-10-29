import math

import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Bool, Integer, StringLiteral
from Hql.Expressions.References import NamedReference
from Hql.Functions.hql_len import hql_len
from Hql.Functions.null import isnull
from Hql.Functions.series_stat import series_stats
from Hql.Functions.tolower import tolower


def make_ctx(rows):
    return Context(data=Data([Table(init_data=rows, name='t')]))


class TestToLower:
    def test_field(self):
        ctx = make_ctx([{'x': 'ABC'}, {'x': 'DeF'}])
        out = tolower([NamedReference('x')]).eval(ctx)
        assert out['t'].df['x'].to_list() == ['abc', 'def']

    def test_string_literal_preprocesses(self, empty_ctx):
        out = tolower([StringLiteral('AbÉ')]).preprocess(empty_ctx)
        assert out == StringLiteral('abé')

    def test_string_literal_eval_broadcasts(self):
        out = tolower([StringLiteral('ABC')]).eval(make_ctx([{'x': 1}]))
        assert out['t'].series.series.to_list() == ['abc']


class TestLen:
    def test_returns_only_lengths(self):
        ctx = make_ctx([{'l': [1, 2, 3], 'x': 'a'}, {'l': [4], 'x': 'b'}, {'l': [], 'x': 'c'}])
        out = hql_len([NamedReference('l')]).eval(ctx)
        assert out['t'].series.series.to_list() == [3, 1, 0]

    def test_skips_non_multivalue(self):
        ctx = make_ctx([{'x': 'a'}])
        out = hql_len([NamedReference('x')]).eval(ctx)
        assert len(out['t']) == 0
        assert not out['t'].series


class TestSeriesStats:
    def test_eval(self):
        ctx = make_ctx([{'n': 1}, {'n': 3}, {'n': 5}])
        out = series_stats([NamedReference('n')]).eval(ctx)

        row = out['t'].df.row(0, named=True)
        assert row['series_stats_n_min'] == 1
        assert row['series_stats_n_max'] == 5
        assert row['series_stats_n_avg'] == 3.0
        assert len(out['t']) == 3

    def test_ignore_nonfinite(self):
        ctx = make_ctx([{'n': 1.0}, {'n': math.inf}, {'n': 3.0}])
        out = series_stats([NamedReference('n'), Bool(True)]).eval(ctx)

        row = out['t'].df.row(0, named=True)
        assert row['series_stats_n_max'] == 3.0
        assert row['series_stats_n_avg'] == 2.0
        # stats still repeat across every source row
        assert len(out['t']) == 3

    def test_rejects_non_bool_flag(self):
        with pytest.raises(hqle.ArgumentException):
            series_stats([NamedReference('n'), Integer(1)])

    def test_rejects_third_argument(self):
        with pytest.raises(hqle.ArgumentException):
            series_stats([NamedReference('n'), Bool(True), Bool(True)])


class TestIsNull:
    def test_rejects_non_reference(self):
        with pytest.raises(hqle.ArgumentException):
            isnull([Integer(1)])

    def test_accepts_reference(self):
        isnull([NamedReference('x')])
