import pytest

from Hql.Compiler.InstructionSet import InstructionSet
from Hql.Context import Context
from Hql.Data import Data
from Hql.Database.Database import Database
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer
from Hql.Expressions.References import NamedReference
from Hql.Operators.Count import Count
from Hql.Operators.Take import Take


class _FakeUpstream:
    def __init__(self, name="fake"):
        self.name = name

    def to_dict(self):
        return {"type": "fake", "name": self.name}


class _CachingDatabase(Database):
    def __init__(self, key):
        super().__init__({}, name=key)
        self.key = key

    def eval(self, ctx):
        ctx.cache.set(self.key, None, self.key)
        return ctx


class TestInstructionSetInit:
    def test_empty_upstream_raises(self):
        with pytest.raises(hqle.CompilerException):
            InstructionSet([])

    def test_single_non_sequence_wraps(self):
        iset = InstructionSet(_FakeUpstream())
        assert len(iset.upstream) == 1

    def test_ops_default_empty(self):
        iset = InstructionSet(_FakeUpstream())
        assert iset.ops == []

    def test_id_is_8_char_hex(self):
        iset = InstructionSet(_FakeUpstream())
        assert len(iset.id) == 8
        int(iset.id, 16)


class TestInstructionSetCache:
    def test_query_cache_writes_through_instruction_cache(self):
        ctx = Context(Data())
        iset = InstructionSet(_CachingDatabase("cached-result"))

        result = iset.eval(ctx)

        assert result.cache.parent is ctx.cache
        assert ctx.cache.get("cached-result") == "cached-result"

    def test_multi_upstream_merge_retains_instruction_cache(self):
        ctx = Context(Data())
        iset = InstructionSet([
            _CachingDatabase("left"),
            _CachingDatabase("right"),
        ])

        result = iset.eval(ctx)

        assert result.cache.parent is ctx.cache
        assert ctx.cache.get("left") == "left"
        assert ctx.cache.get("right") == "right"


class TestInstructionSetFlatten:
    def test_nested_instruction_set_flattens_ops(self):
        inner = InstructionSet(_FakeUpstream(), operators=[Count()])
        outer = InstructionSet(inner, operators=[Take(Integer(5), [])])
        # outer should absorb inner's ops before its own
        assert len(outer.ops) == 2
        assert isinstance(outer.ops[0], Count)
        assert isinstance(outer.ops[1], Take)


class TestIsEmpty:
    def test_not_empty_with_upstream(self):
        # Both fields being truthy is the "not empty" case
        iset = InstructionSet(_FakeUpstream())
        assert not iset.is_empty()

    def test_reports_empty_when_both_cleared(self):
        iset = InstructionSet(_FakeUpstream())
        iset.upstream = []
        iset.ops = []
        assert iset.is_empty()


class TestAddOp:
    def test_appends_operator(self):
        iset = InstructionSet(_FakeUpstream())
        c = Count()
        acc, rej = iset.add_op(c)
        assert acc is None and rej is None
        assert iset.ops == [c]


class TestToDict:
    def test_shape(self):
        iset = InstructionSet(_FakeUpstream("src"))
        iset.add_op(Count(NamedReference("total")))
        d = iset.to_dict()

        assert d["id"] == iset.id
        assert d["upstream"] == [{"type": "fake", "name": "src"}]
        assert len(d["ops"]) == 1
        assert d["ops"][0]["type"] == "Count"
        assert d["ops"][0]["deparse"] == "count as total"
