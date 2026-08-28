from __future__ import annotations

import math
from collections.abc import Mapping as MappingABC
from typing import TYPE_CHECKING, Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests

from Hql.Context import register_database
from Hql.Database.Database import Database
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Data import Data
    from Hql.Database.SCOT.SCOTCatalog import Endpoint
    from Hql.Expressions.References import NamedReference


DEFAULT_TIMEOUT = 10.0
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_ROWS = 10_000


def _positive_int(conf: dict[str, Any], key: str, default: int) -> int:
    value = conf.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise hqle.ConfigException(f"SCOT config {key} must be a positive integer")
    return value


def _positive_number(conf: dict[str, Any], key: str, default: float) -> float:
    value = conf.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise hqle.ConfigException(
            f"SCOT config {key} must be a positive finite number"
        )
    return float(value)


def _required_secret(conf: dict[str, Any], key: str, database_name: str) -> str:
    value = conf.get(key)
    if not isinstance(value, str) or not value.strip():
        raise hqle.ConfigException(
            f"Missing or empty {key} in SCOT config for {database_name}"
        )
    return value.strip()


def _normalize_base_url(value: Any, database_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise hqle.ConfigException(
            f"Missing or empty base_url in SCOT config for {database_name}"
        )

    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise hqle.ConfigException(
            f"SCOT config base_url for {database_name} must be an HTTP(S) URL"
        )
    if parsed.username is not None or parsed.password is not None:
        raise hqle.ConfigException("SCOT config base_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise hqle.ConfigException(
            "SCOT config base_url must not contain a query string or fragment"
        )

    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", ""))


@register_database("SCOT")
class SCOT(Database):
    """Read-only SCOT 4 database adapter.

    Example configuration::

        database:
          name: scot
          type: SCOT
          conf:
            base_url: https://scot.example.invalid
            api_key: <INJECT_SCOT_API_KEY>
            verify_tls: true
            timeout: 10
            page_size: 100
            max_rows: 10000

    Supply ``api_key`` at deployment time rather than committing a usable key.
    Select a table with an expression such as ``database('scot').entity``.
    """

    def __init__(
        self,
        config: dict,
        name: str = "unnamed-scot",
        *,
        session: requests.Session | None = None,
    ):
        if not isinstance(config, dict):
            raise hqle.ConfigException("SCOT database configuration must be a mapping")
        conf = config.get("conf")
        if not isinstance(conf, dict):
            raise hqle.ConfigException(
                f"Missing conf mapping in SCOT config for {name}"
            )

        super().__init__(config, name=name)
        from Hql.Compiler import SCOTCompiler

        self.compiler = SCOTCompiler()
        self.base_url = _normalize_base_url(conf.get("base_url"), name)
        self._api_key = _required_secret(conf, "api_key", name)

        verify_tls = conf.get("verify_tls", True)
        if not isinstance(verify_tls, bool):
            raise hqle.ConfigException("SCOT config verify_tls must be a boolean")
        self.verify_tls = verify_tls

        self.timeout = _positive_number(conf, "timeout", DEFAULT_TIMEOUT)
        self.page_size = _positive_int(conf, "page_size", DEFAULT_PAGE_SIZE)
        self.max_rows = _positive_int(conf, "max_rows", DEFAULT_MAX_ROWS)
        if self.page_size > self.max_rows:
            raise hqle.ConfigException(
                "SCOT config page_size must not exceed max_rows"
            )

        self.endpoint: Endpoint | None = None
        self.methods = ["index", "macro"]
        self._session = session if session is not None else requests.Session()

    def get_variable(self, name: NamedReference) -> SCOT:
        from Hql.Database.SCOT.SCOTCatalog import SCOT_TABLES

        endpoint = SCOT_TABLES.get(name.name)
        if endpoint is None:
            raise hqle.QueryException(f"Unknown or unavailable SCOT table {name.name}")
        if self.endpoint is not None and self.endpoint != endpoint:
            raise hqle.QueryException(
                f"SCOT table is already selected as {self.endpoint.name}"
            )
        self.endpoint = endpoint
        self.compiler.set_endpoint(endpoint)
        return self

    def add_index(self, index: str) -> None:
        from Hql.Expressions.References import NamedReference

        self.get_variable(NamedReference(index))

    def _fetch_selected(self) -> Any:
        if self.endpoint is None:
            raise hqle.QueryException("No SCOT table selected")
        return self._request_json(self.endpoint.path, self.compiler.simple_compile())

    def _extract_rows(self, payload: Any) -> list[dict[str, Any]]:
        """Extract and validate rows using the selected endpoint descriptor."""

        if self.endpoint is None:
            raise hqle.QueryException("No SCOT table selected")

        value = payload
        for segment in self.endpoint.result_path:
            if not isinstance(value, MappingABC) or segment not in value:
                raise hqle.QueryException(
                    f"SCOT table {self.endpoint.name} returned an invalid response "
                    f"envelope; missing {'.'.join(self.endpoint.result_path)}"
                )
            value = value[segment]

        if not isinstance(value, list):
            raise hqle.QueryException(
                f"SCOT table {self.endpoint.name} returned non-list result rows"
            )
        if not all(isinstance(row, MappingABC) for row in value):
            raise hqle.QueryException(
                f"SCOT table {self.endpoint.name} returned a non-object result row"
            )

        return [dict(row) for row in value]

    def _response_to_data(self, payload: Any) -> Data:
        from Hql.Data import Data, Table

        assert self.endpoint is not None
        rows = self._extract_rows(payload)
        return Data([Table(init_data=rows, name=self.endpoint.name)])

    def eval(self, ctx: Context) -> Context:
        """Fetch the selected SCOT collection into the current HQL context."""

        self.ctx = ctx
        ctx.data = self._response_to_data(self._fetch_selected())
        return ctx

    def _request_json(
        self, path: str, params: Mapping[str, str | int] | None = None
    ) -> Any:
        """Execute an authenticated GET through the adapter's sole HTTP path."""

        if not path.startswith("/api/v1/") or "://" in path or ".." in path:
            raise hqle.QueryException("Invalid SCOT API path")

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"apikey {self._api_key}"}
        try:
            response = self._session.get(
                url,
                headers=headers,
                params=dict(params or {}),
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.Timeout:
            raise hqle.QueryException(f"SCOT GET {path} timed out") from None
        except requests.RequestException:
            raise hqle.QueryException(f"SCOT GET {path} failed to connect") from None

        if not 200 <= response.status_code < 300:
            raise hqle.QueryException(
                f"SCOT GET {path} failed with HTTP {response.status_code}"
            )
        try:
            return response.json()
        except (ValueError, requests.JSONDecodeError):
            raise hqle.QueryException(
                f"SCOT GET {path} returned malformed JSON"
            ) from None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "base_url": self.base_url,
            "verify_tls": self.verify_tls,
            "timeout": self.timeout,
            "page_size": self.page_size,
            "max_rows": self.max_rows,
            "table": self.endpoint.name if self.endpoint else None,
        }
