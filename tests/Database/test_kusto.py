from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Context import Context, database_registry, get_database
from Hql.Data import Data, Schema
from Hql.Database import Kusto
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Functions.raw import raw
from Hql.Operators.Take import Take
from Hql.Parser import Parser
from Hql.Types.Hql import HqlTypes as hqlt


def kusto_config(**overrides):
    conf = {
        'database': 'test-database',
        'cluster': 'https://cluster.example.test',
        'client_id': 'client-id',
        'client_secret': 'client-secret',
        'tenant_id': 'tenant-id',
    }
    conf.update(overrides)
    return {'name': 'kusto-test', 'type': 'Kusto', 'conf': conf}


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def execute(self, database, query):
        self.calls.append((database, query))
        return self.response


class FakeResult(list):
    def __init__(self, rows, columns):
        super().__init__(rows)
        self.columns = [
            SimpleNamespace(column_name=name, column_type=column_type)
            for name, column_type in columns
        ]


def test_kusto_is_registered_for_database_resolution():
    assert get_database('Kusto') is Kusto


def test_kusto_rejects_every_hql_operator():
    adapter = Kusto(kusto_config(), query_client=FakeClient(None))
    operator = Take(Integer(5), [])

    accepted, rejected = adapter.add_op(operator)

    assert accepted is None
    assert rejected is operator


def test_table_creation_uses_kusto_type_system():
    client = FakeClient(None)
    adapter = Kusto(kusto_config(), query_client=client)

    adapter._create_table(
        'Events',
        Schema(
            schema={
                'message': hqlt.string(),
                'count': hqlt.long(),
                'metadata': {'source': hqlt.string()},
            }
        ),
    )

    assert client.calls == [
        (
            'test-database',
            ".create table ['Events'] "
            "(['message']: string, ['count']: long, ['metadata']: dynamic)",
        )
    ]


def test_raw_query_executes_and_converts_kusto_rows():
    response = SimpleNamespace(
        primary_results=[
            FakeResult(
                [[1, 'first'], [2, 'second']],
                [('id', 'long'), ('value', 'string')],
            )
        ]
    )
    client = FakeClient(response)
    adapter = Kusto(kusto_config(), name='kusto-test', query_client=client)
    configured = raw([StringLiteral('Events | take 2')]).eval(
        Context(Data()), receiver=adapter
    )

    result = configured.eval(Context(Data()))

    assert client.calls == [('test-database', 'Events | take 2')]
    assert result.data['kusto-test'].to_dicts() == [
        {'id': 1, 'value': 'first'},
        {'id': 2, 'value': 'second'},
    ]


def test_raw_query_compiles_and_following_hql_operators_run_locally(monkeypatch):
    response = SimpleNamespace(
        primary_results=[FakeResult([[1], [2]], [('id', 'long')])]
    )
    client = FakeClient(response)

    class TestKusto(Kusto):
        def __init__(self, config, name='Kusto Database'):
            super().__init__(config, name=name, query_client=client)

    monkeypatch.setitem(database_registry, 'Kusto', TestKusto)
    config = Config()
    config.set_database('kusto', kusto_config())
    parser = Parser("database('kusto').raw('Events | take 2')\n| take 1")
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert client.calls == [('test-database', 'Events | take 2')]
    assert result['kusto'].to_dicts() == [{'id': 1}]


def test_raw_query_accepts_a_let_bound_string(monkeypatch):
    response = SimpleNamespace(
        primary_results=[FakeResult([[1], [2]], [('id', 'long')])]
    )
    client = FakeClient(response)

    class TestKusto(Kusto):
        def __init__(self, config, name='Kusto Database'):
            super().__init__(config, name=name, query_client=client)

    monkeypatch.setitem(database_registry, 'Kusto', TestKusto)
    config = Config()
    config.set_database('kusto', kusto_config())
    parser = Parser(
        "let NativeQuery = 'Events | take 2';\n"
        "database('kusto').raw(NativeQuery)"
    )
    parser.assemble()

    result = HqlCompiler(config, parser.assembly).run().data

    assert client.calls == [('test-database', 'Events | take 2')]
    assert result['kusto'].to_dicts() == [{'id': 1}, {'id': 2}]


def test_raw_query_accepts_mapping_rows():
    response = SimpleNamespace(
        primary_results=[FakeResult([{'id': 7}], [('id', 'long')])]
    )
    adapter = Kusto(kusto_config(), query_client=FakeClient(response))
    adapter.set_raw_query('Events')

    result = adapter.eval(Context(Data()))

    assert result.data[adapter.name].to_dicts() == [{'id': 7}]


def test_result_metadata_preserves_datetime_after_null_values():
    event_time = datetime(2026, 9, 1, 21, 31, 10, 811000, tzinfo=timezone.utc)
    response = SimpleNamespace(
        primary_results=[
            FakeResult(
                [[None], [event_time]],
                [('EventTime', 'datetime')],
            )
        ]
    )
    adapter = Kusto(kusto_config(), query_client=FakeClient(response))
    adapter.set_raw_query('Events | project EventTime')

    table = adapter.eval(Context(Data())).data[adapter.name]

    assert len(table) == 2
    assert table.to_dicts()[0]['EventTime'] is None
    assert table.to_dicts()[1]['EventTime'] == event_time.replace(tzinfo=None)
    assert isinstance(table.schema.schema.schema['EventTime'], hqlt.datetime)


def test_kusto_copy_preserves_query_and_shares_sdk_client():
    client = FakeClient(SimpleNamespace(primary_results=[]))
    adapter = Kusto(kusto_config(), query_client=client)
    adapter.set_raw_query('Events')

    copied = deepcopy(adapter)

    assert copied is not adapter
    assert copied.query_client is client
    assert copied.to_dict()['query'] == 'Events'


def test_kusto_requires_raw_query_before_evaluation():
    adapter = Kusto(kusto_config(), query_client=FakeClient(None))

    with pytest.raises(hqle.QueryException, match='requires a raw query'):
        adapter.eval(Context(Data()))


def test_empty_raw_query_is_rejected():
    adapter = Kusto(kusto_config(), query_client=FakeClient(None))

    with pytest.raises(hqle.QueryException, match='cannot be empty'):
        adapter.set_raw_query('   ')


def test_raw_is_rejected_by_unsupported_databases():
    from Hql.Database import Database

    adapter = Database({})

    with pytest.raises(hqle.QueryException, match='does not support raw queries'):
        raw([StringLiteral('native query')]).eval(Context(Data()), receiver=adapter)


def test_raw_requires_a_string_expression():
    with pytest.raises(hqle.ArgumentException, match='Bad raw query argument'):
        raw([Integer(1)])
