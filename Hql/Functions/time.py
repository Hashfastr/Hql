from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from . import Function
from Hql.Context import register_func

if TYPE_CHECKING:
    from Hql.Context import Context

'''
Static function, can be precomputed
Generates a time delta
'''
@register_func('ago')
class ago(Function):
    """Return a duration used to address a time in the past."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        Function.__init__(self, args, 1, 1)
        val = args[0]
        assert isinstance(val, StringLiteral)
        self.delta = val

    def preprocess(self, ctx: Context, receiver=None) -> object:
        
        return self.delta

'''
Static function, can be precomputed
Generates a time delta
'''
@register_func('now')
class now(Function):
    """Return a duration used to address a time in the past."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        import datetime
        Function.__init__(self, args, 0, 0)
        self.time = datetime.datetime.now()

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import Datetime
        return Datetime(self.time)
