# ADR-0018: Architecture: the boundary, the ports and the packages

**Status:** Accepted, 2026-10-22.

**Scope:** `ag/ports/` as a package, `ag/adapters/`, `ag/generalization/helpers/`,
`ag/observability/`, the composition roots in `ag/runtime/` and `ag/orchestrator/`,
`.importlinter`, and the conformance matrix in `tests/static/`. No A-items.

Related: ADR-0019 (what crosses a port), ADR-0020 (how an operation receives the ports),
ADR-0017 (row shape).

## Direction

1. Ports, adapters, composition roots, contract tests and fakes are adopted from
   ports-and-adapters. The store-oriented and application-oriented patterns of that literature
   are not: this is batch geoprocessing with one sequential executor, no requests and no
   transactional store.
2. A port is a capability the core calls out through, defined by the conversation it carries
   and not by a library. An adapter is per vendor, which adapter serves a port is chosen per
   port at the composition root, and a port's implementation may call other ports. A
   capability outside the geoprocessing seam, such as graph algorithms over abstract topology,
   is its own port.
3. The geoprocessing seam is split by kind of operation: primitive dataset operations, with
   schema and row work, on one side, and named generalization operators on the other.
   Primitive operations have near one-to-one equivalents in other engines; generalization
   operators have none and cost hundreds to thousands of lines each, so one port would block
   any non-arcpy adapter until every operator was rewritten. A generalization port may be
   built on the primitive ports, never the reverse.
4. Every port is a `typing.Protocol`. Conformance is structural and asserted statically; an
   adapter never inherits from a port.
5. A port exists only for a distinct external capability with a foreseeable second
   implementation. Logging and helpers are not ports.

## AR-1 What is adopted, and on what grounds

**Direction.** Adopted decisions rest on domain-specific grounds, not textbook ones, and are
revisited on those grounds.

**Details.**

- **AR-D1** Ports are split by migration path and measured call-site frequency, not by "one
  reason to change". A port's boundary follows what the engines provide, not an application
  use case.
- **AR-D2** Ports are coarse. Interface segregation applies when clients depend on different
  subsets; here every operation may use any method of a port, and all adapters are
  constructed together. A large, implementation-oriented Protocol is the shape PEP 544
  cautions against; it is accepted knowingly. Whether the generalization port splits per
  operator is Q-B, settled by measurement once one operator is reimplemented.
- **AR-D3** Fakes over mocks: the real dependency is licensed, Windows-adjacent and slow.
- **AR-D4** The driving side is the orchestrator's CLI, the pod entry points and
  `tests/invariance/`; it sits outside the `core → ports → adapters` layering as the adapters
  on the driving side, and a composition root is where the two sides meet.
  `tests/invariance/` is a driving adapter, which is why one pipeline runs at K=4 under the
  harness and at K=16 under Kubernetes with no special-casing.

## AR-2 Ports and adapters

**Direction.** A port is a conversation the core has with an engine; the composition root
decides, per port, which adapter carries it.

**Details.**

- **AR-D5** The ports: `GeometryOps` (operations on spatial datasets), `TableOps` (schema,
  attributes and bulk row IO), `CartographicOps` (named generalization operators), `GraphOps`
  (graph algorithms over abstract topology), `ArchiveClient` (object storage transport),
  `ClusterClient` (Kubernetes job lifecycle).
- **AR-D6** `TableOps` is separate from `GeometryOps`: a different conversation, schema and
  rows rather than geometry; it applies to non-spatial tables; and `GeometryOps.add_field()`
  reads wrong.
- **AR-D7** Whether `GraphOps` takes datasets or pure values is Q-C, open. The dataset-aware
  form changes no operation signature, so deciding is deferred until the code that turns on
  it is read.
- **AR-D8** Migration order: `TableOps` first, then `GeometryOps`, then generalization
  operators one at a time, each written against the other ports rather than a new library, so
  the arcpy `CartographicOps` adapter shrinks method by method.
- **AR-D9** `CartographicOps` may use `GeometryOps`, `TableOps` and `GraphOps`; those three
  never use `CartographicOps`. The ports stay acyclic, linted. An adapter that consumes other
  ports is a client of their contracts, not of their implementations, and the composition
  root wires it.
- **AR-D10** An implementation that adapts nothing is not an adapter. A generalization
  operator written on the primitive ports is domain logic that satisfies `CartographicOps`
  and lives in a top-level `cartography/`, so `adapters/` means "wraps somebody else's
  library", and the port names no arcpy concept.
- **AR-D11** Only `runtime/` and `orchestrator/` choose which adapter to instantiate.
  `runtime/compose.py` takes port instances, never an adapter name, and the fake is imported
  by `runtime/local.py` alone.
- **AR-D12** Port vocabulary comes from OGC CQL2, OGC Simple Features and the ICA
  generalization operator taxonomy, never from arcpy's spelling. A port modelled on arcpy
  would pass every test today and be worthless on the day it is needed.
- **AR-D13** An operation that needs several ports receives them as one `Toolbox`
  (ADR-0020 OP-3).
- **AR-D23** Each adapter has one session module that alone executes engine tools, holds
  engine-global state and names vendor exceptions; every other engine call in the adapter,
  including the fetches and the conversions that touch engine objects, runs inside the
  session's guard. No vendor exception leaves an adapter: a tool failure or a guarded call
  leaves it only as `EngineError`, carrying what the engine was asked and its messages. How
  an adapter enforces this is its own. The ArcPy adapter enforces the names with a
  constrained type stub and the direct uses with a static scan; a call on an engine object
  is a review rule.

## AR-3 Ports are Protocols

**Direction.** Conformance is structural, asserted statically and never by inheritance, so
the dependency arrow points one way.

**Details.**

- **AR-D14** Conformance is asserted by an `if TYPE_CHECKING:` assignment at the bottom of
  each adapter module, and by one adapter × port matrix in `tests/static/` that covers the
  fakes.
- **AR-D15** There is no runtime enforcement: `@runtime_checkable` with `isinstance` checks
  method names only, not signatures.
- **AR-D16** Third-party clients and plain dataclass test doubles satisfy a Protocol with no
  wrapper.

## AR-4 Packages that are not ports

**Direction.** Observability and helpers are ordinary packages: logging has no vendor to adapt
and no second implementation, and helpers compose port calls without being scheduled.

**Details.**

- **AR-D17** There is no log port. `observability/` imports stdlib `logging` and `core.types`
  only. Every package may import it except `core/`, which stays side-effect free.
- **AR-D18** Archived logs are transported by `ArchiveClient`. The JSONL record schema is the
  contract; changing it breaks the merge in `orchestrator/`.
- **AR-D19** Context fields travel in a `ContextVar` set by a logging filter, not as a
  parameter. It is the one place ambient passing is accepted, because the context carries no
  capability (ADR-0020 OP-D23).
- **AR-D20** Reusable, object-agnostic, scale-agnostic functions that compose port calls live
  in `generalization/helpers/`, one module per subject: `lines`, `polygons`, `points`,
  `topology`, `attributes`, `extents`. They are called only from inside operations, never
  named in a stage and never scheduled.
- **AR-D21** Membership is mechanical: a helper is not decorated with `@operation`. The
  subject axis is declared, not emergent.
- **AR-D22** `operations/shared/` holds operations shared between objects. It is not a
  helpers package: a helper composes port calls and is never scheduled, a shared operation is
  declared in a stage like any other.

## Rejected

- **AR-R1** Repository and Unit of Work. No transactional aggregate store: the datasets the
  adapters read and write are the store, whatever their format, and the pod is the unit of
  work. Reopened by a transactional store behind a port.
- **AR-R2** The application-layer patterns: entities and aggregates, a service layer above
  operations, a message bus with domain events and CQRS. Feature classes on disk are not
  object graphs; operations are the use cases; one sequential executor and one writer per
  object. Reopened by concurrency within a pod, a second writer per object, or a
  request-serving use; any of these changes Direction 1. Nothing reopens entities.
- **AR-R5** A formal primary port. One driving actor, Kubernetes via the orchestrator. The
  CLI, the pod entry points and the invariance harness are driving adapters, not further
  actors; a Protocol around one caller is ceremony. Reopened by a second driving actor that
  needs a call shape the pod entry points do not offer.
- **AR-R6** `ABC` ports. The adapter must subclass the port, so the arrow points both ways;
  one inherited interface grows past its callers. Reopening this changes Direction 4.
- **AR-R7** A log port. It fails the port test on every clause: stdlib, no vendor to adapt,
  no second implementation foreseeable. Reopened by a log transport stdlib handlers cannot
  reach.
- **AR-R8** Other names for the helpers package: `tools/`, `toolkit/`, `composites/`. "Tool"
  is retired and collides with port methods and arcpy tools; "composite" is
  multipart-geometry vocabulary here. Reopened by the terminology retiring the collision:
  `tool` leaving the retired-words list, or multipart geometry leaving the vocabulary. The
  rename itself is one `git mv` and one `.importlinter` line.
