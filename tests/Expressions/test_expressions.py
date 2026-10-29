from Hql.Expressions import OpParameter, ToClause
from Hql.Expressions.Literals import Integer, TypeExpression
from Hql.Expressions.References import NamedReference
from Hql.Types.Hql import HqlTypes as hqlt


# ---------------------------------------------------------------------------
# OpParameter
# ---------------------------------------------------------------------------

class TestOpParameter:
    def test_deparse(self):
        op = OpParameter(NamedReference("limit"), Integer(10))
        assert op.deparse() == "limit=10"


# ---------------------------------------------------------------------------
# ToClause
# ---------------------------------------------------------------------------

class TestToClause:
    def test_stores_hql_type_from_type_expression(self):
        tc = ToClause(NamedReference("x"), TypeExpression(hqlt.int()))
        assert isinstance(tc.to, hqlt.int)

    def test_stores_hql_type_directly(self):
        tc = ToClause(NamedReference("x"), hqlt.int())
        assert isinstance(tc.to, hqlt.int)

    def test_deparse(self):
        tc = ToClause(NamedReference("x"), hqlt.int())
        assert tc.deparse() == "x to int"

    def test_to_defaults_to_none(self):
        tc = ToClause(NamedReference("x"))
        assert tc.to is None

    def test_deparse_without_to(self):
        assert ToClause(NamedReference("x")).deparse() == "x"

    def test_to_dict_without_to(self):
        assert ToClause(NamedReference("x")).to_dict()["to"] is None

    def test_eval_without_to_leaves_data(self, empty_ctx):
        import polars as pl
        from Hql.Data import Data, Table

        empty_ctx.data = Data([Table(df=pl.DataFrame({"x": [1, 2]}), name="t")])
        out = ToClause(NamedReference("x")).eval(empty_ctx)
        assert out.data["t"].to_dicts() == [{"x": 1}, {"x": 2}]


# ---------------------------------------------------------------------------
# Deepcopy regression
# ---------------------------------------------------------------------------

class TestDeepcopy:
    def test_op_parameter(self):
        from copy import deepcopy
        op = OpParameter(NamedReference("limit"), Integer(10))
        c = deepcopy(op)
        assert c is not op
        assert c.deparse() == op.deparse()

    def test_to_clause(self):
        from copy import deepcopy
        tc = ToClause(NamedReference("x"), hqlt.int())
        c = deepcopy(tc)
        assert c is not tc
        assert c.deparse() == tc.deparse()
