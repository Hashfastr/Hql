from __future__ import annotations

from Hql.Exceptions import HqlExceptions as hqle
from typing import Union, Optional, TYPE_CHECKING
import Hql.Expressions.References as References

from . import Compiler

if TYPE_CHECKING:
    import Hql.Operators as Operators
    from Hql.Expressions import Expression
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Query import Statement
    from Hql.Compiler import BranchDescriptor
    import Hql.Expressions.Logic as Logic
    from Hql.Expressions import Literals
    from Hql.Functions import Function

import ipaddress
import re

# Where Kusto's ipv6 functions place IPv4 addresses
KUSTO_IPV4_MAPPED = ipaddress.ip_network('::ffff:0:0/96')

# Hql functions with the same semantics in KQL, by their KQL name.
# Each converts what it can't parse to null, as Hql's do.
KUSTO_FUNCTIONS = {
    'iff': 'iff',
    'toint': 'toint',
    'tostring': 'tostring',
    'todouble': 'todouble',
    'tofloat': 'toreal',
}

# Escapes for a regular (non-verbatim) KQL string literal
KUSTO_ESCAPES = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\r': '\\r', '\t': '\\t'}

def kql_string(value:str) -> str:
    return '"' + ''.join(KUSTO_ESCAPES.get(c, c) for c in value) + '"'

# Names that need no quoting, anything else goes in ['...']
KQL_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')

def kql_quoted_name(name:str) -> str:
    return "['" + name.replace('\\', '\\\\').replace("'", "\\'") + "']"

def kql_name(name:str) -> str:
    return name if KQL_IDENTIFIER.fullmatch(name) else kql_quoted_name(name)

def kql_verbatim(value:str) -> str:
    # In @"..." only a quote needs escaping, by doubling it
    return '@"' + value.replace('"', '""') + '"'

class KustoCompiler(Compiler):
    """Compile supported HQL predicates into a Kusto where predicate."""

    def __init__(self) -> None:
        Compiler.__init__(self)
        self.attrs = {
            'nested_objects': True,
            'indexing': True,
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

        # What the ops are piped onto: a table, or raw KQL as given
        self.tabular:str|References.Reference|Operators.Union|None = None
        self.ops:list[Operators.Operator] = []

        # Columns the pushed operators have taken away. KQL fails on a reference to one,
        # where Hql sees a missing field, so anything that references one stays local.
        self.removed:set[str] = set()
        # The only columns left after a pushed project, None before one
        self.kept:Optional[set[str]] = None

    def add_index(self, name:str|StringLiteral|References.Reference):
        from Hql.Expressions.Literals import StringLiteral

        if isinstance(name, StringLiteral):
            name = name.str()
        if isinstance(name, str):
            name = References.NamedReference(name)

        self.tabular = name

    def add_raw(self, query:str):
        self.tabular = query

    def compile(self, src: Union[Expression, Operators.Operator, Statement, Function, None], prep: bool = True) -> tuple[Optional[object], Optional[object]]:
        # root compile case
        if not prep and src is None:
            assert self.tabular is not None

            if isinstance(self.tabular, str):
                query = self.tabular
            elif isinstance(self.tabular, References.NamedReference):
                query = kql_name(self.tabular.name)
            else:
                query = self.tabular.deparse()
            for i in self.ops:
                acc, _ = self.compile(i, prep=prep)
                query += f'\n| {acc}'
            return query, None

        # Comparisons only preprocess their right hand side, check the field they read too
        lh = getattr(src, 'lh', None)
        if prep and isinstance(lh, (References.Reference, References.Element)):
            _, rej = self.compile(lh)
            if rej is not None:
                return None, src

        return Compiler.compile(self, src, prep=prep)

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
        from Hql.Expressions.Logic import Logic

        acc, rej = self.compile(op.expr, prep=prep)

        if not prep:
            assert isinstance(acc, str)
            return 'where ' + acc, None

        if acc is not None:
            assert isinstance(acc, Logic)
            acc = Where(acc)
            self.ops.append(acc)

        if rej is not None:
            assert isinstance(rej, Logic)
            rej = Where(rej, op.parameters)

        return acc, rej

    def Take(self, op:Operators.Take, prep:bool=True) -> tuple[object, object]:
        if not prep:
            limit, _ = self.compile(op.expr, prep=prep)
            return f'take {limit}', None

        if op.tables:
            return None, op

        self.ops.append(op)
        return op, None

    def available(self, name:str) -> bool:
        return name not in self.removed and (self.kept is None or name in self.kept)

    def provide(self, name:str):
        self.removed.discard(name)
        if self.kept is not None:
            self.kept.add(name)

    def track(self, op:Operators.Operator):
        '''Updates the columns left after a pushed operator.'''
        from Hql.Expressions.References import NamedExpression

        if op.type == 'Project':
            self.kept = set()
            self.removed = set()

        new = set()
        old = set()
        for i in getattr(op, 'exprs'):
            if isinstance(i, NamedExpression):
                new.add(getattr(i.paths[0], 'name'))
                if op.type == 'ProjectRename':
                    old.add(getattr(i.value, 'name'))
            elif op.type == 'Project':
                new.add(getattr(i, 'name'))

        for i in old - new:
            self.removed.add(i)
            if self.kept is not None:
                self.kept.discard(i)
        for i in new:
            self.provide(i)

    def column(self, ref:object) -> Optional[str]:
        '''
        A KQL column name for an assignment target or rename source, None if it isn't one.
        Paths into dynamic columns can be read but not assigned or renamed.
        '''
        if not isinstance(ref, References.NamedReference) or isinstance(ref, References.Wildcard):
            return None
        name, _ = self.compile(ref, prep=False)
        assert isinstance(name, str)
        return name

    def assignments(self, exprs, allow_bare:bool, prep:bool) -> Optional[list[str]]:
        '''
        Compiles name = value pairs, and bare columns when allowed.
        None if any of them can't be expressed, the whole operator then stays local.
        '''
        from Hql.Expressions.References import NamedExpression

        out = []
        for i in exprs:
            if not isinstance(i, NamedExpression):
                name = self.column(i)
                if not allow_bare or name is None:
                    return None
                if prep and not self.available(getattr(i, 'name')):
                    return None
                out.append(name)
                continue

            if len(i.paths) != 1:
                return None
            name = self.column(i.paths[0])
            if name is None:
                return None

            # Checked against the columns before this operator, only while preprocessing
            if prep:
                _, rej = self.compile(i.value)
                if rej is not None:
                    return None
            value, _ = self.compile(i.value, prep=False)
            out.append(f'{name} = {value}')
        return out

    def assigning_op(self, op:Operators.Operator, optok:str, allow_bare:bool, prep:bool) -> tuple[object, object]:
        exprs = self.assignments(getattr(op, 'exprs'), allow_bare, prep)
        if exprs is None or not exprs:
            return None, op

        if not prep:
            return f'{optok} ' + ', '.join(exprs), None

        self.track(op)
        self.ops.append(op)
        return op, None

    def Extend(self, op:Operators.Extend, prep:bool=True) -> tuple[object, object]:
        return self.assigning_op(op, 'extend', False, prep)

    def Project(self, op:Operators.Project, prep:bool=True) -> tuple[object, object]:
        return self.assigning_op(op, 'project', True, prep)

    def ProjectRename(self, op:Operators.ProjectRename, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression

        # KQL renames columns only, not values or paths into dynamic columns
        for i in op.exprs:
            if isinstance(i, NamedExpression) and self.column(i.value) is None:
                return None, op
        return self.assigning_op(op, 'project-rename', True, prep)

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
        return f'{lh} matches regex {kql_verbatim(pattern)}', None

    # only executes static functions on preprocess and sees if we can handle the result
    def Function(self, expr:Function, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import Reference

        if expr.name == 'isnull':
            lh = expr.args[0]
            if not isinstance(lh, Reference) or (prep and self.compile(lh)[1] is not None):
                return None, expr
            if prep:
                return expr, None

            # Kusto strings are empty rather than null
            name, _ = self.compile(lh, prep=prep)
            return f'isempty({name})', None

        if expr.name in KUSTO_FUNCTIONS:
            if prep:
                for i in expr.args:
                    _, rej = self.compile(i)
                    if rej is not None:
                        return None, expr
                return expr, None

            args = [str(self.compile(x, prep=prep)[0]) for x in expr.args]
            return f'{KUSTO_FUNCTIONS[expr.name]}({", ".join(args)})', None

        from Hql.Functions.ip_range import ip_is_in_range
        if isinstance(expr, ip_is_in_range):
            from Hql.Expressions.Literals import StringLiteral

            lh, cidr = expr.args
            if not isinstance(lh, Reference) or not isinstance(cidr, StringLiteral):
                return None, expr
            if prep and self.compile(lh)[1] is not None:
                return None, expr
            # Kusto reads IPv4 addresses as IPv4-mapped IPv6, so they'd match ranges over ::ffff:0:0/96
            if expr.version == 6 and expr.network.overlaps(KUSTO_IPV4_MAPPED):
                return None, expr
            if prep:
                return expr, None

            name, _ = self.compile(lh, prep=prep)
            rh, _ = self.compile(cidr, prep=prep)
            # Kusto gives null for a value that isn't an address of that version, Hql gives false.
            # A bare null would null out a surrounding not() or 'or' and drop the row.
            return f'coalesce({expr.name}({name}, {rh}), false)', None

        return None, expr

    '''
    Literals
    '''

    def StringLiteral(self, expr: Literals.StringLiteral, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        # The literal's own quoting escapes for Hql, not KQL
        return kql_string(expr.value.decode('utf-8')), None

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
            if not self.available(expr.name):
                return None, expr
            return expr, None
        return kql_name(expr.name), None

    def EscapedNamedReference(self, expr: References.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return self.NamedReference(expr, prep=prep)
        # Escaped in Hql for a reason, possibly a KQL keyword too
        return kql_quoted_name(expr.name), None

    # Kusto has no wildcard column matching in predicates
    def Wildcard(self, expr: References.Wildcard, prep:bool=True) -> tuple[object, object]:
        return expr.deparse(), None

    def Path(self, expr: References.Path, prep:bool=True) -> tuple[object, object]:
        if prep:
            for i in expr.path:
                _, rej = self.compile(i)
                if rej:
                    return None, expr
            return expr, None

        # The first name is the column, the rest index into it
        out = ''
        for i in expr.path:
            name, _ = self.compile(i, prep=prep)
            assert isinstance(name, str)
            if not out:
                out = name
            elif name.startswith('['):
                out += name
            else:
                out += '.' + name
        return out, None

    def Element(self, expr: References.Element, prep:bool=True) -> tuple[object, object]:
        if prep:
            _, rej = self.compile(expr.base)
            if rej is not None:
                return None, expr
            try:
                expr.index()
            except hqle.QueryException:
                return None, expr
            return expr, None

        base, _ = self.compile(expr.base, prep=prep)
        assert isinstance(base, str)
        idx = expr.index()
        if isinstance(idx, int):
            return f'{base}[{idx}]', None
        if KQL_IDENTIFIER.fullmatch(idx):
            return f'{base}.{idx}', None
        return base + kql_quoted_name(idx), None
