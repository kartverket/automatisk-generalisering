"""By-hand probe for W28: true curves and degenerate rings per raw source, counts only.

Run detached inside the ArcPy image from the repository root, with `src` and the root on
the path and the `ag_timing` volume mounted, against the plain `cp -a` copies and never
the timing run's derived copies, whose tool steps may keep or drop a curve:

    docker run -d --name ag_w28 -v "$PWD":/work:ro -w /work -v ag_timing:/timing:ro \\
      -e PYTHONPATH=/work/src:/work -e PYTHONDONTWRITEBYTECODE=1 \\
      ghcr.io/kartverket/arcpy-linux:12.1 \\
      python docs/refactor/temp/w28_curve_count_probe.py \\
        /timing/copies/building.gdb /timing/copies/area.gdb /timing/copies/fkb_water.gdb
    docker logs -f ag_w28          # one JSON line per batch and per dataset
    docker stop -t 60 ag_w28       # SIGTERM: an `interrupted` line with the counts so far

A geodatabase argument is walked for every feature class it holds; a feature class path
is counted on its own. Only paths under `/timing/copies` are accepted.

Why: the port carries planar simple features with straight segments and no true curve
(B33). `SHAPE@WKB` exports an arc as its end vertices, so the WKB walk cannot see a
curve; the geometry object's `hasCurves` can, at a per-row cost this run also prices.
Whether ingest (T3.4) has to densify every raw input, or only check a new source,
rests on whether any source holds a curve today; and whether the degenerate-ring
refusal, a polygon ring under four coordinates or a line under two, would fail a read of
a source today rests on whether any source holds such a ring, which the timing walk's
per-row counts could not tell.

What it prints, per dataset: the shape type, rows read, rows whose geometry `hasCurves`,
rings under four coordinates and lines under two, counted over every ring, exterior,
hole and member alike, and the elapsed time. Nothing a line carries comes from the data.
"""

from __future__ import annotations

import json
import signal
import struct
import sys
import time
from collections.abc import Iterator
from types import FrameType

from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_schema import DATA_TYPES
from ag.core.types import DataType

COPIES = "/timing/copies/"
BATCH = 100_000
MIN_RING = 4
MIN_LINE = 2
_POINT, _LINESTRING, _POLYGON, _MULTIPOINT, _MULTILINESTRING, _MULTIPOLYGON = range(
    1, 7
)


class Interrupted(Exception):
    """SIGTERM, turned into an exception so the counts so far are written."""


def line(**fields: object) -> None:
    print(json.dumps(fields), flush=True)


def feature_classes(session: ArcpySession, path: str) -> Iterator[str]:
    """The feature classes under a geodatabase path, or the path itself."""
    with session.guard("Describe"):
        import arcpy

        if DATA_TYPES.get(arcpy.Describe(path).dataType) is DataType.FEATURE_CLASS:
            yield path
            return
        for directory, _, names in arcpy.da.Walk(path, datatype="FeatureClass"):
            for name in names:
                yield f"{directory}/{name}"


def short_parts(data: object) -> tuple[int, int]:
    """(rings under MIN_RING coordinates, lines under MIN_LINE), over every ring and
    member of one WKB value; (0, 0) for a null, a point kind or an unreadable value."""
    if not isinstance(data, bytes | bytearray | memoryview):
        return 0, 0
    data = bytes(data)
    offset = 0

    def uint(order: str) -> int:
        nonlocal offset
        (value,) = struct.unpack_from(f"{order}I", data, offset)
        offset += 4
        return value

    def header() -> tuple[str, int]:
        nonlocal offset
        order = "<" if data[offset] == 1 else ">"
        offset += 1
        return order, uint(order)

    def ring_points(order: str) -> int:
        nonlocal offset
        count = uint(order)
        offset += 16 * count
        return count

    short_rings = short_lines = 0

    def one(order: str, code: int) -> None:
        nonlocal offset, short_rings, short_lines
        if code == _POINT:
            offset += 16
        elif code == _LINESTRING:
            if ring_points(order) < MIN_LINE:
                short_lines += 1
        elif code == _POLYGON:
            for _ in range(uint(order)):
                if ring_points(order) < MIN_RING:
                    short_rings += 1
        elif code in (_MULTIPOINT, _MULTILINESTRING, _MULTIPOLYGON):
            for _ in range(uint(order)):
                member_order, member_code = header()
                one(member_order, member_code)

    try:
        order, code = header()
        one(order, code)
    except (struct.error, IndexError):
        return 0, 0
    return short_rings, short_lines


def count(session: ArcpySession, path: str) -> None:
    name = path.rsplit("/", 1)[-1]
    with session.guard("Describe"):
        import arcpy

        shape_type = arcpy.Describe(path).shapeType
    counts = {"rows": 0, "curved_rows": 0, "short_rings": 0, "short_lines": 0}
    start = time.perf_counter()
    status = "complete"
    try:
        with session.guard("SearchCursor"):
            import arcpy

            with arcpy.da.SearchCursor(path, ("SHAPE@", "SHAPE@WKB")) as cursor:
                for shape, wkb in cursor:
                    counts["rows"] += 1
                    if shape is not None and shape.hasCurves:
                        counts["curved_rows"] += 1
                    rings, lines = short_parts(wkb)
                    counts["short_rings"] += rings
                    counts["short_lines"] += lines
                    if counts["rows"] % BATCH == 0:
                        elapsed = time.perf_counter() - start
                        line(
                            kind="batch",
                            dataset=name,
                            elapsed_s=round(elapsed, 1),
                            rows_per_s=round(counts["rows"] / elapsed),
                            **counts,
                        )
    except Interrupted:
        status = "interrupted"
    except Exception as error:  # noqa: BLE001  a probe reports, it does not handle
        status = f"failed: {type(error).__name__}"
    line(
        kind="dataset",
        dataset=name,
        shape_type=shape_type,
        status=status,
        elapsed_s=round(time.perf_counter() - start, 1),
        **counts,
    )
    if status == "interrupted":
        raise Interrupted


def main(paths: list[str]) -> int:
    for path in paths:
        if not path.startswith(COPIES):
            line(kind="refused", path=path, reason=f"not under {COPIES}")
            return 2

    def interrupt(signum: int, frame: FrameType | None) -> None:
        raise Interrupted

    signal.signal(signal.SIGTERM, interrupt)
    session = open_session()
    try:
        for path in paths:
            for dataset in feature_classes(session, path):
                count(session, dataset)
    except Interrupted:
        line(kind="end", status="interrupted")
        return 1
    line(kind="end", status="complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
