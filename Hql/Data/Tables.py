from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Union

import polars as pl
from polars.dataframe.group_by import GroupBy

from .Series import Series
from Hql.Exceptions import HqlExceptions as hqle
from Hql.PolarsTools import pltools
from Hql.Types.Hql import HqlTypes as hqlt

from Hql.Expressions.References import NamedReference, Path

import logging
import json

if TYPE_CHECKING:
    from Hql.Expressions.References import Reference
    from .Schema import Schema

'''
Table for a structure of data, includes schema definition.
Mimics a pl.DataFrame
'''
class Table():
    """Store a named Polars table together with its HQL schema."""

    def __init__(
            self,
            df:Union[pl.DataFrame, None]=None,
            series:Union[Series, None]=None,
            init_data:Union[list[dict], None]=None,
            schema:Union[Schema, dict, None]=None,
            name:Union[str, None]=None
        ):
        from Hql.Data import Schema
        
        self.df:pl.DataFrame = df if isinstance(df, pl.DataFrame) else pl.DataFrame()
        
        if isinstance(schema, dict):
            schema = Schema(schema=schema)
        
        self.name = name if name else ''
        self.series = None
        self.schema = Schema() # safe default
       
        # rely on self.agg being None for the existence of an aggregation
        self.agg:Optional[GroupBy] = None
        self.agg_paths:list[Reference] = []
        self.agg_schema:Schema = Schema()

        if series:
            self.series = series

        elif init_data and not schema:
            self.schema = Schema(data=init_data, sample_size=-1)
            init_data = self.schema.adjust_mv(init_data)
            pl_schema = self.schema.gen_pl_schema()

            try:
                self.df = pl.from_dicts(init_data, schema=pl_schema, strict=False)
            except pl.exceptions.ComputeError as e:
                logging.warning(e)
                logging.warning(f'Possible typing issue caught when loading dicts into table {self.name}')
                logging.warning(f'Offending schema: {json.dumps(self.schema.to_dict())}')
                logging.warning('Retrying with polars inference over all rows')

                # Serialize values polars can't put in a string column (e.g. dict vs str),
                # then let polars infer widths (e.g. ints overflowing the inferred type).
                # Never drop the data, if this fails we want the error.
                init_data = self.schema.adjust_str(init_data)
                self.df = pl.from_dicts(init_data, infer_schema_length=None, strict=False)
                self.schema = Schema(data=self.df)
        
        elif init_data and schema:
            self.schema = schema
            pl_schema = schema.gen_pl_schema()
            self.df = pl.from_dicts(init_data, schema=pl_schema)
        
        elif self.df.width and schema:
            self.schema = schema
            self.df = schema.apply(self.df)

        elif self.df.width and not schema:
            self.schema = Schema(data=self.df)

        elif schema:
            logging.warning('Schema defined in table without data')
            self.schema = schema

        else:
            self.schema = Schema()

    def __len__(self):
        if hasattr(self.df, '__len__'):
            return len(self.df)
        return 0

    def to_dicts(self):
        human = self.schema.present_complex(self.df)
        return human.to_dicts()

    def get_schema(self):
        return self.schema.to_dict()

    # Shallow copy, polars frames are immutable but our schema is not
    def copy(self) -> Table:
        new = Table(name=self.name)
        new.df = self.df
        new.series = self.series
        new.schema = self.schema.copy()
        new.agg = self.agg
        new.agg_paths = list(self.agg_paths)
        new.agg_schema = self.agg_schema
        return new

    def set_schema(self, schema:Schema):
        self.df = schema.apply(self.df)
        self.schema = schema

    def get_type(self, path:Reference):
        if self.schema:
            return self.schema.get_type(path)
        return None

    def drop(self, path:Reference, df:Union[pl.DataFrame, None]=None, idx:int=0) -> Union[pl.DataFrame, Table]:
        if isinstance(df, type(None)) and idx != 0:
            raise hqle.CompilerException('Logic error? Would reinit df with a non-zero index.')

        if isinstance(df, type(None)):
            self.schema.drop(path)
            assert isinstance(self.df, pl.DataFrame)
            df = self.df
        assert not isinstance(df, type(None))

        new = {}
        for col in df:
            if col.name == path[idx]:
                if idx == len(path) - 1:
                    # silent drop
                    continue
                
                if col.dtype == pl.Struct:
                    rec = self.drop(path, df=pl.DataFrame(col).unnest(col.name), idx=idx+1)
                    
                    if not isinstance(rec, pl.DataFrame):
                        raise hqle.CompilerException('Logic error? Final recursion step hit before end.')

                    # width, zero row structs still have fields
                    if rec.width:
                        new[col.name] = rec.to_struct(col.name)

                # Path goes deeper than this scalar, nothing to drop
                else:
                    new[col.name] = col
                
            # Not dropping
            else:
                new[col.name] = col
        
        # end of recursion
        if idx == 0:
            self.df = pl.DataFrame(new)
            return self
            
        return pl.DataFrame(new)
    
    def drop_many(self, paths:Sequence[Reference]):
        for path in paths:
            self.drop(path)
        return self
        
    '''
    Truncates the dataset to a given amount
    '''
    def truncate(self, amount:int):
        self.df = self.df[:amount]

    '''
    Runs a polars filter on the table
    '''
    def filter(self, expr:pl.Expr):
        try:
            self.df = self.df.filter(expr)
        except pl.exceptions.ColumnNotFoundError as e:
            raise hqle.UnreferencedFieldException(e.args[0])
        
    def get_value(self, path:Reference):
        return pltools.get_element_value(self.df, path.list())

    @staticmethod
    def merge_rows(tables:list[Table]):
        from Hql.Data import Schema

        if not tables:
            return Table()
        
        # Quick short circuit
        if len(tables) == 1:
            return tables[0]
        
        name = tables[0].name
        
        schemas = []
        for table in tables:
            schemas.append(table.schema)
        # Work on the raw dict, hqlt.object is keyed by references and immutable
        schema = Schema.merge(schemas).schema.schema
        
        # generate col groups
        longest_len = 0
        col_groups = dict()
        for table in tables:
            # skip tables without columns, zero row tables still carry columns
            if isinstance(table.df, type(None)) or not table.df.width:
                continue

            for col in table.df:
                longest_len = len(col) if len(col) > longest_len else longest_len
                if col.name not in col_groups:
                    col_groups[col.name] = []
                col_groups[col.name].append(col)

        new = dict()
        for key in col_groups:
            for col in col_groups[key]:
                if longest_len > len(col):
                    if len(col) == 1:
                        col = col.new_from_index(0, longest_len)
                    else:
                        pad = longest_len - len(col)
                        col = col.extend_constant(None, pad)

                if key not in new:
                    new[key] = col
                    continue
                
                # Canon conflict
                if not isinstance(new[key], list) and new[key].dtype == pl.Struct and col.dtype == pl.Struct:
                    l = Table(df=new[key].struct.unnest(), name=name)
                    r = Table(df=col.struct.unnest(), name=name)
                    
                    merged = Table.merge_rows([l, r])
                    new[key] = merged.df.to_struct(key)
                    schema[key] = merged.schema.schema.schema
                    continue

                if not isinstance(new[key], list):
                    new[key] = [new[key], col]
                else:
                    new[key].append(col)

        # Conflicting columns become a multivalue holding each table's value per row
        for key in new:
            if not isinstance(new[key], list):
                continue

            new[key] = pl.select(pl.concat_list(new[key]).alias(key)).to_series()

            cur = schema.get(key)
            if isinstance(cur, dict):
                cur = hqlt.object(cur)
            if isinstance(cur, hqlt.HqlType) and not isinstance(cur, hqlt.multivalue):
                cur = hqlt.multivalue(cur)

            if isinstance(cur, hqlt.multivalue) and cur.pl_schema() == new[key].dtype:
                schema[key] = cur
            else:
                # Polars had to resolve differing types, follow its lead
                schema[key] = Schema.from_df(new[key].to_frame()).schema.schema[key]
        
        df = pl.DataFrame(new)
        schema = Schema(schema=schema)
                
        return Table(df=df, schema=schema, name=name)

    @staticmethod
    def merge(tables:list[Table], merge_rows=True):
        from Hql.Types.Compiler import CompilerType
        from Hql.Data import Schema

        if merge_rows:
            return Table.merge_rows(tables)

        if not tables:
            return Table()
        
        # Quick short circuit
        if len(tables) == 1:
            return tables[0]

        groups = dict()
        for table in tables:
            if table.name in groups:
                groups[table.name].append(table)
            else:
                groups[table.name] = [table]

        name = tables[0].name
        
        schemas = []
        for table in tables:
            schemas.append(table.schema)
        schema = Schema.merge(schemas)

        # Makes an assumption that the above merge converted field names accurately
        # in the case of a conflict, e.g. they get split into types.
        new = []
        for table in tables:
            cur = table.df
            # raw dict, iterating hqlt.object yields references rather than names
            curs = table.schema.schema.schema
            for key in curs:
                if isinstance(curs[key], CompilerType):
                    dup_key = f'{key}_{curs[key].name}'
                else:
                    dup_key = f'{key}_object'

                if dup_key in schema.schema.schema:
                    cur = cur.rename({key: dup_key})
            new.append(cur)

        df = pl.concat(new, how='diagonal_relaxed')
        return Table(df=df, schema=schema, name=name)

    '''
    Takes in a reference path
    client.ip.src
    Returns a Table with just the data of that path
    If not found then it returns an empty table with the parent name.
    '''
    def select(self, field:Reference):
        if not self.assert_field(field):
            return Table(name=self.name)
        
        df = pltools.get_element(self.df, field.list())
        schema = self.schema.select(field)

        return Table(df=df, schema=schema, name=self.name)

    def unnest(self, field:Reference) -> Table:
        from Hql.Data import Schema

        if not isinstance(self.schema, Schema):
            raise hqle.CompilerException('Attempting to unnest an uninitalized table object with a None Schema')

        if not self.assert_field(field):
            raise hqle.QueryException(f"Could not unnest field {field.deparse()} from table {self.name}")
        
        df = self.get_value(field)
        # Exactly the field's type, strip would also descend through single key children
        dtype = self.schema.schema[field]

        if isinstance(df, pl.Series):
            if isinstance(dtype, hqlt.multivalue):
                df = df.explode(empty_as_null=False)
                dtype = dtype.inner

                if isinstance(dtype, hqlt.object):
                    df = df.struct.unnest()
                else:
                    name = dtype.name
                    df = df.to_frame(name=name)
                    dtype = hqlt.object({name: dtype})

        if not isinstance(df, pl.DataFrame):
            raise hqle.CompilerException(f'Table unnest resulted in Non-DataFrame: {type(df)}')

        if isinstance(dtype, hqlt.object):
            schema = Schema(schema=dtype)
        elif isinstance(dtype, Schema):
            schema = dtype
        else:
            raise hqle.CompilerException(f'Table unnest resulted in invalid data type: {type(dtype)}')

        return Table(df=df, schema=schema, name=self.name)

    '''
    Returns the deep stripped value of a DataFrame with a single value.
    So {'destination': {'ip': hqlt.ip4}} would just return hqlt.ip4.
    A more complex case is:

    {
        'destination': {
            'ip': hqlt.ip4,
            'port': hqlt.short
        }
    }

    Which would just return:

    {
        'ip': hqlt.ip4,
        'port': hqlt.short
    }

    The idea here is if you want to extract the value of a function, this does it.
    '''
    def strip(self):
        from Hql.Data import Schema
        
        cur = self.df
        path = []
        while isinstance(cur, pl.DataFrame) and len(cur.columns) == 1:
            key = cur.columns[0]
            cur = pltools.get_element_value(cur, [key])
            path.append(NamedReference(key))
        
        # Using this instead of strip to ensure we're in sync
        if path:
            schema = self.schema.unnest(Path(path)).strip()
            # strip hands back a Schema when it stops on a multi field object
            if isinstance(schema, Schema):
                schema = schema.schema
        else:
            schema = self.schema.schema

        if isinstance(cur, pl.Series):
            if isinstance(schema, dict):
                raise hqle.CompilerException('Schema generated for series is a dict!')

            series = Series(cur, stype=schema)
            return Table(series=series, name=self.name)
            
        if not isinstance(schema, hqlt.object):
            raise hqle.CompilerException('Schema generated for a dataframe is a non-dict!')

        return Table(df=cur, schema=Schema(schema), name=self.name)

    def rename(self, src:Reference, dest:Reference):
        if not self.assert_field(src):
            raise hqle.QueryException('Attempting to rename a non-existing field')
        
        #if self.assert_field(dest):
        #    raise hqle.QueryException('Attempting to rename field into an existing field')
        
        popped = self.pop(src)
        value = popped.get_value(src)
        schema = popped.schema.schema[src]
        if isinstance(schema, hqlt.object):
            schema = schema.schema

        if not isinstance(schema, (dict, hqlt.HqlType)):
            raise hqle.CompilerException(f'Attempting to rename with schema of type {type(schema)}')
        
        self.insert(dest, value, schema)
    
    # Inserts a piece of data at a given name
    def insert(
            self,
            name:Reference,
            value:Union[pl.DataFrame, pl.Series],
            vtype:Union[hqlt.HqlType, dict],
            cur_df:Union[None, pl.DataFrame]=None,
            idx:int=0
        ) -> pl.DataFrame:
        if isinstance(cur_df, type(None)):
            cur_df = self.df

        # Conflicts rename path segments, work on a copy rather than the caller's reference
        if idx == 0:
            parts = name.list() if isinstance(name, (NamedReference, Path)) else list(name)
            name = Path([NamedReference(x) for x in parts])
            
        split = name[idx]
                
        # Endpoint
        if idx == len(name) - 1:
            # Find a unique name
            if split in cur_df:
                i = 0
                while f'{split}_{i}' in cur_df:
                    i += 1
                split = f'{split}_{i}'
                name[idx] = split
                        
            self.schema.set(name, vtype)
            new = pl.DataFrame({name[-1]: value})
        
        # Not the end, but we're now free to do whatever we want
        elif split not in cur_df:
            recurse = self.insert(name, value, vtype, cur_df=pl.DataFrame(), idx=idx + 1)
            new = pl.DataFrame({split: recurse.to_struct()})
        
        # Recurse up a nested object
        elif cur_df[split].dtype == pl.Struct:        
            recurse = self.insert(name, value, vtype, cur_df=cur_df.select(split).unnest(split), idx=idx + 1)
            cur_df = cur_df.drop(split)
            new = pl.DataFrame({split: recurse.to_struct(split)})
        
        # Conflict, a base type is where we're trying to put a struct
        else:
            i = 0
            while f'{split}_{i}' in cur_df:
                # Merging case
                if cur_df[f'{split}_{i}'].dtype == pl.Struct:
                    break
                i += 1
            split = f'{split}_{i}'
            name[idx] = split
         
            if split in cur_df and cur_df[split].dtype == pl.Struct:
                recurse = self.insert(name, value, vtype, cur_df=cur_df.select(split).unnest(split), idx=idx + 1)
                cur_df = cur_df.drop(split)
            else:
                recurse = self.insert(name, value, vtype, cur_df=pl.DataFrame(), idx=idx + 1)
            
            new = pl.DataFrame({split: recurse.to_struct(split)})
        
        new = pl.concat([new, cur_df], how='horizontal')
        
        if idx == 0:
            self.df = new
        
        return new

    def remove(self, name:Reference, cur_df:Union[None, pl.DataFrame]=None, idx:int=0):
        if isinstance(cur_df, type(None)):
            cur_df = self.df
            
        if idx == 0 and not self.assert_field(name):
            return cur_df
            
        split = name[idx]
        mask = cur_df.drop(split)
        
        if idx == len(name) - 1:
            return mask
        
        if cur_df[split].dtype == pl.Struct:
            recurse = self.remove(name, cur_df=cur_df.select(split).unnest(split), idx=idx + 1)
            
            if recurse.width:
                recurse = pl.DataFrame({split: recurse.to_struct(split)})
                merged = pl.concat([mask, recurse], how='horizontal')
            else:
                merged = mask
        else:
            merged = mask

        return merged
            
    def pop(self, name:Reference):
        if not self.assert_field(name):
            raise hqle.QueryException('Attempting to pop a non-existing field')
        
        # Schema is tracked through the select
        value = self.select(name)
        # remove checks the schema, so pop it afterwards
        self.df = self.remove(name)
        self.schema.pop(name)
        
        return value
    
    # Asserts by checking against schema
    # Schema should always be sync'd with the table data
    def assert_field(self, field:Reference):
        return self.schema.assert_field(field)
    
    def cast_in_place(self, path:Reference, cast_type:hqlt.HqlType):
        if not self.assert_field(path):
            return self
        
        self.schema.set(path, cast_type)
        self.df = self.schema.apply(self.df)

        return self
    
    def join(self, right:Table, on:Sequence[Reference], kind:str):
        from Hql.Context import Context
        from Hql.Data import Data, Schema

        # faux ctx
        ctx = Context(Data())

        if not isinstance(on, list):
            on = [on]
        if not isinstance(self.df, pl.DataFrame):
            raise hqle.CompilerException(f'Attempting to join with left non-dataframe: {type(self.df)}')
        if not isinstance(right.df, pl.DataFrame):
            raise hqle.CompilerException(f'Attempting to join with right non-dataframe: {type(right.df)}')

        schema = self.schema.join(right.schema, on, kind)

        # Join keys must be bare values, Path.polars() rebuilds the struct with an alias
        pl_on = []
        for i in on:
            pl_on.append(i.polars_value())

        # Keep key coalescing explicit, Schema.join mirrors this behavior
        coalesce = Schema.join_coalesces(on, kind)

        if kind == 'inner':
            df = self.df.join(right.df, on=pl_on, how='inner', coalesce=coalesce)
        
        elif kind == 'leftsemi':
            df = self.df.join(right.df, on=pl_on, how='semi')

        elif kind == 'rightsemi':
            df = right.df.join(self.df, on=pl_on, how='semi')

        elif kind == 'leftouter':
            df = self.df.join(right.df, on=pl_on, how='left', coalesce=coalesce)

        elif kind == 'rightouter':
            df = self.df.join(right.df, on=pl_on, how='right', coalesce=coalesce)

        elif kind == 'fullouter':
            df = self.df.join(right.df, on=pl_on, how='full', coalesce=coalesce)

        elif kind == 'leftanti':
            df = self.df.join(right.df, on=pl_on, how='anti')

        elif kind == 'rightanti':
            df = right.df.join(self.df, on=pl_on, how='anti')

        elif kind == 'innerunique':
            left = self.df.unique(subset=pl_on)
            df = left.join(right.df, on=pl_on, how='inner', coalesce=coalesce)

        else:
            raise hqle.QueryException(f'Invalid join kind {kind} used')
        
        return Table(df=df, schema=schema, name=self.name)

    '''
    Sorts by expression, if they exist
    '''
    def sort(self, exprs:list[pl.Expr], orders:Union[None, list[bool]]=None, nulls:Union[None, list[bool]]=None):
        orders = [True for x in exprs] if orders is None else orders
        nulls = [x for x in orders] if nulls is None else nulls
        exprs = exprs if isinstance(exprs, list) else [exprs]
        
        if len(orders) < len(exprs):
            logging.warning('Passing incomplete list of orders to table sort, defaulting to desc for missing values')
            for i in range(len(exprs) - len(orders)):
                orders.append(True)
                
        if len(nulls) < len(exprs):
            logging.warning('Passing incomplete list of nulls to table sort, defaulting to last for missing values')
            for i in range(len(exprs) - len(nulls)):
                nulls.append(True)
        
        texprs = []
        torders = []
        tnulls = []
        for idx, expr in enumerate(exprs):
            try:
                self.df.select(expr)
                texprs.append(exprs[idx])
                torders.append(orders[idx])
                tnulls.append(nulls[idx])
            except:
                continue

        # No applicable sort
        if not len(texprs):
            return self
        
        self.df = self.df.sort(by=texprs, descending=torders, nulls_last=tnulls)
        return self
