from __future__ import annotations
import json
from typing import TYPE_CHECKING, Union
from warnings import deprecated

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Compiler.InstructionSet import InstructionSet
    from Hql.Expressions import PipeExpression
    from Hql.Expressions.References import Reference
    from Hql.Context import Context
    from Hql.Operators.Operator import Operator
    from Hql.Expressions.Logic import Bool, Logic

# Top most object, a query.
# Comprised of multiple statements
#
# let AttackerIPs = syslog-*
# | where program == "sshd" and user == "hashfastr" and status == "Accepted"
# | project IP;
# syslog-*
# | where program == "sshd" and status == "Accepted"
# | join kind=inner (AttackerIPs) on IP
# | project timestamp, user, IP, authtype
#
# Has two statements, AttackerIPs, and the root statement.
# Each statement is denoted by a ; with the exception of the root statement.
# The root statement is denoted by EOF, but can have a ; regardless
class Query():
    """Represent and preprocess a complete sequence of HQL statements."""

    def __init__(self, statements:list[Statement]):
        from Hql.Context import Context
        from Hql.Data import Data
        
        self.statements = statements
        self.ctx = Context(Data())

    def preprocess(self):
        from Hql.Database.Database import Database
        from Hql.Expressions import PipeExpression

        for i in self.statements:
            if isinstance(i, LetStatement):
                self.ctx.symbol_table[i.name.name] = i.root.preprocess(self.ctx)
            elif isinstance(i, QueryStatement):
                root = i.root.preprocess(self.ctx)
                
                if isinstance(root, Database):
                    root = PipeExpression([], root)

                # Should be final statement
                i.root = root
                self.statements = [i]
                break

    @deprecated('Dumb idea, maybe an idea in the future')
    def expand_iset(self):
        from Hql.Expressions.References import NamedReference
        from Hql.Operators.Union import Union as HqlUnion
        from Hql.Compiler import InstructionSet
        from Hql.Operators.Operator import Operator
        from Hql.Expressions import PipeExpression
        
        def process_iset(iset:InstructionSet) -> tuple[dict, list[Operator]]:
            symbol_table = dict()
            up_names = []
            for i in iset.upstream:
                up_names.append(i.id)
                if isinstance(i, InstructionSet):
                    up_symbols, up_pipes = process_iset(i)
                    names = []
                    for j in up_symbols:
                        names.append(i.id + j)
                        symbol_table[i.id + j] = up_symbols[i]

                    union = HqlUnion([NamedReference(x) for x in names], NamedReference(i.id))
                    symbol_table[i.id] = PipeExpression(up_pipes, union)

                else:
                    symbol_table[i.id] = i

            union = HqlUnion([NamedReference(x) for x in up_names], NamedReference(iset.id))
            ops = [union] + iset.ops
            return symbol_table, ops

        def merge_symbols(symbols:dict):
            for i in symbols:
                self.ctx.symbol_table[i] = symbols[i]

        root = None
        for i in self.statements:
            if isinstance(i, LetStatement):
                self.ctx.symbol_table[i.name.name] = i.root.preprocess(self.ctx)
            elif isinstance(i, QueryStatement):
                root = i.root.preprocess(self.ctx)
                break

        for i in self.ctx.symbol_table:
            cur = self.ctx.symbol_table[i]
            if isinstance(cur, InstructionSet):
                symbols, pipes = process_iset(cur)
                merge_symbols(symbols)

                union = pipes[0]
                if isinstance(union, Operator) and not isinstance(union, HqlUnion):
                    self.ctx.symbol_table[i] = PipeExpression(pipes)
                elif not isinstance(union, HqlUnion):
                    self.ctx.symbol_table[i] = PipeExpression(pipes)
                else:
                    self.ctx.symbol_table[i] = PipeExpression(pipes[1:], union)

        if isinstance(root, InstructionSet):
            symbols, pipes = process_iset(root)
            merge_symbols(symbols)

            union = pipes[0]
            if isinstance(union, Operator) and not isinstance(union, HqlUnion):
                raise hqle.CompilerException(f'Expanding instruction sets in query resulted in no-prepipe root')
            elif not isinstance(union, HqlUnion):
                raise hqle.CompilerException(f'Expanding instruction sets in query resulted in no-prepipe root')
            else:
                root = PipeExpression(pipes[1:], union)

        if not isinstance(root, PipeExpression):
            root = PipeExpression([], prepipe=root)

        self.statements = [QueryStatement(root)]

    def deparse(self):
        from Hql.Expressions.References import NamedReference
        from Hql.Compiler.InstructionSet import InstructionSet
        # self.expand_iset()

        statements = []
        for i in self.ctx.symbol_table:
            if isinstance(self.ctx.symbol_table[i], InstructionSet):
                raise Exception('Attempting to deparse compiled Query')
            statements.append(LetStatement(NamedReference(i), self.ctx.symbol_table[i]))
        statements += self.statements

        out = ''
        cur = ''
        for i in statements:
            if cur:
                if len(cur) < 120:
                    out += ';\n'
                else:
                    out += '\n;\n'

            cur = i.deparse()
            out += cur

        return out

    def to_dict(self):
        return {
            "statements": [x.to_dict() for x in self.statements]
        }

    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

# Generic for a statement, see children as this can be very diverse
class Statement():
    """Base class for top-level statements in an HQL query."""

    def __init__(self):
        self.type = self.__class__.__name__
    
    def to_dict(self) -> dict:
        return {
            'type': self.type,
        }

    def deparse(self) -> str:
        return ''
    
    def __str__(self):
        return json.dumps(self.to_dict(), indent=2)

class QueryStatement(Statement):
    """Wrap the root pipeline that produces a query result."""

    def __init__(self, root:PipeExpression):
        Statement.__init__(self)
        self.root:PipeExpression = root

    def to_dict(self):
        out = super().to_dict()
        out['query'] = self.root.to_dict()
        return out

    def deparse(self):
        from Hql.Compiler.InstructionSet import InstructionSet

        if isinstance(self.root, InstructionSet):
            raise Exception('Attempting to deparse compiled QueryStatement')

        return self.root.deparse()

class LetStatement(Statement):
    """Bind a pipeline or macro expression to a name."""

    def __init__(self, name:Reference, value:PipeExpression, macro:bool=False):
        Statement.__init__(self)
        self.root = value
        self.name = name
        self.macro = macro
        
    def to_dict(self):
        return {
            'type': self.type,
            'macro': self.macro,
            'name': self.name.to_dict(),
            'value': self.root.to_dict()
        }

    def deparse(self) -> str:
        name = self.name.deparse()
        value = self.root.deparse()
        return f'let {name} = {value}'
        
    def eval(self, ctx:Context) -> Context:
        name = self.name.str()
        
        if self.macro:
            ctx.macros[name] = self.root
        else:
            ctx.symbol_table[name] = self.root

        return ctx

class LetLogicStatement(LetStatement):
    """Bind a logical expression to a name in the query context."""

    def __init__(self, name:Reference, value:Union[Logic, Bool]):
        Statement.__init__(self)
        self.root = value
        self.name = name

    def to_dict(self):
        return {
            'type': self.type,
            'name': self.name.to_dict(),
            'value': self.root.to_dict()
        }

    def eval(self, ctx:Context) -> Context:
        name = self.name.str()
        ctx.symbol_table[name] = self.root
        return ctx

class ClassStatement(Statement):
    def __init__(self, name:Reference, query:Query):
        Statement.__init__(self)
        self.name = name
        self.query = query

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'name': self.name.to_dict(),
            'value': self.query.to_dict()
        }

    def eval(self, ctx:Context) -> Context:
        name = self.name.str()
        ctx.symbol_table[name] = self.query
        return ctx
