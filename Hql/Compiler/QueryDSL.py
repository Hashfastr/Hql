from __future__ import annotations

from Hql.Exceptions import HqlExceptions as hqle
from typing import Union, Optional, TYPE_CHECKING

from . import Compiler

if TYPE_CHECKING:
    import Hql.Operators as Operators
    from Hql.Expressions import Expression
    from Hql.Query import Statement
    from Hql.Compiler import BranchDescriptor
    import Hql.Expressions.Logic as Logic
    import Hql.Expressions.References as References
    from Hql.Expressions import Literals, Operator
    from Hql.Functions import Function

class QueryDSLCompiler(Compiler):
    """Compile supported HQL predicates into Elasticsearch Query DSL."""

    def __init__(self) -> None:
        Compiler.__init__(self)
        self.attrs = {
            'nested_objects': True,
            'wildcards': True,
            'wildcard_names': True,
            'complex_names': True,
            'row_reducing': True,
            'regex_matching': True,
            'regex_insensitive': False,
            'regex_multiline': False,
            'regex_dotall': False,
            'regex_global': False
        }
        self.expr:Optional[Logic.Logic] = None

    def compile(self, src: Union[Expression, Operators.Operator, Statement, Function, None], prep: bool = True) -> tuple[Optional[object], Optional[object]]:
        from Hql.Functions import Function
        from Hql.Expressions.Literals import Bool

        if src == None:
            src = self.expr

        # still missing a root
        if src == None:
            return self.compile(Bool(True), prep=prep)

        if isinstance(src, Function):
            return self.Function(src, prep=prep), None

        return super().compile(src, prep=prep)

    def add_op(self, op:Union[Operator, BranchDescriptor]) -> tuple[Optional[Operator], Optional[Operator]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Operator import Operator

        if isinstance(op, BranchDescriptor):
            op = op.get_op()
        acc, rej = super().compile_op(op)
        
        assert isinstance(acc, (type(None), Operator))
        return acc, rej

    def simple_compile(self) -> dict:
        acc, _ = self.compile(None, prep=False)
        assert isinstance(acc, dict)
        return acc

    def Where(self, op:Operators.Where, prep:bool=True) -> tuple[Optional[Operators.Where], Optional[Operators.Where]]:
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BinaryLogic, Logic

        acc, rej = self.compile(op.expr)

        if acc != None:
            assert isinstance(acc, Logic)
            self.expr = acc if self.expr is None else BinaryLogic([self.expr, acc])
            acc = Where(acc, op.parameters)

        if rej != None:
            assert isinstance(rej, Logic)
            rej = Where(rej, op.parameters)
        
        return acc, rej
        
    def BinaryLogic(self, expr: Logic.BinaryLogic, prep: bool = True) -> tuple[Union[None, Logic.Logic, dict], Union[None, Logic.Logic]]:
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
        for i in expr:
            acc, _ = self.compile(i, prep=prep)
            exprs.append(acc)

        if expr.logic_and:
            ret = {'must': exprs}
        else:
            ret = {'should': exprs}
            
        return {'bool': ret}, None

    def Not(self, expr: Logic.Not, prep: bool = True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Not
        from Hql.Expressions import Function

        if prep:
            if isinstance(expr.expr, Function):
                return None, expr

            acc, rej = self.compile(expr.expr)
            if rej:
                return None, expr
            assert isinstance(acc, (Logic.Logic, References.Reference))
            return Not(acc), None

        inner, _ = self.compile(expr.expr, prep=prep)

        if isinstance(inner, dict):
            if 'must' in inner and len(inner) == 1:
                out = {'must_not': inner.pop('must')}
            else:
                out = {'must_not': inner}
        else:
            out = {'must_not': inner}

        out = {'bool': out}

        return out, None

    def Equality(self, expr: Logic.Equality, prep: bool = True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Equality, Not

        if prep:
            rh = []
            for i in expr.rh:
                acc, rej = self.compile(i)
                if rej:
                    return None, expr

                if isinstance(acc, list):
                    rh += acc
                else:
                    rh.append(acc)

            return Equality(expr.lh, rh, expr.cs, expr.neq), None

        # wrap in a not statement
        if expr.neq:
            expr.neq = False
            return self.Not(Not(expr), prep=prep)

        lh, _ = self.compile(expr.lh, prep=prep)

        rh = []
        for i in expr.rh:
            acc, rej = self.compile(i, prep=False)
            if rej:
                raise hqle.CompilerException('Compiling invalid expression, forgot to preprocess?')
            rh.append(acc)        

        term = 'term' if len(rh) == 1 else 'terms'
        return {term: {lh: rh[0]}}, None

    # only executes static functions on preprocess and sees if we can handle the result
    def Function(self, expr:Function, prep:bool=True) -> tuple[object, object]:
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.Logic import Regex, Not
        from Hql.Expressions.References import Reference

        if expr.name == 'isnull':
            lh = expr.args[0]
            assert isinstance(lh, Reference)
            rexpr = Regex(lh, StringLiteral('.*'))
            rexpr = Not(rexpr)
            return self.compile(rexpr, prep=prep)

        return None, expr

    def StringLiteral(self, expr: Literals.StringLiteral, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.quote(''), None

    def MultiString(self, expr: Literals.MultiString, prep:bool=True) -> tuple[object, object]:
        return self.StringLiteral(expr, prep=prep)

    def Integer(self, expr: Literals.Integer, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.value, None

    def Float(self, expr: Literals.Float, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.value, None

    def Bool(self, expr: Literals.Bool, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.value, None

    def Datetime(self, expr: Literals.Datetime, prep:bool = True) -> tuple[object, object]:
        import datetime

        if prep:
            return expr, None
        dt = expr.value.astimezone(datetime.timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), None

    def Multivalue(self, expr: Literals.Multivalue, prep:bool = True) -> tuple[object, object]:
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

    def NamedReference(self, expr: References.NamedReference, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.name, None

    def EscapedNamedReference(self, expr: References.EscapedNamedReference, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None
        return expr.name, None

    def Path(self, expr: References.Path, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None

        parts = []
        for i in expr.path:
            acc, _ = self.compile(i, prep=prep)
            parts.append(acc)

        return '.'.join(parts), None

    def Relational(self, expr: Logic.Relational, prep:bool = True) -> tuple[object, object]:
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
        op =  'g'  if expr.gt else 'l'
        op += 'te' if expr.eq else 't'

        return {'range': {lh: {op: rh}}}, None

    def BetweenEquality(self, expr: Logic.BetweenEquality, prep:bool = True) -> tuple[object, object]:
        from Hql.Expressions.Logic import BasicRange

        if prep:
            return expr, None

        lh, _ = self.compile(expr.lh, prep=False)
        rh, _ = self.compile(BasicRange(expr.start, expr.end), prep=False)

        ret = {'range': {lh: rh}}
        if expr.neq:
            ret = {'bool': {'must_not': ret}}

        return ret, None

    def BasicRange(self, expr: Logic.BasicRange, prep:bool = True) -> tuple[object, object]:
        if prep:
            return expr, None

        start, _ = self.compile(expr.start, prep=False)
        end, _ = self.compile(expr.end, prep=False)

        return {'gte': start, 'lte': end}, None

    def Regex(self, expr: Logic.Regex, prep:bool = True) -> tuple[object, object]:
        if prep:
            # No flags supported
            if expr.m or expr.s or expr.g:
                return None, expr
            return expr, None

        lh, _ = self.compile(expr.lh, prep=False)
        rh, _ = self.compile(expr.rh, prep=False)

        ret = {
            'regexp': {
                lh: {
                    'value': rh,
                    'flags': 'ALL',
                    'case_insensitive': expr.i,
                }
            }
        }

        return ret, None

    def Substring(self, expr: Logic.Substring, prep:bool = True) -> tuple[object, object]:
        from Hql.Expressions.Logic import Regex
        from Hql.Expressions.Literals import StringLiteral

        if prep:
            return expr, None

        exprs = []
        for i in expr.rh:
            rh = i.quote('')
            if expr.startswith:
                rh = f'{rh}.*'
            elif expr.endswith:
                rh = f'.*{rh}'
            else:
                rh = f'.*{rh}.*'
            rh = StringLiteral(rh, verbatim=True)
            
            acc, _ = self.Regex(Regex(expr.lh, rh), prep=False)
            exprs.append(acc)

        op = 'must' if expr.logic_and else 'should'
        ret = exprs[0] if len(exprs) == 1 else {op: exprs}

        if expr.neq:
            if 'must' in ret:
                ret['must_not'] = ret.pop('must')
            else:
                ret = {'must_not': ret}

        if len(exprs) > 1:
            ret = {'bool': ret}

        return ret, None
