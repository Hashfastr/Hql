from __future__ import annotations

from .Logic import LogicFunction
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

'''
Whether a field is present and not null, as for Sigma's |exists.
A missing field is false rather than a missing column error.

| where exists(CommandLine)
| where not(exists(['properties.message']))
'''
@register_func('exists')
class exists(LogicFunction):
    """Test whether a field is present and not null."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.References import Reference

        LogicFunction.__init__(self, args, 1, 1, conf=conf)
        if not isinstance(args[0], Reference):
            raise hqle.ArgumentException(f'exists takes a field, got {type(args[0]).__name__}')
        self.path = args[0].list()

    def walk(self, series:pl.Series) -> pl.Series:
        import polars as pl

        # Down the rest of the path through structs, null where it doesn't go
        for name in self.path[1:]:
            if series.dtype != pl.Struct or name not in series.struct.fields:
                return pl.Series([None] * len(series), dtype=pl.Null)
            series = series.struct.field(name)
        return series

    def polars(self) -> pl.Expr:
        import polars as pl
        import polars.selectors as cs

        # Selects the column only if it's there, so a missing one is false, not an error.
        # Works on dynamic (Object) columns too, which can't go in a struct.
        expr = cs.by_name(self.path[0], require_all=False)
        if len(self.path) > 1:
            expr = expr.map_batches(self.walk)
        return pl.any_horizontal(expr.is_not_null())

    def deparse(self) -> str:
        return f'exists({self.args[0].deparse()})'
