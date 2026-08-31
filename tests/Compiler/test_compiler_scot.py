from __future__ import annotations

import datetime
from dataclasses import replace

import pytest

from Hql.Compiler import SCOTCompiler
from Hql.Database.SCOT.SCOTCatalog import SCOT_ENDPOINTS, SCOT_TABLES
from Hql.Expressions.Literals import Bool, Datetime, Integer, StringLiteral
from Hql.Expressions.Logic import BetweenEquality, BinaryLogic, Equality, Not, Regex
from Hql.Expressions.References import NamedReference
from Hql.Operators.Take import Take
from Hql.Operators.Where import Where


def eq(field, value, *, neq=False):
    return Equality(NamedReference(field), value, neq=neq)


def test_equality_and_inequality():
    compiler = SCOTCompiler()

    params, rejected = compiler.compile_filter(eq("owner", StringLiteral("alice")))
    negated, negated_rejected = compiler.compile_filter(
        eq("status", StringLiteral("closed"), neq=True)
    )

    assert params == {"owner": "alice"}
    assert rejected is None
    assert negated == {"status": "!closed"}
    assert negated_rejected is None
    assert compiler.parameters == {}


def test_multi_value_equality():
    compiler = SCOTCompiler()
    expr = Equality(
        NamedReference("owner"),
        [StringLiteral("alice"), StringLiteral("bob")],
    )

    params, rejected = compiler.compile_filter(expr)

    assert params == {"owner": "[alice,bob]"}
    assert rejected is None


def test_between_and_negated_between():
    compiler = SCOTCompiler()
    start = Datetime(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
    end = Datetime(datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc))

    params, rejected = compiler.compile_filter(
        BetweenEquality(NamedReference("created"), start, end)
    )
    negated, _ = compiler.compile_filter(
        BetweenEquality(NamedReference("created"), start, end, neq=True)
    )

    assert params == {"created": "(2026-01-01T00:00:00Z,2026-02-01T00:00:00Z)"}
    assert negated == {"created": "!(2026-01-01T00:00:00Z,2026-02-01T00:00:00Z)"}
    assert rejected is None


def test_safe_not_inverts_atomic_predicate():
    compiler = SCOTCompiler()
    params, rejected = compiler.compile_filter(
        Not(eq("owner", StringLiteral("alice")))
    )

    assert params == {"owner": "!alice"}
    assert rejected is None


def test_and_pushes_supported_terms_and_preserves_remainder():
    compiler = SCOTCompiler()
    accepted = eq("owner", StringLiteral("alice"))
    unsupported = Regex(NamedReference("subject"), StringLiteral("danger.*"))
    expression = BinaryLogic([accepted, unsupported], logic_and=True)

    params, rejected = compiler.compile_filter(expression)

    assert params == {"owner": "alice"}
    assert rejected == unsupported


def test_same_field_or_becomes_list():
    compiler = SCOTCompiler()
    expression = BinaryLogic(
        [eq("owner", StringLiteral("alice")), eq("owner", StringLiteral("bob"))],
        logic_and=False,
    )

    params, rejected = compiler.compile_filter(expression)

    assert params == {"owner": "[alice,bob]"}
    assert rejected is None


def test_cross_field_or_is_rejected_atomically():
    compiler = SCOTCompiler()
    expression = BinaryLogic(
        [eq("owner", StringLiteral("alice")), eq("status", StringLiteral("open"))],
        logic_and=False,
    )

    params, rejected = compiler.compile_filter(expression)

    assert params == {}
    assert rejected is not None
    assert rejected.to_dict() == expression.to_dict()


def test_non_static_rhs_and_regex_are_rejected():
    compiler = SCOTCompiler()
    dynamic = eq("owner", NamedReference("other_field"))
    regex = Regex(NamedReference("subject"), StringLiteral("danger.*"))

    dynamic_params, dynamic_rejected = compiler.compile_filter(dynamic)
    regex_params, regex_rejected = compiler.compile_filter(regex)

    assert dynamic_params == {}
    assert dynamic_rejected is not None
    assert dynamic_rejected.to_dict() == dynamic.to_dict()
    assert regex_params == {}
    assert regex_rejected is not None
    assert regex_rejected.to_dict() == regex.to_dict()


def test_add_op_records_only_accepted_parameters():
    compiler = SCOTCompiler()
    first = Where(eq("owner", StringLiteral("alice")))
    second = Where(eq("status", StringLiteral("open")))

    first_accepted, first_rejected = compiler.add_op(first)
    second_accepted, second_rejected = compiler.add_op(second)

    assert first_accepted is not None and first_rejected is None
    assert second_accepted is not None and second_rejected is None
    assert compiler.simple_compile() == {"owner": "alice", "status": "open"}


def test_conflicting_parameter_is_left_for_local_evaluation():
    compiler = SCOTCompiler()
    compiler.add_op(Where(eq("owner", StringLiteral("alice"))))
    conflicting = Where(eq("owner", StringLiteral("bob")))

    accepted, rejected = compiler.add_op(conflicting)

    assert accepted is None
    assert rejected is conflicting
    assert compiler.simple_compile() == {"owner": "alice"}


def test_empty_filter_set_and_non_where_operator():
    compiler = SCOTCompiler()
    take = Take(Integer(5), [])

    assert compiler.simple_compile() == {}
    assert compiler.add_op(take) == (None, take)


def test_take_sets_limit_for_alertgroup():
    compiler = SCOTCompiler(SCOT_TABLES["alertgroup"], max_limit=1_000)
    take = Take(Integer(25), [])

    accepted, rejected = compiler.add_op(take)

    assert accepted is take
    assert rejected is None
    assert compiler.simple_compile() == {"limit": 25}


def test_take_never_increases_existing_limit():
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)

    compiler.add_op(Take(Integer(20), []))
    compiler.add_op(Take(Integer(50), []))
    compiler.add_op(Take(Integer(10), []))

    assert compiler.simple_compile() == {"limit": 10}


def test_take_is_clamped_to_configured_maximum_by_default():
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)

    assert compiler.simple_compile() == {"limit": 100}
    compiler.add_op(Take(Integer(1_000), []))
    assert compiler.simple_compile() == {"limit": 100}


def test_zero_take_is_pushed_down():
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)

    accepted, rejected = compiler.add_op(Take(Integer(0), []))

    assert accepted is not None
    assert rejected is None
    assert compiler.simple_compile() == {"limit": 0}


@pytest.mark.parametrize("target", ["entity", "ent*", "*"])
def test_matching_and_wildcard_table_targets_apply(target):
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)
    take = Take(Integer(5), [NamedReference(target)])

    assert compiler.add_op(take) == (take, None)
    assert compiler.simple_compile() == {"limit": 5}


def test_nonmatching_table_target_is_rejected():
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)
    take = Take(Integer(5), [NamedReference("alertgroup")])

    assert compiler.add_op(take) == (None, take)
    assert compiler.simple_compile() == {"limit": 100}


@pytest.mark.parametrize("value", [-1, "invalid"])
def test_invalid_take_is_rejected(value):
    compiler = SCOTCompiler(SCOT_TABLES["entity"], max_limit=100)
    literal = Integer(value) if isinstance(value, int) else StringLiteral(value)
    take = Take(literal, [])

    assert compiler.add_op(take) == (None, take)
    assert compiler.simple_compile() == {"limit": 100}


def test_endpoint_without_limit_support_rejects_take():
    endpoint = replace(SCOT_TABLES["entity"], limit_parameter=None)
    compiler = SCOTCompiler(endpoint, max_limit=100)
    take = Take(Integer(5), [])

    assert compiler.add_op(take) == (None, take)
    assert compiler.simple_compile() == {}


def compatible_value(parameter):
    if parameter.type == "boolean":
        return Bool(True)
    if parameter.format == "date-time":
        return Datetime(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc))
    return StringLiteral("test")


def test_each_catalog_endpoint_accepts_all_documented_filter_fields():
    for endpoint in SCOT_ENDPOINTS:
        compiler = SCOTCompiler(endpoint)
        for field, parameter in endpoint.filters.items():
            params, rejected = compiler.compile_filter(
                eq(field, compatible_value(parameter))
            )
            assert field in params, f"{endpoint.name}.{field} was not accepted"
            assert rejected is None


def test_field_valid_for_one_endpoint_is_invalid_for_another():
    entity = SCOTCompiler(SCOT_TABLES["entity"])
    event = SCOTCompiler(SCOT_TABLES["event"])
    predicate = eq("value", StringLiteral("example.com"))

    assert entity.compile_filter(predicate)[0] == {"value": "example.com"}
    params, rejected = event.compile_filter(predicate)
    assert params == {}
    assert rejected is not None


def test_control_parameters_cannot_be_compiled_as_filters():
    compiler = SCOTCompiler(SCOT_TABLES["entity"])

    for field in ("skip", "limit", "sort"):
        params, rejected = compiler.compile_filter(eq(field, Integer(1)))
        assert params == {}
        assert rejected is not None


def test_endpoint_parameter_type_is_enforced():
    compiler = SCOTCompiler(SCOT_TABLES["notification"])

    accepted, rejected = compiler.compile_filter(eq("include_acked", Bool(True)))
    invalid, invalid_rejected = compiler.compile_filter(
        eq("include_acked", Integer(1))
    )

    assert accepted == {"include_acked": "true"}
    assert rejected is None
    assert invalid == {}
    assert invalid_rejected is not None


def test_endpoint_aware_mixed_and_and_atomic_or():
    compiler = SCOTCompiler(SCOT_TABLES["entity"])
    valid = eq("value", StringLiteral("example.com"))
    invalid = eq("owner", StringLiteral("alice"))

    and_params, and_rejected = compiler.compile_filter(
        BinaryLogic([valid, invalid], logic_and=True)
    )
    or_params, or_rejected = compiler.compile_filter(
        BinaryLogic([valid, invalid], logic_and=False)
    )

    assert and_params == {"value": "example.com"}
    assert and_rejected is not None
    assert and_rejected.to_dict() == invalid.to_dict()
    assert or_params == {}
    assert or_rejected is not None


def test_invalid_field_does_not_mutate_compiler_state():
    compiler = SCOTCompiler(SCOT_TABLES["entity"])
    invalid = Where(eq("owner", StringLiteral("alice")))

    accepted, rejected = compiler.add_op(invalid)

    assert accepted is None
    assert rejected is not None
    assert compiler.simple_compile() == {}
