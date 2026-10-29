from __future__ import annotations
from typing import TYPE_CHECKING
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions import ToClause

class Rename(Operator):
    """Rename input tables according to a list of clauses."""

    def __init__(self, exprs:list[ToClause]):
        Operator.__init__(self)
        self.exprs = exprs

    def deparse(self) -> str:
        exprs = []
        for i in self.exprs:
            assert i.to is not None
            exprs.append(f'{i.expr.deparse()} to {i.to.deparse()}')
        return 'rename ' + ', '.join(exprs)

    def eval(self, ctx:Context, **kwargs) -> Context:
        from copy import copy
        from Hql.Data import Data
        from Hql.Expressions.References import Reference
        from Hql.Exceptions import HqlExceptions as hqle

        tables = dict(ctx.data.tables)
        for i in self.exprs:
            if not isinstance(i.to, Reference):
                raise hqle.CompilerException(f'Rename given non-reference destination {type(i.to)}')
            src = i.expr.str()
            dst = i.to.str()

            if src in tables:
                # Copy so the source context's table keeps its name
                table = copy(tables.pop(src))
                table.name = dst
                tables[dst] = table

        ctx = ctx.copy()
        ctx.data = Data()
        ctx.data.tables = tables
        return ctx
