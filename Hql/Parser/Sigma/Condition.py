from __future__ import annotations
from typing import TYPE_CHECKING
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from .grammar.SigmaLexer import SigmaLexer
from .grammar.SigmaParser import SigmaParser
from .grammar.SigmaVisitor import SigmaVisitor
from fnmatch import fnmatch

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Parser.Sigma.Selection import Selection

class ConditionErrorListener(ErrorListener):
    def __init__(self, text:str):
        self.text = text

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise hqle.QueryException(f'Invalid Sigma condition {self.text!r} at column {column}: {msg}')

class Condition():
    def __init__(self, text:str, selections:list[Selection]):
        self.text = text
        self.selections:list[Selection] = selections
        self.tree = self.parse()

    def get_sel(self, name:str) -> list[Selection]:
        matches = []
        for i in self.selections:
            if fnmatch(i.name, name):
                matches.append(i)

        return matches

    def parse(self):
        listener = ConditionErrorListener(self.text)

        lexer = SigmaLexer(InputStream(self.text))
        lexer.removeErrorListeners()
        lexer.addErrorListener(listener)

        parser = SigmaParser(CommonTokenStream(lexer))
        parser.removeErrorListeners()
        parser.addErrorListener(listener)

        return parser.condition()

    def assemble(self):
        visitor = Visitor(self)
        self.assembly = visitor.visit(self.tree)
        return self.assembly

class Visitor(SigmaVisitor):
    def __init__(self, condition:Condition):
        self.condition = condition

    def visitCondition(self, ctx: SigmaParser.ConditionContext):
        return self.visit(ctx.Statement)

    def visitOrStatement(self, ctx: SigmaParser.OrStatementContext):
        from Hql.Expressions.Logic import BinaryLogic

        exprs = [self.visit(ctx.Left)]
        for i in ctx.Right:
            exprs.append(self.visit(i))

        return BinaryLogic(exprs, logic_and=False)

    def visitAndStatement(self, ctx: SigmaParser.AndStatementContext):
        from Hql.Expressions.Logic import BinaryLogic

        exprs = [self.visit(ctx.Left)]
        for i in ctx.Right:
            exprs.append(self.visit(i))

        return BinaryLogic(exprs, logic_and=True)

    def visitNotStatement(self, ctx: SigmaParser.NotStatementContext):
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference
        inner = self.visit(ctx.Statement)
        return FuncExpr(NamedReference('not'), [inner])

    def visitBracketStatement(self, ctx: SigmaParser.BracketStatementContext):
        return self.visit(ctx.Statement)

    def visitOfStatement(self, ctx: SigmaParser.OfStatementContext):
        from itertools import combinations
        from Hql.Expressions.Logic import BinaryLogic

        specifier = self.visit(ctx.Specifier)
        target = [x.build_selection() for x in self.visit(ctx.Target)]

        if specifier == 'all':
            return BinaryLogic(target, logic_and=True)

        count = int(specifier)
        if count < 1 or count > len(target):
            raise hqle.QueryException(f'{count} of matches {len(target)} selections')
        if count == 1:
            return BinaryLogic(target, logic_and=False)

        # At least count of them: any combination of count selections all matching
        return BinaryLogic(
            [BinaryLogic(list(x), logic_and=True) for x in combinations(target, count)],
            logic_and=False,
        )

    def visitOfSpecifier(self, ctx: SigmaParser.OfSpecifierContext):
        if ctx.Int:
            return ctx.Int.text

        if ctx.All:
            return ctx.All.text

    def visitOfTarget(self, ctx: SigmaParser.OfTargetContext) -> list[Selection]:
        # pattern or 'them'
        # 'them' means all selections
        if ctx.Pattern:
            pat = self.visit(ctx.Pattern)
        else:
            pat = '*'

        target = self.condition.get_sel(pat)

        if not target:
            raise hqle.QueryException(f'Sigma condition pattern {pat} matches no selection')

        return target

    def visitSelectionIdentifier(self, ctx: SigmaParser.SelectionIdentifierContext):
        if ctx.Basic:
            identifier = self.visit(ctx.Basic)
            matches = self.condition.get_sel(identifier)
            if not matches:
                raise hqle.QueryException(f'Sigma condition references undefined selection {identifier}')
            return matches[0].build_selection()
        else:
            return None

    def visitPatternIdentifier(self, ctx: SigmaParser.PatternIdentifierContext):
        return self.visit(ctx.Wildcard)

    def visitWildcardIdentifier(self, ctx: SigmaParser.WildcardIdentifierContext):
        if ctx.Identifier:
            return ctx.Identifier.text

    def visitBasicIdentifier(self, ctx: SigmaParser.BasicIdentifierContext):
        if ctx.Identifier:
            return ctx.Identifier.text
