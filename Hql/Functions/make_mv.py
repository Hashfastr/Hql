from __future__ import annotations
from . import Function
from Hql.Expressions import Expression
from Hql.Context import register_func, Context
from Hql.Data import Data, Series, Table, Schema
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Exceptions import HqlExceptions as hqle
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    import polars as pl
    from Hql.Expressions.References import Reference

'''
This function is both an aggregate function and a normal function,
behavior will change accordingly.

If aggregate it will generate mutlivalue based on the aggregation.
If normal it will simply take those field values and join them into a multivalue field.

// Creates a non-directional IP field giving all IPs in a 5 minute bin
| summarize ips = make_mv(src_ip, dest_ip) by bin(['@timestamp'], 5m)

OR

// Joins the field in to a group of generic non-directional IPs
| extend ips = make_mv(source.ip, destination.ip)
'''
@register_func('make_list')
@register_func('make_mv')
class make_mv(Function):
    """Combine fields or aggregation values into a multivalue field."""

    def __init__(self, args:list[Expression], conf:Optional[dict]=None):
        Function.__init__(self, args, 1, -1)
        self.args = args
    
    '''
    Takes in a schema and a list of paths
    Creates a schema consisting of only those paths
    Each type is then set to a hqlt.multivalue type
    Output schema only contains the multivalue types of those paths.
    '''
    def gen_schema(self, schema:Schema, paths:Sequence[Reference]):
        schema = schema.select_many(paths)
        
        new = Schema()
        for path in paths:
            t = schema.select(path).strip()
            
            if isinstance(t, dict):
                raise hqle.QueryException(f'Object is an unsupported multivalue type at the moment.')

            if not isinstance(t, hqlt.HqlType):
                raise hqle.CompilerException(f'Attempting to make multivalue of type {type(t)}')

            t = hqlt.multivalue(t)
            new.set(path, t)

        return new
    
    '''
    Need to rebuild, shouldn't be hard.
    '''
    def aggregate(self, ctx:Context, table:Table):
        cols = []
        paths = []
        for arg in self.args:
            cols.append(arg.polars())
            paths.append(arg)
        
        if table.agg == None:
            raise hqle.CompilerException('Attempting to aggregate with a None Table.agg')

        # Generates our mv
        df = table.agg.agg(cols)
                    
        schema = self.gen_schema(table.schema, paths)

        # Drop the aggregation fields as they can be added back later
        # Such as with a summarize
        new = Table(df=df, schema=schema, name=table.name)
        return new.drop_many(table.agg_paths)
    
    '''
    Recursively create a list of series for each value referenced in a schema

    '''
    def get_series(self, df:pl.DataFrame, schema:dict):
        cur = []
                
        for key in schema:
            if isinstance(schema[key], dict):
                cur += self.get_series(df.select(key).unnest(key), schema[key])
                continue
            
            series = df.select(key).to_series().rename('')
            stype = schema[key]
            cur.append(Series(series, stype))
            
        return cur
    
    '''
    Takes in our args and resolves them using a project call.
    Then gets the values, aka series, for each reference.
    Finds a common type, cast everything to that type, then joins into one big series.

    Returns a Series with a multivalue type
    '''
    def normal(self, ctx:Context, table:Table):
        import polars as pl
        from Hql.Operators.Project import Project

        # Only operate on the single table
        ctx.data = Data(tables=[table])

        # Create the data subset and grab the table
        # Using project as it resolves functions for us, clever huh?
        data:Data = Project(self.args).eval(ctx).data
        table = data.table_by_index(0)
        series = self.get_series(table.df, table.schema.schema)
        
        # Cast to our agreed upon type
        mv_type = hqlt.resolve_conflict([x.type for x in series])
        series = [mv_type.cast(x.series) for x in series]
        series = pl.Series(pl.DataFrame(series).rows())
        mv_type = hqlt.multivalue(mv_type)
        
        return Series(series, mv_type)
        
    def eval(self, ctx: Context, receiver=None, as_value:bool=False) -> object:
        import polars as pl
        import polars.dataframe.group_by as group_by
        
        new = []
        for table in ctx.data:
            # Make mv over an aggregation
            if isinstance(table.agg, group_by.GroupBy):
                new.append(self.aggregate(ctx, table))
                continue
            
            series = self.normal(ctx, table)
            
            if as_value:
                new.append(Table(series=series, name=table.name))
                continue
            
            df = pl.DataFrame({'mv': series.series})
            schema = {'mv': series.type}

            new.append(Table(df=df, schema=Schema(schema=schema), name=table.name))
        
        return Data(tables=new)
