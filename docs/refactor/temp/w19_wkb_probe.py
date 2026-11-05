"""By-hand probe for the engine run of slice 1b: polygon WKB codes and ring orientation
(W19), and what the multipart tool does when `ORIG_FID` is already a field (W11).

Run inside the ArcPy image from the repository root, with `src` and the root on the path:

    python docs/refactor/temp/w19_wkb_probe.py

Writes five polygons to one feature class, reads each back as `SHAPE@WKB` and prints the
type code, the members, the rings per member and each ring's orientation; then explodes
the two holed ones and prints the children the same way. Then seeds the multilines case
with an `ORIG_FID` field holding 99, runs the multipart tool directly and prints the
output's fields and rows. Nothing here asserts; the output is pasted into the evidence.
"""

from __future__ import annotations

import struct
import tempfile

from ag.adapters.arcpy.session import open_session
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.ports import Field, FieldType, Schema
from tests.support import wkb
from tests.support.arcpy import gdb
from tests.support.cases import CRS, multilines
from tests.support.gdb_cases import cells_of

Ring = tuple[tuple[float, float], ...]

SQUARE_CCW: Ring = ((0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0), (0.0, 0.0))
HOLE_CCW: Ring = ((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0), (1.0, 1.0))


def reverse(ring: Ring) -> Ring:
    return tuple(reversed(ring))


def polygon(*rings: Ring, order: str = "<") -> bytes:
    body = struct.pack(f"{order}I", len(rings))
    for ring in rings:
        body += struct.pack(f"{order}I", len(ring))
        for x, y in ring:
            body += struct.pack(f"{order}dd", x, y)
    return (b"\x01" if order == "<" else b"\x00") + struct.pack(f"{order}I", 3) + body


def orientation(ring: Ring) -> str:
    area = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        area += x1 * y2 - x2 * y1
    return "CW" if area < 0 else "CCW"


def describe_wkb(data: object) -> str:
    """Type code, members, rings per member, each ring's vertex count and orientation."""
    if data is None:
        return "None"
    assert isinstance(data, bytes | bytearray | memoryview)
    data = bytes(data)
    offset = 0

    def uint() -> int:
        nonlocal offset
        order = "<" if data[0] == 1 else ">"
        (value,) = struct.unpack_from(f"{order}I", data, offset)
        offset += 4
        return value

    def header() -> int:
        nonlocal offset
        offset += 1
        return uint()

    def ring() -> str:
        nonlocal offset
        order = "<" if data[0] == 1 else ">"
        count = uint()
        points: list[tuple[float, float]] = []
        for _ in range(count):
            x, y = struct.unpack_from(f"{order}dd", data, offset)
            offset += 16
            points.append((x, y))
        return f"{count} pts {orientation(tuple(points))}"

    code = header()
    if code == 3:
        count = uint()
        return f"type 3 POLYGON rings={count} [" + ", ".join(ring() for _ in range(count)) + "]"
    if code == 6:
        members = uint()
        parts: list[str] = []
        for _ in range(members):
            member_code = header()
            rings = uint()
            parts.append(
                f"member type {member_code} rings={rings} ["
                + ", ".join(ring() for _ in range(rings))
                + "]"
            )
        return f"type 6 MULTIPOLYGON members={members} " + "; ".join(parts)
    return f"type {code} (not summarised here), {len(data)} bytes"


def main() -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w19_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    schema = Schema(fields=(Field("name", FieldType.TEXT, 30),), geometry_crs=CRS)
    shapes: dict[str, bytes] = {
        "single_ccw": polygon(SQUARE_CCW),
        "single_cw": polygon(reverse(SQUARE_CCW)),
        "hole_esri": polygon(reverse(SQUARE_CCW), HOLE_CCW),
        "hole_ogc": polygon(SQUARE_CCW, reverse(HOLE_CCW)),
        "hole_same": polygon(SQUARE_CCW, HOLE_CCW),
        "multi_hole_test_encoder": wkb.multipolygon_with_hole(),
    }
    print("== written ==")
    for name, data in shapes.items():
        print(f"{name:26} {describe_wkb(data)}")
    gdb.seed(
        session,
        workspace=workspace,
        name="polys",
        schema=schema,
        cells=[(name, data) for name, data in shapes.items()],
        geometry_type="POLYGON",
    )
    print("== read back as SHAPE@WKB ==")
    for name, data in gdb.read_cells(
        session, path=f"{workspace}/polys", tokens=("name", WKB_TOKEN)
    ):
        print(f"{name!s:26} {describe_wkb(data)}")
    session.run_tool(
        "management.MultipartToSinglepart",
        in_features=f"{workspace}/polys",
        out_feature_class=f"{workspace}/polys_exploded",
    )
    print("== children of MultipartToSinglepart ==")
    for name, parent, data in gdb.read_cells(
        session,
        path=f"{workspace}/polys_exploded",
        tokens=("name", "ORIG_FID", WKB_TOKEN),
    ):
        print(f"{name!s:26} parent={parent} {describe_wkb(data)}")

    print("== ORIG_FID already a field ==")
    case = multilines()
    cells = [(name, 99, shape) for name, shape in cells_of(case.schema, case.rows)]
    taken = Schema(
        fields=(*case.schema.fields, Field("ORIG_FID", FieldType.LONG)), geometry_crs=CRS
    )
    gdb.seed(
        session,
        workspace=workspace,
        name="taken",
        schema=taken,
        cells=cells,
        geometry_type="POLYLINE",
    )
    session.run_tool(
        "management.MultipartToSinglepart",
        in_features=f"{workspace}/taken",
        out_feature_class=f"{workspace}/taken_exploded",
    )
    import arcpy  # the probe is by hand and outside the scanned roots

    print("output fields:", [f.name for f in arcpy.Describe(f"{workspace}/taken_exploded").fields])
    for row in gdb.read_cells(
        session, path=f"{workspace}/taken_exploded", tokens=("OID@", "name", "ORIG_FID")
    ):
        print("  ", row)
    print("input ORIG_FID values after the tool:")
    for row in gdb.read_cells(session, path=f"{workspace}/taken", tokens=("OID@", "ORIG_FID")):
        print("  ", row)


if __name__ == "__main__":
    main()
