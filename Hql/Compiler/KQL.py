from __future__ import annotations

from Hql.Exceptions import HqlExceptions as hqle
from typing import Union, Optional, TYPE_CHECKING
import logging
import copy
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

# Characters that must be backslash escaped in unquoted KQL values and field names
KQL_SPECIAL_CHARS = '\\():<>"*{}'
KQL_WHITESPACE = {'\t': '\\t', '\r': '\\r', '\n': '\\n'}

class KQLCompiler(Compiler):
    """Compile supported HQL predicates into Kibana Query Language."""

    def __init__(self) -> None:
        Compiler.__init__(self)
        self.attrs = {
            'nested_objects': True,
            'wildcards': True,
            'wildcard_names': True,
            'complex_names': True,
            'row_reducing': True,
            'regex_matching': False,
            'regex_insensitive': False,
            'regex_multiline': False,
            'regex_dotall': False,
            'regex_global': False
        }
        self.expr:Union[Logic.Logic, None] = None

    @staticmethod
    def escape(value:str, wildcards:bool=False) -> str:
        out = ''
        for c in value:
            if c in KQL_WHITESPACE:
                out += KQL_WHITESPACE[c]
            elif c in KQL_SPECIAL_CHARS and not (wildcards and c == '*'):
                out += '\\' + c
            else:
                out += c

        # or, and, not are keywords when unquoted
        return re.sub(r'\b(or|and|not)\b', r'\\\1', out, flags=re.IGNORECASE)

    @staticmethod
    def quote(value:str) -> str:
        out = value.replace('\\', '\\\\').replace('"', '\\"')
        for k, v in KQL_WHITESPACE.items():
            out = out.replace(k, v)
        return f'"{out}"'

    # Bare literals and references are free text searches in KQL, not predicates
    @staticmethod
    def is_predicate(expr:object) -> bool:
        from Hql.Expressions.Logic import Logic
        from Hql.Expressions.Literals import Literal
        return isinstance(expr, Logic) and not isinstance(expr, Literal)

    def compile(self, src: Union[Expression, Operators.Operator, Statement, Function, None], prep: bool = True) -> tuple[Optional[object], Optional[object]]:
        from Hql.Functions import Function

        if src is None:
            src = self.expr

        # still missing a root, an empty KQL query matches everything
        if src is None:
            return (None, None) if prep else ('', None)

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

    def Where(self, op:Operators.Where, prep:bool=True) -> tuple[Optional[Operators.Where], Optional[Operators.Where]]:
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BinaryLogic
        from Hql.Expressions.Literals import Bool

        acc, rej = self.compile(op.expr)

        if acc is not None and not self.is_predicate(acc):
            # where true is a no-op, anything else is left to Hql
            if isinstance(acc, Bool) and acc.value:
                acc = None
            else:
                acc, rej = None, op.expr

        if acc is not None:
            self.expr = acc if self.expr is None else BinaryLogic([self.expr, acc])
            acc = None

        if rej is not None:
            rej = Where(rej, op.parameters)

        return acc, rej

    def simple_compile(self) -> str:
        acc, _ = self.compile(None, prep=False)
        assert isinstance(acc, str)
        return acc

    def BinaryLogic(self, expr: Logic.BinaryLogic, prep:bool=True) -> tuple[Union[None, Logic.Logic, str], Union[None, Logic.Logic, str]]:
        from Hql.Expressions.Logic import BinaryLogic

        if prep:
            rejs = []
            accs = []
            for i in expr:
                acc, rej = self.compile(i)

                if isinstance(i, BinaryLogic) and rej:
                    rejs.append(i)
                    continue

                if acc is not None and not self.is_predicate(acc):
                    rejs.append(i)
                    continue

                if acc is not None:
                    accs.append(acc)
                if rej is not None:
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
        ret = bitok.join(exprs)
        return ret, None

    def Not(self, expr: Logic.Not, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not, BinaryLogic

        if prep:
            acc, rej = self.compile(expr.expr)
            if rej or not self.is_predicate(acc):
                return None, expr
            return Not(acc), None

        inner, _ = self.compile(expr.expr, prep=prep)
        assert isinstance(inner, str)

        # not only binds to a single sub query, and can't be stacked
        if isinstance(expr.expr, BinaryLogic) or inner.startswith('not '):
            inner = f'({inner})'

        return f'not {inner}', None

    def Equality(self, expr: Logic.Equality, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality, Not, BasicRange
        from Hql.Expressions.Literals import Literal

        if prep:
            if expr.cs:
                logging.warning('Case sensitive comparison in KQL depends on field mappings')
                logging.warning('For compatibility, assuming agnostic')

            _, rej = self.compile(expr.lh)
            if rej:
                return None, expr

            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr

                # handles multivalues
                if isinstance(acc, list):
                    rh += acc
                elif isinstance(acc, (Literal, BasicRange)):
                    rh.append(acc)
                else:
                    return None, expr

            if not rh:
                return None, expr

            return Equality(expr.lh, rh, expr.cs, expr.neq), None

        # wrap in a not statement
        if expr.neq:
            pos = copy.copy(expr)
            pos.neq = False
            return self.Not(Not(pos), prep=prep)

        lh, _ = self.compile(expr.lh, prep=prep)

        values = []
        clauses = []
        for i in expr.rh:
            if isinstance(i, BasicRange):
                clauses.append(self.range_clause(lh, i))
                continue

            acc, rej = self.compile(i, prep=prep)
            if rej:
                raise hqle.CompilerException('Compiling invalid expression, forgot to preprocess?')
            values.append(acc)

        if values:
            vals = values[0] if len(values) == 1 else f'({" or ".join(values)})'
            clauses.insert(0, f'{lh}: {vals}')

        ret = ' or '.join(clauses)
        if len(clauses) > 1:
            ret = f'({ret})'

        return ret, None

    # only executes static functions on preprocess and sees if we can handle the result
    def Function(self, expr:Function, prep:bool=True) -> tuple[object, object]:
        if expr.name == 'isnull':
            if prep:
                _, rej = self.compile(expr.args[0])
                if rej:
                    return None, expr
                return expr, None

            lh, _ = self.compile(expr.args[0], prep=prep)
            return f'not {lh}: *', None

        return None, expr

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
        return f'{expr.value}', None

    def IP4(self, expr: Literals.IP4, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.quote(expr.str()), None

    def Bool(self, expr: Literals.Bool, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        val = 'true' if expr.value else 'false'
        return val, None

    def Datetime(self, expr: Literals.Datetime, prep:bool=True) -> tuple[object, object]:
        import datetime

        if prep:
            return expr, None
        dt = expr.value.astimezone(datetime.timezone.utc)
        return self.quote(dt.strftime("%Y-%m-%dT%H:%M:%SZ")), None

    # elements are stored as a raw series, so convert them back into literals
    def Multivalue(self, expr: Literals.Multivalue, prep:bool=True) -> tuple[object, object]:
        import datetime
        from Hql.Expressions.Literals import StringLiteral, Bool, Integer, Float, Datetime

        exprs = []
        for i in expr.value.to_list():
            if isinstance(i, bool):
                lit = Bool(i)
            elif isinstance(i, int):
                lit = Integer(i)
            elif isinstance(i, float):
                lit = Float(i)
            elif isinstance(i, str):
                lit = StringLiteral(i)
            elif isinstance(i, datetime.datetime):
                lit = Datetime(i)
            else:
                return None, expr

            acc, rej = self.compile(lit, prep=prep)
            if rej:
                return None, expr
            exprs.append(acc)

        return exprs, None

    def NamedReference(self, expr: References.NamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.escape(expr.name), None

    def EscapedNamedReference(self, expr: References.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.escape(expr.name), None

    def Wildcard(self, expr: References.Wildcard, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None
        return self.escape(expr.name, wildcards=True), None

    def Path(self, expr: References.Path, prep:bool=True) -> tuple[object, object]:
        if prep:
            return expr, None

        parts = []
        for i in expr.path:
            acc, _ = self.compile(i, prep=prep)
            parts.append(acc)

        return '.'.join(parts), None

    def Relational(self, expr: Logic.Relational, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Relational
        from Hql.Expressions.Literals import Literal, Bool

        if prep:
            _, rej = self.compile(expr.lh)
            if rej:
                return None, expr

            acc, rej = self.compile(expr.rh[0])
            if rej or not isinstance(acc, Literal) or isinstance(acc, Bool):
                return None, expr

            return Relational(expr.lh, acc, expr.gt, expr.eq), None

        lh, _ = self.compile(expr.lh, prep=prep)
        rh, _ = self.compile(expr.rh[0], prep=prep)

        op =  '>' if expr.gt else '<'
        op += '=' if expr.eq else ''

        return f'{lh} {op} {rh}', None

    def BetweenEquality(self, expr: Logic.BetweenEquality, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import BasicRange, Equality

        # case sensitivity is meaningless for ranges
        new = Equality(expr.lh, BasicRange(expr.start, expr.end), False, expr.neq)
        return self.compile(new, prep=prep)

    def BasicRange(self, expr: Logic.BasicRange, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Literal

        if prep:
            for i in (expr.start, expr.end):
                acc, rej = self.compile(i)
                if rej or not isinstance(acc, Literal):
                    return None, expr
            return expr, None

        raise hqle.CompilerException('KQL ranges must be compiled as part of an equality')

    def range_clause(self, lh:str, expr:Logic.BasicRange) -> str:
        start, _ = self.compile(expr.start, prep=False)
        end, _ = self.compile(expr.end, prep=False)
        return f'({lh} >= {start} and {lh} <= {end})'

    # KQL has no regex support
    def Regex(self, expr: Logic.Regex, prep:bool=True) -> tuple[object, object]:
        return None, expr

    def Substring(self, expr: Logic.Substring, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not
        from Hql.Expressions.Literals import StringLiteral

        if prep:
            _, rej = self.compile(expr.lh)
            if rej:
                return None, expr

            for i in expr.rh:
                if not isinstance(i, StringLiteral):
                    return None, expr

                # KQL trims leading and trailing whitespace from unquoted values
                value = i.value.decode('utf-8')
                if expr.startswith and value.startswith(' '):
                    return None, expr
                if not expr.startswith and expr.endswith and value.endswith(' '):
                    return None, expr

            return expr, None

        # wrap in a not statement
        if expr.neq:
            pos = copy.copy(expr)
            pos.neq = False
            return self.Not(Not(pos), prep=prep)

        lh, _ = self.compile_expr(expr.lh, prep=prep)

        patterns = []
        for i in expr.rh:
            assert isinstance(i, StringLiteral)
            value = i.value.decode('utf-8')

            # every string contains the empty string
            if not value:
                if expr.logic_and:
                    continue
                patterns = []
                break

            rh = self.escape(value)

            if expr.startswith:
                rh = f'{rh}*'
            elif expr.endswith:
                rh = f'*{rh}'
            else:
                rh = f'*{rh}*'

            patterns.append(rh)

        if not patterns:
            patterns = ['*']

        op = ' and ' if expr.logic_and else ' or '
        vals = patterns[0] if len(patterns) == 1 else f'({op.join(patterns)})'

        return f'{lh}: {vals}', None
