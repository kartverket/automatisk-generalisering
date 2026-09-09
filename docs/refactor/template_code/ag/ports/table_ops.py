"""TEMPLATE — not shipped. Target module: `src/ag/ports/table_ops.py`.

Schema, attributes, and bulk row IO. 10-15 methods.

WHY THIS IS NOT PART OF GeometryOps (03-architecture §2.1), three reasons and the
third is the decisive one:

  it is a different conversation - schema and rows, not geometry.
  it applies to NON-SPATIAL lookup tables, which are a real case here: a context
  input replicated whole to every pod rather than partitioned.
  `GeometryOps.add_field()` reads wrong.

NO CURSOR. ADR-0004, and `ports/geometry.py` carries the argument. Three bulk methods
replace 483 cursor call sites:

    set a field from other fields    UpdateCursor loop  ->  calculate_field
    read attributes for an algorithm SearchCursor loop  ->  read_rows
    build a dataset from rows        InsertCursor loop  ->  write_rows
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol, TypeAlias

from ag.core.operations import ScratchHandle
from ag.core.types import DataType
from ag.ports.geometry import CRS, Geometry


class FieldType(Enum):
    """Field types, restricted to what the pipelines actually declare."""

    SHORT = "short"
    LONG = "long"
    DOUBLE = "double"
    TEXT = "text"
    DATE = "date"


FieldName: TypeAlias = str
"""Names a column in data the program does not own, so it stays a literal - the
value half of ADR-0011's identifier/value test."""

AttributeValue: TypeAlias = int | float | str | date | None
"""What a cell can hold. Exactly the `FieldType` members, plus None for a null.

A CLOSED UNION RATHER THAN `object`, because `object` pushes a cast to every read
site: `int(row.attributes["feature_id"])` does not type-check against `object`, and
the fix at each site is a cast that asserts something no one checked. With the union,
a caller that needs an `int` writes one narrowing guard and gets a real error message
when the field turns out to be TEXT - see `_node_id` in `operations/road`.

This was found by writing the first caller, not by design: the port type-checked
perfectly until an operation tried to read a row out of it.
"""


@dataclass(frozen=True)
class Field:
    name: FieldName
    type: FieldType
    length: int | None = None
    """TEXT only. None for every other type."""

    def __post_init__(self) -> None:
        if self.type is FieldType.TEXT and self.length is None:
            raise ValueError(f"TEXT field {self.name!r} needs a length")
        if self.type is not FieldType.TEXT and self.length is not None:
            raise ValueError(f"{self.type.value} field {self.name!r} takes no length")


@dataclass(frozen=True)
class Schema:
    """What `write_rows` needs in order to create a dataset from nothing."""

    fields: tuple[Field, ...]
    data_type: DataType = DataType.FEATURE_CLASS
    geometry_crs: CRS | None = None

    def __post_init__(self) -> None:
        spatial = self.data_type is DataType.FEATURE_CLASS
        if spatial and self.geometry_crs is None:
            raise ValueError(
                "a FEATURE_CLASS schema needs geometry_crs. A feature class written "
                "with no CRS is the failure that surfaces two stages later as an "
                "empty spatial join."
            )


@dataclass(frozen=True)
class Row:
    """One record: attributes, and geometry if there is any.

    GEOMETRY IS A SEPARATE FIELD, not an entry in `attributes`, so that a caller
    reading `row.geometry.coords[0]` is type-checked. arcpy's `SHAPE@` token puts
    geometry in the same tuple as the attributes and gives up the distinction; that
    is exactly the vendor spelling this port exists to avoid.

    `geometry` IS None FOR A NULL GEOMETRY and for every row of a TABLE. That is the
    one case `Geometry.__post_init__` refuses to represent as an empty Geometry.
    """

    attributes: Mapping[FieldName, AttributeValue]
    geometry: Geometry | None = None


class TableOps(Protocol):
    """Schema, attributes and bulk row IO."""

    # -- existence and shape ------------------------------------------------
    #
    # CATALOG CONCERNS, HOUSED HERE DELIBERATELY. `exists` and `data_type_of` ask
    # about a dataset's presence and kind rather than its schema or its rows, so on a
    # strict reading they are a fourth conversation. Two methods do not earn a
    # `CatalogOps`: ports/__init__ requires a distinct external capability AND a
    # foreseeable second implementation before a file exists, and a capability that
    # shares an existing conversation is a method, not a port. "What is this dataset"
    # is close enough to "what are its fields" to live beside it, and any adapter that
    # can answer describe_fields can answer both of these for free. Revisit if a third
    # and fourth catalog method appear.

    def exists(self, *, input: ScratchHandle) -> bool:
        """Whether anything is actually there.

        THE POST-OPERATION SWEEP IS WHY THIS IS ON A PORT AT ALL. `runtime/
        stage_entry.sweep_outputs` checks after every operation that each declared
        output appeared with the declared type; without this method that check is
        the one `import arcpy` left in `runtime/`, and 03-architecture §4.1's
        "only adapters import a vendor library" would be false by one line.
        """
        ...

    def data_type_of(self, *, input: ScratchHandle) -> DataType:
        """FEATURE_CLASS, TABLE or RASTER. The other half of the sweep.

        This is the ONLY thing in the design that verifies `DataType` against real
        data. It is carried on every handle and used to pick a join rule and a
        payload shape, and until the sweep nothing confirms the data agrees.
        """
        ...

    def describe_fields(self, *, input: ScratchHandle) -> tuple[Field, ...]: ...

    # -- schema -------------------------------------------------------------

    def add_field(self, *, input: ScratchHandle, field: Field) -> None: ...

    def delete_fields(
        self, *, input: ScratchHandle, fields: tuple[FieldName, ...]
    ) -> None: ...

    def map_fields(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        mapping: Mapping[FieldName, FieldName],
        keep_unmapped: bool = False,
    ) -> None:
        """Rename and drop in one pass, producing the published schema.

        `keep_unmapped=False` by default: the last step before upload is meant to
        DROP working fields, and defaulting the other way makes forgetting silent.
        """
        ...

    # -- attributes ---------------------------------------------------------

    def calculate_field(
        self, *, input: ScratchHandle, field: FieldName, expression: str
    ) -> None:
        """Set a field from other fields, vectorized by the backend.

        `expression` IS A STRING AND THAT IS THE COMPROMISE IN THIS PORT. A Python
        callable would be honest about what arcpy does and catastrophic for any
        vectorized adapter, which needs something it can push down. A CQL2-shaped
        expression is what both can compile. Where the logic is too complex for one,
        the answer is read_rows / write_rows, not a lambda here.
        """
        ...

    def join_field(
        self,
        *,
        input: ScratchHandle,
        key: FieldName,
        join: ScratchHandle,
        join_key: FieldName,
        fields: tuple[FieldName, ...],
    ) -> None: ...

    # -- bulk row IO (ADR-0004) ---------------------------------------------

    def read_rows(
        self, *, input: ScratchHandle, fields: tuple[FieldName, ...] = ()
    ) -> Iterable[Row]:
        """Every row, as values. Empty `fields` means all of them.

        RETURNS AN Iterable, NOT A Sequence, so an adapter may stream and a caller
        may not index or re-iterate without materializing first. That is the one
        cursor property worth keeping: these datasets do not fit in memory twice.
        """
        ...

    def write_rows(
        self, *, output: ScratchHandle, schema: Schema, rows: Iterable[Row]
    ) -> None:
        """Create a dataset from computed rows.

        This is where `_GeneratedLineRecord` in the current `line_topology.py` goes.
        It exists only to buffer rows because arcpy cannot insert while an
        UpdateCursor is open; under bulk read/write there is nothing to buffer.
        """
        ...

    def write_table(
        self, *, output: ScratchHandle, fields: Sequence[Field], rows: Iterable[Row]
    ) -> None:
        """`write_rows` for the non-spatial case, so a caller building a lookup table
        does not have to construct a Schema with a CRS it does not have."""
        ...
