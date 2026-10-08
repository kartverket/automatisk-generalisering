"""The column vocabulary shared by the table port and the predicate algebra.

What: `FieldName`, the closed `AttributeValue` union, `FieldType` and `Field`.

Why: its own module, rather than part of the table port, because the predicate algebra
names fields and values too, and the port Protocols must stay independent of each other:
a predicate module that imported the table port would make the geometry port depend on
the table port through it. Values and names are the part of the table vocabulary that
every port shares, so they sit below all of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TypeAlias

FieldName: TypeAlias = str
"""Names a column in data the program does not own, so it stays a literal: the value half
of the identifier-or-value test. ADR-0011."""

AttributeValue: TypeAlias = int | float | str | datetime | None
"""What a cell can hold: exactly the `FieldType` members, plus None for a null.

A `DATE` field holds a date and a time, carried as a naive `datetime` in the workspace's
own convention, because that is what the engine stores and returns; a date-only value is a
`datetime` at midnight. The engine's separate date-only and time-only field types are not
represented, because no pipeline declares one.

Why: a closed union rather than `object`, because `object` pushes a cast to every read
site, and a cast asserts something no one checked. With the union a caller that needs an
`int` writes one narrowing guard and gets a real error when the field turns out to be
TEXT. BLOB and raster values are out of scope: if one arrives, the answer is a reference
in a TEXT field with the bytes in a side store, not a wider union.
"""


class FieldType(Enum):
    """Field types, restricted to what the pipelines declare."""

    SHORT = "short"
    LONG = "long"
    DOUBLE = "double"
    TEXT = "text"
    DATE = "date"
    """Date and time, as a naive `datetime`; never a bare `date`."""


@dataclass(frozen=True)
class Field:
    """One column: its name, its type, and for TEXT its length."""

    name: FieldName
    type: FieldType
    length: int | None = None

    def __post_init__(self) -> None:
        if self.type is FieldType.TEXT and self.length is None:
            raise ValueError(f"TEXT field {self.name!r} needs a length")
        if self.type is not FieldType.TEXT and self.length is not None:
            raise ValueError(f"{self.type.value} field {self.name!r} takes no length")
