from __future__ import annotations
from . import Database

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Data import Data, Table, Schema
from Hql.Context import register_database

from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Operators.Operator import Operator
    from Hql.Compiler import BranchDescriptor

import os
import polars as pl
import logging
import requests
from pathlib import Path
from io import StringIO

# Index in a database to grab data from, extremely simple.
@register_database('CSV')
class CSV(Database):
    def __init__(self, config:dict, name:str='csv'):
        Database.__init__(self, config, name=name)
        config = config.get('conf', dict())
        
        self.files = []
        self.urls = []
        self.local_base = Path(config.get('local-base', './'))
        self.http_base:str = config.get('http-base', '')
        
        self.methods = [
            'file',
            'http',
            'macro'
        ]
        
        self.limits:dict[str, int] = dict()

    def from_file(self, filename:str, limit:Optional[int]=None) -> Table:
        try:
            with open(self.local_base / filename, mode='r') as f:
                if limit != None:
                    data = pl.read_csv(f, n_rows=limit)
                else:
                    data = pl.read_csv(f)
        except:
            logging.critical(f'Could not load csv from {filename}')
            raise hqle.QueryException('CSV database not given valid csv data')
                
        return Table(df=data, name=filename)
        
    def from_url(self, url:str, limit:Optional[int]=None) -> Table:
        try:
            url = f'{self.http_base}/{url}' if self.http_base else url
            
            res = requests.get(url)
            if res.status_code != 200:
                raise hqle.QueryException(f'Could not query remote url {url}')
            
            name = url.split('/')[-1]
            reader = StringIO(res.text)

            if limit != None:
                data = pl.read_csv(reader, n_rows=limit)
            else:
                data = pl.read_csv(reader)
        
            return Table(df=data, name=name)
        except:
            logging.critical(f'Could not load csv from {url}')
            raise hqle.QueryException('CSV databse not given valid csv data')

    def get_limit(self, name:str) -> Optional[int]:
        from fnmatch import fnmatch

        cur = None
        for i in self.limits:
            if fnmatch(name, i):
                if cur == None:
                    cur = self.limits[i]
                    continue
                cur = self.limits[i] if self.limits[i] < cur else cur

        return cur

    def set_limit(self, name:str, limit:int):
        cur = self.get_limit(name)
        if cur == None:
            self.limits[name] = limit
        else:
            # Ensure we don't override a smaller take
            self.limits[name] = limit if limit < cur else cur

    def add_op(self, op: Union[Operator, BranchDescriptor]) -> tuple[Union[Operator, None], Union[Operator, None]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Take import Take

        if isinstance(op, BranchDescriptor):
            op = op.get_op()

        if isinstance(op, Take):
            if not op.tables:
                self.set_limit('*', op.expr.value)

            for i in op.tables:
                self.set_limit(i.str(), op.expr.value)

            return op, None

        return None, op
                
    def eval(self, ctx:Context) -> Context:
        # just check file, base_path is check upon instanciation
        if not self.files and not self.urls:
            logging.critical('No file or http provided to CSV database')
            logging.critical('Correct usages:')
            logging.critical('                database("csv").file("filename")')
            logging.critical('                database("csv").http("https://host/file.csv")')
            logging.critical('Where filename exists relative to the configured base_path')
            raise hqle.QueryException('No file provided to CSV database')
        
        tables = []
        for file in self.files:
            limit = self.get_limit(file)
            tables.append(self.from_file(file, limit=limit))

        for url in self.urls:
            limit = self.get_limit(url.split('/')[-1])
            tables.append(self.from_url(url, limit=limit))
                
        ctx = ctx.copy()
        ctx.data = Data(tables=tables)
        return ctx
