# Architecture: packages, ports, and layering

**Status:** TARGET — not yet implemented

**Owns:** how the code is structured — the system boundary, the ports and their vocabulary,
package layering and import direction, the helper layer, observability, failure handling, and
the source tree.

**Does not own:** how the system executes — declarations, derivation, storage scopes, legality,
partition correctness and validation are [02-runtime](02-runtime.md); vocabulary is
[01-terminology](01-terminology.md); what changes in the current codebase is
[04-migration](04-migration.md).

**Graduates when:** `.importlinter` exists and passes in CI, and at least one port has an
adapter plus a contract-test suite. At that point the tree here becomes illustrative and the
contracts file is authoritative.

**Executable companion:** [`template_code/`](template_code/README.md) is laid out to mirror
[§7](#7-the-tree) exactly, so that tree is checkable with `ls` rather than trusted. Where it and
this document disagree, this document is right and the code is the bug.

**Assumption:** all existing code is changeable. `temp_skip_folder/` is a WIP proof that the
K8s shape works; nothing in it survives as written.

Every subsection is tagged **Decided**, **Recommended** (with the question that would reopen
it), or **Open**.

---

## Summary

The system must be able to replace arcpy on need, and networkx and shapely carry the same
requirement. No second adapter is planned or scheduled, so the value delivered now is entirely
in the *shape* of the contracts: a port modelled on arcpy's spelling would pass every test today
and be worthless on the day it is needed. Port vocabulary therefore comes from OGC CQL2, OGC
Simple Features, and the ICA generalization operator taxonomy.

Six ports. `GeometryOps`, `TableOps` and `CartographicOps` split the geoprocessing seam so the
migration can be incremental. `GraphOps` covers networkx. `ArchiveClient` and `ClusterClient`
already have implementations.

A `Geometry` value type sits alongside them so row-level geometry logic survives the migration.

There is no format port and no log port.

---

## Contents

1. [System boundary and constraints](#1-system-boundary-and-constraints)
2. [The ports](#2-the-ports) — the six · vocabulary from open standards · contract shape ·
   selection is a predicate value · the other libraries · format is the same seam
3. [Rows, geometry values, and the cursor](#3-rows-geometry-values-and-the-cursor) —
   no cursor · the Geometry value type · decomposition: line_topology.py
4. [Layers and the import hierarchy](#4-layers-and-the-import-hierarchy) — the rules ·
   enforcement · thick adapters · how ports reach the code · the driving side ·
   adapter-internal scratch · deliberate deviations
5. [The helper layer](#5-the-helper-layer) · 6. [Observability](#6-observability)
7. [The tree](#7-the-tree) — src/ag · ports conventions · stage wiring · object-major ·
   symbology · contract tests
8. [Failure and disruption](#8-failure-and-disruption) ·
   9. [Open questions](#9-open-questions) · 10. [Decisions](#10-decisions)

---

## 1. System boundary and constraints

### 1.1 What is outside

**Decided.**

Everything the system reads or writes but does not control:

| external system | relationship |
|---|---|
| NVDB | raw road source, `Scale.RAW`, `PREM_ONLY` |
| the N50/N100 product registry | ladder inputs read as `ProductIdentity`, published products written back to the same |
| Scality (on-prem) | object storage, `s3://`; the restricted side |
| GCS (cloud) | object storage, `gs://` |
| the ArcGIS licence server | required by every arcpy adapter; a single point of failure for the partition tier |
| Kubernetes, two clusters | the only execution substrate |
| downstream product consumers | read published identities; the reason `Publish` is a human decision |

Two consequences that are otherwise implicit. Legality
([02-runtime §5](02-runtime.md#5-legality-and-placement)) is entirely a statement about which
of these a datum may reach. And the two lineage-root types are what "something crossing this
boundary" means — `ExternalSource` inward only, `ProductIdentity` in both directions — which is
why they are the only places a location is declared. Only the inward one carries a
classification: what we produce is computed, never declared. ADR-0012.

### 1.2 What forces the design

**Decided.**

**The system must be able to replace arcpy on need.** Licensing terms, vendor roadmap and
platform direction are outside our control, and a change in any of them must cost an adapter
rather than a rewrite. That is what turns the geoprocessing seam into a genuine port rather than
a wrapper: the test is a *foreseeable* second implementation, the same test
[02-runtime §10](02-runtime.md#10-explicitly-not-building) (the explicitly-not-building list)
uses to justify `ArchiveClient`. networkx and shapely carry the same requirement at smaller
scale.

**No second adapter is planned or scheduled.** The value delivered now is the shape of the
contracts, not working alternatives — and a contract shaped after the incumbent buys nothing on
the day it is needed. Hence [§2.2](#22-port-vocabulary-comes-from-open-standards).

**Python domain and Kubernetes are permanent.** File format, storage backend and processing
engine are assumed temporary.

---

## 2. The ports

### 2.1 The six

**Decided.**

| port | conversation | ~size |
|---|---|---|
| `GeometryOps` | operations on spatial datasets | 25–35 |
| `TableOps` | schema, attributes, and bulk row IO | 10–15 |
| `CartographicOps` | named generalization operators | 8–12 |
| `GraphOps` | graph algorithms over abstract topology | ~8 |
| `ArchiveClient` | object storage transport | 2 |
| `ClusterClient` | Kubernetes job lifecycle | 4–5 |

**Geoprocessing splits into three ports because the migration must be incremental.** Most
arcpy calls have near-1:1 equivalents elsewhere; the ones that do not are concentrated in the
cartography toolbox, which is 78 of 2801 tool call sites here across 16 distinct tools
([04-migration, Appendix A](04-migration.md#appendix-a-measurements)). That residue is small
and enumerable, but each member needs hundreds to thousands of lines to reproduce. Full
argument: ADR-0002.

`TableOps` separates from `GeometryOps` because it is a different conversation (schema and
rows, not geometry), because it applies to non-spatial lookup tables — a real case here,
[02-runtime §2.3](02-runtime.md#23-stages) (context inputs replicated to every pod) — and
because `GeometryOps.add_field()` reads wrong.

**Ports are `typing.Protocol`, not `ABC`**, so adapters satisfy them structurally and the
dependency arrow never reverses.

Conformance is asserted by an `if TYPE_CHECKING:` assignment at the bottom of each adapter
module, plus one adapter × port matrix in `tests/static/`. ADR-0007.

**Prior art:**

- Cockburn 2005 for the pattern itself.
- Percival & Gregory, *Architecture Patterns with Python* (O'Reilly), for the Python treatment
  this design follows on fakes over mocks and edge-to-edge testing — see `tests/contract/` and
  `adapters/fakes/`. Its store-oriented patterns are rejected per
  [§4.7](#47-deliberate-deviations).
- Django's `Q` and SQLAlchemy's `BooleanClauseList` for the predicate algebra in
  [§2.4](#24-selection-is-a-predicate-value).

### 2.2 Port vocabulary comes from open standards

**Decided.**

**Spatial predicates: OGC CQL2 / DE-9IM.** CQL2 defines standardized spatial predicate
functions with an `s_` prefix over the DE-9IM relation model: `s_intersects`, `s_within`,
`s_contains`, `s_touches`, `s_crosses`, `s_overlaps`, `s_disjoint`, `s_equals`, plus
`s_dwithin` for distance. Our `Relation` enum takes these names, not arcpy's `OverlapType`
strings. Two arcpy relations have no standard equivalent and are expressed as composites
rather than as magic relations:

- `WITHIN_A_DISTANCE` → `s_dwithin`; keep as `Relation.DWITHIN` + `distance_m`.
- `HAVE_THEIR_CENTER_IN` → not a relation but `s_within(centroid(geom), other)`. Express it
  that way so a SQL or dataframe adapter has something to compile. This is the rule fan-in
  uses to decide feature ownership.

**Geometry operations: OGC Simple Features.** `buffer`, `intersection`, `difference`,
`union`, `convex_hull`, `centroid`, `boundary` carry the same semantics in PostGIS, GEOS,
shapely and DuckDB. `erase` becomes `difference`; `clip` stays `clip`, meaning dataset-level
rather than geometry-level.

**Cartographic operators: the ICA taxonomy.** Vendor-neutral operator vocabulary —
selection/elimination, simplification, smoothing, aggregation, amalgamation, collapse,
displacement, typification, exaggeration, enhancement, classification:

| arcpy tool | operator | port method |
|---|---|---|
| `ResolveBuildingConflicts` | displacement + elimination | `displace_features` |
| `ResolveRoadConflicts` | displacement | `displace_features` |
| `PropagateDisplacement` | displacement | `propagate_displacement` |
| `ThinRoadNetwork` | selection (network) | `select_network` |
| `SimplifyLine` / `SimplifyPolygon` | simplification | `simplify` |
| `SmoothLine` | smoothing | `smooth` |
| `AggregatePolygons` | aggregation | `aggregate` |
| `MergeDividedRoads`, `CollapseDualLinesToCenterline` | collapse | `collapse_to_centerline` |
| polygon-to-point | collapse | `collapse_to_point` |

The names describe what the cartographer wanted rather than which vendor button was
pressed, and each maps to a published literature trail for whoever reimplements it.

### 2.3 Contract shape

**Decided.**

- **`ScratchHandle`, not `DataObject`.** `DataObject` is the declaration vocabulary —
  identity, lineage, legality, remote location. Putting it in a port drags the planning
  layer into every adapter. ADR-0003.
- **Project enums, never vendor strings or bare booleans.** `end_cap: EndCap`, not
  `flat: bool`.
- **Keyword-only, explicit units in the name:** `width_m`, `distance_m`, `tolerance_m`.

### 2.4 Selection is a predicate value

**Decided.**

Selection is a composable predicate, not a mutable held selection: a mutable selection is the
arcpy idiom, not the concept, and exposing it would force every future adapter to emulate it.
It is also lazier — nothing materializes until `select`. This collapses the largest idiom
cluster in the codebase, the 616-site make-layer/select triple
([04-migration, Appendix A](04-migration.md#appendix-a-measurements)), into two methods and a
value type. ADR-0001.

`count(input, where=...) -> int` answers "how many match" without materializing; comparing
to zero covers the boolean case. A dedicated `any()` is not shipped: it only pays when a
backend can short-circuit (SQL `EXISTS`, `LIMIT 1`), and arcpy's `GetCount` cannot.

The full vertical slice, port to call site — the only end-to-end example in these documents.

```python
# ── ports/geometry_ops.py ────────────────────────────────────────────────────
class Relation(Enum):                        # CQL2 names, see "port vocabulary" above
    INTERSECTS = "s_intersects"; WITHIN = "s_within"; DWITHIN = "s_dwithin"

class Predicate:                             # `&`, `|`, `~` construct And/Or/Not nodes
    def __and__(self, other: Predicate) -> Predicate: return And((self, other))
    def __or__(self, other: Predicate) -> Predicate:  return Or((self, other))
    def __invert__(self) -> Predicate:                return Not(self)

@dataclass(frozen=True)                      # variants: Attr, Spatial, And, Or, Not
class Attr(Predicate):    cql: str
@dataclass(frozen=True)
class Spatial(Predicate): relate_to: ScratchHandle; relation: Relation; distance_m: float | None = None
@dataclass(frozen=True)
class And(Predicate):     terms: tuple[Predicate, ...]
@dataclass(frozen=True)
class Or(Predicate):      terms: tuple[Predicate, ...]
@dataclass(frozen=True)
class Not(Predicate):     term: Predicate

class GeometryOps(Protocol):
    def select(self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle) -> None: ...
    def count(self, *, input: ScratchHandle, where: Predicate | None = None) -> int: ...

# ── adapters/arcpy/predicates.py ─────────────────────────────────────────────
@dataclass(frozen=True)
class Negated(Predicate): term: Predicate    # adapter-internal; never crosses the port

_COMBINE = {Combine.NEW: "NEW_SELECTION", Combine.ADD: "ADD_TO_SELECTION",
            Combine.REMOVE: "REMOVE_FROM_SELECTION", Combine.SUBSET: "SUBSET_SELECTION"}

def push_negation(p: Predicate, negate: bool = False) -> Predicate:
    """De Morgan to the leaves. arcpy inverts only at a leaf (invert_where_clause,
    invert_spatial_relationship), so Not(And(...)) has no representation."""
    match p:
        case Not(term):
            return push_negation(term, not negate)
        case And(terms):
            return (Or if negate else And)(tuple(push_negation(t, negate) for t in terms))
        case Or(terms):
            return (And if negate else Or)(tuple(push_negation(t, negate) for t in terms))
        case _:
            return Negated(p) if negate else p

def apply(layer: str, p: Predicate, combine: Combine) -> None:
    """And -> SUBSET the running selection; Or -> ADD to it."""
    match p:
        case And(terms) | Or(terms):
            rest = Combine.SUBSET if isinstance(p, And) else Combine.ADD
            apply(layer, terms[0], combine)
            for t in terms[1:]:
                apply(layer, t, rest)
        case Attr() | Negated(Attr()):
            ...          # SelectLayerByAttribute, invert_where_clause
        case Spatial() | Negated(Spatial()):
            ...          # SelectLayerByLocation, invert_spatial_relationship

# The same tree in a SQL adapter — the awkwardness above is one adapter's, not the model's:
#   And(terms) -> " AND ".join(compile(t) for t in terms)
#   Not(term)  -> f"NOT ({compile(term)})"
#   Spatial(h, Relation.DWITHIN, d) -> f"ST_DWithin(geom, {ref(h)}, {d})"

# ── runtime/partition.py ─────────────────────────────────────────────────────
toolbox = Toolbox(geometry=ArcpyGeometryOps(session), table=..., cartographic=..., graph=...)

# ── operations/building/selection.py ─────────────────────────────────────────
# every church building within 500 m of water, excluding any that touch a road
tb.geometry.select(
    input=buildings,
    where=Attr("byggtyp_nbr = 970") & Within(water, 500) & ~Intersects(roads),
    output=selected,
)
```

`Within(water, 500)` and `Intersects(roads)` are constructors over
`Spatial(relate_to=..., relation=Relation.DWITHIN, distance_m=500)` and
`Relation.INTERSECTS`.

### 2.5 The other libraries

**Decided.**

- **networkx → `GraphOps`.** Build a graph from edges, connected components, shortest path,
  MST, cycle detection. Currently `custom_tools/general_tools/graph.py`, `_UnionFind` inside
  `line_topology.py`, and the river strahler modules.
- **shapely → below the `Geometry` value type** ([§3.2](#32-the-geometry-value-type)). Domain
  code manipulates `Geometry`; adapters use shapely, GEOS or arcpy geometry to implement it.
- **numpy → not a port.** A data structure, not a capability.

### 2.6 Format swappability is the same seam

**Decided.**

`buffer(input: ScratchHandle, output: ScratchHandle)` implies the engine can read and write
whatever those handles point at. Format and engine are not independent: a geoparquet future
is a non-arcpy-engine future.

So there is no format port. Swappability comes from the engine ports plus
`staging/workspace.py` — the one module that knows the workspace/layer join rule
(`x.gdb/layer` vs `x.gpkg` vs `dir/layer.shp`), name legality and budget, and whether a
workspace is a directory (pack for object storage) or a single file. An enum plus three
functions: data with several values, not a capability with several implementations.

---

## 3. Rows, geometry values, and the cursor

### 3.1 No cursor

**Decided.**

`SearchCursor`, `UpdateCursor` and `InsertCursor` are 483 call sites here
([04-migration, Appendix A](04-migration.md#appendix-a-measurements)) and the least portable
arcpy API: streaming row iterators with a vendor field-token language (`SHAPE@`, `OID@`,
`SHAPE@XY`).

Target engines are vectorized, where a row loop is idiomatically wrong and orders of
magnitude slower. Porting the cursor faithfully would make the slowest arcpy-shaped pattern
part of the contract and guarantee a bad second adapter. `TableOps` has no cursor:

| purpose | today | port |
|---|---|---|
| set a field from other fields | `UpdateCursor` loop | `calculate_field(input, field, expression)` |
| read attributes for an algorithm | `SearchCursor` loop | `read_rows(input, fields) -> Iterable[Row]` |
| build a dataset from computed rows | `InsertCursor` loop | `write_rows(output, schema, rows)` |

These 483 sites are the most expensive part of the migration and the least mechanically
translatable. ADR-0004.

### 3.2 The `Geometry` value type

**Decided.**

Some logic manipulates geometry values in Python rather than whole datasets:
`line_topology.py` constructs `arcpy.Polyline(arcpy.Array([arcpy.Point(x, y), ...]))`,
inspects `.firstPoint` and `.lastPoint`, and inserts the results. That is our algorithm, and
a dataset-level port gives it nowhere to live.

The port vocabulary therefore includes a small immutable `Geometry` value type — geometry
kind, coordinate sequence, CRS — that `read_rows` yields and `write_rows` accepts. Adapters
convert at the boundary: `arcpy.Polyline(arcpy.Array(pts))` ↔ `LineString(coords)`,
`.firstPoint`/`.lastPoint` ↔ `coords[0]`/`coords[-1]`.

### 3.3 Decomposition: `line_topology.py`

**Decided.**

6581 lines, the hardest case in the repo, and it decomposes without residue:

| today | lands in |
|---|---|
| `SearchCursor` over OIDs, near-table rows, `original_id_field` | `TableOps.read_rows` |
| `MakeFeatureLayer` + `SelectLayerByAttribute` / `ByLocation` | the `Predicate` algebra |
| `GenerateNearTable` | a `GeometryOps` method |
| `_UnionFind`, connected components | `GraphOps` (signature open: **Q-C**) |
| `arcpy.Polyline`, `.firstPoint`, `.lastPoint` | `Geometry` |
| `InsertCursor` with `SHAPE@` | `TableOps.write_rows` |

`_GeneratedLineRecord` exists only to buffer rows because arcpy cannot insert while an
`UpdateCursor` is open. Under bulk read/write it disappears.

---

## 4. Layers and the import hierarchy

```
runtime/  orchestrator/      composition roots: choose adapters, assemble Toolbox
     └────┬────┘
   pipelines/                Stage / Source / Derived declarations
   operations/               declarable units (have an OperationCall factory)
   helpers/                  reusable composites (no factory)
   ports/  ◄─ adapters/ ──►  arcpy, networkx, shapely, gcs, kubernetes
   core/                     types, declarations, planning; imports stdlib only

   staging/         imports core/ + ports/; imported by runtime/ only
   observability/   imports stdlib + core.types; imported by all except core/
```

Nothing imports `adapters/` except the composition roots.

### 4.1 The rules

**Decided.**

| package | may import | may **not** import |
|---|---|---|
| `core/` | stdlib only | everything else in `ag` |
| `ports/` | `core.operations` (handles only), `core.types`, stdlib | `adapters`, `operations`, `staging`, `core.pipeline` |
| `adapters/` | `ports`, `core.operations` (handles only), **its own vendor library** | `operations`, `pipelines`, other adapters |
| `helpers/` | `ports`, `core.operations` | `adapters`, `core.pipeline`, `staging`, `operations` |
| `operations/` | `ports`, `core.operations`, `helpers` | `adapters`, `core.pipeline`, `staging` |
| `sources/`, `products/` | `core` only — leaf modules | everything else in `ag` |
| `tuning/` | `core`, the config types in `operations` | `adapters`, `ports`, `staging`, `pipelines` |
| `pipelines/` | `core`, `sources`, `products`, `tuning`, `operations` (declarations only) | `adapters`, `ports`, `staging`, `runtime` |
| `staging/` | `core`, `ports` | `operations`, `pipelines`, `adapters` |
| `observability/` | stdlib, `core.types` | everything else in `ag` |
| `runtime/` | everything — composition root | — |
| `orchestrator/` | `core`, `pipelines`, `ports.cluster`, `ports.archive`, `observability` | `operations`, `adapters.arcpy`, `staging` |

Every package except `core/` may import `observability/`; `core/` stays side-effect free.

**Only `adapters/` may import a third-party processing library.** `import arcpy` appears in
exactly one file (`adapters/arcpy/session.py`, lazily bound so the module stays
import-safe); `networkx` in one; `shapely` only under `adapters/`. This makes
[02-runtime §2.6](02-runtime.md#26-declarations-must-be-constructible-without-touching-data)
(declarations constructible with no data and no arcpy) pass by construction.

**`runtime/` and `orchestrator/` are the only places that choose which adapter to
instantiate.**

**`sources/` and `products/` must stay leaves.** They are only useful as the single place every
identity is declared; one convenience import back into a pipeline makes them a cycle and the
"read one file and see everything entering the project" property is gone silently. A docstring
saying "leaf module" is not enforcement — a contract is. ADR-0012.

### 4.2 Enforcement

**Decided.**

`import-linter` contracts in `.importlinter`, run in CI, plus the
[02-runtime §2.6](02-runtime.md#26-declarations-must-be-constructible-without-touching-data)
subprocess guard. The table above in machine-readable form:

| contract type | enforces |
|---|---|
| `layers` | the package ordering in the table above: `core` at the bottom, `runtime`/`orchestrator` at the top |
| `forbidden`, `include_external_packages = True` | `import arcpy` appears in exactly one module; same for `networkx`, `shapely` |
| `forbidden` | `sources/` and `products/` import nothing but `core/` |
| `forbidden` | `operations/` never imports `core.data_objects` — the port-boundary rule of ADR-0003, made mechanical |
| `forbidden` | `core/` and `pipelines/` may not import the ambient observability accessor |
| `layers`, `exhaustive = True` | fails when a module exists in the package without being declared — the mechanism that stops the tree and the table drifting apart |

Once `.importlinter` exists **over `src/ag/`** it is authoritative and [§7](#7-the-tree) is
illustrative.

[`template_code/.importlinter`](template_code/.importlinter) is a first instalment, not that
trigger: four contracts — identity modules are leaves, the package stack, `core` imports nothing
above it, and operations never import a `DataObject` — passing over the companion's packages. The
rows above that it cannot yet express are the ones needing `ports/` and `adapters/` to have
content: the vendor-import contracts, and any layering that mentions them.

### 4.3 Port layering and thick adapters

**Decided.**

An adapter may consume other ports — it is a client of those contracts, not of their
implementations, and the composition root wires it:

```python
class OpenCartographicOps:                       # satisfies CartographicOps
    def __init__(self, geometry: GeometryOps, table: TableOps, graph: GraphOps): ...
    def displace_features(self, **kwargs) -> None: ...  # thousands of lines, ports only
```

The eventual non-arcpy `CartographicOps` is written against `GeometryOps`/`TableOps`/
`GraphOps`, not against GeoPandas directly, so it can be developed and tested while arcpy is
still the backend.

**Ports must stay acyclic**, linted: `CartographicOps` may use `GeometryOps`, `TableOps`,
`GraphOps`; those three may never use `CartographicOps`.

**An implementation that adapts nothing is not an adapter.** Our own displacement algorithm
is domain logic that satisfies a port; the first one goes in a top-level `cartography/`,
leaving `adapters/` to mean "wraps somebody else's library". Not created now.

### 4.4 How ports reach the code

**Decided.**

One bundled context object, resolved once by the pod entry point and passed explicitly,
rather than three or four port parameters at 100+ call sites:

```python
@dataclass(frozen=True)
class Toolbox:
    geometry: GeometryOps
    table: TableOps
    cartographic: CartographicOps
    graph: GraphOps
```

Explicit rather than ambient, because
[02-runtime §2.4](02-runtime.md#24-operations) already passes `ScratchScope` as a parameter
and two dependency-passing styles in one signature is worse than either consistently. The one
exception is observability context, which carries no capability. ADR-0008.

### 4.5 The driving side

**Decided.**

All six declared ports are driven (secondary): the core calls out through them. The driving
(primary) side is `orchestrator/cli.py`, the three `runtime/` pod entry points, and
`tests/invariance/`.

**A primary port is deliberately not formalised.** A formal primary port pays off when
several actors drive the same core and logic would otherwise be duplicated across them. This
system has one driving actor — Kubernetes, via the orchestrator — with no plan for a second.
A Protocol around a single caller is ceremony.

Naming the driving side still buys two things. It explains why `runtime/` and `orchestrator/`
sit outside the `core → ports → adapters` layering rather than violating it: they are the
adapters on the driving side, and a composition root is where the two sides meet. And it
identifies `tests/invariance/` as a driving adapter, which is the structural reason the same
pipeline can be driven at K=4 by a harness and K=16 by Kubernetes with no special-casing.
Cockburn names a test harness as the natural primary adapter and isolated-mode execution as
the pattern's ultimate payoff.

### 4.6 Adapter-internal scratch

**Decided.**

**Lifetime test.** An intermediate that dies before the port method returns belongs to the
adapter. One that must survive the call is the caller's, and is a `ScratchHandle`.

**Allocation.** `ScratchFileManager` allocates a workspace for the adapter exactly as it does
for an operation. `runtime/` passes the workspace path plus the computed name budget (a plain
`int`) to the adapter constructor, so the adapter never imports `staging/` —
[§4.1](#41-the-rules) holds, and so does
[02-runtime §4.2](02-runtime.md#42-scratch-workspaces-and-naming)'s "the manager owns every
path in the pod scratch root".

**Retention differs from the declared tiers.** Adapter intermediates are deleted on successful
completion and retained on failure, so a failure lands in the scratch dump and a success does
not inflate it. Declared handles are always kept.

**On graduation to `cartography/`** ([§4.3](#43-port-layering-and-thick-adapters)), an
implementation gets a `ScratchScope` factory by constructor injection instead, so its
intermediates become trail-bearing and dumpable. Port signatures do not change.

### 4.7 Deliberate deviations

**Decided.**

This is batch geoprocessing: no users, no requests, no transactional store, no concurrency
within a pod.

Repository, Unit of Work, DDD aggregates, a service layer above operations, and a message bus
are all deliberately absent. ADR-0010 records why, so nobody later "fixes" the omission.

Two adopted deviations change how the rest of this document should be read:

- **Ports are split by measured call-site frequency**
  ([04-migration, Appendix A](04-migration.md#appendix-a-measurements)), not by "one reason to
  change". The port boundary tracks a vendor library's surface, not a use case.
- **Ports are coarse** (25–35 methods). Interface segregation applies when clients depend on
  different subsets, and here every operation potentially uses any geometry method. This
  weakens the textbook pressure behind **Q-B** — settle it by measurement, not by ISP.

The K-invariance harness
([02-runtime §7.2](02-runtime.md#72-partition-invariance-is-testable--build-it-first)) is the
most valuable correctness mechanism in the system, and it is not a hexagonal artifact.
Partition correctness is data-shaped, and no architecture pattern addresses it.

---

## 5. The helper layer

**Decided.**

Reusable, object-agnostic, scale-agnostic functions that compose port calls. Called only
from inside operations, never named in a stage, never scheduled.

**Membership test:** an operation is decorated with `@operation`, so calling it returns an
`OperationCall` that can be named in a `Stage`; a helper is not decorated. It takes whatever
arguments it needs and never appears in a stage.

**Package name: `helpers/`.** ADR-0005.

**Not `operations/shared/`.** That name is reserved for operations shared between objects,
which [02-runtime §6.1](02-runtime.md#61-a-run-is-a-selection) (selecting a run by operation)
requires.

**Subject axis**, since helpers have no object or scale dimension: `lines.py` (segmentation,
isolated removal, endpoints, angles), `polygons.py` (hole filling, small-feature
elimination), `points.py` (rotation, placement), `topology.py` (node/edge construction,
connectivity), `attributes.py` (field derivation above `TableOps`), `extents.py` (envelope
and partition geometry).

**Promotion rule.** A helper used by one object's operations stays next to them in
`operations/road/`; it moves here on a second caller from a different object.

**Helpers take a `ScratchScope`** exactly like operations, deriving downward.

---

## 6. Observability

**Decided.**

**Logging is not a port.** It fails [§7.2](#72-ports-directory-conventions)'s test: stdlib, no
vendor to adapt, no second implementation foreseeable. Transport of archived logs reuses
`ArchiveClient`. Do not add a `LogPort`. ADR-0006.

**`observability/` is a horizontal leaf** — imports stdlib and `core.types` only; every
package may import it except `core/`, which stays side-effect free
([§4.1](#41-the-rules)).

**Format is JSONL.** Text logs do not merge deterministically: multi-line tracebacks, no
stable sort key.

**Every record carries** `run_id`, `stage_id`, `pod_role`, `partition_index`,
`partition_count`, `operation`, `level`, `ts`, `seq`. `seq` is a per-process monotonic
counter and exists because pod clocks drift, so `ts` alone yields a plausible but wrong
interleaving. Sort key is `(ts, pod_key, seq)`: exact within a pod, approximate across pods.
Fields live in a `ContextVar` and are injected by a logging filter, so an operation calls
`log.info()` with no plumbing.

**Two sinks per pod.** stdout is ground truth: the cluster collector receives it even if the
pod dies. A local JSONL, uploaded via `ArchiveClient` in the pod's `finally`, is the
mergeable artifact; an OOM-killed pod loses it. Layout
`logs/{run_id}/{stage_id}/{pod_role}-{partition_index:04d}.jsonl`, merged to `merged.jsonl`
beside it. **Merge lives in `orchestrator/`**, runs once a stage reaches a terminal state
including failure, and is a streaming k-way merge (`heapq.merge`) since each per-pod file is
already sorted.

**arcpy tool messages bypass Python logging.** `adapters/arcpy/session.py` drains
`arcpy.GetMessages()` after each tool call and re-emits them tagged with the tool name — one
wrapper rather than 483 call sites, a direct payoff of the port design.

**Volume rule:** per-feature at DEBUG, per-operation at INFO. `timing_decorator` emits
structured duration records, so the merged log doubles as a partition profile.

---

## 7. The tree

Packages, responsibilities and import direction. Object and scale subdirectories under
`operations/` and `pipelines/` are per-pipeline and not enumerated here.

**This tree is mirrored by [`template_code/ag/`](template_code/README.md), directory for
directory**, so it is checked by `ls` rather than by reading. That matters because the previous
version of this tree had drifted in eight places — it listed four modules that never existed and
omitted four that did. A directory cannot drift the way a code block can.

Packages the design specifies and the companion has not written — `ports/`, `adapters/`,
`helpers/`, `observability/`, and most of `runtime/` and `orchestrator/` — exist there as
directories holding only a docstring that names what belongs in them. Omitting them would make
the tree read as though the port design were not real.

```
src/ag/
├── core/                    pure. no arcpy, no clients, no filesystem, no k8s.
│   ├── types.py                 Scale, ObjectName (StrEnums), DatasetName, enums
│   ├── data_objects.py          ExternalSource, ProductIdentity, Derived, lineage_roots
│   ├── operations.py            ScratchHandle, __set_name__, Handles, In/Out,
│   │                            ScratchScope, @operation, OperationCall  (ADR-0011)
│   ├── pipeline.py              Stage, StageInput/Output, Publish, Pipeline,
│   │                            StageRegistry, flatten
│   ├── locations.py             StorageRoots + every remote path: archive, source,
│   │                            scratch, payload, scratch dump  (single owner)
│   ├── graph.py                 edge derivation, topological order
│   ├── selection.py             RunRequest, closures
│   ├── policy.py                classification, placement
│   ├── planning.py              RunPlan, pinning
│   └── validation.py            validate() -> list[Finding]
│
├── sources.py               every ExternalSource in the project. leaf.
├── products.py              every ProductIdentity in the project. leaf.
│
├── ports/                   __init__ index docstring, toolbox.py, archive.py, cluster.py
│   ├── geometry_ops.py          + Predicate, Relation, EndCap, DissolveOption
│   ├── table_ops.py             + FieldType, Row
│   ├── geometry.py              the Geometry value type
│   ├── cartographic_ops.py      ICA operator names
│   └── graph_ops.py
│
├── adapters/                only place a vendor library is imported
│   ├── arcpy/                   session.py (lazy import, env, licence, handle release,
│   │                            GetMessages drain), geometry_ops, table_ops,
│   │                            cartographic_ops, predicates, geometry, errors
│   ├── networkx/  storage/  cluster/
│   └── fakes/                   in-memory implementations of every port
│
├── helpers/                 reusable composites below the operation level
├── operations/              declarable units; object subdirectories, scale-free.
│   └── road/                    config CLASSES beside the operations they constrain
│       └── tuning/              config VALUES: base, plus one delta per scale
├── tuning/scale/            cartographic constants per scale, shared across objects
├── pipelines/               declarations; object/scale subdirectories
├── classification_rules.py  the one file a security reviewer reads
│
├── staging/
│   ├── scratch.py               ScratchFileManager, trail rendering, name budget
│   ├── workspace.py             WorkspaceFormat: join rule, legality, pack/unpack
│   └── transfer.py              stage_down / stage_up / dump_scratch
│
├── observability/           JSONL records, context filter, timing
├── runtime/                 fan_out, partition, fan_in, env. Toolbox assembled here.
│   └── stage_entry.py           the pod dispatch loop and the post-operation output
│                                sweep — the one check that cannot move earlier
└── orchestrator/            execute, jobs, metadata, log_merge, cli

tools/                       dev-only scripts, not shipped in the image
                             (incl. dump_tuning — resolved configs per scale)
tests/                       static/ (validation + arcpy-blocked guard + port matrix),
                             contract/ (every adapter against one per-port suite),
                             invariance/ (K=4 vs K=16), unit/
```

### 7.1 `src/ag/`

**Decided.**

`ag` is the distribution and import name (placeholder, see **Q-F**); `src/` is the layout.

The repository root is therefore not importable, so a module resolves only if it was actually
packaged. Tests import `ag` from the installed distribution, which is what ships in the image.

The companion already uses `ag` as its top-level package for that reason: promotion is
`git mv docs/refactor/template_code/ag src/ag`, with no re-layout and no import rewrite, because
`from ag.core.pipeline import Stage` is already the production path. It needs a `conftest.py` to
put itself on `sys.path`; the shipped distribution does not, which is the whole difference.

### 7.2 Ports directory conventions

**Decided.**

Flat; six files are browsable and a `processing/` vs `infrastructure/` split buys nothing.
Revisit past ~10.

`ports/__init__.py` carries a one-line index — "changing attributes? `table_ops`. Moving
geometry? `geometry_ops`. Named generalization operator? `cartographic_ops`."

**Adding a port** requires a distinct external capability *and* a foreseeable second
implementation. Otherwise it is a helper or an adapter detail. A distinct capability sharing
an existing conversation is a method, not a file.

### 7.3 Stage wiring

**Decided.**

Stages are declared per `(scale, object)`; `Stage` carries a `scale` field per
[02-runtime §2.3](02-runtime.md#23-stages). No `compose(object_def, scale_config)` layer.
Layout: directory per `(object, scale)`, one module per stage — a stage is the unit of
scheduling, of the grouping judgement, and of `--invalidate-from`.

Accepted consequence: N100 and N250 road each declare their own stage wiring, differing in
parameter values and which stages are present. Revisit against evidence rather than
pre-building an indirection.

### 7.4 Object-major

**Decided.**

`operations/` has no scale dimension, so a scale-major tree is not expressible there without
reintroducing the scale binding being removed. And the ladder is an object-major chain:
`road/n50 → road/n100 → road/n250` becomes a directory listing, while cross-object edges
(building_n100 reading road_n100) correctly cross a directory boundary.

### 7.5 Symbology

**Decided.**

Symbol dimensions are data, not a port: `LineToBufferSymbologyKwargs` already carries
`sql_selection_query: dict` plus buffer factors, and `BufferDisplacementKwargs` carries
`building_symbol_dimension: Dict[int, Tuple[int, int]]`. They become pipeline parameters, or
an `ExternalSource` context input if cartographers own them (**Q-D**).

`.lyrx` appears only where arcpy's own tools demand it as an input format
(`ApplySymbologyFromLayer`, `resolve_road_conflicts.py`'s `input_lyrx`/`lyrx_output`).
Producing one is an implementation detail inside `adapters/arcpy/cartographic_ops.py`, so
the migration never inherits `.lyrx`. A `StyleOps` port is deferred until there is map
rendering to produce; its adapters would be lyrx / SLD / QML.

### 7.6 Contract tests

**Decided.**

One suite per port, run against every adapter. Written now against the arcpy adapter, it is
the specification the future adapter must satisfy.

---

## 8. Failure and disruption

Orchestrator-level failure and the `--invalidate-from` rerun path are
[02-runtime §6.4](02-runtime.md#64-failure-and-resume). This section owns pod-level
disruption, the Job spec that survives it, and resume granularity. The log trail a failed run
leaves is [§6](#6-observability).

### 8.1 Causes, by likelihood at K partitions

**Decided.**

OOMKill and ephemeral-storage eviction come first: both are new at K and both are caused by
uneven partitions ([02-runtime §7.3](02-runtime.md#73-sizing-objective-inverts)). Then node
maintenance, autoscaler scale-down, node NotReady. Never Spot or preemptible instances for
multi-hour partitions.

### 8.2 The Job spec

**Decided.**

- **`podFailurePolicy`** (GA in Kubernetes 1.31): `Ignore` on the `DisruptionTarget`
  condition, so a maintenance drain does not consume `backoffLimit`; `FailJob` on exit codes
  that will recur. Requires `restartPolicy: Never`.
- **`terminationGracePeriodSeconds`** long enough to upload the scratch dump on SIGTERM. The
  highest-value resilience change available, and it is a number in a manifest.
- **`cluster-autoscaler.kubernetes.io/safe-to-evict: "false"`** on partition pods.
- **Explicit memory and ephemeral-storage limits**, per
  [02-runtime §11](02-runtime.md#11-open-items)'s node-disk `emptyDir` item.

### 8.3 Resume granularity is the stage

**Decided.**

Intra-pod resume is not planned, and the blocker is structural rather than effort. The stage
workspace is pod-local ([§4.1](#41-the-rules)), so resuming from operation N requires
persisting inter-operation handles to run-scratch — the ~2K transfers plus merge that stage
grouping ([02-runtime §2.3](02-runtime.md#23-stages)) exists to avoid.

An operator whose runtime approaches its stage's re-run cost becomes its own stage. That is a
declaration change, not an architecture change. **Q-G** is the measurement. ADR-0009.

---

## 9. Open questions

**Q-A — closed.** See ADR-0005.

**Q-B — `CartographicOps`: one port or several?** Displacement and network selection share
no vocabulary. If the reimplementations are independent projects, splitting per operator
lets them land separately. Defer until at least one is reimplemented; settle by measurement,
not by interface segregation ([§4.7](#47-deliberate-deviations)).

**Q-C — Does `GraphOps` know about datasets?** Whether graph construction is a `GraphOps`
method taking a `ScratchHandle`, or a helper that calls `read_rows` and hands edges to a
pure `GraphOps`. The second is cleaner; confirm against the strahler code first.

**Q-D — Who authors symbol dimensions.** Cartographer-authored means an `ExternalSource` with a
vintage and pinning; developer-authored means pipeline parameters.

**Q-E — closed.** See ADR-0008.

**Q-F — The distribution name.** `ag` is a placeholder.

**Q-G — Is a stage split cheaper than a re-run?** For an operator whose runtime approaches
its stage's total re-run cost, measure whether promoting it to its own stage costs less than
re-running the stage on failure. Measure once one operator is reimplemented
([§8.3](#83-resume-granularity-is-the-stage)).

---

## 10. Decisions

| ADR | decision |
|---|---|
| 0001 | Selection is a composable predicate value, not a held selection |
| 0002 | Three geoprocessing ports rather than one or many |
| 0003 | `ScratchHandle`, not `DataObject`, at the port boundary |
| 0004 | `Geometry` as a value type; no cursor in the port |
| 0005 | `helpers/` as the package name |
| 0006 | Logging is not a port |
| 0007 | Ports are `Protocol`, not `ABC` |
| 0008 | `Toolbox` passed explicitly, not ambient |
| 0009 | No intra-pod resume; the stage is the resume granularity |
| 0010 | Hexagonal adopted selectively for a batch geoprocessing domain |
| 0011 | Declarations come from signatures and class attributes, not from strings |
| 0012 | Sources and products are declared once, centrally, as symbols |
| 0013 | Tuning is base plus one delta, with no resolution mechanism |
