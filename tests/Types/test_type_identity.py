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
