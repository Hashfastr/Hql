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
        pl = PolarsTypes.pl

        # bare classes (pl.Int64 vs pl.Int64()) carry no parameters
        if isinstance(pltype, type):
            if name in ('Struct', 'Object'):
                return resolved(schema={})
            if name in ('List', 'Array'):
                return resolved(inner=PolarsTypes.Null())
            if name == 'Enum':
                return resolved(values=[])
            return resolved()

        if isinstance(pltype, pl.Struct):
            schema = {
                field.name: PolarsTypes.from_pure_polars(field.dtype).hql_schema()
                for field in pltype.fields
            }
            return resolved(schema=schema)
        elif isinstance(pltype, pl.Enum):
            return resolved(values=pltype.categories.to_list())
        elif isinstance(pltype, pl.Datetime):
            return resolved(time_unit=pltype.time_unit, time_zone=pltype.time_zone)
        elif isinstance(pltype, pl.Duration):
            return resolved(time_unit=pltype.time_unit)
        elif isinstance(pltype, pl.Decimal):
            return resolved(precision=pltype.precision, scale=pltype.scale)
        elif isinstance(pltype, pl.Object):
            return resolved(schema={})
        elif hasattr(pltype, 'inner'):
            inner = PolarsTypes.from_pure_polars(pltype.inner)
            return resolved(inner=inner)
        else:
            return resolved()
            
    @register_type('polars_Decimal')
    class Decimal(PolarsType):
        """Map Polars decimals to HQL decimals."""

        def __init__(self, precision:Optional[int]=None, scale:int=0):
            PolarsTypes.PolarsType.__init__(self)
            # no precision means polars' maximum
            precision = 38 if precision is None else precision
            self.HqlType = PolarsTypes.hqlt.decimal(precision, scale)
            self.pltype = PolarsTypes.pl.Decimal(precision, scale)

    @register_type('polars_Float16')
    class Float16(PolarsType):
        """Map 16-bit Polars floats to HQL floats."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.float()
            self.pltype = PolarsTypes.pl.Float32()

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
            self.pltype = PolarsTypes.pl.Int128()
    
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
    
    @register_type('polars_UInt128') 
    class UInt128(PolarsType):
        """Map unsigned 128-bit Polars integers to HQL unsigned extended longs."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.uxlong()
            self.pltype = PolarsTypes.pl.UInt128()
    
    @register_type('polars_Date') 
    class Date(PolarsType):
        """Map Polars dates to HQL dates."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.date()
            self.pltype = PolarsTypes.pl.Date()

    @register_type('polars_Datetime')
    class Datetime(PolarsType):
        """Map Polars datetimes to HQL datetimes."""

        def __init__(self, time_unit:str='us', time_zone:Optional[str]=None):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.datetime(time_unit, time_zone)
            self.pltype = PolarsTypes.pl.Datetime(time_unit, time_zone)
    
    @register_type('polars_Duration') 
    class Duration(PolarsType):
        """Map Polars durations to HQL durations."""

        def __init__(self, time_unit:str='us'):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.duration(time_unit)
            self.pltype = PolarsTypes.pl.Duration(time_unit)
    
    @register_type('polars_Time') 
    class Time(PolarsType):
        """Map Polars times to HQL times."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.time()
            self.pltype = PolarsTypes.pl.Time()
    
    @register_type('polars_Array') 
    class Array(PolarsType):
        """Map fixed-size Polars arrays to HQL multivalues until matrix is implemented."""

        def __init__(self, inner:PolarsTypes.PolarsType):
            PolarsTypes.PolarsType.__init__(self, inner=inner)
            self.HqlType = PolarsTypes.hqlt.multivalue(inner.hql_schema())
            self.pltype = PolarsTypes.pl.List(inner.pl_schema())
    
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
        """Map a Polars enumeration to HQL strings until enum is implemented."""

        def __init__(self, values:list[str]):
            PolarsTypes.PolarsType.__init__(self)
            self.values = values
            self.HqlType = PolarsTypes.hqlt.string()
            self.pltype = PolarsTypes.pl.String()

    @register_type('polars_Categorical')
    class Categorical(PolarsType):
        """Map Polars categoricals to HQL strings."""

        def __init__(self):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.string()
            self.pltype = PolarsTypes.pl.String()
    
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
        """Map arbitrary Python objects to HQL dynamic values."""

        def __init__(self, schema:Optional[dict]=None):
            PolarsTypes.PolarsType.__init__(self)
            self.HqlType = PolarsTypes.hqlt.dynamic()
            self.pltype = PolarsTypes.pl.Object()

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
