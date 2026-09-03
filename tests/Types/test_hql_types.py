import pytest

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Types.Hql import HqlTypes as hqlt


# ---------------------------------------------------------------------------
# HqlType base surface (CompilerType)
# ---------------------------------------------------------------------------

class TestHqlTypeBase:
    def test_int_deparse_returns_name(self):
        assert hqlt.int().deparse() == "int"

    def test_str_returns_name(self):
        assert hqlt.int().str() == "int"

    def test_equal_by_class(self):
        assert hqlt.int() == hqlt.int()
        assert hqlt.int() != hqlt.float()

    def test_hash_matches_equal(self):
        assert hash(hqlt.int()) == hash(hqlt.int())

    def test_len_is_one(self):
        assert len(hqlt.int()) == 1

    def test_pl_schema_returns_proto(self):
        import polars as pl
        assert hqlt.int().pl_schema() == pl.Int32()

    def test_long_uses_64_bit_polars_schema(self):
        import polars as pl
        assert hqlt.long().pl_schema() == pl.Int64()

    def test_to_dict_includes_name(self):
        d = hqlt.int().to_dict()
        assert d["name"] == "int"


# ---------------------------------------------------------------------------
# from_name
# ---------------------------------------------------------------------------

class TestFromName:
    def test_returns_class_not_instance(self):
        # Documented current behavior (bug): from_name returns the class.
        # See tests/Expressions/test_literals.py xfail for downstream fallout.
        assert hqlt.from_name("int") == hqlt.int()


# ---------------------------------------------------------------------------
# ip4 bitwise codec (pure Python)
# ---------------------------------------------------------------------------

class TestIP4CastSingle:
    def test_from_string_literal(self):
        assert hqlt.ip4().cast_single(StringLiteral("192.168.1.1")) == (192 << 24) | (168 << 16) | (1 << 8) | 1

    def test_from_string(self):
        assert hqlt.ip4().cast_single("10.0.0.1") == (10 << 24) | 1

    def test_zero_ip(self):
        assert hqlt.ip4().cast_single("0.0.0.0") == 0

    def test_broadcast_ip(self):
        assert hqlt.ip4().cast_single("255.255.255.255") == 0xFFFFFFFF


class TestIP4HumanSingle:
    def test_from_int(self):
        assert hqlt.ip4().human_single(0) == "0.0.0.0"

    def test_broadcast(self):
        assert hqlt.ip4().human_single(0xFFFFFFFF) == "255.255.255.255"

    def test_from_integer_literal(self):
        assert hqlt.ip4().human_single(Integer(0x0A000001)) == "10.0.0.1"

    def test_round_trip(self):
        cases = ["192.168.1.1", "10.0.0.1", "255.255.255.255", "0.0.0.0"]
        codec = hqlt.ip4()
        for ip in cases:
            assert codec.human_single(codec.cast_single(ip)) == ip


# ---------------------------------------------------------------------------
# object schema
# ---------------------------------------------------------------------------

class TestObjectType:
    def test_bool_false_for_empty(self):
        assert not hqlt.object({})

    def test_bool_true_for_non_empty(self):
        assert hqlt.object({"a": hqlt.int()})

    def test_len(self):
        assert len(hqlt.object({"a": hqlt.int(), "b": hqlt.string()})) == 2

    def test_equality_by_schema(self):
        left = hqlt.object({"a": hqlt.int()})
        right = hqlt.object({"a": hqlt.int()})
        assert left == right

    def test_inequality_different_shape(self):
        left = hqlt.object({"a": hqlt.int()})
        right = hqlt.object({"a": hqlt.string()})
        assert left != right

    def test_iter_yields_named_references(self):
        from Hql.Expressions.References import NamedReference

        obj = hqlt.object({"a": hqlt.int(), "b": hqlt.string()})
        refs = list(obj)
        assert all(isinstance(r, NamedReference) for r in refs)
        assert {r.name for r in refs} == {"a", "b"}


# ---------------------------------------------------------------------------
# range
# ---------------------------------------------------------------------------

class TestRangeType:
    def test_pl_schema_is_struct_with_start_end(self):
        import polars as pl

        r = hqlt.range(hqlt.int())
        schema = r.pl_schema()
        assert isinstance(schema, pl.Struct)
        assert {f.name for f in schema.fields} == {"start", "end"}


# ---------------------------------------------------------------------------
# matrix / enum / unknown — documented unimplemented
# ---------------------------------------------------------------------------

class TestUnimplementedTypes:
    def test_matrix_raises_on_init(self):
        with pytest.raises(hqle.CompilerException):
            hqlt.matrix(hqlt.int())

    def test_enum_raises_on_init(self):
        with pytest.raises(hqle.CompilerException):
            hqlt.enum(["a", "b"])

    def test_unknown_raises_on_init(self):
        with pytest.raises(hqle.CompilerException):
            hqlt.unknown()


# ---------------------------------------------------------------------------
# resolve_conflict
# ---------------------------------------------------------------------------

class TestResolveConflict:
    def test_empty_raises(self):
        with pytest.raises(hqle.CompilerException):
            hqlt.resolve_conflict([])

    def test_single_returns_itself(self):
        t = hqlt.int()
        assert hqlt.resolve_conflict([t]) is t

    def test_duplicates_dedupe(self):
        # deduping identical types should not error
        result = hqlt.resolve_conflict([hqlt.int(), hqlt.int()])
        assert result == hqlt.int()


# ---------------------------------------------------------------------------
# multivalue
# ---------------------------------------------------------------------------

class TestMultivalueType:
    def test_construction_from_int(self):
        mv = hqlt.multivalue(hqlt.int())
        assert isinstance(mv.inner, hqlt.int)

    def test_pl_schema_is_list(self):
        import polars as pl

        mv = hqlt.multivalue(hqlt.int())
        assert isinstance(mv.pl_schema(), pl.List)


# ---------------------------------------------------------------------------
# null
# ---------------------------------------------------------------------------

class TestNullType:
    def test_priority_is_zero(self):
        assert hqlt.null().priority == 0

    def test_pl_schema_is_null(self):
        import polars as pl

        assert hqlt.null().pl_schema() == pl.Null()


# ---------------------------------------------------------------------------
# bool
# ---------------------------------------------------------------------------

class TestBoolType:
    def test_super_includes_int(self):
        assert any(isinstance(s, hqlt.int) for s in hqlt.bool().super)
