from __future__ import annotations
from typing import Sequence, TYPE_CHECKING
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.Aggregation import OrderedExpression
    from Hql.Context import Context

class Sort(Operator):
    """Sort table rows by one or more ordered expressions."""

    _exprs: Sequence[OrderedExpression]

    def __init__(self, exprs:Sequence[OrderedExpression]):
        Operator.__init__(self)
        self.exprs = exprs

    @property
    def exprs(self) -> Sequence[OrderedExpression]:
        return self._exprs

    @exprs.setter
    def exprs(self, value:Sequence[Expression]) -> None:
        from Hql.Expressions.Aggregation import OrderedExpression
        from Hql.Exceptions import HqlExceptions as hqle

        new:list[OrderedExpression] = []
        for v in value:
            if not isinstance(v, OrderedExpression):
                raise hqle.CompilerException('Setting Sort exprs to non-OrderedExpression')
            new.append(v)
        self._exprs = new

    def deparse(self) -> str:
        return 'sort by ' + ', '.join(x.deparse() for x in self.exprs)

    def eval(self, ctx:Context) -> Context:
        exprs = []
        orders = []
        nulls = []
        for ordering in self.exprs:
            exprs.append(ordering.expr.polars())
            orders.append(ordering.order == 'desc')
            nulls.append(ordering.nulls == 'last')

        for table in ctx.data:
            table.sort(exprs, orders, nulls)

        return ctx
