from __future__ import annotations
from typing import Optional, TYPE_CHECKING
import datetime
import re
from . import Function
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Context import Context

# Matches the TIMESPANLITERAL grammar, e.g. 1h, 30min, 1.5days, 10ms
_timespan_units = [
    ('microseconds', r'micro(s((ec(ond)?)?s?)?)?'),
    ('milliseconds', r'ms|milli(s((ec(ond)?)?s?)?)?'),
    ('minutes', r'm(in(ute)?s?)?'),
    ('seconds', r's(ec(ond)?s?)?'),
    ('hours', r'h((our|r)s?)?'),
    ('days', r'd(ays?)?'),
]

def parse_timespan(text:str) -> datetime.timedelta:
    for unit, pat in _timespan_units:
        match = re.fullmatch(rf'(?P<value>\d+(\.\d+)?)\s*(?:{pat})', text.strip())
        if match:
            return datetime.timedelta(**{unit: float(match.group('value'))})
    raise hqle.ArgumentException(f'Invalid timespan given to ago: {text}')

'''
Static function, can be precomputed
Generates a datetime the given timespan before now
'''
@register_func('ago')
class ago(Function):
    """Return the datetime a duration before the current time."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 1, 1)
        self.delta = args[0]

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import Datetime, StringLiteral, TimeDelta

        delta = self.delta.preprocess(ctx)

        if isinstance(delta, TimeDelta):
            delta = delta.delta
        elif isinstance(delta, StringLiteral):
            delta = parse_timespan(delta.value.decode('utf-8'))
        else:
            raise hqle.ArgumentException(f'ago expects a timespan, got {type(delta)}')

        return Datetime(datetime.datetime.now() - delta)

    def eval(self, ctx: Context, receiver=None) -> object:
        return self.broadcast(ctx, self.preprocess(ctx))

'''
Static function, can be precomputed
Generates a time delta
'''
@register_func('now')
class now(Function):
    """Return a duration used to address a time in the past."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 0, 0)
        self.time = datetime.datetime.now()

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import Datetime
        return Datetime(self.time)

    def eval(self, ctx: Context, receiver=None) -> object:
        return self.broadcast(ctx, self.preprocess(ctx))
