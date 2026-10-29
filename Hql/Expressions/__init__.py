from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Union
from Hql.Exceptions import HqlExceptions as hqle

from .__proto__ import Expression

'''
from .Logic import Logic, Comparator, Equality, Substring
from .Logic import Relational, BetweenEquality, BinaryLogic
from .Logic import BasicRange, Regex, Not

from .References import Reference, NamedReference, Wildcard
from .References import EscapedNamedReference, Path, NamedExpression

from .Literals import Literal, TypeExpression, StringLiteral
from .Literals import MultiString, Integer, IP4, Float, Bool
from .Literals import Multivalue, Datetime, Null

from .Functions import FuncProto, FuncExpr, DotFuncExpr

from .Aggregation import OrderedExpression, ByExpression
'''

if TYPE_CHECKING:
    from Hql.Operators.Operator import Operator
    from Hql.Database import Database
    from Hql.Types.Hql import HqlTypes as hqlt
    from Hql.Context import Context
    from Hql.Expressions.References import Reference
    from Hql.Expressions.Literals import TypeExpression 
    from Hql.Functions import Function, DotCompositeFunction
    from Hql.Compiler.InstructionSet import InstructionSet
    from Hql.Operators.Union import Union as HqlUnion

PrepipeType = Union['Function', 'DotCompositeFunction', 'Database', 'HqlUnion', Expression]

class PipeExpression(Expression):
    """Represent a query source followed by a sequence of pipe operators."""

    def __init__(self, pipes:list[Operator], prepipe:Optional[PrepipeType]=None):
        Expression.__init__(self)
        self.prepipe              = prepipe
        self.pipes:list[Operator] = pipes

    def __bool__(self):
        return bool(self.prepipe) or bool(self.pipes)

    def preprocess(self, ctx: Context) -> Union[PipeExpression, InstructionSet]:
        from Hql.Compiler.InstructionSet import InstructionSet
        from Hql.Functions import Function, DotCompositeFunction
        from Hql.Database import Database
        from Hql.Hac.Sources import Source
        from Hql.Operators.Union import Union as HqlUnion

        pipes = []
        for i in self.pipes:
            pipes.append(i.preprocess(ctx))
        self.pipes = pipes

        if self.prepipe:
            prepipe = self.prepipe.preprocess(ctx)

            if isinstance(prepipe, Source):
                prepipe = prepipe.preprocess(ctx)

            if not isinstance(prepipe, (Function, DotCompositeFunction, Database, Expression, HqlUnion)):
                if isinstance(prepipe, InstructionSet):
                    iset = InstructionSet(prepipe, pipes)
                    return iset

                raise hqle.QueryException(f'Invalid prepipe following preprocess: {type(prepipe)}')
            self.prepipe = prepipe

        return self
        
    def to_dict(self):
        d:dict = {
            'type': self.type,
        }
        
        if self.prepipe:
            d['prepipe'] = self.prepipe.to_dict()

        d['pipes'] = [x.to_dict() for x in self.pipes]

        return d

    def deparse(self) -> str:
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BinaryLogic
        # print(self.prepipe.exprs)
        prepipe = self.prepipe.deparse() if self.prepipe else ''

        def dp(ops:Sequence[Operator]) -> list[str]:
            out:list[str] = []
            for i in ops:
                # if isinstance(i, Where):
                #     if isinstance(i.expr, BinaryLogic) and len(i.expr) > 1 and not i.expr.logic_and:
                #         print('morgan')
                #         i.expr = i.expr.demorgan()
                #     split = i.split_by_length()
                #     out += [x.deparse() for x in split]
                # else:
                out.append(i.deparse())
            # print([type(x) for x in out])
            return out

        out = prepipe
        for i in dp(self.pipes):
            # print(i)
            # print(type(i))
            # print(out)
            if out:
                out += '\n'
            out += f'| {i}'

        return out

class OpParameter(Expression):
    """Represent a named parameter passed to a pipe operator."""

    def __init__(self, name:Reference, value:Expression):
        Expression.__init__(self)
        self.name = name
        self.value = value

    def deparse(self) -> str:
        name = self.name.deparse()
        value = self.value.deparse()
        return f'{name}={value}'
        
    def to_dict(self):        
        return {
            'name': self.name.to_dict(),
            'value': self.value.to_dict()
        }

class ToClause(Expression):
    """Associate a reference with its target HQL type for casting."""

    # to is optional, e.g. mv-expand a without a 'to typeof(...)'
    def __init__(self, expr:Reference, to:Union[TypeExpression, hqlt.HqlType, None]=None):
        from Hql.Expressions.Literals import TypeExpression

        Expression.__init__(self)
        self.expr = expr
        if isinstance(to, TypeExpression):
            to = to.dtype()
        self.to = to

    def to_dict(self):
        return {
            'type': self.type,
            'expr': self.expr.to_dict(),
            'to': self.to.to_dict() if self.to is not None else None
        }

    def deparse(self) -> str:
        expr = self.expr.deparse()
        if self.to is not None:
            expr += ' to ' + self.to.deparse()
        return expr

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data
        ctx = ctx.copy()

        # Nothing to cast to
        if self.to is None:
            return ctx

        new = []
        for table in ctx.data:
            table = table.cast_in_place(self.expr, self.to)
            new.append(table)
        
        ctx.data = Data(tables=new)
        return ctx
