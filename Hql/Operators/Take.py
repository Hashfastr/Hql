from __future__ import annotations
from typing import TYPE_CHECKING
from Hql.Operators.Operator import Operator
from Hql.Expressions.Literals import Integer

if TYPE_CHECKING:
    from Hql.Expressions.References import NamedReference
    from Hql.Context import Context

# Take, limits the number of results given an integer
# Ensures that only integers are given, if not then errors
# The implementation algorithm is just grab the first n rows.
#
# https://learn.microsoft.com/en-us/kusto/query/take-operator
class Take(Operator):
    """Limit the number of rows retained from selected tables."""

    def __init__(self, limit:Integer, tables:list[NamedReference]):
        Operator.__init__(self)
        self._expr:Integer = limit
        self.tables = tables

    @property
    def expr(self) -> Integer:
        expr = self._expr
        assert isinstance(expr, Integer)
        return expr

    @expr.setter
    def expr(self, value):
        assert isinstance(value, Integer)
        self._expr = value

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'limit': self.expr.to_dict(),
            'tables': [x.to_dict() for x in self.tables]
        }

    def get_limits(self):
        limit = self.expr.value
        tables = [x.str() for x in self.tables]

        return {
            'limit': limit,
            'tables': tables
        }

    def deparse(self) -> str:
        out = 'take ' + self.expr.deparse()

        if self.tables:
            out += ' from '
            exprs = []
            for i in self.tables:
                exprs.append(i.deparse())
            out += ', '.join(exprs)

        return out

    '''
    Takes only so many results for each table.

    If given the parameter global=True then it will limit results such that
    the sum of all tables is less than or equal to the take amount.
    Unimplemented.
    '''
    def eval(self, ctx:Context):
        from Hql.Exceptions import HqlExceptions as hqle

        limit = self.expr.value
        if limit < 0:
            raise hqle.QueryException(f'Take given negative limit {limit}')

        ctx = self.copy_tables(ctx)

        table_names = []
        for i in self.tables:
            table_names.append(i.str())

        if not table_names:
            table_names.append('*')

        for i in table_names:
            tables = ctx.data.get_tables(i)
            for j in tables:
                j.truncate(limit)

        return ctx
