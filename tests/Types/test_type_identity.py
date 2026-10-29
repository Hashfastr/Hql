import json

import polars as pl
import pytest

from Hql.Data import Schema, Table
from Hql.Expressions.References import NamedReference, Path
from Hql.Types.Hql import HqlTypes as hqlt
from Hql.Types.Kusto import KustoTypes
from Hql.Types.Polars import PolarsTypes as plt
from Hql.Types.Python import PythonTypes as pyt


def load(values, key='a'):
    return Table(init_data=[{key: v} for v in values])


# ---------------------------------------------------------------------------
# workspace-qgw.24: parameterized types compare their parameters
# ---------------------------------------------------------------------------

class TestParameterizedEquality:
    def test_multivalue_inner_distinguishes(self):
        assert hqlt.multivalue(hqlt.int()) != hqlt.multivalue(hqlt.string())
        assert hqlt.multivalue(hqlt.int()) == hqlt.multivalue(hqlt.int())

    def test_multivalue_hash_follows_eq(self):
        assert hash(hqlt.multivalue(hqlt.int())) == hash(hqlt.multivalue(hqlt.int()))
        assert len({hqlt.multivalue(hqlt.int()), hqlt.multivalue(hqlt.string())}) == 2

    def test_range_inner_distinguishes(self):
        assert hqlt.range(hqlt.int()) != hqlt.range(hqlt.string())

    def test_schema_merge_keeps_both_multivalues(self):
        merged = Schema.merge([
            Schema(schema={'a': hqlt.multivalue(hqlt.int())}),
            Schema(schema={'a': hqlt.multivalue(hqlt.string())}),
        ])
        assert len(merged.schema.schema) == 2


# ---------------------------------------------------------------------------
# workspace-qgw.25: object is hashable
# ---------------------------------------------------------------------------

class TestObjectHash:
    def test_hashable(self):
        hash(hqlt.object({'a': hqlt.int()}))

    def test_equal_objects_hash_equal(self):
        left = hqlt.object({'a': hqlt.int(), 'b': {'c': hqlt.string()}})
        right = hqlt.object({'b': hqlt.object({'c': hqlt.string()}), 'a': hqlt.int()})
        assert left == right
        assert hash(left) == hash(right)

    def test_different_objects_not_equal(self):
        assert hqlt.object({'a': {'c': hqlt.int()}}) != hqlt.object({'a': {'c': hqlt.string()}})

    def test_set_of_objects(self):
        assert len({hqlt.object({'a': hqlt.int()}), hqlt.object({'a': hqlt.int()})}) == 1

    def test_resolve_conflict_on_objects(self):
        result = hqlt.resolve_conflict([hqlt.object({'a': hqlt.int()}), hqlt.object({'b': hqlt.string()})])
        assert result == hqlt.object({'a': hqlt.int(), 'b': hqlt.string()})


# ---------------------------------------------------------------------------
# workspace-qgw.26: to_dict keeps leaf types and is JSON serializable
# ---------------------------------------------------------------------------

class TestToDict:
    def test_object_to_dict_keeps_leaves(self):
        obj = hqlt.object({'a': hqlt.string(), 'b': {'c': hqlt.int()}})
        assert obj.to_dict() == {'a': 'string', 'b': {'c': 'int'}}

    def test_schema_to_dict(self):
        schema = Schema(schema={'a': hqlt.long(), 'b': {'c': hqlt.string()}})
        assert schema.to_dict() == {'a': 'long', 'b': {'c': 'string'}}

    def test_compiler_type_to_dict_is_json(self):
        for t in (hqlt.int(), pyt.int(), plt.Int64(), KustoTypes.long()):
            json.dumps(t.to_dict())

    def test_compiler_type_to_dict_type_name(self):
        assert hqlt.int().to_dict() == {'type': 'HqlType', 'name': 'int'}


# ---------------------------------------------------------------------------
# workspace-qgw.27: nested multivalue
# ---------------------------------------------------------------------------

class TestNestedMultivalue:
    def test_proto_set(self):
        assert hqlt.multivalue(hqlt.int()).proto == pl.List(pl.Int32)

    def test_nested(self):
        mv = hqlt.multivalue(hqlt.multivalue(hqlt.int()))
        assert mv.pl_schema() == pl.List(pl.List(pl.Int32))

    def test_proto_tracks_inner(self):
        mv = hqlt.multivalue(hqlt.int())
        mv.inner = hqlt.string()
        assert mv.proto == pl.List(pl.String)

    def test_table_of_nested_lists(self):
        assert load([[[1], [2]]]).df.to_dicts() == [{'a': [[1], [2]]}]


# ---------------------------------------------------------------------------
# workspace-qgw.39: misc helpers
# ---------------------------------------------------------------------------

class TestMiscHelpers:
    def test_dict_hash_consistent_with_eq(self):
        left = pyt.dict({'a': pyt.int(), 'b': pyt.dict({'c': pyt.str()})})
        right = pyt.dict({'b': pyt.dict({'c': pyt.str()}), 'a': pyt.int()})
        assert left == right
        assert hash(left) == hash(right)

    def test_from_value_returns_instance(self):
        assert isinstance(pyt.from_value(1), pyt.int)

    def test_resolve_mv(self):
        assert isinstance(pyt.resolve_mv([int, float]), pyt.float)

    def test_object_getitem_nested_object(self):
        obj = hqlt.object({'a': hqlt.object({'b': {'c': hqlt.string()}})})
        assert obj[Path([NamedReference('a'), NamedReference('b'), NamedReference('c')])] == hqlt.string()

    def test_object_getitem_scalar_path_raises(self):
        obj = hqlt.object({'a': hqlt.int()})
        with pytest.raises(IndexError):
            obj[Path([NamedReference('a'), NamedReference('b')])]

    def test_multivalue_of_empty_object_casts(self):
        mv = hqlt.multivalue(hqlt.object({}))
        out = mv.cast(pl.Series([[{}]], dtype=pl.List(pl.Struct([]))))
        assert out.dtype == pl.List(pl.Struct([]))
