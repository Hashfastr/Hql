from __future__ import annotations

from typing import TYPE_CHECKING

from .__proto__ import Expression
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Context import Context
    import polars as pl

# Base class for numeric expressions evaluated per row
class Arithmetic(Expression):
    """Base class for arithmetic expressions over references and literals."""

    def __init__(self) -> None:
        Expression.__init__(self)

    def polars_value(self) -> pl.Expr:
        return self.polars()

    # Functions don't have polars implementations yet, so only expressions can be operands
    @staticmethod
    def operand(expr:object) -> pl.Expr:
        import polars as pl

        value = expr.polars_value() if isinstance(expr, Expression) else NotImplemented
        if not isinstance(value, pl.Expr):
            raise hqle.QueryException(f'{type(expr).__name__} is not supported as an arithmetic operand')
        return value

    '''
    Folds a constant expression into a literal, used when all operands are
    numeric literals. Folds on the raw values so no precision is lost.
    '''
    @staticmethod
    def fold(expr:pl.Expr) -> Expression:
        import polars as pl
        from Hql.Expressions.Literals import Integer, Float, Null

        value = pl.select(expr).to_series()

        if value.null_count():
            return Null()
        if value.dtype.is_integer():
            return Integer(value.item())
        return Float(value.item())

    '''
    Evaluates the expression for each table, returning a series for each.
    Tables missing a referenced field are dropped, like a where filter.
    '''
    def eval(self, ctx:Context) -> Context:
        import polars as pl
        from Hql.Data import Data, Table, Series

        ctx = ctx.copy()
        expr = self.polars()

        tables = []
        for table in ctx.data:
            try:
                series = table.df.select(expr).to_series()
            except pl.exceptions.ColumnNotFoundError:
                continue
            tables.append(Table(series=Series(series), name=table.name))

        ctx.data = Data(tables=tables)
        return ctx

'''
Handles binary arithmetic, as per the grammar
- + and -
- *, / and %

a + b * 2
'''
class BinaryArithmetic(Arithmetic):
    """Combine two expressions with an arithmetic operator."""

    # Higher binds tighter
    precedence = {
        '+': 1,
        '-': 1,
        '*': 2,
        '/': 2,
        '%': 2,
    }

    def __init__(self, lh:Expression, op:str, rh:Expression) -> None:
        Arithmetic.__init__(self)

        if op not in self.precedence:
            raise hqle.CompilerException(f'Invalid arithmetic operator {op}')

        self.lh = lh
        self.op = op
        self.rh = rh

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, BinaryArithmetic):
            return False
        return self.op == value.op and self.lh == value.lh and self.rh == value.rh

    def __hash__(self):
        return hash((self.op, hash(self.lh), hash(self.rh)))

    def to_dict(self):
        return {
            'type': self.type,
            'op': self.op,
            'lh': self.lh.to_dict(),
            'rh': self.rh.to_dict()
        }

    def deparse(self) -> str:
        prec = self.precedence[self.op]

        lh = self.lh.deparse()
        if isinstance(self.lh, BinaryArithmetic) and self.lh.precedence[self.lh.op] < prec:
            lh = f'({lh})'

        # Operators are left associative, so equal precedence on the right needs parens
        rh = self.rh.deparse()
        if isinstance(self.rh, BinaryArithmetic) and self.rh.precedence[self.rh.op] <= prec:
            rh = f'({rh})'

        return f'{lh} {self.op} {rh}'

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import Integer, Float

        lh = self.lh.preprocess(ctx)
        rh = self.rh.preprocess(ctx)
        assert isinstance(lh, Expression)
        assert isinstance(rh, Expression)

        if isinstance(lh, (Integer, Float)) and isinstance(rh, (Integer, Float)):
            import polars as pl
            return self.fold(self.apply(pl.lit(lh.value), pl.lit(rh.value)))

        return BinaryArithmetic(lh, self.op, rh)

    def polars(self) -> pl.Expr:
        return self.apply(self.operand(self.lh), self.operand(self.rh))

    def apply(self, lh:pl.Expr, rh:pl.Expr) -> pl.Expr:
        if self.op == '+':
            return lh + rh
        elif self.op == '-':
            return lh - rh
        elif self.op == '*':
            return lh * rh
        elif self.op == '/':
            return lh / rh
        else:
            return lh % rh

'''
Unary minus

-a
'''
class Negate(Arithmetic):
    """Negate the numeric value of an expression."""

    def __init__(self, expr:Expression) -> None:
        Arithmetic.__init__(self)
        self.expr = expr

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Negate):
            return False
        return self.expr == value.expr

    def __hash__(self):
        return hash(('-', hash(self.expr)))

    def to_dict(self):
        return {
            'type': self.type,
            'expr': self.expr.to_dict()
        }

    def deparse(self) -> str:
        expr = self.expr.deparse()
        if isinstance(self.expr, BinaryArithmetic):
            expr = f'({expr})'
        return f'-{expr}'

    def preprocess(self, ctx: Context) -> object:
        from Hql.Expressions.Literals import Integer, Float

        expr = self.expr.preprocess(ctx)
        assert isinstance(expr, Expression)

        if isinstance(expr, (Integer, Float)):
            import polars as pl
            return self.fold(-pl.lit(expr.value))

        return Negate(expr)

    def polars(self) -> pl.Expr:
        return -self.operand(self.expr)
