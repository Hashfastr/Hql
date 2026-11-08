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
    compiler.set_index('Events')
    _, rej = compiler.add_op(desc)
    query = compiler.simple_compile()
    assert query.startswith('Events\n| where ')
    return query.removeprefix('Events\n| where '), rej


# BinaryLogic doesn't preserve order
def clauses(query):
    return sorted(query.split(' and '))


def test_index_without_operators_is_the_table():
    compiler = KustoCompiler()
    compiler.set_index('Events')
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
