# Slice 1b evidence: the engine run, first pull request

**Status:** EVIDENCE IN PROGRESS, 2026-11-04. For the third pull request of slice 1b, cut in
two with the architect: this one holds the `.gdb` builders (`tests/support/arcpy/gdb.py`,
`tests/support/gdb_cases.py`), the conformance suite over both adapters
(`tests/conformance/`), the engine-expectation tests (`tests/engine/arcpy/`), the support
writer the builders and `shape.py` share (`adapters/arcpy/support/dataset_writer.py`), the
session's `read_environment`, `PARENTS_SCHEMA` in `ports/table_ops.py`, the stub's
`da.UpdateCursor`, the split of the mixed `parts()` case into one case per engine geometry
type, and B23. The second holds `tools/time_read_rows.py` with W14, and every code change a
W-item forces that no test here needs.

No engine ran in WSL, where this file was written: every output below is from the sandbox
without ArcPy. The marked tests have not run. The architect runs them under ArcGIS Pro and
pastes the output into the section "The Pro run" below; nothing in this file claims an
engine result it has not been shown.

## What the batch adds, and why it needs no break-once case

No new guard: `create_table`, `add_fields` and `insert_rows` carry no port rule of their own
(PC-D26's row checks arrive with `write_rows`); `read_environment` reads back and refuses
nothing but a unit it cannot parse, which is an adapter defect; the stub's `UpdateCursor`
adds a declared name, and `tests/static/test_arcpy_stub.py` pins refused lines, not
declared ones. The existing cases still match:

```
$ uv run --locked --extra dev python -m tools.break_once --check
break-it-once: 161 cases in 8 set(s); needles match, targets collect
```

## By hand, in WSL

### Collection without the engine

Every module under `tests/engine/` and `tests/conformance/` imports the builders inside a
fixture or a method; `gdb.py` imports `arcpy` inside each function, under the guard. The
hook's selection collects and runs; a bare run of the engine root skips every test with the
import error as the reason.

```
$ uv run --locked --extra dev pytest -m "not arcpy" --collect-only -q | tail -1
495/530 tests collected (35 deselected) in 0.12s
$ uv run --locked --extra dev pytest -m "not arcpy" -q | tail -1
495 passed, 35 deselected in 2.93s
$ uv run --locked --extra dev pytest tests/engine -q | tail -1
14 skipped in 0.03s
```

The 35 deselected are the 21 ArcPy parameters of the conformance suite and the 14 engine
tests. The 21 memory parameters pass.

### The engine root type-checks without the engine

`tests/engine/` imports the engine nowhere, so it sits under the root pyright environment
with no stub. Probed on a scratch copy of that environment: a test reaching the engine
through `open_session` is clean; a test with `import arcpy` and `arcpy.env.XYTolerance`
fails strict pyright, which is the enforcement the rest of `tests/` already relies on.

```
test_b.py:5:11 - error: "env" is not a known attribute of module "arcpy" (reportAttributeAccessIssue)
3 errors, 0 warnings, 0 informations      (the import-arcpy probe)
0 errors, 0 warnings, 0 informations      (the adapter-only probe)
```

### The builders' root and `tests.*`

A module under `tests/support/arcpy/` cannot import `tests.support.cases` under its pyright
environment (`reportMissingImports`, probed), and a relative import resolves there (probed,
clean). Neither is used: the builders take a `Schema` and cell tuples, and
`tests/support/gdb_cases.py`, outside that root, encodes a case's rows and joins the two.

### Row 5 and `PARENTS_SCHEMA`

The agreed home, `ports/columns.py`, sits below `table_ops` in the row 5 layers
(`.importlinter`: `predicates | row_shape | columns` under `geometry_ops | table_ops |
graph_ops`), so a `Schema` there would import upward. The constant sits in
`ports/table_ops.py` beside `Schema`, importing the column names downward, and cites
RS-D16; the memory adapter imports it and the ArcPy adapter writes it through the support
writer. `lint-imports`: 24 kept, 0 broken.

## The engine runs

### The image run, 2026-11-05

Run by the architect from WSL in the project's image, `arcpy-linux:12.1` built locally from
the same source as `ghcr.io/kartverket/arcpy-linux:12.1` (digest to be recorded). Python
3.13.17, ArcPy 12.1; `import arcpy` works in the bare image without `startserver.sh`, which
answers T4.11's licence question for the image route: no activation step. The pinned pytest
went into a target folder, never into the image's environment:

```
docker run --rm -v "$PWD":/work:ro -w /work \
  -e PYTHONPATH=/work/src:/tmp/pt -e PYTHONDONTWRITEBYTECODE=1 arcpy-linux:12.1 \
  bash -c 'pip install --quiet --no-cache-dir --target /tmp/pt pytest==9.1.1 &&
           python -m pytest tests/conformance tests/engine -m arcpy -ra -p no:cacheprovider'
collected 56 items / 21 deselected / 35 selected
7 failed, 28 passed, 21 deselected in 51.90s
```

A first attempt without the two roots named failed at collection: `-m arcpy` collects every
`testpaths` root and `tests/static/test_import_contracts.py` imports `importlinter`, which
the image lacks. The marked run names its roots wherever the dev tools are absent.

Passed: every conformance case but one (`select`, `LIKE`, the date literal, the table form,
both partitions, the non-dense input through `explode_multipart` and `select`, the null
shape, the table input, every field type, the kinds `roads`, `multilines`, `multipoints`,
`points`); the memory workspace (W16, W7, W8); the empty shape (W12); W1, W2, W4, W6.
Every seed worked, so W13 and W21 (the EPSG code as `spatial_reference`) hold on Linux.

The seven failures and what was done with each, under the rule below:

| test | observed | disposition |
|---|---|---|
| `test_read_rows_round_trips_each_geometry_kind[arcpy-polygons]` | the square with a hole read back as a two-member `MULTIPOLYGON`, one ring each; the two-member case matched | settled by the probe below: ring orientation; the case and the write side are oriented |
| `test_describe_of_a_missing_dataset_is_an_engine_error` | `OSError: "<path>" does not exist`, left unwrapped | fixed here: an exact `OSError` joins the guard's catch set with the no-drain rule; the fake's Describe raises it; unit tests pin both the wrap and that a subclass passes |
| `test_a_date_with_a_fraction_is_held_to_the_second_by_the_engine_or_refused` | 12:00:00.5 read back as 12:00:01 | the engine rounds a fraction to the second; the test now pins that, and `read_rows` returns the stored value; the read-side refusal cannot fire on file geodatabase data (W18) |
| `test_a_write_cursor_on_a_dataset_held_by_a_read_cursor_is_an_engine_error` | the insert succeeded | W3's provocation refuted; test and helper removed; no `RuntimeError` after engine work found, the drain rule stands unrefuted and the session docstring says so |
| `test_the_tool_keeps_a_global_id_field_and_adds_only_the_reference` | the output has no GlobalID field; the declared fields match | the tool drops GlobalID; test and `shape.py` docstring state it; nothing in the adapter depended on it |
| `test_the_reference_is_found_by_diff_when_orig_fid_is_taken` | the tool added no field | settled by the probe below: the tool writes into the existing field; `shape.py` refuses such an input before the tool; the test asserts the refusal |
| `test_a_multipart_polygon_with_holes_is_refused_as_one_row_and_explodes_with_them` | `read_rows` did not refuse | settled by the probe below: orientation, and a one-member multipolygon is stored as a polygon; the shape is now two members, oriented |

After these fixes and the probe's: 497 unit tests pass, 34 deselected, pyright and the
scans clean, the break-once needles match. The marked run is to be repeated on the image
before the commit point; every marked test is expected to pass.

### The probe, 2026-11-05

Image digest `arcpy-linux@sha256:eb53667b7b73076f3eb3e7547b3d35c94aa79fdd6afe5a002959f28d484f4575`,
a local build of the source pushed as `ghcr.io/kartverket/arcpy-linux:12.1`.
`docs/refactor/temp/w19_wkb_probe.py`, run as
`python docs/refactor/temp/w19_wkb_probe.py` with `src` and the root on the path, writes
five polygons and the test encoder's shape, reads them back and explodes them, then runs
the multipart tool over an input that already has `ORIG_FID`. A first attempt failed on
the probe's own 10-character name field, which showed one more cursor class on the way:
an over-long text in an insert cursor is an exact `RuntimeError`
(`The row contains a bad value. [Field length exceeded ...]`), wrapped by the guard.

```
== written ==                              == read back as SHAPE@WKB ==
single_ccw   type 3 rings=1 [CCW]          type 3 POLYGON rings=1 [CCW]
single_cw    type 3 rings=1 [CW]           None
hole_esri    type 3 rings=2 [CW, CCW]      type 3 POLYGON rings=2 [CCW, CW]
hole_ogc     type 3 rings=2 [CCW, CW]      type 3 POLYGON rings=2 [CCW, CW]
hole_same    type 3 rings=2 [CCW, CCW]     type 6 MULTIPOLYGON members=2, one ring each [CCW]; [CCW]
encoder      type 6 members=1 rings=2 [CCW, CCW]   type 6 MULTIPOLYGON members=2, one ring each
== children of MultipartToSinglepart ==
single_cw    parent=2 None; every holed input: one child, type 3 rings=2 [CCW, CW]
== ORIG_FID already a field ==
output fields: ['OBJECTID', 'Shape', 'name', 'ORIG_FID', 'Shape_Length']
output rows (OID@, name, ORIG_FID): (1, a, 1) (2, b, 2) (3, b, 2) (4, b, 2) (5, e, 3) (6, e, 3)
input ORIG_FID values after the tool: 99, 99, 99
```

What it settles:

- **W19, polygons.** A single polygon exports as type 3 and a multipolygon as type 6, as
  lines export as 2 and 5 (the image run). Kinds round-trip; the codec stands and the
  `polygons` id of the kind test passes once the case is oriented.
- **Ring orientation is semantic on write.** The engine reads a WKB ring's role from its
  orientation, not its position: exterior counter-clockwise, hole clockwise. Two
  counter-clockwise rings become two exterior members; a lone clockwise ring becomes an
  empty shape; a clockwise exterior with a counter-clockwise hole is repaired by area.
  On read the engine writes exterior counter-clockwise and holes clockwise. So the write
  side orients: `tests/support/wkb.py` gains `oriented`, the builders' glue applies it,
  `polygons()` and `multipolygon_with_hole()` are written in that orientation, and
  `TableOps.write_rows` inherits the step. Nothing in the codec or the port changes.
- **A one-member multipolygon is stored as a polygon** and exports as type 3. "A lake with
  islands arriving as one row" therefore means a multipolygon with two or more members,
  one of them holed; `multipolygon_with_hole()` is now that shape, and T4.11 (1c) reads:
  refused as one row, and after `explode_multipart` the children are the holed polygon
  and its neighbour, each type 3 with its rings.
- **`ORIG_FID` taken.** The tool writes its parent reference into the existing field and
  adds nothing: the output's `ORIG_FID` holds the parents, the input's 99 is gone from the
  output. `shape.py` refuses such an input before the tool runs, with `PortContractError`
  naming the field, so the output's attributes are never changed silently; the diff that
  finds the added field stays as the check that the tool added exactly one. This is a new
  guard and needs a break-once case; the exact case text is in the end-of-task report
  and waits on the architect's request to edit `tools/break_once/cases/arcpy_adapter.py`.

B-item candidate for the architect, beside the `write_rows` geometry-type item: whether
ring orientation is part of the `Geometry` contract (a value is canonical, exterior
counter-clockwise and holes clockwise, and a round trip is identity) or an adapter
concern at the boundary (the write side orients, and a value may come back with its rings
reversed). PC-D25 says adapters convert at the boundary; the codec's "nothing depends on
ring orientation" holds on read only.

### The Pro run

To be run by the architect when a Windows Pro environment is at hand; the image run above
is the gate's environment and this one the divergence detector. The environment is B23; the two candidates to try on one
Windows machine, from the repository root, with `<pro>` the Pro interpreter
(`C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3\python.exe` on the team's machines):

```
# (a) a venv over the Pro interpreter
<pro> -m venv --system-site-packages .venv-pro
.venv-pro\Scripts\python.exe -m pip install -e . pytest==9.1.1
.venv-pro\Scripts\python.exe -m pytest -m arcpy -p no:cacheprovider -ra

# (b) a target folder beside the Pro interpreter
uv pip install --target .pytest-pro --python <pro> pytest==9.1.1
set PYTHONPATH=src;.pytest-pro
<pro> -m pytest -m arcpy -p no:cacheprovider -ra
```

Then once, the bare run in the same environment, both buckets in one session, which
confirms that the unit fixture's fake and the real engine coexist:

```
<python> -m pytest -q
```

Paste here: the command that worked, its full `-ra` output, and the bare run's last line.

### The rule for a marked test the run fails

Every marked test passes at the commit point. A failure whose fix is inside the adapter's
engine-facing assumption, the catch set, a spelling, the empty-shape handling, is fixed in
this pull request. A failure that opens a contract question, W19's kind or W18's
truncation, removes that test from this pull request, records the observation in the
dependent docstring, names the test and its question in T4.11's status, and goes to the
architect. No `xfail` and no `skip` anywhere but the conftest's marker skip.

## The W-items and where each is answered

| item | where | changes code if it fails |
|---|---|---|
| W1 misspelt keyword after a success | `engine/arcpy/test_session.py::test_a_misspelt_keyword_after_a_successful_tool_is_a_type_error_unwrapped` | `run_tool` |
| W2 a failure's own lines | `test_session.py::test_a_tool_failure_after_a_success_carries_its_own_messages` | the drain rule |
| W3 a `RuntimeError` after engine work | tried as a write cursor under a held read cursor: the engine allowed the write (image run); the test is removed and W3 recorded as unrefuted | the drain rule |
| W4 the environment read back | `test_session.py::test_the_environment_reads_back_as_applied`, against `ENVIRONMENT` as committed (EPSG 25833, 0.1 m, 0.01 m, overwrite on) | `_apply` |
| W5 the probe module under the Pro interpreter | by hand: open `src/ag/adapters/arcpy/session.py` under the Pro interpreter in the editor and confirm the stub applies | `pyproject.toml` |
| W6 the cursor exception classes | `test_session.py`: the missing-field and bad-clause tests, `type(error.__cause__) is RuntimeError`, passed on the image; an over-long text in an insert cursor is the same class (the probe); the lock is W3 | the catch set |
| W7 `LIKE` semantics | conformance `test_like_is_case_sensitive_with_percent_and_underscore_as_its_wildcards`; the memory workspace in `test_memory_workspace.py` | the compiler |
| W8 the date literal, the delimiters | conformance `test_a_date_comparison_selects_to_the_whole_second`; the memory workspace in `test_memory_workspace.py` | the compiler |
| W9 Describe's names and spellings; the missing path | conformance round trips (`test_read_rows_round_trips_every_field_type`, every seed), passed on the image; `test_dataset_schema.py::test_describe_of_a_missing_dataset_is_an_engine_error`: `OSError`, now in the catch set | `FIELD_TYPES`, the catch set |
| W10 the select tools' keywords and output fields | conformance `test_select_*` | `selection.py` |
| W11 GlobalID kept; `ORIG_FID` taken | `test_shape.py`: GlobalID is dropped by the tool (image run); with `ORIG_FID` already a field the tool writes into it and adds nothing (probe), so `shape.py` refuses that input | the diff in `shape.py` |
| W12 null, empty and curve shapes | null: conformance `roads()` round trip; empty: `test_row_io.py::test_an_empty_shape_arrives_as_none_or_an_empty_wkb_and_reads_as_null`; curves: by hand, second pull request | the codec |
| W13 the insert cursor takes `SHAPE@WKB` | every seed of a feature class | the builders |
| W14 timing | second pull request | |
| W15 the non-dense input | conformance `test_a_mint_method_on_a_non_dense_input_reports_the_pre_call_indices_unchanged`, `explode_multipart` directly and `select` on the same input | A9.2's line |
| W16 the memory workspace's `dataType` strings | `test_memory_workspace.py::test_describe_reports_a_memory_feature_class_and_table_as_the_port_sees_them` | `_DATA_TYPES` |
| W17 `hasZ`/`hasM` of production sources | by hand, over the production sources | |
| W18 date precision | `test_row_io.py::test_a_date_with_a_fraction_is_rounded_to_the_second_by_the_engine`: a file geodatabase holds seconds and the engine rounds (image run); production sources by hand | read-side truncation, a contract question |
| W19 (new) the WKB code for single-part lines and polygons: 2 and 3, or a one-member 5 and 6 | conformance `test_read_rows_round_trips_each_geometry_kind`, one id per kind: lines and points round-trip as written (image run); polygons as type 3 and multipolygons as type 6 (probe); ring orientation is semantic on write, see the probe | the codec: no change |
| W20 (new) the output kind of exploding a multipoint class, and whether the tool takes a one-member multipoint | conformance partition test, id `points` | the memory adapter's `_single_parts` or the contract |
| W21 (new) `CreateFeatureclass` takes the EPSG code as `spatial_reference`, and mixed-separator paths (`C:\...\x.gdb/name`) are accepted | every seed of a feature class | the builders; `SpatialReference` into the stub if not |

What the codec does today under W19's two outcomes, stated before the run: with codes 2
and 3, kinds round-trip on both adapters and the holed polygon after `explode_multipart`
reads as `POLYGON` with its rings; with 5 and 6 for every line and polygon, every line row
reads back `MULTILINESTRING` on ArcPy and `LINESTRING` on memory, the children of
`explode_multipart` differ in kind between the adapters, and a one-member multipolygon with
holes is refused by the member check in `geometry_values.py`, so T4.11 (1c) fails. The
candidate responses, collapsing a one-member multi to its single kind or accepting the
engine's kind in the contract, are the architect's to choose.

## Record edits waiting on the run

Each with a per-item summary first: T4.11's status (the halves that ran, and any test
removed with the question it waits on); T2.1's status (the compile confirmed by W7, W8 and
W10); B23 closed with the environment that worked; `testing.md`'s "Running the ArcPy tests"
with the command; A9.2's contract line in `ports/table_ops.py` with what W15 showed; T4.11
gains the step that moves `CreateFeatureclass` and `GEOMETRY_TYPES` from the builders into
the adapter when `write_rows` lands and switches the builders to it; a B-item candidate for
the architect to open: how `write_rows` learns a feature class's geometry type (a `Schema`
field or inference, the empty dataset undecided) and whether `MemoryStore.write` refuses
what every engine refuses, one geometry type per feature class, which is what let the mixed
`parts()` case pass as engine-neutral until this pull request.

## Deferred by name

- The write direction of the WKB codec in the adapter, and `CreateFeatureclass` in the
  adapter: with `write_rows` (PC-D22). The builders carry both until then, stated in their
  module docstring.
- W14 and `tools/time_read_rows.py`: the second pull request.
- B28, B30 untouched; B29 unwritten.
- RS-D16's text: unchanged; the architect may adapt it to name `PARENTS_SCHEMA` (summary
  presented 2026-11-04, not applied).
