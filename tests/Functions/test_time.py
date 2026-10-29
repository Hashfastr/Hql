import datetime

import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Datetime, Integer, StringLiteral
from Hql.Functions.time import ago, now, parse_timespan


@pytest.mark.parametrize('text, expected', [
    ('1h', datetime.timedelta(hours=1)),
    ('3hr', datetime.timedelta(hours=3)),
    ('30min', datetime.timedelta(minutes=30)),
    ('5m', datetime.timedelta(minutes=5)),
    ('2s', datetime.timedelta(seconds=2)),
    ('10ms', datetime.timedelta(milliseconds=10)),
    ('1.5days', datetime.timedelta(days=1.5)),
    ('7d', datetime.timedelta(days=7)),
])
def test_parse_timespan(text, expected):
    assert parse_timespan(text) == expected


def test_parse_timespan_rejects_garbage():
    with pytest.raises(hqle.ArgumentException):
        parse_timespan('1 fortnight')


def test_ago_returns_datetime_in_the_past(empty_ctx):
    before = datetime.datetime.now()
    out = ago([StringLiteral('1h')]).preprocess(empty_ctx)
    after = datetime.datetime.now()

    assert isinstance(out, Datetime)
    assert before - datetime.timedelta(hours=1) <= out.value <= after - datetime.timedelta(hours=1)


def test_ago_rejects_non_timespan(empty_ctx):
    with pytest.raises(hqle.ArgumentException):
        ago([Integer(5)]).preprocess(empty_ctx)


def test_ago_and_now_broadcast_in_eval():
    ctx = Context(data=Data([Table(init_data=[{'x': 1}], name='t')]))
    assert isinstance(ago([StringLiteral('1d')]).eval(ctx), Data)
    assert isinstance(now([]).eval(ctx), Data)
