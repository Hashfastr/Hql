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


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

class TestMapping:
    def test_map_statement(self):
        from Hql.Query import Mapping

        statements = parse("map ecs = { EventID: event.id, Host: (host.name, hostname) }; t | take 1").statements
        mapping = statements[0]

        assert isinstance(mapping, Mapping)
        assert mapping.to_dict() == {
            "type": "Mapping",
            "name": "ecs",
            "maps": {"EventID": ["event.id"], "Host": ["host.name", "hostname"]},
        }

    def test_map_statement_roundtrip(self):
        text = "map ecs = { EventID: event.id, Host: (host.name, hostname) }"
        assert parse(f"{text}; t").statements[0].deparse() == text

    def test_map_operator(self):
        from Hql.Operators.Map import Map
        from Hql.Parser.grammar.HqlParser import HqlParser

        if not hasattr(HqlParser, "MapOperatorContext"):
            pytest.skip("Generated parser predates the map operator, regenerate from Hql.g4")

        op = first_pipe("t | map ecs, other")
        assert isinstance(op, Map)
        assert op.names == [NamedReference("ecs"), NamedReference("other")]
        assert op.deparse() == "map ecs, other"



# ---------------------------------------------------------------------------
# Imports, inline the statements of another file in place
# ---------------------------------------------------------------------------

class TestImport:
    @pytest.fixture
    def lib(self, tmp_path):
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "common.hql").write_text("let f = 't.json';\nmap ecs = { EventID: event.id }")
        (tmp_path / "outer.hql").write_text("import lib.common;\nlet n = 2")
        return tmp_path

    def parse_in(self, directory, text):
        parser = Parser(text, filename=str(directory / "main.hql"))
        parser.assemble()
        return parser.assembly

    def test_statements_inlined_in_place(self, lib):
        from Hql.Query import LetStatement, Mapping, QueryStatement

        statements = self.parse_in(lib, "let a = 1; import lib.common; t").statements

        assert [type(x) for x in statements] == [LetStatement, LetStatement, Mapping, QueryStatement]
        assert statements[1].name == NamedReference("f")
        assert statements[2].name == NamedReference("ecs")

    def test_from_import(self, lib):
        statements = self.parse_in(lib, "from lib import common; t").statements
        assert [x.name for x in statements[:-1]] == [NamedReference("f"), NamedReference("ecs")]

    def test_nested_imports_resolve_from_the_imported_file(self, lib):
        statements = self.parse_in(lib, "import outer; t").statements
        assert [x.name for x in statements[:-1]] == [NamedReference("f"), NamedReference("ecs"), NamedReference("n")]

    def test_deparse_has_imported_statements(self, lib):
        assert self.parse_in(lib, "import lib.common; t").deparse() == (
            "let f = 't.json';\nmap ecs = { EventID: event.id };\nt"
        )

    def test_falls_back_to_working_directory(self, lib, monkeypatch):
        monkeypatch.chdir(lib)
        statements = parse("import lib.common; t").statements
        assert len(statements) == 3

    def test_resolves_against_given_paths(self, lib, tmp_path_factory):
        # As with the api, the query has no file to resolve relative to
        parser = Parser("import lib.common; t", filename="api", paths=[lib])
        parser.assemble()
        assert [x.name for x in parser.assembly.statements[:-1]] == [NamedReference("f"), NamedReference("ecs")]

    def test_nested_imports_keep_given_paths(self, lib, tmp_path_factory):
        other = tmp_path_factory.mktemp("other")
        (other / "outer.hql").write_text("import lib.common")

        parser = Parser("import outer; t", filename="api", paths=[other, lib])
        parser.assemble()
        assert len(parser.assembly.statements) == 3

    def test_importing_file_directory_wins_over_paths(self, lib, tmp_path_factory):
        other = tmp_path_factory.mktemp("other")
        (other / "lib").mkdir()
        (other / "lib" / "common.hql").write_text("let g = 1")

        parser = Parser("import lib.common; t", filename=str(lib / "main.hql"), paths=[other])
        parser.assemble()
        assert parser.assembly.statements[0].name == NamedReference("f")

    def test_missing_file_raises(self, lib, caplog):
        from Hql.Exceptions import HqlExceptions as hqle

        with pytest.raises(hqle.CompilerException):
            self.parse_in(lib, "import missing; t")
        assert "Could not find missing.hql" in caplog.text

    def test_circular_import_raises(self, tmp_path, caplog):
        from Hql.Exceptions import HqlExceptions as hqle

        (tmp_path / "a.hql").write_text("import b")
        (tmp_path / "b.hql").write_text("import a")

        with pytest.raises(hqle.CompilerException):
            self.parse_in(tmp_path, "import a; t")
        assert "Circular import" in caplog.text

    def test_query_statement_in_import_raises(self, tmp_path, caplog):
        from Hql.Exceptions import HqlExceptions as hqle

        (tmp_path / "q.hql").write_text("t | take 1")

        with pytest.raises(hqle.CompilerException):
            self.parse_in(tmp_path, "import q; t")
        assert "has a query statement" in caplog.text



# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class TestClass:
    def test_class_statement(self):
        from Hql.Query import ClassStatement, LetStatement

        statements = parse("class c = { let a = 1; let b = t | take 1; }; c.b").statements
        cls = statements[0]

        assert isinstance(cls, ClassStatement)
        assert cls.name == NamedReference("c")
        assert [type(x) for x in cls.root.statements] == [LetStatement, LetStatement]
        assert [x.name for x in cls.root.statements] == [NamedReference("a"), NamedReference("b")]

    def test_nested_class(self):
        from Hql.Query import ClassStatement

        inner = parse("class a = { class b = { let x = 1 } }; t").statements[0].root.statements[0]
        assert isinstance(inner, ClassStatement)
        assert inner.name == NamedReference("b")

    def test_trailing_input_is_rejected(self):
        from Hql.Exceptions import HqlExceptions as hqle
        with pytest.raises(hqle.CompilerException):
            parse("t | take 1 ) garbage")
