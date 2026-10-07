"""N:1 parents gate, for B17 in findings/n1_correspondence.md. THROWAWAY.

Sibling of `t0_1_bigint_gate.py` with the same conventions: cases print observations
and never assert; a case that raises prints the full traceback and the run continues;
case functions are named by description. The shared helpers are imported from the T0.1
script rather than copied. The N:1 cases lived inside that script until the fixture
cache, the child-interpreter timing and the size ladder outgrew it.

WHERE IT RUNS. Windows Pro or the Linux image; never CI. Fixtures are cached under
`<workdir>\\fixtures` (see `n1_fixtures.py`); tools write to scratch geodatabases and
`memory` only.

    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_fixture_build_method
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_boundary_fixtures --write-goldens
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_resolver_correctness_ladder
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_resolver_timing_ladder
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_resolver_timing_ladder --confirm-large
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_real_data_group_sizes --real-fc C:\\temp\\t0_1\\real.gdb\\largest_partition
    python n1_parents_gate.py --workdir C:\\temp\\t0_1 --only case_real_data_group_sizes --real-count-only --real-fc <stage input fc>

Run order: `case_fixture_build_method` first (it picks the segment writer the cache
uses), then the small cases, then the correctness ladder, then timing.

TIMING DISCIPLINE. Large timed runs happen in a child interpreter with a timeout of
`--timeout-factor` x the one-minute budget plus interpreter start-up; "TIMED OUT after
N s" is recorded as the result. Each fixture is dissolved once per size and every
locator runs against that output. 10^6 runs only with `--confirm-large`, and only for a
locator whose time fitted from 10^4 and 10^5 predicts under the timeout.

LOGGING. Every run tees stdout to `<workdir>\\logs\\<timestamp>_<cases>.txt` regardless of
runner; child interpreters append to the same file, and the parent echoes their lines to
the console only. Dissolve outputs and native tables are cached per (fixture, parameters)
with `.done` markers, so a second run of a ladder performs no dissolve. The plain-dissolve
baseline of a timing point runs in the capped child; a timeout is recorded as "tool alone
over budget on this shape" and that point's locators are skipped. `lattice_long_vertexed`
is excluded from `--confirm-large` unless `--include-pathological` is passed; its settled
10^6 baseline is 5,088 s (2026-09-15).

Child modes, internal: `--child-locate NAME --child-input FC --child-output FC` and
`--child-dissolve --child-input FC --child-output FC [--child-table T]`, both with
`--log-file`.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import traceback
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import arcpy

import n1_fixtures as fx
from arcpy_part_locator import (
    ArcpyPartLocator,
    ArcpySegmentLocator,
    degenerate_inputs,
    find_empty_geometries,
)
from dissolve_parents import (
    DissolveKey,
    LocateRequest,
    ParentPair,
    ParentsResolution,
    PartLocator,
    UnmatchedInputError,
    dissolve_parents,
    require_matched,
)
from t0_1_bigint_gate import (
    WORK_KEY,
    Workspace,
    _parse_tokens,
    header,
    insert,
    polyline,
    read,
    record,
    square,
)

BUDGET_S = 60.0
"""The user's guidance of 2026-09-15: lineage overhead on a common GP tool under one
minute. Not recorded in DECISIONS.md or TASKS.md; the findings file asks for that."""

CORRECTNESS_SIZES = (10**2, 10**3, 10**4)
TIMING_SIZES = (10**4, 10**5)
LARGE_SIZE = 10**6
CHILD_STARTUP_S = 90.0
"""Allowance for the child interpreter importing arcpy, outside the budget."""

LINEAGE_TABLE_PARAMETER = "out_lineage_table"
KEY_FIELDS = (fx.GROUP,)
RAMPS_KEY_FIELDS = ("objtype", "medium", "motorvegtype", "vegkategori", "typeveg")
"""`dissolve_and_return_connection` in generalization/n100/road/ramps.py:256-282."""
NATIONAL_KEY_FIELDS = (
    "objtype",
    "subtypekode",
    "vegstatus",
    "typeveg",
    "vegkategori",
    "vegnummer",
    "motorvegtype",
    "vegklasse",
    "rutemerking",
    "medium",
    "uttegning",
    "er_kryssningspunkt",
)
"""`FieldNames.road_input_fields` (constants/n100_constants.py:145-158), the key of the
unpartitioned national `run_dissolve_with_intersections` (data_preparation_2.py:336-346)."""
PARTITION_FIELD = "partition_selection_field"
"""PartitionIterator.PARTITION_FIELD: 1 = processing row, 0 = halo row."""
RAMPS_SUBSET_WHERE = "objtype = 'VegSenterlinje' and typeveg <> 'rampe'"
RAMPS_BUFFER_M = 400
NO_FIELDS = "-"
"""`--child-key-fields` value meaning: dissolve the whole input as one group."""
HANDLED_ERRORS: list[str] = []
"""Every exception a case caught and recorded; the summary counts them."""


def handled(label: str, exc: BaseException) -> None:
    """Record an exception a case handles itself, and count it for the summary."""
    record(label, f"{type(exc).__name__}: {exc}")
    HANDLED_ERRORS.append(f"{label}: {type(exc).__name__}")


LOCATORS = ("midpoint", "feature_to_point", "segment")
TIMING_FIXTURES = ("collinear_one_part", "lattice_segmented", "lattice_long_vertexed")
PATHOLOGICAL_FIXTURES = ("lattice_long_vertexed",)
"""Excluded from --confirm-large unless --include-pathological: the tool itself is over budget."""
SETTLED_BASELINES: dict[tuple[str, int], float] = {
    ("lattice_long_vertexed", 10**6): 5087.93
}
"""Plain-dissolve seconds measured once and not re-run (Pro 3.7.2, 2026-09-15)."""
PartSets = set[frozenset[int]]


# ---------------------------------------------------------------------------
# Logging: tee to <workdir>\logs regardless of runner
# ---------------------------------------------------------------------------


class _Tee:
    """stdout that also appends to the run log; `console_only` bypasses the file."""

    def __init__(self, console: object, path: str) -> None:
        self.console = console
        self._file = open(path, "a", encoding="utf-8")

    def write(self, text: str) -> int:
        self.console.write(text)  # type: ignore[attr-defined]
        self._file.write(text)
        return len(text)

    def flush(self) -> None:
        self.console.flush()  # type: ignore[attr-defined]
        self._file.flush()

    def console_only(self, text: str) -> None:
        self.console.write(text)  # type: ignore[attr-defined]


def _console(text: str) -> None:
    """Print to the console only: for child output that is already in the log."""
    out = sys.stdout
    if isinstance(out, _Tee):
        out.console_only(text)
    else:
        out.write(text)


def install_log(workdir: str, log_file: str | None, selected: Sequence[str]) -> str:
    if log_file is None:
        os.makedirs(os.path.join(workdir, "logs"), exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        cases = "_".join(name.removeprefix("case_") for name in selected)[:80]
        log_file = os.path.join(workdir, "logs", f"{stamp}_{cases}.txt")
    sys.stdout = _Tee(sys.stdout, log_file)
    return log_file


# ---------------------------------------------------------------------------
# Locators and the resolver run
# ---------------------------------------------------------------------------


@dataclass
class LocatorRun:
    resolution: ParentsResolution
    hits: list[ParentPair]
    timings: dict[str, float]

    @property
    def total_s(self) -> float:
        return sum(
            v for k, v in self.timings.items() if not k.startswith("locator stage:")
        )


class _Recording:
    """Wraps a locator to keep its raw hits for the goldens."""

    def __init__(self, inner: PartLocator) -> None:
        self.inner = inner
        self.hits: list[ParentPair] = []

    def locate(self, *, requests: Sequence[LocateRequest]) -> Iterable[ParentPair]:
        self.hits = list(self.inner.locate(requests=requests))
        return self.hits


def make_locator(
    name: str, fc: str, out: str
) -> ArcpyPartLocator | ArcpySegmentLocator:
    if name == "midpoint":
        return ArcpyPartLocator(input_path=fc, output_path=out)
    if name == "feature_to_point":
        return ArcpyPartLocator(
            input_path=fc, output_path=out, point_source="feature_to_point"
        )
    if name == "segment":
        return ArcpySegmentLocator(input_path=fc, output_path=out)
    raise ValueError(f"unknown locator {name!r}; choose from {LOCATORS}")


def locators_for(fc: str) -> tuple[str, ...]:
    shape = arcpy.Describe(fc).shapeType
    if shape == "Polyline":
        return LOCATORS
    if shape == "Polygon":
        return ("midpoint", "feature_to_point")
    return ("midpoint",)


def _read_keys(path: str, fields: Sequence[str]) -> list[tuple[int, DissolveKey]]:
    with arcpy.da.SearchCursor(path, ["OID@", *fields]) as cursor:
        return [(row[0], tuple(row[1:])) for row in cursor]


def run_locator(name: str, fc: str, out: str, *, fields: Sequence[str]) -> LocatorRun:
    """Option C end to end with one locator, every stage timed, on the given key fields."""
    timings: dict[str, float] = {}
    started = time.perf_counter()
    input_keys = _read_keys(fc, fields)
    timings["read input keys s"] = time.perf_counter() - started
    started = time.perf_counter()
    output_keys = _read_keys(out, fields)
    timings["read output keys s"] = time.perf_counter() - started
    inner = make_locator(name, fc, out)
    recording = _Recording(inner)
    started = time.perf_counter()
    resolution = dissolve_parents(
        input_keys=input_keys, output_keys=output_keys, locator=recording
    )
    timings["resolve (join path + locator) s"] = time.perf_counter() - started
    for stage, seconds in inner.last_timings.items():
        timings[f"locator stage: {stage}"] = seconds
    return LocatorRun(resolution=resolution, hits=recording.hits, timings=timings)


# ---------------------------------------------------------------------------
# Native table, comparison, guards
# ---------------------------------------------------------------------------


def _lineage_table_available() -> bool:
    info = arcpy.GetInstallInfo()
    record("Pro version", info.get("Version"))
    names: list[str] = []
    try:
        names = [p.name for p in arcpy.GetParameterInfo("analysis.PairwiseDissolve")]
    except Exception as exc:
        record("GetParameterInfo raised", f"{type(exc).__name__}: {exc}")
    available = LINEAGE_TABLE_PARAMETER in names
    record(f"{LINEAGE_TABLE_PARAMETER} parameter present", available)
    return available


def pro_version() -> str:
    return str(arcpy.GetInstallInfo().get("Version"))


def dissolve_once(
    fc: str, out: str, table: str | None, fields: Sequence[str] = KEY_FIELDS
) -> float:
    """One PairwiseDissolve on the key fields, SINGLE_PART, timed; with the table if asked."""
    extra = {LINEAGE_TABLE_PARAMETER: table} if table else {}
    started = time.perf_counter()
    arcpy.analysis.PairwiseDissolve(
        fc, out, list(fields) or None, multi_part="SINGLE_PART", **extra
    )
    elapsed = time.perf_counter() - started
    record("dissolve s", round(elapsed, 2))
    record("output rows", int(arcpy.management.GetCount(out)[0]))
    if table:
        record("lineage table at the given path", arcpy.Exists(table))
    return elapsed


def _table_pairs(table: str) -> list[ParentPair]:
    return [
        ParentPair(output_index=o, input_index=i)
        for o, i in read(table, ["OUTPUT_FID", "INPUT_FID"])
    ]


def _partition(pairs: Iterable[ParentPair]) -> PartSets:
    parts: dict[int, set[int]] = {}
    for pair in pairs:
        parts.setdefault(pair.output_index, set()).add(pair.input_index)
    return {frozenset(members) for members in parts.values()}


def _by_input(pairs: Iterable[ParentPair]) -> dict[int, set[int]]:
    by_input: dict[int, set[int]] = {}
    for pair in pairs:
        by_input.setdefault(pair.input_index, set()).add(pair.output_index)
    return by_input


def _part_sets(pairs: Iterable[ParentPair], work_key_of: dict[int, int]) -> PartSets:
    parts: dict[int, set[int]] = {}
    for pair in pairs:
        parts.setdefault(pair.output_index, set()).add(work_key_of[pair.input_index])
    return {frozenset(members) for members in parts.values()}


def _show_parts(parts: PartSets) -> list[list[int]]:
    return sorted(sorted(part) for part in parts)


def compare_with_native(
    pairs: Iterable[ParentPair],
    native: set[ParentPair],
    show: int = 5,
    spotlight: Collection[int] = (),
) -> bool:
    """Pair for pair, as a partition, and per input in both directions.

    Pairs whose input is in `spotlight` (inputs the native table omits) are reported on
    their own and left out of the general counts, so those describe the locator alone.
    """
    ours = set(pairs)
    if spotlight:
        spot = set(spotlight)
        spot_native = {p for p in native if p.input_index in spot}
        spot_ours = {p for p in ours if p.input_index in spot}
        record(
            "mismatches involving absent inputs",
            f"only in native {sorted(spot_native - spot_ours)[:show]}, "
            f"only in resolver {sorted(spot_ours - spot_native)[:show]}",
        )
        native = native - spot_native
        ours = ours - spot_ours
    record("native pairs", len(native))
    record("resolver pairs", len(ours))
    record("pair sets equal", ours == native)
    record("partitions of inputs equal", _partition(ours) == _partition(native))
    if ours != native:
        record(f"only in native (first {show})", sorted(native - ours)[:show])
        record(f"only in resolver (first {show})", sorted(ours - native)[:show])
        native_by, ours_by = _by_input(native), _by_input(ours)
        fewer = sorted(
            i for i, outs in native_by.items() if len(ours_by.get(i, set())) < len(outs)
        )
        extra = sorted(
            i for i, outs in ours_by.items() if outs - native_by.get(i, set())
        )
        record(
            "inputs matched to fewer parts than native",
            f"{len(fewer)}, first {show}: {fewer[:show]}",
        )
        record(
            "inputs matched to parts native does not list",
            f"{len(extra)}, first {show}: {extra[:show]}",
        )
    return ours == native


def check_guards(fc: str, resolution: ParentsResolution) -> None:
    """The post-call rule: unmatched inputs must be degenerate, else it raises."""
    unmatched = list(resolution.unmatched_input_indices)
    degenerate = degenerate_inputs(fc, unmatched)
    record("unmatched inputs", len(unmatched))
    record("of which degenerate", len(degenerate))
    try:
        require_matched(resolution=resolution, degenerate_input_indices=degenerate)
        record("require_matched", "ok")
    except UnmatchedInputError as exc:
        record("require_matched raised", str(exc)[:200])


def precheck(fc: str) -> list[int]:
    """The pre-call guard, timed and reported, never raised here."""
    started = time.perf_counter()
    empty = find_empty_geometries(fc)
    record("empty-geometry pre-check s", round(time.perf_counter() - started, 2))
    record("empty geometries (OIDs, first 10)", empty[:10] if empty else "none")
    if empty:
        record(
            "pre-call guard", f"would raise EmptyGeometryError for {len(empty)} row(s)"
        )
    return empty


def run_all_locators(
    fc: str, out: str, native: set[ParentPair] | None
) -> dict[str, dict[str, list[tuple[int, int]]]]:
    """Every applicable locator against one dissolve output; returns golden material."""
    recorded: dict[str, dict[str, list[tuple[int, int]]]] = {}
    for name in locators_for(fc):
        print(f"     . locator {name}")
        try:
            run = run_locator(name, fc, out, fields=KEY_FIELDS)
        except Exception as exc:
            handled("raised", exc)
            print(traceback.format_exc())
            continue
        record("resolver total s", round(run.total_s, 2))
        for stage, seconds in run.timings.items():
            if stage.startswith("locator stage:"):
                record(stage, round(seconds, 2))
        if native is not None:
            compare_with_native(run.resolution.pairs, native)
        check_guards(fc, run.resolution)
        recorded[name] = {
            "hits": [(p.output_index, p.input_index) for p in run.hits],
            "resolved": [(p.output_index, p.input_index) for p in run.resolution.pairs],
        }
    return recorded


# ---------------------------------------------------------------------------
# Small fixtures
# ---------------------------------------------------------------------------


def multipart_polyline(
    parts: Sequence[Sequence[tuple[float, float]]],
) -> arcpy.Polyline:
    return arcpy.Polyline(
        arcpy.Array([arcpy.Array([arcpy.Point(*c) for c in part]) for part in parts]),
        fx.spatial_reference(),
    )


def _split_group_lines(gdb: str, name: str = "split_lines") -> tuple[str, PartSets]:
    """Five 10 m segments, one key: rows 1-3 touch end to end, rows 4-5 too, 100 m away."""
    fc = fx.create_keyed_fc(gdb, name, "POLYLINE")
    x0, y0 = fx.ORIGIN
    starts = {1: 0.0, 2: 10.0, 3: 20.0, 4: 130.0, 5: 140.0}
    insert(
        fc,
        ["SHAPE@", WORK_KEY, fx.GROUP],
        (
            (polyline([(x0 + s, y0), (x0 + s + 10.0, y0)]), k, 1)
            for k, s in starts.items()
        ),
    )
    return fc, {frozenset({1, 2, 3}), frozenset({4, 5})}


def _split_group_polygons(
    gdb: str, name: str = "split_polygons"
) -> tuple[str, PartSets]:
    """Two 50 m squares 100 m apart, one key."""
    fc = fx.create_keyed_fc(gdb, name, "POLYGON")
    x0, y0 = fx.ORIGIN
    insert(
        fc,
        ["SHAPE@", WORK_KEY, fx.GROUP],
        [(square(x0, y0, 50.0), 1, 1), (square(x0 + 150.0, y0, 50.0), 2, 1)],
    )
    return fc, {frozenset({1}), frozenset({2})}


def _boundary_fixtures(gdb: str) -> list[tuple[str, str, PartSets | None]]:
    """(slug, feature class, expected parts as work-key sets or None) for each shape."""
    x0, y0 = fx.ORIGIN
    fixtures: list[tuple[str, str, PartSets | None]] = []
    keyed = ["SHAPE@", WORK_KEY, fx.GROUP]

    fc = fx.create_keyed_fc(gdb, "shared_edge", "POLYGON")
    insert(
        fc,
        keyed,
        [(square(x0, y0, 100.0), 1, 1), (square(x0 + 100.0, y0, 100.0), 2, 2)],
    )
    fixtures.append(("shared_edge", fc, {frozenset({1}), frozenset({2})}))

    fc = fx.create_keyed_fc(gdb, "overlap", "POLYGON")
    insert(
        fc, keyed, [(square(x0, y0, 100.0), 1, 1), (square(x0 + 30.0, y0, 100.0), 2, 2)]
    )
    fixtures.append(("overlap", fc, {frozenset({1}), frozenset({2})}))

    junction = (x0 + 100.0, y0 + 100.0)
    arms = [(x0, y0 + 100.0), (x0 + 100.0, y0 + 200.0), (x0 + 200.0, y0 + 100.0)]
    fc = fx.create_keyed_fc(gdb, "junction_keys", "POLYLINE")
    insert(
        fc, keyed, [(polyline([arm, junction]), k, k) for k, arm in enumerate(arms, 1)]
    )
    fixtures.append(
        ("junction_keys", fc, {frozenset({1}), frozenset({2}), frozenset({3})})
    )

    fc = fx.create_keyed_fc(gdb, "junction_same_key", "POLYLINE")
    insert(
        fc, keyed, [(polyline([arm, junction]), k, 1) for k, arm in enumerate(arms, 1)]
    )
    fixtures.append(("junction_same_key", fc, None))

    fc = fx.create_keyed_fc(gdb, "zero_length", "POLYLINE")
    rows: list[tuple[arcpy.Polyline, int, int]] = [
        (polyline([(x0, y0), (x0 + 10.0, y0)]), 1, 1)
    ]
    for work_key, group, x in ((2, 1, x0 + 50.0), (3, 2, x0 + 80.0)):
        try:
            rows.append((polyline([(x, y0), (x, y0)]), work_key, group))
        except Exception as exc:
            record(
                f"zero-length polyline {work_key} raised",
                f"{type(exc).__name__}: {exc}",
            )
    insert(fc, keyed, rows)
    fixtures.append(("zero_length", fc, None))

    fc = fx.create_keyed_fc(gdb, "multipart_spanning", "POLYLINE")
    insert(
        fc,
        keyed,
        [
            (polyline([(x0, y0), (x0 + 10.0, y0)]), 1, 1),
            (polyline([(x0 + 10.0, y0), (x0 + 20.0, y0)]), 2, 1),
            (
                multipart_polyline(
                    [
                        [(x0 + 20.0, y0), (x0 + 30.0, y0)],
                        [(x0 + 130.0, y0), (x0 + 140.0, y0)],
                    ]
                ),
                3,
                1,
            ),
            (polyline([(x0 + 140.0, y0), (x0 + 150.0, y0)]), 4, 1),
        ],
    )
    fixtures.append(
        ("multipart_spanning", fc, {frozenset({1, 2, 3}), frozenset({3, 4})})
    )

    fc, expected = _split_group_lines(gdb)
    fixtures.append(("split_lines", fc, expected))
    fc, expected = _split_group_polygons(gdb)
    fixtures.append(("split_polygons", fc, expected))
    return fixtures


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def case_fixture_build_method(ws: Workspace, cache: fx.FixtureCache) -> None:
    """InsertCursor against NumPyArrayToTable + XYToLine for 10^5 two-point segments.

    The faster method that ran is written to the cache root and used by every later
    segment fixture build. Fixtures already cached keep the method they were built with.
    """
    size = 10**5
    timings: dict[str, float] = {}
    for method in ("cursor", "xy_to_line"):
        print(f"  -- {method}")
        gdb = ws.gdb(f"build_{method}")
        started = time.perf_counter()
        try:
            fc = fx.write_segments(
                gdb, "segments", fx.collinear_rows(size, None), method
            )
        except Exception as exc:
            handled("raised", exc)
            continue
        timings[method] = time.perf_counter() - started
        record("seconds", round(timings[method], 1))
        record("rows", int(arcpy.management.GetCount(fc)[0]))
        record("fields", [f.name for f in arcpy.ListFields(fc)])
    if not timings:
        record("build method", "neither method ran; cache keeps 'cursor'")
        return
    chosen = min(timings, key=lambda m: timings[m])
    cache.save_build_method(chosen, {k: round(v, 1) for k, v in timings.items()})
    record("build method chosen", chosen)


def case_native_lineage_table(ws: Workspace) -> None:
    """Pro 3.7's PairwiseDissolve lineage table on the split fixtures, and MULTI_PART.

    Timing at size was recorded on 2026-09-15 (110 s added at 10^5) and settled B's
    production role; this case keeps only the behavioural checks.
    """
    if not _lineage_table_available():
        record("verdict", "NOT AVAILABLE on this build")
        return
    gdb = ws.gdb("native_lineage")
    for label, (fc, expected) in (
        ("lines", _split_group_lines(gdb)),
        ("polygons", _split_group_polygons(gdb)),
    ):
        print(f"  -- split group, {label}")
        out = os.path.join(gdb, f"{label}_dissolved")
        table = os.path.join(gdb, f"{label}_tbl")
        try:
            dissolve_once(fc, out, table)
        except Exception as exc:
            handled("raised", exc)
            continue
        record("lineage table at <output>_Tbl", arcpy.Exists(out + "_Tbl"))
        if not arcpy.Exists(table):
            continue
        pairs = _table_pairs(table)
        work_key_of = dict(read(fc, ["OID@", WORK_KEY]))
        observed = _part_sets(pairs, work_key_of)
        record("parts as work-key sets", _show_parts(observed))
        record("expected", _show_parts(expected))
        record("parts match expected", observed == expected)

    print("  -- MULTI_PART with a table path: the page says no table is created")
    fc, _ = _split_group_lines(gdb, name="multipart_probe")
    out = os.path.join(gdb, "multipart_dissolved")
    table = os.path.join(gdb, "multipart_tbl")
    try:
        arcpy.analysis.PairwiseDissolve(
            fc,
            out,
            fx.GROUP,
            multi_part="MULTI_PART",
            **{LINEAGE_TABLE_PARAMETER: table},
        )
        record("ran", "no error")
        record("table at the given path", arcpy.Exists(table))
        record("table at <output>_Tbl", arcpy.Exists(out + "_Tbl"))
    except Exception as exc:
        handled("raised", exc)


def case_statistics_per_part_or_per_group(ws: Workspace) -> None:
    """With SINGLE_PART, are statistics computed per output part or per dissolve group?

    Measured PER GROUP on 3.7.2 for both tools on 2026-09-15; kept so any build can
    re-answer it.
    """
    gdb = ws.gdb("statistics_scope")
    statistics = [[WORK_KEY, "CONCATENATE"], [WORK_KEY, "COUNT"]]
    for label, (fc, expected) in (
        ("lines", _split_group_lines(gdb)),
        ("polygons", _split_group_polygons(gdb)),
    ):
        work_key_of = dict(read(fc, ["OID@", WORK_KEY]))
        group_size = len(work_key_of)
        for tool_label in ("PairwiseDissolve", "Dissolve"):
            print(f"  -- {label}, {tool_label}, CONCATENATE + COUNT of the work key")
            out = os.path.join(gdb, f"{label}_{tool_label.lower()}")
            try:
                if tool_label == "PairwiseDissolve":
                    arcpy.analysis.PairwiseDissolve(
                        fc, out, fx.GROUP, statistics, "SINGLE_PART", ";"
                    )
                else:
                    arcpy.management.Dissolve(
                        fc,
                        out,
                        fx.GROUP,
                        statistics,
                        "SINGLE_PART",
                        "DISSOLVE_LINES",
                        ";",
                    )
            except Exception as exc:
                handled("raised", exc)
                continue
            names = [f.name for f in arcpy.ListFields(out)]
            concat = next(
                (n for n in names if n.upper().startswith("CONCATENATE")), None
            )
            count = next((n for n in names if n.upper().startswith("COUNT")), None)
            if concat is None or count is None:
                record("statistic fields", f"missing: {names}")
                continue
            rows = read(out, ["OID@", concat, count])
            record("rows (OID, CONCATENATE, COUNT)", rows)
            observed: PartSets = set()
            for _, text, _ in rows:
                _, parsed, _, _ = _parse_tokens(text or "", ";")
                observed.add(frozenset(parsed))
            record("CONCATENATE as work-key sets", _show_parts(observed))
            record("expected parts", _show_parts(expected))
            counts = [c for _, _, c in rows]
            if len(rows) > 1 and all(c == group_size for c in counts):
                verdict = "PER GROUP: every part carries the whole group's statistics"
            elif observed == expected:
                verdict = "PER PART"
            else:
                verdict = "NEITHER cleanly; read the rows"
            record("verdict to record", verdict)


def case_aggregate_pass_through(ws: Workspace) -> None:
    """AggregatePolygons out_table: does it list an input that passed through unaggregated?

    Three 20 m squares: A and B 5 m apart (aggregated at 10 m), C 200 m away
    (pass-through). Advanced licence required.
    """
    gdb = ws.gdb("aggregate")
    fc = fx.create_keyed_fc(gdb, "squares", "POLYGON")
    x0, y0 = fx.ORIGIN
    insert(
        fc,
        ["SHAPE@", WORK_KEY, fx.GROUP],
        [
            (square(x0, y0, 20.0), 1, 1),
            (square(x0 + 25.0, y0, 20.0), 2, 1),
            (square(x0 + 200.0, y0, 20.0), 3, 1),
        ],
    )
    out = os.path.join(gdb, "aggregated")
    table = os.path.join(gdb, "aggregated_tbl")
    record("CheckProduct ArcInfo (Advanced)", arcpy.CheckProduct("ArcInfo"))
    try:
        arcpy.cartography.AggregatePolygons(fc, out, "10 Meters", out_table=table)
    except Exception as exc:
        handled("raised", exc)
        return
    record("output rows (OID, area)", read(out, ["OID@", "SHAPE@AREA"]))
    record("table exists at the given path", arcpy.Exists(table))
    if not arcpy.Exists(table):
        record("table at <output>_tbl", arcpy.Exists(out + "_tbl"))
        return
    rows = read(table, ["OUTPUT_FID", "INPUT_FID"])
    record("table rows (OUTPUT_FID, INPUT_FID)", rows)
    listed = {i for _, i in rows}
    record("pass-through input 3 listed in the table", 3 in listed)
    record("inputs listed", sorted(listed))
    record("distinct OUTPUT_FID", len({o for o, _ in rows}))


def case_boundary_fixtures(ws: Workspace, goldens_dir: str | None) -> None:
    """Every small shape: one dissolve with the lineage table, every locator against it.

    Shared edge and overlap between keys, junctions with distinct and with one key,
    empty geometries, a multipart input spanning two parts, and the two split groups.
    With --write-goldens, each fixture's keys, native pairs and per-locator hits are
    written for the no-ArcPy replay test.
    """
    available = _lineage_table_available()
    gdb = ws.gdb("boundary")
    version = pro_version()
    for slug, fc, expected in _boundary_fixtures(gdb):
        print(f"  -- {slug}")
        record(
            "input rows (OID, work key, grp, parts, length)",
            [
                (
                    oid,
                    k,
                    g,
                    geom.partCount if geom else None,
                    round(geom.length, 3) if geom else None,
                )
                for oid, k, g, geom in read(fc, ["OID@", WORK_KEY, fx.GROUP, "SHAPE@"])
            ],
        )
        precheck(fc)
        out = os.path.join(gdb, f"{slug}_dissolved")
        table = os.path.join(gdb, f"{slug}_tbl") if available else None
        try:
            dissolve_once(fc, out, table)
        except Exception as exc:
            handled("dissolve raised", exc)
            continue
        record(
            "output rows (OID, grp, parts)",
            [
                (oid, g, geom.partCount if geom else None)
                for oid, g, geom in read(out, ["OID@", fx.GROUP, "SHAPE@"])
            ],
        )
        native = set(_table_pairs(table)) if table and arcpy.Exists(table) else None
        work_key_of = dict(read(fc, ["OID@", WORK_KEY]))
        if native is not None:
            record(
                "native parts as work-key sets",
                _show_parts(_part_sets(native, work_key_of)),
            )
        if expected is not None:
            record("expected", _show_parts(expected))
        recorded = run_all_locators(fc, out, native)
        if goldens_dir and native is not None:
            path = fx.write_golden(
                goldens_dir,
                fixture=slug,
                pro_version=version,
                input_keys=_read_keys(fc, KEY_FIELDS),
                output_keys=_read_keys(out, KEY_FIELDS),
                native_pairs=[(p.output_index, p.input_index) for p in native],
                locators=recorded,
            )
            record("golden written", path)


def case_group_size_prepass_timing(ws: Workspace, cache: fx.FixtureCache) -> None:
    """Option C's fixed per-dissolve costs at each timing size: key reads and the pre-check."""
    for size in TIMING_SIZES:
        print(f"  -- {size:,} rows")
        fc, built = cache.inputs("collinear_one_part", size)
        record("fixture", "built now" if built is not None else "cached")
        started = time.perf_counter()
        with arcpy.da.SearchCursor(fc, [fx.GROUP]) as cursor:
            counter = Counter(key for (key,) in cursor)
        elapsed = time.perf_counter() - started
        record("Counter over one field s", round(elapsed, 2))
        record("rows per s", int(size / elapsed) if elapsed else "n/a")
        record("largest group", max(counter.values()))
        started = time.perf_counter()
        keys = _read_keys(fc, KEY_FIELDS)
        record("(OID, one-field key) list s", round(time.perf_counter() - started, 2))
        started = time.perf_counter()
        keys = _read_keys(fc, (fx.GROUP, WORK_KEY))
        record("(OID, two-field key) list s", round(time.perf_counter() - started, 2))
        record("distinct two-field keys", len({key for _, key in keys}))
        precheck(fc)


def case_resolver_correctness_ladder(ws: Workspace, cache: fx.FixtureCache) -> None:
    """Every fixture at 10^2, 10^3 and 10^4: one dissolve with the lineage table, every
    locator against it, pair for pair and as a partition, with the per-input diagnostics.
    """
    available = _lineage_table_available()
    for name in fx.FIXTURE_BUILDERS:
        for size in CORRECTNESS_SIZES:
            print(f"  -- {name}, size {size:,}: {fx.FIXTURE_NOTES[name]}")
            if name.startswith("lattice"):
                record("lattice", fx.lattice_counts(size))
            fc, built = cache.inputs(name, size)
            record(
                "fixture", f"built in {built:.1f} s" if built is not None else "cached"
            )
            record("input rows", int(arcpy.management.GetCount(fc)[0]))
            try:
                out, table = cached_dissolve(cache, name, size, with_table=available)
            except Exception as exc:
                handled("dissolve raised", exc)
                continue
            native = set(_table_pairs(table)) if table and arcpy.Exists(table) else None
            if native is not None:
                record("native pairs", len(native))
                record(
                    "native parts per input, max",
                    max(len(v) for v in _by_input(native).values()),
                )
            run_all_locators(fc, out, native)


def cached_dissolve(
    cache: fx.FixtureCache, name: str, size: int, with_table: bool
) -> tuple[str, str | None]:
    """The fixture's dissolve output from the cache, dissolving in-process if absent."""
    out, table, directory, payload = cache.dissolved(name, size, with_table)
    if payload is not None:
        record("dissolve output", f"cached ({payload.get('seconds')} s when made)")
        record("output rows", payload.get("rows"))
        return out, table
    cache.prepare_dissolve(directory)
    seconds = dissolve_once(fc_of(cache, name, size), out, table)
    cache.mark_dissolved(
        directory,
        {"seconds": round(seconds, 2), "rows": int(arcpy.management.GetCount(out)[0])},
    )
    return out, table


def fc_of(cache: fx.FixtureCache, name: str, size: int) -> str:
    fc, _ = cache.inputs(name, size)
    return fc


def _spawn_child(
    label: str,
    child_args: Sequence[str],
    workdir: str,
    log_file: str,
    timeout_s: float,
) -> dict[str, Any] | None:
    """One child interpreter; returns its RESULT payload, or None on timeout or failure.

    The child appends to the same log, so its lines are echoed to the console only.
    """
    command = [
        sys.executable,
        os.path.abspath(__file__),
        "--workdir",
        workdir,
        "--log-file",
        log_file,
        *child_args,
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - started)
        record(
            label,
            f"TIMED OUT after {elapsed} s (limit {timeout_s:.0f} s including "
            f"{CHILD_STARTUP_S:.0f} s interpreter start-up)",
        )
        partial = exc.stdout if isinstance(exc.stdout, str) else ""
        for line in (partial or "").splitlines():
            _console(f"       {line}\n")
        return None
    for line in completed.stdout.splitlines():
        if not line.startswith("RESULT "):
            _console(f"       {line}\n")
    if completed.returncode != 0:
        record(f"{label} child exit code", completed.returncode)
        for line in completed.stderr.splitlines()[-15:]:
            print(f"       {line}")
        return None
    result_line = next(
        (line for line in completed.stdout.splitlines() if line.startswith("RESULT ")),
        None,
    )
    if result_line is None:
        record(label, "child printed no RESULT line")
        return None
    return dict(json.loads(result_line[len("RESULT ") :]))


def _spawn_locator(
    locator_name: str, fc: str, out: str, workdir: str, log_file: str, timeout_s: float
) -> float | None:
    result = _spawn_child(
        locator_name,
        ["--child-locate", locator_name, "--child-input", fc, "--child-output", out],
        workdir,
        log_file,
        timeout_s,
    )
    if result is None:
        return None
    record(f"{locator_name} total s", round(float(result["total_s"]), 2))
    return float(result["total_s"])


def _spawn_dissolve(
    fc: str, out: str, workdir: str, log_file: str, timeout_s: float
) -> float | None:
    result = _spawn_child(
        "plain dissolve",
        ["--child-dissolve", "--child-input", fc, "--child-output", out],
        workdir,
        log_file,
        timeout_s,
    )
    return None if result is None else float(result["dissolve_s"])


def _timing_point(
    name: str,
    size: int,
    locator_names: Sequence[str],
    cache: fx.FixtureCache,
    workdir: str,
    log_file: str,
    timeout_s: float,
) -> dict[str, float | None]:
    """One (fixture, size): cached fixture, cached or child-capped dissolve, then locators."""
    print(f"  -- {name}, size {size:,}")
    fc, built = cache.inputs(name, size)
    record("fixture", f"built in {built:.1f} s" if built is not None else "cached")
    precheck(fc)
    skipped: dict[str, float | None] = {n: None for n in locator_names}
    out, _, directory, payload = cache.dissolved(name, size, with_table=False)
    if payload is None:
        baseline = cache.baseline(name, size)
        if baseline is not None and baseline.get("timed_out_after_s") is not None:
            record(
                "plain dissolve",
                f"tool alone over budget on this shape (timed out after "
                f"{baseline['timed_out_after_s']} s on an earlier run); locators skipped",
            )
            return skipped
        cache.prepare_dissolve(directory)
        seconds = _spawn_dissolve(fc, out, workdir, log_file, timeout_s)
        if seconds is None:
            cache.save_baseline(name, size, None, timed_out_after_s=timeout_s)
            record(
                "plain dissolve",
                "tool alone over budget on this shape; locators skipped",
            )
            return skipped
        cache.mark_dissolved(
            directory,
            {
                "seconds": round(seconds, 2),
                "rows": int(arcpy.management.GetCount(out)[0]),
            },
        )
        cache.save_baseline(name, size, seconds)
        record("plain dissolve baseline s", round(seconds, 2))
    else:
        record("plain dissolve baseline s (cached)", payload.get("seconds"))
    results: dict[str, float | None] = {}
    for locator_name in locator_names:
        print(f"     . locator {locator_name}, child interpreter")
        results[locator_name] = _spawn_locator(
            locator_name, fc, out, workdir, log_file, timeout_s
        )
    return results


def case_resolver_timing_ladder(
    cache: fx.FixtureCache,
    workdir: str,
    log_file: str,
    timeout_factor: float,
    confirm_large: bool,
    include_pathological: bool,
) -> None:
    """The three realistic shapes at 10^4 and 10^5, dissolve and each locator in a capped
    child, then the fitted exponent and the predicted 10^6 time; 10^6 only with
    --confirm-large, only for locators predicted under the timeout, and never for a
    pathological fixture without --include-pathological.
    """
    timeout_s = timeout_factor * BUDGET_S + CHILD_STARTUP_S
    record("budget s", BUDGET_S)
    record("child timeout s", timeout_s)
    for name in TIMING_FIXTURES:
        fc_probe, _ = cache.inputs(name, TIMING_SIZES[0])
        locator_names = locators_for(fc_probe)
        if name == "collinear_one_part":
            locator_names = ("midpoint",)
        results: dict[str, dict[int, float | None]] = {n: {} for n in locator_names}
        for size in TIMING_SIZES:
            point = _timing_point(
                name, size, locator_names, cache, workdir, log_file, timeout_s
            )
            for locator_name, seconds in point.items():
                results[locator_name][size] = seconds
        print(f"  -- {name}: fit from {TIMING_SIZES[0]:,} and {TIMING_SIZES[1]:,}")
        eligible: list[str] = []
        for locator_name, by_size in results.items():
            small, large = by_size.get(TIMING_SIZES[0]), by_size.get(TIMING_SIZES[1])
            if small is None or large is None:
                record(f"{locator_name}", "no fit: a point timed out or failed")
                continue
            exponent = math.log10(large / max(small, 0.01))
            predicted = large * 10**exponent
            record(f"{locator_name} fitted exponent", round(exponent, 2))
            record(f"{locator_name} predicted 10^6 s", round(predicted, 1))
            record(
                f"{locator_name} predicted under {timeout_s:.0f} s",
                predicted < timeout_s,
            )
            if predicted < timeout_s:
                eligible.append(locator_name)
        settled = SETTLED_BASELINES.get((name, LARGE_SIZE))
        if settled is not None:
            record("settled 10^6 plain-dissolve baseline s", settled)
        if not confirm_large:
            record(
                "10^6",
                f"not run: pass --confirm-large; eligible now: {eligible or 'none'}",
            )
            continue
        if name in PATHOLOGICAL_FIXTURES and not include_pathological:
            record(
                "10^6",
                "not run: pathological fixture (the tool alone is over budget); "
                "pass --include-pathological to run it anyway",
            )
            continue
        if not eligible:
            record("10^6", "not run: no locator predicted under the timeout")
            continue
        _timing_point(name, LARGE_SIZE, eligible, cache, workdir, log_file, timeout_s)


def _percentiles(values: Sequence[int]) -> dict[str, int]:
    if not values:
        return {"p50": 0, "p95": 0, "max": 0}
    ordered = sorted(values)
    last = len(ordered) - 1
    return {
        "p50": ordered[int(0.5 * last)],
        "p95": ordered[int(0.95 * last)],
        "max": ordered[last],
    }


def _key_stats(path: str, fields: Sequence[str]) -> tuple[Counter, int]:
    """Group sizes of the key over `path`; returns the Counter and the row count."""
    keys = _read_keys(path, fields)
    counter = Counter(key for _, key in keys)
    record("rows", len(keys))
    record("distinct keys", len(counter))
    record("largest groups (key, rows)", counter.most_common(5))
    return counter, len(keys)


def _selection_rows(path: str) -> tuple[int, int] | None:
    """(processing, halo) from the iterator's selection field, or None if not present."""
    if PARTITION_FIELD not in [f.name for f in arcpy.ListFields(path)]:
        return None
    processing = halo = 0
    with arcpy.da.SearchCursor(path, [PARTITION_FIELD]) as cursor:
        for (flag,) in cursor:
            if flag == 1:
                processing += 1
            else:
                halo += 1
    return processing, halo


def _ramps_subset(path: str, gdb: str) -> str | None:
    """The rows the live ramps dissolve sees: non-ramp centrelines within 400 m of ramps."""
    names = [f.name for f in arcpy.ListFields(path)]
    if "typeveg" not in names or "objtype" not in names:
        record("ramps subset", "skipped: typeveg or objtype missing")
        return None
    ramps = arcpy.management.MakeFeatureLayer(path, "ramps_lyr", "typeveg = 'rampe'")[0]
    buffer = os.path.join(gdb, "ramps_buffer")
    arcpy.analysis.Buffer(ramps, buffer, f"{RAMPS_BUFFER_M} Meters")
    roads = arcpy.management.MakeFeatureLayer(path, "roads_lyr", RAMPS_SUBSET_WHERE)[0]
    arcpy.management.SelectLayerByLocation(
        roads, "INTERSECT", buffer, selection_type="NEW_SELECTION"
    )
    subset = os.path.join(gdb, "ramps_subset")
    arcpy.management.CopyFeatures(roads, subset)
    arcpy.management.Delete(ramps)
    arcpy.management.Delete(roads)
    return subset


def _dissolve_in_child(
    label: str,
    path: str,
    fields: Sequence[str],
    out: str,
    table: str | None,
    workdir: str,
    log_file: str,
    timeout_s: float,
) -> float | None:
    """One dissolve of real data in the capped child; seconds, or None on timeout."""
    child_args = [
        "--child-dissolve",
        "--child-input",
        path,
        "--child-output",
        out,
        "--child-key-fields",
        ",".join(fields) if fields else NO_FIELDS,
    ]
    if table:
        child_args += ["--child-table", table]
    result = _spawn_child(label, child_args, workdir, log_file, timeout_s)
    return None if result is None else float(result["dissolve_s"])


def _key_where(path: str, fields: Sequence[str], key: DissolveKey) -> str:
    """A where clause selecting one dissolve key's rows; empty fields select everything."""
    clauses: list[str] = []
    for field, value in zip(fields, key):
        name = arcpy.AddFieldDelimiters(path, field)
        if value is None:
            clauses.append(f"{name} IS NULL")
        elif isinstance(value, str):
            clauses.append(f"{name} = '{value.replace(chr(39), chr(39) * 2)}'")
        else:
            clauses.append(f"{name} = {value}")
    return " AND ".join(clauses) or "1=1"


def _nearest_same_key(
    out: str,
    fields: Sequence[str],
    key: DissolveKey,
    geometry: arcpy.Geometry,
    radius_m: float,
) -> tuple[float | None, int | None]:
    """Distance to, and OID of, the nearest same-key part within `radius_m`, else (None, None)."""
    layer = arcpy.management.MakeFeatureLayer(
        out, "same_key_parts", _key_where(out, fields, key)
    )[0]
    try:
        arcpy.management.SelectLayerByLocation(
            layer, "WITHIN_A_DISTANCE", geometry, f"{radius_m} Meters", "NEW_SELECTION"
        )
        best: tuple[float | None, int | None] = (None, None)
        with arcpy.da.SearchCursor(layer, ["OID@", "SHAPE@"]) as cursor:
            for oid, part in cursor:
                distance = geometry.distanceTo(part)
                if best[0] is None or distance < best[0]:
                    best = (distance, oid)
        return best
    finally:
        arcpy.management.Delete(layer)


def _diagnose_absent(
    path: str,
    fields: Sequence[str],
    absent: Sequence[int],
    plain_out: str,
    lineage_out: str,
    in_table: set[int],
    tolerance: float,
) -> dict[int, str]:
    """Per absent input: shape facts, same-key duplicates, nearest parts, and the outcome.

    Outcomes: 'dropped by the tool' (absent from both outputs), 'duplicate or overlap'
    (a same-key input with identical or overlapping geometry is in the table), 'omitted
    parent' (lies on a lineage part, no duplicate explains it), else 'unclear'.
    """
    outcomes: dict[int, str] = {}
    if not absent:
        return outcomes
    oid_field = arcpy.Describe(path).OIDFieldName
    where = f"{oid_field} IN ({', '.join(str(i) for i in absent)})"
    rows = []
    with arcpy.da.SearchCursor(
        path, ["OID@", "SHAPE@", *fields], where_clause=where
    ) as cursor:
        rows = [(row[0], row[1], tuple(row[2:])) for row in cursor]
    for oid, geometry, key in rows:
        print(f"     . absent input {oid}")
        if geometry is None:
            record("shape", "empty")
            outcomes[oid] = "empty geometry"
            continue
        first, last = geometry.firstPoint, geometry.lastPoint
        closed = first.X == last.X and first.Y == last.Y
        record(
            "length / vertices / parts / closed loop",
            (
                round(geometry.length, 3),
                geometry.pointCount,
                geometry.partCount,
                closed,
            ),
        )
        record("key", key)
        duplicate: tuple[int, str, bool] | None = None
        layer = arcpy.management.MakeFeatureLayer(
            path,
            "same_key_inputs",
            f"({_key_where(path, fields, key)}) AND {oid_field} <> {oid}",
        )[0]
        try:
            arcpy.management.SelectLayerByLocation(
                layer, "INTERSECT", geometry, selection_type="NEW_SELECTION"
            )
            with arcpy.da.SearchCursor(layer, ["OID@", "SHAPE@"]) as cursor:
                for other_oid, other in cursor:
                    if other is None:
                        continue
                    if geometry.equals(other):
                        relation = "identical"
                    elif (
                        geometry.overlaps(other)
                        or geometry.contains(other)
                        or geometry.within(other)
                    ):
                        relation = "overlapping"
                    else:
                        continue
                    duplicate = (other_oid, relation, other_oid in in_table)
                    break
        finally:
            arcpy.management.Delete(layer)
        record("same-key duplicate (OID, relation, in table)", duplicate or "none")
        plain_distance, plain_oid = _nearest_same_key(
            plain_out, fields, key, geometry, 50.0
        )
        lineage_distance, lineage_oid = _nearest_same_key(
            lineage_out, fields, key, geometry, 50.0
        )
        record(
            "nearest same-key part in the plain output (m, OID)",
            (plain_distance, plain_oid),
        )
        record(
            "nearest same-key part in the lineage output (m, OID)",
            (lineage_distance, lineage_oid),
        )
        on_plain = plain_distance is not None and plain_distance <= tolerance
        on_lineage = lineage_distance is not None and lineage_distance <= tolerance
        if not on_plain and not on_lineage:
            outcome = "dropped by the tool: absent from both outputs"
        elif duplicate is not None and duplicate[2]:
            outcome = f"duplicate or overlap with input {duplicate[0]} ({duplicate[1]}), which is in the table"
        elif on_lineage:
            outcome = f"omitted parent: lies on lineage part {lineage_oid} and no same-key duplicate explains it"
        else:
            outcome = "unclear: on the plain output only"
        record("outcome", outcome)
        outcomes[oid] = outcome
    return outcomes


def _match_outputs(
    plain_out: str,
    lineage_out: str,
    fields: Sequence[str],
    tolerance: float,
    contributors: dict[int, list[int]],
    absent_geometries: dict[int, arcpy.Geometry],
) -> None:
    """Which parts differ between the plain and the lineage dissolve, without pairwise work.

    Parts are bucketed by (key, length, centroid) rounded to the XY tolerance, `equals`
    runs inside a bucket only, and the few parts left unmatched are checked against the
    other side's same-key parts by extent before being reported.
    """
    started = time.perf_counter()

    def signature(key: DissolveKey, geometry: arcpy.Geometry) -> tuple:
        centroid = geometry.centroid
        return (
            key,
            round(geometry.length / tolerance),
            round(centroid.X / tolerance),
            round(centroid.Y / tolerance),
        )

    def read(out: str) -> dict[tuple, list[tuple[int, arcpy.Geometry, DissolveKey]]]:
        buckets: dict[tuple, list[tuple[int, arcpy.Geometry, DissolveKey]]] = {}
        with arcpy.da.SearchCursor(out, ["OID@", "SHAPE@", *fields]) as cursor:
            for row in cursor:
                oid, geometry, key = row[0], row[1], tuple(row[2:])
                if geometry is None:
                    continue
                buckets.setdefault(signature(key, geometry), []).append(
                    (oid, geometry, key)
                )
        return buckets

    plain_buckets = read(plain_out)
    lineage_buckets = read(lineage_out)
    record("bucketing s", round(time.perf_counter() - started, 1))
    started = time.perf_counter()
    unmatched_lineage: list[tuple[int, arcpy.Geometry, DissolveKey]] = []
    for sig, parts in lineage_buckets.items():
        candidates = plain_buckets.get(sig, [])
        for oid, geometry, key in parts:
            match = next((c for c in candidates if geometry.equals(c[1])), None)
            if match is None:
                unmatched_lineage.append((oid, geometry, key))
            else:
                candidates.remove(match)
    unmatched_plain = [part for parts in plain_buckets.values() for part in parts]
    record("matching s", round(time.perf_counter() - started, 1))
    record(
        "parts unmatched by bucket: lineage / plain",
        (len(unmatched_lineage), len(unmatched_plain)),
    )

    def confirm(part: tuple[int, arcpy.Geometry, DissolveKey], other_out: str) -> str:
        distance, other_oid = _nearest_same_key(
            other_out, fields, part[2], part[1], 50.0
        )
        if distance is not None and distance <= tolerance:
            return f"a same-key part within tolerance on the other side (OID {other_oid}, {round(distance, 4)} m)"
        return f"no same-key part within tolerance on the other side (nearest {distance} m)"

    for side, parts, other in (
        ("lineage", unmatched_lineage[:20], plain_out),
        ("plain", unmatched_plain[:20], lineage_out),
    ):
        for oid, geometry, key in parts:
            print(f"     . unmatched {side} part {oid}")
            record("key / length m", (key, round(geometry.length, 3)))
            record(
                "check against the other output", confirm((oid, geometry, key), other)
            )
            if side == "lineage":
                record(
                    "contributing inputs from the table", contributors.get(oid, [])[:20]
                )
            on_part = [
                a
                for a, g in absent_geometries.items()
                if g is not None and geometry.distanceTo(g) <= tolerance
            ]
            record("absent inputs on this part", on_part or "none")


def _probe_one(
    label: str,
    path: str,
    fields: Sequence[str],
    gdb: str,
    workdir: str,
    log_file: str,
    timeout_s: float,
    available: bool,
    count_only: bool,
) -> None:
    """One feature class, one key: group sizes, the bracketed dissolve, the native table's
    cost added over plain, the absent-input diagnostic, the extra-part match, and every
    line locator against the table.
    """
    print(f"  -- {label}: {path}")
    present = [f.name for f in arcpy.ListFields(path)]
    missing = [f for f in fields if f not in present]
    record("key fields", list(fields) or "none: the whole selection is one group")
    if missing:
        record("key fields missing", f"{missing}; block stopped")
        return
    counter, rows = _key_stats(path, fields)
    largest_key, largest_rows = counter.most_common(1)[0]
    record("largest key size (rows)", largest_rows)
    selection = _selection_rows(path)
    if selection is not None:
        processing, halo = selection
        record("processing rows", processing)
        record("halo rows", halo)
        record(
            "largest key <= processing + halo rows",
            f"{largest_rows} <= {processing} + {halo}: {largest_rows <= processing + halo}",
        )
    else:
        record("processing / halo rows", "not an exported partition selection")
    if count_only:
        record("count only", "no dissolve at this size")
        return

    started = time.perf_counter()
    with arcpy.da.SearchCursor(path, ["SHAPE@"]) as cursor:
        vertices = [geom.pointCount if geom else 0 for (geom,) in cursor]
    record("vertex scan s", round(time.perf_counter() - started, 1))
    record("vertices per input (p50/p95/max)", _percentiles(vertices))
    record("empty geometries", sum(1 for v in vertices if v == 0))
    tolerance = float(arcpy.Describe(path).spatialReference.XYTolerance)

    plain_out = os.path.join(gdb, f"{label}_plain")
    plain = _dissolve_in_child(
        "plain dissolve", path, fields, plain_out, None, workdir, log_file, timeout_s
    )
    if plain is None:
        record(
            "plain dissolve",
            "tool alone over budget on this shape; nothing else measured",
        )
        return
    record("plain dissolve s", round(plain, 1))
    out, table = plain_out, None
    if not available:
        record("native table", "not available on this build; no pair comparison")
    else:
        out = os.path.join(gdb, f"{label}_dissolved")
        table = os.path.join(gdb, f"{label}_lineage_tbl")
        with_table = _dissolve_in_child(
            "dissolve with lineage table",
            path,
            fields,
            out,
            table,
            workdir,
            log_file,
            timeout_s,
        )
        if with_table is None:
            record(
                "dissolve with lineage table",
                "over budget on this shape; locators run on the plain output",
            )
            out, table = plain_out, None
        else:
            record("dissolve with lineage table s", round(with_table, 1))
            record("lineage table, added over plain s", round(with_table - plain, 1))

    parts = Counter(key for _, key in _read_keys(out, fields))
    record("output parts", sum(parts.values()))
    record("keys with more than one part", sum(1 for v in parts.values() if v > 1))
    record("parts produced by the largest key", parts.get(largest_key, 0))
    record("most parts (key, parts)", parts.most_common(5))

    native = set(_table_pairs(table)) if table and arcpy.Exists(table) else None
    absent: list[int] = []
    if native is not None:
        per_input = Counter(pair.input_index for pair in native)
        record(
            "output parts per input (p50/p95/max)",
            _percentiles(list(per_input.values())),
        )
        absent = sorted({oid for oid, _ in _read_keys(path, ())} - set(per_input))
        degenerate = degenerate_inputs(path, absent)
        record(
            "inputs absent from the lineage table",
            f"{len(absent)}, degenerate {len(degenerate)}, first 10: {absent[:10]}",
        )
        if absent:
            try:
                _diagnose_absent(
                    path, fields, absent[:20], plain_out, out, set(per_input), tolerance
                )
            except Exception as exc:
                handled("absent-input diagnostic raised", exc)
                print(traceback.format_exc())
        plain_rows = int(arcpy.management.GetCount(plain_out)[0])
        lineage_rows = int(arcpy.management.GetCount(out)[0])
        record("plain / lineage output rows", (plain_rows, lineage_rows))
        try:
            contributors: dict[int, list[int]] = {}
            for pair in native:
                contributors.setdefault(pair.output_index, []).append(pair.input_index)
            absent_geometries: dict[int, arcpy.Geometry] = {}
            if absent:
                oid_field = arcpy.Describe(path).OIDFieldName
                with arcpy.da.SearchCursor(
                    path,
                    ["OID@", "SHAPE@"],
                    where_clause=f"{oid_field} IN ({', '.join(str(i) for i in absent[:20])})",
                ) as cursor:
                    absent_geometries = {oid: geom for oid, geom in cursor}
            _match_outputs(
                plain_out, out, fields, tolerance, contributors, absent_geometries
            )
        except Exception as exc:
            handled("extra-part match raised", exc)
            print(traceback.format_exc())
    else:
        record("output parts per input", "not measured")

    shape = arcpy.Describe(path).shapeType
    locator_names = ("midpoint", "segment") if shape == "Polyline" else ("midpoint",)
    for name in locator_names:
        print(f"     . locator {name}")
        try:
            run = run_locator(name, path, out, fields=fields)
        except Exception as exc:
            handled("raised", exc)
            print(traceback.format_exc())
            continue
        record("resolver total s (added over plain)", round(run.total_s, 2))
        for stage, seconds in run.timings.items():
            record(stage, round(seconds, 2))
        if native is not None:
            compare_with_native(run.resolution.pairs, native, show=10, spotlight=absent)
            if absent:
                fate = {
                    a: sorted(
                        p.output_index
                        for p in run.resolution.pairs
                        if p.input_index == a
                    )
                    for a in absent[:20]
                }
                record("absent inputs paired by this locator (OID: parts)", fate)
        check_guards(path, run.resolution)


def case_real_data_group_sizes(
    ws: Workspace,
    paths: Sequence[str],
    key_fields: Sequence[str] | None,
    count_only: bool,
    single_key: bool,
    workdir: str,
    log_file: str,
    timeout_factor: float,
) -> None:
    """The ramps dissolve key on the exported largest partition, then on the ramps subset the
    live dissolve sees; with --real-single-key also the whole selection as one group; with
    --real-count-only, the national 12-field key counted, no dissolve.

    Pass the feature class exported by `n1_real_partition.py` with --real-fc. For the national
    count pass the chain's input, `data_preparation___road_single_part___n100_road`. Every
    dissolve runs in the capped child, plain and with the lineage table, so the table's cost
    is reported added over plain; both line locators are compared against the table.
    """
    if not paths:
        record("real data", "NOT RUN: pass --real-fc <feature class> (repeatable)")
        return
    available = _lineage_table_available()
    timeout_s = timeout_factor * BUDGET_S + CHILD_STARTUP_S
    record("child timeout s", timeout_s)
    fields = (
        tuple(key_fields)
        if key_fields
        else (NATIONAL_KEY_FIELDS if count_only else RAMPS_KEY_FIELDS)
    )
    for index, path in enumerate(paths):
        gdb = ws.gdb(f"real_{index}")
        try:
            _probe_one(
                "partition",
                path,
                fields,
                gdb,
                workdir,
                log_file,
                timeout_s,
                available,
                count_only,
            )
            if count_only:
                continue
            if single_key:
                _probe_one(
                    "partition_single_key",
                    path,
                    (),
                    gdb,
                    workdir,
                    log_file,
                    timeout_s,
                    available,
                    False,
                )
            subset = _ramps_subset(path, gdb)
            if subset is not None:
                _probe_one(
                    "ramps_subset",
                    subset,
                    RAMPS_KEY_FIELDS,
                    gdb,
                    workdir,
                    log_file,
                    timeout_s,
                    available,
                    False,
                )
                if single_key:
                    _probe_one(
                        "ramps_subset_single_key",
                        subset,
                        (),
                        gdb,
                        workdir,
                        log_file,
                        timeout_s,
                        available,
                        False,
                    )
        except Exception as exc:
            handled("raised", exc)
            print(traceback.format_exc())


# ---------------------------------------------------------------------------
# Child and driver
# ---------------------------------------------------------------------------


def run_child_locate(locator_name: str, fc: str, out: str) -> int:
    run = run_locator(locator_name, fc, out, fields=KEY_FIELDS)
    for stage, seconds in run.timings.items():
        record(stage, round(seconds, 2))
    record("pairs", len(run.resolution.pairs))
    check_guards(fc, run.resolution)
    print(
        "RESULT "
        + json.dumps(
            {
                "locator": locator_name,
                "total_s": run.total_s,
                "pairs": len(run.resolution.pairs),
                "unmatched": len(run.resolution.unmatched_input_indices),
                "timings": run.timings,
            }
        )
    )
    return 0


def run_child_dissolve(
    fc: str, out: str, table: str | None, fields: Sequence[str] = KEY_FIELDS
) -> int:
    seconds = dissolve_once(fc, out, table, fields)
    rows = int(arcpy.management.GetCount(out)[0])
    print("RESULT " + json.dumps({"dissolve_s": seconds, "rows": rows}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="N:1 parents gate (B17).")
    parser.add_argument(
        "--workdir", required=True, help="scratch root; fixtures cache under it"
    )
    parser.add_argument(
        "--only", action="append", help="run only this case; repeatable"
    )
    parser.add_argument(
        "--write-goldens", action="store_true", help="write <workdir>\\goldens"
    )
    parser.add_argument(
        "--confirm-large", action="store_true", help="allow the 10^6 timing runs"
    )
    parser.add_argument(
        "--timeout-factor",
        type=float,
        default=3.0,
        help="child timeout = factor x budget",
    )
    parser.add_argument(
        "--real-fc", action="append", default=[], help="real feature class; repeatable"
    )
    parser.add_argument(
        "--real-key-fields",
        nargs="*",
        default=[],
        help="dissolve fields, space- or comma-separated, or the word 'national' for the "
        "twelve-field key; default ramps' five, or the twelve with --real-count-only",
    )
    parser.add_argument(
        "--real-count-only",
        action="store_true",
        help="real-data probe: count the national key only, no dissolve",
    )
    parser.add_argument(
        "--real-single-key",
        action="store_true",
        help="real-data probe: also dissolve the whole selection as one group (STRESS)",
    )
    parser.add_argument(
        "--include-pathological",
        action="store_true",
        help="let --confirm-large run fixtures whose dissolve alone is over budget",
    )
    parser.add_argument("--log-file", help="append to this log instead of a new one")
    parser.add_argument("--child-locate", help=argparse.SUPPRESS)
    parser.add_argument("--child-dissolve", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-input", help=argparse.SUPPRESS)
    parser.add_argument("--child-output", help=argparse.SUPPRESS)
    parser.add_argument("--child-table", help=argparse.SUPPRESS)
    parser.add_argument("--child-key-fields", help=argparse.SUPPRESS)
    args = parser.parse_args()

    arcpy.env.overwriteOutput = True
    if args.child_locate or args.child_dissolve:
        if args.log_file:
            install_log(args.workdir, args.log_file, [])
        if args.child_locate:
            return run_child_locate(
                args.child_locate, args.child_input, args.child_output
            )
        if args.child_key_fields == NO_FIELDS:
            child_fields: tuple[str, ...] = ()
        elif args.child_key_fields:
            child_fields = tuple(args.child_key_fields.split(","))
        else:
            child_fields = KEY_FIELDS
        return run_child_dissolve(
            args.child_input, args.child_output, args.child_table, child_fields
        )

    selected_for_log = args.only or ["all"]
    log_file = install_log(args.workdir, args.log_file, selected_for_log)
    print(f"log: {log_file}")
    ws = Workspace(os.path.join(args.workdir, "n1_scratch"))
    cache = fx.FixtureCache(args.workdir)
    goldens_dir = os.path.join(args.workdir, "goldens") if args.write_goldens else None
    # The Windows runner splits on commas as well as spaces, so both arrive as tokens.
    key_fields = [
        f.strip()
        for token in args.real_key_fields
        for f in token.split(",")
        if f.strip()
    ] or None
    if key_fields == ["national"]:
        key_fields = list(NATIONAL_KEY_FIELDS)

    cases: dict[str, Callable[[], None]] = {
        "case_fixture_build_method": lambda: case_fixture_build_method(ws, cache),
        "case_native_lineage_table": lambda: case_native_lineage_table(ws),
        "case_statistics_per_part_or_per_group": lambda: case_statistics_per_part_or_per_group(
            ws
        ),
        "case_aggregate_pass_through": lambda: case_aggregate_pass_through(ws),
        "case_boundary_fixtures": lambda: case_boundary_fixtures(ws, goldens_dir),
        "case_group_size_prepass_timing": lambda: case_group_size_prepass_timing(
            ws, cache
        ),
        "case_resolver_correctness_ladder": lambda: case_resolver_correctness_ladder(
            ws, cache
        ),
        "case_resolver_timing_ladder": lambda: case_resolver_timing_ladder(
            cache,
            args.workdir,
            log_file,
            args.timeout_factor,
            args.confirm_large,
            args.include_pathological,
        ),
        "case_real_data_group_sizes": lambda: case_real_data_group_sizes(
            ws,
            args.real_fc,
            key_fields,
            args.real_count_only,
            args.real_single_key,
            args.workdir,
            log_file,
            args.timeout_factor,
        ),
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
    record("raised inside cases", len(HANDLED_ERRORS))
    for entry in HANDLED_ERRORS[:20]:
        print(f"      {entry}")
    print(
        "  Every block above is an observation for the written finding, not a pass/fail."
    )
    return 1 if raised or HANDLED_ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
