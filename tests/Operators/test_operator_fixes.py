import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer
from Hql.Expressions.Logic import Equality
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


# ---------------------------------------------------------------------------
# datatable
# ---------------------------------------------------------------------------

from Hql.Expressions.Literals import StringLiteral, TypeExpression
from Hql.Operators.Datatable import Datatable
from Hql.Types.Hql import HqlTypes as hqlt


def make_datatable(values, name=None):
    schema = [
        (NamedReference("a"), TypeExpression("int")),
        (NamedReference("b"), TypeExpression("string")),
    ]
    return Datatable(schema, values, name=name)


class TestDatatableEval:
    def test_eval_from_type_expressions(self):
        dt = make_datatable(
            [Integer(1), StringLiteral("x"), Integer(2), StringLiteral("y")]
        )

        ctx = dt.eval(make_ctx())
        table = ctx.data["datatable"]

        assert table.to_dicts() == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        assert isinstance(table.schema.schema.schema["a"], hqlt.int)
        assert isinstance(table.schema.schema.schema["b"], hqlt.string)

    def test_eval_with_hql_types_and_name(self):
        dt = Datatable(
            [(NamedReference("a"), hqlt.int())],
            [Integer(1), Integer(2)],
            name=NamedReference("tbl"),
        )

        ctx = dt.eval(make_ctx())

        assert ctx.data["tbl"].to_dicts() == [{"a": 1}, {"a": 2}]

    def test_ragged_values_rejected(self):
        dt = make_datatable([Integer(1), StringLiteral("x"), Integer(2)])
        with pytest.raises(hqle.QueryException):
            dt.eval(make_ctx())

    def test_deparse_uses_type_names(self):
        dt = make_datatable([Integer(1), StringLiteral("x")])
        assert dt.deparse() == "datatable (a: int, b: string)\n[\n    1, 'x'\n]"

    def test_to_dict_includes_schema_and_values(self):
        dt = make_datatable([Integer(1), StringLiteral("x")])
        d = dt.to_dict()

        assert d["id"] == dt.id
        assert d["schema"] == {"a": "int", "b": "string"}
        assert [v["value"] for v in d["values"]] == [1, "x"]


# ---------------------------------------------------------------------------
# top
# ---------------------------------------------------------------------------

from Hql.Expressions.Aggregation import ByExpression, OrderedExpression
from Hql.Operators.Top import Top


def top_values(limit, by, rows=None):
    rows = rows if rows is not None else [{"a": 1}, {"a": 3}, {"a": 2}, {"a": 5}]
    ctx = make_ctx(Table(init_data=rows, name="t"))
    result = Top(Integer(limit), by).eval(ctx)
    return [r["a"] for r in result.data["t"].to_dicts()]


class TestTopEval:
    def test_sorts_desc_before_truncating(self):
        by = OrderedExpression(NamedReference("a"), order="desc")
        assert top_values(2, by) == [5, 3]

    def test_sorts_asc(self):
        by = OrderedExpression(NamedReference("a"), order="asc")
        assert top_values(2, by) == [1, 2]

    def test_nulls_last(self):
        rows = [{"a": 1}, {"a": None}, {"a": 2}]
        by = OrderedExpression(NamedReference("a"), order="asc", nulls="last")
        assert top_values(1, by, rows) == [1]

    def test_accepts_by_expression(self):
        assert top_values(2, ByExpression([NamedReference("a")])) == [5, 3]

    def test_does_not_mutate_input(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}, {"a": 3}], name="t"))
        Top(Integer(1), OrderedExpression(NamedReference("a"))).eval(ctx)
        assert len(ctx.data["t"]) == 2

    def test_to_dict_and_deparse(self):
        t = Top(Integer(2), OrderedExpression(NamedReference("a"), order="asc"))
        assert t.to_dict()["id"] == t.id
        assert t.deparse() == "top 2 by a asc"

    def test_compiles_from_parser(self):
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config
        from Hql.Parser import Parser

        parser = Parser("datatable (a: int) [1, 3, 2] | top 2 by a desc")
        parser.assemble()
        compiler = HqlCompiler(Config(), parser.assembly)
        assert compiler.root is not None
        ops = [x for x in compiler.root.ops if isinstance(x, Top)]
        assert len(ops) == 1
        assert ops[0].expr.value == 2
        assert [(x.expr.deparse(), x.order) for x in ops[0].by] == [("a", "desc")]


# ---------------------------------------------------------------------------
# union
# ---------------------------------------------------------------------------

from Hql.Operators.Union import Union


def union_tables():
    return (
        Table(init_data=[{"a": 1}, {"a": 2}], name="t1"),
        Table(init_data=[{"a": 3}], name="t2"),
        Table(init_data=[{"c": True}], name="t3"),
    )


class TestUnionEval:
    def test_returns_context_and_renames(self):
        ctx = make_ctx(*union_tables())

        result = Union([NamedReference("t1")], name=NamedReference("both")).eval(ctx)

        assert isinstance(result, Context)
        assert sorted(t.name for t in result.data) == ["both", "t2", "t3"]
        assert result.data["both"].to_dicts() == [{"a": 1}, {"a": 2}]
        # Input left alone
        assert "t1" in ctx.data

    def test_no_match_passes_through(self):
        ctx = make_ctx(*union_tables())

        result = Union([NamedReference("nomatch")]).eval(ctx)

        assert sorted(t.name for t in result.data) == ["t1", "t2", "t3"]

    @pytest.mark.skip(reason="needs Table.merge(merge_rows=False) fix (workspace-qgw.3, Hql/Data)")
    def test_merges_multiple_tables(self):
        ctx = make_ctx(*union_tables())

        result = Union(
            [NamedReference("t1"), NamedReference("t2")], name=NamedReference("both")
        ).eval(ctx)

        assert [r["a"] for r in result.data["both"].to_dicts()] == [1, 2, 3]


# ---------------------------------------------------------------------------
# join
# ---------------------------------------------------------------------------

from Hql.Compiler import InstructionSet
from Hql.Database.Static import Static
from Hql.Expressions import OpParameter
from Hql.Expressions.Logic import Equality
from Hql.Expressions.Literals import Bool, Float
from Hql.Operators.Join import Join


class ContextStatic(Static):
    # Static.eval returns Data, wrap it so it can be used as an upstream
    # independent of the Database fix
    def eval(self, ctx, **kwargs):
        ctx = ctx.copy()
        ctx.data = self.data
        return ctx


def right_set():
    right = Data([
        Table(init_data=[
            {"a": 1, "k": "one"},
            {"a": 2, "k": "two"},
            {"a": 5, "k": "five"},
        ], name="u")
    ])
    return InstructionSet(ContextStatic(right))


def make_join(kind="inner", where=None):
    params = [OpParameter(NamedReference("kind"), StringLiteral(kind))]
    return Join(right_set(), [NamedReference("a")], params=params, where=where)


def join_rows(join, left_rows, empty=False):
    table = Table(init_data=left_rows, name="l")
    if empty:
        table.df = table.df.clear()
    ctx = make_ctx(table)
    result = join.eval(ctx)
    return sorted(
        (r for t in result.data for r in t.to_dicts()),
        key=lambda r: (r.get("k") or "", r.get("a") or 0),
    )


LEFT = [{"a": 1, "v": "L1"}, {"a": 3, "v": "L3"}, {"a": 2, "v": "L2"}]


class TestJoinEval:
    def test_inner(self):
        rows = join_rows(make_join("inner"), LEFT)
        assert [(r["a"], r["k"]) for r in rows] == [(1, "one"), (2, "two")]

    def test_null_left_key_does_not_break_pushdown(self):
        rows = join_rows(make_join("inner"), [{"a": 1}, {"a": None}])
        assert [(r["a"], r["k"]) for r in rows] == [(1, "one")]

    def test_rightouter_keeps_unmatched_right(self):
        rows = join_rows(make_join("rightouter"), LEFT)
        assert sorted(r["k"] for r in rows) == ["five", "one", "two"]

    def test_fullouter_keeps_unmatched_right(self):
        rows = join_rows(make_join("fullouter"), LEFT)
        assert "five" in [r["k"] for r in rows]
        assert len(rows) == 4

    def test_rightouter_with_empty_left(self):
        rows = join_rows(make_join("rightouter"), LEFT, empty=True)
        assert sorted(r["k"] for r in rows) == ["five", "one", "two"]

    def test_inner_with_empty_left_short_circuits(self):
        assert join_rows(make_join("inner"), LEFT, empty=True) == []

    def test_repeated_eval_does_not_accumulate_filters(self):
        join = make_join("inner")

        first = join_rows(join, [{"a": 1}])
        second = join_rows(join, [{"a": 2}])

        assert [r["k"] for r in first] == ["one"]
        assert [r["k"] for r in second] == ["two"]
        assert join.rh.ops == []

    def test_where_prefilters_right(self):
        where = Equality(NamedReference("k"), StringLiteral("two"))
        rows = join_rows(make_join("inner", where=where), LEFT)
        assert [(r["a"], r["k"]) for r in rows] == [(2, "two")]

    def test_gen_optimization_literals(self):
        join = Join(NamedReference("r"), [NamedReference("a")])

        expr = join.gen_optimization(
            Data([Table(init_data=[{"a": True}, {"a": None}], name="t")])
        )

        assert expr is not None
        assert expr.deparse() == "a == True"

    def test_gen_optimization_all_null_is_none(self):
        join = Join(NamedReference("r"), [NamedReference("a")])
        data = Data([Table(init_data=[{"a": 1}], name="t")])
        data["t"].df = data["t"].df.clear()

        assert join.gen_optimization(data) is None


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

from Hql.Functions.count import count
from Hql.Operators.Summarize import Summarize


class TestSummarizeEval:
    def test_without_by_aggregates_whole_table(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}, {"a": 2}, {"a": 2}], name="t"))

        result = Summarize([count([])], None).eval(ctx)

        assert result.data["t"].to_dicts() == [{"count_": 3}]
        # Input left alone
        assert "__hql_summarize_all__" not in ctx.data["t"].df.columns

    def test_without_by_per_table(self):
        ctx = make_ctx(
            Table(init_data=[{"a": 1}], name="l"),
            Table(init_data=[{"a": 1}, {"a": 2}], name="u"),
        )

        result = Summarize([count([])], None).eval(ctx)

        assert result.data["l"].to_dicts() == [{"count_": 1}]
        assert result.data["u"].to_dicts() == [{"count_": 2}]

    def test_with_by_still_groups(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}, {"a": 2}, {"a": 2}], name="t"))

        result = Summarize([count([])], ByExpression([NamedReference("a")])).eval(ctx)

        assert result.data["t"].to_dicts() == [
            {"a": 1, "count_": 1},
            {"a": 2, "count_": 2},
        ]

    def test_compiles_without_by(self):
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config
        from Hql.Parser import Parser

        parser = Parser("datatable (a: int) [1, 2] | summarize count()")
        parser.assemble()
        compiler = HqlCompiler(Config(), parser.assembly)

        ops = [x for x in compiler.root.ops if isinstance(x, Summarize)]
        assert len(ops) == 1
        assert ops[0].by_expr is None


# ---------------------------------------------------------------------------
# mv-expand
# ---------------------------------------------------------------------------

from Hql.Expressions import ToClause
from Hql.Operators.MvExpand import MvExpand


def to_clause(ref, to=None):
    # ToClause's `to` is being made optional on another branch, build it
    # with a type and clear it so these tests don't depend on that
    clause = ToClause(ref, hqlt.int())
    clause.to = to
    return clause


MV_ROWS = [
    {"a": 1, "c": [1, 2, 3]},
    {"a": 2, "c": []},
    {"a": 3, "c": None},
    {"a": 4, "c": [9]},
]


class TestMvExpandEval:
    def test_expands_rows(self):
        ctx = make_ctx(Table(init_data=MV_ROWS, name="t"))

        result = MvExpand([to_clause(NamedReference("c"))]).eval(ctx)
        table = result.data["t"]

        assert [(r["a"], r["c"]) for r in table.to_dicts()] == [
            (1, 1), (1, 2), (1, 3), (2, None), (3, None), (4, 9),
        ]
        assert isinstance(table.schema.schema.schema["c"], hqlt.long)

    def test_limit(self):
        ctx = make_ctx(Table(init_data=MV_ROWS, name="t"))

        result = MvExpand([to_clause(NamedReference("c"))], limit=Integer(1)).eval(ctx)

        assert [r["c"] for r in result.data["t"].to_dicts()] == [1, None, None, 9]

    def test_to_type_casts(self):
        ctx = make_ctx(Table(init_data=[{"c": [1, 2]}], name="t"))

        result = MvExpand([to_clause(NamedReference("c"), hqlt.string())]).eval(ctx)
        table = result.data["t"]

        assert table.to_dicts() == [{"c": "1"}, {"c": "2"}]
        assert isinstance(table.schema.schema.schema["c"], hqlt.string)

    def test_nested_path(self):
        ctx = make_ctx(Table(init_data=[{"n": {"c": [1, 2], "x": "p"}}], name="t"))
        path = Path([NamedReference("n"), NamedReference("c")])

        result = MvExpand([to_clause(path)]).eval(ctx)

        assert result.data["t"].to_dicts() == [
            {"n": {"c": 1, "x": "p"}},
            {"n": {"c": 2, "x": "p"}},
        ]

    def test_does_not_mutate_input_schema(self):
        table = Table(init_data=MV_ROWS, name="t")
        ctx = make_ctx(table)

        MvExpand([to_clause(NamedReference("c"))]).eval(ctx)

        assert isinstance(table.schema.schema.schema["c"], hqlt.multivalue)
        assert len(table) == 4

    def test_skips_tables_missing_field(self):
        ctx = make_ctx(
            Table(init_data=MV_ROWS, name="t"),
            Table(init_data=[{"b": 1}], name="u"),
        )

        result = MvExpand([to_clause(NamedReference("c"))]).eval(ctx)

        assert len(result.data["t"]) == 6
        assert result.data["u"].to_dicts() == [{"b": 1}]

    def test_deparse(self):
        mv = MvExpand([to_clause(NamedReference("c"), hqlt.int())], limit=Integer(2))
        assert mv.deparse() == "mvexpand c to int limit 2"
        assert MvExpand([to_clause(NamedReference("c"))]).deparse() == "mvexpand c"

    def test_compiler_accepts_missing_to(self):
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config

        acc, _ = HqlCompiler(Config()).compile(to_clause(NamedReference("c")))

        assert acc.get_expr().to is None


# ---------------------------------------------------------------------------
# rename / push
# ---------------------------------------------------------------------------

from Hql.Operators.Push import Push
from Hql.Operators.Rename import Rename


def table_rename(src, dst):
    clause = ToClause(NamedReference(src), hqlt.int())
    clause.to = NamedReference(dst)
    return clause


class TestRenameEval:
    def test_renames_table_and_returns_context(self):
        ctx = make_ctx(
            Table(init_data=[{"a": 1}], name="l"),
            Table(init_data=[{"a": 2}], name="u"),
        )

        result = Rename([table_rename("u", "q")]).eval(ctx)

        assert isinstance(result, Context)
        assert sorted(t.name for t in result.data) == ["l", "q"]
        assert result.data["q"].name == "q"
        assert result.data["q"].to_dicts() == [{"a": 2}]
        # Input left alone
        assert sorted(t.name for t in ctx.data) == ["l", "u"]
        assert ctx.data["u"].name == "u"

    def test_missing_table_is_ignored(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}], name="l"))

        result = Rename([table_rename("nope", "q")]).eval(ctx)

        assert [t.name for t in result.data] == ["l"]

    def test_deparse(self):
        r = Rename([table_rename("u", "q"), table_rename("l", "m")])
        assert r.deparse() == "rename u to q, l to m"


class TestPush:
    def test_deparse(self):
        p = Push([NamedReference("a"), NamedReference("b")])
        assert p.deparse() == "push a, b"

    def test_eval_returns_context(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}], name="t"))
        assert Push([NamedReference("a")]).eval(ctx) is ctx


# ---------------------------------------------------------------------------
# where / unnest on partial schemas, and copy isolation
# ---------------------------------------------------------------------------

from Hql.Operators.Sort import Sort
from Hql.Operators.Take import Take
from Hql.Operators.Unnest import Unnest
from Hql.Operators.Where import Where
from Hql.Expressions.References import Wildcard


class TestWhereMissingField:
    def test_missing_struct_subfield_drops_table(self):
        ctx = make_ctx(Table(init_data=[{"n": {"x": 1}}], name="t"))
        expr = Equality(Path([NamedReference("n"), NamedReference("zz")]), Integer(1))

        result = Where(expr).eval(ctx)

        assert "t" not in result.data

    def test_existing_struct_subfield_filters(self):
        ctx = make_ctx(Table(init_data=[{"n": {"x": 1}}, {"n": {"x": 2}}], name="t"))
        expr = Equality(Path([NamedReference("n"), NamedReference("x")]), Integer(1))

        result = Where(expr).eval(ctx)

        assert result.data["t"].to_dicts() == [{"n": {"x": 1}}]


class TestUnnestPartial:
    def test_skips_tables_missing_field(self):
        ctx = make_ctx(
            Table(init_data=[{"a": 1}], name="l"),
            Table(init_data=[{"n": {"x": 1, "y": "p"}}], name="t"),
        )

        result = Unnest(NamedReference("n"), [Wildcard("*")]).eval(ctx)

        assert result.data["l"].to_dicts() == [{"a": 1}]
        assert result.data["t"].to_dicts() == [{"x": 1, "y": "p"}]


class TestCopyIsolation:
    def make(self):
        return make_ctx(Table(init_data=[{"a": 1}, {"a": 3}, {"a": 2}], name="t"))

    def test_take(self):
        c1 = self.make()
        c2 = c1.copy()

        Take(Integer(1), []).eval(c2)

        assert len(c1.data["t"]) == 3

    def test_take_negative_rejected(self):
        with pytest.raises(hqle.QueryException):
            Take(Integer(-1), []).eval(self.make())

    def test_sort(self):
        c1 = self.make()

        Sort([OrderedExpression(NamedReference("a"))]).eval(c1.copy())

        assert [r["a"] for r in c1.data["t"].to_dicts()] == [1, 3, 2]

    def test_where(self):
        c1 = self.make()

        Where(Equality(NamedReference("a"), Integer(1))).eval(c1.copy())

        assert len(c1.data["t"]) == 3

    def test_unnest(self):
        c1 = make_ctx(Table(init_data=[{"n": {"x": 1, "y": "p"}}], name="t"))

        Unnest(NamedReference("n"), [Wildcard("*")]).eval(c1.copy())

        assert c1.data["t"].to_dicts() == [{"n": {"x": 1, "y": "p"}}]


# ---------------------------------------------------------------------------
# project literal broadcast / count over nothing
# ---------------------------------------------------------------------------

from Hql.Operators.Count import Count
from Hql.Operators.Project import Project


class TestProjectLiteral:
    def test_literal_only_broadcasts(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}, {"a": 2}, {"a": 3}], name="t"))

        result = Project([NamedExpression([NamedReference("d")], Integer(1))]).eval(ctx)

        assert result.data["t"].to_dicts() == [{"d": 1}] * 3

    def test_literal_on_empty_table_is_empty(self):
        table = Table(init_data=[{"a": 1}], name="t")
        table.df = table.df.clear()

        result = Project([NamedExpression([NamedReference("d")], Integer(1))]).eval(make_ctx(table))

        assert len(result.data["t"]) == 0

    def test_mixed_still_matches_rows(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}, {"a": 2}], name="t"))

        result = Project(
            [NamedReference("a"), NamedExpression([NamedReference("d")], Integer(1))]
        ).eval(ctx)

        assert result.data["t"].to_dicts() == [{"a": 1, "d": 1}, {"a": 2, "d": 1}]


class TestCountEmpty:
    def test_no_tables_counts_zero(self):
        result = Count().eval(make_ctx())

        assert [t.to_dicts() for t in result.data] == [[{"Count": 0}]]

    def test_named_with_no_tables(self):
        result = Count(NamedReference("c")).eval(make_ctx())

        assert result.data["c"].to_dicts() == []
        assert result.data["c"].df.columns == ["Table", "Count"]

    def test_named_does_not_mutate_input(self):
        ctx = make_ctx(Table(init_data=[{"a": 1}], name="t"))

        result = Count(NamedReference("c")).eval(ctx)

        assert result.data["c"].to_dicts() == [{"Table": "t", "Count": 1}]
        assert "c" not in ctx.data
