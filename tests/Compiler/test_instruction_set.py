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


class _FakeUpstream(Database):
    def __init__(self, name="fake"):
        super().__init__({}, name=name)

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

    def test_non_database_upstream_raises(self):
        with pytest.raises(hqle.CompilerException):
            InstructionSet(object())

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

    def test_upstream_cannot_be_cleared(self):
        iset = InstructionSet(_FakeUpstream())
        with pytest.raises(hqle.CompilerException):
            iset.upstream = []


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


# ---------------------------------------------------------------------------
# Mappings, map ecs = { EventID: event.id }
# ---------------------------------------------------------------------------

def _path(*names):
    from Hql.Expressions.References import Path
    return Path([NamedReference(x) for x in names])


def _ecs():
    from Hql.Query import Mapping

    mapping = Mapping(NamedReference("ecs"))
    mapping.add(NamedReference("EventID"), _path("event", "id"))
    return mapping


def _where_eventid(value=4624):
    from Hql.Expressions.Logic import Equality
    from Hql.Operators.Where import Where
    return Where(Equality(NamedReference("EventID"), [Integer(value)]))


class TestAddOpMaps:
    def _iset(self):
        return InstructionSet(Database({}, name="src"))

    def test_without_maps_appends_unchanged(self):
        iset = self._iset()
        op = _where_eventid()
        iset.add_op(op)
        assert iset.ops == [op]

    def test_map_sets_maps_without_adding_an_op(self):
        from Hql.Operators.Map import Map

        iset = self._iset()
        mapping = _ecs()
        acc, rej = iset.add_op(Map(mapping))

        assert acc is None and rej is None
        assert iset.ops == []
        assert iset.maps == [mapping]

    def test_same_mapping_added_once(self):
        from Hql.Operators.Map import Map

        iset = self._iset()
        mapping = _ecs()
        iset.add_op(Map(mapping))
        iset.add_op(Map(mapping))
        assert iset.maps == [mapping]

    def test_unresolved_map_raises(self):
        from Hql.Operators.Map import Map

        with pytest.raises(hqle.CompilerException):
            self._iset().add_op(Map(NamedReference("ecs")))

    def test_operators_after_map_are_remapped(self):
        from Hql.Operators.Map import Map

        iset = self._iset()
        iset.add_op(Map(_ecs()))
        iset.add_op(_where_eventid())

        assert [x.deparse() for x in iset.ops] == ["where event.id == 4624"]

    def test_operators_before_map_are_untouched(self):
        from Hql.Operators.Map import Map

        iset = self._iset()
        iset.add_op(_where_eventid())
        iset.add_op(Map(_ecs()))

        assert [x.deparse() for x in iset.ops] == ["where EventID == 4624"]

    def test_mapping_does_not_modify_the_given_operator(self):
        from Hql.Operators.Map import Map

        iset = self._iset()
        op = _where_eventid()
        iset.add_op(Map(_ecs()))
        iset.add_op(op)

        assert op.deparse() == "where EventID == 4624"

    def test_multi_destination_reference_raises(self):
        from Hql.Operators.Map import Map

        mapping = _ecs()
        mapping.add(NamedReference("EventID"), NamedReference("event_id"))

        iset = self._iset()
        iset.add_op(Map(mapping))
        with pytest.raises(hqle.CompilerException):
            iset.add_op(_where_eventid())


class TestUnmap:
    def test_appends_reverse_rename_and_clears(self):
        from Hql.Operators.Map import Map
        from Hql.Operators.Project import ProjectRename

        iset = InstructionSet(Database({}, name="src"))
        iset.add_op(Map(_ecs()))
        iset.unmap()

        assert len(iset.ops) == 1
        assert isinstance(iset.ops[0], ProjectRename)
        assert iset.ops[0].deparse() == "project-rename EventID=event.id"
        assert iset.maps == []

    def test_renames_every_destination(self):
        from Hql.Operators.Map import Map

        mapping = _ecs()
        mapping.add(NamedReference("EventID"), NamedReference("event_id"))

        iset = InstructionSet(Database({}, name="src"))
        iset.add_op(Map(mapping))
        iset.unmap()

        assert iset.ops[0].deparse() == "project-rename EventID=event.id, EventID=event_id"

    def test_without_maps_adds_nothing(self):
        iset = InstructionSet(Database({}, name="src"))
        iset.unmap()
        assert iset.ops == []
