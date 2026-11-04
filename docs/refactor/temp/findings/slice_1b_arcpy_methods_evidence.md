# Slice 1b evidence: the ArcPy adapter's first methods

**Status:** EVIDENCE, 2026-11-04. Produced for the second pull request of slice 1b (the
capability record `ports/capabilities.py` and `capabilities()` in each adapter package, the
row-shape reader `declared_rows`, the shared `adapters/_shared/preconditions.py`, the stub's
first four declarations, `support/dataset_schema.py`, `support/geometry_values.py`,
`support/predicate_compiler.py`, the group modules `geometry_ops/selection.py`,
`geometry_ops/shape.py` and `table_ops/row_io.py` with their composed classes, the
whole-second date rule in `adapters/_shared/field_values.py`, the unit tests on the fake
engine `tests/support/fake_arcpy.py`, `tests/static/test_capabilities.py`, ADR-0019
Direction 5, PC-D17's precision clause, PC-D27, PC-5 with PC-D28 and PC-D29, A14.1 in the
moved form and B30) by `python -m tools.break_once arcpy_adapter`, whose case table is
`tools/break_once/cases/arcpy_adapter.py` (A30). Every guard broken once, with the covering
tests failing, then restored; `git status` showed the mutated files unchanged after the run,
and the set's suite was green after the last restore. No engine ran in this PR: every test is
unmarked and runs on the fake engine installed as `arcpy` through `sys.modules` for the
test's duration, or on pyright. B23 stays open and is not needed here. The by-hand checks and
the cases carried to the first run under the engine follow the report.

Case set `arcpy_adapter`, run by `python -m tools.break_once arcpy_adapter`. Per case: its targets pass on the clean tree (baseline), one source file is edited to remove the guard, the same targets must then fail, and the file is restored. The set's suite runs after the last restore.

### D1: Z and M not refused

File: `src/ag/adapters/arcpy/support/dataset_schema.py`. Edit: `if raw.has_z or raw.has_m:` -> `if False:`.

Targets: test_describe_refuses_before_any_row[z], test_describe_refuses_before_any_row[m]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=message) as caught:
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_dataset_schema.py::test_describe_refuses_before_any_row[z]
FAILED tests/unit/adapters/arcpy/test_dataset_schema.py::test_describe_refuses_before_any_row[m]
2 failed in 0.02s
```

### D2: an unrepresentable field dropped instead of recorded

File: `src/ag/adapters/arcpy/support/dataset_schema.py`. Edit: `unrepresentable[name] = engine_type` -> `pass`.

Targets: test_an_unrepresentable_field_is_recorded_not_refused_until_named. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert dataset.unrepresentable == {"GlobalID": "GlobalID", "big": "BigInteger"}
E       AssertionError: assert mappingproxy({}) == {'GlobalID': ... 'BigInteger'}
E         Right contains 2 more items:
E         {'GlobalID': 'GlobalID', 'big': 'BigInteger'}
E         Use -v to get more diff
FAILED tests/unit/adapters/arcpy/test_dataset_schema.py::test_an_unrepresentable_field_is_recorded_not_refused_until_named
1 failed in 0.02s
```

### V1: a non-planar type code accepted

File: `src/ag/adapters/arcpy/support/geometry_values.py`. Edit: `if code not in _KINDS:` -> `if False:`.

Targets: test_what_the_port_cannot_hold_is_refused_naming_the_row[z], test_what_the_port_cannot_hold_is_refused_naming_the_row[circular-string]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           geometry_from_wkb(data, crs=CRS, where="'roads' row 3")
>       member_code = _MEMBER_OF[code]
E       KeyError: 1001
E       KeyError: 8
FAILED tests/unit/adapters/arcpy/test_geometry_values.py::test_what_the_port_cannot_hold_is_refused_naming_the_row[z]
FAILED tests/unit/adapters/arcpy/test_geometry_values.py::test_what_the_port_cannot_hold_is_refused_naming_the_row[circular-string]
2 failed in 0.02s
```

### V2: a multipolygon member with holes flattened instead of refused

File: `src/ag/adapters/arcpy/support/geometry_values.py`. Edit: `if len(member) > 1:` -> `if False:`.

Targets: test_what_the_port_cannot_hold_is_refused_naming_the_row[member-with-hole]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=message) as caught:
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_geometry_values.py::test_what_the_port_cannot_hold_is_refused_naming_the_row[member-with-hole]
1 failed in 0.01s
```

### P1: the value check against the field removed

File: `src/ag/adapters/arcpy/support/predicate_compiler.py`. Edit: `reason = type_mismatch(value=value, field=field)` -> `reason = None`.

Targets: test_check_refuses_before_anything_compiles[wrong-type], test_check_refuses_before_anything_compiles[long-overflow]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=message):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_check_refuses_before_anything_compiles[wrong-type]
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_check_refuses_before_anything_compiles[long-overflow]
2 failed in 0.02s
```

### P2: LIKE allowed on a non-text field

File: `src/ag/adapters/arcpy/support/predicate_compiler.py`. Edit: `if field.type is not FieldType.TEXT:` -> `if False:`.

Targets: test_check_refuses_before_anything_compiles[like-on-number]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=message):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_check_refuses_before_anything_compiles[like-on-number]
1 failed in 0.02s
```

### P3: the empty IsIn compiled as IN ()

File: `src/ag/adapters/arcpy/support/predicate_compiler.py`. Edit: `if not values:` -> `if False:`.

Targets: test_the_clause[empty-in], test_the_clause[not-empty-in]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert compiled(where, session=session, dataset=dataset) == clause
E       assert '"rank" IN ()' == '("rank" IS N... IS NOT NULL)'
E         - ("rank" IS NULL AND "rank" IS NOT NULL)
E         + "rank" IN ()
E       assert 'NOT ("rank" IN ())' == 'NOT (("rank"...IS NOT NULL))'
E         - NOT (("rank" IS NULL AND "rank" IS NOT NULL))
E         + NOT ("rank" IN ())
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_the_clause[empty-in]
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_the_clause[not-empty-in]
2 failed in 0.02s
```

### P4: a sub-second date accepted by the shared rule, so one adapter truncates

File: `src/ag/adapters/_shared/field_values.py`. Edit: `if value.microsecond:` -> `if False:`.

Targets: test_a_sub_second_date_is_refused_not_truncated, test_check_refuses_what_the_adapter_cannot_evaluate[sub-second-date], test_a_row_that_does_not_fit_the_schema_is_refused[sub-second-date]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=r"replace\(microsecond=0\)"):
E       Failed: DID NOT RAISE PortContractError
>       with pytest.raises(PortContractError, match=reason):
FAILED tests/unit/adapters/arcpy/test_predicate_compiler.py::test_a_sub_second_date_is_refused_not_truncated
FAILED tests/unit/adapters/fakes/memory/test_predicate_eval.py::test_check_refuses_what_the_adapter_cannot_evaluate[sub-second-date]
FAILED tests/unit/adapters/fakes/memory/test_store.py::test_a_row_that_does_not_fit_the_schema_is_refused[sub-second-date]
3 failed in 0.03s
```

### S1: select compiles without checking the predicate

File: `src/ag/adapters/arcpy/geometry_ops/selection.py`. Edit: `check(where, dataset=dataset)` -> `pass`.

Targets: test_a_bad_predicate_is_refused_before_any_tool_runs. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_a_bad_predicate_is_refused_before_any_tool_runs
1 failed in 0.02s
```

### S2: select does not check its paths

File: `src/ag/adapters/arcpy/geometry_ops/selection.py`. Edit: `distinct_paths(handles=(input, output))` -> `pass`.

Targets: test_select_refuses_an_output_on_the_input_path. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="both name"):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_select_refuses_an_output_on_the_input_path
1 failed in 0.02s
```

### X1: a null shape reaches the tool

File: `src/ag/adapters/arcpy/geometry_ops/shape.py`. Edit: `_refuse_null_shapes(self._session, path=source)` -> `pass`.

Targets: test_explode_refuses_a_null_shape_before_the_tool_whether_or_not_parents_asked, test_an_empty_shape_counts_as_null. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(EmptyGeometryError) as caught:
E       Failed: DID NOT RAISE EmptyGeometryError
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_explode_refuses_a_null_shape_before_the_tool_whether_or_not_parents_asked
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_an_empty_shape_counts_as_null
2 failed in 0.02s
```

### X2: a table input and shared paths accepted

File: `src/ag/adapters/arcpy/geometry_ops/shape.py`. Edit: `distinct_paths(handles=handles)` -> `pass`; `if before.schema.data_type is not DataType.FEATURE_CLASS:` -> `if False:`.

Targets: test_explode_refuses_a_table_and_handles_on_one_path. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           yield
>               raise RuntimeError(
E               RuntimeError: A column was specified that does not exist. [SHAPE@WKB]
>           ops.explode_multipart(
>           raise EngineError(
                f"arcpy: {what} failed: {error}",
E           ag.ports.errors.EngineError: arcpy: SearchCursor failed: A column was specified that does not exist. [SHAPE@WKB]
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_explode_refuses_a_table_and_handles_on_one_path
1 failed in 0.03s
```

### X3: the reference field assumed instead of found: any added field accepted

File: `src/ag/adapters/arcpy/geometry_ops/shape.py`. Edit: `if len(added) != 1:` -> `if not added:`.

Targets: test_a_tool_that_adds_two_fields_is_an_engine_error. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(EngineError, match="one reference field was expected") as caught:
E       Failed: DID NOT RAISE EngineError
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_a_tool_that_adds_two_fields_is_an_engine_error
1 failed in 0.02s
```

### X4: the output's own engine fields counted as added

File: `src/ag/adapters/arcpy/geometry_ops/shape.py`. Edit: `if name not in before.all_fields and name not in after.engine_fields` -> `if name not in before.all_fields`.

Targets: test_the_reference_diff_ignores_the_output_engine_fields. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       ArcpyGeometryOps(session=session).explode_multipart(
>           raise EngineError(
E           ag.ports.errors.EngineError: arcpy: management.MultipartToSinglepart added ['Shape_Length', 'ORIG_FID'] to 'exploded'; one reference field was expected.
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_the_reference_diff_ignores_the_output_engine_fields
1 failed in 0.02s
```

### X5: the reference field kept on the output

File: `src/ag/adapters/arcpy/geometry_ops/shape.py`. Edit: `self._session.run_tool(` -> `pass`.

Targets: test_explode_without_parents_runs_the_tool_and_drops_the_reference. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert engine.tool_names() == [
E       AssertionError: assert ['management....ToSinglepart'] == ['management.....DeleteField']
E         Right contains one more item: 'management.DeleteField'
E         Use -v to get more diff
FAILED tests/unit/adapters/arcpy/test_geometry_ops.py::test_explode_without_parents_runs_the_tool_and_drops_the_reference
1 failed in 0.02s
```

### R1: read_rows opens the cursor on an unchecked field

File: `src/ag/adapters/arcpy/table_ops/row_io.py`. Edit: `declared_field(dataset, name)` -> `pass`.

Targets: test_read_rows_refuses_a_field_before_the_cursor_opens[undeclared], test_read_rows_refuses_a_field_before_the_cursor_opens[unrepresentable]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match=message):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_table_ops.py::test_read_rows_refuses_a_field_before_the_cursor_opens[undeclared]
FAILED tests/unit/adapters/arcpy/test_table_ops.py::test_read_rows_refuses_a_field_before_the_cursor_opens[unrepresentable]
2 failed in 0.02s
```

### R2: the cursor iterated outside the guard

File: `src/ag/adapters/arcpy/table_ops/row_io.py`. Edit: `with session.guard("SearchCursor"):` -> `if True:`.

Targets: test_a_cursor_failure_mid_read_leaves_as_an_engine_error, test_tree_is_clean[adapters-arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>           next(iterator)
>               raise RuntimeError("The cursor failed mid-read.")
E               RuntimeError: The cursor failed mid-read.
>       assert [found.render() for found in findings] == []
E       assert ["table_ops/r...sion's guard"] == []
E         Left contains one more item: "table_ops/row_io.py:61: [arcpy-session-only] `arcpy` is referenced outside the session's guard"
E         Use -v to get more diff
FAILED tests/unit/adapters/arcpy/test_table_ops.py::test_a_cursor_failure_mid_read_leaves_as_an_engine_error
FAILED tests/static/test_source_scans.py::test_tree_is_clean[adapters-arcpy]
2 failed in 0.04s
```

### R3: a sub-second date read through and truncated on the next write

File: `src/ag/adapters/arcpy/table_ops/row_io.py`. Edit: `if isinstance(value, datetime) and value.microsecond:` -> `if False:`.

Targets: test_a_sub_second_date_read_is_refused_naming_the_field_and_the_row. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       with pytest.raises(PortContractError, match="'roads' row 1: 'surveyed' holds"):
E       Failed: DID NOT RAISE PortContractError
FAILED tests/unit/adapters/arcpy/test_table_ops.py::test_a_sub_second_date_read_is_refused_naming_the_field_and_the_row
1 failed in 0.02s
```

### C1: the record leaves out a method the adapter honours parents for

File: `src/ag/adapters/arcpy/__init__.py`. Edit: `frozenset({GeometryOps.explode_multipart})` -> `frozenset[PortMethod]()`; `from ag.ports.capabilities import AdapterCapabilities` -> `from ag.ports.capabilities import AdapterCapabilities, PortMethod`.

Targets: test_the_record_names_every_mint_method_the_adapter_implements_and_no_other[arcpy]. Baseline: passed.

Result: **FAILED as expected** (exit 1)

```
>       assert build().parents_for == expected
E       assert frozenset() == {<function Ge...7352d6218d60>}
E         Extra items in the right set:
E         <function GeometryOps.explode_multipart at 0x7352d6218d60>
E         Use -v to get more diff
FAILED tests/static/test_capabilities.py::test_the_record_names_every_mint_method_the_adapter_implements_and_no_other[arcpy]
1 failed in 0.04s
```

### After the last restore

```
235 passed in 2.55s
```

## By hand

### The static matrix for the ArcPy adapter

The three conformance assignments under `TYPE_CHECKING`, `ArcpyGeometryOps` as
`GeometryOps`, `ArcpyTableOps` as `TableOps` and `ArcpyCartographicOps` as
`CartographicOps`, in the port packages and in `tests/static/test_adapter_groups.py`,
pass the pyright hook. Dropping `Shape` from `ArcpyGeometryOps`'s bases on a scratch copy
reported `"explode_multipart" is not present` on the assignment, and the runtime matrix test
reported the method implemented by no group; both restored.

### The case tables after the needle edits

`tools/break_once/cases/row_shape.py` matches the decorator's `setattr(fn, _ATTRIBUTE, ...)`
line and `cases/memory_adapter.py` the shared `distinct_paths`:

```
$ uv run --locked --extra dev python -m tools.break_once row_shape --check
break-it-once: 17 cases in 1 set(s); needles match, targets collect
$ uv run --locked --extra dev python -m tools.break_once arcpy_adapter --check
break-it-once: 19 cases in 1 set(s); needles match, targets collect
$ uv run --locked --extra dev python -m tools.break_once --check
break-it-once: 161 cases in 8 set(s); needles match, targets collect
```

## Carried to the first run under the engine

The adapter's assumptions about the engine are expectations until a marked run confirms
them; each is named in the docstring that depends on it. To run under an ArcGIS Pro Python
environment once B23 is settled, beside W1 to W6 of the session evidence:

- **W7** `LIKE` is case-sensitive in a file geodatabase and in the memory workspace, with `%`
  and `_` as the only wildcards and no escape character.
- **W8** The date literal `date 'YYYY-MM-DD HH:MM:SS'` is accepted by the memory workspace as
  by a file geodatabase; `AddFieldDelimiters` answers with double quotes for both.
- **W9** `Describe` reports `lengthFieldName` and `areaFieldName` as empty strings where a
  feature class has no such field; the type names it reports for the five field types are
  the spellings `FIELD_TYPES` holds; and the exception class for a path that does not exist.
- **W10** `analysis.Select` and `analysis.TableSelect` take the keyword names the adapter
  passes, and their output carries the input's declared fields and no other.
- **W11** `management.MultipartToSinglepart` keeps a GlobalID field as it is, adds no field
  but the reference, and the name it chooses when `ORIG_FID` is already taken; the diff in
  `shape.py` finds that name.
- **W12** `SHAPE@WKB`: a null shape arrives as None; an empty shape as None or as an empty
  WKB; a true curve is densified or arrives as a curve code; the type codes the engine writes
  for Z and M geometry, which the dataset-level refusal should make unreachable.
- **W13** An insert cursor accepts `SHAPE@WKB` bytes, which is what the `.gdb` builders of the
  next pull request rely on.
- **W14** On the `read_rows` timing run: one guard around a streamed cursor against the bare
  cursor; the WKB parse per row; `Describe`'s time per call on a file geodatabase and on the
  memory workspace, against a budget of a few hundred calls per stage; and the null-shape
  pre-pass of `explode_multipart` against the tool's own time on the timing dataset. Within
  one call no path is described twice and a cache across calls goes stale on every write, so
  if `Describe` proves costly the lever is a narrower read of the output's field list, not a
  cache.
- **W15** The reference field holds the input's `OBJECTID` values: on a `.gdb` input whose
  `OBJECTID`s are non-dense after deletes, `select` then `explode_multipart`, the `PARENT_ID`s
  are the pre-call index set and the input's index set is unchanged. This is the conformance
  case of T4.11 (1a), run as such in the next pull request.
- **W16** The `dataType` strings `Describe` reports for a feature class and a table in the
  memory workspace; `_DATA_TYPES` maps `FeatureClass` and `Table` only.
- **W17** The `hasZ` and `hasM` flags of every production source, since the refusal reads the
  dataset's flag and not its values.
- **W18** The precision a file geodatabase date field holds and whether a date literal with a
  fraction is accepted; and whether any production source's date fields return sub-second
  values, the editor-tracking fields in particular. The port carries dates to the whole
  second either way; the read side refuses a fraction rather than truncate it, and
  truncation can replace the refusal in one function if sources carry fractions.

## Deferred by name

- The spatial leaf of `select`: `NotImplementedError` from the compiler until its first
  caller; the route is the engine's layer selection with negation pushed to the leaves.
- A dialect check on the workspace type: not built. The compiler writes the file geodatabase
  dialect and the memory workspace is expected to share it (W8); an enterprise geodatabase
  needs two Describe properties the first run has not confirmed.
- The write direction of the WKB codec: with the builders of the next pull request.
- `ParentsUnavailableError` has no raiser yet: every method the record names honours
  `parents=`, and the next `MINT` method decides.
- Holes in multipolygon members: B30.
