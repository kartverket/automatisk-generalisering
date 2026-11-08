"""Engine geometry to the `Geometry` value type, through well-known binary.

What: `WKB_TOKEN`, the cursor token that yields a row's shape as WKB and the one place it
is spelled; `geometry_from_wkb(value, crs=, where=)`, the `Geometry` of one row or None
for a null or empty shape; `is_null_shape(value)`, the same question answered from the
header alone, for a pass that only needs to know.

How: a pure parser over the six planar simple-feature type codes, point to multipolygon,
so the conversion touches no engine object and is tested without one (ADR-0018 AR-D23).
A polygon's rings are kept in WKB order, exterior first, closed as the engine writes
them, exterior counter-clockwise and holes clockwise, which is the orientation
`Geometry` holds canonical, so construction reverses nothing on read. A multi kind
becomes one part per member, so
a multipolygon member with more than one ring is refused: `Geometry` holds one ring per
member of a multi kind and cannot carry its holes. A multipart polygon with holes, a lake
with islands arriving as one row, is read after `explode_multipart`, which yields one
polygon with its holes per row, and not before. Any other type code, the curve codes,
the Z, M and ZM codes and the extended-WKB flags, is refused as well: the port carries
planar simple features and the dataset was already held to that before any row was
read. A refusal is a `PortContractError` naming the row through `where`. An empty
shape, zero members or zero points, is None, as a null geometry is; a value that is not
bytes is an adapter defect and a `TypeError`. ADR-0019 PC-D25.

Expected of the engine, confirmed by the first run under it: a null shape arrives as
None; an empty shape as None or as an empty WKB. A true curve arrives as neither a
densified ring nor a curve code but as the arc's vertices alone, a planar ring this
parser accepts (the probe of 2026-11-06), so a curve is geometry loss this codec cannot
see; what the port does about it is open (B33).

Second caller: `TableOps.write_rows`, ADR-0019 PC-D22, not yet landed.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from ag.ports.errors import PortContractError
from ag.ports.geometry import CRS, Coordinate, Geometry, GeometryKind, Ring

WKB_TOKEN = "SHAPE@WKB"
"""The cursor token for a row's shape as well-known binary."""

_POINT, _LINESTRING, _POLYGON, _MULTIPOINT, _MULTILINESTRING, _MULTIPOLYGON = range(
    1, 7
)
_KINDS = {
    _POINT: GeometryKind.POINT,
    _LINESTRING: GeometryKind.LINESTRING,
    _POLYGON: GeometryKind.POLYGON,
    _MULTIPOINT: GeometryKind.MULTIPOINT,
    _MULTILINESTRING: GeometryKind.MULTILINESTRING,
    _MULTIPOLYGON: GeometryKind.MULTIPOLYGON,
}
_MEMBER_OF = {
    _MULTIPOINT: _POINT,
    _MULTILINESTRING: _LINESTRING,
    _MULTIPOLYGON: _POLYGON,
}


def geometry_from_wkb(value: object, *, crs: CRS, where: str) -> Geometry | None:
    """The `Geometry` of one row from its WKB, in `crs`; None for a null or empty shape.

    `where` names the row for a refusal, such as `'<path>' row 3`.
    """
    data = _bytes(value)
    if data is None:
        return None
    wkb = _Wkb(data, where)
    order, code, offset = wkb.header(0)
    parts, _ = wkb.parts(code, order, offset)
    if not parts:
        return None
    return Geometry(kind=_KINDS[code], parts=parts, crs=crs)


def is_null_shape(value: object) -> bool:
    """Whether `value` is a null or an empty shape: None, or a WKB with no members or no
    points. Reads only what it needs; a shape it cannot read is not null."""
    data = _bytes(value)
    if data is None:
        return True
    wkb = _Wkb(data, "shape")
    try:
        order, code, offset = wkb.header(0)
    except PortContractError:
        return False
    if code == _POINT:
        point, _ = wkb.point(order, offset)
        return point is None
    count, _ = wkb.uint(order, offset)
    return count == 0


def _bytes(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes | bytearray):
        return bytes(value)
    if isinstance(value, memoryview):
        return value.tobytes()
    raise TypeError(
        f"{type(value).__name__} is not well-known binary; the cursor token "
        f"{WKB_TOKEN!r} yields bytes or None."
    )


@dataclass(frozen=True, slots=True)
class _Wkb:
    """One WKB value and the row it belongs to; every read takes an offset and returns
    the next, since each member of a multi kind carries its own header."""

    data: bytes
    where: str

    def header(self, offset: int) -> tuple[str, int, int]:
        """(byte order, type code, next offset); refuses any code but the six."""
        order = "<" if self.data[offset] == 1 else ">"
        code, offset = self.uint(order, offset + 1)
        if code not in _KINDS:
            raise PortContractError(
                f"{self.where}: WKB type {code} is not a planar simple feature; the port "
                "carries points, lines and polygons and their multi kinds, without "
                "Z, M or curves."
            )
        return order, code, offset

    def parts(self, code: int, order: str, offset: int) -> tuple[tuple[Ring, ...], int]:
        """The rings of one geometry of `code`: one for a point or line, the rings of a
        polygon, and one per member of a multi kind."""
        if code == _POINT:
            point, offset = self.point(order, offset)
            return (() if point is None else ((point,),)), offset
        if code == _LINESTRING:
            ring, offset = self.ring(order, offset)
            return ((ring,) if ring else ()), offset
        count, offset = self.uint(order, offset)
        if code == _POLYGON:
            rings: list[Ring] = []
            for _ in range(count):
                ring, offset = self.ring(order, offset)
                rings.append(ring)
            return tuple(rings), offset
        member_code = _MEMBER_OF[code]
        parts: list[Ring] = []
        for _ in range(count):
            member_order, found, offset = self.header(offset)
            if found != member_code:
                raise PortContractError(
                    f"{self.where}: a member of WKB type {code} has type {found}, not "
                    f"{member_code}."
                )
            member, offset = self.parts(member_code, member_order, offset)
            if len(member) > 1:
                raise PortContractError(
                    f"{self.where}: a multipolygon member with holes is not "
                    "representable as one row; Geometry holds one ring per member of "
                    "a multi kind."
                )
            parts.extend(member)
        return tuple(parts), offset

    def point(self, order: str, offset: int) -> tuple[Coordinate | None, int]:
        """One coordinate; None for the NaN pair that encodes an empty point."""
        x, y = struct.unpack_from(f"{order}dd", self.data, offset)
        if math.isnan(x) or math.isnan(y):
            return None, offset + 16
        return (float(x), float(y)), offset + 16

    def ring(self, order: str, offset: int) -> tuple[Ring, int]:
        count, offset = self.uint(order, offset)
        coordinates: list[Coordinate] = []
        for _ in range(count):
            point, offset = self.point(order, offset)
            if point is not None:
                coordinates.append(point)
        return tuple(coordinates), offset

    def uint(self, order: str, offset: int) -> tuple[int, int]:
        (value,) = struct.unpack_from(f"{order}I", self.data, offset)
        return int(value), offset + 4
