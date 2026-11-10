from __future__ import annotations
from Hql.Parser.grammar.HqlVisitor import HqlVisitor
from Hql.Parser.grammar.HqlParser import HqlParser

from Hql.Exceptions import HqlExceptions as hqle
from typing import TYPE_CHECKING, Optional

import logging

if TYPE_CHECKING:
    from Hql.Expressions.References import Element

class Functions(HqlVisitor):
    def __init__(self):
        pass
    
    '''
    Couldn't remember what this does but it handles paths with function calls and namedreferences in it

    myfunc().Name
    '''
    def visitFunctionCallOrPathPathExpression(self, ctx: HqlParser.FunctionCallOrPathPathExpressionContext):
        from Hql.Expressions.References import Path, NamedReference, EscapedNamedReference, Element
        from Hql.Expressions.Functions import FuncExpr, ReceiverFuncExpr
        from Hql.Expressions.Literals import StringLiteral
        path = []
        # Set once an index leaves what a field path can name, R[0]
        element:Optional[Element] = None

        expr = self.visit(ctx.Expression)
        if expr == None:
            logging.error('Path expression given NoneType root expression')
            raise hqle.SemanticException(
                'NoneType root path expression',
                ctx.start.line,
                ctx.start.column
            )

        path.append(expr)
        for i in ctx.Operations:
            # R[key] and the legacy R.[key]
            index = i.getChild(0)
            if isinstance(index, (
                HqlParser.FunctionCallOrPathElementOperationContext,
                HqlParser.LegacyFunctionCallOrPathElementOperationContext,
            )):
                key = self.visit(index.Element)
                if key is None:
                    raise hqle.SemanticException('Empty index in path expression', ctx.start.line, ctx.start.column)
                if isinstance(path[-1], ReceiverFuncExpr) and element is None:
                    raise hqle.SemanticException(
                        'Indexing the result of a receiver function call is unsupported',
                        ctx.start.line,
                        ctx.start.column
                    )

                if element is not None:
                    element = Element(element, key)
                # A field name in brackets is just a field, R['a'] is R.a
                elif isinstance(key, StringLiteral):
                    path.append(EscapedNamedReference(key.str()))
                else:
                    element = Element(Path(path), key)
                continue

            op = self.visit(i)

            if element is not None:
                if not isinstance(op, NamedReference):
                    raise hqle.SemanticException(
                        'Only field names can follow an index in a path expression',
                        ctx.start.line,
                        ctx.start.column
                    )
                element = Element(element, StringLiteral(op.name), dotted=True)
                continue

            # short cut if there is a function
            if isinstance(op, FuncExpr):
                path = [ReceiverFuncExpr(Path(path), op)]
                continue

            if isinstance(path[-1], ReceiverFuncExpr):
                raise hqle.SemanticException(
                    'Path segment after receiver function call is unsupported',
                    ctx.start.line,
                    ctx.start.column
                )
            path.append(op)

        if element is not None:
            return element
        return Path(path)

    def visitScopedFunctionCallExpression(self, ctx: HqlParser.ScopedFunctionCallExpressionContext):
        from Hql.Expressions.Functions import ReceiverFuncExpr

        return ReceiverFuncExpr(self.visit(ctx.Scope), self.visit(ctx.FunctionCall))
    
    '''
    The basic function call
    '''
    def visitFunctionCallExpression(self, ctx: HqlParser.FunctionCallExpressionContext):
        from Hql.Expressions.Functions import FuncExpr
        expr = FuncExpr(self.visit(ctx.Name))
        
        for i in ctx.Arguments:
            expr.args.append(self.visit(i))
        
        return expr

    # def visitFunctionCallName(self, ctx: HqlParser.FunctionCallNameContext):
    #     return self.visit(ctx.)
    
    '''
    Pure path of functions
    '''
    def visitDotCompositeFunctionCallExpression(self, ctx: HqlParser.DotCompositeFunctionCallExpressionContext):
        from Hql.Expressions.Functions import DotFuncExpr
        funcs = [self.visit(ctx.Call)]
                
        for i in ctx.Operations:
            funcs.append(self.visit(i))
        
        return DotFuncExpr(funcs)
