# Generated from Sigma.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .SigmaParser import SigmaParser
else:
    from SigmaParser import SigmaParser

# This class defines a complete generic visitor for a parse tree produced by SigmaParser.

class SigmaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by SigmaParser#condition.
    def visitCondition(self, ctx:SigmaParser.ConditionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#orStatement.
    def visitOrStatement(self, ctx:SigmaParser.OrStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#andStatement.
    def visitAndStatement(self, ctx:SigmaParser.AndStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#statement.
    def visitStatement(self, ctx:SigmaParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#notStatement.
    def visitNotStatement(self, ctx:SigmaParser.NotStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#bracketStatement.
    def visitBracketStatement(self, ctx:SigmaParser.BracketStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#ofStatement.
    def visitOfStatement(self, ctx:SigmaParser.OfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#ofSpecifier.
    def visitOfSpecifier(self, ctx:SigmaParser.OfSpecifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#ofTarget.
    def visitOfTarget(self, ctx:SigmaParser.OfTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#selectionIdentifier.
    def visitSelectionIdentifier(self, ctx:SigmaParser.SelectionIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#patternIdentifier.
    def visitPatternIdentifier(self, ctx:SigmaParser.PatternIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#basicIdentifier.
    def visitBasicIdentifier(self, ctx:SigmaParser.BasicIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by SigmaParser#wildcardIdentifier.
    def visitWildcardIdentifier(self, ctx:SigmaParser.WildcardIdentifierContext):
        return self.visitChildren(ctx)



del SigmaParser