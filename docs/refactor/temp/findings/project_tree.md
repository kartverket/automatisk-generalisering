# Proposed tree for `src/ag`

**Status:** ACCEPTED by the architect, 2026-09-21, with the recommended options (§2 option B, §3.1 option A); §3.2, §4, §6 and §7 amended in review the same day. Originally a proposal for approval, 2026-09-21. Slice 0 of `implementation_plan.md` creates the
approved tree as empty packages with docstrings; no template code enters with it. The two
questions marked **DECIDE** (the placement of cartographic domain code, §2, and the split of a
port's Protocol, §3.1) were decided with the recommended options; both options stay on the page
as the record of what was weighed.

**Where the planned tree is defined.** `docs/refactor/03-architecture.md` §7 (the tree), §4.1
(the import rules per package), §4.2 (the contracts that enforce them), §5 (`helpers/` and its
subject axis), §7.2 (ports are flat, one file per port), §7.3 (a directory per (object, scale),
one module per stage), §7.4 (object-major), §7.6 (contract tests). `template_code/.importlinter`
is the first instalment of §4.2. `04-migration.md` §1 maps every legacy module onto that tree.
ADR-0005 names `helpers/`; ADR-0012 fixes `sources.py` and `products.py` as leaves; ADR-0013
fixes the tuning layout. This proposal starts from that tree and departs from it in the eight
places §8 lists.

**Designed for the scope it grows into.** Five objects by five scales; roughly 44,000 lines of
legacy `generalization/` and 17,000 of `custom_tools/` to absorb; three port Protocols of 25 to
35 methods each with two adapters apiece; two developers adding port methods and operations
concurrently, one person reviewing.

---

## 1. The tree

Shown for the recommended options of §2 and §3.

```
pyproject.toml            [project] src layout, requires-python 3.13; [tool.pyright] strict;
                          [tool.black]; [tool.ruff]; [tool.pytest.ini_options] markers
.importlinter             the contracts of §6
stubs/arcpy_constrained/  the local type stub for ArcPy: only the non-tool names the adapter
                          and the test builders may use (§6.1). Applied to two roots only,
                          by pyright execution environments. Not shipped.

src/ag/
├── core/                     pure: stdlib only. No filesystem, no engine, no environment.
│   ├── types.py                  Scale, ObjectName, DataType, InputRole, Classification, ...
│   ├── injection.py              the Injected marker
│   ├── handles.py                ScratchHandle, handle, Handles, Direction, In, Out, Mutates,
│   │                             ParentsOut, ScratchScope, INJECTED        (departure 1)
│   ├── operations.py             @operation, OperationCall
│   ├── data_objects.py           ExternalSource, ProductIdentity, Derived, OriginRoot
│   ├── pipeline.py               Stage, StageInput/Output, Publish, Pipeline, StageRegistry
│   ├── locations.py              every remote path
│   ├── graph.py  selection.py  policy.py  planning.py
│   ├── findings.py               Finding, Severity                         (departure 2)
│   ├── validation.py             validate() -> list[Finding]
│   ├── errors.py                 AgError, ErrorContext, InjectionError
│   └── warnings.py               AgWarning and its three categories
│
├── ports/                    Protocols and the values that cross them. Flat.
│   ├── geometry_ops.py           GeometryOps + its enums
│   ├── table_ops.py              TableOps + Field, Schema, Row, FieldType; create_workspace (A5.7)
│   ├── workspace_format.py       WorkspaceFormat, named by create_workspace (A5.7)
│   ├── cartographic_ops.py       CartographicOps
│   ├── graph_ops.py              GraphOps
│   ├── archive.py                ArchiveClient
│   ├── cluster.py                ClusterClient (not in this pass)
│   ├── geometry.py               the Geometry value type
│   ├── predicates.py             Predicate, Attr, Spatial, And, Or, Not     (departure 3)
│   ├── row_shape.py              Rows, Cardinality, Ids, @row_shape
│   ├── columns.py                port-owned column constants: PARENT_ID, CHILD_ID,
│   │                             NEAR_INPUT_ID, VERTEX_SOURCE, ...          (departure 3)
│   ├── capabilities.py           AdapterCapabilities                       (departure 4)
│   ├── errors.py                 PortError and its members
│   └── toolbox.py                Toolbox, NOT_INJECTED
│
├── adapters/                 the only place a vendor library is imported
│   ├── errors.py                 AdapterDefectError and its members
│   ├── _shared/                  ENGINE-FREE code more than one adapter needs (§3.2 rule 5)
│   │   └── parents_resolver.py       the keyed dissolve resolver            (departure 5)
│   ├── arcpy/                    root holds session, base and the port packages, nothing else
│   │   ├── session.py                the ONLY module that runs a tool, touches arcpy.env or names
│   │   │                             a vendor exception: run_tool, environment, licence (§6.1)
│   │   ├── _base.py                  ArcpyPortBase: holds the session (§3.2 rule 1)
│   │   ├── support/                  ENGINE-BOUND code more than one group needs (§3.2 rule 4)
│   │   │   ├── geometry_values.py        Geometry <-> arcpy converters
│   │   │   ├── predicate_compiler.py     push_negation, apply
│   │   │   ├── part_locators.py          segment and point locators for the resolver
│   │   │   ├── pair_tables.py            read native references, write PARENT_ID/CHILD_ID
│   │   │   ├── geometry_guards.py        empty-geometry check, degenerate classification
│   │   │   └── field_names.py            identifier quoting per workspace type
│   │   ├── geometry_ops/             one module per method group, composed in __init__
│   │   │   ├── __init__.py               class ArcpyGeometryOps(Selection, Shape, Overlay, ...)
│   │   │   ├── selection.py  shape.py  overlay.py  collapse.py  quality.py
│   │   │   └── points.py  proximity.py  raster.py
│   │   ├── table_ops/                catalog.py  schema.py  attributes.py  rows.py
│   │   └── cartographic_ops/         simplification.py  aggregation.py  selection.py
│   │                                 displacement.py
│   ├── fakes/                    ships in src; importable by runtime/local.py only (§4)
│   │   ├── recording.py              the spy
│   │   └── memory/                   the in-memory adapter, same package shape as arcpy/
│   │       ├── store.py                  MemoryStore: tables, native index, field types,
│   │       │                             failure injection, capabilities
│   │       ├── _base.py                  MemoryPortBase: holds the store (§3.2 rule 1)
│   │       ├── support/                  pair rules, duplicate-field naming
│   │       ├── geometry_ops/  table_ops/  cartographic_ops/
│   │       └── graph_ops.py
│   ├── networkx/graph_ops.py         (slice 4)
│   ├── storage/
│   │   ├── filesystem.py             (slice 1c)
│   │   ├── s3.py                     (slice 5)
│   │   └── gcs.py                    (slice 5)
│   └── cluster/                  (not in this pass)
│
├── lineage/                  identity above the ports. Imported by runtime/ only.
│   ├── minter.py  id_map.py  facade.py  session.py  edges.py  work_key.py
│   ├── errors.py                 LineageError and its members
│   └── query.py                  (not in this pass)
│
├── staging/                  pod-local paths and transfer. Imported by runtime/ only.
│   ├── workspace.py              join rule, name legality, name budget (WorkspaceFormat is in ports/)
│   ├── scratch.py  transfer.py
│
├── observability/            horizontal leaf: stdlib + core.types
│   ├── records.py  context.py  timing.py
│
├── runtime/                  composition root for a pod
│   ├── env.py                    Settings, the only reader of the environment
│   ├── compose.py                PortSet in, Toolbox out: facade wrapping; arcpy_ports()  (§4)
│   ├── stage_ref.py              the one import by string; ag.generalization.* only     (§4)
│   ├── stage_entry.py            run_operations, sweep_outputs
│   ├── local.py                  the local single-pod runner; the only importer of fakes
│   ├── fan_out.py  partition.py  fan_in.py  ingest.py
│   └── errors.py                 StageRunError and its members
│
├── orchestrator/             composition root for a run
│   ├── dispatch.py               minter counter, dispatch registry
│   └── (execute, jobs, metadata, log_merge, cli: not in this pass)
│
└── generalization/           ALL cartographic domain code (§2, option B)
    ├── errors.py                 DomainError and its members
    ├── sources.py                every ExternalSource. Leaf.
    ├── products.py               every ProductIdentity. Leaf.
    ├── classification_rules.py   the one file a security reviewer reads
    ├── registry.py               every Pipeline, listed once; what the entry points import
    ├── tuning/scale/             n10.py ... n250.py: cartographic constants per scale
    ├── helpers/                  lines.py polygons.py points.py topology.py attributes.py
    │                             extents.py   (subject axis; fills by the promotion rule)
    ├── operations/               scale-free
    │   ├── shared/                   operations used by more than one object
    │   └── <object>/                 building/ road/ river/ railway/ land_use/
    │       ├── <topic>.py                one module per cohesive group of operations, with
    │       │                             their config classes and private helpers
    │       └── tuning/                   __init__.py (base) + one module per scale (delta)
    └── pipelines/
        └── <object>/<scale>/         building/n100/, road/n100/, road/n250/, ...
            ├── objects.py                the Derived declarations of this pipeline
            ├── <stage>.py                one module per stage: its Handles class and its Stage
            └── __init__.py               the Pipeline: stage membership and publications

tests/
├── unit/             mirrors src/ag by directory; no engine
├── static/           import contracts as tests, row-shape check, port matrix, arcpy-blocked
│                     import guard, terminology-matches-code, exception-name scan
├── conformance/      one module per port method group, parametrized over adapters   (§4)
├── goldens/          recorded artifacts and their replay tests
├── invariance/       K = 4 against K = 16
├── smoke/            one real stage end to end
├── support/          engine-neutral builders, local_scope, the adapter fixture, gdb builders
└── fixtures/
    └── example_pipelines/    the template's worked examples, fixed per A17

tools/                run_example.py, dump_tuning.py, scan_sources.py; never shipped
docs/                 as in implementation_plan.md §4
```

---

## 2. Framework code and cartographic domain code — DECIDE

The planned tree puts `operations/`, `pipelines/`, `helpers/`, `tuning/`, `sources.py`,
`products.py` and `classification_rules.py` beside `core/`, `ports/`, `adapters/`, `staging/`,
`runtime/` and `orchestrator/`: fourteen or fifteen siblings under `ag/`.

| | **A. Flat, as planned** | **B. Domain grouped under one package** (recommended) |
|---|---|---|
| shape | `ag/operations/road/`, `ag/pipelines/road/n100/`, `ag/helpers/`, `ag/sources.py` | `ag/generalization/operations/road/`, `ag/generalization/pipelines/road/n100/`, `ag/generalization/helpers/`, `ag/generalization/sources.py` |
| framework paths | unchanged | unchanged: every `destination:` in DECISIONS that names `ports/...`, `adapters/arcpy/`, `core/...`, `runtime/...` still resolves |
| what a developer sees | fifteen directories, half of which they must not touch without review | one directory that is theirs, and the rest |
| contracts | each domain package named in each contract; a new domain package must be added to several | the framework side of every contract names `ag.generalization` once; layering inside it is one small contract |
| review routing | CODEOWNERS lists seven paths | CODEOWNERS is two lines: framework to the architect, `generalization/` to the team |
| growth | five objects by five scales lands across four top-level packages interleaved with framework | the same code lands under one root; the framework's top level stays about nine entries |
| cost | none | departs from 03-architecture §7 and from every `ag.operations...` path in the ADRs and the template; must be done now, because it is free only while no code exists |
| migration naming | `generalization/n100/building/x.py` to `ag/operations/building/` | `generalization/n100/building/x.py` to `ag/generalization/...`: continuity for the team, and a grep for `generalization/` is ambiguous until the legacy package is gone |

**Recommendation: B.** The decided structure inside the domain is untouched (object-major,
scale-free operations, a directory per (object, scale), one module per stage, base-plus-delta
tuning, leaf `sources.py` and `products.py`). What B adds is the one boundary the team will use
every day: framework code changes rarely and needs architecture review; domain code changes
constantly and should not. A directory is the cheapest way to make that visible to people,
CODEOWNERS and import-linter at once. If the name is the objection, `ag/domain/` works too, but
*domain* already means something else in the terminology (*domain key*; *object* is "a pipeline
domain"), and `generalization` is the word the team already uses for this code.

A third option, a second root package (`src/ag_generalization/` beside `src/ag/`), gives the
hardest boundary, since the framework could not import the domain even by accident. It is not
recommended now: it needs a second distribution or a multi-root layout for no benefit the single
contract in §6 does not already give. B does not close that door; the move would be one rename.

**One consequence of B to accept with it.** The entry points never import a pipeline module by
name. `runtime/local.py` and later the pod entry points take a `module:STAGE` reference, and the
orchestrator imports `ag.generalization.registry`. That keeps "framework does not depend on
domain" true for everything except the two composition roots, which is where 03-architecture
§4.5 says the two sides meet.

---

## 3. How ports and adapters split as the surface widens

### 3.1 Protocols — DECIDE

| | **A. One module per port** (recommended) | **B. A package per port, Protocol composed from method-group Protocols** |
|---|---|---|
| shape | `ports/geometry_ops.py` holds the whole `GeometryOps` Protocol, sectioned by method group | `ports/geometry_ops/selection.py` holds `SelectionMethods(Protocol)`, ...; `__init__` composes `class GeometryOps(SelectionMethods, OverlayMethods, ..., Protocol)` |
| file size at full surface | about 1,200 to 1,500 lines with What / How / Why docstrings | 150 to 300 lines per file |
| reading the contract | top to bottom in one file; what a second adapter author needs | assembled across eight files |
| concurrent edits | two developers adding methods to one port touch one file, in different sections; conflicts are rare and trivial | never touch the same file |
| risk | a long file | the group Protocols are importable, and someone will type a parameter as `SelectionMethods`; that is the interface segregation ADR-0002 and 03-architecture §4.7 decided against, arriving by the back door |
| `__row_shape__` lookup | `GeometryOps.dissolve.__row_shape__` | same, through inheritance |

**Recommendation: A**, as 03-architecture §7.2 already says ("flat; six files are browsable").
The Protocol file is the specification; its length is the length of the contract. The value
types and the grammar that would otherwise bloat it move out (`predicates.py`, `columns.py`,
`row_shape.py`, `capabilities.py`, `errors.py`), which is where most of the template's 400 lines
in `geometry_ops.py` went. Revisit if a port passes about 2,000 lines.

### 3.2 Adapters

**One package per port per adapter; one module per method group; the adapter class composed
from the groups.** `adapters/arcpy/geometry_ops/__init__.py` declares
`class ArcpyGeometryOps(Selection, Shape, Overlay, Collapse, Quality, Points, Proximity,
Raster)` with an empty body and carries the `if TYPE_CHECKING:` conformance assignment. The fake
mirrors the package shape exactly, so "where is the fake for this method" has the same answer as
"where is the ArcPy code for it".

Why groups and not one module per port: the ArcPy `GeometryOps` will be several thousand lines
(the dissolve path alone brings the resolver call, two guards and the statistics group-by), and
this is the code two developers add to every week. Why groups and not one module per method:
forty-five files per adapter per port is a directory nobody can scan.

#### Decision, 2026-09-21: group classes hold Protocol methods only; helpers are module-level functions

**The concern** (raised in review): composing the adapter from group classes by multiple
inheritance puts every group of one adapter in a single attribute namespace. Two developers
adding `_prepare_fields` in two group modules get no error; the MRO picks one and the other
group silently calls the wrong helper.

**The risk is real for this codebase. Three checks, each run rather than argued:**

1. *Pyright strict does not see it.* Probe under pyright 1.1.399, strict, Python 3.13: two group
   classes each defining `_prepare(self, name: str) -> str` with different bodies, composed into
   one adapter, give **0 errors**. At runtime `dissolve` called the selection group's `_prepare`;
   with the two bases swapped, `select` called the collapse group's. Only when the two signatures
   were made incompatible did pyright report it (`reportIncompatibleMethodOverride`, "base
   classes define method in incompatible way").
2. *The team's existing code collides in exactly this way.* Across 236 classes in
   `custom_tools/`, `generalization/`, `file_manager/`, the template and `temp/`, 14 private
   method names are defined in more than one class, and **every one of the 14 has a single
   signature across its classes with different bodies**: `_validate_config` (6, 3 and 5
   statements in three sibling tools), `_fetch_data` (1 and 12), `_prepare_processing_feature_class`,
   `_ensure_output_fields`, `_serialize_row_result`, `_write_row_values_to_cursor_row`. The three
   sibling tools in `geometry_tools.py` are the closest thing the repository has to the method
   groups of one adapter, and they share eleven helper names. Same name, same signature,
   different behaviour is the team's normal style for sibling classes, and it is the one case
   pyright cannot flag.
3. *The helpers the groups need are mostly not group-local anyway.* Going through A12.11 and
   A14.1, what is shared between methods cuts **across** groups: writing the parents pair table
   (every `MINT` method: `explode_multipart` in shape, `clip`/`intersection`/`difference` in
   overlay, `dissolve`/`buffer_dissolve` in collapse, `split_at_points`/`cluster_points` in
   points); the pre-call empty-geometry guard (every subject); the work-key stamp on a copy
   (`clip`, `difference`); geometry-kind dispatch (`simplify`, `smooth`); identifier quoting
   (predicates, `calculate_field`, `join_field`). None of these could sensibly be a method of one
   group class. What is left inside a group is small and local to one or two methods. The earlier
   sentence in this section, that methods in a group share private helpers, was wrong about where
   the sharing is.

The new code already has the other style. Every helper in the template takes what it needs as an
explicit argument and is a module-level function (`_repair_geometry`, `_build_topology`,
`_vertex_deltas` take `tb` and `scratch`; A1.3, ADR-0008), and `temp/arcpy_part_locator.py` has
nine module-level helpers against three helper methods, with `find_empty_geometries` and
`degenerate_inputs` as plain functions. Module-level private functions collide in 2 of 136 names
across the same scan, harmlessly, because a module is its own namespace.

**Options weighed.**

| option | pyright strict | collisions | cost |
|---|---|---|---|
| mixins with helper methods (the first draft) | clean, and blind to the collision | silent, order-dependent | none until it bites |
| **mixins holding Protocol methods only; helpers module-level, session passed as an argument; one base class per adapter; a static test** (chosen) | clean; `self._session` is typed in every group through the base | impossible for helpers (module namespace); a duplicated Protocol method or a stray attribute fails the static test | the session is an explicit first argument to helpers, which is already the house style |
| composition with delegation | clean; a forgotten delegate is caught by the conformance assignment (probed: `"dissolve" is not present`) | impossible | every method's keyword list and defaults restated a third time (Protocol, delegate, group), which is the restated-signature disease ADR-0011 removed; about 45 delegates per adapter per port, twice |
| group modules of plain functions bound into the class body (`select = select`) | clean (probed, with `self` typed by a small `HasSession` Protocol) | impossible | no restated signatures, but an idiom nobody on the team has seen, and a binding list per adapter |

**Chosen: the second.** It removes the hazard by construction instead of detecting it, costs
nothing the code style does not already pay, and keeps one statement of each signature per
adapter. Name mangling (`__helper`) would also isolate helpers per class and was rejected: it
fixes methods but not instance attributes, and it hides the rule in a spelling.

**The rules.**

1. **One base class per adapter**, in `adapters/<adapter>/_base.py`: it takes the adapter's one
   shared object in `__init__` and keeps it. It is the only class in the adapter that assigns an
   instance attribute. Every group class subclasses it.
   - ArcPy: `adapters/arcpy/_base.py`, `ArcpyPortBase(session)`, sets `self._session`.
   - Fake: `adapters/fakes/memory/_base.py`, `MemoryPortBase(store)`, sets `self._store`. **The
     row store is held by that base and by nothing else.** `MemoryStore` itself lives in
     `adapters/fakes/memory/store.py` and is a separate object: one instance is created by
     whoever assembles the fake `Toolbox` (`runtime/local.py`, or the `adapter` fixture in
     `tests/support/`) and passed to each of the fake's port classes, so that what
     `table.write_rows` wrote is what `geometry.select` reads. All mutable state of the fake is
     inside that one object; the group classes have none, exactly as under ArcPy all engine state
     is behind the session.
2. **A group class defines Protocol methods of its port and nothing else**: no helper methods,
   no `__init__`, no class attributes, no state. A Protocol method is defined in exactly one
   group.
3. **Helpers are module-level functions** in the group module, private by underscore, taking the
   session or store (and anything else) as explicit arguments.
4. **A helper needed by a second group of the same adapter moves up** into that adapter's
   `support/` package. **Group modules never import each other** (§6 row 16). **Imports run one
   way**: a group module may import `support/`, `_base` and `session` (or `store`); a `support/`
   module never imports a group module or a port package (§6 row 17).
5. **Two homes for shared adapter code, told apart by one question: does it import the engine?**
   - *Engine-free* code needed by more than one adapter goes in `adapters/_shared/`. It imports
     only `ag.core`, `ag.ports` and stdlib, and the fake and the tests can import it. Today that
     is `parents_resolver.py`, which decides which output part each input belongs to from keys
     and located pairs and never touches a dataset.
   - *Engine-bound* code needed by more than one group of **one** adapter goes in that adapter's
     `support/`. It may call the engine through the session. Today, for ArcPy:
     `pair_tables.py` (reads `ORIG_FID`, `FID_<input>` and the tools' own tables, writes the
     `PARENT_ID`/`CHILD_ID` table), `part_locators.py`, `geometry_guards.py`, `field_names.py`,
     `geometry_values.py`, `predicate_compiler.py`.
   The names are chosen so the two cannot be mistaken for each other: `_shared/` modules are
   named for a decision they compute (`parents_resolver`), `support/` modules for the engine
   artefact they handle (`pair_tables`, `part_locators`, `field_names`). Neither package has a
   module called `parents.py`.
6. **The composed class has an empty body.** Base order is the Protocol's section order and is
   never load-bearing, because no name is defined twice.
7. **`tests/static/test_adapter_groups.py`**, per adapter and port, by AST and by inspection:
   every name defined in a group class is a method of the port's Protocol; no name is defined in
   two group classes; no `self.<name> =` assignment outside `_base.py`; the composed class body
   is empty; the adapter's root contains only `session.py` or `store.py`, `_base.py`, `support/`
   and the port packages. Broken on purpose once when it is written (a helper method added to
   one group, a method duplicated in two), with the failure messages in the PR.

Pyright strict accepts the structure as probed: group classes in separate modules subclassing a
base in another module, `self._session` accessed from each, the composed class assigned to the
Protocol under `TYPE_CHECKING`, 0 errors.

**The groups are the section headings of the Protocol file**, in the same order, and the
conformance suite uses the same names. Today's headings in the template's `geometry_ops.py` are
the starting set: selection, dataset shape, OGC simple features (overlay), geometry quality,
derived points, proximity; plus collapse (`dissolve`, `buffer_dissolve`) and raster
(`sample_at`). A method's group is decided once, when it is declared on the Protocol.

---

## 4. The fake adapter and the conformance suite

**The fake ships in `src`, at `ag/adapters/fakes/memory/`.** It is not test support, for three
reasons. Editing happens in WSL where no ArcPy exists, so `python -m ag.runtime.local --adapter
fake` is how a developer runs a stage's declarations and port-call sequence while writing it.
The K-invariance harness and a dry run of a whole pipeline are driving adapters in
03-architecture §4.5's sense, not tests. And 03-architecture §7 already places `fakes/` under
`adapters/`.

**What it costs, honestly.** At full surface the fake implements the same 75 to 105 methods the
ArcPy adapter does (the three handle-bearing ports after A5.6's splits, plus `GraphOps`), each
with a body of roughly 8 to 20 lines because it is geometry naive, plus the parents rules for
the ten `MINT` methods and the row store (tables, native index reassignment on write, declared
field types, failure injection, the duplicate-field rule, the capability record). That is
roughly **1,500 to 2,500 lines**, not a few hundred. In the image it is inert pure Python with
no dependencies, so shipping it costs nothing at runtime; what it costs is maintenance, one fake
method per port method for the life of the project, and that is the reason plan §5.7 forbids it
from computing geometry.

**The guard is an import contract, not a settings check.** `ag.adapters.fakes` is `protected`
with `ag.runtime.local` as its only allowed importer (§6 row 18). `runtime/compose.py`, the pod
entry points and the orchestrator therefore cannot construct the fake at all, and
`runtime/env.py`'s `Settings` has no adapter value that names it: the local runner's
`--adapter fake` is a flag of that one module. Tests and `tools/` sit outside the root package
and import it freely. No check is kept in `env.py`.

**Imports by string: one sanctioned site, and it is constrained.** A contract sees only static
imports, so three things close the rest:

- There is exactly one dynamic import in `src/ag`: `runtime/stage_ref.py`, which turns a
  `module:STAGE` reference from the command line into a `Stage`. The pod entry points and the
  local runner call it; the orchestrator does not need it, because it imports
  `ag.generalization.registry` statically.
- **The resolver rejects any reference whose module is not under `ag.generalization.`**,
  checked on the string *before* anything is imported (an import executes the module), and
  again on the imported module's `__name__`; the resolved attribute must be a `Stage`. Without
  this the exemption would be the hole: the one module allowed to import by string is the one
  that takes an arbitrary string from a user, so `ag.adapters.fakes...` would pass both the
  contract and the scan. It also means a command line cannot make a pod import and execute an
  arbitrary module.
- The static scan fails on any use of `importlib` (the module, in any import form),
  `__import__` and `runpy` anywhere in `src/ag` except `runtime/stage_ref.py`. It bans
  `importlib` wholesale on purpose; a legitimate later need (`importlib.metadata` for a version
  string) is added to the allowlist deliberately, in a reviewed diff.

One consequence, accepted: the example pipelines under `tests/fixtures/` are not under
`ag.generalization.`, so they cannot be run by reference. They do not need to be. The local
runner's core is a function that takes a `Stage` object; the command line is a thin wrapper that
resolves a reference and calls it; tests import the fixture and call the function directly.

**How `runtime/local.py` gives the fake to `runtime/compose.py`.** `compose.py` cannot import
the fake, so it never selects an adapter by name. Its interface is instances in, `Toolbox` out:

- `compose.build_toolbox(*, ports: PortSet, settings: Settings) -> Toolbox`, where `PortSet` is
  a small frozen dataclass in `compose.py` holding `geometry: GeometryOps`, `table: TableOps`,
  `cartographic: CartographicOps`, `graph: GraphOps` and `capabilities: AdapterCapabilities`,
  every field typed by its Protocol. This function is the whole composition: it wraps the three
  handle-bearing ports in the lineage facade, reads the capability record, and assembles the
  `Toolbox`. It exists once.
- `compose.arcpy_ports(settings) -> PortSet` builds the ArcPy session and the ArcPy port
  classes (importing the adapter lazily, so `compose` stays importable without the engine).
- A pod entry point calls `build_toolbox(ports=arcpy_ports(settings), ...)`. There is no
  selection in a pod: one engine in this pass.
- `runtime/local.py` builds a `PortSet` either from `compose.arcpy_ports` or, for
  `--adapter fake`, from a `MemoryStore` and the fake's four port classes, and passes it to the
  same `build_toolbox`. So the only thing `local.py` adds is the choice, and nothing about the
  composition is duplicated. The `adapter` fixture in `tests/support/` does the same for tests.

This is the shape `stage_entry.run_operations` already argues for (the `Toolbox` is a parameter
so a harness can drive it with fakes); the rule extends it one level up.

**The spy stays beside it** (`fakes/recording.py`); it answers a different question (template
review §4).

**The conformance suite lives in `tests/conformance/`**, one module per port method group
(`test_geometry_ops_selection.py`, ...), parametrized over an `adapter` fixture defined in
`tests/support/adapters.py` that yields the fake always and the ArcPy adapter under the `arcpy`
marker. It drives the Protocol, not the facade (B10's fifth site). Input fixtures are built by
engine-neutral builders in `tests/support/` so the same case runs on both adapters.

The planned tree calls this directory `tests/contract/`. This proposal uses `conformance`
because T4.11 names the thing "the adapter conformance suite", and because "contract" is already
the word for import-linter contracts and for the static tests in `tests/static/`.

---

## 5. Where errors live

One module per layer, one base per module. Full taxonomy in `implementation_plan.md` §6.1.

| layer | module | base |
|---|---|---|
| core | `ag/core/errors.py` | `AgError` (root), plus `ErrorContext` and `InjectionError`, because the injection sentinels that raise it live in `core/` and `ports/` |
| port | `ag/ports/errors.py` | `PortError(AgError)`: what a caller can see from a port call |
| adapter | `ag/adapters/errors.py` | `AdapterDefectError(AgError)`: the adapter is wrong; a sibling of `PortError`, not a kind of it |
| lineage | `ag/lineage/errors.py` | `LineageError(AgError)` |
| domain | `ag/generalization/errors.py` | `DomainError(AgError)`; importable by `helpers/` and `operations/` alike, which a home inside `operations/` would not be (helpers may not import operations) |
| runtime | `ag/runtime/errors.py` | `StageRunError(AgError)` |
| warnings | `ag/core/warnings.py` | `AgWarning(UserWarning)` |

Import direction makes this work without exceptions: every error module imports only
`ag.core.errors`.

---

## 6. Directory layout against the import-linter contracts

One directory, one row. "Expressible" means import-linter can state it without a custom check.

| # | contract (type) | directory it protects | rule | expressible |
|---|---|---|---|---|
| 1 | layers, `exhaustive = true` | all of `ag/` | `orchestrator` > `runtime` > `generalization` > `lineage \| staging` > `adapters` > `ports` > `core`; `observability` exempt as a horizontal leaf. Exhaustive makes an unlisted package a failure, which replaces the hand-written package-coverage check of T7.4 if the installed import-linter supports it; otherwise that check stays. | yes |
| 2 | layers | inside `ag/generalization/` | `registry` > `pipelines` > `operations` > `helpers` > `tuning \| errors \| sources \| products \| classification_rules` (the bottom five independent of each other) | yes; see the note below the table |
| 3 | forbidden | `ag/core/` | imports nothing else in `ag` | yes |
| 4 | forbidden | `ag/ports/` | may import `ag.core.handles`, `ag.core.types`, `ag.core.injection`, `ag.core.errors` and nothing else in `ag` | **yes, because of departure 1**; with handles inside `core/operations.py` it was a convention |
| 5 | layers | inside `ag/ports/` | `cartographic_ops` above `geometry_ops`, `table_ops`, `graph_ops` (03-architecture §4.3, ports stay acyclic) | yes |
| 6 | protected | `ag/adapters/` | importers: `ag.runtime`, `ag.orchestrator` | yes |
| 7 | independence | `ag/adapters/*` | `arcpy`, `fakes`, `networkx`, `storage`, `cluster` do not import each other; `_shared` and `errors` are importable by all | yes |
| 8 | forbidden, external | whole tree | `arcpy` imported only under `ag.adapters.arcpy` (widened 2026-09-21, §6.1); `networkx` only by `ag.adapters.networkx.graph_ops`; `shapely`, `boto3`, `minio`, `google` only under `ag.adapters` | yes. The narrower rule, that only `session.py` runs a tool, touches `arcpy.env` or names a vendor exception, is not an import rule; §6.1 says what enforces it |
| 9 | protected | `ag/staging/` | importers: `ag.runtime` | yes |
| 10 | protected | `ag/lineage/` | importers: `ag.runtime`, plus whatever T4.3's mint surface requires. If `mint` is reached through the `Toolbox`, the domain imports nothing from `lineage/` and the list stays at one entry. | yes |
| 11 | forbidden | `ag/generalization/sources.py`, `products.py` | import only `ag.core` | yes |
| 12 | forbidden | `ag/generalization/operations/`, `helpers/` | may not import `ag.core.data_objects`, `ag.core.pipeline`, `sources`, `products` (ADR-0003) | yes |
| 13 | forbidden | `ag/generalization/` | may not import `ag.adapters`, `ag.staging`, `ag.runtime`, `ag.orchestrator`, `ag.lineage` | yes (redundant with 6, 9, 10; kept because its failure message is the one a domain developer should read) |
| 14 | forbidden | `ag/observability/` | imports only stdlib and `ag.core.types`; and `ag.core`, `ag.generalization.pipelines` may not import the context accessor | yes |
| 15 | forbidden | `ag/orchestrator/` | may not import `ag.generalization.operations`, `ag.adapters.arcpy`, `ag.staging`; among ports only `cluster` and `archive` | yes |
| 16 | independence, one per adapter and port | the group modules of `ag/adapters/<adapter>/<port>/` | group modules of one port package do not import each other (§3.2 rule 4) | yes |
| 17 | layers, `containers = ag.adapters.arcpy, ag.adapters.fakes.memory` | inside each adapter | `geometry_ops \| table_ops \| cartographic_ops` > `support` > `_base` > `(session)` `(store)`. So a group module may import `support`, `_base` and the session or store; a `support` module never imports a group module or a port package; the port packages of one adapter do not import each other (an adapter that consumes another port does so through the Protocol it is handed, 03-architecture §4.3). The last two layers are optional because each adapter has one of them. | yes |
| 18 | protected | `ag/adapters/fakes/` | importers: `ag.runtime.local` only. Narrower than row 6, and both apply: an import from `ag.runtime.compose` passes row 6 and fails here. | yes |

Note on row 2. It is fully expressible; the one thing that looks like a problem is not.
`operations/<object>/tuning/` sits inside `operations/` and imports its parent's config classes
(same layer) and `ag.generalization.tuning.scale` (a lower layer); `pipelines/` imports
`operations.<object>.tuning.<scale>` (a lower layer). A package-level layers contract accepts
all three. `classification_rules` imports `ag.core.policy`, which is outside this contract and
allowed by row 1.

### 6.1 Decision, 2026-09-21: how adapter modules reach ArcPy

Row 8 first said `arcpy` is imported only by `session.py`, while §3.2 rule 5 lets `support/`
modules use the engine. Both cannot hold, so what those modules need was checked.

**What they need.** The staged locator and guards (`temp/arcpy_part_locator.py`, which becomes
`support/part_locators.py` and `support/geometry_guards.py`) use thirteen ArcPy names. Five are
tool calls (`analysis.SpatialJoin`, `management.AddField`, `FeatureToPoint`, `Delete`,
`CreateFeatureclass`). Eight are not tools: `da.SearchCursor`, `da.InsertCursor`, `Describe`,
`SpatialReference`, `Polyline`, `Polygon`, `Geometry` and `Exists`. The converters in
`support/geometry_values.py` must build `Point`, `Array`, `Polyline`, `Polygon`,
`PointGeometry` and `SpatialReference` objects; `rows.py` and `support/pair_tables.py` read and
write with `arcpy.da` cursors; `support/field_names.py` calls `AddFieldDelimiters`. The legacy
code the adapter replaces uses the same set: 308 `SearchCursor`, 117 `Describe`, 114
`UpdateCursor`, 84 `Point`, 80 `ListFields`, 78 `Polyline`, 71 `PointGeometry`, 61
`InsertCursor`, 52 `Array`.

**Options.**

| option | result |
|---|---|
| `session.py` re-exports the `arcpy` module | the contract is satisfied and enforces nothing |
| `session.py` wraps every object and cursor constructor | about fifteen wrappers today and growing with every method; `session.py` becomes a second adapter, and every wrapper restates a vendor signature |
| **row 8 widens to `ag.adapters.arcpy`; the one-module rule is kept for tools, the environment and exceptions, and is enforced by something that can see it** (chosen) | the import contract says what is true; the narrow rule gets a real check |

**Chosen: the third, and the enforcement is the type stub.** A second thing came out of the
check. CI has no ArcPy on purpose, and under pyright strict a nine-line module with
`import arcpy` and one cursor gives seven errors there (unresolved import, then unknown types
all the way down). A local stub package fixes that, and the same probe showed what else it
does: with a stub that declares only `arcpy.da.SearchCursor`, the module is clean, and a call
to `arcpy.management.Delete` in it is an error (`"management" is not a known attribute of
module "arcpy"`). So:

1. `stubs/arcpy_constrained/arcpy/` is a hand-written stub declaring **only the non-tool names
   the adapter may use**: the `da` cursors and array functions, the geometry and spatial-reference
   constructors, `Describe`, `ListFields`, `Exists`, `AddFieldDelimiters`. It declares **no
   toolbox module** (`management`, `analysis`, `cartography`, ...), **no `env`**, **no
   `ExecuteError`** and no licence functions. It is the allowlist, and adding a name to it is a
   reviewed diff.
2. Any module under `ag/adapters/arcpy/` may `import arcpy`, and pyright then rejects a tool
   call, an `arcpy.env` access or a vendor exception name anywhere in it, because for the type
   checker those names do not exist. The same holds for `tests/support/arcpy/`, the second
   root the stub applies to (below).
3. `session.py` is the one module that reaches them, dynamically: `run_tool("analysis.
   PairwiseBuffer", ...)` resolves the tool by name, and the environment, the licence, the
   message drain and the exception wrapping sit behind the same small typed surface. It is the
   only module allowed `getattr` on the `arcpy` module.
4. A static scan over `ag/adapters/arcpy/` and `tests/support/arcpy/` is the backstop for what
   a stub cannot see: `getattr(arcpy, ...)`, `vars(arcpy)`, `from arcpy import *` and the
   strings `ExecuteError` and `except arcpy` outside `session.py`.

The adapter modules import `arcpy` at module level; nothing outside `ag.adapters.arcpy` is
affected, because `runtime/compose.arcpy_ports` imports the adapter lazily and row 6 keeps
everyone else out. The first converter and the first stub entries are written in slice 1b.

**Corrected 2026-10-02, before the first push of slice 0: where the stub lives, and a second
root.** The stub was placed at `typings/arcpy/`. Probed with pyright 1.1.399: a directory of
that name is pyright's default `stubPath` and applies to every file in the repository, so a
legacy module opened in an editor under the ArcGIS Pro interpreter reported `"management" is
not a known attribute of module "arcpy"` and lost ArcPy completion. The stub moved to
`stubs/arcpy_constrained/arcpy/`, reached only through two pyright execution environments in
`pyproject.toml` (`root = "src/ag/adapters/arcpy"` and `root = "tests/support/arcpy"`, each
with `extraPaths = ["stubs/arcpy_constrained"]`). An execution environment's `extraPaths`
outranks the interpreter's site-packages, so the constraint holds whichever interpreter an
editor has selected, and every other directory resolves `arcpy` from the interpreter or not
at all. The second root settles slice 1b's `.gdb` fixture builders: they live in
`tests/support/arcpy/`, are written against the same stub, run tools through
`session.run_tool`, and are imported lazily inside `arcpy`-marked fixtures, never at the top
of a test module, because collection imports test modules and CI has no ArcPy. Strictness is
scoped the same way: `typeCheckingMode = "standard"` with `strict = ["src", "tests",
"tools"]`, so an open legacy file gets standard-mode diagnostics, not strict ones.

**What the tree cannot express as an import contract**, each with the check that covers it:

| rule | why not | covered by |
|---|---|---|
| "`pipelines/` imports `operations/` for declarations only" | import-linter sees modules, not what is done with the import | nothing mechanical; an operation body called at import would fail the arcpy-blocked guard |
| domain code never obtains an unwrapped port | reach-through such as `tb.geometry._port` needs no import | ruff `SLF001` scoped to `ag/generalization/` (B10) |
| no environment reads outside `runtime/env.py` | `os` is stdlib | a static test scanning for `os.environ` and `os.getenv` |
| no import by string outside `runtime/stage_ref.py`, and that one only into `ag.generalization.` | a dynamic import is invisible to import-linter | the same static test, failing on `importlib`, `__import__`, `runpy`; plus a unit test that the resolver rejects `ag.adapters.fakes.*`, `ag.runtime.*` and a non-`Stage` attribute before importing anything (§4) |
| a group class holds Protocol methods only; no name defined in two groups; no state outside `_base.py` | class contents, not imports | `tests/static/test_adapter_groups.py` (§3.2 rule 7) |
| only `session.py` runs a tool, touches `arcpy.env` or names a vendor exception | not an import: every adapter module may import `arcpy` (row 8) | the stub in `stubs/arcpy_constrained/` omits those names, so pyright strict rejects them in the adapter and in `tests/support/arcpy/`; a static scan covers `getattr` on the module and the exception strings (§6.1) |
| driven-port Protocols declared only in `ports/` | a class definition, not an import | a static test over the port names |
| every handle parameter of a port carries a marker; every `Out` has a row shape | annotations | the T4.1 check |
| an adapter module ends with its `TYPE_CHECKING` conformance assignment, and has a conformance test module | file content | the port matrix test |
| `tests/` and `tools/` are outside the root package | by design; a test may import an adapter | nothing; correct as is |

---

## 7. Where new code goes

For the two developers, without asking.

**A new port method.**
1. Find its row in A12.11 or A12.11a. If it has none, stop and ask; that is an architecture
   question.
2. Declare it in `ag/ports/<port>.py`, under the section heading of its group, with `In`,
   `Out`, `Mutates`, `ParentsOut` on every handle parameter and its `@row_shape`.
3. ArcPy: `ag/adapters/arcpy/<port>/<group>.py`. You may `import arcpy` there, for cursors,
   geometry objects, `Describe` and the other names declared in `stubs/arcpy_constrained/`. **Every tool
   goes through `session.run_tool("<toolbox>.<Tool>", ...)`**; never call
   `arcpy.<toolbox>.<Tool>` directly, never touch `arcpy.env`, never name `arcpy.ExecuteError`.
   Pyright will stop you, because the stub does not declare them. If you need an ArcPy name the
   stub lacks and it is not a tool, add it to `stubs/arcpy_constrained/` in the same pull request and say
   why (§6.1).
4. Fake: `ag/adapters/fakes/memory/<port>/<group>.py`, reading and writing only through
   `self._store`.
5. In both adapters, follow §3.2's rules, which `tests/static/test_adapter_groups.py` enforces:
   - the method goes on the group's class, and **the class gets nothing else**: no helper
     method, no `__init__`, no attribute, no `self.x = ...`;
   - anything the method needs beyond its own body is a **module-level function** in the same
     group module, underscore-prefixed, taking the session (or store) as an argument;
   - never import another group module. If a second group needs your helper, move it:
     **does it import the engine?** *No*, and another adapter or the tests need it too:
     `ag/adapters/_shared/`. *Yes* (or it is specific to one adapter): that adapter's
     `support/`. Name a `support/` module after the engine artefact it handles
     (`pair_tables`, `field_names`), never after the concept a `_shared/` module already owns;
   - a `support/` module never imports a group module;
   - a new group (a new module in the port package) is added to the composed class's bases in
     the Protocol's section order, and to import-linter row 16.
6. Conformance: `tests/conformance/test_<port>_<group>.py`, the cases its row-shape cell
   requires.
7. If the row is `MINT`: add the method name to each adapter's capability record.
8. A new value type or enum goes in the port's module; a new column constant in
   `ag/ports/columns.py`; a new error type only if a caller would handle it differently
   (`implementation_plan.md` §6.1).
The guide `docs/contributing/adding-a-port-method.md` is the long form of this list.

**A new operation.**
1. `ag/generalization/operations/<object>/<topic>.py`, decorated with `@operation`; its frozen
   config class directly above it; its private helpers (undecorated, leading underscore) below.
   One legacy module usually becomes one operation plus helpers (A1.2).
2. Config values: every field once in `operations/<object>/tuning/__init__.py`; the per-scale
   difference as a `replace` in `operations/<object>/tuning/<scale>.py`. A value that is a fact
   about the map at a scale, not about this object, goes in `tuning/scale/<scale>.py` and is
   referenced from there.
3. Used by a second object: move it to `operations/shared/`. A *helper* used by a second object
   moves to `helpers/<subject>.py` (the promotion rule, ADR-0005).
4. Unit test under `tests/unit/generalization/operations/<object>/`, run against the fake.
5. Imports. The contracts are the rule (§6 rows 8, 12, 13); this is what they leave open to an
   operation or helper module:
   - stdlib;
   - from `ag.core`: `handles`, `operations`, `types`, `injection`, `errors`, `warnings`;
   - `ag.ports` (the re-exported vocabulary; never an adapter);
   - `ag.observability`;
   - `ag.generalization.helpers`, `ag.generalization.errors`, and for an operation its own
     package's modules.
   And what they forbid: `ag.core.data_objects` and `ag.core.pipeline`, **directly or through
   another module**, which rules out `ag.core.locations`, `graph`, `selection`, `policy`,
   `planning` and `validation` as well, since each imports one of the two (import-linter's
   `forbidden` contracts follow indirect imports); `sources`, `products`, `pipelines`,
   `registry`; `ag.adapters`, `ag.staging`, `ag.runtime`, `ag.orchestrator`, `ag.lineage`; any
   vendor library (`arcpy`, `networkx`, `shapely`, the storage clients). If `lint-imports`
   fails, the failing contract's message says which of these it was.

**A new stage.**
1. `ag/generalization/pipelines/<object>/<scale>/<stage>.py`: the stage's `Handles` class and
   its `Stage`.
2. Any new `Derived` in `pipelines/<object>/<scale>/objects.py`.
3. Add the stage to the `Pipeline` in `pipelines/<object>/<scale>/__init__.py`; add a `Publish`
   there if it produces a product.
4. A new external input is one declaration in `sources.py`; a new published identity is one in
   `products.py`. A new (object, scale) pipeline is one line in `registry.py`.
5. `context_radius_m` is a claim about the logic; say in the stage's docstring how it was
   measured, or that it was not.

**Anything else** (a new port, a new adapter package, a new top-level package, a change under
`core/`, `lineage/`, `staging/`, `runtime/`) is an architecture change and goes through review
first.

---

## 8. Departures from the planned tree, in one list

| # | departure | reason |
|---|---|---|
| 1 | `core/operations.py` splits into `core/handles.py` and `core/operations.py` | makes "ports and adapters import handles only" a module-level contract (§6 row 4) |
| 2 | `core/findings.py` | `selection` depended on `validation` for one type |
| 3 | `ports/predicates.py`, `ports/columns.py` split out of `geometry_ops.py` | shared by two ports; keeps the Protocol file the contract |
| 4 | `ports/capabilities.py` | adapters publish the record and may not import `lineage/` |
| 5 | `adapters/_shared/` | the engine-free resolver is needed by the ArcPy adapter, the fake and the tests; an adapter may not import another adapter |
| 6 | a package per port inside each adapter, one module per method group; group classes hold Protocol methods only; `_base.py` and a `support/` package per adapter. The planned tree's `adapters/arcpy/predicates.py` and `geometry.py` become `support/predicate_compiler.py` and `support/geometry_values.py`, so that an adapter's root holds only the session, the base and the port packages | §3.2 |
| 6b | `arcpy` may be imported anywhere under `ag/adapters/arcpy/`, not only in `session.py`; a local stub in `stubs/arcpy_constrained/` that omits tools, `env` and exceptions keeps the one-module rule for those. The planned tree's "`import arcpy` appears in exactly one file" becomes "tools, the environment and vendor exceptions appear in exactly one file" | §6.1 |
| 6c | `ports/workspace_format.py`: `WorkspaceFormat` moves out of `staging/workspace.py` because `TableOps.create_workspace` names it | A5.7 |
| 6a | `runtime/compose.py` takes port instances, never an adapter name; `runtime/stage_ref.py` is the one import by string; `ag.adapters.fakes` importable by `runtime/local.py` only | §4 |
| 7 | `lineage/` as a top-level package, with `work_key.py` inside it | absent from 03-architecture §7 because it postdates it; T3.2's "no home" finding |
| 8 | **all domain code under `ag/generalization/`** (if you choose option B) | §2 |
| — | `tests/conformance/` instead of `tests/contract/`; `tests/support/` added | §4 |

`adapters/arcpy/errors.py` from the planned tree is not created: the errors a caller sees are in
`ports/errors.py` (T2.4) and adapter defects are in `adapters/errors.py`, shared by every
adapter.
