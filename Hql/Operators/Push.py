from Hql.Operators import Operator
from Hql.Context import Context
from Hql.Expressions import Expression
from typing import Sequence, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from Hql.Operators import Database

class Push(Operator):
    """Push the current data to configured database targets."""

    def __init__(self, exprs:Sequence[Expression]):
        Operator.__init__(self)
        self.exprs = exprs
        self.dbs:list[Database] = []

    def deparse(self) -> str:
        return 'push ' + ', '.join([x.deparse() for x in self.exprs])

    def eval(self, ctx:'Context', **kwargs) -> 'Context':
        for i in self.dbs:
            if not i.can_push:
                logging.error(f'Cannot push to DB {i.name}')
                continue

            i.push(ctx)

        return ctx
