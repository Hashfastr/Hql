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


class TestDefaultDatabase:
    def test_bare_file_uses_default_db(self, conf):
        assert rows(conf, "file('t.json') | count") == [{'Count': 4}]

    def test_bare_file_with_let(self, conf):
        assert rows(conf, "let f = 't.json'; file(f) | count") == [{'Count': 4}]


class TestNumericLiterals:
    @pytest.fixture
    def nums(self, conf, tmp_path):
        (tmp_path / 'f.json').write_text(json.dumps([{'x': 1.1, 'n': 3000000000}, {'x': 2.5, 'n': 1}]))
        return conf

    def test_float_literal_matches_double_column(self, nums):
        assert rows(nums, "database('json').file('f.json') | where x == 1.1 | count", 'f.json') == [{'Count': 1}]

    def test_large_integer_literal(self, nums):
        assert rows(nums, "database('json').file('f.json') | where n == 3000000000 | count", 'f.json') == [{'Count': 1}]


class TestTake:
    def test_negative_limit_rejected(self, conf):
        from Hql.Exceptions import HqlExceptions as hqle
        with pytest.raises(hqle.CompilerException):
            query(conf, f'{T} | take -1')


# ---------------------------------------------------------------------------
# Mappings, the query uses EventID while the data has event.id
# ---------------------------------------------------------------------------

EVENTS = [
    {'event': {'id': 4624, 'action': 'logon'}, 'host': 'h1'},
    {'event': {'id': 4625, 'action': 'failed'}, 'host': 'h2'},
    {'event': {'id': 4624, 'action': 'logon'}, 'host': 'h3'},
]

ECS = 'map ecs = { EventID: event.id, Action: event.action };'
E = "database('json').file('e.json')"


def map_op_parses():
    from Hql.Parser.grammar.HqlParser import HqlParser
    return hasattr(HqlParser, 'MapOperatorContext')


def mapped(conf, pipes, maps=ECS, source=E, name='e.json'):
    '''
    Runs {maps} {source} | map ecs | {pipes}

    Until the parser is regenerated with the map operator, the operator is
    spliced into the parsed query instead.
    '''
    from Hql.Compiler import HqlCompiler
    from Hql.Expressions.References import NamedReference
    from Hql.Operators import Map
    from Hql.Parser import Parser

    if map_op_parses():
        text = f'{maps} {source} | map ecs' + (f' | {pipes}' if pipes else '')
        return query(conf, text)[name].to_dicts()

    parser = Parser(f'{maps} {source}' + (f' | {pipes}' if pipes else ''))
    parser.assemble()
    parser.assembly.statements[-1].root.pipes.insert(0, Map([NamedReference('ecs')]))
    return HqlCompiler(conf, parser.assembly).run().data[name].to_dicts()


class TestMapping:
    @pytest.fixture
    def events(self, conf, tmp_path):
        (tmp_path / 'e.json').write_text(json.dumps(EVENTS))
        return conf

    def test_results_use_mapped_names(self, events):
        assert mapped(events, '') == [
            {'EventID': 4624, 'Action': 'logon', 'host': 'h1'},
            {'EventID': 4625, 'Action': 'failed', 'host': 'h2'},
            {'EventID': 4624, 'Action': 'logon', 'host': 'h3'},
        ]

    def test_where_on_mapped_name(self, events):
        out = mapped(events, 'where EventID == 4625')
        assert [x['host'] for x in out] == ['h2']

    def test_project_mapped_and_unmapped(self, events):
        assert mapped(events, 'where EventID == 4625 | project EventID, host') == [{'EventID': 4625, 'host': 'h2'}]

    def test_summarize_by_mapped_name(self, events):
        out = mapped(events, 'summarize count() by Action')
        assert sorted(x['Action'] for x in out) == ['failed', 'logon']

    def test_sort_by_mapped_name(self, events):
        out = mapped(events, 'sort by EventID desc | take 1')
        assert out[0]['EventID'] == 4625

    def test_extend_mapped_name(self, events):
        out = mapped(events, 'extend EventID = EventID + 1')
        assert [x['EventID'] for x in out] == [4625, 4626, 4625]

    def test_undefined_mapping_raises(self, events):
        from Hql.Exceptions import HqlExceptions as hqle
        with pytest.raises(hqle.CompilerException):
            mapped(events, 'take 1', maps='')

    def test_multi_destination_in_where_raises(self, events):
        from Hql.Exceptions import HqlExceptions as hqle
        with pytest.raises(hqle.CompilerException):
            mapped(events, 'where Host == "h1"', maps='map ecs = { Host: (host, hostname) };')

    def test_operators_before_map_use_data_names(self, events):
        from Hql.Compiler import HqlCompiler
        from Hql.Expressions.References import NamedReference
        from Hql.Operators import Map
        from Hql.Parser import Parser

        parser = Parser(f'{ECS} {E} | where event.id == 4625 | project event.id, host')
        parser.assemble()
        parser.assembly.statements[-1].root.pipes.insert(1, Map([NamedReference('ecs')]))
        out = HqlCompiler(events, parser.assembly).run().data['e.json'].to_dicts()

        assert out == [{'EventID': 4625, 'host': 'h2'}]

    def test_filter_after_mapped_let_is_remapped(self, events):
        from Hql.Compiler import HqlCompiler
        from Hql.Expressions.References import NamedReference
        from Hql.Operators import Map
        from Hql.Parser import Parser

        parser = Parser(f'{ECS} let x = {E} | project EventID, host; x | where EventID == 4625')
        parser.assemble()
        parser.assembly.statements[1].root.pipes.insert(0, Map([NamedReference('ecs')]))
        compiler = HqlCompiler(events, parser.assembly)

        # The outer filter is moved up past the rename back, so it uses event.id
        ops = [x.deparse() for x in compiler.root.ops]
        assert ops[0] == 'where event.id == 4625'
        assert ops[-1] == 'project-rename EventID=event.id, Action=event.action'
        assert compiler.run().data['e.json'].to_dicts() == [{'EventID': 4625, 'host': 'h2'}]

    def test_mapped_where_is_pushed_to_database(self):
        from Hql.Compiler import BranchDescriptor, Compiler, HqlCompiler
        from Hql.Config import Config
        from Hql.Database.Database import Database
        from Hql.Expressions.References import NamedReference
        from Hql.Operators import Map, Where
        from Hql.Parser import Parser

        # Accepts filters like a backend would, rejects everything else
        class WhereCompiler(Compiler):
            def add_op(self, op):
                if isinstance(op, BranchDescriptor):
                    op = op.get_op()
                if isinstance(op, Where):
                    self.ops.append(op)
                    return op, None
                return None, op

        db = Database({}, name='db')
        db.compiler = WhereCompiler()

        parser = Parser(f'{ECS} db | where EventID == 4624')
        parser.assemble()
        parser.assembly.statements[-1].root.pipes.insert(0, Map([NamedReference('ecs')]))

        compiler = HqlCompiler(Config())
        compiler.ctx.symbol_table[NamedReference('db')] = db
        compiler.Query(parser.assembly)

        assert [x.deparse() for x in db.compiler.ops] == ['where event.id == 4624']
        assert [x.deparse() for x in compiler.root.ops] == ['project-rename EventID=event.id, Action=event.action']
