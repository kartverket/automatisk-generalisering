# Slice 1c evidence: the catalog methods on `TableOps`

**Status:** EVIDENCE, 2026-11-23, probe run, marked tests pending. Produced for the change
that lands `TableOps.exists`, `TableOps.data_type_of` and `TableOps.create_workspace` on
both adapters (A5.7, T2.12): `ports/workspace_format.py` with `FILE_GDB` only, the catalog
group module `table_ops/catalog.py` in each adapter, the kind reader `data_type` in
`support/dataset_schema.py`, `Exists` in the constrained stub, the store's workspace record,
the conformance cases over every `WorkspaceFormat` member, the unit tests on the fake engine
and on the store, the marked tests in `tests/engine/arcpy/test_catalog.py`, the test-side
builder `file_gdb` now calling the port, ADR-0019 Direction 6, PC-6 with PC-D31 and PC-D32,
PC-R6 to PC-R8, ADR-0017 RS-D12 in its adapted form, and the break-once cases K1 to K4,
M32 to M35 and R15's description. The first two sections come from the fake engine
installed as `arcpy` through `sys.modules`, from pyright and from the hooks. The engine
section holds what the probe printed in the image, pasted by the architect; the marked
tests have not run yet, and nothing below states a result of theirs.

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

## Engine run: the probe

`docs/refactor/temp/slice_1c_catalog_probe.py`, run as a module in the image with the
command in its docstring, three times: on 2026-11-19, and twice on 2026-11-23, the second
time after the locked-folder cases were corrected to ask about a geodatabase and a table
that exist behind the locked folder, since the earlier form asked only about an absent
path there and so could not tell "absent" from "unreachable". Every observation held over
the runs; the timing lines of each are kept below so one run is not taken for the band.
The process runs as euid 150, not root, so the removed permissions bind for ordinary
access and the locked rows are a reachability test.

1. **A fresh file geodatabase.** `Describe(...).dataType` is `'Workspace'`, equal to
   `WORKSPACE_DATA_TYPE`; `workspaceFactoryProgID` is
   `'esriDataSourcesGDB.FileGDBWorkspaceFactory'`, the value the fake records as
   `FILE_GDB_PROG_ID`. The builder's `is_workspace` check and the fake agree with the
   engine.
2. **`Exists` and `Describe` at the margins.** `Exists` answered `False` for a missing
   dataset in the geodatabase, a missing `.gdb`, a `.gdb` under a missing parent folder, an
   absent `.gdb` under the locked folder and a missing dataset in the memory workspace;
   `True` for the locked folder itself (Describe `'Folder'`) and for the memory workspace
   (Describe `'Workspace'`). Describe on every path `Exists` denied raised `OSError` with
   the message `"<path>" does not exist`, the memory one spelled `"memory/nothing"`.
   Reachability: the geodatabase that exists behind the locked folder and the table in it
   both answered `Exists -> False` and `Describe -> OSError ... does not exist`, the same
   two answers as the absent path beside them. `Exists` and `Describe` do not keep
   "absent" and "unreachable" apart: a path behind a folder the process cannot read is
   reported as a path that does not exist, by both calls. The tool's failure differs
   (000732 under a missing parent, 999999 under the locked folder, item 3), but no
   catalog call reads it.
3. **The tool where the port expects the engine to fail.** Under a missing parent the
   port raised `EngineError` with `context.tool == 'management.CreateFileGDB'` and the
   engine's `ERROR 000732: File GDB Location: Dataset Z:/tmp/.../no_folder does not exist
   or is not supported`; the tool did not create the parent, so the conformance case
   `test_create_workspace_under_a_missing_parent_is_an_engine_error_naming_the_tool`
   stands as written. Under the locked folder the same error class and tool, with
   `ERROR 999999: Something unexpected caused the tool to fail`. The engine spells the
   path in its messages with a drive letter, `Z:/tmp/...`, where the call gave `/tmp/...`.
   The engine's lines appear three times in one `EngineError`: in the exception text, as
   the first entry of `tool_messages`, and again as the per-line messages between
   `Start Time` and `Failed at`; recorded as a follow-up under T2.14 in `TASKS.md`.
4. **`Exists` timings**, seconds per call, min, median and max:

   - 2026-11-19: file geodatabase fresh (n=5) 0.0320, 0.0326, 0.0380; repeated (n=20)
     0.0316, 0.0342, 0.0386; memory fresh 0.0002, 0.0002, 0.0004; repeated 0.0002, 0.0002,
     0.0003.
   - 2026-11-23, before the correction: file geodatabase fresh 0.0365, 0.0392, 0.0407;
     repeated 0.0356, 0.0372, 0.0391; memory fresh 0.0003, 0.0003, 0.0006; repeated
     0.0002, 0.0002, 0.0003.
   - 2026-11-23, corrected: file geodatabase fresh 0.0353, 0.0376, 0.0394; repeated
     0.0333, 0.0356, 0.0396; memory fresh 0.0002, 0.0003, 0.0004; repeated 0.0002, 0.0002,
     0.0003.

   Every call sat under the band's floor of 0.1 s, with no difference between a first call
   and a repeated one, and the memory workspace two orders of magnitude below the file
   geodatabase. Presence before Describe in `data_type_of` costs one such call, which was
   the condition on that decision.
5. **The tool on an existing geodatabase, overwrite as applied.** `overwriteOutput` read
   back `True`; the tool ran on the geodatabase holding a table, and afterwards the table
   answered `Exists -> False` and Describe `OSError ... does not exist`. The refusal of a
   taken path before any tool, PC-D32, is justified by the engine's own behaviour.

## Answered by the probe

- `Exists` and `Describe` do not separate "absent" from "unreachable" (item 2), so
  `exists` has no second signal to offer. "Reachable" leaves the order present,
  reachable, has rows: an unreachable path reads as absent, and the first call that
  needs access fails as an `EngineError`. The port's `exists` docstring and PC-D31 say
  that False means nothing was found at the path and that an adapter may report a path it
  cannot reach as absent; the ArcPy adapter's docstring says its engine does, by `Exists`
  and by `Describe`.
- The `Exists` timing is inside the band (item 4).
- The engine's failure on a missing parent is what the adapter expects (item 3): an
  `ExecuteError` from the tool, wrapped as `EngineError` naming
  `management.CreateFileGDB`. No contract question.

## Still pending

- The probe's added attempt: the tool, through the port, on the geodatabase that exists
  behind the locked folder, and after the permissions are restored whether the table in
  it is still there. `create_workspace` refuses a taken path on `exists` answering True,
  which it does not there, so PC-D32's guarantee rests on the tool failing. A defensive
  check of the engine, not a case the design expects: the scratch manager chooses every
  path, so no path it names is behind a folder the process cannot read. If the table does
  not survive, that is a contract question for the architect, not a fix in place.
- The marked tests, with the command in `docs/contributing/testing.md`: the ArcPy
  parameter of every case in `tests/conformance/test_table_ops.py` (the catalog cases over
  `WorkspaceFormat.FILE_GDB`), `tests/engine/arcpy/test_catalog.py`, and the rest of
  `tests/conformance` and `tests/engine`, since `file_gdb` now goes through the port and
  every marked test creates its workspace through it. T4.11's count of marked tests
  changes only after this run.
- The feature-dataset walk case recorded as "awaiting the image" in
  `slice_1b_family_orientation_evidence.md`
  (`test_a_feature_class_in_a_feature_dataset_finds_its_workspace`) runs in the same
  session; its result goes into that file, beside its item.
