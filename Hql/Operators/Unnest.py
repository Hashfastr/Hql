from __future__ import annotations
from typing import TYPE_CHECKING, Sequence, Union
from Hql.Operators.Operator import Operator
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Context import Context
    from Hql.Expressions import References

class Unnest(Operator):
    """Expand a nested field in each selected table."""

    def __init__(self, field:References.Reference, tables:Sequence[Union[References.NamedReference, References.Wildcard]]):
        Operator.__init__(self)
        self.field = field
        self.tables = tables

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'field': self.field.to_dict(),
            'tables': [x.to_dict() for x in self.tables]
        }

    def deparse(self) -> str:
        out = 'unnest '
        out += self.field.deparse()

        if self.tables:
            out += ' on '
            exprs = []
            for i in self.tables:
                exprs.append(i.deparse())
            out += ', '.join(exprs)

        return out

    def gets_all(self, ctx:Context) -> bool:
        for i in self.tables:
            if i.str() == '*':
                return True
        return False

    def eval(self, ctx: Context) -> Context:
        from Hql.Data.Tables import Table

        ctx = self.copy_tables(ctx)

        # loop through tables defined by 'on'
        for i in self.tables:
            # match tables matching the pattern
            tables = ctx.data.get_tables(i.str())

            # loop through matching tables
            for j in tables:
                # Might reference a field that exists in another table but not this one
                if not j.assert_field(self.field):
                    continue

                new_table = j.unnest(self.field)
                if not isinstance(new_table, Table):
                    raise hqle.CompilerException(f'Unnesting table returned Non-table type {type(new_table)}')
                ctx.data.replace_table(new_table)

        return ctx
