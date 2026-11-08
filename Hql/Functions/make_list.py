from __future__ import annotations
from . import Function
from Hql.Context import register_func, Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Hql import HqlTypes as hqlt
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Expressions import Expression
    from Hql.Expressions.References import Reference

'''
Aggregate the values of a field in each group into a list, skipping nulls.
An optional max_size caps the length of each list.

| summarize Services = make_list(ServiceName) by IpAddress
| summarize make_list(ServiceName, 10) by IpAddress    // list_ServiceName
'''
@register_func('make_list')
class make_list(Function):
    """Aggregate the values of a field within each group into a list."""

    # Kusto's default maxSize
    MAX_SIZE = 1048576

    def __init__(self, args:list[Expression], conf:Optional[dict]=None):
        from Hql.Expressions.Literals import Integer
        from Hql.Expressions.References import Reference

        super().__init__(args, 1, 2, conf=conf)

        if not isinstance(args[0], Reference):
            raise hqle.ArgumentException(f'make_list takes a field, got {type(args[0]).__name__}')
        self.field:Reference = args[0]

        self.max_size = self.MAX_SIZE
        if len(args) > 1:
            if not isinstance(args[1], Integer) or args[1].value < 1:
                raise hqle.ArgumentException('make_list max_size must be a positive integer')
            self.max_size = args[1].value

    def get_list_name(self, agg) -> Reference:
        from Hql.Expressions.References import NamedReference
        base = 'list_' + '_'.join(self.field.list())
        name = base

        taken = agg.df.columns

        i = 0
        while name in taken:
            i += 1
            name = f'{base}{i}'

        return NamedReference(name)

    def get_list_type(self, table:Table) -> hqlt.HqlType:
        t = table.schema.select(self.field).strip()

        if isinstance(t, dict):
            raise hqle.QueryException('Object is an unsupported list type at the moment.')

        if not isinstance(t, hqlt.HqlType):
            raise hqle.CompilerException(f'Attempting to make list of type {type(t)}')

        return hqlt.multivalue(t)

    def eval(self, ctx: Context, receiver=None) -> object:
        tables = []
        for table in ctx.data:
            if not table.agg:
                raise hqle.QueryException('make_list is an aggregation function, use it in a summarize')

            lname = self.get_list_name(table.agg)
            values = self.field.polars_value().drop_nulls().head(self.max_size)

            df = table.agg.agg(values.alias(lname.str()))
            schema = table.agg_schema.copy().set(lname, self.get_list_type(table))
            new = Table(df=df, schema=schema, name=table.name)
            new = new.drop_many(table.agg_paths)

            tables.append(new)

        return Data(tables=tables)
