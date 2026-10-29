from __future__ import annotations
from . import Function
from Hql.Context import register_func
from Hql.Data import Data, Table, Series
from Hql.Types.Hql import HqlTypes as hqlt
from typing import TYPE_CHECKING, Optional

import logging

if TYPE_CHECKING:
    from Hql.Context import Context

@register_func('len')
@register_func('array_length')
class hql_len(Function):
    """Calculate the length of each value in a multivalue field."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        super().__init__(args, 1, 1)
        self.args = args
        self.count_type = hqlt.ulong()
        
    def eval(self, ctx: Context, receiver=None) -> object:
        path = self.args[0]
        filter = path.polars_value()
        
        new = []
        for table in ctx.data:            
            if not table.assert_field(path):
                new.append(Table(name=table.name))
                continue
            
            if not isinstance(table.schema.get_type(path).strip(), hqlt.multivalue):
                logging.warning(f"Skipping over evaluating length of {path.deparse()} in {table.name}")
                new.append(Table(name=table.name))
                continue
            
            count = table.df.select(filter.list.len()).to_series()
            count = self.count_type.cast(count)
            
            new.append(Table(series=Series(count, self.count_type), name=table.name))
            
        return Data(tables=new)
