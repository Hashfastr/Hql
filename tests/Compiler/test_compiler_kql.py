from __future__ import annotations

import datetime

from Hql.Compiler import KQLCompiler
from Hql.Expressions.Literals import Bool, Datetime, Float, Integer, Multivalue, StringLiteral
from Hql.Expressions.Logic import BetweenEquality, BinaryLogic, Equality, Not, Regex, Relational, Substring
from Hql.Expressions.References import NamedReference, Path, Wildcard
from Hql.Functions.null import isnull
from Hql.Operators.Where import Where


def eq(field, value, *, neq=False):
    return Equality(NamedReference(field), value, neq=neq)


def compile_where(*exprs):
    compiler = KQLCompiler()
    rejected = [compiler.add_op(Where(x))[1] for x in exprs]
    return compiler.simple_compile(), rejected


# BinaryLogic doesn't preserve order, so compile each predicate on its own
def compile_each(*exprs):
    return [compile_where(x)[0] for x in exprs]


def test_empty_query_matches_everything():
    assert KQLCompiler().simple_compile() == ''


def test_string_equality_is_quoted_and_escaped():
    query, rejected = compile_where(eq('user', StringLiteral('al"ice\\x')))

    assert query == r'user: "al\"ice\\x"'
    assert rejected == [None]


def test_literal_values():
    queries = compile_each(
        eq('count', Integer(5)),
        eq('ratio', Float(1.5)),
        eq('enabled', Bool(True)),
    )

    assert queries == ['count: 5', 'ratio: 1.5', 'enabled: true']


def test_multi_value_and_negated_equality():
    query, _ = compile_where(eq('user', [StringLiteral('a'), StringLiteral('b')], neq=True))
    assert query == 'not user: ("a" or "b")'


def test_multivalue_literal_is_flattened():
    query, _ = compile_where(eq('port', Multivalue([Integer(80), Integer(443)])))
    assert query == 'port: (80 or 443)'


def test_negated_compile_does_not_mutate_expression():
    compiler = KQLCompiler()
    compiler.add_op(Where(eq('user', StringLiteral('a'), neq=True)))

    assert compiler.simple_compile() == 'not user: "a"'
    assert compiler.simple_compile() == 'not user: "a"'


def test_field_names():
    path = Path([NamedReference('process'), NamedReference('name')])
    queries = compile_each(
        Equality(path, StringLiteral('cmd.exe')),
        Equality(Wildcard('host.*'), StringLiteral('a')),
        eq('odd:name', StringLiteral('b')),
    )

    assert queries == ['process.name: "cmd.exe"', 'host.*: "a"', r'odd\:name: "b"']


def test_relational_and_between():
    start = Datetime(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
    end = Datetime(datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc))

    queries = compile_each(
        Relational(NamedReference('bytes'), Integer(10), gt=True, eq=False),
        BetweenEquality(NamedReference('@timestamp'), start, end),
    )

    assert queries == [
        'bytes > 10',
        '(@timestamp >= "2026-01-01T00:00:00Z" and @timestamp <= "2026-02-01T00:00:00Z")',
    ]


def test_relational_against_field_is_rejected():
    query, rejected = compile_where(
        Relational(NamedReference('a'), NamedReference('b'), gt=True, eq=True)
    )

    assert query == ''
    assert rejected[0] is not None


def test_substring_wildcards_are_escaped():
    queries = compile_each(
        Substring(NamedReference('cmd'), [StringLiteral('socks5://'), StringLiteral('a or (b)*')]),
        Substring(NamedReference('img'), [StringLiteral('\\curl.exe')], endswith=True),
        Substring(NamedReference('name'), [StringLiteral('svc')], startswith=True, neq=True),
    )

    assert queries == [
        r'cmd: (*socks5\://* or *a \or \(b\)\**)',
        r'img: *\\curl.exe',
        'not name: svc*',
    ]


def test_substring_all_terms():
    query, _ = compile_where(
        Substring(NamedReference('cmd'), [StringLiteral('a'), StringLiteral('b')], logic_and=True)
    )
    assert query == 'cmd: (*a* and *b*)'


def test_substring_with_unrepresentable_whitespace_is_rejected():
    query, rejected = compile_where(
        Substring(NamedReference('cmd'), [StringLiteral(' a')], startswith=True)
    )

    assert query == ''
    assert rejected[0] is not None


def test_regex_is_rejected():
    regex = Regex(NamedReference('cmd'), StringLiteral('a.*'))
    query, rejected = compile_where(regex)

    assert query == ''
    assert rejected[0] is not None
    assert rejected[0].expr.to_dict() == regex.to_dict()


def test_and_keeps_supported_terms_and_rejects_remainder():
    regex = Regex(NamedReference('cmd'), StringLiteral('a.*'))
    query, rejected = compile_where(BinaryLogic([eq('a', Integer(1)), regex]))

    assert query == 'a: 1'
    assert rejected[0].expr.to_dict() == regex.to_dict()


def test_or_with_unsupported_term_is_rejected_atomically():
    regex = Regex(NamedReference('cmd'), StringLiteral('a.*'))
    expr = BinaryLogic([eq('a', Integer(1)), regex], logic_and=False)
    query, rejected = compile_where(expr)

    assert query == ''
    assert rejected[0].expr.to_dict() == expr.to_dict()


def test_mixed_logic_is_parenthesized():
    expr = BinaryLogic([
        eq('a', Integer(1)),
        BinaryLogic([eq('b', Integer(2)), eq('c', Integer(3))], logic_and=False),
    ])
    query, _ = compile_where(expr)

    # BinaryLogic may reorder terms, the parentheses are what matters here
    assert query in (
        'a: 1 and (b: 2 or c: 3)',
        'a: 1 and (c: 3 or b: 2)',
        '(b: 2 or c: 3) and a: 1',
        '(c: 3 or b: 2) and a: 1',
    )


def test_not_wraps_compound_and_nested_negations():
    queries = compile_each(
        Not(BinaryLogic([eq('a', Integer(1)), eq('b', Integer(2))], logic_and=False)),
        Not(eq('c', Integer(3), neq=True)),
    )

    assert queries[0] in ('not (a: 1 or b: 2)', 'not (b: 2 or a: 1)')
    assert queries[1] == 'not (not c: 3)'


def test_isnull():
    queries = compile_each(
        isnull([NamedReference('x')]),
        Not(isnull([NamedReference('y')])),
    )

    assert queries == ['not x: *', 'not (not y: *)']


def test_non_predicates_are_rejected():
    query, rejected = compile_where(
        eq('a', NamedReference('b')),
        Bool(True),
        Bool(False),
    )

    assert query == ''
    assert rejected[0] is not None
    assert rejected[1] is None
    assert rejected[2] is not None
