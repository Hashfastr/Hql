from __future__ import annotations
from Hql.Parser.grammar.HqlVisitor import HqlVisitor
from Hql.Parser.grammar.HqlParser import HqlParser

from Hql.Exceptions import HqlExceptions as hqle

class BaseExpressions(HqlVisitor):
    def __init__(self):
        pass
    
    '''
    Name references
    
    Not values, but references to values such as columns and tables.
    '''

    def visitEscapedName(self, ctx: HqlParser.EscapedNameContext):
        from Hql.Expressions.References import EscapedNamedReference

        # Probably need to unescape these eventually
        literal = self.visit(ctx.StringLiteral)
        return EscapedNamedReference(literal.quote(''))

    def visitWildcardedName(self, ctx: HqlParser.WildcardedNameContext):
        from Hql.Expressions.References import Wildcard

        if ctx.Star:
            txt = ctx.Star.getText()
        elif ctx.Name:
            txt = ctx.Name.getText()
        else:
            raise hqle.ParseException("Wildcarded name given nothing", ctx)
        return Wildcard(txt)
    
    def visitKeywordName(self, ctx: HqlParser.KeywordNameContext):
        from Hql.Expressions.References import NamedReference

        if ctx.Token == None:
            raise hqle.ParseException('Keyword has no string token', ctx)
        return NamedReference(ctx.Token.text)

    def visitExtendedKeywordName(self, ctx: HqlParser.ExtendedKeywordNameContext):
        from Hql.Expressions.References import NamedReference

        if ctx.Token == None:
            raise hqle.ParseException('Keyword has no string token', ctx)
        return NamedReference(ctx.Token.text)
    
    def visitIdentifierName(self, ctx: HqlParser.IdentifierNameContext):
        from Hql.Expressions.References import NamedReference

        if ctx.Token == None:
            raise hqle.ParseException('Identifier has no string token', ctx)
        return NamedReference(ctx.Token.text)
    
    def visitNamedExpression(self, ctx: HqlParser.NamedExpressionContext):
        from Hql.Expressions.References import NamedExpression

        if not ctx.Name:
            return self.visit(ctx.Expression)
                
        names = self.visit(ctx.Name)
        value = self.visit(ctx.Expression)
        return NamedExpression(names, value)
    
    def visitNamedExpressionNameClause(self, ctx: HqlParser.NamedExpressionNameClauseContext):
        return [self.visit(ctx.Name)] if ctx.Name else self.visit(ctx.NameList)
        
    def visitNamedExpressionNameList(self, ctx: HqlParser.NamedExpressionNameListContext):
        return [self.visit(x) for x in ctx.Names]
    
    def visitPathReference(self, ctx: HqlParser.PathReferenceContext):
        from Hql.Expressions.References import Path

        parts = [self.visit(x) for x in ctx.Parts]
        return Path(parts)

    '''
    Individual constant values
    
    Strings
    Longs
    Bools
    Ints
    '''
    
    def visitStringLiteralExpression(self, ctx: HqlParser.StringLiteralExpressionContext):
        import re
        from Hql.Expressions.Literals import StringLiteral, MultiString

        parts = []
        for i in ctx.Tokens:
            cur = i.text
            verbatim = False
            obfuscated = False

            if i.text[0] in ('h', 'H'):
                cur = cur[1:]
                obfuscated = True

            if i.text[0] == '@':
                cur = cur[1:]
                verbatim = True
                
            if i.text[:3] == '"""' or i.text[:3] == "'''":
                verbatim = True

            if not verbatim:
                cur = eval(cur)
                assert isinstance(cur, str)
                cur = cur.encode('utf-8')

            else:
                if i.text[:3] == '"""' or i.text[:3] == "'''":
                    quote = i.text[:3]
                    cur = cur[3:-3]
                else:
                    quote = cur[0]
                    cur = cur[1:-1]

                # unescape any quotes
                old = ''.join([fr'\{x}' for x in quote])
                cur = re.sub(old, quote, cur).encode('utf-8')

            parts.append(StringLiteral(cur, verbatim=verbatim, obfuscated=obfuscated))

        if len(parts) == 1:
            return parts[0]
        else:
            return MultiString(parts)

    def visitLongLiteralExpression(self, ctx: HqlParser.LongLiteralExpressionContext):
        from Hql.Expressions.Literals import Integer

        if ctx.Token == None:
            raise hqle.ParseException('LongLiteral has no string token', ctx)
        return Integer(ctx.Token.text)
    
    def visitBooleanLiteralExpression(self, ctx: HqlParser.BooleanLiteralExpressionContext):
        from Hql.Expressions.Literals import Bool

        if ctx.Token == None:
            raise hqle.ParseException('BooleanLiteral has no string token', ctx)
        return Bool(ctx.Token.text.lower() == 'true')

    def visitRealLiteralExpression(self, ctx: HqlParser.RealLiteralExpressionContext):
        from Hql.Expressions.Literals import Float

        if ctx.Token == None:
            raise hqle.ParseException('RealLiteral has no string token', ctx)
        return Float(ctx.Token.text)

    def visitDateTimeLiteralExpression(self, ctx: HqlParser.DateTimeLiteralExpressionContext):
        from Hql.Expressions.Literals import StringLiteral, Datetime

        import re

        if ctx.Token == None:
            raise hqle.ParseException('DatetimeLiteral has no string token', ctx)

        datestr = re.findall(r'datetime\([\'"]?([^\)]+)[\'"]?\)', ctx.Token.text)[0]
        lit = StringLiteral(datestr)

        return Datetime(lit)

    def visitTimeSpanLiteralExpression(self, ctx: HqlParser.TimeSpanLiteralExpressionContext):
        from Hql.Expressions.Literals import StringLiteral, TimeDelta

        if ctx.Token == None:
            raise hqle.ParseException('TimeSpanLiteral has no string token', ctx)

        return TimeDelta(StringLiteral(ctx.Token.text))
    
    '''
    Sort specific
    '''
    
    def visitOrderedExpression(self, ctx: HqlParser.OrderedExpressionContext):
        from Hql.Expressions.Aggregation import OrderedExpression

        order = ctx.OrderKind.text if ctx.OrderKind else 'desc'
        nulls = ctx.NullsKind.text if ctx.NullsKind else ''
        expr = self.visit(ctx.Expression)

        return OrderedExpression(expr, order=order, nulls=nulls)

    def visitScalarType(self, ctx: HqlParser.ScalarTypeContext):
        from Hql.Expressions.Literals import TypeExpression

        if ctx.Token == None:
            raise hqle.ParseException('ScalarType has no string token', ctx)
        return TypeExpression(ctx.Token.text)

    def visitStaticNamedExpression(self, ctx: HqlParser.StaticNamedExpressionContext):
        from Hql.Expressions.References import NamedExpression

        name = self.visit(ctx.Name)
        value = self.visit(ctx.Value)
        return NamedExpression([name], value)
