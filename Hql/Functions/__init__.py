from __future__ import annotations
import importlib, pkgutil

import json
import logging
from typing import TYPE_CHECKING, Optional, Sequence, Union

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions import Expression
    from Hql.Expressions.Literals import Literal
    from Hql.Data import Data, Series
    from Hql.Database import Database
    from polars import Expr as plExpr

class Function():
    """Base class for callable HQL functions."""

    def __init__(self, args:Sequence[Expression], min:int, max:int, conf:Optional[dict]=None):
        self.name = self.__class__.__name__
        self.type = 'Function'
        self.args:Sequence[Expression] = args
        self.min = min
        # Can disable by passing -1
        self.can_preprocess = False
        self.max = max
        # self.static = False
        self.conf = conf if conf else dict()
        self.logic = False
        
        if len(args) < min:
            raise hqle.ArgumentException(f'Function {self.name} got {len(args)} args, expected at least {self.min}')
        if max != -1 and len(args) > max:
            raise hqle.ArgumentException(f'Function {self.name} got {len(args)} args, expected at most {self.max}')
    
    def __hash__(self):
        return hash((self.name))

    def deparse(self):
        args = ', '.join([x.deparse() for x in self.args])
        return f'{self.name}({args})'
        
    def to_dict(self):
        return {
            'type': 'function',
            'name': self.name,
            'args': [x.to_dict() for x in self.args]
        }
    
    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    def __repr__(self) -> str:
        return self.__str__()

    def str(self) -> str:
        return self.__str__()

    def preprocess(self, ctx:Context, receiver=None) -> object:
        args = []
        for i in self.args:
            args.append(i.preprocess(ctx))
        self.args = args

        return self
        
    def eval(self, ctx:Context, receiver=None) -> object:
        return NotImplemented

    def broadcast(self, ctx:Context, value:Union[Literal, Series]) -> Data:
        '''
        Gives each table in the context a copy of a static value.
        Lets functions that resolve to a single value be used in an extend.
        '''
        from Hql.Data import Data, Table
        from Hql.Expressions.Literals import Literal

        series = value.series() if isinstance(value, Literal) else value

        data = Data()
        for table in ctx.data:
            data.add_table(Table(name=table.name, series=series))
        return data

    def default_db(self, ctx:Context) -> Database:
        '''
        The configured default database, used when a database function
        such as file() or index() is called without a receiver.
        '''
        dbconf = ctx.config.get_default_db()
        return ctx.get_db(dbconf['type'])(dbconf, name=dbconf.get('name', 'default'))

    def polars(self) -> plExpr:
        return NotImplemented

class DotCompositeFunction():
    """Apply a sequence of functions as a receiver-based call chain."""

    def __init__(self, funcs:Sequence[Union[Function, DotCompositeFunction]]):
        self.type = self.__class__.__name__
        self.funcs:list[Function] = []
        for i in funcs:
            if isinstance(i, DotCompositeFunction):
                self.funcs += i.funcs
            else:
                self.funcs.append(i)

    def __new__(cls, funcs:Sequence[Union[Function, DotCompositeFunction]]):
        if len(funcs) == 1:
            return funcs[0]
        return super().__new__(cls)

    def __reduce__(self):
        return (self.__class__, (self.funcs,))

    def __bool__(self):
        return bool(self.funcs)
    
    def to_dict(self):
        return {
            'type': self.type,
            'funcs': [x.to_dict() for x in self.funcs]
        }

    def deparse(self) -> str:
        funcs = []
        for i in self.funcs:
            funcs.append(i.deparse())
        return '.'.join(funcs)

    def preprocess(self, ctx:Context) -> object:
        from Hql.Expressions.Functions import FuncExpr
        ctx = ctx.copy()
            
        rec = None
        for i in self.funcs:
            if isinstance(i, FuncExpr):
                i = i.preprocess(ctx)
                assert isinstance(i, Function)

            try:
                rec = i.preprocess(ctx, receiver=rec)
            except hqle.FunctionException as e:
                # catching for handling for if a function can't preprocess within the chain
                e.add_note(f'Occured in {self.deparse()}')
                raise

        return rec

    def eval(self, ctx:Context) -> object:
        ctx = ctx.copy()

        rec = None
        for func in self.funcs:
            rec = func.eval(ctx, receiver=rec)

            if rec == NotImplemented:
                logging.error(type(func))
                logging.error(func.to_dict())
                raise hqle.CompilerException(f'Function {func.name} provided "NotImplemented" when eval\'d')
        
        return rec

for loader, name, is_pkg in pkgutil.iter_modules(__path__):
    skip = ['template', 'typecasting']
    for i in skip:
        if i in name:
            continue
    importlib.import_module(f"{__name__}.{name}")
