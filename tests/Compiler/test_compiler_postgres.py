from __future__ import annotations

import datetime

import pytest

from Hql.Compiler import PostgresCompiler
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Aggregation import OrderedExpression
from Hql.Expressions.Literals import Bool, Datetime, Float, Integer, Multivalue, StringLiteral
from Hql.Expressions.Logic import BasicRange, BetweenEquality, BinaryLogic, Equality, Not, Regex, Relational, Substring
from Hql.Expressions.References import NamedExpression, NamedReference, Path, Wildcard
from Hql.Functions.null import isnull
from Hql.Operators.Project import Project
from Hql.Operators.Sort import Sort
from Hql.Operators.Take import Take
from Hql.Operators.Top import Top
from Hql.Operators.Where import Where


def ref(name):
    return NamedReference(name)


def eq(field, value, *, neq=False, cs=True):
    return Equality(ref(field), value, cs=cs, neq=neq)


def sql(compiler):
    return ' '.join(compiler.simple_compile().split())


def compile_ops(*ops, table='events'):
    compiler = PostgresCompiler(table)
    rejected = compiler.add_ops(list(ops))
    return sql(compiler), rejected


def where(expr):
    query, rejected = compile_ops(Where(expr))
    prefix = 'SELECT * FROM events WHERE '
    if rejected:
        return None, rejected
    assert query.startswith(prefix)
    return query[len(prefix):], None


def test_plain_table_and_schema():
    assert compile_ops() == ('SELECT * FROM events', None)
    assert compile_ops(table='Logs.Process')[0] == 'SELECT * FROM "Logs"."Process"'


def test_missing_table_raises():
    compiler = PostgresCompiler()
    with pytest.raises(hqle.CompilerException):
        compiler.add_op(Take(Integer(1), []))


def test_identifiers_and_strings_are_quoted():
    assert where(eq('user', StringLiteral("o'neil\\x"))) == ("\"user\" = 'o''neil\\x'", None)
    assert where(eq('CommandLine', Integer(5))) == ('"CommandLine" = 5', None)


def test_literal_values():
    start = Datetime(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))

    assert where(eq('ratio', Float(1.5)))[0] == 'ratio = 1.5'
    assert where(eq('enabled', Bool(True)))[0] == 'enabled = true'
    assert where(Relational(ref('ts'), start, gt=True, eq=True))[0] == "ts >= '2026-01-01 00:00:00+00:00'"


def test_multi_value_and_negated_equality():
    assert where(eq('user', [StringLiteral('a'), StringLiteral('b')]))[0] == "\"user\" IN ('a', 'b')"
    assert where(eq('user', StringLiteral('a'), neq=True))[0] == "\"user\" != 'a'"
    assert where(eq('port', Multivalue([Integer(80), Integer(443)]), neq=True))[0] == '(port NOT IN (80, 443))'


def test_case_insensitive_equality():
    assert where(eq('user', StringLiteral('Bob'), cs=False))[0] == "lower(\"user\") = 'bob'"
    assert where(eq('user', ref('Other'), cs=False))[0] == 'lower("user") = lower("Other")'


def test_paths_are_dotted_columns():
    path = Path([ref('process'), ref('executable')])

    assert where(Substring(path, [StringLiteral('\\curl.exe')], endswith=True))[0] == \
        "\"process.executable\" ILIKE '%\\\\curl.exe' ESCAPE '\\'"
    assert compile_ops(Project([path]))[0] == 'SELECT "process.executable" FROM events'


def test_wildcard_paths_are_rejected():
    _, rejected = where(Equality(Path([ref('process'), Wildcard('*')]), Integer(1)))
    assert rejected is not None


def test_field_comparisons():
    assert where(eq('a', ref('b')))[0] == 'a = b'
    assert where(Relational(ref('a'), ref('b'), gt=False, eq=False))[0] == 'a < b'


def test_between():
    assert where(BetweenEquality(ref('n'), Integer(1), Integer(5)))[0] == 'n BETWEEN 1 AND 5'
    assert where(BetweenEquality(ref('n'), Integer(1), Integer(5), neq=True))[0] == 'n NOT BETWEEN 1 AND 5'


def test_equality_with_range():
    expr = eq('n', [BasicRange(Integer(1), Integer(5)), Integer(9)])
    assert where(expr)[0] == 'n = 9 OR n BETWEEN 1 AND 5'
    assert where(eq('n', BasicRange(ref('a'), Integer(5))))[1] is not None


def test_substring_like_patterns_are_escaped():
    contains = Substring(ref('cmd'), [StringLiteral('50%_off')])
    endswith = Substring(ref('img'), [StringLiteral('\\curl.exe')], endswith=True, cs=True)
    startswith = Substring(ref('name'), [StringLiteral('svc')], startswith=True, neq=True)

    assert where(contains)[0] == "cmd ILIKE '%50\\%\\_off%' ESCAPE '\\'"
    assert where(endswith)[0] == "img LIKE '%\\\\curl.exe' ESCAPE '\\'"
    assert where(startswith)[0] == "name NOT ILIKE 'svc%' ESCAPE '\\'"


def test_substring_all_terms():
    expr = Substring(ref('cmd'), [StringLiteral('a'), StringLiteral('b')], logic_and=True)
    assert where(expr)[0] == "cmd ILIKE '%a%' ESCAPE '\\' AND cmd ILIKE '%b%' ESCAPE '\\'"


def test_term_match_uses_word_boundaries():
    assert where(Substring(ref('cmd'), [StringLiteral('foo')], term=True))[0] == "cmd ~ '(?i)\\mfoo\\M'"
    assert where(Substring(ref('cmd'), [StringLiteral('-x')], term=True, cs=True))[0] == "cmd ~ '\\-x\\M'"


def test_regex_flags_and_escapes():
    assert where(Regex(ref('cmd'), StringLiteral('\\bfoo')))[0] == "cmd ~ '(?p)\\yfoo'"
    assert where(Regex(ref('cmd'), StringLiteral('a.b'), i=True, s=True))[0] == "cmd ~ '(?i)a.b'"
    assert where(Regex(ref('cmd'), StringLiteral('^a'), m=True))[0] == "cmd ~ '(?n)^a'"
    assert where(Regex(ref('cmd'), StringLiteral('(?i)a')))[0] == "cmd ~ '(?ip)a'"


@pytest.mark.parametrize('pattern', ['(?P<name>a)', '(?<name>a)', 'a(?i)b', '\\p{L}', '(?u)a'])
def test_unsupported_regex_is_rejected(pattern):
    regex = Regex(ref('cmd'), StringLiteral(pattern))
    _, rejected = where(regex)
    assert rejected[0].expr.to_dict() == regex.to_dict()


def test_isnull_and_not():
    assert where(isnull([ref('x')]))[0] == 'x IS NULL'
    assert where(Not(isnull([ref('x')])))[0] == 'x IS NOT NULL'


def test_mixed_logic():
    expr = BinaryLogic([
        eq('a', Integer(1)),
        BinaryLogic([eq('b', Integer(2)), eq('c', Integer(3))], logic_and=False),
    ])

    # BinaryLogic may reorder terms
    assert where(expr)[0] in (
        'a = 1 AND (b = 2 OR c = 3)',
        'a = 1 AND (c = 3 OR b = 2)',
        '(b = 2 OR c = 3) AND a = 1',
        '(c = 3 OR b = 2) AND a = 1',
    )


def test_and_keeps_supported_terms_and_rejects_remainder():
    unsupported = Equality(Wildcard('b*'), StringLiteral('x'))
    query, rejected = compile_ops(Where(BinaryLogic([eq('a', Integer(1)), unsupported])))

    assert query == 'SELECT * FROM events WHERE a = 1'
    assert rejected[0].expr.to_dict() == unsupported.to_dict()


def test_or_with_unsupported_term_is_rejected_atomically():
    expr = BinaryLogic([eq('a', Integer(1)), Equality(Wildcard('b*'), Integer(2))], logic_and=False)
    query, rejected = compile_ops(Where(expr))

    assert query == 'SELECT * FROM events'
    assert rejected[0].expr.to_dict() == expr.to_dict()


def test_rejection_stops_later_ops():
    regex = Regex(ref('cmd'), StringLiteral('\\p{L}'))
    query, rejected = compile_ops(Where(regex), Take(Integer(5), []))

    assert query == 'SELECT * FROM events'
    assert [x.type for x in rejected] == ['Where', 'Take']


def test_bare_reference_is_not_a_predicate():
    _, rejected = where(ref('flag'))
    assert rejected is not None


def test_take_keeps_smallest_limit():
    assert compile_ops(Take(Integer(10), []), Take(Integer(5), []), Take(Integer(8), []))[0] == \
        'SELECT * FROM events LIMIT 5'


def test_where_after_take_uses_subquery():
    query, _ = compile_ops(Take(Integer(10), []), Where(eq('x', Integer(1))))
    assert query == 'SELECT * FROM (SELECT * FROM events LIMIT 10) AS anon_1 WHERE x = 1'


def test_sort_and_top():
    by = [OrderedExpression(ref('ts'), 'asc')]

    assert compile_ops(Sort(by))[0] == 'SELECT * FROM events ORDER BY ts ASC NULLS FIRST'
    assert compile_ops(Top(Integer(5), [OrderedExpression(ref('ts'))]))[0] == \
        'SELECT * FROM events ORDER BY ts DESC NULLS LAST LIMIT 5'
    assert compile_ops(Take(Integer(10), []), Sort(by))[0] == \
        'SELECT * FROM (SELECT * FROM events LIMIT 10) AS anon_1 ORDER BY ts ASC NULLS FIRST'


def test_project_and_rename():
    project = Project([ref('ts'), NamedExpression([ref('who')], ref('user'))])
    assert compile_ops(project)[0] == 'SELECT ts, "user" AS who FROM events'


def test_where_after_project_uses_subquery():
    project = Project([NamedExpression([ref('who')], ref('user'))])
    query, _ = compile_ops(project, Where(eq('who', StringLiteral('a'))))
    assert query == "SELECT * FROM (SELECT \"user\" AS who FROM events) AS anon_1 WHERE who = 'a'"


def test_compile_is_repeatable():
    compiler = PostgresCompiler('events')
    compiler.add_op(Where(eq('a', Integer(1), neq=True)))

    assert sql(compiler) == 'SELECT * FROM events WHERE a != 1'
    assert sql(compiler) == 'SELECT * FROM events WHERE a != 1'


def test_statement_uses_bound_parameters():
    compiler = PostgresCompiler('events')
    compiler.add_op(Where(eq('user', StringLiteral('alice'))))

    compiled = compiler.statement().compile(dialect=compiler.dialect)
    assert ' '.join(str(compiled).split()).startswith('SELECT * FROM events WHERE "user" = :param_1')
    assert compiled.params == {'param_1': 'alice'}
