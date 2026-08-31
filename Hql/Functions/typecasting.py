from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func, Context
from Hql.Data import Data, Table, Series, Schema
from Hql.Types.Hql import HqlTypes as hqlt
import polars as pl
from Hql.Expressions import Literals
from typing import Optional
import logging

class Typecast(Function):
    """Base function for casting literals and fields to an HQL type."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 1, 1)
        self.src = args[0]
        
        if self.src.literal:
            self.src = pl.Series([self.src.value])
        
        # default cast type
        self.cast_type = hqlt.string()
        self.expr = Literals.StringLiteral
        
    def eval(self, ctx:Context, receiver=None):
        # represents a single value literal 
        if isinstance(self.src, pl.Series):
            new = self.cast_type.cast(self.src)
            return self.expr(new[0])

        data = ctx.data.select(self.src).strip()
        logging.debug(type(data))
        logging.debug(data)

        tables = []
        for table in data:
            if table.series is None:
                continue

            series = table.series.cast(self.cast_type).series

            new = Table(name=table.name)
            new.insert(self.src, series, self.cast_type)
            tables.append(new)

        ctx.data = Data(tables=tables)
        return ctx
    
@register_func('toint')
class toint(Typecast):
    """Cast a value to an HQL integer."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.int()
        self.expr = Literals.Integer

@register_func('tofloat')
class tofloat(Typecast):
    """Cast a value to an HQL float."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.float()
        self.expr = Literals.Float
        
@register_func('todouble')
class todouble(Typecast):
    """Cast a value to an HQL double."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.double()
        self.expr = Literals.Float
        
@register_func('tostring')
class tostring(Typecast):
    """Cast a value to an HQL string."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.string()
        self.expr = Literals.StringLiteral

@register_func('toip4')
class toip4(Typecast):
    """Cast a value to an HQL IPv4 address."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.ip4()
        self.expr = Literals.IP4

@register_func('todatetime')
class todatetime(Typecast):
    """Cast a value to an HQL datetime."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Typecast.__init__(self, args)
        self.cast_type = hqlt.datetime()
        self.expr = Literals.Datetime
