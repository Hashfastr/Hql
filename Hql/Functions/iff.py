from __future__ import annotations
from . import Function
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Data import Data, Table
    from Hql.Expressions import Expression
    import polars as pl

'''
Picks between two values row by row on a predicate

datatable (a:string) ['0', '1']
| extend b = iff(a == '0', 'zero', a)

https://learn.microsoft.com/en-us/kusto/query/iff-function
'''
@register_func('iff')
class iff(Function):
    """Return the second argument where the predicate holds, otherwise the third."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 3, 3, conf)

    @property
    def cond(self) -> Expression:
        return self.args[0]

    @property
    def then(self) -> Expression:
        return self.args[1]

    @property
    def otherwise(self) -> Expression:
        return self.args[2]

    @staticmethod
    def values(expr:Expression, ctx:Context, table:Table) -> pl.Series:
        from Hql.Expressions.Literals import Literal
        from Hql.Expressions.References import Reference
        from Hql.Context import Context
        from Hql.Data import Data

        # Literals and references broadcast over the table's rows
        if isinstance(expr, (Literal, Reference)):
            return table.df.with_columns(__iff=expr.polars()).get_column('__iff')

        out = expr.eval(ctx)
        if isinstance(out, Context):
            out = out.data
        if not isinstance(out, Data) or table.name not in out.tables:
            raise hqle.QueryException(f'iff argument {expr.deparse()} did not eval to Data')

        # Functions hand back either a bare series or a single column table
        res = out.tables[table.name]
        if not res.series:
            res = res.strip()
        if not res.series:
            raise hqle.QueryException(f'iff argument {expr.deparse()} did not eval to a single value')
        return res.series.series

    def eval(self, ctx:Context, receiver=None) -> Data:
        import polars as pl
        from Hql.Data import Data, Series, Table

        tables = []
        for table in ctx.data:
            if not len(table.df):
                continue

            mask = table.df.select(self.cond.polars()).to_series()
            then = self.values(self.then, ctx, table)
            otherwise = self.values(self.otherwise, ctx, table)

            series = pl.select(pl.when(mask).then(then).otherwise(otherwise)).to_series()
            tables.append(Table(name=table.name, series=Series(series)))

        return Data(tables=tables)
