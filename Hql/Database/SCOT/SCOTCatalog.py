"""Declarative catalog of SCOT endpoints exposed as HQL tables.

The catalog is derived from ``docs/scot/openapi.json`` (SCOT 4.7.1), but is
kept in Python so an installed HQL package does not need the documentation
tree at runtime.  :func:`validate_catalog` keeps the declaration synchronized
with the checked-in OpenAPI document.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class QueryParameter:
    """The OpenAPI type information needed to serialize a SCOT filter."""

    type: str
    format: str | None = None


STRING = QueryParameter("string")
BOOL = QueryParameter("boolean")
DATETIME = QueryParameter("string", "date-time")
INTEGER = QueryParameter("integer")


@dataclass(frozen=True, slots=True)
class Endpoint:
    """A read-only SCOT collection that can be selected as an HQL table."""

    name: str
    path: str
    filters: Mapping[str, QueryParameter]
    response_model: str
    row_model: str
    result_path: tuple[str, ...] = ("result",)
    skip_parameter: str | None = None
    limit_parameter: str | None = None
    sort_parameter: str | None = None
    path_parameters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "filters", MappingProxyType(dict(self.filters)))

    def __deepcopy__(self, _memo: dict[int, Any]) -> Endpoint:
        return self

    def __reduce__(self):
        return (
            type(self),
            (
                self.name,
                self.path,
                dict(self.filters),
                self.response_model,
                self.row_model,
                self.result_path,
                self.skip_parameter,
                self.limit_parameter,
                self.sort_parameter,
                self.path_parameters,
            ),
        )

    @property
    def supports_skip(self) -> bool:
        return self.skip_parameter is not None

    @property
    def supports_limit(self) -> bool:
        return self.limit_parameter is not None

    @property
    def supports_sort(self) -> bool:
        return self.sort_parameter is not None


def _endpoint(
    name: str,
    row_model: str,
    *,
    filters: Mapping[str, QueryParameter],
    skip: bool = True,
    limit: bool = True,
    sort: bool = True,
) -> Endpoint:
    return Endpoint(
        name=name,
        path=f"/api/v1/{name}/",
        filters=filters,
        response_model=f"ListResponse_{row_model}_",
        row_model=row_model,
        skip_parameter="skip" if skip else None,
        limit_parameter="limit" if limit else None,
        sort_parameter="sort" if sort else None,
    )


def _string_filters(*names: str) -> Mapping[str, QueryParameter]:
    """Build the common SCOT search-field declaration."""

    return {name: STRING for name in names}


# Approved top-level JSON collections. Relationship endpoints, singleton
# resources, user/authentication/administration APIs, exports, downloads,
# firehose, health, and mutation routes are intentionally not represented.
SCOT_ENDPOINTS = (
    _endpoint(
        "alertgroup",
        "AlertGroup",
        filters=_string_filters(
            "id", "created", "modified", "owner", "subject", "tlp", "alf",
            "message_id", "source", "tag", "status", "alert_count",
            "promoted_count", "open_count", "closed_count", "first_view",
            "parsed", "view_count",
        ),
    ),
    _endpoint(
        "alert",
        "Alert",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "parsed",
            "alertgroup_id", "entry_count", "promoted_to",
        ),
    ),
    _endpoint(
        "dispatch",
        "Dispatch",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "status",
            "tag", "source", "subject", "entry_count", "promoted_to",
        ),
    ),
    _endpoint(
        "entity",
        "Entity",
        filters=_string_filters(
            "id", "created", "modified", "source", "tag", "value",
            "type_name", "entity_count", "status", "classes",
        ),
    ),
    _endpoint(
        "entry",
        "EntryWithParent",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "target_type", "target_id", "entry_class",
            "task_assignee", "task_status", "parent_subject",
        ),
    ),
    _endpoint(
        "event",
        "Event",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "view_count", "status", "entry_count",
            "promoted_to",
        ),
    ),
    _endpoint(
        "feed",
        "Feed",
        filters=_string_filters(
            "id", "created", "modified", "owner", "name", "status", "uri",
            "type", "article_count", "promotions_count", "last_article",
            "last_attempt",
        ),
    ),
    _endpoint(
        "guide",
        "Guide",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "subject",
            "status", "entry_count",
        ),
    ),
    _endpoint(
        "incident",
        "Incident",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "view_count", "status", "entry_count",
            "promoted_from",
        ),
    ),
    _endpoint(
        "intel",
        "Intel",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "entry_count", "promoted_to", "status",
        ),
    ),
    _endpoint(
        "product",
        "Product",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "entry_count", "promoted_from",
        ),
    ),
    _endpoint(
        "signature",
        "Signature",
        filters=_string_filters(
            "id", "created", "modified", "name", "description",
            "signature_group", "type", "owner", "tlp", "alf", "tag",
            "source", "status",
        ),
    ),
    _endpoint(
        "vuln_feed",
        "VulnFeed",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "view_count", "status", "entry_count",
            "promoted_to",
        ),
    ),
    _endpoint(
        "vuln_track",
        "VulnTrack",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "subject", "view_count", "status", "entry_count",
            "promoted_to",
        ),
    ),
    _endpoint(
        "appearance",
        "Appearance",
        filters=_string_filters(
            "id", "when_date", "value_str", "value_type", "target_type",
            "target_id",
        ),
    ),
    _endpoint(
        "audit",
        "Audit",
        filters=_string_filters(
            "id", "when_date", "username", "what", "thing_type", "thing_id",
        ),
    ),
    _endpoint(
        "link",
        "Link",
        filters=_string_filters("v0_type", "v0_id", "v1_id", "v1_type"),
    ),
    _endpoint(
        "source",
        "Source",
        filters=_string_filters(
            "id", "created", "modified", "name", "description",
        ),
    ),
    _endpoint(
        "tag",
        "Tag",
        filters=_string_filters(
            "id", "created", "modified", "name", "description",
        ),
    ),
    # The OpenAPI document incorrectly labels ``skip`` as a path parameter even
    # though the path has no placeholder. Do not advertise unsupported pushdown.
    _endpoint(
        "handler",
        "Handler",
        filters={"start_date": DATETIME, "end_date": DATETIME},
        skip=False,
        sort=False,
    ),
    _endpoint(
        "file",
        "File",
        filters=_string_filters(
            "id", "created", "modified", "owner", "tlp", "alf", "tag",
            "source", "filename", "sha256", "glob", "description",
            "content_type",
        ),
    ),
    _endpoint(
        "entity_class",
        "EntityClass",
        filters=_string_filters(
            "id", "created", "modified", "description", "display_name",
            "name", "icon",
        ),
    ),
    _endpoint(
        "entity_type",
        "EntityType",
        filters=_string_filters("id", "created", "modified"),
    ),
    _endpoint(
        "pivot",
        "Pivot",
        filters=_string_filters(
            "id", "created", "modified", "title", "template", "description",
        ),
    ),
    _endpoint(
        "notification",
        "Notification",
        filters={"include_acked": BOOL},
        sort=False,
    ),
    _endpoint(
        "special_metric",
        "SpecialMetric",
        filters=_string_filters(
            "id", "created", "modified", "target_id", "target_type",
            "metric_type", "start_time", "end_time",
        ),
    ),
    _endpoint(
        "threat_model_item",
        "ThreatModelItem",
        filters=_string_filters(
            "id", "created", "modified", "threat_model_name",
            "threat_model_id", "title", "description", "owner", "data",
            "tag", "source",
        ),
    ),
)

SCOT_TABLES: Mapping[str, Endpoint] = MappingProxyType(
    {endpoint.name: endpoint for endpoint in SCOT_ENDPOINTS}
)

SCOT_RELATIONSHIPS: Mapping[tuple[str, str], Endpoint] = MappingProxyType(
    {
        ("alert", "entity"): Endpoint(
            name="entity",
            path="/api/v1/alert/{id}/entity",
            filters={"id": INTEGER},
            response_model="ListResponse_Entity_",
            row_model="Entity",
            path_parameters=("id",),
        )
    }
)

# These names are useful for contract tests and make the security boundary
# explicit. Paths below these resources are never exposed through the catalog.
EXCLUDED_RESOURCES = frozenset(
    {
        "apikey",
        "firehose",
        "game",
        "health",
        "login",
        "logout",
        "metric",
        "permissions",
        "role",
        "settings",
        "user_links",
        "users",
    }
)


def validate_catalog(
    openapi: Mapping[str, Any],
    endpoints: Sequence[Endpoint] = SCOT_ENDPOINTS,
) -> None:
    """Raise ``ValueError`` when catalog entries drift from the OpenAPI spec."""

    errors: list[str] = []
    names: set[str] = set()
    paths: set[str] = set()
    schemas = openapi.get("components", {}).get("schemas", {})
    openapi_paths = openapi.get("paths", {})

    for endpoint in endpoints:
        if endpoint.name in names:
            errors.append(f"duplicate table name: {endpoint.name}")
        names.add(endpoint.name)
        if endpoint.path in paths:
            errors.append(f"duplicate endpoint path: {endpoint.path}")
        paths.add(endpoint.path)

        operation = openapi_paths.get(endpoint.path, {}).get("get")
        if operation is None:
            errors.append(f"{endpoint.name}: missing GET path {endpoint.path}")
            continue

        query_parameters = {
            parameter["name"]: parameter.get("schema", {})
            for parameter in operation.get("parameters", [])
            if parameter.get("in") == "query"
        }
        path_parameters = {
            parameter["name"]: parameter.get("schema", {})
            for parameter in operation.get("parameters", [])
            if parameter.get("in") == "path"
            and f"{{{parameter['name']}}}" in endpoint.path
        }
        controls = {
            parameter
            for parameter in (
                endpoint.skip_parameter,
                endpoint.limit_parameter,
                endpoint.sort_parameter,
            )
            if parameter is not None
        }
        if set(endpoint.path_parameters) != set(path_parameters):
            errors.append(
                f"{endpoint.name}: path fields differ: "
                f"catalog={sorted(endpoint.path_parameters)}, "
                f"openapi={sorted(path_parameters)}"
            )
        expected_filters = (
            set(query_parameters) - {"skip", "limit", "sort"}
        ) | set(path_parameters)
        if set(endpoint.filters) != expected_filters:
            errors.append(
                f"{endpoint.name}: filter fields differ: "
                f"catalog={sorted(endpoint.filters)}, "
                f"openapi={sorted(expected_filters)}"
            )

        for control in controls:
            if control not in query_parameters:
                errors.append(f"{endpoint.name}: missing query control {control}")
        for name, declared in endpoint.filters.items():
            actual = query_parameters.get(name, path_parameters.get(name))
            if actual is None:
                continue
            type_differs = actual.get("type") != declared.type
            format_differs = actual.get("format") != declared.format
            if type_differs or format_differs:
                errors.append(
                    f"{endpoint.name}.{name}: catalog type {declared} differs from "
                    f"OpenAPI {actual.get('type')}/{actual.get('format')}"
                )

        response_ref = (
            operation.get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
            .get("$ref")
        )
        expected_response_ref = f"#/components/schemas/{endpoint.response_model}"
        if response_ref != expected_response_ref:
            errors.append(
                f"{endpoint.name}: response is {response_ref!r}, expected "
                f"{expected_response_ref!r}"
            )
            continue

        response_schema = schemas.get(endpoint.response_model)
        if response_schema is None:
            errors.append(
                f"{endpoint.name}: missing response model {endpoint.response_model}"
            )
            continue
        if endpoint.result_path != ("result",):
            errors.append(
                f"{endpoint.name}: unsupported result path {endpoint.result_path!r}"
            )
            continue
        result = response_schema.get("properties", {}).get("result", {})
        expected_row_ref = f"#/components/schemas/{endpoint.row_model}"
        is_array = result.get("type") == "array"
        has_expected_rows = result.get("items", {}).get("$ref") == expected_row_ref
        if not is_array or not has_expected_rows:
            errors.append(
                f"{endpoint.name}: response result is not an array of "
                f"{endpoint.row_model}"
            )

    if errors:
        raise ValueError("Invalid SCOT endpoint catalog:\n- " + "\n- ".join(errors))
