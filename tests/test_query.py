from Hql.Expressions import PipeExpression
from Hql.Expressions.References import NamedReference, Path
from Hql.Query import ClassStatement, ImportStatement, LetStatement, Mapping, Query, QueryStatement, Statement


class TestStatement:
    def test_default_deparse_is_empty(self):
        assert Statement().deparse() == ""

    def test_type_marker(self):
        assert Statement().type == "Statement"


class TestQueryStatement:
    def test_deparse_delegates_to_root(self):
        root = PipeExpression([])
        qs = QueryStatement(root)
        assert qs.deparse() == root.deparse()

    def test_to_dict_includes_query(self):
        qs = QueryStatement(PipeExpression([]))
        d = qs.to_dict()
        assert d["type"] == "QueryStatement"
        assert "query" in d


class TestLetStatement:
    def test_deparse(self):
        ls = LetStatement(NamedReference("x"), PipeExpression([]))
        assert ls.deparse() == "let x = "

    def test_to_dict_shape(self):
        ls = LetStatement(NamedReference("x"), PipeExpression([]))
        d = ls.to_dict()
        assert d["type"] == "LetStatement"


class TestQuery:
    def test_stores_statements(self):
        s = QueryStatement(PipeExpression([]))
        q = Query([s])
        assert q.statements == [s]

    def test_to_dict_shape(self):
        q = Query([QueryStatement(PipeExpression([]))])
        d = q.to_dict()
        assert "statements" in d
        assert len(d["statements"]) == 1

    def test_deparse_single_statement(self):
        q = Query([QueryStatement(PipeExpression([]))])
        # No let statements, no context, so just the one deparse
        assert q.deparse() == ""


def ecs():
    mapping = Mapping(NamedReference("ecs"))
    mapping.add(NamedReference("EventID"), Path([NamedReference("event"), NamedReference("id")]))
    mapping.add(NamedReference("Host"), [NamedReference("hostname"), Path([NamedReference("host"), NamedReference("name")])])
    return mapping


class TestMapping:
    def test_type_marker(self):
        assert ecs().type == "Mapping"

    def test_iterates_sources(self):
        assert list(ecs()) == [NamedReference("EventID"), NamedReference("Host")]

    def test_add_ignores_duplicates(self):
        mapping = ecs()
        mapping.add(NamedReference("Host"), NamedReference("hostname"))
        assert mapping[NamedReference("Host")] == [
            NamedReference("hostname"),
            Path([NamedReference("host"), NamedReference("name")]),
        ]

    def test_get_returns_copy(self):
        mapping = ecs()
        mapping.get(NamedReference("EventID")).append(NamedReference("x"))
        assert len(mapping[NamedReference("EventID")]) == 1

    def test_merge(self):
        other = Mapping(NamedReference("other"))
        other.add(NamedReference("EventID"), NamedReference("event_id"))
        other.add(NamedReference("User"), NamedReference("user"))

        mapping = ecs().merge(other)
        assert mapping[NamedReference("EventID")] == [
            Path([NamedReference("event"), NamedReference("id")]),
            NamedReference("event_id"),
        ]
        assert NamedReference("User") in mapping

    def test_to_dict_shape(self):
        assert ecs().to_dict() == {
            "type": "Mapping",
            "name": "ecs",
            "maps": {"EventID": ["event.id"], "Host": ["hostname", "host.name"]},
        }

    def test_deparse(self):
        assert ecs().deparse() == "map ecs = { EventID: event.id, Host: (hostname, host.name) }"

    def test_query_deparse_includes_mapping(self):
        q = Query([ecs(), QueryStatement(PipeExpression([]))])
        assert q.deparse().startswith("map ecs = {")


class TestImportStatement:
    def test_type_marker(self):
        assert ImportStatement(NamedReference("common")).type == "ImportStatement"

    def test_parts_simple(self):
        name = Path([NamedReference("lib"), NamedReference("common")])
        assert ImportStatement(name).parts == ["lib", "common"]

    def test_parts_from(self):
        statement = ImportStatement(NamedReference("common"), src=Path([NamedReference("a"), NamedReference("lib")]))
        assert statement.parts == ["a", "lib", "common"]

    def test_deparse_simple(self):
        name = Path([NamedReference("lib"), NamedReference("common")])
        assert ImportStatement(name).deparse() == "import lib.common"

    def test_deparse_from(self):
        statement = ImportStatement(NamedReference("common"), src=NamedReference("lib"))
        assert statement.deparse() == "from lib import common"

    def test_to_dict_includes_statements(self):
        let = LetStatement(NamedReference("x"), PipeExpression([]))
        d = ImportStatement(NamedReference("common"), statements=[let], path="/lib/common.hql").to_dict()
        assert d["type"] == "ImportStatement"
        assert d["path"] == "/lib/common.hql"
        assert d["src"] is None
        assert len(d["statements"]) == 1


class TestClassStatement:
    def test_to_dict_includes_body(self):
        body = Query([LetStatement(NamedReference("x"), PipeExpression([]))])
        d = ClassStatement(NamedReference("c"), body).to_dict()
        assert d["type"] == "ClassStatement"
        assert d["name"] == {"type": "NamedReference", "name": "c"}
        assert len(d["value"]["statements"]) == 1

    def test_deparse(self):
        body = Query([LetStatement(NamedReference("x"), PipeExpression([]))])
        assert ClassStatement(NamedReference("c"), body).deparse() == "class c = {\nlet x = \n}"
