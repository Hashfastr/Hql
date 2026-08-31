from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func
# from Hql.Expressions import PipeExpression, StringLiteral, Expression, DotCompositeFunction
from typing import TYPE_CHECKING, Optional, Sequence, Union
import logging

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Expressions.References import Reference
    from Hql.Expressions import Expression

@register_func('macro')
class macro(Function):
    """Resolve configured database macros into executable instructions."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference

        Function.__init__(self, args, 1, -1)

        self.names:Sequence[Union[StringLiteral, Reference]] = []
        for i in args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.QueryException(f'Invalid argument type passed to macro function: {type(i)}')
            self.names.append(i)

    def parse_macro(self, macro:dict, src:str) -> Expression:
        from Hql.Parser import Parser
        from Hql.Expressions import Expression

        if 'hql' not in macro:
            raise hqle.ConfigException(f'Missing hql definition in config {src}')

        parser = Parser(macro['hql'], f'{src}')
        parser.assemble(targets=['pipeExpression', 'beforePipeExpression', 'emptyPipedExpression'])
        assert isinstance(parser.assembly, Expression)

        return parser.assembly

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral
        
        new = []
        for i in self.names:
            i = i.preprocess(ctx)
            if not isinstance(i, StringLiteral):
                raise hqle.QueryException(f'File function give argument that doesn\'t resolve to string literal: {type(i)}')
            new.append(i)

        self.names = new

        return self
        
    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Compiler import InstructionSet, HqlCompiler
        from Hql.Database import Database
        from Hql.Expressions import PipeExpression

        self.preprocess(ctx)
        
        db = receiver
        macros = [x.str() for x in self.args]
        compiler = HqlCompiler(ctx.config)
        
        if not db:
            dbconf = ctx.config.get_default_db()
            db = ctx.get_db(dbconf['type'])(dbconf, name='default')

        upstream = []
        for i in macros:
            macro = db.get_macro(i)
            if not macro:
                raise hqle.QueryException(f'Macro not found: {i}')
            if isinstance(macro, (Database, InstructionSet)):
                upstream.append(macro)
                continue
            parsed = self.parse_macro(macro, f'{db.name}/{i}')

            if not isinstance(parsed, PipeExpression):
                parsed = PipeExpression([], prepipe=parsed)

            acc, _ = compiler.compile(parsed)
            upstream.append(acc)

        return InstructionSet(upstream)
