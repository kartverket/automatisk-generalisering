# Slice 1b evidence: the `read_rows` timing run, second pull request, batch 1

**Status:** PREPARED, 2026-11-06. The tool, its root and the run commands are in place; no
engine result is recorded yet. Batch 1 of the second pull request of slice 1b: the timing
run (`tools/engine/time_read_rows.py`), W14, the by-hand items W12, W17 and W18, and their
records. Batch 2, B31 and B32, is a later session on the same branch.

This file is written in WSL without ArcPy; every engine result below is run by the
architect in the project's image, `ghcr.io/kartverket/arcpy-linux:12.1`, and pasted, and
nothing here claims an engine result it has not been shown.

**The data is not open.** The logs, the probe output and this file carry aggregates and
schema only: counts, rates, timings, vertex statistics, dataset and field names, field
types, shape types, EPSG codes and the Z and M flags. Never a cell value, a coordinate, an
extent or an object id. The tool's docstring states the rule and its refusal lines record
an exception class, never a message, because the port's own errors embed cell values.

## What this batch adds

- `tools/engine/`, the third root under the constrained ArcPy stub: its execution
  environment in `pyproject.toml`, placed before the root one because pyright applies the
  first environment whose root contains the file (probed on a scratch copy: appended after
  the root entry, a function-local `import arcpy` has 5 strict errors; before it, 0); its
  scope `tools-engine` in `tools/scan_sources.py` with the `arcpy-session-only` and
  `import-by-string` rules and no allowlist; and break-once case S9 in
  `tools/break_once/cases/arcpy_session.py`, a reference outside a guard in that root.
- `tools/engine/time_read_rows.py`, the tool, and `tests/unit/tools/test_time_read_rows.py`
  for its pure parts: the pass loop closes its iterator on completion, cap and interrupt;
  the WKB walk classifies null, empty, planar, Z, M, ZM, curve and unknown codes in the
  ISO and the extended spelling; the orientation count names the rings a canonical value
  would reverse.
- The stub gains `shapeType` on Describe, for the preflight and for B31.
- `DATA_TYPES` in `dataset_schema.py` is public, so the tool reads the engine's data type
  through the adapter's own map instead of restating the string.

### Proposed, not applied: public names in `shape.py`

The tool restates three spellings of `shape.py`: the reference field `ORIG_FID`, the
multipart tool and the DeleteField tool. The project rule is one constant or an object
reference, and the point of the measurement is that it times the adapter's own method, so
the tool should import them. Giving them public names changes two break-once needles in
`tools/break_once/cases/arcpy_adapter.py`, an explicit-request file, so this waits on the
architect naming it:

- `shape.py`: `_EXPLODE` becomes `EXPLODE_TOOL`, `_REFERENCE` becomes `REFERENCE_FIELD`,
  and `DELETE_FIELD_TOOL = "management.DeleteField"` joins them; the call at the end of
  `explode_multipart` uses it.
- `arcpy_adapter.py`: X6's needle `if _REFERENCE in before.all_fields:` becomes
  `if REFERENCE_FIELD in before.all_fields:`; the needle holding
  `"management.DeleteField", in_table=target, drop_field=reference` becomes
  `DELETE_FIELD_TOOL, in_table=target, drop_field=reference`.
- The tool imports the three and drops its own `_REFERENCE`.
- `docs/refactor/temp/w12_curve_probe.py`, the by-hand half of W12 that the sources
  cannot answer: whether `SHAPE@WKB` densifies a true curve or exports a curve code.

### A finding the tool's design surfaced

`TableOps.read_rows` carries the shape of a feature class on every row (`row_io.py`), so
the port has no attributes-only pass on a feature class: the plan's "attributes only"
pass exists for the bare cursor alone, and the port's figure is always with geometry. A
caller that needs attributes alone, as a lineage-aware pipe over a parents mapping might,
pays the codec on every row. Whether `read_rows` gets a way to leave the shape out is a
port question for the architect, not something this batch decides.

## The run

### The sources, as the architect listed them on the volume, 2026-11-06

Run by the architect against `gis_files` mounted read-only, with Describe and GetCount
from the image's own Python; dataset names, shape types and counts only. The three sets of
this run, and the geodatabases that hold them:

| geodatabase | size | dataset | shape type | rows |
|---|---|---|---|---|
| `raw_data/building.gdb` | 103 MB | `BygningsPunkt_N10` | Point | 1,167,072 |
| `raw_data/area.gdb` | 15.6 GB | `ArealdekkeFlate_N10` | Polygon | 3,044,617 |
| `raw_data/fkb_water.gdb` | 8.9 GB | `fkb_vann_grense` | Polyline | 14,695,279 |

The listing read the raw data on the read-only mount without error, so a file geodatabase
opens for reading there; the copies below are still made, since the rule is that the raw
data is never opened by the tool. `area.gdb` also holds `ArealdekkeFlate` with 14.7M
polygons, not used here.

### Volumes and copies, once

The sources sit on the named volume `gis_files`, mounted read-only; the working copies, the
tool outputs and the logs go on a second named volume. The copies are made with `cp -a`
from inside the image so the raw data is never opened for writing.

```
docker volume create ag_timing
docker run --rm -v gis_files:/data/ag_inputs:ro -v ag_timing:/timing \
  ghcr.io/kartverket/arcpy-linux:12.1 \
  bash -c 'mkdir -p /timing/copies /timing/run &&
           cp -a /data/ag_inputs/raw_data/building.gdb /timing/copies/ &&
           cp -a /data/ag_inputs/raw_data/area.gdb /timing/copies/ &&
           cp -a /data/ag_inputs/raw_data/fkb_water.gdb /timing/copies/ &&
           du -sh /timing/copies/*'
```

The copies take about 25 GB; the working outputs come on top (a 2D copy of the lines, the
exploded polygons, the Select outputs), so the volume needs room for roughly twice that.
`cp -a` copies whole geodatabases because a feature class is spread over numbered files
inside one.

### The invocations, one process per dataset

The tool needs the engine and `src` only, no dev tools. The image digest is recorded in
the header line through `--image`. Run detached so that a closed terminal does not end
the run; `docker stop` sends SIGTERM, which the tool turns into an `interrupted` line.

```
IMAGE=ghcr.io/kartverket/arcpy-linux:12.1
DIGEST=$(docker inspect --format '{{index .RepoDigests 0}}' "$IMAGE")
run() {  # run <name> <dataset> [tool arguments...]
  docker run -d --name "ag_timing_$1" -v "$PWD":/work:ro -w /work -v ag_timing:/timing \
    -e PYTHONPATH=/work/src -e PYTHONDONTWRITEBYTECODE=1 "$IMAGE" \
    python tools/engine/time_read_rows.py --dataset "$2" --workdir /timing/run \
      --cap-seconds 600 --image "$DIGEST" "${@:3}"
}
run points   /timing/copies/building.gdb/BygningsPunkt_N10  --only preflight copies reads describe
run polygons /timing/copies/area.gdb/ArealdekkeFlate_N10
run lines    /timing/copies/fkb_water.gdb/fkb_vann_grense    --only preflight copies reads describe
docker wait ag_timing_points         # the tool prints nothing; the JSONL is the output
docker logs ag_timing_points         # a traceback here is a defect to report, not a result
docker stop -t 60 ag_timing_lines    # to end a run early: SIGTERM, 60 s for the line
```

A `start` line goes out before every tool call, so a run killed during a long tool call,
the Append of 14.7M rows for one, shows in the log where it stopped. Every pass and stage
ends with a status: `refused` is a port refusal by design, `failed` any other exception,
both recorded as the class alone.

The three run one after another, not at once, so that each reads with the disk to itself.
`--only` leaves the explode stage to the polygons, where W14's tool figure is wanted and
where holed members are expected; `--fields` names three declared fields where the first
three the preflight lists are not the ones wanted.

### Copy-out, after the architect has read the logs

```
mkdir -p docs/refactor/temp/logs
docker run --rm -v ag_timing:/timing:ro -v "$PWD/docs/refactor/temp/logs":/out \
  ghcr.io/kartverket/arcpy-linux:12.1 bash -c 'cp /timing/run/logs/*.jsonl /out/'
```

### The wall-clock budget, stated before the run

Per dataset, with the cap at 600 s: the preflight walk, untimed, one full pass; on a
feature class the fields alone run bare once and the geometry set runs bare, codec, port,
port, codec, bare, six capped passes, plus orient twice on the polygons; so at most 7 or 9
capped passes, 70 or 90 minutes if every pass hits the cap, which a 1.2M-row set will not.
On top: the copies, a 2D copy when a source carries Z (the Append of 14.7M rows is the
unknown of the lines run), a copy without null shapes when a source has them; the explode
of the polygons, bare and through the port, each a tool over 3.0M rows; and the Describe
stage, 300 repeats and 100 fresh outputs in each workspace. A capped pass gives a rate; the
cap can drop to 300 s on the lines after the first two runs show stable rates.

### What the run can refuse, by design

- Z or M: `describe` refuses before any row (ADR-0019 PC-D27); the tool reads the 2D copy
  instead, made through `CreateFeatureclass` with `has_z="DISABLED"` and `Append` with
  `schema_type="NO_TEST"`. That the engine drops Z this way is W22, an expectation until
  the run shows it; if it does not, the route through the session's environment is a
  proposal to the architect, not a change this batch makes.
- A holed multipolygon member: the codec refuses it mid-stream (B30); the read passes then
  read the exploded copy, and the bare variant reads the same copy.
- A null or empty shape: `explode_multipart` refuses the input; the explode stage runs on
  the copy without them, with the count recorded.
- A spatial reference without an EPSG code: `describe` refuses; recorded as a refusal.
- A source in another CRS than EPSG 25833: a tool output is reprojected by the session's
  environment standard; the copy line records the source's code beside the copy's, and a
  difference is reported, not fixed.

## Results

To be pasted per dataset from the JSONL: the header, the preflight and walk lines, the
copy lines, the explode line, the end line of every pass, the describe line and the peak.

### BygningsPunkt_N10 (points)

Pending.

### ArealdekkeFlate_N10 (polygons)

Pending.

### fkb_vann_grense (lines)

Pending.

### The W12 probe

Pending: `python docs/refactor/temp/w12_curve_probe.py` in the image, with `src` and the
root on the path.

## What the numbers decide

- The rate per row and the 36,407-row projection per dataset, with the vertex figures
  beside each. The projection is partition 18 of the road stage input scaled from a rate;
  this run does not read that partition.
- A15.7's minute is "time added over the bare tool": the port's overhead is the port pass
  against the bare pass of the same process, not the port's time alone. For
  `explode_multipart`, the overhead is the sum of the parts the explode line measures one
  by one, Describe before, the pre-pass, Describe after and DeleteField; the port's total
  less the bare tool's time is the cross-check, since those are two single runs of a tool
  over 3.0M rows with the bare one first, and a warm cache and the tool's run-to-run
  spread fall into that difference.
- Whether slice 3's lineage-aware pipe can stream `Row` values or needs a columnar read.
- The price of the attributes-only question: the attributes set bare against the geometry
  set bare gives what the shape costs the cursor, and codec against port what the codec
  and the rest of `_rows` cost; together they state, at partition size, what an
  attributes-only port read would save, so the question reaches the architect priced.
- B32's price: the `orient` variant against the `port` variant on the polygons, at
  partition size, against A15.7.
- Describe against the agreed band: 0.1 to 0.5 s per call over hundreds to thousands of
  calls per stage is acceptable, 1 to 5 s is not; the lever is a narrower read, not a cache.

## W-items

| item | where | status |
|---|---|---|
| W12 curves | preflight `shapes.curve` per source; the probe for densification | pending |
| W14 timing | the reads, explode and describe stages | pending |
| W17 hasZ/hasM of the sources | preflight line per source | pending |
| W18 date fields of the sources | preflight `date_fields` per source | pending |
| W22 (new) the 2D copy through CreateFeatureclass and Append drops Z and M | copy line, `copy_has_z`, `copy_has_m` | pending |
| W23 (new) the engine's `shapeType` strings | preflight `shape_type`; Point, Polyline and Polygon expected here, Multipoint not in these sources | pending |

## Record edits

To be presented as per-item summaries once the run has numbers: T4.11's status; the
W-items above into the methods evidence table where they close; the B-item for the
destinations that name the design documents; the PR description with the rates.
A15.7 stays as it is.
