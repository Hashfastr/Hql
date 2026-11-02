from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func, Context
from typing import TYPE_CHECKING, Optional, Sequence, Union

@register_func('service')
class service(Function):
    """Select configured source services for an analytic query."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, -1)

        self.names:Sequence[Union[StringLiteral, Reference]] = []
        for i in self.args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.QueryException(f"Invalid argument type passed to function service {type(i)}")
            self.names.append(i)
        
    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Hac.Sources import Source
        from Hql.Expressions.Literals import StringLiteral
        
        src = receiver if receiver else Source(ctx)

        if not isinstance(src, Source):
            raise hqle.CompilerException(f'Expected Source got {type(src)} for service preprocess')

        for i in self.names:
            name = i.preprocess(ctx)
            if not isinstance(name, StringLiteral):
                raise hqle.QueryException(f"Invalid argument type passed to function service {type(i)}")
            src.service(name.str())

        return src
