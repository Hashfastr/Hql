import pytest

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Bool, Integer, StringLiteral
from Hql.Expressions.Logic import (
    BasicRange,
    BetweenEquality,
    BinaryLogic,
    Equality,
    Logic,
    Not,
    Regex,
    Relational,
    Substring,
)
from Hql.Expressions.References import NamedReference


# ---------------------------------------------------------------------------
# Equality
# ---------------------------------------------------------------------------

class TestEquality:
    def test_build_op_single_default(self):
        eq = Equality(NamedReference("f"), Integer(5))
        assert eq.build_op() == "=="

    def test_build_op_single_case_insensitive(self):
        eq = Equality(NamedReference("f"), StringLiteral("x"), cs=False)
        assert eq.build_op() == "=~"

    def test_build_op_single_negated(self):
        eq = Equality(NamedReference("f"), Integer(5), neq=True)
        assert eq.build_op() == "!="

    def test_build_op_list(self):
        eq = Equality(NamedReference("f"), [Integer(1), Integer(2)])
        assert eq.build_op() == "in"

    def test_build_op_list_negated_case_insensitive(self):
        eq = Equality(
            NamedReference("f"),
            [StringLiteral("a"), StringLiteral("b")],
            cs=False,
            neq=True,
        )
        assert eq.build_op() == "!in~"

    def test_deparse_single(self):
        eq = Equality(NamedReference("f"), Integer(5))
        assert eq.deparse() == "f == 5"

    def test_deparse_list(self):
        eq = Equality(NamedReference("f"), [Integer(1), Integer(2)])
        assert eq.deparse() == "f in (1, 2)"

    def test_coerce_rh_wraps_single_expression(self):
        eq = Equality(NamedReference("f"), Integer(5))
        assert len(eq.rh) == 1


# ---------------------------------------------------------------------------
# Substring
# ---------------------------------------------------------------------------

class TestSubstring:
    def test_build_op_contains_default(self):
        s = Substring(NamedReference("f"), [StringLiteral("x")])
        assert s.build_op() == "contains"

    def test_build_op_has_term(self):
        s = Substring(NamedReference("f"), [StringLiteral("x")], term=True)
        assert s.build_op() == "has"

    def test_build_op_startswith_case_sensitive(self):
        s = Substring(NamedReference("f"), [StringLiteral("x")], startswith=True, cs=True)
        assert s.build_op() == "startswith_cs"

    def test_build_op_endswith_negated(self):
        s = Substring(NamedReference("f"), [StringLiteral("x")], endswith=True, neq=True)
        assert s.build_op() == "!endswith"

    def test_build_op_list_all(self):
        s = Substring(
            NamedReference("f"),
            [StringLiteral("a"), StringLiteral("b")],
            logic_and=True,
        )
        assert s.build_op() == "contains_all"

    def test_build_op_list_any_case_sensitive(self):
        s = Substring(
            NamedReference("f"),
            [StringLiteral("a"), StringLiteral("b")],
            logic_and=False,
            cs=True,
        )
        assert s.build_op() == "contains_any_cs"

    def test_deparse_single(self):
        s = Substring(NamedReference("f"), [StringLiteral("x")])
        assert s.deparse() == "f contains 'x'"

    def test_deparse_list(self):
        s = Substring(
            NamedReference("f"),
            [StringLiteral("a"), StringLiteral("b")],
            logic_and=True,
        )
        assert s.deparse() == "f contains_all ('a', 'b')"

    def test_equality_same(self):
        left = Substring(NamedReference("f"), [StringLiteral("x")])
        right = Substring(NamedReference("f"), [StringLiteral("x")])
        assert left == right

    def test_equality_different_flag(self):
        left = Substring(NamedReference("f"), [StringLiteral("x")], term=True)
        right = Substring(NamedReference("f"), [StringLiteral("x")], term=False)
        assert left != right


# ---------------------------------------------------------------------------
# Relational
# ---------------------------------------------------------------------------

class TestRelational:
    def test_build_op_gt(self):
        r = Relational(NamedReference("f"), Integer(5), gt=True, eq=False)
        assert r.build_op() == ">"

    def test_build_op_lte(self):
        r = Relational(NamedReference("f"), Integer(5), gt=False, eq=True)
        assert r.build_op() == "<="

    def test_deparse(self):
        r = Relational(NamedReference("f"), Integer(5), gt=True, eq=True)
        assert r.deparse() == "f >= 5"

    @pytest.mark.parametrize("gt, eq, expected", [
        (True, False, "f < 5"),   # 5 > f
        (True, True, "f <= 5"),   # 5 >= f
        (False, False, "f > 5"),  # 5 < f
        (False, True, "f >= 5"),  # 5 <= f
    ])
    def test_preprocess_swap_keeps_inclusivity(self, empty_ctx, gt, eq, expected):
        r = Relational(Integer(5), NamedReference("f"), gt=gt, eq=eq)
        assert r.preprocess(empty_ctx).deparse() == expected


# ---------------------------------------------------------------------------
# BetweenEquality
# ---------------------------------------------------------------------------

class TestBetweenEquality:
    def test_deparse_default(self):
        b = BetweenEquality(NamedReference("f"), Integer(1), Integer(10))
        assert b.deparse() == "f between (1 .. 10)"

    def test_deparse_negated(self):
        b = BetweenEquality(NamedReference("f"), Integer(1), Integer(10), neq=True)
        assert b.deparse() == "f !between (1 .. 10)"


# ---------------------------------------------------------------------------
# BasicRange
# ---------------------------------------------------------------------------

class TestBasicRange:
    def test_deparse(self):
        r = BasicRange(Integer(1), Integer(5))
        assert r.deparse() == "(1 .. 5)"


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

class TestRegex:
    def test_deparse(self):
        r = Regex(NamedReference("f"), StringLiteral("^foo$"))
        assert r.deparse() == "f matches regex '^foo$'"


# ---------------------------------------------------------------------------
# Not
# ---------------------------------------------------------------------------

class TestNot:
    def test_deparse_wraps_expression(self):
        assert Not(NamedReference("x")).deparse() == "not(x)"


# ---------------------------------------------------------------------------
# BinaryLogic
# ---------------------------------------------------------------------------

class TestBinaryLogic:
    def test_empty_raises(self):
        with pytest.raises(hqle.CompilerException):
            BinaryLogic([], logic_and=True)

    def test_single_expression_collapses(self):
        eq = Equality(NamedReference("f"), Integer(5))
        result = BinaryLogic([eq], logic_and=True)
        assert result is eq

    def test_or_with_true_short_circuits_to_true(self):
        eq = Equality(NamedReference("f"), Integer(5))
        result = BinaryLogic([eq, Bool(True)], logic_and=False)
        assert result == Bool(True)

    def test_and_with_false_short_circuits_to_false(self):
        eq = Equality(NamedReference("f"), Integer(5))
        result = BinaryLogic([eq, Bool(False)], logic_and=True)
        assert result == Bool(False)

    def test_deparse_and(self):
        left = Equality(NamedReference("a"), Integer(1))
        right = Equality(NamedReference("b"), Integer(2))
        bl = BinaryLogic([left, right], logic_and=True)
        parts = set(bl.deparse().split(" and "))
        assert parts == {"a == 1", "b == 2"}

    def test_deparse_or(self):
        left = Equality(NamedReference("a"), Integer(1))
        right = Equality(NamedReference("b"), Integer(2))
        bl = BinaryLogic([left, right], logic_and=False)
        parts = set(bl.deparse().split(" or "))
        assert parts == {"a == 1", "b == 2"}

    def test_build_op(self):
        left = Equality(NamedReference("a"), Integer(1))
        right = Equality(NamedReference("b"), Integer(2))
        assert BinaryLogic([left, right], logic_and=True).build_op() == "and"
        assert BinaryLogic([left, right], logic_and=False).build_op() == "or"

    def test_iterable(self):
        left = Equality(NamedReference("a"), Integer(1))
        right = Equality(NamedReference("b"), Integer(2))
        bl = BinaryLogic([left, right], logic_and=True)
        assert len(bl) == 2
        assert set(bl) == {left, right}


# ---------------------------------------------------------------------------
# Logic base
# ---------------------------------------------------------------------------

class TestLogic:
    def test_reduce_returns_self_by_default(self):
        base = Logic()
        assert base.reduce() is base


# ---------------------------------------------------------------------------
# Deepcopy regression
# ---------------------------------------------------------------------------

class TestDeepcopy:
    def test_equality(self):
        from copy import deepcopy
        eq = Equality(NamedReference("f"), Integer(5))
        c = deepcopy(eq)
        assert c is not eq
        assert c.deparse() == eq.deparse()

    def test_substring(self):
        from copy import deepcopy
        s = Substring(NamedReference("f"), [StringLiteral("x")])
        c = deepcopy(s)
        assert c is not s
        assert c.deparse() == s.deparse()

    def test_relational(self):
        from copy import deepcopy
        r = Relational(NamedReference("f"), Integer(5), gt=True, eq=False)
        c = deepcopy(r)
        assert c is not r
        assert c.deparse() == r.deparse()

    def test_between_equality(self):
        from copy import deepcopy
        b = BetweenEquality(NamedReference("f"), Integer(1), Integer(10))
        c = deepcopy(b)
        assert c is not b
        assert c.deparse() == b.deparse()

    def test_basic_range(self):
        from copy import deepcopy
        r = BasicRange(Integer(1), Integer(5))
        c = deepcopy(r)
        assert c is not r
        assert c.deparse() == r.deparse()

    def test_regex(self):
        from copy import deepcopy
        r = Regex(NamedReference("f"), StringLiteral("^foo$"))
        c = deepcopy(r)
        assert c is not r
        assert c.deparse() == r.deparse()

    def test_not(self):
        from copy import deepcopy
        n = Not(NamedReference("x"))
        c = deepcopy(n)
        assert c is not n
        assert c.deparse() == n.deparse()

    def test_binary_logic(self):
        from copy import deepcopy
        left = Equality(NamedReference("a"), Integer(1))
        right = Equality(NamedReference("b"), Integer(2))
        bl = BinaryLogic([left, right], logic_and=True)
        c = deepcopy(bl)
        assert c is not bl
        # deparse order may differ (set-based storage) — just check it's a valid BinaryLogic
        assert isinstance(c, BinaryLogic)
        assert len(c) == 2
