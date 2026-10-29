import pytest

from Hql.Context import Context
from Hql.Data import Data
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import StringLiteral
from Hql.Expressions.References import NamedReference
from Hql.Functions.ip4subnet import ip4subnet


def bounds(rng):
    return rng.start.value, rng.end.value


def test_basic_range(empty_ctx):
    out = ip4subnet([StringLiteral('10.0.0.0/8')]).eval(empty_ctx)
    assert bounds(out) == (0x0A000000, 0x0AFFFFFF)


def test_slash_32_and_slash_0(empty_ctx):
    assert bounds(ip4subnet([StringLiteral('1.2.3.4/32')]).eval(empty_ctx)) == (0x01020304, 0x01020304)
    assert bounds(ip4subnet([StringLiteral('1.2.3.4/0')]).eval(empty_ctx)) == (0, 0xFFFFFFFF)


@pytest.mark.parametrize('subnet', [
    '10.0.0.0/123',   # previously read as /12
    '10.0.0.0/8junk',
    'x10.0.0.0/8',
    '10.0.0.0/33',
    '10.0.0.256/8',
    '10.0.0.0',
])
def test_invalid_subnets_raise(empty_ctx, subnet):
    with pytest.raises(hqle.QueryException):
        ip4subnet([StringLiteral(subnet)]).eval(empty_ctx)


def test_resolves_let_variable():
    ctx = Context(data=Data(), symbol_table={'s': StringLiteral('192.168.0.0/16')})
    out = ip4subnet([NamedReference('s')]).eval(ctx)
    assert bounds(out) == (0xC0A80000, 0xC0A8FFFF)
