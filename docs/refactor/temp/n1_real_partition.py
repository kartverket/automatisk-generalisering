"""Export the largest partition selection of a road feature class, via PartitionIterator. STAGING.

What:
    Partitions a road feature class the way the ramps stage does — the iterator's own
    `CreateCartographicPartitions` with optimisation off and the stage's element limit — and
    exports only the largest selection, processing rows plus halo rows exactly as the
    iterator selects them, to a scratch geodatabase. No full pipeline run.

How:
    One `PartitionIterator.run()` with a single processing input, no outputs, and one
    injected callback that receives each partition's selection feature class. The callback
    counts rows by `partition_selection_field` (1 = processing, 0 = halo), keeps a running
    maximum, and `CopyFeatures` the selection to a literal scratch path when it is the largest
    so far. Only the iterator's own work-manager paths are deleted between partitions, so
    the copy survives. The iterator calls the callback in-process, so module-level state is
    sound. Every callback exception is caught and recorded (the iterator would otherwise
    retry fifty times); after `run()` the export raises if anything was recorded or no copy
    exists.

Why:
    The N:1 parents probe needs the input the pipeline's dissolve actually sees, not a manual
    selection. Reusing the iterator's selection code is what makes the numbers comparable.

Runs on Windows Pro, never in CI, and needs no `.env`: the four variables `paths.py` and
`composition_configs` read at import get dummy values here (every path is passed explicitly),
and the pipeline's arcpy settings are applied directly. Defaults are the ramps stage's:
35,000 elements per partition and a 500 m context radius
(`generalization/n100/road/data_preparation_2.py:403-407`).

    python n1_real_partition.py --workdir C:\\temp\\t0_1 --road-fc <stage input fc> --scratch-gdb C:\\temp\\t0_1\\real.gdb
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass, field

import arcpy

from n1_parents_gate import PARTITION_FIELD, install_log, record

XY_TOLERANCE_M = 0.02
XY_RESOLUTION_M = 0.01
SPATIAL_REFERENCE = 25833
"""The pipeline's arcpy environment (`env_setup/environment_setup.py`), set here directly so
the run needs no `.env`; the tolerance decides what a dissolve merges."""

IMPORT_TIME_VARIABLES = (
    "SELECT_STUDY_AREA",
    "DEFAULT_PROJECT_WORKSPACE",
    "GIS_FILES_ROOT",
    "PYTHONPATH",
)
"""Read by `paths.py` and `composition_configs/core_config.py` at import time. The helper
passes every path explicitly, so these only need to exist; the values are never used."""

RAMPS_ELEMENT_LIMIT = 35_000
RAMPS_CONTEXT_RADIUS_M = 500
OBJECT = "road"
EXPORT_NAME = "largest_partition"
INPUT_COPY = "input_copy"


@dataclass(frozen=True)
class ExportConfig:
    """The callback's only parameter; `selection` is an InjectIO the iterator resolves."""

    selection: object


@dataclass(frozen=True)
class ExportedPartition:
    path: str
    partition_id: int
    processing_rows: int
    halo_rows: int
    partition_count: int


@dataclass
class _State:
    export_path: str = ""
    best: ExportedPartition | None = None
    seen: list[int] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)


_STATE = _State()


def _partition_id_from(path: str) -> int:
    match = re.search(r"_iteration_(\d+)", path)
    return int(match.group(1)) if match else -1


def _counts(selection: str) -> tuple[int, int]:
    processing = halo = 0
    with arcpy.da.SearchCursor(selection, [PARTITION_FIELD]) as cursor:
        for (flag,) in cursor:
            if flag == 1:
                processing += 1
            else:
                halo += 1
    return processing, halo


def _keep_largest(config: ExportConfig) -> None:
    """The injected callback: count, compare, copy when largest. Never raises."""
    selection = str(config.selection)
    partition_id = _partition_id_from(selection)
    try:
        _STATE.seen.append(partition_id)
        processing, halo = _counts(selection)
        total = processing + halo
        best_total = (
            -1
            if _STATE.best is None
            else (_STATE.best.processing_rows + _STATE.best.halo_rows)
        )
        if total > best_total:
            if arcpy.Exists(_STATE.export_path):
                arcpy.management.Delete(_STATE.export_path)
            arcpy.management.CopyFeatures(selection, _STATE.export_path)
            _STATE.best = ExportedPartition(
                path=_STATE.export_path,
                partition_id=partition_id,
                processing_rows=processing,
                halo_rows=halo,
                partition_count=0,
            )
            best_total = total
        best_id = _STATE.best.partition_id if _STATE.best else -1
        print(
            f"partition {partition_id}: processing {processing}, halo {halo}, "
            f"total {total}, running max {best_total} (partition {best_id})"
        )
    except Exception as exc:  # recorded, re-raised after run() by the caller
        _STATE.errors.append((partition_id, repr(exc)))
        print(f"partition {partition_id}: callback error recorded: {exc!r}")


def default_environment(workdir: str) -> None:
    """Give the import-time variables a value when the shell did not, so no `.env` is needed."""
    dummy = os.path.join(workdir, "real_partition_env")
    os.makedirs(dummy, exist_ok=True)
    defaults = {
        "SELECT_STUDY_AREA": "False",
        "DEFAULT_PROJECT_WORKSPACE": dummy,
        "GIS_FILES_ROOT": dummy,
        "PYTHONPATH": os.getcwd(),
    }
    for name in IMPORT_TIME_VARIABLES:
        if name not in os.environ:
            os.environ[name] = defaults[name]
            record(f"environment default {name}", defaults[name])


def arcpy_environment() -> None:
    """The pipeline's arcpy settings, without `environment_setup.main()` and its `.env`."""
    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(SPATIAL_REFERENCE)
    arcpy.env.XYTolerance = f"{XY_TOLERANCE_M} Meters"
    arcpy.env.XYResolution = f"{XY_RESOLUTION_M} Meters"
    record("XY tolerance", arcpy.env.XYTolerance)
    record("XY resolution", arcpy.env.XYResolution)


def export_largest_partition(
    *,
    road_fc: str,
    scratch_gdb: str,
    workdir: str,
    element_limit: int = RAMPS_ELEMENT_LIMIT,
    context_radius_m: int = RAMPS_CONTEXT_RADIUS_M,
) -> ExportedPartition:
    """Partition `road_fc` like the ramps stage and export the largest selection.

    What: returns the exported feature class and its partition id and row counts.
    How: copies the input first, because the iterator adds and removes its selection field
    on the input in place; builds the four configs with no outputs and one callback; runs;
    raises `RuntimeError` on any recorded callback error or when no copy exists.
    Why: the probe must see what the pipeline's dissolve sees, selected by the same code.
    """
    # Imported here, after `default_environment` has run: `paths.py` and
    # `composition_configs` read environment variables at import time.
    from composition_configs import core_config, type_defs
    from custom_tools.general_tools.partition_iterator import PartitionIterator

    global _STATE
    _STATE = _State()
    if not arcpy.Exists(scratch_gdb):
        arcpy.management.CreateFileGDB(
            os.path.dirname(scratch_gdb), os.path.basename(scratch_gdb)
        )
    _STATE.export_path = os.path.join(scratch_gdb, EXPORT_NAME)

    record("input", road_fc)
    record("input rows", int(arcpy.management.GetCount(road_fc)[0]))
    started = time.perf_counter()
    input_copy = os.path.join(scratch_gdb, INPUT_COPY)
    arcpy.management.CopyFeatures(road_fc, input_copy)
    record("input copied s", round(time.perf_counter() - started, 1))
    record("element limit", element_limit)
    record("context radius m", context_radius_m)

    documentation = type_defs.SubdirectoryPath(
        os.path.join(workdir, "real_partition_docs")
    )
    io_config = core_config.PartitionIOConfig(
        input_config=core_config.PartitionInputConfig(
            entries=[
                core_config.InputEntry.processing_input(object=OBJECT, path=input_copy)
            ]
        ),
        output_config=core_config.PartitionOutputConfig(entries=[]),
        documentation_directory=documentation,
    )
    methods = core_config.MethodEntriesConfig(
        entries=[
            core_config.FuncMethodEntryConfig(
                func=_keep_largest,
                params=ExportConfig(selection=core_config.InjectIO(OBJECT, "input")),
            )
        ]
    )
    run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=element_limit,
        context_radius_meters=context_radius_m,
        run_partition_optimization=False,
    )
    work_files = core_config.WorkFileConfig(
        root_file=os.path.join(scratch_gdb, "real_partition_root"),
        write_to_memory=False,
        keep_files=False,
    )

    started = time.perf_counter()
    iterator = PartitionIterator(io_config, methods, run_config, work_files)
    iterator.run()
    record("iterator run s", round(time.perf_counter() - started, 1))
    partition_count = int(getattr(iterator, "max_partition_count", len(_STATE.seen)))
    record("partitions", partition_count)
    record("partitions with processing rows", len(_STATE.seen))

    if _STATE.errors:
        raise RuntimeError(
            f"{len(_STATE.errors)} callback error(s) recorded; first: {_STATE.errors[:3]}"
        )
    if _STATE.best is None or not arcpy.Exists(_STATE.export_path):
        raise RuntimeError("no partition had processing rows; nothing exported")
    best = ExportedPartition(
        path=_STATE.best.path,
        partition_id=_STATE.best.partition_id,
        processing_rows=_STATE.best.processing_rows,
        halo_rows=_STATE.best.halo_rows,
        partition_count=partition_count,
    )
    record("largest partition id", best.partition_id)
    record("processing rows", best.processing_rows)
    record("halo rows", best.halo_rows)
    record("total rows", best.processing_rows + best.halo_rows)
    record("exported to", best.path)
    return best


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the largest partition selection."
    )
    parser.add_argument("--workdir", required=True, help="log and documentation root")
    parser.add_argument(
        "--road-fc", required=True, help="the ramps stage's input feature class"
    )
    parser.add_argument("--scratch-gdb", help="default <workdir>\\real.gdb")
    parser.add_argument("--element-limit", type=int, default=RAMPS_ELEMENT_LIMIT)
    parser.add_argument("--context-radius-m", type=int, default=RAMPS_CONTEXT_RADIUS_M)
    args = parser.parse_args()

    log_file = install_log(args.workdir, None, ["real_partition"])
    print(f"log: {log_file}")
    default_environment(args.workdir)
    arcpy_environment()
    scratch_gdb = args.scratch_gdb or os.path.join(args.workdir, "real.gdb")
    try:
        export_largest_partition(
            road_fc=args.road_fc,
            scratch_gdb=scratch_gdb,
            workdir=args.workdir,
            element_limit=args.element_limit,
            context_radius_m=args.context_radius_m,
        )
    except Exception as exc:
        record("export failed", f"{type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
