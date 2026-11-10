from __future__ import annotations

from .__proto__ import Expression
from Hql.Exceptions import HqlExceptions as hqle

from typing import TYPE_CHECKING, Optional, Sequence, Union
import logging

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Functions import Function
    from Hql.Data import Data, Table
    from polars import Expr as plExpr

class Reference(Expression):
    """Base expression for selecting a named or nested value."""

    def __init__(self):
        Expression.__init__(self)
        self.name = ''

    def __getitem__(self, idx:int) -> str:
        return self.list()[idx]

    def __setitem__(self, idx:int, value:str):
        if idx not in (0, -1):
            raise IndexError(f'Invalid index {idx} for Reference of length {1}')
        self.name = value
        return self

    def __iter__(self):
        return iter(self.list())

    def __len__(self):
        return len(self.list())

    def __hash__(self):
        return hash((self.name))

    def polars(self) -> plExpr:
        return NotImplemented

    def polars_value(self) -> plExpr:
        return NotImplemented

    def polars_reference(self) -> plExpr:
        return NotImplemented

    def list(self) -> list[str]:
        return NotImplemented
    
    def get_symbol(self, ctx:Context):
        if self.name in ctx.symbol_table:
            return ctx.symbol_table[self.name]
        return ctx.symbol_table.get(self, None)

    def preprocess(self, ctx: Context) -> object:
        rec = self.get_symbol(ctx)
        if rec is None:
            return self
        if isinstance(rec, dict):
            return self
        return rec

    def eval(self, ctx: Context, unnest:bool=False) -> Context:
        ctx = ctx.copy()
        if unnest:
            ctx.data = ctx.data.unnest(self)
        else:
            ctx.data = ctx.data.select(self)
        return ctx

# A named reference, can be scoped
# Scopes are not implemented yet.
class NamedReference(Reference):
    """Reference a value by its unescaped name."""

    def __init__(self, name:str):
        Reference.__init__(self)
        self.name = name

    def __eq__(self, value: object, /) -> bool:
        if isinstance(value, NamedReference):
            return self.name == value.name
        return super().__eq__(value)

    def __hash__(self):
        return hash((self.name))

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'name': self.name,
        }

    def deparse(self) -> str:
        return self.name

    def str(self) -> str:
        return self.name

    def list(self) -> list[str]:
        return [self.name]

    def polars(self) -> plExpr:
        from polars import col
        return col(self.name)

    def polars_value(self) -> plExpr:
        from polars import col
        return col(self.name)

class Wildcard(NamedReference):
    """Represent a wildcard field reference."""

    def __hash__(self):
        return hash((self.name))
        
class EscapedNamedReference(NamedReference):
    """Reference a name that must be emitted with bracket escaping."""

    def __hash__(self):
        return hash((self.name))

    def deparse(self) -> str:
        from Hql.Expressions.Literals import StringLiteral
        return "[" + StringLiteral(self.name).quote("'") + "]"

# Why again?
# class HacNamedReference(NamedReference):
#     ...

class Path(Reference):
    """Reference a value through a sequence of nested field names."""

    def __init__(self, path:Sequence[Union[NamedReference, Path]]):
        Reference.__init__(self)
        self.path:list[NamedReference] = self.condense(path)

    # allows for collapsing single length paths
    def __new__(cls, path:list):
        if len(path) == 1:
            return path[0]
        return super().__new__(cls)

    # for copying/pickling
    def __reduce__(self):
        return (self.__class__, (self.path,))

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Path):
            return super().__eq__(value)

        if len(self.path) != len(value.path):
            return False

        for i in range(len(self.path)):
            if self.path[i] != value.path[i]:
                return False
        return True

    def __hash__(self):
        return hash(tuple([hash(x) for x in self.path]))

    def __setitem__(self, idx:int, value:str):
        self.path[idx].name = value
        return self

    def condense(self, path:Sequence[Reference]) -> list[NamedReference]:
        new = []
        for i in path:
            if isinstance(i, NamedReference):
                new.append(i)
            elif isinstance(i, Path):
                new += self.condense(i.path)
        return new
      
    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'path': [x.to_dict() for x in self.path]
        }

    def deparse(self) -> str:
        return '.'.join([x.deparse() for x in self.path])

    def list(self) -> list[str]:
        return [x.str() for x in self.path]

    def polars(self) -> plExpr:
        from polars import struct
        expr = self.polars_value()
        for i in self.path[::-1][1:]:
            expr = struct(expr).alias(i.str())
        return expr

    def polars_value(self) -> plExpr:
        expr = self.path[0].polars_value()
        for i in self.path[1:]:
            expr = expr.struct.field(i.str())
        return expr

    def preprocess(self, ctx: Context) -> object:
        rec = self.path[0].get_symbol(ctx)
        if not rec or not isinstance(rec, dict):
            return self

        for i in self.path[1:-1]:
            if i.name in rec:
                rec = rec[i.name]
            else:
                return self

        if self.path[-1].name in rec:
            rec = rec[self.path[-1].name]
        else:
            return self

        if isinstance(rec, dict):
            return self

        return rec

    def eval(self, ctx: Context, unnest:bool=False) -> Context:
        ctx = ctx.copy()
        if unnest:
            ctx.data = ctx.data.unnest(self)
        else:
            ctx.data = ctx.data.select(self)
        return ctx
    
class Element(Expression):
    '''
    One step into a value that a field path can't name: a list position, R[0],
    or a field reached through one, the type in R[0].type. Fields reached by name
    alone stay a Path, R['type'] is R.type.
    '''

    def __init__(self, base:Expression, key:Expression, dotted:bool=False):
        Expression.__init__(self)
        self.base = base
        self.key = key
        # Written as .name rather than ['name'], only kept so deparse round trips
        self.dotted = dotted

    def __reduce__(self):
        return (self.__class__, (self.base, self.key, self.dotted))

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Element):
            return False
        return self.base == value.base and self.key == value.key

    def __hash__(self):
        return hash(('element', hash(self.base), hash(self.key)))

    def index(self) -> Union[int, str]:
        '''A list position or a field name, nothing else indexes yet.'''
        from Hql.Expressions.Literals import Integer, StringLiteral
        from Hql.Expressions.Arithmetic import Negate

        key = self.key
        if isinstance(key, Integer):
            return key.value
        if isinstance(key, Negate) and isinstance(key.expr, Integer):
            return -key.expr.value
        if isinstance(key, StringLiteral):
            return key.str()
        raise hqle.QueryException(f'Unsupported index {key.deparse()} in {self.deparse()}, expected a whole number or a field name')

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'base': self.base.to_dict(),
            'key': self.key.to_dict(),
        }

    def deparse(self) -> str:
        from Hql.Expressions.Literals import StringLiteral
        if self.dotted and isinstance(self.key, StringLiteral):
            return f'{self.base.deparse()}.{self.key.str()}'
        return f'{self.base.deparse()}[{self.key.deparse()}]'

    def str(self) -> str:
        return self.deparse()

    def list(self) -> list[str]:
        # Names the value when it's stored, e.g. by a function evaluated over it
        return [self.deparse()]

    def __iter__(self):
        return iter(self.list())

    def select(self, table:Table) -> Optional[Table]:
        '''
        The indexed value as a one column table, None when the table can't be indexed
        like this, e.g. a missing field, as a missing field matches nothing in Hql.
        '''
        import polars as pl
        from Hql.Data import Table

        try:
            df = table.df.select(self.polars().alias(self.deparse()))
        except (pl.exceptions.ColumnNotFoundError, pl.exceptions.StructFieldNotFoundError,
                pl.exceptions.InvalidOperationError, pl.exceptions.SchemaError) as e:
            logging.warning(f'Could not index {self.deparse()} in {table.name}: {e}')
            return None
        return Table(df=df, name=table.name)

    def eval(self, ctx:Context, **kwargs) -> Context:
        from Hql.Data import Data, Series, Table

        ctx = ctx.copy()
        tables = []
        for table in ctx.data:
            value = self.select(table)
            if value is not None:
                tables.append(Table(name=table.name, series=Series(value.df.to_series())))
        ctx.data = Data(tables)
        return ctx

    def references(self) -> list[Reference]:
        '''The field this indexes into, at the bottom of the chain.'''
        base = self.base
        while isinstance(base, Element):
            base = base.base
        return [base] if isinstance(base, Reference) else []

    def polars(self) -> plExpr:
        base = self.base.polars_value() if isinstance(self.base, (Reference, Element)) else self.base.polars()
        idx = self.index()
        if isinstance(idx, str):
            return base.struct.field(idx)
        return base.list.get(idx, null_on_oob=True)

    def polars_value(self) -> plExpr:
        return self.polars()

'''
Sets a name a value

ip_addr, ip2 = ip4(destination.ip)
'''
class NamedExpression(Expression):
    """Assign an expression's value to one or more reference paths."""

    def __init__(self, paths:list[Reference], value:Union[Expression, Function]):
        Expression.__init__(self)
        self.paths = paths
        self.value = value

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, NamedExpression):
            return super().__eq__(value)

        if len(self.paths) != len(value.paths):
            return False

        # Create a shallow copy
        # Unordered comparison
        value_paths = [x for x in value.paths]
        for i in self.paths:
            if i in value_paths:
                value_paths.remove(i)
            else:
                return False

        if value_paths:
            return False

        if self.value != value.value:
            return False

        return True

    def __hash__(self):
        return hash((frozenset(self.paths), self.value))

    def to_dict(self):        
        return {
            'type': self.type,
            'name': [x.to_dict() for x in self.paths],
            'value': self.value.to_dict()
        }

    def deparse(self) -> str:
        paths = []
        for i in self.paths:
            paths.append(i.deparse())

        lh = ', '.join(paths)
        value = self.value.deparse()

        return f'{lh}={value}'

    def can_polars(self) -> bool:
        from Hql.Functions import Function
        if isinstance(self.value, Function):
            return False
        return True

    ## TODO
    # def polars(self) -> plExpr:
    #     return NotImplemented
    #
    #     if not self.can_polars():
    #         logging.error(self.deparse())
    #         raise hqle.CompilerException(f'Attempting to polars non-polars expression')
    #
    #     value = self.polars_value()
    #     exprs = []
    #
    #     for i in self.paths:
    #         i.polars()
    #
    #     return 

    ## TODO
    # def polars_value(self) -> plExpr:
    #     return NotImplemented
    #
    #     if isinstance(self.value, Function):
    #         logging.error(self.deparse())
    #         raise hqle.CompilerException(f'Attempting to polars non-polars expression')
    #     return self.value.polars()

    def eval(self, ctx:Context, insert:bool=True, unnest:bool=True) -> Context:
        from Hql.Expressions.Literals import Literal
        from Hql.Data import Data, Table
        from Hql.Context import Context
        ctx = ctx.copy()

        def get_value(ref:Union[Expression, Function], ctx:Context) -> Data:
            if isinstance(ref, Literal):
                series = ref.series()
                value = Data()
                for i in ctx.data:
                    value.add_table(Table(name=i.name, series=series))
            else:
                value = ref.eval(ctx)

                # Will always take place if not a function
                # Handles Expression case
                if isinstance(value, Context):
                    value = value.data

                # Functions can return a number of things
                if not isinstance(value, Data):
                    raise hqle.QueryException(ref.str() + ' did not eval to Data')

            return value

        def set_value(ref:Reference, value:Data, data:Data) -> Data:
            # loop through value tables as those are the only ones we can vouch for
            for table in value:
                # Need this if we're creating a new dataset instead of inserting
                if table.name not in data.tables:
                    data.add_table(Table(name=table.name))
                
                path = ref.list()
                
                cur = table

                if cur.series:
                    # Get the series and set the type
                    schema = cur.series.type
                    cur = cur.series.series
                    
                else:
                    # Get the value of the dataframe and schema
                    cur = cur.strip()

                    if len(cur.df):
                        schema = cur.schema
                        cur = cur.df

                    elif cur.series:
                        schema = cur.series.type
                        cur = cur.series.series

                    # empty case
                    else:
                        continue

                # Insert properly
                data.tables[table.name].insert(path, cur, schema)

            return data

        value = get_value(self.value, ctx)
        if unnest:
            ctx.data = value
            return ctx

        # Chose which dataset to insert on
        # If set to false it'll create it's own blank dataset
        if insert:
            data = ctx.data
        else:
            data = Data()

        for i in self.paths:
            data = set_value(i, value, data)

        ctx.data = data
        return ctx
