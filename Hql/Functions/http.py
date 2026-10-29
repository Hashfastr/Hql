from __future__ import annotations
from . import Function

from Hql import Config
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from typing import Optional, Sequence, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from Hql.Context import Context

# This is a meta function resolved while parsing
@register_func('http')
class http(Function):
    """Select URLs from a database that supports HTTP access."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.References import Reference
        from Hql.Expressions.Literals import StringLiteral

        Function.__init__(self, args, 1, -1)

        self.names:Sequence[Union[Reference, StringLiteral]] = []
        
        for i in self.args:
            if not isinstance(i, (StringLiteral, Reference)):
                raise hqle.ArgumentException(f'Bad database file argument datatype {args[0].type}')
            self.names.append(i)

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral
        
        new = []
        for i in self.names:
            i = i.preprocess(ctx)
            if not isinstance(i, StringLiteral):
                raise hqle.QueryException(f'File function give argument that doesn\'t resolve to string literal: {type(i)}')
            new.append(i)

        self.names = new

        return self
        
    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Database import Database

        self.preprocess(ctx)

        db = receiver
        urls = [x.str() for x in self.names]
        
        if not db:
            db = self.default_db(ctx)
        
        if db and issubclass(type(db), Database) and db.has_method(self.name):
            db.urls += urls
        else:
            raise hqle.CompilerException(f'Function {self.name} cannot be called on {type(db)}')
        
        return db
