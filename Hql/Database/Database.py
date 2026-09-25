from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union
from Hql.Operators.Operator import Operator
from Hql.Exceptions import HqlExceptions as hqle
import datetime
import logging
from Hql.Cache import Cache

if TYPE_CHECKING:
    from Hql.Data import Data
    from Hql.Context import Context
    from Hql.Compiler import BranchDescriptor
    from Hql.Expressions.References import NamedReference
    from Hql.Expressions import PipeExpression

class Database(Operator):
    def __init__(self, config:dict, name:str='unnamed-database'):
        from Hql.Compiler import Compiler
        from Hql.Context import Context
        from Hql.Data import Data
        Operator.__init__(self)

        self.type = self.__class__.__name__
        
        self.cache = Cache()
        self.ctx = Context(Data())
        self.config = config
        self.compiler = Compiler()
        self.name = name
        self.index = ''
        self._preamble:Optional[PipeExpression] = None
        self.methods = []

    def __eq__(self, value: object, /) -> bool:
        if isinstance(value, Database):
            if self.name == value.name and self.config == value.config:
                return True
            else:
                return False
        return super().__eq__(value)

    def __bool__(self) -> bool:
        return True

    @property
    def preamble(self) -> PipeExpression:
        from Hql.Expressions import PipeExpression

        if self._preamble is None:
            return PipeExpression([])
        else:
            return self._preamble

    @preamble.setter
    def preamble(self, val:PipeExpression):
        from Hql.Expressions import PipeExpression
        assert isinstance(val, PipeExpression)
        self._preamble = val

    def add_op(self, op:Union[Operator, BranchDescriptor]) -> tuple[Union[Operator, None], Union[Operator, None]]:
        return self.compiler.add_op(op)

    def add_timebound(self, start:datetime.datetime, end:datetime.datetime) -> tuple[Database, Union[None, Operator]]:
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import BetweenEquality
        from Hql.Expressions.Literals import Datetime
        from Hql.Expressions.References import NamedReference

        if not self.config.get('timeseries', True):
            # Fake consume it if we don't use it
            logging.debug(f'Skipping timeseries for {self.type}')
            return self, None

        _, rej = self.add_op(
            Where(
                BetweenEquality(
                    NamedReference('_hqltimestamp'),
                    Datetime(start),
                    Datetime(end),
                    False
                )
            )
        )

        return self, rej

    def add_index(self, index:str):
        self.index = index

    def set_raw_query(self, query:str) -> None:
        raise hqle.QueryException(
            f'{self.type} database does not support raw queries'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
        }

    def eval(self, ctx:Context) -> Context:
        return NotImplemented
    
    def get_variable(self, name:NamedReference) -> object:
        raise hqle.QueryException(f'{self.type} database has no variables')

    def get_macro(self, name:str) -> Union[None, dict]:
        macros = self.config.get('macro', dict())
        return macros.get(name, None)
