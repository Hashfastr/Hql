from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Union, Optional
from Hql.Operators.Operator import Operator
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.Logic import Logic
    from Hql.Expressions import OpParameter
    from Hql.Context import Context

# Where operator
# Essentially just a field filter, can hold a number of expressions, even nested ones.
# Can also take a number of parameters, although I'm not sure what they are
# but they can exist.
# https://learn.microsoft.com/en-us/kusto/query/where-operator
class Where(Operator):
    """Filter table rows using a logical expression."""

    # Pass in the parser context here for helpful debugging
    def __init__(self, expr:Logic, params:Union[None, list[OpParameter]]=None):
        Operator.__init__(self)
        self.parameters = params if params else []
        self._expr:Logic = expr

    @property
    def expr(self) -> Logic:
        expr = self._expr
        assert expr
        return expr

    @expr.setter
    def expr(self, value:Optional[Expression]) -> None:
        from Hql.Expressions.Logic import Logic

        if value is None or not isinstance(value, Logic):
            raise hqle.CompilerException('Setting Where expression to non-Logic')
        self._expr = value

    def deparse(self) -> str:
        out = 'where '

        if self.parameters:
            exprs = []
            for i in self.parameters:
                exprs.append(i.deparse())
            out += ' '.join(exprs)
            out += ' '

        out += self.expr.deparse()
        return out

    def split_by_length(self, max_length:int=80) -> list[Where]:
        from Hql.Expressions.Logic import BinaryLogic

        expr = self.expr
        if max_length < 0 or not isinstance(expr, BinaryLogic):
            return [self]

        splits = expr.split_by_length(max_length=max_length)

        return [Where(x, self.parameters) for x in splits]

    def integrate(self, op: Operator):
        from Hql.Expressions.Logic import BinaryLogic

        if not isinstance(op, Where):
            return op

        self.expr = BinaryLogic([self.expr, op.expr], logic_and=True)
        return None

    '''
    Applies a polars filter expression
    If there is a field reference error, the filter does not apply to that table
    so drop it
    '''
    def eval(self, ctx:Context) -> Context:
        from polars.exceptions import StructFieldNotFoundError
        from Hql.Data import Data

        pl_filter = self.expr.polars()

        ctx = self.copy_tables(ctx)

        new = []
        for table in ctx.data:
            try:
                table.filter(pl_filter)
                new.append(table)
            except hqle.UnreferencedFieldException as e:
                logging.warning(e)
            # Missing sub-field of an existing struct, e.g. n.zz
            except StructFieldNotFoundError as e:
                logging.warning(e)

        ctx.data = Data(new)
        return ctx
