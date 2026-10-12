from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union
import logging

from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle

from . import Function

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Expressions.References import Reference


@register_func('raw')
class raw(Function):
    """Configure a database source with a native query string."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference

        Function.__init__(self, args, 1, 1)
        query = args[0]
        if not isinstance(query, (StringLiteral, Reference)):
            raise hqle.ArgumentException(
                f'Bad raw query argument datatype {type(query)}'
            )
        self.query:Union[StringLiteral, Reference] = query

    def preprocess(self, ctx:Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral

        query = self.query.preprocess(ctx)
        if not isinstance(query, StringLiteral):
            raise hqle.QueryException(f'Raw function argument did not resolve to a string literal: {type(query)}')
        self.query = query
        return self

    def eval(self, ctx:Context, receiver=None) -> object:
        from Hql.Database import Database

        self.preprocess(ctx, receiver=receiver)

        db = receiver
        if db is None:
            dbconf = ctx.config.get_default_db()
            db = ctx.get_db(dbconf['type'])(
                dbconf,
                name=dbconf.get('name', 'default'),
            )

        if not isinstance(db, Database):
            raise hqle.CompilerException(
                f'Function {self.name} cannot be called on {type(db)}'
            )

        db.set_raw_query(self.query.str())
        return db
