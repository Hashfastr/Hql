import json
import logging

import pytest

from Hql.Config import Config
from Hql.Helpers import run_query


# End to end queries through the parser, compiler and operators over a JSON database.
# These cover the seams between areas, unit tests cover each piece on its own.

ROWS = [
    {'a': 1, 'b': 'x', 'c': [1, 2, 3], 'ip': '10.1.2.3'},
    {'a': 3, 'b': 'y', 'c': [], 'ip': '192.168.1.1'},
    {'a': 2, 'b': None, 'c': None, 'ip': '10.255.0.1'},
    {'a': None, 'b': 'z', 'c': [4], 'ip': '11.0.0.1'},
]

LEFT = [{'a': 1}, {'a': 3}, {'a': 2}]
RIGHT = [{'a': 1, 'k': 'one'}, {'a': 2, 'k': 'two'}, {'a': 5, 'k': 'five'}]


@pytest.fixture
def conf(tmp_path):
    (tmp_path / 't.json').write_text(json.dumps(ROWS))
    (tmp_path / 'l.json').write_text(json.dumps(LEFT))
    (tmp_path / 'u.json').write_text(json.dumps(RIGHT))

    config = Config()
    config.add_database('test', {
        'name': 'json',
        'type': 'JSON',
        'conf': {'local-base': str(tmp_path)},
    })
    config.load_general('test', {'default_db': 'json'})
    return config


@pytest.fixture(autouse=True)
def quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def query(conf, text):
    return run_query(text, conf)


def rows(conf, text, name='t.json'):
    return query(conf, text)[name].to_dicts()


def col(conf, text, field, name='t.json'):
    return [i[field] for i in rows(conf, text, name)]


T = "database('json').file('t.json')"
L = "database('json').file('l.json')"
U = "database('json').file('u.json')"


class TestArithmetic:
    def test_extend_computes_values(self, conf):
        assert col(conf, f'{T} | extend d = a * 2 + 1 | project d', 'd') == [3, 7, 5, None]

    def test_where_on_arithmetic(self, conf):
        assert col(conf, f'{T} | where a + 1 > 3 | project a', 'a') == [3]


class TestConstantFunctions:
    def test_typecast_literal_in_where(self, conf):
        assert col(conf, f"{T} | where a == toint('3') | project a", 'a') == [3]

    def test_literal_function_in_extend(self, conf):
        assert col(conf, f"{T} | extend s = tolower('ABC') | project s", 's') == ['abc'] * 4

    def test_ip4subnet_equality(self, conf):
        text = f"{T} | extend ip = toip4(ip) | where ip == ip4subnet('10.0.0.0/8') | count"
        assert rows(conf, text) == [{'Count': 2}]

    def test_ip4subnet_inequality(self, conf):
        text = f"{T} | extend ip = toip4(ip) | where ip != ip4subnet('10.0.0.0/8') | count"
        assert rows(conf, text) == [{'Count': 2}]


class TestTimespan:
    def test_timespan_literal(self, conf):
        from datetime import timedelta
        assert col(conf, f'{T} | extend t = 90m | project t | take 1', 't') == [timedelta(minutes=90)]


class TestSummarize:
    def test_named_aggregate(self, conf):
        out = rows(conf, f'{T} | summarize c = count() by b')
        assert sorted(i['c'] for i in out) == [1, 1, 1, 1]
        assert set(out[0]) == {'b', 'c'}

    def test_named_aggregate_without_by(self, conf):
        assert rows(conf, f'{T} | summarize c = count()') == [{'c': 4}]

    def test_repeated_unnamed_aggregates(self, conf):
        assert rows(conf, f'{T} | summarize count(), count()') == [{'count_': 4, 'count_1': 4}]

    def test_named_make_mv(self, conf):
        out = rows(conf, f'{T} | summarize m = make_mv(a) by b')
        assert sorted(i['m'][0] for i in out if i['m'][0] is not None) == [1, 2, 3]


class TestOperators:
    def test_range(self, conf):
        out = query(conf, 'range x from 1 to 5 step 2')
        assert [i['x'] for i in next(iter(out)).to_dicts()] == [1, 3, 5]

    def test_datatable(self, conf):
        out = query(conf, "datatable (a: int, b: string) [1, 'x', 2, 'y'] | take 1")
        assert next(iter(out)).to_dicts() == [{'a': 1, 'b': 'x'}]

    def test_top(self, conf):
        assert col(conf, f'{T} | top 2 by a desc | project a', 'a') == [3, 2]

    def test_mv_expand(self, conf):
        assert col(conf, f'{T} | mv-expand c | project c', 'c') == [1, 2, 3, None, None, 4]

    def test_union(self, conf):
        out = query(conf, f'union {T}, {U} | count')
        assert sum(i['Count'] for t in out for i in t.to_dicts()) == 7


class TestJoin:
    def test_rightanti(self, conf):
        assert rows(conf, f'{L} | join kind=rightanti ({U}) on a', 'l.json') == [{'a': 5, 'k': 'five'}]

    def test_fullouter_keeps_right_only_rows(self, conf):
        assert rows(conf, f'{L} | join kind=fullouter ({U}) on a | count', 'l.json') == [{'Count': 4}]
