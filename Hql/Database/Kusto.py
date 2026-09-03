from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional, Union
import logging

from Hql.Context import register_database
from Hql.Database.Database import Database
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Operators.Operator import Operator
from Hql.Types.Kusto import KustoTypes

if TYPE_CHECKING:
    from Hql.Compiler import BranchDescriptor
    from Hql.Context import Context
    from Hql.Data import Schema


'''
Example configuration:
 
database:
  name: 'kusto'
  type: 'Kusto'
  conf:
    database: '<DATABASE_NAME>'
    cluster: 'https://<CLUSTER>.<REGION>.kusto.windows.net'
    client_id: '<APPLICATION_CLIENT_ID>'
    client_secret: '<INJECT_CLIENT_SECRET>'
    tenant_id: '<AZURE_TENANT_ID>'
 
Inject client_secret from a secret manager; never commit a usable secret.
'''
@register_database('Kusto')
class Kusto(Database):
    """Execute native KQL while leaving every HQL operator for local evaluation."""

    REQUIRED_CONFIG = ('database', 'cluster', 'client_id', 'client_secret', 'tenant_id')

    def __init__(
        self,
        config:dict,
        name:str='Kusto Database',
        query_client:Optional[Any]=None,
    ):
        Database.__init__(self, config, name=name)

        conf = self.config.get('conf', {})
        if not conf:
            raise hqle.ConfigException('Kusto database given no config')

        missing = [
            key
            for key in self.REQUIRED_CONFIG
            if not isinstance(conf.get(key), str) or not conf[key].strip()
        ]
        if missing:
            raise hqle.ConfigException(
                f"Kusto database missing required config: {', '.join(missing)}"
            )

        self.database = conf['database']
        self.cluster = conf['cluster']
        self.client_id = conf['client_id']
        self.client_secret = conf['client_secret']
        self.tenant_id = conf['tenant_id']
        self._raw_query:Optional[str] = None

        self.methods = ['raw']
        self.can_push = True

        if query_client is not None:
            self.query_client = query_client
        else:
            try:
                from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
            except ImportError as exc:
                raise hqle.ConfigException(
                    'Kusto queries require the azure-kusto-data package'
                ) from exc

            kcsb_data = KustoConnectionStringBuilder.with_aad_application_key_authentication(
                self.cluster, self.client_id, self.client_secret, self.tenant_id
            )
            self.query_client = KustoClient(kcsb_data)

    def __deepcopy__(self, memo:dict[int, Any]) -> Kusto:
        """Copy query state while sharing the SDK client and its internal locks."""
        from copy import deepcopy

        copied = self.__class__.__new__(self.__class__)
        memo[id(self)] = copied
        for key, value in vars(self).items():
            setattr(
                copied,
                key,
                value if key == 'query_client' else deepcopy(value, memo),
            )
        return copied

    def add_op(self, op:Union[Operator, BranchDescriptor]) -> tuple[None, Operator]:
        """Reject every HQL operator so it executes after the native query."""
        if not isinstance(op, Operator):
            op = op.get_op()
        return None, op

    def set_raw_query(self, query:str) -> None:
        if not query.strip():
            raise hqle.QueryException('Kusto raw query cannot be empty')
        self._raw_query = query

    @staticmethod
    def _column_names(result:Any) -> list[str]:
        names = []
        for column in getattr(result, 'columns', []):
            name = getattr(column, 'column_name', None)
            if name is None:
                name = getattr(column, 'name', None)
            if not isinstance(name, str):
                raise hqle.QueryException('Kusto returned invalid column metadata')
            names.append(name)
        return names

    @classmethod
    def _response_rows(cls, response:Any) -> list[dict]:
        if not hasattr(response, 'primary_results'):
            raise hqle.QueryException('Kusto returned an invalid query response')

        if not response.primary_results:
            return []

        result = response.primary_results[0]
        columns = cls._column_names(result)
        rows = []
        for raw_row in result:
            to_dict = getattr(raw_row, 'to_dict', None)
            if isinstance(raw_row, Mapping):
                row = dict(raw_row)
            elif callable(to_dict):
                row = dict(to_dict())
            else:
                values = list(raw_row)
                if len(values) != len(columns):
                    raise hqle.QueryException(
                        'Kusto returned a row that does not match its columns'
                    )
                row = dict(zip(columns, values))
            rows.append(row)
        return rows

    def eval(self, ctx:Context) -> Context:
        from Hql.Data import Data, Table

        if self._raw_query is None:
            raise hqle.QueryException('Kusto database requires a raw query')

        response = self.query_client.execute(self.database, self._raw_query)
        rows = self._response_rows(response)
        ctx.data = Data([Table(init_data=rows, name=self.name)])
        return ctx

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            'name': self.name,
            'database': self.database,
            'query': self._raw_query,
        }

    def _table_exists(self, table: str) -> bool:
        kql = f".show tables | where TableName == '{table}'"
        response = self.query_client.execute(self.database, kql)
        return len(response.primary_results[0]) > 0

    def _create_table(self, table:str, schema:Schema) -> None:
        columns = []
        for field in schema.schema:
            hql_type = schema.schema[field]
            kusto_type = KustoTypes.from_hql(hql_type)
            columns.append(f"['{field.str()}']: {kusto_type.deparse()}")

        command = f".create table ['{table}'] ({', '.join(columns)})"
        self.query_client.execute(self.database, command)

    def ensure_table(self, table:str, schema:Schema) -> None:
        if not self._table_exists(table):
            self._create_table(table, schema)

    def push(self, ctx: 'Context', **kwargs) -> bool:
        from azure.kusto.ingest import IngestionProperties, QueuedIngestClient
        from azure.kusto.data import DataFormat, KustoConnectionStringBuilder
        import io
        import polars as pl

        kcsb_ingest = KustoConnectionStringBuilder.with_aad_application_key_authentication(
            self.cluster.replace("https://", "https://ingest-"), self.client_id, self.client_secret, self.tenant_id
        )

        ingest_client = QueuedIngestClient(kcsb_ingest)

        for i in ctx.data:
            if not isinstance(i.df, pl.DataFrame):
                logging.warning(f'{i.name} does not contain a dataframe, continuing...')
                continue

            self.ensure_table(i.name, i.schema)

            properties = IngestionProperties(
                database=self.database,
                table=i.name,
                data_format=DataFormat.CSV,
            )

            # Kusto SDK expects a file-like stream; serialize Polars to CSV in memory.
            buffer = io.BytesIO()
            i.df.write_csv(buffer)
            buffer.seek(0)

            ingest_client.ingest_from_stream(buffer, ingestion_properties=properties)

        return True
