from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Optional
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.Aggregation import ByExpression
    from Hql.Context import Context

class Summarize(Operator):
    """Aggregate input data, optionally grouped by reference expressions."""

    def __init__(self, aggregate_exprs:Sequence[Expression], by_expr:Optional[ByExpression]):
        Operator.__init__(self)
        self.aggregate_exprs = aggregate_exprs
        self.by_expr = by_expr

    def deparse(self) -> str:
        out = 'summarize'

        if self.aggregate_exprs:
            out += ' ' + ', '.join(i.deparse() for i in self.aggregate_exprs)

        if self.by_expr:
            out += ' ' + self.by_expr.deparse()

        return out

    # Placeholder group key used to aggregate a whole table when there's no by
    ALL_KEY = '__hql_summarize_all__'

    def group_all(self, ctx:Context) -> Context:
        from polars import lit
        from Hql.Data import Schema
        from Hql.Expressions.References import NamedReference

        ctx = self.copy_tables(ctx)
        for table in ctx.data:
            table.agg = table.df.group_by(lit(True).alias(self.ALL_KEY))
            table.agg_paths = [NamedReference(self.ALL_KEY)]
            table.agg_schema = Schema()
        return ctx

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data, Table
        from Hql.Expressions.References import NamedReference

        if self.by_expr is not None:
            ctx = self.by_expr.eval(ctx)
        else:
            ctx = self.group_all(ctx)

        agg_data = []
        for expr in self.aggregate_exprs:
            agg_data.append(expr.eval(ctx))

        new = []
        for table in ctx.data:
            # Without a by there are no key columns to keep
            if self.by_expr is None:
                new.append(Table(name=table.name))
                continue
            table = Table(table.agg.agg(), schema=table.agg_schema, name=table.name)
            new.append(table)

        ctx.data = Data.merge([Data(tables=new)] + agg_data)

        if self.by_expr is None:
            key = NamedReference(self.ALL_KEY)
            for table in ctx.data:
                if self.ALL_KEY in table.df.columns:
                    table.drop(key)

        return ctx
