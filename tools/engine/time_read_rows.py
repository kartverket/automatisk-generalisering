"""The `read_rows` timing run: what the port adds over a bare cursor, on raw sources.

What: one invocation times one dataset in one process and appends JSON lines to
`<workdir>/logs/<timestamp>_read_rows.jsonl`, opening with a header line that names the
dataset, the fields used, the pass sequence, the cap and the image. The stages, each
selectable with `--only`:

- `preflight`: an untimed walk over the source that reports the shape family, the Z and
  M flags, the EPSG code, the fields and their engine types, the row count, null and
  empty shapes, holed multipolygon members, curve and Z codes, rings and vertices per
  row, and per date field the values with a time of day or a sub-second part (W12, W17,
  W18). It is also the warm-up read.
- `copies`: the working copies the port needs, through tools: a 2D copy when the source
  carries Z or M, a copy without null shapes when it has them. Each is a copy cost,
  reported apart from the W14 figures, with the copy's EPSG code beside the source's,
  since the session's environment standard makes a tool write EPSG 25833.
- `explode`: the multipart tool bare against the port's `explode_multipart` on the same
  copy, the port's time split into its two Describe calls, its null pre-pass, the tool
  and the DeleteField of the reference (W14). When the source has holed members the
  read passes then read the exploded copy, since the codec refuses such a member.
- `reads`: the timed passes. On a feature class the token set is the chosen fields with
  the shape and the variants are `bare`, a loop over the cursor; `codec`, the bare loop
  plus `geometry_from_wkb` per row; `port`, `TableOps.read_rows`; and for polygons
  `orient`, the port plus a signed-area check of every ring, the price B32 asks about.
  The fields alone run bare only: `read_rows` carries the shape of a feature class on
  every row, so the port has no attributes-only pass there. On a table the fields alone
  are the token set and the variants are `bare` and `port`. A set runs in the order
  bare, variants, variants reversed, bare, so that a warm cache favours neither side.
- `describe`: the time per Describe call, repeated on one warm path and once on each of
  N fresh `analysis.Select` outputs, in the file geodatabase and in the memory workspace
  (W14).

Every timed pass is capped by `--cap-seconds`, writes one line per `--batch-rows` rows
with the current RSS, closes its iterator explicitly so the cursor's lock is released
before the next pass, and ends with a line whose status is `complete`, `capped`,
`interrupted`, `refused` for a port refusal by design, or `failed` for any other
exception, an adapter defect included. All five are results and the exit code is 0. A rate is also
projected to the full table and to a partition of 36,407 rows, which is the rate scaled
by that count and not a measured partition. The peak RSS is written once at the end.

The data is not open. Nothing a line carries comes from the data: names, types, counts,
timings and memory only, never a cell value, a coordinate, an extent or an object id.
The port's own errors embed cell values and row indices, so a refusal records the
exception class, the dataset name and the variant, and never the message.

How: the engine is reached as the adapter reaches it, `arcpy` imported inside the
function that uses it, under `session.guard`, and every tool through `run_tool`
(ADR-0018 AR-D23). Run inside the ArcPy image with `src` on the path:

    python tools/engine/time_read_rows.py --dataset <gdb>/<name> --workdir <dir>
        --image <digest> [--fields a,b,c] [--cap-seconds 1200] [--only preflight reads]
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import struct
import sys
import time
from collections import Counter
from collections.abc import Callable, Generator, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import TextIO

from ag.adapters.arcpy.geometry_ops import ArcpyGeometryOps
from ag.adapters.arcpy.session import ArcpySession, open_session
from ag.adapters.arcpy.support.dataset_schema import (
    DATA_TYPES,
    FIELD_TYPES,
    OID_TOKEN,
    describe,
)
from ag.adapters.arcpy.support.geometry_values import (
    WKB_TOKEN,
    geometry_from_wkb,
    is_null_shape,
)
from ag.adapters.arcpy.table_ops import ArcpyTableOps
from ag.core.errors import AgError
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.attributes import FieldType
from ag.ports.geometry import Geometry, GeometryKind, Ring
from ag.ports.table_ops import Row

PARTITION_ROWS = 36_407
"""Partition 18 of the road stage input; the projection scales a rate by this count."""

STAGES = ("preflight", "copies", "explode", "reads", "describe")
NAMESPACE = "tools.engine.time_read_rows"
SEQUENCE = "bare, variants, variants reversed, bare, per token set"
_REFERENCE = "ORIG_FID"
"""Restates `shape.py`'s private name, as the two tool names in the explode stage
restate its tool spellings, until those gain public names (proposed with this batch)."""
_SELECT_ROWS = 1_000
"""Rows in each fresh output the Describe stage creates; the clause names the OID field."""

Clock = Callable[[], float]


# --- The log ---------------------------------------------------------------------------


class Log:
    """One JSONL file, flushed after every line; names, types, counts and timings only."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def write(self, kind: str, **fields: object) -> None:
        line: dict[str, object] = {"kind": kind, "at": datetime.now().isoformat()}
        line.update(fields)
        self._stream.write(json.dumps(line, default=str) + "\n")
        self._stream.flush()


def rss_mb() -> float | None:
    """The process's current resident set in MiB from `/proc`, None where absent."""
    try:
        with open("/proc/self/statm", encoding="ascii") as statm:
            pages = int(statm.read().split()[1])
    except (OSError, IndexError, ValueError):
        return None
    return pages * os.sysconf("SC_PAGE_SIZE") / 2**20


def peak_rss_mb() -> float | None:
    """The process's peak resident set in MiB, once, at the end."""
    try:
        import resource
    except ImportError:
        return None
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**10


# --- The pass loop, pure ----------------------------------------------------------------


@dataclass(frozen=True)
class PassResult:
    """How a pass ended: the status, the rows it read and the seconds it took."""

    status: str
    rows: int
    elapsed_s: float
    error: str | None = None
    """The exception class of a refused or failed pass; never its message."""

    @property
    def rows_per_s(self) -> float | None:
        return self.rows / self.elapsed_s if self.elapsed_s > 0 and self.rows else None


def run_pass(
    rows: Iterator[object],
    *,
    cap_seconds: float,
    batch_rows: int,
    clock: Clock = time.perf_counter,
    on_batch: Callable[[int, float], None] | None = None,
) -> PassResult:
    """Consumes `rows` until they end, the cap is hit or the run is interrupted.

    `on_batch(rows, elapsed)` is called after every `batch_rows` rows; the cap is
    checked at the same points. The iterator is closed explicitly whatever happens, so a
    cursor that lives in a generator's frame releases its lock before the next pass.
    """
    count = 0
    status = "complete"
    error: str | None = None
    start = clock()
    try:
        for _ in rows:
            count += 1
            if count % batch_rows == 0:
                elapsed = clock() - start
                if on_batch is not None:
                    on_batch(count, elapsed)
                if elapsed >= cap_seconds:
                    status = "capped"
                    break
    except KeyboardInterrupt:
        status = "interrupted"
    except AgError as refusal:
        status, error = "refused", type(refusal).__name__
    except Exception as defect:
        status, error = "failed", type(defect).__name__
    finally:
        close_iterator(rows)
    return PassResult(status=status, rows=count, elapsed_s=clock() - start, error=error)


def close_iterator(rows: Iterator[object]) -> None:
    """Closes a generator; a plain iterator has nothing to close."""
    if isinstance(rows, Generator):
        rows.close()


# --- The engine, under the guard ------------------------------------------------------


@dataclass(frozen=True)
class RawDescribe:
    """What Describe says about a source, before any port rule is applied."""

    data_type: str
    shape_type: str
    has_z: bool
    has_m: bool
    epsg: int
    oid_field: str
    fields: tuple[tuple[str, str], ...]
    """Every field as (name, engine type), the engine's own fields left out."""

    @property
    def is_feature_class(self) -> bool:
        return DATA_TYPES.get(self.data_type) is DataType.FEATURE_CLASS


def raw_describe(session: ArcpySession, path: str) -> RawDescribe:
    """Describe without the port's refusals, so a Z source or one without an EPSG code
    is reported rather than refused."""
    with session.guard("Describe"):
        import arcpy

        described = arcpy.Describe(path)
        feature_class = DATA_TYPES.get(described.dataType) is DataType.FEATURE_CLASS
        engine_fields = {described.OIDFieldName}
        if feature_class:
            engine_fields |= {
                described.shapeFieldName,
                described.lengthFieldName,
                described.areaFieldName,
            }
        return RawDescribe(
            data_type=described.dataType,
            shape_type=described.shapeType if feature_class else "",
            has_z=described.hasZ if feature_class else False,
            has_m=described.hasM if feature_class else False,
            epsg=int(described.spatialReference.factoryCode) if feature_class else 0,
            oid_field=described.OIDFieldName,
            fields=tuple(
                (f.name, f.type)
                for f in described.fields
                if f.name not in engine_fields
            ),
        )


def bare_rows(
    session: ArcpySession, *, path: str, tokens: Sequence[str]
) -> Generator[tuple[object, ...], None, None]:
    """One search cursor's rows as the engine yields them, no per-row copy."""
    with session.guard("SearchCursor"):
        import arcpy

        with arcpy.da.SearchCursor(path, tokens) as cursor:
            yield from cursor


def delete_null_shapes(session: ArcpySession, *, path: str) -> int:
    """Deletes every row of `path` whose shape is null or empty; returns the count."""
    deleted = 0
    with session.guard("UpdateCursor"):
        import arcpy

        with arcpy.da.UpdateCursor(path, (OID_TOKEN, WKB_TOKEN)) as cursor:
            for row in cursor:
                if is_null_shape(row[1]):
                    cursor.deleteRow()
                    deleted += 1
    return deleted


# --- The WKB walk -----------------------------------------------------------------------

_PLANAR = frozenset(range(1, 7))
_CURVES = frozenset({8, 9, 10, 11, 12, 13})
_Z_FLAG, _M_FLAG, _SRID_FLAG = 0x40000000, 0x20000000, 0x80000000


@dataclass(frozen=True)
class ShapeStats:
    """One shape's class and, for a planar simple feature, its rings and vertices."""

    kind: str
    """`null`, `empty`, `planar`, `z`, `m`, `zm`, `curve` or `other`."""
    rings: int = 0
    vertices: int = 0
    holed_members: int = 0


def shape_stats(value: object) -> ShapeStats:
    """Reads a WKB value's type class and walks a planar simple feature for its counts.

    Z, M and curve codes are classified from the header, in both the ISO and the
    extended spelling, and not walked: a 3D source is counted here and walked once its
    2D copy exists.
    """
    if value is None:
        return ShapeStats("null")
    if isinstance(value, memoryview):
        data = value.tobytes()
    elif isinstance(value, bytes | bytearray):
        data = bytes(value)
    else:
        return ShapeStats("other")
    if len(data) < 5:
        return ShapeStats("other")
    order = "<" if data[0] == 1 else ">"
    code = _Walk(data).uint(order, 1)
    plain = code & ~(_Z_FLAG | _M_FLAG | _SRID_FLAG)
    iso = plain // 1000
    has_z = bool(code & _Z_FLAG) or iso in (1, 3)
    has_m = bool(code & _M_FLAG) or iso in (2, 3)
    base = plain % 1000
    if has_z or has_m:
        return ShapeStats("zm" if has_z and has_m else "z" if has_z else "m")
    if base in _CURVES:
        return ShapeStats("curve")
    if base not in _PLANAR:
        return ShapeStats("other")
    rings, vertices, holed, _ = _Walk(data).geometry(base, order, 5)
    if vertices == 0:
        return ShapeStats("empty")
    return ShapeStats("planar", rings=rings, vertices=vertices, holed_members=holed)


@dataclass(frozen=True)
class _Walk:
    """Counts rings, vertices and holed multipolygon members in one planar WKB value.

    Independent of the adapter's codec on purpose: the walk classifies the codes the codec
    refuses, Z, M and curves, and must not share its refusals.
    """

    data: bytes

    def uint(self, order: str, offset: int) -> int:
        (value,) = struct.unpack_from(f"{order}I", self.data, offset)
        return int(value)

    def geometry(self, code: int, order: str, offset: int) -> tuple[int, int, int, int]:
        """(rings, vertices, holed members, next offset) of the geometry of `code`
        whose body starts at `offset`."""
        if code == 1:
            x, y = struct.unpack_from(f"{order}dd", self.data, offset)
            empty = x != x or y != y
            return (0 if empty else 1), (0 if empty else 1), 0, offset + 16
        if code == 2:
            count = self.uint(order, offset)
            return 1, count, 0, offset + 4 + 16 * count
        if code == 3:
            count = self.uint(order, offset)
            offset += 4
            vertices = 0
            for _ in range(count):
                points = self.uint(order, offset)
                vertices += points
                offset += 4 + 16 * points
            return count, vertices, 0, offset
        members = self.uint(order, offset)
        offset += 4
        rings = vertices = holed = 0
        for _ in range(members):
            member_order = "<" if self.data[offset] == 1 else ">"
            member_code = self.uint(member_order, offset + 1) % 1000
            r, v, _, offset = self.geometry(member_code, member_order, offset + 5)
            rings += r
            vertices += v
            if code == 6 and r > 1:
                holed += 1
        return rings, vertices, holed, offset


@dataclass
class WalkStats:
    """What one walk over a dataset counted."""

    rows: int = 0
    shapes: Counter[str] = field(default_factory=lambda: Counter[str]())
    holed_members: int = 0
    rows_with_holed_members: int = 0
    rings: Counter[int] = field(default_factory=lambda: Counter[int]())
    vertices: Counter[int] = field(default_factory=lambda: Counter[int]())
    date_non_null: Counter[str] = field(default_factory=lambda: Counter[str]())
    date_time_of_day: Counter[str] = field(default_factory=lambda: Counter[str]())
    date_sub_second: Counter[str] = field(default_factory=lambda: Counter[str]())

    def add(self, shape: ShapeStats) -> None:
        self.shapes[shape.kind] += 1
        if shape.kind == "planar":
            self.rings[shape.rings] += 1
            self.vertices[shape.vertices] += 1
            if shape.holed_members:
                self.holed_members += shape.holed_members
                self.rows_with_holed_members += 1

    def add_date(self, name: str, value: object) -> None:
        if isinstance(value, datetime):
            self.date_non_null[name] += 1
            if value.hour or value.minute or value.second:
                self.date_time_of_day[name] += 1
            if value.microsecond:
                self.date_sub_second[name] += 1

    def report(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "shapes": dict(self.shapes),
            "holed_members": self.holed_members,
            "rows_with_holed_members": self.rows_with_holed_members,
            "rings_per_row": summary(self.rings),
            "vertices_per_row": summary(self.vertices),
            "date_fields": {
                name: {
                    "non_null": self.date_non_null[name],
                    "with_time_of_day": self.date_time_of_day[name],
                    "with_sub_second": self.date_sub_second[name],
                }
                for name in sorted(self.date_non_null)
            },
        }


def summary(histogram: Counter[int]) -> dict[str, float | int | None]:
    """Mean, p50, p95 and max of a histogram of counts."""
    total = sum(histogram.values())
    if total == 0:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "max": None}
    weighted = sum(value * count for value, count in histogram.items())
    return {
        "n": total,
        "mean": round(weighted / total, 2),
        "p50": percentile(histogram, 0.50),
        "p95": percentile(histogram, 0.95),
        "max": max(histogram),
    }


def percentile(histogram: Counter[int], share: float) -> int:
    """The smallest value at or below which `share` of the counts lie."""
    target = share * sum(histogram.values())
    seen = 0
    for value in sorted(histogram):
        seen += histogram[value]
        if seen >= target:
            return value
    return max(histogram)


def walk(
    session: ArcpySession,
    *,
    path: str,
    date_fields: Sequence[str],
    is_feature_class: bool,
) -> WalkStats:
    """One untimed pass over `path` counting shapes and date parts; the warm-up read."""
    tokens: tuple[str, ...] = (OID_TOKEN, *date_fields)
    if is_feature_class:
        tokens = (OID_TOKEN, WKB_TOKEN, *date_fields)
    first_date = 2 if is_feature_class else 1
    stats = WalkStats()
    rows = bare_rows(session, path=path, tokens=tokens)
    try:
        for row in rows:
            stats.rows += 1
            if is_feature_class:
                stats.add(shape_stats(row[1]))
            for name, value in zip(date_fields, row[first_date:], strict=True):
                stats.add_date(name, value)
    finally:
        rows.close()
    return stats


# --- The variants -----------------------------------------------------------------------


def codec_rows(
    session: ArcpySession, *, path: str, tokens: Sequence[str], crs: str
) -> Iterator[object]:
    """The bare loop plus the codec on the shape cell, which is the last token."""
    rows = bare_rows(session, path=path, tokens=tokens)
    try:
        for row in rows:
            yield geometry_from_wkb(row[-1], crs=crs, where=path)
    finally:
        rows.close()


def port_rows(
    session: ArcpySession, *, handle: ScratchHandle, fields: Sequence[str]
) -> Iterator[Row]:
    """`TableOps.read_rows` as a caller consumes it."""
    return iter(
        ArcpyTableOps(session=session).read_rows(input=handle, fields=tuple(fields))
    )


def oriented_rows(rows: Iterator[Row]) -> Iterator[int]:
    """The port's rows plus the per-ring signed-area check a canonical `Geometry` would
    run on construction; yields the rings each row would reverse, for the count."""
    try:
        for row in rows:
            yield rings_to_reverse(row.geometry)
    finally:
        close_iterator(rows)


def rings_to_reverse(geometry: Geometry | None) -> int:
    """How many rings of a polygon value a canonical orientation would reverse: the
    exterior and every member counter-clockwise, every hole clockwise."""
    if geometry is None:
        return 0
    if geometry.kind is GeometryKind.MULTIPOLYGON:
        return sum(signed_area(member) < 0 for member in geometry.parts)
    if geometry.kind is GeometryKind.POLYGON:
        exterior, *holes = geometry.parts
        return (signed_area(exterior) < 0) + sum(signed_area(h) > 0 for h in holes)
    return 0


def signed_area(ring: Ring) -> float:
    """Twice the shoelace area: positive counter-clockwise, negative clockwise."""
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))


# --- The run ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Options:
    dataset: str
    workdir: Path
    cap_seconds: float
    batch_rows: int
    fields: tuple[str, ...] | None
    select_count: int
    describe_repeats: int
    image: str
    stages: frozenset[str]


@dataclass
class Run:
    """One dataset, one process: the session, the log and the working copies."""

    options: Options
    session: ArcpySession
    log: Log
    name: str
    workspace: str
    raw: RawDescribe
    read_path: str
    """The copy every read pass reads; the source until a copy replaces it."""
    walked: WalkStats = field(default_factory=WalkStats)
    """The last walk, of the source and then of the read copy."""
    interrupted: bool = False

    @property
    def declared(self) -> tuple[str, ...]:
        return tuple(name for name, kind in self.raw.fields if kind in FIELD_TYPES)

    @property
    def date_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, kind in self.raw.fields
            if FIELD_TYPES.get(kind) is FieldType.DATE
        )

    @property
    def fields(self) -> tuple[str, ...]:
        chosen = self.options.fields
        return self.declared[:3] if chosen is None else chosen

    @property
    def crs(self) -> str:
        return f"EPSG:{self.raw.epsg}"

    def handle(self, path: str) -> ScratchHandle:
        workspace, _, name = path.rpartition("/")
        data_type = (
            DataType.FEATURE_CLASS if self.raw.is_feature_class else DataType.TABLE
        )
        return ScratchHandle(
            name=name, data_type=data_type, namespace=NAMESPACE
        ).materialize(f"{workspace}/{name}")

    stage: str = ""
    """The stage running, for the start line written before every tool call."""

    def timed_tool(self, name: str, /, **arguments: object) -> float:
        """Runs a tool and returns its seconds; a `start` line goes out first, so a run
        killed during a long tool call shows where it stopped."""
        inputs = {
            key: value
            for key, value in arguments.items()
            if key in ("in_features", "inputs", "in_table", "template")
        }
        self.log.write(
            "start", dataset=self.name, stage=self.stage, tool=name, **inputs
        )
        start = time.perf_counter()
        self.session.run_tool(name, **arguments)
        return time.perf_counter() - start

    def timed_describe(self, path: str) -> float:
        start = time.perf_counter()
        describe(self.session, path)
        return time.perf_counter() - start

    def walk_into(self, path: str, *, date_fields: Sequence[str]) -> None:
        start = time.perf_counter()
        self.walked = walk(
            self.session,
            path=path,
            date_fields=date_fields,
            is_feature_class=self.raw.is_feature_class,
        )
        self.log.write(
            "walk",
            dataset=self.name,
            path=path,
            elapsed_s=round(time.perf_counter() - start, 3),
            **self.walked.report(),
        )

    # -- stages --

    def preflight(self) -> None:
        raw = self.raw
        self.log.write(
            "preflight",
            dataset=self.name,
            data_type=raw.data_type,
            shape_type=raw.shape_type,
            has_z=raw.has_z,
            has_m=raw.has_m,
            epsg=raw.epsg,
            oid_field=raw.oid_field,
            fields=[{"name": n, "type": t} for n, t in raw.fields],
            declared=list(self.declared),
            unrepresentable=[n for n, t in raw.fields if t not in FIELD_TYPES],
            read_fields=list(self.fields),
        )
        self.walk_into(self.options.dataset, date_fields=self.date_fields)

    def copies(self) -> None:
        if not self.raw.is_feature_class:
            return
        try:
            self.make_copies()
        except Exception as error:
            self.log.write("copy", dataset=self.name, **failure(error))

    def make_copies(self) -> None:
        source = self.options.dataset
        if self.raw.has_z or self.raw.has_m:
            target = f"{self.workspace}/{self.name}_2d"
            seconds = self.timed_tool(
                "management.CreateFeatureclass",
                out_path=self.workspace,
                out_name=f"{self.name}_2d",
                geometry_type=self.raw.shape_type.upper(),
                template=source,
                has_m="DISABLED",
                has_z="DISABLED",
                spatial_reference=source,
            )
            seconds += self.timed_tool(
                "management.Append",
                inputs=source,
                target=target,
                schema_type="NO_TEST",
            )
            self.copy_line("2d", source, target, seconds)
            source = target
        nulls = self.walked.shapes["null"] + self.walked.shapes["empty"]
        if nulls:
            target = f"{self.workspace}/{self.name}_nonnull"
            seconds = self.timed_tool(
                "management.CopyFeatures", in_features=source, out_feature_class=target
            )
            start = time.perf_counter()
            deleted = delete_null_shapes(self.session, path=target)
            seconds += time.perf_counter() - start
            self.copy_line("nonnull", source, target, seconds, deleted=deleted)
            source = target
        self.read_path = source

    def copy_line(
        self, which: str, source: str, target: str, seconds: float, **extra: object
    ) -> None:
        copy = raw_describe(self.session, target)
        self.log.write(
            "copy",
            dataset=self.name,
            copy=which,
            source=source,
            target=target,
            elapsed_s=round(seconds, 3),
            source_epsg=self.raw.epsg,
            copy_epsg=copy.epsg,
            copy_has_z=copy.has_z,
            copy_has_m=copy.has_m,
            **extra,
        )

    def explode(self) -> None:
        if not self.raw.is_feature_class:
            return
        source = self.read_path
        out_bare = f"{self.workspace}/{self.name}_exploded_bare"
        out_port = f"{self.workspace}/{self.name}_exploded_port"
        line: dict[str, object] = {"dataset": self.name, "input": source}
        try:
            line["tool_s"] = round(
                self.timed_tool(
                    "management.MultipartToSinglepart",
                    in_features=source,
                    out_feature_class=out_bare,
                ),
                3,
            )
            line["describe_after_s"] = round(self.timed_describe(out_bare), 3)
            line["delete_field_s"] = round(
                self.timed_tool(
                    "management.DeleteField", in_table=out_bare, drop_field=_REFERENCE
                ),
                3,
            )
            line["describe_before_s"] = round(self.timed_describe(source), 3)
            start = time.perf_counter()
            line["prepass_nulls"] = self.prepass(source)
            line["prepass_s"] = round(time.perf_counter() - start, 3)
        except Exception as error:
            self.log.write("explode", **line, **failure(error))
            return
        start = time.perf_counter()
        try:
            ArcpyGeometryOps(session=self.session).explode_multipart(
                input=self.handle(source), output=self.handle(out_port)
            )
            line["port_total_s"] = round(time.perf_counter() - start, 3)
            line["port_status"] = "complete"
        except Exception as error:
            port = failure(error)
            line["port_status"] = port["status"]
            line["port_error"] = port["error"]
        self.log.write("explode", **line, status="complete")
        if self.walked.rows_with_holed_members:
            self.read_path = out_bare

    def prepass(self, path: str) -> int:
        """The null pre-pass as `explode_multipart` runs it, counted."""
        nulls = 0
        rows = bare_rows(self.session, path=path, tokens=(OID_TOKEN, WKB_TOKEN))
        try:
            for row in rows:
                nulls += is_null_shape(row[1])
        finally:
            rows.close()
        return nulls

    def reads(self) -> None:
        if self.read_path != self.options.dataset or self.walked.rows == 0:
            self.walk_into(self.read_path, date_fields=())
        fields = self.fields
        if not self.raw.is_feature_class:
            self.token_set("attributes", fields, variants=("port",))
            return
        self.token_set("attributes", fields, variants=())
        variants = ("codec", "port")
        if self.raw.shape_type == "Polygon":  # the engine's string, W23, until B31
            variants = ("codec", "port", "orient")
        self.token_set("geometry", fields, variants=variants)

    def token_set(
        self, name: str, fields: Sequence[str], *, variants: Sequence[str]
    ) -> None:
        """bare, the variants, the variants reversed, bare; bare alone when none."""
        sequence = ("bare", *variants, *reversed(variants), "bare")
        if not variants:
            sequence = ("bare",)
        for position, variant in enumerate(sequence):
            if self.interrupted:
                return
            self.timed_pass(name, variant, fields, position=position)

    def timed_pass(
        self, token_set: str, variant: str, fields: Sequence[str], *, position: int
    ) -> None:
        path = self.read_path
        tokens: tuple[str, ...] = tuple(fields)
        if token_set == "geometry":
            tokens = (*fields, WKB_TOKEN)
        if not tokens:
            tokens = (OID_TOKEN,)
        line: dict[str, object] = {
            "dataset": self.name,
            "path": path,
            "token_set": token_set,
            "variant": variant,
            "position": position,
            "tokens": list(tokens),
        }

        def batch(count: int, elapsed: float) -> None:
            self.log.write(
                "batch",
                **line,
                rows=count,
                elapsed_s=round(elapsed, 3),
                rows_per_s=round(count / elapsed, 1) if elapsed else None,
                rss_mb=rounded(rss_mb()),
            )

        try:
            rows = self.variant_rows(variant, path=path, tokens=tokens, fields=fields)
        except Exception as error:
            self.log.write("end", **line, **failure(error))
            return
        result = run_pass(
            rows,
            cap_seconds=self.options.cap_seconds,
            batch_rows=self.options.batch_rows,
            on_batch=batch,
        )
        rate = result.rows_per_s
        total = self.walked.rows
        self.log.write(
            "end",
            **line,
            status=result.status,
            error=result.error,
            rows=result.rows,
            elapsed_s=round(result.elapsed_s, 3),
            rows_per_s=rounded(rate, 1),
            projected_full_s=rounded(total / rate if rate else None),
            projected_partition_s=rounded(PARTITION_ROWS / rate if rate else None),
            rss_mb=rounded(rss_mb()),
        )
        if result.status == "interrupted":
            self.interrupted = True

    def variant_rows(
        self, variant: str, *, path: str, tokens: Sequence[str], fields: Sequence[str]
    ) -> Iterator[object]:
        if variant == "bare":
            return bare_rows(self.session, path=path, tokens=tokens)
        if variant == "codec":
            return codec_rows(self.session, path=path, tokens=tokens, crs=self.crs)
        rows = port_rows(self.session, handle=self.handle(path), fields=fields)
        if variant == "port":
            return rows
        if variant == "orient":
            return oriented_rows(rows)
        raise ValueError(f"{variant!r} is not a variant.")

    def describe_stage(self) -> None:
        path = self.read_path
        line: dict[str, object] = {"dataset": self.name, "path": path}
        try:
            line["file_gdb_repeat"] = self.describe_repeat(path)
            outputs, selects = self.fresh_outputs(self.workspace, "gdb")
            line["file_gdb_select"] = selects
            line["file_gdb_fresh"] = self.describe_fresh(outputs)
            outputs, selects = self.fresh_outputs("memory", "memory")
            line["memory_select"] = selects
            line["memory_fresh"] = self.describe_fresh(outputs)
            if outputs:
                line["memory_repeat"] = self.describe_repeat(outputs[0])
        except Exception as error:
            self.log.write("describe", **line, **failure(error))
            return
        self.log.write("describe", **line, status="complete")

    def describe_repeat(self, path: str) -> dict[str, float | int | None]:
        repeats = self.options.describe_repeats
        return timing_summary([self.timed_describe(path) for _ in range(repeats)])

    def fresh_outputs(
        self, workspace: str, label: str
    ) -> tuple[list[str], dict[str, float | int | None]]:
        """N small outputs of `analysis.Select` in `workspace`, and the Select times."""
        outputs: list[str] = []
        times: list[float] = []
        clause = f"{self.raw.oid_field} <= {_SELECT_ROWS}"
        for index in range(self.options.select_count):
            target = f"{workspace}/{self.name}_select_{label}_{index}"
            times.append(
                self.timed_tool(
                    "analysis.Select",
                    in_features=self.read_path,
                    out_feature_class=target,
                    where_clause=clause,
                )
            )
            outputs.append(target)
        return outputs, timing_summary(times)

    def describe_fresh(self, outputs: Sequence[str]) -> dict[str, float | int | None]:
        return timing_summary([self.timed_describe(path) for path in outputs])


def failure(error: Exception) -> dict[str, object]:
    """The status and class of an exception, never its message: `refused` for a port
    refusal by design, `failed` for anything else."""
    status = "refused" if isinstance(error, AgError) else "failed"
    return {"status": status, "error": type(error).__name__}


def rounded(value: float | None, digits: int = 3) -> float | None:
    return None if value is None else round(value, digits)


def timing_summary(times: Sequence[float]) -> dict[str, float | int | None]:
    if not times:
        return {"n": 0, "min_s": None, "median_s": None, "mean_s": None, "max_s": None}
    return {
        "n": len(times),
        "min_s": round(min(times), 4),
        "median_s": round(statistics.median(times), 4),
        "mean_s": round(statistics.fmean(times), 4),
        "max_s": round(max(times), 4),
    }


def workspace_for(session: ArcpySession, workdir: Path) -> str:
    """The working file geodatabase under `workdir`, created once."""
    path = workdir / "timing.gdb"
    if not path.is_dir():
        session.run_tool(
            "management.CreateFileGDB", out_folder_path=str(workdir), out_name="timing"
        )
    return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse(argv)
    logs = options.workdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = options.dataset.replace("\\", "/").rpartition("/")[2]
    interrupt_on_sigterm()
    with open(logs / f"{stamp}_read_rows.jsonl", "a", encoding="utf-8") as stream:
        log = Log(stream)
        session = open_session()
        run = Run(
            options=options,
            session=session,
            log=log,
            name=name,
            workspace=workspace_for(session, options.workdir),
            raw=raw_describe(session, options.dataset),
            read_path=options.dataset,
        )
        log.write(
            "header",
            dataset=name,
            path=options.dataset,
            image=options.image,
            python=sys.version.split()[0],
            cap_seconds=options.cap_seconds,
            batch_rows=options.batch_rows,
            fields=list(run.fields),
            stages=[stage for stage in STAGES if stage in options.stages],
            sequence=SEQUENCE,
            partition_rows=PARTITION_ROWS,
            environment=str(session.environment),
        )
        stages: dict[str, Callable[[], None]] = {
            "preflight": run.preflight,
            "copies": run.copies,
            "explode": run.explode,
            "reads": run.reads,
            "describe": run.describe_stage,
        }
        try:
            for stage in STAGES:
                if stage in options.stages and not run.interrupted:
                    run.stage = stage
                    stages[stage]()
        except KeyboardInterrupt:
            log.write("end", dataset=name, status="interrupted", stage="outside a pass")
        finally:
            log.write("peak", dataset=name, rss_peak_mb=rounded(peak_rss_mb()))
    return 0


def interrupt_on_sigterm() -> None:
    """`docker stop` sends SIGTERM; it ends the pass as Ctrl-C does, with its line."""

    def raise_interrupt(signum: int, frame: FrameType | None) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, raise_interrupt)


def parse(argv: Sequence[str] | None) -> Options:
    parser = argparse.ArgumentParser(
        prog="python tools/engine/time_read_rows.py",
        description="Times TableOps.read_rows against a bare cursor on one dataset.",
    )
    parser.add_argument("--dataset", required=True, help="<gdb>/<name>, on the copy")
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--cap-seconds", type=float, default=1_200.0)
    parser.add_argument("--batch-rows", type=int, default=50_000)
    parser.add_argument(
        "--fields", default=None, help="comma-separated; default: first three declared"
    )
    parser.add_argument("--select-count", type=int, default=100)
    parser.add_argument("--describe-repeats", type=int, default=300)
    parser.add_argument("--image", default="NOT GIVEN: pass --image <digest>")
    parser.add_argument("--only", nargs="+", choices=STAGES, default=list(STAGES))
    args = parser.parse_args(argv)
    chosen = None if args.fields is None else str(args.fields)
    return Options(
        dataset=str(args.dataset),
        workdir=Path(str(args.workdir)),
        cap_seconds=float(args.cap_seconds),
        batch_rows=int(args.batch_rows),
        fields=None if chosen is None else tuple(chosen.split(",")),
        select_count=int(args.select_count),
        describe_repeats=int(args.describe_repeats),
        image=str(args.image),
        stages=frozenset(str(stage) for stage in args.only),
    )


if __name__ == "__main__":
    sys.exit(main())
