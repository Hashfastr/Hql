from __future__ import annotations

from .Logic import LogicFunction
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

'''
Whether a string IP address is in a CIDR range, as in Kusto. Sigma's |cidr compiles to these.

| where ipv4_is_in_range(IPAddress, '10.0.0.0/8')
| where ipv6_is_in_range(IPAddress, 'fe80::/10')
'''
class ip_is_in_range(LogicFunction):
    """Test whether a string IP address falls in a CIDR range."""

    version = 4

    def __init__(self, args:list, conf:Optional[dict]=None):
        import ipaddress
        from Hql.Expressions.Literals import StringLiteral

        LogicFunction.__init__(self, args, 2, 2, conf=conf)

        if not isinstance(args[1], StringLiteral):
            raise hqle.ArgumentException(f'{self.name} takes a CIDR string, got {type(args[1]).__name__}')

        self.cidr = args[1].str()
        try:
            self.network = ipaddress.ip_network(self.cidr, strict=False)
        except ValueError as exc:
            raise hqle.ArgumentException(f'{self.name} given invalid CIDR {self.cidr!r}') from exc

        if self.network.version != self.version:
            raise hqle.ArgumentException(f'{self.name} given IPv{self.network.version} CIDR {self.cidr!r}')

    def in_range(self, series:pl.Series) -> pl.Series:
        import ipaddress
        import polars as pl

        def check(value) -> bool:
            if value is None:
                return False
            try:
                return ipaddress.ip_address(str(value).strip()) in self.network
            except ValueError:
                return False

        return pl.Series([check(x) for x in series], dtype=pl.Boolean)

    def polars(self) -> pl.Expr:
        import polars as pl
        return self.args[0].polars().map_batches(self.in_range, return_dtype=pl.Boolean)

    def deparse(self) -> str:
        return f"{self.name}({self.args[0].deparse()}, {self.args[1].deparse()})"

@register_func('ipv4_is_in_range')
class ipv4_is_in_range(ip_is_in_range):
    version = 4

@register_func('ipv6_is_in_range')
class ipv6_is_in_range(ip_is_in_range):
    version = 6
