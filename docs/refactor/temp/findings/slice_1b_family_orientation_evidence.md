# Slice 1b evidence: geometry family and canonical orientation

**Status:** EVIDENCE, 2026-11-08, the marked run green; the W24 and W25 probe output
pending. B31 (the geometry family on `Schema`) and B32 (canonical ring orientation in
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

## Records

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
