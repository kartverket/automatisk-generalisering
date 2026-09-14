"""T0.1 gate: 64-bit storage capability. THROWAWAY.

Runs the cases listed under T0.1 in TASKS.md and prints what the written finding has to
record. Nothing here asserts quietly: every case prints its observations, and a case
that raises prints the full traceback and the run continues.

Depends on arcpy and the standard library only. It imports nothing from `ag`, because
the gate exists to be answered before any of that code is built on it.

WHERE IT RUNS. In the Linux production image. Windows Pro is an optional cross-check;
run it there too and diff the two outputs if you want a divergence detector.

    python t0_1_bigint_gate.py --workdir /data/t0_1 --image-ref ghcr.io/...:12.0
    python t0_1_bigint_gate.py --workdir /data/t0_1 --only case_type_survival
    python t0_1_bigint_gate.py --workdir /data/t0_1 --archive-gdb /mnt/archive/probe.gdb
    python t0_1_bigint_gate.py --workdir /data/t0_1 --skip-large

Case functions are named by description, matching T0.1's case titles, never by number.

SIGNATURES. Checked against the Esri tool pages on 2026-09-14: PairwiseDissolve,
JoinField, ExportFeatures, AddField, SimplifyLine, SimplifyPolygon,
ResolveRoadConflicts, PropagateDisplacement, TableToNumPyArray, Intersect,
CreateFileGDB, MinimumBoundingGeometry, FeatureToPoint, Merge. Written from memory and
NOT checked that day: CopyFeatures, Select, PairwiseBuffer, SmoothLine, SmoothPolygon,
Densify, Snap, RepairGeometry, MakeFeatureLayer, the FieldMappings API. A signature
error on one of those surfaces as a printed traceback in its own block, not a silent
pass.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import time
import traceback
from collections.abc import Callable, Iterable, Sequence

import arcpy

TWO_53 = 2**53
LAYOUT_MAX = 2**52 - 1
"""A10.1's largest generated-id magnitude."""

SPATIAL_REFERENCE = 25833
"""ETRS89 / UTM zone 33N."""

LINEAGE = "lineage_id"


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def record(key: str, value: object) -> None:
    print(f"  {key}: {value}")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def generated_id(minter: int, counter: int) -> int:
    """A10.1: negative, magnitude [minter (20) | counter (32)]."""
    return -((minter << 32) | counter)


TYPICAL_GENERATED = [
    generated_id(1, 1),
    generated_id(7, 5),
    generated_id(1, 2**31),
    generated_id(1, 2**32 - 1),
    generated_id(2**20 - 1, 2**32 - 1),
]
TYPICAL_RAW = [1, 42, 70_000]


class Workspace:
    def __init__(self, root: str) -> None:
        self.root = root
        os.makedirs(root, exist_ok=True)
        self._counter = 0

    def gdb(self, stem: str, version: str = "CURRENT") -> str:
        self._counter += 1
        name = f"{stem}_{self._counter}.gdb"
        path = os.path.join(self.root, name)
        if os.path.exists(path):
            shutil.rmtree(path)
        arcpy.management.CreateFileGDB(self.root, name, version)
        return path


def create_fc(
    gdb: str,
    name: str,
    geometry: str,
    fields: Sequence[tuple[str, str]] = ((LINEAGE, "BIGINTEGER"),),
) -> str:
    arcpy.management.CreateFeatureclass(
        gdb, name, geometry, spatial_reference=arcpy.SpatialReference(SPATIAL_REFERENCE)
    )
    path = os.path.join(gdb, name)
    for field_name, field_type in fields:
        arcpy.management.AddField(path, field_name, field_type)
    return path


def create_table(gdb: str, name: str, fields: Sequence[tuple[str, str]]) -> str:
    arcpy.management.CreateTable(gdb, name)
    path = os.path.join(gdb, name)
    for field_name, field_type in fields:
        arcpy.management.AddField(path, field_name, field_type)
    return path


def insert(path: str, fields: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    with arcpy.da.InsertCursor(path, list(fields)) as cursor:
        for row in rows:
            cursor.insertRow(list(row))


def read(path: str, fields: Sequence[str], where: str | None = None) -> list[tuple]:
    with arcpy.da.SearchCursor(path, list(fields), where_clause=where) as cursor:
        return [tuple(row) for row in cursor]


def fields_of(path: str) -> list[tuple[str, str, int]]:
    return [(f.name, f.type, f.length) for f in arcpy.ListFields(path)]


def field_named(path: str, name: str) -> tuple[str, int] | None:
    for f in arcpy.ListFields(path):
        if f.name.lower() == name.lower():
            return f.type, f.length
    return None


def lineage_like(path: str) -> list[tuple[str, str, int]]:
    return [f for f in fields_of(path) if "lineage" in f[0].lower()]


def point_rows(ids: Sequence[int]) -> list[tuple[tuple[float, float], int]]:
    return [((500_000.0 + i * 100.0, 6_600_000.0), value) for i, value in enumerate(ids)]


def square(x: float, y: float, side: float) -> arcpy.Polygon:
    corners = [(x, y), (x + side, y), (x + side, y + side), (x, y + side), (x, y)]
    return arcpy.Polygon(
        arcpy.Array([arcpy.Point(*c) for c in corners]),
        arcpy.SpatialReference(SPATIAL_REFERENCE),
    )


def polyline(coords: Sequence[tuple[float, float]]) -> arcpy.Polyline:
    return arcpy.Polyline(
        arcpy.Array([arcpy.Point(*c) for c in coords]),
        arcpy.SpatialReference(SPATIAL_REFERENCE),
    )


def compare_ids(path: str, expected: Iterable[int]) -> None:
    """Presence, type, and value survival of lineage_id on one output."""
    info = field_named(path, LINEAGE)
    record("lineage_id present", info is not None)
    if info is None:
        record("fields on output", fields_of(path))
        return
    record("lineage_id field type", f"{info[0]} (length {info[1]})")
    values = [row[0] for row in read(path, [LINEAGE])]
    record("row count", len(values))
    record("python types seen", sorted({type(v).__name__ for v in values}))
    record("all int", all(type(v) is int for v in values))
    record("value set equals input set", set(values) == set(expected))
    missing = set(expected) - set(values)
    if missing:
        record("input ids absent from output (first 5)", sorted(missing)[:5])


# ---------------------------------------------------------------------------
# Cases 1 to 5: the field itself
# ---------------------------------------------------------------------------


def case_under_2_53(ws: Workspace) -> None:
    """A value just under 2^53 writes and reads back unchanged."""
    gdb = ws.gdb("under_2_53")
    fc = create_fc(gdb, "pts", "POINT")
    value = TWO_53 - 1
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows([value]))
    (read_back,) = read(fc, [LINEAGE])[0]
    record("written", value)
    record("read back", read_back)
    record("equal", read_back == value)
    record("type", type(read_back).__name__)


def case_2_53_plus_1(ws: Workspace) -> None:
    """2^53 + 1, not 2^53: does it error or silently coerce?

    2^53 is exactly representable as a float, so it would pass through a float path
    unchanged and prove nothing. Two write paths are tried: a cursor and CalculateField.
    """
    value = TWO_53 + 1
    record("value", value)

    gdb = ws.gdb("plus_1_cursor")
    fc = create_fc(gdb, "pts", "POINT")
    try:
        insert(fc, ["SHAPE@XY", LINEAGE], point_rows([value]))
        rows = read(fc, [LINEAGE])
        got = rows[0][0] if rows else None
        record("cursor write", "no error")
        record("cursor read back", got)
        record("cursor equal", got == value)
        record("cursor coerced to 2^53", got == TWO_53)
    except Exception as exc:  # the error text is the finding
        record("cursor write raised", f"{type(exc).__name__}: {exc}")

    gdb = ws.gdb("plus_1_calculate")
    fc = create_fc(gdb, "pts", "POINT")
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows([0]))
    try:
        arcpy.management.CalculateField(fc, LINEAGE, str(value), "PYTHON3")
        got = read(fc, [LINEAGE])[0][0]
        record("CalculateField write", "no error")
        record("CalculateField read back", got)
        record("CalculateField equal", got == value)
        record("CalculateField coerced to 2^53", got == TWO_53)
    except Exception as exc:
        record("CalculateField raised", f"{type(exc).__name__}: {exc}")


def case_round_trip_int_type(ws: Workspace) -> None:
    """Round trip asserting `type(value) is int`, not only equality.

    4503599627370495.0 == 4503599627370495 is True, so equality alone passes on a value
    that has been through a float. The port's write_rows/read_rows compile to these
    cursors on arcpy.
    """
    gdb = ws.gdb("round_trip")
    fc = create_fc(gdb, "pts", "POINT")
    values = [LAYOUT_MAX, -LAYOUT_MAX, *TYPICAL_GENERATED, *TYPICAL_RAW]
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows(values))
    for written, (got,) in zip(values, read(fc, [LINEAGE])):
        print(
            f"  written {written:>22}  read {got!r:>24}  "
            f"equal {got == written!s:5}  type(value) is int {type(got) is int}"
        )


def case_typical_generated_ids(ws: Workspace) -> None:
    """Ordinary generated ids, magnitude >= 2^32, through three 32-bit traps."""
    record("generated ids", TYPICAL_GENERATED)

    gdb = ws.gdb("typical_bigint")
    fc = create_fc(gdb, "pts", "POINT")
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows(TYPICAL_GENERATED + TYPICAL_RAW))
    compare_ids(fc, TYPICAL_GENERATED + TYPICAL_RAW)

    print("  -- LONG output schema")
    gdb = ws.gdb("typical_long")
    fc = create_fc(gdb, "pts", "POINT", fields=((LINEAGE, "LONG"),))
    for value in TYPICAL_GENERATED:
        try:
            insert(fc, ["SHAPE@XY", LINEAGE], point_rows([value]))
            got = read(fc, [LINEAGE])[-1][0]
            record(f"LONG write {value}", f"no error, read back {got!r}")
        except Exception as exc:
            record(f"LONG write {value}", f"raised {type(exc).__name__}: {exc}")

    print("  -- int32 dtype")
    gdb = ws.gdb("typical_dtype")
    fc = create_fc(gdb, "pts", "POINT")
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows(TYPICAL_GENERATED))
    array = arcpy.da.FeatureClassToNumPyArray(fc, [LINEAGE])
    record("FeatureClassToNumPyArray dtype", repr(array.dtype))
    record("values", array[LINEAGE].tolist())
    record("equal to written", array[LINEAGE].tolist() == TYPICAL_GENERATED)

    print("  -- where-clause literal")
    for value in TYPICAL_GENERATED:
        try:
            hits = read(fc, [LINEAGE], where=f"{LINEAGE} = {value}")
            record(f"where {LINEAGE} = {value}", f"{len(hits)} row(s)")
        except Exception as exc:
            record(f"where {LINEAGE} = {value}", f"raised {type(exc).__name__}: {exc}")


def case_predicate_filter(ws: Workspace) -> None:
    """Predicate filters on the field: equality, range, IN, and a feature layer."""
    gdb = ws.gdb("predicate")
    fc = create_fc(gdb, "pts", "POINT")
    values = TYPICAL_GENERATED + TYPICAL_RAW
    insert(fc, ["SHAPE@XY", LINEAGE], point_rows(values))

    clauses = {
        "equality on a generated id": (f"{LINEAGE} = {TYPICAL_GENERATED[2]}", 1),
        "less than -2^32": (f"{LINEAGE} < {-(2**32)}", len(TYPICAL_GENERATED)),
        "greater than zero": (f"{LINEAGE} > 0", len(TYPICAL_RAW)),
        "IN over generated ids": (
            f"{LINEAGE} IN ({', '.join(str(v) for v in TYPICAL_GENERATED)})",
            len(TYPICAL_GENERATED),
        ),
    }
    for label, (clause, expected) in clauses.items():
        try:
            hits = len(read(fc, [LINEAGE], where=clause))
            record(label, f"{hits} row(s), expected {expected}, ok {hits == expected}")
        except Exception as exc:
            record(label, f"raised {type(exc).__name__}: {exc}")

    layer = arcpy.management.MakeFeatureLayer(fc, "pred_layer")[0]
    clause, expected = clauses["IN over generated ids"]
    arcpy.management.SelectLayerByAttribute(layer, "NEW_SELECTION", clause)
    count = int(arcpy.management.GetCount(layer)[0])
    record("SelectLayerByAttribute IN", f"{count} selected, expected {expected}")
    arcpy.management.Delete(layer)


# ---------------------------------------------------------------------------
# Case 6: type survival through carrying tools
# ---------------------------------------------------------------------------


def _input_polygons(gdb: str) -> tuple[str, list[int]]:
    """Ordinary squares plus two tiny squares SimplifyPolygon's minimum area removes."""
    fc = create_fc(gdb, "polys", "POLYGON")
    ids = TYPICAL_GENERATED + TYPICAL_RAW
    rows = [(square(500_000.0 + i * 1_000.0, 6_600_000.0, 400.0), v) for i, v in enumerate(ids)]
    tiny_ids = [generated_id(3, 1), generated_id(3, 2)]
    rows += [
        (square(520_000.0 + i * 1_000.0, 6_600_000.0, 3.0), v) for i, v in enumerate(tiny_ids)
    ]
    insert(fc, ["SHAPE@", LINEAGE], rows)
    return fc, ids + tiny_ids


def _input_lines(gdb: str) -> tuple[str, list[int]]:
    """Ordinary zig-zags plus small closed loops that simplify to zero length."""
    fc = create_fc(gdb, "lines", "POLYLINE")
    ids = TYPICAL_GENERATED + TYPICAL_RAW
    rows = []
    for i, v in enumerate(ids):
        x0, y0 = 500_000.0, 6_600_000.0 + i * 1_000.0
        coords = [(x0 + k * 50.0, y0 + (15.0 if k % 2 else 0.0)) for k in range(21)]
        rows.append((polyline(coords), v))
    loop_ids = [generated_id(4, 1), generated_id(4, 2)]
    for i, v in enumerate(loop_ids):
        x0, y0 = 540_000.0 + i * 1_000.0, 6_600_000.0
        coords = [(x0, y0), (x0 + 4.0, y0), (x0 + 4.0, y0 + 4.0), (x0, y0 + 4.0), (x0, y0)]
        rows.append((polyline(coords), v))
    insert(fc, ["SHAPE@", LINEAGE], rows)
    return fc, ids + loop_ids


def _field_mappings_for(inputs: Sequence[str], force_big_integer: bool) -> arcpy.FieldMappings:
    mappings = arcpy.FieldMappings()
    for path in inputs:
        mappings.addTable(path)
    index = mappings.findFieldMapIndex(LINEAGE)
    field_map = mappings.getFieldMap(index)
    output_field = field_map.outputField
    record("field map output type before run", output_field.type)
    if force_big_integer:
        output_field.type = "BigInteger"
        field_map.outputField = output_field
        mappings.replaceFieldMap(index, field_map)
        record("field map output type forced to", "BigInteger")
    return mappings


def _run_tool(label: str, run: Callable[[], str], expected: Sequence[int]) -> None:
    print(f"  -- {label}")
    try:
        started = time.perf_counter()
        out = run()
        record("elapsed s", round(time.perf_counter() - started, 2))
        compare_ids(out, expected)
    except Exception as exc:
        record("raised", f"{type(exc).__name__}: {exc}")


def _derived_points(label: str, main_out: str, input_count: int) -> None:
    """simplify.collapsed_points: presence, then a reference column, then type."""
    points = main_out + "_Pnt"
    print(f"  -- {label} derived point output ({os.path.basename(points)})")
    if not arcpy.Exists(points):
        record("point output exists", False)
        return
    record("point output exists", True)
    record("point output fields", fields_of(points))
    record("point output row count", int(arcpy.management.GetCount(points)[0]))
    record("lineage_id present on points", field_named(points, LINEAGE) is not None)
    record("main output row count", int(arcpy.management.GetCount(main_out)[0]))
    record("input row count", input_count)
    record(
        "main output reference fields",
        [f for f in fields_of(main_out) if f[0].lower() in ("inline_fid", "inpoly_fid")],
    )
    reference = next(
        (f[0] for f in fields_of(points) if f[0].lower() in ("inline_fid", "inpoly_fid")), None
    )
    if reference is not None:
        per_input: dict[object, int] = {}
        for (fid,) in read(points, [reference]):
            per_input[fid] = per_input.get(fid, 0) + 1
        record(f"points per {reference} value", dict(sorted(per_input.items(), key=str)))
    print(
        "  NOTE: the tool pages say the point output 'will not contain' the input's "
        "fields. Record whether ANY column on the points references an input feature "
        "(a native-index reference), and how many points each collapsed input produced "
        "(SimplifyLine documents 'endpoints', which may be two per line)."
    )


def _simplify_line_collapse_probe(gdb: str) -> None:
    """Which input shape and algorithm make SimplifyLine emit collapsed points at all.

    The zig-zag input keeps its 4 m loops under POINT_REMOVE, so its point output is
    empty and says nothing about how many points a collapsed line produces.
    """
    print("  -- SimplifyLine collapse probe: small shapes, 30 m tolerance, each algorithm")
    fc = create_fc(gdb, "collapse_candidates", "POLYLINE")
    x0, y0 = 560_000.0, 6_600_000.0
    shapes = {
        "closed 4 m loop": [(x0, y0), (x0 + 4.0, y0), (x0 + 4.0, y0 + 4.0), (x0, y0 + 4.0), (x0, y0)],
        "4 m hairpin": [(x0 + 100.0, y0), (x0 + 104.0, y0), (x0 + 100.0, y0 + 0.5)],
        "2 m straight segment": [(x0 + 200.0, y0), (x0 + 202.0, y0)],
        # The tool page: collapsed points are for lines "smaller than the spatial tolerance
        # of the data", which is the XY tolerance (0.001 m by default), not the 30 m here.
        "0.5 mm segment, under the XY tolerance": [(x0 + 300.0, y0), (x0 + 300.0005, y0)],
    }
    ids: list[int] = []
    for i, (name, coords) in enumerate(shapes.items()):
        value = generated_id(5, i + 1)
        try:
            insert(fc, ["SHAPE@", LINEAGE], [(polyline(coords), value)])
            ids.append(value)
        except Exception as exc:
            record(f"insert {name} raised", f"{type(exc).__name__}: {exc}")
    names = dict(zip((generated_id(5, i + 1) for i in range(len(shapes))), shapes))
    record(
        "candidates (OBJECTID, shape, lineage_id, length m)",
        [(oid, names[v], v, length) for oid, v, length in read(fc, ["OID@", LINEAGE, "SHAPE@LENGTH"])],
    )
    for algorithm in ("POINT_REMOVE", "BEND_SIMPLIFY", "WEIGHTED_AREA", "EFFECTIVE_AREA"):
        result = os.path.join(gdb, f"collapse_{algorithm.lower()}")
        try:
            arcpy.cartography.SimplifyLine(
                fc, result, algorithm, "30 Meters",
                collapsed_point_option="KEEP_COLLAPSED_POINTS",
            )
        except Exception as exc:
            record(f"{algorithm} raised", f"{type(exc).__name__}: {exc}")
            continue
        record(f"{algorithm} lineage_id kept on main output", sorted(r[0] for r in read(result, [LINEAGE])))
        _derived_points(f"SimplifyLine {algorithm}", result, len(ids))


def case_type_survival(ws: Workspace) -> None:
    """Every ONE + CARRY method's expected arcpy tool: does lineage_id keep its type?"""
    gdb = ws.gdb("type_survival")
    polys, poly_ids = _input_polygons(gdb)
    lines, line_ids = _input_lines(gdb)
    record("input polygons", f"{len(poly_ids)} rows, {field_named(polys, LINEAGE)}")
    record("input lines", f"{len(line_ids)} rows, {field_named(lines, LINEAGE)}")

    def out(name: str) -> str:
        return os.path.join(gdb, name)

    # map_fields runs first: it is the call B9(d) is about.
    for force in (False, True):
        suffix = "_forced" if force else ""

        def export(force: bool = force, suffix: str = suffix) -> str:
            mappings = _field_mappings_for([polys], force)
            arcpy.conversion.ExportFeatures(
                polys, out(f"export{suffix}"), field_mapping=mappings
            )
            return out(f"export{suffix}")

        _run_tool(f"map_fields -> ExportFeatures with FieldMappings{suffix}", export, poly_ids)

    second = create_fc(gdb, "polys_b", "POLYGON")
    second_ids = [generated_id(9, 1), generated_id(9, 2)]
    insert(
        second,
        ["SHAPE@", LINEAGE],
        [(square(600_000.0 + i * 1_000.0, 6_600_000.0, 400.0), v) for i, v in enumerate(second_ids)],
    )
    for force in (False, True):
        suffix = "_forced" if force else ""

        def merge(force: bool = force, suffix: str = suffix) -> str:
            mappings = _field_mappings_for([polys, second], force)
            arcpy.management.Merge([polys, second], out(f"merge{suffix}"), mappings)
            return out(f"merge{suffix}")

        _run_tool(f"merge -> Merge with FieldMappings{suffix}", merge, poly_ids + second_ids)

    def copy() -> str:
        arcpy.management.CopyFeatures(polys, out("copy"))
        return out("copy")

    def select() -> str:
        # "select" is a reserved SQL keyword and is refused as an output name.
        arcpy.analysis.Select(polys, out("selected"), f"{LINEAGE} IS NOT NULL")
        return out("selected")

    def buffer() -> str:
        arcpy.analysis.PairwiseBuffer(polys, out("buffer"), "10 Meters")
        return out("buffer")

    def simplify_line() -> str:
        arcpy.cartography.SimplifyLine(
            lines, out("simplify_line"), "POINT_REMOVE", "30 Meters",
            collapsed_point_option="KEEP_COLLAPSED_POINTS",
        )
        return out("simplify_line")

    def simplify_polygon() -> str:
        arcpy.cartography.SimplifyPolygon(
            polys, out("simplify_polygon"), "POINT_REMOVE", "5 Meters",
            minimum_area="100 SquareMeters",
            collapsed_point_option="KEEP_COLLAPSED_POINTS",
        )
        return out("simplify_polygon")

    def smooth_line() -> str:
        arcpy.cartography.SmoothLine(lines, out("smooth_line"), "PAEK", "100 Meters")
        return out("smooth_line")

    def smooth_polygon() -> str:
        arcpy.cartography.SmoothPolygon(polys, out("smooth_polygon"), "PAEK", "100 Meters")
        return out("smooth_polygon")

    def centroid() -> str:
        arcpy.management.FeatureToPoint(polys, out("centroid"), "CENTROID")
        return out("centroid")

    def point_on_surface() -> str:
        arcpy.management.FeatureToPoint(polys, out("inside"), "INSIDE")
        return out("inside")

    def convex_hull() -> str:
        arcpy.management.MinimumBoundingGeometry(polys, out("hull"), "CONVEX_HULL", "NONE")
        return out("hull")

    _run_tool("copy -> CopyFeatures", copy, poly_ids)
    _run_tool("select -> Select", select, poly_ids)
    _run_tool("buffer -> PairwiseBuffer", buffer, poly_ids)
    _run_tool("simplify -> SimplifyLine", simplify_line, line_ids)
    _derived_points("SimplifyLine", out("simplify_line"), len(line_ids))
    _simplify_line_collapse_probe(gdb)
    _run_tool("simplify -> SimplifyPolygon", simplify_polygon, poly_ids)
    _derived_points("SimplifyPolygon", out("simplify_polygon"), len(poly_ids))
    _run_tool("smooth -> SmoothLine", smooth_line, line_ids)
    _run_tool("smooth -> SmoothPolygon", smooth_polygon, poly_ids)
    _run_tool("centroid -> FeatureToPoint CENTROID", centroid, poly_ids)
    _run_tool("point_on_surface -> FeatureToPoint INSIDE", point_on_surface, poly_ids)
    _run_tool("collapse_to_point -> FeatureToPoint (same tool as centroid)", centroid, poly_ids)
    _run_tool("convex_hull -> MinimumBoundingGeometry CONVEX_HULL", convex_hull, poly_ids)

    print("  -- in-place editors: n/a by construction; confirming the type is unchanged")
    for label, run in (
        ("densify -> Densify", lambda p: arcpy.edit.Densify(p, "DISTANCE", "10 Meters")),
        ("snap -> Snap", lambda p: arcpy.edit.Snap(p, [[second, "VERTEX", "5 Meters"]])),
        ("make_valid -> RepairGeometry", lambda p: arcpy.management.RepairGeometry(p)),
    ):
        target = out(f"inplace_{label.split(' ')[0]}")
        arcpy.management.CopyFeatures(polys, target)
        before = field_named(target, LINEAGE)
        try:
            run(target)
            record(label, f"before {before}, after {field_named(target, LINEAGE)}")
        except Exception as exc:
            record(label, f"raised {type(exc).__name__}: {exc}")

    _cartography_in_place(gdb, lines, line_ids, polys)


def _cartography_in_place(gdb: str, lines: str, line_ids: list[int], polys: str) -> None:
    """ResolveRoadConflicts and PropagateDisplacement need an Advanced licence.

    Also records what B11 needs about the displacement output: its columns, and the
    mapping shape if a reference column exists. Row count alone cannot establish ONE.
    """
    print("  -- cartography in-place tools")
    record("ProductInfo", arcpy.ProductInfo())
    record("CheckProduct ArcInfo (Advanced)", arcpy.CheckProduct("ArcInfo"))
    arcpy.env.referenceScale = 100_000

    roads = os.path.join(gdb, "roads_for_rrc")
    arcpy.management.CopyFeatures(lines, roads)
    arcpy.management.AddField(roads, "hierarchy", "LONG")
    arcpy.management.CalculateField(roads, "hierarchy", "1", "PYTHON3")
    displacement = os.path.join(gdb, "rrc_displacement")
    layer = arcpy.management.MakeFeatureLayer(roads, "rrc_roads")[0]
    before = field_named(roads, LINEAGE)
    try:
        arcpy.cartography.ResolveRoadConflicts([layer], "hierarchy", displacement)
        record("displace_features -> ResolveRoadConflicts", "ran")
        record("input lineage_id before / after", f"{before} / {field_named(roads, LINEAGE)}")
        if arcpy.Exists(displacement):
            record("displacement output fields", fields_of(displacement))
            record("displacement row count", int(arcpy.management.GetCount(displacement)[0]))
            record("input row count", len(line_ids))
            print(
                "  NOTE for B11: if any displacement column references input features, "
                "record the mapping shape from it (1:1, 1:N, N:1). If none does, record "
                "the mapping shape as UNDETERMINABLE; do not infer it from row counts."
            )
        else:
            record("displacement output exists", False)
    except Exception as exc:
        record("ResolveRoadConflicts raised", f"{type(exc).__name__}: {exc}")
    finally:
        arcpy.management.Delete(layer)

    record(
        "ResolveBuildingConflicts",
        "NOT RUN: needs building, barrier and hierarchy setup; its tool page carries the "
        "same in-place statement. Run by hand if the finding needs it.",
    )

    points = os.path.join(gdb, "propagate_points")
    arcpy.management.FeatureToPoint(polys, points, "CENTROID")
    before = field_named(points, LINEAGE)
    try:
        if arcpy.Exists(displacement):
            arcpy.cartography.PropagateDisplacement(points, displacement, "AUTO")
            record(
                "propagate_displacement -> PropagateDisplacement",
                f"before {before}, after {field_named(points, LINEAGE)}",
            )
        else:
            record("PropagateDisplacement", "NOT RUN: no displacement output to propagate")
    except Exception as exc:
        record("PropagateDisplacement raised", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Cases 7 to 9: joins and arrays
# ---------------------------------------------------------------------------


def case_overlay_duplicate(ws: Workspace) -> None:
    """Does a duplicate lineage_id appear, and under what name? Intersect and JoinField.

    The JoinField page states a same-named joined field is 'appended with _1'. Intersect's
    page says nothing. The finding states whether the two tools agree.
    """
    gdb = ws.gdb("overlay_duplicate")
    a = create_fc(gdb, "a", "POLYGON")
    b = create_fc(gdb, "b", "POLYGON")
    insert(a, ["SHAPE@", LINEAGE], [(square(500_000.0, 6_600_000.0, 400.0), generated_id(1, 1))])
    insert(b, ["SHAPE@", LINEAGE], [(square(500_200.0, 6_600_200.0, 400.0), generated_id(2, 1))])

    print("  -- Intersect, join_attributes ALL")
    out = os.path.join(gdb, "intersect")
    try:
        arcpy.analysis.Intersect([a, b], out, "ALL")
        record("fields containing 'lineage'", lineage_like(out))
        names = [f[0] for f in lineage_like(out)]
        record("values", read(out, names))
    except Exception as exc:
        record("raised", f"{type(exc).__name__}: {exc}")

    print("  -- JoinField with a lineage-bearing join table")
    target = create_fc(gdb, "target", "POINT", fields=((LINEAGE, "BIGINTEGER"), ("key", "LONG")))
    insert(
        target,
        ["SHAPE@XY", LINEAGE, "key"],
        [((500_000.0, 6_600_000.0), generated_id(1, 1), 1)],
    )
    join = create_table(gdb, "join", fields=(("key", "LONG"), (LINEAGE, "BIGINTEGER")))
    insert(join, ["key", LINEAGE], [(1, generated_id(5, 5))])
    try:
        arcpy.management.JoinField(target, "key", join, "key", [LINEAGE])
        record("fields containing 'lineage'", lineage_like(target))
        names = [f[0] for f in lineage_like(target)]
        record("values", read(target, names))
        print(
            "  NOTE: record each lineage field's type as well as its name. T0.6's JoinField "
            "path depends on the transferred field arriving as BigInteger."
        )
    except Exception as exc:
        record("raised", f"{type(exc).__name__}: {exc}")


def case_joinfield_bigint_key(ws: Workspace) -> None:
    """JoinField keyed on BIGINT on both sides, with generated ids above 2^32."""
    gdb = ws.gdb("joinfield_key")
    target = create_fc(gdb, "target", "POINT")
    values = TYPICAL_GENERATED + TYPICAL_RAW
    insert(target, ["SHAPE@XY", LINEAGE], point_rows(values))
    join = create_table(gdb, "join", fields=(("join_key", "BIGINTEGER"), ("payload", "LONG")))
    insert(join, ["join_key", "payload"], [(v, i + 1) for i, v in enumerate(values)])
    try:
        arcpy.management.JoinField(target, LINEAGE, join, "join_key", ["payload"])
        rows = read(target, [LINEAGE, "payload"])
        matched = sum(1 for _, p in rows if p is not None)
        record("rows", len(rows))
        record("matched", matched)
        record("unmatched ids", [lid for lid, p in rows if p is None])
        record(
            "correct pairing",
            all(p == values.index(lid) + 1 for lid, p in rows if p is not None),
        )
    except Exception as exc:
        record("raised", f"{type(exc).__name__}: {exc}")


def case_table_to_numpy_dtype(ws: Workspace) -> None:
    """TableToNumPyArray dtype for a BIGINT field, recorded verbatim."""
    gdb = ws.gdb("numpy_dtype")
    table = create_table(gdb, "t", fields=((LINEAGE, "BIGINTEGER"),))
    values = TYPICAL_GENERATED + [LAYOUT_MAX]
    insert(table, [LINEAGE], [(v,) for v in values])
    array = arcpy.da.TableToNumPyArray(table, [LINEAGE])
    record("dtype", repr(array.dtype))
    record("values equal", array[LINEAGE].tolist() == values)

    insert(table, [LINEAGE], [(None,)])
    for label, kwargs in (
        ("with a null, default", {}),
        ("with a null, skip_nulls=True", {"skip_nulls": True}),
        ("with a null, null_value=0", {"null_value": 0}),
    ):
        try:
            array = arcpy.da.TableToNumPyArray(table, [LINEAGE], **kwargs)
            record(label, f"dtype {array.dtype!r}, {len(array)} rows")
        except Exception as exc:
            record(label, f"raised {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Cases 10 and 11: environment
# ---------------------------------------------------------------------------


def case_fgdb_version(ws: Workspace) -> None:
    """Does a target fgdb's version gate the BigInteger field type?"""
    for version in ("CURRENT", "10.0"):
        try:
            gdb = ws.gdb(f"version_{version.replace('.', '_')}", version)
            record(f"{version} workspace release", getattr(arcpy.Describe(gdb), "release", "n/a"))
            fc = create_fc(gdb, "pts", "POINT")
            insert(fc, ["SHAPE@XY", LINEAGE], point_rows([TYPICAL_GENERATED[-1]]))
            record(f"{version} BIGINTEGER", f"ok, {field_named(fc, LINEAGE)}, {read(fc, [LINEAGE])}")
        except Exception as exc:
            record(f"{version} raised", f"{type(exc).__name__}: {exc}")


def case_build_and_archive_path(ws: Workspace, archive_gdb: str | None, image_ref: str) -> None:
    """Exact ArcPy build, image reference, and the archive creation path."""
    for key, value in sorted(arcpy.GetInstallInfo().items()):
        record(f"install {key}", value)
    record("platform", platform.platform())
    record("python", sys.version.replace("\n", " "))
    record("image reference", image_ref or "NOT GIVEN: pass --image-ref")

    if not archive_gdb:
        record(
            "archive creation path",
            "NOT TESTED: pass --archive-gdb with a geodatabase created by the pipeline's "
            "archive-writing path. Every other case used CreateFileGDB CURRENT.",
        )
        return
    record("archive gdb", archive_gdb)
    record("archive release", getattr(arcpy.Describe(archive_gdb), "release", "n/a"))
    name = f"t0_1_probe_{int(time.time())}"
    try:
        fc = create_fc(archive_gdb, name, "POINT")
        insert(fc, ["SHAPE@XY", LINEAGE], point_rows(TYPICAL_GENERATED + [LAYOUT_MAX]))
        compare_ids(fc, TYPICAL_GENERATED + [LAYOUT_MAX])
        arcpy.management.Delete(fc)
    except Exception as exc:
        record("raised", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Concatenation group-size case
# ---------------------------------------------------------------------------


LINEAGE_TEXT = "lineage_text"
"""A TEXT copy of lineage_id, for when a statistic refuses the BigInteger field."""

WORK_KEY = "work_key"
"""A LONG ordinal per input row: the scoped integer work key A14's tier 2 stamps."""


def _segments(gdb: str, ids: Sequence[int]) -> str:
    """Collinear, end-to-end segments in one group: the id as BigInteger and TEXT, plus a work key."""
    fc = create_fc(
        gdb, "segments", "POLYLINE",
        fields=(
            (LINEAGE, "BIGINTEGER"), (LINEAGE_TEXT, "TEXT"), (WORK_KEY, "LONG"), ("grp", "LONG"),
        ),
    )
    x0, y0 = 300_000.0, 6_600_000.0
    insert(
        fc,
        ["SHAPE@", LINEAGE, LINEAGE_TEXT, WORK_KEY, "grp"],
        (
            (polyline([(x0 + i, y0), (x0 + i + 1, y0)]), lid, str(lid), i + 1, 1)
            for i, lid in enumerate(ids)
        ),
    )
    return fc


def _statistics_accepted(ws: Workspace, separator: str) -> str:
    """Which statistics PairwiseDissolve accepts, on a small group.

    Returns the field the group-size runs concatenate, in preference order: the LONG work
    key (T0.1 asks for an integer key), then lineage_id, then the TEXT copy.
    """
    print("  -- statistics accepted per field type (group of 10)")
    gdb = ws.gdb("concat_probe")
    fc = _segments(gdb, [generated_id(1, i + 1) for i in range(10)])
    record("TEXT copy field", field_named(fc, LINEAGE_TEXT))
    record("work key field", field_named(fc, WORK_KEY))
    accepted: dict[str, bool] = {}
    for label, statistics in (
        ("CONCATENATE on the LONG work key", [[WORK_KEY, "CONCATENATE"]]),
        ("CONCATENATE on lineage_id", [[LINEAGE, "CONCATENATE"]]),
        ("COUNT on lineage_id", [[LINEAGE, "COUNT"]]),
        ("CONCATENATE on the TEXT copy", [[LINEAGE_TEXT, "CONCATENATE"]]),
    ):
        out = os.path.join(gdb, f"probe_{len(accepted)}")
        try:
            arcpy.analysis.PairwiseDissolve(fc, out, "grp", statistics, "SINGLE_PART", separator)
            accepted[label] = True
            record(label, f"accepted, output fields {fields_of(out)}")
        except Exception as exc:
            accepted[label] = False
            record(label, f"raised {type(exc).__name__}: {exc}")
    if accepted["CONCATENATE on the LONG work key"]:
        field = WORK_KEY
    elif accepted["CONCATENATE on lineage_id"]:
        field = LINEAGE
    else:
        field = LINEAGE_TEXT
    record("group-size runs concatenate", field)
    return field


def case_concatenate_group_size(ws: Workspace, sizes: Sequence[int]) -> None:
    """PairwiseDissolve CONCATENATE over one large group: truncate, error, or grow?

    Collinear, end-to-end segments, so SINGLE_PART dissolves each size to one feature,
    which is A14's lineage-table constraint and the configuration tier 2 would run.
    A COUNT statistic rides alongside, so the output itself shows the group size.
    """
    separator = ";"
    field = _statistics_accepted(ws, separator)
    for size in sizes:
        print(f"  -- group of {size:,}, concatenating {field}")
        gdb = ws.gdb(f"concat_{size}")
        ids = [generated_id(1, i + 1) for i in range(size)]
        expected = set(range(1, size + 1)) if field == WORK_KEY else set(ids)
        started = time.perf_counter()
        fc = _segments(gdb, ids)
        record("input write s", round(time.perf_counter() - started, 1))

        out = os.path.join(gdb, "dissolved")
        started = time.perf_counter()
        try:
            arcpy.analysis.PairwiseDissolve(
                fc, out, "grp", [[field, "CONCATENATE"], [LINEAGE_TEXT, "COUNT"]],
                "SINGLE_PART", separator,
            )
        except Exception as exc:
            record("dissolve elapsed s", round(time.perf_counter() - started, 1))
            record("dissolve raised", f"{type(exc).__name__}: {exc}")
            print(traceback.format_exc())
            continue
        record("dissolve elapsed s", round(time.perf_counter() - started, 1))
        record("output row count", int(arcpy.management.GetCount(out)[0]))
        record("output fields", fields_of(out))

        concat = next((f.name for f in arcpy.ListFields(out) if f.name.upper().startswith("CONCATENATE")), None)
        count = next((f.name for f in arcpy.ListFields(out) if f.name.upper().startswith("COUNT")), None)
        if concat is None:
            record("CONCATENATE field", "ABSENT from output")
            continue
        for value, counted in read(out, [concat, count] if count else [concat, concat]):
            text = value or ""
            tokens = [t for t in text.split(separator) if t != ""]
            record("concatenated string length", len(text))
            record("COUNT statistic", counted if count else "no COUNT field")
            record("tokens parsed", len(tokens))
            record("tokens equal group size", len(tokens) == size)
            try:
                parsed = {int(t) for t in tokens}
                record("parsed set equals input set", parsed == expected)
                record("input values missing from parse", len(expected - parsed))
            except ValueError as exc:
                record("token did not parse as int", str(exc))
                record("last 40 characters", text[-40:])
            record(
                "verdict to record",
                "GROWS (complete)" if len(tokens) == size else "TRUNCATED SILENTLY",
            )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="T0.1 gate: 64-bit storage capability.")
    parser.add_argument("--workdir", required=True, help="local directory for scratch geodatabases")
    parser.add_argument("--archive-gdb", help="a geodatabase created by the pipeline's archive path")
    parser.add_argument("--image-ref", default=os.environ.get("IMAGE_REF", ""))
    parser.add_argument("--only", action="append", help="run only this case; repeatable")
    parser.add_argument("--skip-large", action="store_true", help="skip the 10^6 concatenation group")
    args = parser.parse_args()

    arcpy.env.overwriteOutput = True
    ws = Workspace(args.workdir)
    concat_sizes = [10**5] if args.skip_large else [10**5, 10**6]

    cases: dict[str, Callable[[], None]] = {
        "case_under_2_53": lambda: case_under_2_53(ws),
        "case_2_53_plus_1": lambda: case_2_53_plus_1(ws),
        "case_round_trip_int_type": lambda: case_round_trip_int_type(ws),
        "case_typical_generated_ids": lambda: case_typical_generated_ids(ws),
        "case_predicate_filter": lambda: case_predicate_filter(ws),
        "case_type_survival": lambda: case_type_survival(ws),
        "case_overlay_duplicate": lambda: case_overlay_duplicate(ws),
        "case_joinfield_bigint_key": lambda: case_joinfield_bigint_key(ws),
        "case_table_to_numpy_dtype": lambda: case_table_to_numpy_dtype(ws),
        "case_fgdb_version": lambda: case_fgdb_version(ws),
        "case_build_and_archive_path": lambda: case_build_and_archive_path(
            ws, args.archive_gdb, args.image_ref
        ),
        "case_concatenate_group_size": lambda: case_concatenate_group_size(ws, concat_sizes),
    }
    selected = args.only or list(cases)
    unknown = [name for name in selected if name not in cases]
    if unknown:
        parser.error(f"unknown case(s): {unknown}; choose from {list(cases)}")

    raised: list[str] = []
    for name in selected:
        header(name)
        doc = (globals()[name].__doc__ or "").strip().splitlines()[0]
        print(f"  {doc}")
        try:
            cases[name]()
        except Exception:
            raised.append(name)
            print(traceback.format_exc())

    header("summary")
    record("cases run", len(selected))
    record("cases that raised outside their own handling", raised or "none")
    print("  Every block above is an observation for the written finding, not a pass/fail.")
    return 1 if raised else 0


if __name__ == "__main__":
    sys.exit(main())
