from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Sequence, Union, Iterator
from fnmatch import fnmatch

from .Tables import Table
from .Schema import Schema
from .Series import Series
from Hql.Exceptions import HqlExceptions as hqle

import logging

if TYPE_CHECKING:
    from Hql.Types.Hql import HqlTypes as hqlt
    from Hql.Expressions.References import Reference

class Data():
    """Manage a collection of named HQL tables as one dataset."""

    def __init__(self, tables:Optional[list[Table]]=None, merge_rows=True):
        self.tables = dict()

        # empty base case
        if not tables:
            return

        table_groups = dict()

        for table in tables:
            if not isinstance(table, Table):
                raise hqle.CompilerException('Non-table passed to Data as init data')

        # Give names to names-less tables
        for idx, i in enumerate(tables):
            if not i.name:
                i.name = f'Table {idx}'

        # Form table groups for merging
        for i in tables:
            if i.name not in table_groups:
                table_groups[i.name] = [i]
            else:
                table_groups[i.name].append(i)

        # Merge table groups
        for name in table_groups:
            self.tables[name] = Table.merge(tables=table_groups[name], merge_rows=merge_rows)
            
    def __len__(self):
        length = 0
        for table in self:
            length += len(table)
            
        return length

    def __iter__(self) -> Iterator[Table]:
        tables = []
        for name in self.tables:
            tables.append(self.tables[name])
            
        return iter(tables)

    def __bool__(self):
        for i in self.tables:
            if len(self.tables[i]):
                return True
        return False

    def __contains__(self, key:str):
        return key in self.tables

    def __setitem__(self, key:str, item:Table):
        self.tables[key] = item

    def __getitem__(self, key:str) -> Table:
        return self.tables[key]

    '''
    Gets tables relevant to a given table pattern
    
    * 
    gets all tables
    
    so-beats-*
    gets all tables starting with so-beats-
    
    so-network-2022.10
    Just gets the table named so-network-2022.10
    '''
    def get_tables(self, pattern:str) -> list[Table]:
        tables = []
        for table in self:
            if fnmatch(table.name, pattern):
                tables.append(table)
        return tables
    
    def table_by_index(self, idx:int):
        key = list(self.tables.keys())[idx]
        return self.tables[key]
    
    def add_table(self, table:Table):
        if table.name in self.tables:
            raise hqle.QueryException(f'Table {table.name} already exists')
        
        self.tables[table.name] = table
        
    def replace_table(self, table:Table):
        self.tables[table.name] = table
        
    def get_schema(self):
        schemata = {}
        for table in self:
            schemata[table.name] = table.get_schema()
        
        return schemata

    # Given a path, select just the data at that path
    def select(self, ref:Reference):
        tables = []
        for table in self:
            tables.append(table.select(ref))

        return Data(tables=tables)
    
    def unnest(self, ref:Reference):
        tables = []
        for table in self:
            new = table.unnest(ref)
            
            if isinstance(new, Series):
                new = Table(series=new, name=table.name)
            
            tables.append(new)
        
        return Data(tables=tables)

    def to_dict(self):
        dataset = dict()
        
        dataset['data'] = {}
        for table in self:
            dataset['data'][table.name] = table.to_dicts()
            
        dataset['schema'] = self.get_schema()

        return dataset
   
    @staticmethod
    def merge(data:list[Data], merge_rows=True):
        if len(data) == 1:
            return data[0]
        
        tables = []
        for datum in data:
            for table in datum:
                tables.append(table)

        return Data(tables=tables, merge_rows=merge_rows)

    # Ensures that the field exists in at least one table
    # Returns the tables where it does exists
    def assert_field(self, field:Reference):
        exists = []
        
        if not self.tables:
            return exists
        
        for table in self:
            if table.assert_field(field):
                exists.append(table)

        if not len(exists):
            logging.warning(f"Could not find {field.deparse()} in any tables in the dataset")
            logging.warning(', '.join([x.name for x in self]))
        
        return exists
    
    def cast_in_place(self, field:Reference, cast_type:hqlt.HqlType):
        tables = self.assert_field(field)
        if not tables:
            return False

        for i in tables:
            i.cast_in_place(field, cast_type)

        return self

    def join(self, right:Data, on:Sequence[Reference], kind:str='innerunique'):
        tables = []
        for lt in self:
            new = []
            for rt in right:
                new.append(lt.join(rt, on, kind))

            tables.append(Table.merge(new, merge_rows=False))
        
        return Data(tables=tables, merge_rows=False)
    
    def strip(self):
        new = []
        for table in self:
            new.append(table.strip())
        return Data(tables=new)

    def drop_many(self, paths:Sequence[Reference]):
        cur = self
        for path in paths:
            cur = cur.drop(path)
        return cur

    def drop(self, path:Reference):
        # Table.drop works in place, copy so the tables shared with the
        # caller (e.g. through Context.copy) keep their fields
        new = []
        for table in self:
            new.append(table.copy().drop(path))
        return Data(tables=new)
