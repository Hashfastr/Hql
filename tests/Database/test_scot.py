from __future__ import annotations

import copy
import datetime
import threading
import time
from pathlib import Path

import pytest
import requests

from Hql.Config import Config
from Hql.Compiler import HqlCompiler
from Hql.Context import Context, get_database
from Hql.Data import Data
from Hql.Database import SCOT
from Hql.Cache import Session as CacheSession
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Expressions.References import NamedExpression, NamedReference
from Hql.Functions.database import database
from Hql.Functions.typecasting import todatetime
from Hql.Operators.Extend import Extend
from Hql.Operators.Take import Take
from Hql.Parser import Parser
from Hql.Database.SCOT.SCOTCatalog import EXCLUDED_RESOURCES, SCOT_ENDPOINTS
from Hql.Database.SCOT.SCOT import (
    DEFAULT_MAX_ROWS,
    DEFAULT_PAGE_SIZE,
    DEFAULT_REQUESTS_PER_SECOND,
    DEFAULT_TIMEOUT,
)


SCOT_EXAMPLE = (
    Path(__file__).parents[2] / "conf.example" / "dbs" / "scot" / "conf.yml"
)


def scot_config(**overrides):
    conf = {
        "base_url": "https://scot.example.test/",
        "api_key": "super-secret-test-key",
    }
    conf.update(overrides)
    return {"name": "scot-test", "type": "SCOT", "conf": conf}


def test_example_config_loads_and_matches_constructor_defaults():
    config = Config()
    config.load_file(SCOT_EXAMPLE)
    documented = config.get_database("scot")

    assert documented["type"] == "SCOT"
    assert documented["conf"] == {
        "base_url": "https://scot.example.invalid",
        "api_key": "<INJECT_SCOT_API_KEY>",
        "verify_tls": True,
        "timeout": DEFAULT_TIMEOUT,
        "requests_per_second": DEFAULT_REQUESTS_PER_SECOND,
        "page_size": DEFAULT_PAGE_SIZE,
        "max_rows": DEFAULT_MAX_ROWS,
    }

    configured = copy.deepcopy(documented)
    configured["conf"]["api_key"] = "injected-at-test-runtime"
    adapter = SCOT(configured, session=NoNetworkSession())
    assert adapter.name == "unnamed-scot"


def test_example_config_contains_guidance_but_no_usable_secret():
    example = SCOT_EXAMPLE.read_text(encoding="utf-8")

    assert "database('scot').entity" in example
    assert "<INJECT_SCOT_API_KEY>" in example
    assert "secret manager" in example


class NoNetworkSession:
    def request(self, *args, **kwargs):
        raise AssertionError("SCOT construction must not make a network request")


class FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error=None):
        self.payload = payload
        self.status_code = status_code
        self.json_error = json_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class FakeCacheSession(CacheSession):
    def __init__(self, response):
        super().__init__()
        self.response = response

    def get(self, url, **kwargs):
        return self.response


def test_scot_is_registered_and_resolves_through_database_function():
    config = Config()
    config.set_database("scot-test", scot_config())
    ctx = Context(Data(), config=config)

    resolved = database([StringLiteral("scot-test")]).eval(ctx)

    assert get_database("SCOT") is SCOT
    assert isinstance(resolved, SCOT)
    assert resolved.name == "scot-test"


def test_valid_config_is_normalized_without_network_access():
    adapter = SCOT(
        scot_config(
            base_url="HTTPS://scot.example.test/root///",
            verify_tls=False,
            timeout=2,
            page_size=25,
            max_rows=250,
        ),
        name="scot-test",
        session=NoNetworkSession(),
    )

    assert adapter.base_url == "https://scot.example.test/root"
    assert adapter.verify_tls is False
    assert adapter.timeout == 2.0
    assert adapter.page_size == 25
    assert adapter.max_rows == 250
    assert adapter.endpoint is None
    assert adapter.methods == ["index", "macro"]


def test_safe_defaults():
    adapter = SCOT(scot_config())

    assert adapter.verify_tls is True
    assert adapter.timeout == 10.0
    assert adapter.requests_per_second == 10.0
    assert adapter.page_size == 100
    assert adapter.max_rows == 10_000


@pytest.mark.parametrize("key", ["base_url", "api_key"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_values(key, value):
    with pytest.raises(hqle.ConfigException, match=key):
        SCOT(scot_config(**{key: value}))


@pytest.mark.parametrize(
    ("base_url", "message"),
    [
        ("scot.example.test", "HTTP"),
        ("ftp://scot.example.test", "HTTP"),
        ("https:///missing-host", "HTTP"),
        ("https://user:password@scot.example.test", "credentials"),
        ("https://scot.example.test?token=secret", "query string"),
        ("https://scot.example.test/#fragment", "fragment"),
    ],
)
def test_invalid_base_urls(base_url, message):
    with pytest.raises(hqle.ConfigException, match=message):
        SCOT(scot_config(base_url=base_url))


@pytest.mark.parametrize("key", ["page_size", "max_rows", "requests_per_second"])
@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "10"])
def test_invalid_integer_limits(key, value):
    with pytest.raises(hqle.ConfigException, match=key):
        SCOT(scot_config(**{key: value}))


@pytest.mark.parametrize("key", ["timeout"])
@pytest.mark.parametrize("value", [True, 0, -1, float("inf"), "10"])
def test_invalid_positive_number(key, value):
    with pytest.raises(hqle.ConfigException, match=key):
        SCOT(scot_config(**{key: value}))


def test_page_size_cannot_exceed_max_rows():
    with pytest.raises(hqle.ConfigException, match="page_size"):
        SCOT(scot_config(page_size=101, max_rows=100))


def test_verify_tls_must_be_boolean():
    with pytest.raises(hqle.ConfigException, match="verify_tls"):
        SCOT(scot_config(verify_tls="false"))


def test_secret_is_absent_from_serialization_and_repr():
    secret = "do-not-leak-this-key"
    adapter = SCOT(scot_config(api_key=secret))

    assert secret not in str(adapter.to_dict())
    assert secret not in repr(adapter)
    assert "api_key" not in adapter.to_dict()


def test_selected_adapter_can_be_deepcopied():
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse({})))
    adapter.add_index("alert")
    ctx = Context(Data(), symbol_table={"selected": adapter})

    copied = ctx.copy().symbol_table["selected"]

    assert copied is not adapter
    assert copied.endpoint is adapter.endpoint
    assert copied.compiler.endpoint is adapter.compiler.endpoint


def test_authenticated_request_uses_normalized_url_and_settings():
    session = FakeSession(FakeResponse({"result": [{"id": 1}]}))
    adapter = SCOT(
        scot_config(timeout=3, verify_tls=False),
        session=session,
    )

    result = adapter._request_json(
        "/api/v1/entity/", {"value": "example.com", "limit": 5}
    )

    assert result == {"result": [{"id": 1}]}
    assert session.calls == [
        (
            "https://scot.example.test/api/v1/entity/",
            {
                "headers": {"Authorization": "apikey super-secret-test-key"},
                "params": {"value": "example.com", "limit": 5},
                "timeout": 3.0,
                "verify": False,
            },
        )
    ]


def test_requests_are_limited_to_ten_per_second(monkeypatch):
    clock = [100.0]
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        clock[0] += delay

    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(time, "sleep", sleep)
    adapter = SCOT(
        scot_config(requests_per_second=10),
        session=FakeSession(FakeResponse({"result": []})),
    )

    for _ in range(11):
        adapter._request_json("/api/v1/entity/")

    assert sleeps == pytest.approx([1.0])


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (requests.Timeout("secret transport detail"), "timed out"),
        (requests.ConnectionError("secret transport detail"), "failed to connect"),
    ],
)
def test_transport_failures_are_sanitized(error, message):
    secret = "secret transport detail"
    adapter = SCOT(scot_config(api_key=secret), session=FakeSession(error=error))

    with pytest.raises(hqle.QueryException, match=message) as caught:
        adapter._request_json("/api/v1/entity/")

    assert secret not in str(caught.value)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 503])
def test_http_failures_include_status_but_not_response_body(status):
    secret = "sensitive response body"
    adapter = SCOT(
        scot_config(),
        session=FakeSession(FakeResponse(status_code=status, payload=secret)),
    )

    with pytest.raises(hqle.QueryException, match=f"HTTP {status}") as caught:
        adapter._request_json("/api/v1/entity/")

    assert secret not in str(caught.value)


def test_malformed_json_is_reported_without_parser_details():
    adapter = SCOT(
        scot_config(),
        session=FakeSession(FakeResponse(json_error=ValueError("secret body"))),
    )

    with pytest.raises(hqle.QueryException, match="malformed JSON") as caught:
        adapter._request_json("/api/v1/entity/")

    assert "secret body" not in str(caught.value)


@pytest.mark.parametrize(
    "path",
    ["https://attacker.test/api/v1/entity/", "/api/v1/../apikey/", "/health"],
)
def test_request_rejects_paths_outside_scot_api(path):
    session = FakeSession(FakeResponse({}))
    adapter = SCOT(scot_config(), session=session)

    with pytest.raises(hqle.QueryException, match="Invalid SCOT API path"):
        adapter._request_json(path)

    assert session.calls == []


@pytest.mark.parametrize("endpoint", SCOT_ENDPOINTS, ids=lambda endpoint: endpoint.name)
def test_each_catalog_table_selects_and_dispatches_to_its_path(endpoint):
    session = FakeSession(FakeResponse({"result": []}))
    adapter = SCOT(scot_config(), session=session)

    assert adapter.get_variable(NamedReference(endpoint.name)) is adapter
    assert adapter.endpoint is endpoint
    assert adapter.compiler.endpoint is endpoint
    assert adapter._fetch_selected() == {"result": []}
    assert session.calls[0][0].endswith(endpoint.path)


@pytest.mark.parametrize(
    "name", sorted(EXCLUDED_RESOURCES | {"unknown", "entity/export", "file/download/1"})
)
def test_unknown_and_excluded_tables_fail_without_network(name):
    session = FakeSession(FakeResponse({}))
    adapter = SCOT(scot_config(), session=session)

    with pytest.raises(hqle.QueryException, match="Unknown or unavailable"):
        adapter.get_variable(NamedReference(name))

    assert session.calls == []


def test_selected_table_is_immutable():
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse({})))
    adapter.get_variable(NamedReference("entity"))

    with pytest.raises(hqle.QueryException, match="already selected"):
        adapter.get_variable(NamedReference("entry"))


def test_add_index_uses_the_same_catalog_validation():
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse({})))
    adapter.add_index("entity")
    assert adapter.endpoint is not None
    assert adapter.endpoint.name == "entity"

    with pytest.raises(hqle.QueryException, match="Unknown or unavailable"):
        SCOT(scot_config()).add_index("users")


def test_selected_dispatch_uses_shared_request_helper(monkeypatch):
    adapter = SCOT(scot_config())
    adapter.add_index("entity")
    calls = []

    def fake_request(path, params):
        calls.append((path, params))
        return {"result": []}

    monkeypatch.setattr(adapter, "_request_json", fake_request)

    assert adapter._fetch_selected() == {"result": []}
    assert calls == [("/api/v1/entity/", {"limit": 10_000})]


def test_dispatch_requires_a_selected_table():
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse({})))
    with pytest.raises(hqle.QueryException, match="No SCOT table selected"):
        adapter._fetch_selected()


def test_alertgroup_take_is_sent_as_api_limit():
    session = FakeSession(FakeResponse({"result": []}))
    adapter = SCOT(scot_config(max_rows=500), session=session)
    adapter.add_index("alertgroup")

    accepted, rejected = adapter.add_op(Take(Integer(20), []))
    adapter._fetch_selected()

    assert accepted is not None
    assert rejected is None
    assert session.calls[0][1]["params"] == {"limit": 20}


def test_alertgroup_result_supports_datetime_extend():
    session = FakeSession(
        FakeResponse(
            {
                "result": [
                    {
                        "id": 42,
                        "created": "2026-08-31T12:34:56Z",
                        "subject": "Example alertgroup",
                    }
                ]
            }
        )
    )
    adapter = SCOT(scot_config(), session=session)
    adapter.add_index("alertgroup")
    ctx = adapter.eval(Context(Data()))
    extend = Extend(
        [
            NamedExpression(
                [NamedReference("TimeGenerated")],
                todatetime([NamedReference("created")]),
            )
        ]
    )

    result = extend.eval(ctx).data["alertgroup"].to_dicts()

    assert len(result) == 1
    assert result[0]["id"] == 42
    assert result[0]["created"] == "2026-08-31T12:34:56Z"
    assert result[0]["subject"] == "Example alertgroup"
    assert isinstance(result[0]["TimeGenerated"], datetime.datetime)


def test_alertgroup_to_alert_join_without_where_clause(monkeypatch):
    subject = (
        "New App Role Assigned to a Service Principal by a User involving "
        "multiple users"
    )

    class RoutingSession:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if "/alertgroup/" in url:
                return FakeResponse({"result": [{"id": 7, "subject": subject}]})
            if "/alert/" in url:
                return FakeResponse(
                    {
                        "result": [
                            {"id": 99, "alertgroup_id": 7, "owner": "alice"}
                        ]
                    }
                )
            raise AssertionError(f"Unexpected SCOT URL: {url}")

    session = RoutingSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    config = Config()
    config.set_database("scot", scot_config())
    parser = Parser(
        "let Alert = database('scot').index('alert');\n"
        "let Alertgroup = database('scot').index('alertgroup');\n"
        "let Alerts = Alertgroup\n"
        f"| where subject == '{subject}'\n"
        "| take 10\n"
        "| project alertgroup_id = id\n"
        "| join Alert on alertgroup_id\n"
        ";\n"
        "Alerts"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert result["alertgroup"].to_dicts() == [
        {"alertgroup_id": 7, "owner": "alice", "id": 99}
    ]
    assert [(url, call["params"]) for url, call in session.calls] == [
        (
            "https://scot.example.test/api/v1/alertgroup/",
            {"limit": 10, "subject": subject},
        ),
        (
            "https://scot.example.test/api/v1/alert/",
            {"alertgroup_id": "7", "limit": 10_000},
        ),
    ]


def test_alert_entity_macro_uses_id_as_path_and_filters_results_locally(
    monkeypatch,
):
    session = FakeSession(
        FakeResponse(
            {
                "result": [
                    {"id": 41, "value": "keep"},
                    {"id": 42, "value": "drop"},
                ]
            }
        )
    )
    monkeypatch.setattr(requests, "Session", lambda: session)
    config = Config()
    config.set_database("scot", scot_config())
    parser = Parser(
        "let Entities = database('scot').index('alert').macro('entity');\n"
        "Entities\n"
        "| where id == 1 and value == 'keep'"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert result["entity"].to_dicts() == [
        {"id": 1, "entity_id": 41, "value": "keep"}
    ]
    assert session.calls == [
        (
            "https://scot.example.test/api/v1/alert/1/entity",
            {
                "headers": {"Authorization": "apikey super-secret-test-key"},
                "params": {},
                "timeout": 10.0,
                "verify": True,
            },
        )
    ]


def test_alert_entity_macro_without_id_returns_empty_without_request(monkeypatch):
    session = FakeSession(FakeResponse({"result": [{"id": 41}]}))
    monkeypatch.setattr(requests, "Session", lambda: session)
    config = Config()
    config.set_database("scot", scot_config())
    parser = Parser(
        "let Entities = database('scot').index('alert').macro('entity');\n"
        "Entities"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert list(result.tables) == ["entity"]
    assert len(result["entity"]) == 0
    assert session.calls == []


def test_alert_entity_macro_returns_all_entities_for_alert(monkeypatch):
    alert_id = 42853281
    session = FakeSession(
        FakeResponse(
            {
                "result": [
                    {"id": 71, "value": "one"},
                    {"id": 72, "value": "two"},
                ]
            }
        )
    )
    monkeypatch.setattr(requests, "Session", lambda: session)
    config = Config()
    config.set_database("scot", scot_config())
    parser = Parser(
        "let Entities = database('scot').index('alert').macro('entity');\n"
        "Entities\n"
        f"| where id == {alert_id}"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert result["entity"].to_dicts() == [
        {"id": alert_id, "entity_id": 71, "value": "one"},
        {"id": alert_id, "entity_id": 72, "value": "two"},
    ]


def test_alert_entity_macro_fans_out_join_ids(monkeypatch):
    alert_ids = list(range(1, 11)) + [5]

    class RoutingSession:
        def __init__(self):
            self.calls = []
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()
            self.entity_requests_ready = threading.Barrier(10)

        def __deepcopy__(self, _memo):
            return self

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if url.endswith("/api/v1/alert/"):
                return FakeResponse(
                    {"result": [{"id": alert_id} for alert_id in alert_ids]}
                )
            if url.endswith("/entity"):
                alert_id = int(url.rsplit("/", 2)[-2])
                with self.lock:
                    self.active += 1
                    self.max_active = max(self.max_active, self.active)
                self.entity_requests_ready.wait(timeout=2)
                with self.lock:
                    self.active -= 1
                return FakeResponse(
                    {
                        "result": [
                            {
                                "id": alert_id + 1_000,
                                "value": f"entity-{alert_id}",
                                "status": "tracked",
                                "type_name": "domain",
                            }
                        ]
                    }
                )
            raise AssertionError(f"Unexpected SCOT URL: {url}")

    session = RoutingSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    config = Config()
    config.set_database("scot", scot_config())
    parser = Parser(
        "let Alerts = database('scot').index('alert');\n"
        "let Entities = database('scot').index('alert').macro('entity');\n"
        "Alerts\n"
        "| project id\n"
        "| join Entities on id\n"
        "| where status == 'tracked' and type_name == 'domain'"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    rows = result["alert"].to_dicts()
    assert len(rows) == len(alert_ids)
    assert sorted(row["id"] for row in rows) == sorted(alert_ids)
    assert sorted(row["entity_id"] for row in rows) == sorted(
        alert_id + 1_000 for alert_id in alert_ids
    )
    assert session.max_active == 10
    assert (session.calls[0][0], session.calls[0][1]["params"]) == (
        "https://scot.example.test/api/v1/alert/",
        {"limit": 10_000},
    )
    entity_calls = session.calls[1:]
    assert sorted(url for url, _ in entity_calls) == sorted(
        f"https://scot.example.test/api/v1/alert/{alert_id}/entity"
        for alert_id in range(1, 11)
    )
    assert all(call["params"] == {} for _, call in entity_calls)


@pytest.mark.parametrize("table_name", ["entity", "entry"])
def test_eval_returns_context_with_named_table_and_nested_rows(table_name):
    rows = [
        {
            "id": 7,
            "nullable": None,
            "nested": {"source": "unit-test"},
            "values": ["one", "two"],
        }
    ]
    payload = {"result": rows, "resultCount": 1, "totalCount": 99}
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse(payload)))
    adapter.add_index(table_name)
    ctx = Context(Data())

    result = adapter.eval(ctx)

    assert result is ctx
    assert list(result.data.tables) == [table_name]
    assert result.data[table_name].to_dicts() == rows
    assert "resultCount" not in result.data[table_name].to_dicts()[0]
    assert "totalCount" not in result.data[table_name].to_dicts()[0]


def test_eval_binds_cache_session_to_active_context():
    session = FakeCacheSession(FakeResponse({"result": []}))
    adapter = SCOT(scot_config(), session=session)
    adapter.add_index("entity")
    ctx = Context(Data())

    adapter.eval(ctx)

    assert adapter.cache is ctx.cache
    assert session.cache is ctx.cache


def test_eval_preserves_empty_table_identity():
    payload = {"result": [], "resultCount": 0, "totalCount": 0}
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse(payload)))
    adapter.add_index("entity")

    result = adapter.eval(Context(Data()))

    assert "entity" in result.data
    assert len(result.data["entity"]) == 0


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing result"),
        ({"result": {}}, "non-list"),
        ({"result": ["not-an-object"]}, "non-object"),
    ],
)
def test_eval_rejects_malformed_response_envelopes(payload, message):
    adapter = SCOT(scot_config(), session=FakeSession(FakeResponse(payload)))
    adapter.add_index("entity")

    with pytest.raises(hqle.QueryException, match=message):
        adapter.eval(Context(Data()))
