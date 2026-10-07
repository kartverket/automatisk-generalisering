"""Schema and bulk row IO: the `TableOps` Protocol and the values that cross it.

What: `Schema`, what a write needs to create a dataset from nothing; `Row`, one record as
attributes plus an optional geometry; and the Protocol, which gains its methods as their
callers arrive.

Why: a separate port from geometry because schema and rows are a different conversation,
because it applies to non-spatial lookup tables, which are a real case here, and because
`GeometryOps.add_field()` reads wrong. No cursor crosses the port: bulk reads and writes
carrying `Row` values replace the row loops, so the slowest engine-shaped pattern never
becomes part of the contract. ADR-0004.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from ag.core.types import DataType
from ag.ports.attributes import AttributeValue, Field, FieldName
from ag.ports.geometry import CRS, Geometry


@dataclass(frozen=True)
class Schema:
    """What a write needs in order to create a dataset from nothing.

    A feature class needs its CRS: one written without it is the failure that surfaces two
    stages later as an empty spatial join.
    """

    fields: tuple[Field, ...]
    data_type: DataType = DataType.FEATURE_CLASS
    geometry_crs: CRS | None = None

    def __post_init__(self) -> None:
        if self.data_type is DataType.FEATURE_CLASS and self.geometry_crs is None:
            raise ValueError(
                "a FEATURE_CLASS schema needs geometry_crs. A feature class written with "
                "no CRS is the failure that surfaces two stages later as an empty spatial "
                "join."
            )


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

    Intentionally empty until its first methods land. A Protocol with no members is
    satisfied by any object, so a toolbox field typed with it gives no structural
    protection yet; nothing may rely on it for that.
    """
