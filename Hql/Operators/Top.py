from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Sequence, Union
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.Literals import Integer
    from Hql.Expressions.Aggregation import ByExpression, OrderedExpression
    from Hql.Context import Context

'''
Give the top, or bottom, x values for a given field in a dataframe

range x from 1 to 100 step 2
| top 5 by x desc

99
97
95
93
91

Preserves the other fields as well

https://learn.microsoft.com/en-us/kusto/query/top-operator
'''
class Top(Operator):
    """Retain the first rows after sorting by an ordered expression."""

    def __init__(self, expr:Integer, by:Union[OrderedExpression, ByExpression, Sequence[OrderedExpression]]):
        Operator.__init__(self)
        self._expr:Integer = expr
        self.by:list[OrderedExpression] = self.normalize_by(by)

    # The grammar gives a single OrderedExpression, older callers a ByExpression
    @staticmethod
    def normalize_by(by) -> list[OrderedExpression]:
        from Hql.Expressions.Aggregation import ByExpression, OrderedExpression
        from Hql.Exceptions import HqlExceptions as hqle

        if isinstance(by, OrderedExpression):
            return [by]

        if isinstance(by, ByExpression):
            return [OrderedExpression(x) for x in by.exprs]

        out = []
        for i in by:
            if not isinstance(i, OrderedExpression):
                raise hqle.CompilerException(f'Top given non-OrderedExpression by clause {type(i)}')
            out.append(i)
        return out

    @property
    def expr(self) -> Integer:
        expr = self._expr
        assert expr
        return expr

    @expr.setter
    def expr(self, value:Optional[Expression]) -> None:
        from Hql.Expressions.Literals import Integer
        from Hql.Exceptions import HqlExceptions as hqle

        if value is None or not isinstance(value, Integer):
            raise hqle.CompilerException('Setting Top expression to non-Integer')
        self._expr = value

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'quota': self.expr.to_dict(),
            'by': [x.to_dict() for x in self.by]
        }

    def deparse(self) -> str:
        return f'top {self.expr.deparse()} by ' + ', '.join(x.deparse() for x in self.by)

    def eval(self, ctx:Context) -> Context:
        from Hql.Exceptions import HqlExceptions as hqle

        limit = self.expr.value
        if limit < 0:
            raise hqle.QueryException(f'Top given negative limit {limit}')

        exprs = []
        orders = []
        nulls = []
        for ordering in self.by:
            exprs.append(ordering.expr.polars())
            orders.append(ordering.order == 'desc')
            nulls.append(ordering.nulls == 'last')

        ctx = self.copy_tables(ctx)
        for table in ctx.data:
            table.sort(exprs, orders, nulls)
            table.truncate(limit)
        return ctx
