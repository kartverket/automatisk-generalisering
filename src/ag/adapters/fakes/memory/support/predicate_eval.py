"""Three-valued evaluation of a predicate over one row, the way SQL evaluates it.

What: `Truth`, TRUE, FALSE or UNKNOWN; `check(predicate, schema=)`, one walk over the
tree that raises for anything the adapter cannot evaluate over that schema;
`evaluate(predicate, row=, schema=)`, the truth for one row, after the check has passed.

How: `Compare` and a non-empty `IsIn` are UNKNOWN when the field is NULL; the empty `IsIn`
is FALSE for every row; `IsNull` is never UNKNOWN; `Not` of UNKNOWN is UNKNOWN; `And` is
FALSE if any term is FALSE and otherwise UNKNOWN if any term is; `Or` is the mirror.
`LIKE` matches `%` as any run of characters and `_` as one, case-sensitively, with no
escape character. A value that does not fit the field, or a field the schema does not
declare, is a `PortContractError` from `check`; so is a `RawAttr`, which this adapter
does not compile, and a `Spatial` leaf, which it does not evaluate. The check runs once
per call, before any row, so a bad predicate fails on an empty dataset exactly as it
would under an engine that compiles first. ADR-0019 PC-D15, PC-D16, PC-D17, PC-D20.

Why: evaluated in Python rather than compiled, so a selection under the fake agrees with
one under an engine on every NULL and every type, which is what a selection test is most
likely to get wrong. The spatial leaf is refused rather than approximated because the
fake computes no geometry.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from ag.adapters._shared.field_values import type_mismatch
from ag.ports.attributes import AttributeValue, Field, FieldName, FieldType
from ag.ports.errors import PortContractError
from ag.ports.predicates import (
    And,
    Compare,
    Comparison,
    IsIn,
    IsNull,
    Not,
    Or,
    Predicate,
    RawAttr,
    Spatial,
)
from ag.ports.table_ops import Row, Schema


class Truth(Enum):
    """The three values a predicate takes for one row."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


def check(predicate: Predicate, *, schema: Schema) -> None:
    """Raises `PortContractError` for anything in `predicate` the adapter cannot
    evaluate over `schema`: an undeclared field, a value that does not fit its field, a
    raw expression, a spatial leaf. Runs once per call, before any row is read."""
    match predicate:
        case Compare(field=name, value=value):
            _fit(value=value, field=_declared(schema=schema, name=name))
        case IsIn(field=name, values=values):
            field = _declared(schema=schema, name=name)
            for value in values:
                _fit(value=value, field=field)
        case IsNull(field=name):
            _declared(schema=schema, name=name)
        case RawAttr(cql=cql):
            raise PortContractError(
                f"Attr.raw({cql!r}) cannot run under the in-memory adapter, which "
                "compiles no CQL; a raw expression runs only under an engine."
            )
        case Spatial():
            raise PortContractError(
                f"{predicate!r} cannot run under the in-memory adapter, which computes "
                "no geometry; a spatial predicate runs only under an engine."
            )
        case Not(term=term):
            check(term, schema=schema)
        case And(terms=terms) | Or(terms=terms):
            for term in terms:
                check(term, schema=schema)
        case _:
            raise TypeError(
                f"{predicate!r} is not a predicate node this adapter knows."
            )


def evaluate(predicate: Predicate, *, row: Row, schema: Schema) -> Truth:
    """The truth of `predicate` for `row`, whose dataset has `schema`; `check` has run."""
    match predicate:
        case Compare(field=name, op=op, value=value):
            actual = row.attributes[name]
            if actual is None:
                return Truth.UNKNOWN
            field = _declared(schema=schema, name=name)
            return _truth(_compare(actual=actual, op=op, value=value, field=field))
        case IsIn(field=name, values=values):
            if not values:
                return Truth.FALSE
            actual = row.attributes[name]
            if actual is None:
                return Truth.UNKNOWN
            return _truth(actual in values)
        case IsNull(field=name):
            return _truth(row.attributes[name] is None)
        case RawAttr() | Spatial():
            raise TypeError(
                f"{predicate!r} reached evaluation; check() refuses it and runs first."
            )
        case Not(term=term):
            return _negate(evaluate(term, row=row, schema=schema))
        case And(terms=terms):
            results = [evaluate(term, row=row, schema=schema) for term in terms]
            if Truth.FALSE in results:
                return Truth.FALSE
            return Truth.UNKNOWN if Truth.UNKNOWN in results else Truth.TRUE
        case Or(terms=terms):
            results = [evaluate(term, row=row, schema=schema) for term in terms]
            if Truth.TRUE in results:
                return Truth.TRUE
            return Truth.UNKNOWN if Truth.UNKNOWN in results else Truth.FALSE
        case _:
            raise TypeError(
                f"{predicate!r} is not a predicate node this adapter knows."
            )


def _declared(*, schema: Schema, name: FieldName) -> Field:
    for field in schema.fields:
        if field.name == name:
            return field
    raise PortContractError(
        f"{name!r} is not a field of the dataset, whose fields are "
        f"{[field.name for field in schema.fields]}."
    )


def _fit(*, value: AttributeValue, field: Field) -> None:
    reason = type_mismatch(value=value, field=field)
    if reason is not None:
        raise PortContractError(f"predicate on field {field.name!r}: {reason}.")


def _truth(value: bool) -> Truth:
    return Truth.TRUE if value else Truth.FALSE


def _negate(value: Truth) -> Truth:
    if value is Truth.UNKNOWN:
        return Truth.UNKNOWN
    return Truth.FALSE if value is Truth.TRUE else Truth.TRUE


def _compare(
    *, actual: AttributeValue, op: Comparison, value: AttributeValue, field: Field
) -> bool:
    """`actual <op> value`, both non-null and both already checked against `field`."""
    if field.type is FieldType.TEXT:
        if isinstance(actual, str) and isinstance(value, str):
            if op is Comparison.LIKE:
                return _like(pattern=value, text=actual)
            return _ordered(op=op, left=actual, right=value)
    elif field.type is FieldType.DATE:
        if isinstance(actual, datetime) and isinstance(value, datetime):
            return _ordered(op=op, left=actual, right=value)
    elif isinstance(actual, int | float) and isinstance(value, int | float):
        return _ordered(op=op, left=actual, right=value)
    raise TypeError(
        f"{actual!r} and {value!r} reached a comparison on {field.type.value} field "
        f"{field.name!r} without fitting it; the write and the leaf checks must both "
        "have passed them."
    )


def _ordered[T: (float, str, datetime)](*, op: Comparison, left: T, right: T) -> bool:
    if op is Comparison.EQ:
        return left == right
    if op is Comparison.NE:
        return left != right
    if op is Comparison.LT:
        return left < right
    if op is Comparison.LE:
        return left <= right
    if op is Comparison.GT:
        return left > right
    if op is Comparison.GE:
        return left >= right
    raise TypeError(f"{op.name} is not an ordering; LIKE is matched on text only.")


def _like(*, pattern: str, text: str) -> bool:
    """SQL `LIKE`: `%` any run of characters, `_` one, no escape, case-sensitive."""
    parts: list[str] = []
    for char in pattern:
        if char == "%":
            parts.append(".*")
        elif char == "_":
            parts.append(".")
        else:
            parts.append(re.escape(char))
    return re.fullmatch("".join(parts), text, flags=re.DOTALL) is not None
