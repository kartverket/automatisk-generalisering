"""Whether a value fits a field: the rule both adapters hold attribute values to.

What: `type_mismatch`, the reason a value does not fit a `Field`, or None when it does,
and the inclusive ranges of `SHORT` and `LONG`.

Why: the rule is the port contract's and not an engine's, so it lives once, where the
in-memory adapter, the ArcPy adapter and the tests all import it; an adapter that
coerced instead would let an engine comparison and a Python comparison disagree.
ADR-0019 PC-D17, PC-D26.
"""

from __future__ import annotations

from datetime import datetime

from ag.ports.attributes import AttributeValue, Field, FieldType

SHORT_RANGE = (-32_768, 32_767)
"""Inclusive bounds of a `SHORT` value."""

LONG_RANGE = (-2_147_483_648, 2_147_483_647)
"""Inclusive bounds of a `LONG` value."""


def type_mismatch(*, value: AttributeValue, field: Field) -> str | None:
    """Why `value` does not fit `field`, or None when it does.

    `SHORT` and `LONG` take an `int` within the type's range, `DOUBLE` takes `int` or
    `float`, `TEXT` takes a `str` of at most the field's length in characters, `DATE`
    takes a naive `datetime`; a `bool` fits no field and None fits every one.
    ADR-0019 PC-D17.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return f"{value!r} is a bool and no field type holds one"
    kind = field.type
    if kind is FieldType.SHORT or kind is FieldType.LONG:
        if not isinstance(value, int):
            return f"{value!r} is not an int, which a {kind.value} field takes"
        low, high = SHORT_RANGE if kind is FieldType.SHORT else LONG_RANGE
        if not low <= value <= high:
            return f"{value!r} is outside the {kind.value} range {low} to {high}"
        return None
    if kind is FieldType.DOUBLE:
        if not isinstance(value, int | float):
            return f"{value!r} is not a number, which a double field takes"
        return None
    if kind is FieldType.TEXT:
        if not isinstance(value, str):
            return f"{value!r} is not a str, which a text field takes"
        if field.length is not None and len(value) > field.length:
            return (
                f"{value!r} is {len(value)} characters, and the text field holds at most "
                f"{field.length}"
            )
        return None
    if not isinstance(value, datetime):
        return f"{value!r} is not a datetime, which a date field takes"
    if value.tzinfo is not None:
        return f"{value!r} is an aware datetime; a date field holds a naive one"
    return None
