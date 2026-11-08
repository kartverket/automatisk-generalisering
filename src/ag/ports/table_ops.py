"""Schema and bulk row IO: the `TableOps` Protocol and the values that cross it.

What: `Schema`, what a write needs to create a dataset from nothing, a feature class with
its CRS and geometry family; `PARENTS_SCHEMA`, the one schema every parents table has; `Row`, one record as attributes plus an optional
geometry; and the Protocol, which gains its methods as their callers arrive.

Why: a separate port from geometry because schema and rows are a different conversation,
because it applies to non-spatial lookup tables, which are a real case here, and because
`GeometryOps.add_field()` reads wrong. No cursor crosses the port: bulk reads and writes
carrying `Row` values replace the row loops, so the slowest engine-shaped pattern never
becomes part of the contract. ADR-0019 PC-4.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from ag.core.handles import In
from ag.core.types import DataType
from ag.ports.attributes import AttributeValue, Field, FieldName, FieldType
from ag.ports.columns import CHILD_ID, PARENT_ID
from ag.ports.geometry import CRS, Geometry, GeometryFamily


@dataclass(frozen=True)
class Schema:
    """What a write needs in order to create a dataset from nothing.

    A feature class needs its CRS and its geometry family: one written without a CRS is
    the failure that surfaces two stages later as an empty spatial join, and one has one
    geometry type on every engine, which nothing but the schema can say when a partition
    has no rows of an input and the dataset is still created with all its fields. A row
    whose geometry is outside the family is refused by the adapter before anything is
    written (ADR-0019 PC-D26). A table has no geometry and takes neither.
    ADR-0019 PC-D22.
    """

    fields: tuple[Field, ...]
    data_type: DataType = DataType.FEATURE_CLASS
    geometry_crs: CRS | None = None
    geometry_family: GeometryFamily | None = None

    def __post_init__(self) -> None:
        if self.data_type is DataType.FEATURE_CLASS and self.geometry_crs is None:
            raise ValueError(
                "a FEATURE_CLASS schema needs geometry_crs. A feature class written with "
                "no CRS is the failure that surfaces two stages later as an empty spatial "
                "join."
            )
        if self.data_type is DataType.FEATURE_CLASS and self.geometry_family is None:
            raise ValueError(
                "a FEATURE_CLASS schema needs geometry_family. A feature class holds one "
                "geometry type, and an empty one can be created from the schema alone "
                "only if the schema says which."
            )
        if (
            self.data_type is not DataType.FEATURE_CLASS
            and self.geometry_crs is not None
        ):
            raise ValueError(
                f"a {self.data_type.value} schema takes no geometry_crs; only a feature "
                "class has a geometry to reference."
            )
        if (
            self.data_type is not DataType.FEATURE_CLASS
            and self.geometry_family is not None
        ):
            raise ValueError(
                f"a {self.data_type.value} schema takes no geometry_family; only a "
                "feature class has a geometry type."
            )


PARENTS_SCHEMA = Schema(
    fields=(Field(PARENT_ID, FieldType.LONG), Field(CHILD_ID, FieldType.LONG)),
    data_type=DataType.TABLE,
)
"""The schema of a parents table: both native indices, as `LONG`, so every adapter writes
the same table and the layer above reads it without knowing which engine produced it.
ADR-0017 RS-D16."""


@dataclass(frozen=True, slots=True)
class Row:
    """One record: attributes, and geometry if there is any.

    Why: geometry is a separate field, not an entry in `attributes`, so that reading
    `row.geometry.coords[0]` is type-checked; the engine's shape token puts geometry in the
    same tuple as the attributes and gives up the distinction. `geometry` is None for a
    null geometry and for every row of a table. Slots, because rows are the one value
    produced in bulk.
    """

    attributes: Mapping[FieldName, AttributeValue]
    geometry: Geometry | None = None


class TableOps(Protocol):
    """Schema, attributes and bulk row IO.

    Every handle parameter carries a direction marker, and every output declares its row
    shape on the method; a method that returns values and writes no handle is outside
    the row-shape grammar and is listed as such by the check over the surface. ADR-0017.

    A native index a port method reports, as the columns of a parents table do, is valid
    until its dataset is next written: a method reads its input's indices as they are and
    never rewrites them, and an output's indices are its own.
    """

    def read_rows(self, *, input: In, fields: tuple[FieldName, ...]) -> Iterable[Row]:
        """Every row of `input`, as values, with exactly the named fields.

        How: returns an iterable rather than a sequence, so an adapter may stream and a
        caller may not index or re-iterate without materialising first; that is the one
        cursor property worth keeping, since these datasets do not fit in memory twice.
        `fields` is required: which fields "all of them" means is engine-dependent, and a
        default can be added later without breaking a caller. `geometry` is read whenever
        the dataset has one. `fields` names attribute fields the dataset declares; the
        native index, the geometry and a length or area the engine maintains are not
        among them, and an undeclared name is a `PortContractError`, raised before any
        row is read. A query, outside the row-shape grammar: it writes no handle.

        Why: bulk reads carrying `Row` values replace the row loops, so the slowest
        engine-shaped pattern never becomes part of the contract. ADR-0019 PC-D22.
        """
        ...
