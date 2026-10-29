from __future__ import annotations
from . import Function
from Hql.Context import register_func

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Context import Context

@register_func('tolower')
class tolower(Function):
    """Convert string literals or field values to lowercase."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 1, 1, conf)
        self.src = args[0]

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral

        src = self.src.preprocess(ctx)
        if isinstance(src, StringLiteral):
            return StringLiteral(src.value.decode('utf-8').lower())
        return self
        
    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Data import Data, Table
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Types.Hql import HqlTypes as hqlt

        if isinstance(self.src, StringLiteral):
            return self.broadcast(ctx, self.preprocess(ctx))

        data = self.src.eval(ctx).data.strip()
        
        tables = []
        for table in data:
            if not table.series:
                continue

            series = table.series.series.str.to_lowercase()

            new = Table(name=table.name)
            new.insert(self.src, series, hqlt.string())
            tables.append(new)

        return Data(tables=tables)
