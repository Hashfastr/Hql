from __future__ import annotations
from Hql.Functions import Function
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import StringLiteral
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from Hql.Context import Context

@register_func('wide')
class wide(Function):
    """Encode a string value as little-endian UTF-16 bytes."""

    def __init__(self, args: list, conf:Optional[dict]=None):
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, 1)

        val = args[0]
        if not isinstance(val, (Reference, StringLiteral)):
            raise hqle.ArgumentException(f'Invalid argument type {type(args[0])} passed to {self.name}')
            
        self.val:Union[StringLiteral, Reference] = args[0]

    def preprocess(self, ctx: Context, receiver=None) -> object:
        val = self.val.preprocess(ctx)
        if not isinstance(val, StringLiteral):
            raise hqle.ArgumentException(f'Invalid argument type {type(val)} passed to {self.name}') 

        # Use the raw value, str() gives the escaped form
        raw = val.value.decode('utf-8').encode('utf-16le')
        return StringLiteral(raw)

    def eval(self, ctx: Context, receiver=None) -> object:
        import polars as pl
        from Hql.Data import Series
        from Hql.Types.Hql import HqlTypes as hqlt

        # UTF-16 bytes aren't valid UTF-8 in general, so keep them binary
        wide = self.preprocess(ctx)
        assert isinstance(wide, StringLiteral)
        series = Series(pl.Series([wide.value], dtype=pl.Binary), hqlt.binary())
        return self.broadcast(ctx, series)
