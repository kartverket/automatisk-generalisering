# Slice 1b evidence: geometry family and canonical orientation

**Status:** EVIDENCE, 2026-11-09, every marked run green, the date rule landed and
confirmed on the image. Open: B33, with the architect's team. B31 (the geometry family on `Schema`) and B32 (canonical ring orientation in
`Geometry`), their refusals, their break-once cases, the W23 pins, the W24 and W25
probe, and the records. The timing run that priced B32 is
`slice_1b_read_rows_timing_evidence.md`.

This file is written in WSL without ArcPy. The unit tests, the conformance suite's memory
half, the static tests and the break-once sets ran here; the marked tests ran in the
image, run by the architect and pasted, and nothing here claims an engine result it has
not been shown. The marked run command is in `docs/contributing/testing.md`.

**The data is not open.** Nothing here comes from project data. The W24 and W25 probe
reads one production field's Describe properties from the working copy on the
`ag_timing` volume, never from the read-only `gis_files` mount, and prints names and
properties only.

## What B31 and B32 add

- `GeometryFamily` in `ports/geometry.py`: `POINT`, `MULTIPOINT`, `LINE`, `POLYGON`, the
  folding every engine shares; `GeometryKind.family`; `GeometryFamily.single`, the family
  `explode_multipart` writes, multipoint to point and every other family to itself.
- `Schema.geometry_family`, required for a feature class and refused on a table, beside
  `geometry_crs`. The empty dataset is answered by the schema: a partition in which one
  input has no rows still hands the method a dataset with every field and its geometry
  type, created from the schema alone (the architect, 2026-11-08; the legacy partition
  iterator did this with a template feature class, and the port has no template).
- `MemoryStore.write` refuses a row whose kind is outside the schema's family before
  anything is replaced, as every engine refuses it. The memory `explode_multipart` writes
  its output under the input family's `single`, so an empty multipoint input writes an
  empty point feature class with no row consulted.
- `describe` fills the family from the engine's `shapeType` through `SHAPE_TYPES` in
  `dataset_schema.py`, spelled once, and refuses a shape type none of the families holds;
  `_read` maps `dataType` inside the guard and branches on the port's `DataType`, not on
  the engine's string.
- `GEOMETRY_TYPES`, the CreateFeatureclass vocabulary keyed by family, moved from the test
  builders into `dataset_writer.py` beside the AddField vocabulary; the builders and the
  timing tool import it. All four keywords were exercised on the image on 2026-11-05
  through the conformance seeds.
- Canonical orientation in `Geometry.__post_init__`: a polygon's exterior and every
  multipolygon member counter-clockwise, holes clockwise, through `object.__setattr__`;
  the same `parts` tuple is kept when nothing reverses, which is every value an engine
  returns; a ring of zero signed area keeps its order; lines and points are never touched.
  The signed area is taken relative to the ring's first vertex.
- `oriented`, `signed_area` and their helpers left `tests/support/wkb.py`; `to_wkb` stays
  as the oracle. The builders seed a feature class from the schema's family and no longer
  infer a geometry type from the rows' kinds (`geometry_type_of` removed).
- The fake engine inverts `DATA_TYPES` and `SHAPE_TYPES` as it inverts `FIELD_TYPES`, so
  its `FeatureClass`, `Table`, `Point`, `Multipoint`, `Polyline` and `Polygon` strings are
  the adapter's own, and `seed` reads the data type and the shape type from the schema.
- The timing tool: the `orient` variant, `oriented_rows`, `rings_to_reverse`, `signed_area`
  and their tests retired; the 2D copy's geometry type read through the family and
  `GEOMETRY_TYPES`; no engine string restated.
- `docs/refactor/temp/w24_w25_date_probe.py`, the by-hand probe for W24 and W25.
- The probes `w12_curve_probe.py` and `w19_wkb_probe.py` build their schemas with a family
  and seed without a geometry type, so they run as before.

## The signed-area form, 2026-11-08

The plain shoelace form, `sum(x1 * y2 - x2 * y1)`, multiplies coordinates of 5e5 by 7e6
and takes the sign from the difference of products near 3.5e12, where a double's spacing
is about 5e-4. A ring a few millimetres across has twice its area below that spacing, so
the sign is rounding. The relative form subtracts the first vertex first. Probe in the
scratch directory, Python, no engine:

```
20000 CCW rectangles, sides 1 mm to 1 m, eastings 2e5-8e5, northings 6.4e6-7.9e6:
  wrong sign plain=736 relative=0; exactly zero plain=4781 relative=0
1 cm x 0.1 mm at (500000, 7000000): plain=0.0 relative=1.9999966e-06 true=2.0e-06
same ring clockwise: plain=0.0 relative=-1.9999966e-06
two-vertex ring: relative=0.0; collinear ring: relative=0.0
200k calls, 5-vertex ring: plain=0.075s relative=0.100s ratio=1.33
```

So with the plain form a quarter of real rings would have read as zero area and kept
whatever order they came in, and "a zero-area ring keeps its order" would have been a
rule about rounding. The unit tests pin the thin and the small ring at UTM coordinates in
both orientations, the two-vertex and the collinear ring, and the identity of `parts`
when nothing reverses.

## The explode family rule, 2026-11-08

On the memory adapter before the family check, run in WSL:

```
multipoints  input kinds ['MULTIPOINT'] -> output kinds ['POINT']; output schema is input schema: True
multilines   input kinds ['LINESTRING', 'MULTILINESTRING'] -> output kinds ['LINESTRING']; output schema is input schema: True
polygons     input kinds ['MULTIPOLYGON', 'POLYGON'] -> output kinds ['POLYGON']; output schema is input schema: True
```

With the store's kind-against-family check, the first line is a refusal: point children
under a multipoint schema. `GeometryFamily.single` is the rule, declared once; the memory
adapter applies it to the output schema, and on the engine the tool decides, which the
marked test in `tests/engine/arcpy/test_shape.py` asserts through `describe`.

## Checks run here, 2026-11-08

```
$ uv run --locked --extra dev pre-commit run --all-files
ruff format --check / ruff check / pyright strict / import contracts / source scans /
pytest -m "not arcpy" / break-it-once case tables / design record consistency /
terminology anchors and headwords: all Passed
$ uv run --locked --extra dev pytest -m "not arcpy" -q
540 passed, 43 deselected
$ uv run --locked --extra dev python -m tools.break_once --check
break-it-once: 173 cases in 8 set(s); needles match, targets collect
$ uv run --locked --extra dev python -m tools.break_once ports --out ...
break-it-once: 30 cases, 0 unexpected      (P25-P30 new: FAILED as expected)
$ uv run --locked --extra dev python -m tools.break_once memory_adapter --out ...
break-it-once: 31 cases, 0 unexpected      (M30, M31 new)
$ uv run --locked --extra dev python -m tools.break_once arcpy_adapter --out ...
break-it-once: 22 cases, 0 unexpected      (D3, D4 new)
```

The nine new marked tests collect (`pytest tests/engine tests/conformance
--collect-only`: 64 tests) and have not run.

## The marked run, 2026-11-08

Image `ghcr.io/kartverket/arcpy-linux:12.1`, the documented command, tip `097c509`:

```
collected 64 items / 21 deselected / 43 selected
tests/conformance/test_geometry_ops.py ............
tests/conformance/test_table_ops.py .........
tests/engine/arcpy/test_dataset_schema.py .........
tests/engine/arcpy/test_memory_workspace.py ..
tests/engine/arcpy/test_row_io.py ..
tests/engine/arcpy/test_session.py .....
tests/engine/arcpy/test_shape.py ....
43 passed, 21 deselected in 60.21s
```

No test was fixed or removed. What the nine new tests confirmed:

| test | confirmed |
|---|---|
| `tests/engine/arcpy/test_dataset_schema.py::test_describe_reads_each_family_from_the_shape_type`, eight ids | W23 closed: the four `shapeType` spellings, `Multipoint` included, in a file geodatabase and in the memory workspace |
| `tests/engine/arcpy/test_shape.py::test_a_multipoint_input_explodes_into_a_point_family_output` | the tool writes a multipoint input's children into a point class, which is `GeometryFamily.single` |
| `tests/conformance/test_table_ops.py::test_read_rows_round_trips_each_geometry_kind[arcpy-*]` | the round trip is identity with the builders orienting nothing |
| every other marked test | unchanged in intent; the seeds take the geometry type from the schema |

The `SHAPE_TYPES` docstring's note that `Multipoint` was unconfirmed is lifted with this
run.

## W24 and W25, the probe

To be pasted from the architect's run of `docs/refactor/temp/w24_w25_date_probe.py` in
the image, with the `ag_timing` volume mounted for the production copy's field
properties. Two defects of the probe surfaced on its first runs, 2026-11-08, and are
fixed: it needs the repository root on the path beside `src`, as the earlier probes do;
and, run as a file, it is `__main__`, where the engine rebinds `datetime` to the module
when the session opens, so an `isinstance` against that name after `open_session` raised
`TypeError`. The probe now prints a date through its `isoformat` attribute and names its
field `stamp`, since Describe listed no field named `when`, an SQL keyword, on the first
run; the second run listed `stamp`, so the field name was the cause and the probe's
first field was never created under the name it asked for.

### The second run, 2026-11-08

Image digest `sha256:7159decd0b00fc3ab152a000e66e8709b0816f38e1da5f69f8ae40963a858a61`,
`PYTHONPATH=/work/src:/work`, the production copy from the `ag_timing` volume:

```
== file: AddField DATE, fresh ==
describe reports fields ['OBJECTID', 'stamp']
field properties: {}
written 2024-01-01T12:00:00.500000 and 2024-01-01T12:00:00
read back ['2024-01-01T12:00:01', '2024-01-01T12:00:00']
where timestamp-fraction   -> 0 row(s)
where timestamp-whole      -> 1 row(s)
where date-fraction        -> 0 row(s)
where date-whole           -> 1 row(s)
== management.MigrateDateFieldToHighPrecision ==
tool unavailable or refused: TypeError
== memory: AddField DATE, fresh ==
describe reports fields ['OBJECTID', 'stamp']
field properties: {}
written 2024-01-01T12:00:00.500000 and 2024-01-01T12:00:00
read back ['2024-01-01T12:00:00.500000', '2024-01-01T12:00:00']
where timestamp-fraction   -> 1 row(s)
where timestamp-whole      -> 1 row(s)
where date-fraction        -> 1 row(s)
where date-whole           -> 1 row(s)
== production copy, date fields of BygningsPunkt_N10 ==
describe reports fields [OBJECTID, shape, 14 declared fields]
datafangstdato: {}   merknadsdato: {}   created_date: {}   last_edited_date: {}
port type for 'Date': FieldType.DATE
```

What it settles and what it does not:

- **W25, answered.** A fractional literal is accepted by the file geodatabase's SQL and
  compared with its fraction: in the file geodatabase it matched neither the row stored
  as 12:00:01 nor the one stored as 12:00:00, which a literal truncated or rounded to the
  second would have matched; in the memory workspace it matched the fractional row. The
  predicate compiler's literal may carry the fraction, which is the condition A33.2 set.
- **W24, half.** A DATE field made by AddField in a fresh file geodatabase rounds a
  fraction to the second, PR A's observation again on this digest, while the memory
  workspace keeps microseconds. So the engine has a store that holds the fraction and a
  store that, as the adapter creates it today, does not; the production fields that hold
  fractions (the timing run) are of a third kind the probe has not yet told apart from
  the fresh one.
- **Two probe defects, fixed for the third run.** The property dump walked `dir()` and
  found nothing public on every Field object, fresh and production alike, so the dump
  now asks for named properties through `arcpy.ListFields`, the documented ones and the
  candidates for a precision flag, and prints the object's type and attribute names
  once. The migration tool was called with the keyword `field` and raised `TypeError`,
  which the session's rule says is a misspelt keyword and not a missing tool, so the
  tool is present on the image; the call now uses `field_names` and a failure prints the
  message, since the table is synthetic.
- **For slice 2a.** Under A33 an adapter whose store holds less precision truncates
  before handing over. The file geodatabase store the adapter creates today holds whole
  seconds and rounds, so `write_rows` truncates for such a field and not for the memory
  workspace, and the precision is a fact the adapter has to read, which is what the
  third run is for.

### The third run, 2026-11-08

Same digest and command. The property dump through `ListFields` worked; the read-back
and where-clause lines repeated the second run exactly.

```
field object arcpy.arcobjects.arcobjects.Field
public attributes ['aliasName', 'baseName', 'defaultValue', 'domain', 'editable',
                   'isNullable', 'length', 'name', 'precision', 'required', 'scale', 'type']
file gdb, fresh:        {'type': 'Date', 'length': 8,   'precision': 0, 'scale': 0, ...}
memory, fresh:          {'type': 'Date', 'length': 255, 'precision': 0, 'scale': 0, ...}
production created_date {'type': 'Date', 'length': 8,   'precision': 0, 'scale': 0, ...}
production datafangstdato, merknadsdato, last_edited_date: the same values
== management.MigrateDateFieldToHighPrecision ==
TypeError: MigrateDateFieldToHighPrecision() got an unexpected keyword argument 'field_names'
```

What it settles:

- **The precision is not a Field property.** The fresh file geodatabase field, which
  rounds, and the production `created_date`, which holds microseconds (the timing run),
  have identical Field objects: `Date`, length 8, precision 0, scale 0, and the object
  exposes twelve attributes and no other. So `write_rows` cannot read the precision from
  the field it creates; it is a property of the dataset or the geodatabase, if the engine
  exposes it at all.
- The memory workspace's Date field reports length 255 against 8; a difference of the
  store, not a flag.
- The migration tool exists and takes neither `field` nor `field_names`; the fourth run
  calls it with the table alone and prints its signature on a refusal, and dumps the
  dataset-level Describe attributes of the fresh table before and after the migration, of
  the memory table and of the production class, with the names that differ. Which way
  2a goes, migrate every created dataset or truncate for the file geodatabase, is what
  that run decides.

### The fourth run, 2026-11-08

Same digest and command. The read-back and where-clause lines repeated the second run.

```
== management.MigrateDateFieldToHighPrecision ==
EngineError: ... ERROR 000735: Date Fields: Value is required
signature: (in_table=None, date_fields=None) -> 'Result1[str | Table | Layer | Path]'
dataset attributes, fresh table: {}
dataset attributes changed by the migration (before, after): {}
dataset attributes, memory table, differing from fresh (fresh, memory): {}
dataset attributes, production: []
differing from the fresh table (fresh, production): {}
```

What it settles:

- **The migration tool's signature** on the image is `(in_table, date_fields)`, and
  `date_fields` is required; the fifth run calls it so.
- **A Describe object lists nothing through `dir()`,** as a Field object did not, so the
  dataset dump has to ask by name. The fifth run asks for the documented table,
  geodatabase-table, feature-class and workspace attributes and for candidate names of
  a date-precision flag, each reported present with its value or absent, on the dataset
  and on its workspace.

### The fifth run, 2026-11-08

Same digest and command. The migration ran with `date_fields`.

```
file gdb, AddField DATE        precision 0   12:00:00.5 -> 12:00:01            fraction literal 0 rows
after MigrateDateFieldToHighPrecision(in_table, date_fields='stamp')
                               precision 1   12:00:00.5 -> 12:00:00.500000     fraction literal 1 row
memory, AddField DATE          precision 0   12:00:00.5 -> 12:00:00.500000     fraction literal 1 row
dataset attributes changed by the migration: {}
memory table, differing from fresh: workspace.release, workspace.workspaceFactoryProgID only
production BygningsPunkt_N10: datafangstdato, merknadsdato, created_date, last_edited_date
                               all precision 0; dataset attributes differ from the fresh
                               table only in being a feature class
```

**W24, answered.** In a file geodatabase the flag is `Field.precision`: 0 is a store of
whole seconds, the engine rounding what it is given on write; 1 keeps the fraction and
matches a fractional literal; `MigrateDateFieldToHighPrecision(in_table, date_fields)`
switches a field from 0 to 1 and changes nothing on the dataset or the workspace. So
`write_rows` can create a date field that keeps the fraction: AddField, then the
migration on the date fields. The memory workspace keeps the fraction whatever
`precision` says. No dataset or workspace attribute carries the distinction.

**The premise behind A33, reopened for the architect.** Every production date field is
`precision` 0, a store of whole seconds, yet the timing run counted microsecond parts in
them, about 12% of the values with a time of day in every set. Those cannot be stored
fractions. The candidate explanation is the encoding: a low-precision file geodatabase
date is a double of days, and a double represents few whole seconds exactly, so a
whole second reads back as 10.999999 or 11.000001 some of the time. Not shown yet; the
sixth run counts the microsecond parts of each production date field in two bands,
within a millisecond of a whole second or elsewhere, counts only. If the parts are
noise, the sources hold whole seconds: A33's contract line stands, since `precision` 1
fields hold real fractions and `write_rows` can make them, but A33's rule for a
fraction an adapter cannot store, truncate and never round, would turn 11.999999 into
11, one second from the value the source meant, where rounding would restore it; and
the read-side refusal that fired on production data fired on noise. Which rule holds,
and whether the port reads a `precision` 0 field to the second, is the architect's
decision and is not changed here. The project reads dates rarely, to order
observations, and has to handle varying raw data reliably (the architect, 2026-11-09),
so the rule has to be right for noise and for real fractions alike.

### The sixth run, 2026-11-09

Same digest and command; the engine lines repeated the fifth run. The microsecond parts
of the production copy's date fields, counts only, the band one millisecond wide:

| field | non-null | with a fraction | within a millisecond of a whole second | elsewhere |
|---|---|---|---|---|
| `datafangstdato` | 1,167,072 | 365 | 365 | 0 |
| `merknadsdato` | 62 | 0 | 0 | 0 |
| `created_date` | 202,005 | 24,456 | 24,456 | 0 |
| `last_edited_date` | 371,619 | 44,778 | 44,778 | 0 |

**The parts are encoding noise.** Every stray fraction on every production field lies
within a millisecond of a whole second and none elsewhere, which a stored fraction would
have produced somewhere in 69,599 values. The sources hold whole seconds; the file
geodatabase's `precision` 0 store encodes them as a double of days and about one in
eight reads back a microsecond off. W24 and W25 close.

### The date rule, decided 2026-11-09

The architect chose, from four options presented with their costs: the adapter decodes
by the field's precision and creates fields that hold the fraction. The project reads
dates rarely, to pick the newer of two observations years apart or to order its own run
stamps minutes apart, but has to handle varying raw data reliably, and a later need for
accuracy has to be cheap to meet.

- `describe` reads each field's engine `precision` and names the date fields at 0 as
  `DescribedDataset.whole_second_fields`; `read_rows` reads such a field to its nearest
  second, so no encoding noise crosses the port and two copies of one timestamp compare
  equal, and reads a `precision` 1 field with its fraction. Rounding, not truncation,
  because the noise lies on both sides of the stored second; A33's truncation rule is
  for a real fraction meeting a store that cannot hold it, which this is not.
- `add_fields` migrates every date field it adds to `precision` 1 through
  `MigrateDateFieldToHighPrecision(in_table, date_fields)`, so every date field the
  adapter creates holds what the port carries, and `write_rows` inherits the step. The
  engine documents that store as milliseconds; the marked test holds a value written
  with microseconds to within a millisecond, and the adapter's docstring states it.
- The shared value rule and the memory store accept a fraction; the compiler's literal
  carries it as `.ffffff`; the read-side refusal is gone.
- Rejected: whole seconds only in the port, which reverses A33 and makes a later need
  for accuracy a contract change; a noise band in the data path, a magic threshold that
  destroys a real fraction near a whole second; A33 unchanged with nothing on the read
  side, which truncates 11.999999 to 11 on one value in eight.

What landed with it, 2026-11-09:

- `dataset_schema.py`: `_Raw.fields` carries `precision`; `WHOLE_SECOND_PRECISION`;
  `DescribedDataset.whole_second_fields`. `row_io.py`: the decode, the refusal removed.
  `_shared/field_values.py`: the microsecond branch removed. `predicate_compiler.py`:
  the fraction in the literal. `dataset_writer.py`: `MIGRATION_TOOL`, the migration in
  `add_fields`. The stub's `_Field` gains `precision`.
- The fake engine: `FakeField.precision`, the migration tool, `seed(date_precision=)`
  with the adapter's own precision as the default and the whole-second store for a test
  that stands in for a raw source.
- Tests: the whole-second decode on both sides of the second and across midnight, the
  fraction read as it is, the compiler's fractional literal, the fraction through the
  memory store and the evaluator, `whole_second_fields` from describe, the builders'
  migration call; `tests/support/cases.py` gains `stamps`, two rows half a second apart;
  conformance round-trips it on both adapters and selects on a fractional and a
  whole-second literal; the marked `test_row_io.py` tests a bare AddField field that
  rounds and reads to the second, and a field the adapter creates that holds a fraction
  to within a millisecond. The sub-second refusal tests are gone.
- Break-once: P4 is now the compiler's literal dropping the fraction; R3 the decode
  removed; R4 truncation instead of rounding; D5 the precision not read; W1 the
  migration not run.
- Records: ADR-0019 PC-D17 adapted per A33.1's decided text; T4.11's follow-up; the W18
  rows of the timing evidence. A33's "Why" and A33.2 in `DECISIONS.md`, approved by the
  architect on 2026-11-09 and applied.

### The marked run of the date rule, 2026-11-09

Same digest, the documented command, 69 collected, 46 selected: 44 passed, 2 failed. The
six new tests passed, which confirms what the probe had not shown: a six-digit fraction
in a literal matches (`test_a_date_comparison_carries_its_fraction[arcpy]`), a value
written with microseconds into a field the adapter creates reads back within a
millisecond and not whole, and a bare AddField field rounds and is read to the second.

The two failures were both `test_memory_workspace.py`, at the seed:

```
EngineError: arcpy: management.MigrateDateFieldToHighPrecision failed:
ERROR 002764: The operation is not supported by this implementation.
```

An engine-facing assumption, fixed in place under the run's rule: the in-memory
workspace refuses the migration, and it also reports `precision` 0 while keeping the
fraction (the fifth run), so `describe` would have named its date fields whole-second
stores and `read_rows` rounded real fractions there. The adapter now tells the workspace
apart through the engine: `in_memory_workspace` reads the dataset's `path` and the
workspace's `workspaceFactoryProgID`, the spelling the fifth run showed, kept once in
`dataset_schema.py`; `add_fields` skips the migration there and `describe` names no
whole-second field there, consulting the workspace only when a date field at 0 is
present. The fake engine models workspaces the same way and refuses the migration in
its memory one. Break-once D6 and W2 cover the two guards.

The run after the fix, same digest and command, 2026-11-09:

```
collected 69 items / 23 deselected / 46 selected
tests/conformance/test_geometry_ops.py .............
tests/conformance/test_table_ops.py ..........
tests/engine/arcpy/test_dataset_schema.py .........
tests/engine/arcpy/test_memory_workspace.py ..
tests/engine/arcpy/test_row_io.py ...
tests/engine/arcpy/test_session.py .....
tests/engine/arcpy/test_shape.py ....
46 passed, 23 deselected in 68.59s
```

The two memory-workspace tests seed through `add_fields` and so pass only if the
Describe `path` attribute names the dataset's workspace and the workspace's
`workspaceFactoryProgID` is the memory one; both held. Nothing on the date rule is open
on the engine. A33's text in `DECISIONS.md` was approved and applied the same day.

### Review rounds three and four, 2026-11-09

Four points adopted, one adapted, from the reviewer's third round, and three adopted from
the fourth; assumptions checked against the tree before acting, the session's guard
among them (it wraps the vendor class and an exact `RuntimeError` or `OSError`, so a
missing Describe attribute leaves as a raw `AttributeError`).

- **Two engine behaviours the date rule rests on, unobserved** (W26, W27). `read_rows`
  rounds a `precision` 0 value to its second, but whether the engine's own where clause
  on that second selects a value that reads back a microsecond off is not shown, and
  the compiler's docstring predicted the disagreement PC-D17 forbids. The `precision`
  1 store is documented as milliseconds, the writer's docstring said both that and
  "nothing is reduced", and the marked test's one-millisecond window cannot tell
  truncation from rounding. `docs/refactor/temp/w26_w27_date_store_probe.py`, counts
  only, settles both; the writer's text, A33.2's millisecond rule for `write_rows` and
  the marked test's assertion follow its output.
- **An empty polygon ring** raised `IndexError` from `_signed_area` on construction and
  through the codec, where both had constructed before; the guard would have let it out
  raw. A ring under two vertices now has signed area zero and keeps its order, like any
  degenerate ring; whether it is a valid ring is B33's. Unit tests on the value and on
  the codec; break-once P31 in the ports set.
- **The workspace walk.** A feature class in a feature dataset has the feature dataset
  as its `path`, whose Describe is not shown to carry `workspaceFactoryProgID`. The
  lookup now walks `path` upward until a Describe reports `dataType` `Workspace`
  (`WORKSPACE_DATA_TYPE`), at most `WORKSPACE_DEPTH` = 2 steps, since feature datasets
  do not nest, and refuses with `PortContractError` naming the dataset past that. Unit
  tests on the fake, which models feature datasets and nests them to reach the refusal;
  break-once D7; a marked case in `tests/engine/arcpy/test_dataset_schema.py`, a feature
  class with a bare date field inside a feature dataset, described and read, awaiting
  the image.
- **The arcpy break-once set in full**, after the date rule and these changes:

```
$ uv run --locked --extra dev python -m tools.break_once arcpy_adapter --out ...
break-it-once: 28 cases, 0 unexpected   (P4, R3 changed; R4, D5, D6, D7, W1, W2 new)
$ uv run --locked --extra dev python -m tools.break_once ports --out ...
break-it-once: 31 cases, 0 unexpected   (P31 new)
```

## B33, true curves: the decision and the probes before it lands, 2026-11-09

The architect's decision: the project does not support or deliver true curves. The port
carries planar simple features with straight segments, settled the way B30 was: ingest
makes a raw input conform, and the pipeline's own curve-producing methods, buffer first,
densify their output within a set deviation (Densify, not Simplify, which removes
vertices and changes the form). The degenerate-ring refusal, a polygon ring under four
coordinates or a line under two on every ring, exterior, hole and member alike, is the
backstop for a curve that is a whole ring, such as a buffered point's circle, and not the
guard: a curved corner inside a longer ring reads as a straight chord, off by about 0.29
of the radius on a right angle, and keeps its coordinates. Why the loss is new with the
port: the legacy code reads geometry objects, which keep curves; the port reads WKB,
which drops them.

Order of landing, the architect's: the count first, then the refusal and T3.4's rule.
Two probes, written 2026-11-09, their output to be pasted here:

- `docs/refactor/temp/w28_curve_count_probe.py` (W28): per raw source on the plain
  `cp -a` copies under `/timing/copies`, never the timing run's derived copies, rows
  whose geometry `hasCurves` through `SHAPE@`, and rings under four coordinates or lines
  under two through a per-ring WKB walk, which the timing walk's per-row counts could not
  give. It walks every feature class of each geodatabase it is given, so `ArealdekkeFlate`
  is counted with the three datasets the timing run read; runs detached with a progress
  line per 100,000 rows and an `interrupted` line on SIGTERM. Which geodatabases under
  `ag_inputs/raw_data` the stages read is not declared in this tree; the three copied are
  counted and the architect names what is left out.
- `docs/refactor/temp/w29_buffer_densify_probe.py` (W29): a point, a line and a polygon
  buffered by ten metres in a file geodatabase and in the memory workspace, `hasCurves`
  and the vertex count per row before and after `edit.Densify` with the offset method at
  one centimetre. Turns the architect's Pro observation (a buffered point is one true
  curve, a buffered line straight segments, a buffered polygon curves at its corners) and
  the engine's documented Densify behaviour into image facts.

### W28, the count, 2026-11-09

Run detached on the plain `cp -a` copies of the three raw geodatabases, fifteen feature
classes, 39.7 million rows in 21 minutes; `hasCurves` through `SHAPE@` per row and the
per-ring WKB walk in one cursor. The `dataset` lines, batch lines left out:

| feature class | shape | rows | curved rows | rings under 4 | lines under 2 | s |
|---|---|---|---|---|---|---|
| `AnleggsLinje_N50` | Polyline | 29,506 | 20 | 0 | 0 | 0.2 |
| `BygningsPunkt_N10` | Point | 1,167,072 | 0 | 0 | 0 | 3.9 |
| `Grunnriss_N10` | Polygon | 43,735 | 69 | 0 | 0 | 0.4 |
| `TuristHytte_N10` | Point | 1,864 | 0 | 0 | 0 | 0.0 |
| `Begrensningskurve_N50` | Polyline | 1,220,991 | 0 | 0 | 0 | 12.4 |
| `AdminGrense_N50` | Polyline | 1,083 | 0 | 0 | 0 | 0.1 |
| `AdminFlate_N50` | Polygon | 365 | 0 | 0 | 0 | 0.1 |
| `ArealdekkeFlate_N50` | Polygon | 526,121 | 0 | 0 | 0 | 42.0 |
| `ArealdekkeFlate_N10` | Polygon | 3,044,617 | 0 | 0 | 0 | 119.0 |
| `ArealdekkeFlate` | Polygon | 14,730,236 | 0 | 4,312 | 0 | 714.5 |
| `Fishnet_500m` | Polygon | 1,887,170 | 0 | 0 | 0 | 13.4 |
| `Arealdekke_Test` | Polygon | 469 | 0 | 0 | 0 | 0.0 |
| `fkb_vann_omrade` | Polygon | 2,344,625 | 0 | 0 | 0 | 138.1 |
| `fkb_vann_grense` | Polyline | 14,695,279 | 0 | 0 | 0 | 208.7 |
| `fkb_vann_posisjon` | Point | 176,351 | 0 | 0 | 0 | 0.7 |

Two sources hold true curves, so by the architect's rule ingest densifies raw inputs
(T3.4; whether every input or only the curved rows is W30). One source holds 4,312
polygon rings under four coordinates, none of them curves: bad source geometry, which
ingest repairs or removes (T3.4, W31) and which a port read refuses. The counts are from
that day's copies, which is why T3.4 records a rule. Which geodatabases under
`ag_inputs/raw_data` beyond these three the stages read is for the architect to name.
The `SHAPE@` pass priced itself: 20,600 rows a second on the 14.7M-row polygons and
70,400 on the lines, against 46,000 and 121,000 for the bare WKB cursor in the timing
run, so a per-row `hasCurves` check on read would have cost more than the codec does.

### W29, buffer and Densify, 2026-11-09

`analysis.Buffer` with `buffer_distance_or_field="10 Meters"` and every other parameter
at its default (full side, round end, no dissolve, planar method) over the `points`,
`roads` and `polygons` cases (two points; three two-vertex lines; an axis-aligned square
with a square hole and a two-member multipolygon), then `edit.Densify` with
`densification_method="OFFSET"` and `max_deviation="0.01 Meters"` on the output:

```
== buffers written to probe.gdb ==
  points after Buffer:    rows=2 with_curves=2 vertices=[2, 2]
  points after Densify:   rows=2 with_curves=0 vertices=[37, 37]
  roads after Buffer:     rows=3 with_curves=0 vertices=[99, 99, 99]
  roads after Densify:    rows=3 with_curves=0 vertices=[99, 99, 99]
  polygons after Buffer:  rows=2 with_curves=0 vertices=[101, 107]
  polygons after Densify: rows=2 with_curves=0 vertices=[101, 107]
== buffers written to memory ==  (identical)
```

A buffered point is one true curve, read as two vertices, as the architect saw in Pro; a
buffered line is straight segments, as in Pro; a buffered polygon had no curve on the
image where the architect saw curved corners in Pro, both recorded as observed (W29).
Densify's offset method at one centimetre makes the ten-metre circle 37 segments and
`hasCurves` false, in both workspaces, so the acceptance test of every curve-producing
method is viable. Vertex counts of curve-free rows were unchanged; whether their
coordinates were is W30.

### W26 and W27, the date stores, 2026-11-09

```
== W26, precision 0, 1000 whole seconds written ==
read back: 1000; with a microsecond part: 118
of those, engine equality on the rounded second: {'selected by the rounded literal': 118}
control, 52 exact reads selected by their own literal: 52
== W27, precision 1, 1015 values written, 1015 read ==
  millisecond-aligned: exact: 792      millisecond-aligned: other: 208
  sub-millisecond: truncated to the millisecond: 9   rounded: 4   other: 2
== W27, memory, precision 0, 1015 values written, 1015 read ==
  millisecond-aligned: exact: 842      millisecond-aligned: other: 158
  sub-millisecond: truncated to the millisecond: 9   rounded: 4   other: 2
```

**W26, settled.** The engine's equality on the rounded second selects every one of the
118 reads that came back a microsecond off, so `select` and `read_rows` agree on every
row of a whole-second store (PC-D17); the compiler's docstring states it.

**W27, the fraction store is milliseconds with the same noise.** A fifth of the
millisecond-aligned values read back a few microseconds off, in the file geodatabase at
`precision` 1 and in the memory workspace alike; the `stamps` case passed because one
half is exact in binary. For a sub-millisecond value handed raw to the cursor the
engine's result is mixed and unreadable through the noise, which does not matter: under
A33 `write_rows` truncates to the millisecond itself. The reader's rule therefore
generalises to a store grain per field, a second at `precision` 0, a millisecond at
`precision` 1 and in the memory workspace, `read_rows` rounding to it; the architect
agreed (2026-11-09: second accuracy is enough, as long as the original values are
preserved and nothing crashes). It lands after the probe's next run shows the engine's
equality on the millisecond-rounded literal selects the noisy reads, which the probe now
counts, since the rule rests on `select` and `read_rows` agreeing at that grain too.

### What landed with B33's closing, 2026-11-09

- `ports/geometry.py` refuses a polygon ring under four coordinates or a line under two,
  on every ring; the codec reports the refusal as the row's `PortContractError`. Tests
  on the value (empty, one, two and three coordinates, as exterior, hole and member; a
  one-coordinate line and member; the shortest valid parts) and on the codec; break-once
  P31 and P32.
- ADR-0019 PC-D30 added beside PC-D27. Direction affected: no.
- B33 closed with the counts and the sources ingest has to clean; B34 opened for the
  port methods ingest's order needs and the removed-at-ingest case.
- T3.4: lineage first, cleanup after, read last, with the order and why; the densify
  rule with W30; the repair rule with W31. T4.11: the millisecond truncation in
  `write_rows`, the densify-your-output rule and its acceptance, W29.
- The writer's docstring states the store's grain and drops "nothing is reduced"; the
  compiler's states the W26 fact.
- `w26_w27_date_store_probe.py` gains the select count at the millisecond grain.

### The millisecond grain, 2026-11-09

The probe's second run, same digest, the new lines:

```
precision 1:  millisecond-aligned reads that came back off: 208;
              selected by engine equality on the millisecond-rounded literal: 208
              control, 53 exact reads selected by their own literal: 57
memory:       millisecond-aligned reads that came back off: 158;
              selected by engine equality on the millisecond-rounded literal: 158
              control, 53 exact reads selected by their own literal: 57
```

Every noisy read is selected by the engine's equality on its millisecond, so `select`
and `read_rows` agree at that grain as at the second (PC-D17). The control's 57 rows for
53 literals is the store holding milliseconds: the sub-millisecond probe values collapse
onto their millisecond, so a literal for one of those selects its neighbours too.

Landed: `DescribedDataset.date_grains`, a `DateGrain` per declared date field,
`SECOND` at `precision` 0 and `MILLISECOND` at `precision` 1 and in the memory
workspace, replacing the whole-second set; `read_rows` rounds to the field's grain. Unit
tests on both grains on both sides of the grain and across the second; the marked
`test_row_io.py` asserts an exact read of a millisecond-aligned value that is not exact
in binary, replacing the one-millisecond window; break-once R3, R4, D5 and D6 follow the
changed lines. A33.2's millisecond line, approved by the architect word for word and
applied. The marked run of the refusal, 47 passed, before this landed; the three
changed marked tests await the next.

W-items opened here: W28 the count (done), W29 the Pro observation against the image,
W30 Densify on curve-free rows, W31 the repair tool on a ring under four coordinates.

## Records

- ADR-0019 PC-D17 adapted per A33.1: `DATE` carried to microsecond precision, an adapter
  whose store holds less stating its precision, a round trip identity to the coarser side.
  Direction affected: no.
- ADR-0019 PC-D22 adapted: `write_rows`'s `Schema` names a feature class's CRS and
  geometry family, so an empty dataset is created from the schema alone. PC-D25 adapted:
  polygon rings canonical on construction, a round trip identity on every adapter, line
  direction untouched. PC-D26 adapted: a row's geometry is held to the schema's CRS and
  family. Direction affected: no, on all three.
- B31 and B32 closed in `DECISIONS.md`, their opening text kept.
- T4.11's status and follow-up paragraph in `TASKS.md`.
- The timing evidence: the `orient` variant's retirement, the plain-form note on B32's
  price, the W23 row.
- B33 is re-assessed before the pull request and is not touched here.
