from __future__ import annotations
from Hql.Exceptions import HqlExceptions as hqle
from typing import TYPE_CHECKING, Optional
import logging

from Hql.Cache import Cache

from Hql.Config import Config

if TYPE_CHECKING:
    from Hql.Data import Data
    from Hql.Hac import Hac

database_registry = {}

def register_database(name:str):
    def decorator(cls):
        from Hql.Database import Database

        if not issubclass(cls, Database):
            raise hqle.CompilerException(f'Attempting to register non-database class {name} as a database')

        database_registry[name] = cls
        return cls
    return decorator

def get_database(name:str):
    if name in database_registry:
        return database_registry[name]
    else:
        raise hqle.CompilerException(f"Unknown database type {name}")
    
func_registry = {}

def register_func(name):
    def decorator(cls):
        from Hql.Functions import Function

        if not issubclass(cls, Function):
            raise hqle.CompilerException(f'Attempting to register non-function class {name} as a function')

        func_registry[name] = cls
        return cls

    return decorator

def get_func(name):
    if name in func_registry:
        return func_registry[name]
    else:
        raise hqle.CompilerException(f"Unknown function {name} referenced")

'''
The naming scheme here is 

{db_type}_{typename}

So for Elasticsearch it would be

elasticsearch_scaled_float

Since the schema provided by elasticsearch calls that type scaled_float.
It can be helpful for you to provide a from_name function in your base type for looking up:

def from_name(name:str):
    return get_type(f'elasticsearch_{name}')
'''
type_registry = {}

def register_type(name):
    def decorator(cls):
        type_registry[name] = cls
        return cls
    return decorator

def get_type(name):
    if name in type_registry:
        return type_registry[name]
    else:
        raise hqle.CompilerException(f"Unknown type {name} referenced")

# Essentially a scoped context
class Context():
    """Carry data, symbols, registries, and configuration through execution."""

    def __init__(self, data:Data, hac:Optional[Hac]=None, symbol_table:Optional[dict]=None, macros:Optional[dict]=None, config:Optional[Config]=None, cache:Optional[Cache]=None) -> None:
        import copy

        # contexts are copied a lot so want to make sure things don't linger
        self.dbs = copy.deepcopy(database_registry)
        self.funcs = copy.deepcopy(func_registry)
        self.symbol_table = copy.deepcopy(symbol_table) if symbol_table else dict()
        self.macros = copy.deepcopy(macros) if macros else dict()
        self.config = copy.deepcopy(config) if config else Config()
        self.hac = copy.deepcopy(hac)
        self.data = data
        self.cache = Cache(parent=cache)

    def __bool__(self):
        return self.data.__bool__()

    '''
    Copy with pointer to data
    '''
    def copy(self):
        return Context(
            self.data,
            hac=self.hac,
            symbol_table=self.symbol_table,
            macros=self.macros,
            config=self.config
        )

    @staticmethod
    def merge(ctxs:list[Context], merge_rows=True):
        from Hql.Data import Data
        
        if len(ctxs) == 1:
            return ctxs[0]

        data = Data.merge([x.data for x in ctxs], merge_rows=merge_rows)

        syms = dict()
        macros = dict()
        for i in ctxs:
            for j in i.symbol_table:
                syms[j] = i.symbol_table[j]
            
            for j in i.macros:
                macros[j] = i.macros[j]

        return Context(data, symbol_table=syms, macros=macros, hac=ctxs[0].hac)

    def get_db(self, name:str):
        if name in self.dbs:
            return self.dbs[name]
        else:
            raise hqle.CompilerException(f"Unknown database {name} referenced")

    def get_db_types(self):
        return list(self.dbs.keys())

    def get_func(self, name:str):
        if name in self.funcs:
            logging.debug(f'Resolved func {name}')
            return self.funcs[name]
        else:
            raise hqle.CompilerException(f"Unknown function {name} referenced")
