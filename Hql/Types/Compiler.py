from __future__ import annotations
from typing import Union, Optional, TYPE_CHECKING
import polars as pl
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Types.Hql import HqlTypes as hqlt

class CompilerType():
    """Base adapter between an external type and an HQL type."""

    def __init__(self, inner:Optional[CompilerType]=None):
        bases = type(self).__bases__

        self._inner = None
        self._HqlType = None

        self.type = bases[0]
        self.HqlType = None
        self.inner = inner
        self.name = self.__class__.__name__

    def __eq__(self, value: object, /) -> bool:
        if type(value) != type(self):
            return False
        # parameterized types (multivalue(int), decimal(10, 2), ...) differ by their parameters
        assert isinstance(value, CompilerType)
        return self.inner == value.inner and self.params() == value.params()

    def __len__(self) -> int:
        return 1

    def __hash__(self):
        return hash((self.name, self.type.__name__, self.inner, self.params()))

    # Type parameters other than inner that distinguish two instances of a type
    def params(self) -> tuple:
        return ()

    @property
    def inner(self) -> Optional[CompilerType]:
        return self._inner

    @inner.setter
    def inner(self, val:Optional[CompilerType]):
        if val is not None and not isinstance(val, CompilerType):
            raise hqle.CompilerException(f'CompilerType given non-CompilerType inner: {val}')
        self._inner = val

    @property
    def HqlType(self) -> Optional[hqlt.HqlType]:
        return self._HqlType

    @HqlType.setter
    def HqlType(self, val:Optional[hqlt.HqlType]):
        from Hql.Types.Hql import HqlTypes as hqlt

        if val is not None and not isinstance(val, hqlt.HqlType):
            raise hqle.CompilerException(f'CompilerType given non-CompilerType inner: {val}')
        self._HqlType = val

    def hql_schema(self) -> hqlt.HqlType:
        if self.HqlType == None:
            raise hqle.CompilerException(f"{self.type}.{self.name} defined without an Hql proto")

        if self.inner:
            self.HqlType.inner = self.inner.hql_schema()

        return self.HqlType

    def pl_schema(self):
        return self.hql_schema().pl_schema()

    def cast(self, series:pl.Series):
        if self.HqlType == None:
            raise hqle.CompilerException('Attempting to cast data to type without a prototype')

        return series.cast(self.pl_schema())

    def to_dict(self):
        return {
            'type': self.type.__name__,
            'name': self.name
        }

    def deparse(self):
        return self.name

    def str(self):
        return self.name
