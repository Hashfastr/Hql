from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional, Union, override

from .__proto__ import Expression
from Hql.Exceptions import HqlExceptions as hqle

import logging

from Hql.Functions import Function

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions.Literals import StringLiteral, Literal, Bool
    from Hql.Expressions.References import Reference
    import polars as pl

# descriptive class
class Logic(Expression):
    """Base class for expressions that evaluate as predicates."""

    def __init__(self):
        Expression.__init__(self)

    def merge(self, expr:Logic) -> Optional[Logic]:
        return expr

    def reduce(self):
        return self

class Comparator(Logic):
    """Base predicate comparing a reference with one or more expressions."""

    def __init__(self, lh:Reference, rh:Union[Sequence[Expression], Expression], cs:bool=True, neq:bool=False, term:bool=False, logic_and:bool=False) -> None:
        Logic.__init__(self)

        self.lh:Reference = lh
        self.rh:Sequence[Expression] = self._coerce_rh(rh)
        
        for i in self.rh:
            if not isinstance(i, Expression):
                raise hqle.CompilerException(f'Comparator {self.type} given non-Expression rh {type(i)}')

        # case sensitive compare
        self.cs:bool        = cs
        # is negated
        self.neq:bool       = neq
        # term matching
        self.term:bool      = term
        # How right hand logic should be handled
        # expr AND expr AND expr
        # vs
        # expr OR expr OR expr
        self.logic_and:bool = logic_and
        # if a comparator can be a righthand list
        self.can_list:bool  = True

    @staticmethod
    def _coerce_rh(rh:Union[Sequence[Expression], Expression]) -> Sequence[Expression]:
        if isinstance(rh, Expression):
            return [rh]
        return list(rh)

    '''
    If an expression can resolve to row values, such as a field or arithmetic on one
    '''
    @staticmethod
    def is_row_value(expr:object) -> bool:
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Arithmetic import Arithmetic
        return isinstance(expr, (Reference, Arithmetic))

    def set_rh(self, rh:Union[Sequence[Expression], Expression]):
        self.rh = self._coerce_rh(rh)
    
    def add_rh(self, rh:Union[Sequence[Expression], Expression]):
        self.rh += self._coerce_rh(rh)

    '''
    Simplifys some things, breaks out rhs to a set of singular comparators and a BinaryOperator
    Most languages don't support list right hands, so a lot of repeated code to do this:
    '''
    def expand_rh(self) -> Logic:
        exprs = []
        for i in self.rh:
            new = self.dupe()
            new.set_rh(i)
            exprs.append(new)
        return BinaryLogic(exprs, logic_and=self.logic_and)

    '''
    Create a copy duplicate of this object.
    Expressions can be reused many places, not costy to copy
    '''    
    def dupe(self):
        import copy
        return copy.deepcopy(self)

    def to_dict(self):
        return {
            'type': self.type,
            'cs': self.cs,
            'neq': self.neq,
            'term': self.term,
            'op': self.build_op(),
            'lh': self.lh.to_dict(),
            'rh': [x.to_dict() for x in self.rh]
        }
    
    def build_op(self) -> str:
        return NotImplemented

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import Literal, StringLiteral, Bool
        from Hql.Expressions.References import Reference

        if len(self.rh) > 1:
            rh = self.expand_rh().preprocess(ctx)
            if isinstance(rh, Logic):
                return rh.reduce()
            return rh

        lh = self.lh.preprocess(ctx)
        rh = self.rh[0].preprocess(ctx)

        if isinstance(lh, Literal) and isinstance(rh, Literal):
            if isinstance(lh, StringLiteral):
                return Bool(lh.cmp(rh, self.cs) != self.neq)
            else:
                return Bool((lh == rh) != self.neq)

        if isinstance(lh, Reference) and lh == rh:
            return Bool(True != self.neq)

        assert isinstance(lh, Expression)
        assert isinstance(rh, Expression)

        if not self.is_row_value(lh):
            if self.is_row_value(rh):
                tmp = lh
                lh = rh
                rh = tmp
            else:
                new = self.dupe()
                logging.error(f'Expression: {self.deparse()}')
                logging.error(f'Is invalid with preprocessed operands {lh.deparse()} and {rh.deparse()}')
                raise hqle.QueryException(f'Invalid preprocessed expression')

        new = self.dupe()
        new.lh = lh
        new.rh = [rh]
        return new

'''
Handles the following direct comparators:
- ==/!=
- =~/!~
- in/!in
- in~/!in~
Not substring comparators
'''
class Equality(Comparator):
    """Compare a reference for equality or membership, optionally negated."""

    def __init__(self, lh:Reference, rh:Union[Sequence[Expression], Expression], cs:bool=True, neq:bool=False):
        Comparator.__init__(self, lh, rh, cs=cs, neq=neq)
        self.cs = cs
        self.neq = neq
        self.logic_and = False
        self.can_list = True

    # for pickle (aka deepcopy)
    def __reduce__(self):
        return (self.__class__, (self.lh, self.rh, self.cs, self.neq))

    def reduce(self) -> Logic:
        new = self.dupe()

        or_exprs = []
        rhs = []
        for i in new.rh:
            if isinstance(i, BasicRange):
                or_exprs.append(BetweenEquality(new.lh, i.start, i.end))
                continue
            rhs.append(i)

        # avoids recurse
        if or_exprs:
            new.rh = rhs
            or_exprs = [new] + or_exprs
            return BinaryLogic(or_exprs, logic_and=False)

        return self
    
    '''
    Returns None if successful, the passed expr if not possible
    '''
    def merge(self, expr: Logic) -> Optional[Logic]:
        if not (isinstance(expr, type(self)) and self.lh == expr.lh):
            return expr

        attrs = ['cs', 'neq', 'logic_and']
        for i in attrs:
            if getattr(self, i) != getattr(expr, i):
                return expr

        self.rh = list(self.rh) + list(expr.rh)
        return None

    '''
    Justifies the operator to correctly represent the flags given
    '''
    def build_op(self) -> str:
        op = ''
        if len(self.rh) > 1:
            if self.neq:
                op += '!'
            op += 'in'
            if not self.cs:
                op += '~'
        else:
            op += '!' if self.neq else '='
            op += '=' if self.cs else '~'
        return op

    def polars(self) -> pl.Expr:
        import polars as pl

        reduced = self.reduce()
        if not isinstance(reduced, Equality):
            return reduced.polars()

        if len(reduced.rh) > 1:
            return reduced.expand_rh().polars()

        lh = reduced.lh.polars()
        rh = reduced.rh[0].polars()

        if reduced.cs:
            new = (lh == rh)
        else:
            rh = pl.select(rh.str.escape_regex()).item()
            regex = f'(?i)^{rh}$'
            new = lh.str.contains(regex)

        if reduced.neq:
            new = ~new
        return new

    def deparse(self):
        reduced = self.reduce()
        if not isinstance(reduced, Equality):
            return reduced.deparse()

        lh = reduced.lh.deparse()

        op = f'{lh} {reduced.build_op()} '

        if len(reduced.rh) == 1:
            return op + reduced.rh[0].deparse()

        rh = []
        for i in reduced.rh:
            rh.append(i.deparse())
        rh = ', '.join(rh)

        return op + f'({rh})'

'''
Handles the following term operators:
- has/has_cs
    - term substring
- has_all/has_all_cs
    - term substring list and
    - field has 'test' and field has 'foo'
- has_any/has_any_cs
    - term substring list or
    - field has 'test' or field has 'foo'
- hasprefix/hasprefix_cs
    - Term prefix/startswith
- hassuffix/hassuffix_cs
    - Term suffix/endswith

Non-term operators:
- contains/contains_cs
    - non-term substring
- contains_all/contains_all_cs
    - contains substring list and
    - field contains 'test' and field contains 'foo'
- contains_any/contains_any_cs
    - contains substring list or
    - field contains 'test' or field contains 'foo'
- startswith/startswith_cs
    - non-term prefix/startswith
- endswith/endswith_cs
    - non-term suffix/endswith
'''
class Substring(Comparator):
    """Match strings by substring, term, prefix, or suffix semantics."""

    def __init__(self, lh:Reference, rh:list[StringLiteral], term:bool=False, logic_and:bool=False, neq:bool=False, cs:bool=False, startswith:bool=False, endswith:bool=False):
        Comparator.__init__(self, lh, rh)
        # narrow type defs
        self.lh:Reference = lh
        self._rh:list[StringLiteral] = rh

        self.term = term
        self.logic_and = logic_and
        self.neq = neq
        self.cs = cs
        self.startswith = startswith
        self.endswith = endswith
        self.can_list = True

    def __hash__(self):
        hashes = []

        attrs = ['lh', 'term', 'logic_and', 'neq', 'cs', 'startswith', 'endswith', 'can_list']
        for i in attrs:
            hashes.append(self.__getattribute__(i).__hash__())

        for i in self.rh:
            hashes.append(hash(i))

        return hash(frozenset(hashes))

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Substring):
            return False

        attrs = ['lh', 'term', 'logic_and', 'neq', 'cs', 'startswith', 'endswith', 'can_list']
        for i in attrs:
            if value.__getattribute__(i) != self.__getattribute__(i):
                return False

        if len(self.rh) != len(value.rh):
            return False

        for idx, i in enumerate(self.rh):
            if self.rh[idx] != value.rh[idx]:
                return False

        return True

    @property
    def rh(self) -> list[StringLiteral]:
        """The rh property."""
        return self._rh

    @rh.setter
    def rh(self, value:list[StringLiteral]):
        self._rh = value

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference

        lh = self.lh.preprocess(ctx)

        if not isinstance(lh, Reference):
            raise Exception(f'Substring lh resolved to {type(lh)} not Reference')
        
        rhs = []
        for i in self.rh:
            rh = i.preprocess(ctx)
            assert isinstance(rh, Expression)
            if not isinstance(rh, StringLiteral):
                rh = StringLiteral(rh.str())
            rhs.append(rh)

        new = self.dupe()
        new.lh = lh
        new.rh = rhs
        return new

    def to_dict(self):
        return {
            'type': self.type,
            'lh': self.lh.to_dict(),
            'op': self.build_op(),
            'rh': [x.to_dict() for x in self.rh]
        }

    def build_op(self) -> str:
        if self.startswith:
            core = 'startswith'
        elif self.endswith:
            core = 'endswith'
        elif self.term:
            core = 'has'
        else:
            core = 'contains'

        if self.neq:
            core = '!' + core
        
        if len(self.rh) > 1:
            core += '_all' if self.logic_and else '_any'
        
        if self.cs:
            core += '_cs'

        return core

    '''
    contains and has operators
    '''
    def has(self, lh:pl.Expr, rh:Expression):
        import polars as pl

        rh_str = pl.escape_regex(rh.str())

        regex = '' if self.cs else '(?i)'
        regex += rh_str

        return lh.str.contains(regex)

    '''
    prefix and suffix operators
    '''
    def prefix(self, lh:pl.Expr, rh:Expression):
        import polars as pl

        rh_str = pl.escape_regex(rh.str())
        
        regex = '' if self.cs else '(?i)'
        regex += '^' if self.startswith else ''
        regex += rh_str
        regex += '$' if self.endswith else ''

        return lh.str.contains(regex)

    def deparse(self) -> str:
        lh = self.lh.deparse()
        op = self.build_op()

        rh = []
        for i in self.rh:
            rh.append(i.deparse())
        rh = ', '.join(rh)

        out = f'{lh} {op} '
        if len(self.rh) > 1:
            out += f'({rh})'
        else:
            out += rh

        return out

    def polars(self) -> pl.Expr:
        if self.term:
            logging.warning('Term matching not supported in Hql-land, do not expect increased performance')

        if len(self.rh) > 1:
            return self.expand_rh().polars()
        
        lh = self.lh.polars()
        if self.startswith or self.endswith:
            expr = self.prefix(lh, self.rh[0])
        else:
            expr = self.has(lh, self.rh[0])

        return ~expr if self.neq else expr

    def merge(self, expr: Logic) -> Optional[Logic]:
        if not isinstance(expr, type(self)) or self.lh != expr.lh:
            return expr

        attrs = ['term', 'logic_and', 'neq', 'cs', 'startswith', 'endswith']
        for i in attrs:
            if getattr(self, i) != getattr(expr, i):
                return expr

        self.add_rh(expr.rh)
        return None

# Handles relational expressions
# - <
# - >
# - <=
# - >=
# As per the grammar
# Takes after the equality expression
class Relational(Comparator):
    """Compare a reference with an expression using an ordering operator."""

    def __init__(self, lh:Reference, rh:Expression, gt:bool, eq:bool) -> None:
        Comparator.__init__(self, lh, rh, logic_and=True)
        self.gt = gt
        self.eq = eq
        self.can_list = False

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import Literal, Bool
        from Hql.Expressions.References import Reference

        def compare(lh, rh, op:str) -> bool:
            if op == '<':
                return lh.value < rh.value
            elif op == '>':
                return lh.value > rh.value
            elif op == '<=':
                return lh.value <= rh.value
            else:
                return lh.value >= rh.value

        if len(self.rh) > 1:
            rh = self.expand_rh().preprocess(ctx)
            if isinstance(rh, Logic):
                return rh.reduce()
            return rh

        lh = self.lh.preprocess(ctx)
        rh = self.rh[0].preprocess(ctx)

        if isinstance(lh, Literal) and isinstance(rh, Literal):
            return Bool(compare(lh, rh, op=self.build_op()))

        if isinstance(lh, Reference) and lh == rh:
            return Bool(self.eq)

        assert isinstance(lh, Expression)
        assert isinstance(rh, Expression)

        new = self.dupe()

        if not self.is_row_value(lh):
            if self.is_row_value(rh):
                tmp = lh
                lh = rh
                rh = tmp

                # 3 > a is a < 3, inclusivity is unchanged by the swap
                new.gt = not self.gt
            else:
                logging.error(f'Expression: {self.deparse()}')
                logging.error(f'Is invalid with preprocessed operands {lh.deparse()} and {rh.deparse()}')
                raise hqle.QueryException(f'Invalid preprocessed expression')

        new.lh = lh
        new.rh = [rh]
        return new

    def __reduce__(self):
        return (self.__class__, (self.lh, self.rh, self.gt, self.eq))

    def deparse(self) -> str:
        lh = self.lh.deparse()
        rh = self.rh[0].deparse()
        return f'{lh} {self.build_op()} {rh}'
    
    def build_op(self) -> str:
        op =  '>' if self.gt else '<'
        op += '=' if self.eq else ''
        return op

    def polars(self) -> pl.Expr:
        lh = self.lh.polars()
        rh = self.rh[0].polars()

        if self.gt:
            if self.eq:
                return (lh >= rh)
            else:
                return (lh > rh)
        else:
            if self.eq:
                return (lh <= rh)
            else:
                return (lh < rh)

# Data range functionality
# Left hand side is the expression to evaluate in being between two values.
# The right hand has a start and end expression showing the range of the values.
#
# | where ['@timestamp'] between ("2022-10-21T15:50:00.000Z" .. "2022-10-21T15:55:00.000Z")
# 
# Here lh is the '@timestamp' escaped string literal, and the right hand has
# the start and end values for the time range.
class BetweenEquality(Comparator):
    """Compare a reference with two literal range bounds."""

    def __init__(self, lh:Reference, start:Literal, end:Literal, neq:bool=False):
        Logic.__init__(self)

        self.lh = lh
        self.start = start
        self.end = end
        self.neq = neq

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import Literal, Bool
        from Hql.Expressions.References import Reference

        def compare(lh, start, end):
            return lh.value > start.value and lh.value < end.value

        lh = self.lh.preprocess(ctx)
        start = self.start.preprocess(ctx)
        end = self.end.preprocess(ctx)

        if isinstance(lh, Literal) and isinstance(start, Literal) and isinstance(end, Literal):
            if lh.hql_type != start.hql_type or lh.hql_type != end.hql_type:
                return Bool(False != self.neq)
            return Bool(compare(lh, start, end) != self.neq)

        assert isinstance(lh, Expression)

        new = self.dupe()

        if isinstance(start, Reference) or isinstance(end, Reference):
            assert isinstance(start, Expression)
            assert isinstance(end, Expression)
            logging.error(f'Expression: {self.deparse()}')
            logging.error(f'Is invalid with preprocessed operands {lh.deparse()}, {start.deparse()}, and {end.deparse()}')
            raise hqle.QueryException(f'Invalid preprocessed expression')

        assert isinstance(lh, Reference)
        new.lh = lh
        new.start = start
        new.end = end
        return new
    
    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'negate': self.neq,
            'lh': self.lh.to_dict(),
            'rh': {
                'start': self.start.to_dict(),
                'end': self.end.to_dict()
            }
        }

    def deparse(self) -> str:
        lh = self.lh.deparse()
        start = self.start.deparse()
        end = self.end.deparse()
        op = '!between' if self.neq else 'between'
        return f'{lh} {op} ({start} .. {end})'

    def polars(self) -> pl.Expr:
        lh = self.lh.polars()
        start = self.start.polars()
        end = self.end.polars()
        
        filt = lh.is_between(start, end)
        if self.neq:
            filt = ~filt
        return filt

'''
Handles binary logic, simple ands and ors
'''
class BinaryLogic(Logic):
    """Combine predicates with Boolean AND or OR semantics."""

    def __init__(self, exprs:Sequence[Logic], logic_and:bool=True):
        from Hql.Expressions.Literals import Bool
        Logic.__init__(self)

        if len(exprs) == 1 and isinstance(exprs[0], BinaryLogic):
            self.logic_and = exprs[0].logic_and
            self.exprs = list(exprs[0].exprs)
            return

        self.logic_and = logic_and

        new = []
        for i in exprs:
            if i == Bool(True) and logic_and:
                continue
            if i == Bool(False) and not logic_and:
                continue

            # collapse logic
            if isinstance(i, BinaryLogic) and i.logic_and == logic_and:
                new += i.exprs
                continue
                
            new.append(i)

        self.exprs = list(set(new))

    def __new__(cls, exprs:Sequence[Logic], logic_and:bool=True) -> Union[Logic, Bool]:
        from Hql.Expressions.Literals import Bool

        if len(exprs) == 0:
            raise hqle.CompilerException('BinaryLogic given no expressions!')
        if len(exprs) == 1 and not isinstance(exprs[0], cls):
            return exprs[0]
        if not logic_and and Bool(True) in exprs:
            return Bool(True)
        if logic_and and Bool(False) in exprs:
            return Bool(False)

        return super().__new__(cls)

    def __reduce__(self):
        return (self.__class__, (self.exprs, self.logic_and))
    
    def __iter__(self):
        return iter(self.exprs)

    def __len__(self):
        return len(self.exprs)

    def preprocess(self, ctx: Context) -> object:
        exprs = []
        for i in self.exprs:
            exprs.append(i.preprocess(ctx))

        new = BinaryLogic(exprs, self.logic_and)
        if isinstance(new, BinaryLogic):
            new = new.condense()
        return new

    '''
    Condense down equality operators so they're more syntactically condensed.
    Flatten nested logic
    '''
    def condense(self) -> Logic:
        new:list[Logic] = []
        merged = False
        for i in self.exprs:
            if isinstance(i, BinaryLogic):
                i = i.condense()
            
            # second pass, integrate
            if isinstance(i, BinaryLogic) and i.logic_and == self.logic_and:
                new += i.exprs
                continue

            if isinstance(i, Logic):
                new.append(i)
                continue

            # merge back to old stuff
            for j in new:
                if j.merge(i) == None:
                    merged = True
                    break

            if not merged:
                new.append(i)
            else:
                merged = False

        return BinaryLogic(new, self.logic_and)

    def demorgan(self):
        exprs = []
        for i in self.exprs:
            exprs.append(Not(i))
        return BinaryLogic(exprs, not self.logic_and)
        
    def to_dict(self):
        return {
            'type': self.type,
            'and': self.logic_and,
            'exprs': [x.to_dict() for x in self.exprs]
        }

    def build_op(self):
        return 'and' if self.logic_and else 'or'

    def split_by_length(self, max_length:int=80) -> list[BinaryLogic]:
        from copy import deepcopy

        if max_length < 0 or not self.logic_and:
            return [self]

        def get_len(exprs:list):
            pad = len(self.build_op()) + 2
            lens = [len(x.deparse()) for x in exprs]
            return sum(lens) + (len(lens) * pad)

        out = []
        cur:list[Logic] = []
        for i in self.exprs:
            if not cur:
                cur = [i]

            if get_len(cur) > max_length:
                out.append(BinaryLogic(cur, logic_and=True))
                cur = []
            else:
                cur.append(i)
        
        if cur:
            out.append(BinaryLogic(cur, logic_and=True))

        return out

    def deparse(self) -> str:
        depar = []
        for i in self.exprs:
            j = i.deparse()
            if isinstance(i, BinaryLogic):
                j = f'({j})'
            depar.append(j)

        bitype = f' {self.build_op()} '
        return bitype.join(depar)
        
    def polars(self):
        exprs = []
        for i in self.exprs:
            exprs.append(i.polars())    
        
        filt = exprs[0]
        for i in exprs[1:]:
            if self.logic_and:
                filt = filt & i
            else:
                filt = filt | i
                
        return (filt)

class BasicRange(Logic):
    """Store the endpoints of a range expression."""

    def __init__(self, start:Literal, end:Literal):
        Logic.__init__(self)
        self.start = start
        self.end = end

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'start': self.start.to_dict(),
            'end': self.end.to_dict()
        }

    def deparse(self) -> str:
        start = self.start.deparse()
        end = self.end.deparse()
        return f'({start} .. {end})'

class Regex(Logic):
    """Match a referenced string against a regular expression."""

    def __init__(self, lh:Reference, rh:StringLiteral, i:bool=False, m:bool=False, s:bool=False, g:bool=False) -> None:
        Logic.__init__(self)
        self.lh = lh
        self.rh = rh

        self.i = i # case insentive
        self.m = m # multiline
        self.s = s # dotall
        self.g = g # global

        if m:
            logging.warning('Regex multiline flag currently ignored')
        if s:
            logging.warning('Regex dotall flag currently ignored')
        if g:
            logging.warning('Regex global flag currently ignored')

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'lh': self.lh.to_dict(),
            'rh': self.rh.to_dict(),
            'i': self.i,
            'm': self.m,
            's': self.s,
            'g': self.g,
        }

    def deparse(self) -> str:
        lh = self.lh.deparse()
        rh = self.rh.deparse()
        return f'{lh} matches regex {rh}'

    def polars(self) -> pl.Expr:
        import polars as pl

        lh = self.lh.polars()
        rh = self.rh.str()

        if self.i:
            rh = '(?i)' + rh
        rh = pl.lit(rh)

        return lh.str.contains(rh)

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Literals import Bool, StringLiteral

        lh = self.lh.preprocess(ctx)
        assert isinstance(lh, Expression)
        rh = self.rh.preprocess(ctx)
        assert isinstance(rh, StringLiteral)

        if isinstance(lh, Reference):
            return self

        if isinstance(lh, StringLiteral):
            import polars as pl

            rh = rh.str()
            if self.i:
                rh = '(?i)' + rh
            rh = pl.lit(rh)

            return Bool(
                pl.select(
                    pl.lit(lh.str()).str.contains(rh).alias('matches')
                ).item()
            )

        logging.error(f'Expression: {self.deparse()}')
        logging.error(f'Is invalid with preprocessed operands {lh.deparse()} and {rh.deparse()}')
        raise hqle.QueryException(f'Invalid preprocessed expression')

class Not(Logic):
    """Negate a logical, reference, or function expression."""

    def __init__(self, expr:Union[Logic, Reference, Function]) -> None:
        Logic.__init__(self)
        self.expr = expr

    def deparse(self) -> str:
        expr = self.expr.deparse()
        return f'not({expr})'

    def polars(self) -> pl.Expr:
        return self.expr.polars().not_()
