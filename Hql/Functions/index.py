from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Expressions.References import Reference

# This is a meta function resolved while parsing
@register_func('index')
class index(Function):
    """Select an index on a database source."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        Function.__init__(self, args, 1, 1)
        self._index = StringLiteral('')
        self.index = args[0]

    @property
    def index(self) -> Union[StringLiteral, Reference]:
        return self._index

    @index.setter
    def index(self, val:Union[StringLiteral, Reference]):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference

        if not isinstance(val, (StringLiteral, Reference)):
            raise hqle.ArgumentException(f'Bad database index argument datatype {type(val)}')

        self._index = val
    
    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Expressions.Literals import StringLiteral
        
        index = self.index.preprocess(ctx)
        
        if not isinstance(index, StringLiteral):
            raise hqle.QueryException(f'File function give argument that doesn\'t resolve to string literal: {type(index)}')

        self.index = index

        return self
        
    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Database import Database
        from Hql.Expressions.Literals import StringLiteral

        if not isinstance(self.index, StringLiteral):
            raise hqle.QueryException(f'Index function given {type(self.index)} instead of StringLiteral')
                    
        index_name = self.index.str()
        
        if not receiver:
            db = self.default_db(ctx)
        else:
            db = receiver
        
        if issubclass(type(db), Database):
            db.add_index(index_name)
        else:
            raise hqle.CompilerException(f'Function {self.name} cannot be called on {type(db)}')
        
        return db
