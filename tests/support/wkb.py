"""Well-known binary for tests: `Geometry` values and hand-built edge cases to bytes.

What: `to_wkb(geometry, order=)`, the planar WKB of a value in either byte order;
`empty(code)`, an empty geometry of a type code; `typed(code)`, a point payload under any
type code, for the codes the adapter refuses; `multipolygon_with_hole()`, the one shape
`Geometry` cannot hold.

Why: the adapter's codec is a parser and nothing in the package writes WKB yet, so the
tests carry the encoder. It is independent of the codec on purpose: a round trip through
two implementations of the same specification is the evidence.
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


def multipolygon_with_hole(*, order: str = "<") -> bytes:
    """One member with an exterior and a hole: the shape `Geometry` cannot hold."""
    outer: Ring = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
    inner: Ring = ((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (1.0, 1.0))
    member = _header(POLYGON, order) + _rings((outer, inner), order=order)
    return _header(MULTIPOLYGON, order) + struct.pack(f"{order}I", 1) + member


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
