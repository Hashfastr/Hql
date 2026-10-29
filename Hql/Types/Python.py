from __future__ import annotations
from typing import Optional, Mapping
from Hql.Context import register_type, get_type
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Types.Compiler import CompilerType

class PythonTypes():
    """Namespace for Python-to-HQL type adapters."""

    from Hql.Types.Hql import HqlTypes as hqlt

    class PythonType(CompilerType):
        """Base adapter for a Python runtime type."""

        # Registered python type names this type can be widened to, nearest first.
        # Every list follows the same overall ordering so resolve_conflict is order independent.
        promotes_to:tuple[str, ...] = ()

        def __init__(self, inner:Optional[PythonTypes.PythonType]=None):
            CompilerType.__init__(self, inner=inner)

            self.priority = 0

        def __len__(self):
            return 1
        
    @staticmethod
    def from_name(name:str):
        # any python value can at least be carried as a dynamic object
        try:
            return get_type(f'python_{name}')
        except hqle.CompilerException:
            return PythonTypes.object

    @staticmethod
    def from_value(value) -> PythonTypes.PythonType:
        if isinstance(value, dict):
            new = dict()
            for i in value:
                new[i] = PythonTypes.from_value(value[i])
            return PythonTypes.dict(new)
        elif isinstance(value, list):
            if not value:
                return PythonTypes.list(PythonTypes.NoneType())
            inner = PythonTypes.resolve_conflict([PythonTypes.from_value(x) for x in value])
            return PythonTypes.list(inner)
        else:
            return PythonTypes.from_name(type(value).__name__)()

    @staticmethod
    def resolve_conflict(types:list[PythonType]) -> PythonType:
        if len(types) == 0:
            raise hqle.CompilerException('Passed empty types list to resolve conflict')

        # order preserving dedupe, set() order depends on the hash seed
        deduped = []
        for i in types:
            if i not in deduped:
                deduped.append(i)
        types = deduped

        if len(types) == 1:
            return types[0]

        # None merges into anything
        types = [x for x in types if not isinstance(x, PythonTypes.NoneType)]
        if len(types) == 0:
            return PythonTypes.NoneType()
        if len(types) == 1:
            return types[0]

        # dicts merge key by key, keys missing from some dicts are None there
        if all(isinstance(x, PythonTypes.dict) for x in types):
            keyset:dict = dict()
            for i in types:
                assert isinstance(i, PythonTypes.dict)
                for key in i.schema:
                    keyset.setdefault(key, []).append(i[key])

            merged = dict()
            for key in keyset:
                merged[key] = PythonTypes.resolve_conflict(keyset[key])
            return PythonTypes.dict(merged)
        
        # A scalar mixed with lists becomes a single element list
        if any(isinstance(x, PythonTypes.list) for x in types):
            inners = []
            for i in types:
                if isinstance(i, PythonTypes.list):
                    assert isinstance(i.inner, PythonTypes.PythonType)
                    inners.append(i.inner)
                else:
                    inners.append(i)
            return PythonTypes.list(PythonTypes.resolve_conflict(inners))

        # polars can load these into a string column, anything else (datetimes, dicts, bytes...) can't
        stringable = ('bool', 'int', 'Decimal', 'float', 'str')

        def promote(l:PythonTypes.PythonType, r:PythonTypes.PythonType) -> PythonTypes.PythonType:
            if l == r:
                return l

            if isinstance(l, PythonTypes.object) or isinstance(r, PythonTypes.object):
                return PythonTypes.object()

            if r.name in l.promotes_to:
                return r

            if l.name in r.promotes_to:
                return l

            # nearest common promotion
            for i in l.promotes_to:
                if i in r.promotes_to:
                    return PythonTypes.from_name(i)()

            # only common type is string, if the values can be loaded as one
            if l.name in stringable and r.name in stringable:
                return PythonTypes.str()
            return PythonTypes.object()

        l = types[0]
        for r in types[1:]:
            l = promote(l, r)

        return l

    @staticmethod
    def resolve_mv(mv:list[type]):
        types = [PythonTypes.from_name(i.__name__)() for i in mv]
        return PythonTypes.resolve_conflict(types)
            
    @register_type('python_int')
    class int(PythonType):
        """Map Python integers to the HQL long type."""

        # not Decimal, polars can't load bools (which widen to int) into a decimal column
        promotes_to = ('float',)

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.long()
            
            self.priority = 2

    @register_type('python_Decimal')
    class Decimal(PythonType):
        """Map Python decimals to the HQL decimal type."""

        promotes_to = ('float',)

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.decimal()

            self.priority = 3

    @register_type('python_float')
    class float(PythonType):
        """Map Python floating-point values to the HQL double type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.double()
            
            self.priority = 3
        
    @register_type('python_str')
    class str(PythonType):
        """Map Python strings to the HQL string type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.string()
 
            self.priority = 4

    @register_type('python_date')
    class date(PythonType):
        """Map Python dates to the HQL date type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.date()

            self.priority = 4

    @register_type('python_datetime')
    class datetime(PythonType):
        """Map Python datetimes to the HQL datetime type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.datetime()

            self.priority = 4

    @register_type('python_timedelta')
    class timedelta(PythonType):
        """Map Python timedeltas to the HQL duration type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.duration()

            self.priority = 4

    @register_type('python_complex') 
    class complex(str):
        """Map Python complex values to their HQL string representation."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.string()

    @register_type('python_bytes')
    class bytes(PythonType):
        """Map Python byte strings to the HQL binary type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.binary()

            self.priority = 4
    
    @register_type('python_bool') 
    class bool(PythonType):
        """Map Python Boolean values to the HQL Boolean type."""

        promotes_to = ('int', 'float')

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.bool()
                        
            self.priority = 1
        
    @register_type('python_NoneType')
    class NoneType(PythonType):
        """Map Python's singleton null type to the HQL null type."""

        # None merges into anything, resolve_conflict special cases it

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.null()
                        
            self.priority = 0

    @register_type('python_object')
    class object(PythonType):
        """Map arbitrary or mixed Python values to the HQL dynamic type."""

        def __init__(self):
            PythonTypes.PythonType.__init__(self)
            self.HqlType = PythonTypes.hqlt.dynamic()

            self.priority = 6

    @register_type('python_list')
    class list(PythonType):
        """Map Python lists to an HQL multivalue type."""

        def __init__(self, inner:PythonTypes.PythonType):
            PythonTypes.PythonType.__init__(self, inner=inner)
            self.inner = inner
            self.HqlType = PythonTypes.hqlt.multivalue(inner.hql_schema())
            
            self.priority = 5

        def hql_schema(self) -> PythonTypes.hqlt.HqlType:
            assert isinstance(self.inner, PythonTypes.PythonType)
            # polars can't hold a list of arbitrary objects, so mixed lists are dynamic as a whole
            if isinstance(self.inner, PythonTypes.object):
                return PythonTypes.hqlt.dynamic()
            return PythonTypes.hqlt.multivalue(self.inner.hql_schema())

    @register_type('python_dict')
    class dict(PythonType):
        """Map Python dictionaries to a structured HQL object type."""

        def __init__(self, schema:dict):
            PythonTypes.PythonType.__init__(self)
            self.schema = schema
            self.HqlType = PythonTypes.hqlt.object(schema)
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

        def __hash__(self):
            # structural, consistent with __eq__
            def h(schema):
                items = []
                for key in sorted(schema):
                    cur = schema[key]
                    if isinstance(cur, PythonTypes.dict):
                        cur = cur.schema
                    items.append((key, h(cur) if isinstance(cur, Mapping) else hash(cur)))
                return hash(tuple(items))
            return h(self.schema)

        def hql_schema(self) -> PythonTypes.hqlt.HqlType:
            new = dict()
            for i in self.schema:
                new[i] = self[i].hql_schema()
            return PythonTypes.hqlt.object(new)

        def pl_schema(self):
            return self.hql_schema().pl_schema()
