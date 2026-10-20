from __future__ import annotations
from typing import TYPE_CHECKING, Union

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Expressions.References import NamedReference

class Selection():
    def __init__(self, selection:Union[list, dict], name:str=''):
        from Hql.Context import Context
        from Hql.Data import Data

        self.ctx = Context(Data())

        self.name = name
        self.selection = selection
        self.fields = []
    
    def gen_let(self):
        from Hql.Query import LetLogicStatement
        from Hql.Expressions.References import NamedReference

        return LetLogicStatement(
            NamedReference(self.name),
            self.build_selection()
        )

    def __hash__(self) -> int:
        return self.build_selection().__hash__()

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Selection):
            return False

        return self.build_selection() == value.build_selection()

    def deparse(self) -> str:
        return self.build_selection().deparse()

    def build_selection(self):
        from Hql.Expressions.Logic import BinaryLogic
        
        def build_dict(sel:dict):
            exprs = []
            for i in sel:
                expr = self.process_field(i, sel[i])
                exprs.append(expr)
            return BinaryLogic(exprs)

        if isinstance(self.selection, list):
            sel = self.selection
        else:
            sel = [self.selection]

        exprs = []
        for i in sel:
            expr = build_dict(i)
            exprs.append(expr)
        return BinaryLogic(exprs, logic_and=False)

    def to_literal_object(self, value, modifiers:list[str]):
        from Hql.Expressions.Literals import StringLiteral, Integer, Float
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference as NR
        
        if isinstance(value, str):
            expr = StringLiteral(value, verbatim=True)

        elif isinstance(value, int):
            expr = Integer(value)

        elif isinstance(value, float):
            expr = Float(value)
        
        else:
            raise hqle.CompilerException(f'Unhandled literal object type {type(value)} in Sigma parse')

        if 'base64' in modifiers:
            expr = FuncExpr(NR('base64'), [expr])

        elif 'base64offset' in modifiers:
            expr = FuncExpr(NR('base64offset'), [expr])

        return expr

    def substring(self, lh:NamedReference, modifiers:list, rh:list):
        from Hql.Expressions.Logic import Substring

        # probably deadcode
        if not isinstance(rh, list):
            rh = [rh]

        exprs = []
        for i in rh:
            if i == None:
                continue
            exprs.append(self.to_literal_object(i, modifiers))

        logic_and = 'all' in modifiers
        startswith = 'startswith' in modifiers
        endswith = 'endswith' in modifiers
        cs = 'cased' in modifiers

        return Substring(lh, exprs, logic_and=logic_and, startswith=startswith, endswith=endswith, cs=cs)

    def cidr(self, name:NamedReference, field:list):
        from Hql.Expressions.Logic import Equality
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference as NR

        exprs = []
        for i in field:
            if i == None:
                continue

            expr = self.to_literal_object(i, [])
            if ':' in field:
                expr = FuncExpr(NR('ip6subnet'), [expr]).eval(self.ctx)
            else:
                expr = FuncExpr(NR('ip4subnet'), [expr]).eval(self.ctx)

            exprs.append(expr)

        return Equality(name, exprs)

    def relational(self, name:NamedReference, modifiers:list[str], field:list):
        from Hql.Expressions.Logic import Relational, BinaryLogic

        gt = False
        eq = False
        for i in modifiers:
            if i.startswith('gt') or i.startswith('lt'):
                gt = 'gt' in i
                eq = 'e' in i
                break

        exprs = []
        for i in field:
            if i == None:
                continue
            lit = self.to_literal_object(i, modifiers)
            exprs.append(Relational(name, lit, gt=gt, eq=eq))

        return BinaryLogic(exprs)

    def fieldref(self, name:NamedReference, field:list):
        from Hql.Expressions.References import NamedReference
        from Hql.Expressions.Logic import Equality

        exprs = []
        for i in field:
            exprs.append(NamedReference(i))

        return Equality(name, exprs)

    def regex(self, name:NamedReference, modifiers:list[str], field:list):
        from Hql.Expressions.Logic import Regex
        from Hql.Expressions.Logic import BinaryLogic

        patterns = []
        for i in field:
            if i == None:
                continue
            patterns.append(self.to_literal_object(i, modifiers))
        
        exprs = []
        for i in patterns:
            expr = Regex(name, i)

            expr.i = 'i' in modifiers
            expr.m = 'm' in modifiers
            expr.s = 's' in modifiers

            exprs.append(expr)

        return BinaryLogic(exprs, logic_and=False)

    def equality(self, name:NamedReference, field:list):
        from Hql.Expressions.Logic import Equality, BinaryLogic
        from Hql.Expressions.References import NamedReference as NR
        from Hql.Expressions.Functions import FuncExpr

        rhs = []
        other = []
        for i in field:
            if i == None:
                other.append(FuncExpr(NR('isnull'), [name]))
            else:
                rhs.append(self.to_literal_object(i, []))

        if len(rhs) == 0:
            exprs = other
        else:
            exprs = [Equality(name, rhs)] + other

        return BinaryLogic(exprs, logic_and=False)

    def process_field(self, field_name:str, field):
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference as NR

        if not isinstance(field, list):
            field = [field]

        name = field_name.split('|')

        lh = NR(name[0])
        modifiers = name[1:]

        if 'exists' in modifiers:
            expr = FuncExpr(NR('exists'), [lh]).preprocess(self.ctx)
            if not field:
                expr = FuncExpr(NR('not'), [expr]).preprocess(self.ctx)
            return expr

        for i in ['contains', 'endswith', 'startswith']:
            if i in modifiers:
                return self.substring(lh, modifiers, field)

        if 'cidr' in modifiers:
            return self.cidr(lh, field)

        if 'fieldref' in modifiers:
            return self.fieldref(lh, field)

        for i in ['gte', 'lte', 'lt', 'lte']:
            if i in modifiers:
                return self.relational(lh, modifiers, field)

        if 're' in modifiers:
            return self.regex(lh, modifiers, field)

        return self.equality(lh, field)
