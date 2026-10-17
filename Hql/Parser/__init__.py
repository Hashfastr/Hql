from __future__ import annotations
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from Hql.Exceptions import HqlExceptions as hqle

from Hql.Parser.grammar.HqlLexer import HqlLexer
from Hql.Parser.grammar.HqlParser import HqlParser
from Hql.Parser.grammar.HqlVisitor import HqlVisitor

from Hql.Parser.BaseExpressions import BaseExpressions as ParseBaseExpressions
from Hql.Parser.Functions import Functions as ParseFunctions
from Hql.Parser.Operators import Operators as ParseOperators
from Hql.Parser.Logic import Logic as ParseLogic

import logging
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Operators.Operator import Operator
    from Hql.Query import Query, Statement

class HqlErrorListener(ErrorListener):
    def __init__(self, text:str, filename:str):
        ErrorListener.__init__(self)
        self.text = text
        self.filename = filename

    def syntaxError(self, recognizer:HqlParser, offendingSymbol, line, column, msg, e):
        e = hqle.LexerException(msg, self.text, line, column, offendingSymbol, filename=self.filename)
        Parser.handleException(recognizer, e)
        
class Parser():
    def __init__(self, text:str, filename:str=''):
        self.filename = filename
        self.text = text
        self.tree = None
        self.assembly:Union[None, Query, Statement, Operator, Expression] = None
    
    def parse_text(self) -> HqlParser:
        if not self.text:
            logging.error(f'Given query is empty: {self.filename}')
            raise hqle.QueryException('Empty query given')
        
        self.err_listener = HqlErrorListener(self.text, self.filename)
        
        lexer = HqlLexer(InputStream(self.text))
        token_stream = CommonTokenStream(lexer)
        parser = HqlParser(token_stream)
        
        parser.removeErrorListeners()
        parser.addErrorListener(self.err_listener)
         
        return parser

    def assemble(self, target:str='query', targets:Union[None, list]=None):
        if not targets:
            targets = [target]
        
        traces = []
        for i in targets:
            try:
                self.tree = self.parse_text()
                visitor = Visitor(self.filename)
                target = getattr(self.tree, i)()
                self.assembly = visitor.visit(target)
            except:
                import traceback
                traces.append(traceback.format_exc())
                continue
            break

        if not self.assembly:
            [logging.critical(x) for x in traces]
            if self.filename:
                logging.critical(self.filename)
            logging.critical(f'Failed to parse with targets {targets}')
            raise hqle.CompilerException(f'Could not parse\n{self.text}')
    
    @staticmethod
    def getText(ctx):
        stream = ctx.parser.getTokenStream()
        start = ctx.start.tokenIndex
        stop = ctx.stop.tokenIndex

        return stream.getText(start, stop)
    
    @staticmethod
    def handleException(ctx, e:Union[hqle.ParseException, hqle.LexerException]):
        if isinstance(e, hqle.LexerException):
            text = e.text
            text = text.split('\n')[e.line - 1]
        else:
            text = Parser.getText(ctx)
        
        text += '\n'
        text += (' ' * e.col) + '^'
        # text 
        raise e

# Overrides the HqlVisitor templates
# If not defined here, each node only returns its children.
class Visitor(ParseOperators, ParseFunctions, ParseLogic, ParseBaseExpressions, HqlVisitor):
    def __init__(self, filename:str):
        self.filename = filename
    
    def visitQuery(self, ctx: HqlParser.QueryContext):
        from Hql.Query import Query

        statements = []
        for i in ctx.Statements:
            statements.append(self.visit(i))
                
        return Query(statements)
    
    def visitQueryStatement(self, ctx: HqlParser.QueryStatementContext):
        from Hql.Query import QueryStatement

        expr = self.visit(ctx.Expression)
        
        if not expr:
            raise hqle.ParseException(
                'Query statement given None',
                ctx.start.line,
                ctx.start.column 
            )
        
        statement = QueryStatement(expr)
        
        return statement

    def visitPipeExpression(self, ctx: HqlParser.PipeExpressionContext):
        from Hql.Expressions import PipeExpression
        
        prepipe = self.visit(ctx.Expression)
        if ctx.PipedOperators:
            pipes = self.visit(ctx.PipedOperators).pipes
        else:
            pipes = []
        
        return PipeExpression(pipes, prepipe=prepipe)

    def visitEmptyPipedExpression(self, ctx: HqlParser.EmptyPipedExpressionContext):
        from Hql.Expressions import PipeExpression 
        
        pipes = []
        for i in ctx.Operators:
            try:
                pipes.append(self.visit(i))
            except hqle.ParseException as e:
                e.filename = self.filename
                Parser.handleException(i, e)
        return PipeExpression(pipes)

    def visitLetVariableDeclaration(self, ctx: HqlParser.LetVariableDeclarationContext):
        from Hql.Query import LetStatement
        name = self.visit(ctx.Name)
        value = self.visit(ctx.Expression)
        return LetStatement(name, value)

    def visitLetLogicDeclaration(self, ctx: HqlParser.LetLogicDeclarationContext):
        from Hql.Query import LetLogicStatement
        name = self.visit(ctx.Name)
        logic = self.visit(ctx.Logic)
        return LetLogicStatement(name, logic)

    def visitMacroStatement(self, ctx: HqlParser.MacroStatementContext):
        from Hql.Query import PipeExpression

