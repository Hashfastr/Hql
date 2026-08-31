"""Compiler for SCOT's query-parameter search grammar."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING, Any, Mapping

from Hql.Compiler.Compiler import Compiler
from Hql.Database.SCOT.SCOTSerializer import (
    UnsupportedSCOTValue,
    serialize_list,
    serialize_range,
    serialize_value,
)

if TYPE_CHECKING:
    from Hql.Compiler import BranchDescriptor
    from Hql.Database.SCOT.SCOTCatalog import Endpoint, QueryParameter
    from Hql.Expressions.Logic import Logic
    from Hql.Operators.Operator import Operator


@dataclass(slots=True)
class _Compiled:
    parameters: dict[str, str]
    accepted: Logic | None
    rejected: Logic | None


def _and(expressions: list[Logic]) -> Logic | None:
    from Hql.Expressions.Logic import BinaryLogic

    if not expressions:
        return None
    if len(expressions) == 1:
        return expressions[0]
    return BinaryLogic(expressions, logic_and=True)


def _has_conflict(
    existing: Mapping[str, str],
    candidate: Mapping[str, str],
) -> bool:
    """Return whether a candidate would overwrite a different field value."""

    return any(
        name in existing and existing[name] != value
        for name, value in candidate.items()
    )


class SCOTCompiler(Compiler):
    """Compile safely representable HQL predicates into SCOT parameters."""

    def __init__(
        self,
        endpoint: Endpoint | None = None,
        max_limit: int | None = None,
    ) -> None:
        super().__init__()
        self.endpoint = endpoint
        self.parameters: dict[str, str] = {}
        self.limit = max_limit

    def set_endpoint(self, endpoint: Endpoint) -> None:
        if self.endpoint is not None and self.endpoint != endpoint:
            raise ValueError("A SCOT compiler cannot change endpoints")
        self.endpoint = endpoint

    @staticmethod
    def _compatible(parameter: QueryParameter, value: Any) -> bool:
        import datetime
        from Hql.Expressions.Literals import (
            Bool,
            Datetime,
            Float,
            Integer,
            StringLiteral,
        )
        from Hql.Expressions.Logic import BasicRange

        if isinstance(value, BasicRange):
            start_is_valid = SCOTCompiler._compatible(parameter, value.start)
            end_is_valid = SCOTCompiler._compatible(parameter, value.end)
            return start_is_valid and end_is_valid
        if isinstance(value, (list, tuple)):
            return bool(value) and all(
                SCOTCompiler._compatible(parameter, item) for item in value
            )
        if parameter.type == "boolean":
            return isinstance(value, (Bool, bool))
        if parameter.format == "date-time":
            return isinstance(value, (Datetime, datetime.datetime, StringLiteral, str))
        if parameter.type == "string":
            return isinstance(
                value,
                (
                    StringLiteral,
                    Integer,
                    Float,
                    Datetime,
                    str,
                    int,
                    float,
                    datetime.datetime,
                ),
            ) and not isinstance(value, (Bool, bool))
        return False

    def _field_supported(self, field: str, values) -> bool:
        if self.endpoint is None:
            return True
        parameter = self.endpoint.filters.get(field)
        if parameter is None:
            return False
        return all(self._compatible(parameter, value) for value in values)

    @staticmethod
    def _field(expr) -> str | None:
        from Hql.Expressions.References import NamedReference

        return expr.name if isinstance(expr, NamedReference) else None

    def _equality(self, expr, *, invert: bool = False) -> _Compiled:
        field = self._field(expr.lh)
        if field is None or not self._field_supported(field, expr.rh):
            return _Compiled({}, None, expr)

        try:
            negated = expr.neq != invert
            if len(expr.rh) == 1:
                value = serialize_value(expr.rh[0], negated=negated)
            else:
                value = serialize_list(expr.rh, negated=negated)
        except (UnsupportedSCOTValue, UnicodeDecodeError):
            return _Compiled({}, None, expr)
        return _Compiled({field: value}, expr, None)

    def _between(self, expr, *, invert: bool = False) -> _Compiled:
        field = self._field(expr.lh)
        if field is None or not self._field_supported(field, [expr.start, expr.end]):
            return _Compiled({}, None, expr)
        try:
            value = serialize_range(expr.start, expr.end, negated=expr.neq != invert)
        except (UnsupportedSCOTValue, UnicodeDecodeError):
            return _Compiled({}, None, expr)
        return _Compiled({field: value}, expr, None)

    def _or(self, expr) -> _Compiled:
        from Hql.Expressions.Logic import Equality

        field: str | None = None
        values = []
        for branch in expr.exprs:
            if not isinstance(branch, Equality) or branch.neq:
                return _Compiled({}, None, expr)
            branch_field = self._field(branch.lh)
            if branch_field is None or (field is not None and branch_field != field):
                return _Compiled({}, None, expr)
            field = branch_field
            values.extend(branch.rh)

        if field is None or not self._field_supported(field, values):
            return _Compiled({}, None, expr)

        try:
            values.sort(key=serialize_value)
            serialized = serialize_list(values)
        except (UnsupportedSCOTValue, UnicodeDecodeError):
            return _Compiled({}, None, expr)
        return _Compiled({field: serialized}, expr, None)

    def _binary(self, expr) -> _Compiled:
        if not expr.logic_and:
            return self._or(expr)

        parameters: dict[str, str] = {}
        accepted = []
        rejected = []
        for branch in expr.exprs:
            compiled = self._compile_expression(branch)
            conflict = _has_conflict(parameters, compiled.parameters)
            if conflict:
                if compiled.accepted is not None:
                    rejected.append(compiled.accepted)
            else:
                parameters.update(compiled.parameters)
                if compiled.accepted is not None:
                    accepted.append(compiled.accepted)
            if compiled.rejected is not None:
                rejected.append(compiled.rejected)

        return _Compiled(parameters, _and(accepted), _and(rejected))

    def _compile_expression(self, expr) -> _Compiled:
        from Hql.Expressions.Logic import BetweenEquality, BinaryLogic, Equality, Not

        if isinstance(expr, Equality):
            return self._equality(expr)
        if isinstance(expr, BetweenEquality):
            return self._between(expr)
        if isinstance(expr, BinaryLogic):
            return self._binary(expr)
        if isinstance(expr, Not):
            if isinstance(expr.expr, Equality):
                compiled = self._equality(expr.expr, invert=True)
            elif isinstance(expr.expr, BetweenEquality):
                compiled = self._between(expr.expr, invert=True)
            else:
                return _Compiled({}, None, expr)
            if compiled.rejected is not None:
                return _Compiled({}, None, expr)
            return _Compiled(compiled.parameters, expr, None)
        return _Compiled({}, None, expr)

    def compile_filter(self, expr) -> tuple[dict[str, str], Logic | None]:
        """Compile without changing compiler state, returning any remainder."""

        processed = expr.preprocess(self.ctx)
        compiled = self._compile_expression(processed)
        return dict(sorted(compiled.parameters.items())), compiled.rejected

    def _take(self, op: Operator) -> tuple[Operator | None, Operator | None]:
        from Hql.Expressions.Literals import Integer

        if self.endpoint is None or not self.endpoint.supports_limit:
            return None, op
        if not isinstance(op.expr, Integer) or op.expr.value < 0:
            return None, op

        targets = [table.str() for table in op.tables]
        applies = not targets or any(
            fnmatchcase(self.endpoint.name, target) for target in targets
        )
        if not applies:
            return None, op

        requested = op.expr.value
        self.limit = requested if self.limit is None else min(self.limit, requested)
        return op, None

    def add_op(
        self, op: Operator | BranchDescriptor
    ) -> tuple[Operator | None, Operator | None]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Take import Take
        from Hql.Operators.Where import Where

        if isinstance(op, BranchDescriptor):
            op = op.get_op()
        if isinstance(op, Take):
            return self._take(op)
        if not isinstance(op, Where):
            return None, op

        processed = op.expr.preprocess(self.ctx)
        compiled = self._compile_expression(processed)
        if _has_conflict(self.parameters, compiled.parameters):
            return None, op

        self.parameters.update(compiled.parameters)
        accepted = (
            Where(compiled.accepted, op.parameters) if compiled.accepted else None
        )
        rejected = (
            Where(compiled.rejected, op.parameters) if compiled.rejected else None
        )
        return accepted, rejected

    def simple_compile(self) -> Mapping[str, str | int]:
        parameters: dict[str, str | int] = dict(self.parameters)
        if (
            self.endpoint is not None
            and self.endpoint.limit_parameter is not None
            and self.limit is not None
        ):
            parameters[self.endpoint.limit_parameter] = self.limit
        return dict(sorted(parameters.items()))
