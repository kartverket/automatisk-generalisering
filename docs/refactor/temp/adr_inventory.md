# ADR inventory (pass 1 working document)

**Status:** working document for the ADR consolidation, 2026-10-21. Not an ADR. Deleted with
`docs/refactor/` or earlier, once the cut-over (pass 4) has landed. Nothing here is decided by
being written here: Direction lines are drafts awaiting approval as exact text in pass 2, detail
placements are proposals for the pass 2 change summaries, and Rejected candidates are proposals
for pass 3.

**Source codes used below.** `00nn §X`: a passage of ADR-00nn, section X. `A n.m`: an A-item of
`DECISIONS.md`. `02 §x`, `03 §x`: a section of `02-runtime.md` or `03-architecture.md`.
`arch YYYY-MM-DD n`: an explicit decision of the architect, item n of that day's message.
`NEW`: traces to nothing; needs a decision before it can be written in.

**Lean test** (README): a detail stays if it constrains future code or design, or stops a likely
mistake; it goes if it only explains or reports how a decision was reached. **Rejected test**:
kept only if likely to be proposed again given the current design, with what would reopen it.
Placement column values: `Dir n` (folds into top-level Direction n), `Dir X-n` (folds into a
section Direction line), `detail`, `rejected`, `drop`, `cross-ref` (one line pointing at another
theme).

## 1. Themes and numbers

| ADR | prefix | theme | absorbs | reading order |
|---|---|---|---|---|
| ADR-0018 | AR | Architecture: the boundary, the ports and the packages | 0010, 0002, 0007, 0006, 0005 | 1 |
| ADR-0019 | PC | Port contract: what crosses a port | 0003, 0001, 0015, 0004; A2.1–A2.3 (landed), A4.1–A4.3 (to land) | 2 |
| ADR-0017 | RS | Row shape | unchanged; revised last for format | 3 |
| ADR-0020 | OP | Operations: declaration, injection and tuning | 0011, 0014, 0008, 0013; A1.3 (to land) | 4 |
| ADR-0021 | ST | Stages: identities, inputs and execution | 0012, 0016, 0009 | 5 |

Future themes from 0022: lineage ids (A9, A10, A24, A25), lineage mechanism (A11, A13, A15,
A16), cross-run lineage and retention (A21, A22, A23). Partition ownership (A6, A7, A8) joins
ADR-0021; A14.1 and A18 join ADR-0019. Agreed 2026-10-20.

Work order for pass 2: AR, PC, OP, ST, then RS.

## 2. Theme AR: Architecture

### 2.1 Draft top-level Direction

| n | draft text | source |
|---|---|---|
| 1 | Ports, adapters, composition roots, contract tests and fakes are adopted from ports-and-adapters. The store-oriented and application-oriented patterns of that literature are not: this is batch geoprocessing with one sequential executor, no requests and no transactional store. | 0010 §Context, §Decision |
| 2 | A port is a capability the core calls out through, defined by the conversation it carries and not by a library. Adapters are per vendor, and which adapter serves a port is chosen per port at the composition root. A port's implementation may call other ports. A capability outside the geoprocessing seam, such as graph algorithms over abstract topology, is its own port. | 03 §2 (port table, "conversation" column; §2.5 "numpy: a data structure, not a capability"); 03 §4.1 ("`runtime/` and `orchestrator/` are the only places that choose which adapter to instantiate"); 03 §4.3 (an adapter may consume other ports; the composition root wires it); 0006 §Context (the port test); arch 2026-10-21 items 3 and 5, revised 2026-10-21 (multi-library clause dropped) |
| 3 | The geoprocessing seam is split into `GeometryOps`, `TableOps` and `CartographicOps`: primitive dataset operations and schema and row work on one side, named ICA generalization operators on the other. Primitive operations have near one-to-one equivalents in other engines; cartographic operators have none and cost hundreds to thousands of lines each, so one port would block any non-arcpy adapter until every operator was rewritten. `CartographicOps` may be built on the other ports, never the reverse. | 0002 §Context, §Decision, §Consequences; 03 §2 ("Geoprocessing splits into three ports because the migration must be incremental"; `TableOps` is a different conversation); 03 §4.3 ("Ports must stay acyclic"); arch 2026-10-21 item 4 |
| 4 | Every port is a `typing.Protocol`. Conformance is structural and asserted statically; an adapter never inherits from a port. | 0007 §Decision, §Consequences |
| 5 | A port exists only for a distinct external capability with a foreseeable second implementation. Logging is not one: records are written with stdlib `logging`, transported by `ArchiveClient`, and the JSONL record schema is the contract. Helpers are not one: they compose port calls and are never scheduled. | 0006 §Context (the port test), §Decision, §Consequences; 0005 §Context; arch 2026-10-21 (logging settled) |

### 2.2 Sections and draft Direction lines

| section | draft Direction line | source |
|---|---|---|
| AR-1 What is adopted, and on what grounds | Adopted decisions rest on domain-specific grounds, not textbook ones, and are revisited on those grounds. | 0010 §Consequences, first sentence |
| AR-2 Ports and adapters | A port is a conversation the core has with an engine; the composition root decides, per port, which adapter carries it. | 03 §2 table; 03 §4.1; 03 §4.4 |
| AR-3 Ports are Protocols | Conformance is structural, asserted statically and never by inheritance, so the dependency arrow points one way. | 0007 §Consequences |
| AR-4 Packages that are not ports | Observability and helpers are ordinary packages: logging has no vendor to adapt and no second implementation, and helpers compose port calls without being scheduled. | 0006 §Consequences; 0005 §Context |

### 2.3 Decisions from the old ADRs

| from | decision | source | placement | note |
|---|---|---|---|---|
| 0010 | Adopt ports, adapters, composition roots, contract tests, fakes; reject store and application patterns | §Decision | Dir 1 | |
| 0010 | Literature assumes request-serving app with transactional store; this system has none of it | §Context | Dir 1 | folded as the reason clause |
| 0010 | Repository and Unit of Work rejected: geodatabase is the store, pod is the unit of work | §Decision table | rejected | likely proposed by a reader of the textbook; reopen: NEW |
| 0010 | DDD entities and aggregates rejected: domain objects are feature classes on disk | §Decision table | rejected | reopen: NEW |
| 0010 | Service layer above operations rejected: operations are the use cases | §Decision table | rejected | reopen: NEW |
| 0010 | Message bus, domain events, CQRS rejected: one sequential executor, one writer per object | §Decision table | rejected | reopen: NEW |
| 0010 | Formal primary port rejected: one driving actor, no plan for a second | §Decision table; 03 §4.5 | rejected | reopen: NEW |
| 0010 | Ports split by measured call-site frequency, not "one reason to change"; boundary tracks a vendor surface, not a use case | §Consequences | detail | stops a likely mistake (SRP applied to ports) |
| 0010 | Ports are coarse; ISP does not apply because every operation may use any method and all adapters are constructed together; Q-B is settled by measurement | §Consequences | detail | merged with 0007's PEP 544 point |
| 0010 | Fakes over mocks: real dependency is licensed, Windows-adjacent, slow | §Consequences | detail | constrains tests |
| 0010 | K-invariance harness is the most valuable correctness mechanism and not a hexagonal artifact | §Consequences | drop | commentary; the constraint below survives |
| 0010 | `tests/invariance/` is a driving adapter | §Consequences; 03 §4.5 | detail | constrains the driving side |
| 0010 | "A future reader who notices the missing Repository should read this" | §Consequences | drop | the Rejected entry carries it |
| 0002 | Three geoprocessing ports: `GeometryOps`, `TableOps`, `CartographicOps` | §Decision | Dir 3 | method-count estimates dropped; 03 §2 keeps them |
| 0002 | Cartography is 78 of 2801 call sites across 16 tools; each member costs hundreds to thousands of lines | §Context | Dir 3 (cost clause) | the counts themselves drop; 04-migration Appendix A keeps them |
| 0002 | Migration order: `TableOps`, then `GeometryOps`, then cartographic operators one at a time, each written against the other ports | §Consequences | detail | constrains future work |
| 0002 | One port rejected: all-or-nothing cutover | §Consequences | Dir 3 | arch 2026-10-21 item 4: one statement, no Rejected entry |
| 0002 | `CartographicOps` will hold thick implementations that adapt nothing; those move to `cartography/`; the port must not name arcpy concepts | §Consequences; 03 §4.3 | detail | constrains port vocabulary |
| 0002 | An operation may need several ports; see Toolbox | §Consequences | cross-ref | ADR-0020 OP-3 |
| 0002 | Whether `CartographicOps` splits per operator is Q-B, deferred until one operator is reimplemented | §Consequences | detail | open point, by subject and Q-id |
| 03 §2 | `GraphOps`: graph algorithms over abstract topology, its own port; Q-C (does it know about datasets) is open | 03 §2 table, §2.5, §9 | detail | worded per arch 2026-10-21 item 3 |
| 03 §2 | `TableOps` separates from `GeometryOps`: a different conversation (schema and rows), applies to non-spatial tables, `GeometryOps.add_field()` reads wrong | 03 §2 | detail | |
| 03 §4.1 | Only `runtime/` and `orchestrator/` choose which adapter to instantiate, per port; `runtime/compose.py` takes port instances, never an adapter name | 03 §4.1 | detail | arch 2026-10-21 item 5, confirmed 2026-10-21 |
| 03 §4.3 | An adapter may consume other ports: it is a client of those contracts, not of their implementations, and the composition root wires it | 03 §4.3 | detail | arch 2026-10-21 |
| 03 §2.5 | Domain code manipulates `Geometry`; adapters implement it with shapely, GEOS or arcpy geometry | 03 §2.5 | detail | also cited by PC-4 |
| 0007 | Every port is a `typing.Protocol` | §Decision | Dir 4 | |
| 0007 | Conformance: `if TYPE_CHECKING:` assignment at the bottom of each adapter module plus one adapter × port matrix in `tests/static/` covering the fakes | §Decision | detail | contract |
| 0007 | ABC rejected: adapter imports and subclasses the port, arrow both ways; one interface everybody inherits | §Consequences | rejected | likely proposed by a newcomer; reopen: NEW |
| 0007 | Six-method `ArchiveClient` with two callers | §Context | drop | history |
| 0007 | Third-party clients and plain dataclass test doubles satisfy a Protocol with no wrapper | §Consequences | detail | stops a likely mistake |
| 0007 | No runtime enforcement: `@runtime_checkable` plus `isinstance` checks names only | §Consequences | detail | stops a likely mistake |
| 0007 | PEP 544 caution on large protocols; `GeometryOps` is that shape, accepted; substance of Q-B | §Consequences | detail | merged with 0010's ISP point |
| 0006 | No `LogPort`; `observability/` imports stdlib `logging` and `core.types` only; archived logs via `ArchiveClient` | §Decision | Dir 5 + detail | arch settled 2026-10-21 |
| 0006 | Fails the port test on every clause | §Consequences | rejected (LogPort) | reopen: a log transport stdlib handlers cannot reach (arch 2026-10-21) |
| 0006 | `observability/` is a horizontal leaf; every package may import it except `core/` | §Consequences; 03 §4.1 | detail | constrains imports |
| 0006 | Context fields travel in a `ContextVar` set by a logging filter; the one accepted ambient passing, because it carries no capability | §Consequences | detail | cross-ref OP-3 |
| 0006 | JSONL record schema is the contract; changing it breaks the merge in `orchestrator/` | §Consequences | detail | arch settled 2026-10-21 |
| 0005 | Package name `helpers/`, subject axis: `lines`, `polygons`, `points`, `topology`, `attributes`, `extents` | §Decision | detail | package is `ag/generalization/helpers/` in `src/` |
| 0005 | Reusable, object-agnostic, scale-agnostic functions composing port calls; called only from operations, never named in a stage, never scheduled | §Context | Dir 5 + detail | |
| 0005 | Membership is a mechanical test: not decorated with `@operation`; the subject axis is declared, not emergent | §Consequences; 0011 §Consequences (corrected test) | detail | stated as current fact, no "corrected" |
| 03 §5 | Promotion rule for helpers | 03 §5 | drop | stays in 03 §5, not copied into an ADR (arch 2026-10-21); the `helpers/__init__.py` docstring's citation of 0005 for it is repointed to 03 §5 at the cut-over |
| 0005 | Rename cost is one `git mv` plus one `.importlinter` line | §Consequences | drop | reassurance, no constraint |
| 0005 | `tools/`, `toolkit/` rejected: "tool" is retired, collides with port methods and arcpy tools | §Consequences | rejected | likely; reopen: NEW |
| 0005 | `composites/` rejected: collides with composite and multipart geometry | §Consequences | rejected | plausible; reopen: NEW |
| 0005 | `subroutines/`, `techniques/` rejected | §Consequences | drop | unlikely to be proposed again (proposal; pass 3) |
| 0005 | `operations/shared/` rejected: reserved for operations shared between objects | §Consequences; 02 §6.1 | rejected | likely confusion; reopen: NEW |
| 0005 | Closes Q-A | header | drop | 03 §9 keeps "Q-A closed", repointed |

### 2.4 Open ideas carried in this theme (not decisions)

- **Per-stage or per-operation adapter choice.** Operations do not build Toolboxes; one is
  assembled at the composition root and injected (decided, OP-3). Choosing different adapters
  per operation, as a default `Toolbox` with per-stage or per-operation overrides at the
  composition root and never in operation code, is **not decided**. Recorded here as an open
  idea (arch 2026-10-21). If it is ever decided, it is an AR-2 or OP-3 detail.

### 2.5 Approved text for ADR-0018 (pass 2, 2026-10-21)

Status, Scope, Direction 1 to 5 and the section lines are approved as exact text. Details are
agreed as listed. This is the text pass 4 writes.

**Status:** Accepted, <cut-over date>.

**Scope:** `ag/ports/` as a package, `ag/adapters/`, `ag/generalization/helpers/`,
`ag/observability/`, the composition roots in `ag/runtime/` and `ag/orchestrator/`,
`.importlinter`, and the conformance matrix in `tests/static/`. No A-items.

**Direction.**

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

**AR-1 What is adopted, and on what grounds.** Direction: Adopted decisions rest on
domain-specific grounds, not textbook ones, and are revisited on those grounds.

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

**AR-2 Ports and adapters.** Direction: A port is a conversation the core has with an engine;
the composition root decides, per port, which adapter carries it.

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

**AR-3 Ports are Protocols.** Direction: Conformance is structural, asserted statically and
never by inheritance, so the dependency arrow points one way.

- **AR-D14** Conformance is asserted by an `if TYPE_CHECKING:` assignment at the bottom of
  each adapter module, and by one adapter × port matrix in `tests/static/` that covers the
  fakes.
- **AR-D15** There is no runtime enforcement: `@runtime_checkable` with `isinstance` checks
  method names only, not signatures.
- **AR-D16** Third-party clients and plain dataclass test doubles satisfy a Protocol with no
  wrapper.

**AR-4 Packages that are not ports.** Direction: Observability and helpers are ordinary
packages: logging has no vendor to adapt and no second implementation, and helpers compose
port calls without being scheduled.

- **AR-D17** There is no log port. `observability/` imports stdlib `logging` and `core.types`
  only. Every package may import it except `core/`, which stays side-effect free.
- **AR-D18** Archived logs are transported by `ArchiveClient`. The JSONL record schema is the
  contract; changing it breaks the merge in `orchestrator/`.
- **AR-D19** Context fields travel in a `ContextVar` set by a logging filter, not as a
  parameter. It is the one place ambient passing is accepted, because the context carries no
  capability (ADR-0020 OP-3).
- **AR-D20** Reusable, object-agnostic, scale-agnostic functions that compose port calls live
  in `generalization/helpers/`, one module per subject: `lines`, `polygons`, `points`,
  `topology`, `attributes`, `extents`. They are called only from inside operations, never
  named in a stage and never scheduled.
- **AR-D21** Membership is mechanical: a helper is not decorated with `@operation`. The
  subject axis is declared, not emergent.

**Rejected candidates for pass 3** (each once; reopen conditions in pass 3): AR-R1 Repository
and Unit of Work; AR-R2 DDD entities and aggregates; AR-R3 a service layer above operations;
AR-R4 message bus, domain events, CQRS; AR-R5 a formal primary port; AR-R6 `ABC` ports; AR-R7
a log port (reopen given: a log transport stdlib handlers cannot reach); AR-R8 `tools/`,
`toolkit/`; AR-R9 `composites/`. `operations/shared/` is a reservation (02 §6.1), not a
rejection; pass 3 decides whether it is an AR-4 detail instead.

**Design-document passages absorbed by this theme**, replaced at the cut-over by a pointer to
the ADR id, the document keeping only explanation that is not a rule: 03 §2 (the port table and
the split argument, AR-D5, AR-D6, AR-D12, Direction 3), 03 §4.1 (adapter choice, AR-D11), 03
§4.3 (port layering and thick adapters, AR-D9, AR-D10), 03 §4.5 (the driving side, AR-D4).

## 3. Theme PC: Port contract

### 3.1 Draft top-level Direction

| n | draft text | source |
|---|---|---|
| 1 | Every port method takes `ScratchHandle`. `DataObject` never appears in `ports/`, so an adapter sees no identity, classification or location and cannot branch on them. | 0003 §Decision, §Consequences |
| 2 | Selection is an immutable predicate value with a closed algebra. No mutable selection crosses a port, and nothing materialises until `select`. | 0001 §Decision, §Consequences |
| 3 | Attribute predicates are a closed set of structured leaves, evaluated in three values as SQL does. A raw expression is a counted escape hatch. | 0015 §Decision |
| 4 | No cursor crosses a port. Rows are read, written and updated in bulk, an update keyed on a stable id; expression updates are declarative; `Geometry` is an immutable value type. | 0004 §Decision; A4.2, A4.3; arch 2026-10-21 item 1 (text as suggested) |

### 3.2 Sections and draft Direction lines

| section | draft Direction line | source |
|---|---|---|
| PC-1 Handles at the boundary | Port signatures name `ScratchHandle`, the operation's view of data, never `DataObject`, the planner's. | 0003 §Context, §Decision |
| PC-2 Selection as a predicate | `GeometryOps` selects and counts with an immutable `Predicate`; add-to, remove-from and subset are `Or`, `And Not` and `And`, not a held selection. | 0001 §Decision, §Consequences |
| PC-3 Attribute leaves | The attribute leaf is a closed set of structured nodes built through constructors on `Attr`, a namespace and not a type; `Attr.raw` is the escape hatch and every call site is counted. | 0015 §Decision |
| PC-4 Row IO without a cursor | `TableOps` has no cursor: `calculate_field` declares an expression update, `read_rows` and `write_rows` move rows in bulk, `update_rows` writes back values computed in Python keyed on a stable id, and `Geometry` is the value they carry. | 0004 §Decision; A4.2, A4.3; arch 2026-10-21 item 1 |

### 3.3 Decisions from the old ADRs and the A-items

| from | decision | source | placement | note |
|---|---|---|---|---|
| 0003 | Every port method takes `ScratchHandle`; `DataObject` never in `ports/` | §Decision | Dir 1 | |
| 0003 | `DataObject` (`ExternalSource`, `ProductIdentity`, `Derived`) is what a stage declares; graph, classification and pinning are computed over it; `ScratchHandle` is a named slot in the pod scratch root with no identity and no location | §Context; 0012 §Consequences (the three types) | detail | stated as current fact |
| 0003 | A `DataObject` parameter would drag identity, classification and pinning into every adapter; an adapter would need the registry to resolve a location | §Consequences | drop | rationale; Dir 1 carries the constraint |
| 0003 | An operation sees no URI, no client, no partition index, no context radius; the rule extends unchanged to adapters | §Consequences; 02 §2.4 | detail | constraint; cited by ST-D (radius) |
| 0003 | An adapter cannot branch on where data came from; classification is computed at plan time | §Consequences | Dir 1 | folded |
| 0003 | `ports/` imports `core.handles`, `core.types`, `core.injection`, `core.errors` and nothing else in `ag`; never `core.pipeline` | §Consequences (stale list); `.importlinter` row 4; 03 §4.1 | detail | current rule stated, no "corrected" |
| 0001 | `select(input, where, output)` and `count(input, where) -> int` on `GeometryOps` | §Decision | detail | |
| 0001 | `Predicate` algebra: attribute leaves, `Spatial`, `And`, `Or`, `Not`; `&`, `\|`, `~` | §Decision | detail | |
| 0001 | `any()` not shipped: pays only where a backend short-circuits; `count(...) > 0` covers it | §Decision | rejected | likely proposed; reopen: a backend that short-circuits (0001's own clause) |
| 0001 | Held selection is arcpy's implementation; add-to is `Or`, remove-from `And Not`, subset `And` | §Consequences | Dir PC-2 | |
| 0001 | Exposing the handle would make every adapter emulate arcpy's statefulness | §Consequences | rejected (mutable selection handle) | plausible; reopen: NEW |
| 0001 | Tree maps onto CQL2 and a SQL `WHERE` | §Consequences; 03 §2 (vocabulary from CQL2) | detail | one line |
| 0001 | Lazier than a held selection; nothing materialises until `select` | §Consequences | Dir 2 | |
| 0001 | arcpy adapter pushes negation to leaves by De Morgan; internal `Negated` never crosses the port | §Consequences; 0015 §Consequences | detail | constrains adapter |
| 0001 | `CopyFeatures` is materialisation, surviving as the output write inside `select` | §Consequences | drop | migration mapping; 04-migration owns it; see NEW list item 3 |
| 0015 | Four constructors on `Attr`: `cmp`, `in_`, `is_null`, `raw`, with their rules | §Decision | detail (one per constructor) | contract |
| 0015 | Three-valued evaluation rules, verbatim | §Decision | detail | contract |
| 0015 | `LIKE` semantics | §Decision | detail | contract |
| 0015 | Type mismatch is `PortContractError` from the adapter | §Decision | detail | contract |
| 0015 | No Python truth value; connective has at least two terms | §Decision | detail | contract |
| 0015 | Leaves are frozen dataclasses `Compare`, `IsIn`, `IsNull`, `RawAttr`; alias names the closed set; algebra in `ports/predicates.py` beside the column vocabulary | §Decision | detail | contract |
| 0015 | Adapters compile four leaf shapes plus raw, quoting identifiers per workspace type, never parsing; in-memory adapter evaluates in Python, raises on `RawAttr` | §Consequences | detail | constrains adapters |
| 0015 | Wrong field name not checked; schema declarations on handles are a stated non-goal | §Consequences; A2.3 | detail | |
| 0015 | `Attr(cql: str)` as the only leaf rejected: every adapter parses; admits uncompilable expressions | §Context | rejected | plausible; reopen: NEW |
| 0015 | Three template expressions rewritten; subqueries become `read_rows` plus `Attr.in_` | §Consequences | drop | history; the target form survives as a detail under PC-4 (deletion) |
| 0015 | Amends ADR-0001 | header | drop | |
| 0004 | No cursor; `calculate_field`, `read_rows`, `write_rows` | §Decision | Dir 4 + detail | |
| 0004 | `Geometry` value type: kind, coordinates, CRS; yielded by `read_rows`, accepted by `write_rows` | §Decision | detail | |
| 0004 | Vectorized engines; a cursor port guarantees a bad second adapter | §Consequences | rejected (a cursor or row iterator) | likely proposed under migration pressure; reopen: NEW |
| 0004 | 483 cursor sites, cost accepted | §Context, §Consequences | drop | reporting |
| 0004 | Row-level geometry algorithms survive; conversion at the adapter boundary near-mechanical | §Consequences; 03 §2.5 | detail | as "domain code manipulates `Geometry`; adapters convert" |
| 0004 | `_GeneratedLineRecord` disappears | §Consequences | drop | history |
| A4.1 | `SearchCursor` to `read_rows`, `insertRow` to `write_rows`, `deleteRow` to `select` with a negated predicate | A4.1; arch 2026-10-21 | detail (the bulk mapping; there is no delete method, deletion is `select` with a negated membership predicate) | the per-method counts go to 04-migration Appendix A with their `rg` commands; they count cursor method calls, not constructions, so they do not sum to the 483 there |
| A4.2 | `updateRow` sites are the real constraint; `CalculateField` covers the expression-only case; side table plus `join_field` costs a full write plus a join | A4.2 | Dir 4; rejected (side table plus join) | reopen: NEW |
| A4.3 | `update_rows(input, key, fields, rows)`: bulk, keyed, no iteration protocol, writes M changed rows, must allow `Row.geometry`, requires a stable key which `lineage_id` provides | A4.3 | detail | contract |

### 3.4 Approved text for ADR-0019 (pass 2, 2026-10-21)

Status, Scope, Direction 1 to 4 and the section lines are approved as exact text (Direction 1
and PC-1 in the architect's revised form). Details are agreed as listed, including PC-D4, PC-D7
and PC-D24. This is the text pass 4 writes.

**Status:** Accepted, <cut-over date>.

**Scope:** The values and method contracts of `ag/ports/`: handles at the boundary,
`ports/predicates.py`, `ports/attributes.py`, `ports/geometry.py`, and row IO on `TableOps`.
Absorbs A2.1, A2.2 and A2.3; A4.1, A4.2 and A4.3 land here. The method contracts for parents
capability and single-part dissolve (A14.1, A18) join when they migrate. Row shape is
ADR-0017.

**Direction.**

1. A port method that takes a dataset takes it as a `ScratchHandle`. `DataObject` never
   appears in `ports/`, so an adapter sees no identity, classification or location of a
   dataset and cannot branch on them.
2. Selection is an immutable predicate value with a closed algebra. No mutable selection
   crosses a port, and a predicate materialises nothing until it is applied.
3. Attribute predicates are a closed set of structured leaves, evaluated in three values as
   SQL does. A raw expression is a counted escape hatch.
4. No cursor crosses a port. Rows are read, written and updated in bulk, an update keyed on a
   stable id; expression updates are declarative; `Geometry` is an immutable value type.

**PC-1 Handles at the boundary.** Direction: Port signatures name a dataset by
`ScratchHandle`, the operation's view of data, never by `DataObject`, the planner's.

- **PC-D1** `DataObject` (`ExternalSource`, `ProductIdentity`, `Derived`) is what a stage
  declares; the dependency graph, classification and pinning are computed over it.
  `ScratchHandle` is what an operation receives: a named slot in the pod scratch root, with no
  identity and no location.
- **PC-D2** An operation sees no URI, no client, no partition index and no context radius, and
  the rule extends unchanged to adapters. An adapter resolves no location and sees no
  classification; classification is computed at plan time.
- **PC-D3** `ports/` imports only the `core` modules that `.importlinter` row 4 allows, and
  never `core.pipeline`.
- **PC-D4** Port parameters are keyword-only, with the unit in the name (`width_m`,
  `tolerance_m`). Options are project enums, never vendor strings or bare booleans.

**PC-2 Selection as a predicate.** Direction: A selection is an immutable predicate: adding
to, removing from and subsetting a selection are disjunction, conjunction with a negation, and
conjunction, never a held selection.

- **PC-D5** `GeometryOps` exposes `select(input, where, output)` and
  `count(input, where) -> int`.
- **PC-D6** `Predicate` is an immutable algebra: the attribute leaves of PC-3, `Spatial`,
  `And`, `Or` and `Not`, built with `&`, `|` and `~`.
- **PC-D7** `Spatial(relate_to, relation, distance_m)` names a handle as a value; `Relation`
  carries the CQL2 relation names, and `DWithin` and `Intersects` are constructors over it.
  Which handles a predicate may name is open.
- **PC-D8** The tree maps onto OGC CQL2 and onto a `WHERE` clause in a SQL adapter.
- **PC-D9** An adapter whose engine inverts only at a leaf pushes negation to the leaves by
  De Morgan inside the adapter; its internal negated node never crosses the port.

**PC-3 Attribute leaves.** Direction: The attribute leaf is a closed set of structured nodes
built through constructors on a namespace, not a type, and the raw escape hatch is counted.

- **PC-D10** `Attr` is a namespace, not a type, with four constructors: `cmp`, `in_`,
  `is_null` and `raw`.
- **PC-D11** `Attr.cmp(field, op, value)`: `op` is one of `=`, `<>`, `<`, `<=`, `>`, `>=` and
  `LIKE`; `value` is an attribute value other than `None`. A comparison with NULL is refused
  at construction and goes through `Attr.is_null`.
- **PC-D12** `Attr.in_(field, values)`: the values are kept as a tuple, `None` is refused, and
  the empty set is legitimate and matches no row.
- **PC-D13** `Attr.is_null(field)`: `field IS NULL`.
- **PC-D14** `Attr.raw(cql)`: a CQL2 text expression compiled as written. A static test pins
  the count of call sites in the package, so adding one is a deliberate edit to that test.
- **PC-D15** Every adapter evaluates a predicate in three values: TRUE, FALSE or UNKNOWN per
  row, and `select` keeps the rows where it is TRUE. `Compare` and a non-empty `IsIn` are
  UNKNOWN when the field is NULL; the empty `IsIn` is FALSE for every row; `IsNull` is never
  UNKNOWN; `Spatial` is UNKNOWN for a row with a null geometry; `Not` of UNKNOWN is UNKNOWN;
  `And` is FALSE if any term is FALSE and otherwise UNKNOWN if any term is; `Or` is the
  mirror. `~Attr.in_(f, ids)` excludes the NULL rows; a caller that wants them writes
  `~Attr.in_(f, ids) | Attr.is_null(f)`.
- **PC-D16** `LIKE` takes a string pattern, `%` for any run of characters and `_` for one,
  matched case-sensitively with no escape character; a literal `%` or `_` goes through
  `Attr.raw`.
- **PC-D17** A value whose type does not match the field's type is a `PortContractError`
  raised by the adapter, so an engine's coercion and a Python comparison can never disagree.
- **PC-D18** A predicate has no truth value in Python: `and`, `or` and `not` raise. A
  connective has at least two terms.
- **PC-D19** The leaves are frozen dataclasses `Compare`, `IsIn`, `IsNull` and `RawAttr`, so
  an adapter pattern-matches them exhaustively, and a type alias names the closed set. The
  algebra lives in `ports/predicates.py` beside the column vocabulary, because two ports take
  predicates and a Protocol file stays the contract.
- **PC-D20** An adapter compiles four leaf shapes plus the raw string, quoting identifiers for
  its workspace type; it never parses. The in-memory adapter evaluates the three-valued rule
  in Python and raises `PortContractError` on `RawAttr`.
- **PC-D21** Structure and value types are checked when a leaf is built, at import for a
  declaration module. A wrong field name is not: that needs schema declarations on handles, a
  stated non-goal.

**PC-4 Rows without a cursor.** Direction: Expression updates are declared, rows move in
bulk, and a bulk update is keyed on a stable id and may carry geometry.

- **PC-D22** `TableOps` has no cursor. `calculate_field(input, field, expression)` declares an
  expression update; `read_rows(input, fields) -> Iterable[Row]` reads in bulk;
  `write_rows(output, schema, rows)` writes in bulk; `update_rows(input, key, fields, rows)`
  writes back rows computed in Python, keyed on a stable id, with no iteration protocol,
  writing the changed rows and not every row, and may carry `Row.geometry`. The key must be
  stable; `lineage_id` provides one.
- **PC-D23** There is no delete method. Deletion is `select` with a negated membership
  predicate.
- **PC-D24** The bulk mapping: a search cursor becomes `read_rows`; an insert cursor becomes
  `write_rows`; an update cursor becomes `calculate_field` where an expression suffices and
  `update_rows` where values are computed in Python.
- **PC-D25** `ports/geometry.py` defines an immutable `Geometry` value type: geometry kind,
  coordinate sequence, CRS. `read_rows` yields it and `write_rows` accepts it. Domain code
  manipulates `Geometry`; adapters implement it with shapely, GEOS or arcpy geometry and
  convert at the boundary.

**Rejected candidates for pass 3** (each once): PC-R1 `any()` on the port (reopen given: a
backend that short-circuits); PC-R2 a mutable selection handle at the port; PC-R3 a text
expression as the only attribute leaf; PC-R4 a cursor or row iterator in the port; PC-R5 a side
table plus a join for computed updates.

**Design-document passages absorbed by this theme**, replaced at the cut-over by a pointer to
the ADR id: 03 §2.3 (contract shape: the `ScratchHandle` bullet, the enum rule and the keyword
rule, PC-D1, PC-D4), 03 §2.4 (selection is a predicate value, `count` and `any()`, the leaf
shapes, PC-D5 to PC-D9), 03 §2.5 (shapely under `Geometry`, PC-D25), 03 §3.1 (no cursor and
the mapping table, PC-D22, PC-D24), 03 §3.2 (the `Geometry` value type, PC-D25), 02 §2.4 (the
operation sees no URI, client, partition index or radius, PC-D2).

### 3.5 Inherited errors found in the remaining themes (checked against `src/` on 2026-10-21)

Sentences true when the old ADR was written and false for the design as it stands. Each is a
detail correction unless marked otherwise; the corrected wording is used in the pass 2 text.

| theme | old sentence | evidence | correction |
|---|---|---|---|
| OP | 0011: `@operation` returns `Callable[P, OperationCall]` | `src/ag/core/operations.py:116-147`: it returns an `OperationDeclaration[P]`, a class whose `__call__` has the function's parameter list and returns an `OperationCall`; `signature.bind` runs in `__call__`, at the declaration site | detail: OP-D2 states the class; the `P` argument of 0014 (a sentinel default is forced because the declaration site shares the parameter list) still holds |
| OP | 0011: direction is carried by `In` / `Out` annotations; 0014's kinds table likewise | `src/ag/core/handles.py:4`: four markers, `In`, `Out`, `Mutates`, `ParentsOut`; ADR-0017 RS-D11 | detail: the handle markers are four; every handle parameter carries exactly one |
| OP | 0011: three mechanisms, all in `core/operations.py` | `ScratchHandle`, the markers, `ScratchScope` and `INJECTED` are in `core/handles.py`; `Injected` in `core/injection.py`; `@operation` and `OperationCall` in `core/operations.py` | detail: modules named as they are |
| OP | 0011: `wants_scratch` from the presence of a `ScratchScope` parameter | `operations.py:93`: a property over the injected mapping | detail: already the 0014 form |
| OP | 0014: `Toolbox`'s four fields are typed by the six port Protocols | `ports/toolbox.py:3`: the four processing ports; `ArchiveClient` and `ClusterClient` are not in it | Rejected wording only (OP-R4) |
| OP, document | 04-migration line 50: road-specific values to `pipelines/road/tuning/n100.py` | 0013 and the fixture layout: `operations/road/tuning/n100.py` | not an ADR error; 04-migration corrected at the cut-over (checklist) |
| ST | none false. 0012 and 0016 name `core/pipeline.py`, `data_objects`, `locations.py`, `policy` and `check_stage_tags_match_pipeline`, none lifted | all present in `template_code/ag/core/` and in the planned tree (03 §5); the fixture's `StageInput(obj=, handle=, role=)` matches 0012 | the ADR states the design; no correction |

The Architecture and Port contract themes were checked the same way on approval: the three-port
count (AR-D5), the import list (PC-D3), the `DataObject` enumeration (PC-D1) and
"every port method takes `ScratchHandle`" (Direction 1) were the inherited errors there, and
are corrected in the approved text.

## 4. Theme OP: Operations

### 4.1 Draft top-level Direction

| n | draft text | source |
|---|---|---|
| 1 | An operation's declaration is its signature. `@operation` reads the name, the handle directions and the parameter kinds from it at import, and nothing is restated as a string. | 0011 §Decision |
| 2 | An identifier the program must match is a symbol. A value that names something outside the program stays a literal. | 0011 §Context (the test) |
| 3 | The runtime supplies the parameters a declaration site must not. They are recognised by the `Injected` marker base class, never by name, and each carries a sentinel default. | 0014 §Decision |
| 4 | Ports reach an operation as one explicit, frozen `Toolbox`, assembled at the composition root. A helper receives it explicitly, as a parameter or through a constructor, never ambiently. | 0008 §Decision; 03 §4.4; A1.3; arch 2026-10-21 item 2 and settled note |
| 5 | Tuning is one frozen config dataclass per operation, valued as a base plus exactly one scale delta, with no resolution mechanism and no scale in the config. | 0013 §Decision |

### 4.2 Sections and draft Direction lines

| section | draft Direction line | source |
|---|---|---|
| OP-1 The declaration is the signature | `@operation` type-checks the declaration site against the real signature and classifies every parameter at decoration; a declared handle takes its name and namespace from the class attribute it is bound to. | 0011 §Decision |
| OP-2 Injected parameters | A marker base class in `core/`, inherited by the injected types, lets `@operation` recognise what the runtime supplies without `core/` naming anything in `ports/`. | 0014 §Decision |
| OP-3 The toolbox | A frozen `Toolbox` bundling the ports is assembled at the composition root and passed explicitly to every operation; a helper receives it explicitly, as a parameter or through a constructor, never ambiently. | 0008 §Decision; A1.3; arch 2026-10-21 item 2 (text as suggested) |
| OP-4 Config and tuning | Config fields live beside the operation because they change with it; values live in tuning modules because they change per scale; base plus exactly one delta, read, not resolved. | 0013 §Decision |

### 4.3 Decisions from the old ADRs and the A-items

| from | decision | source | placement | note |
|---|---|---|---|---|
| 0011 | The identifier-or-value test | §Context | Dir 2 | |
| 0011 | Hand-written factory twins and module-level handle constants: what the design had before | §Context | drop | history; not a plausible re-proposal once the decorator exists |
| 0011 | `WorkFileManager` and `PartitionInputConfig` in the legacy code | §Context | drop | 04-migration owns the legacy inventory |
| 0011 | `@operation`: `Callable[P, OperationCall]`, `In`/`Out` carry direction, name from `fn.__name__`, `signature.bind` at declaration | §Decision | detail | `wants_scratch` now derives from the injected mapping (0014) |
| 0011 | `ScratchHandle.__set_name__` gives name and namespace | §Decision | Dir OP-1 + detail | |
| 0011 | Internal scratch names stay literals | §Decision | detail | |
| 0011 | `Derived("...")` stays a literal; uniqueness is a check; a symbol would let a rename move a live object's run-scratch location | §Decision | detail | stops a likely mistake |
| 0011 | Failures move to import: the list | §Consequences | detail | contract |
| 0011 | Two checks deleted (`check_handle_names_unique_per_stage`, `check_sources_agree`) | §Consequences | drop | history |
| 0011 | `namespace` participates in equality; `Stage.handles` plus `check_stage_uses_own_handles` catch borrowed handles | §Consequences | detail | contract |
| 0011 | `__set_name__` rather than `__init_subclass__`; `Handles` is a readability marker nothing depends on | §Consequences | detail | stops a likely mistake (depending on the base) |
| 0011 | Introspection once at import; entry point dispatches by splat, inspecting nothing | §Consequences | detail | |
| 0011 | Configs one frozen dataclass named `config`, enforced at decoration | §Consequences | OP-4 | |
| 0011 | Stale parentheticals in 0003 and 0005 | §Consequences | drop | applied as current facts in AR and PC |
| 0011 | Composition dataclass for IO rejected: position is an unnamed identifier; three levels of nesting; config half adopted | §Rejected | rejected | likely ("make operations classes"); reopen: substitutability per scale (0011's own clause) |
| 0014 | Parameter kinds: `In`/`Out` by marker, `config` by name, injected by marker, anything else rejected | §Context table, §Decision | detail | contract |
| 0014 | `core/` may not import `ports/`; the cycle | §Context | Dir OP-2 | folded as the clause |
| 0014 | `Injected` in `core/injection.py`, stdlib-only; `ScratchScope` and `Toolbox` inherit; arrow `ports → core` | §Decision | detail | |
| 0014 | `isinstance(hint, type) and issubclass(hint, Injected)`; guard load-bearing because `In`/`Out` are `Annotated` | §Decision | detail | stops a likely mistake |
| 0014 | `get_type_hints` resolves in the operation module's namespace; future annotations change nothing | §Decision | drop | explains why it works; proposal, pass 2 may keep one clause |
| 0014 | Sentinel defaults `INJECTED`, `NOT_INJECTED`; passing one at a declaration site rejected; default forced by `Callable[P, OperationCall]` | §Decision | detail | contract plus one reason clause |
| 0014 | `NOT_INJECTED` is one `cast` over one object whose `__getattr__` raises, naming the port | §Decision | detail | |
| 0014 | `Toolbox \| None = None` rejected | §Decision | rejected | 0014: "recorded so it is not re-proposed"; reopen: NEW (nothing) |
| 0014 | `OperationCall.injected: Mapping[type[Injected], ParamName]`; `core/` never names `Toolbox`; adding a kind changes nothing in `core/`; the parameter name is not load-bearing | §Decision | detail | the template bug story drops |
| 0014 | `wants_scratch` is a property over the mapping; no `wants_toolbox` | §Decision | detail | |
| 0014 | Two parameters of one injected kind rejected at decoration | §Decision | detail | |
| 0014 | Adding a kind is inheriting; rejection message distinguishes the two cases; `core/injection.py` exists to be imported upward | §Consequences | drop | first clause folds into the mapping detail; rest is commentary |
| 0014 | `NOT_INJECTED` re-exported from `ports/__init__.py` with the operation-facing vocabulary | §Consequences | detail | contract |
| 0014 | `core-is-pure` contract unchanged | §Consequences | Dir OP-2 | |
| 0014 | Classify by parameter name rejected: the `config` precedent does not transfer | §Rejected | rejected | likely (cheap); reopen: NEW (nothing) |
| 0014 | Move `Toolbox` into `core/` rejected: drags `ports/` in; `TYPE_CHECKING` plus string compare fails at runtime | §Rejected | rejected | plausible; reopen: NEW (nothing) |
| 0014 | Extends ADR-0011 | header | drop | |
| 0008 | Frozen `Toolbox` bundling `geometry`, `table`, `cartographic`, `graph`, assembled once by the pod entry point, passed explicitly | §Decision; 03 §4.4 | Dir 4 + detail | |
| 0008 | `ScratchScope` is already explicit and derived downward into helpers; two styles in one signature is worse than either | §Consequences; 02 §2.4 | detail | as "`Toolbox` and `ScratchScope` are passed the same way" |
| 0008 | Tests stay stateless: a fake `Toolbox` is constructed and passed | §Consequences | detail | constrains tests |
| 0008 | One parameter rather than four | §Consequences | drop | rationale |
| 0008 | Observability context in a `ContextVar` is the exception; carries no capability | §Consequences | cross-ref | AR detail |
| 0008 | Revisit if the parameter proves worse once real operations exist | §Consequences | rejected (singleton) reopen clause | |
| 0008 | Module-level singleton rejected | §Context | rejected | reopen: 0008's revisit clause |
| A1.3 | Singleton would prevent two pipelines running different adapters in one process (the incremental-port path); large tools bind `tb` and `scratch` once in a plain class constructor, not through forty signatures | A1.3 | Dir 4; detail; strengthens the singleton Rejected entry | sweep row below |
| 0008 | Closes Q-E | header | drop | 03 §9 keeps it |
| 0013 | One frozen config dataclass per operation, parameter named `config`, enforced at decoration; fields beside the operation, values in tuning modules | §Decision | Dir 5 + detail | |
| 0013 | Layout tree: operations with config classes, `tuning/` base and per-scale deltas, `tuning/scale/` shared constants | §Decision | detail | |
| 0013 | No resolution mechanism; sharing by referencing a constant | §Decision | detail; rejected (a layered resolver) | reopen: NEW (nothing) |
| 0013 | Base plus exactly one delta | §Decision | detail | |
| 0013 | No defaults on config fields; a scale is a `replace` diff | §Decision | detail | |
| 0013 | Scale constants named after the cartographic concept | §Decision | detail | |
| 0013 | No `scale` field; an operation cannot know its scale | §Decision, §Consequences | detail | merged |
| 0013 | Legacy `ThinRoadNetworkKwargs` mixing IO, plumbing, tuning | §Context | drop | 04-migration |
| 0013 | `OperationCall.parameters` uniformly `{"config": ...}` or empty; manifest via `dataclasses.asdict` | §Consequences | detail | contract |
| 0013 | `__post_init__` is where a value constraint goes | §Consequences | detail | |
| 0013 | Wrong config is a pyright error at the call site | §Consequences | drop | property, no constraint (proposal) |
| 0013 | Shared sub-config earns nesting, one level; `NetworkWeightsConfig` example | §Consequences | detail | |
| 0013 | A third layer is a signal to promote to `tuning/scale/` | §Consequences | detail | |
| 0013 | Unchanged config re-exported, not omitted; `None` placeholder is a trap | §Consequences | detail | |
| 0013 | `dump_tuning.py` prints the resolved result as a read | §Consequences | drop | not lifted; dropped (arch 2026-10-21) |
| 0013 | Loose keyword tuning rejected | §Context | drop | not a plausible re-proposal (proposal; pass 3) |

### 4.4 Approved text for ADR-0020 (pass 2, 2026-10-21)

Status, Scope, Direction 1 to 5 and the section lines are approved as exact text. Details are
agreed as listed, with OP-D3 and OP-D17 in the architect's revised form. `Toolbox` stays in
OP-D19: the decision is one explicit, frozen bundle assembled at the composition root, not the
class name. This is the text pass 4 writes.

**Status:** Accepted, <cut-over date>.

**Scope:** `ag/core/operations.py`, `ag/core/handles.py`, `ag/core/injection.py`,
`ag/ports/toolbox.py`, the operation config classes and the tuning modules. No A-items; A1.3
lands here.

**Direction.**

1. An operation's declaration is its signature. The operation decorator reads the name, the
   handle directions and the parameter kinds from it at import, and nothing is restated as a
   string.
2. An identifier the program must match is a symbol. A value that names something outside the
   program stays a literal.
3. The runtime supplies the parameters a declaration site must not. They are recognised by a
   marker base class, never by name, and each carries a sentinel default.
4. Ports reach an operation as one explicit, frozen bundle assembled at the composition root.
   A helper receives it explicitly, as a parameter or through a constructor, never ambiently.
5. Tuning is one frozen config dataclass per operation, valued as a base plus exactly one
   scale delta, with no resolution mechanism and no scale in the config.

**OP-1 The declaration is the signature.** Direction: The decorator type-checks the
declaration site against the real signature and classifies every parameter at decoration; a
declared handle takes its name and namespace from the class attribute it is bound to.

- **OP-D1** The test: could a different string literal ever be correct here, given the rest
  of the code? If no, it is an identifier and must be a symbol. If yes, it names something
  outside the program and stays a literal.
- **OP-D2** `@operation` returns an `OperationDeclaration[P]`. Calling it with the declared
  keywords at a declaration site binds handles and a config and returns an `OperationCall`.
  Its parameter list is the function's, so the declaration site is type-checked against the
  real signature and go-to-definition lands on the implementation; the name is
  `fn.__name__`; `signature.bind` runs at the declaration site, when the pipeline module is
  imported.
- **OP-D3** An operation's handle parameters are `In` or `Out`, written with the signature,
  as `Annotated` aliases over `ScratchHandle` in `core/handles.py`. `Mutates` and
  `ParentsOut` belong to port methods (ADR-0017 RS-D11) and are rejected on an operation.
- **OP-D4** `ScratchHandle.__set_name__` gives a declared handle its `name` and `namespace`
  from the class attribute it is bound to. It fires in any class body, so a stage file that
  omits the `Handles` base still gets correct handles; `Handles` is a readability marker
  nothing depends on.
- **OP-D5** Internal scratch names stay literals: `scratch("dissolved")` names nothing a
  consumer must match.
- **OP-D6** `Derived("...")` stays a literal: declared once, `eq=False`, no consumer must
  match it. Pipeline-wide uniqueness is a check, not a naming mechanism; a symbol would let a
  rename move a live object's run-scratch location and invalidate the resume window.
- **OP-D7** Failures move to import: a misspelled keyword, a missing argument, a non-handle
  passed to a handle parameter, an undeclared handle, a non-frozen config and an injected
  argument passed by hand are `TypeError` while the pipeline module is imported, in CI or at
  orchestrator startup.
- **OP-D8** `namespace` participates in handle equality, so `Stage.handles` plus the
  own-handles check catch a handle borrowed from another stage.
- **OP-D9** Introspection happens once, at import. The entry point receives an
  `OperationCall` with plain mappings and dispatches by splat, inspecting nothing.

**OP-2 Injected parameters.** Direction: A marker base class in the core, inherited by the
injected types, lets the decorator recognise what the runtime supplies without the core naming
anything in the ports package.

- **OP-D10** Parameter kinds: handle parameters by their markers; `config` by the parameter
  name, because a config's type differs per operation and the name is the only handle
  available; injected kinds by subclassing `Injected`; anything else is rejected at
  decoration.
- **OP-D11** `core/injection.py` is stdlib-only and holds `Injected`. `ScratchScope` in
  `core/handles.py` and `Toolbox` in `ports/toolbox.py` inherit it; the arrow is
  `ports → core`, and the core-is-pure contract is unchanged.
- **OP-D12** The decorator classifies with `isinstance(hint, type) and issubclass(hint,
  Injected)`. The guard is load-bearing: the handle markers resolve to `Annotated[...]`,
  which is not a type.
- **OP-D13** Each injected type supplies a sentinel default, `INJECTED` for `ScratchScope`
  and `NOT_INJECTED` for `Toolbox`, and passing one at a declaration site is rejected. The
  default is forced because the declaration site shares the function's parameter list;
  without it every declaration site is a type error for omitting an argument it must not
  supply.
- **OP-D14** `NOT_INJECTED` is one `cast` over one object whose `__getattr__` raises, naming
  the port that was reached.
- **OP-D15** `OperationCall.injected: Mapping[type[Injected], ParamName]`, read at
  decoration. The core never names `Toolbox`; adding a kind changes nothing in the core; the
  parameter name is not load-bearing.
- **OP-D16** `wants_scratch` is a property over the mapping. There is no `wants_toolbox`.
- **OP-D17** Rejected at decoration: two parameters of one injected kind, the bare `Injected`
  base as an annotation, and a union containing an injected kind. (Source: the `@operation`
  contract in `core/operations.py`.)
- **OP-D18** `NOT_INJECTED` is re-exported from `ports/__init__.py` with the operation-facing
  vocabulary.

**OP-3 The toolbox.** Direction: A frozen bundle of the ports is assembled at the composition
root and passed explicitly to every operation; a helper receives it explicitly, as a parameter
or through a constructor, never ambiently.

- **OP-D19** `Toolbox` is the bundle: `geometry`, `table`, `cartographic` and `graph`, the
  four processing ports, as one frozen value assembled once by the pod entry point.
- **OP-D20** `Toolbox` and `ScratchScope` are passed the same way, explicitly, and derived
  downward into helpers.
- **OP-D21** A large tool binds `tb` and `scratch` once in a plain class constructor rather
  than threading them through many signatures: constructor injection, not ambient state.
- **OP-D22** Tests stay stateless: a fake `Toolbox` is constructed and passed, with no global
  to set or reset.
- **OP-D23** The observability context (ADR-0018 AR-D19) travels in a `ContextVar`. It
  carries no capability, so it is not a second dependency-passing style.

**OP-4 Config and tuning.** Direction: Config fields live beside the operation because they
change with it; values live in tuning modules because they change per scale; base plus exactly
one delta, read, not resolved.

- **OP-D24** One frozen config dataclass per operation, passed as the parameter named
  `config`, enforced at decoration.
- **OP-D25** Layout: the config classes beside the operations in `operations/<object>/`;
  `operations/<object>/tuning/__init__.py` holds the base configs with every field stated
  once; `tuning/<scale>.py` one `replace` delta each; `tuning/scale/<scale>.py` cartographic
  constants shared across objects.
- **OP-D26** No resolution mechanism: nothing walks object defaults, then scale defaults,
  then overrides. Sharing happens because a line of code references a constant.
- **OP-D27** Base plus exactly one delta: object base, then scale delta, and that is the end.
  Wanting a third layer is a signal to promote a value to a named constant in `tuning/scale/`.
- **OP-D28** No defaults on config dataclass fields. Every field is stated in the base; a
  scale is a `replace` diff.
- **OP-D29** Scale constants are named after the cartographic concept
  (`MINIMUM_VISIBLE_LENGTH_M`), never the consuming parameter.
- **OP-D30** No `scale` field in any config. The scale selects which config and is never in
  it, so an operation cannot branch on it and one function serves every scale.
- **OP-D31** `OperationCall.parameters` is uniformly `{"config": ...}` or empty, so a run
  manifest gets a JSON-able tuning record from `dataclasses.asdict`.
- **OP-D32** `__post_init__` is where a constraint on a value goes. A stage cannot check that
  a tolerance is positive; a config can.
- **OP-D33** A sub-config shared across operations earns nesting, kept to one level. Declared
  once per scale and referenced from both configs, disagreement is unrepresentable.
- **OP-D34** A config unchanged at a scale is re-exported, not omitted. A `None` placeholder
  is a trap.

**Rejected candidates for pass 3** (each once): OP-R1 a composition dataclass for an
operation's IO (reopen given: substitutability per scale); OP-R2 classifying injected
parameters by name; OP-R3 moving the bundle into the core; OP-R4 `Toolbox | None = None`;
OP-R5 a module-level bundle singleton (reopen given: the parameter proving worse once real
operations exist); OP-R6 a layered resolution mechanism for tuning.

**Design-document passages absorbed by this theme**, replaced at the cut-over by a pointer to
the ADR id: 03 §4.4 (how ports reach the code, OP-D19, OP-D20, OP-D23); 02 §2.4 (operations,
OP-D20, OP-D24); 02 §2.7 (tuning, OP-D25 to OP-D34). 02 §2.4 and §2.7 are split into rule and
explanation line by line before the cut-over.

## 5. Theme ST: Stages

### 5.1 Draft top-level Direction

| n | draft text | source |
|---|---|---|
| 1 | Every external source and every product is declared once, centrally, as a symbol, and both sides of a publication reference the symbol. The legality of what we produce is computed over the wiring, never declared on the product. | 0012 §Decision, §Consequences |
| 2 | A stage input has a declared role, answering whether its rows may become stage output, and a spatiality read from its object's data type, never declared. | 0016 §Decision |
| 3 | Only rows originating from `PROCESSING` inputs become stage outputs. A `CONTEXT` row influences an output and never becomes one. | 0016 §Decision |
| 4 | The stage is the resume granularity. The design neither plans for nor depends on intra-pod checkpoints. | 0009 §Decision; arch 2026-10-21 (exact text) |

### 5.2 Sections and draft Direction lines

| section | draft Direction line | source |
|---|---|---|
| ST-1 Sources and products | `sources.py` holds every `ExternalSource`, with its classification required; `products.py` holds every `ProductIdentity`, with no classification; pipelines import these leaves and never each other. | 0012 §Decision, §Consequences; 03 §4.1 |
| ST-2 Stage inputs: role and spatiality | The role is declared per stage input and belongs to it, not to the object; spatiality is read from `DataType`; fan-out's transfer follows from both and from the context radius, and from nothing else. | 0016 §Decision, §Consequences |
| ST-3 Resume | A pod lost mid-stage restarts the stage, and the resilience budget goes into not losing pods. | 0009 §Context, §Consequences |

### 5.3 Decisions from the old ADRs

| from | decision | source | placement | note |
|---|---|---|---|---|
| 0012 | Earlier per-pipeline `Source` with value equality: silent misclassification, product with no location | §Context | rejected (per-pipeline declaration) | plausible ("pipelines should be independent"); reopen: NEW (nothing) |
| 0012 | `sources.py`: every `ExternalSource`; `classification` required; `eq=False` | §Decision | detail | |
| 0012 | `products.py`: every `ProductIdentity`: scale, dataset, location; `eq=False`; no classification | §Decision | detail | |
| 0012 | `Publish` and `StageInput` reference the symbol; import-linter keeps both leaves | §Decision; 03 §4.1 | detail | |
| 0012 | New restricted source is a `TypeError` at import; one reviewable file | §Consequences | detail | condensed |
| 0012 | `check_sources_agree` deleted | §Consequences | drop | history |
| 0012 | `identity_producer`, `check_no_self_read` keyed on an object | §Consequences | detail | contract |
| 0012 | `ProductIdentity` carries no classification; `reclassify_to` is the one auditable assertion | §Consequences | Dir 1 + detail | |
| 0012 | `policy.classification_of` resolves a published identity with `reclassify_to` applied; unknown identity fails closed | §Consequences | detail | contract |
| 0012 | Reviewer property moved up a level | §Consequences | drop | commentary |
| 0012 | No pipeline imports another; pipelines import a leaf | §Consequences | detail | constraint |
| 0012 | `locations.py` owns environment prefixing; four remote-path builders live there | §Consequences | detail | the argument itself stays in the docstring |
| 0012 | Note on ADR-0003's stale enumeration | §Consequences | drop | applied in PC |
| 0012 | `Scale`, `ObjectName` are `StrEnum`; `RAW` is `Scale.RAW`; closed `ObjectName` | §Also decided | detail | |
| 0012 | `scale`, `object_name` repeated on every `Stage`; `check_stage_tags_match_pipeline` at plan time | §Also decided | detail | |
| 0012 | Supersedes 02 §2.2 | header | drop | 02-runtime already reflects it |
| 0016 | What the design documents got wrong; the legacy iterator's behaviour | §Context | drop | history |
| 0016 | Deriving a role from the data | §Context | rejected | plausible ("a table is obviously context"); reopen: NEW (nothing) |
| 0016 | Role declared per stage input, belongs to the input not the object; the water-layer example | §Decision | Dir 2 + detail | |
| 0016 | Spatiality from `DataType`; `FEATURE_CLASS`, `RASTER` spatial; `TABLE`, `SYMBOLOGY` not; `DataType.spatial` | §Decision | detail | |
| 0016 | Transfer table (four cells) | §Decision | detail | |
| 0016 | Context filter within the radius before partitioning; 0 m intersects; the radius with no second number; overlap for both partitioned roles; fan-in discards halo copies | §Decision | detail | |
| 0016 | Non-spatial `PROCESSING` rejected at `StageInput` construction, break-it case; no other guard | §Decision, §Consequences | detail | |
| 0016 | Only `PROCESSING` rows become outputs; scratch intermediates from `CONTEXT` legal; produce in a stage where the source is `PROCESSING`; enforced by review until a static check exists | §Decision | Dir 3 + detail | open point stated by subject |
| 0016 | The radius is a claim about the logic; 0 m states nothing consults a neighbour; not guarded | §Decision | detail | cross-ref PC (no partition index) |
| 0016 | Rasters spatial, either role; tile selection or clipping; mechanism open | §Decision | detail | |
| 0016 | Symbology files: non-spatial `CONTEXT`, `ExternalSource` with `SYMBOLOGY`, settable location, classification; all tables and symbology are stage inputs, never baked into the image; `SYMBOLOGY` not `FILE` | §Decision | detail | |
| 0016 | Numeric symbol dimensions are config fields, never a stage input | §Decision | detail | cross-ref OP-4 |
| 0016 | Port-level subject and context relate to the roles and are not the same | §Decision | detail | cross-ref RS-2 |
| 0016 | Third role rejected | §Rejected | rejected | plausible; reopen: NEW (nothing) |
| 0016 | Generic `FILE` rejected | §Rejected | rejected | plausible; reopen: NEW (nothing) |
| 0016 | Consequences list: `DataType` four members, `InputRole` two with docstring; fan-out reads three facts; fan-in keeps non-spatial outputs by id ownership; context-only output is a declaration error; `PREM_ONLY` pins the stage | §Consequences | detail | condensed |
| 0009 | No intra-pod resume; `--invalidate-from <stage>` only | §Decision | Dir 4 | |
| 0009 | Blocker is structural: pod-local workspace, roughly 2K transfers plus a merge per stage, the cost grouping exists to avoid | §Consequences | rejected (intra-pod resume) | reopen (arch 2026-10-21): a stage whose re-run cost makes a checkpoint pay after promoting its expensive operator to its own stage has been tried; the mint counter then becomes checkpoint state |
| 0009 | Escape hatch: promote an operator approaching its stage's re-run cost to its own stage; Q-G measures | §Consequences | detail | |
| 0009 | Resilience budget: `podFailurePolicy`, `terminationGracePeriodSeconds`, `safe-to-evict: "false"`, memory and ephemeral-storage limits | §Consequences | detail | constrains the job spec |
| 0009 | Recorded so the reason is not re-derived | §Consequences | drop | |

### 5.4 Approved text for ADR-0021 (pass 2, 2026-10-21)

Status, Scope, Direction 1 to 4 and the section lines are approved as exact text; Direction 2,
Direction 3, ST-2, ST-D11, ST-D16 and ST-D21 in the architect's revised form. ST-D25 (the
Kubernetes settings) is removed: deployment configuration, carried by 03 §8. The id ST-D25 is
not used. This is the text pass 4 writes.

**Status:** Accepted, <cut-over date>.

**Scope:** `ag/core/pipeline.py`, `ag/generalization/sources.py`,
`ag/generalization/products.py`, `ag/core/locations.py`, and the stage-level model that
fan-out, fan-in and resume implement. Absorbs A31.1 to A31.7. Partition ownership (A6, A7, A8)
joins when it migrates.

**Direction.**

1. Every external source and every product is declared once, centrally, as a symbol, and both
   sides of a publication reference the symbol. The legality of what we produce is computed
   over the wiring, never declared on the product.
2. A stage input declares a role, which tells fan-out how that source is treated, and has a
   spatiality read from its object's data type, never declared.
3. Only PROCESSING inputs can become stage outputs, though they need not. A CONTEXT input
   serves only as context for the PROCESSING inputs and never becomes an output.
4. The stage is the resume granularity. The design neither plans for nor depends on intra-pod
   checkpoints.

(Direction 2 is the architect's text of 2026-10-21; the variant adding "and whether it may
become stage output" was offered and not chosen unless the architect says so.) The role names
stay in Direction under the naming exception: defined terms, the word "context" chosen on
purpose (A31.6), alternatives rejected by name (A31.7).

**ST-1 Sources and products.** Direction: External sources and products are each declared in
one leaf module as symbols, an external source with its classification required and a product
carrying none; pipelines import those leaves and never each other.

- **ST-D1** `sources.py` holds every `ExternalSource` in the project; `classification` is
  required, with no default; `eq=False`. A new restricted source is a `TypeError` at import
  until its legality is stated, and appears as a diff in the one file that shows everything
  entering the project under what restriction.
- **ST-D2** `products.py` holds every `ProductIdentity`: scale, dataset and location;
  `eq=False`; no `classification` field.
- **ST-D3** Both sides of a publication reference the symbol:
  `Publish(obj=..., identity=..., reclassify_to=...)` and `StageInput(obj=<the identity>,
  ...)`. `.importlinter` keeps both modules leaves that import only the core.
- **ST-D4** `identity_producer` and `check_no_self_read` are lookups keyed on the object, so
  find-references on a symbol answers who produces it and who reads it.
- **ST-D5** The legality of something we produce is computed over the stage wiring that
  produced it. The one human assertion that generalization removed a restriction lives on
  `reclassify_to`, at one auditable point.
- **ST-D6** `policy.classification_of` resolves a published `ProductIdentity` to the
  producing stage's computation with `reclassify_to` applied. An identity nothing here
  publishes falls back to rules and fails closed.
- **ST-D7** No pipeline imports another pipeline. Pipelines import the leaves.
- **ST-D8** `locations.py` owns environment prefixing: the remote-path builders
  (`scratch_location`, `scratch_dump_location`, `payload_location` and the archive location)
  live there.
- **ST-D9** `Scale` and `ObjectName` are `StrEnum`, so a member renders as its value in a
  path builder; `RAW` is `Scale.RAW`. `ObjectName` is closed, so adding an object edits a
  shared module.
- **ST-D10** `scale` and `object_name` are repeated on every `Stage`. A plan-time check
  confirms they agree with the pipeline, since the `Stage` is constructed before the
  `Pipeline`.

**ST-2 Stage inputs: role and spatiality.** Direction: The role is declared per stage input
and belongs to it, not to the object; spatiality is read from the object's data type;
fan-out's treatment of a source follows from both and from the context radius, and from
nothing else.

- **ST-D11** PROCESSING: the stage acts on the whole source. Fan-out applies no filter; every
  row is processed in its partition, with the context around the partition. CONTEXT: the
  source matters only as context for the PROCESSING inputs. Fan-out filters a spatial CONTEXT
  input to the context radius around the PROCESSING rows and sends a non-spatial one whole.
  The role belongs to the stage input, not to the object: the same water layer is PROCESSING
  in the stage that generalises it and CONTEXT in the stage that moves buildings away from
  it.
- **ST-D12** `FEATURE_CLASS` and `RASTER` are spatial; `TABLE` and `SYMBOLOGY` are not.
  `DataType.spatial` says so, and no module re-derives it.
- **ST-D13** Transfer: spatial PROCESSING is partitioned with halo overlap; spatial CONTEXT is
  context-filtered, then partitioned with the same overlap; non-spatial PROCESSING is
  rejected at declaration; non-spatial CONTEXT is sent whole to every pod, written once at a
  shared key.
- **ST-D14** The context filter keeps CONTEXT rows within the stage's context radius of any
  PROCESSING row, before partitioning; at 0 m, the rows that intersect one. The filter
  distance is the radius, with no second number. Overlap applies to both partitioned roles: a
  PROCESSING row within the radius of a partition but outside it reaches that partition too
  and fan-in discards it; a CONTEXT row within the radius reaches it.
- **ST-D15** Non-spatial PROCESSING is rejected when the `StageInput` is constructed, with a
  break-it case. There is no other guard: 0 m with spatial context is legal.
- **ST-D16** A stage output derives only from PROCESSING inputs: every output row originates
  from a PROCESSING input. Values taken from a CONTEXT input (an attribute joined from a
  table, a value sampled from a raster, symbology a tool applies) may shape or annotate those
  rows. A row that originates from a CONTEXT input never becomes output, whether or not
  PROCESSING rows are mixed in. Found in review until a static check exists; the check needs
  an operation-level subject marker, which is open. Scratch intermediates built from a
  CONTEXT input are legal inside a stage and reach the scratch dump. An object built from a
  CONTEXT input that a later stage must read is produced in a stage where its source is
  PROCESSING.
- **ST-D17** The context radius is a claim about the logic. Operations never see partitions
  (ADR-0019 PC-D2), so the radius is the one place a stage author reasons about partition
  boundaries; 0 m states that nothing in the stage consults a neighbour, and the model does
  not guard it.
- **ST-D18** Rasters are spatial and take either role; transfer is tile selection or clipping
  to the partition plus its halo, not row filtering. The mechanism is open until a stage
  declares a raster input.
- **ST-D19** Symbology files are non-spatial CONTEXT inputs: an `ExternalSource` with
  `data_type=DataType.SYMBOLOGY`, a settable location and a classification, reaching every
  pod whole. Every table and every symbology file is a stage input with a settable storage
  location, never baked into the container image. The member is `SYMBOLOGY`, not a generic
  `FILE`, so the next file kind gets its own decision.
- **ST-D20** Numeric symbol dimensions are a project-wide Python resource that reaches
  operations as config fields varying by pipeline (ADR-0020 OP-4), never a stage input.
- **ST-D21** The port-level subject and context of the row-shape grammar relate to the roles
  and are not the same thing (ADR-0017 RS-2). The grammar declares, per port method, which
  input's rows carry identity into an output; the roles declare, per stage input, whether a
  source may become stage output. At both levels, only the subject carries identity into
  outputs, and a context influences without contributing identity.
- **ST-D22** `DataType` has four members and a `spatial` property; `InputRole` has two
  members and a docstring stating the rule and the four transfers. Fan-out reads three
  declared facts, the role, the radius and the object's data type, and nothing else; fan-in
  keeps non-spatial outputs by id ownership. A `PREM_ONLY` classification on a table or
  symbology file pins the stage on-prem like any other input.

**ST-3 Resume.** Direction: A pod lost mid-stage restarts the stage, and the resilience budget
goes into not losing pods.

- **ST-D23** The stage workspace is pod-local. `--invalidate-from <stage>` is the only resume
  mechanism; a pod lost to OOMKill, eviction or node maintenance restarts from the beginning
  of its stage.
- **ST-D24** An operator whose runtime approaches its stage's total re-run cost is promoted
  to its own stage: a declaration change, not an architecture change. Whether the trade pays
  is Q-G, measurable once one operator is reimplemented.

**Rejected candidates for pass 3** (each once): ST-R1 each pipeline declaring its own sources,
linked by value equality; ST-R2 a `classification` field on a product identity; ST-R3 deriving
the role from the data; ST-R4 a third role for the non-spatial case; ST-R5 a generic `FILE`
data type; ST-R6 intra-pod resume (reopen given, section 5.3).

**Design-document passages absorbed by this theme**, split into rule and explanation line by
line before the cut-over: 02 §2.2 (ST-D1 to ST-D3), 02 §2.3 (ST-D11 to ST-D22), 02 §7 where
it states transfer rules, 03 §4.1 (the leaves paragraph, ST-D3, ST-D7), 03 §7.5 (ST-D19,
ST-D20), 03 §9 (the Q-D closure).

**A31 at the cut-over:** its strike lines as one approval request with exact text, landing
A31.1 to A31.7 at ST ids; the terminology rows citing A31.1 to A31.6 (input role, spatial,
context filter, `SYMBOLOGY`, subject, `context`) repointed to ST and RS ids; the "input role"
row reworded at source level to match Direction 2 and 3.

## 6. Theme RS: ADR-0017, revised last

Direction and details unchanged in substance. Format changes to match the others, all as a
pass 2 change summary:

- Status becomes status and date only: "Accepted, 2026-10-19".
- Scope keeps its A-ids (allowed there). The sentence naming slice 2a and T2.8 is reworded by
  subject: "the call-site declaration for writes (A12.7a), with its declaration type; the
  in-place mutators (A12.6), with their declaration form".
- RS-D10 drops "(A11.11)"; RS-D13 drops "(A12.6, with T2.8)" and says "open until the in-place
  mutators join"; RS-D15 drops "(A12.7a)".
- The Related line cites ADR-0018 AR-3, ADR-0020 OP-1 and ADR-0021 ST-2.
- No retired number appears anywhere in the file. Nothing in the body contrasts with an
  earlier design; RS-R1 names the single-enum alternative as a rejected entry, which passes the
  Rejected test (it is the obvious first proposal).

## 7. A-item sweep: every A-item whose destination names a retiring ADR

| A-item | destination as written | draft Direction line | result |
|---|---|---|---|
| A1.3 | ADR-0008 (amend with the incremental-port argument and the constructor-injection guidance) | OP Dir 4; OP-3 line | compatible: constructor binding is in both; the incremental-port argument becomes the singleton Rejected entry's reason |
| A2.1 | ADR-0015 (landed 2026-10-07) | PC Dir 3; PC-3 line | compatible; already in 0015 §Decision |
| A2.2 | ADR-0015 (landed) | PC Dir 3 | compatible |
| A2.3 | ADR-0015 (landed) | PC-3 detail (schema declarations a non-goal) | compatible |
| A4.1 | ADR-0004 (amend with the counts) | PC Dir 4; PC-4 line | compatible. Resolved 2026-10-21: the counts go to 04-migration Appendix A as rows with their regenerating `rg` commands; the ADR keeps the rules. Approved destination text: "`destination:` ADR-0019 PC-4 (the no-cursor rule, the bulk mapping, deletion as select); 04-migration.md Appendix A (the per-method counts, with their commands)." Applied at the cut-over. |
| A4.2 | ADR-0004 | PC Dir 4 (keyed bulk update) | compatible; the side-table alternative becomes a Rejected candidate. Destination text proposed for approval: "`destination:` ADR-0019 PC-4 (the keyed bulk update; the side-table alternative as a Rejected entry); 04-migration.md Appendix A (the `updateRow` and `CalculateField` counts, with their commands)." |
| A4.3 | `ports/table_ops.py` docstring; ADR-0004 amendment | PC-4 line; detail | compatible: `update_rows`, keyed, `Row.geometry`, stable key |
| A10.5 | same ADR as A10.1; ADR-0009 | ST Dir 4 | Resolved 2026-10-21: checkpoints for job pods are out of scope for the refactor, neither planned nor depended on nor banned; F4 closed. Approved replacement text: "**A10.5** Minter id is stable per logical job. A job exceeding 2³²−1 mints fails loudly rather than wrapping into another minter's space. `destination:` same ADR as A10.1." TASKS T3.5's "ADR-0009 amendment for the checkpoint" is removed. Both applied at the cut-over. |
| A10.4 | same ADR as A10.1; 02 §7.4 (TASKS 1320 adds "ADR-0009 amendment") | ST-3 | compatible: retry reuses the minter id and replaces artifacts wholesale, which is a stage restart, not a resume |
| body cites, not destinations | DECISIONS.md 1792 (ADR-0011, `fn.__name__`), 1875 (ADR-0003, no partition index), 1904 (ADR-0013, config fields), 2567 (B22, ADR-0011's own-handles check) | OP-1 detail; PC-1 detail; OP-4; OP-1 detail | compatible; repointed at the cut-over |

No other `destination:` line names ADR-0001 to ADR-0016. Lines naming ADR-0017 (A12.1 to
A12.5a) are unaffected.

## 8. Lines marked "new, needs decision"

1. **Every reopen condition** in sections 2 to 5 marked `reopen: NEW`. Deferred to pass 3
   (arch 2026-10-21). Supplied so far: 0001 (`any()`: a backend that short-circuits), 0008
   (singleton: the revisit clause), 0011 (composition dataclass: substitutability per scale),
   the LogPort clause, and the intra-pod resume clause (section 5.3).
2. **Dropped** (arch 2026-10-21): "an adapter may serve a port's methods from more than one
   library" conflicted with 03 §4.1 and is not in AR Dir 2. Kept: per-port choice at the
   composition root (03 §4.1) and that a port's implementation may call other ports (03 §4.3).
3. **Kept as a PC-4 detail** (arch 2026-10-21): there is no delete method; deletion is
   `select` with a negated membership predicate. Source: A4.1 and the decision.
4. **Kept** (arch 2026-10-21): per-port adapter choice at the composition root.
5. **Dropped** (arch 2026-10-21): `dump_tuning.py`.
6. **Settled** (arch 2026-10-21): "resume granularity"; ST Dir 4 text as in section 5.1.
7. **Settled** (arch 2026-10-21): the helper promotion rule stays in 03 §5 and is not copied
   into an ADR.

## 9. Open ideas recorded, not decided

- Per-stage or per-operation adapter overrides at the composition root (section 2.4).
- `CartographicOps` split per operator: Q-B, by measurement after one operator is reimplemented.
- `GraphOps` signature, datasets or pure values: Q-C, open in 03 §9.
- Stage promotion of a long operator: Q-G, by measurement.
- A static check for the output rule (needs an operation-level subject marker); the raster
  transfer mechanism (ST-2).

## 10. Pass 4 cut-over checklist

1. Write ADR-0018, ADR-0019, ADR-0020, ADR-0021 under `docs/decisions/`, from the approved
   pass 2 and pass 3 text. Move and revise ADR-0017 to `docs/decisions/0017-row-shape-grammar.md`.
2. Remove the seventeen files under `docs/refactor/decisions/` from the working tree. Staging
   (`git rm`) is the architect's, listed in the report.
3. `docs/decisions/README.md`: fill the Index in reading order (AR, PC, RS, OP, ST), fill the
   Provenance table (0001 to 0016 to their ADR and ids), add the Sources section (Cockburn,
   PEP 544, CQL2, the Kubernetes reference from the refactor README), remove the
   "Consolidation in progress" paragraph.
4. CLAUDE.md version (b), applied by the architect to the working tree in the same change,
   before the full check, with the hook bullet as applied in (a). The "No hook resolves ADR
   ids yet" clause is dropped only if the citation test has landed by the cut-over.
5. DECISIONS.md: the thirteen lines of the Part B table (2026-10-20 message), applied only with
   the architect's approval of the exact text, requested again at pass 4 with ids final. Already
   approved as exact text (2026-10-21): the A10.5 replacement and the A4.1 destination, both in
   section 7; A4.2's destination awaits approval. TASKS.md 1320 loses "ADR-0009 amendment for
   the checkpoint"; T3.5's acceptance clause that copies the checkpoint sentence (REVIEW F4) is
   checked and removed if present; F4 recorded as closed, checkpoints out of scope.
5a. 04-migration.md Appendix A gains the A4.1 and A4.2 per-method counts as rows, each with
   its regenerating `rg` command, noted as counting cursor method calls, not constructions.
6. Repoint every other citation: TASKS.md (784, 810, 912, 1320, 1444, 1459, 1488, 2193, 2196);
   PROPOSALS-2026-10-14.md (eight, line-number citations dropped); REVIEW-2026-09-14.md
   (three); findings (`project_tree.md`, `slice_0_contract_evidence.md`,
   `slice_1a_row_shape_evidence.md`, `template_review.md`, `implementation_plan.md`);
   `template_code/` (README and the eleven modules, numbers only, reference code);
   01-terminology rows 94 to 98, 157, 176, 177; 02-runtime 153, 257, 293, 324, 383, 838;
   03-architecture (22 citations, including the §9 Q-A, Q-D, Q-E closures); 04-migration
   (four); `docs/refactor/README.md`; the thirteen files under `src/` and `tests/`.
   `docs/presentations/scaling-plan-board.md` is untracked and belongs to the maintainer; its
   six citations are listed, not edited.
7. `docs/refactor/README.md`: decisions row points to `../decisions/README.md`; the
   immutability sentence, the per-ADR table, the 0001–0010 and 0011–0014 paragraphs and the
   Sources list go; convention bullets on numbers and paths stay; recommended action 6 struck.
8. `implementation_plan.md` §4.2, §4.4, §4.6, §4.8: the exact text approved in pass 2 (the
   2026-10-20 draft, revised for the README's provenance rule).
8a. Design-document passages absorbed by an ADR are replaced by a pointer to the ADR id; the
   document keeps only explanation that is not a rule (arch 2026-10-21). Per theme: AR: 03 §2,
   §4.1, §4.3, §4.5. PC: 03 §2.3, §2.4, §2.5, §3.1, §3.2; 02 §2.4. OP: 03 §4.4; 02 §2.4,
   §2.7, the two 02 sections split into rule and explanation line by line before the
   cut-over. ST: 02 §2.2, §2.3, §7 (transfer rules only); 03 §4.1 (leaves), §7.5, §9 (Q-D).
   RS: listed in its approved-text section.
8c. A31: strike lines for A31.1 to A31.7 as one approval request with exact text; terminology
   rows citing A31.1 to A31.6 repointed to ST and RS ids; the "input role" row reworded at
   source level (section 5.4).
8b. 04-migration.md line 50: `pipelines/road/tuning/n100.py` becomes
   `operations/road/tuning/n100.py`, the decided layout (section 3.5).
9. The citation test, `tests/static/test_adr_citations.py`, if adopted: every `ADR-\d{4}`
   under `src/`, `tests/` and `docs/` resolves to a file in `docs/decisions/`; every id after
   it exists in that ADR; no retired number appears outside `docs/decisions/README.md` and
   `docs/decisions/evidence/`; no ADR body cites an A-id, B-id, task id, slice or PR outside
   Scope. Its break-once cases need `tools/break_once/`, an explicit-request path.
10. Full check green; `check_terminology.py` untouched (rows citing ADR ids have no
    `file.md#anchor` and are skipped by its current rules).
11. Report: every changed item per ADR; the files to stage; a commit message naming each
    removed rejected alternative and each changed Direction.

## 11. Citation inventory (from `grep -rnoE "ADR-00[0-9]{2}"`, 2026-10-20)

| area | files | citations |
|---|---|---|
| `docs/refactor/temp/` (DECISIONS, TASKS, PROPOSALS, REVIEW, findings) | 9 | 103 |
| `docs/refactor/decisions/` (the ADRs themselves) | 17 | 48 |
| `docs/refactor/` design documents and README | 5 | 41 |
| `docs/refactor/template_code/` | 19 | 46 |
| `src/ag/` | 13 | 31 |
| `tests/` | 3 | 4 |
| `docs/presentations/` (untracked) | 1 | 6 |
