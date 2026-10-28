from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Union

import polars as pl

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Compiler import CompilerType 
from Hql.Types.Hql import HqlTypes as hqlt, SchemaDT

if TYPE_CHECKING:
    from Hql.Expressions.References import Reference

class Schema():
    """Track and transform the nested HQL types of tabular fields."""

    def __init__(
            self,
            schema:Union[SchemaDT, hqlt.object, None]=None,
            data:Union[pl.DataFrame, dict, list[dict], None]=None,
            sample_size:int=1
        ):
        self.schema:hqlt.object = hqlt.object(dict())

        if isinstance(data, (list, dict)):
            if isinstance(data, dict):
                data = [data]

            sample = data[:sample_size] if sample_size > 0 else data
            self.schema = Schema.from_json(sample).schema
            return

        if isinstance(data, pl.DataFrame):
            self.schema = Schema.from_df(data).schema
            return

        if schema:
            self.schema = schema if isinstance(schema, hqlt.object) else hqlt.object(schema)
            self.normalize()
        
        # Pass through empty case else we get an hqlt.object([])
        # Otherwise immediately convert to HqlTypes
        if len(self.schema):
            self.convert_schema()

        assert isinstance(self.schema, hqlt.object)
    
    def __len__(self) -> int:
        if hasattr(self.schema, '__len__'):
            return len(self.schema)
        else:
            return 0

    def __bool__(self) -> bool:
        return bool(self.schema)

    def __contains__(self, item:Reference) -> bool:
        cur = self.schema.schema
        for i in item.list():
            if not isinstance(cur, dict) or i not in cur:
                return False
            cur = cur[i]
        return True

    def __iter__(self):
        return iter(self.blowup_schema())

    def blowup_schema(self) -> list[tuple[Reference, CompilerType]]:
        from Hql.Expressions.References import NamedReference, Path
        
        def bs(schema:SchemaDT) -> list[tuple[Reference, CompilerType]]:
            out = []
            for key in schema:
                name = NamedReference(key)
                cur = schema[key]

                if isinstance(cur, hqlt.object):
                    cur = cur.schema

                if isinstance(cur, dict):
                    recurse = bs(cur)
                    for path, stype in recurse:
                        path = Path([name, path])
                        out.append((path, stype))
                else:
                    out.append((name, schema[key]))

            return out

        return bs(self.schema.schema)

    def to_dict(self) -> dict:
        return self.schema.to_dict()
    
    @staticmethod
    def merge(schemata:list[Schema]) -> Schema:
        from Hql.Types.Hql import HqlTypes as hqlt

        # generates key groups looking for conflicts
        # only does shallow level
        def gkg(schemata:list[hqlt.object]):
            keygroups = dict()
            for schema in schemata:
                for key in schema.schema:
                    if key not in keygroups:
                        keygroups[key] = [schema.schema[key]]
                    elif schema.schema[key] not in keygroups[key]:
                        keygroups[key].append(schema.schema[key])
            return keygroups

        # Create renames based on dupes
        # Shallow level only
        def rename(keygroups:dict) -> dict:
            new = dict()
            for key in keygroups:
                # recursable objects
                objs = []
                # normal singular types
                types:list[hqlt.HqlType] = []

                for i in keygroups[key]:
                    if isinstance(i, dict):
                        objs.append(hqlt.object(i))
                    elif isinstance(i, hqlt.object):
                        objs.append(i)
                    else:
                        types.append(i)

                if objs:
                    types = [hqlt.object(rename(gkg(objs)))] + types

                for i in types:
                    if key not in new:
                        new[key] = i
                    else:
                        new[f'{key}_{i.name}'] = i

            return new

        schemata = [x.normalize() for x in schemata]
        keygroups = gkg([x.schema for x in schemata])
        new = rename(keygroups)

        return Schema(schema=new)

    '''
    Created to solve the problem of nested Schema objects in a schema dict.
    Just unnests them such that we have a pure dict structure.
    '''
    def normalize(self):
        from Hql.Data import Schema
        from Hql.Types.Hql import HqlTypes as hqlt

        def n(node:Union[SchemaDT, Schema, hqlt.object]) -> dict:
            if isinstance(node, Schema):
                return n(node.schema)
            if isinstance(node, hqlt.object):
                return n(node.schema)

            new = dict()
            for key in node:
                cur = node[key]
                if isinstance(cur, (dict, Schema)):
                    new[key] = n(cur)
                elif isinstance(cur, hqlt.object) and cur.schema:
                    new[key] = n(cur.schema)
                else:
                    new[key] = node[key]
            return new

        self.schema = hqlt.object(n(self.schema))
        assert isinstance(self.schema, hqlt.object)
        return self

    # Isolate the schema at a given path
    def select(self, path:Reference) -> Schema:
        # unnest already rebuilds the full path around the value
        return self.unnest(path)

    def select_many(self, paths:Sequence[Reference]):
        schemas = []
        for path in paths:
            schemas.append(self.select(path))
        return Schema.merge(schemas)
    
    def unnest(self, path:Reference) -> Schema:
        def un(schema, path:list[str]):
            if path[0] not in schema:
                raise hqle.CompilerException(f'Failed to unnest value {path} in {schema}')

            val = schema[path[0]]

            if len(path) > 1 and not isinstance(val, (dict, hqlt.object)):
                raise hqle.CompilerException(f'Failed to unnest deeper path than schema: {path} in {schema}')

            if isinstance(val, hqlt.object):
                val = val.schema

            if isinstance(val, dict) and len(path) != 1:
                val = un(val, path[1:])

            return {path[0]: val}

        new = un(self.schema.schema, path.list())
        return Schema(schema=hqlt.object(new))

    
    def copy(self):
        from copy import deepcopy
        return Schema(schema=deepcopy(self.schema))
        
    '''
    Descriptive rename of unnest, might remove later
    '''
    def get_type(self, path:Reference) -> Union[hqlt.HqlType, Schema]:
        return self.unnest(path)

    '''
    Returns the deep stripped value of a dict with a single value.
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

    Doesn't return a schema object as it might be a type or a dict
    Typically this is called with a named expression, so it's gonna build the schema anyways.
    '''
    def strip(self) -> Union[Schema, hqlt.HqlType]:
        cur = self.schema
        while True:
            if isinstance(cur, hqlt.object):
                cur = cur.schema
            if not isinstance(cur, dict) or len(cur) != 1:
                break
            cur = next(iter(cur.values()))

        if isinstance(cur, dict):
            return Schema(schema=cur)
        else:
            return cur
    
    def rename(self, src:Reference, dest:Reference):
        if not self.assert_field(src):
            raise hqle.QueryException('Attempting to rename a non-existing field')
        
        if self.assert_field(dest):
            raise hqle.QueryException('Attempting to rename field into an existing field')
        
        src_type = self.pop(src)
        
        cur = self.schema
        for idx, i in enumerate(dest):
            # the previous assertion functions guarantee a destination path will work
            # adding to please the linter
            assert isinstance(cur, dict)

            if idx == len(dest) - 1:
                cur[i] = src_type
            else:
                cur = cur[i]
                
    def pop(self, name:Reference):
        if not self.assert_field(name):
            raise hqle.QueryException(f'Attempting to pop a non-existing field {name}')
        
        src_type = hqlt.null()
        cur = self.schema
        for idx, i in enumerate(name):
            # the previous assertion function guarantees our path exists
            # adding to please the linter
            assert isinstance(cur, dict)

            if idx == len(name) - 1:
                src_type = cur.pop(i)
            else:
                cur = cur[i]
                
        return src_type

    def drop(self, path:Reference):
        def d(path:Reference, schema:dict, idx:int=0) -> dict:
            new = {}
            for key in schema:
                if key == path[idx]:
                    if idx == len(path) - 1:
                        # Silent drop
                        continue

                    cur = schema[key]
                    if isinstance(cur, hqlt.object):
                        cur = cur.schema
                    if isinstance(cur, dict):
                        rec = d(path, cur, idx+1)
                        if rec:
                            new[key] = rec

                # Don't have to do anything
                else:
                    new[key] = schema[key]
            return new

        # Iterate the raw dict, not the hqlt.object: iterating hqlt.object
        # yields NamedReference keys, which would poison the rebuilt schema
        # (and never match path[idx], silently skipping the drop).
        raw = self.schema.schema if isinstance(self.schema, hqlt.object) else self.schema
        self.schema = hqlt.object(d(path, raw))
        return self
    
    def drop_many(self, paths:Sequence[Reference]):
        for path in paths:
            self.drop(path)
        return self
    
    '''
    Set a field to a specific type in the schema apply is then expected to be ran
    '''
    def set(self, path:Reference, htype:Union[CompilerType, Schema, dict]):
        if isinstance(htype, Schema):
            htype = htype.normalize().schema

        def s(path:Reference, htype:Union[CompilerType, dict], schema, idx:int=0):
            split = path[idx]

            if idx == len(path) - 1:
                schema[split] = htype
                return schema

            if split in schema:
                schema[split] = s(path, htype, schema[split], idx=idx+1)
            else:
                schema[split] = s(path, htype, {}, idx=idx+1)

            return schema

        self.schema = hqlt.object(s(path, htype, self.schema.schema))
        self.normalize()
        return self

    '''
    Generates a schema converted to a given schema target.
    Default is HqlTypes
    '''
    def convert_schema(self, target:str='hql') -> Schema:
        from Hql.Types.Hql import HqlTypes as hqlt

        def ce(node:CompilerType, target:str):
            if target == 'hql':
                return node.hql_schema()
            elif target == 'polars':
                return node.pl_schema()
            else:
                raise hqle.CompilerException(f'Unsupported type to convert {node} to {target}')

        def cs(schema:dict, target:str):
            out = dict()
            for key in schema:
                # Not sure if this is needed but I put it there anyways
                '''
                if not schema[key]:
                    target_schema[key] = hqlt.null()
                    continue
                '''
                
                if schema[key] == {}:
                    out[key] = ce(hqlt.object({}), target)
                elif isinstance(schema[key], dict):
                    out[key] = cs(schema[key], target)
                else:
                    out[key] = ce(schema[key], target)
        
            return out

        schema = self.schema.schema
        assert isinstance(schema, dict)

        self.schema = hqlt.object(cs(schema, target))
        return self
        
    '''
    Generates a schema for use in polars using their types
    Uses structs for nested objects instead of json objects
    '''
    def gen_pl_schema(self):
        schema = self.schema.pl_schema()
        assert isinstance(schema, pl.Struct)
        return schema.to_schema()

    '''
    Gen schema from dicts
    Uses python typing
    '''
    @staticmethod
    def from_json(data:list[dict]) -> Schema:
        from Hql.Types.Python import PythonTypes as pyt
        from Hql.Types.Hql import HqlTypes as hqlt

        def from_value(value) -> pyt.PythonType:
            if isinstance(value, dict):
                new = dict()
                for key in value:
                    new[key] = from_value(value[key])
                return pyt.dict(new)

            if isinstance(value, list):
                if not value:
                    return pyt.list(pyt.NoneType())

                return pyt.list(merge_python_types([from_value(item) for item in value]))

            ptype = pyt.from_name(type(value).__name__)
            return ptype() if isinstance(ptype, type) else ptype

        def from_sample(data:dict) -> pyt.dict:
            new = dict()
            for i in data:
                new[i] = from_value(data[i])
            return pyt.dict(new)

        def merge_python_types(types:list[pyt.PythonType]) -> pyt.PythonType:
            if all(isinstance(ptype, pyt.dict) for ptype in types):
                keys = set()
                for ptype in types:
                    assert isinstance(ptype, pyt.dict)
                    keys.update(ptype.schema)

                merged = dict()
                for key in keys:
                    values = []
                    for ptype in types:
                        assert isinstance(ptype, pyt.dict)
                        values.append(ptype.schema.get(key, pyt.NoneType()))
                    merged[key] = merge_python_types(values)

                return pyt.dict(merged)

            return pyt.resolve_conflict(types)

        schema = merge_python_types([from_sample(i) for i in data]).hql_schema()

        # Always expect object from dict
        assert isinstance(schema, hqlt.object)
        return Schema(schema=schema)
    
    '''
    Generates a schema using polars typing
    '''
    @staticmethod
    def from_df(df:pl.DataFrame) -> Schema:
        from Hql.Types.Polars import PolarsTypes as plt

        def gen_schema(df:pl.DataFrame) -> hqlt.object:
            schema = dict()
            
            for col in df:
                if isinstance(col.dtype, pl.Struct):
                    schema[col.name] = Schema.from_df(pl.DataFrame(col).unnest(col.name))
                    continue
                
                schema[col.name] = plt.from_pure_polars(col.dtype).hql_schema()
                
            return hqlt.object(schema)

        return Schema(schema=gen_schema(df))

    # Adjusts json to multivalue
    def adjust_mv(self, data:list[dict], schema:Union[dict, None]=None) -> list[dict]:
        from Hql.Types.Hql import HqlTypes as hqlt

        schema = schema if schema != None else self.schema
        
        # Loop through each defined multivalue field
        for key in schema:
            if isinstance(schema[key], dict):
                rows = []
                for row in data:
                    if key in row:
                        rows.append(row[key])
                        
                self.adjust_mv(data, schema=schema[key])
            
            if not isinstance(schema[key], hqlt.multivalue):
                continue
            
            for row in data:
                if key in row and not isinstance(row[key], list):
                    row[key] = [row[key]]

        return data
    
    '''
    Applies a schema to a dataset
    If a col is not defined in the schema, then it just skips over it
    Errors if a col defined in the schema is not in the df
    '''
    def apply(self, df:pl.DataFrame):
        import polars as pl

        def rec_apply(df:pl.DataFrame, schema:SchemaDT) -> pl.DataFrame:
            new = {}
            
            # Had this here to handle cases where the schema defines non-existing cols
            # This is fine, would likely help the receiving program.
            # We don't operate from the schema anyways, but from the dataframe
            # Keeping as we *might* want to do something?
            for key in schema:
                if key not in df:
                    # logging.warning(f"{key} not found in dataframe {', '.join(df.columns)}, manually adding")
                    # new[key] = pl.Series(name=key, values=[None] * df.height)
                    pass
            
            for col in df:
                key = col.name
                
                # Handle undefined types, don't have to worry about them, carry on.
                if key not in schema:
                    new[key] = col
                    continue

                cur = schema[key]

                if isinstance(cur, (dict, hqlt.object)):
                    if isinstance(cur, hqlt.object):
                        cur = cur.schema

                    new[key] = rec_apply(pl.DataFrame(col).unnest(key), cur).to_struct()
                    continue
                
                new[key] = cur.cast(col)

            return pl.DataFrame(new)

        return rec_apply(df, self.schema.schema)
    
    # Asserts by attempting to retrieve the field's value
    def assert_field(self, field:Reference):
        return field in self
        
    def present_complex(self, df:pl.DataFrame):
        def pc(df:pl.DataFrame, schema:dict):
            newdf = {}
            for col in df:
                if col.name not in schema:
                    newdf[col.name] = col
                    continue
                
                if isinstance(schema[col.name], dict):
                    newdf[col.name] = pc(col.struct.unnest(), schema[col.name]).to_struct()
                    continue

                if schema[col.name].complex:
                    newdf[col.name] = schema[col.name].human(col)
                else:
                    newdf[col.name] = col

            return pl.DataFrame(newdf)

        return pc(df, self.schema.schema)

    def join(self, right:Schema, on:Sequence[Reference], kind:str) -> Schema:
        # all of these are semantically the same schema wise
        if kind in ('inner', 'leftsemi', 'rightsemi', 'innerunique', 'leftouter', 'rightouter', 'fullouter'):
            new = self.copy()
            for path, stype in right:
                # change naming for duplicates
                if path in new and path not in on:
                    path[-1] += '_right'
                    new.set(path, stype)

                # No duplicate, matches both sets
                elif path in new and path in on:
                    ...

                # Not yet existing in schema
                elif path not in new:
                    new.set(path, stype)
            
            return new

        elif kind == 'leftanti':
            return self

        elif kind == 'rightanti':
            return right

        else:
            raise hqle.QueryException(f'Invalid join kind {kind} used')
            
