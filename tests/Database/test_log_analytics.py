from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Context import Context, database_registry, get_database
from Hql.Data import Data
from Hql.Database import LogAnalytics
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Operators.Count import Count
from Hql.Parser import Parser
from Hql.Types.Hql import HqlTypes as hqlt


def la_config(**overrides):
    conf = {
        'workspace_id': 'workspace-id',
        'client_id': 'client-id',
        'client_secret': 'client-secret',
        'tenant_id': 'tenant-id',
    }
    conf.update(overrides)
    return {'name': 'la-test', 'type': 'LogAnalytics', 'conf': conf}


class FakeTable:
    '''Shaped like azure.monitor.query.LogsTable'''
    def __init__(self, rows, columns):
        self.name = 'PrimaryResult'
        self.columns = [name for name, _ in columns]
        self.columns_types = [kind for _, kind in columns]
        self.rows = rows


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def query_workspace(self, workspace_id, query, *, timespan):
        self.calls.append((workspace_id, query, timespan))
        return self.response


def result(rows, columns):
    return SimpleNamespace(tables=[FakeTable(rows, columns)])


def test_log_analytics_is_registered_for_database_resolution():
    assert get_database('LogAnalytics') is LogAnalytics


def test_missing_config_is_reported():
    config = la_config()
    del config['conf']['workspace_id']

    with pytest.raises(hqle.ConfigException, match='Log Analytics database missing required config: workspace_id'):
        LogAnalytics(config, query_client=FakeClient(None))


def test_rejects_unsupported_operators():
    adapter = LogAnalytics(la_config(), query_client=FakeClient(None))
    adapter.set_raw_query('Events')
    operator = Count()

    accepted, rejected = adapter.add_op(operator)

    assert accepted is None
    assert rejected is operator


def test_cannot_push():
    assert not LogAnalytics(la_config(), query_client=FakeClient(None)).can_push


def test_raw_query_executes_and_converts_rows():
    client = FakeClient(result([[1, 'first'], [2, 'second']], [('id', 'long'), ('value', 'string')]))
    adapter = LogAnalytics(la_config(), name='la-test', query_client=client)
    adapter.set_raw_query('Events | take 2')

    out = adapter.eval(Context(Data()))

    assert client.calls == [('workspace-id', 'Events | take 2', None)]
    assert out.data['la-test'].to_dicts() == [
        {'id': 1, 'value': 'first'},
        {'id': 2, 'value': 'second'},
    ]


def test_dynamic_and_timespan_strings_match_the_kusto_sdk():
    client = FakeClient(result(
        [
            ['{"trustType":"Hybrid","ids":[1,2]}', '1.02:03:04.5', 'plain'],
            ['[1,2]', '-00:00:01', None],
        ],
        [('DeviceDetail', 'dynamic'), ('Duration', 'timespan'), ('Raw', 'dynamic')],
    ))
    adapter = LogAnalytics(la_config(), query_client=client)
    adapter.set_raw_query('Events')

    rows = adapter.eval(Context(Data())).data[adapter.name].to_dicts()

    assert rows[0]['DeviceDetail'] == {'trustType': 'Hybrid', 'ids': [1, 2]}
    assert rows[1]['DeviceDetail'] == [1, 2]
    assert rows[0]['Duration'] == timedelta(days=1, hours=2, minutes=3, seconds=4, milliseconds=500)
    assert rows[1]['Duration'] == timedelta(seconds=-1)
    # Not JSON, left as the string the API returned
    assert rows[0]['Raw'] == 'plain'


def test_result_types_come_from_column_metadata():
    event_time = datetime(2026, 9, 1, 21, 31, 10, tzinfo=timezone.utc)
    client = FakeClient(result([[None, 1], [event_time, 2]], [('TimeGenerated', 'datetime'), ('EventID', 'int')]))
    adapter = LogAnalytics(la_config(), query_client=client)
    adapter.set_raw_query('SecurityEvent')

    table = adapter.eval(Context(Data())).data[adapter.name]

    assert len(table) == 2
    assert isinstance(table.schema.schema.schema['TimeGenerated'], hqlt.datetime)
    assert isinstance(table.schema.schema.schema['EventID'], hqlt.int)


def test_partial_results_are_kept():
    response = SimpleNamespace(
        partial_data=[FakeTable([[1]], [('id', 'long')])],
        partial_error='query exceeded the result limit',
    )
    adapter = LogAnalytics(la_config(), query_client=FakeClient(response))
    adapter.set_raw_query('Events')

    assert adapter.eval(Context(Data())).data[adapter.name].to_dicts() == [{'id': 1}]


def test_empty_response_is_an_empty_table():
    adapter = LogAnalytics(la_config(), query_client=FakeClient(SimpleNamespace(tables=[])))
    adapter.set_raw_query('Events')

    assert adapter.eval(Context(Data())).data[adapter.name].to_dicts() == []


def test_row_width_must_match_columns():
    adapter = LogAnalytics(la_config(), query_client=FakeClient(result([[1, 2]], [('id', 'long')])))
    adapter.set_raw_query('Events')

    with pytest.raises(hqle.QueryException, match='does not match its columns'):
        adapter.eval(Context(Data()))


def test_requires_raw_query_before_evaluation():
    adapter = LogAnalytics(la_config(), query_client=FakeClient(None))

    with pytest.raises(hqle.QueryException, match='requires a raw query'):
        adapter.eval(Context(Data()))


def test_timebound_becomes_the_query_timespan():
    client = FakeClient(result([], [('id', 'long')]))
    adapter = LogAnalytics(la_config(), query_client=client)
    adapter.set_raw_query('Events')
    start, end = datetime(2026, 1, 1), datetime(2026, 1, 2)

    acc, rej = adapter.add_timebound(start, end)
    acc.eval(Context(Data()))

    assert rej is None
    assert client.calls == [('workspace-id', 'Events', (start, end))]


def test_timebound_ignored_when_not_timeseries():
    client = FakeClient(result([], [('id', 'long')]))
    adapter = LogAnalytics({**la_config(), 'timeseries': False}, query_client=client)
    adapter.set_raw_query('Events')

    adapter.add_timebound(datetime(2026, 1, 1), datetime(2026, 1, 2))
    adapter.eval(Context(Data()))

    assert client.calls[0][2] is None


def test_copy_preserves_query_and_shares_sdk_client():
    client = FakeClient(None)
    adapter = LogAnalytics(la_config(), query_client=client)
    adapter.set_raw_query('Events')

    copied = deepcopy(adapter)

    assert copied is not adapter
    assert copied.query_client is client
    assert copied.to_dict()['query'] == 'Events'
    assert copied.to_dict()['workspace_id'] == 'workspace-id'


def test_where_is_pushed_onto_the_raw_query(monkeypatch):
    client = FakeClient(result([[2, '{"a":{"b":"y"}}']], [('id', 'long'), ('d', 'dynamic')]))

    class TestLogAnalytics(LogAnalytics):
        def __init__(self, config, name='Log Analytics Database'):
            super().__init__(config, name=name, query_client=client)

    monkeypatch.setitem(database_registry, 'LogAnalytics', TestLogAnalytics)
    config = Config()
    config.set_database('la', la_config())
    parser = Parser("database('la').raw('Events')\n| where id == 2")
    parser.assemble()

    out = HqlCompiler(config, parser.assembly).run().data

    assert client.calls == [('workspace-id', 'Events\n| where id == 2', None)]
    assert out['la'].to_dicts() == [{'id': 2, 'd': {'a': {'b': 'y'}}}]


def test_index_queries_the_table_and_pushes_take(monkeypatch):
    client = FakeClient(result([[1]], [('id', 'long')]))

    class TestLogAnalytics(LogAnalytics):
        def __init__(self, config, name='Log Analytics Database'):
            super().__init__(config, name=name, query_client=client)

    monkeypatch.setitem(database_registry, 'LogAnalytics', TestLogAnalytics)
    config = Config()
    config.set_database('la', la_config())
    parser = Parser("database('la').index('SigninLogs')\n| take 1")
    parser.assemble()

    out = HqlCompiler(config, parser.assembly).run().data

    assert client.calls == [('workspace-id', 'SigninLogs\n| take 1', None)]
    assert out['la'].to_dicts() == [{'id': 1}]


def test_auth_defaults_to_azcli_without_app_credentials():
    config = la_config()
    for key in ('client_id', 'client_secret', 'tenant_id'):
        del config['conf'][key]

    assert LogAnalytics(config, query_client=FakeClient(None)).auth == 'azcli'


def test_auth_defaults_to_secret_with_app_credentials():
    assert LogAnalytics(la_config(), query_client=FakeClient(None)).auth == 'secret'


def test_secret_auth_requires_app_credentials():
    config = la_config()
    del config['conf']['client_secret']

    with pytest.raises(hqle.ConfigException, match='missing required config: client_secret'):
        LogAnalytics(config, query_client=FakeClient(None))


def test_explicit_azcli_ignores_app_credentials():
    adapter = LogAnalytics(la_config(auth='azcli', client_secret=''), query_client=FakeClient(None))

    assert adapter.auth == 'azcli'


def test_unknown_auth_is_rejected():
    with pytest.raises(hqle.ConfigException, match='auth must be one of secret, azcli'):
        LogAnalytics(la_config(auth='password'), query_client=FakeClient(None))


class TestSigmaPushdown:
    '''Sigma through a class of lets over one Log Analytics table, as maps/azure.hql does.'''

    HEADER = '''
let base = database('la').index('DeviceRegistryEvents')
    | project-rename TargetObject = RegistryKey, EventType = ActionType;
class windows = {
    let registry_add = base | where EventType == 'RegistryKeyCreated';
    let registry_set = base | where EventType == 'RegistryValueSet';
};
'''

    @pytest.fixture
    def run(self, monkeypatch):
        client = FakeClient(result([], [('TargetObject', 'string'), ('EventType', 'string')]))

        class TestLogAnalytics(LogAnalytics):
            def __init__(self, config, name='Log Analytics Database'):
                super().__init__(config, name=name, query_client=client)

        monkeypatch.setitem(database_registry, 'LogAnalytics', TestLogAnalytics)

        def inner(detection):
            from Hql.Parser.Sigma import SigmaParser

            config = Config()
            config.set_database('la', la_config())
            config.load_sigma('test', {'header': self.HEADER})
            text = (
                'title: t\nlogsource:\n    product: windows\n    category: registry_set\n'
                f'detection:\n    selection:\n        {detection}\n    condition: selection\n'
            )
            parser = SigmaParser(text, config)
            parser.assemble()
            HqlCompiler(config, parser.assembly, time=False).run()
            return [query for _, query, _ in client.calls]

        return inner

    def test_where_is_pushed_past_project_rename(self, run):
        # renamed names are mapped back to the table's columns
        assert run(r"TargetObject|endswith: '\Run'") == [
            'DeviceRegistryEvents\n| where ActionType == "RegistryValueSet"\n| where RegistryKey endswith "\\\\Run"'
        ]

    def test_lets_on_one_table_keep_their_own_filters(self, run):
        # registry_add's where used to be pushed into the shared database too
        query, = run("TargetObject: x")
        assert 'RegistryKeyCreated' not in query

    def test_where_on_a_renamed_away_name_is_split(self, run):
        # EventType is the rename's new name, ActionType the old one it removes; only
        # the term on the removed name has to stay local
        query, = run("TargetObject: x\n        ActionType: y")
        assert query == (
            'DeviceRegistryEvents\n| where ActionType == "RegistryValueSet"\n| where RegistryKey == "x"'
        )
