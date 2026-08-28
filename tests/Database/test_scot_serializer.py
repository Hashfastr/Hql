from __future__ import annotations

import datetime
from urllib.parse import parse_qs, urlencode

import pytest

from Hql.Database.SCOT.SCOTSerializer import (
    UnsupportedSCOTValue,
    serialize_list,
    serialize_range,
    serialize_value,
    try_serialize_value,
)
from Hql.Expressions.Literals import Bool, Datetime, Float, Integer, Null, StringLiteral
from Hql.Expressions.Logic import BasicRange


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (StringLiteral("hello"), "hello"),
        (Integer(42), "42"),
        (Float(1.25), "1.25"),
        (Bool(True), "true"),
        (False, "false"),
        ("", ""),
    ],
)
def test_scalar_values(value, expected):
    assert serialize_value(value) == expected


def test_datetime_is_normalized_to_utc():
    value = Datetime(
        datetime.datetime(
            2026, 8, 27, 12, 34, 56, 123456,
            tzinfo=datetime.timezone(datetime.timedelta(hours=-6)),
        )
    )

    assert serialize_value(value) == "2026-08-27T18:34:56.123456Z"


def test_naive_datetime_is_treated_as_utc():
    value = datetime.datetime(2026, 8, 27, 12, 34, 56)
    assert serialize_value(value) == "2026-08-27T12:34:56Z"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("!literal", r"\!literal"),
        ("[literal]", r"\[literal]"),
        ("(literal)", r"\(literal)"),
        ("{literal}", r"\{literal}"),
        (r"\literal", r"\\literal"),
        ("ordinary!value", "ordinary!value"),
    ],
)
def test_leading_control_characters_are_escaped(value, expected):
    assert serialize_value(value) == expected


def test_negation_wraps_escaped_scalar():
    assert serialize_value("!literal", negated=True) == r"!\!literal"


def test_range_and_negated_range():
    value = BasicRange(Integer(1), Integer(10))

    assert serialize_value(value) == "(1,10)"
    assert serialize_value(value, negated=True) == "!(1,10)"
    assert serialize_range(1, 10) == "(1,10)"


def test_list_and_negated_list():
    values = [StringLiteral("alice"), StringLiteral("bob"), Integer(3)]

    assert serialize_value(values) == "[alice,bob,3]"
    assert serialize_list(values, negated=True) == "![alice,bob,3]"


def test_reserved_characters_and_unicode_are_left_for_url_encoder():
    serialized = serialize_value("snowman ☃ & status=ready 100%")
    encoded = urlencode({"subject": serialized})

    assert "%26" in encoded
    assert "%3D" in encoded
    assert "%25" in encoded
    assert parse_qs(encoded)["subject"] == [serialized]


def test_syntax_is_not_double_encoded():
    serialized = serialize_list(["alpha", "beta"])
    encoded = urlencode({"owner": serialized})

    assert encoded == "owner=%5Balpha%2Cbeta%5D"
    assert parse_qs(encoded)["owner"] == ["[alpha,beta]"]


@pytest.mark.parametrize(
    "value",
    [Null(), None, object(), {"nested": "mapping"}, float("nan"), float("inf")],
)
def test_unsupported_scalar_values_are_rejected(value):
    with pytest.raises(UnsupportedSCOTValue):
        serialize_value(value)

    result = try_serialize_value(value)
    assert not result.accepted
    assert result.value is None
    assert result.rejected is value


@pytest.mark.parametrize(
    "values",
    [[], [["nested"]], ["comma,value"], ["closing]"]],
)
def test_empty_nested_or_ambiguous_lists_are_rejected(values):
    with pytest.raises(UnsupportedSCOTValue):
        serialize_list(values)


@pytest.mark.parametrize("bounds", [("", 1), (1, ""), ("a,b", "z")])
def test_empty_or_ambiguous_range_bounds_are_rejected(bounds):
    with pytest.raises(UnsupportedSCOTValue):
        serialize_range(*bounds)
