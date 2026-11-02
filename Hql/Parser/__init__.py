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
from pathlib import Path
from typing import Sequence, Union, TYPE_CHECKING

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
    def __init__(self, text:str, filename:str='', imports:tuple[Path, ...]=(), paths:Sequence[Path]=()):
        self.filename = filename
        # Files currently being imported, used to catch circular imports
        self.imports = imports
        # Extra directories to resolve imports against, such as the config
        self.paths = list(paths)
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
                visitor = Visitor(self.filename, self.imports, self.paths)
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
    def __init__(self, filename:str, imports:tuple[Path, ...]=(), paths:Sequence[Path]=()):
        self.filename = filename
        self.imports = imports
        self.paths = list(paths)
    
    def visitQuery(self, ctx: HqlParser.QueryContext):
        from Hql.Query import Query, ImportStatement

        statements = []
        for i in ctx.Statements:
            statement = self.visit(i)

            # Imports are inlined in place
            if isinstance(statement, ImportStatement):
                statements += statement.statements
            else:
                statements.append(statement)
                
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

    def visitMapStatement(self, ctx: HqlParser.MapStatementContext):
        from Hql.Query import Mapping
        name = self.visit(ctx.Name)

        mapping = Mapping(name)
        for i in ctx.Maps:
            mapping.merge(self.visit(i)) 

        return mapping

    def visitImportStatement(self, ctx: HqlParser.ImportStatementContext):
        if ctx.From:
            return self.visit(ctx.From)
        return self.visit(ctx.Simple)

    def visitFromImportStatement(self, ctx: HqlParser.FromImportStatementContext):
        src = self.visit(ctx.Src)
        name = self.visit(ctx.Import.Name)
        return self.import_file(ctx, name, src)

    def visitSimpleImportStatement(self, ctx: HqlParser.SimpleImportStatementContext):
        name = self.visit(ctx.Name)
        return self.import_file(ctx, name)

    '''
    Parses the imported file, a.b resolves to a/b.hql
    Looks relative to the importing file, then the given paths (the config
    directory), then the working directory.
    '''
    def import_file(self, ctx, name, src=None):
        from Hql.Query import ImportStatement, Query, QueryStatement

        statement = ImportStatement(name, src)
        rel = Path(*statement.parts).with_suffix('.hql')

        bases = []
        if self.filename and Path(self.filename).parent.is_dir():
            bases.append(Path(self.filename).parent)
        bases += self.paths
        bases.append(Path.cwd())

        path = None
        for base in bases:
            if (base / rel).is_file():
                path = (base / rel).resolve()
                break

        if path is None:
            raise hqle.ParseException(f'Could not find {rel} to import, looked in {", ".join(str(x) for x in bases)}', ctx, self.filename)

        importing = self.imports
        if self.filename:
            importing += (Path(self.filename).resolve(),)

        if path in importing:
            raise hqle.ParseException(f'Circular import of {path}', ctx, self.filename)

        parser = Parser(path.read_text(), filename=str(path), imports=importing, paths=self.paths)
        parser.assemble()
        assert isinstance(parser.assembly, Query)

        for i in parser.assembly.statements:
            if isinstance(i, QueryStatement):
                raise hqle.ParseException(f'Imported file {path} has a query statement, only declarations can be imported', ctx, self.filename)

        statement.statements = parser.assembly.statements
        statement.path = str(path)
        return statement
