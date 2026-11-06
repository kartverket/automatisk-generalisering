"""By-hand probe for W12: what `SHAPE@WKB` yields for a shape that holds a true curve.

Run inside the ArcPy image from the repository root, with `src` and the root on the path:

    python docs/refactor/temp/w12_curve_probe.py

Writes one point to a file geodatabase, buffers it with the engine's Buffer tool, which
stores true curves in a file geodatabase, and confirms the curve through the geometry
object's `hasCurves` before reading the same row as `SHAPE@WKB`. The outcome is one of
three: the WKB carries a curve code (the codec refuses it); the WKB is a planar polygon
with more vertices than the curve had (the engine densifies on export); or `hasCurves`
is False, in which case the probe is inconclusive and says so. The same is repeated on a
copy in the memory workspace. Nothing here asserts and nothing comes from project data;
the output is pasted into the evidence.
"""

from __future__ import annotations

import tempfile

from ag.adapters.arcpy.session import open_session
from ag.adapters.arcpy.support.geometry_values import WKB_TOKEN
from ag.ports import Field, FieldType, Schema
from ag.ports.geometry import Geometry
from tests.support import wkb
from tests.support.arcpy import gdb
from tests.support.cases import CRS
from tools.engine.time_read_rows import shape_stats


def report(session: object, path: str, label: str) -> None:
    import arcpy

    with arcpy.da.SearchCursor(path, ("SHAPE@", WKB_TOKEN)) as cursor:
        for shape, data in cursor:
            stats = shape_stats(data)
            print(
                f"{label:12} hasCurves={shape.hasCurves} pointCount={shape.pointCount} "
                f"wkb={stats.kind} rings={stats.rings} vertices={stats.vertices} "
                f"bytes={len(data) if data is not None else None}"
            )
            if not shape.hasCurves:
                print(f"{label:12} INCONCLUSIVE: the buffer holds no true curve")


def main() -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w12_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    schema = Schema(fields=(Field("name", FieldType.TEXT, 30),), geometry_crs=CRS)
    point = Geometry.point(100.0, 100.0, crs=CRS)
    gdb.seed(
        session,
        workspace=workspace,
        name="centre",
        schema=schema,
        cells=[("centre", wkb.to_wkb(point))],
        geometry_type="POINT",
    )
    buffered = f"{workspace}/buffered"
    session.run_tool(
        "analysis.Buffer",
        in_features=f"{workspace}/centre",
        out_feature_class=buffered,
        buffer_distance_or_field="10 Meters",
    )
    report(session, buffered, "file gdb")
    session.run_tool(
        "management.CopyFeatures",
        in_features=buffered,
        out_feature_class="memory/buffered",
    )
    report(session, "memory/buffered", "memory")


if __name__ == "__main__":
    main()
