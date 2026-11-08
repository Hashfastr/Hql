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
        keywords = []
        for i in sel:
            # A plain value instead of a map is a keyword, searched for in every field
            if isinstance(i, dict):
                exprs.append(build_dict(i))
            else:
                keywords.append(i)

        if keywords:
            exprs.append(self.keywords(keywords))

        return BinaryLogic(exprs, logic_and=False)

    def keywords(self, values:list):
        from Hql.Expressions.Logic import Substring
        from Hql.Expressions.References import Wildcard

        lits = [self.to_literal_object(x, []) for x in values if x is not None]
        if not lits:
            raise hqle.QueryException(f'Sigma keyword selection {self.name} has no values')
        return Substring(Wildcard('*'), lits)

    def to_literal_object(self, value, modifiers:list[str]):
        from Hql.Expressions.Literals import Bool, StringLiteral, Integer, Float
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference as NR
        
        if isinstance(value, str):
            expr = StringLiteral(value, verbatim=True)

        # before int, bool is a subclass of it
        elif isinstance(value, bool):
            expr = Bool(value)

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
        from Hql.Expressions.Logic import BinaryLogic, Substring
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.References import NamedReference as NR

        # probably deadcode
        if not isinstance(rh, list):
            rh = [rh]

        logic_and = 'all' in modifiers
        startswith = 'startswith' in modifiers
        endswith = 'endswith' in modifiers
        cs = 'cased' in modifiers

        # A null value matches a null field, nothing to search for in it
        nulls = [FuncExpr(NR('isnull'), [lh])] if None in rh else []
        values = [x for x in rh if x is not None]
        if not values:
            return BinaryLogic(nulls, logic_and=False)

        if 'base64offset' in modifiers:
            # Each value matches if any of its three offset encodings does
            expr = BinaryLogic([
                Substring(lh, self.base64offset(x, modifiers), startswith=startswith, endswith=endswith, cs=cs)
                for x in values
            ], logic_and=logic_and)
        else:
            exprs = [self.to_literal_object(x, modifiers) for x in values]
            expr = Substring(lh, exprs, logic_and=logic_and, startswith=startswith, endswith=endswith, cs=cs)
        return BinaryLogic([expr] + nulls, logic_and=False) if nulls else expr

    def base64offset(self, value, modifiers:list[str]) -> list:
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Functions.base64 import base64off

        # Sigma's encoding modifiers apply before the base64
        encoding = 'ascii'
        if 'wide' in modifiers or 'utf16le' in modifiers:
            encoding = 'utf-16-le'
        elif 'utf16be' in modifiers:
            encoding = 'utf-16-be'
        elif 'utf16' in modifiers:
            encoding = 'utf-16'

        return base64off([StringLiteral(str(value))]).calc_offset(str(value).encode(encoding))

    def cidr(self, name:NamedReference, field:list):
        from Hql.Expressions.Logic import BinaryLogic
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import NamedReference as NR

        exprs = []
        for i in field:
            if i == None:
                continue

            # IP fields are usually strings, so test membership rather than a numeric range
            func = 'ipv6_is_in_range' if ':' in str(i) else 'ipv4_is_in_range'
            exprs.append(FuncExpr(NR(func), [name, StringLiteral(str(i))]))

        return BinaryLogic(exprs, logic_and=False)

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
            expr = FuncExpr(NR('exists'), [lh])
            # field is the list [true] or [false]
            if field == [False]:
                expr = FuncExpr(NR('not'), [expr])
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
