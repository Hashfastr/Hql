from __future__ import annotations

from Hql.Exceptions import HqlExceptions as hqle
from typing import Union, Optional, TYPE_CHECKING
import re

from . import Compiler

if TYPE_CHECKING:
    import Hql.Operators as Operators
    from Hql.Expressions import Expression
    from Hql.Query import Statement
    from Hql.Compiler import BranchDescriptor
    import Hql.Expressions.Logic as Logic
    import Hql.Expressions.References as References
    from Hql.Expressions import Literals
    from Hql.Functions import Function

KUSTO_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
KUSTO_ESCAPES = {'\\': '\\\\', "'": "\\'", '\n': '\\n', '\r': '\\r', '\t': '\\t'}

class KustoCompiler(Compiler):
    """Compile supported HQL predicates into a Kusto where predicate."""

    def __init__(self) -> None:
        Compiler.__init__(self)
        self.attrs = {
            'nested_objects': True,
            'wildcards': False,
            'wildcard_names': False,
            'complex_names': True,
            'row_reducing': True,
            'regex_matching': True,
            'regex_insensitive': True,
            'regex_multiline': True,
            'regex_dotall': True,
            'regex_global': False
        }
        self.expr:Union[Logic.Logic, None] = None

    @staticmethod
    def quote(value:str) -> str:
        return "'" + ''.join(KUSTO_ESCAPES.get(c, c) for c in value) + "'"

    @staticmethod
    def name(value:str, escape:bool=False) -> str:
        if not escape and KUSTO_IDENTIFIER.match(value):
            return value
        return f'[{KustoCompiler.quote(value)}]'

    def compile(self, src: Union[Expression, Operators.Operator, Statement, Function, None], prep: bool = True) -> tuple[Optional[object], Optional[object]]:
        from Hql.Functions import Function
        from Hql.Expressions.Literals import Bool

        if src is None:
            src = self.expr

        # still missing a root
        if src is None:
            return self.compile(Bool(True), prep=prep)

        if isinstance(src, Function):
            return self.Function(src, prep=prep)

        return super().compile(src, prep=prep)

    def add_op(self, op:Union[Operators.Operator, BranchDescriptor]) -> tuple[Optional[Operators.Operator], Optional[Operators.Operator]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Operator import Operator

        if isinstance(op, BranchDescriptor):
            op = op.get_op()
        acc, rej = super().compile_op(op)

        assert isinstance(acc, (type(None), Operator))
        return acc, rej

    def simple_compile(self) -> str:
        acc, _ = self.compile(None, prep=False)
        assert isinstance(acc, str)
        return acc

    '''
    Operators
    '''

    def Where(self, op:Operators.Where, prep:bool=True) -> tuple[Optional[Operators.Where], Optional[Operators.Where]]:
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BinaryLogic, Logic

        acc, rej = self.compile(op.expr)

        if acc is not None:
            assert isinstance(acc, Logic)
            self.expr = acc if self.expr is None else BinaryLogic([self.expr, acc])
            acc = None

        if rej is not None:
            assert isinstance(rej, Logic)
            rej = Where(rej, op.parameters)

        return acc, rej

    '''
    Logic
    '''

    def BinaryLogic(self, expr: Logic.BinaryLogic, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import BinaryLogic

        if prep:
            rejs = []
            accs = []
            for i in expr:
                acc, rej = self.compile(i)

                if isinstance(i, BinaryLogic) and rej:
                    rejs.append(i)
                    continue

                if acc:
                    accs.append(acc)
                if rej:
                    rejs.append(rej)

            # Cannot salvage
            if rejs and not expr.logic_and:
                return None, expr

            acc = None
            if accs:
                acc = BinaryLogic(accs, logic_and=expr.logic_and)

            rej = None
            if rejs:
                rej = BinaryLogic(rejs, logic_and=expr.logic_and)

            return acc, rej

        exprs = []
        for i in expr.exprs:
            acc, _ = self.compile(i, prep=prep)
            if isinstance(i, BinaryLogic) and i.logic_and != expr.logic_and:
                acc = f'({acc})'
            exprs.append(acc)

        bitok = ' and ' if expr.logic_and else ' or '
        return bitok.join(exprs), None

    def Not(self, expr: Logic.Not, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not, Logic
        from Hql.Expressions.References import Reference
        from Hql.Functions import Function

        if prep:
            acc, rej = self.compile(expr.expr)
            if rej:
                return None, expr
            assert isinstance(acc, (Logic, Reference, Function))
            return Not(acc), None

        inner, _ = self.compile(expr.expr, prep=prep)
        return f'not({inner})', None

    def Equality(self, expr: Logic.Equality, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality
        from Hql.Expressions.Literals import StringLiteral

        if prep:
            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr

                # handles multivalues
                if isinstance(acc, list):
                    rh += acc
                else:
                    rh.append(acc)

            return Equality(expr.lh, rh, expr.cs, expr.neq), None

        lh, _ = self.compile(expr.lh, prep=prep)

        rh = []
        for i in expr.rh:
            acc, rej = self.compile(i, prep=prep)
            if rej:
                raise hqle.CompilerException('Compiling invalid expression, forgot to preprocess?')
            rh.append(acc)

        # =~ and in~ only apply to strings
        ci = not expr.cs and all(isinstance(x, StringLiteral) for x in expr.rh)

        if len(rh) == 1:
            op = ('!' if expr.neq else '=') + ('~' if ci else '=')
            return f'{lh} {op} {rh[0]}', None

        op = ('!in' if expr.neq else 'in') + ('~' if ci else '')
        return f'{lh} {op} ({", ".join(rh)})', None

    def Substring(self, expr: Logic.Substring, prep:bool=True) -> tuple[object, object]:
        if prep:
            for i in expr.rh:
                _, rej = self.compile(i)
                if rej:
                    return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)

        if expr.term:
            op = 'hasprefix' if expr.startswith else 'hassuffix' if expr.endswith else 'has'
        else:
            op = 'startswith' if expr.startswith else 'endswith' if expr.endswith else 'contains'

        if expr.cs:
            op += '_cs'

        rhs = []
        for i in expr.rh:
            rh, _ = self.compile(i, prep=prep)
            rhs.append(rh)

        if len(rhs) == 1:
            neg = '!' if expr.neq else ''
            return f'{lh} {neg}{op} {rhs[0]}', None

        exprs = [f'{lh} {op} {x}' for x in rhs]
        bitok = ' and ' if expr.logic_and else ' or '
        ret = bitok.join(exprs)
        return (f'not({ret})' if expr.neq else f'({ret})'), None

    def Relational(self, expr: Logic.Relational, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Relational, Expression

        if prep:
            acc, rej = self.compile(expr.rh[0])
            if rej:
                return None, expr
            rh = acc
            assert isinstance(rh, Expression)

            return Relational(expr.lh, rh, expr.gt, expr.eq), None

        lh, _ = self.compile(expr.lh, prep=prep)
        rh, _ = self.compile(expr.rh[0], prep=prep)

        op =  '>' if expr.gt else '<'
        op += '=' if expr.eq else ''

        return f'{lh} {op} {rh}', None

    def BetweenEquality(self, expr: Logic.BetweenEquality, prep:bool=True) -> tuple[object, object]:
        if prep:
            for i in (expr.start, expr.end):
                _, rej = self.compile(i)
                if rej:
                    return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)
        start, _ = self.compile(expr.start, prep=prep)
        end, _ = self.compile(expr.end, prep=prep)

        op = '!between' if expr.neq else 'between'
        return f'{lh} {op} ({start} .. {end})', None

    def Regex(self, expr: Logic.Regex, prep:bool=True) -> tuple[object, object]:
        if prep:
            # global has no meaning for a match
            if expr.g:
                return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)

        # RE2 inline flags
        flags = ''.join(f for f, on in (('i', expr.i), ('m', expr.m), ('s', expr.s)) if on)
        pattern = expr.rh.value.decode('utf-8')
        if flags:
            pattern = f'(?{flags}){pattern}'

        return f'{lh} matches regex {self.quote(pattern)}', None

    # only executes static functions on preprocess and sees if we can handle the result
    def Function(self, expr:Function, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import Reference

        if expr.name == 'isnull':
            lh = expr.args[0]
            if not isinstance(lh, Reference):
                return None, expr
            if prep:
                return expr, None

            # Kusto strings are empty rather than null
            name, _ = self.compile(lh, prep=prep)
            return f'isempty({name})', None

        return None, expr

    '''
    Literals
    '''

    def StringLiteral(self, expr: Literals.StringLiteral, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.quote(expr.value.decode('utf-8')), None

    def MultiString(self, expr: Literals.MultiString, prep:bool=True) -> tuple[object, object]:
        return self.StringLiteral(expr, prep=prep)

    def Integer(self, expr: Literals.Integer, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return f'{expr.value}', None

    def Float(self, expr: Literals.Float, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return f'real({expr.value})', None

    def Bool(self, expr: Literals.Bool, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return ('true' if expr.value else 'false'), None

    def Datetime(self, expr: Literals.Datetime, prep:bool=True) -> tuple[object, object]:
        import datetime

        if prep:
            return expr, None
        dt = expr.value.astimezone(datetime.timezone.utc)
        return f'datetime({dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")})', None

    def Multivalue(self, expr: Literals.Multivalue, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Multivalue

        exprs = []
        for i in expr.value:
            acc, rej = self.compile(i, prep=prep)
            if rej:
                return None, expr
            exprs.append(acc)

        if prep:
            return Multivalue(exprs), None

        return exprs, None

    '''
    References
    '''

    def NamedReference(self, expr: References.NamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.name(expr.name), None

    def EscapedNamedReference(self, expr: References.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.name(expr.name, escape=True), None

    # Kusto has no wildcard column matching in predicates
    def Wildcard(self, expr: References.Wildcard, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Path(self, expr: References.Path, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import EscapedNamedReference

        if prep:
            for i in expr.path:
                _, rej = self.compile(i)
                if rej:
                    return None, expr
            return expr, None

        head, _ = self.compile(expr.path[0], prep=prep)
        out = str(head)
        for i in expr.path[1:]:
            part = self.name(i.name, escape=isinstance(i, EscapedNamedReference))
            out += part if part.startswith('[') else f'.{part}'

        return out, None
