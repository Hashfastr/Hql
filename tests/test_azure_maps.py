import json
import logging
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Context import database_registry
from Hql.Database import Kusto, LogAnalytics
from Hql.Helpers import run_query
from Hql.Parser.Sigma import SigmaParser


# examples/deathcon-26/config/maps/azure_fields.hql and azure.hql: Sigma field names
# over Azure Monitor tables. The rows use the tables' real column names.

CONFIG = Path(__file__).parent.parent / 'examples' / 'deathcon-26' / 'config'

SIGNIN = [
    {
        'UserAgent': 'azurehound/2.0', 'ClientAppUsed': 'IMAP', 'UserPrincipalName': 'a@x',
        'ConditionalAccessStatus': 'success', 'AuthenticationProtocol': 'ropc',
        'DeviceDetail': {'trustType': 'Hybrid', 'isCompliant': False, 'deviceId': 'd1'},
    },
    {
        'UserAgent': 'edge', 'ClientAppUsed': 'Browser', 'UserPrincipalName': 'b@x',
        'ConditionalAccessStatus': 'notApplied', 'AuthenticationProtocol': 'none',
        'DeviceDetail': {'trustType': 'None', 'isCompliant': True, 'deviceId': 'd2'},
    },
]

AUDIT = [
    {
        'OperationName': 'Add member to role', 'ActivityDisplayName': 'Add member to role',
        'Category': 'RoleManagement', 'Result': 'success', 'ResultReason': '',
    },
    {
        'OperationName': 'Delete user', 'ActivityDisplayName': 'Delete user',
        'Category': 'UserManagement', 'Result': 'failure', 'ResultReason': 'blocked',
    },
]

ACTIVITY = [
    {
        'OperationNameValue': 'MICROSOFT.NETWORK/DNSZONES/WRITE', 'OperationName': 'Create zone',
        'CategoryValue': 'Administrative', 'ResourceId': '/x/AdFederationService',
    },
    {
        'OperationNameValue': 'MICROSOFT.STORAGE/READ', 'OperationName': 'Read',
        'CategoryValue': 'Policy', 'ResourceId': '/y',
    },
]

RISK = [{'RiskEventType': 'unlikelyTravel'}, {'RiskEventType': 'other'}]

SECURITY = [
    {
        'EventSourceName': 'Service Control Manager', 'NewProcessName': 'C:\\cmd.exe',
        'ParentProcessName': 'C:\\p.exe', 'SubjectUserName': 'bob', 'ServiceName': 'svc',
    },
    {
        'EventSourceName': 'Other', 'NewProcessName': 'C:\\notepad.exe',
        'ParentProcessName': 'C:\\q.exe', 'SubjectUserName': 'eve', 'ServiceName': 'x',
    },
]

PROCESS = [
    {
        'FolderPath': 'C:\\rundll32.exe', 'ProcessCommandLine': 'rundll32 a',
        'ProcessVersionInfoOriginalFileName': 'RUNDLL32.EXE', 'InitiatingProcessFolderPath': 'C:\\p.exe',
        'InitiatingProcessCommandLine': 'p', 'AccountName': 'bob', 'DeviceName': 'h1',
    },
    {
        'FolderPath': 'C:\\notepad.exe', 'ProcessCommandLine': 'notepad',
        'ProcessVersionInfoOriginalFileName': 'NOTEPAD.EXE', 'InitiatingProcessFolderPath': 'C:\\q.exe',
        'InitiatingProcessCommandLine': 'q', 'AccountName': 'eve', 'DeviceName': 'h2',
    },
]

NETWORK = [
    {
        'InitiatingProcessFolderPath': 'C:\\a.exe', 'LocalIP': '10.0.0.1', 'LocalPort': 5000,
        'RemoteIP': '1.1.1.1', 'RemotePort': 443, 'RemoteUrl': 'evil.example', 'DeviceName': 'h1',
    },
    {
        'InitiatingProcessFolderPath': 'C:\\b.exe', 'LocalIP': '10.0.0.2', 'LocalPort': 5001,
        'RemoteIP': '2.2.2.2', 'RemotePort': 80, 'RemoteUrl': 'ok.example', 'DeviceName': 'h2',
    },
]

FILE = [
    {'FolderPath': 'C:\\t\\x.dll', 'InitiatingProcessFolderPath': 'C:\\a.exe', 'DeviceName': 'h1'},
    {'FolderPath': 'C:\\t\\y.txt', 'InitiatingProcessFolderPath': 'C:\\b.exe', 'DeviceName': 'h2'},
]

REGISTRY = [
    {
        'RegistryKey': 'HKLM\\Run', 'RegistryValueData': 'evil', 'ActionType': 'RegistryValueSet',
        'InitiatingProcessFolderPath': 'C:\\a.exe',
    },
    {
        'RegistryKey': 'HKLM\\Other', 'RegistryValueData': 'ok', 'ActionType': 'RegistryKeyCreated',
        'InitiatingProcessFolderPath': 'C:\\b.exe',
    },
]

IMAGE_LOAD = [
    {'FolderPath': 'C:\\evil.dll', 'InitiatingProcessFolderPath': 'C:\\a.exe', 'InitiatingProcessCommandLine': 'a'},
    {'FolderPath': 'C:\\ok.dll', 'InitiatingProcessFolderPath': 'C:\\b.exe', 'InitiatingProcessCommandLine': 'b'},
]


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.mark.parametrize('mapping, data, pred, expected', [
    ('azure_activity', ACTIVITY, "operationName == 'MICROSOFT.NETWORK/DNSZONES/WRITE'", 'Create zone'),
    ('azure_activity', ACTIVITY, "category == 'Policy'", 'MICROSOFT.STORAGE/READ'),
    ('azure_activity', ACTIVITY, "resourceId contains 'AdFederation'", 'Administrative'),
    ('azure_activity', ACTIVITY, "['properties.message'] == 'Read'", 'Policy'),

    ('azure_audit', AUDIT, "operationName == 'Delete user'", 'UserManagement'),
    ('azure_audit', AUDIT, "['properties.message'] == 'Delete user'", 'UserManagement'),
    ('azure_audit', AUDIT, "category == 'RoleManagement'", ''),
    ('azure_audit', AUDIT, "Status == 'failure'", 'UserManagement'),
    ('azure_audit', AUDIT, "['properties.result'] == 'success'", 'RoleManagement'),
    ('azure_audit', AUDIT, "activityType contains 'member'", 'RoleManagement'),
    ('azure_audit', AUDIT, "failure_status_reason == 'blocked'", 'UserManagement'),

    ('azure_signin', SIGNIN, "userAgent contains 'azurehound'", 'a@x'),
    ('azure_signin', SIGNIN, "ClientApp == 'IMAP'", 'a@x'),
    ('azure_signin', SIGNIN, "Username == 'b@x'", 'Browser'),
    ('azure_signin', SIGNIN, "conditionalAccessStatus == 'notApplied'", 'b@x'),
    ('azure_signin', SIGNIN, "['properties.message'] == 'ropc'", 'a@x'),
    ('azure_signin', SIGNIN, "['DeviceDetail.trusttype'] == 'Hybrid'", 'a@x'),
    ('azure_signin', SIGNIN, "['DeviceDetail.deviceId'] == 'd2'", 'b@x'),

    ('azure_risk', RISK, "riskEventType == 'unlikelyTravel'", 'unlikelyTravel'),

    ('azure_security_event', SECURITY, "Image endswith 'cmd.exe'", 'svc'),
    ('azure_security_event', SECURITY, "ParentImage endswith 'q.exe'", 'x'),
    ('azure_security_event', SECURITY, "User == 'bob'", 'svc'),
    ('azure_security_event', SECURITY, "Provider_Name == 'Other'", 'x'),

    ('azure_device_process', PROCESS, "Image endswith 'rundll32.exe'", 'bob'),
    ('azure_device_process', PROCESS, "CommandLine contains 'notepad'", 'eve'),
    ('azure_device_process', PROCESS, "OriginalFileName == 'RUNDLL32.EXE'", 'bob'),
    ('azure_device_process', PROCESS, "ParentImage endswith 'q.exe'", 'eve'),
    ('azure_device_process', PROCESS, "ParentCommandLine == 'p'", 'bob'),
    ('azure_device_process', PROCESS, "Computer == 'h2'", 'eve'),

    ('azure_device_network', NETWORK, 'DestinationPort == 443', '10.0.0.1'),
    ('azure_device_network', NETWORK, "DestinationIp == '2.2.2.2'", '10.0.0.2'),
    ('azure_device_network', NETWORK, "DestinationHostname contains 'evil'", '10.0.0.1'),
    ('azure_device_network', NETWORK, "SourceIp == '10.0.0.2'", 'ok.example'),
    ('azure_device_network', NETWORK, "Image endswith 'b.exe'", '10.0.0.2'),

    ('azure_device_file', FILE, "TargetFilename endswith '.dll'", 'h1'),
    ('azure_device_file', FILE, "Image endswith 'b.exe'", 'h2'),

    ('azure_device_registry', REGISTRY, "TargetObject endswith 'Run'", 'evil'),
    ('azure_device_registry', REGISTRY, "Details == 'ok'", 'HKLM\\Other'),
    ('azure_device_registry', REGISTRY, "EventType == 'RegistryValueSet'", 'HKLM\\Run'),

    ('azure_device_image_load', IMAGE_LOAD, "ImageLoaded endswith 'evil.dll'", 'a'),
    ('azure_device_image_load', IMAGE_LOAD, "Image endswith 'b.exe'", 'b'),
])
def test_field_map(tmp_path, mapping, data, pred, expected):
    (tmp_path / 'table.json').write_text(json.dumps(data))
    config = Config(CONFIG)
    config.add_database('test', {'name': 'table', 'type': 'JSON', 'conf': {'local-base': str(tmp_path)}})

    text = f"import maps.azure_fields; database('table').file('table.json') | map {mapping} | where {pred}"
    out = run_query(text, config)['table.json'].to_dicts()

    # A field that didn't resolve to a column matches no rows
    assert len(out) == 1
    assert expected in out[0].values()


def rule(product, service, detection):
    return '\n'.join([
        'title: test',
        'status: test',
        'logsource:',
        f'    product: {product}',
        f'    {service}',
        'detection:',
        '    sel:',
        *[f'        {i}' for i in detection],
        '    condition: sel',
    ])


class FakeResult(list):
    def __init__(self, rows, columns):
        super().__init__(rows)
        self.columns = [SimpleNamespace(column_name=name, column_type=kind) for name, kind in columns]


class TestSigmaOverKusto:
    '''Rules through the azure.hql header, the Kusto client answering by table.'''

    TABLES = {
        'SigninLogs': (
            [('UserAgent', 'string'), ('ResultType', 'int'), ('Status', 'string'), ('UserPrincipalName', 'string')],
            [['azurehound/2.0', 0, 'Success', 'a@x'], ['edge', 50053, '{"errorCode":50053}', 'b@x']],
        ),
        'AuditLogs': (
            [('OperationName', 'string'), ('TargetResources', 'string'), ('Result', 'string')],
            [['Add member to role', '[{"displayName":"Admins"}]', 'success'], ['Delete user', '[]', 'failure']],
        ),
        'DeviceProcessEvents': (
            [('FolderPath', 'string'), ('ProcessCommandLine', 'string')],
            [['C:\\Windows\\rundll32.exe', 'rundll32 a'], ['C:\\Windows\\notepad.exe', 'notepad']],
        ),
    }

    @pytest.fixture
    def run(self, monkeypatch):
        calls = []
        tables = self.TABLES

        class Client:
            def execute(self, database, query):
                calls.append(query)
                columns, rows = tables[query.split()[0]]
                return SimpleNamespace(primary_results=[FakeResult(rows, columns)])

        class TestKusto(Kusto):
            def __init__(self, config, name='Kusto Database'):
                super().__init__(config, name=name, query_client=Client())

        monkeypatch.setitem(database_registry, 'Kusto', TestKusto)

        def inner(text):
            config = Config(CONFIG)
            config.set_database('kusto', {
                'name': 'kusto',
                'type': 'Kusto',
                'conf': {
                    'database': 'd',
                    'cluster': 'https://c.example.test',
                    'client_id': 'i',
                    'client_secret': 's',
                    'tenant_id': 't',
                },
            })
            config.conf['sigma']['header'] = 'import maps.azure'
            parser = SigmaParser(text, config)
            parser.assemble()
            return HqlCompiler(config, parser.assembly).run().data['kusto'].to_dicts(), calls

        return inner

    def test_signin_user_agent(self, run):
        out, calls = run(rule('azure', 'service: signinlogs', ['userAgent|contains: azurehound']))
        assert [x['Username'] for x in out] == ['a@x']
        assert calls[0].startswith('SigninLogs | where TimeGenerated > ago(1d)')

    def test_signin_unquoted_result_type(self, run):
        out, _ = run(rule('azure', 'service: signinlogs', ['ResultType: 50053']))
        assert [x['Username'] for x in out] == ['b@x']

    def test_signin_status_success(self, run):
        out, _ = run(rule('azure', 'service: signinlogs', ['Status: Success']))
        assert [x['Username'] for x in out] == ['a@x']

    def test_audit_contains_on_dynamic_column(self, run):
        out, calls = run(rule('azure', 'service: auditlogs', ['properties.targetResources|contains: Admins']))
        assert [x['properties.message'] for x in out] == ['Add member to role']
        assert 'tostring(TargetResources)' in calls[0]

    def test_process_creation(self, run):
        out, calls = run(rule('windows', 'category: process_creation', ['Image|endswith: \\rundll32.exe']))
        assert [x['CommandLine'] for x in out] == ['rundll32 a']
        assert "ActionType == 'ProcessCreated'" in calls[0]


class FakeLogsTable:
    def __init__(self, rows, columns):
        self.columns = [name for name, _ in columns]
        self.columns_types = [kind for _, kind in columns]
        self.rows = rows


class TestSigmaOverLogAnalytics:
    '''The same rules with azure_db switched to the loganalytics workspace config.'''

    @pytest.fixture
    def run(self, monkeypatch, tmp_path):
        calls = []
        tables = TestSigmaOverKusto.TABLES

        class Client:
            def query_workspace(self, workspace_id, query, *, timespan):
                calls.append((workspace_id, query))
                columns, rows = tables[query.split()[0]]
                return SimpleNamespace(tables=[FakeLogsTable(rows, columns)])

        class TestLogAnalytics(LogAnalytics):
            def __init__(self, config, name='Log Analytics Database'):
                super().__init__(config, name=name, query_client=Client())

        monkeypatch.setitem(database_registry, 'LogAnalytics', TestLogAnalytics)

        config_dir = tmp_path / 'config'
        shutil.copytree(CONFIG, config_dir)
        azure = config_dir / 'maps' / 'azure.hql'
        text = azure.read_text()
        assert "let azure_db = 'kusto';" in text
        azure.write_text(text.replace("let azure_db = 'kusto';", "let azure_db = 'loganalytics';"))

        def inner(text):
            # The placeholder loganalytics.yml from the workshop config, as is
            config = Config(config_dir)
            config.conf['sigma']['header'] = 'import maps.azure'
            parser = SigmaParser(text, config)
            parser.assemble()
            return HqlCompiler(config, parser.assembly).run().data['loganalytics'].to_dicts(), calls

        return inner

    def test_signin_user_agent(self, run):
        out, calls = run(rule('azure', 'service: signinlogs', ['userAgent|contains: azurehound']))
        assert [x['Username'] for x in out] == ['a@x']
        assert calls[0][0] == '<WORKSPACE_ID>'
        assert calls[0][1].startswith('SigninLogs | where TimeGenerated > ago(1d)')

    def test_audit_contains_on_dynamic_column(self, run):
        out, calls = run(rule('azure', 'service: auditlogs', ['properties.targetResources|contains: Admins']))
        assert [x['properties.message'] for x in out] == ['Add member to role']
        assert 'tostring(TargetResources)' in calls[0][1]

    def test_process_creation(self, run):
        out, calls = run(rule('windows', 'category: process_creation', ['Image|endswith: \\rundll32.exe']))
        assert [x['CommandLine'] for x in out] == ['rundll32 a']
        assert "ActionType == 'ProcessCreated'" in calls[0][1]
