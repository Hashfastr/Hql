from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union
from Hql.Operators.Operator import Operator

if TYPE_CHECKING:
    from Hql.Expressions.References import NamedReference
    from Hql.Expressions.Literals import Literal, TypeExpression
    from Hql.Context import Context
    from Hql.Types.Hql import HqlTypes

'''
Creates a simple datatable, essentially an inline dataframe/table
'''
class Datatable(Operator):
    """Create an inline table from a schema and literal values."""

    def __init__(self, schema:list[tuple[NamedReference, Union[HqlTypes.HqlType, TypeExpression]]], values:list[Literal], name:Optional[NamedReference]=None):
        Operator.__init__(self)
        self.values:list[Literal] = values
        self.schema:list[tuple[NamedReference, Union[HqlTypes.HqlType, TypeExpression]]] = schema
        self.name:Optional[NamedReference] = name
        self.tabular:bool = True

    def to_dict(self):
        out = super().to_dict()
        out['schema'] = {i[0].str(): self.get_type(i[1]).deparse() for i in self.schema}
        out['values'] = [x.to_dict() for x in self.values]
        if self.name:
            out['name'] = self.name.to_dict()
        return out

    # The parser gives TypeExpressions, convert them to the type itself
    @staticmethod
    def get_type(t:Union[HqlTypes.HqlType, TypeExpression]) -> HqlTypes.HqlType:
        from Hql.Expressions.Literals import TypeExpression

        if isinstance(t, TypeExpression):
            return t.dtype()
        return t

    def gen_schema(self) -> HqlTypes.object:
        from Hql.Types.Hql import HqlTypes

        d = dict()
        for i in self.schema:
            d[i[0].str()] = self.get_type(i[1])
        return HqlTypes.object(d)

    def deparse(self) -> str:
        width = len(self.schema)
        nvalues = len(self.values)

        schema = []
        for i in self.schema:
            schema.append(f'{i[0].deparse()}: {self.get_type(i[1]).deparse()}')
        schema = ', '.join(schema)

        values = []
        if width:
            for i in range(0, nvalues, width):
                row = [x.deparse() for x in self.values[i:i+width]]
                values.append(', '.join(row))

        table = '    '
        table += ',\n    '.join(values)
        table += '\n'

        total  = f'datatable ({schema})\n'
        total += '[\n'
        total += table
        total += ']'

        if self.name:
            total += f' as {self.name.deparse()}'

        return total

    def eval(self, ctx:Context):
        from polars import DataFrame
        from Hql.Data import Data, Table, Schema
        from Hql.Exceptions import HqlExceptions as hqle

        ctx = ctx.copy()

        width = len(self.schema)
        nvalues = len(self.values)

        if not width:
            raise hqle.QueryException('Datatable defined without any columns')

        if nvalues % width != 0:
            raise hqle.QueryException(f'Datatable given {nvalues} values, not a multiple of its {width} columns')

        schema = self.gen_schema()
        keys = [x[0].str() for x in self.schema]

        data = dict()
        for i in range(width):
            rows = []
            for j in range(0, nvalues, width):
                value = self.values[j + i].value
                # StringLiterals hold bytes
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                rows.append(value)
            data[keys[i]] = rows

        name = 'datatable'
        if self.name:
            name = self.name.str()

        table = Table(
            df=DataFrame(data, strict=False),
            schema=Schema(schema=schema),
            name=name
        )
        ctx.data = Data(tables=[table])

        return ctx
