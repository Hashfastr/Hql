from __future__ import annotations

from .Logic import LogicFunction
from Hql.Context import register_func
from typing import Optional, TYPE_CHECKING
# import copy

if TYPE_CHECKING:
    from Hql.Context import Context
    import polars as pl

@register_func('isnotempty')
class isnotempty(LogicFunction):
    """Build a predicate requiring every argument to be non-null and non-empty."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        # allows 1 to infinity args
        LogicFunction.__init__(self, args, 1, -1)

    @staticmethod
    def nonempty(series:pl.Series) -> pl.Series:
        import polars as pl

        # Empty strings count as empty, dtype is only known at runtime
        out = series.is_not_null()
        if series.dtype == pl.String:
            out = out & (series != '')
        return out

    def polars(self) -> pl.Expr:
        import polars as pl

        expr:pl.Expr = pl.lit(True)

        for i in self.args:
            cur = i.polars().map_batches(self.nonempty, return_dtype=pl.Boolean)
            expr = expr.and_(cur)

        return expr
        
    def eval(self, ctx: Context, receiver=None) -> Context:
        return NotImplemented

        # walling off for now, want to move this code implementation up
        # make this a proper logic function

        # might need to change this to duplcate the data
        # data = copy.deepcopy(ctx.data)
        # for i in data:
        #     i.filter(self.polars())
        # ctx.data = data
        # return ctx
