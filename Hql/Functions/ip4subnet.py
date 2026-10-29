from __future__ import annotations

from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func
from Hql.Expressions.Logic import BasicRange
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Context import Context

@register_func('ip4subnet')
class ip4subnet(Function):
    """Convert an IPv4 CIDR subnet into its numeric address range."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        Function.__init__(self, args, 1, 1)
        self.subnet:StringLiteral = args[0]

    def eval(self, ctx: Context, receiver=None) -> BasicRange:
        from Hql.Expressions.Literals import Integer, StringLiteral
        import re
        
        # resolve let variables
        subnet = self.subnet.preprocess(ctx)
        if not isinstance(subnet, StringLiteral):
            raise hqle.QueryException(f'ip4subnet given non-string subnet {self.subnet.deparse()}')

        subnet_regex = r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})'

        subnet_text = subnet.str()
        match = re.fullmatch(subnet_regex, subnet_text)
        if match == None:
            raise hqle.QueryException(f'Invalid subnet given {subnet_text}')

        octets = [int(x) for x in match.groups()[:4]]
        prefix = int(match.group(5))

        if any(x > 255 for x in octets) or prefix > 32:
            raise hqle.QueryException(f'Invalid subnet given {subnet_text}')
        
        mask = 0xFFFFFFFF - ((1 << (32 - prefix)) - 1)
        ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]

        ip_start = ip_int &  mask
        ip_end   = ip_int | (mask ^ 0xFFFFFFFF)

        ip_start = Integer(ip_start)
        ip_end = Integer(ip_end)
        
        return BasicRange(ip_start, ip_end)
