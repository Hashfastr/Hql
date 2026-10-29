from __future__ import annotations
from Hql.Parser.grammar.HqlVisitor import HqlVisitor
from Hql.Parser.grammar.HqlParser import HqlParser

from Hql.Exceptions import HqlExceptions as hqle

class Logic(HqlVisitor):
    def __init__(self):
        pass
    
    def visitEqualsEqualityExpression(self, ctx: HqlParser.EqualsEqualityExpressionContext):
        from Hql.Expressions.Logic import Equality

        if ctx.OperatorToken == None:
            return self.visit(ctx.Left)

        op = ctx.OperatorToken.text

        expr = Equality(
            self.visit(ctx.Left),
            [self.visit(ctx.Right)],
            cs='~' not in op,
            neq='!' in op
        )

        return expr

    def visitRelationalExpression(self, ctx: HqlParser.RelationalExpressionContext):
        from Hql.Expressions.Logic import Relational

        # Pass through in case we're doing stupid shit
        if ctx.OperatorToken == None:
            return self.visit(ctx.Left)

        op = ctx.OperatorToken.text

        expr = Relational(
            self.visit(ctx.Left),
            self.visit(ctx.Right),
            '>' in op,
            '=' in op
        )

        return expr

    '''
    Arithmetic, operations are left associative
    a - b + c -> (a - b) + c
    '''
    def visitAdditiveExpression(self, ctx: HqlParser.AdditiveExpressionContext):
        from Hql.Expressions.Arithmetic import BinaryArithmetic

        expr = self.visit(ctx.Left)
        for i in ctx.Operations:
            expr = BinaryArithmetic(expr, i.OperatorToken.text, self.visit(i.Right))

        return expr

    def visitMultiplicativeExpression(self, ctx: HqlParser.MultiplicativeExpressionContext):
        from Hql.Expressions.Arithmetic import BinaryArithmetic

        expr = self.visit(ctx.Left)
        for i in ctx.Operations:
            expr = BinaryArithmetic(expr, i.OperatorToken.text, self.visit(i.Right))

        return expr

    def visitInvocationExpression(self, ctx: HqlParser.InvocationExpressionContext):
        from Hql.Expressions.Arithmetic import Negate
        from Hql.Expressions.Literals import Integer, Float

        expr = self.visit(ctx.Expression)

        if ctx.OperatorToken == None or ctx.OperatorToken.text == '+':
            return expr

        # Negative numeric literals stay literals
        if isinstance(expr, Integer):
            return Integer(-expr.value)
        if isinstance(expr, Float):
            return Float(-expr.value)

        return Negate(expr)

    def visitBetweenEqualityExpression(self, ctx: HqlParser.BetweenEqualityExpressionContext):
        from Hql.Expressions.Logic import BetweenEquality

        if ctx.OperatorToken == None:
            return self.visit(ctx.Left)

        start = self.visit(ctx.Expressions[0])
        end = self.visit(ctx.Expressions[1])

        expr = BetweenEquality(
            self.visit(ctx.Left),
            start,
            end,
            neq='!' in ctx.OperatorToken.text
        )
        
        return expr
    
    def visitLogicalOrExpression(self, ctx: HqlParser.LogicalOrExpressionContext):
        from Hql.Expressions.Logic import BinaryLogic

        exprs = [self.visit(ctx.Left)]

        for i in ctx.Operations:
            exprs.append(self.visit(i))
        
        return BinaryLogic(
            exprs,
            logic_and=False
        )
    
    def visitLogicalOrOperation(self, ctx: HqlParser.LogicalOrOperationContext):
        return self.visit(ctx.Right)

    def visitLogicalAndExpression(self, ctx: HqlParser.LogicalAndExpressionContext):
        from Hql.Expressions.Logic import BinaryLogic

        exprs = [self.visit(ctx.Left)]

        for i in ctx.Operations:
            exprs.append(self.visit(i))
        
        return BinaryLogic(
            exprs,
            logic_and=True
        )
    
    def visitLogicalAndOperation(self, ctx: HqlParser.LogicalAndOperationContext):
        return self.visit(ctx.Right)

    def visitParenthesizedExpression(self, ctx: HqlParser.ParenthesizedExpressionContext):
        from Hql.Expressions import PipeExpression

        expr = self.visit(ctx.Expression)

        # (a + 1) is just grouping, not a subquery
        if isinstance(expr, PipeExpression) and not expr.pipes and expr.prepipe is not None:
            return expr.prepipe

        return expr

    def visitListEqualityExpression(self, ctx: HqlParser.ListEqualityExpressionContext):
        from Hql.Expressions.Logic import Equality, Substring

        if ctx.OperatorToken == None:
            return self.visit(ctx.Left)

        lh = self.visit(ctx.Left)
        op = ctx.OperatorToken.text
        
        rh = []
        for i in ctx.Expressions:
            rh.append(self.visit(i))

        if 'in' in op:
            return Equality(lh, rh, cs='~' not in op, neq='!' in op)
        
        return Substring(lh, rh, term='has' in op, logic_and='all' in op, cs='cs' in op)

    def visitStringBinaryOperator(self, ctx: HqlParser.StringBinaryOperatorContext):
        if not ctx.OperatorToken:
            raise hqle.CompilerException('String Binary Operator has no Operator, wut')

        return ctx.OperatorToken.text

    def visitStringBinaryOperatorExpression(self, ctx: HqlParser.StringBinaryOperatorExpressionContext):
        from Hql.Expressions.Logic import Substring, Equality, Regex

        if not ctx.Right:
            return self.visit(ctx.Left)

        lh = self.visit(ctx.Left)
        rh = self.visit(ctx.Right)

        if ctx.Operator:
            op:str = self.visit(ctx.Operator)

        elif ctx.HasOperator:
            op:str = ctx.HasOperator.text

        else:
            raise hqle.ParseException('String Binary Operator has no Operator, wut?', ctx)
        
        if op in ('=~', '!~'):
            return Equality(lh, [rh], cs=False, neq='!' in op)

        if op == 'matches regex':
            return Regex(lh, rh)

        return Substring(
            lh, [rh],
            term='has' in op,
            neq='!' in op,
            cs='cs' in op,
            startswith='startswith' in op or 'prefix' in op,
            endswith='endswith' in op or 'suffix' in op
        )
