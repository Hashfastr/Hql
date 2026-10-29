from __future__ import annotations

import polars as pl
import logging
import json
import uuid
import ipaddress
from typing import TYPE_CHECKING, Iterator, Union, Optional, Mapping

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_type, get_type
from Hql.Types.Compiler import CompilerType

if TYPE_CHECKING:
    from Hql.Expressions.Literals import Integer, StringLiteral
    from Hql.Expressions.References import Reference

SchemaDT = Mapping[str, Union['HqlTypes.HqlType', dict]]

class HqlTypes():
    """Namespace for HQL's canonical type system."""

    class HqlType(CompilerType):
        """Base class for canonical HQL data types."""

        # Registered names of the types this type can be widened to, nearest first.
        # Every list must follow the same overall ordering so resolve_conflict is order independent.
        promotes_to:tuple[str, ...] = ()

        def __init__(self, inner:Optional[HqlTypes.HqlType]=None):
            CompilerType.__init__(self)

            self._proto = None
            self._super:Optional[list[HqlTypes.HqlType]] = None
            self._inner = None

            self.complex:bool = False
            self.priority:int = 0
            self.proto = None
            self.inner = inner

        def __len__(self) -> int:
            return 1

        @property
        def proto(self) -> Optional[pl.DataType]:
            return self._proto

        @proto.setter
        def proto(self, val:Optional[pl.DataType]):
            if val is not None and not isinstance(val, pl.DataType):
                raise hqle.CompilerException(f'HqlType given non-pl.DataType proto: {val}')
            self._proto = val

        @property
        def super(self) -> list[HqlTypes.HqlType]:
            # built on demand, constructing every promotion target on init is wasteful
            if self._super is None:
                return [HqlTypes.from_name(x) for x in self.promotes_to]
            return self._super

        @super.setter
        def super(self, val:list[HqlTypes.HqlType]):
            if not isinstance(val, list):
                raise hqle.CompilerException(f'HqlType given non-list[HqlType] super: {val}')

            for i in val:
                if not isinstance(i, HqlTypes.HqlType):
                    raise hqle.CompilerException(f'HqlType given non-HqlType super: {i}')

            self._super = val

        @property
        def inner(self) -> Optional[HqlTypes.HqlType]:
            return self._inner

        @inner.setter
        def inner(self, val:Optional[CompilerType]):
            if val is not None and not isinstance(val, HqlTypes.HqlType):
                raise hqle.CompilerException(f'HqlTypes.HqlType given non-HqlTypes.HqlType inner: {val}')
            self._inner = val

        def pl_schema(self) -> pl.DataType:
            if self.proto == None:
                raise hqle.CompilerException(f'{self.name}')
            else:
                return self.proto

        def cast(self, series:pl.Series):
            if self.proto == None:
                logging.error(f'No prototype for HqlType {self.name}')
                raise hqle.CompilerException('Attempting to cast data to type without a prototype')

            return series.cast(self.pl_schema())

        def hql_schema(self):
            return self

        # Combines two differently parameterized instances of the same type,
        # e.g. decimal(10, 2) and decimal(20, 4). None if they can't be combined.
        def widen(self, other:HqlTypes.HqlType) -> Optional[HqlTypes.HqlType]:
            return None
    
    @staticmethod
    def from_name(name:str) -> HqlTypes.HqlType:
        return get_type(f'hql_{name}')()

    @staticmethod
    def finer_unit(l:str, r:str) -> str:
        units = ['ms', 'us', 'ns']
        return units[max(units.index(l), units.index(r))]

    @staticmethod
    def dedupe(types:list) -> list:
        # order preserving, set() iteration order depends on the hash seed
        out = []
        for i in types:
            if i not in out:
                out.append(i)
        return out
    
    @staticmethod
    def resolve_conflict(types:list[HqlType]) -> HqlType:
        if len(types) == 0:
            raise hqle.CompilerException('Passed empty types list to resolve conflict')

        types = HqlTypes.dedupe(types)
        if len(types) == 1:
            return types[0]

        # null merges into anything
        types = [x for x in types if not isinstance(x, HqlTypes.null)]
        if len(types) == 0:
            return HqlTypes.null()
        if len(types) == 1:
            return types[0]

        ### objs

        if all(isinstance(x, HqlTypes.object) for x in types):
            keyset:dict[str, list] = dict()
            for i in types:
                # ew, linter
                assert isinstance(i, HqlTypes.object)
                for j in i.schema:
                    cur = i.schema[j]
                    if isinstance(cur, dict):
                        cur = HqlTypes.object(cur)
                    keyset.setdefault(j, []).append(cur)

            # keys missing from some objects are null there, so just resolve the present ones
            out:dict[str, HqlTypes.HqlType] = dict()
            for i in keyset:
                out[i] = HqlTypes.resolve_conflict(keyset[i])

            return HqlTypes.object(out)

        ### multivalue

        # A scalar mixed with multivalues becomes a single element multivalue
        if any(isinstance(x, HqlTypes.multivalue) for x in types):
            inners = []
            for i in types:
                if isinstance(i, HqlTypes.multivalue):
                    inners.append(i.inner)
                else:
                    inners.append(i)

            inner = HqlTypes.resolve_conflict(inners)
            # polars can't hold a list of arbitrary objects
            if isinstance(inner, HqlTypes.dynamic):
                return inner
            return HqlTypes.multivalue(inner)

        ### base types

        def promote(l:HqlTypes.HqlType, r:HqlTypes.HqlType) -> HqlTypes.HqlType:
            if l == r:
                return l

            if isinstance(l, HqlTypes.dynamic) or isinstance(r, HqlTypes.dynamic):
                return HqlTypes.dynamic()

            if type(l) == type(r):
                widened = l.widen(r)
                if widened is not None:
                    return widened

            if r.name in l.promotes_to:
                return r

            if l.name in r.promotes_to:
                return l

            # nearest common promotion
            for i in l.promotes_to:
                if i in r.promotes_to:
                    return HqlTypes.from_name(i)

            # only common type is string
            return HqlTypes.string()

        l = types[0]
        for r in types[1:]:
            l = promote(l, r)

        return l

    @register_type('hql_type')
    class type(HqlType):
        """Represent the generic HQL type metatype."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.DataType()

    @register_type('hql_decimal')
    class decimal(HqlType):
        """Represent decimal numeric values."""

        promotes_to = ('double',)

        # polars caps decimals at 38 digits, default to an even integer/fraction split
        def __init__(self, precision:int=38, scale:int=18):
            HqlTypes.HqlType.__init__(self)
            self.precision = precision
            self.scale = scale
            self.proto = pl.Decimal(precision, scale)

        def params(self) -> tuple:
            return (self.precision, self.scale)

        def cast(self, series:pl.Series):
            # polars can't cast booleans straight to decimals
            if series.dtype == pl.Boolean:
                series = series.cast(pl.Int8)
            return series.cast(self.pl_schema())

        def widen(self, other:HqlTypes.HqlType) -> Optional[HqlTypes.HqlType]:
            assert isinstance(other, HqlTypes.decimal)
            scale = max(self.scale, other.scale)
            digits = max(self.precision - self.scale, other.precision - other.scale)
            return HqlTypes.decimal(min(38, digits + scale), scale)
    
    @register_type('hql_float') 
    class float(HqlType):
        """Represent single-precision floating-point values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Float32()

            self.priority = 3

        promotes_to = ('double',)

    @register_type('hql_double')
    @register_type('hql_real')
    class double(HqlType):
        """Represent double-precision floating-point values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Float64()
    
    @register_type('hql_byte') 
    @register_type('hql_int8')
    class byte(HqlType):
        """Represent signed 8-bit integer values."""

        promotes_to = ('short', 'int', 'long', 'xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int8()

    @register_type('hql_short')
    @register_type('hql_int16')
    class short(HqlType):
        """Represent signed 16-bit integer values."""

        promotes_to = ('int', 'long', 'xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int16()

    @register_type('hql_int')
    @register_type('hql_int32')
    class int(HqlType):
        """Represent signed 32-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int32()
            
            self.priority = 2

        promotes_to = ('long', 'xlong', 'decimal', 'double')
    
    @register_type('hql_long') 
    @register_type('hql_int64')
    class long(HqlType):
        """Represent signed long integer values."""

        promotes_to = ('xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int64()

    @register_type('hql_xlong')
    class xlong(HqlType):
        """Represent signed 128-bit integer values."""

        promotes_to = ('double',)

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int128()

    @register_type('hql_uxlong')
    class uxlong(HqlType):
        """Represent unsigned 128-bit integer values."""

        promotes_to = ('double',)

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt128()

    @register_type('hql_guid')
    @register_type('hql_uniqueid')
    class guid(HqlType):
        """Represent globally unique identifiers as canonical strings."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.String()

        def cast_single(self, value) -> Optional[str]:
            try:
                if isinstance(value, int):
                    return str(uuid.UUID(int=value))
                return str(uuid.UUID(str(value)))
            except ValueError:
                return None

        def cast(self, series:pl.Series):
            if series.dtype == pl.Null:
                return series.cast(self.pl_schema())

            guids = [self.cast_single(i) if i is not None else None for i in series]
            return pl.Series(series.name, guids, dtype=self.proto)
    
    @register_type('hql_ubyte') 
    @register_type('hql_uint8')
    class ubyte(HqlType):
        """Represent unsigned 8-bit integer values."""

        promotes_to = ('ushort', 'short', 'uint', 'int', 'ulong', 'long', 'uxlong', 'xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt8()
        
    @register_type('hql_ushort')
    @register_type('hql_uint16')
    class ushort(HqlType):
        """Represent unsigned 16-bit integer values."""

        promotes_to = ('uint', 'int', 'ulong', 'long', 'uxlong', 'xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt16()
    
    @register_type('hql_uint') 
    @register_type('hql_uint32')
    class uint(HqlType):
        """Represent unsigned 32-bit integer values."""

        promotes_to = ('ulong', 'long', 'uxlong', 'xlong', 'decimal', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt32()
    
    @register_type('hql_ulong') 
    @register_type('hql_uint64')
    class ulong(HqlType):
        """Represent unsigned 64-bit integer values."""

        # not decimal, that would make the join with signed types (xlong) order dependent
        promotes_to = ('uxlong', 'xlong', 'double')

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt64()

    @register_type('hql_ip')
    class ip(HqlType):
        """Represent generic IP address values as strings."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.String()

    @register_type('hql_ip4')
    class ip4(HqlType):
        """Represent IPv4 addresses as unsigned 32-bit integers."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt32()

            self.complex = True

        def cast_single(self, ip:Union[StringLiteral, str]) -> Optional[int]:
            from Hql.Expressions.Literals import StringLiteral

            if isinstance(ip, StringLiteral):
                ip = ip.str()

            # Likely IPv6 or trash garbo data if this fails
            try:
                return int(ipaddress.IPv4Address(ip.strip()))
            except ValueError:
                return None

        def cast(self, series:pl.Series):
            # lazy if not string
            if series.dtype != pl.String:
                return series.cast(self.pl_schema())

            ips = []
            for i in series:
                ips.append(self.cast_single(i)) if i != None else ips.append(None)
                
            return pl.Series(ips, dtype=self.proto)
        
        def human_single(self, ip:Union[Integer, int]) -> str:
            from Hql.Expressions.Literals import Integer

            if isinstance(ip, Integer):
                ip = ip.value

            d = 0xFF
            c = d << 8
            b = c << 8
            a = b << 8

            return f'{(ip & a) >> 24}.{(ip & b) >> 16}.{(ip & c) >> 8}.{ip & d}'
        
        def human(self, series:pl.Series):
            if series.dtype != self.proto:
                raise hqle.CompilerException('Attempting to human a non-converted ip4 field')
            
            ips = []
            for i in series:
                ips.append(self.human_single(i)) if i != None else ips.append(None)

            return pl.Series(ips, dtype=pl.String)                

    @register_type('hql_ip6')
    class ip6(HqlType):
        """Represent IPv6 addresses as unsigned 128-bit integers."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt128()

            self.complex = True

        def cast_single(self, ip:Union[StringLiteral, str]) -> Optional[int]:
            from Hql.Expressions.Literals import StringLiteral

            if isinstance(ip, StringLiteral):
                ip = ip.str()

            try:
                return int(ipaddress.IPv6Address(ip.strip()))
            except ValueError:
                return None

        def cast(self, series:pl.Series):
            # lazy if not string
            if series.dtype != pl.String:
                return series.cast(self.pl_schema())

            ips = [self.cast_single(i) if i is not None else None for i in series]
            return pl.Series(series.name, ips, dtype=self.proto)

        def human_single(self, ip:int) -> str:
            return str(ipaddress.IPv6Address(ip))

        def human(self, series:pl.Series):
            if series.dtype != self.proto:
                raise hqle.CompilerException('Attempting to human a non-converted ip6 field')

            ips = [self.human_single(i) if i is not None else None for i in series]
            return pl.Series(ips, dtype=pl.String)
    
    # Not registered as hql_date, in queries date is KQL's synonym for datetime.
    # Exists so python dates and polars Date columns load without conversion.
    class date(HqlType):
        """Represent calendar date values."""

        promotes_to = ('datetime',)

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Date()

    @register_type('hql_datetime')     
    @register_type('hql_date')
    class datetime(HqlType):
        """Represent date and time values."""

        def __init__(self, time_unit:str='us', time_zone:Optional[str]=None):
            HqlTypes.HqlType.__init__(self)
            self.time_unit = time_unit
            self.time_zone = time_zone
            self.proto = pl.Datetime(time_unit, time_zone)

            self.complex = True

        def params(self) -> tuple:
            return (self.time_unit, self.time_zone)

        def widen(self, other:HqlTypes.HqlType) -> Optional[HqlTypes.HqlType]:
            assert isinstance(other, HqlTypes.datetime)
            unit = HqlTypes.finer_unit(self.time_unit, other.time_unit)
            zone = self.time_zone if self.time_zone == other.time_zone else 'UTC'
            return HqlTypes.datetime(unit, zone)

        def human(self, series:pl.Series):
            dates = []
            for i in series:
                if i == None:
                    dates.append(None)
                    continue
                dates.append(i.isoformat())
            return pl.Series(dates, dtype=pl.String)
        
    @register_type('hql_duration')
    @register_type('hql_timespan')
    class duration(HqlType):
        """Represent elapsed time values."""

        def __init__(self, time_unit:str='us'):
            HqlTypes.HqlType.__init__(self)
            self.time_unit = time_unit
            self.proto = pl.Duration(time_unit)

        def params(self) -> tuple:
            return (self.time_unit,)

        def widen(self, other:HqlTypes.HqlType) -> Optional[HqlTypes.HqlType]:
            assert isinstance(other, HqlTypes.duration)
            return HqlTypes.duration(HqlTypes.finer_unit(self.time_unit, other.time_unit))
        
    @register_type('hql_time')  
    class time(HqlType):
        """Represent time-of-day values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Time()

    # Need to figure this out properly
    @register_type('hql_range')
    class range(HqlType, pl.Struct):
        """Represent typed start and end values as a range."""

        def __init__(self, inner:HqlTypes.HqlType):
            HqlTypes.HqlType.__init__(self, inner=inner)
            self.proto = self.pl_schema()

        def pl_schema(self) -> pl.DataType:
            assert self.inner != None
            pl_schema = self.inner.pl_schema()
            return pl.Struct(fields=[pl.Field('start', pl_schema), pl.Field('end', pl_schema)])

    @register_type('hql_matrix')
    class matrix(HqlType):
        """Represent a fixed-size collection of one element type."""

        def __init__(self, inner:HqlTypes.HqlType):
            HqlTypes.HqlType.__init__(self, inner=inner)
            raise hqle.CompilerException('Unimplemented hql type matrix')

        def pl_schema(self) -> pl.DataType:
            assert self.inner != None
            return pl.Array(self.inner.pl_schema())
    
    @register_type('hql_string') 
    class string(HqlType):
        """Represent UTF-8 string values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.String()
            
            self.priority = 4

        def cast(self, series:pl.Series):
            # polars can't cast these to strings (or does it poorly), so serialize to JSON
            if isinstance(series.dtype, (pl.Object, pl.Struct, pl.List, pl.Array)):
                def single(value):
                    if value is None or isinstance(value, str):
                        return value
                    return json.dumps(value, default=str)
                return pl.Series(series.name, [single(x) for x in series.to_list()], dtype=pl.String)

            return series.cast(self.pl_schema())
        
    @register_type('hql_dynamic')
    class dynamic(HqlType):
        """Represent schemaless values (scalars, lists, or objects) as Python objects."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Object()

        def cast(self, series:pl.Series):
            if series.dtype == pl.Object:
                return series
            return pl.Series(series.name, series.to_list(), dtype=pl.Object)

    @register_type('hql_enum') 
    class enum(HqlType):
        """Represent values restricted to a string enumeration."""

        def __init__(self, values:list[str]):
            raise hqle.CompilerException('Unimplemented type enum')
            HqlTypes.HqlType.__init__(self, pl.Null())
        
    @register_type('hql_binary') 
    class binary(HqlType):
        """Represent arbitrary binary values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Binary()
    
    @register_type('hql_bool') 
    @register_type('hql_boolean')
    class bool(HqlType):
        """Represent Boolean values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Boolean()
            
            self.priority = 1

        promotes_to = ('ubyte', 'byte', 'ushort', 'short', 'uint', 'int', 'ulong', 'long', 'uxlong', 'xlong', 'decimal', 'float', 'double')

    '''
    This is a generic object, unspecified the contents
    '''
    @register_type('hql_object')
    class object(HqlType):
        """Represent structured values described by a field schema."""

        def __init__(self, schema:SchemaDT):
            HqlTypes.HqlType.__init__(self)
            self.schema:SchemaDT = schema

        def __bool__(self):
            return bool(self.schema)

        def __eq__(self, value: object, /) -> bool:
            if not isinstance(value, HqlTypes.object):
                return False
            return self.eq(self.schema, value.schema)

        def __hash__(self):
            # nested dicts and nested objects hash the same, eq treats them alike
            def h(schema:SchemaDT):
                items = []
                for key in sorted(schema):
                    cur = schema[key]
                    if isinstance(cur, HqlTypes.object):
                        cur = cur.schema
                    items.append((key, h(cur) if isinstance(cur, Mapping) else hash(cur)))
                return hash(tuple(items))
            return h(self.schema)

        def __len__(self):
            return len(self.schema)

        def __getitem__(self, key:Reference):
            from Hql.Expressions.References import Path

            def get(data:SchemaDT, key:Reference):
                base = key[0]
                if base not in data:
                    logging.error(f'Error getting item from object: {base}')
                    logging.error(json.dumps(data, default=repr))
                    raise IndexError
                out = data[base]

                if isinstance(key, Path):
                    if isinstance(out, HqlTypes.object):
                        out = out.schema
                    elif isinstance(out, HqlTypes.HqlType):
                        raise IndexError
                    return get(out, Path(key.path[1:]))

                return out

            got = get(self.schema, key)
            if isinstance(got, dict):
                got = HqlTypes.object(got)
            return got

        def __iter__(self) -> Iterator[Reference]:
            from Hql.Expressions.References import NamedReference

            keys = []
            for i in self.schema:
                keys.append(NamedReference(i))
            return iter(keys)

        @property
        def proto(self) -> Optional[pl.DataType]:
            return self.pl_schema()

        @proto.setter
        def proto(self, val):
            ...

        def to_dict(self) -> dict:
            def td(schema:SchemaDT):
                out = dict()
                for key in schema:
                    cur = schema[key]
                    if isinstance(cur, HqlTypes.object):
                        out[key] = cur.to_dict()

                    elif isinstance(cur, dict):
                        out[key] = td(cur)
                    
                    elif isinstance(cur, HqlTypes.HqlType):
                        out[key] = cur.name

                return out

            return td(self.schema)

        # generic to be used for other types resembling this one
        # reduces repeat code which might become inconsistent
        @staticmethod
        def eq(l:SchemaDT, r:SchemaDT) -> bool:
            if len(l) != len(r):
                return False

            for i in l:
                # keycheck
                if i not in r:
                    return False

                # another linter trick
                lv = l[i]
                rv = r[i]

                # nested dicts and nested objects are interchangeable
                if isinstance(lv, HqlTypes.object):
                    lv = lv.schema
                if isinstance(rv, HqlTypes.object):
                    rv = rv.schema

                # dict check
                if isinstance(lv, Mapping) and isinstance(rv, Mapping):
                    if not HqlTypes.object.eq(lv, rv):
                        return False
                    continue

                # everything else
                if lv != rv:
                    return False

            return True
        
        def pl_schema(self) -> pl.Struct:
            # returns list in the case of empty dict
            # polars likes it better
            def gs(schema:Union[SchemaDT, dict]) -> Union[dict, list]:
                new = {}
                for key in schema:
                    cur = schema[key]
                    if isinstance(cur, dict):
                        new[key] = pl.Struct(gs(cur))
                    else:
                        new[key] = cur.pl_schema()
                return new if new else []
            return pl.Struct(gs(self.schema))
            
    @register_type('hql_null')
    class null(HqlType):
        """Represent missing or null values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Null()
            
            self.priority = 0

        # null merges into anything, resolve_conflict special cases it
        
    @register_type('hql_unknown')
    class unknown(HqlType, pl.Unknown):
        """Represent values whose HQL type is not yet known."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Unknown()
            raise hqle.CompilerException('Unknown type Unimplemented')
        
    @register_type('hql_multivalue')
    class multivalue(HqlType):
        """Represent a variable-length collection of one element type."""

        def __init__(self, inner:HqlTypes.HqlType):
            HqlTypes.HqlType.__init__(self, inner=inner)
            # fail early on inner types without a polars representation
            assert inner.pl_schema() is not None
            
            self.priority = 5

        # derived from inner, which can be swapped out after init
        @property
        def proto(self) -> Optional[pl.DataType]:
            return self.pl_schema()

        @proto.setter
        def proto(self, val):
            ...

        @property
        def inner(self) -> HqlTypes.HqlType:
            inner = self._inner
            assert isinstance(inner, HqlTypes.HqlType)
            return inner

        @inner.setter
        def inner(self, val:Optional[CompilerType]):
            assert val is None or isinstance(val, HqlTypes.HqlType)
            self._inner = val
        
        def pl_schema(self):
            if isinstance(self.inner, type):
                return pl.List(self.inner().pl_schema())
            return pl.List(self.inner.pl_schema())
        
        # Casts a polars series to List
        def cast(self, series:pl.Series):
            # empty objects are falsy, so check for None explicitly
            if self._inner is None:
                logging.critical('Cannot cast to empty multivalue!')
                raise TypeError('Attempted to cast to empty multivalue')
            
            return series.cast(self.pl_schema())
