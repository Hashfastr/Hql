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
    from sqlalchemy.sql import Select

# Leading inline flags, e.g. (?i), which postgres only accepts at the start of a pattern
REGEX_INLINE_FLAGS = re.compile(r'^\(\?([a-zA-Z]+)\)')
# Named groups and scoped flags have no postgres equivalent
REGEX_UNSUPPORTED = re.compile(r'\(\?[a-zA-Z]|\(\?<[a-zA-Z]')
# Python/Rust escapes that are spelled differently in postgres AREs
REGEX_ESCAPES = {'b': '\\y', 'B': '\\Y', 'z': '\\Z'}

class PostgresCompiler(Compiler):
    """Compile supported HQL pipelines into PostgreSQL using SQLAlchemy."""

    def __init__(self, table:Optional[str]=None) -> None:
        from sqlalchemy.dialects import postgresql
        Compiler.__init__(self)
        self.attrs = {
            'nested_objects': True,
            'wildcards': True,
            'wildcard_names': False,
            'complex_names': True,
            'row_reducing': True,
            'regex_matching': True,
            'regex_insensitive': True,
            'regex_multiline': True,
            'regex_dotall': True,
            'regex_global': True
        }

        # named paramstyle keeps % from being doubled in rendered literals
        self.dialect = postgresql.dialect(paramstyle='named')

        self.stmt:Optional[Select] = None
        self.limit:Optional[int] = None
        self.projected = False
        self.ops_added = False

        if table:
            self.set_table(table)

    def set_table(self, name:str) -> None:
        from sqlalchemy import select, table, literal_column

        if self.ops_added:
            raise hqle.CompilerException('Cannot change PostgreSQL table after operators have been added')

        schema, _, tname = name.rpartition('.')
        source = table(tname, schema=schema if schema else None)
        self.stmt = select(literal_column('*')).select_from(source)

    def statement(self) -> Select:
        if self.stmt is None:
            raise hqle.CompilerException('No table set for PostgreSQL query')
        return self.stmt

    # Wraps the current statement so following clauses apply to its output
    def wrap(self) -> None:
        from sqlalchemy import select, literal_column

        self.stmt = select(literal_column('*')).select_from(self.statement().subquery())
        self.limit = None
        self.projected = False

    def render(self) -> str:
        compiled = self.statement().compile(dialect=self.dialect, compile_kwargs={'literal_binds': True})
        return str(compiled)

    def compile(self, src: Union[Expression, Operators.Operator, Statement, Function, None], prep: bool = True) -> tuple[Optional[object], Optional[object]]:
        from Hql.Functions import Function

        if src is None:
            if prep:
                return self.statement(), None
            return self.render(), None

        if isinstance(src, Function):
            return self.Function(src, prep=prep)

        return super().compile(src, prep=prep)

    def add_op(self, op:Union[Operators.Operator, BranchDescriptor]) -> tuple[Optional[Operators.Operator], Optional[Operators.Operator]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Operator import Operator

        if isinstance(op, BranchDescriptor):
            op = op.get_op()

        self.statement()
        self.ops_added = True
        acc, rej = super().compile_op(op)

        assert isinstance(acc, (type(None), Operator))
        return acc, rej

    def simple_compile(self) -> str:
        acc, _ = self.compile(None, prep=False)
        assert isinstance(acc, str)
        return acc

    @staticmethod
    def is_predicate(expr:object) -> bool:
        from Hql.Expressions.Logic import Logic
        return isinstance(expr, Logic)

    @staticmethod
    def is_column(expr:object) -> bool:
        from Hql.Expressions.References import NamedReference, Wildcard, Path

        # paths map to flattened, dotted column names
        if isinstance(expr, Path):
            return all(PostgresCompiler.is_column(x) for x in expr.path)
        return isinstance(expr, NamedReference) and not isinstance(expr, Wildcard)

    @staticmethod
    def like_escape(value:str) -> str:
        return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    @staticmethod
    def translate_regex(pattern:str, i:bool, m:bool, s:bool) -> Optional[str]:
        match = REGEX_INLINE_FLAGS.match(pattern)
        if match:
            flags = match.group(1)
            if set(flags) - set('imsx'):
                return None
            i, m, s = i or 'i' in flags, m or 'm' in flags, s or 's' in flags
            x = 'x' in flags
            pattern = pattern[match.end():]
        else:
            x = False

        if REGEX_UNSUPPORTED.search(pattern):
            return None

        out = ''
        idx = 0
        while idx < len(pattern):
            c = pattern[idx]
            if c == '\\' and idx + 1 < len(pattern):
                n = pattern[idx + 1]
                # unicode classes aren't supported
                if n in 'pP':
                    return None
                out += REGEX_ESCAPES.get(n, c + n)
                idx += 2
                continue
            out += c
            idx += 1

        # postgres defaults to . matching newlines and ^$ only matching the string ends
        if m:
            newline = 'w' if s else 'n'
        else:
            newline = '' if s else 'p'

        opts = ('i' if i else '') + ('x' if x else '') + newline
        if opts:
            out = f'(?{opts})' + out

        return out

    def Where(self, op:Operators.Where, prep:bool=True) -> tuple[Optional[Operators.Where], Optional[Operators.Where]]:
        from Hql.Operators.Where import Where

        acc, rej = self.compile(op.expr)

        if acc is not None and not self.is_predicate(acc):
            acc, rej = None, op.expr

        if acc is not None:
            clause, _ = self.compile(acc, prep=False)

            # WHERE runs before LIMIT and can't see projected aliases
            if self.limit is not None or self.projected:
                self.wrap()

            self.stmt = self.statement().where(clause)
            acc = None

        if rej is not None:
            rej = Where(rej, op.parameters)

        return acc, rej

    def Take(self, op:Operators.Take, prep:bool=True) -> tuple[object, object]:
        if op.tables:
            return None, op

        self.add_limit(op.expr.value)
        return None, None

    def add_limit(self, limit:int) -> None:
        self.limit = limit if self.limit is None else min(self.limit, limit)
        self.stmt = self.statement().limit(self.limit)

    def Sort(self, op:Operators.Sort, prep:bool=True) -> tuple[object, object]:
        clauses = self.order_by(op.exprs)
        if clauses is None:
            return None, op

        # ORDER BY runs before LIMIT
        if self.limit is not None:
            self.wrap()

        # a later sort replaces an earlier one
        self.stmt = self.statement().order_by(None).order_by(*clauses)
        return None, None

    def Top(self, op:Operators.Top, prep:bool=True) -> tuple[object, object]:
        clauses = self.order_by(op.by)
        if clauses is None:
            return None, op

        if self.limit is not None:
            self.wrap()

        self.stmt = self.statement().order_by(None).order_by(*clauses)
        self.add_limit(op.expr.value)
        return None, None

    def order_by(self, exprs:list) -> Optional[list]:
        clauses = []
        for i in exprs:
            if not self.is_column(i.expr):
                return None

            col, _ = self.compile(i.expr, prep=False)
            col = col.desc() if i.order == 'desc' else col.asc()
            col = col.nulls_last() if i.nulls == 'last' else col.nulls_first()
            clauses.append(col)

        return clauses

    def Project(self, op:Operators.Project, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.References import NamedExpression
        from Hql.Expressions.Literals import Literal, Multivalue

        cols = []
        for i in op.exprs:
            if self.is_column(i):
                acc, _ = self.compile(i, prep=False)
                cols.append(acc)
                continue

            if not isinstance(i, NamedExpression) or len(i.paths) != 1 or not self.is_column(i.paths[0]):
                return None, op

            value = i.value
            if not (self.is_column(value) or isinstance(value, Literal)) or isinstance(value, Multivalue):
                return None, op

            acc, _ = self.compile(value, prep=False)
            cols.append(acc.label(i.paths[0].name))

        # projected names may shadow source columns
        if self.projected:
            self.wrap()

        self.stmt = self.statement().with_only_columns(*cols)
        self.projected = True
        return None, None

    def BinaryLogic(self, expr: Logic.BinaryLogic, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import BinaryLogic
        from sqlalchemy import and_, or_

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

        clauses = [self.compile(x, prep=prep)[0] for x in expr.exprs]
        return (and_(*clauses) if expr.logic_and else or_(*clauses)), None

    def Not(self, expr: Logic.Not, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not
        from sqlalchemy import not_

        if prep:
            acc, rej = self.compile(expr.expr)
            if rej or not self.is_predicate(acc):
                return None, expr
            return Not(acc), None

        inner, _ = self.compile(expr.expr, prep=prep)
        return not_(inner), None

    def Equality(self, expr: Logic.Equality, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality, BasicRange
        from Hql.Expressions.Literals import Literal, StringLiteral
        from sqlalchemy import func, not_, or_

        if prep:
            if not self.is_column(expr.lh):
                return None, expr

            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr

                # handles multivalues
                if isinstance(acc, list):
                    rh += acc
                elif isinstance(acc, (Literal, BasicRange)) or self.is_column(acc):
                    rh.append(acc)
                else:
                    return None, expr

            if not rh:
                return None, expr

            return Equality(expr.lh, rh, expr.cs, expr.neq), None

        lh, _ = self.compile(expr.lh, prep=prep)

        values = []
        lowered = []
        clauses = []
        for i in expr.rh:
            if isinstance(i, StringLiteral) and not expr.cs:
                lowered.append(i.value.decode('utf-8').lower())
                continue

            # ranges come from other compilers' rewrites of between
            if isinstance(i, BasicRange):
                start, _ = self.compile(i.start, prep=prep)
                end, _ = self.compile(i.end, prep=prep)
                clauses.append(lh.between(start, end))
                continue

            acc, _ = self.compile(i, prep=prep)
            if self.is_column(i):
                clauses.append(lh == acc if expr.cs else func.lower(lh) == func.lower(acc))
            else:
                values.append(acc)

        if values:
            clauses.insert(0, lh == values[0] if len(values) == 1 else lh.in_(values))

        if lowered:
            low = func.lower(lh)
            clauses.insert(0, low == lowered[0] if len(lowered) == 1 else low.in_(lowered))

        clause = clauses[0] if len(clauses) == 1 else or_(*clauses)
        return (not_(clause) if expr.neq else clause), None

    def Relational(self, expr: Logic.Relational, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Literal, Multivalue, Bool
        import operator

        if prep:
            if not self.is_column(expr.lh):
                return None, expr

            rh = expr.rh[0]
            if self.is_column(rh):
                return expr, None
            if not isinstance(rh, Literal) or isinstance(rh, (Multivalue, Bool)):
                return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)
        rh, _ = self.compile(expr.rh[0], prep=prep)

        if expr.gt:
            op = operator.ge if expr.eq else operator.gt
        else:
            op = operator.le if expr.eq else operator.lt

        return op(lh, rh), None

    def BetweenEquality(self, expr: Logic.BetweenEquality, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Literal, Multivalue
        from sqlalchemy import not_

        if prep:
            if not self.is_column(expr.lh):
                return None, expr
            for i in (expr.start, expr.end):
                if not isinstance(i, Literal) or isinstance(i, Multivalue):
                    return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)
        start, _ = self.compile(expr.start, prep=prep)
        end, _ = self.compile(expr.end, prep=prep)

        clause = lh.between(start, end)
        return (not_(clause) if expr.neq else clause), None

    def BasicRange(self, expr: Logic.BasicRange, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import Literal, Multivalue

        if prep:
            for i in (expr.start, expr.end):
                if not isinstance(i, Literal) or isinstance(i, Multivalue):
                    return None, expr
            return expr, None

        raise hqle.CompilerException('PostgreSQL ranges must be compiled as part of an equality')

    def Substring(self, expr: Logic.Substring, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import StringLiteral
        from sqlalchemy import and_, or_, not_

        if prep:
            if not self.is_column(expr.lh):
                return None, expr
            for i in expr.rh:
                if not isinstance(i, StringLiteral):
                    return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)

        clauses = []
        for i in expr.rh:
            assert isinstance(i, StringLiteral)
            value = i.value.decode('utf-8')

            if expr.term:
                clauses.append(self.term_match(lh, value, expr))
                continue

            pattern = self.like_escape(value)
            if expr.startswith:
                pattern = f'{pattern}%'
            elif expr.endswith:
                pattern = f'%{pattern}'
            else:
                pattern = f'%{pattern}%'

            if expr.cs:
                clauses.append(lh.like(pattern, escape='\\'))
            else:
                clauses.append(lh.ilike(pattern, escape='\\'))

        clause = and_(*clauses) if expr.logic_and else or_(*clauses)
        return (not_(clause) if expr.neq else clause), None

    # SQL has no term index, approximate with postgres word boundaries
    def term_match(self, lh, value:str, expr:Logic.Substring):
        pattern = re.escape(value)

        if value[:1].isalnum() and not expr.endswith:
            pattern = '\\m' + pattern
        if value[-1:].isalnum() and not expr.startswith:
            pattern = pattern + '\\M'

        if not expr.cs:
            pattern = '(?i)' + pattern

        return lh.regexp_match(pattern)

    def Regex(self, expr: Logic.Regex, prep:bool=True) -> tuple[object, object]:
        if prep:
            if not self.is_column(expr.lh):
                return None, expr
            if self.translate_regex(expr.rh.value.decode('utf-8'), expr.i, expr.m, expr.s) is None:
                return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=prep)
        pattern = self.translate_regex(expr.rh.value.decode('utf-8'), expr.i, expr.m, expr.s)
        assert pattern is not None

        return lh.regexp_match(pattern), None

    # only executes static functions on preprocess and sees if we can handle the result
    def Function(self, expr:Function, prep:bool=True) -> tuple[object, object]:
        if expr.name == 'isnull':
            if prep:
                if not self.is_column(expr.args[0]):
                    return None, expr
                return expr, None

            lh, _ = self.compile(expr.args[0], prep=prep)
            return lh.is_(None), None

        return None, expr

    def StringLiteral(self, expr: Literals.StringLiteral, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import literal, String

        if prep:
            return expr, None
        return literal(expr.value.decode('utf-8'), String), None

    def MultiString(self, expr: Literals.MultiString, prep:bool=True) -> tuple[object, object]:
        return self.StringLiteral(expr, prep=prep)

    def Integer(self, expr: Literals.Integer, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import literal

        if prep:
            return expr, None
        return literal(expr.value), None

    def Float(self, expr: Literals.Float, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import literal

        if prep:
            return expr, None
        return literal(expr.value), None

    def IP4(self, expr: Literals.IP4, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import literal, String

        if prep:
            return expr, None
        return literal(expr.str(), String), None

    def Bool(self, expr: Literals.Bool, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import true, false

        if prep:
            return expr, None
        return (true() if expr.value else false()), None

    def Datetime(self, expr: Literals.Datetime, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import literal, DateTime
        import datetime

        if prep:
            return expr, None
        dt = expr.value.astimezone(datetime.timezone.utc)
        return literal(dt, DateTime(timezone=True)), None

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
        from sqlalchemy import column

        if prep:
            return expr, None
        return column(expr.name), None

    def EscapedNamedReference(self, expr: References.EscapedNamedReference, prep:bool=True) -> tuple[object, object]:
        return self.NamedReference(expr, prep=prep)

    # column wildcards have no direct SQL equivalent
    def Wildcard(self, expr: References.Wildcard, prep:bool=True) -> tuple[object, object]:
        return None, expr

    # nested fields are expected as flattened columns, e.g. "process.executable"
    def Path(self, expr: References.Path, prep:bool=True) -> tuple[object, object]:
        from sqlalchemy import column

        if not self.is_column(expr):
            return None, expr
        if prep:
            return expr, None
        return column('.'.join(x.name for x in expr.path)), None
