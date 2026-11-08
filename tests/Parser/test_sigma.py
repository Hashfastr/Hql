import json
import logging

import pytest

from Hql.Config import Config
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Hac.Engine import Detection
from Hql.Helpers import run_query


# Sigma rules end to end over a JSON database, through the sigma header's class.
# Each case was a rule that failed against a live Log Analytics workspace.

ROWS = [
    {'id': 1, 'IPAddress': '10.1.2.3', 'ResultType': 0, 'Asn': '8075',
     'CommandLine': 'C:\\Windows\\system32\\cmd.exe /c whoami', 'UserAgent': 'Mozilla/5.0', 'Extra': 'x',
     'IsInteractive': True},
    {'id': 2, 'IPAddress': 'fe80::1', 'ResultType': 50126, 'Asn': '16509',
     'CommandLine': '', 'UserAgent': 'azurehound/2.0', 'Extra': None, 'IsInteractive': False},
    {'id': 3, 'IPAddress': '192.168.1.1', 'ResultType': 0, 'Asn': '8075',
     'CommandLine': 'powershell -e SQBFAFgA', 'UserAgent': 'python-requests', 'Extra': 'y',
     'IsInteractive': True},
]


@pytest.fixture
def conf(tmp_path):
    (tmp_path / 't.json').write_text(json.dumps(ROWS))

    config = Config()
    config.add_database('test', {
        'name': 'json',
        'type': 'JSON',
        # no timestamps, HaC's time window would drop every row
        'timeseries': False,
        'conf': {'local-base': str(tmp_path)},
    })
    config.load_sigma('test', {'header': "class test = { let events = database('json').file('t.json') }"})
    return config


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def rule(detection, extra=''):
    return f'''title: test
id: 00000000-0000-0000-0000-000000000000
status: test
description: test
logsource:
    product: test
    service: events
detection:
{detection}
{extra}'''


def ids(conf, text):
    return sorted(i['id'] for i in run_query(text, conf)['t.json'].to_dicts())


def indent(text):
    return '\n'.join('    ' + x for x in text.strip('\n').splitlines())


def run(conf, detection):
    return ids(conf, rule(indent(detection)))


class TestCondition:
    def test_hyphenated_selection_names(self, conf):
        assert run(conf, '''
selection-ok:
    ResultType: 0
filter-ip:
    IPAddress: 192.168.1.1
condition: selection-ok and not filter-ip
''') == [1]

    def test_undefined_selection_is_named(self, conf):
        with pytest.raises(hqle.QueryException, match='undefined selection filter'):
            run(conf, '''
selection:
    ResultType: 0
condition: selection and not filter
''')

    def test_trailing_text_is_an_error_not_dropped(self, conf):
        # previously parsed as just 'selection', silently losing the rest
        with pytest.raises(hqle.QueryException, match='Invalid Sigma condition'):
            run(conf, '''
selection:
    ResultType: 0
filter:
    id: 3
condition: selection AND NOT filter
''')

    def test_n_of(self, conf):
        assert run(conf, '''
sel_a:
    ResultType: 0
sel_b:
    Asn: '8075'
sel_c:
    id: 3
condition: 2 of sel_*
''') == [1, 3]

    def test_condition_list_matches_any(self, conf):
        assert run(conf, '''
sel_a:
    id: 1
sel_b:
    id: 2
condition:
    - sel_a
    - sel_b
''') == [1, 2]


class TestSelection:
    def test_keywords_search_every_field(self, conf):
        assert run(conf, '''
keywords:
    - azurehound
    - whoami
condition: keywords
''') == [1, 2]

    def test_cidr_v4_and_v6(self, conf):
        assert run(conf, '''
selection:
    IPAddress|cidr:
        - 10.0.0.0/8
        - fe80::/10
condition: selection
''') == [1, 2]

    def test_exists(self, conf):
        assert run(conf, '''
selection:
    Extra|exists: true
condition: selection
''') == [1, 3]
        assert run(conf, '''
selection:
    Extra|exists: false
condition: selection
''') == [2]

    def test_exists_on_missing_field(self, conf):
        assert run(conf, '''
selection:
    Missing|exists: false
condition: selection
''') == [1, 2, 3]

    def test_contains_null(self, conf):
        assert run(conf, '''
selection:
    Extra|contains:
        - null
        - y
condition: selection
''') == [2, 3]

    def test_empty_string_value(self, conf):
        assert run(conf, '''
selection:
    CommandLine: ''
condition: selection
''') == [2]

    def test_quoted_number_against_int_field(self, conf):
        assert run(conf, '''
selection:
    ResultType: '0'
condition: selection
''') == [1, 3]

    def test_number_against_string_field(self, conf):
        assert run(conf, '''
selection:
    Asn:
        - 8075
condition: selection
''') == [1, 3]

    def test_bool_value(self, conf):
        # YAML true is a bool, which is also an int, and used to compile to 1
        assert run(conf, '''
selection:
    IsInteractive: true
condition: selection
''') == [1, 3]

    def test_backslashes_are_literal(self, conf):
        assert run(conf, '''
selection:
    CommandLine|contains: '\\system32\\cmd.exe'
condition: selection
''') == [1]

    def test_base64offset(self, conf):
        # 'IEX' UTF-16 encoded is in row 3's encoded command
        assert run(conf, '''
selection:
    CommandLine|wide|base64offset|contains: 'IEX'
condition: selection
''') == [3]


class TestErrors:
    def test_invalid_sigma_reports_the_sigma_error(self, conf):
        text = rule(indent('''
selection:
    ResultType: 0
condition: selection
'''), extra='status: deprecated').replace('status: test\n', '')

        with pytest.raises(hqle.QueryException, match='Invalid Sigma rule: Sigma rule is deprecated'):
            run_query(text, conf)

        detection = Detection(text, 'api', conf, no_hac=True)
        with pytest.raises(hqle.QueryException, match='deprecated'):
            detection.run()

    def test_invalid_yaml_is_still_sigma(self, conf):
        text = rule(indent('''
selection:
    ResultType: 0
condition: selection | count() by IPAddress > 10: bad
'''))
        with pytest.raises(hqle.QueryException, match='not valid YAML'):
            run_query(text, conf)

    def test_multi_document_rule(self, conf):
        text = rule(indent('''
selection:
    ResultType: 0
condition: selection
''')) + '\n---\ntitle: correlation\n'
        with pytest.raises(hqle.QueryException, match='Multi-document'):
            run_query(text, conf)

    def test_description_is_optional(self, conf):
        text = rule(indent('''
selection:
    id: 1
condition: selection
''')).replace('description: test\n', '')
        assert ids(conf, text) == [1]

        detection = Detection(text, 'api', conf, no_hac=True)
        assert detection.sigma
        assert detection.hac.asm['description'] == ''


class TestDeparse:
    TEXT = rule(indent('''
selection:
    id: 1
condition: selection
'''))
    HEADER = "class test = { let events = database('json').file('t.json') }"

    def check(self, out):
        # Header as written, not its assembled statements, then only the rule body
        header, body = out.split('*/\n\n', 1)[1].split('\n', 1)
        assert header == self.HEADER + ';'
        assert body == "product('test').service('events')\n| where id == 1"

    def test_run_query_keeps_header_unexpanded(self, conf):
        self.check(run_query(self.TEXT, conf, deparse=True))

    def test_detection_keeps_header_unexpanded(self, conf):
        self.check(Detection(self.TEXT, 'api', conf).deparse())

    def test_deparse_compiles_back(self, conf):
        out = run_query(self.TEXT, conf, deparse=True)
        assert sorted(i['id'] for i in run_query(out, conf)['t.json'].to_dicts()) == [1]
