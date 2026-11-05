"""Well-known binary for tests: `Geometry` values and hand-built edge cases to bytes.

What: `to_wkb(geometry, order=)`, the planar WKB of a value in either byte order;
`oriented(geometry)`, the value with its polygon rings in the orientation the engine reads
through WKB; `empty(code)`, an empty geometry of a type code; `typed(code)`, a point
payload under any type code, for the codes the adapter refuses;
`multipolygon_with_hole()`, the one shape `Geometry` cannot hold, and the rings it is made
of.

Why: the adapter's codec is a parser and nothing in the package writes WKB yet, so the
tests carry the encoder. It is independent of the codec on purpose: a round trip through
two implementations of the same specification is the evidence. The engine decides a
ring's role from its orientation on import, not from its position in the WKB: two
counter-clockwise rings become two exteriors and a lone clockwise ring an empty shape
(the first engine run), so the write side orients, exterior counter-clockwise and holes
clockwise, and a value written that way reads back as written. `TableOps.write_rows`
inherits the step when the adapter writes geometry itself.
"""

from __future__ import annotations

import struct

from ag.ports.geometry import Geometry, GeometryKind, Ring

POINT, LINESTRING, POLYGON, MULTIPOINT, MULTILINESTRING, MULTIPOLYGON = range(1, 7)
_CODES = {
    GeometryKind.POINT: POINT,
    GeometryKind.LINESTRING: LINESTRING,
    GeometryKind.POLYGON: POLYGON,
    GeometryKind.MULTIPOINT: MULTIPOINT,
    GeometryKind.MULTILINESTRING: MULTILINESTRING,
    GeometryKind.MULTIPOLYGON: MULTIPOLYGON,
}
_MEMBER = {
    GeometryKind.MULTIPOINT: GeometryKind.POINT,
    GeometryKind.MULTILINESTRING: GeometryKind.LINESTRING,
    GeometryKind.MULTIPOLYGON: GeometryKind.POLYGON,
}


def to_wkb(geometry: Geometry, *, order: str = "<") -> bytes:
    """The WKB of `geometry`; `order` is `<` (little-endian) or `>`."""
    return _geometry(geometry.kind, geometry.parts, order=order)


def empty(code: int, *, order: str = "<") -> bytes:
    """An empty geometry of `code`: a NaN point, or zero members or points."""
    if code == POINT:
        return _header(POINT, order) + struct.pack(
            f"{order}dd", float("nan"), float("nan")
        )
    return _header(code, order) + struct.pack(f"{order}I", 0)


def typed(code: int, *, order: str = "<") -> bytes:
    """A point payload under `code`, for the type codes the adapter refuses."""
    return _header(code, order) + struct.pack(f"{order}dd", 1.0, 2.0)


LAKE_OUTER: Ring = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
"""A lake's shore, counter-clockwise."""
LAKE_ISLAND: Ring = ((1.0, 1.0), (1.0, 2.0), (2.0, 2.0), (2.0, 1.0), (1.0, 1.0))
"""Its island, a hole, clockwise."""
LAKE_NEIGHBOUR: Ring = ((6.0, 0.0), (7.0, 0.0), (7.0, 1.0), (6.0, 1.0), (6.0, 0.0))
"""A second lake beside it, counter-clockwise."""


def multipolygon_with_hole(*, order: str = "<") -> bytes:
    """Two members, the first an exterior with a hole: a lake with an island beside a
    plain lake, as one row. `Geometry` holds one ring per member of a multi kind, so this
    is the shape it cannot hold; the engine keeps it as one row only with two or more
    members, since a one-member multipolygon is stored as a polygon."""
    lake = _header(POLYGON, order) + _rings((LAKE_OUTER, LAKE_ISLAND), order=order)
    neighbour = _header(POLYGON, order) + _rings((LAKE_NEIGHBOUR,), order=order)
    return _header(MULTIPOLYGON, order) + struct.pack(f"{order}I", 2) + lake + neighbour


def oriented(geometry: Geometry) -> Geometry:
    """`geometry` with a polygon's exterior counter-clockwise and its holes clockwise,
    and every member of a multipolygon counter-clockwise; other kinds as they are."""
    if geometry.kind is GeometryKind.POLYGON:
        exterior, *holes = geometry.parts
        parts = (_counter_clockwise(exterior), *(_clockwise(hole) for hole in holes))
    elif geometry.kind is GeometryKind.MULTIPOLYGON:
        parts = tuple(_counter_clockwise(member) for member in geometry.parts)
    else:
        return geometry
    return Geometry(kind=geometry.kind, parts=parts, crs=geometry.crs)


def signed_area(ring: Ring) -> float:
    """Twice the shoelace area: positive counter-clockwise, negative clockwise."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))


def _counter_clockwise(ring: Ring) -> Ring:
    return ring if signed_area(ring) >= 0 else tuple(reversed(ring))


def _clockwise(ring: Ring) -> Ring:
    return ring if signed_area(ring) <= 0 else tuple(reversed(ring))


def _geometry(kind: GeometryKind, parts: tuple[Ring, ...], *, order: str) -> bytes:
    head = _header(_CODES[kind], order)
    if kind is GeometryKind.POINT:
        return head + _point(parts[0][0], order=order)
    if kind is GeometryKind.LINESTRING:
        return head + _ring(parts[0], order=order)
    if kind is GeometryKind.POLYGON:
        return head + _rings(parts, order=order)
    member = _MEMBER[kind]
    body = b"".join(_geometry(member, (part,), order=order) for part in parts)
    return head + struct.pack(f"{order}I", len(parts)) + body


def _header(code: int, order: str) -> bytes:
    return (b"\x01" if order == "<" else b"\x00") + struct.pack(f"{order}I", code)


def _point(coordinate: tuple[float, float], *, order: str) -> bytes:
    return struct.pack(f"{order}dd", *coordinate)


def _ring(ring: Ring, *, order: str) -> bytes:
    return struct.pack(f"{order}I", len(ring)) + b"".join(
        _point(c, order=order) for c in ring
    )


def _rings(rings: tuple[Ring, ...], *, order: str) -> bytes:
    return struct.pack(f"{order}I", len(rings)) + b"".join(
        _ring(r, order=order) for r in rings
    )
