from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_type, get_type
from Hql.Types.Compiler import CompilerType


class PolarsTypes():
    """Namespace for Polars-to-HQL type adapters."""

    from Hql.Types.Hql import HqlTypes as hqlt
    import polars as pl
    
    class PolarsType(CompilerType):
        """Base adapter for a Polars data type."""

        def __init__(self, inner:Optional[PolarsTypes.PolarsType]=None):
            CompilerType.__init__(self, inner=inner)
            self.inner:Optional[PolarsTypes.PolarsType] = inner
            self.pltype:Optional[PolarsTypes.pl.DataType] = None

        def pl_schema(self) -> PolarsTypes.pl.DataType:
            if isinstance(self.pltype, type(None)):
                raise hqle.CompilerException(f'Polars type {self.name} has no defined pl_schema')
            return self.pltype
        
    @staticmethod
    def from_name(name:str):
        return get_type(f'polars_{name}')
    
    @staticmethod
    def from_pure_polars(pltype) -> PolarsType:
        if hasattr(pltype, '__name__'):
            name = pltype.__name__
        else:
            name = type(pltype).__name__

        resolved = PolarsTypes.from_name(name)

        if isinstance(pltype, PolarsTypes.pl.Struct):
            schema = {
                field.name: PolarsTypes.from_pure_polars(field.dtype).hql_schema()
                for field in pltype.fields
            }
            return resolved(schema=schema)
        elif hasattr(pltype, 'inner'):
            inner = PolarsTypes.from_pure_polars(pltype.inner)
            return resolved(inner=inner)
        else:
            return resolved()
            
    @register_type('polars_Decimal')
    class Decimal(PolarsType):
        """Map Polars decimals to HQL decimals."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.decimal()
            self.pltype = PolarsTypes.pl.Decimal()

    @register_type('polars_Float32')
    class Float32(PolarsType):
        """Map 32-bit Polars floats to HQL floats."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.float()
            self.pltype = PolarsTypes.pl.Float32()
    
    @register_type('polars_Float64') 
    class Float64(PolarsType):
        """Map 64-bit Polars floats to HQL doubles."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.double()
            self.pltype = PolarsTypes.pl.Float64()
        
    @register_type('polars_Int8')
    class Int8(PolarsType):
        """Map 8-bit Polars integers to HQL bytes."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.byte()
            self.pltype = PolarsTypes.pl.Int8()
    
    @register_type('polars_Int16') 
    class Int16(PolarsType):
        """Map 16-bit Polars integers to HQL shorts."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.short()
            self.pltype = PolarsTypes.pl.Int16()
    
    @register_type('polars_Int32') 
    class Int32(PolarsType):
        """Map 32-bit Polars integers to HQL integers."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.int()
            self.pltype = PolarsTypes.pl.Int32()
    
    @register_type('polars_Int64') 
    class Int64(PolarsType):
        """Map 64-bit Polars integers to HQL longs."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.long()
            self.pltype = PolarsTypes.pl.Int64()
    
    @register_type('polars_Int128') 
    class Int128(PolarsType):
        """Map 128-bit Polars integers to HQL extended longs."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.xlong()
            self.pltype = PolarsTypes.pl.UInt128()
    
    @register_type('polars_UInt8') 
    class UInt8(PolarsType):
        """Map unsigned 8-bit Polars integers to HQL unsigned bytes."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.ubyte()
            self.pltype = PolarsTypes.pl.UInt8()
    
    @register_type('polars_UInt16') 
    class UInt16(PolarsType):
        """Map unsigned 16-bit Polars integers to HQL unsigned shorts."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.ushort()
            self.pltype = PolarsTypes.pl.UInt16()
        
    @register_type('polars_UInt32')
    class UInt32(PolarsType):
        """Map unsigned 32-bit Polars integers to HQL unsigned integers."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.uint()
            self.pltype = PolarsTypes.pl.UInt32()
    
    @register_type('polars_UInt64') 
    class UInt64(PolarsType):
        """Map unsigned 64-bit Polars integers to HQL unsigned longs."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.ulong()
            self.pltype = PolarsTypes.pl.UInt64()
    
    @register_type('polars_Date') 
    class Date(PolarsType):
        """Map Polars dates to HQL datetimes."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.datetime()
            self.pltype = PolarsTypes.pl.Date()

    @register_type('polars_Datetime')
    class Datetime(PolarsType):
        """Map Polars datetimes to HQL datetimes."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.datetime()
            self.pltype = PolarsTypes.pl.Datetime()
    
    @register_type('polars_Duration') 
    class Duration(PolarsType):
        """Map Polars durations to HQL durations."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.duration()
            self.pltype = PolarsTypes.pl.Duration()
    
    @register_type('polars_Time') 
    class Time(PolarsType):
        """Map Polars times to HQL times."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.time()
            self.pltype = PolarsTypes.pl.Time()
    
    @register_type('polars_Array') 
    class Array(PolarsType):
        """Map fixed-size Polars arrays to HQL matrices."""

        def __init__(self, inner:PolarsTypes.PolarsType):
            PolarsTypes.PolarsType.__init__(self, inner=inner)
            self.HqlType = PolarsTypes.hqlt.matrix(inner.hql_schema())
            self.pltype = PolarsTypes.pl.Array(inner.pl_schema())
    
    @register_type('polars_List') 
    class List(PolarsType):
        """Map Polars lists to HQL multivalue types."""

        def __init__(self, inner:PolarsTypes.PolarsType):
            PolarsTypes.PolarsType.__init__(self, inner=inner)
            self.HqlType = PolarsTypes.hqlt.multivalue(inner.hql_schema())
            self.pltype = PolarsTypes.pl.List(inner.pl_schema())
    
    @register_type('polars_String') 
    class String(PolarsType):
        """Map Polars strings to HQL strings."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.string()
            self.pltype = PolarsTypes.pl.String()
        
    @register_type('polars_Enum')
    class Enum(PolarsType):
        """Map a Polars enumeration and its values to HQL."""

        def __init__(self, values:list[str]):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.enum(values)
            self.pltype = PolarsTypes.pl.Enum(values)
    
    @register_type('polars_Utf8') 
    class Utf8(PolarsType):
        """Map legacy Polars UTF-8 values to HQL strings."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.string()
            self.pltype = PolarsTypes.pl.Utf8()
        
    @register_type('polars_Binary')
    class Binary(PolarsType):
        """Map Polars binary values to HQL binary values."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.binary()
            self.pltype = PolarsTypes.pl.Binary()
        
    @register_type('polars_Boolean')
    class Boolean(PolarsType):
        """Map Polars Boolean values to HQL Booleans."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.bool()
            self.pltype = PolarsTypes.pl.Boolean()
        
    @register_type('polars_Null') 
    class Null(PolarsType):
        """Map Polars null values to HQL null values."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.null()
            self.pltype = PolarsTypes.pl.Null()
        
    @register_type('polars_Object')   
    class Object(PolarsType):
        """Map a Polars object schema to an HQL object."""

        def __init__(self, schema:dict):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.object(schema)
            self.pltype = self.HqlType.pl_schema()

        def pl_schema(self) -> PolarsTypes.pl.DataType:
            assert self.HqlType
            self.pltype = self.HqlType.pl_schema()
            return self.pltype

    @register_type('polars_Struct')   
    class Struct(PolarsType):
        """Map a Polars struct schema to an HQL object."""

        def __init__(self, schema:dict):
            PolarsTypes.PolarsType.__init__(self)
            self.schema = schema
            self.HqlType = PolarsTypes.hqlt.object(schema)
            self.pltype = self.HqlType.pl_schema()
        
    @register_type('polars_Unknown')
    class Unknown(PolarsType):
        """Map an unknown Polars type to the HQL unknown type."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.unknown()
            self.pltype = PolarsTypes.pl.Unknown()
