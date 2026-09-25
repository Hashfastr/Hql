from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Mapping as MappingABC
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests
from Hql.Cache import Session, Cache

from Hql.Context import register_database
from Hql.Database.Database import Database
from Hql.Exceptions import HqlExceptions as hqle

import logging

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Data import Data
    from Hql.Database.SCOT.SCOTCatalog import Endpoint
    from Hql.Expressions.References import NamedReference


DEFAULT_TIMEOUT = 10.0
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_ROWS = 10_000
DEFAULT_REQUESTS_PER_SECOND = 10


class _RateLimiter:
    """Permit bounded bursts and remain shared by deep-copied adapters."""

    def __init__(self, requests_per_second: int) -> None:
        self.requests_per_second = requests_per_second
        self.request_times: deque[float] = deque()
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            while True:
                now = time.monotonic()
                cutoff = now - 1
                while self.request_times and self.request_times[0] <= cutoff:
                    self.request_times.popleft()

                if len(self.request_times) < self.requests_per_second:
                    self.request_times.append(now)
                    return

                time.sleep(self.request_times[0] + 1 - now)

    def __deepcopy__(self, _memo: dict[int, Any]) -> _RateLimiter:
        return self


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
            requests_per_second: 10

    Supply ``api_key`` at deployment time rather than committing a usable key.
    Select a table with an expression such as ``database('scot').entity``.
    """

    def __init__(
        self,
        config: dict,
        name: str = "unnamed-scot",
        *,
        session: Session | None = None,
        cache: Cache | None = None
    ):
        if not isinstance(config, dict):
            raise hqle.ConfigException("SCOT database configuration must be a mapping")
        conf = config.get("conf")
        if not isinstance(conf, dict):
            raise hqle.ConfigException(
                f"Missing conf mapping in SCOT config for {name}"
            )

        super().__init__(config, name=name, cache=cache)
        from Hql.Compiler import SCOTCompiler

        self.base_url = _normalize_base_url(conf.get("base_url"), name)
        self._api_key = _required_secret(conf, "api_key", name)

        verify_tls = conf.get("verify_tls", True)
        if not isinstance(verify_tls, bool):
            raise hqle.ConfigException("SCOT config verify_tls must be a boolean")
        self.verify_tls = verify_tls

        self.timeout = _positive_number(conf, "timeout", DEFAULT_TIMEOUT)
        self.requests_per_second = _positive_int(
            conf,
            "requests_per_second",
            DEFAULT_REQUESTS_PER_SECOND,
        )
        self.page_size = _positive_int(conf, "page_size", DEFAULT_PAGE_SIZE)
        self.max_rows = _positive_int(conf, "max_rows", DEFAULT_MAX_ROWS)
        if self.page_size > self.max_rows:
            raise hqle.ConfigException(
                "SCOT config page_size must not exceed max_rows"
            )
        self.compiler = SCOTCompiler(max_limit=self.max_rows)

        self.endpoint: Endpoint | None = None
        self.methods = ["index", "macro"]
        self._session = (
            session
            if session is not None
            else Session(cache=self.cache, session=requests.Session())
        )
        self._rate_limiter = _RateLimiter(self.requests_per_second)

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

    def get_macro(self, name: str) -> dict | SCOT | None:
        from Hql.Compiler import SCOTCompiler
        from Hql.Database.SCOT.SCOTCatalog import SCOT_RELATIONSHIPS

        if self.endpoint is not None:
            relationship = SCOT_RELATIONSHIPS.get((self.endpoint.name, name))
            if relationship is not None:
                self.endpoint = relationship
                self.compiler = SCOTCompiler(
                    relationship,
                    max_limit=self.max_rows,
                )
                return self
        return super().get_macro(name)

    def _fetch_selected(self) -> Any:
        if self.endpoint is None:
            raise hqle.QueryException("No SCOT table selected")
        requests_to_make = self.compiler.resolved_requests()
        if not requests_to_make:
            return {"result": []}

        params = self.compiler.simple_compile()
        if len(requests_to_make) == 1 and not requests_to_make[0][1]:
            return self._request_json(requests_to_make[0][0], params)

        def fetch(request: tuple[str, dict[str, str]]) -> list[dict[str, Any]]:
            path, path_values = request
            fetched = self._extract_rows(self._request_json(path, params))
            return self._attach_path_values(fetched, path_values)

        if len(requests_to_make) == 1:
            return {"result": fetch(requests_to_make[0])}

        workers = min(len(requests_to_make), self.requests_per_second)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            batches = executor.map(fetch, requests_to_make)
            rows = [row for batch in batches for row in batch]
        return {"result": rows}

    def _attach_path_values(
        self,
        rows: list[dict[str, Any]],
        path_values: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        """Expose relationship keys while retaining same-named result fields."""

        assert self.endpoint is not None
        attached = []
        for row in rows:
            row = dict(row)
            for name, serialized in path_values.items():
                if name in row:
                    row[f"{self.endpoint.name}_{name}"] = row[name]
                parameter = self.endpoint.filters[name]
                row[name] = (
                    int(serialized)
                    if parameter.type == "integer"
                    else serialized
                )
            attached.append(row)
        return attached

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
        self.cache = ctx.cache
        if isinstance(self._session, Session):
            self._session.cache = ctx.cache
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
        self._rate_limiter.wait()
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
            "requests_per_second": self.requests_per_second,
            "page_size": self.page_size,
            "max_rows": self.max_rows,
            "table": self.endpoint.name if self.endpoint else None,
        }
