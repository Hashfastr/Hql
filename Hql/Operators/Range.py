from __future__ import annotations
from typing import TYPE_CHECKING, Union
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.References import NamedReference
    from Hql.Context import Context

'''
Generates a single-column table of values

range x from 1 to 5 step 1

https://learn.microsoft.com/en-us/kusto/query/range-operator
'''
class Range(Operator):
    """Generate a single-column table over a numeric range."""

    def __init__(self, name:NamedReference, start:Expression, end:Expression, step:Expression):
        Operator.__init__(self)
        self.name:NamedReference = name
        self.start = start
        self.end = end
        self.step = step
        self.tabular = True

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'name': self.name.to_dict(),
            'start': self.start.to_dict(),
            'end': self.end.to_dict(),
            'step': self.step.to_dict(),
        }

    def deparse(self) -> str:
        name = self.name.deparse()
        start = self.start.deparse()
        end = self.end.deparse()
        step = self.step.deparse()

        return f'range {name} from {start} to {end} step {step}'

    @staticmethod
    def get_number(expr:Expression, label:str) -> Union[int, float]:
        from Hql.Expressions.Literals import Literal
        from Hql.Exceptions import HqlExceptions as hqle

        value = expr.value if isinstance(expr, Literal) else None

        # bool is a subclass of int, don't let it through
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise hqle.CompilerException(f'Range given invalid {label} value {expr.deparse()}')

        return value

    def eval(self, ctx:Context, **kwargs) -> Context:
        from math import floor
        from numpy import arange
        from polars import Series, Int64, Float64
        from Hql.Data import Data, Table
        from Hql.PolarsTools import pltools
        from Hql.Exceptions import HqlExceptions as hqle

        ctx = ctx.copy()

        name = self.name.list()
        start = self.get_number(self.start, 'start')
        end = self.get_number(self.end, 'end')
        step = self.get_number(self.step, 'step')

        if step == 0:
            raise hqle.QueryException('Range step cannot be 0')

        # Inclusive of end, empty if the step moves away from end.
        # Small epsilon absorbs float error, e.g. 0 to 1 step 0.1
        count = max(floor((end - start) / step + 1e-9) + 1, 0)
        values = start + arange(count) * step

        if all(isinstance(x, int) for x in (start, end, step)):
            series = Series(values, dtype=Int64)
        else:
            series = Series(values, dtype=Float64)

        df = pltools.build_element(name, series)
        ctx.data = Data(tables=[Table(df=df, name='range')])

        return ctx
