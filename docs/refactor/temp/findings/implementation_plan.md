# Implementation plan: the first real pass of `src/ag`

**Status:** PLAN, 2026-09-18; revised 2026-09-21 after review (the template is not promoted; two
review documents gate slice 0; slice 1 split into 1a, 1b, 1c; Python target 3.13; decisions
needed before slice 0 in §8.0); approved 2026-09-21 with `template_review.md` and `project_tree.md`; slice 0 waits for the architect's go; revised again the same day before approval (the core lift is the architect's first
pull request of 1a; slice 3 waits for four named methods; ArcPy reachable under the whole ArcPy
adapter with a stub as the guard; the design record stays under `docs/refactor/` until the end of
slice 5; §8.0 decided and recorded in DECISIONS.md). Not a decision record. Where this plan proposes something the
decisions do not cover it says so and §8 lists it; it does not re-open a settled A-item.

**Inputs read:** `temp/DECISIONS.md`, `temp/TASKS.md`, `01-terminology.md`,
`findings/lineage_conclusion.md`, `findings/lineage_seam_readiness.md`,
`findings/n1_correspondence.md`, `findings/PATCH-2026-09-17.patch`, `template_code/` in full,
`02-runtime.md`, `03-architecture.md`, `04-migration.md`, `README.md`, the 14 ADRs, the current
`docs/` tree, and a survey of `generalization/`, `custom_tools/`, `file_manager/`,
`composition_configs/`, `paths.py`, `main_on_*.py`, `tests/`, `.github/`.

**Patch status.** `PATCH-2026-09-17.patch` is **not applied**: `git apply --check` succeeds
forward and fails in reverse, and none of A9.11, A9.12, A11.15, A12.5a, A14.1, A15.7, B17-B20,
T4.14, T7.5 is present in `DECISIONS.md`, `TASKS.md` or `01-terminology.md`. This plan assumes
it is applied before slice 1 starts (slice 0 does it). **A12.7a** (call-site ids declaration on writes) was signed on 2026-09-21 and is in DECISIONS.md,
as are A5.7 (workspace creation), `Attr.cmp`'s operator set under A2.1, and A26 (the Python
target); each was placed so that the patch still applies. **B9** (PROPOSALS §1, archive carries
`lineage_id`) remains unsigned and is needed before ingest and publish in slice 5. §8.0 lists what must be decided before slice 0; §8.1 ranks the
rest by what each gates.

**Two companion documents gate slice 0.** `findings/template_review.md` gives a verdict per
template module (keep as is, keep with changes, rewrite, drop) with the item it rests on;
`findings/project_tree.md` gives the `src/ag` tree, its import contracts and where new code
goes. Slice 0 does not start until both are approved. `project_tree.md` was accepted on
2026-09-21 with its recommended options (domain code under `ag/generalization/`, one module per
port Protocol, each adapter a package per port with one module per method group), and paths
in this plan follow it.

**Python target: 3.13** (decided 2026-09-21; the architect records it in DECISIONS). No fixed
lower constraint exists: the project follows its runtimes upward and the target is the lowest
Python minor version across the supported runtimes (§4.7). Nothing is in production yet.

**Vocabulary** per `01-terminology.md`: port method, operation, stage, workspace, pod scratch
root, parents, lineage-bearing, diff-tracked, combining rule. "Fake adapter" below means the
in-memory implementation of a port; "spy" means the existing recording toolbox.

---

## 0. The shape of the pass, in one paragraph

The template was a learning pass and is not promoted. Two reviews come first
(`template_review.md`, `project_tree.md`); slice 0 then creates the approved tree empty, with the
tooling around it; template code enters `src/ag` module by module, only in the slice that needs
it, and each lift cites its verdict. Slice 1 is a walking skeleton in three reviews. 1a, with no
ArcPy, lands the row-shape grammar, the `In`/`Out`/`Mutates`/`ParentsOut` markers, the port
errors, three Protocol methods (`read_rows`, `select`, `explode_multipart`), the in-memory fake
for them, and a facade spike with no lineage logic. 1b adds the ArcPy session and adapter for the
same methods, conformance on both adapters, the Windows run and a capped `read_rows` timing at
2.3 M rows. 1c adds the scratch manager, a filesystem `ArchiveClient`, settings, the local
runner, a fixture stage end to end under both adapters, and the port-method guide. Slice 2 adds identity above the ports (minter, id map,
facade) and, in parallel, the dissolve parents mechanism inside the ArcPy adapter, which already
exists as tested staging code. Slice 3 closes the operation boundary (edges, sweeps, `DROPPED`)
and runs one operation end to end with lineage at K = 1. Slice 4 is the steady hand-off stream:
one port method per task, against a written guide. Slice 5 adds fan-out, fan-in, ingest, the
dispatch registry and the fan-in assertions around an unchanged `run_operations`. Slice 6 moves
the first real building stage and then the first partitioned road stage. A legacy track (the
shadow centroid experiment, the two gates, the `SELECT_STUDY_AREA` fix) runs beside slices 0 to 3
and needs no architecture decisions.

---

## 1. Inventory: what the template gives, per module

**The verdicts are in `template_review.md`; this section is the index of when each module enters
`src/ag`.** Nothing is promoted wholesale and nothing enters in slice 0. A module is lifted in
the slice named in the last column, by the PR that needs it, and that PR cites the module's row
in `template_review.md`. Where the review found a defect (five were confirmed by running the
template) the lift fixes it. Target paths follow `project_tree.md`: `core/operations.py` splits
into `core/handles.py` and `core/operations.py`; the predicate algebra moves to
`ports/predicates.py`; an adapter is a package per port with one module per method group plus a
`support/` package; domain code sits under `ag/generalization/`. "Task B" in the last column is
the hand-off of §3.1: it starts when the first pull request of 1a (the architect's core lift)
has merged, and lifts the rest of the core declaration modules.

Legend (state of the template module): **lift** = move with small edits; **rework** = keep the shape, rewrite parts;
**stale** = contradicts a decision and must change before use; **new** = written from nothing.

### 1.1 `core/`

| module | state | what changes | slice |
|---|---|---|---|
| `types.py` | lift | nothing | 1a, first pull request (the architect's core lift) |
| `injection.py` | lift | nothing | 1a, first pull request |
| `operations.py` | lift, then extend | `ScratchHandle` (frozen, `path` `compare=False`, `namespace` in equality) matches A15.3's retained clause and A12.5a's needs exactly. `Direction`/`In`/`Out` exist; add the two markers A12.5a needs (`Mutates` for T2.8's in-place mutators, `ParentsOut` for A11.15) as `Direction` members with aliases, and make `@operation` reject them on an operation signature (an operation parameter is only ever `In` or `Out`). `@operation`, `OperationCall`, `ScratchScope`, `INJECTED` are decided (ADR-0011, ADR-0014) and lift as is. | 1a, first pull request: the split into `handles.py` and `operations.py`, the restamp guard, the internal-handle namespace, the markers, and the pyright-strict restructuring of `@operation` |
| `pipeline.py` | lift | `LineageRoot` becomes `OriginRoot` (T7.2), applied inside the template and the documents in slice 0, so every later lift carries the new name; TASKS says it must precede the lineage vocabulary landing in the same documents. | Task B |
| `data_objects.py` | lift | T7.2 rename (`lineage_roots()` becomes `origin_roots()`) | Task B |
| `locations.py` | lift, one edit | `StorageRoots.for_environment` hardcodes bucket names; that is deployment configuration and moves to the settings object of §7.1. Path builders stay. | 1c (dump path), 5 (payloads) |
| `graph.py` | lift | nothing | Task B |
| `selection.py` | lift | `check_upstream_available` stays `NotImplementedError` until slice 5 | 5 |
| `policy.py` | lift | nothing | Task B |
| `planning.py` | lift as stub | `build_run_plan` and `downstream_closure` stay unimplemented; nothing before slice 5 needs a `RunPlan` (the local runner of §7.5 drives a `Stage` directly). | 5 |
| `validation.py` | lift | `check_stage_graph_acyclic`, `check_no_coarser_input`, `check_publications` are `NotImplementedError` and fully specified by their docstrings and `02-runtime.md` §8. Hand-off work (§3). | Task B |

### 1.2 `ports/`

| module | state | how close to the decided design | slice |
|---|---|---|---|
| `toolbox.py` | lift | Exactly A1.3 / ADR-0008 / ADR-0014: frozen four-port bundle, `NOT_INJECTED` sentinel with the one load-bearing cast. No change. | 1a |
| `geometry.py` | lift | `Geometry` value type is ADR-0004 as decided. T2.5 (linear referencing methods) and T2.7 (`Coordinate` z-free docstring) are additive, independent hand-offs. | 1a (value type), 4 (T2.5, T2.7) |
| `table_ops.py` | rework | `FieldType` lacks `BIGINT` (A10.1, B1, gated by T0.1). `Row` needs `slots=True` (T2.7). Missing: the native index accessor and its join-key addressability declaration (T3.1), `update_rows` (T2.2), the `join_field` unique-key contract (T2.8), `create_workspace` (A5.7, decided 2026-09-21). No `In`/`Out` annotations (A12.5a), no `@row_shape` on `map_fields` (A12.11a) and none on `write_rows`/`write_table` (B13, A12.7a). `read_rows` returning `Iterable[Row]` is right and is what the lineage-aware pipe of A12.7 wraps. | 1a (`read_rows` and its value types), 1c (`exists`, `data_type_of`), 2a (what the id map needs), 4 |
| `geometry_ops.py` | stale in five places | `union` must go (A5.4). `DissolveOption` must go (B18). `buffer`, `spatial_join`, `nearest_neighbors`, `extract_vertices` must split (A5.6). `dissolve` needs `statistics: tuple[StatisticSpec, ...]` (A9.12) and `parents: ScratchHandle \| None` (A11.15), and the other four `MINT` methods need `parents` too. `Attr(cql: str)` becomes structured leaves plus `Attr.raw` (A2.1). `VertexPosition.DANGLE` is already present (A5.5 is done in the template). `Relation`, `EndCap`, `JoinStyle`, the predicate algebra and `Spatial.__post_init__` are decided and lift. `sample_at` (T2.6) is additive. | 1a (`select`, `explode_multipart`, the predicate algebra), 2b (`dissolve`), 4 (rest) |
| `cartographic_ops.py` | rework | `aggregate`, `collapse_to_centerline` need `parents` (A11.15); `displace_features.displacement` stays undeclared until B11; `select_network.exempt: Predicate` stays. Row shapes per A12.11. | 4 |
| `graph_ops.py` | lift | `NodeId` becomes `NewType` (A3); Q-C / B2 stays open, deferring is cheap by the module's own argument. | 4 |
| `archive.py` | lift, and it wins a conflict | Two-method `upload`/`download` on `str` paths. **`staging/transfer.py` declares a second, incompatible `ArchiveClient` Protocol** (`read(location, into: ScratchHandle)` / `write(source, location)`) that predates `ports/`. Keep `ports/archive.py`; delete the one in `transfer.py`; `transfer.py` is the one place a handle is turned into a path for it. | 1c |
| `cluster.py` | lift, unused | `JobSpec`/`JobStatus`/`ClusterClient` as decided; no adapter until the orchestrator pass, which is outside this plan. | not in this pass |
| `__init__.py` | rework | Re-export list changes with the surface: drop `DissolveOption`, add `Statistic`, `StatisticSpec`, `Rows`, `Cardinality`, `Ids`, `Mutates`, `ParentsOut`. | 1a |
| `row_shape.py` | **new** | `Rows`, `Cardinality`, `Ids`, `@row_shape` keyed by output parameter name, `__row_shape__` on the Protocol method (A12.1-A12.5, T4.1). | 1a |
| `errors.py` | **new** | `PortError` base plus `EmptyGeometryError`, `UnmatchedInputError`, `ParentsUnavailableError`, `EngineError` (§6). | 1a |

### 1.3 `adapters/`

| module | state | notes | slice |
|---|---|---|---|
| `arcpy/predicates.py` | lift, then rework | `push_negation` and `Negated` are correct and tested. `apply` is unimplemented and assumes `cql_to_sql(term.cql)`; under A2.1 it compiles structured leaves with `AddFieldDelimiters` per workspace type instead. | 1b |
| `arcpy/session.py` | **new** | The only module that runs a tool, touches `arcpy.env` or names a vendor exception (any module under `adapters/arcpy/` may import `arcpy` for cursors and geometry objects; `project_tree.md` §6.1); environment (SR 25833, XY tolerance 0.02 m, resolution 0.01 m, from `env_setup/environment_setup.py`); `run_tool` wrapper draining `GetMessages()` and wrapping `ExecuteError` into `EngineError` (§6.4); handle release before pack; capability record. | 1b |
| `arcpy/table_ops.py`, `geometry_ops.py`, `geometry.py` (converters) | **new** | The three skeleton methods in slice 1b as group modules under a package per port, widened per method in slice 4. | 1b (three methods), 4 |
| `adapters/_shared/parents_resolver.py`, `adapters/arcpy/support/` | **new by promotion** | `temp/dissolve_parents.py` (engine-free, 15 tests, goldens) becomes `_shared/parents_resolver.py`, importable by the fake and the conformance suite. `temp/arcpy_part_locator.py` splits into `support/part_locators.py` (segment and point locators) and `support/geometry_guards.py` (pre-call empty-geometry guard, `degenerate_inputs`). The two homes are told apart by whether the code imports the engine (`project_tree.md` §3.2 rule 5). | 2b |
| `arcpy/cartographic_ops.py` | **new** | slice 4, method by method | 4 |
| `fakes/recording_toolbox.py` | lift | It is a spy, not a fake. Stays for the "every operation runs to completion against the surface" check and for B14's trace candidate. | 1c |
| `fakes/memory/` | **new** | The in-memory adapter (§5.7). | 1a (three methods), then with every widened method |
| `networkx/graph_ops.py` | **new** | Thin; `custom_tools/general_tools/graph.py` is the source. | 4 |
| `storage/filesystem.py`, `storage/s3.py`, `storage/gcs.py` | **new** | Filesystem first (slice 1c, for scratch dumps and local runs); object storage with fan-out (slice 5). `temp_skip_folder/core/infrastructure/archive/` and `main_on_*.py` hold the MinIO and GCS code to lift from. | 1c (filesystem), 5 (S3, GCS) |
| `cluster/` | not in this pass | | |

### 1.4 `staging/`, `runtime/`, `orchestrator/`, `observability/`, `helpers/`

| module | state | notes | slice |
|---|---|---|---|
| `staging/workspace.py` | lift | `normalize_layer_name` unimplemented and specified; hand-off. `posixpath` joins are used deliberately; slice 1b confirms ArcPy on Windows accepts them for `.gdb` layer paths (§8.2). | 1c; `normalize_layer_name` as a hand-off |
| `staging/scratch.py` | lift, one gap | `ScratchFileManager` is the decided design (02-runtime §4.2). `create_workspaces` is unimplemented and its docstring says `CreateFileGDB`, which `staging/` may not call. Decided 2026-09-21 (A5.7): `TableOps.create_workspace`. The manager calls it through the toolbox; implemented in 1c. | 1c |
| `staging/transfer.py` | stale | Duplicate `ArchiveClient` (above); `stage_down`/`stage_up`/`dump_scratch` unimplemented; `PinnedInput`/`PlannedOutput` typed as `object`. Rewrite in slice 1c for the local case (dump only) and slice 5 for the remote case. | 1c (dump), 5 (stage down and up) |
| `runtime/stage_entry.py` | lift | `run_operations`, `_supply`, `sweep_outputs` are the decided pod dispatch loop. Slice 3 wraps it with the lineage session; the function itself does not change shape. | 1c, 3 |
| `runtime/env.py`, `runtime/local.py` | **new** | Settings object and the local single-pod runner (§7.1, §7.5). | 1c |
| `runtime/fan_out.py`, `fan_in.py`, `partition.py`, `ingest.py` | **new** | slice 5 | 5 |
| `orchestrator/execute.py` | lift as stub | Outside this pass except the dispatch registry's counter (T3.3), which is orchestration and lands as a small module in slice 5. | 5 |
| `observability/` | **new** | JSONL records, `ContextVar` context, timing (03-architecture §6). Minimal in slice 3, merge in slice 5. | 3, 5 |
| `helpers/` | empty by rule | Fills on the first second-caller during slice 6. | 6 |
| `lineage/` | **new** | Not in the template at all. Minter, id map, facade, edge log, session, errors, later `query.py`. | 1a (the facade spike), 2a, 3 |

### 1.5 Examples, declarations, tooling

| item | state | notes | slice |
|---|---|---|---|
| `operations/road`, `operations/building`, `pipelines/*`, `tuning/`, `sources.py`, `products.py`, `classification_rules.py` values | examples, stale in the ways A17 lists | They are worked examples, not production pipelines, and they carry known defects (A17.2 ramps inversion, A17.4/A17.7 uncompilable subqueries, A17.5 ranks joins, A17.1 origin). Recommend: move them to `tests/fixtures/example_pipelines/` rather than into `src/ag/generalization/`; they stay inert (excluded from pyright and from collection) until the modules they import exist, in 1c; apply T0.3, T2.1's call-site fixes and T2.10's ranks fix there, and keep them as the declaration fixture every unit test and the walking skeleton use. `src/ag/generalization/sources.py`, `products.py`, `classification_rules.py` start empty of values and fill in slice 6 from `data_orchestrator/features/*` and `file_manager/*`. | 0 (moved, inert), 1c (live) |
| `tools/run_example.py`, `dump_tuning.py` | lift | Move to repo `tools/`; `run_example` becomes the spy-driven "surface completeness" test. | 1c (`run_example`), 6 (`dump_tuning`) |
| `tests/unit/*` (3 files) | lift | `test_road_operations.py:161` imports a module that does not exist; its ArcPy half becomes a conformance case in 1b and the fixture-stage run in 1c. | 1a (two files), 1c (`test_road_operations`) |
| `.importlinter` | lift, then T7.4 | Seven contracts pass today. Add `ag.helpers` to the layers stack, the `lineage/` protected row (T4.3 chooses the mint surface; B10 argues `protected`), the vendor-import contracts (`include_external_packages`), the observability accessor rule from 03-architecture §4.2, and the package-coverage meta-check. | 0, 2a |
| `pyrightconfig.json` | rework | `standard` today; the pass runs `strict`. Expect friction in `@operation` (`ParamSpec` plus `functools.update_wrapper`), the `cast`s in `toolbox.py` and the spy, and `__dataclass_params__`. Becomes `[tool.pyright]` in `pyproject.toml`. The friction is resolved in the PR that lifts `core/operations.py`, not in slice 0, because no template code enters in slice 0. | 0 |
| `conftest.py` | drop | `src` layout plus an installable `pyproject.toml` replaces the `sys.path` insert (03-architecture §7.1). | never |

**Row shape, handle and toolbox pieces, judged against the decided design.** The handle
(`ScratchHandle`, `handle()`, `Handles`, `__set_name__`) and the toolbox (`Toolbox`,
`NOT_INJECTED`, `Injected`) are right in design: nothing in DECISIONS changes them, and A15.3
explicitly retains the handle's equality rule. The review still found two defects in the handle
code, both confirmed by running it and both fixed at the lift in 1a: a handle bound in two class
bodies is silently restamped with the second namespace, and internal scratch handles compare
equal across operations, which A15.3's handle-keyed cache cannot tolerate. It found three more
in `staging/` (the leaf-collision check is keyed without the operation, `sidecar()` splits on the
wrong dot, and `In`/`Out` must stay `TypeAlias`); see `template_review.md`. The row-shape piece does not exist: the template
predates A12 entirely, so `row_shape.py`, the annotations on every port handle parameter and the
T4.1 check are all new. The port *surfaces* are about 70 % right by method count and wrong in
the five places §1.2 lists, all of which are decided.

---

## 2. Build order

### 2.0 Principles behind the order

1. **Every slice is one reviewable diff on `src/ag`.** The template is not promoted: it was a
   learning pass, it is reviewed first (`template_review.md`), and a module enters in the slice
   that needs it, citing its verdict. A lift is therefore always small enough to read, and a
   module nobody needs never enters.
2. **The seam that is most likely to be wrong lands first with the least surface.** The three
   things the walking skeleton must prove are: the facade can read `__row_shape__` off a
   Protocol and wrap an adapter without per-method code; the native index survives a port call
   well enough to key parents (A9.2); and one stage runs through `run_operations` under both a
   fake and ArcPy with no operation knowing which.
3. **Gates run beside code, never in front of it.** T0.1 and T0.6 are Linux-image measurements
   with scripts already written. They start in slice 0 and their results are consumed by slice 2.
   Only T0.1's failure would change code already written; §8.2 says what.
4. **Lineage is above the ports (A11.11), so the ports land first and lineage is added as a
   wrapper.** Slices 1 and 2 are separable for exactly this reason.
5. **The partition machinery is added around `run_operations`, not into it.** Slices 2 and 3
   run at K = 1 with a trivial minter dispatch; slice 5 replaces the dispatch and adds fan-out and
   fan-in without editing anything an operation or the facade sees.

### 2.1 Judgement on the straw man

Kept: the slice boundaries 0 to 6 and the order. Changed, with reasons:

- **Slice 0 creates the approved tree and the tooling and lifts nothing** (revised 2026-09-21).
  The first draft of this plan promoted the template wholesale. The template was a learning pass,
  so it is reviewed module by module first and enters slice by slice; two documents and the
  decisions of §8.0 come before slice 0.
- **Slice 1 is three reviews (1a, 1b, 1c) over three Protocol methods**, chosen so the narrow
  surface still covers the grammar: `read_rows` (returns values, so it is outside the grammar, and
  it is the subject of the timing run), `select` (ONE + CARRY) and `explode_multipart`
  (MANY + MINT, with the parents channel over the engine's native `ORIG_FID`). The GROUP cell
  arrives with `dissolve` in 2b, together with its mechanism. Reason for not going narrower: a
  skeleton that only shows ONE + CARRY proves nothing about the parents seam the audit called
  blocking. `exists` and `data_type_of` join in 1c because the output sweep needs them.
- **`ArchiveClient` moves from slice 2 to slice 1c** as the port plus a filesystem adapter, because
  the walking skeleton's scratch dump and the local runner need a transport and the port is two
  methods. The S3 and GCS adapters wait for slice 5, where fan-out needs them.
- **Slice 2 splits into 2a (identity above the ports) and 2b (dissolve parents inside the ArcPy
  adapter).** 2b is adapter-internal by A14.1, already exists as staging code with goldens, and is
  `[PARALLEL]` by T4.14; running it as its own review keeps the facade review about the facade.
- **Slice 3 is where edges are emitted**, as the straw man says, and it is also where the lineage
  facade's post-call assertion (B10) and the lineage-aware pipe (T4.4) land, because both are
  operation-boundary behaviour.
- **A legacy track** is added beside the slices: it is where the first hand-offs come from and it
  needs no architecture decision.

### 2.2 The slices

**Every slice's "Done when" includes the design record.** `docs/refactor/` is the working design
record for this change and stays where it is while the pass runs (§4.8). In the same pull
requests as the code, each slice updates: the status of the tasks it closes in `TASKS.md`; the
A-items it lands, struck in `DECISIONS.md` with a pointer to where they landed, per the migration
protocol, with the `01-terminology.md` entries that cite them repointed; and the sections of
`02-runtime.md` and `03-architecture.md` its code makes true or proves wrong. A slice whose code
is merged and whose record is not updated is not done. Each slice below names its share.

Sizes are rough and assume one person on the architecture slices with review time included.
"Hand-off" means a task another developer can take from a written spec.

#### Before slice 0: two reviews and the architect's decisions

**Contains.** `findings/template_review.md` (written 2026-09-21: a verdict per template module,
five defects confirmed by running the template, and fourteen things the template taught that the
decisions do not capture) and `findings/project_tree.md` (written and accepted 2026-09-21: the
tree, the adapter structure, eighteen import contracts, and where a new port method, operation
and stage go). The decisions of §8.0.

**Done when.** Both documents are approved and every row of §8.0 has an answer. Slice 0 does not
start before that.

**Runs meanwhile.** The legacy track does not wait: Task A (T0.2 + T1.1) and T7.5 touch only
legacy code and start now (§3).

#### Slice 0: the approved tree, the tooling, the gates started. No template code.

**Contains.**
- Apply `PATCH-2026-09-17.patch`; run `check_consistency.py` and `check_terminology.py`.
- **Create the approved tree** (`project_tree.md` §1) as empty packages, each with a one-paragraph
  docstring saying what belongs there and its membership test. Nothing from the template enters
  `src/ag` in this slice.
- `pyproject.toml`: a `[project]` table with the `src` layout and an editable install;
  **`requires-python = ">=3.13"`, `[tool.pyright] pythonVersion = "3.13"` and
  `[tool.ruff] target-version = "py313"`, set together** (§4.7; ruff format replaces Black,
  first for the new code and, from 2026-10-02, for the whole repository, A28). `[tool.pyright]` is `strict` over `src`, `tests`, `tools`
  and replaces the template's `pyrightconfig.json`. The legacy packages are outside its include
  list.
- One toolchain (revised in slice 0): uv manages the environment (A27); tool versions pinned
  once, in `pyproject.toml`'s `dev` extra, resolved in the committed `uv.lock`;
  `.pre-commit-config.yaml` is the one list of checks, every hook local and running its tool
  through `uv run --locked --extra dev`, independent of `PATH` and activation: `ruff format --check`
  and `ruff check` over the whole repository (A28: no Black; `F401`/`I001` held back on the
  legacy packages with a per-file baseline), `pyright`, `lint-imports`, the source scans,
  `pytest -m "not arcpy"`, the two document checkers. CI on `ubuntu-latest` and
  `windows-latest`, **Python 3.13** from `.python-version`, runs `uv sync --locked --extra dev`
  and then `pre-commit run --all-files` through uv, and nothing else for these checks; the old
  black workflow is deleted, and its "Black Lint Check" is replaced as the required status
  check on `main` by the two `pre-commit (<os>)` jobs once they have reported on the first pull
  request. The
  legacy tests move to `tests_legacy/`, run by hand under a Pro environment.
- `.importlinter` at the repository root, **rebuilt against `project_tree.md` §6** (rows 1 to
  18), not lifted from the template. Contracts over empty packages pass trivially, so each one
  is broken on purpose once with a throwaway probe module, as B10 did for the `helpers/` row,
  and the failure message is recorded in the PR. Ruff `SLF001` scoped to `ag/generalization/`.
  The static scans for `os.environ` and for imports by string (`importlib`, `__import__`,
  `runpy`) exist with their allowlists.
- Test layout (§5.1) with the `arcpy` marker registered.
- **T7.2 applied inside `docs/refactor/template_code/` and the documents**, so every later lift
  carries `OriginRoot`. `tools/run_example.py` still runs from the template directory afterwards.
- The worked examples move to `tests/fixtures/example_pipelines/`, inert: excluded from pyright
  and from collection until 1c, because the modules they import do not exist yet. The A17 fixes
  are tracked against them there. The rest of `template_code/` stays where it is, as the source
  for lifts, and is deleted when its last module has been lifted or dropped.
- Start the gates in the Linux image, in parallel: T0.1 (script exists) and T0.6(a).
- `docs/README.md`, the CURRENT banners on `docs/developer_reference/*`, and
  `docs/contributing/python-version.md` (§4.7).

**Depends on.** Approval of `template_review.md` and `project_tree.md`; the decisions of §8.0.

**Done when.** Every CI step is green on both runners over the empty tree; each of the eighteen
contracts has been shown failing once; the examples are moved and inert; T7.2 is applied and
`run_example.py` prints the same derivation as before; T0.1 and T0.6(a) are running or scheduled
with an owner.

**Design record.** `DECISIONS.md`, `TASKS.md` and `01-terminology.md` carry the applied patch; T7.2 and T7.4 are marked done in `TASKS.md` and B8 is resolved; `03-architecture.md` §7 shows the accepted tree and §4.1, §4.2 the eighteen contracts, with `.importlinter` named as authoritative; A26's destination exists.

**Size.** 2 to 3 days of the architect. It shrank because the pyright-strict fallout moved to
the PRs that lift code.

**Review hard.** The contracts file against `project_tree.md` §6, row by row. It is the
architecture in executable form, and an empty tree is the cheapest moment it will ever be to
read it. Check the break-it-once evidence for each contract rather than the green run.

#### Slice 1: the walking skeleton, in three reviews

Three Protocol methods carry the whole slice: `TableOps.read_rows`, `GeometryOps.select`,
`GeometryOps.explode_multipart`. 1c adds `TableOps.exists` and `data_type_of` for the output
sweep, and `TableOps.create_workspace` (A5.7) for the scratch manager. No write method lands in slice 1 (A12.7a governs those; they arrive in 2a), so fixtures
are seeded by test support, not through a port.

##### Slice 1a: the grammar, the markers, the errors, the fake, the facade spike. No ArcPy.

**Status, 2026-10-05.** The core lift (first pull request) is drafted on `slice_1a` and under
review: `core/types.py`, `core/injection.py`, `core/handles.py`, `core/operations.py`, plus
`core/errors.py`, pulled forward because the handle module raises `InjectionError`. Departures
recorded on the way: `ErrorContext.messages` is `tool_messages` (§6.2 below repointed);
`Scale.rank` because a `StrEnum` orders as text; `Classification.join` fails closed; internal
handles are named by trail and leaf and stamped with the scope's namespace; call identity is
A29 (T2.13). Evidence: `findings/slice_1a_core_lift_evidence.md`. The core lift merged as #688.
**Second pull request, the port values (2026-10-07):** `ports/geometry.py`, `ports/attributes.py`
(a departure, project_tree §8 row 9), `ports/table_ops.py` values, `ports/predicates.py` with
structured `Attr` (A2.1 to A2.3 struck into ADR-0015), `ports/toolbox.py` with the sentinel as a
`Toolbox` subclass and no cast, `ports/errors.py`, `core/warnings.py`, the four Protocol classes
empty, `ports/__init__.py` rebuilt; T2.7 done, T2.1's port half done. Evidence:
`findings/slice_1a_port_values_evidence.md`.

**Contains.**
- **The first pull request of 1a is the core lift, by the architect**: `core/types.py`,
  `core/injection.py`, `core/handles.py` and `core/operations.py`, with the split, the restamp
  guard, the internal-handle namespace, the `Mutates` and `ParentsOut` markers rejected on
  operation signatures, and the pyright-strict restructuring of `@operation`. It is its own pull
  request because the restructuring is architecture work, and because Task B starts the moment it
  merges: a hand-off never lifts or edits `core/operations.py`, so no structural change is ever
  rebased onto a plain lift.
- Further lifts, each citing its verdict: `ports/toolbox.py`,
  `ports/geometry.py`, the value types of `ports/table_ops.py` (`Field`, `FieldType`, `Schema`,
  `Row` with slots, `AttributeValue`), `ports/predicates.py` with structured `Attr`
  (`cmp`, `in_`, `is_null` per A2.1, and `raw` with its pinned call-site count), and the two
  unit-test files that cover them (`test_operation_classification.py` goes with the core lift).
- New: `core/errors.py` (`AgError`, `ErrorContext`, `InjectionError`), `core/warnings.py`,
  `ports/errors.py` (§6), `ports/columns.py` (`PARENT_ID`, `CHILD_ID`), `ports/row_shape.py`
  (`Cardinality`, `Ids`, `Rows` with the three illegal cells rejected in `__post_init__` with
  A12.1's messages, `@row_shape(**outputs)` storing `__row_shape__` on the Protocol function
  without altering its signature; its docstring states that a handle inside a `Spatial` predicate
  is outside the grammar).
- The three Protocol methods, annotated (`In`, `Out`, `ParentsOut`), with What / How / Why
  docstrings: `read_rows` (explicitly outside the grammar), `select` as ONE + CARRY,
  `explode_multipart` as MANY + MINT with `parents: ScratchHandle | None`.
- `tests/static/test_row_shape.py`: T4.1's check over every Protocol method in `ports/`, with the
  break-it-once evidence in the PR. Its rule set is written for A12.7a as signed.
- The fake for those three methods: `adapters/fakes/memory/` with `store.py`, `_base.py` and the
  group modules, following `project_tree.md` §3.2; `tests/static/test_adapter_groups.py`, broken
  once. Fixtures are seeded into the `MemoryStore` by a builder in `tests/support/`.
- **The facade spike** (moved here from 2a's risk table): `lineage/facade.py` as a generic
  wrapper with **no lineage logic**. It wraps any port instance, looks the called method up on
  the **Protocol** to read `__row_shape__`, calls a no-op hook before and after, and forwards.
  It passes pyright strict with exactly one `cast`, at the point where the wrapper is handed out
  as the port type. A reachability test walks every method of every handle-bearing Protocol and
  asserts it is reachable through the wrapper and that the wrapped call gives the same result as
  the direct call under the fake. This is the first commit of the real module, not a throwaway.

**Depends on.** Slice 0. A12.7a, signed 2026-09-21.

**Done when.**
- `pytest -m "not arcpy"`, pyright strict and `lint-imports` are green with the lifted and new
  modules in place, with no new `type: ignore` in `core/operations.py` beyond what the review
  allows for `__dataclass_params__`.
- The row-shape check fails on each of its rules when one is broken deliberately: an `Out` with
  no row, a row naming a non-`Out`, a `subject` naming a non-`In`, a missing axis, each illegal
  cell; and passes with `ParentsOut` undeclared.
- Under the fake: `select` preserves row count and attributes; `explode_multipart` with
  `parents=` writes native-index pairs equal to the fixture's expected partition and with
  `parents=None` writes nothing; the native index of the input is unchanged by both and is
  reassigned when the dataset is next written.
- The two handle defects are covered by tests that fail on the template's code: a handle bound
  in two class bodies raises; two operations' `scratch("x")` are unequal.
- The facade spike: one `cast` in `src/ag`, reachability test green, pyright strict green.

**Design record.** T4.1 marked done and the 1a share of T2.1 recorded; A12.1 to A12.6, A12.5a and A2.1 to A2.3 migrated to their destinations (`ports/row_shape.py`, `ports/predicates.py`, the ADR amending ADR-0001) and struck; `03-architecture.md` §2.3 and §2.4 updated for the markers and structured `Attr`; the terminology rows for *row shape*, *cardinality*, `ids`, *subject* and `context` repointed.

**Size.** About one week.

**Review hard.**
- `__row_shape__` is read from the Protocol, never from the adapter instance (A11.11); the
  decorator does not wrap the function in a way that breaks structural typing under strict.
- The facade spike: count the casts and look at what strict forced besides them. If the answer
  is per-method code, A11.11's "one generic facade" is in question and it is week one, which is
  the point of moving it here.
- The three illegal-cell messages state their reasons, and `MANY + CARRY` names A11.2.
- The fake's group classes hold Protocol methods only.

##### Slice 1b: the ArcPy session and adapter, conformance, the Windows run, the timing run

**Contains.**
- `stubs/arcpy_constrained/arcpy/`: the local stub, declaring only the non-tool names the
  adapter and the builders use so far (the `da` cursors, the geometry and spatial-reference
  constructors, `Describe`). It omits every toolbox, `env` and `ExecuteError` on purpose,
  which is what lets pyright strict pass in a CI without ArcPy and makes it reject a tool
  call outside the session (`project_tree.md` §6.1). Its module docstring states the rule a
  developer meets on hover or go-to-definition: a tool goes through `session.run_tool`; a
  non-tool name is added here with its reason in the same pull request. The two pyright
  execution environments that apply it (`src/ag/adapters/arcpy`, `tests/support/arcpy`)
  already exist in `pyproject.toml` from slice 0.
- `adapters/arcpy/session.py`: the only module that runs a tool, touches `arcpy.env` or names a
  vendor exception; tools are resolved by name inside `run_tool`; the environment (spatial
  reference 25833, XY tolerance 0.02 m, resolution 0.01 m, from `env_setup/environment_setup.py`);
  `run_tool`, which drains `GetMessages()` and wraps any vendor exception into `EngineError`
  (§6.4); the first capability record.
- `adapters/arcpy/_base.py`; `support/geometry_values.py` (converters), `support/
  predicate_compiler.py` (`push_negation` lifted, `apply` written for structured leaves with
  identifier quoting per workspace type through `support/field_names.py`), `support/
  pair_tables.py` (reads `ORIG_FID`, writes the pair table); the group modules for the three
  methods.
- `tests/conformance/` for the three methods, parametrized over both adapters (§5.2).
  Engine-neutral fixture builders in `tests/support/`; the ArcPy side of the builder lives in
  `tests/support/arcpy/`, sits under the `arcpy` marker and writes small `.gdb` inputs with
  the engine directly, because no write method exists on the port yet: tools through
  `session.run_tool`, rows through the stub's cursors, under the same constrained stub as the
  adapter. Those modules are imported lazily, inside an `arcpy`-marked fixture or test, never
  at the top of a test module: collection imports test modules and CI has no ArcPy. The 1b
  static scan covers both roots.
- The run of the conformance suite under an interpreter that has ArcPy (`pytest -m arcpy`,
  `docs/contributing/testing.md`), with its log kept. The environment for that run is B23,
  settled in this slice by trying its candidates on one Windows machine; the result lands
  on the toolchain and testing pages.
- **The `read_rows` timing run**, `tools/time_read_rows.py`, on
  `data_preparation___road_single_part___n100_road` (2,320,817 rows), two passes: attributes only
  (three fields), then with geometry.
  - *Wall-clock cap:* `--cap-seconds`, default 1,200 per pass, checked after every batch.
  - *Incremental output:* the total row count is read first; then after every 50,000 rows one
    JSON line (rows read, elapsed seconds, rows per second, process memory) is appended to
    `<workdir>/logs/<timestamp>_read_rows.jsonl` and flushed.
  - *When the cap is hit:* iteration stops, the cursor is released, a final line is written with
    `status: "capped"`, the rows read, the rate, and the projected time for the full table
    (elapsed times total over read), and the script exits 0. A capped pass is a result, not a
    failure.
  - *When the run is interrupted or killed:* the file already holds a line from the last
    completed batch, so a rate exists whatever happens; the script also writes a
    `status: "interrupted"` line if it gets the chance.
  - *What the number decides:* whether slice 3's lineage-aware pipe and the facade's parents
    mapping can stream `Row` values or need a columnar read beside `read_rows`. It is reported
    as a rate and as the time for a partition-sized input (36,407 rows) against A15.7's minute.

**Depends on.** 1a.

**Done when.**
- The conformance cases for the three methods pass under the fake in CI and under ArcPy on
  Windows: row count and attributes preserved by `select`; `ORIG_FID`-derived pairs equal the
  expected partition; **on a `.gdb` input whose `OBJECTID`s are non-dense after deletes**, the
  input's native index set is unchanged by both methods and the reported `PARENT_ID`s are the
  pre-call indices (T4.11 case 1a); `EngineError` carries the tool name and the drained messages
  when a tool fails.
- `lint-imports` shows `arcpy` imported only under `ag.adapters.arcpy`; pyright strict is green in
  CI without ArcPy; a probe module that calls `arcpy.management.Delete` directly fails pyright,
  and one that uses `getattr(arcpy, ...)` or names `ExecuteError` outside `session.py` fails the
  static scan (both shown once in the pull request).
- The timing log exists with a final line of status `complete` or `capped` for each pass, and the
  rate and the partition-sized projection are written into the PR.

**Design record.** `03-architecture.md` §4.1 and §4.2 state the widened ArcPy import rule and the stub; §6 records the message drain as implemented; A9.2's contract line is in `ports/table_ops.py` with what the non-dense `OBJECTID` case showed; the timing result is written into `04-migration.md` Appendix A.

**Size.** About one week.

**Review hard.**
- `run_tool`: every engine call goes through it; messages are drained on success and on failure.
- What the adapter's `select` does to `OBJECTID`, and how `explode_multipart` maps `ORIG_FID`
  back to the pre-call native index; this is A9.2's contract meeting a real engine for the first
  time.
- Whether ArcPy on Windows accepts the `posixpath`-joined layer paths the staging code will
  produce (checked here with hand-built paths, before 1c depends on it).

##### Slice 1c: the runtime around it, a fixture stage end to end, the guide

**Contains.**
- Lifts, each citing its verdict: `core/locations.py` (bucket names out to settings;
  `core/data_objects.py` and `core/pipeline.py`, which it imports, arrive with Task B);
  `staging/workspace.py` with the
  `sidecar` fix; `staging/scratch.py` with the collision check keyed on (call identity, layer)
  per A29 and T2.13, and its contract test: a repeated (trail, leaf) within one bound
  materialiser raises rather than returning a second path;
  `runtime/stage_entry.py` with its errors moved into the taxonomy; the recording spy;
  `tools/run_example.py`; `tests/unit/test_road_operations.py` with its helpers moved to
  `tests/support/`. `staging/transfer.py` is rewritten down to `dump_scratch` over
  `ports/archive.py` (lifted as is; the duplicate Protocol in `transfer.py` is not).
- New: `adapters/storage/filesystem.py`; `runtime/env.py` (`Settings`, §7.1); `runtime/
  compose.py` (`PortSet` in, `Toolbox` out); `runtime/stage_ref.py` (the one import by string,
  `ag.generalization.` only); `runtime/local.py` (§7.5); `runtime/errors.py`;
  `TableOps.exists` and `data_type_of` in both adapters; **`TableOps.create_workspace`** (A5.7,
  T2.12) in both adapters with its conformance cases, `WorkspaceFormat` moved to
  `ports/workspace_format.py`, and `ScratchFileManager.create_workspaces` implemented through it
  (the stage workspace, one per operation, and the sidecar directories, which the manager makes
  itself).
- The example fixtures go live: the `tests/fixtures/example_pipelines` exclusions in
  `[tool.pyright]` and `[tool.ruff]` of `pyproject.toml` are both removed in this slice, so the
  fixtures are type-checked, formatted, linted and collected from here on; with the skeleton's fixture
  stage, two operations using only `select` and `explode_multipart`, derived from the building
  example.
- That stage run through `run_operations` under the fake in CI and under ArcPy on Windows.
- No test-support stopgap for workspaces: under both adapters the manager creates what it names,
  through the port.
- Docs: `docs/contributing/adding-a-port-method.md`, `docs/architecture/errors.md`,
  `docs/contributing/testing.md` (§4).

**Depends on.** 1b; Task B's lift of `core/data_objects.py` and `core/pipeline.py`.

**Done when.**
- `create_workspace` conformance passes on both adapters: the workspace exists afterwards;
  creating one that exists is a `PortContractError`; a missing parent is an `EngineError` naming
  the tool. The manager creates three or four workspaces per pod, not one per handle.
- The fixture stage runs to completion under the fake in CI and under ArcPy on Windows through
  the same `run_operations`; the output sweep is real under the fake (it answers `exists` from
  writes) and fails when an operation is edited to skip an output.
- The three `staging/` defects are covered by tests that fail on the template's code: the same
  leaf name in two operations of one stage is accepted; a repeated leaf in one scope still
  raises; `sidecar` is right for a root containing a dot and for the directory format.
- The scratch root is dumped through the filesystem `ArchiveClient`, manifest included.
- `runtime/stage_ref.py` rejects `ag.adapters.fakes.*`, `ag.runtime.*` and a non-`Stage`
  attribute before importing anything; import-linter row 18 fails when `runtime/compose.py` is
  made to import the fake.
- The surface-completeness run (spy) still executes every fixture operation it can reach with
  the methods declared so far, and says which operations it skipped and why.
- The guide exists and has been followed once by someone other than its author (Task C, §3.1).

**Design record.** T2.12 marked done and A5.7 migrated; `02-runtime.md` §4.2 and §4.3 updated for the collision rule as implemented, workspace creation through the port and the dump; `03-architecture.md` §4.4 and §4.6 updated for `compose`, `stage_ref` and the fake's import contract; the template's `README.md` claims that no longer hold are removed.

**Size.** One to one and a half weeks. It was the fullest of the three at one week, and
`create_workspace` adds about a day (one method, two adapters, three cases, the manager's use of
it) while removing the half-day stopgap. If it has to hold at one week, `errors.md` and
`testing.md` may trail by a few days; the guide may not, because Task C waits for it.

**Review hard.**
- `compose.build_toolbox` is the only composition and takes instances typed by their Protocols.
- `Settings` is built once by an entry point and passed down; nothing else reads the environment.
- `create_workspace` creates what the manager names and chooses nothing: no path is built in an
  adapter, and `staging/` still imports no engine.
- The guide: Task C's review is the guide's review.

#### Slice 2a: identity above the ports

**Contains.**
- `lineage/minter.py`: A10.1 layout (20-bit `minter_id`, 32-bit counter, negative generated,
  positive raw), `minter_id = 0` invalid, the 2^32 - 1 loud failure (A10.5), a `Minter` object
  handed to the session at construction. At K = 1 the local runner hands out `minter_id = 1`.
- `lineage/id_map.py`: the `native_index -> lineage_id` map with both paths (A15.3, T4.5): Path A
  as `write_table` plus `join_field` when the adapter's capability record says the native index
  is join-key addressable; Path B as packed `int64` arrays on pod-local disk with a fixed block
  cache and the two ceilings (A11.4a) as named constants, design ceiling checked first.
  Invalidated on any call naming the handle as an output; row-count guard.
- The port methods the id map and the facade need, each entering with both adapters and its
  conformance cases: `TableOps.write_table` (with A12.7a's call-site declaration), `join_field`,
  `add_field`, `describe_fields`, the native index accessor with its join-key addressability
  declaration (T3.1), and `FieldType.BIGINT` once T0.1 confirms it.
- `lineage/facade.py`: 1a's generic wrapper (one `cast`, reachability test, A11.11) gains its
  lineage logic. Reads `__row_shape__`; on a `MINT` output whose subject is lineage-bearing
  passes its own scratch handle as `parents=` (A11.15 c), maps pairs to `lineage_id`, carries for
  one parent and mints for two or more (A12.4), creates `lineage_id` unconditionally on `MINT`
  outputs (A13), writes the domain's `parents=` in `lineage_id` values, raises on `parents=`
  against a subject without `lineage_id` (A11.15 d). Tracks lineage-bearing per handle at
  runtime from the calls it sees (this is what makes B14 a plan-time-only gap). No accessor to
  the inner port.
- `ports/capabilities.py`: `AdapterCapabilities` (§7.4), published by each adapter and read by
  the facade. It sits in `ports/` because adapters may not import `lineage/`. The ArcPy record
  names `explode_multipart` only until 2b lands.
- `lineage/errors.py` (§6.2).
- `.importlinter`: the `lineage/` protected row; the mint surface choice (T4.3) recorded.
- `runtime/compose.build_toolbox` wraps the ports it is handed in the facade; `run_operations`
  and `runtime/local.py` are unchanged.

**Depends on.** Slice 1c. T0.1's finding (BIGINT viable in the image) before the field type is
frozen; T0.6(a)'s curve for the resource-ceiling method, not blocking.

**Done when.**
- The fixture stage under the fake: `select` carries ids; `explode_multipart` mints per part and
  the id map resolves parents; a domain `parents=` on a lineage-bearing subject receives
  `lineage_id` pairs; on a non-bearing subject it raises before the port is called.
- Under ArcPy on Windows: `lineage_id` is BIGINT on every output of the fixture stage (T0.1 case
  6 for the skeleton tools); Path A's `join_field` on a BIGINT key works (case 8).
- Path B is exercised by a fake adapter that declares the native index not addressable, at 10^5
  rows, with the block cache smaller than the map and the read loop honouring map order.
- 1a's reachability test still passes with the lineage logic in place: every method on the three
  Protocols is reachable through the wrapper, the wrapper is accepted as the port type under
  strict, and `src/ag` still contains one `cast` for it.
- Both ceilings trip with A11.4a's messages on synthetic sizes.

**Design record.** T4.3, T4.5 and T3.1 marked done; A10.1 to A10.5, A11.11, A11.12, A11.15, A13 and A15.3 migrated to the lineage ADR and the `lineage/` docstrings and struck; T0.1's finding written into the id-allocation ADR and B1 resolved; `02-runtime.md` §8 gains the two ceilings; the terminology rows for `lineage_id`, `minter_id`, *mint* and *disk-backed id map* repointed.

**Size.** About two weeks.

**Review hard.** The read-loop ordering constraint of A15.3 in both the map and the facade; the
`cast` at the composition root is the only one; the facade never receives the domain's handle
for the port call; `CARRY` with a null `lineage_id` fails rather than mints (A11.12) even though
edges are not emitted yet.

#### Slice 2b: dissolve parents in the ArcPy adapter

**Contains.** `GeometryOps.dissolve` is declared here, with its full decided signature (`fields`,
`statistics: tuple[StatisticSpec, ...]`, `parents`), single-part by contract (B18), its docstring
stating junction splitting on lines, null handling and output types (A9.11, A9.12), drop
semantics and the two errors; `Statistic` and `StatisticSpec` beside it; `union` and
`DissolveOption` never enter. The fake implements it with an injectable part-splitting rule.
Promote `temp/dissolve_parents.py` and its tests to `adapters/_shared/parents_resolver.py`
(engine-free, importable by the fake and the tests), `temp/arcpy_part_locator.py` to
`adapters/arcpy/support/part_locators.py` and `support/geometry_guards.py`, and `temp/goldens/`
with `temp/test_goldens.py` to `tests/goldens/`, with B17's closing decisions: degenerate is the engine's XY tolerance, the segment
locator for lines with the proximity second pass, the point locator for polygons and points
pending the 904-unmatched diagnostic, `require_matched` raising `UnmatchedInputError`,
`EmptyGeometryError` before the tool, combining rules computed from the pairs joined to input
attributes (A9.11), never the engine's statistics option. `dissolve` enters the ArcPy capability
record. `buffer_dissolve` follows the same path when slice 4 declares it.

**Depends on.** Slice 1b (the session, `pair_tables`, the errors). Independent of 2a; can run in
parallel with 1c and 2a.

**Done when.**
- The eight goldens replay through the promoted resolver.
- The conformance `dissolve` case asserts resolver ⊇ the engine's own lineage table where the
  build has one, and equality with the recorded goldens otherwise.
- **The second pass is tested on the inputs that made `require_matched` raise**, because those
  are the evidence that it is needed and that it works: the STRESS five-field key, where 6 of the
  16 sub-decimetre inputs were left unmatched (log `20260917_181205`), and the national ramps
  subset, where 6 of 12 were (log `20260917_191748`). The OIDs are taken from those logs. On
  both inputs, every one of those segments is paired with the same-key part it lies on,
  `require_matched` no longer raises, and the run prints the count resolved by proximity. The
  same two inputs with the second pass switched off still raise, so the test cannot pass
  vacuously.
- **Partition 18 stays in as a regression case and must still pass.** It is not the evidence
  that the fix works: it passed before the second pass existed, because the locator happened to
  pair all five of its tiny segments.
- A per-part `MAX` statistic on the split-group fixture gives per-part values.
- The 904-unmatched diagnostic is written up (it decides whether polygons close).

**Design record.** T2.10, T4.10 and T4.14 marked done; B17 closed with the four decisions and migrated to the `adapters/arcpy/` package docstring; A9.11, A9.12 and A14.1 migrated to `ports/geometry_ops.py` and struck; the findings' status lines say which of their open items closed here.

**Size.** About one week; the code exists, the work is packaging, the second pass and the
diagnostic.

**Review hard.** Nothing above the port changed (the readiness audit's whole point); the
adapter contract sentence "an input the engine discarded that was not degenerate is an error"
is in the `dissolve` docstring without any XY-tolerance wording (audit §2.10).

#### Slice 3: execution, the operation boundary

**Contains.**
- `lineage/session.py`: `LineageSession` per pod (A15.4); a provisional edge buffer per
  operation; at operation exit the sweep reads each Out's id set and collapses to net effect with
  the three termination clauses (A11.4, A11.8); `EdgeKind` derived (A11.5); `DROPPED` from the
  boundary diff (A11.7); `CREATED` for empty parents; `LineageEdge`, `JobLineageLog` (T4.6); the
  stage-exit sweep (T4.8); the diff-tracked property computed from the stage declaration (A15.2,
  T4.9).
- B10's post-call assertion in the facade: after every call that produces or mutates a
  lineage-bearing handle, `lineage_id` exists with the declared type and no adapter-declared
  duplicate exists.
- T4.4 lineage-aware pipe under A12.7a: `read_rows` on a lineage-bearing handle returns the
  tracked iterable; `write_rows`/`write_table` take the call-site ids declaration.
- `mint(parents=...)` reachable by domain code through the surface T4.3 chose.
- T3.5: the per-job log written pod-local and uploaded through `ArchiveClient` on success.
- `observability/`: JSONL records with the 03-architecture §6 fields, `ContextVar` context,
  timing; warnings routed through it (§6.6).
- `runtime/stage_entry.py` gains the session around each operation and the failure path
  (annotate the error, dump scratch, write the failure record). `run_operations`' signature
  stays.
- One operation over real data end to end: the fixture `simplify_polygons` and
  `build_displacement_feature` (buffer, merge, dissolve) run on a Windows extract of real building
  and road data at K = 1, producing outputs, an edge log and the pod-local halves of the A16
  assertions (which are complete at K = 1 with `D` unpromoted).
- **Fan-out and fan-in as signatures only.** `runtime/fan_out.py` and `runtime/fan_in.py` are
  written as typed stubs against the `Stage` lifted in 1c: the functions, their parameters, and
  the dataclasses that cross them (the partition payload manifest, the run metadata carrying K,
  the reference to a per-job log, the ownership assignment). No bodies. This is the test of the
  inference in slice 5 that `Stage` already carries everything partitioning needs.
- Docs: `docs/contributing/writing-an-operation.md` (A11.4's authoring consequence, A11.13's ref
  columns, when to call `mint`).

**Depends on.** 2a and 2b. A12.7a (signed 2026-09-21). **It starts when four methods from the
slice 4 stream have merged**: `buffer`, `merge` and `densify` on `GeometryOps`, and `simplify` on
`CartographicOps`. The real-data operations use exactly these plus `dissolve` (2b), and they are
the head of the hand-off queue for that reason (§3.1).

*Can they be ready by the end of 2a?* The three `GeometryOps` methods, yes: each is `ONE + CARRY`
with a one-tool ArcPy body, one to two days apiece, two developers, starting when 1c closes,
against 2a's two weeks. `simplify` is the one at risk: it is the first cartography method, its
tool depends on the geometry kind, and its `collapsed_points` output is open (B16; T0.1 case 6
has not run). So for slice 3 `simplify` lands with its main output only. `collapsed_points` is
declared per A12.11 and implemented by the fake (by set difference, which the stage-exit sweep
test needs); the ArcPy adapter raises `CapabilityError` when it is requested, until B16 is
answered. The fixture `simplify_polygons` does not request it. **If `simplify` has still not
merged when 2a and 2b close**, slice 3 runs `build_displacement_feature` alone (`buffer`,
`merge`, `dissolve`): it is A15.5's worst case, covers `ONE + CARRY`, a two-input `CARRY` merge
and `GROUP + MINT`, and needs nothing from `CartographicOps`. If `buffer` or `merge` slipped
too, an operation over `select`, `explode_multipart` and `dissolve`, all landed by 2b, serves,
at the cost of a less realistic subject.

**Done when.** The `resolve_ramps` multi-output shape test emits `(1..5) -> g5` and `g5 -> g9`
(T4.6); the fixture stage's log passes assertions (1) to (3) at K = 1; `map_fields` dropping
`lineage_id` fails naming `map_fields` (B10, B9 d); the per-job log is an uploaded artifact and
a retry overwrites it wholesale; a run with the fake and a run with ArcPy produce edge logs
equal up to id values; **the fan-out and fan-in signatures type-check under pyright strict
against the drafted `Stage` with no additions to `Stage`**. Signatures and the data crossing
them only. If they do not type-check (the recorded doubt is that `Stage` has no partition
sizing input), `Stage` changes here, in slice 3, under review, and not in slice 5.

**Design record.** T4.4, T4.6, T4.8, T4.9 and T3.5 marked done; A11.1 to A11.10, A11.13, A11.14, A12.7, A12.7a, A15.2, A15.6 and A16.2 migrated and struck; `02-runtime.md` §2.4 gains the authoring consequences and §8 the sweeps; if `Stage` changed, §2.3 and the `Stage` rows of the terminology say how; the fan-out and fan-in signatures are reflected in §6.3.

**Size.** About two weeks.

**Review hard.** A11.6's set-membership completeness rather than kind-driven; A16.2's stage-exit
case with `collapsed_points`; the pipe's error on untracked rows written to a diff-tracked output
without a declaration; that no lineage state crosses the pod boundary except artifacts.

#### Slice 4: widening, method by method (the hand-off stream)

**Contains.** Every remaining port method of A12.11 and A12.11a, each as one task: Protocol
declaration with annotations and `@row_shape` per its row, What/How/Why docstring with the
contract sentences DECISIONS assigns to it, ArcPy implementation through `run_tool`, fake
implementation, conformance case(s), capability record entry if `MINT`. Plus the independent
items: T2.1 (structured `Attr` at the fixture call sites), T2.2 `update_rows`, T2.5 linear
referencing, T2.6 `sample_at`, T2.7 docstrings and slots, T2.8 `join_field` contract, T3.1's
adapter declaration, B2 (read the strahler code; `NodeId` `NewType`), the three validation
checks, `normalize_layer_name`, the `networkx` adapter. The one-shot two-way check of A12.11
against the Protocol (T4.2) closes the slice.

**Depends on.** Slice 1c for the guide and the pattern; slice 2a for `MINT` methods' conformance
against the facade; 2b for `buffer_dissolve`.

**Done when.** Every A12.11 row has a method and every row-producing method has a row (T4.2);
the conformance suite has a case per method; `tools/run_example` shows no `AttributeError` off
`tb` for either fixture pipeline; the ArcPy capability record names every `MINT` method the
adapter honours.

**Design record.** Per method, in its pull request: the A12.11 row it implements is struck with a pointer to the Protocol docstring, and the task it belongs to (T2.2, T2.5, T2.6, T2.7, T2.8, T2.9) is updated. At the close: T4.2 done, A12.10 to A12.12 and A12.11a migrated, and `04-migration.md` §1 updated with what each legacy tool became.

**Size.** One to two days per method for a developer once the pattern exists; about 45 methods
across three ports, so it runs for the length of the pass. Method order: `buffer`, `merge`, `densify` and `simplify` first, because slice 3 starts when they
have merged; then the rest of the T0.1 case-6 table
first (they are the `ONE + CARRY` tools whose type survival the conformance suite makes
permanent), then `MANY + MINT` with native references, then `FOREIGN`, then the rest of cartography.

**Review hard.** Per PR, three questions only: does the row match A12.11; does the docstring
state the contract facts DECISIONS assigned to this method (`destination:` lines); does the
conformance case assert the row-shape claim and not merely that the tool ran. Anything else the
guide should have covered is a guide bug.

#### Slice 5: partitioning around the unchanged stage

**Where partitioning belongs and why.** *What follows rests on an inference, not a finding.* The
template's `Stage` carries `context_radius_m` and `InputRole` on `StageInput`, and the argument
assumes that is everything partitioning needs from a declaration. That `Stage` has not been
lifted, and the review records one doubt about it already: it has no partition sizing input,
and nothing else declares one (`template_review.md` §2). Slice 3 tests the inference by writing
fan-out's and fan-in's signatures against the drafted `Stage`; if they need something it lacks,
`Stage` changes there. With that caveat, the argument: operations are
partition-blind by construction, `run_operations` runs a stage's operations against one
workspace, and the facade and session are pod-local (A15.4). So fan-out and fan-in are
additions *around* the partition pod, and everything in slices 1 to 3 is written and tested at
K = 1 with a trivial dispatch. The reason partitioning comes after execution rather than before
is that the lineage artifacts fan-in merges (per-job log, dispatch registry, ingest map) have to
exist first, and the partition-side behaviour that partitioning depends on (idempotence, wholesale
artifact replacement, ownership never in the data) is cheaper to enforce when the pod code is
small. The risk that partitioning is wrong is measured by the legacy track (T1.4) independently.

**Contains.**
- `runtime/fan_out.py`: partition geometry generation lifted from `PartitionIterator`'s
  optimisation logic (not its iteration), K written to run metadata, payloads per partition and
  once at the shared key for context (A6.6 applies the ingest map, mints nothing).
- `runtime/ingest.py` (T3.4): the three-way copy-or-map rule, the four-column ingest map,
  disjoint raw ranges; cold start as an empty incoming column (A22). B9 decides whether map-only
  is reachable.
- `orchestrator/dispatch.py` (T3.3): the run-scoped minter counter and dispatch registry.
- `runtime/fan_in.py`: centroid ownership (A6.1-A6.5) in one shared helper, non-spatial outputs
  by id, K-way log merge and `DROPPED` promotion (T5.1), completeness assertions (T5.2),
  origin-closure check (T5.3), ownership recomputation (T5.4), all appending here (7.4).
- T3.7 foreign-id guard at stage entry folded into A13's check, and again at fan-in.
- `adapters/storage/s3.py`, `gcs.py`; `staging/transfer.py`'s `stage_down`/`stage_up` with pack
  and unpack after handle release; `core/planning.py`'s `build_run_plan` and
  `selection.check_upstream_available`.
- `observability/` log merge (`heapq.merge`) and the warnings summary (§6.6).
- The K-invariance harness under `tests/invariance/`: a stage at K = 4 and K = 16 through the
  new fan-out and fan-in, outputs diffed by multiset on (id, geometry) (A7.2).
- `PartitionIterator` is untouched; it keeps running the legacy pipeline until slice 6 retires
  its callers stage by stage.

**Depends on.** Slice 3; B9 signed; T1.4's verdict (or accept the risk explicitly and keep the
legacy shadow track open).

**Done when.** The fixture pipeline runs at K = 1, 4 and 16 locally (a process per pod, no
Kubernetes) with identical outputs, edge logs that merge to the same completeness verdict, and a
cold-start run from an archived input with no `lineage_id`; a deliberately missed fan-out join
is caught by T3.7(a).

**Design record.** T3.3, T3.4, T3.6, T3.7, T5.1 to T5.4 marked done; A6 to A8, A10.6, A10.7, A16, A21 to A25 migrated to `02-runtime.md` §6, §7, §8 and the ADRs and struck; B9 and B20 resolved. **Then, as the last pull request of the slice, the design documents move to `docs/` (§4.8).**

**Size.** Three to four weeks. The largest slice, and the one with the most decided text to
implement rather than design.

**Review hard.** Fan-in emits no `DROPPED` for discarded context copies (A6.5); no ownership
field ever appears in the data (A6.1); the record format carries no own/context flag (A16.1);
partition pods reach only their own payload.

#### Slice 6: migration of the first real stages

**Recommended first stage: building N100, the simplify-and-point chain.**
`generalization/n100/building/simplify_polygons.py` (159 lines, `AggregatePolygons` then
`SimplifyBuilding` twice, parameters already in `constants/n100_constants.py`) followed by
`polygon_to_point.py` (77 lines, `SpatialJoin` three times and `Merge`). Together they are one
contiguous span of `building_main`, use no partitioning, exercise `aggregate` (GROUP + MINT with
the engine's own parents table), `simplify` with `collapsed_points` (B16's open question, so the
migration is where it gets answered), `spatial_join` (FOREIGN) and `merge` (CARRY), and the
template's building example already mirrors them, so the stage declaration nearly exists.
`calculate_polygon_values.py` (the in-place-mutation example `check_operations_produce_something`
was written for) is the natural third operation.

**Recommended first partitioned stage: the ramps dissolve**, `dissolve_and_return_connection` in
`generalization/n100/road/ramps.py` under `data_preparation_2.py`'s 35,000 / 500 m
partitioning. It is the stage every real-data measurement in the findings was made on, its
input is a national set with a known largest partition, and B20's decision 3 (the national
`run_dissolve_with_intersections` chain is ingest) means its upstream needs no lineage. It is
also 3,900 lines, so this is a slice-6b, not the first cut.

**Contains.** `src/ag/generalization/sources.py` and `products.py` gain the real declarations for the inputs and
products those stages touch (from `data_orchestrator/features/*` and `file_manager/n100/*`);
`classification_rules.py` gets the real policy; `operations/building/` and
`pipelines/building/n100/` become real; `tuning/scale/n100.py` receives the values from
`N100_Values` that are cartographic facts; the legacy `building_main` calls the new stage through
the local runner in place of the two modules, so the rest of the legacy pipeline keeps running;
a smoke test (§5.6) runs the stage over the study-area extract; `04-migration.md` gains the
"how to migrate a stage" recipe from what this cost.

**Depends on.** Slice 3 for the building chain (K = 1); slice 5 for ramps.

**Done when.** The migrated stage's outputs match the legacy module's on the study-area extract
by multiset on (domain key, geometry) within tolerance, the edge log passes completeness, and
the legacy modules are deleted.

**Design record.** `04-migration.md` gains the per-stage status table and the recipe; A9.8 and A9.9 migrated there; `docs/developer_reference/*` files whose legacy package is gone are retired.

**Size.** About two weeks for the building chain including the smoke harness; ramps is a
separate estimate once slice 5 exists.

**Review hard.** That the migrated operation declares only what the legacy code actually did,
not what the template example imagined; that constants split correctly between config values and
scale constants (ADR-0013); that no `in_memory\` literal or `WorkFileManager` survives.

#### The legacy track (beside slices 0 to 3, all hand-off)

**Starts now**, before slice 0 and before the two reviews are approved, because none of it
depends on anything in this plan. T0.2, T1.1, T1.3, T1.4 (the shadow centroid experiment in `PartitionIterator`, gating A6), T7.5
(`SELECT_STUDY_AREA` parser), T0.1 and T0.6 execution, and the `scan_arcpy_usage.py`-based
inventory of tool call sites per legacy stage that slice 6 needs. None touches `src/ag`. Who reviews it is in §3.

---

## 3. Work the other developers can take, and when

| slice | hand-off ready | needs the architect |
|---|---|---|
| **now**, before slice 0 | **Task A** (T0.2 + T1.1) and **T7.5**: both touch only legacy code and depend on nothing in this plan | the two review documents; the decisions of §8.0 |
| 0 | running T0.1 and T0.6(a) in the image; the CI matrix and pre-commit wiring; `docs/README.md`, the CURRENT banners, the Python-floor page; moving the examples to fixtures | creating the tree; `.importlinter` against `project_tree.md` §6, each contract broken once |
| 1a | **Task B**, from the moment 1a's first pull request (the architect's core lift) merges; it lifts the rest of the core declaration modules, citing their verdicts; T1.3 once T1.1 is in; the fake's `MemoryStore` once its interface is sketched | row shape, markers, errors, the three Protocol methods, the facade spike |
| 1b | the engine-neutral fixture builders in `tests/support/`; running the Windows conformance run and the timing run | the session and `run_tool`, the ArcPy adapter's first three methods |
| 1c | `normalize_layer_name`; the filesystem `ArchiveClient`; the `sidecar` and collision-key fixes with their tests | settings, compose, the local runner, the fixture stage, the guide. **Task C** starts when the guide exists |
| 2a | Path B's packed map with the block cache once the map interface is fixed; T2.5, T2.6, T2.7 (touch only `geometry.py`/`table_ops.py` docstrings and the value type) | minter, facade, capability record, the `lineage/` contract |
| 2b | the 904-unmatched diagnostic; the proximity second pass; goldens on the image (T4.11 case 1b) | B17's closing wording in the docstring |
| 3 | `observability/` (03-architecture §6 is a complete spec); T3.5's upload; the real-data K = 1 run and its report | session, sweeps, pipe, B10 |
| 4 | everything (one method per task) | reviewing against the guide; B11 if `displace_features` comes up; T2.8's mutator declaration; B2's verdict |
| 5 | S3 and GCS adapters; pack/unpack; the K-invariance harness runner; T5.3, T5.4 | fan-out ownership, ingest, dispatch, log merge, completeness |
| 6 | the second and later stages once the first is a recipe; `sources.py`/`products.py` transcription from `data_orchestrator` and `file_manager`; the arcpy call-site inventory per stage | the first stage; the split of constants |

**Who reviews the legacy track while it runs beside slices 0 to 3.** The two developers review
each other's legacy-track pull requests (T0.2, T1.1, T1.3, T7.5). The work is fully specified in
TASKS.md, touches no `src/ag` code and needs no architecture judgement, so it must not queue
behind the architect while slices 0 to 3 are under review. The architect reviews exactly three
things on that track: T1.4's written judgment, because it can invalidate A6 and is an
architecture verdict rather than a code review; and the written findings of T0.1 and T0.6,
because they gate 2a. A disagreement between the two developers on a legacy pull request is
escalated; otherwise it merges on peer approval.

### 3.1 The first three hand-off tasks, and when each can start

**Task A: T0.2 + T1.1, the shadow centroid selection in `PartitionIterator`.**
**Starts now; it depends on no slice.** Reviewed by the other developer. Files: `custom_tools/general_tools/partition_iterator.py` only. Spec is TASKS.md T0.2 and T1.1
verbatim (hook at `_extract_partition_output`, `HAVE_THEIR_CENTER_IN` against
`iteration_partition`, orphan test against `self.partition_feature`, multiset equality on (id,
geometry) via hashed `Counter`s, CLIP outputs excluded, JSON through `write_documentation` with
the claim record and drift distribution split by geometry type). Acceptance is T1.1's list plus:
the shadow is not selectable by callers, and a run of `data_preparation_2.py` on the study area
produces the JSON. Runs on Windows with the ArcGIS interpreter. Nothing in it depends on a
design decision; A6 and A7 are settled and this is their test. Two to four days.

**Task B: the three unimplemented validation checks.**
**Starts when the first pull request of 1a has merged.** That pull request is the architect's
core lift (`core/types.py`, `injection.py`, `handles.py`, `operations.py`, with the `@operation`
restructuring). Task B then lifts the rest it needs, each module citing its verdict in
`template_review.md`: `core/data_objects.py`, `pipeline.py`, `graph.py`, `policy.py`,
`findings.py`, `validation.py`. All six are "keep as is" or "keep with changes" with the changes
listed, so the lift is mechanical, and none of them is `core/operations.py`, which no hand-off
touches. Files: `src/ag/core/validation.py`, `tests/unit/core/test_validation.py`, and
purpose-built minimal fixture stages with portless operations beside the tests, because the
example pipelines import `ag.ports` and stay inert until 1c. Implement `check_stage_graph_acyclic` (Kahn over
`graph.derive_stage_dependencies`, report cycle members and the inducing object chain),
`check_no_coarser_input` (rank via `ScaleRanking.rank`, RAW never trips) and `check_publications`
(`policy.publication_classification` must permit the identity's location; a PREM_ONLY object
bound for `gs://` is the error). Each check's docstring already states what it catches and why it
cannot move earlier; `02-runtime.md` §8 items 11, 13, 15 are the spec. Acceptance: a minimal fixture
with a PREM_ONLY object published to a `gs://` identity is reported by `check_publications` (the
building example's deliberately inconsistent `N100_BUILDING_POLYGONS` publication becomes a
second assertion when the example fixtures go live in 1c); a fixture with `op1(A) -> op2(B) -> op3(A)` is reported as a cycle naming
both stages; N25 reading N100 is reported; `validate()` on the two fixture pipelines reports
exactly those and nothing else. No ArcPy. Two to three days.

**Task C: the first widening method, `GeometryOps.buffer`.**
**Starts after 1c, when the guide exists.** Files: `src/ag/ports/geometry_ops.py`,
`src/ag/adapters/arcpy/geometry_ops/<group>.py`, `src/ag/adapters/fakes/memory/geometry_ops/<group>.py`
(the group is the Protocol section the method is declared under), and
`tests/conformance/test_geometry_ops_<group>.py`. In both adapters the group class gets the
method and nothing else; helpers are module-level functions (`project_tree.md` §3.2, §7).
Following `docs/contributing/adding-a-port-method.md`: declare `buffer(*, input: In, output:
Out, distance_m: float, end_cap: EndCap = ROUND, join_style: JoinStyle = ROUND) -> None` as
`@row_shape(output=Rows(ONE, CARRY, subject="input"))` (A12.11 row); docstring states it is the
non-dissolving buffer and that `buffer_dissolve` is the GROUP + MINT twin (A5.6), and that
`distance_m` is signed for polygons. ArcPy compiles to `PairwiseBuffer` with `dissolve_option`
NONE through `session.run_tool`; the fake copies rows and marks geometry as buffered (it does not
compute a buffer). Conformance: row count preserved; declared field types preserved through the
tool, `lineage_id` BIGINT among them on a stamped fixture (T0.1 case 6 made permanent);
`native_index` of the input unchanged; negative distance on a polygon fixture does not raise;
`EngineError` on a line input with a negative distance carries the tool name. Acceptance: the
PR contains the row, the docstring, both adapters, the cases, and the T4.2 two-way check still
passes. One to two days; the review takes twenty minutes if the guide is right, which is the
point of doing this one first.

Queue behind Task C, in order. **First, because slice 3 starts when they have merged: `merge`
and `densify` (`GeometryOps`), then `simplify` (`CartographicOps`, main output; see slice 3).**
Then T2.7, T2.5, `normalize_layer_name`, `copy`, `map_fields` (the B9(d) case), T2.6, the
`networkx` adapter, then the remaining `MANY + MINT` methods.

---

## 4. Documentation

### 4.1 Where documentation lives

`docs/**/*.md` is browsed on GitHub; Sphinx renders only `generated_docs/` API pages for the
legacy packages and does not see `docs/`. Keep it that way for this pass: markdown under
`docs/`, a link checker in CI (README action 5), and point `sphinx-apidoc` at `src/ag` in slice 4
once the port docstrings are worth publishing. Do not add a MyST build now; nothing in the plan
needs it.

### 4.2 The documents

| document | covers | created / updated in |
|---|---|---|
| `docs/refactor/` as a whole: `01-terminology.md`, `02-runtime.md`, `03-architecture.md`, `decisions/`, `temp/DECISIONS.md`, `temp/TASKS.md` | **the working design record for this change**; stays where it is and is updated in place, in the same pull requests as the code (§2.2) | every slice; moves once, at the end of slice 5 (§4.8) |
| `docs/README.md` | index: `setup/`, `contributing/`, `developer_reference/`, each with its status; gains `architecture/`, `decisions/` and `terminology.md` at the move. It never indexes `refactor/`: nothing outside `docs/refactor/` references the design record unless tooling needs the path to run | 0, 5 |
| `docs/architecture/errors.md` | the taxonomy of §6, the raise/warn/log rules, what every error carries | 1a (with the error modules), completed 1c |
| `docs/architecture/lineage.md` | short: the seam in one page (parents at the port, ids above it, edges at the boundary), pointing at the ADRs and the `lineage/` docstrings | 3 |
| `docs/contributing/adding-a-port-method.md` | the guide (§4.5) | 1c |
| `docs/contributing/toolchain.md` | uv as the environment and tool manager: installing it, `uv sync --extra dev`, `uv.lock`, hooks through uv, the two environments on Windows (A27) | 0 |
| `docs/contributing/python-version.md` | the Python target and how to raise the floor (§4.7) | 0 |
| `docs/contributing/testing.md` | the layers of §5, markers, what runs where (the four buckets from the platform decision) | 0, updated 1c and 5 |
| `docs/contributing/writing-an-operation.md` | operation authoring: In/Out, config, scratch, ports only, `mint(parents=)`, ref columns, what not to do | 3 |
| `docs/contributing/migrating-a-stage.md` | the recipe, written from slice 6's first stage | 6 |
| after the move: `docs/terminology.md`, `docs/architecture/runtime.md`, `docs/architecture/structure.md`, `docs/decisions/` | the same documents, settled (§4.8) | end of 5 |
| `docs/refactor/04-migration.md` | stays until the migration completes; gains the per-stage inventory and status table | 6 |

The split is by what a document describes. **A document describing landed code is created under
`docs/` when that code lands** (the port-method guide, testing, errors, the Python floor, writing
an operation, migrating a stage). **A design document stays under `docs/refactor/` and is kept
current there until its content has settled.** Nothing moves before its content has landed, so
no document ever needs a per-section landed/pending marker.

Package docstrings remain the home for what DECISIONS assigns to them (`adapters/arcpy/`
package docstring for A14.1 and B17, the lineage module docstring for A11.x, `ports/*.py` for the
contract facts). Documents point at docstrings; they do not repeat them.

### 4.3 How `01-terminology.md` becomes the real terminology document

- **Stays at `docs/refactor/01-terminology.md` while the pass runs**, updated in place: each
  slice repoints the authority column of the entries whose A-items it lands (step 3 of the
  migration protocol) and adds the terms it introduces. **Moves** to `docs/terminology.md` once,
  with the other design documents, at the end of slice 5 (§4.8). The three tables move whole. The collisions table (§2) is the part with the
  most value for an AI reader and stays verbatim. The retired table (§3) stays; entries whose old
  word never reached code (`origin_id`, `correspondence`, the old row-shape enums) move to a
  short "never existed" note at the bottom so the table reads as what to avoid, not history.
- **Drops** the TARGET header and the graduation clause; the `LineageRoot` renaming note (T7.2
  done in slice 0); the `@row_shape(out=...)` example (the patch fixes it).
- **The authority column** keeps citing A-ids until each item migrates; the migration protocol's
  step 3 repoints them. After the lineage record moves under `docs/decisions/` (§4.4) an A-id
  citation is a permanent link, so the "no entry cites an A-id" completion clause becomes
  "every citation resolves", which `check_terminology.py` already tests for anchors.
- **A new check** in `tests/static/`: every backticked identifier in the terminology tables that
  names a class, function or field (`ScratchHandle`, `lineage_id`, `PARENT_ID`, `Statistic`)
  exists in `src/ag` by grep. That is what makes the document "the vocabulary reference for the
  implemented system" mechanically rather than by intent.
- **Who updates it:** the author of the PR that introduces or renames a term, in the same PR,
  and the reviewer refuses a PR that adds a public identifier the tables do not know. The static
  check catches removals; the reviewer catches additions.

### 4.4 What happens to `DECISIONS.md`

**Recommendation: it stays one file, stays at `docs/refactor/temp/DECISIONS.md` while the pass
runs so that every citation in findings, pull requests and `check_consistency.py` keeps resolving,
moves to `docs/decisions/lineage-decision-record.md` once at the end of slice 5 (§4.8), and is
never deleted.** The rationale migrates into ADRs per the existing protocol; the
file becomes the permanent index of A- and B-ids.

Why not ADRs only: the completion test in TASKS.md deletes `temp/` when every A-item has landed,
which is exactly the moment every `A11.15` citation in findings, docstrings, PR descriptions and
this plan becomes a dead reference. The A-numbering is stable *because* the file is; deleting the
file breaks the property it exists for. Why not a split: forty numbered items across six files
is the section-number rot the README warns about.

Mechanics:
- The file keeps its structure. As an item migrates, its body is replaced by one line:
  `**A11.15** moved to ADR-0017 §Decision and the `lineage/` package docstring.` The heading and
  number stay, so the anchor stays.
- New ADRs, numbered from 0015, written under `docs/refactor/decisions/` beside the fourteen while
  the pass runs and moved with them (§4.8), one per cluster the `destination:` lines
  already name: identity (A9, A10, A24, A25), lineage mechanism (A11, A13, A15, A16), row shape
  and the port contract (A12, A14.1, A18), partition ownership (A6, A7, A8), cross-run lineage and
  retention (A21, A22, A23). Five, not forty. Each ADR's Context section cites the A-ids it
  absorbs, so a reader arriving from either side finds the other.
- B-items resolve into A-items as now, or are promoted to a named open question in the owning
  document. The record keeps the B-id line either way.
- `check_consistency.py` is retargeted at the new path at the move (§4.8) and stops being temp-lifetime.

### 4.5 The port-method guide is slice 1c

It is written after the skeleton's methods exist in both adapters, from what they took, and before the first
slice 4 hand-off. Contents: the A12.11 row lookup; the annotation rules (`In`, `Out`, `Mutates`,
`ParentsOut`); the docstring skeleton (What / How / Why, plus the contract facts a method must
state: drop semantics, null handling, what it never does); `session.run_tool`; the fake
implementation's obligations (§5.7); the conformance cases by row-shape cell; the capability
record entry; the T4.2 two-way check; the PR checklist the reviewer applies. Task C in §3.1 is
its first use and the review of Task C is the review of the guide.

### 4.6 The older `docs/refactor/` material

| item | fate | when |
|---|---|---|
| `template_code/` | stays as the source for lifts; T7.2 is applied inside it in slice 0; the examples leave for `tests/fixtures/` in slice 0; deleted when its last module has been lifted or dropped | during 4 |
| `01-terminology.md` | stays, updated in place; moves to `docs/terminology.md` at the move (§4.8) | end of 5 |
| `02-runtime.md`, `03-architecture.md` | stay, updated in place by every slice (§2.2); move to `docs/architecture/` at the move. No per-section status markers: nothing moves before its content has landed | end of 5 |
| `04-migration.md` | stays; deleted on completion as it says | 6+ |
| `README.md` | stays; its "recommended actions" are struck as slice 0 performs them; becomes `docs/architecture/README.md` at the move | end of 5 |
| `decisions/` | stays; new ADRs from 0015 are written here beside the fourteen; moves to `docs/decisions/` at the move | end of 5 |
| `check_terminology.py` | runs in CI from slice 0 where it is; moves with the terminology document | 0, end of 5 |
| `temp/DECISIONS.md` | stays, items struck in place as they land; moves to `docs/decisions/lineage-decision-record.md` at the move | end of 5 |
| `temp/TASKS.md` | stays in `temp/` as the task tracker until its tasks are done; its status column is the one place progress is recorded | throughout |
| `temp/findings/*` | stay; move to `docs/decisions/evidence/` at the move: the measurements are the rationale for A14.1 and B17 and must outlive `temp/`. This plan, `template_review.md` and `project_tree.md` go with them as the record of the pass | end of 5 |
| `temp/goldens/`, the resolver scripts | promoted with slice 2b | 2b |
| `temp/PROPOSALS-*.md`, `REVIEW-*.md` | deleted once signed or recorded, as they say. PROPOSALS §2 and §3 are signed (A12.5a in the patch, A12.7a on 2026-09-21); §1 (B9) is what keeps the file | when B9 is signed |
| `docs/developer_reference/*` | CURRENT banner now; each file retires when the legacy package it describes is deleted | 0, 6+ |
| `file_seames_discussion/` | archive per README action 1 and 2 | 0 |

### 4.7 The Python target, and raising the floor

Decided 2026-09-21; landed in slice 0 as `docs/contributing/python-version.md`, which is now
the authority. Revised the same slice: Black was replaced by ruff format for the new code, and
the CI workflow states the version too, so four settings move together, not three. Black was
retired altogether on 2026-10-02 (A28).

- **The target is Python 3.13.** There is no fixed lower constraint. The project follows its
  runtimes upward: the target is the lowest Python minor version across the supported runtimes
  (the ArcGIS Pro interpreter the team develops with, and the Linux image). Nothing is in
  production yet, so no older build constrains it.
- **Four settings state it, and they always change together:** `requires-python`, pyright's
  `pythonVersion` and ruff's `target-version` in `pyproject.toml`, and `.python-version`, which
  uv reads locally and in CI.
- **CI runs the pure-core suite on that version**, on both runners.
- **Raising the floor.** Raise it only when every supported runtime has moved. Change the
  four settings in one pull request; run the full check set; say in the pull request which
  runtime had been holding the floor. Do not raise it for a language feature.
- **One thing a raise must not do:** convert `In` and `Out` to PEP 695 `type` statements. The
  review confirmed that `@operation` then classifies no parameter, because the `Annotated`
  metadata is hidden behind a `TypeAliasType`. A unit test pins it.

### 4.8 When the design documents move, and what the move involves

**When: once, as the last pull request of slice 5.** By then `02-runtime.md` §2 to §8 and
`03-architecture.md` §2 to §7 describe implemented code (declarations, the ports, the layering,
storage scopes, partition correctness, validation, the fan-out and fan-in loop run locally), the
bulk of the A-items has been struck into ADRs and docstrings, and the citation traffic from
findings and pull requests has died down. Earlier would mean moving documents that are still
being revised and changing the path every live citation uses. Later has no natural point: slice
6 is open-ended. What is still target at that moment (the Kubernetes loop of `02-runtime.md`
§6.3 and §6.4, the Job spec of `03-architecture.md` §8) is named in one sentence of each
document's header, not marked per section.

**What moves, in one pull request of `git mv` and mechanical retargeting, with no content
edits:**

| from | to |
|---|---|
| `docs/refactor/01-terminology.md`, `check_terminology.py` | `docs/terminology.md`, `docs/check_terminology.py` |
| `docs/refactor/02-runtime.md`, `03-architecture.md`, `README.md` | `docs/architecture/runtime.md`, `structure.md`, `README.md` |
| `docs/refactor/decisions/` (ADR-0001 onward) | `docs/decisions/` |
| `docs/refactor/temp/DECISIONS.md`, `check_consistency.py` | `docs/decisions/lineage-decision-record.md`, `docs/decisions/check_consistency.py` |
| `docs/refactor/temp/findings/` | `docs/decisions/evidence/` |

`TASKS.md` and `04-migration.md` stay under `docs/refactor/` until their work is done; both are
disposable by their own terms.

**The retargeting, all of it greppable:**

- **The two checker scripts become tests and their hooks go** (decided 2026-10-02). Every hook
  must still run after `docs/refactor/` is deleted in full, so no hook may name a document path
  after the move. `check_terminology.py` becomes `tests/static/test_terminology.py` over
  `docs/terminology.md` and the architecture documents, and absorbs the two checks of
  `check_consistency.py` that concern the glossary's authority column (every cited A-id resolves
  in `docs/decisions/lineage-decision-record.md`; every headword appears there): permanent.
  `check_consistency.py`'s other four checks (A-orphan, dangling-ref, ordering, B-referenced) all
  read `TASKS.md` and become `tests/static/test_task_plan.py`, the one test module that still
  reads `docs/refactor/`; the deletion commit deletes it with the directory. Both checker hooks
  are removed from `.pre-commit-config.yaml` at the move; the `pytest` hook carries the tests.
  Run the scripts and the tests side by side once; the findings must be identical. The
  terminology test rewrites nothing: the authority column's `file.md#anchor` citations are
  retargeted in the documents by the move itself, and the test proves every one resolves.
- Citation paths: `temp/DECISIONS.md`, `temp/findings/...`, `02-runtime.md`, `03-architecture.md`,
  `01-terminology.md` and `decisions/NNNN-...` as they appear in the documents themselves (their
  links to each other), in `TASKS.md`'s `destination` and `doc migration` lines, in module and
  package docstrings under `src/ag`, in the contributor guides, in the CI workflow and
  pre-commit steps that run the two checkers, and in `.claude/settings.local.json`'s allowlist.
  **A-ids, B-ids, T-ids and ADR numbers do not change**, which is why they were made stable.
- **Acceptance for the move:** the markdown link checker in CI passes, **and**
  `git grep "docs/refactor"` outside `docs/refactor/` returns nothing but the paths of
  `TASKS.md` and `04-migration.md`, which stay. The link checker sees only markdown; the grep
  also sees `.importlinter`, `pyproject.toml`, `.pre-commit-config.yaml`, the CI workflow,
  `tools/` and the docstrings under `src/ag`, which is where a stale path survives a link check.

**The final step: `docs/refactor/` is deleted in full.** After the move it holds only
`TASKS.md`, `04-migration.md` and whatever `temp/` still carries. Its trigger is stated once:
**`TASKS.md`'s completion test passes and `04-migration.md`'s per-stage table shows every stage
migrated**, at which point both documents have done what they exist for. One pull request then:

- deletes `docs/refactor/` with everything under it, including `temp/`, `TASKS.md` and
  `04-migration.md`;
- deletes `tests/static/test_task_plan.py`, the one remaining reader of the directory;
- removes any allowlist entry that named the deleted paths.

**Acceptance for the deletion:** `git grep "docs/refactor"` over the whole repository returns
nothing, and `pre-commit run --all-files` is green with no hook referencing a path that no
longer exists. Deleting `docs/refactor/` is one commit that breaks nothing; what makes that
true is kept true from slice 0 on: prose outside `docs/refactor/` names no slice number, plan
section, task id or temp document, and only the two checker hooks reference the directory
until the move removes them.

---

## 5. Tests

### 5.1 Layout and where each layer runs

```
tests/
  unit/            no ArcPy; the bulk; CI on ubuntu and windows
  static/          contract tests: import-linter, row-shape check, port matrix, arcpy-blocked
                   import guard, terminology-matches-code, Attr.raw count, capability coverage
  conformance/     one module per port, parametrized over adapters; fake in CI, arcpy marked
  goldens/         recorded artifacts and their replay tests
  invariance/      K = 4 vs K = 16, local processes; arcpy marked (slice 5)
  smoke/           one real stage end to end; arcpy marked (slice 6)
  support/         engine-neutral builders, the adapter fixture, local_scope
    arcpy/         the .gdb builders: constrained stub, session.run_tool, imported lazily
  fixtures/        example_pipelines/, row fixtures
```

Buckets, per the platform decision already recorded: pure-Python checks in pre-commit and CI on
both runners; `arcpy`-marked tests under an ArcGIS Pro Python environment and in the image under
Docker; conformance also gates image promotion; the two gates are one-off in the image.
`pytest -m "not arcpy"` in pre-commit and CI, excluding by marker; an unmarked test that imports
ArcPy fails on `ImportError`, which is the property the marker exists for. `tests/conftest.py`
makes the marker behave the same everywhere: without ArcPy a bare run skips marked tests with a
reason, and `-m arcpy` fails the session instead of reporting green. `pyproject.toml` registers
the marker and the `testpaths`, and no default `addopts`, so a developer runs `pytest -m arcpy`
explicitly. The legacy tests live in `tests_legacy/`, outside `testpaths`, run by hand under the
Pro environment, and are deleted with the code they test.

### 5.2 The conformance suite

`tests/conformance/test_<port>.py`, one test function per method per claim, parametrized with an
`adapter` fixture that yields the fake always and the ArcPy adapter under the marker. The suite
drives the **Protocol directly**, not the facade (B10's fifth site), and **from slice 2a on** every case
builds its input through the adapter's own `write_rows`, so a fixture is engine-neutral. Until
`write_rows` lands, the builders in `tests/support/` seed inputs directly (the `MemoryStore` for
the fake; a small `.gdb` written with the engine, under the `arcpy` marker), as slice 1b
describes. The builders' interface does not change when they switch, so no case is rewritten.

What it asserts, per row-shape cell:

| cell | asserts |
|---|---|
| every method | output exists with the declared `DataType`; the input's `native_index` set is unchanged after the call (T4.11 1a); declared field types survive (T0.1 case 6, permanent); the method goes through the error wrapper: a fake told to fail yields `EngineError` with `tool` and `messages` |
| ONE + CARRY | row count equal; every declared attribute value preserved; on a fixture stamped with a BIGINT `lineage_id`, the column is present with type BIGINT on the output (T4.11 2) |
| MANY + MINT, GROUP + MINT | with `parents=None` no table is written and nothing else changes; with `parents=` a handle, the table has `PARENT_ID`/`CHILD_ID` in native indices, `PARENT_ID` references the subject only (A11.15 a), the pair set equals the fixture's declared expected partition; for `dissolve`, resolver ⊇ the engine's own lineage table where the build has one and equality with the recorded goldens otherwise, per-part statistics on a split-group fixture (A9.11), `EmptyGeometryError` before the tool with the offending indices, `UnmatchedInputError` on a fixture the guard must reject; an adapter whose capability record omits the method raises `ParentsUnavailableError` and never returns an empty table (A14.1) |
| FOREIGN | the declared ref columns exist and hold subject native indices; a null ref is permitted and present on the no-match fixture; no `lineage_id` column is created |
| `Mutates` (in-place) | row identity preserved; the named written fields changed and nothing else; the input's `describe_fields` after the call is as declared |
| in-place cartography (`displace_features`, `propagate_displacement`) | the input handle's geometry is unchanged after the call (T4.11 3) |
| adapter-level | the duplicate-field naming rule the adapter declares is what the engine produces on the overlay-duplicate fixture (T0.1 case 7); the capability record names every `MINT` method the adapter implements and no other |

How the parents assertions fit: the goldens recorded on Pro 3.7.2 are the oracle everywhere the
native table is absent; on a build with the table the case computes both and asserts the resolver
is a superset (B17, decision 1). The suite never asserts geometry equality across engines; it
asserts the partition of inputs into parents and the lineage invariants (conclusion §7).

### 5.3 Golden files, where they earn their place

- `dissolve` parents on the eight boundary fixtures and partition 18's subset (exist).
- Compiled predicates: the SQL string the ArcPy adapter produces for a set of `Predicate` trees
  per workspace type (catches quoting regressions with no ArcPy).
- Rendered scratch paths and the manifest for the fixture stage under both workspace formats.
- The edge log of the fixture stage under the fake, normalised by mapping ids to their first
  appearance (slice 3).
- The `tools/run_example` derivation output (already the drift detector for the documents).

Not goldens: geometry outputs of real tools (engine drift), timings, anything the K-invariance
diff already compares against itself.

### 5.4 Contract tests (`tests/static/`)

- `lint-imports` as a test and a CI step; the package-coverage meta-check; `arcpy` only under `ag.adapters.arcpy` (with tools, `arcpy.env` and vendor exceptions only in
  `session.py`, enforced by the stub and a scan), `networkx` in one module, `shapely` only under
  `adapters/`.
- T4.1's row-shape check over every Protocol method: every `Out` has a row; every row names an
  `Out`; `subject`/`context`/`refs` name an `In`; both axes present; `MINT` has a subject;
  `FOREIGN` has refs; the three illegal cells; `ParentsOut` exempt; query methods explicitly
  listed as outside the grammar.
- Every port handle parameter carries exactly one of the four markers (A12.5a).
- The A12.11 two-way check (one-shot in slice 4, kept as a frozen list afterwards).
- The port matrix: every adapter module ends with the `if TYPE_CHECKING` conformance
  assignment, and every `(port, adapter)` pair has a conformance module (03-architecture §7.6).
- The facade reaches every Protocol method (A11.11).
- The arcpy-blocked subprocess guard: importing every fixture pipeline with `arcpy` stubbed to
  raise succeeds (02-runtime §2.6).
- `Attr.raw` call-site count pinned; `SLF001` clean on the three domain packages.
- Terminology-matches-code (§4.3).

### 5.5 ArcPy-only tests

Marked `arcpy`; conformance and everything above that needs an engine, T0.1's cases kept as a
permanent module once the gate has run, the image checks (locale decimal mark in anything the
adapter parses, `memory\` paths, the goldens replayed in the image). On a developer machine:
`pytest -m arcpy` under an ArcGIS Pro Python environment. In the image: the same command
under Docker, triggered by image rebuilds and by changes under `adapters/arcpy/`. The licence
question for the image is open and decides whether that gate is automatic.

### 5.6 The smoke test

`tests/smoke/test_stage_end_to_end.py`: the first migrated stage (§2.2 slice 6) over the
study-area extract, through `runtime/local.py` with the ArcPy adapter: outputs exist with the
declared types; row counts within a recorded band; the edge log passes the three completeness
assertions at K = 1; the scratch dump lands through the filesystem `ArchiveClient`; total time
under a recorded budget. It is the test a developer runs before opening a migration PR.

### 5.7 What the fake adapter must simulate, and what it must not

**Must.** Tables as in-memory row stores keyed by the handle's path, holding `Row` values with
attributes and geometry; a native index that is a dense integer assigned on write and
**reassigned when the dataset is next written**, so A9.2's contract is exercised rather than
assumed; declared field types, so a BIGINT column stays one and a LONG one overflows loudly;
parents for every `MINT` method by a declared rule (`explode_multipart` one child per part;
`dissolve` groups by `fields` with an injectable part-splitting function so a fixture can make a
key split into several parts; `clip` and `difference` one child per input row it keeps) so the
facade and the conformance suite see the same pair-table shape ArcPy produces; the pre-call
empty-geometry check; failure injection (a `fail_on(method, exception)` hook that makes the next
call raise a fake engine exception, which the wrapper must turn into `EngineError`); a duplicate
field naming rule (`_1` suffix) on overlays and joins; a capability record with everything it
implements and a switch to declare the native index not join-key addressable, so Path B of the
id map has a test adapter.

**Must not.** Compute geometry: a buffer copies the input geometry, a dissolve concatenates parts,
an intersection keeps every input row, a spatial predicate answers by bounding box or by an
injectable oracle. Model tolerances, degenerate lengths, engine messages beyond a string, or
performance. Reproduce the engine's part splitting on lines. Anything the fake computes
"correctly" is a second engine to maintain and a way for a test to pass on the fake and fail on
ArcPy for a reason the fake hid; the fake is row-identity accurate and geometry naive, and the
docstring says so.

---

## 6. Errors and warnings

### 6.1 Layout

| layer | module | base | members |
|---|---|---|---|
| core | `ag/core/errors.py` | `AgError(Exception)` with an `ErrorContext` | `ErrorContext`; `InjectionError` (a value the runtime should have supplied never was: the `INJECTED` and `NOT_INJECTED` sentinels and an unmaterialised handle raise it from `core/` and `ports/`, so it cannot live in `runtime/`); import-time declaration errors stay `TypeError`/`ValueError` as the template raises them, because they fire while a module is being imported and a project base class buys nothing there |
| port | `ag/ports/errors.py` | `PortError(AgError)`: what a caller can see from a port call | `EmptyGeometryError`, `UnmatchedInputError`, `ParentsUnavailableError` (all T2.4 / A14.1), `EngineError` (a wrapped vendor exception: `engine`, `tool`, `messages`), `PortContractError` (a caller broke a stated precondition: key in `fields` for `update_rows`, `lineage_id` as a statistic source, a negative distance where the docstring forbids one) |
| adapter | `ag/adapters/errors.py` | `AdapterDefectError(AgError)`: the adapter itself is wrong, never a data condition. A **sibling** of `PortError`, not a subclass: code that handles `PortError` must never swallow a defect in the adapter | `LocatorContractError` (a cross-key pair from a locator), `CapabilityError` (a method called that the record says is unsupported, other than parents) |
| lineage | `ag/lineage/errors.py` | `LineageError(AgError)` | `LineageFieldError` (B10: column absent, duplicate, wrong type; A11.12: null on `CARRY`), `DesignCeilingError`, `ResourceCeilingError` (A11.4a, two types because the fixes differ), `ParentsOnUnbearingSubjectError` (A11.15 d), `ForeignIdError` (A25), `CompletenessError` (A16), `UntrackedWriteError` (A12.7a) |
| domain | `ag/generalization/errors.py` (importable by `helpers/` and `operations/` alike) | `DomainError(AgError)` | `DataContractError` (an operation's assumption about the data failed: `_node_id`'s "feature_id must be LONG"); nothing else until an operation needs it |
| runtime | `ag/runtime/errors.py` | `StageRunError(AgError)` | `OutputMissing` (a bare `RuntimeError` subclass in the template), `WorkspaceError` (leaf collision, over-budget name), `StageInputMissing` |

This table is reconciled with `template_review.md` §5, which lists every raise site in the
template and what it becomes; the template has no error module of its own.

Six modules, one base each, about sixteen leaf types. Adding a port method adds none of them:
its failure modes are `EngineError` (the tool failed), `PortContractError` (the caller broke the
docstring), or one of the three parents errors. A new exception type is justified only by a new
*recovery*: a caller that would catch it differently from its siblings.

### 6.2 What every error carries

`ErrorContext(operation: str | None, port: str | None, method: str | None, handle: str | None,
row_indices: tuple[int, ...], row_count: int | None, tool: str | None, tool_messages: tuple[str,
...])`, on `AgError.context`. Row indices are capped (first 20) with the total in `row_count`.
The layer that knows a field fills it: the adapter fills `method`, `tool`, `tool_messages`,
`row_indices`; the facade fills `handle` and `port`; `run_operations` fills `operation` on any
`AgError` passing through it and appends a one-line `add_note()` (PEP 678) so the traceback reads
`operation resolve_ramps, geometry.dissolve, handle Network.dissolved, rows 8701, 11698 ...`.
The rule is fill-if-empty, never overwrite, so an error thrown from inside a helper keeps the
innermost method. That is what lets a failure localise without a re-run, and it is why a
partitioned run's failure record (slice 5) is the serialised context plus `partition_index`.

### 6.3 When a component raises, warns or logs, and what a caller catches

| component | raises | warns | logs |
|---|---|---|---|
| adapter | engine failure (`EngineError`), precondition broken, parents it cannot produce, a non-degenerate input it could not match, an empty shape in a subject | degenerate inputs skipped (count and indices), proximity-resolved pairs (count) | every tool call with timing, at INFO; engine messages at DEBUG |
| facade / lineage | the lineage errors of §6.1; nothing is downgraded to a warning because every one of them means the log would be wrong | the two `CREATED` ∧ `DROPPED` detectors of T4.13 that are WARNING by decision | mint counts per operation |
| operation | `DataContractError` only; an operation catches nothing from a port, because it has no recovery and catching would hide the context | nothing directly; it reports through data (a `match_report` table) | per-operation progress at INFO |
| runtime | `StageRunError`; re-raises everything else after annotation | orphan features claimed by nearest (count), drift beyond a threshold | the stage timeline |
| fan-in (slice 5) | `CompletenessError`, `ForeignIdError`, ownership mismatch | partition warnings aggregated | the merged summary |

Callers: an operation catches nothing. `run_operations` catches `AgError` to annotate, dump
scratch, write the failure record and re-raise. The local runner and the pod entry point turn the
class into an exit code (contract 2, engine 3, lineage 4, runtime 5, adapter defect 6) so the orchestrator can
apply `podFailurePolicy` without parsing text.

### 6.4 Engine exceptions never escape an adapter

`adapters/arcpy/session.py` owns `run_tool(name, call, *, rows_of=None)`: it runs the call,
drains `arcpy.GetMessages()`, and on `arcpy.ExecuteError` (or any exception from the vendor
module) raises `EngineError(engine="arcpy", tool=name, messages=...)` from it. Every adapter
method calls tools through it; nothing else in `adapters/arcpy/` names an `arcpy` exception. Two
checks make that a property rather than a habit: a static test that the strings `ExecuteError`
and `except arcpy` appear only in `session.py`, and the conformance case that a fake told to fail
yields `EngineError`. The same shape applies to `networkx` and to the storage clients (`boto3`,
`google.cloud` exceptions wrap into a `TransportError(PortError)` in their adapters).

### 6.5 Warnings

`ag/core/warnings.py`: `AgWarning(UserWarning)` with `LineageWarning`, `DataQualityWarning`,
`PartitionWarning`. Emitted with `warnings.warn(..., category)` from the layers above. Rules:
a warning is for a result that is *correct but degraded or suspicious* (degenerate inputs
dropped, orphans claimed by nearest, the T4.13 detectors); anything that makes an output or the
log wrong raises.

### 6.6 How warnings survive a long partitioned run

`logging.captureWarnings(True)` in every entry point routes them into the JSONL sink with the
category as a structured field and the `ErrorContext`-shaped fields where the emitter has them.
Each pod's session keeps a per-category counter with the first message and up to five example
row indices, written into the pod's run metadata at exit. Fan-in merges the counters, prints the
summary once, and promotes a category with a non-zero count to a `Finding` of severity WARNING
in the stage record so it appears beside the completeness verdict rather than in 150 pod logs.
The orchestrator's log merge writes `warnings.jsonl` beside `merged.jsonl`. A warning is
therefore visible three ways (pod log, stage summary, merged file) and lost in none.

---

## 7. What else belongs in this pass

### 7.1 Configuration and environment parsing (slice 1c)

One frozen `Settings` dataclass in `ag/runtime/env.py`, built once by the entry point from the
environment through typed parsers (`require_str`, `require_bool` accepting only `true`/`false`
case-insensitively, `require_int`, `optional`), never read at import time, and passed down as a
value. Fields for this pass: scratch root, workspace format, keep-scratch flag,
log level, the study-area extent for local runs, storage roots (the buckets `locations.py`
hardcodes today) and later the pod identity (`JOB_COMPLETION_INDEX`, run id, stage name). The
composition root is the only reader; nothing under `core/`, `ports/`, `operations/` sees an
environment variable, and an import-linter contract forbids `os.environ` there through a small
static test. T7.5 fixes the legacy readers in the same convention so the two codebases agree
while both run. Not a port (02-runtime §10: configuration is data with many values).

### 7.2 Structured run logging and the edge log (slice 3, merge in slice 5)

Two artifacts, deliberately separate. The log is for humans and timing: JSONL, the §6 fields,
progress and warnings, never a `lineage_id`. The edge log is data: written by the session,
uploaded as an artifact, read only by fan-in and the query API. They share the run id and the
per-pod prefix so one download gets both, and nothing else joins them. Timing records per
operation and per tool call make the merged log a partition profile, which is what the
`timing_decorator` does today.

### 7.3 Scratch lifecycle and cleanup (slice 1c policy, slice 5 remote)

Per 02-runtime §4 and 03-architecture §4.6: the pod scratch root starts empty; declared handles
are always kept until the dump; adapter-internal intermediates are deleted on a method's success
and kept on its failure; the whole root is dumped at exit under the policy (default on) and dies
with the pod. For local runs on Windows nothing dies, so the local runner creates a fresh root per
run under the configured scratch root, dumps to a filesystem archive location, and deletes the
root unless `keep-scratch` is set. The legacy `WorkFileManager` and the `in_memory\` literals do
not carry over; the migrated stage's intermediates come only from `ScratchScope`.

### 7.4 The capability record (slice 2a)

In `ports/capabilities.py`, because adapters publish it and may not import `lineage/`:
`AdapterCapabilities(engine: str, build: str, parents_for: frozenset[str], native_index_joinable:
bool, duplicate_field_rule: DuplicateRule, statistics_supported: bool)` published by each adapter
at construction (A14.1). Consumers: the facade (which parents channel to expect, which id-map
path, which duplicate names to fail on) and `validate()` as data once B14 gives it a derivation
of which port methods a stage calls. The record names methods, never mechanisms.

### 7.5 A local entry point for running a stage (slice 1c)

`python -m ag.runtime.local --stage <module:STAGE> --root <dir> --adapter arcpy|fake
[--extent ...] [--keep-scratch]`. It is the driving adapter for development and the walking
skeleton's proof. Its core is a function that takes a `Stage` object; the command line resolves
the reference through `runtime/stage_ref.py`, which accepts only modules under
`ag.generalization.`, and tests pass a fixture `Stage` directly. There is no adapter setting: a
pod has one engine, and the fake is chosen only by this module's flag, which is also the only
module allowed to import it (`project_tree.md` §4). It builds `Settings`, builds a `PortSet`
(ArcPy through `compose.arcpy_ports`, or the fake), hands it to `compose.build_toolbox` (the one
composition; the facade joins it in 2a), constructs the `ScratchFileManager` at `Tier.PARTITION` with index 0, copies stage inputs
from local paths into the stage workspace (a stand-in for `stage_down`), runs `run_operations`,
dumps scratch. The pod entry point of slice 5 is the same function with `stage_down` and
`stage_up` around it. The orchestrator CLI is outside this pass.

### 7.6 Things the template assumes that the decisions do not cover

- `ScratchFileManager.create_workspaces` needs an engine (decided 2026-09-21: A5.7, a `TableOps` method, in 1c).
- Two `ArchiveClient` Protocols (§1.2); resolved by deletion.
- `calculate_field(expression: str)` documents "a CQL2-shaped expression both can compile"; the
  template's examples are SQL `case when` and `lpad`, which ArcPy's CalculateField (Python or
  Arcade) cannot take. No decision names the expression language. This is not needed by the
  skeleton, but 101 legacy call sites use CalculateField and slice 6 will hit it (§8.1).
- The recording toolbox's `exists` answers from handles seen in any call; the fake of §5.7
  answers from writes, so `run_operations`' sweep is real under the fake.
- The example pipelines carry the A17 defects; relocated and fixed as fixtures (§1.5).
- `run_operations` materialises handles but nothing places stage inputs; the local runner does
  (§7.5).
- `Toolbox` has four ports; the facade wraps three (`graph` carries no handles).
- The observability accessor import rule of 03-architecture §4.2 is not in `.importlinter`; add
  it in slice 3 when the accessor exists.

### 7.7 Deliberately not in this pass

Kubernetes execution (`orchestrator/execute.py`, the cluster adapter, Job specs); the publish
step and T0.4 (B9); the lineage query API and edge storage format (T6.1, T6.2); the
`cartography/` package; any engine adapter beyond ArcPy and the fake; NFS substrate; trail
elision (`render_trail` errors deliberately); `dissolve_multipart` and an unsplit method (no
caller until migration reaches them); the displacement declaration (B11); GraphOps
dataset-awareness (B2 stays open); `StyleOps`; resumability; a per-stage backend override
(the template names the extension point and says not to build it).

---

## 8. Risks and blocking gaps

### 8.0 Decisions needed before slice 0: all made, 2026-09-21. §8.0 is closed.

Decided by the architect on 2026-09-21 and recorded in `DECISIONS.md` and `TASKS.md` the same
day, each placed so that the unapplied patch still applies (`git apply --check` passes, and
`check_consistency.py` passes both before and after the patch).

| # | decision | rests on | outcome |
|---|---|---|---|
| 1 | Approve `findings/template_review.md` | this plan's rule that every lift cites a verdict; the five defects it confirmed by running the template | **Approved as written, 2026-09-21.** Every lift cites its row. The two verdicts that change most downstream are the handle fixes (A15.3's cache keys on handle equality) and the `ArchiveClient` verdict. |
| 2 | Approve `findings/project_tree.md` | 03-architecture §7, §4.1, §4.2; ADR-0005, ADR-0012, ADR-0013 | **Accepted**, with §2 option B (domain code under `ag/generalization/`), §3.1 option A (one module per port Protocol), §3.2 (group classes hold Protocol methods only), §4 (the fake importable by `runtime/local.py` only; one constrained import by string) and §6.1 (ArcPy importable under the whole ArcPy adapter, with a stub that omits tools, `env` and exceptions as the guard). |
| 3 | Apply `PATCH-2026-09-17.patch` | the patch; every slice cites its items | **Decided: applied as the first act of slice 0.** Recorded at the head of `DECISIONS.md`. B17's closing wording is still owed before 2b. |
| 4 | A12.7a, the signature | PROPOSALS-2026-09-14 §3; B13; A12.7 against A15.6 | **Signed as proposed.** `DECISIONS.md` A12.7a (after A12.7, which carries a supersession note); B13 marked resolved; `TASKS.md` T4.4 carries the acceptance additions and cites it. The check of 1a treats an `Out` whose row is declared at the call site as a category of the grammar. |
| 5 | Workspace creation (raised here as B21) | no A-item covered it; `staging/` may not import an engine | **Decided: option (a), `TableOps.create_workspace`.** `DECISIONS.md` A5.7, with B21 kept as a resolved entry; `WorkspaceFormat` moves to `ports/`; `TASKS.md` gains T2.12. Delivered in slice 1c in both adapters with conformance cases; the test-support stopgap is dropped. |
| 6 | `IN` and `IS NULL`; `Attr.cmp`'s operator set | `in_` and `is_null` were already A2.1 | **Decided:** `=`, `<>`, `<`, `<=`, `>`, `>=`, `LIKE`; values are `AttributeValue` without `None`; nulls go through `is_null`. One sentence under A2.1 in `DECISIONS.md`; implemented in 1a. |
| 7 | Python target 3.13 | §4.7 | **Decided.** `DECISIONS.md` A26; `TASKS.md` T7.4 cites it; slice 0 sets the three settings. |

### 8.1 Remaining gaps, ranked by what each gates

A gap that gates a slice stops that slice from starting or from being accepted. A gap that gates
one method stops that method's widening and nothing else. Within a group, the order is the order
in which the answer is needed.

| gates | gap | what is missing | proposal |
|---|---|---|---|
| **slice 0** | the architect's go | §8.0 is closed and the plan, the tree and the review are approved (2026-09-21); slice 0 starts on a separate go, and nothing enters `src/` before it | none needed |
| **slice 2a** | **T0.1 has not run in the image** | BIGINT viability decides the field type of every lineage-bearing output (B1) | Run it in slice 0. If it fails, A10.1's layout does not survive, and TEXT or paired LONG changes every call site that stores an id; 2a waits for the finding. |
| slice 2a | the mint surface (T4.3) | a public `ag.lineage.api`, or through the `Toolbox`; B10 says both cost one contract | Recommend through the `Toolbox`: operations then import nothing from `lineage/`, which keeps import-linter row 10 at one allowed importer and matches A11.12. It adds a fifth `Toolbox` field typed by a small Protocol in `ports/`. Decide at the 2a review. |
| slice 2a, not blocking | the resource ceiling's value | T0.6(a) unmeasured | provisional constant from A11.4a; the method is calibrated later |
| **slice 2b** | B17's closing text | the patch's B17 predates the decisions on the degenerate threshold, the second pass, the chain as ingest, and the locator per geometry type | write the closing paragraph into B17 before the adapter's package docstring cites it |
| slice 2b, polygons only | the 904-unmatched diagnostic | decides whether the point locator closes for polygons and points | run it in 2b; the synthetic squares cover polygons in conformance meanwhile |
| **slice 3** | `Stage`'s sufficiency for partitioning | an inference until fan-out's and fan-in's signatures are written against it (slice 3 acceptance) | if they need a partition sizing input, decide then whether it is a `Stage` field, a run-plan value or a setting |
| slice 3 | the work-key API's home (T3.2) | "helpers/ or a new peer package" | `ag/lineage/work_key.py`: operation-scoped identity, swept by the same session; already in the accepted tree |
| **one method in slice 4**: `calculate_field` | **the expression language** | the port docstring promises "a CQL2-shaped expression both can compile"; the template's call sites write SQL `case when`; ArcPy takes Python or Arcade; 101 legacy call sites | decide before that method is widened, not before slice 4 starts: recommend a closed expression form (field arithmetic, `case`, a few string functions) compiled per adapter, with `read_rows` and `update_rows` as the escape |
| one method: `displace_features` | B11, the `displacement` output | one branch has no legal cell | widen the method without that output until T0.1 case 6 records the mapping shape |
| four methods: `update_rows`, `delete_fields`, `calculate_field`, `join_field` | T2.8's mutator declaration (A12.11a's option) | which parameter names the fields a mutator writes | decide when the first of them is widened; recommend taking the option |
| one check in `validate()`, no slice | B14, the plan-time derivation of port calls | `validate()` cannot know which port methods a stage calls | the recording spy's trace is the candidate; runtime tracking in the facade covers execution meanwhile |
| two optional outputs: `simplify.collapsed_points`, `displace_features.displacement` | the pattern for a declared-but-unavailable optional output | the first is declared and refused by the ArcPy adapter with `CapabilityError`, the second is left undeclared; and `CapabilityError` sits under `AdapterDefectError` although a declared limitation is not a defect | recorded as an open note on B16 and B11 in `DECISIONS.md`; settled when either is decided; no change now |
| one method, first exercised in slice 6: `simplify.collapsed_points` | B16 | the tool's point output is documented as lacking the input's fields | the set-difference derivation is the contract, per T0.1's "neither present" branch |
| **slice 5** | **B9 unsigned** (PROPOSALS §1) | whether the archive carries `lineage_id` decides ingest's map-only branch, T3.6, T3.7(a), T0.6(b), T0.4 | sign before slice 5; the proposal is complete |
| slice 5 | B20's decision 3, written down | the national dissolve chain as ingest is recorded in the conclusion document only | write it into B20 |
| slice 5 | the study-area extent | the development-time extent limit has no home in the design | an extent on the local runner in 1c and on `RunRequest` for fan-out in slice 5; recommend an A-item |
| the cluster pass, outside this plan | run-scratch retention, cluster topology, node-disk `emptyDir`, the licence in the image | 02-runtime §11 | none blocks local K = 4 against K = 16 |

### 8.2 Where the design is most likely wrong in an expensive way, and the cheapest early test

| risk | why it would be expensive late | cheapest early test | slice |
|---|---|---|---|
| The native index is not stable enough to key parents across the calls the pipeline makes (A9.2) | every parents mechanism and Path A of the id map key on it | conformance case: a `.gdb` input whose `OBJECTID`s are non-dense after deletes, run `select` then `explode_multipart`, assert `ORIG_FID` maps to the pre-call index set and `native_index` is unchanged | 1b |
| A generic facade cannot satisfy a `Protocol` under pyright strict without per-method code (A11.11's "one cast") | 40 wrappers or a code generator | **now a deliverable of slice 1a**, not a risk to watch: a generic wrapper with no lineage logic, one `cast`, pyright strict clean, reaching every method, with the reachability test | 1a |
| `join_field` on a BIGINT key at national scale is slow or coerces (Path A) | the preferred ArcPy id-map path falls back to Path B everywhere | T0.1 case 8 and T0.6's `JoinField` timing at three sizes | 0, 2a |
| The edge-emission model at the operation boundary mis-handles multi-output operations (A11.8) | forensic answers wrong on every ramp-like operation | the `resolve_ramps` unit test with the fake, written before the session | 3 |
| `read_rows` as `Row` dataclasses over millions of rows is too slow or too large for the pipe and for parents mapping (A4.4) | the bulk-IO design under ADR-0004 needs a columnar path | the capped, incrementally logged timing run of slice 1b over the 2.3 M-row national road set; if the projection is minutes for a partition-sized input, add a columnar read before slice 3 rather than after | 1b |
| Lineage overhead on real partitions exceeds A15.7 on `buffer_dissolve` or polygons (unmeasured) | `build_displacement_feature` is A15.5's worst case | run the promoted resolver on a real building-polygon partition and the displacement buffer in 2b | 2b |
| The K = 1 code path hides a partition dependence (halo, ownership) that only shows at K > 1 | slice 5 finds it after slices 2 to 4 are built | the legacy shadow track (T1.1, T1.4) runs from now on the current implementation, which is the same data and the same tools | legacy track |
| ArcPy on Windows rejects `posixpath`-joined `.gdb` layer paths or the name budget miscounts | every local run fails on the developers' machines | hand-built paths in the slice 1b Windows run, then the fixture stage in 1c | 1b, 1c |
| pyright strict forces `cast`s into `@operation`, weakening call-site checking | the declaration mechanism is the design's strongest selling point | the first pull request of 1a is the architect's core lift and carries the `@operation` restructuring; no hand-off lifts or edits `core/operations.py`, so there is no race and nothing to rebase | 1a |

### 8.3 What not to build yet, and why

- **Fan-out and fan-in before the artifacts they merge exist.** Slice 5's log merge, promotion
  and completeness depend on the per-job log and dispatch registry; building the pod machinery
  first means re-writing its contract when they land.
- **Path B of the id map before Path A works on ArcPy**, beyond what a fake-backed test needs.
  A15.3 keeps both permanent; on the one engine this pass targets the preferred path is Path A, and
  the review's F24 proposes deferring the packed path. Build Path B against the fake in 2a, tune
  it after T0.6.
- **The lineage query API.** Nothing reads the log mid-run by design, and the storage format
  (T6.1) is chosen for the resolver, which needs merged logs from slice 5 to be designed against.
- **A second engine adapter.** The fake is the second implementation for contract purposes; a
  GeoPackage or PostGIS adapter before the surface is closed would be written twice.
- **The publish step and delivered-copy schema** (B9, T0.4). Undecided, and every in-run flow
  works without it.
- **A resolution mechanism for tuning, a per-stage backend override, a workflow engine,
  fingerprint invalidation**: 02-runtime §10 already says no; the template names the extension
  points and leaves them unbuilt, and that is correct.
- **Migrating a road stage first.** `data_preparation_2.py` has 26 first-party imports and four
  partition runs; `ramps.py` is 3,900 lines. The building chain is a two-week proof; a road stage
  first would be a two-month one with nothing reviewable in between.
