import pytest

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions import OpParameter
from Hql.Expressions.Aggregation import OrderedExpression
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Expressions.Logic import BinaryLogic, Equality
from Hql.Expressions.References import NamedReference, Wildcard
from Hql.Operators.Count import Count
from Hql.Operators.Operator import Operator
from Hql.Operators.Project import (
    Project,
    ProjectAway,
    ProjectKeep,
    ProjectRename,
    ProjectReorder,
)
from Hql.Operators.Sort import Sort
from Hql.Operators.Take import Take
from Hql.Operators.Unnest import Unnest
from Hql.Operators.Where import Where


# ---------------------------------------------------------------------------
# Operator base
# ---------------------------------------------------------------------------

class TestOperatorBase:
    def test_has_random_id(self):
        op1 = Operator()
        op2 = Operator()
        assert op1.id != op2.id
        assert len(op1.id) == 8

    def test_default_flags(self):
        op = Operator()
        assert op.exprs == []
        assert op.tabular is False
        assert op.expr is None

    def test_to_dict_omits_missing_expr(self):
        op = Operator()
        d = op.to_dict()
        assert "expression" not in d
        assert d["id"] == op.id

    def test_has_method(self):
        op = Operator()
        op.methods = ["foo"]
        assert op.has_method("foo")
        assert not op.has_method("bar")

    def test_can_integrate(self):
        op = Operator()
        op.compatible = ["Where"]
        assert op.can_integrate("Where")
        assert not op.can_integrate("Sort")


# ---------------------------------------------------------------------------
# Where
# ---------------------------------------------------------------------------

class TestWhere:
    def test_deparse_bare(self):
        w = Where(Equality(NamedReference("f"), Integer(5)))
        assert w.deparse() == "where f == 5"

    def test_deparse_with_parameter(self):
        w = Where(
            Equality(NamedReference("f"), Integer(5)),
            params=[OpParameter(NamedReference("kind"), StringLiteral("a"))],
        )
        assert w.deparse() == "where kind='a' f == 5"

    def test_setter_rejects_non_logic(self):
        w = Where(Equality(NamedReference("f"), Integer(5)))
        with pytest.raises(hqle.CompilerException):
            w.expr = NamedReference("x")  # type: ignore[assignment]

    def test_integrate_merges_where(self):
        w1 = Where(Equality(NamedReference("a"), Integer(1)))
        w2 = Where(Equality(NamedReference("b"), Integer(2)))
        assert w1.integrate(w2) is None
        assert isinstance(w1.expr, BinaryLogic)

    def test_integrate_returns_non_where(self):
        w = Where(Equality(NamedReference("a"), Integer(1)))
        other = Count()
        assert w.integrate(other) is other


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------

class TestSort:
    def test_deparse(self):
        s = Sort([OrderedExpression(NamedReference("x"), order="desc")])
        assert s.deparse() == "sort by x desc"

    def test_setter_rejects_non_ordered_expression(self):
        s = Sort([OrderedExpression(NamedReference("x"), order="desc")])
        with pytest.raises(hqle.CompilerException):
            s.exprs = [NamedReference("y")]  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Project + subclasses
# ---------------------------------------------------------------------------

class TestProject:
    def test_project_deparse(self):
        p = Project([NamedReference("a"), NamedReference("b")])
        assert p.deparse() == "project a, b"

    def test_project_eval_returns_all_requested_columns(self):
        from Hql.Context import Context
        from Hql.Data import Data, Table

        ctx = Context(
            data=Data(
                [Table(init_data=[{"a": 1, "b": 2, "c": 3}], name="events")]
            )
        )

        result = Project(
            [NamedReference("a"), NamedReference("b")]
        ).eval(ctx)

        assert result.data["events"].to_dicts() == [{"a": 1, "b": 2}]

    def test_project_keep_deparse(self):
        p = ProjectKeep([NamedReference("a")])
        assert p.deparse() == "project-keep a"

    def test_project_away_deparse(self):
        p = ProjectAway([NamedReference("a")])
        assert p.deparse() == "project-away a"

    def test_project_reorder_deparse(self):
        p = ProjectReorder([NamedReference("a")])
        assert p.deparse() == "project-reorder a"

    def test_project_rename_deparse(self):
        p = ProjectRename([NamedReference("a")])
        assert p.deparse() == "project-rename a"

    def test_empty_deparse(self):
        p = Project([])
        assert p.deparse() == "project"

    def test_setter_rejects_non_expression(self):
        p = Project([NamedReference("a")])
        with pytest.raises(hqle.CompilerException):
            p.exprs = ["not an expression"]  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# Count
# ---------------------------------------------------------------------------

class TestCount:
    def test_deparse_bare(self):
        assert Count().deparse() == "count"

    def test_deparse_with_name(self):
        assert Count(NamedReference("total")).deparse() == "count as total"

    def test_to_dict_includes_name_when_set(self):
        d = Count(NamedReference("total")).to_dict()
        assert d.get("name") == "total"

    def test_to_dict_omits_name_when_unset(self):
        d = Count().to_dict()
        assert "name" not in d


# ---------------------------------------------------------------------------
# Take
# ---------------------------------------------------------------------------

class TestTake:
    def test_deparse_no_tables(self):
        t = Take(Integer(5), [])
        assert t.deparse() == "take 5"

    def test_deparse_with_tables(self):
        t = Take(Integer(5), [NamedReference("a"), NamedReference("b")])
        assert t.deparse() == "take 5 from a, b"

    def test_to_dict_shape(self):
        t = Take(Integer(5), [NamedReference("a")])
        d = t.to_dict()
        assert d["type"] == "Take"
        assert d["limit"]["value"] == 5
        assert len(d["tables"]) == 1


# ---------------------------------------------------------------------------
# Unnest
# ---------------------------------------------------------------------------

class TestUnnest:
    def test_deparse_no_tables(self):
        u = Unnest(NamedReference("field"), [])
        assert u.deparse() == "unnest field"

    def test_deparse_with_tables(self):
        u = Unnest(NamedReference("field"), [NamedReference("t1")])
        assert u.deparse() == "unnest field on t1"

    def test_gets_all_detects_wildcard(self):
        from Hql.Context import Context
        from Hql.Data import Data

        ctx = Context(data=Data())
        assert Unnest(NamedReference("f"), [Wildcard("*")]).gets_all(ctx) is True
        assert Unnest(NamedReference("f"), [NamedReference("t1")]).gets_all(ctx) is False

    def test_eval_expands_and_flattens_multivalue_objects(self):
        from Hql.Context import Context
        from Hql.Data import Data, Table

        table = Table(
            init_data=[
                {
                    "associated_sig_guide_map": {},
                    "tags": [
                        {"id": 1, "name": "first"},
                        {"id": 2, "name": "second"},
                    ],
                },
                {
                    "associated_sig_guide_map": {},
                    "tags": [{"id": 3, "name": "third"}],
                },
                {
                    "associated_sig_guide_map": {},
                    "tags": [],
                },
            ],
            name="events",
        )
        ctx = Context(data=Data([table]))

        result = Unnest(
            NamedReference("tags"), [Wildcard("*")]
        ).eval(ctx)

        assert result.data["events"].to_dicts() == [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
            {"id": 3, "name": "third"},
        ]

    def test_eval_expands_multivalue_scalars_into_typed_column(self):
        from Hql.Context import Context
        from Hql.Data import Data, Table
        from Hql.Types.Hql import HqlTypes as hqlt

        table = Table(
            init_data=[
                {"values": [1, 2]},
                {"values": [3]},
                {"values": []},
            ],
            name="events",
        )
        ctx = Context(data=Data([table]))

        result = Unnest(
            NamedReference("values"), [Wildcard("*")]
        ).eval(ctx)
        result_table = result.data["events"]

        # python ints infer as long
        assert result_table.df.columns == ["long"]
        assert result_table.to_dicts() == [
            {"long": 1},
            {"long": 2},
            {"long": 3},
        ]
        assert isinstance(result_table.schema.schema.schema["long"], hqlt.long)


# ---------------------------------------------------------------------------
# Deepcopy regression — covers every operator in Hql/Operators/
# ---------------------------------------------------------------------------

from copy import deepcopy

from Hql.Expressions.Aggregation import ByExpression
from Hql.Expressions import ToClause
from Hql.Operators.As import As
from Hql.Operators.Datatable import Datatable
from Hql.Operators.Extend import Extend
from Hql.Operators.Join import Join
from Hql.Operators.MvExpand import MvExpand
from Hql.Operators.Range import Range
from Hql.Operators.Rename import Rename
from Hql.Operators.Summarize import Summarize
from Hql.Operators.Template import Template
from Hql.Operators.Top import Top
from Hql.Operators.Union import Union
from Hql.Types.Hql import HqlTypes as hqlt


class TestDeepcopy:
    def test_operator_base(self):
        op = Operator()
        c = deepcopy(op)
        assert c is not op
        assert c.id == op.id
        assert c.tabular == op.tabular

    def test_where(self):
        w = Where(Equality(NamedReference("f"), Integer(5)))
        c = deepcopy(w)
        assert c is not w
        assert c.deparse() == w.deparse()

    def test_where_with_parameters(self):
        w = Where(
            Equality(NamedReference("f"), Integer(5)),
            params=[OpParameter(NamedReference("kind"), StringLiteral("a"))],
        )
        c = deepcopy(w)
        assert c is not w
        assert c.deparse() == w.deparse()

    def test_sort(self):
        s = Sort([OrderedExpression(NamedReference("x"), order="desc")])
        c = deepcopy(s)
        assert c is not s
        assert c.deparse() == s.deparse()

    def test_project(self):
        p = Project([NamedReference("a"), NamedReference("b")])
        c = deepcopy(p)
        assert c is not p
        assert c.deparse() == p.deparse()

    def test_project_keep(self):
        p = ProjectKeep([NamedReference("a")])
        c = deepcopy(p)
        assert c is not p
        assert c.deparse() == p.deparse()

    def test_project_away(self):
        p = ProjectAway([NamedReference("a")])
        c = deepcopy(p)
        assert c is not p
        assert c.deparse() == p.deparse()

    def test_project_reorder(self):
        p = ProjectReorder([NamedReference("a")])
        c = deepcopy(p)
        assert c is not p
        assert c.deparse() == p.deparse()

    def test_project_rename(self):
        p = ProjectRename([NamedReference("a")])
        c = deepcopy(p)
        assert c is not p
        assert c.deparse() == p.deparse()

    def test_count(self):
        cnt = Count(NamedReference("total"))
        c = deepcopy(cnt)
        assert c is not cnt
        assert c.deparse() == cnt.deparse()

    def test_take(self):
        t = Take(Integer(5), [NamedReference("a")])
        c = deepcopy(t)
        assert c is not t
        assert c.deparse() == t.deparse()

    def test_unnest(self):
        u = Unnest(NamedReference("field"), [NamedReference("t1")])
        c = deepcopy(u)
        assert c is not u
        assert c.deparse() == u.deparse()

    def test_as(self):
        a = As(NamedReference("alias"))
        c = deepcopy(a)
        assert c is not a
        assert c.expr == a.expr

    def test_datatable(self):
        dt = Datatable(
            schema=[(NamedReference("a"), hqlt.int())],
            values=[Integer(1), Integer(2)],
        )
        c = deepcopy(dt)
        assert c is not dt
        assert len(c.values) == 2
        assert c.tabular is True

    def test_extend(self):
        e = Extend([NamedReference("a")])
        c = deepcopy(e)
        assert c is not e
        assert list(c.exprs) == list(e.exprs)

    def test_join(self):
        j = Join(
            rh=NamedReference("other_table"),
            on=[NamedReference("id")],
        )
        c = deepcopy(j)
        assert c is not j
        assert c.kind == j.kind

    def test_mv_expand(self):
        mv = MvExpand([ToClause(NamedReference("x"), hqlt.int())])
        c = deepcopy(mv)
        assert c is not mv
        assert len(c.exprs) == 1

    def test_range(self):
        r = Range(
            NamedReference("x"),
            Integer(1),
            Integer(10),
            Integer(2),
        )
        c = deepcopy(r)
        assert c is not r
        assert c.name == r.name
        assert c.tabular is True

    def test_rename(self):
        r = Rename([ToClause(NamedReference("x"), hqlt.int())])
        c = deepcopy(r)
        assert c is not r
        assert len(c.exprs) == 1

    def test_summarize(self):
        s = Summarize(
            aggregate_exprs=[NamedReference("count_")],
            by_expr=ByExpression([NamedReference("g")]),
        )
        c = deepcopy(s)
        assert c is not s
        assert c.deparse() == s.deparse()

    def test_template(self):
        t = Template()
        c = deepcopy(t)
        assert c is not t
        assert c.deparse() == ""

    def test_top(self):
        t = Top(Integer(5), ByExpression([NamedReference("x")]))
        c = deepcopy(t)
        assert c is not t
        assert c.expr.value == 5

    def test_union(self):
        u = Union([NamedReference("a"), NamedReference("b")])
        c = deepcopy(u)
        assert c is not u
        assert c.deparse() == u.deparse()
