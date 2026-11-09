"""By-hand probe for W29: what Buffer writes and what Densify leaves, flags and counts.

Run inside the ArcPy image from the repository root, with `src` and the root on the path:

    python docs/refactor/temp/w29_buffer_densify_probe.py

Why: the port carries no true curve (B33), and the guard is densifying where curves
arise, the adapter's curve-producing methods, buffer first. The architect observed in
ArcGIS Pro that a buffered point is one true curve, a buffered line straight segments,
and a buffered polygon curves at its corners; and the engine documents Densify's offset
method as replacing curves with segments within a maximum deviation. Neither is shown
on the image yet, and `hasCurves` after Densify is the fact the acceptance test of every
such method will assert.

What it does, on synthetic shapes: buffers a point, a line and a polygon by ten metres
in a file geodatabase and in the memory workspace, prints per output `hasCurves` and the
vertex count of every row, runs `edit.Densify` with the offset method at one centimetre
on the output, and prints both again. A refusal prints the exception class and message,
since nothing here is data.
"""

from __future__ import annotations

import tempfile

from ag.adapters.arcpy.session import ArcpySession, open_session
from tests.support import gdb_cases
from tests.support.arcpy import gdb
from tests.support.cases import points, polygons, roads

DISTANCE = "10 Meters"
DEVIATION = "0.01 Meters"


def shapes(session: ArcpySession, path: str) -> list[tuple[bool, int]]:
    """(hasCurves, pointCount) per row."""
    found: list[tuple[bool, int]] = []
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(path, ("SHAPE@",)) as cursor:
            for (shape,) in cursor:
                found.append((bool(shape.hasCurves), int(shape.pointCount)))
    return found


def report(label: str, rows: list[tuple[bool, int]]) -> None:
    curved = sum(1 for has_curves, _ in rows if has_curves)
    print(f"  {label}: rows={len(rows)} with_curves={curved} vertices={[n for _, n in rows]}")


def probe(session: ArcpySession, source_workspace: str, out_workspace: str) -> None:
    print(f"== buffers written to {out_workspace.rsplit('/', 1)[-1]} ==")
    for case in (points(), roads(), polygons()):
        seeded = gdb_cases.seed_case(
            session, workspace=source_workspace, case=case, name=f"{case.name}_src"
        )
        output = f"{out_workspace}/{case.name}_buffer"
        try:
            session.run_tool(
                "analysis.Buffer",
                in_features=str(seeded.handle.path),
                out_feature_class=output,
                buffer_distance_or_field=DISTANCE,
            )
        except Exception as error:  # noqa: BLE001  a probe reports, it does not handle
            print(f"  {case.name}: Buffer refused: {type(error).__name__}: {error}")
            continue
        report(f"{case.name} after Buffer", shapes(session, output))
        try:
            session.run_tool(
                "edit.Densify",
                in_features=output,
                densification_method="OFFSET",
                max_deviation=DEVIATION,
            )
        except Exception as error:  # noqa: BLE001
            print(f"  {case.name}: Densify refused: {type(error).__name__}: {error}")
            continue
        report(f"{case.name} after Densify", shapes(session, output))


def main() -> None:
    session = open_session()
    directory = tempfile.mkdtemp(prefix="w29_")
    workspace = gdb.file_gdb(session, directory=directory, name="probe")
    probe(session, workspace, workspace)
    probe(session, workspace, "memory")


if __name__ == "__main__":
    main()
