"""Fixtures, cache, baselines and goldens for the N:1 parents gate. STAGING.

What:
    Builds the synthetic inputs the N:1 cases dissolve — collinear segments and three
    lattice variants — once per (shape, size, generator version) under
    `<workdir>\\fixtures`, with a `.done` marker written last so a killed build is
    rebuilt rather than trusted. Beside each fixture it keeps the plain-dissolve
    baseline, and beside the cache root the segment build method the probe found
    faster. Also writes the JSON goldens the no-ArcPy replay test reads.

How:
    A fixture directory is `<name>_<size>_v<GENERATOR_VERSION>` holding `fixture.gdb`
    with one feature class `inputs` (fields `work_key`, `grp`), `plain_dissolve.json`
    and `.done`. Tools never write into it: dissolve outputs and locator scratch go to
    the gate's scratch geodatabases or `memory`. Bumping `GENERATOR_VERSION` retires
    every cached fixture at once.

    For the lattices, `size` is the target number of *cell edges*, which is what the
    dissolve output part count will be, so the three variants are comparable: (a)
    segmented has one input per edge; (b) long vertexed has 2(k+1) lines with a vertex
    at every crossing, k even so a line's half-length point is a crossing node; (c)
    long plain has the same lines without crossing vertices.

Why:
    Test speed is a requirement. A 10^6-row write is two minutes; paying it once per
    fixture instead of once per case is what makes a size ladder affordable.

Depends on `arcpy`; runs on Windows Pro or in the image, never in CI.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import time
import uuid
from collections.abc import Callable, Iterable, Iterator

import arcpy

GENERATOR_VERSION = 1
SPATIAL_REFERENCE = 25833
WORK_KEY = "work_key"
GROUP = "grp"
INPUTS = "inputs"
DONE_MARKER = ".done"
BASELINE_FILE = "plain_dissolve.json"
BUILD_METHOD_FILE = "build_method.json"
DISSOLVED = "dissolved"
LINEAGE_TABLE = "lineage_tbl"
ORIGIN = (300_000.0, 6_600_000.0)
SPACING_M = 10.0

SegmentRow = tuple[float, float, float, float, int, int]
"""x1, y1, x2, y2, work key, group."""

Builder = Callable[[str, str, int, str], None]
"""(gdb, feature class name, size, segment build method) -> None."""


def spatial_reference() -> arcpy.SpatialReference:
    return arcpy.SpatialReference(SPATIAL_REFERENCE)


def create_keyed_fc(gdb: str, name: str, geometry: str) -> str:
    arcpy.management.CreateFeatureclass(
        gdb, name, geometry, spatial_reference=spatial_reference()
    )
    path = os.path.join(gdb, name)
    arcpy.management.AddField(path, WORK_KEY, "LONG")
    arcpy.management.AddField(path, GROUP, "LONG")
    return path


# ---------------------------------------------------------------------------
# Segment writers: the InsertCursor build and the XYToLine build
# ---------------------------------------------------------------------------


def write_segments(gdb: str, name: str, rows: Iterable[SegmentRow], method: str) -> str:
    if method == "xy_to_line":
        return write_segments_xy_to_line(gdb, name, rows)
    return write_segments_cursor(gdb, name, rows)


def write_segments_cursor(gdb: str, name: str, rows: Iterable[SegmentRow]) -> str:
    fc = create_keyed_fc(gdb, name, "POLYLINE")
    reference = spatial_reference()
    with arcpy.da.InsertCursor(fc, ["SHAPE@", WORK_KEY, GROUP]) as cursor:
        for x1, y1, x2, y2, work_key, group in rows:
            line = arcpy.Polyline(
                arcpy.Array([arcpy.Point(x1, y1), arcpy.Point(x2, y2)]), reference
            )
            cursor.insertRow([line, work_key, group])
    return fc


def write_segments_xy_to_line(gdb: str, name: str, rows: Iterable[SegmentRow]) -> str:
    """NumPyArrayToTable then XYToLine(PLANAR, ATTRIBUTES): one tool call, no cursor."""
    import numpy

    array = numpy.array(
        list(rows),
        dtype=[
            ("x1", "f8"),
            ("y1", "f8"),
            ("x2", "f8"),
            ("y2", "f8"),
            (WORK_KEY, "i4"),
            (GROUP, "i4"),
        ],
    )
    table = f"memory\\ag_xy_{uuid.uuid4().hex[:8]}"
    fc = os.path.join(gdb, name)
    arcpy.da.NumPyArrayToTable(array, table)
    try:
        arcpy.management.XYToLine(
            in_table=table,
            out_featureclass=fc,
            startx_field="x1",
            starty_field="y1",
            endx_field="x2",
            endy_field="y2",
            line_type="PLANAR",
            spatial_reference=spatial_reference(),
            attributes="ATTRIBUTES",
        )
    finally:
        if arcpy.Exists(table):
            arcpy.management.Delete(table)
    return fc


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def collinear_rows(size: int, gap_fraction: float | None) -> Iterator[SegmentRow]:
    """1 m segments end to end on one line; with a gap fraction, a 100 m gap at that point."""
    x0, y0 = ORIGIN
    gap_after = None if gap_fraction is None else int(size * gap_fraction)
    for i in range(size):
        x = x0 + i + (100.0 if gap_after is not None and i >= gap_after else 0.0)
        yield (x, y0, x + 1.0, y0, i + 1, 1)


def lattice_k(size: int) -> int:
    """Even k with about `size` cell edges: a k x k grid has 2k(k+1) edges."""
    k = max(2, round(math.sqrt(size / 2)))
    return k if k % 2 == 0 else k + 1


def lattice_counts(size: int) -> dict[str, int]:
    k = lattice_k(size)
    return {"k": k, "cell edges": 2 * k * (k + 1), "long lines": 2 * (k + 1)}


def lattice_segmented_rows(k: int) -> Iterator[SegmentRow]:
    """Every cell edge is one input; crossings are shared vertices."""
    x0, y0 = ORIGIN
    s = SPACING_M
    key = 0
    for r in range(k + 1):
        for c in range(k):
            key += 1
            yield (x0 + c * s, y0 + r * s, x0 + (c + 1) * s, y0 + r * s, key, 1)
    for c in range(k + 1):
        for r in range(k):
            key += 1
            yield (x0 + c * s, y0 + r * s, x0 + c * s, y0 + (r + 1) * s, key, 1)


def write_lattice_long_lines(
    gdb: str, name: str, k: int, vertex_at_crossings: bool
) -> str:
    """2(k+1) full-span lines, with or without a vertex at every crossing."""
    fc = create_keyed_fc(gdb, name, "POLYLINE")
    reference = spatial_reference()
    x0, y0 = ORIGIN
    s = SPACING_M

    def line(coords: list[tuple[float, float]]) -> arcpy.Polyline:
        return arcpy.Polyline(arcpy.Array([arcpy.Point(*c) for c in coords]), reference)

    key = 0
    with arcpy.da.InsertCursor(fc, ["SHAPE@", WORK_KEY, GROUP]) as cursor:
        for r in range(k + 1):
            key += 1
            if vertex_at_crossings:
                coords = [(x0 + c * s, y0 + r * s) for c in range(k + 1)]
            else:
                coords = [(x0, y0 + r * s), (x0 + k * s, y0 + r * s)]
            cursor.insertRow([line(coords), key, 1])
        for c in range(k + 1):
            key += 1
            if vertex_at_crossings:
                coords = [(x0 + c * s, y0 + r * s) for r in range(k + 1)]
            else:
                coords = [(x0 + c * s, y0), (x0 + c * s, y0 + k * s)]
            cursor.insertRow([line(coords), key, 1])
    return fc


# ---------------------------------------------------------------------------
# Builders, by fixture name
# ---------------------------------------------------------------------------


def build_collinear_one_part(gdb: str, name: str, size: int, method: str) -> None:
    write_segments(gdb, name, collinear_rows(size, None), method)


def build_collinear_two_parts(gdb: str, name: str, size: int, method: str) -> None:
    write_segments(gdb, name, collinear_rows(size, 0.5), method)


def build_lattice_segmented(gdb: str, name: str, size: int, method: str) -> None:
    write_segments(gdb, name, lattice_segmented_rows(lattice_k(size)), method)


def build_lattice_long_vertexed(gdb: str, name: str, size: int, method: str) -> None:
    write_lattice_long_lines(gdb, name, lattice_k(size), vertex_at_crossings=True)


def build_lattice_long_plain(gdb: str, name: str, size: int, method: str) -> None:
    write_lattice_long_lines(gdb, name, lattice_k(size), vertex_at_crossings=False)


FIXTURE_BUILDERS: dict[str, Builder] = {
    "collinear_one_part": build_collinear_one_part,
    "collinear_two_parts": build_collinear_two_parts,
    "lattice_segmented": build_lattice_segmented,
    "lattice_long_vertexed": build_lattice_long_vertexed,
    "lattice_long_plain": build_lattice_long_plain,
}

FIXTURE_NOTES: dict[str, str] = {
    "collinear_one_part": "size inputs, one key, one part: the attribute-join path",
    "collinear_two_parts": "size inputs, one key, 100 m gap at the middle: two parts",
    "lattice_segmented": "about size cell edges, one input each, shared vertices",
    "lattice_long_vertexed": "2(k+1) long lines, vertex at every crossing, k even",
    "lattice_long_plain": "2(k+1) long lines crossing without shared vertices",
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class FixtureCache:
    def __init__(self, workdir: str) -> None:
        self.root = os.path.join(workdir, "fixtures")
        os.makedirs(self.root, exist_ok=True)

    def directory(self, name: str, size: int) -> str:
        return os.path.join(self.root, f"{name}_{size}_v{GENERATOR_VERSION}")

    def inputs(self, name: str, size: int) -> tuple[str, float | None]:
        """The cached input feature class, built now if the marker is absent.

        What: returns the path and the build seconds, or None when it was cached.
        How: a directory without `.done` is deleted and rebuilt; the marker is the last
        thing written, so a build killed midway never counts as done.
        Why: the builds are the expensive part of every large case.
        """
        directory = self.directory(name, size)
        gdb = os.path.join(directory, "fixture.gdb")
        fc = os.path.join(gdb, INPUTS)
        marker = os.path.join(directory, DONE_MARKER)
        if os.path.exists(marker):
            return fc, None
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
        arcpy.management.CreateFileGDB(directory, "fixture.gdb")
        method = self.build_method()
        started = time.perf_counter()
        FIXTURE_BUILDERS[name](gdb, INPUTS, size, method)
        elapsed = time.perf_counter() - started
        with open(marker, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "seconds": round(elapsed, 1),
                    "method": method,
                    "generator_version": GENERATOR_VERSION,
                },
                handle,
            )
        return fc, elapsed

    def baseline(self, name: str, size: int) -> dict[str, object] | None:
        """The cached plain-dissolve baseline: `plain_dissolve_s`, or `timed_out_after_s`."""
        path = os.path.join(self.directory(name, size), BASELINE_FILE)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as handle:
            return dict(json.load(handle))

    def save_baseline(
        self,
        name: str,
        size: int,
        seconds: float | None,
        timed_out_after_s: float | None = None,
    ) -> None:
        path = os.path.join(self.directory(name, size), BASELINE_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload: dict[str, object] = {
            "plain_dissolve_s": round(seconds, 2) if seconds is not None else None
        }
        if timed_out_after_s is not None:
            payload["timed_out_after_s"] = round(timed_out_after_s)
            payload["note"] = "tool alone over budget on this shape"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def dissolved(
        self, name: str, size: int, with_table: bool
    ) -> tuple[str, str | None, str, dict[str, object] | None]:
        """Cached dissolve output for (fixture, PairwiseDissolve, SINGLE_PART on `grp`, table or not).

        What: returns (output fc, lineage table or None, cache directory, marker payload or
        None when not yet dissolved).
        How: one directory per parameter set under the fixture, `.done` written last by
        `mark_dissolved`; a directory without the marker is rebuilt by `prepare_dissolve`.
        Why: one dissolve per fixture and parameter set, ever; a second run of any ladder
        performs no dissolve.
        """
        suffix = "_table" if with_table else ""
        directory = os.path.join(
            self.directory(name, size), f"dissolve_single_part{suffix}"
        )
        gdb = os.path.join(directory, "out.gdb")
        out = os.path.join(gdb, DISSOLVED)
        table = os.path.join(gdb, LINEAGE_TABLE) if with_table else None
        marker = os.path.join(directory, DONE_MARKER)
        payload = None
        if os.path.exists(marker):
            with open(marker, encoding="utf-8") as handle:
                payload = dict(json.load(handle))
        return out, table, directory, payload

    def prepare_dissolve(self, directory: str) -> None:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)
        arcpy.management.CreateFileGDB(directory, "out.gdb")

    def mark_dissolved(self, directory: str, payload: dict[str, object]) -> None:
        payload = {**payload, "done": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with open(
            os.path.join(directory, DONE_MARKER), "w", encoding="utf-8"
        ) as handle:
            json.dump(payload, handle)

    def build_method(self) -> str:
        path = os.path.join(self.root, BUILD_METHOD_FILE)
        if not os.path.exists(path):
            return "cursor"
        with open(path, encoding="utf-8") as handle:
            return str(json.load(handle)["method"])

    def save_build_method(self, method: str, timings: dict[str, float]) -> None:
        path = os.path.join(self.root, BUILD_METHOD_FILE)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"method": method, "timings_s": timings}, handle)


# ---------------------------------------------------------------------------
# Goldens
# ---------------------------------------------------------------------------


def write_golden(
    directory: str,
    *,
    fixture: str,
    pro_version: str,
    input_keys: list[tuple[int, tuple[object, ...]]],
    output_keys: list[tuple[int, tuple[object, ...]]],
    native_pairs: list[tuple[int, int]],
    locators: dict[str, dict[str, list[tuple[int, int]]]],
) -> str:
    """One JSON file per fixture: both key lists, the native pairs, and per locator its
    raw hits and the resolver's pairs. `test_goldens.py` replays the hits without ArcPy.
    """
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{fixture}.json")
    payload = {
        "fixture": fixture,
        "generator_version": GENERATOR_VERSION,
        "pro_version": pro_version,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "input_keys": [[index, list(key)] for index, key in input_keys],
        "output_keys": [[index, list(key)] for index, key in output_keys],
        "native_pairs": [list(pair) for pair in native_pairs],
        "locators": {
            name: {
                kind: [list(pair) for pair in pairs] for kind, pairs in parts.items()
            }
            for name, parts in locators.items()
        },
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    return path
