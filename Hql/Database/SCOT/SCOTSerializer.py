"""Serialize static HQL values using the SCOT search-parameter grammar."""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from Hql.Expressions.Literals import (
    Bool,
    Datetime,
    Float,
    Integer,
    Multivalue,
    StringLiteral,
)
from Hql.Expressions.Logic import BasicRange


class UnsupportedSCOTValue(ValueError):
    """A value cannot be represented without changing SCOT query semantics."""


@dataclass(frozen=True, slots=True)
class SerializationResult:
    """Preserve unsupported input for the compiler's rejected expression."""

    value: str | None
    rejected: object | None
    error: str | None = None

    @property
    def accepted(self) -> bool:
        return self.error is None


_LEADING_CONTROL_CHARACTERS = frozenset("!([{\\")


def _escape_string(value: str) -> str:
    if value and value[0] in _LEADING_CONTROL_CHARACTERS:
        return "\\" + value
    return value


def _datetime(value: datetime.datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    value = value.astimezone(datetime.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _scalar(value: Any) -> str:
    if isinstance(value, StringLiteral):
        return _escape_string(value.value.decode("utf-8"))
    if isinstance(value, Bool):
        return "true" if value.value else "false"
    if isinstance(value, Integer):
        return str(value.value)
    if isinstance(value, Float):
        if not math.isfinite(value.value):
            raise UnsupportedSCOTValue("SCOT cannot represent a non-finite float")
        return str(value.value)
    if isinstance(value, Datetime):
        return _datetime(value.value)

    # Native values make the serializer reusable by endpoint controls without
    # weakening the accepted HQL literal set.
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise UnsupportedSCOTValue("SCOT cannot represent a non-finite float")
        return str(value)
    if isinstance(value, datetime.datetime):
        return _datetime(value)

    raise UnsupportedSCOTValue(
        f"SCOT cannot serialize value of type {type(value).__name__}"
    )


def _composite_scalar(value: Any, forbidden: str, kind: str) -> str:
    serialized = _scalar(value)
    if not serialized:
        raise UnsupportedSCOTValue(f"SCOT cannot represent an empty {kind} item")
    if any(character in serialized for character in forbidden):
        raise UnsupportedSCOTValue(
            f"SCOT cannot safely represent {kind} item containing a delimiter"
        )
    return serialized


def serialize_list(values: Sequence[Any], *, negated: bool = False) -> str:
    """Serialize a non-empty, flat SCOT list expression."""

    if isinstance(values, (str, bytes, bytearray)):
        raise UnsupportedSCOTValue("SCOT list input must be a sequence of values")
    if not values:
        raise UnsupportedSCOTValue("SCOT cannot represent an empty list")

    serialized = [_composite_scalar(value, ",[]", "list") for value in values]
    prefix = "!" if negated else ""
    return f"{prefix}[{','.join(serialized)}]"


def serialize_range(start: Any, end: Any, *, negated: bool = False) -> str:
    """Serialize two static bounds as a SCOT range expression."""

    first = _composite_scalar(start, ",()", "range")
    last = _composite_scalar(end, ",()", "range")
    prefix = "!" if negated else ""
    return f"{prefix}({first},{last})"


def serialize_value(value: Any, *, negated: bool = False) -> str:
    """Serialize one scalar, HQL range, or flat multi-value expression.

    The return value is intentionally not percent encoded. ``requests`` (or
    another standards-based query encoder) must receive it through ``params``.
    """

    if isinstance(value, BasicRange):
        return serialize_range(value.start, value.end, negated=negated)
    if isinstance(value, Multivalue):
        return serialize_list(value.value.to_list(), negated=negated)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return serialize_list(value, negated=negated)

    serialized = _scalar(value)
    return f"!{serialized}" if negated else serialized


def try_serialize_value(value: Any, *, negated: bool = False) -> SerializationResult:
    """Return unsupported input for preservation by the SCOT compiler."""

    try:
        return SerializationResult(serialize_value(value, negated=negated), None)
    except (UnsupportedSCOTValue, UnicodeDecodeError) as error:
        return SerializationResult(None, value, str(error))
