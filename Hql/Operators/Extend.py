from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Union
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.References import NamedExpression, Reference
    from Hql.Context import Context

# Creates a field with a value in the extend
#
# StormEvents
# | project EndTime, StartTime
# | extend Duration = EndTime - StartTime
#
# https://learn.microsoft.com/en-us/kusto/query/extend-operator
class Extend(Operator):
    """Add or replace fields using named expressions."""

    _exprs: Sequence[Union[Reference, NamedExpression]]

    def __init__(self, exprs:Sequence[Union[Reference, NamedExpression]]):
        Operator.__init__(self)
        self.exprs = exprs

    @property
    def exprs(self) -> Sequence[Union[Reference, NamedExpression]]:
        return self._exprs

    @exprs.setter
    def exprs(self, value:Sequence[Expression]) -> None:
        from Hql.Expressions.References import NamedExpression, Reference
        from Hql.Exceptions import HqlExceptions as hqle

        new:list[Union[Reference, NamedExpression]] = []
        for v in value:
            if not isinstance(v, (Reference, NamedExpression)):
                raise hqle.CompilerException('Setting Extend exprs to non-Reference/NamedExpression')
            new.append(v)
        self._exprs = new

    def deparse(self) -> str:
        return 'extend ' + ', '.join(x.deparse() for x in self.exprs)

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data
        from Hql.Expressions.References import NamedExpression

        ctx = ctx.copy()
        orig:Data = ctx.data
        data:list[Data] = []

        for i in self.exprs:
            # skip just references if they exist, base case
            if isinstance(i, NamedExpression):
                datum = i.eval(ctx, insert=False, unnest=False).data
                data.append(datum)

                for j in i.paths:
                    orig = orig.drop(j)

        # orig is now a subset of the original with all assignments replaced
        data.append(orig)
        ctx.data = Data.merge(data)

        return ctx
