import pytest

from Hql.Config import Config
from Hql.Exceptions import HqlExceptions as hqle


class TestConfigInit:
    def test_default_has_expected_sections(self):
        c = Config()
        assert set(c.conf.keys()) >= {
            "general",
            "databases",
            "products",
            "categories",
            "functions",
            "sigma",
        }
        assert c.conf["sigma"] == {"header": "", "posthql": {}}


class TestAddDatabase:
    def test_adds_valid_config(self):
        c = Config()
        c.add_database("src.yaml", {"name": "db1", "type": "es", "conf": {}})
        assert c.is_database("db1")
        assert c.get_database("db1")["type"] == "es"

    def test_missing_required_key_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.add_database("src.yaml", {"name": "db1", "type": "es"})

    def test_duplicate_raises(self):
        c = Config()
        c.add_database("src.yaml", {"name": "db1", "type": "es", "conf": {}})
        with pytest.raises(hqle.ConfigException):
            c.add_database("src.yaml", {"name": "db1", "type": "es", "conf": {}})

    def test_get_unknown_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.get_database("nope")


class TestLoadGeneral:
    def test_stores_first_call(self):
        c = Config()
        c.load_general("src.yaml", {"default_db": "es"})
        assert c.conf["general"]["default_db"] == "es"

    def test_second_call_raises(self):
        c = Config()
        c.load_general("src.yaml", {"default_db": "es"})
        with pytest.raises(hqle.ConfigException):
            c.load_general("src.yaml", {"default_db": "es"})


class TestGetDefaultDb:
    def test_missing_default_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.get_default_db()

    def test_returns_referenced_db(self):
        c = Config()
        c.add_database("src.yaml", {"name": "primary", "type": "es", "conf": {}})
        c.load_general("src.yaml", {"default_db": "primary"})
        assert c.get_default_db()["name"] == "primary"


class TestLoadProduct:
    def test_missing_hql_and_upstream_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.load_product({"name": "p1"}, "src.yaml")

    def test_hql_promoted_to_upstream(self):
        c = Config()
        c.load_product({"name": "p1", "hql": "myquery"}, "src.yaml")
        assert c.conf["products"]["p1"]["upstream"] == ["myquery"]

    def test_unconfigured_skipped(self):
        c = Config()
        c.load_product({"name": "p1", "configured": False}, "src.yaml")
        assert "p1" not in c.conf["products"]


class TestLoadFunction:
    def test_stores_valid(self):
        c = Config()
        c.load_function("src.yaml", {"name": "toupper", "conf": {"opt": True}})
        assert c.get_function("toupper") == {"opt": True}

    def test_get_function_default_empty(self):
        c = Config()
        assert c.get_function("nope") == {}

    def test_missing_required_key_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.load_function("src.yaml", {"name": "toupper"})


class TestGetPosthql:
    def test_unknown_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.get_posthql("nope")


class TestSigmaHeader:
    def test_default_empty(self):
        assert Config().get_sigma_header() == ""

    def test_loads_header(self):
        c = Config()
        c.load_sigma("src.yaml", {"header": "import maps.windows"})
        assert c.get_sigma_header() == "import maps.windows"

    def test_duplicate_raises(self):
        c = Config()
        c.load_sigma("a.yaml", {"header": "import maps.windows"})
        with pytest.raises(hqle.ConfigException):
            c.load_sigma("b.yaml", {"header": "import maps.linux"})


class TestGetProduct:
    def test_unknown_raises(self):
        c = Config()
        with pytest.raises(hqle.ConfigException):
            c.get_product("nope")


class TestGetEngine:
    def test_default_empty(self):
        assert Config().get_engine() == {}


class TestGetImportPaths:
    def test_empty_without_path(self):
        assert Config().get_import_paths() == []

    def test_directory(self, tmp_path):
        assert Config(tmp_path).get_import_paths() == [tmp_path]

    def test_file_uses_its_directory(self, tmp_path):
        conf = tmp_path / "general.yml"
        conf.write_text("type: general\n")
        assert Config(conf).get_import_paths() == [tmp_path]
