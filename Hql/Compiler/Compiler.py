from __future__ import annotations
from typing import Optional, Union, TYPE_CHECKING, Callable, Sequence

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context
import logging
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from Hql.Compiler import BranchDescriptor, InstructionSet
    from Hql.Operators.Operator import Operator
    from Hql.Expressions import Expression
    from Hql.Query import Statement
    import Hql

class Compiler():
    """Base dispatcher for compiling HQL nodes into a target form."""

    def __init__(self):
        from Hql.Data import Data
        self.type = self.__class__.__name__
        self.ctx = Context(Data())

        self.ops:list[Operator] = []
        self.stmts:list[Statement] = []

    '''
    What?

    This is to get the operator method for a compiler
    Might want to change this
    '''
    def from_name(self, name:str) -> Callable:
        return getattr(self, name)

    def run(self, ctx:Union[Context, None]=None) -> Context:
        return ctx if ctx is not None else self.ctx

    '''
    Returns None, op as an auto denial
    '''
    def add_op(self, op:Union[Operator, BranchDescriptor]) -> tuple[Optional[Operator], Optional[Operator]]:
        from Hql.Compiler import BranchDescriptor
        if isinstance(op, BranchDescriptor):
            op = op.get_op()
        return None, op
    
    def add_ops(self, ops:Sequence[Union[Operator, BranchDescriptor]]) -> Optional[list[Operator]]:
        from Hql.Operators.Operator import Operator

        for idx, op in enumerate(ops):
            _, rej = self.add_op(op)
            if rej:
                post = []
                for i in ops[idx+1:]:
                    if isinstance(i, Operator):
                        post.append(i)
                    else:
                        post.append(i.get_op())
                return [rej] + post
        return None

    def optimize(self, ops: list[BranchDescriptor]) -> list[BranchDescriptor]:
        return ops

    '''
    You'll want to replace this with something like a string that you'll query your database with.
    Default returns optimized operators for running in Hql-land
    '''
    def compile(self, src:Union[Expression, Operator, Statement, None], prep:bool=True) -> tuple[Optional[object], Optional[object]]:
        if src is None:
            return None, None
        return self.from_name(src.type)(src, prep=prep)

    def compile_op(self, src:Operator, prep:bool=True) -> tuple[Optional[object], Optional[Operator]]:
        return self.from_name(src.type)(src, prep=prep)

    def compile_expr(self, src:Expression, prep:bool=True) -> tuple[Optional[object], Optional[Expression]]:
        return self.from_name(src.type)(src, prep=prep)

    def compile_stmt(self, src:Statement, prep:bool=True) -> tuple[Optional[object], Optional[Statement]]:
        return self.from_name(src.type)(src, prep=prep)

    def decompile(self) -> str:
        from Hql.Expressions import PipeExpression
        logging.critical("Decompilation doesn't actually work right now, sorry")
        # return PipeExpression(pipes=self.ops).decompile(self.ctx)
        return ''

    def add_time_bound(self, start:Union[datetime, timedelta], end:Union[datetime, timedelta, None]=None):
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BetweenEquality, NamedReference, Datetime

        if end == None:
            end = datetime.now()

        if isinstance(end, timedelta):
            end = datetime.now() - end

        if isinstance(start, timedelta):
            start = datetime.now() - start

        op = Where(
            BetweenEquality(
                NamedReference('_hqltimestamp'),
                Datetime(start),
                Datetime(end)
            )
        )

        self.add_op(op)

    '''
    By default, all of these return themselves as they are being
    'rejected' back to the compiler
    '''

    '''
    Operators
    '''

    def Where(self, op:Hql.Operators.Where, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Project(self, op:Hql.Operators.Project, prep:bool=True) -> tuple[object, object]:
        return None, op

    def ProjectAway(self, op:Hql.Operators.ProjectAway, prep:bool=True) -> tuple[object, object]:
        return None, op

    def ProjectKeep(self, op:Hql.Operators.ProjectKeep, prep:bool=True) -> tuple[object, object]:
        return None, op

    def ProjectReorder(self, op:Hql.Operators.ProjectReorder, prep:bool=True) -> tuple[object, object]:
        return None, op

    def ProjectRename(self, op:Hql.Operators.ProjectRename, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Take(self, op:Hql.Operators.Take, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Count(self, op:Hql.Operators.Count, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Extend(self, op:Hql.Operators.Extend, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Range(self, op:Hql.Operators.Range, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Top(self, op:Hql.Operators.Top, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Unnest(self, op:Hql.Operators.Unnest, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Union(self, op:Hql.Operators.Union, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Summarize(self, op:Hql.Operators.Summarize, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Datatable(self, op:Hql.Operators.Datatable, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Join(self, op:Hql.Operators.Join, prep:bool=True) -> tuple[object, object]:
        return None, op

    def MvExpand(self, op:Hql.Operators.MvExpand, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Sort(self, op:Hql.Operators.Sort, prep:bool=True) -> tuple[object, object]:
        return None, op

    def Rename(self, op:Hql.Operators.Rename, prep:bool=True) -> tuple[object, object]:
        return None, op

    '''
    Expressions
    '''

    def Tabular(self, expr:Hql.Expressions.Expression) -> tuple[Optional[InstructionSet], Optional[Hql.Expressions.Expression]]:
        return None, expr

    def PipeExpression(self, expr:Hql.Expressions.PipeExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def OpParameter(self, expr:Hql.Expressions.OpParameter, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def ToClause(self, expr:Hql.Expressions.ToClause, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def OrderedExpression(self, expr:Hql.Expressions.OrderedExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def ByExpression(self, expr:Hql.Expressions.ByExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Function(self, expr:Hql.Functions.Function, prep:bool=True) -> tuple[object, object]:
        return None, expr

    # Logic functions are still functions, fall back to Function handling by default
    def LogicFunction(self, expr:Hql.Functions.Logic.LogicFunction, prep:bool=True) -> tuple[object, object]:
        return self.Function(expr, prep=prep)

    def FuncExpr(self, expr:Hql.Expressions.FuncExpr, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def DotCompositeFunction(self, expr:Hql.Expressions.DotCompositeFunction, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Equality(self, expr:Hql.Expressions.Equality, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Substring(self, expr:Hql.Expressions.Substring, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Relational(self, expr:Hql.Expressions.Relational, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def BetweenEquality(self, expr:Hql.Expressions.BetweenEquality, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def BinaryLogic(self, expr:Hql.Expressions.BinaryLogic, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Not(self, expr:Hql.Expressions.Not, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def BasicRange(self, expr:Hql.Expressions.BasicRange, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Regex(self, expr:Hql.Expressions.Regex, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def TypeExpression(self, expr:Hql.Expressions.TypeExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def StringLiteral(self, expr:Hql.Expressions.StringLiteral, prep:bool=True) -> tuple[object, object]:
        return None, expr
    
    def MultiString(self, expr:Hql.Expressions.MultiString, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Integer(self, expr:Hql.Expressions.Integer, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def IP4(self, expr:Hql.Expressions.IP4, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Float(self, expr:Hql.Expressions.Float, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Bool(self, expr:Hql.Expressions.Bool, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Multivalue(self, expr:Hql.Expressions.Multivalue, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Datetime(self, expr:Hql.Expressions.Datetime, prep:bool=True) -> tuple[object, object]:
        return None, expr
    
    def NamedReference(self, expr:Hql.Expressions.NamedReference, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def EscapedNamedReference(self, expr:Hql.Expressions.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Wildcard(self, expr:Hql.Expressions.Wildcard, prep:bool=True) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    def Path(self, expr:Hql.Expressions.Path, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def NamedExpression(self, expr:Hql.Expressions.NamedExpression, prep:bool=True) -> tuple[object, object]:
        return None, expr
