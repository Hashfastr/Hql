from __future__ import annotations
from typing import Optional
from Hql.Context import register_type, get_type
from Hql.Types.Compiler import CompilerType

class PythonTypes():
    """Namespace for Python-to-HQL type adapters."""

    from Hql.Types.Hql import HqlTypes as hqlt

    class PythonType(CompilerType):
        """Base adapter for a Python runtime type."""

        def __init__(self, inner:Optional[PythonTypes.PythonType]=None):
            CompilerType.__init__(self, inner=inner)

            self.priority = 0
            self.super = []

        def __len__(self):
            return 1
        
    @staticmethod
    def from_name(name:str):
        return get_type(f'python_{name}')

    @staticmethod
    def from_value(value) -> PythonTypes.PythonType:
        if isinstance(value, dict):
            new = dict()
            for i in value:
                new[i] = PythonTypes.from_value(value[i])
            return PythonTypes.dict(new)
        else:
            return PythonTypes.from_name(type(value).__name__)

    @staticmethod
    def resolve_conflict(types:list[PythonType]):
        if len(types) == 1:
            return types[0]
        
        # Check to see if there's a multivalue we need to handle
        mv = False
        for i in types:
            if isinstance(i, PythonTypes.list):
                mv = True
                break
        
        # Handle multivalue
        if mv:
            inner_set = set()
            for i in types:
                if isinstance(i, PythonTypes.list):
                    inner_set.add(i.inner)
                else:
                    inner_set.add(i)
            types = list(inner_set)

        # set to default basecase
        l = PythonTypes.NoneType()
        for r in types:
            if l.priority > r.priority:
                continue

            if type(r) in l.super:
                l = r
                continue

        if mv:
            return PythonTypes.list(l)
        else:
            return l

    @staticmethod
    def resolve_mv(mv:list[type]):
        mvset = set()
        for i in mv:
            mvset.add(PythonTypes.from_name(i.__name__))
        return PythonTypes.resolve_conflict(list(mvset))
            
    @register_type('python_int')
    class int(PythonType):
        """Map Python integers to the HQL integer type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.int()
            
            self.priority = 2
            self.super = (PythonTypes.float, PythonTypes.str, PythonTypes.list) 

    @register_type('python_float')
    class float(PythonType):
        """Map Python floating-point values to the HQL float type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.float()
            
            self.priority = 3
            self.super = (PythonTypes.str, PythonTypes.list)
        
    @register_type('python_str')
    class str(PythonType):
        """Map Python strings to the HQL string type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.string()
 
            self.priority = 4
            self.super = [PythonTypes.list]

    @register_type('python_datetime')
    class datetime(PythonType):
        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.datetime()

            self.priority = 4
            self.super = [PythonTypes.str, PythonTypes.list]

    @register_type('python_complex') 
    class complex(str):
        """Map Python complex values to their HQL string representation."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.string()

    @register_type('python_bytes')
    class bytes(PythonType, hqlt.binary):
        """Map Python byte strings to the HQL binary type."""
        ...
    
    @register_type('python_bool') 
    class bool(PythonType):
        """Map Python Boolean values to the HQL Boolean type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.bool()
                        
            self.priority = 1
            self.super = (PythonTypes.int, PythonTypes.str, PythonTypes.list)
        
    @register_type('python_NoneType')
    class NoneType(PythonType):
        """Map Python's singleton null type to the HQL null type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.null()
                        
            self.priority = 0
            self.super = (PythonTypes.bool, PythonTypes.int, PythonTypes.float, PythonTypes.str, PythonTypes.list, PythonTypes.dict)

    @register_type('python_list')
    class list(PythonType):
        """Map Python lists to an HQL multivalue type."""

        def __init__(self, inner:PythonTypes.PythonType):
            PythonTypes.PythonType.__init__(self, inner=inner)
            self.inner = inner
            self.HqlType = PythonTypes.hqlt.multivalue(inner.hql_schema())
            
            self.priority = 5
            self.super = []

    @register_type('python_dict')
    class dict(PythonType):
        """Map Python dictionaries to a structured HQL object type."""

        def __init__(self, schema:dict):
            PythonTypes.PythonType.__init__(self)
            self.schema = schema
            self.HqlType = PythonTypes.hqlt.object(schema)
            self.super = [PythonTypes.str]
            self.priority = 3

        def __getitem__(self, key:str):
            if isinstance(self.schema[key], dict):
                return PythonTypes.dict(self.schema[key])
            else:
                return self.schema[key]

        def __eq__(self, value: object, /) -> bool:
            if not isinstance(value, PythonTypes.dict):
                return False
            return PythonTypes.hqlt.object.eq(self.schema, value.schema)

        # I hate this, has to be a better way
        def __hash__(self):
            import json
            from hashlib import sha1
            return hash(sha1(json.dumps(self.schema, sort_keys=True, default=repr).encode()))

        def hql_schema(self) -> PythonTypes.hqlt.HqlType:
            new = dict()
            for i in self.schema:
                new[i] = self[i].hql_schema()
            return PythonTypes.hqlt.object(new)

        def pl_schema(self):
            return self.hql_schema().pl_schema()
