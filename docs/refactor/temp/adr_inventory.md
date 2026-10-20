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
