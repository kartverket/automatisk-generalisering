"""TEMPLATE — not shipped. Target module: `src/ag/ports/geometry.py`.

The `Geometry` value type. ADR-0004.

WHY A VALUE TYPE AND NOT A CURSOR

`SearchCursor`, `UpdateCursor` and `InsertCursor` are 483 call sites in the current
codebase and the least portable arcpy API there is: streaming row iterators with a
vendor field-token language (`SHAPE@`, `OID@`, `SHAPE@XY`). Target engines are
vectorized, where a row loop is idiomatically wrong and orders of magnitude slower.
Porting the cursor faithfully would make the slowest arcpy-shaped pattern part of the
contract and guarantee a bad second adapter.

But some logic genuinely manipulates geometry VALUES in Python rather than whole
datasets - `line_topology.py` builds `arcpy.Polyline(arcpy.Array([arcpy.Point(x, y),
...]))`, inspects `.firstPoint` and `.lastPoint`, and inserts the results. That is our
algorithm, and a dataset-level port gives it nowhere to live. So: bulk read and write
(`TableOps.read_rows` / `write_rows`) carrying an immutable value type, and no cursor.

Adapters convert at the boundary:

    arcpy.Polyline(arcpy.Array(pts))  <->  Geometry(GeometryKind.LINESTRING, coords)
    .firstPoint / .lastPoint          <->  coords[0] / coords[-1]

FROZEN, AND COORDINATES ARE A TUPLE OF TUPLES. A row read out of one dataset is
routinely written into another; if geometry were mutable, editing it after the read
would change what an unrelated row is about to write. Immutability also means a
Geometry can be a dict key and can be compared, which is what `line_topology`'s
endpoint matching wants.

NO SHAPELY HERE. Shapely lives below this type, in `adapters/`, exactly as arcpy does
(03-architecture §2.5). This module imports stdlib and `ag.core.types` only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

Coordinate: TypeAlias = tuple[float, float]
"""(x, y). Planar only - every dataset in this system is in a projected CRS.

No z and no m. Neither appears in any current call site, and a two-float tuple is
what keeps a coordinate sequence cheap enough to pass around by value. Adding them
later is a widening change to this alias and to the adapters' converters, and
touches no operation.
"""

Ring: TypeAlias = tuple[Coordinate, ...]
CRS: TypeAlias = str
"""An EPSG code as `"EPSG:25833"`. A string because it crosses into every adapter,
every workspace and every published product, and every one of them spells it that
way."""


class GeometryKind(Enum):
    """OGC Simple Features geometry types, restricted to what this system produces.

    NO GEOMETRYCOLLECTION. Nothing in the domain produces one, and admitting it would
    mean every operation handling a Geometry needs a branch for the heterogeneous
    case. `MultipartToSinglepart` exists precisely because the pipeline wants
    singlepart features.
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

    `parts` IS ALWAYS A SEQUENCE OF RINGS, whatever the kind, so that a consumer
    never branches on kind to find the coordinates:

        POINT        one part, one coordinate
        LINESTRING   one part, n coordinates
        POLYGON      one exterior ring, then any interior rings
        MULTI*       one part per member; polygons with holes are why this cannot
                     be flattened to a single ring list

    The alternative - a `coords` field for simple kinds and a `parts` field for
    multi - means every reader checks which one is populated, and the check is
    forgotten in the one place a multipolygon actually arrives.
    """

    kind: GeometryKind
    parts: tuple[Ring, ...]
    crs: CRS

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError(
                f"{self.kind.value} has no parts. An empty geometry is a null "
                "geometry, and a null geometry is represented by Row.geometry being "
                "None - not by a Geometry with nothing in it."
            )
        if self.kind is GeometryKind.POINT and (
            len(self.parts) != 1 or len(self.parts[0]) != 1
        ):
            raise ValueError(
                f"POINT must be exactly one part of one coordinate, got "
                f"{[len(p) for p in self.parts]}"
            )

    @property
    def coords(self) -> Ring:
        """The first part's coordinates. The common case, named.

        `line_topology`'s endpoint logic is `geometry.coords[0]` and
        `geometry.coords[-1]`, replacing `.firstPoint` and `.lastPoint`. Deliberately
        NOT a flatten across parts: for a multipart geometry the first and last
        coordinate of a concatenation are not endpoints of anything.
        """
        return self.parts[0]

    @classmethod
    def point(cls, x: float, y: float, *, crs: CRS) -> Geometry:
        return cls(kind=GeometryKind.POINT, parts=(((x, y),),), crs=crs)

    @classmethod
    def linestring(cls, coords: Ring, *, crs: CRS) -> Geometry:
        return cls(kind=GeometryKind.LINESTRING, parts=(tuple(coords),), crs=crs)
