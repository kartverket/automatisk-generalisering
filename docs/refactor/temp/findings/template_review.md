# Template review: `docs/refactor/template_code/`, module by module

**Status:** APPROVED as written by the architect, 2026-09-21. Originally a review for approval, 2026-09-21 (entry slices and decided items aligned with the revised plan, the accepted tree and the decisions of the same day). Slice 0 of `implementation_plan.md` depends on the
approval of this document and of `project_tree.md`. Nothing here is a decision; each verdict is a
proposal and the A- and B-items it cites are the authority.

**What this is for.** The template was a learning pass. No module is promoted wholesale.
A module enters `src/ag` only in the slice that needs it, and the PR that lifts it cites its row
here. A lifted module that departs from its verdict says why in the PR.

**Verdicts.** *Keep as is* means the code is lifted unchanged apart from the two cross-cutting
edits in §1. *Keep with changes* lists the changes. *Rewrite* keeps the intent and replaces the
code. *Drop* means it does not enter `src/ag` in this pass. Target paths follow
`project_tree.md`; where that document offers two layouts the path is given for its
recommendation.

**How it was reviewed.** Every file under `template_code/` was read. Five suspected defects were
confirmed by running the template under Python 3.12 from a scratch script (no file in the
repository was changed); they are marked *(run)* below. `run_example.py` passes today only
because neither worked pipeline happens to trigger them.

---

## 1. Two cross-cutting edits that apply to every lifted module

These are not repeated per row.

1. **Docstrings are converted to the project convention.** The template's docstrings are essays
   with capitalised headings, and several contain code examples (`ScratchScope`, `@operation`,
   `OperationFn`, `ProductIdentity`, `push_negation`). The convention is What / How / Why on entry
   points and classes, brief for helpers, no code examples (`docs/contributing/docstring.md` plus
   the plan's constraints). On lift: the first line `TEMPLATE, not shipped. Target module ...`
   goes; the What and How stay; the Why is cut to the argument a maintainer needs at that site
   plus a pointer to the ADR or A-item that holds the rest; examples move to the contributor
   guides. This matters more than it looks: DECISIONS sends a great deal of rationale to
   "module docstring" destinations, and without a length rule those docstrings regrow (§6, item 7).
2. **`LineageRoot` becomes `OriginRoot`** and `lineage_roots()` becomes `origin_roots()` (B8,
   T7.2). Slice 0 applies the rename inside the template and the documents, so every later lift
   carries the new name.

---

## 2. `core/`

| module | verdict | reason and changes | rests on | enters |
|---|---|---|---|---|
| `types.py` | **keep as is** | Closed `StrEnum`s for `Scale` and `ObjectName`, `TypeAlias` over `NewType` with the reason stated, `Classification.join` failing closed. Nothing in DECISIONS touches it. | 02-runtime §2; ADR-0012 | 1a, first pull request (the architect's core lift) |
| `injection.py` | **keep as is** | A nominal marker with no behaviour is the honest encoding of "who supplies this". | ADR-0014 | 1a, first pull request |
| `operations.py`, handle half (`ScratchHandle`, `handle`, `Handles`, `Direction`, `In`, `Out`, `ScratchScope`, `INJECTED`) | **keep with changes** | The design is decided and correct: frozen handle, `path` `compare=False`, `namespace` in equality, `__set_name__` naming. Four changes. **(a)** Move to its own module `core/handles.py` so that "ports and adapters import handles only" (03-architecture §4.1) becomes a module-level import contract instead of a convention; see `project_tree.md` §6. **(b)** Add the `Mutates` and `ParentsOut` markers beside `In`/`Out` (A12.5a); `@operation` rejects both on an operation signature. **(c)** `__set_name__` restamps silently: one `handle()` object bound in two class bodies ends with the second class's namespace for both *(run: `A.h.namespace == "B"`)*. Raise if the handle is already named. **(d)** Internal scratch handles are built with an empty namespace, so two operations' `scratch("dissolved")` compare equal and hash equal although they are different files *(run: a dict keyed by the two has one entry)*. A15.3 keys the id-map cache and its invalidation on `ScratchHandle`, and the facade's lineage-bearing tracking will do the same, so this conflates handles across operations. Stamp internal handles with a namespace derived from the operation (the workspace stem is enough). Keep `In`/`Out` as `TypeAlias`: a PEP 695 `type` alias hides the `Annotated` metadata from `_direction_of` *(run: returns `None`)*. | ADR-0011, ADR-0014, A12.5a, A15.3 | 1a, first pull request, with the fixes and the markers; no hand-off lifts or edits it |
| `operations.py`, operation half (`@operation`, `_classify`, `OperationCall`, `CONFIG_PARAM`) | **keep as is** | Reads name, direction, config and injected kinds off the signature; every rejection fires at import; `injected` keyed by type fixed the `wants_scratch` bug and is tested. Expect pyright-strict friction at `functools.update_wrapper` and `__dataclass_params__`; resolve by restructuring, not by suppressing, because this decorator is what makes a declaration site type-checked. That restructuring is architecture work and is part of the architect's core lift. | ADR-0011, ADR-0014 | 1a, first pull request |
| `data_objects.py` | **keep as is** (rename only) | Three identity-equality symbols, `origin` as roots only, no `location` on `Derived` by construction. | ADR-0012, B8 | Task B, which starts when the core lift has merged |
| `pipeline.py` | **keep as is** (rename only), with one recorded doubt | `Stage`, `StageInput`, `StageOutput`, `Publish`, `Pipeline`, `StageRegistry`, `flatten` match 02-runtime §2.3 and §2.5. The doubt: `Stage` carries `context_radius_m` and input roles but **no partition sizing input**, and nothing else declares one (the legacy stages pass 35,000 elements and 500 m). Whether that belongs on `Stage`, on the run plan or in settings is not decided anywhere. The plan's slice 3 tests it by writing fan-out's signature against this class. | 02-runtime §2.3, §7.3 | Task B |
| `locations.py` | **keep with changes** | One owner for every remote path is right. `StorageRoots.for_environment` hardcodes four bucket names: that is deployment configuration and moves to the settings object. `payload_location(obj: object)` with a `getattr` fallback becomes `DataObject`. | 02-runtime §4.1 | 1c (dump path), 5 (payloads) |
| `graph.py` | **keep as is** | Derivation by the one rule, both edge kinds, deterministic Kahn. | 02-runtime §3 | with Task B |
| `selection.py` | **keep with changes** | Imports `validation` only for `Finding`. Move `Finding` and `Severity` to `core/findings.py` so selection does not depend on the validation module. `check_upstream_available` stays unimplemented until slice 5. | 02-runtime §6.1 | 5 |
| `policy.py` | **keep as is** (rename only) | Classification over stage wiring, monotone precedence, fail closed. | 02-runtime §5 | with Task B |
| `planning.py` | **keep with changes** | Dataclasses are fine. `build_run_plan(request: object, ranking: object, rules: Sequence[object])` types three parameters as `object`; type them. Both functions stay unimplemented until slice 5. | 02-runtime §6.2 | 5 |
| `validation.py` | **keep with changes** | The twelve implemented checks are right and each says why it cannot move earlier. **(a)** `validate(registry, ranking: object, rules: Sequence[object])` says "loose to avoid an import cycle"; there is no cycle (`policy` does not import `validation`), so type them `ScaleRanking` and `Sequence[ClassificationRule]`. **(b)** Three checks are `NotImplementedError` and specified: hand-off Task B. **(c)** `not_statically_checkable()` is a function that exists to hold a docstring; drop it, the text is already in 02-runtime §8. | 02-runtime §8 | with Task B |

---

## 3. `ports/`

| module | verdict | reason and changes | rests on | enters |
|---|---|---|---|---|
| **row shape** | **absent; write from the decisions** | The template predates A12. There is no `row_shape.py`, no declaration on any method, and every port handle parameter is a bare `ScratchHandle`. What the template does contribute is the `Annotated` marker mechanism in `core`, which A12.5a reuses. New: `Cardinality`, `Ids`, `Rows` with the three illegal cells rejected with A12.1's messages, `@row_shape(**outputs)` storing `__row_shape__` on the Protocol function, and the T4.1 check. One fact the grammar's docstring must state: a `Spatial` predicate embeds a `ScratchHandle` (`relate_to`), so a handle can reach a port method inside a value, outside the `In`/`Out` annotations. It is harmless for lineage (a predicate's handle is context by nature and is never written) but the check cannot see it, and saying so stops someone "fixing" it. | A12.1 to A12.6, A12.5a, A11.11 | 1a |
| `toolbox.py` | **keep as is** | Frozen four-field bundle, namespaced access, `NOT_INJECTED` with the one load-bearing cast, `Injected` inheritance so `core` never names it. Exactly A1.3 and ADR-0008. If T4.3 chooses to reach `mint` through the `Toolbox`, that is a fifth field added then, not now. | A1.3, ADR-0008, ADR-0014 | 1a |
| `geometry.py` | **keep as is** | Immutable value type, `parts` always a sequence of rings, no `GeometryCollection`, null geometry as `None`. T2.5 and T2.7 are additive. | ADR-0004, A4.4, A4.6, A5.1, A5.3 | 1a (`read_rows` returns `Row`, which carries a `Geometry`) |
| `geometry_ops.py`, enums and predicate algebra | **keep with changes** | `Relation`, `EndCap`, `JoinStyle`, `VertexPosition` (already has `DANGLE`, so A5.5 is done), `Predicate`, `Spatial` with its `__post_init__`, `And`/`Or`/`Not`, the sugar constructors: all decided and correct. `Attr(cql: str)` is **rewritten** into structured leaves plus `Attr.raw` (A2.1). `DissolveOption` is **dropped** (B18). The algebra moves to `ports/predicates.py`, because `cartographic_ops` imports it too and with structured `Attr` it is no longer a footnote to one port. | ADR-0001, A2.1, A5.5, B18 | 1a |
| `geometry_ops.py`, the Protocol | **keep with changes**, method by method | Method names, OGC vocabulary, keyword-only and units-in-the-name conventions are right. Decided changes: delete `union` (A5.4); split `buffer`, `spatial_join`, `nearest_neighbors`, `extract_vertices` (A5.6); `dissolve` loses `option`, gains `statistics` and `parents` (B18, A9.12, A11.15); `parents` on the other four `MINT` methods; `fields: tuple[str, ...]` becomes `tuple[FieldName, ...]`; annotations and row shapes throughout. Methods enter one at a time as their slice needs them, never as a block. | A5.4, A5.6, A9.11, A9.12, A11.15, A12.11, A17.3, A18 | 1a (three methods), 2b (`dissolve`), 4 (rest) |
| `table_ops.py` | **keep with changes** | `FieldType`, `Field`, `Schema`, `Row`, the closed `AttributeValue` union and the no-cursor bulk IO are decided. Changes: `FieldType.BIGINT` (A10.1, gated by T0.1); `Row` gets `slots=True` (A4.4); native index accessor with the join-key addressability declaration (A9.2, T3.1); `update_rows` (A4.3); the `join_field` unique-key contract (B4, T2.8); call-site ids declaration on the two writes (A12.7a, unsigned); annotations and `map_fields`' row (A12.11a). `calculate_field(expression: str)` promises "a CQL2-shaped expression both can compile" while the template's own call sites write SQL `case when` and `lpad`; no decision names the expression language, and that gates the method's widening. | ADR-0004, A4.x, A9.2, A12.6, A12.11a, B13 | 1a (`read_rows`), 1c (`exists`, `data_type_of`), 2a, 4 |
| `cartographic_ops.py` | **keep with changes** | ICA operator names and the one-method-for-line-and-polygon choice are right. `parents` on `aggregate` and `collapse_to_centerline`; `displace_features.displacement` stays undeclared until B11; rows per A12.11. | A11.15, A12.10, A12.11, B11 | 4, 6 |
| `graph_ops.py` | **keep with changes** | Pure-value form, undirected. `NodeId` becomes `NewType` (A3). Four methods have no caller in the package and one (`articulation_points`) has none anywhere by the module's own admission; under slice-by-slice entry, declare a method when its caller migrates. Q-C stays open. | A3, B2 | 4 |
| `archive.py` | **keep as is; this one survives** | See §3.1. | 02-runtime §10, ADR-0006 | 1c |
| `cluster.py` | **drop from this pass** | Correct as a contract, no caller until the orchestrator pass, which is outside the plan. It returns from the template then. | 02-runtime §1.3 | not in this pass |
| `ports/__init__.py` | **rewrite** | The idea (one import line at the head of an operation module, Protocols deliberately absent) is kept; the list is rebuilt as the surface lands. | 03-architecture §7.2 | 1a |

### 3.1 The two `ArchiveClient` Protocols

`ports/archive.py` declares `upload(*, local_path: str, location: Location)` and
`download(*, location: Location, local_path: str)`. `staging/transfer.py` declares a second
`ArchiveClient` with `read(location, into: ScratchHandle) -> ScratchHandle` and
`write(source: ScratchHandle, location)`.

**`ports/archive.py` survives, unchanged; the one in `transfer.py` is deleted.** Reasons:

- It is the newer of the two and states the argument against the other: a handle names a slot
  under a join rule only `staging/` knows; what crosses to object storage is a file or a packed
  directory, which is a path. A transport that took handles would have to know the workspace
  format, which `staging/workspace.py` exists to be the only place for.
- Protocols for driven ports live in `ports/` (03-architecture §7.2). A Protocol declared in its
  caller's module is how the two drifted apart with nobody noticing.
- `transfer.py`'s version returns a `ScratchHandle` from `read`, which puts materialisation in
  the transport; `ScratchFileManager` owns that.

Two things are kept from `transfer.py`: clients keyed by URI scheme (an on-prem pod reads
`gs://` and `s3://` in one run), and the two-methods-until-a-third-has-a-caller rule. The third
method is already visible: `selection.check_upstream_available` needs `exists(location)` and a
completion marker. It is added in slice 5 with that caller, not before.

---

## 4. `adapters/`, `staging/`, `runtime/`, `orchestrator/`, packages with only a docstring

| module | verdict | reason and changes | rests on | enters |
|---|---|---|---|---|
| `adapters/arcpy/predicates.py` | **keep with changes** | Lifts to `adapters/arcpy/support/predicate_compiler.py` (`project_tree.md` §3.2). `push_negation` and `Negated` are correct and carry the only non-obvious claim of ADR-0001, with thirteen tests. `apply` is unimplemented and assumes `cql_to_sql(term.cql)`; under A2.1 it compiles structured leaves with identifier quoting per workspace type. | ADR-0001, A2.1 | 1b |
| `adapters/fakes/recording_toolbox.py` | **keep as is**, narrower role | It is a spy, and says so. Once the in-memory fake exists the spy's jobs are the surface-completeness run and B14's trace candidate. Its `exists` answers from any mention of a handle, so the output sweep is weak under it; that is acceptable for a spy and is the reason the fake answers from writes. | 03-architecture §7.6, B14 | 1c |
| in-memory fake | **absent; new** | `fakes/__init__.py` asks for fakes that "genuinely buffer, intersect and dissolve". The plan rejects that: a fake that computes geometry is a second engine to maintain. Row-identity accurate, geometry naive (plan §5.7). | T4.11 | 1a |
| `adapters/__init__.py`, `adapters/arcpy/__init__.py`, `adapters/fakes/__init__.py` | **rewrite** | Package docstrings are destinations for A14.1 and B17; written when their content lands. Two claims in them no longer hold and must not be lifted: "`import arcpy` appears in exactly one file" (it is tools, `arcpy.env` and vendor exceptions that appear in one file; `project_tree.md` §6.1), and `errors` listed under `arcpy/` (the errors a caller sees are in `ports/errors.py`). | A14.1, B17 | 1b, 2b |
| `staging/workspace.py` | **keep with changes** | Format knowledge in one module, computed name budget, error rather than truncate. **(a)** `sidecar()` uses `rpartition(".")` on the whole path: a root containing a dot gives the wrong directory *(run: `/tmp/run.1/n100_road` yields `/tmp/run`)*, and for the directory format the sidecar is the workspace itself, so loose files land among the shapefiles. Strip a known suffix from the last segment only. **(b)** `normalize_layer_name` is unimplemented and specified (hand-off). **(c)** `windows: bool` is passed by hand; derive it once in settings. **(d)** `WorkspaceFormat` moves to `ports/workspace_format.py`, because `TableOps.create_workspace` names it (A5.7); the join rule, name legality and the name budget stay here. | 02-runtime §4.2 | 1c |
| `staging/scratch.py` | **keep with changes** | Two workspace tiers, no timestamps, the manifest: decided. **(a)** The leaf-collision check is keyed on the rendered layer name without the operation, so the same leaf in two operations of one stage raises "already issued in this pod" although they live in different workspaces *(run)*. Key on (operation, layer). **(b)** `create_workspaces` is unimplemented and its docstring names `CreateFileGDB`, which `staging/` may not call. Decided 2026-09-21 (A5.7): it calls `TableOps.create_workspace` through the toolbox the runtime hands it; implemented in 1c. | 02-runtime §4.2, 03-architecture §4.6 | 1c |
| `staging/transfer.py` | **rewrite** | Duplicate `ArchiveClient` (§3.1); an unused `SUBSTRATE` constant; `PinnedInput` and `PlannedOutput` typed as `object`; all three functions unimplemented. `ScratchDumpPolicy` and the substrate notes are kept. | 02-runtime §4.1, §4.3 | 1c (dump), 5 (stage down and up) |
| `runtime/stage_entry.py` | **keep with changes** | One materialisation pass, dispatch by splat with no signature inspection, the per-operation output sweep through `tb.table`: decided and correct. `OutputMissing(RuntimeError)` and `_supply`'s `TypeError` join the error taxonomy (§5). | 02-runtime §8, ADR-0008 | 1c |
| `orchestrator/execute.py` | **drop from this pass** | Five unimplemented functions whose docstrings are design notes already present in 02-runtime §6.3 and §6.4 and 03-architecture §8. The dispatch registry (T3.3) is new code in slice 5. | 02-runtime §1.3 | not in this pass |
| `helpers/__init__.py`, `observability/__init__.py`, `operations/__init__.py`, `pipelines/__init__.py`, `runtime/__init__.py`, `orchestrator/__init__.py`, `ag/__init__.py` | **keep with changes** | One-paragraph package docstrings naming what belongs there and the membership test; created with the tree in slice 0 as the only content of each package. | ADR-0005, ADR-0006 | 0 |

---

## 5. The error module

**Verdict: absent; write new.** The template has no error module. `adapters/arcpy/__init__.py`
names an `errors.py` it never wrote, and `adapters/__init__.py` lists `errors` under `arcpy/`,
which is the wrong layer for the three errors T2.4 puts in `ports/errors.py`. What exists:

| raise site | today | verdict |
|---|---|---|
| `@operation` classification and declaration checks; `_expect_declared`; `_expect_config`; `pipeline._check_declared`; `Field`, `Schema`, `Spatial`, `Geometry` `__post_init__`; config `__post_init__` | `TypeError`, `ValueError` | **keep builtins.** They fire while a module is being imported or a value is being constructed, which is exactly what those builtins mean, and the tests match on them. |
| `ScratchHandle.__fspath__` on an unmaterialised handle; `_unbound` scope; `_NotInjected.__getattr__` | `RuntimeError` | **change** to `InjectionError(AgError)` in `core/errors.py`. They are raised from `core/` and `ports/`, so the type cannot live in `runtime/`. |
| `stage_entry._supply` unknown injected kind | `TypeError` | **change** to `InjectionError`. |
| `stage_entry.OutputMissing` | `RuntimeError` subclass | **change** base to `StageRunError(AgError)` in `runtime/errors.py`. |
| `ScratchFileManager` leaf collision; `render_trail` over budget | `ValueError` | **change** to `WorkspaceError(StageRunError)`; they happen in a pod, not at import. |
| `policy.external_classification` mismatch | `ValueError` | **keep**; it is a plan-time declaration fault reported beside `Finding`s. |
| `_node_id` in the road example | `TypeError` | **change** to `DataContractError(DomainError)` in the fixture. |

The taxonomy the plan proposes (§6.1) is consistent with this: `AgError` and `ErrorContext` and
`InjectionError` in `core/errors.py`; `PortError` and its members in `ports/errors.py`;
`AdapterDefectError` in `adapters/errors.py` as a **sibling** of `PortError` under `AgError`,
because an adapter defect is not something a caller of a port is expected to handle as a port
condition; `LineageError` with `DesignCeilingError` and `ResourceCeilingError`; `DomainError`;
`StageRunError`.

---

## 6. Examples, declarations, tooling, tests

| item | verdict | reason and changes | rests on | enters |
|---|---|---|---|---|
| `operations/road`, `operations/building`, their `tuning/`, `pipelines/*`, `tuning/scale/` | **keep with changes, as test fixtures, not in `src/ag`** | They are worked examples with known defects: `resolve_ramps` inverted (A17.2), three uncompilable `Attr` subqueries (A17.4, A17.7), the two `ranks` joins (A17.5), `DISPLACEMENT_FEATURE`'s origin (A17.1), `merge_report`'s exemption across two mints (B15), bare `"near_fid"` literals (T2.4). They move to `tests/fixtures/example_pipelines/` in slice 0 and stay excluded from type checking and collection until the modules they import exist (1c). `n100_objects.py` declares `ADDRESSED_BUILDINGS`, which nothing produces; drop it or wire it. The base-plus-one-delta tuning shape is kept exactly. | A17.x, ADR-0013 | 0 (moved), 1c (live) |
| `sources.py`, `products.py`, `classification_rules.py` | **structure: keep as is; values: fixtures** | Leaf modules, one declaration per identity, required classification, rules keyed on values. The bucket names and datasets are invented; the real declarations arrive with the first migrated stage. | ADR-0012, 02-runtime §5.4 | 6 |
| `tools/run_example.py` | **keep with changes** | The derivation printout is the documents' drift detector and the spy run is the surface-completeness check. Drop the `sys.path` insert; `_DryRunFileManager` stays in `tools/` for the reason its docstring gives (the `staging` contract). `_split_on_sweeps` infers operation boundaries from sweep calls; once the runtime emits a per-operation record, read that instead. | template README | 1c |
| `tools/dump_tuning.py` | **keep as is** | Ten lines that make the no-resolution-mechanism rule verifiable. Module path changes with the tree. | ADR-0013 | 6 |
| `tests/unit/test_operation_classification.py` | **keep as is** | Tests the precondition (annotations really are strings) before the claim; the model for every later test. | ADR-0014 | 1a |
| `tests/unit/test_predicates.py` | **keep as is**, extended | Same quality. Gains cases for the structured `Attr` leaves. | ADR-0001, A2.1 | 1a |
| `tests/unit/test_road_operations.py` | **keep with changes** | Declaration tests stay. `local_scope` and `local` move to `tests/support/`. The ArcPy test imports `ag.adapters.arcpy.session`, which does not exist, so the README's "pyright, 0 errors" is false for that file (REVIEW F21); it becomes a conformance and smoke concern. | ADR-0011 | 1c |
| `.importlinter` | **keep with changes** | Seven contracts pass and the `protected`-over-`forbidden` argument is right. Rebuilt against the approved tree (`project_tree.md` §6). | 03-architecture §4.2, B10, T7.4 | 0 |
| `pyrightconfig.json` | **rewrite** | `standard` mode and a template-local include list. Becomes `[tool.pyright]` in `pyproject.toml`: strict, Python 3.13, over `src`, `tests`, `tools`. | plan item 3 | 0 |
| `conftest.py` | **drop** | A `sys.path` insert; the `src` layout and an editable install replace it. | 03-architecture §7.1 | never |
| `README.md` | **drop** | Its content is this review, the plan, and `docs/contributing/testing.md`. | | never |

---

## 7. What the template taught us that the decisions do not yet capture

Each is a candidate B-item or a sentence in an existing item; none is decided here.

1. **Internal scratch handles have no identity.** They compare equal across operations, and
   A15.3 keys a cache on handle equality. The handle needs a namespace rule for internal scratch,
   stated next to A15.3's "a materialised copy equals its declaration".
2. **The leaf-collision rule is per operation workspace, not per pod.** 02-runtime §4.2 says "a
   repeated leaf name within one scope is an error"; the code enforces it per pod.
3. **Someone has to create a workspace, and it needs an engine.** `staging/` may not import one.
   No A-item, port method or ADR covered it. *Decided 2026-09-21: A5.7, a `TableOps` method.*
4. **A handle can reach a port inside a value.** `Spatial.relate_to` is outside the `In`/`Out`
   grammar. Harmless, and it should be written down in `row_shape.py` so the check's blind spot
   is deliberate.
5. **`calculate_field` has no expression language.** The port docstring promises one; the
   template's own call sites contradict it; 101 legacy call sites will need it.
6. **`Stage` has no partition sizing input**, and nothing else declares one. Whether fan-out
   needs anything beyond `context_radius_m` and the input roles is an inference until fan-out's
   signature is written against the class.
7. **Docstrings need a length rule.** DECISIONS routes much rationale to docstrings, the template
   shows what that grows into, and the project convention forbids the code examples the template
   relies on. Proposed rule: Why is one paragraph plus a pointer to the ADR or A-item.
8. **Keep `In`/`Out` as `TypeAlias`.** With the floor at 3.13 someone will modernise them to PEP
   695 `type` statements, and `_direction_of` then classifies nothing. One sentence in the module
   and a test.
9. **Driven-port Protocols live only in `ports/`.** The duplicate `ArchiveClient` is what happens
   otherwise. A static test can enforce it for the port names; adapter-internal Protocols such as
   the part locator are exempt.
10. **The capability record has to live in `ports/`.** Adapters publish it and may not import
    `lineage/`; the facade and `validate()` read it.
11. **Errors raised by sentinels come from `core/` and `ports/`.** Their type must sit in `core/`,
    so "one base per layer" needs `core/errors.py` to hold more than the root class.
12. **Loose `object` typing was justified by an import cycle that does not exist.** Under strict
    typing the justification should be tested before it is believed; three modules carry it.
13. **The spy and the fake answer `exists` differently**, on purpose. The output sweep is only a
    real check under an adapter that answers from writes.
14. **A green example run proved less than it appeared to.** Items 1 and 2 and the `sidecar`
    defect were all reachable, and the two worked pipelines happened not to reach them. The
    template's tests assert preconditions before claims; its runnable example did not, and the
    same discipline (break it on purpose once) belongs on every walking-skeleton acceptance line.
