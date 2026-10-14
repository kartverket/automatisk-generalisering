"""The `Geometry` value type.

What: an immutable geometry in one coordinate reference system, with `parts` always a
sequence of rings whatever the kind, plus the `Coordinate`, `Ring` and `CRS` aliases.

Why: the row cursors are the least portable engine API there is, a streaming iterator with
a vendor token language, and a dataset-level port gives logic that manipulates geometry
values in Python nowhere to live. So bulk reads and writes carry an immutable value type and
no cursor crosses the port; adapters convert at the boundary. Frozen, with coordinates as
tuples, because a row read from one dataset is routinely written into another, and a value
that can be a dict key is what endpoint matching needs. No geometry library is imported here:
that lives in the adapters. ADR-0004.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

Coordinate: TypeAlias = tuple[float, float]
"""(x, y), planar: every dataset in this system is in a projected CRS.

No z and no m, and that is not a gap to fill: sampled elevations land in attribute fields,
not in the geometry, and a two-float tuple is what keeps a coordinate sequence cheap enough
to pass around by value. Adding them would widen this alias and the adapters' converters
and touch no operation.
"""

Ring: TypeAlias = tuple[Coordinate, ...]
"""A closed or open coordinate sequence: a point's one coordinate, a line's vertices, a
polygon's exterior or one of its holes."""

CRS: TypeAlias = str
"""An EPSG code spelled `"EPSG:25833"`: a string because it crosses into every adapter,
every workspace and every published product, and every one of them spells it that way."""


class GeometryKind(Enum):
    """OGC Simple Features geometry types, restricted to what this system produces.

    Why: no GeometryCollection. Nothing in the domain produces one, and admitting it would
    give every consumer a branch for the heterogeneous case; exploding multipart features
    exists because the pipelines want one geometry per row.
    """

    POINT = "Point"
    LINESTRING = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINESTRING = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"


@dataclass(frozen=True)
class Geometry:
    """One immutable geometry value, in one CRS.

    What: `parts` is always a sequence of rings, whatever the kind: a point is one part of
    one coordinate, a linestring one part, a polygon its exterior ring then any holes, and a
    multi-kind one part per member.

    Why: a `coords` field for simple kinds beside a `parts` field for multi-kinds means every
    reader checks which one is populated, and the check is forgotten in the one place a
    multipolygon arrives. An empty geometry is not representable: a null geometry is a `Row`
    whose `geometry` is None.
    """

    kind: GeometryKind
    parts: tuple[Ring, ...]
    crs: CRS

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError(
                f"{self.kind.value} has no parts. An empty geometry is a null geometry, "
                "and a null geometry is represented by Row.geometry being None, not by a "
                "Geometry with nothing in it."
            )
        if self.kind is GeometryKind.POINT and (
            len(self.parts) != 1 or len(self.parts[0]) != 1
        ):
            raise ValueError(
                "POINT must be exactly one part of one coordinate, got parts of lengths "
                f"{[len(part) for part in self.parts]}"
            )

    @property
    def coords(self) -> Ring:
        """The first part's coordinates: the common case, named.

        Endpoint logic reads `coords[0]` and `coords[-1]`. Deliberately not a flatten across
        parts: for a multipart geometry the first and last coordinate of a concatenation
        are endpoints of nothing.
        """
        return self.parts[0]

    @classmethod
    def point(cls, x: float, y: float, *, crs: CRS) -> Geometry:
        """A point geometry from one coordinate."""
        return cls(kind=GeometryKind.POINT, parts=(((x, y),),), crs=crs)

    @classmethod
    def linestring(cls, coords: Ring, *, crs: CRS) -> Geometry:
        """A linestring geometry from one coordinate sequence."""
        return cls(kind=GeometryKind.LINESTRING, parts=(tuple(coords),), crs=crs)
