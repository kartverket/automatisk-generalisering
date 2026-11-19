# Slice 1c evidence: the catalog methods on `TableOps`

**Status:** EVIDENCE, 2026-11-19, engine run pending. Produced for the change that lands
`TableOps.exists`, `TableOps.data_type_of` and `TableOps.create_workspace` on both adapters
(A5.7, T2.12): `ports/workspace_format.py` with `FILE_GDB` only, the catalog group module
`table_ops/catalog.py` in each adapter, the kind reader `data_type` in
`support/dataset_schema.py`, `Exists` in the constrained stub, the store's workspace record,
the conformance cases over every `WorkspaceFormat` member, the unit tests on the fake engine
and on the store, the marked tests in `tests/engine/arcpy/test_catalog.py`, the test-side
builder `file_gdb` now calling the port, ADR-0019 Direction 6, PC-6 with PC-D31 and PC-D32,
PC-R6 to PC-R8, ADR-0017 RS-D12 in its adapted form, and the break-once cases K1 to K4,
M32 to M35 and R15's description. No engine ran for this file yet: every result below
comes from the fake engine installed as `arcpy` through `sys.modules`, from pyright, or from
the hooks. The engine section at the end lists what the image run records and holds no
result until the architect pastes one.

## What the fake engine and the hooks show

- The port: `exists(*, input) -> bool`, `data_type_of(*, input) -> DataType`,
  `create_workspace(*, path, fmt) -> None`, each with the row-shape note in its docstring;
  the three join the list of methods outside the grammar in
  `tests/static/test_row_shape.py`, renamed `OUTSIDE_THE_GRAMMAR`, with the rule id
  `unlisted-query` unchanged.
- The ArcPy adapter: `exists` is `arcpy.Exists` under the guard; `data_type_of` reads
  presence first and then one Describe for `dataType` through `data_type` in the schema
  module, mapped through `DATA_TYPES`, and refuses any other kind naming what the engine
  reports; `create_workspace` refuses a path without the format's suffix and a path
  `Exists` answers for, both before any tool, then dispatches through `CREATORS`, keyed by
  `WorkspaceFormat`, which hands `management.CreateFileGDB` the folder and the stem. The
  tool name is spelled once, as `FILE_GDB_TOOL` in the group module; the fake imports it.
- The in-memory adapter: the store records workspaces by path with their format, refuses a
  path something is already at, and answers `present` and `is_workspace`; the group
  checks the real parent folder with `os.path.isdir` and raises `EngineError` with the
  port method's own name as the tool.
- `"memory"` is spelled once, in `tests/support/fake_arcpy.py`; the engine test modules
  import it from there. `FILE_GDB_PROG_ID` stays in the fake.
- The suffix is `WorkspaceFormat.FILE_GDB.suffix`, read by the adapter's check, by the
  builder's path rendering and by the fake's tool body.

The hooks on the tree, all green: `ruff format --check`, `ruff check`, `pyright` (0 errors),
`lint-imports` (24 kept, 0 broken, row 5 with `workspace_format` in its bottom layer),
`scan_sources.py`, `pytest -m "not arcpy"`, `break_once --check`, `check_consistency.py`,
`check_terminology.py`. The grep for an import of `ag.ports` under `ag.core` is empty.

## Break-once reports

Run by hand on the clean tree, `python -m tools.break_once <set> --out <report>`, after the
change; every case failed under its mutation and the file was restored, `git status`
unchanged for the mutated files after each run.

```
$ uv run --locked --extra dev python -m tools.break_once arcpy_adapter --out ...
break-it-once: 32 cases, 0 unexpected   (K1, K2, K3, K4 new)
$ uv run --locked --extra dev python -m tools.break_once memory_adapter --out ...
break-it-once: 35 cases, 0 unexpected   (M32, M33, M34, M35 new)
$ uv run --locked --extra dev python -m tools.break_once row_shape --out ...
break-it-once: 17 cases, 0 unexpected   (R15's description changed)
```

The new cases and what covered them:

- **K1** the suffix check removed: `test_create_workspace_refuses_before_any_tool`
  `[no-suffix]`, `[other-suffix]`, `[memory-path]` fail with `DID NOT RAISE`.
- **K2** the existing-path check removed: the same test's `[workspace-exists]` and
  `[dataset-exists]` fail with `DID NOT RAISE`.
- **K3** an unmapped `dataType` answered as a table: `test_data_type_of_refuses_any_other_kind_and_a_missing_path`
  `[raster]` and `[workspace]` fail with `DID NOT RAISE`.
- **K4** the presence check before Describe removed: the same test's `[missing]` fails,
  the fake's Describe raising `OSError` where the port promised a contract error.
- **M32** the store's existing-path check removed: both parameters of
  `test_a_workspace_is_recorded_once_whatever_is_at_the_path` and
  `test_create_workspace_records_once_and_refuses_a_taken_path` fail with `DID NOT RAISE`.
- **M33** a workspace path answered as a dataset's kind: `test_exists_and_data_type_of_answer_what_the_store_holds`
  fails, the message naming no dataset instead of a workspace.
- **M34** the store's missing-dataset refusal removed: the same test fails with
  `AttributeError` on `None`.
- **M35** the parent check removed: `test_create_workspace_under_a_missing_parent_names_its_own_method_as_the_tool`
  fails with `DID NOT RAISE EngineError`.
- **R15** unchanged edit, description reworded: `test_rule_holds[unlisted-query]` fails
  naming `Probe.count` as not in the list of methods outside the grammar.

## Engine run: what the image records

Awaiting the image. Nothing below is a result. The architect runs the marked tests and the
probe and pastes the output; the observations then go here, and the open questions under
them are answered from the paste and nowhere else.

Marked tests, with the command in `docs/contributing/testing.md`: the ArcPy parameter of
every case in `tests/conformance/test_table_ops.py` (the catalog cases over
`WorkspaceFormat.FILE_GDB`), `tests/engine/arcpy/test_catalog.py`, and the rest of
`tests/conformance` and `tests/engine`, since `file_gdb` now goes through the port and
every marked test creates its workspace through it. T4.11's count of marked tests changes
only after this run.

The probe, `docs/refactor/temp/slice_1c_catalog_probe.py`, run as a module in the image
(the command is in its docstring), records:

1. `Describe` of a freshly created file geodatabase: `dataType` against
   `WORKSPACE_DATA_TYPE`, and `workspaceFactoryProgID`.
2. `Exists` and `Describe` on a missing dataset, a missing `.gdb`, a `.gdb` under a missing
   parent folder, a folder whose permissions were removed and a `.gdb` under it, the memory
   workspace and a missing dataset in it: the answer or the exception class per call.
3. The file geodatabase tool, through the port, under a missing parent and under the
   unreadable folder: the error class, the tool named in the context, and the engine's
   messages.
4. `Exists` timings, 20 repeated and 5 fresh, in a file geodatabase and in the memory
   workspace, against the band of `slice_1b_read_rows_timing_evidence.md`: 0.1 to 0.5 s
   per call acceptable, 1 to 5 s not.
5. The tool on a geodatabase that holds a table, with the session's overwrite setting as
   applied: whether the table survives.

The feature-dataset walk case recorded as "awaiting the image" in
`slice_1b_family_orientation_evidence.md` (`test_a_feature_class_in_a_feature_dataset_finds_its_workspace`)
runs in the same session; its result goes into that file, beside its item.

## Open after the paste

- Whether `Exists` keeps "absent" apart from "unreachable" (item 2), and the sentence the
  `exists` docstring then needs, if a second signal is wanted to keep the order present,
  reachable, has rows.
- Whether "reachable" joins PC-6 as a detail or as a proposed Direction change.
- The `Exists` timing against the band (item 4), the condition on the architect's
  `data_type_of` decision.
- Whether the engine's own failure on a missing parent (item 3) is what the adapter
  expects: an `ExecuteError` from the tool, wrapped as `EngineError` naming
  `management.CreateFileGDB`. If the tool creates the parent instead, the conformance case
  `test_create_workspace_under_a_missing_parent_is_an_engine_error_naming_the_tool` is a
  contract question for the architect, not a test to fix in place.
