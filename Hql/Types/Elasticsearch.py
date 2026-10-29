from __future__ import annotations
from Hql.Types.Compiler import CompilerType
import logging
from typing import Optional

from Hql.Context import register_type, get_type

class ESTypes():
    """Namespace for Elasticsearch-to-HQL type adapters."""

    from Hql.Types.Hql import HqlTypes as hqlt

    class ESType(CompilerType):
        """Base adapter for an Elasticsearch field type."""

        def __init__(self, inner:Optional[ESTypes.ESType]=None):
            CompilerType.__init__(self, inner=inner)
            self.inner:Optional[ESTypes.ESType] = inner
    
    @staticmethod
    def from_name(name:str):
        return get_type(f'elasticsearch_{name}')
            
    @register_type('elasticsearch_text')
    @register_type('elasticsearch_match_only_text')
    class text(ESType):
        """Map Elasticsearch text fields to HQL strings."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()

    @register_type('elasticsearch_boolean')
    class boolean(ESType):
        """Map Elasticsearch Boolean fields to HQL Booleans."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.bool()

    @register_type('elasticsearch_scaled_float')
    class scaled_float(ESType):
        """Map Elasticsearch scaled floats to HQL doubles."""

        # returned as doubles in _source, scaling only affects storage
        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.double()

    @register_type('elasticsearch_half_float')
    class half_float(ESType):
        """Map Elasticsearch half-precision floats to HQL floats."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.float()
    
    @register_type('elasticsearch_float')
    class float(ESType):
        """Map Elasticsearch single-precision floats to HQL floats."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.float()
        
    @register_type('elasticsearch_double')
    class double(ESType):
        """Map Elasticsearch double-precision floats to HQL doubles."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.double()
    
    @register_type('elasticsearch_byte') 
    class byte(ESType):
        """Map Elasticsearch byte integers to HQL bytes."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.byte()
    
    @register_type('elasticsearch_short') 
    class short(ESType):
        """Map Elasticsearch short integers to HQL shorts."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.short()
    
    @register_type('elasticsearch_integer') 
    class integer(ESType):
        """Map Elasticsearch integers to HQL integers."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.int()
    
    @register_type('elasticsearch_long') 
    class long(ESType):
        """Map Elasticsearch long integers to HQL longs."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.long()
    
    @register_type('elasticsearch_unsigned_long') 
    class unsigned_long(ESType):
        """Map Elasticsearch unsigned longs to HQL unsigned longs."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.ulong()
    
    @register_type('elasticsearch_ip') 
    class ip(ESType):
        """Map Elasticsearch IP fields to HQL strings."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()
        
    @register_type('elasticsearch_date')
    class date(ESType):
        """Map Elasticsearch dates to HQL datetimes."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.datetime()
    
    @register_type('elasticsearch_date_nanos') 
    class date_nanos(ESType):
        """Map nanosecond Elasticsearch dates to HQL datetimes."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.datetime()

    @register_type('elasticsearch_range')
    class range(ESType):
        """Map an Elasticsearch range and its element type to HQL."""

        def __init__(self, inner:ESTypes.ESType):
            ESTypes.ESType.__init__(self, inner=inner)
            assert self.inner
            self.HqlType = ESTypes.hqlt.range(self.inner.hql_schema())
    
    @register_type('elasticsearch_keyword') 
    @register_type('elasticsearch_constant_keyword') 
    class keyword(ESType):
        """Map Elasticsearch keyword fields to HQL strings."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()
    
    @register_type('elasticsearch_wildcard') 
    class wildcard(ESType):
        """Map Elasticsearch wildcard fields to HQL strings."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()

    @register_type('elasticsearch_binary') 
    class binary(ESType):
        """Map Elasticsearch binary fields to their HQL representation."""

        def __init__(self):
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()
    
    @register_type('elasticsearch_object') 
    class object(ESType):
        """Map an Elasticsearch object schema to an HQL object."""

        def __init__(self, schema:dict):
            ESTypes.ESType.__init__(self)
            self.schema = schema
            self.HqlType = ESTypes.hqlt.object(schema)

    '''
    Kinda odd datatype should figure out how to handle this.
    Basically an object but it's treated as a singular field.
    So a flattened field with 3 fields, one string, two integer,
    will directly match a comparison to those values without specifying the field name
    '''
    @register_type('elasticsearch_flattened') 
    class flattened(ESType):
        """Map a flattened Elasticsearch object to an HQL object."""

        def __init__(self, schema:dict):
            ESTypes.ESType.__init__(self)
            self.schema = schema
            self.HqlType = ESTypes.hqlt.object(schema)
        
    '''
    From what I can tell this is just an internal rework of objects
    '''
    @register_type('elasticsearch_nested')
    class nested(ESType):
        """Map a nested Elasticsearch object to an HQL object."""

        def __init__(self, schema:dict):
            ESTypes.ESType.__init__(self)
            self.schema = schema
            self.HqlType = ESTypes.hqlt.object(schema)
    
    @register_type('elasticsearch_alias') 
    class alias(ESType):
        """Provide a placeholder mapping for Elasticsearch aliases."""

        def __init__(self):
            logging.warning("Elasticsearch type 'alias' not implemented at the moment")
            logging.warning("This is a metatype, I don't have examples")
            ESTypes.ESType.__init__(self)
            self.HqlType = ESTypes.hqlt.string()
        
    @register_type('elasticsearch_point')
    class point(ESType):
        """Map Elasticsearch Cartesian points to HQL numeric values."""

        def __init__(self):
            ESTypes.ESType.__init__(self, ESTypes.double())
            self.HqlType = ESTypes.hqlt.multivalue(ESTypes.hqlt.double())
        
    @register_type('elasticsearch_geo_point')
    class geo_point(ESType):
        """Map Elasticsearch geographic points to HQL numeric values."""

        def __init__(self):
            ESTypes.ESType.__init__(self, ESTypes.double())
            self.HqlType = ESTypes.hqlt.multivalue(ESTypes.hqlt.double())
    
    @register_type('elasticsearch_shape') 
    class shape(ESType):
        """Map Elasticsearch Cartesian shapes to HQL numeric values."""

        def __init__(self):
            ESTypes.ESType.__init__(self, ESTypes.double())
            self.HqlType = ESTypes.hqlt.multivalue(ESTypes.hqlt.double())
                    
    @register_type('elasticsearch_geo_shape')   
    class geo_shape(ESType):
        """Map Elasticsearch geographic shapes to HQL numeric values."""

        def __init__(self):
            ESTypes.ESType.__init__(self, ESTypes.double())
            self.HqlType = ESTypes.hqlt.multivalue(ESTypes.hqlt.double())
