import polars as pl
import pytest

from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Arithmetic import BinaryArithmetic, Negate
from Hql.Expressions.Literals import Float, Integer, Null
from Hql.Expressions.Logic import Relational
from Hql.Expressions.References import NamedReference


def frame():
    return pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})


def values(expr):
    return frame().select(expr.polars().alias("out"))["out"].to_list()


# ---------------------------------------------------------------------------
# BinaryArithmetic
# ---------------------------------------------------------------------------

class TestBinaryArithmetic:
    def test_invalid_operator_rejected(self):
        with pytest.raises(hqle.CompilerException):
            BinaryArithmetic(NamedReference("a"), "^", Integer(2))

    @pytest.mark.parametrize("op, expected", [
        ("+", [3, 4, 5]),
        ("-", [-1, 0, 1]),
        ("*", [2, 4, 6]),
        ("/", [0.5, 1.0, 1.5]),
        ("%", [1, 0, 1]),
    ])
    def test_polars_with_literal(self, op, expected):
        expr = BinaryArithmetic(NamedReference("a"), op, Integer(2))
        assert values(expr) == expected

    def test_polars_rejects_non_expression_operand(self):
        expr = BinaryArithmetic(object(), "*", Integer(2))
        with pytest.raises(hqle.QueryException):
            expr.polars()

    def test_polars_two_columns(self):
        expr = BinaryArithmetic(NamedReference("a"), "*", NamedReference("b"))
        assert values(expr) == [4, 10, 18]

    def test_polars_nested(self):
        # (a + 1) * b
        inner = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        expr = BinaryArithmetic(inner, "*", NamedReference("b"))
        assert values(expr) == [8, 15, 24]

    def test_deparse(self):
        expr = BinaryArithmetic(NamedReference("a"), "*", Integer(2))
        assert expr.deparse() == "a * 2"

    def test_deparse_parenthesizes_lower_precedence(self):
        inner = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        assert BinaryArithmetic(inner, "*", Integer(2)).deparse() == "(a + 1) * 2"

    def test_deparse_omits_needless_parens(self):
        inner = BinaryArithmetic(NamedReference("a"), "*", Integer(2))
        assert BinaryArithmetic(inner, "+", Integer(1)).deparse() == "a * 2 + 1"

    def test_deparse_parenthesizes_right_associative_group(self):
        inner = BinaryArithmetic(NamedReference("b"), "-", NamedReference("c"))
        assert BinaryArithmetic(NamedReference("a"), "-", inner).deparse() == "a - (b - c)"

    def test_to_dict(self):
        d = BinaryArithmetic(NamedReference("a"), "+", Integer(1)).to_dict()
        assert d["type"] == "BinaryArithmetic"
        assert d["op"] == "+"
        assert d["lh"] == {"type": "NamedReference", "name": "a"}
        assert d["rh"] == {"type": "Integer", "value": 1}

    def test_equality_and_hash(self):
        x = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        y = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        assert x == y
        assert hash(x) == hash(y)
        assert x != BinaryArithmetic(NamedReference("a"), "-", Integer(1))

    def test_preprocess_folds_integer_literals(self, empty_ctx):
        expr = BinaryArithmetic(Integer(2), "*", Integer(3)).preprocess(empty_ctx)
        assert expr == Integer(6)

    def test_preprocess_folds_float_literals(self, empty_ctx):
        expr = BinaryArithmetic(Integer(7), "/", Integer(2)).preprocess(empty_ctx)
        assert expr == Float(3.5)

    def test_preprocess_folds_division_by_zero_to_null(self, empty_ctx):
        expr = BinaryArithmetic(Integer(7), "%", Integer(0)).preprocess(empty_ctx)
        assert isinstance(expr, Null)

    def test_preprocess_keeps_references(self, empty_ctx):
        expr = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        assert expr.preprocess(empty_ctx) == expr

    def test_preprocess_resolves_symbols(self, empty_ctx):
        empty_ctx.symbol_table["n"] = Integer(4)
        expr = BinaryArithmetic(NamedReference("n"), "-", Integer(1))
        assert expr.preprocess(empty_ctx) == Integer(3)

    def test_eval_returns_series_per_table(self, empty_ctx):
        empty_ctx.data = Data([Table(df=frame(), name="t")])
        out = BinaryArithmetic(NamedReference("a"), "*", Integer(2)).eval(empty_ctx)
        assert out.data["t"].series.series.to_list() == [2, 4, 6]

    def test_eval_drops_tables_missing_field(self, empty_ctx):
        empty_ctx.data = Data([
            Table(df=frame(), name="t"),
            Table(df=pl.DataFrame({"z": [1]}), name="u"),
        ])
        out = BinaryArithmetic(NamedReference("a"), "+", Integer(1)).eval(empty_ctx)
        assert "t" in out.data
        assert "u" not in out.data


# ---------------------------------------------------------------------------
# Negate
# ---------------------------------------------------------------------------

class TestNegate:
    def test_polars(self):
        assert values(Negate(NamedReference("a"))) == [-1, -2, -3]

    def test_deparse(self):
        assert Negate(NamedReference("a")).deparse() == "-a"

    def test_deparse_parenthesizes_binary(self):
        inner = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        assert Negate(inner).deparse() == "-(a + 1)"

    def test_preprocess_folds_literal(self, empty_ctx):
        assert Negate(Integer(5)).preprocess(empty_ctx) == Integer(-5)


# ---------------------------------------------------------------------------
# Comparators over arithmetic
# ---------------------------------------------------------------------------

class TestRelationalArithmetic:
    def test_filters_on_arithmetic(self):
        lh = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        rel = Relational(lh, Integer(3), gt=True, eq=False)
        assert frame().filter(rel.polars())["a"].to_list() == [3]

    def test_preprocess_keeps_arithmetic_lh(self, empty_ctx):
        lh = BinaryArithmetic(NamedReference("a"), "+", Integer(1))
        rel = Relational(lh, Integer(3), gt=True, eq=False).preprocess(empty_ctx)
        assert rel.deparse() == "a + 1 > 3"

    def test_preprocess_swaps_literal_lh(self, empty_ctx):
        rh = BinaryArithmetic(NamedReference("a"), "*", Integer(1))
        rel = Relational(Integer(3), rh, gt=False, eq=False).preprocess(empty_ctx)
        assert rel.deparse() == "a * 1 > 3"
