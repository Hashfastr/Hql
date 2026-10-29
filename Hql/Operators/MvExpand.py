from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions import ToClause
    from Hql.Expressions.Literals import Integer
    from Hql.Context import Context
    from Hql.Data import Table

class MvExpand(Operator):
    """Expand multivalue fields into individual rows."""

    def __init__(self, exprs:list[ToClause], limit:Optional[Integer]=None):
        Operator.__init__(self)
        self.exprs = exprs
        self.limit = limit

    @property
    def to_clauses(self) -> list[ToClause]:
        from Hql.Expressions import ToClause

        out:list[ToClause] = []
        for e in self.exprs:
            assert isinstance(e, ToClause)
            out.append(e)
        return out

    # Temp column used to hold the exploded values
    TMP_COL = '__hql_mvexpand__'

    def explode_table(self, table:Table, limit:Optional[int]):
        import polars as pl
        from Hql.Types.Hql import HqlTypes as hqlt
        from Hql.Data import Table

        schema = table.schema.copy()
        df = table.df

        for to in self.to_clauses:
            path = to.expr

            # Might reference a field that exists in another table but not this one
            if not schema.assert_field(path):
                continue

            to_schema = schema.get_type(path).strip()

            # Short circuit case
            if not isinstance(to_schema, hqlt.multivalue):
                continue

            # Explode a copy of the values then write them back in place,
            # handles nested paths without flattening their parent structs
            names = path.list()
            value = pl.col(names[0])
            for i in names[1:]:
                value = value.struct.field(i)

            df = df.with_columns(
                value.list.slice(0, limit).alias(self.TMP_COL)
            ).explode(self.TMP_COL, empty_as_null=True)

            new_type = to_schema.inner
            if to.to:
                new_type = to.to
                df = df.with_columns(new_type.cast(df[self.TMP_COL]).alias(self.TMP_COL))

            df = df.with_columns(self.replace_expr(names, pl.col(self.TMP_COL))).drop(self.TMP_COL)
            schema.set(path, new_type)

        return Table(df=df, schema=schema, name=table.name)

    # Builds an expression replacing the value at a path with expr
    @staticmethod
    def replace_expr(names:list[str], expr):
        import polars as pl

        if len(names) == 1:
            return expr.alias(names[0])

        def rec(names:list[str]):
            if len(names) == 1:
                return expr.alias(names[0])
            return pl.field(names[0]).struct.with_fields(rec(names[1:]))

        return pl.col(names[0]).struct.with_fields(rec(names[1:]))

    def deparse(self) -> str:
        out = 'mvexpand '

        exprs = []
        for i in self.to_clauses:
            expr = i.expr.deparse()
            if i.to:
                expr += ' to ' + i.to.deparse()
            exprs.append(expr)
        out += ', '.join(exprs)

        if self.limit:
            out += ' limit '
            out += self.limit.deparse()

        return out

    def eval(self, ctx:Context):
        from Hql.Data import Data

        ctx = ctx.copy()

        # Long literal, just get us the number
        limit = None
        if self.limit:
            limit = self.limit.value

        new = []
        for table in ctx.data:
            new.append(self.explode_table(table, limit))

        ctx.data = Data(tables=new)
        return ctx
