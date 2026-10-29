import polars as pl
import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Expressions import ToClause
from Hql.Expressions.Arithmetic import BinaryArithmetic, Negate
from Hql.Expressions.Literals import Float, Integer
from Hql.Expressions.References import NamedReference, Wildcard
from Hql.Operators.Extend import Extend
from Hql.Operators.MvExpand import MvExpand
from Hql.Operators.Take import Take
from Hql.Operators.Union import Union
from Hql.Operators.Where import Where
from Hql.Parser import Parser


def parse(text):
    parser = Parser(text)
    parser.assemble()
    return parser.assembly


def root(text):
    return parse(text).statements[0].root


def first_pipe(text):
    return root(text).pipes[0]


def roundtrip(text):
    return root(text).deparse().replace("\n", " ")


def table():
    return Data([Table(df=pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}), name="t")])


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_multiplication_keeps_left_operand(self):
        value = first_pipe("t | extend d = a * 2").exprs[0].value
        assert value == BinaryArithmetic(NamedReference("a"), "*", Integer(2))

    @pytest.mark.parametrize("text", [
        "t | extend d=a * 2",
        "t | where a + 1 > 3",
        "t | extend d=a - b + c * 2 / 4 % 3",
        "t | extend d=a - (b - c)",
        "t | extend d=(a + 1) * 2",
        "t | extend d=-(a + 1)",
        "t | extend d=a.b * 2",
    ])
    def test_deparse_roundtrip(self, text):
        assert roundtrip(text) == text

    def test_precedence(self):
        # a + b * 2 -> a + (b * 2)
        value = first_pipe("t | extend d = a + b * 2").exprs[0].value
        assert value.op == "+"
        assert value.rh == BinaryArithmetic(NamedReference("b"), "*", Integer(2))

    def test_left_associative(self):
        # a - b - c -> (a - b) - c
        value = first_pipe("t | extend d = a - b - c").exprs[0].value
        assert value.lh == BinaryArithmetic(NamedReference("a"), "-", NamedReference("b"))
        assert value.rh == NamedReference("c")

    def test_parens_group_without_subquery(self):
        value = first_pipe("t | extend d = (a + 1) * 2").exprs[0].value
        assert value.lh == BinaryArithmetic(NamedReference("a"), "+", Integer(1))

    def test_where_relational_keeps_arithmetic(self):
        expr = first_pipe("t | where a + 1 > 3").expr
        assert expr.lh == BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        assert expr.rh == [Integer(3)]

    def test_parenthesized_subquery_still_pipe(self):
        assert roundtrip("t | join (u | take 1) on x") == "t | join (u | take 1) on x"

    def test_extend_evaluates(self):
        op = first_pipe("t | extend d = a * 2, e = a + b, f = -a")
        assert isinstance(op, Extend)
        rows = op.eval(Context(table())).data["t"].to_dicts()
        assert [x["d"] for x in rows] == [2, 4, 6]
        assert [x["e"] for x in rows] == [5, 7, 9]
        assert [x["f"] for x in rows] == [-1, -2, -3]

    def test_where_evaluates(self):
        op = first_pipe("t | where a + 1 > 3")
        assert isinstance(op, Where)
        rows = op.eval(Context(table())).data["t"].to_dicts()
        assert rows == [{"a": 3, "b": 6}]


# ---------------------------------------------------------------------------
# Unary operators
# ---------------------------------------------------------------------------

class TestUnary:
    def test_take_negative_literal(self):
        op = first_pipe("t | take -1")
        assert isinstance(op, Take)
        assert op.expr == Integer(-1)

    def test_negative_float_literal(self):
        assert first_pipe("t | where a > -1.5").expr.rh == [Float(-1.5)]

    def test_negate_reference(self):
        assert first_pipe("t | extend d = -a").exprs[0].value == Negate(NamedReference("a"))

    def test_unary_plus_is_identity(self):
        assert first_pipe("t | extend d = +a").exprs[0].value == NamedReference("a")


# ---------------------------------------------------------------------------
# mv-expand
# ---------------------------------------------------------------------------

class TestMvExpand:
    def test_parses_without_to(self):
        op = first_pipe("t | mv-expand a")
        assert isinstance(op, MvExpand)
        assert isinstance(op.exprs[0], ToClause)
        assert op.exprs[0].expr == NamedReference("a")
        assert op.exprs[0].to is None

    def test_parses_with_to(self):
        op = first_pipe("t | mv-expand a to string")
        assert op.exprs[0].to.name == "string"


# ---------------------------------------------------------------------------
# Wildcards
# ---------------------------------------------------------------------------

class TestWildcard:
    def test_union_wildcard_name(self):
        union = root("union u*").prepipe
        assert isinstance(union, Union)
        assert isinstance(union.exprs[0], Wildcard)
        assert union.exprs[0].name == "u*"

    def test_union_wildcard_and_name(self):
        assert roundtrip("union u*, v") == "union u*, v"


# ---------------------------------------------------------------------------
# Static database, as produced for let-bound datatables/ranges
# ---------------------------------------------------------------------------

class TestStatic:
    def test_eval_returns_context(self):
        from Hql.Database import Static

        data = table()
        out = Static(data).eval(Context(Data()))
        assert isinstance(out, Context)
        assert out.data is data

    def test_compiled_query_over_static_runs(self):
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config
        from Hql.Database import Static

        compiler = HqlCompiler(Config())
        compiler.ctx.symbol_table[NamedReference("t")] = Static(table())
        compiler.Query(parse("t | take 1"))

        result = compiler.run().data
        assert result["t"].to_dicts() == [{"a": 1, "b": 4}]
