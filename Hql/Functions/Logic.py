from typing import Sequence, Optional
from Hql.Expressions.Logic import Logic
from Hql.Expressions import Expression
from Hql.Context import Context
from . import Function

class LogicFunction(Function, Logic):
    def __init__(self, args: Sequence[Expression], min: int, max: int, conf: Optional[dict] = None):
        Function.__init__(self, args, min, max, conf)
        self.type = 'LogicFunction'

    def eval(self, ctx:Context, receiver=None) -> Context:
        return NotImplemented
