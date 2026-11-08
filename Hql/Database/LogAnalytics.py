from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
import datetime
import json
import logging
import re

from Hql.Compiler import KustoCompiler
from Hql.Context import register_database
from Hql.Database.Database import Database
from Hql.Database.Kusto import Kusto
from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Context import Context
    from Hql.Data import Schema


'''
Example configuration, authenticating as an app registration:

database:
  name: 'sentinel'
  type: 'LogAnalytics'
  conf:
    workspace_id: '<WORKSPACE_ID>'
    client_id: '<APPLICATION_CLIENT_ID>'
    client_secret: '<INJECT_CLIENT_SECRET>'
    tenant_id: '<AZURE_TENANT_ID>'
    # Sovereign clouds only, e.g. Azure Government:
    # endpoint: 'https://api.loganalytics.us'
    # authority: 'login.microsoftonline.us'

Or reusing the session from `az login`:

database:
  name: 'sentinel'
  type: 'LogAnalytics'
  conf:
    workspace_id: '<WORKSPACE_ID>'
    auth: 'azcli'
    # Optional, query a tenant other than the CLI's default:
    # tenant_id: '<AZURE_TENANT_ID>'

auth is 'secret' or 'azcli'. Left out, it is 'azcli' when no client_id or
client_secret is configured, and 'secret' otherwise. With azcli, sovereign clouds
come from `az cloud set`, so authority is ignored.

workspace_id is the Workspace ID GUID from the workspace's Overview blade. The app,
or the signed in user, needs the Log Analytics Reader role on the workspace.

Inject client_secret from a secret manager; never commit a usable secret.
'''

# [-][d.]hh:mm:ss[.fffffff], the Log Analytics API returns timespans as these strings
TIMESPAN = re.compile(r'^(-)?(?:(\d+)\.)?(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$')

@register_database('LogAnalytics')
class LogAnalytics(Kusto):
    """Execute native KQL against a Log Analytics workspace, pushing supported where predicates and takes onto it."""

    REQUIRED_CONFIG = ('workspace_id',)
    SECRET_CONFIG = ('client_id', 'client_secret', 'tenant_id')
    AUTH_METHODS = ('secret', 'azcli')

    def __init__(
        self,
        config:dict,
        name:str='Log Analytics Database',
        query_client:Optional[Any]=None,
    ):
        Database.__init__(self, config, name=name)

        conf = self._require_conf(self.config, self.REQUIRED_CONFIG, 'Log Analytics')
        self.workspace_id = conf['workspace_id']
        self.auth = self._auth_method(conf)
        if self.auth == 'secret':
            self._require_conf(self.config, self.SECRET_CONFIG, 'Log Analytics')
        self._raw_query:Optional[str] = None
        self._timespan:Optional[tuple[datetime.datetime, datetime.datetime]] = None
        self.compiler = KustoCompiler()

        self.methods = ['raw', 'index']
        # Writing to a workspace goes through data collection rules, not this API
        self.can_push = False

        if query_client is not None:
            self.query_client = query_client
        else:
            try:
                from azure.monitor.query import LogsQueryClient
            except ImportError as exc:
                raise hqle.ConfigException(
                    'Log Analytics queries require the azure-monitor-query package'
                ) from exc

            credential = self._credential(conf, name)
            client_kwargs = {'endpoint': conf['endpoint']} if conf.get('endpoint') else {}
            self.query_client = LogsQueryClient(credential, **client_kwargs)

    @classmethod
    def _auth_method(cls, conf:dict) -> str:
        auth = conf.get('auth')
        if auth is None:
            return 'secret' if conf.get('client_id') or conf.get('client_secret') else 'azcli'
        if auth not in cls.AUTH_METHODS:
            raise hqle.ConfigException(
                f"Log Analytics auth must be one of {', '.join(cls.AUTH_METHODS)}, got {auth!r}"
            )
        return auth

    def _credential(self, conf:dict, name:str) -> Any:
        try:
            from azure.identity import AzureCliCredential, ClientSecretCredential
        except ImportError as exc:
            raise hqle.ConfigException(
                'Log Analytics queries require the azure-identity package'
            ) from exc

        # Both raise ValueError on a malformed tenant_id, such as an unfilled placeholder
        try:
            if self.auth == 'azcli':
                # Shells out to az for a token on each refresh, so a later az login is picked up
                cred_kwargs = {'tenant_id': conf['tenant_id']} if conf.get('tenant_id') else {}
                return AzureCliCredential(**cred_kwargs)

            cred_kwargs = {'authority': conf['authority']} if conf.get('authority') else {}
            return ClientSecretCredential(
                conf['tenant_id'], conf['client_id'], conf['client_secret'], **cred_kwargs
            )
        except ValueError as exc:
            raise hqle.ConfigException(f'Log Analytics database {name}: {exc}') from exc

    def _query(self) -> Any:
        try:
            from azure.core.exceptions import ClientAuthenticationError
        except ImportError:
            # Only an injected client runs without the Azure SDK, it raises nothing to translate
            ClientAuthenticationError = ()  # type: ignore[assignment,misc]

        try:
            return self.query_client.query_workspace(
                self.workspace_id, self.compile(), timespan=self._timespan
            )
        except ClientAuthenticationError as exc:
            hint = ', run `az login` and retry' if self.auth == 'azcli' else ''
            raise hqle.QueryException(
                f'Log Analytics database {self.name} failed to authenticate{hint}: {exc.message}'
            ) from exc

    def add_timebound(self, start: datetime.datetime, end: datetime.datetime) -> tuple[Database, None]:
        # The API bounds the query server side, on top of any time filter in the KQL
        if self.config.get('timeseries', True):
            self._timespan = (start, end)
        return self, None

    @staticmethod
    def _timedelta(value:str) -> Any:
        match = TIMESPAN.match(value)
        if not match:
            return value

        sign, days, hours, minutes, seconds, fraction = match.groups()
        delta = datetime.timedelta(
            days=int(days or 0),
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            microseconds=int((fraction or '0')[:6].ljust(6, '0')),
        )
        return -delta if sign else delta

    @classmethod
    def _native(cls, kusto_name:str, value:Any) -> Any:
        '''
        The Kusto SDK returns dynamic values as objects and timespans as timedeltas,
        Log Analytics returns both as strings. Convert them so the two match.
        '''
        if not isinstance(value, str):
            return value

        kusto_name = kusto_name.lower()
        if kusto_name == 'dynamic':
            try:
                return json.loads(value)
            except ValueError:
                return value
        if kusto_name == 'timespan':
            return cls._timedelta(value)
        return value

    @classmethod
    def _table_data(cls, table:Any) -> tuple[list[dict], Schema]:
        from Hql.Data import Schema

        columns = getattr(table, 'columns', None)
        kinds = getattr(table, 'columns_types', None)
        if (
            not isinstance(columns, list)
            or not isinstance(kinds, list)
            or len(columns) != len(kinds)
            or not all(isinstance(x, str) for x in columns + kinds)
        ):
            raise hqle.QueryException('Log Analytics returned invalid column metadata')

        fields = {name: cls._column_schema(name, kind) for name, kind in zip(columns, kinds)}

        rows = []
        for raw_row in table.rows:
            values = list(raw_row)
            if len(values) != len(columns):
                raise hqle.QueryException(
                    'Log Analytics returned a row that does not match its columns'
                )
            rows.append({
                name: cls._native(kind, value)
                for name, kind, value in zip(columns, kinds, values)
            })

        return rows, Schema(schema=fields)

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data, Schema, Table

        response = self._query()

        # Partial results come back when the query hits a limit, keep what was returned
        if hasattr(response, 'partial_data'):
            logging.warning(
                f'Log Analytics returned partial results for {self.name}: {response.partial_error}'
            )
            tables = response.partial_data
        elif hasattr(response, 'tables'):
            tables = response.tables
        else:
            raise hqle.QueryException('Log Analytics returned an invalid query response')

        if tables:
            rows, schema = self._table_data(tables[0])
        else:
            rows, schema = [], Schema()

        ctx.data = Data([Table(init_data=rows, schema=schema, name=self.name)])
        return ctx

    def to_dict(self) -> dict:
        return {
            **Database.to_dict(self),
            'name': self.name,
            'workspace_id': self.workspace_id,
            'query': self.compile() if self.compiler.tabular is not None else None,
        }
