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
