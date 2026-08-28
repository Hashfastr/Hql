from __future__ import annotations

import polars as pl
import logging
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

        def __init__(self, inner:Optional[HqlTypes.HqlType]=None):
            CompilerType.__init__(self)

            self._proto = None
            self._super = []
            self._inner = None

            self.complex:bool = False
            self.priority:int = 0
            self.super = [] # [HqlTypes.string(), HqlTypes.multivalue(self.__class__())]
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
    
    @staticmethod
    def from_name(name:str) -> HqlTypes.HqlType:
        return get_type(f'hql_{name}')()
    
    @staticmethod
    def resolve_conflict(types:list[HqlType]) -> HqlType:
        if len(types) == 0:
            raise hqle.CompilerException('Passed empty types list to resolve conflict')

        if len(types) == 1:
            return types[0]

        # dedupe
        types = list(set(types))

        def res_obj(objs:list[HqlTypes.HqlType]) -> HqlTypes.HqlType:
            for i in objs:
                # only common type is string
                if not isinstance(i, HqlTypes.object):
                    return HqlTypes.string()

            keyset:dict[str, set] = dict()
            for i in list(set(objs)):
                # ew, linter
                assert isinstance(i, HqlTypes.object)
                for j in i.schema:
                    if j not in keyset:
                        keyset[j] = set()
                    keyset[j].add(i.schema[j])

            out:dict[str, HqlTypes.HqlType] = dict()
            for i in keyset:
                if len(keyset[i]) == 1:
                    out[i] = list(keyset[i])[0]
                else:
                    out[i] = HqlTypes.resolve_conflict(list(keyset[i]))

            return HqlTypes.object(out)

        ### objs

        obj = True
        for i in types:
            if not isinstance(i, HqlTypes.object):
                obj = False

        if obj:
            return res_obj(types)

        ### multivalue
        
        # Check to see if there's a multivalue we need to handle
        mv = False
        for i in types:
            if isinstance(i, HqlTypes.multivalue):
                mv = True
        
        # Handle multivalue
        if mv:
            inner_set = set()
            for i in types:
                if isinstance(i, HqlTypes.multivalue):
                    inner_set.add(i.inner)
                else:
                    inner_set.add(i)

            inner = HqlTypes.resolve_conflict(list(inner_set))
            return HqlTypes.multivalue(inner)

        ### base types

        # set to default basecase, always lowest rung
        l = HqlTypes.null()
        for r in types:
            if l.priority > r.priority:
                continue
            
            # promotion case
            if r in l.super:
                l = r
            
            # find common super case
            # this might be the source of a bug in the future
            else:
                for i in l.super:
                    if i in r.super:
                        l = i

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

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Decimal()
    
    @register_type('hql_float') 
    class float(HqlType):
        """Represent single-precision floating-point values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Float32()

            self.priority = 3

    @register_type('hql_double')
    class double(HqlType):
        """Represent double-precision floating-point values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Float64()
    
    @register_type('hql_byte') 
    class byte(HqlType):
        """Represent signed 8-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int8()

    @register_type('hql_short')
    class short(HqlType):
        """Represent signed 16-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int16()

    @register_type('hql_int')
    class int(HqlType):
        """Represent signed 32-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int32()
            
            self.priority = 2
            self.super += [HqlTypes.float()]
    
    @register_type('hql_long') 
    class long(HqlType):
        """Represent signed long integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)

    @register_type('hql_xlong')
    class xlong(HqlType):
        """Represent signed 128-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int128()

    @register_type('hql_guid')
    class guid(HqlType):
        """Represent globally unique identifier values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int128()
    
    @register_type('hql_ubyte') 
    class ubyte(HqlType):
        """Represent unsigned 8-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt8()
        
    @register_type('hql_ushort')
    class ushort(HqlType):
        """Represent unsigned 16-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt16()
    
    @register_type('hql_uint') 
    class uint(HqlType):
        """Represent unsigned 32-bit integer values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.UInt32()
    
    @register_type('hql_ulong') 
    class ulong(HqlType):
        """Represent unsigned 64-bit integer values."""

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

        def cast_single(self, ip:Union[StringLiteral, str]) -> int:
            from Hql.Expressions.Literals import StringLiteral

            if isinstance(ip, StringLiteral):
                ip = ip.str()

            split = ip.split('.')
            num = 0
            for idx, j in enumerate(split):
                try:
                    # magnitude scales with the index
                    num += int(split[idx]) << (8 * (3 - idx))
                
                # Likely IPv6 if we hit this
                # Or trash garbo data
                except ValueError:
                    continue
            return num

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
        """Represent IPv6 addresses as signed 128-bit integers."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Int128()
    
    @register_type('hql_datetime')     
    class datetime(HqlType):
        """Represent date and time values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Datetime()

            self.complex = True

        def human(self, series:pl.Series):
            dates = []
            for i in series:
                if i == None:
                    dates.append(None)
                    continue
                dates.append(i.isoformat())
            return pl.Series(dates, dtype=pl.String)
        
    @register_type('hql_duration')
    class duration(HqlType):
        """Represent elapsed time values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Duration()
        
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
            self.super = []
        
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
    class bool(HqlType):
        """Represent Boolean values."""

        def __init__(self):
            HqlTypes.HqlType.__init__(self)
            self.proto = pl.Boolean()
            
            self.priority = 1
            self.super = [HqlTypes.int()]

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

        def __len__(self):
            return len(self.schema)

        def __getitem__(self, key:Reference):
            from Hql.Expressions.References import Path

            def get(data:SchemaDT, key:Reference):
                base = key[0]
                if base not in data:
                    raise IndexError
                out = data[base]

                if isinstance(key, Path):
                    if isinstance(out, HqlTypes.HqlType):
                        raise IndexError
                    return get(out, Path(key.list()[1:]))

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
                    
                    elif isinstance(cur, HqlTypes.type):
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

                # dict check
                if isinstance(lv, Mapping) and isinstance(rv, Mapping):
                    if not HqlTypes.object.eq(lv, rv):
                        return False

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
            self.super += [HqlTypes.bool(), HqlTypes.int(), HqlTypes.float()]
        
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
            self.inner = inner
            assert inner.proto
            self.proto = pl.List(inner.proto)

            HqlTypes.HqlType.__init__(self, inner=inner)
            
            self.priority = 5
            self.super = []
        
        def pl_schema(self):
            if isinstance(self.inner, type):
                return pl.List(self.inner().pl_schema())
            return pl.List(self.inner.pl_schema())
        
        # Casts a polars series to List
        def cast(self, series:pl.Series):
            if not self.inner:
                logging.critical('Cannot cast to empty multivalue!')
                raise TypeError('Attempted to cast to empty multivalue')
            
            return series.cast(self.pl_schema())
