from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import ToClause
    from Hql.Expressions.Literals import Integer
    from Hql.Context import Context
    from Hql.Data import Table

class MvExpand(Operator):
    """Expand multivalue fields into individual rows."""

    def __init__(self, exprs:list[ToClause], limit:Optional[Integer]=None):
        Operator.__init__(self)
        self.exprs = exprs
        self.limit = limit

    @property
    def to_clauses(self) -> list[ToClause]:
        from Hql.Expressions import ToClause

        out:list[ToClause] = []
        for e in self.exprs:
            assert isinstance(e, ToClause)
            out.append(e)
        return out

    def explode_table(self, table:Table, limit:int):
        from Hql.Types.Hql import HqlTypes as hqlt
        from Hql.Data import Table

        schema = table.schema
        df = table.df

        for to in self.to_clauses:
            path = to.expr.list()
            pl_expr = to.expr.polars()

            to_schema = schema.get_type(path).schema

            # Short circuit case
            if not isinstance(to_schema, hqlt.multivalue):
                continue

            new_type = to_schema.inner
            # need to fix the typing on this
            df = df.with_columns(
                pl_expr.list.slice(0, limit)
            ).explode(pl_expr)

            if to.to:
                new_type = to.to

            schema.set(path, new_type)

        return Table(df=df, schema=schema, name=table.name)

    def deparse(self) -> str:
        out = 'mvexpand '

        exprs = []
        for i in self.exprs:
            exprs.append(i.deparse())
        out += ', '.join(exprs)

        if self.limit:
            out += ' '
            out += self.limit.deparse()

        return out

    def eval(self, ctx:Context):
        from Hql.Data import Data

        ctx = ctx.copy()

        # Long literal, just get us the number
        limit = -1
        if self.limit:
            limit = self.limit.value

        new = []
        for table in ctx.data:
            new.append(self.explode_table(table, limit))

        ctx.data = Data(tables=new)
        return ctx
