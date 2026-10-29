import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer
from Hql.Expressions.References import NamedExpression, NamedReference, Path
from Hql.Operators.Project import ProjectRename


def make_ctx(*tables: Table) -> Context:
    return Context(data=Data(list(tables)))


def rename_expr(dest: str, src: str) -> NamedExpression:
    return NamedExpression([NamedReference(dest)], NamedReference(src))


# ---------------------------------------------------------------------------
# project-rename
# ---------------------------------------------------------------------------

class TestProjectRenameEval:
    def test_renames_field(self):
        ctx = make_ctx(Table(init_data=[{"a": 1, "b": 2}], name="t"))

        result = ProjectRename([rename_expr("z", "a")]).eval(ctx)

        assert result.data["t"].to_dicts() == [{"z": 1, "b": 2}]

    def test_accepts_bare_reference(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}], name="t"))

        result = ProjectRename([NamedReference("a")]).eval(ctx)

        assert result.data["t"].to_dicts() == [{"a": 1}]

    def test_rejects_non_reference_value(self):
        with pytest.raises(hqle.CompilerException):
            ProjectRename([NamedExpression([NamedReference("z")], Integer(1))])

    def test_swap(self):
        ctx = make_ctx(Table(init_data=[{"a": 1, "b": 2}], name="t"))

        result = ProjectRename(
            [rename_expr("a", "b"), rename_expr("b", "a")]
        ).eval(ctx)

        assert result.data["t"].to_dicts()[0] == {"a": 2, "b": 1}

    def test_nested_value_keeps_schema(self):
        ctx = make_ctx(
            Table(init_data=[{"n": {"x": 1, "y": "p"}, "a": 1}], name="t")
        )

        result = ProjectRename([rename_expr("m", "n")]).eval(ctx)
        table = result.data["t"]

        assert table.to_dicts() == [{"m": {"x": 1, "y": "p"}, "a": 1}]
        assert table.assert_field(Path([NamedReference("m"), NamedReference("x")]))

    def test_skips_tables_missing_field(self):
        ctx = make_ctx(
            Table(init_data=[{"a": 1, "v": "L1"}], name="l"),
            Table(init_data=[{"a": 2, "k": "two"}], name="u"),
        )

        result = ProjectRename([rename_expr("q", "k")]).eval(ctx)

        assert result.data["l"].to_dicts() == [{"a": 1, "v": "L1"}]
        assert result.data["u"].to_dicts() == [{"q": "two", "a": 2}]

    def test_does_not_mutate_input(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}], name="t"))

        ProjectRename([rename_expr("z", "a")]).eval(ctx)

        assert ctx.data["t"].to_dicts() == [{"a": 1}]


# ---------------------------------------------------------------------------
# range
# ---------------------------------------------------------------------------

from Hql.Expressions.Literals import Float
from Hql.Operators.Range import Range


def run_range(start, end, step):
    ctx = Range(NamedReference("x"), start, end, step).eval(make_ctx())
    assert isinstance(ctx, Context)
    return ctx.data["range"].df["x"].to_list()


class TestRangeEval:
    def test_inclusive_int(self):
        assert run_range(Integer(1), Integer(5), Integer(1)) == [1, 2, 3, 4, 5]

    def test_step_not_landing_on_end(self):
        assert run_range(Integer(1), Integer(10), Integer(3)) == [1, 4, 7, 10]
        assert run_range(Integer(1), Integer(9), Integer(3)) == [1, 4, 7]

    def test_start_after_end_is_empty(self):
        assert run_range(Integer(5), Integer(1), Integer(1)) == []

    def test_negative_step(self):
        assert run_range(Integer(5), Integer(1), Integer(-2)) == [5, 3, 1]

    def test_float_step_includes_end(self):
        values = run_range(Integer(0), Integer(1), Float(0.1))
        assert len(values) == 11
        assert values[-1] == pytest.approx(1.0)

    def test_zero_step_rejected(self):
        with pytest.raises(hqle.QueryException):
            run_range(Integer(1), Integer(5), Integer(0))

    def test_non_numeric_rejected(self):
        with pytest.raises(hqle.CompilerException):
            run_range(NamedReference("a"), Integer(5), Integer(1))

    def test_to_dict_and_deparse(self):
        r = Range(NamedReference("x"), Integer(1), Integer(5), Integer(2))
        assert r.to_dict()["id"] == r.id
        assert r.deparse() == "range x from 1 to 5 step 2"
