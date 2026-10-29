from __future__ import annotations
from .Logic import LogicFunction
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func

import polars as pl
from typing import Optional

@register_func('isnull')
class isnull(LogicFunction):
    """Build a predicate that tests a referenced field for null."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.References import Reference
        LogicFunction.__init__(self, args, 1, 1)

        expr = args[0]
        if not isinstance(expr, Reference):
            raise hqle.ArgumentException(f'Invalid argument type to isnull: {type(expr)}')
        self.expr:Reference = expr

        self.logic = True

    def polars(self) -> pl.Expr:
        # args may be rewritten by the compiler, so don't use self.expr
        expr = self.args[0].polars()
        return expr.is_null()
