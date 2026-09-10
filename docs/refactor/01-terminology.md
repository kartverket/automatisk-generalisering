# Terminology

**Status:** TARGET — not yet implemented

**Owns:** the vocabulary. Every project-specific term, its definition, and which document is
authoritative on it.

**Does not own:** any decision. Where a definition and a design document disagree, the
authoritative document listed in the entry wins and this file is the bug.

**Graduates when:** the identifiers named here exist in `src/ag/`, at which point it becomes
the vocabulary reference for the implemented system rather than a target.

Most of them already exist in [`template_code/ag/`](template_code/README.md), which is where to
look for a term in use rather than defined. The exceptions are the port vocabulary — `port`,
`adapter`, `Toolbox`, `driven`/`driving` — which is designed but unwritten.

Written for two readers: a developer joining the team, and an AI coding assistant reading the
repository. The second is why this file exists in a team that already knows the domain — a
model that infers "workspace" or "container" from general usage will write the wrong code and
the wrong review comments.

---

## 1. Terms

### System

| term | meaning | authority |
|---|---|---|
| **stage** | The only unit the runtime schedules. Expands into fan-out → K partition pods → fan-in. Tagged with a scale and an object. | [02-runtime §2.3](02-runtime.md#23-stages) |
| **operation** | A declared processing unit inside a stage. Decorated with `@operation`, so calling it returns an `OperationCall`; can be named in a `Stage`; scale- and object-agnostic. | [02-runtime §2.4](02-runtime.md#24-operations) |
| **helper** | A reusable function below the operation level. Mechanical test: not decorated with `@operation`. | [03-architecture §5](03-architecture.md#5-the-helper-layer) |
| **pipeline** | `(scale, object)`. A development artifact: it owns stage membership and the publication list. Absent at runtime. | [02-runtime §2.5](02-runtime.md#25-a-pipeline-is-a-development-artifact) |
| **DataObject** | What a stage declares as IO. `ExternalSource`, `ProductIdentity` or `Derived`. Carries identity, lineage and legality. | [02-runtime §2.1](02-runtime.md#21-two-io-vocabularies-deliberately-different-types) |
| **ExternalSource** | Data entering the *project* from outside it. Declared once in `sources.py`; `classification` is required. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **ProductIdentity** | A published identity, carrying its own archive location. Declared once in `products.py`. Carries no classification. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **LineageRoot** | `ExternalSource` or `ProductIdentity` — the two things that carry a location and that an `origin` may name. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **Derived** | A data object produced by a stage. Has no `location` parameter, by construction. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **Publish** | Promotes a `Derived` to a `ProductIdentity` at the pipeline boundary. The only place a human may declassify. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **origin** | The lineage roots a data object fundamentally *is*. Lineage, not influence, and not used for legality. | [02-runtime §2.2](02-runtime.md#22-data-objects) |
| **ScratchHandle** | A named slot in the pod scratch root. What an operation receives instead of a path, a URI or a client. Declared as a class attribute; `name` and `namespace` come from the attribute. | [02-runtime §2.1](02-runtime.md#21-two-io-vocabularies-deliberately-different-types) |
| **namespace** | The handle class a `ScratchHandle` was declared in. Part of its equality, so two stages' `ranked` are different values. | [02-runtime §2.1](02-runtime.md#21-two-io-vocabularies-deliberately-different-types) |
| **ScratchScope** | A trail-bound factory for internal scratch handles, derived downward into helpers. | [02-runtime §2.4](02-runtime.md#24-operations) |
| **trail** | Provenance encoded as a layer-name prefix, so paths stay two segments deep. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **workspace** | A file grouping holding named layers: a `.gdb` directory, a `.gpkg` file, or a directory of shapefiles. The arcpy sense. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **stage workspace** | The workspace holding every declared handle for a stage. Names carry no trail. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **operation workspace** | The workspace holding one operation's internal scratch. Names carry the trail. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **pod scratch root** | The pod's ephemeral directory. Holds several workspaces plus a sibling directory of loose files. Not itself a workspace. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **payload** | One partition's data, written by fan-out at the key the worker and fan-in independently recompute. | [02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming) |
| **fan-out** | The single pod that partitions a stage's processing inputs, writes K payloads, and records K. | [02-runtime §6.3](02-runtime.md#63-the-loop) |
| **partition pod** | One of K workers running the stage's operations against its own payload. Must be idempotent. | [02-runtime §7.4](02-runtime.md#74-partition-pods-must-be-idempotent) |
| **fan-in** | The single pod that merges K outputs, discards non-center-in features, and uploads. | [02-runtime §6.3](02-runtime.md#63-the-loop) |
| **K** | The partition count for a stage. Decided by fan-out; the only value that flows upward. | [02-runtime §6.3](02-runtime.md#63-the-loop) |
| **halo** / **context radius** | The overlap included in each partition so a feature is processed identically wherever it appears. Transitive. | [02-runtime §7.1](02-runtime.md#71-the-halo-requirement-is-transitive) |
| **closure** | Expansion of a run selection along the graph. Downstream = what my change affects; upstream = what I need to run at all. | [02-runtime §6.1](02-runtime.md#61-a-run-is-a-selection) |
| **pod-local** | Storage scope that dies with the pod. | [02-runtime §4.1](02-runtime.md#41-four-scopes) |
| **run-scratch** | Storage scope living for the run plus a retention window. Retention is the resume window. | [02-runtime §4.1](02-runtime.md#41-four-scopes) |
| **archive** | Permanent storage. Scality on-prem, GCS in cloud. | [02-runtime §4.1](02-runtime.md#41-four-scopes) |
| **classification** | Where an output *may* be stored. Policy, computed over stage wiring. Independent of URI scheme. | [02-runtime §5.2](02-runtime.md#52-classification-is-computed-over-stage-wiring) |
| **placement** | Which cluster pods run in. Reachability, decided once per pipeline. | [02-runtime §5.3](02-runtime.md#53-placement-is-per-pipeline) |
| **port** | A `Protocol` naming one purposeful conversation with something outside the core. | [03-architecture §2.1](03-architecture.md#21-the-six) |
| **adapter** | An implementation of a port. The only place a vendor library is imported. | [03-architecture §4.1](03-architecture.md#41-the-rules) |
| **driven port** | A port the core calls out through. All six declared ports. | [03-architecture §4.5](03-architecture.md#45-the-driving-side) |
| **driving adapter** | An actor that calls into the core: `orchestrator/cli.py`, the `runtime/` entry points, `tests/invariance/`. No primary port is formalised. | [03-architecture §4.5](03-architecture.md#45-the-driving-side) |
| **Toolbox** | The frozen bundle of ports passed explicitly into operations and helpers. | [03-architecture §4.4](03-architecture.md#44-how-ports-reach-the-code) |
| **config** | The one non-IO parameter an operation takes: a frozen dataclass holding everything tunable. Never contains a scale. | [02-runtime §2.7](02-runtime.md#27-configs-and-tuning) |
| **tuning** | The values in a config, per scale. A base module plus one `replace` delta per scale; no resolution mechanism. | [02-runtime §2.7](02-runtime.md#27-configs-and-tuning) |
| **scale constant** | A cartographic fact about the map at one scale, shared across objects. Named for the concept (`MINIMUM_VISIBLE_LENGTH_M`), not the consuming parameter. | [02-runtime §2.7](02-runtime.md#27-configs-and-tuning) |
| **Finding** | One validation result, carrying a `Severity` of ERROR or WARNING. | [02-runtime §8](02-runtime.md#8-validation) |

### Identity and lineage

**Status:** designed, not implemented. Authority is
[`temp/DECISIONS.md`](temp/DECISIONS.md) until each entry migrates to its ADR or module
docstring; the A-ids below are that file's section numbers.

| term | meaning | authority |
|---|---|---|
| **native index** | The storage format's own row index — `OBJECTID` in a file gdb, `fid` in GeoPackage. Behind the port. Valid only until the dataset is next written. | A9.2 |
| **`lineage_id`** | A run-scoped, feature-level identity. One row, one id — always 1:1. Signed `BIGINT`; positive is raw, negative is generated. Re-minted on any net cardinality change, so it holds *current* identity, not origin. | A9.1, A10.1 |
| **`work_key`** | An operation-scoped unique row key allocated by the work-key API as `work_key_001`, `work_key_002`. The caller never names the field. Swept at operation exit. | A9.3, A9.4 |
| **`minter_id`** | The 20-bit prefix of a generated `lineage_id`, handed to a job at dispatch from a single run-scoped counter. `0` is reserved invalid. A retry reuses its job's value. | A10.2 |
| **mint** | To allocate a new `lineage_id` and record an edge. Done by the lineage facade, not by operation bodies. | A11.11, A11.12 |
| **mint generation** | Informal: which round of minting an id comes from. Ids either side of a cardinality change are different generations and will not join. | A9.10 |
| **lineage edge** | `(operation, kind, from_ids, to_ids)`. The N:M lineage relation lives here and never in a field. | A11.5 |
| **`EdgeKind`** | `TRANSFORMED` \| `DERIVED` \| `DROPPED` \| `CREATED`. Always derived by the runtime from parent survival; never declared. Descriptive — completeness is computed from set membership, not from the label. | A11.5, A11.6 |
| **lineage log** | The out-of-band, run-scoped, write-only record of edges. Nothing in the pipeline reads it mid-run. | A11.1 |
| **parents** | Which input rows produced an output row. Two senses, deliberately one word: the optional `parents:` out-param on a collapse method, and the `mint(parents=…)` argument. Columns are `PARENT_ID` / `CHILD_ID`. | A11.1 |
| **row shape** | A per-output declaration on a port Protocol method, `@row_shape(out=Rows(...))`, read by the lineage facade. Two axes, never a single enum. | A12.1 |
| **cardinality** | Row-shape axis: `ONE` \| `MANY` \| `GROUP` output rows per subject row. | A12.1 |
| **identity** (row-shape axis) | `CARRY` (keep the subject's id) \| `MINT` (new ids, edges recorded) \| `FOREIGN` (no `lineage_id`; declared columns hold subject ids). `CARRY` implies `ONE`. | A12.1 |
| **subject** | The input parameter whose rows contribute identity to an output. Mirrors PROCESSING. | A12.2 |
| **reference** (row-shape) | An input that influenced an output without contributing identity. Mirrors CONTEXT. | A12.2 |
| **ref column** | A column on a `FOREIGN` output holding a subject's `lineage_id` as a foreign key. A null is legitimate data. When it feeds a rebuild, the ref column *is* the lineage path. | A11.12, A11.13 |
| **in scope** | A handle reaches a `StageOutput`. Decides whether the boundary diff runs. | A15.2 |
| **lineage-bearing** | A handle's declaration chain ends in `CARRY` or `MINT`, so it has a `lineage_id` column. A `FOREIGN`-terminal handle can be in scope without being lineage-bearing — `SNAP_DISPLACEMENT` is. | A15.6 |
| **domain key** | A field whose value the data determines (`kommunenummer`, `vegkategori`). The only legitimate join key across a cardinality change, because attribute propagation preserves it and `lineage_id` does not. | A9.10 |
| **combining rule** | How a collapse reduces several parents' values to one, stated at the call site as `dissolve(statistics=…)`. Domain logic. The log records that the collapse happened, never which parent's value won. | A11.14 |
| **ingest map** | Per-source `native_index → lineage_id`, written as a run artifact by the ingest step that copies each `ExternalSource` and allocates raw ids. | A10.6, A10.7 |
| **dispatch registry** | `minter_id → (stage, partition_index)`, written at dispatch and merged at fan-in. | A10.3 |

### Domain

One line each. This grounds identifiers; it does not teach cartography.

| term | meaning |
|---|---|
| **generalization** | Deriving a coarser, legible map from finer source data by removing, simplifying and moving features. |
| **scale** | A product scale in the national series: N10, N25, N50, N100, N250. A closed `StrEnum`, with `Scale.RAW` as the member for unscaled sources such as NVDB — RAW ranks finest, so anything may read it and the one-producer rule is vacuous for it. |
| **the ladder** | The chain in which one scale's published output is the next scale's input: N10 → N25 → N50 → N100 → N250. |
| **object** | A pipeline domain. A closed `StrEnum`: road, building, river, railway, land_use. |
| **dataset** | A lineage root name: `Road`, `BuildingPolygons`, `Matrikkel`. A `ProductIdentity` or `ExternalSource` is `(scale, dataset)` plus a location — but the two sides of a publication link by *symbol*, not by matching that pair. Not the same as *object*. |
| **operator** | A named generalization action from the ICA taxonomy: simplification, aggregation, collapse, displacement, typification, selection. Port method names come from this list. |
| **feature** | One row in a feature class: geometry plus attributes. |
| **feature class** | A table of features inside a workspace. |
| **center-in** | The ownership rule at fan-in: a feature belongs to the partition containing its centroid. |
| **NVDB** | The national road database. `Scale.RAW`, and `PREM_ONLY` — the restriction that pins both example pipelines on-prem. |
| **Matrikkel** | The national cadastre. `RAW` scale, and `CLOUD_OK` — unlike NVDB it carries no restriction. |
| **`.lyrx`** | An ArcGIS layer file carrying symbology. Here an arcpy adapter input format, not a project concept. |

---

## 2. Collisions

Terms whose project meaning differs from the obvious general reading. These are the ones that
produce wrong code when guessed.

| term | means here | does **not** mean |
|---|---|---|
| **workspace** | A multi-dataset file grouping — `.gdb`, `.gpkg`, a shapefile directory. The arcpy sense. | The pod's scratch directory (that is the **pod scratch root**). An editor/VS Code workspace. A Terraform workspace. |
| **container** | An OCI container: an image, and a pod's runtime. | A `.gdb`, a `.gpkg`, or any data grouping. That sense is retired — see [§3](#3-retired-and-discouraged). |
| **layer** | Depends on context, and every use must be disambiguated: a *feature layer* is arcpy's in-memory selectable view; a *layer name* is the name of a feature class inside a workspace; an *architectural layer* is a package tier in [03-architecture §4](03-architecture.md#4-layers-and-the-import-hierarchy); a *map layer* is a `.lyrx`. | Anything unqualified. Write which one. |
| **object** | A pipeline domain. A closed `StrEnum`: road, building, river, railway, land_use. | An OOP object or instance. Not a "data object" either — that is `DataObject`. |
| **operation** | A declared unit inside a stage, decorated with `@operation`. | Any operation in the general sense. A port method is a *port method*; an arcpy call is an *arcpy tool*. |
| **feature** | A GIS feature: one geometry plus attributes. | A product feature or a capability. Never use it that way in this repository. |
| **trail** | Provenance encoded in a layer name. | A log, a trace, an audit trail. |
| **scale** | A cartographic product scale: N50, N100, N250. | Scaling out, replica count, or resource sizing. For that, say *parallelism* or *K*. |
| **helper** | A function not decorated with `@operation`, in `helpers/`. | A generic utility. The test is mechanical, not stylistic. |
| **stage** | A pipeline stage: the unit the runtime schedules. | A Docker build stage. A deployment environment. |
| **source** | `ExternalSource`, the declared type for data entering the *project* from outside. Another pipeline's output is a `ProductIdentity`, never a source. | Source code. Say *source code* explicitly. Anything this project produces. |
| **partition** | A geometric subdivision of a stage's processing extent, one per pod. | A disk partition or a Kafka partition. |
| **archive** | The permanent storage scope, and `ArchiveClient` which transports to it. | A `.tar` or `.zip`. Packing a `.gdb` for transport is *packing*. |
| **scratch** | Any of the ephemeral tiers: the pod scratch root, run-scratch. | Discardable in the sense of unimportant — the scratch dump is a deliverable. |
| **registry** | `StageRegistry` — every stage in the system, flat, produced by `flatten()`. What the runtime and every check take. | An archive identity registry mapping `(scale, dataset)` to a location: that never existed, and `products.py` replaces the idea (ADR-0012). A container registry — say *image registry*. |
| **validation** | The static checks over declarations in [02-runtime §8](02-runtime.md#8-validation). | Geometry validity, or checking data quality. That is *data validation*. |
| **selection** | A `Predicate` value, or the act of materialising one. | A held, mutable arcpy selection set — deliberately absent. *Run* selection, which is `RunRequest` in `selection.py`. A `Selection` handle class: several pipelines name their first stage's handles that, which is why `namespace` uses `__qualname__`. |
| **`DERIVED`** | An `EdgeKind`: at least one parent of this edge survives in an output. A per-row runtime fact. | **`Derived`**, the `DataObject` a stage produces. Two unrelated concepts one capitalisation apart. Always write `EdgeKind.DERIVED` or "a `Derived` object" — never bare *derived*. |
| **lineage** | Depends on level, and every use must say which: **object-level** lineage is `origin` and `LineageRoot`, declared at plan time; **feature-level** lineage is `lineage_id` and the edge log, produced at runtime. | Anything unqualified. The two never join — an `origin` names datasets, a `lineage_id` names a row. |
| **identity** | Depends on context: the **row-shape axis** (`CARRY`/`MINT`/`FOREIGN`), or a feature's `lineage_id`. | **`ProductIdentity`**, which is an object-level published identity in `products.py`. Unrelated. |
| **scope** | Two distinct things, both needing the qualifier: a **`ScratchScope`**, the trail-bound handle factory; and a handle being **in scope** for lineage, meaning it reaches a `StageOutput`. | Anything unqualified. "Scoped handle" is ambiguous — write *lineage-scoped* or *a scratch scope*. |
| **reference** | Three uses, all qualified: a **row-shape reference** is an input that influenced without contributing identity; a **ref column** holds a foreign `lineage_id`; `snap(reference=…)` is the dataset being snapped to. | Anything unqualified. The first and third are close enough to be confused. |
| **registry** | Now three: **`StageRegistry`** (every stage, flat); the **dispatch registry** (`minter_id → stage, partition`); the **work-key registry** (allocated field names per operation). | An unqualified *registry*. Always say which. See also the existing container-registry note above. |
| **parents** | Which input rows produced an output row — a DAG relation, not a genealogy. The `parents:` out-param and the `mint(parents=…)` argument. | A hierarchy, a tree, or anything implying a single parent. A row routinely has many, and a parent routinely has many children. |
| **statistics** | The `dissolve(statistics=…)` combining rule: how a collapse reduces several parents' values to one. | Analytics or run metrics. For those, say *run metadata* or *diagnostics*. |

---

## 3. Retired and discouraged

| word | status | replacement |
|---|---|---|
| **container** (of data) | Retired. Reserved for OCI/Kubernetes. | **workspace** for a `.gdb`/`.gpkg`/directory; **pod scratch root** for the pod's directory. |
| **tool** | Discouraged. | **operation** for a declared unit; **port method** for a `Toolbox` call; **arcpy tool** only when literally meaning one. |
| **general tools** | Retired. The package is removed by the refactor. | **helpers/**, organised on the subject axis. |
| **custom tools** | Retired. Same package. | **helpers/**, **operations/**, or **adapters/** depending on the piece — see [04-migration](04-migration.md#1-what-dissolves). |
| **file manager** | Retired. `file_manager/**` is removed. | `ScratchFileManager` for pod paths; `locations.py` for remote ones; `ExternalSource`/`ProductIdentity`/`Derived` declarations for identities. |
| **`Source`** | Retired as a single type. It conflated external data with other pipelines' products, and its optional `classification` was a leak — see ADR-0012. | **`ExternalSource`** in `sources.py`; **`ProductIdentity`** in `products.py`. |
| **operation factory** | Retired. The hand-written twin that restated an operation's signature. | **`@operation`** on the function itself — ADR-0011. |
| **`ValidationError`** | Retired. | **`Finding`**, which carries a `Severity`. |
| **work file** | Retired. | **internal scratch**, allocated through a `ScratchScope`. |
| **layout** | Retired for storage. Not a concept when storage is not a tree. | Nothing. Locations come from declarations; scratch paths from `ScratchFileManager`. |
| **container format** | Retired. | **`WorkspaceFormat`**. |
| **`origin_id`** | Retired before it was written. It named a feature-level field that is re-minted on every cardinality change, so it never held an origin — and it sat one character from `origin`, which is object-level and plan-time. | **`lineage_id`** for the feature-level field; **`origin`** stays the object-level `Derived` declaration. Nothing should say `origin_id`. |
| **correspondence** | Retired. Used throughout the design discussion for the input-row-to-output-row relation. | **parents** — the `parents:` out-param, `mint(parents=…)`, and `PARENT_ID`/`CHILD_ID`. `source_rows` was rejected because **source** already means `ExternalSource` here. |
| **`PRESERVE` / `COLLAPSE` / `SPLIT` / `EXPAND` / `REFERENCE` / `NONE`** | Retired. Successive single-axis row-shape enums, replaced by two independent axes. | **cardinality** (`ONE`/`MANY`/`GROUP`) × **identity** (`CARRY`/`MINT`/`FOREIGN`). `REFERENCE` became `identity=FOREIGN`; `EXPAND` became `MANY + FOREIGN`. |

Reclaiming "container" for Kubernetes matters as much as naming the replacement.

Without an explicit retirement someone reintroduces the data sense, because it reads naturally
in a GIS context and nothing in the code stops them. The deployment target is OCI containers on
Kubernetes, and these documents discuss pods, images and registries alongside `.gdb` groupings.

"Workspace" was chosen because it is the native arcpy term for a multi-dataset grouping, so it
matches `arcpy.env.workspace` and what developers already read in arcpy documentation.

Rejected alternatives: `store` (implies a database or a state container), `bundle` (implies
packaging for transport, which is what `pack`/`unpack` already means here), `datasource` (an
OGR/JDBC term implying a connection), `archive` (already the permanent storage scope and
`ArchiveClient`).
