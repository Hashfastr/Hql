from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import pickle

import pytest

from Hql.Database.SCOT.SCOTCatalog import (
    EXCLUDED_RESOURCES,
    SCOT_ENDPOINTS,
    SCOT_TABLES,
    validate_catalog,
)


OPENAPI_PATH = Path(__file__).parents[2] / "docs" / "scot" / "openapi.json"


@pytest.fixture(scope="module")
def openapi():
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def test_catalog_matches_checked_in_openapi(openapi):
    validate_catalog(openapi)


def test_catalog_names_are_unique_and_stable():
    expected = {
        "alertgroup", "alert", "dispatch", "entity", "entry", "event",
        "feed", "guide", "incident", "intel", "product", "signature",
        "vuln_feed", "vuln_track", "appearance", "audit", "link",
        "source", "tag", "handler", "file", "entity_class", "entity_type",
        "pivot", "notification", "special_metric", "threat_model_item",
    }

    assert set(SCOT_TABLES) == expected
    assert len(SCOT_TABLES) == len(SCOT_ENDPOINTS)


def test_catalog_only_exposes_top_level_get_collections(openapi):
    for endpoint in SCOT_ENDPOINTS:
        assert "{" not in endpoint.path
        assert endpoint.path.endswith("/")
        assert "get" in openapi["paths"][endpoint.path]


def test_security_and_non_tabular_resources_are_excluded():
    assert EXCLUDED_RESOURCES.isdisjoint(SCOT_TABLES)
    for endpoint in SCOT_ENDPOINTS:
        assert not any(
            endpoint.path.startswith(f"/api/v1/{resource}/")
            for resource in EXCLUDED_RESOURCES
        )


def test_catalog_describes_filters_response_and_controls():
    entity = SCOT_TABLES["entity"]
    assert entity.filters["value"].type == "string"
    assert entity.result_path == ("result",)
    assert entity.response_model == "ListResponse_Entity_"
    assert entity.row_model == "Entity"
    assert entity.supports_skip
    assert entity.supports_limit
    assert entity.supports_sort

    handler = SCOT_TABLES["handler"]
    assert handler.filters["start_date"].format == "date-time"
    assert not handler.supports_skip
    assert handler.supports_limit
    assert not handler.supports_sort


def test_endpoint_metadata_is_immutable_copyable_and_pickleable():
    endpoint = SCOT_TABLES["alert"]

    assert copy.deepcopy(endpoint) is endpoint
    restored = pickle.loads(pickle.dumps(endpoint))
    assert restored == endpoint

    with pytest.raises(TypeError):
        restored.filters["new"] = restored.filters["id"]


def test_validation_rejects_duplicate_names(openapi):
    duplicate = replace(SCOT_ENDPOINTS[1], name=SCOT_ENDPOINTS[0].name)
    with pytest.raises(ValueError, match="duplicate table name"):
        validate_catalog(openapi, (SCOT_ENDPOINTS[0], duplicate))


def test_validation_rejects_missing_paths(openapi):
    missing = replace(SCOT_ENDPOINTS[0], path="/api/v1/not-a-real-resource/")
    with pytest.raises(ValueError, match="missing GET path"):
        validate_catalog(openapi, (missing,))


def test_validation_rejects_unsupported_response_shapes(openapi):
    unsupported = replace(SCOT_ENDPOINTS[0], response_model="Game", row_model="Game")
    with pytest.raises(ValueError, match="response is"):
        validate_catalog(openapi, (unsupported,))
