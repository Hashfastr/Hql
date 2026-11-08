from Hql.Compiler import HqlCompiler, KustoCompiler
from Hql.Config import Config
from Hql.Parser.Sigma import SigmaParser


RULE = r'''
title: Kusto test
status: test
logsource:
    category: process_creation
    product: windows
detection:
{detection}
'''


def compile_sigma(detection):
    parser = SigmaParser(RULE.format(detection=detection), Config())
    parser.assemble()
    where = parser.assembly.statements[-1].root.pipes[0]
    desc, _ = HqlCompiler(Config()).compile(where)
    compiler = KustoCompiler()
    compiler.add_index('Events')
    _, rej = compiler.add_op(desc)
    query = compiler.simple_compile()
    assert query.startswith('Events\n| where ')
    return query.removeprefix('Events\n| where '), rej


# BinaryLogic doesn't preserve order
def clauses(query):
    return sorted(query.split(' and '))


def test_index_without_operators_is_the_table():
    compiler = KustoCompiler()
    compiler.add_index('Events')
    assert compiler.simple_compile() == 'Events'


def test_endswith_escapes_backslash():
    query, rej = compile_sigma(r'''    selection:
        Image|endswith: '\cmd.exe'
    condition: selection''')
    assert rej is None
    assert query == r"Image endswith '\\cmd.exe'"


def test_contains_any_and_all():
    query, _ = compile_sigma(r'''    selection:
        CommandLine|contains:
            - 'a'
            - "it's"
    condition: selection''')
    assert query in (
        r"(CommandLine contains 'a' or CommandLine contains 'it\'s')",
        r"(CommandLine contains 'it\'s' or CommandLine contains 'a')",
    )

    query, _ = compile_sigma(r'''    selection:
        CommandLine|contains|all|cased:
            - 'a'
            - 'b'
    condition: selection''')
    assert query == "(CommandLine contains_cs 'a' and CommandLine contains_cs 'b')"


def test_not_and_multi_value_equality():
    query, rej = compile_sigma(r'''    selection:
        Image|startswith: 'C:\x'
    filter:
        User:
            - SYSTEM
            - LOCAL SERVICE
    condition: selection and not filter''')
    assert rej is None
    selection, negated = clauses(query)
    assert selection == r"Image startswith 'C:\\x'"
    assert negated in (
        "not(User == 'SYSTEM' or User == 'LOCAL SERVICE')",
        "not(User == 'LOCAL SERVICE' or User == 'SYSTEM')",
    )


def test_equality_operators():
    from Hql.Expressions.Logic import Equality
    from Hql.Expressions.Literals import Integer, StringLiteral
    from Hql.Expressions.References import NamedReference

    compiler = KustoCompiler()
    user = NamedReference('User')
    strs = [StringLiteral('a'), StringLiteral('b')]

    def run(expr):
        acc, rej = compiler.compile(expr)
        assert rej is None
        return compiler.compile(acc, prep=False)[0]

    assert run(Equality(user, strs)) == "User in ('a', 'b')"
    assert run(Equality(user, strs, cs=False, neq=True)) == "User !in~ ('a', 'b')"
    assert run(Equality(user, [StringLiteral('a')], cs=False)) == "User =~ 'a'"
    # =~ is string only
    assert run(Equality(user, [Integer(1)], cs=False, neq=True)) == "User != 1"


def test_relational_regex_and_null():
    query, rej = compile_sigma(r'''    selection:
        Count|gte: 3
        Name|re|i: '^a\.b$'
        Field: null
    condition: selection''')
    assert rej is None
    assert clauses(query) == [
        "Count >= 3",
        r"Name matches regex '(?i)^a\\.b$'",
        "isempty(Field)",
    ]


def test_escaped_names_and_paths():
    from Hql.Expressions.Logic import Equality
    from Hql.Expressions.Literals import StringLiteral
    from Hql.Expressions.References import EscapedNamedReference, NamedReference, Path

    compiler = KustoCompiler()
    lh = Path([NamedReference('DeviceDetail'), NamedReference('trust-type')])
    acc, _ = compiler.compile(Equality(lh, [StringLiteral('a')]), prep=False)
    assert acc == "DeviceDetail['trust-type'] == 'a'"

    acc, _ = compiler.compile(EscapedNamedReference('where'), prep=False)
    assert acc == "['where']"


def test_cidr_is_pushed_down_null_safe():
    query, rej = compile_sigma(r'''    selection:
        EventID: 4624
    filter:
        IpAddress|cidr:
            - '10.0.0.0/8'
            - 'fe80::/10'
    condition: selection and not filter''')
    assert rej is None
    # Kusto's null for an address of the other version is coalesced to Hql's false,
    # or not() would drop the public addresses this is meant to keep
    assert "not(" in query
    assert "coalesce(ipv4_is_in_range(IpAddress, \"10.0.0.0/8\"), false)" in query
    assert "coalesce(ipv6_is_in_range(IpAddress, \"fe80::/10\"), false)" in query


def test_ipv4_mapped_range_stays_local():
    # Kusto puts IPv4 addresses in ::ffff:0:0/96, Hql doesn't
    query, rej = compile_sigma(r'''    selection:
        EventID: 4624
        IpAddress|cidr: '::ffff:0:0/96'
    condition: selection''')
    assert query == 'EventID == 4624'
    assert rej is not None


def compile_pipes(hql):
    from Hql.Parser import Parser

    parser = Parser(hql, 'test')
    parser.assemble(target='emptyPipedExpression')
    compiler = KustoCompiler()
    compiler.add_index('Events')

    rejected = []
    for op in parser.assembly.pipes:
        desc, _ = HqlCompiler(Config()).compile(op)
        # Like the database, everything after a rejection stays local
        if rejected:
            rejected.append(desc.get_op())
            continue
        _, rej = compiler.add_op(desc)
        if rej is not None:
            rejected.append(rej)
    return compiler.simple_compile().removeprefix('Events'), rejected


def test_table_map_operators_are_pushed():
    query, rej = compile_pipes(
        "| extend Status = iff(ResultType == '0', 'Success', tostring(Status)), ResultType = toint(ResultType)"
        "| extend ['DeviceDetail.trusttype'] = DeviceDetail.trustType"
        "| project-rename userAgent = UserAgent"
        "| project TimeGenerated, Agent = userAgent, Status"
    )
    assert rej == []
    assert query.split('\n| ')[1:] == [
        'extend Status = iff(ResultType == "0", "Success", tostring(Status)), ResultType = toint(ResultType)',
        "extend ['DeviceDetail.trusttype'] = DeviceDetail.trustType",
        'project-rename userAgent = UserAgent',
        'project TimeGenerated, Agent = userAgent, Status',
    ]


def test_inexpressible_operators_stay_local():
    # A function KQL isn't given, assigning into a dynamic column, and renaming a path
    for hql in (
        "| extend a = base64(b)",
        "| extend DeviceDetail.trustType = 'x'",
        "| project-rename a = DeviceDetail.trustType",
        "| project-away a",
    ):
        query, rej = compile_pipes(hql)
        assert query == '', hql
        assert len(rej) == 1, hql


def test_operators_after_a_local_one_stay_local():
    query, rej = compile_pipes("| extend a = toint(b) | summarize count() by a | project a")
    assert query == '\n| extend a = toint(b)'
    assert [x.type for x in rej] == ['Summarize', 'Project']
