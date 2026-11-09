"""The `Geometry` value type.

What: an immutable geometry in one coordinate reference system, with `parts` always a
sequence of rings whatever the kind and polygon rings canonical, plus the `Coordinate`,
`Ring` and `CRS` aliases, and `GeometryFamily`, the one geometry type a feature class
holds.

Why: the row cursors are the least portable engine API there is, a streaming iterator with
a vendor token language, and a dataset-level port gives logic that manipulates geometry
values in Python nowhere to live. So bulk reads and writes carry an immutable value type and
no cursor crosses the port; adapters convert at the boundary. Frozen, with coordinates as
tuples, because a row read from one dataset is routinely written into another, and a value
that can be a dict key is what endpoint matching needs. No geometry library is imported here:
that lives in the adapters. ADR-0019 PC-D25.
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


class GeometryFamily(Enum):
    """The one geometry type a feature class holds, as every engine folds the kinds.

    What: a line family holds linestrings and multilinestrings, a polygon family polygons
    and multipolygons, and a multipoint family is kept apart from points, which is the
    folding the engines share. `single` is the family that `explode_multipart` writes:
    a multipoint explodes to points and every other family to itself.

    Why: a feature class holds one geometry type, so a `Schema` needs one to create an
    empty dataset, as a partition with no rows of one input is, and a store refuses a
    row outside it before anything is written, as every engine does. A family and not
    a kind, because one feature class holds both the single and the multi kind of a
    line or a polygon. ADR-0019 PC-D22.
    """

    POINT = "point"
    MULTIPOINT = "multipoint"
    LINE = "line"
    POLYGON = "polygon"

    @property
    def single(self) -> GeometryFamily:
        """The family of the rows `explode_multipart` writes from this one."""
        return GeometryFamily.POINT if self is GeometryFamily.MULTIPOINT else self


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

    @property
    def family(self) -> GeometryFamily:
        """The feature-class family this kind belongs to."""
        return _FAMILY_OF[self]


_FAMILY_OF = {
    GeometryKind.POINT: GeometryFamily.POINT,
    GeometryKind.MULTIPOINT: GeometryFamily.MULTIPOINT,
    GeometryKind.LINESTRING: GeometryFamily.LINE,
    GeometryKind.MULTILINESTRING: GeometryFamily.LINE,
    GeometryKind.POLYGON: GeometryFamily.POLYGON,
    GeometryKind.MULTIPOLYGON: GeometryFamily.POLYGON,
}


@dataclass(frozen=True)
class Geometry:
    """One immutable geometry value, in one CRS.

    What: `parts` is always a sequence of rings, whatever the kind: a point is one part of
    one coordinate, a linestring one part, a polygon its exterior ring then any holes, and a
    multi-kind one part per member.

    Polygon rings are canonical: a polygon's exterior and every member of a multipolygon
    run counter-clockwise and a hole runs clockwise, applied on construction, so one
    polygon has one representation and a round trip through any adapter is identity. A
    ring of zero signed area, collinear vertices, keeps its order. Line direction is
    never touched. A polygon ring under four coordinates or a line under two is
    refused, on every ring, exterior, hole and member alike: the port carries straight
    segments and no true curve (ADR-0019 PC-D30), and an engine exports a curve that is
    a whole ring, a buffered point's circle, as its two end vertices, so such a ring is
    the one trace of a curve a value can show; a line under two coordinates has no
    segment. This is the backstop for a whole-ring curve, not the guard: a curved
    corner inside a longer ring reads as a straight chord and is caught only by the
    adapter densifying where curves arise.

    Why: a `coords` field for simple kinds beside a `parts` field for multi-kinds means every
    reader checks which one is populated, and the check is forgotten in the one place a
    multipolygon arrives. An empty geometry is not representable: a null geometry is a `Row`
    whose `geometry` is None. A multi kind holds one ring per member, so a multipolygon
    member with holes is not representable as one row; such a shape is read after
    `explode_multipart`, which yields one polygon with its holes per row, and a raw input
    carrying one is exploded at ingest. Orientation is canonical here and not at an
    adapter's boundary because an engine reads a ring's role from its orientation, two
    counter-clockwise rings becoming two exteriors and a lone clockwise ring an empty
    shape, while a store that computes no geometry keeps what it was given; a value
    canonical on construction cannot diverge between the two, and reversing a ring
    changes how the polygon is described, not what it is, since the position in `parts`
    already says which ring is the exterior.
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
        least = _LEAST_COORDINATES.get(self.kind.family)
        if least is not None:
            short = [len(part) for part in self.parts if len(part) < least]
            if short:
                raise ValueError(
                    f"{self.kind.value} has a part of {short[0]} coordinate(s); a "
                    f"{self.kind.family.value} part needs at least {least}. A ring this "
                    "short is what an engine exports a true curve as, which the port "
                    "does not carry."
                )
        if self.kind.family is GeometryFamily.POLYGON:
            object.__setattr__(self, "parts", _canonical(self.kind, self.parts))

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


_LEAST_COORDINATES = {GeometryFamily.LINE: 2, GeometryFamily.POLYGON: 4}
"""The fewest coordinates a part of the family may hold: a segment for a line, a closed
triangle for a ring."""


def _canonical(kind: GeometryKind, parts: tuple[Ring, ...]) -> tuple[Ring, ...]:
    """`parts` with a polygon's exterior and a multipolygon's members counter-clockwise
    and a polygon's holes clockwise; the same tuple object when nothing reverses, which
    is every value an engine returns."""
    holes_from = 1 if kind is GeometryKind.POLYGON else len(parts)
    oriented: list[Ring] = []
    changed = False
    for position, ring in enumerate(parts):
        turned = _turned(ring, clockwise=position >= holes_from)
        changed = changed or turned is not ring
        oriented.append(turned)
    return tuple(oriented) if changed else parts


def _turned(ring: Ring, *, clockwise: bool) -> Ring:
    """`ring` in the asked direction; a ring of zero signed area is returned as it is."""
    area = _signed_area(ring)
    if area == 0.0 or (area < 0.0) is clockwise:
        return ring
    return tuple(reversed(ring))


def _signed_area(ring: Ring) -> float:
    """Twice the shoelace area, positive counter-clockwise, taken relative to the first
    vertex: at projected coordinates in the hundreds of kilometres the plain form loses
    the sign of a ring a few millimetres across to rounding, and this form does not."""
    x0, y0 = ring[0]
    return sum(
        (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False)
    )
