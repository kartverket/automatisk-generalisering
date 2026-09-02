# Runtime design: cartographic generalization on Kubernetes

**Status:** TARGET — not yet implemented

**Owns:** how the system executes — declarations, derivation, storage scopes, legality and
placement, run selection, partition correctness, validation, invariants.

**Does not own:** how the code is structured — packages, ports, adapters, import direction,
failure handling and observability are [03-architecture](03-architecture.md); vocabulary is
[01-terminology](01-terminology.md); what changes in the current codebase is
[04-migration](04-migration.md).

**Graduates when:** `src/ag/core/` and `src/ag/runtime/` exist and a stage runs end to end on
the cluster, at which point this becomes reference documentation for the implemented system.

**Executable companion:** [`template_code/`](template_code/README.md) is the same design as
type-checked Python — the types, the derivation algorithms, and two worked pipelines — laid out
as the source tree [03-architecture §7](03-architecture.md#7-the-tree) specifies, so that tree is
checkable rather than prose.

**External unknowns:** `file_seames_discussion/platform_team_questions.md`.

---

## 1. The shape of the system

### 1.1 One flat stage graph

**A stage is the only thing the runtime schedules.** There is no global level, no scale level,
and no pipeline level in execution. Scale and object are *tags* on a stage, used to scope a run
and to compute placement per tag group. Nothing traverses a hierarchy.

A stage expands into three Kubernetes Jobs: fan-out → K partition pods → fan-in.

```
stage ── fan-out (1 pod) ── Indexed Job (K pods) ── fan-in (1 pod)
```

Stages form one graph, derived from declared IO. `arealdekke_n25` depends on `arealdekke_n10`
and on nothing else — it does not wait for `road_n10`, because no data flows between them. A
scale-major loop would serialize on something that is not a real dependency.

**Fan-out is a node type, not a level.** Partitioning is geometric; it exists because features
have extents and neighbours. Only a stage has extents to partition.

### 1.2 Pod tiers

| tier | reaches object storage | reads/writes data | knows K8s | ArcPy |
|---|---|---|---|---|
| orchestrator | run metadata only | **never** | yes | no |
| fan-out | yes | yes | yes | partition, select |
| partition pod | own payload | yes | minimally | the operations |
| fan-in | yes | yes | yes | append, clip |

**The orchestrator never touches data.** Declarations, graph state, run records, Job specs. No
feature class passes through it, so no data-residency rule constrains its placement — only
control-plane reachability does. That framing matters for security review: *"needs Job
create/watch on both clusters, never touches data"* is a very different conversation from
*"holds credentials for both environments."*

**Partition pods do reach object storage.** An Indexed Job offers no other channel into its
pods. What stays blind is *operation logic*, not the pod — see
[two IO vocabularies](#21-two-io-vocabularies-deliberately-different-types).

### 1.3 The orchestrator is ours to write

Argo CD is available and does deployment, not orchestration. Argo Workflows is not available,
but we would build our own regardless, for three reasons independent of availability:

- **The graph is derived, not authored.** Using Argo would mean compiling our derived graph
  into a Workflow spec — keeping all the derivation code and adding a translation layer.
- **Two clusters.** A workflow controller schedules pods in its own cluster. We choose an
  environment per pipeline across two clusters, so we would need two installs plus a
  coordinator above them, which is the orchestrator.
- **We have declined resumability**, which is the most expensive thing it would provide.

This is smaller than it sounds. Execution is sequential, so the executor is a loop — no
queueing, no backpressure, no resource arbitration, no run-state persistence. Order of hundreds
of lines against the official Python `kubernetes` client.

**Fan-out maps onto a native primitive.** `Job` with `completionMode: Indexed`: `completions=K`
is one pod per partition, `parallelism=P` is the throughput knob, `JOB_COMPLETION_INDEX` is the
partition id, and the Job reaching `completions` **is** the fan-in barrier.

---

## 2. Declarations

### 2.1 Two IO vocabularies, deliberately different types

| | declared by | has | used for |
|---|---|---|---|
| **DataObject** | a stage | identity, lineage, legality, remote location | the dependency graph, classification, pinning |
| **ScratchHandle** | the stage module, as a class attribute | a name, a namespace, a data type, and at runtime a path | wiring operations to each other |

`DataObject` is `ExternalSource | ProductIdentity | Derived`. An operation *receives* a
`ScratchHandle`; it does not declare one. **`namespace` is part of handle equality**, so
`Network.ranks` and `ConflictResolution.ranks` are different values rather than merely different
symbols — without it, any structure keyed by handle across stages conflates them.

They cannot be confused because they are different types, and `StageInput` is the only place
one is bound to the other.

**An operation only ever sees ScratchHandles.** Never a DataObject, never a URI, never a client,
never a partition index, never a context radius. An operation runs a fixed sequence of GP tools
against whatever it is handed. That ignorance is what lets it run on a laptop against a
directory of gdbs with no credentials and no cluster — and it is load-bearing for correctness,
because an operation that knew its halo could behave differently near a partition edge.

### 2.2 Data objects

Three kinds of thing, in two leaf modules plus the pipeline. Collapsing any two loses
something.

```python
# ── sources.py — every external source in the project, one declaration each ──
NVDB_ROADS  = ExternalSource(dataset="NVDB_Roads", scale=Scale.RAW,
                             location="s3://kv-source/nvdb/roads.gdb",
                             classification=Classification.PREM_ONLY)

# ── products.py — every published identity, one declaration each ─────────────
N50_BUILDING_POLYGONS = ProductIdentity(scale=Scale.N50, dataset="BuildingPolygons",
                                        location="gs://kv-products/n50/building_polygons.gdb")
N100_BUILDING_POLYGONS = ProductIdentity(scale=Scale.N100, dataset="BuildingPolygons",
                                         location="gs://kv-products/n100/building_polygons.gdb")

# ── the pipeline's own objects module ────────────────────────────────────────
SELECTED  = Derived("selected_polygons",  origin=(N50_BUILDING_POLYGONS,))
DISPLACED = Derived("displaced_polygons", origin=(N50_BUILDING_POLYGONS,))

publishes = (Publish(obj=DISPLACED, identity=N100_BUILDING_POLYGONS),)
```

**ExternalSource** — data entering the *project* from outside it. **`classification` is
required**, not optional. **Declared once, for the whole project.**

**ProductIdentity** — something a pipeline publishes and other pipelines read. Carries its own
location, so a product has a destination whether or not anything consumes it. **Carries no
classification**: the legality of something we produce is computed over the wiring that produced
it, and the single human assertion lives on `reclassify_to`. A field here would be a second,
unreviewed home for that judgement.

**Derived** — produced by a stage. **Has no `location` parameter**, so a derived object cannot
carry one; "a new identity declares its location, an existing one inherits it" is enforced by
construction rather than by a check.

**All three have identity equality (`eq=False`).** They are symbols. This replaces value
equality on `(scale, dataset)`, which linked independently written declarations across
pipelines — and did so with `location`, `classification` and `data_type` all excluded from the
comparison, so a second declaration that *omitted* a restriction compared equal to one that
stated it, and the omitting pipeline computed `CLOUD_OK` for restricted data with no error
anywhere. One declaration site removes the disagreement; a required `classification` removes the
omission. ADR-0012.

**Publish** — promotes a Derived to a `ProductIdentity` at the pipeline boundary. Not derivable
— which outputs are products external consumers depend on is a human decision. Both sides
reference the same symbol, so the producer and its consumers are linked by go-to-definition
rather than by a string match.

**`origin` names lineage roots only, and it means lineage — not influence.** It answers "what
dataset is this, fundamentally." Most objects have one origin and keep it for life. More than
one only when data is genuinely combined, such as a join or a merge. `DISPLACED` keeps
`N50_BUILDING_POLYGONS` alone: road geometry moved it, but no road data is in it.

**The immediate predecessor is never declared.** That `SIMPLIFIED` comes from `SELECTED` is
already stated by the operation wiring.

**Either an object crosses a stage boundary and is a `Derived`, or it does not and is a
`ScratchHandle`.** There is no third state. A `Derived` that no `StageOutput` names is not
uploaded, is invisible to `warn_unused_handles`, and documents a lineage the runtime does not
use.

**Identifiers are symbols; values stay literals.**

**The test:** could a different string literal ever be correct here, given the rest of the code?
If no — only one is ever right and the system misbehaves when it differs — it is an *identifier*
and must be a symbol. If yes — it names something outside the program — it is a *value* and
stays a literal.

Identifiers, therefore symbols: every IO entry, every declared handle name (supplied by
`__set_name__` from the class attribute), every operation parameter name (read off the signature
by `@operation`). Go-to-definition lands on the declaration, find-references lists consumers,
rename is a real refactor, a typo is an error at import.

**`Derived("selected_polygons")` deliberately stays a literal.** It is declared once, `eq=False`,
and no consumer requires it to match its symbol — any unique string would work. What *is*
required is uniqueness within the pipeline, because the scratch location is built from it, and
that is a check rather than a naming mechanism. Converting it would also mean an LSP rename moved
a live object's run-scratch location and invalidated the resume window for in-flight runs.

Internal scratch names (`scratch("dissolved")`) are the same case: nothing in the program reads
them, they render into a layer name in a workspace that dies with the pod, and the only reader is
a human looking at a scratch dump.

### 2.3 Stages

A stage declares DataObject IO and wires operations with ScratchHandles.

```python
class Displacement(Handles):                 # one class per stage
    buildings    = handle()
    roads_source = handle()
    simplified   = handle()
    displaced    = handle()

DISPLACEMENT = Stage(
    name="displacement", scale=Scale.N100, object_name=ObjectName.BUILDING,
    handles=Displacement,
    context_radius_m=1500.0,
    inputs=(
        StageInput(obj=SELECTED,   handle=Displacement.buildings,    role=InputRole.PROCESSING),
        StageInput(obj=NVDB_ROADS, handle=Displacement.roads_source, role=InputRole.CONTEXT),
    ),
    outputs=(StageOutput(obj=DISPLACED, handle=Displacement.displaced),),
    operations=(
        simplify_polygons(input=Displacement.buildings, output=Displacement.simplified,
                          config=tuning.SIMPLIFY_POLYGONS),
        propagate_displacement(input=Displacement.simplified, displacement=...,
                               output=Displacement.displaced),
    ),
)
```

**A handle no `StageOutput` names is not carried forward.** `Displacement.simplified` gets no
identity, no location, and no place in run-scratch, so no later stage can address it and nothing
depends on it existing. It still goes up in the scratch dump ([§4.3](#43-scratch-dump)) like
everything else in the pod scratch root — reachable for troubleshooting, on the dump's retention,
never as an input. That is not an optimisation to implement; it is what happens when nobody
declares it.

**Handles are class attributes, not module constants.** `__set_name__` supplies the `name` and
the `namespace` from the attribute, so the name is written once and two handles in one stage
cannot collide — which is what deleted the uniqueness check that used to police it. A handle
built outside a class body has no namespace and is rejected where it is bound.

**`handles=` is not decoration.** It is what makes cross-stage leakage checkable: a
`Displacement` operation still referencing a handle from another stage's class type-checks, is a
perfectly good `ScratchHandle`, and otherwise fails in the pod as a missing dataset after fan-out
has already moved the data.

**Grouping criterion: a stage is the span between re-partitionings.** Operations belong
together when they prefer the same partition size — a judgement about data, not derivable from
code. Every stage boundary costs roughly 2K transfers plus a merge, plus an image pull per
node, so grouping is what stops a 15-operation pipeline paying that fifteen times.

**The cost of grouping is halo width.** `context_radius_m` must cover the whole operation chain,
and the requirement compounds because each operation works on the last one's output. There is a
crossover where splitting a stage is cheaper than widening its halo, and it is measurable.

**Operations run in listed order.** No intra-stage DAG: within one process in one workspace a
list is enough, and the author grouped them deliberately. Correctness of the list is checked
([the static checks](#8-validation)), not derived.

**`role` is for fan-out, never for an operation.** Processing inputs are partitioned by extent
and drive fan-in, where center-in features are kept and the rest discarded. Context inputs are
selected within `context_radius_m` and not carried into the output. A non-spatial lookup table
is context in the operative sense — replicated whole to every pod, written **once** at a shared
key rather than K times.

### 2.4 Operations

Scale-agnostic, written once, reused by every scale. **The function is the declaration.**

```python
@operation
def thin_road_network(
    *,
    roads: In, ranks: In,                       # handles this operation reads
    output: Out, dropped: Out,                  # handles it writes
    tb: Toolbox,                                # the ports
    config: ThinRoadConfig,                     # everything tunable, frozen
    scratch: ScratchScope = INJECTED,           # internal scratch, injected by the pod
) -> None:
    dissolved = scratch("dissolved")
    tb.geometry.dissolve(input=roads, output=dissolved)
    _build_topology(roads=dissolved, tb=tb, scratch=scratch.child("build_topology"))
```

`@operation` changes only the return type — `Callable[P, OperationCall]` — so the declaration
site is type-checked against the real signature, go-to-definition lands on the implementation,
and a renamed parameter is an error in the editor at every call site. It reads the operation
name, the parameter names, the input/output split and whether a `ScratchScope` is wanted **off
the signature**, so none of the four is restated.

This replaces a hand-written factory twin per operation that restated all four as strings, where
renaming a parameter produced `TypeError: unexpected keyword argument` inside a pod after fan-out
had already moved the data. ADR-0011.

**What fails at import**, while the pipeline module is being read in CI or at orchestrator
startup: an unannotated or misclassified parameter, a positional-or-keyword parameter, a
misspelled or missing keyword at a declaration site, a non-handle passed to an `In`/`Out`, a
handle built outside a class body, a config that is not a frozen dataclass, and a `scratch=`
passed where there is no workspace to allocate in yet.

**An operation calls ports, never a vendor library.** `import arcpy` appears in one file in
the whole system; the engine reaching an operation is whichever adapter the pod entry point
put in the `Toolbox`. This is what keeps a declaration module importable with arcpy blocked, which
[§2.6](#26-declarations-must-be-constructible-without-touching-data) requires. See
[03-architecture, the import rules](03-architecture.md#41-the-rules). `Toolbox` is the fourth
parameter kind `@operation` admits, alongside `In`/`Out`, `config` and `ScratchScope`; anything
else is rejected at decoration.

**Internal scratch comes from a `ScratchScope`**, so a developer writes bare names and never
invents unique ones. A helper receives a scope the same way an operation does — derive downward —
so it never learns its own trail and stays callable from anywhere.

### 2.5 A pipeline is a development artifact

`(scale, object)`. Real for **development**: it has production timeline goals, someone
sequences it, and its parameters get tuned. Absent at **runtime**: flattening produces a stage
registry and the pipeline stops mattering.

It owns exactly two things: the stage membership list, and the publication list. Locations and
legality are *not* among them — those live in `sources.py` and `products.py`, one declaration
per identity for the whole project.

Its `external_inputs` is a derived property over its stages, not a declaration — a hand-written
list would go stale, and since placement is its only consumer, a stale list means a pipeline
silently scheduled in the wrong environment. It covers both kinds of lineage root, because
placement is a reachability question: reading an `s3://` published product pins a pipeline
on-prem for exactly the same reason as reading an `s3://` external source.

### 2.6 Declarations must be constructible without touching data

A declaration must be constructible by importing its module and calling a declaration function,
**without reading data or invoking ArcPy**. Deriving the graph, computing classification, and
validating all require reading every declaration without running anything.

Enforce it: a test that constructs every declaration in a subprocess with `arcpy` import
blocked and filesystem access denied. Without it, someone will eventually open a feature class
to decide an output name.

### 2.7 Configs and tuning

**One frozen config dataclass per operation**, passed as the parameter named `config` and
enforced at decoration, so `OperationCall.parameters` is uniformly `{"config": ...}` or empty and
a run manifest gets a serializable tuning record per operation with no special-casing. An
operation with nothing tunable declares nothing.

Config *fields* are declared beside the operation, because they change when it changes. Config
*values* live in tuning modules, because they change per scale: an object base module stating
every field, one `replace` delta per scale, over per-scale cartographic constants named for the
concept (`MINIMUM_VISIBLE_LENGTH_M`) rather than the consuming parameter. **No resolution
mechanism** — sharing happens because a line of code references a constant, so "what is N100's
road thinning length" stays a value you read rather than one you compute. ADR-0013.

**No config carries a scale.** An operation that could read the scale could branch on it, and
"one function serves N50 and N100" would stop being enforced by anything. The scale selects
*which* config; it is never *in* one.

`__post_init__` on a frozen config is the first place in the design with anywhere to put a
constraint on a value — a stage cannot check that a tolerance is positive.

---

## 3. Derivation

### 3.1 The one rule

> **Stage B depends on stage A iff B's declared inputs include one of A's declared outputs.**

Nothing declares a dependency and nothing declares a sequence.

Under the one-producer rule, declared edges would carry *identical* ordering information —
naming an output uniquely names its producer. The reason to derive is what else each artifact
does. IO must be declared regardless: the pod has to know what to download, pinning needs it,
classification is the join over inputs, placement follows from input locations. Declared edges
would be load-bearing for ordering and nothing else — a redundant second artifact that can
contradict the first.

Two further consequences worth naming:

- **The file is the dependency.** The producing stage is the mechanism that brings it into
  existence, not the thing depended on.
- **Refactoring is free.** Split a stage in two, with the second producing the original output,
  and every consumer is unchanged.

The one thing derivation cannot express is ordering with no data reason ("run this last"). In
this design that is nearly moot, since in-place mutation is forbidden and every real dependency
is a data dependency.

### 3.2 Two ways an edge arises

1. **Object identity** — the consumer names the very `Derived` a stage produces. Intra-pipeline,
   where both stages share the symbol.
2. **Published identity** — the consumer names a `ProductIdentity` some pipeline publishes.
   Cross-pipeline. `building_n100` reads `N100_ROAD` because from its side it is external data
   with a location; `road_n100` produces a `Derived` and promotes it to that identity with a
   `Publish`. **The Derived and the identity are different objects, so matching on the Derived
   alone finds nothing.**

Handling only (1) makes road and building look independent — they could run in either order,
and building would displace against whatever roads were in the archive. No error, just quietly
wrong maps.

Because both sides reference the same symbol, this is a dictionary lookup rather than the
`(scale, dataset)` string match it used to be. It also makes a `ProductIdentity` mean two correct
things at once: "this identity is my input", and "here is where to find it if nothing in this run
produces it." An identity no pipeline here publishes simply has no entry, and consumers read its
declared archive location.

### 3.3 What is never derived

Publication policy, `origin`, stage grouping, and `context_radius_m`. Each carries a human
judgement nothing else knows.

---

## 4. Storage

### 4.1 Four scopes

| scope | lifetime | substrate | paths from | transport |
|---|---|---|---|---|
| pod-local | dies with the pod | the pod scratch root | ScratchFileManager | — |
| intra-stage | the stage | object storage (or NFS) | `locations.py` | ArchiveClient |
| run-scratch | run + retention | object storage (or NFS) | `locations.py` | ArchiveClient |
| archive | permanent | Scality on-prem / GCS cloud | `locations.py` (declared on the identity) | ArchiveClient |

**Every remote path has one owner.** `locations.py` builds all four — payloads, stage outputs,
scratch dumps, and the archive location it reads off a `ProductIdentity` — because three
components independently computing the same name will drift, and the failure is a worker reading
nothing or fan-in silently merging K−1 partitions and reporting success. It is also where the
environment prefix is applied, so the argument below is made once rather than in one of four
places.

Which scope an edge crosses is **derived from tags**: same stage is pod-local, same tag group
is run-scratch, different tag group is the archive.

**Publication to archive is a distinct, deferrable act**, separate from writing a stage output.
A crashed run leaves scratch that a lifecycle policy eats — not a half-written product that
reads as valid. That is the transactional boundary the current shared-disk model lacks.

**Substrate is not model.** Only the staging layer knows whether a scope is object storage or a
shared filesystem. If the platform offers a ReadWriteMany volume, intra-stage and run-scratch
can move to NFS and nothing above changes. The prize is not bytes: a `.gdb` is a directory
tree, so object storage forces archive/unarchive at every hop, with all ArcPy handles released
first or the archive captures `.lock` files and unflushed state. On a shared filesystem the
directory is simply there. Preferred shape if it arrives: **NFS as transport, local disk as
working storage** — copy the partition in, work locally at full speed, copy out. That keeps the
no-pack win and never asks ArcPy to run against NFS.

### 4.2 Scratch workspaces and naming

The ScratchFileManager owns every path in the pod scratch root, and nothing else — every
*remote* path comes from `locations.py` ([§4.1](#41-four-scopes)). **Two workspace tiers:**

- **Stage workspace** — every declared handle: stage inputs, inter-operation handles, stage
  outputs. Names are the handle name, **no trail**, because a handle's name comes from a class
  attribute and is therefore unique within the stage by construction. Operation B must be able to
  read what operation A wrote, so these cannot live in a per-operation workspace.
- **Operation workspaces** — internal scratch. Names carry the trail below the operation.

Putting the operation name in the *workspace* rather than the layer name buys back a level of
name budget and organizes the scratch dump for free.

```
/tmp/n100_road_network_part00003.gdb/                       declared handles
/tmp/n100_road_network_part00003/                           loose files (.lyrx, .csv, logs)
/tmp/n100_road_network_part00003__thin_road_network.gdb/
    dissolved
    build_topology__nodes
    build_topology_2__nodes
```

**Nest in the name, not the path.** A trail rendered as a layer-name prefix gives the full
provenance while keeping paths two segments deep. Four levels is about 74 characters against a
160-character file-GDB limit.

**Compute the name budget, do not hardcode it.** On Linux only the 160-character layer limit
applies. On Windows it is `min(160, 260 − len(workspace) − 1)`, so a deep developer root makes
`MAX_PATH` bind first. Computing it turns a mysterious ArcPy failure into a clear message.

**Error, never truncate**, on over-budget names — truncation silently collides. When trails do
start exceeding budget, render first-two + `t<hash8>` + last-two; the manager's manifest maps
every rendered name to its full trail, so an elided name stays readable. That change lives in
one function.

**Repeated scope labels auto-index** (`build_topology`, `build_topology_2`), because the same
helper is legitimately called twice. First occurrence unnumbered. A repeated *leaf* name within
one scope is an error — that is a genuine mistake.

**No timestamps.** The scratch root starts empty and dies with the pod, so nothing collides.
Determinism buys something concrete: the same failure produces the same path, and two runs'
file listings diff. Run isolation lives in the `run_id` in the remote path.

**A workspace is a workspace.** A `.gdb` is a directory of feature classes, a `.gpkg` a file of
tables, a plain directory holds shapefiles. The manager owns the join rule; an operation never
learns which is in use.

### 4.3 Scratch dump

Every pod tier uploads its whole scratch root at exit, under a job parameter defaulting on. Total
run-scratch is 0.5–3 GB globally and each dump is far smaller, so the cost of always having the
trail is trivial against one afternoon of not having it. The estimate assumes adapter-internal
intermediates are deleted on success and retained only on failure — see
[03-architecture, adapter-internal scratch](03-architecture.md#46-adapter-internal-scratch).

**It goes to the runtime environment's storage.** Safe, and the reason is a dependency someone
could break: running in cloud requires no `s3://` external inputs, and `PREM_ONLY` data lives on
`s3://`, so cloud placement implies nothing restricted was read. **This holds only while
"PREM_ONLY implies stored on-prem" holds.** If that invariant ever lapses, the dump becomes the
easiest leak in the design — it contains *more* detail than the published product.

The same argument covers payloads and stage outputs, which is why it is stated once in
`locations.py` rather than in one of the four path builders.

Keep per-pod workspaces separate rather than merging: knowing which partition misbehaved is
most of the diagnostic value. Ship the trail manifest alongside, and share a prefix with the
run metadata so one download gets counts, timings, drift, and the features they describe.

### 4.4 Retention is the resume window

You can only resume from stage N if stage N−1's output still exists. Retention on `run-scratch/`
should cover the realistic iteration loop — order of a week. Beyond it, rerun from the last
archived boundary. A lifecycle policy, not a feature.

---

## 5. Legality and placement

### 5.1 Two different questions

| | determined by | grain |
|---|---|---|
| **Placement** — where pods run | reachability: if any input's location is on-prem, the whole pipeline runs on-prem | once per pipeline |
| **Classification** — where an output may be stored | policy | per data object |

Location is evidence for placement. It is **not** evidence for classification. A `CLOUD_OK`
dataset that happens to sit on `s3://` forces on-prem placement and taints nothing.

**Only one direction needs guarding.** On-prem data must not reach cloud. Cloud data flowing
on-prem is always safe — it moves into the more restrictive environment. One gate, not two,
which is why the common pattern (pull cloud inputs on-prem, process there, return outputs to
cloud) is legitimate by construction.

### 5.2 Classification is computed over stage wiring

> **Every Source that reached a stage taints everything that stage produces, context included.**

Not over `origin`. `DISPLACED`'s origin is `BUILDING_N50`, which is `CLOUD_OK` — but its
geometry was determined by restricted NVDB road positions, and displaced footprints partially
encode the centrelines they were pushed away from. Computing over origin would publish that to
cloud.

Conservative by construction, and it never depends on a human correctly judging whether an
influence is also a leak. Lineage and legality are two traversals over the same declarations,
and this is exactly where they diverge.

### 5.3 Placement is per pipeline

If any source is on-prem, the whole pipeline runs on-prem. Three reasons, the first decisive:

- **It is where the storage model already switches.** Pipeline-to-pipeline handoff goes through
  the archive anyway, so a cross-environment switch *between* pipelines is free. A switch
  *inside* one would break exactly the case run-scratch exists to serve.
- **It is where classification is already declared**, so both become one computation.
- **Per-stage placement would rarely differ.** Once a stage runs on-prem and writes Scality,
  every downstream stage is pinned there.

The cost of switching is not scheduling — creating a Job in the other cluster is one API call.
The expense is that the data cannot follow.

### 5.4 Rules, and monotone precedence

Classification rules live in **one dedicated file**, separate from pipeline code, so a security
reviewer can read the whole policy without reading any pipeline.

- a rule supplies the classification for any lineage root it matches
- the declared `ExternalSource.classification` may be **more** restrictive, freely
- **less** restrictive is not expressible on an `ExternalSource` at all
- nothing matches: fail closed

This dissolves "which source of truth wins" rather than answering it.

`classification` is **required** on an `ExternalSource`, so there is no "unstated" case to
resolve. A `ProductIdentity` carries none at all: what we produce is computed, not declared.

**Rules key on the input's own scale, never the consuming pipeline's.** `building_n100` reads N50
products and unscaled NVDB simultaneously; a rule "N10 is PREM_ONLY" applies to the N10 *input*
and forces the pipeline on-prem even though it produces N100.

An over-broad rule costs invisibly: nothing errors, work simply runs on-prem forever and
outputs inherit restrictions they never needed.

### 5.5 Reclassification

The one place a human may assert a product is less restricted than what produced it is
`reclassify_to` on a `Publish`.

**Per output, not per pipeline.** A pipeline may publish a generalized product *and*
diagnostics that retained the detail; a blanket reclassification would sweep both silently.

**It takes effect at publication**, which is physically the on-prem → cloud copy — so the guard
fires at one discrete, auditable point rather than being smeared across a run.

**It follows the product to its consumers.** When another pipeline reads a published identity,
its classification is the producing stage's computation with `reclassify_to` applied — so a
consumer of a declassified product sees `CLOUD_OK`, not the producer's raw `PREM_ONLY`. An
identity nothing here publishes falls back to rules and fails closed.

A mismatch between a declared destination and a computed classification is **an error, never
auto-resolved.** It is evidence of human error and requires oversight. Checked in CI, again at
plan time before any pod is created, and again in fan-in before upload — **one function, three
callers.** Discovering at the end of a three-hour run that fan-in may not write its output is
the worst available failure mode.

---

## 6. Running

### 6.1 A run is a selection

```python
RunRequest(run_id, scales=frozenset({Scale.N100}), objects=frozenset({ObjectName.ROAD}))
RunRequest(run_id, operations=frozenset({"simplify_polygons"}), closure=Closure.DOWNSTREAM)
RunRequest(run_id)                                      # everything
```

Enum members, not strings. `Scale.N100`'s *value* is `"n100"`, so a bare `{"N100"}` fails the
type checker and, worse, silently selects nothing at runtime.

**`orchestrator/cli.py` is what builds a `RunRequest`** — the driving adapter, and the only
entry point into a run ([03-architecture §4.5](03-architecture.md#45-the-driving-side)). It is
an ordinary process, so a human invoking it and a Kubernetes `CronJob` invoking it are the same
path with the same arguments. **Scheduled runs are the intended steady state** once the system
is stable; ad-hoc invocation is what development and reruns use. Neither is built yet.

Predicates over `scale`, `object`, `operation` and `stage`. Supplying more than one **narrows**:
a stage is selected only if it matches all of them, so `scales={N100}, objects={ROAD}` is the
N100 road stages, not every N100 stage plus every road stage. The result is then expanded by
closure direction. Two closures answer different questions: **downstream** is "what is affected
by what I changed", **upstream** is "what do I need to run this at all."

**Select by operation, not by object tag,** for "we changed a core generalization operation" —
the operation may be used by stages under other objects, which an object filter would miss
while over-selecting stages that do not use it.

**Upstream errors rather than auto-expanding.** If a selection's inputs are missing, fail and
name them. Silently expanding a request for one object into a six-hour run is the kind of
surprise that costs a night. This is the one place existence checking enters the design.

### 6.2 Pinning

Every identity resolves to a concrete version **once**, at plan time; pods receive pinned
handles. Otherwise a publish landing mid-run gives two stages different vintages.

> If an identity is produced by an **earlier stage in this same run**, it pins to that stage's
> planned output — not to whatever is currently in the archive.

The entire ladder is this case. Get it wrong and the run silently generalizes from stale data.

### 6.3 The loop

Plan is a pure function; execute is a loop. That split is the most important structural
decision in the orchestrator: the whole planning layer is testable without infrastructure, and
CI runs the same validation the orchestrator runs at startup, because it is the same function.

Per stage: fan-out writes K payloads and run metadata **including K**; the Indexed Job runs;
fan-in merges and uploads. **K flows back up by the orchestrator reading fan-out's metadata** —
metadata, not data. It is the only value that flows upward.

**Job names must include scale, object, and stage**, or one stage deletes another's Job.

**Poll, do not watch.** Polling is stateless and retries naturally across a dropped link; a
watch is a long-lived connection that proxies close without telling either end, surfacing as a
hang rather than an error. Stage transitions at two-minute granularity are irrelevant against
hours of ArcPy.

**`ownerReferences` cannot cross clusters.** Remote-cluster Jobs need explicit cleanup by label
selector, with TTL as a backstop — and TTL only fires on completion, so it does not help with a
Job orphaned by an orchestrator crash.

### 6.4 Failure and resume

**Two different levels, and only one of them fails.** Every Job tier retries under
`backoffLimit`, and partition pods are required to be idempotent so that retry is safe
([§7.4](#74-partition-pods-must-be-idempotent)). A pod dying is ordinary and handled.

**What is not persisted is how far the run got.** If the orchestrator itself dies, the run
fails and a human reruns with `--invalidate-from <stage>`, which computes the downstream
closure over the declared graph — not "that stage and everything after it in the list."

**No fingerprinting, and that is the durable part.** A human forgetting to invalidate is
visible and recoverable; an incomplete fingerprint reporting a stale cache as valid is silent.
The one obligation on a failed run is not leaving orphaned Jobs.

**Whether the orchestrator process should survive its own death is open**, and separable from
the above. The plan is a pure function of the declarations plus the `RunRequest`, so a restarted
orchestrator re-derives the identical plan for free; the only thing it cannot re-derive is how
far it got, and it could *observe* that by asking whether each planned output location exists.
That is existence, not fingerprinting, so it does not carry the failure mode this section
rejects — but it requires stage-output upload to be atomic, or a fan-in killed mid-upload leaves
a partial object that reads as done. [§11](#11-open-items) carries it.

Pod-level disruption, the Job spec that survives it, why resume granularity is the stage, and
the log trail a failed run leaves are all in
[03-architecture, failure and disruption](03-architecture.md#8-failure-and-disruption).

### 6.5 Concurrency, if it ever pays

The graph permits running independent stages at once, and the design is ready for it:

- **The in-place-mutation blocker does not apply across tag groups.** The one-producer rule
  guarantees no two pipelines write the same identity, and their intermediates live under
  different prefixes. This is safe in a way concurrent stages *within* a pipeline are not until
  [partition-pod idempotency](#74-partition-pods-must-be-idempotent) holds everywhere.
- **The real gate is capacity.** Each stage is already parallel across K pods. If K saturates
  the cluster, concurrency buys contention.
- **Locking is not needed and should not be built.** With no in-place mutation, every object is
  write-once-read-many; readiness is what the dependency edge already encodes. The useful
  version of that idea is object state as readiness — `pending → producing → available →
  failed` — which is data-driven rather than structure-driven and costs nothing to adopt later.

---

## 7. Partition correctness

### 7.1 The halo requirement is transitive

Fan-out gives each pod a complete dataset plus an overlapping halo. Logic must be deterministic,
so a feature appearing as center-in in partition A and as halo context in partition B is moved
**identically** in both — otherwise fan-in stitches together geometry that disagrees with
itself.

The constraint is stronger than "halo covers features that affect mine." It is **"covers
features that affect features that affect mine,"** for as many hops as the logic propagates.
Displacement chains: displace A, A now conflicts with B, displacing B, which affects C.
Required radius is search distance × propagation depth, and depth is data-dependent — dense
urban extents chain further than sparse ones.

### 7.2 Partition invariance is testable — build it first

"The team knows the logic must be written this way" is exactly the class of invariant that
erodes.

**Run a stage at K=4 and K=16 and diff the outputs.** Genuinely partition-independent logic
with an adequate halo produces identical results. Where they differ there is either a partition
dependence or an undersized halo, and the diff identifies which features.

**Build it against the current implementation, before any Kubernetes work.** It finds today's
violations mechanically rather than by discipline; it becomes the regression test for the
rewrite, and "did the rewrite preserve semantics" is otherwise very hard to answer for geometric
logic; and it exercises the real requirement rather than a proxy. It gets harder once the old
implementation stops running.

**This is the one piece of near-term work this document recommends starting now.**

### 7.3 Sizing objective inverts

Existing partition optimization tunes for one process running partitions sequentially — more
partitions means more iterations means slower, so it pushes toward fewer, larger partitions
bounded by memory.

Under fan-out the objective inverts: more partitions means more parallelism, bounded by cluster
capacity, but each carries fixed overhead — pod startup, image pull, payload transfer, context
selection. **Do not port the existing logic unchanged.**

More broadly, much of the current partitioning design worked around one ArcPy licence being
tied to a core. That restriction does not apply here. When mining existing code for lessons,
discount anything that looks like a single-process workaround.

### 7.4 Partition pods must be idempotent

Kubernetes retries failed pods, and OOM on a dense partition is plausible. A retried pod must
produce the same result as a fresh one — which holds as long as it reads only its own payload
and writes only its own outputs.

**This requires all appending to happen in fan-in.** Appending incrementally as partitions
complete double-appends under retry.

---

## 8. Validation

One entry point, `validate(registry, ranking, rules) -> list[Finding]`. No cluster, no
credentials, no data, no ArcPy. Runs in CI **and** at orchestrator startup, from the same
function. Findings accumulate rather than raise, so one run reports everything wrong at once, and
each carries a **severity**: ERROR aborts the run, WARNING is reported and does not.

It takes the registry rather than one pipeline because over half these invariants are
cross-pipeline.

**The layering rule the whole design follows:**

> Nothing that can fail at import may be deferred to plan.
> Nothing that can fail at plan may be deferred to the pod.

So this section holds exactly what cannot be made structural or checked at import. Every check
should be able to say why it is here — the refactor keeps *deleting* checks by making things
impossible, and the surviving set should read as a legible list of what the type system cannot
express rather than as accumulated habit.

**Inside a stage** — ScratchHandle level:

1. Every operation declares at least one output. *An operation that consumes and produces
   nothing is dead code or an undeclared in-place mutation.*
2. Each handle is written by at most one operation. *Reading is unconstrained; it is writing that
   must be unique.*
3. No operation reads a handle a later operation writes. *The correctness condition for the
   list, and the reason no intra-stage DAG is needed.*
4. Declared stage IO is actually wired. *An unread input downloads gigabytes per partition for
   nothing; an unwritten output fails at upload after all the work.*
5. Every handle a stage touches comes from the handle class it declares. *A handle borrowed from
   another stage's class type-checks and is a perfectly good `ScratchHandle`; it resolves to a
   path in a workspace this pod never creates. This is what `Stage.handles` and
   `ScratchHandle.namespace` exist for.*
6. **(WARNING)** A handle written, read by nothing, and named by no `StageOutput`. *Legal,
   usually dead work.*

**Across stages** — DataObject level:

7. Every `Stage` agrees with its `Pipeline` on scale and object. *Cannot be an import-time check:
   a Stage is fully constructed before the Pipeline that lists it exists. The tags reach the
   scratch path, the Job name, run selection and the placement tag group.*
8. `Derived` names are unique **per pipeline**. *The scratch location is built from the name and
   `Derived` has identity equality, so two same-named objects compute the same location and one
   silently overwrites the other. Per pipeline is deliberately stricter than the path scheme
   requires — the path carries a stage segment — because this design sells regrouping operations
   across stages as a free edit, and a regroup that merges two stages would turn a latent
   duplicate into a silent overwrite.*
9. Exactly one stage produces each `Derived`. *A precondition for derivation, not hygiene: two
   producers make the edge ambiguous and derivation silently picks one.*
10. No two pipelines publish the same identity. *Not covered by 9 — two pipelines can publish two
    different `Derived` to the same identity, so every object has one producer and the identity
    still has two. The loser is dropped without a word.*
11. The stage graph is acyclic. *Does not follow from the operations being sensible: grouping is
    manual, so `op1(A) → op2(B) → op3(A)` is a fine operation sequence and a deadlocked stage
    graph. This is the main way a bad grouping fails.*
12. Every `origin` root is reachable through the wiring. *Deliberately not the converse — a
    stage may read roots that are not in its output's lineage.*
13. No input ranks coarser than the consuming stage's scale. *N25 reading N100 is an error.*
14. No pipeline reads an identity it publishes. *The ladder-input-at-own-scale mistake, which 9
    does not catch because there is still one producer. Now a symbol comparison, so it also
    catches the case where the two would have been spelled differently.*
15. Every publication destination is consistent with its classification.

**Two checks were deleted rather than fixed**, and both deletions are the point:

- *Declared handle names are unique within the stage* — handles are class attributes now, and two
  attributes in one class body cannot share a name. The check policed a property Python already
  guarantees. It was also wrong: it flagged every `StageOutput` naming a handle an operation
  writes, which is the required wiring.
- *One location per identity across all pipelines* — an `ExternalSource` is declared once, in
  `sources.py`. There is nothing to reconcile, and equality is no longer on `(scale, dataset)`.

**One check cannot move earlier than the pod.** After each operation, every declared output must
exist with its declared type. This is the only thing that verifies `DataType` at all, and it
covers the two ArcPy failure modes that do not raise: a tool that completes having written
nothing (an empty selection and a silent no-op look identical), and one that writes the wrong
kind of thing. Sweeping after *each* operation rather than at the end of the stage is what makes
the error name the operation that caused it.

**Not statically checkable**, recorded so nobody adds a weak proxy: that operations in a stage
genuinely share a partitioning, and that `context_radius_m` is large enough. Both are claims
about data, validated by [the K-invariance harness](#72-partition-invariance-is-testable--build-it-first).

---

## 9. Invariants

The properties everything else rests on. Breaking any one silently invalidates a chunk of the
design.

| invariant | what depends on it |
|---|---|
| No unit modifies its inputs | edge derivation, idempotency, resume, any concurrency |
| Exactly one producer per object | edge derivation is a function, not a relation |
| `PREM_ONLY` implies stored on-prem | the scratch dump following the runtime environment |
| Declarations need no data or ArcPy | CI validation, plan-time classification, the whole planner |
| Operations never see partitioning | partition invariance, and therefore fan-out correctness |
| Locations exist only on `ExternalSource` and `ProductIdentity` | a `Derived` cannot carry one, so scratch paths are always mechanical |
| Classification is declared only on `ExternalSource` | the legality traversal has exactly one place to bottom out |
| `namespace` participates in `ScratchHandle` equality | any structure keyed by handle across stages; the cross-stage leakage check |
| Data objects have identity equality | `classification_of`'s memo is keyed by object; two look-alike declarations never share an answer |

---

## 10. Explicitly not building

- **A workflow engine.** The graph is derived, not authored, and the executor is a sequential
  loop: no queueing, no backpressure, no resource arbitration, no concurrent dispatch. Not
  building something Argo-shaped that could host other work — `orchestrator/execute.py` records
  the three reasons that hold even where Argo is available.
- **Run-level state persistence.** Every Job tier retries under `backoffLimit`, and partition
  pods are required to be idempotent so that retry is safe. What is not persisted is how far
  the *run* got: an orchestrator failure fails the run and a human reruns
  ([§6.4](#64-failure-and-resume)).
- **Fingerprint-based invalidation.**
- **Parallel stage execution within a pipeline**, until [partition-pod idempotency](#74-partition-pods-must-be-idempotent) holds everywhere. The payoff is
  small regardless: throughput comes from within-stage fan-out.
- **Locking.**
- **Multi-version artifact tracking.** Separable from invalidation.
- **Ports and adapters anywhere but the boundaries.** Configuration is data with many *values*,
  not a capability with many *implementations*; a Protocol over it is a category error. The two
  places a port pays: `ArchiveClient`, and the Kubernetes client so failure paths can be tested
  against a fake.
- **A global execution level.** The design must not forbid it; do not build for it.

---

## 11. Open items

- **Cluster topology.** One API server or two — the single blocking external fact.
- **On-prem → GCS, with credentials.** An on-prem pipeline reading cloud-published inputs is the
  ordinary case, so this is required for the design to work at all.
- **Node-disk `emptyDir`.** A RAM-backed scratch root will OOM at real data sizes.
- **Shared filesystem availability**, which decides [the storage scopes](#41-four-scopes) substrate.
- **`context_radius_m` per stage.** Not derivable; needs [the K-invariance harness](#72-partition-invariance-is-testable--build-it-first) to measure.
- **Run-scratch retention**, which sets the resume window.
- **Whether the orchestrator restarts and reconciles by existence** rather than failing the run
  ([§6.4](#64-failure-and-resume)). It needs no state persistence — the plan re-derives — but it
  needs atomic stage-output upload, so that existence means validity, and it needs a restarted
  orchestrator to adopt its predecessor's Jobs by `run_id` label rather than recreate them. The
  label-selector path is owed anyway, because `ownerReferences` cannot cross clusters. Decide it
  with an ADR: it changes what `--invalidate-from` is for.
- **Who edits stage grouping and parameters** — cartographers or developers. It is
  simultaneously a cartographic artifact and a performance-tuning one, and those may not have
  the same owner.
- **Symbology.** If `.lyrx` files are authored by cartographers they are archive objects with
  vintage and pinning; if by developers they belong in the repo and the image. A governance
  question that decides the technical answer.
