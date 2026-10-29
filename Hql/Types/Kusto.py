from __future__ import annotations

from Hql.Context import get_type, register_type
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Compiler import CompilerType


class KustoTypes:
    """Namespace for Kusto-to-HQL type adapters."""

    from Hql.Types.Hql import HqlTypes as hqlt

    class KustoType(CompilerType):
        """Base adapter for a Kusto scalar type."""

        def __init__(self, hql_type:KustoTypes.hqlt.HqlType):
            CompilerType.__init__(self)
            self.HqlType = hql_type

    @staticmethod
    def from_name(name:str) -> type[KustoType]:
        return get_type(f'kusto_{name}')

    @staticmethod
    def from_hql(hql_type:KustoTypes.hqlt.HqlType) -> KustoType:
        if not isinstance(hql_type, KustoTypes.hqlt.HqlType):
            raise hqle.CompilerException(
                f'Cannot convert {type(hql_type)} to a Kusto type'
            )

        try:
            return KustoTypes.from_name(hql_type.name)()
        except hqle.CompilerException:
            return KustoTypes.string()

    @register_type('kusto_bool')
    class bool(KustoType):
        """Map HQL Boolean values to Kusto bool values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.bool())

    @register_type('kusto_byte')
    @register_type('kusto_short')
    @register_type('kusto_int')
    @register_type('kusto_ubyte')
    @register_type('kusto_ushort')
    class int(KustoType):
        """Map HQL integer values up to 32 bits to Kusto int values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.int())

    # uint and ip4 (stored as uint) exceed int's signed 32-bit range
    @register_type('kusto_long')
    @register_type('kusto_uint')
    @register_type('kusto_ip4')
    class long(KustoType):
        """Map HQL 64-bit integer values to Kusto long values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.long())

    @register_type('kusto_float')
    @register_type('kusto_double')
    @register_type('kusto_real')
    class real(KustoType):
        """Map HQL floating-point values to Kusto real values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.double())

    # Kusto has no unsigned long, decimal is the only type that holds all of ulong
    @register_type('kusto_decimal')
    @register_type('kusto_ulong')
    class decimal(KustoType):
        """Map HQL decimal values to Kusto decimal values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.decimal())

    @register_type('kusto_date')
    @register_type('kusto_datetime')
    class datetime(KustoType):
        """Map HQL date and datetime values to Kusto datetime values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.datetime())

    @register_type('kusto_duration')
    @register_type('kusto_time')
    @register_type('kusto_timespan')
    class timespan(KustoType):
        """Map HQL duration values to Kusto timespan values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.duration())

    @register_type('kusto_object')
    @register_type('kusto_multivalue')
    @register_type('kusto_dynamic')
    class dynamic(KustoType):
        """Map structured HQL values to Kusto dynamic values."""

        # dynamic columns have no fixed shape, an empty object would drop every value
        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.dynamic())

    @register_type('kusto_guid')
    class guid(KustoType):
        """Map HQL globally unique identifiers to Kusto guid values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.guid())

    @register_type('kusto_string')
    @register_type('kusto_ip')
    @register_type('kusto_binary')
    @register_type('kusto_xlong')
    @register_type('kusto_uxlong')
    @register_type('kusto_ip6')
    @register_type('kusto_null')
    class string(KustoType):
        """Map string-compatible HQL values to Kusto string values."""

        def __init__(self):
            KustoTypes.KustoType.__init__(self, KustoTypes.hqlt.string())
