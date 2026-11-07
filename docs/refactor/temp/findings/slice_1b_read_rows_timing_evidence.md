# Slice 1b evidence: the `read_rows` timing run, second pull request, batch 1

**Status:** EVIDENCE, 2026-11-06 (the three runs complete on the image). The tool, its
root and the run commands are in place; the three datasets and the probe have run, and
the logs are under `docs/refactor/temp/logs/`. Batch 1 of the second pull request of slice 1b: the timing
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

### Public names in `shape.py`, applied 2026-11-07 on the architect's request

The tool restated three spellings of `shape.py`: the reference field, the multipart tool
and the DeleteField tool. The project rule is one constant or an object reference, and
the measurement must time the adapter's own method, so `shape.py` now exports
`EXPLODE_TOOL`, `REFERENCE_FIELD` and `DELETE_FIELD_TOOL` and the tool imports them. The
two break-once needles that carried the old spellings, X5 and X6 in
`tools/break_once/cases/arcpy_adapter.py`, follow the source; the set rerun:

```
$ uv run --locked --extra dev python -m tools.break_once --check
break-it-once: 163 cases in 8 set(s); needles match, targets collect
$ uv run --locked --extra dev python -m tools.break_once arcpy_adapter --out report.md
break-it-once: 20 cases, 0 unexpected       (X5, X6: FAILED as expected; 237 passed after the last restore)
```
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

The volume's root holds `ag_inputs/`, so it mounts at `/data`. The image runs as uid 150
and a fresh named volume belongs to root, so the volume is given to that user once.

```
docker volume create ag_timing
docker run --rm -v ag_timing:/timing alpine chown 150:150 /timing
docker run --rm -v gis_files:/data:ro -v ag_timing:/timing \
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
    python -m tools.engine.time_read_rows --dataset "$2" --workdir /timing/run \
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

### BygningsPunkt_N10 (points), 2026-11-06

Log `20261106_173656_read_rows.jsonl`, image digest `sha256:7159dec...`, Python 3.13.17,
run with `--cap-seconds 30 --select-count 5 --describe-repeats 20` as the smoke test;
every pass completed under the cap, so this is the points run, with the Describe stage at
a fifth of the counts the full command uses. Fields read: `subtypekode`, `objtype`,
`malemetode` (Integer, String, Integer). The source is planar, EPSG 25833, no Z or M, 14
declared fields, none unrepresentable, so no copy was needed and every pass read the
source copy.

Preflight walk, 4.26 s over 1,167,072 rows: every shape planar, one vertex, no nulls.
Date fields (non-null / with a time of day / with a sub-second part):

| field | non-null | time of day | sub-second |
|---|---|---|---|
| `datafangstdato` | 1,167,072 | 3,134 | 365 |
| `created_date` | 202,005 | 202,005 | 24,456 |
| `last_edited_date` | 371,619 | 371,619 | 44,778 |
| `merknadsdato` | 62 | 2 | 0 |

Explode, the tool bare against the port, on the same input:

| part | seconds |
|---|---|
| `MultipartToSinglepart` bare | 11.76 |
| Describe before | 0.05 |
| null pre-pass | 1.49 |
| Describe after | 0.05 |
| `DeleteField` of the reference | 4.64 |
| sum of the parts the port adds | 6.23 |
| `explode_multipart` total | 15.50 |

The port's total less the bare tool is 3.7 s, under the sum of parts, because the second
tool run was warm; the sum of parts is the overhead figure, and `DeleteField` is two
thirds of it.

Reads, 1,167,072 rows each, every status `complete`, RSS 814.6 MB on every line, peak
847.9 MB:

| token set | variant | position | seconds | rows/s | partition of 36,407 rows |
|---|---|---|---|---|---|
| attributes | bare | 0 | 0.62 | 1,891,161 | 0.019 s |
| geometry | bare | 0 | 0.84 | 1,394,028 | 0.026 s |
| geometry | codec | 1 | 2.59 | 450,162 | 0.081 s |
| geometry | port | 2 | 4.09 | 285,559 | 0.127 s |
| geometry | port | 3 | 4.19 | 278,455 | 0.131 s |
| geometry | codec | 4 | 2.64 | 441,688 | 0.082 s |
| geometry | bare | 5 | 0.85 | 1,368,387 | 0.027 s |

Order did not matter: the two bare passes and the two codec passes agree within 3%, the
two port passes within 3%. Over the bare cursor the codec adds 1.8 s per 1.17M points and
the rest of `_rows` adds another 1.5 s; the port reads a partition-sized set of points in
about 0.13 s, 0.10 s of it added over the bare cursor, against A15.7's minute.

Describe (seconds per call):

| where | n | min | median | max |
|---|---|---|---|---|
| file geodatabase, repeated on one path | 20 | 0.037 | 0.038 | 0.049 |
| file geodatabase, first Describe of a fresh Select output | 5 | 0.040 | 0.041 | 0.046 |
| memory, fresh | 5 | 0.0005 | 0.0006 | 0.001 |
| memory, repeated | 20 | 0.0004 | 0.0004 | 0.0006 |

`analysis.Select` of 1,000 rows took 0.35 s per output in the file geodatabase and 0.13 s
in memory. Describe sits at 0.04 s on a file geodatabase, fresh or warm, a tenth of the
agreed band's upper edge; a few hundred calls per stage cost seconds.

**W18, refuted on the sources.** The walk read sub-second parts from a file geodatabase:
24,456 of `created_date`'s values and 365 of `datafangstdato`'s carry microseconds. PR A
showed the engine rounds a fraction it is given to the second; these values arrived with
their fraction, so the sources hold more than seconds and the read-side refusal in
`row_io.py` fires on any read that names such a field. It did not fire here because the
three fields read are not dates. A contract question for the architect: refuse, as today,
or truncate on read (ADR-0019 PC-D17), given that the project's own use of dates is at day
accuracy. A second points run with `--fields created_date,datafangstdato,objtype` shows the
refusal path and is cheap.

#### The date-field pass on points, 2026-11-06

Log `20261106_174853_read_rows.jsonl`, `--fields created_date,datafangstdato,objtype
--only preflight reads --cap-seconds 30`. The bare and codec passes completed over
1,167,072 rows (the bare geometry pass at 976k rows/s, the codec at 378k). Both port
passes ended `refused` with `PortContractError` after 5,071 rows, 0.04 s in: the first
row whose `created_date` carries a sub-second part. The refusal is the one `row_io.py`
raises for a sub-second date, and the class alone was logged. So a production read that
names an editor-tracking date field refuses today; which way PC-D17 goes is the
architect's.

### ArealdekkeFlate_N10 (polygons), 2026-11-06

Log `20261106_190141_read_rows.jsonl`, every stage, `--cap-seconds 600`, default Describe
counts; no pass reached the cap. Fields read: `subtypekode`, `objtype`, `vannbr`. An
earlier start was stopped after five passes with `docker stop` when the machine had to
move; its log stayed on the volume, its lines agree with the rerun, and it is not used.

Preflight, planar, EPSG 25833, no Z or M, 13 declared fields, none unrepresentable. The
walk took 83.7 s over 3,044,617 rows: 85 null shapes, no holed multipolygon member in the
set, rings per row mean 1.62 (p95 2, max 5,014), vertices per row mean 110 (p50 28, p95
286, max 172,086). Date fields: `created_date` 1,658,886 non-null, all with a time of day,
181,237 with a sub-second part; `last_edited_date` 3,044,617 non-null, 353,221 sub-second;
`merknadsdato` 28, none. The copy without null shapes, `CopyFeatures` plus the update
cursor, took 138.1 s and deleted 85 rows; every pass below read that copy.

Explode on the copy, 3,044,532 rows:

| part | seconds |
|---|---|
| `MultipartToSinglepart` bare | 87.3 |
| Describe before | 0.06 |
| null pre-pass | 76.1 |
| Describe after | 0.06 |
| `DeleteField` of the reference | 15.8 |
| sum of the parts the port adds | 92.0 |
| `explode_multipart` total | 183.9 |

The port doubles the tool's time at this size, and the pre-pass is the bulk of it: a
full `SHAPE@WKB` cursor over the input before the tool runs, 87% of the tool's own time
on polygons of 110 vertices on average. Scaled to a partition of 36,407 rows the parts
sum to 1.1 s, against A15.7's minute. The cross-check, total less bare tool, is 96.6 s.

Reads, 3,044,532 rows each, every status `complete`:

| token set | variant | position | seconds | rows/s | partition of 36,407 rows |
|---|---|---|---|---|---|
| attributes | bare | 0 | 2.49 | 1,224,854 | 0.030 s |
| geometry | bare | 0 | 66.88 | 45,522 | 0.800 s |
| geometry | codec | 1 | 152.14 | 20,012 | 1.819 s |
| geometry | port | 2 | 164.80 | 18,474 | 1.971 s |
| geometry | orient | 3 | 175.40 | 17,357 | 2.097 s |
| geometry | orient | 4 | 182.48 | 16,685 | 2.182 s |
| geometry | port | 5 | 162.32 | 18,757 | 1.941 s |
| geometry | codec | 6 | 158.39 | 19,222 | 1.894 s |
| geometry | bare | 7 | 66.12 | 46,046 | 0.791 s |

Pairs agree within 4%. Over the bare cursor the codec adds 1.1 s per partition and the
rest of `_rows` 0.1 s; the port reads a partition-sized set of these polygons in about
2.0 s, 1.2 s of it added over the bare cursor. **B32's price:** the signed-area check of
every ring adds 10.6 s and 20.2 s over the two port passes it follows, 0.13 to 0.24 s per
partition, 6 to 12% of the port pass; against A15.7's minute it is cheap, and batch 2's
condition is met. RSS held between 835 and 854 MB across every pass; the peak of 1,604 MB
belongs to the tools of the copy and explode stages.

Describe (seconds per call):

| where | n | min | median | max |
|---|---|---|---|---|
| file geodatabase, repeated on one path | 300 | 0.035 | 0.040 | 0.060 |
| file geodatabase, first Describe of a fresh Select output | 100 | 0.071 | 0.087 | 0.217 |
| memory, fresh | 100 | 0.0005 | 0.0005 | 0.0008 |
| memory, repeated | 300 | 0.0004 | 0.0005 | 0.0007 |

`analysis.Select` of 1,000 rows took 0.61 s per output in the file geodatabase and 0.24 s
in memory. A fresh output's first Describe is twice a warm one, at 0.09 s; the agreed band
holds.

### fkb_vann_grense (lines), 2026-11-06

Log `20261106_203203_read_rows.jsonl`, `--only preflight copies reads describe`,
`--cap-seconds 600`; no pass reached the cap. Fields read: `objtype`, `lokalid`,
`navnerom`, all String.

Preflight: **hasZ true**, no M, EPSG 25833, 21 declared fields, none unrepresentable. The
walk took 166.9 s over 14,695,279 rows, every shape planar with one ring, vertices per
row mean 35.4 (p50 13, p95 128, max 24,024), no nulls. Date fields: `datafangstdato` and
`verifiseringsdato` carry no time of day; `oppdateringsdato` 14,695,279 non-null, all with
a time of day, 1,485,862 with a sub-second part.

**W17 and W22.** The source carries Z, so the port's `describe` refuses it, and the 2D
copy was made: `CreateFeatureclass` with the source as template and `has_z="DISABLED"`,
then `Append` with `schema_type="NO_TEST"`, 457.4 s for 14.7M rows, and the copy reads
back `hasZ` false, `hasM` false, EPSG 25833 as the source. W22 holds: the route drops Z
through tools alone. The walk of the copy, 143.3 s, counted the same rings and vertices
as the walk of the source, which shows a second thing: `SHAPE@WKB` of a Z feature class
exported planar codes and 16-byte points on all 14.7M rows, so the engine drops Z on WKB
export as it drops curves. The codec can never see Z; the Describe-level refusal
(PC-D27) is the only guard, and it is the right one.

Reads on the 2D copy, 14,695,279 rows each, every status `complete`:

| token set | variant | position | seconds | rows/s | partition of 36,407 rows |
|---|---|---|---|---|---|
| attributes | bare | 0 | 18.39 | 799,233 | 0.046 s |
| geometry | bare | 0 | 121.61 | 120,838 | 0.301 s |
| geometry | codec | 1 | 268.80 | 54,671 | 0.666 s |
| geometry | port | 2 | 295.16 | 49,788 | 0.731 s |
| geometry | port | 3 | 303.48 | 48,423 | 0.752 s |
| geometry | codec | 4 | 275.72 | 53,299 | 0.683 s |
| geometry | bare | 5 | 111.47 | 131,834 | 0.276 s |

Pairs agree within 9% (the two bare passes), 3% otherwise. The port reads a
partition-sized set of these lines in about 0.74 s, 0.45 s of it added over the bare
cursor, 0.38 s of that the codec. RSS held between 818 and 822 MB across 14.7M rows
streamed seven times; the peak of 1,274 MB belongs to the Append.

Describe (seconds per call):

| where | n | min | median | max |
|---|---|---|---|---|
| file geodatabase, repeated on one path | 300 | 0.072 | 0.080 | 0.159 |
| file geodatabase, first Describe of a fresh Select output | 100 | 0.109 | 0.129 | 0.225 |
| memory, fresh | 100 | 0.0006 | 0.0007 | 0.0015 |
| memory, repeated | 300 | 0.0005 | 0.0006 | 0.0014 |

`analysis.Select` of 1,000 rows took 0.73 s per output in the file geodatabase and 0.29 s
in memory. Describe on this 14.7M-row class is twice the polygons' figure, 0.08 s warm
and 0.13 s fresh, still inside the band.

### The W12 probe, 2026-11-06

Run by the architect in the image, digest `sha256:7159decd0b00fc3ab152a000e66e8709b0816f38e1da5f69f8ae40963a858a61`
(a newer build than PR A's `sha256:eb53667b...`; the tag is the same):

```
$ python docs/refactor/temp/w12_curve_probe.py
file gdb     hasCurves=True pointCount=2 wkb=planar rings=1 vertices=2 bytes=45
memory       hasCurves=True pointCount=2 wkb=planar rings=1 vertices=2 bytes=45
```

The engine neither densifies the curve nor exports a curve code: `SHAPE@WKB` of a
buffered point, a true circle, is a planar polygon of one ring and two vertices, 45 bytes,
in both workspaces. The codec accepts it as a polygon, so a curve is silent geometry loss
on read, and nothing in the WKB tells the preflight a curve was there: its `shapes.curve`
count stays zero whatever the sources hold. Detecting a curve needs the geometry object's
`hasCurves` through `SHAPE@`, a stub name and a per-row cost, or a densify of the working
copy before any read. Which, and whether the port refuses or densifies, is a contract
question for the architect; this batch records it and the W-item table says so.

### The engine writes into `__main__` on import, 2026-11-06

The smoke test crashed on its first log line with `module 'datetime' has no attribute
'now'` although the tool imports the class. The image's interpreter and the import are
sound; the engine rebinds names in `__main__` when it is imported:

```
$ python -c "from datetime import datetime; before = dict(globals()); import arcpy; ..."
added ['arcpy', 'before', 'math', 'numpy', 'sys', 'time']
changed ['datetime']
datetime is now <class 'module'> <module 'datetime' from '/opt/miniconda3/envs/arcgis/lib/python3.13/datetime.py'>
```

So a script that is `__main__`, binds `datetime` from the class and then opens the session
loses the class. The tool now runs as a module and its guarded block imports the module
and calls `main` there, where the engine does not write; `tools/engine/__init__.py` states
the rule. The same applies to every pipeline entry point under the `__main__` guard once
one opens the session. Not decided in this batch; the two candidate responses, for the
architect:

- (a) the convention the tool uses: every entry point that opens the session runs as a
  module and its guarded block imports the module and calls `main` there. Cost: a rule
  to know and a run form to follow, `python -m`; nothing in code guards it.
- (b) containment in the session: `open_session` snapshots `__main__`'s namespace around
  the first engine import and restores what the import added or rebound, so the effect
  stays with the module that owns the engine's global state (ADR-0018 AR-D23), and it is
  unit-testable on the fake. Cost: a few lines in `session.py` and a guard case. It relies
  on the session's import being the process's first engine import, which holds today:
  every `import arcpy` under `src/` and `tests/support/arcpy/` sits inside a function
  that takes a session, the unit tests install a fake, and the two hits under
  `tests/static/` are probe strings for the stub test.

## What the numbers decide

Partition-sized figures, 36,407 rows scaled from the rates, vertex means beside them. The
projection is partition 18 of the road stage input scaled from a rate; no run read that
partition.

| dataset | vertices per row, mean | bare cursor | `read_rows` | added by the port | of which the codec |
|---|---|---|---|---|---|
| points | 1 | 0.03 s | 0.13 s | 0.10 s | 0.06 s |
| lines | 35 | 0.30 s | 0.74 s | 0.45 s | 0.38 s |
| polygons | 110 | 0.80 s | 1.96 s | 1.16 s | 1.06 s |

- **Streaming stands.** `read_rows` reads a partition of the heaviest source in two
  seconds and the full 14.7M-row lines class in five minutes, with memory flat; slice 3's
  lineage-aware pipe can stream `Row` values and needs no columnar read beside it.
- **A15.7 holds at partition size** for the one port method measured: `explode_multipart`
  adds 1.1 s per partition of 36,407 polygons over the bare tool. Over the whole 3.0M-row
  source the parts add 92.0 s to the tool's 87.3 s, more than the minute, so a stage that
  explodes a whole source would exceed it. Nearly all of the addition is the null
  pre-pass, a full `SHAPE@WKB` cursor; a cheaper token for the null check is an
  unmeasured candidate, not a fact.
- **B32's price is cheap:** 0.13 to 0.24 s per partition of polygons, 6 to 12% of the
  port pass; batch 2 may put canonical orientation into `Geometry`.
- **The codec is the port's cost.** On every set the codec is most of what the port adds
  (60% on points, 85% on lines, 90% on polygons); `_attribute`, the `Row` and the per-row
  `where` string are the rest. An attributes-only port read on a feature class would cost
  about the bare attributes pass plus that remainder: on polygons 0.03 s plus 0.1 s
  against 1.96 s, on lines 0.05 s plus 0.07 s against 0.74 s. That is the price of the
  attributes-only question, for the architect.
- **Describe is cheap everywhere measured:** 0.04 to 0.08 s warm and 0.09 to 0.13 s on a
  fresh output in a file geodatabase, under a millisecond in memory; hundreds of calls per
  stage cost seconds, inside the agreed band.
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
| W12 curves | the probe: neither densified nor a curve code, the arc's two vertices as a planar ring; the preflight's `shapes.curve` cannot see a curve, so the sources' half is unanswered, not zero | probe observed; sources unanswered; B-item opening |
| W14 timing | the reads, explode and describe stages | done on all three sets, above |
| W17 hasZ/hasM of the sources | preflight line per source | points and polygons: no Z, no M; lines: Z, no M; WKB export drops Z, so the Describe refusal is the only guard |
| W18 date fields of the sources | preflight `date_fields`: every set holds sub-second parts in its editor-tracking date fields (points 3 fields, polygons 2, lines `oppdateringsdato` 1.49M of 14.7M); the refusal fired on the date-field pass | observed on all three, contract question open |
| W22 (new) the 2D copy through CreateFeatureclass and Append drops Z and M | copy line of the lines run: `copy_has_z` false, 457 s for 14.7M rows | holds |
| W23 (new) the engine's `shapeType` strings | preflight `shape_type`: `Point`, `Polygon`, `Polyline` observed; `Multipoint` not in these sources | three of four observed |

## Findings for the architect, not decided here

- A curve is silent geometry loss through `SHAPE@WKB` (W12 above).
- The engine writes into `__main__` on import (above); entry points that open the session
  are exposed.
- `read_rows` has no attributes-only pass on a feature class (above).
- The sources hold sub-second date values, so the read-side refusal fires on production
  data (W18 above, and the date-field pass).
- `SHAPE@WKB` drops Z as it drops curves (the lines run); the Describe-level refusal is
  the only Z guard and stands.
- `explode_multipart`'s null pre-pass costs 87% of the tool's own time on polygons; fine
  at partition size, over A15.7's minute on a whole source.

## The architect's decisions on the findings, 2026-11-07

- Curves: a B-item, opened with this batch; whether curves matter is checked before the
  two batches are pushed as one pull request.
- Z dropped by `SHAPE@WKB`: fine; the Describe-level refusal stands as the only guard.
- Sub-second dates: the port supports the native type and does not remove the fraction;
  the change to ADR-0019 PC-D17, `row_io.py`, the predicate compiler's literal and the
  memory adapter is presented as a per-item summary and lands with later work.
- Holed multipolygon members: not expected and not produced by the pipeline; a raw input
  that has them is exploded at ingest before it is read, so read after `explode_multipart`
  is the contract. B30 closes on that basis.
- B32: the condition is met; batch 2 puts canonical orientation into `Geometry`.
- The attributes-only read: no B-item; the price above is the record.

## Record edits

To be presented as per-item summaries: T4.11's status (the timing run done, the W-items
closed or open as above); the B-item for the destinations that name the design documents
(parked by the architect; it takes the next free number when written, B33 being the
curves item); the PR description with the partition table above. A15.7
stays as it is. The logs under `docs/refactor/temp/logs/` are staged with this file.
