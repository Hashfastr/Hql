from __future__ import annotations
from Hql.Operators.Operator import Operator

from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from Hql.Expressions.References import NamedReference, Mapping
    from Hql.Context import Context
    from Hql.Expressions import Expression

'''
Applies a mapping, to a dataset, can be a compiler directive or passed to a backend.
'''
class Map(Operator):
    """Count the rows in each input table."""

    def __init__(self, mapping:Mapping|list[Mapping]):
        Operator.__init__(self)
        self.maps:list[Mapping] = mapping if isinstance(mapping, list) else [mapping]

    @property
    def exprs(self) -> Sequence[Expression]:
        """The exprs property."""
        return self.maps

    @exprs.setter
    def exprs(self, value) -> None:
        for i in value:
            assert isinstance(i, Mapping)
        self.maps = value

    def deparse(self) -> str:
        return 'map ' + ' '.join([x.name.deparse() for x in self.maps])

    # this operator is meta so shouldn't be evaluated?
    #
    # def eval(self, ctx:Context) -> Context:
    #     from polars import DataFrame, String, Int64
    #     from Hql.Data import Data, Table
    #
    #     counts = dict()
    #     for table in ctx.data:
    #         counts[table.name] = len(table)
    #
    #     # if sending to a table name, make a new table with counts
    #     if self.name:
    #         new_data = []
    #         for count in counts:
    #             new_data.append({'Table': count, 'Count': counts[count]})
    #
    #         # Data shared with other contexts, add to a copy
    #         ctx = self.copy_tables(ctx)
    #         if new_data:
    #             new_table = Table(init_data=new_data, name=self.name.str())
    #         else:
    #             new_table = Table(df=DataFrame({'Table': [], 'Count': []}, schema={'Table': String, 'Count': Int64}), name=self.name.str())
    #         ctx.data.add_table(new_table)
    #
    #         return ctx
    #
    #     # Replace tables with counts
    #     else:
    #         ctx = ctx.copy()
    #
    #         # Nothing left to count, e.g. a where dropped every table
    #         if not counts:
    #             counts['count'] = 0
    #
    #         new_tables = []
    #         for name in counts:
    #             new = [{'Count': counts[name]}]
    #             new_tables.append(Table(name=name, init_data=new))
    #         ctx.data = Data(tables=new_tables)
    #
    #         return ctx
