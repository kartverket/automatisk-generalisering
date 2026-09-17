# Lineage seam readiness — audit, 2026-09-17

**Status:** STAGING finding. Nothing here is decided. It reports what `DECISIONS.md`, `TASKS.md`,
`01-terminology.md` and `findings/n1_correspondence.md` say about the interface between the
ports, the `@row_shape` declarations, the lineage layer and the toolbox call site, so that port
and adapter design can start on settled ground. Proposed A-item and B-item text in §3 is
paste-ready but unsigned.

**Question asked.** Is the lineage seam settled at the interface level, so that the mechanism by
which an adapter produces parents can be refined later without touching a port signature, a
decorator, the toolbox call site or the lineage layer?

**Evidence kinds**, as in the N:1 findings file: *decided* cites an A-item or a task acceptance
line; *implied* cites the items whose conjunction forces the statement; *open* means neither.
Line numbers are into the files as of 2026-09-17.

---

## 1. Verdict

**Ready once items 3.1 to 3.4 are written.** Ready in the sense that the working assumption
holds: every written decision places parents at the port boundary as native index pairs and
`lineage_id` above it (A11.11, DECISIONS.md:726-740), and no mechanism, tier or vendor parameter
appears in a port signature, a decorator or the toolbox call site. The leaks that exist are all in
A14, T4.10, T4.11 and T0.1 case 12, which describe the adapter and its tests, and the findings
file §7 rewording removes them.

What is not ready is narrower than the mechanism and sits on the Protocol itself:

1. **The parents channel exists for `dissolve` only.** T2.4 and B6 give `parents:` to one method.
   A12.11 declares five `GROUP + MINT` methods and five `MANY + MINT` methods, and A12.4 says the
   facade mints from the parents table on every one of them. Nothing written says how the facade
   obtains parents from the other nine. This is the one gap that changes Protocol signatures.
2. **What id space the parents table holds** is written for neither boundary. A11.11 says native
   indices at the port; A11.1 says domain code consumes the parent set; A9.2 says the native index
   is behind the port. Together they force a translation the facade performs, and no item says so.
3. **`dissolve` has two written signatures.** A5.6 keeps `option: DissolveOption` as an argument;
   A18 and T2.9 say a multipart dissolve is a separate `dissolve_multipart` method.
4. **A12.5a is unsigned.** Annotating port parameters `In`/`Out` touches every Protocol once. Doing
   it after the ports are written means writing them twice.

Everything else in §2 either is decided, or is a docstring sentence that can be added to a written
port without changing it, or is adapter-internal.

---

## 2. Questions 1–11

| # | question | status | citation | blocks port or decorator design |
|---|---|---|---|---|
| 1a | what `@row_shape` declares | **decided** | A12.1 (DECISIONS.md:776-822), A12.2 (:824-833), T4.1 (TASKS.md:1279-1282) | no |
| 1b | where it sits, who reads it | **decided** for the facade and CI; **open** for plan time | A11.11 (:735-739), A12.5 (:848-852), A12.9 (:892-897) against B14 (:2050-2063) | no |
| 1c | shape varying with a parameter | **decided**: none | A5.6 (:150-175), A18 (:1356-1365) | no |
| 2a | what a port method returns | **decided**: `None`; parents via an optional out-param handle | A11.1 (:527-546), T2.4 (TASKS.md:1017-1021), terminology `parents` (01-terminology.md:89) | no |
| 2b | is the parents payload in the return type, a side channel, or pulled by the runtime | **decided** for `dissolve` (out-param); **open** for the other nine `MINT` methods | T2.4, B6 (:1619-1621) against A12.11 (:917-944) and A12.4 (:841-846) | **yes** |
| 2c | the type as written | **partly written**: `parents: ScratchHandle \| None`, a TABLE of `(PARENT_ID, CHILD_ID)`; the id space of the two columns is unwritten | T2.4; A11.11 (native at the port); A11.1 (domain consumes) | **yes** |
| 3a | parents unconditional or on request | **implied**: on request | A11.1 ("optional out-param"), A15.1 (:1068-1071), A12.4 | no |
| 3b | how the request reaches the adapter | **decided** for `dissolve` (a parameter); **open** for the rest; the wrapper is the requester by A11.11 and T4.3 | T2.4, T4.3 (TASKS.md:1355-1387) | **yes** (same gap as 2b) |
| 4a | adapter never mints, never sees `lineage_id` | **decided** for minting; **implied** for seeing | A11.11, A11.12 (:742-754), A12.7 (:871-874) | no |
| 4b | single parent carries, two or more mint | **decided** | A12.4 | no |
| 4c | DROPPED derived at runtime from survival | **decided** | A11.5 (:670-688), A11.7 (:702-705), T4.6 (TASKS.md:1484) | no |
| 4d | draft B17 adapter rule conflicts | **no conflict**; see §2.4 | findings §3.7, §6 | no |
| 5a | "statistics are per output part" in the port contract | **implied** by the definitions; not written | A9.10 (:407-418), A11.14 (:765-774), terminology `combining rule` (:99); findings §3.9, §10.2 | no, docstring only |
| 5b | `statistics=` depends on parents even without lineage | **open**; adapter-internal if the findings' recommendation is taken | findings §6, §10.2 | no |
| 5c | the value type of `statistics` | **open** | T2.10 shows `((RANK, MAX),)` and defines nothing | **yes**, for the `dissolve` signature |
| 6a | `SINGLE_PART` on lines splits at every junction | **not written**; measured | findings §3.9 (:267-270), §10.4 | no, docstring only |
| 6b | `buffer_dissolve` positive distances only | **not written**; mechanism-derived | findings §4.1 (:363) | no, but see §2.6 |
| 6c | empty geometry rejected before the call | **open** | findings §3.9 (:253-265), §10.5 | no, precondition sentence plus an error type |
| 7 | engine-neutral, named error types | **open**; today adapter-specific and in `temp/` | `adapters/arcpy/__init__.py` names an unwritten `errors.py`; `dissolve_parents.py:78-99`; A14 tier 4 | docstrings, not signatures |
| 8a | capability record keyed on methods or mechanisms | **written on a mechanism**; §7 rewording makes it methods | A14 (:1051-1060), T4.10 (TASKS.md:1615-1621) | no |
| 8b | after the rewording, anything left exposing a tier | one thing: the record covers `GROUP + MINT` only, and `MANY + MINT` methods also need parents | findings §7 row 1 | no |
| 9 | native index stable across a call, enforced at a named point | **decided** as a contract line; **not enforced** anywhere named | A9.2 (:346-349), T3.1 (TASKS.md:1039-1062) | no |
| 10 | anything in the port contract assumes ArcGIS | **no** in the ports as written; two candidates would enter through §2.6 and §2.7 | template `geometry_ops.py`, A18, A10.1 | no |
| 11 | `tb.<namespace>.<method>(...)` unchanged by any mechanism | **confirmed** | `toolbox.py`, `operations/road/__init__.py:648-653` | no |

### 2.1 The decorator

**Declares**, per output parameter of a port method: `Rows(cardinality=..., ids=..., subject=... |
refs=..., context=...)`.

- `cardinality ∈ {ONE, MANY, GROUP}`, rows per subject row (A12.1).
- `ids ∈ {CARRY, MINT, FOREIGN}` (A12.1; the axis was renamed from `identity=`).
- `subject=` names the input parameter whose rows contribute identity; `context=` names an input
  that influenced the output without contributing identity (A12.2); `refs={COLUMN: "param"}`
  replaces `subject=` on `FOREIGN` (A12.1).
- Three illegal cells, `MANY + CARRY`, `GROUP + CARRY`, `GROUP + FOREIGN`, each with its stated
  reason; so `CARRY` implies `ONE` (A12.1).
- Attached as `@row_shape(**outputs: Rows)` keyed by output parameter name, without changing the
  method signature, so structural typing holds and adapters carry no decoration (T4.1,
  TASKS.md:1281-1282). `01-terminology.md:90` writes `@row_shape(out=Rows(...))`; read `out` as an
  example key, since A12.11 keys `simplify.collapsed_points` by parameter name.
- Stored as `Method.__row_shape__` on the **Protocol**, read from the Protocol and never from the
  adapter instance (A11.11).

**Who reads it.**

| reader | when | status |
|---|---|---|
| the lineage facade (T4.3) | at each port call | decided, A11.11 |
| `tests/unit/test_row_shape.py` (T4.1) | CI | decided, A12.5; the output-parameter rule cannot fire until B12 / A12.5a |
| `validate()` (A12.9 `FOREIGN`-subject check; A14 capability check) | plan time | **open**: B14 records that plan time never sees which port methods an operation body calls |
| the conformance suite (T4.11) | image promotion | decided: one case per `MINT` method and per `CARRY` method |

**Varies with a parameter:** no method, by construction. A5.6 split the four methods whose row
semantics varied by argument and recorded "discriminators needed: zero". `dissolve.option` does not
move the cell (A5.6), `simplify.collapsed_points` is a second output with its own declaration, and
`explode_multipart` on single-part input is `MANY` degenerately. A18 states the design rule: a
behaviour that would change the cell becomes a separate method, never an argument.

### 2.2 What a port method returns

Every handle-producing method returns `None` and writes to its `output` handle (template
`geometry_ops.py`, every method). The parents payload is **not** in the return type and is **not**
pulled by the runtime from the adapter: it is an **optional out-param handle**,
`parents: ScratchHandle | None`, receiving a TABLE of `(PARENT_ID, CHILD_ID)` rows, one per
contributing input row (T2.4, TASKS.md:1017-1018; A11.1). B6 fixes the signature shape so that
adding the parameter to another method is uniform.

**Written for `dissolve` only.** T2.4: "Only `dissolve` gets the parameter. `aggregate`,
`collapse_to_point`, `cluster_points` and `collapse_to_centerline` have no caller wanting the
parent set." That sentence is about *domain* callers. The *facade* is a caller too: A12.4 says
"per-row behaviour comes from the parents table: a dissolve group with one parent carries the id
and emits no edge; only groups with ≥2 mint. Same for `MANY`." So the facade needs a parents table
from every `MINT` method it wraps:

| cell | methods (A12.11) | parents channel written |
|---|---|---|
| `GROUP + MINT` | `dissolve`, `buffer_dissolve`, `aggregate`, `cluster_points`, `collapse_to_centerline` | `dissolve` only |
| `MANY + MINT` | `explode_multipart`, `split_at_points`, `intersection`, `difference`, `clip` | none |

`buffer_dissolve` is A15.5's own worst case (`build_displacement_feature`), and it is one of the
nine with no channel. A14's "`ORIG_FID` from `MultipartToSinglepart` covers most `MANY + MINT`
cases" describes what the adapter can *read*, not how it hands the pairs upward.

**The id space of the two columns is unwritten**, and three written items pull on it:

- A11.11: "the port reports row parentage in its own vocabulary — native indices; the layer above
  maps to `lineage_id`."
- A11.1: the parents handle is "consumed by domain code that acts on the parent set."
- A9.2: the native index "goes behind the port."

If the domain reads the handle the adapter wrote, it reads native indices, which A9.2 keeps behind
the port and which the domain cannot join to anything the facade's `read_rows` returns. The
conjunction forces a facade step: native pairs at the port boundary, `lineage_id` pairs at the
domain boundary. A11.11's "the layer above maps to `lineage_id`" is that step, but no item says the
mapped table is what the domain receives, nor that it is a second write.

**A constraint that narrows the channel choice.** T4.11 (TASKS.md:1647-1649) drives the Protocol
directly and asserts "the reported parents match" per `MINT` method. So the parents payload has to
be reachable through the Protocol, not through a facade-private path. That is B10's own point
("the conformance suite is a fifth site ... because the Protocol is what it conforms"). It rules
out a facade-only side channel and leaves the out-param.

### 2.3 Who asks for parents, and when

**On request, never unconditionally.** Implied by A11.1's "optional out-param", by A12.4 (the
facade needs the table only to mint), and by A15.1's cost model ("mint always; scope only the
boundary diff"). No item states the rule in one sentence.

**Two requesters, one channel.** The domain asks by passing `parents=` (T2.4). The facade asks
when the subject handle is lineage-bearing (A15.6's definition, A12.4's use). Under A15.1 the
facade asks on every `MINT` call whose subject is lineage-bearing, diff-tracked or not.

**How it reaches the adapter:** for `dissolve`, as the `parents=` parameter (T2.4). For the other
nine, unwritten (§2.2). The wrapper is the party that would pass it: T4.3's facade wraps each
port, reads `__row_shape__`, and operations "receive no injected `lineage`" (A11.12).

**The cost is now measured, and A15.1's claim is wrong for lines.** A15.1: "Minting is
O(cardinality changes) and cheap even on context data." The findings file measures the parents
resolution for a line dissolve at 21 s added at 10^5 on a two-part key (§3.9, :240), with the
segment locator's numbers still pending (§3.10), against a plain dissolve of 1.3 s. Minting is
still O(cardinality changes); *obtaining the parents to mint from* is not cheap on lines. Nothing
in the interface changes, but the rule "ask on every `MINT` call on a lineage-bearing subject"
versus "ask only when the output is diff-tracked" is now a real cost decision, and A15.1 as
written has already taken it.

### 2.4 The layer split

- **The adapter never mints:** decided. A11.11 ("Lineage lives above the ports, not in the adapter
  and not in operation bodies"), A11.12 ("the facade mints"), A13 ("`lineage_id` created
  unconditionally on `MINT` outputs" by the lineage layer).
- **The adapter never sees `lineage_id`:** implied, not stated in that form. A12.7 says "adapters
  return plain rows and never see lineage" for the pipe. A9.2 keeps the native index behind the
  port and A11.11 makes native indices the port's vocabulary. Two qualifications the docstring
  should carry: the lineage layer writes `lineage_id` *through* the ports (`join_field`,
  `write_table`, A15.3 Path A, T3.4), so the adapter handles the column as ordinary data without
  interpreting it; and B10's duplicate-naming rule is adapter-declared data about a field name,
  not adapter knowledge of what the field means.
- **One parent carries, two or more mint:** decided, A12.4.
- **DROPPED derived from survival:** decided. A11.5 (kind derived, never declared), A11.7
  (`DROPPED` from the boundary diff, "never from a port call"), T4.6.

**Draft B17's adapter rule does not conflict.** The rule: an unmatched input raises unless it is
degenerate; it is never `DROPPED`. Against the written items:

- A11.7 says `DROPPED` comes only from the boundary diff. The rule adds no `DROPPED`; it raises,
  which is not a lineage event. Consistent.
- A degenerate unmatched input has no pair, so it is in no edge's `from_ids`, so the boundary diff
  finds its id absent from every Out and derives `DROPPED`. That is A11.7 and A12.4 operating
  normally. Consistent.
- A14's stated principle, "prefer an unavailable method to a silently wrong one", is the rule's
  own justification.

Two things the rule does introduce, neither a conflict:

1. **It is per-method.** `dissolve` never drops non-degenerate geometry; `aggregate` drops below
   `minimum_area_m2` legitimately (findings §1, `aggregate` row). So "an unmatched input is an
   error" is a `dissolve` contract line, and each `GROUP` method's docstring has to state its own
   drop semantics. That is a port-contract fact, not a mechanism fact.
2. **"Degenerate" is defined with the engine's XY tolerance** (`dissolve_parents.py:109-111`).
   If that definition is written into a port docstring, an engine concept enters the port (§2.10).
   It can stay adapter-side if the port sentence is "an input the engine discarded that was not
   empty is an error".

### 2.5 Statistics semantics

- **`statistics=` on `dissolve`:** decided (A9.10, A17.5, T2.10).
- **Per output part:** not written. It is implied by the definitions: the combining rule "reduces
  several parents' values to one" (01-terminology.md:99) and parents are "which input rows produced
  an output row" (:89). The output row is the part, so the value on a part is the rule over that
  part's parents. The measured engine behaviour (findings §3.9: both tools compute per group under
  `SINGLE_PART`) is a defect against that reading, not a redefinition of it. The findings' §10.2
  draft T2.10 wording states the port contract correctly and is unsigned.
- **Depends on parents even without lineage:** only if the adapter computes statistics from the
  parents pairs (the findings' recommendation). Then a `statistics=` call pays the parents cost on
  a handle with no lineage. That is adapter-internal and does not change the port, but the port
  docstring should not describe `statistics=` as free, and the recommendation itself is a B17
  decision.
- **The value type is unwritten.** T2.10 writes `statistics=((RANK, MAX),)`. No item defines the
  enum of statistics (`MAX`, `MIN`, `SUM`, `COUNT`, `FIRST`, and whether `CONCATENATE` is offered
  at all given §3.8's cost), nor the parameter's type. This blocks writing the `dissolve` signature.
- **BIGINTEGER not accepted by the engine's statistics** (findings §3.4, §3.8): an engine fact.
  Moot if the adapter computes statistics itself; otherwise the port must forbid `lineage_id` as
  a statistic field, which A12.11a's option for T2.8 already covers generically.

### 2.6 Contract-level facts from the investigation

| fact | written where | belongs in |
|---|---|---|
| `SINGLE_PART` on lines splits at every junction; a group is not a connected component | findings §3.9 (:267-270), §10.4 only | `dissolve` docstring in `ports/geometry_ops.py`, with A18's text (its destination) |
| `buffer_dissolve` accepts positive distances only | findings §4.1 (:363) only, as a consequence of the keyed resolver's precondition | **undecided whether it is a port rule or an adapter limit.** As a port rule it constrains every adapter for one adapter's mechanism, which is the leak this audit looks for. As an adapter limit it is a runtime error under A14 tier 4's principle, and the port docstring says nothing. The 6 real `ALL` sites (A5.6) have not been checked for a zero or negative distance |
| empty geometry is rejected before the call | findings §3.9 (:253-265), §10.5 only; §10.5 leaves the guard's owner open | if a port precondition: the `GeometryOps` class docstring, stated once for every subject; if `validate_geometry`'s job: `02-runtime.md` §2.4 as authoring guidance. Either way an error type (§2.7) |

### 2.7 Errors

**Open, and currently adapter-specific.** Nothing in DECISIONS.md or TASKS.md names an error type
a caller can see from a port call. What exists:

- `adapters/arcpy/__init__.py` lists `errors.py` among the modules "still to write", inside the
  adapter.
- `temp/dissolve_parents.py` defines `KeyMismatchError`, `LocatorContractError`,
  `UnmatchedInputError`; `temp/arcpy_part_locator.py` defines `EmptyGeometryError`. All four are
  staging, and the first two are resolver-internal.
- A14 tier 4: "the method raises on a lineage-bearing handle." With the out-param channel the
  adapter needs no lineage knowledge to do this: it raises when `parents=` is passed and it cannot
  produce them. That is one engine-neutral error, unnamed.
- A11.4a writes two message texts (design ceiling, resource ceiling) and no types. They are
  facade errors, not port errors.
- `Finding` with `Severity` is the plan-time vocabulary (02-runtime §8) and does not apply at
  runtime.

The three callers can see from a lineage-bearing port call, none named in a shared place:
parents requested and unavailable; an input the method could not have discarded is unmatched;
empty geometry in a subject. The signatures do not depend on these; the What / How / Why
docstrings do.

### 2.8 The capability record

**As written, keyed on a mechanism.** A14 (:1051-1054): probed at construction by
`arcpy.GetParameterInfo("analysis.PairwiseDissolve")`, and T4.10 "selects a tier". The record
therefore tells `validate()` which tier the adapter runs, which is exactly the leak.

**After the findings §7 rewording** ("a capability record naming the `GROUP + MINT` methods for
which it can report parents; how it reports them is adapter-internal and not in the record"),
what remains:

1. The record names `GROUP + MINT` methods only. `MANY + MINT` methods need parents for the same
   reason (A12.4), and `clip` and `difference` are the two whose engine emits no reference
   (findings §2). Reword to "every method declared `ids=MINT`".
2. The plan-time consumer has B14's gap: `validate()` cannot know which port methods a stage's
   operations call, so "fails a stage that uses a lineage-bearing handle with a method the record
   does not name" has no derivation today. Not a leak; a gap the rewording inherits.
3. The record's type is unwritten (a frozenset of method names per port is the obvious shape). Not
   a port concern.
4. "Probes at construction only for the oracle the conformance suite may use" keeps a vendor probe
   in the adapter, where it belongs.

### 2.9 Native index stability

**Written as a contract line:** A9.2, "valid until this dataset is next written"; T3.1 adds that
the adapter declares whether the index is addressable as a join key. Both are `ports/table_ops.py`
docstring text.

**Not enforced at any named point.** No assertion checks it. Two consequences for port design:

- The contract only helps a parents mechanism if the port method **does not write its `input`**
  during the call. A15.3 assumes it ("in-place mutators do not invalidate, since row identity is
  unchanged") and T4.11(3) tests it for three cartography tools only. The general sentence, "a
  port method never writes a handle named as `input`; declared in-place mutators write it without
  changing row identity", is implied and unwritten.
- A14 tier 2's work-key stamp writes a field onto the input. In a file geodatabase that keeps
  `OBJECTID`; under A9.2's letter it does not have to. An adapter that stamps must stamp a copy, or
  the contract must say that adding a field preserves the index. Adapter-internal either way.

### 2.10 Portability

In the ports as written, nothing assumes ArcGIS: the vocabulary is OGC and ICA (03-architecture
§2.2), `DissolveOption`, `EndCap` and `Relation` are project enums, and the native index is
abstracted (A9.2). Per example:

| candidate | status |
|---|---|
| OID semantics | behind the port (A9.2); addressability declared per adapter (T3.1) |
| XY tolerance as a concept | absent from the ports; it enters only if "degenerate" is written into a port docstring (§2.4) or the locator's search radius is named there. Keep it adapter-side |
| `SINGLE_PART` as a term | already a project enum member; the vendor's spelling, but the concept (one row per connected part) is engine-neutral. The open point is A5.6 versus A18 (§6) |
| BIGINTEGER rejected by engine statistics | engine limit; moot if statistics are computed from parents; otherwise covered by forbidding `lineage_id` in a statistic field (A12.11a option) |
| `FieldType.BIGINT` | cited by A10.1 and A13; absent from the template `FieldType` (`table_ops.py:34-41`). B1 / T0.1, known |

### 2.11 Toolbox call site

`tb.geometry.dissolve(input=roads, output=dissolved, fields=(ROAD_CLASS,),
option=DissolveOption.SINGLE_PART)` at `operations/road/__init__.py:648-653` needs no change for
any mechanism. The two parameters the tasks add, `statistics=` (T2.10) and `parents=` (T2.4),
exist for domain reasons: a combining rule and a domain-consumed parent set. The facade's own
request for parents travels facade-to-port, never through the call site. **No call-site argument
exists because of a mechanism.** The one condition is that the facade's channel is the same
out-param, so that a domain `parents=` and a facade request do not need two parameters.

---

## 3. Items to land now

Each blocks writing a port signature or a decorator. A-item text is used where the written items
already force the content; B-item text lists the options where a decision is still needed.
Mechanism choices stay in B17.

### 3.1 The parents channel on every `MINT` method — A-item text, forced by T4.11, A12.4, B6

```
**A11.15 Parents are an out-param on every `MINT` method, in native indices at the port.**

Every port method with an output declared `ids=MINT` carries
`parents: ScratchHandle | None = None`. When it is not `None` the adapter writes a TABLE of
`(PARENT_ID, CHILD_ID)` rows to it, one row per (input row, output row) pair, both columns in
the port's own vocabulary: the input's native index and the output's native index (A11.11).
When it is `None` the adapter produces no parents and pays nothing for them.

The lineage facade is a caller. It passes a scratch handle on every `MINT` call whose subject
is lineage-bearing (A15.6), reads the pairs, maps them to `lineage_id` and mints (A11.11,
A12.4). This is why the channel is on the Protocol and not private to the facade: the
conformance suite drives the Protocol directly (T4.11, B10) and asserts the reported pairs.

The domain may pass its own handle. What the domain receives is the same relation in
`lineage_id`, because the native index is behind the port (A9.2) and the domain has nothing to
join it to. The facade performs that translation; whether by rewriting the domain's handle or
by writing a second table is T4.3's choice.

Supersedes T2.4's "only `dissolve` gets the parameter" and narrows B6 to the domain-facing
question: which methods have a domain caller wanting the set. B6 is otherwise unchanged.

`destination:` `ports/geometry_ops.py` and `ports/cartographic_ops.py` (the parameter, once per
method); the lineage module docstring (the facade's use).
```

Affects: T2.4 (nine more signatures), T2.9 (the split methods land with the parameter), T4.11(1)
(how the suite obtains the pairs), findings §7 row 1 (the record covers every `MINT` method).

### 3.2 `dissolve` option versus `dissolve_multipart` — B-item text, decision needed

```
**B18. `dissolve` has two written signatures.** A5.6 keeps `option: DissolveOption` as an
argument on the ground that it does not move the row-shape cell. A18 and T2.9 say a multipart
dissolve, if ever needed, "becomes a separate `dissolve_multipart` method rather than an
argument, which is what keeps `@row_shape` static". Both cannot be the port. The template has
the argument (`geometry_ops.py:242-248`) and every template caller passes `SINGLE_PART`.

Options: (a) keep the argument, per A5.6, and strike the `dissolve_multipart` sentence from
A18 and T2.9; (b) drop the argument, make `dissolve` single-part by contract, and add
`dissolve_multipart` when a caller appears, per A18. Under (b) the findings' §3.9 note that
`SINGLE_PART` splits lines at every junction becomes the whole of `dissolve`'s output contract
rather than one branch of it.

Resolves when one of the two sentences is struck.
`destination:` `ports/geometry_ops.py`, `dissolve` docstring.
```

### 3.3 The `statistics` value type — B-item text, decision needed

```
**B19. `dissolve(statistics=…)` has an example and no type.** T2.10 writes
`statistics=((RANK, MAX),)`. Nothing defines the statistic vocabulary, the parameter type, or
whether a text concatenation is offered at all. The findings measured CONCATENATE at 7,841 s
over one 10^6 group (§3.8), so offering it is a cost decision, not a completeness one.

Needed before the signature is written: a project enum of statistics (project enum, never
vendor strings, 03-architecture §2.3), and `statistics: tuple[tuple[FieldName, Statistic], ...]
= ()` or an equivalent. Per-output-part semantics are stated separately (§3.5 of the readiness
audit) and do not depend on this.

`destination:` `ports/geometry_ops.py`, beside `DissolveOption`.
```

### 3.4 A12.5a sign-off — already drafted

`PROPOSALS-2026-09-14.md` §2 proposes annotating port handle parameters `In`/`Out` (a third marker
for in-place mutators, owned by T2.8), so that T4.1's output-parameter rule can fire. The
proposal defers it to T4.1's scope "so as not to annotate signatures that are about to change".
Designing the ports now inverts that reasoning: the ports are about to be written, and the
annotation should be written with them, once. Sign off the A-item and pull its timing forward
to the port-writing pass. No new text needed.

### 3.5 Per-output-part statistics — A-item text, forced by the definitions

Not blocking a signature; blocking the `dissolve` docstring, and cheap to write now.

```
**A9.11 A combining rule is evaluated over the parents of each output row.** The
combining rule "reduces several parents' values to one" (01-terminology.md, combining rule);
parents are "which input rows produced an output row". So the value written on an output row of
a `GROUP` method is the rule over that row's parents and nothing wider. Under `SINGLE_PART` a
dissolve key that splits into several parts has several output rows, each with its own parent
set and its own value. An engine whose statistics option computes over the whole key (measured on
Pro 3.7.2 for both `Dissolve` and `PairwiseDissolve`, findings §3.9) does not implement this
contract, and the adapter must not use that option to satisfy it.

`destination:` `ports/geometry_ops.py`, `dissolve` docstring; A11.14 gains a pointer.
```

The mechanism by which the adapter meets this (its own group-by over the parents pairs, the
findings' recommendation) stays in B17.

---

## 4. Items that can safely wait

Each with the reason deferring it cannot change a port, a decorator or the call site.

- **Which mechanism produces `dissolve` parents** (B17: keyed resolver, native table, both). The
  Protocol sees `parents: ScratchHandle | None` and a pair table; every candidate writes that
  table. Adapter-internal by A11.11 and A14's first sentence.
- **The locator choice for lines** (point versus segment, findings §4). Inside the mechanism.
- **The native lineage table as conformance oracle.** Test code, and it consumes the same pair
  table.
- **The capability record's shape and its probe.** The record is data handed to `validate()`
  (A14); its type is a runtime and validation concern. The §7 rewording plus "every `MINT` method"
  is the only interface fact, and it is in §3.1.
- **A15.7, the time budgets** (findings §6). They judge mechanisms. They do not name a port. They
  do bear on §2.3's "ask on every `MINT` call" versus "ask only when diff-tracked", which is a
  facade rule, not a port rule; A15.1 already states the facade rule, and revisiting it changes
  the facade's condition for passing `parents=`, not the parameter.
- **The empty-geometry guard's owner** (`validate_geometry` versus the adapter, findings §10.5).
  Either way the port gains one precondition sentence and one error type; the signature is
  unchanged. Land it with §2.7's error vocabulary.
- **`buffer_dissolve` positive-only.** A docstring sentence if it becomes a port rule, a runtime
  error under A14 tier 4 if it stays an adapter limit; `distance_m: float` is unchanged either way.
  Check the 6 `ALL` call sites before choosing.
- **The error vocabulary** (§2.7). Names in a shared `ports/errors.py` or equivalent change no
  signature; they change docstrings and `except` clauses. Write it in the same pass as the ports,
  but the ports can be drafted without it.
- **The statistics-from-parents dependency** (§2.5). Adapter-internal; the port docstring says
  only that `statistics=` is not free.
- **Native-index enforcement point** (§2.9). A contract line today; an assertion is a T4.11 case.
- **B14, the plan-time derivation of lineage-bearing.** A validation and runtime gap. The decorator
  is the same whether or not `validate()` can read it.
- **`SINGLE_PART` splits at junctions.** A docstring sentence (§2.6, paste from findings
  §3.9:267-270); it can be written the day `dissolve`'s docstring is written.

---

## 5. Reference sketch from decided items only

Python 3.11, keyword-only, no adapter internals. Every element not decided is marked `# OPEN`.
`Cardinality` and `Ids` are placeholder enum names: A12.1 fixes the values, not the class names.

```python
"""Sketch only. Three methods, one per cardinality, as the written decisions allow."""

from __future__ import annotations

from typing import Protocol

from ag.core.operations import ScratchHandle  # OPEN: A12.5a would make these In / Out
from ag.ports.geometry_ops import DissolveOption, Predicate
from ag.ports.row_shape import Cardinality, Ids, Rows, row_shape  # T4.1
from ag.ports.table_ops import FieldName


class GeometryOps(Protocol):
    # -- ONE + CARRY --------------------------------------------------------
    # A12.11: select is ONE + CARRY, subject `input`. No parents: ids ride along
    # as attributes (A11.12). The facade's post-call assertion that `lineage_id`
    # survived is B10, a proposal.

    @row_shape(output=Rows(cardinality=Cardinality.ONE, ids=Ids.CARRY, subject="input"))
    def select(
        self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle
    ) -> None:
        """Materialize the features matching `where`."""
        ...

    # -- MANY + MINT --------------------------------------------------------
    # A12.11: clip is MANY + MINT, subject `input`, context `boundary`.

    @row_shape(
        output=Rows(
            cardinality=Cardinality.MANY,
            ids=Ids.MINT,
            subject="input",
            context="boundary",
        )
    )
    def clip(
        self,
        *,
        input: ScratchHandle,
        boundary: ScratchHandle,
        output: ScratchHandle,
        # OPEN: parents channel. T2.4 gives `parents:` to `dissolve` only; A12.4
        # needs pairs here to mint. §3.1 proposes the same out-param on every
        # MINT method.
    ) -> None:
        """Dataset-level, unlike `intersection`, which is geometry-level."""
        ...

    # -- GROUP + MINT -------------------------------------------------------
    # A12.11: dissolve is GROUP + MINT, subject `input`.

    @row_shape(output=Rows(cardinality=Cardinality.GROUP, ids=Ids.MINT, subject="input"))
    def dissolve(
        self,
        *,
        input: ScratchHandle,
        output: ScratchHandle,
        fields: tuple[FieldName, ...] = (),
        option: DissolveOption = DissolveOption.SINGLE_PART,  # OPEN: A5.6 keeps, A18 removes (B18)
        # OPEN: statistics value type (B19). T2.10: statistics=((RANK, MAX),)
        parents: ScratchHandle | None = None,  # T2.4: TABLE of (PARENT_ID, CHILD_ID)
    ) -> None:
        """What: one output row per connected single part of each dissolve-key group.

        How: `parents`, when given, receives one (PARENT_ID, CHILD_ID) row per
        contributing input row, in native indices (A11.11).
        # OPEN: id space of the columns as the domain sees them (§2.2).
        # OPEN: "SINGLE_PART on lines splits at every junction" (§2.6), once B18 settles.
        # OPEN: drop semantics ("never discards non-degenerate geometry") and the
        #       error a caller sees (§2.4, §2.7).

        Why: a collapse that cannot say which input rows it combined is
        under-specified as a collapse (A11.11).
        """
        ...
```

**How parents are requested** (decided parts only):

```python
# Inside the lineage facade (T4.3). Reads GeometryOps.dissolve.__row_shape__ from the
# Protocol, never from the adapter (A11.11).

def dissolve(self, *, input: ScratchHandle, output: ScratchHandle, **kwargs) -> None:
    shape = GeometryOps.dissolve.__row_shape__["output"]        # A11.11, T4.1
    wants_parents = shape.ids is Ids.MINT and self._lineage_bearing(input)  # A15.6, A12.4
    # OPEN: whether `wants_parents` is also conditioned on diff-tracked (A15.1 says no;
    #       §2.3 records the measured cost that makes this a live decision).
    parents = kwargs.get("parents")
    if wants_parents and parents is None:
        parents = self._scratch("parents", TABLE)               # facade-owned handle
        # OPEN: only decided for `dissolve`; §3.1 makes it every MINT method.
    self._port.dissolve(input=input, output=output, parents=parents, **kwargs)
    if wants_parents:
        pairs = self._read_native_pairs(parents)                 # native indices, A11.11
        self._mint_from_pairs(input=input, output=output, pairs=pairs)  # A12.4: 1 parent carries, >=2 mint
        # OPEN: if the domain passed its own `parents`, what it now holds (§2.2).
```

**Where statistics are computed:** `# OPEN`. The contract is per output part (§3.5). Whether the
adapter meets it through the engine (measured wrong under `SINGLE_PART`) or by its own group-by
over the parents pairs is B17's, and never appears above the port.

---

## 6. Contradictions

Between DECISIONS, TASKS, terminology and the findings file. Line references as of 2026-09-17.

1. **A5.6 versus A18 / T2.9 on `dissolve`'s `option`.** DECISIONS.md:165-166 keeps
   `dissolve.option` as an argument ("does not move the cell, so no split"); DECISIONS.md:1363-1364
   and TASKS.md:948-951 say a multipart dissolve "becomes a separate `dissolve_multipart` method
   rather than an argument". §3.2.
2. **T2.4 / B6 versus A12.11 + A12.4 on where parents come from.** TASKS.md:1019-1021 and
   DECISIONS.md:1619-1621 give `parents:` to `dissolve` only, because no domain caller wants the
   others. DECISIONS.md:841-846 has the facade mint from the parents table on every `GROUP` and
   `MANY` method. Nine `MINT` methods have no written channel. §3.1.
3. **A11.1 versus A11.11 versus A9.2 on the parents table's id space.** DECISIONS.md:530-531
   (domain consumes the parent set), :727-728 (the port reports native indices), :346-347 (the
   native index is behind the port). The three are jointly satisfiable only with a facade
   translation that no item names. §2.2.
4. **A15.1 versus the measured cost of parents.** DECISIONS.md:1068-1069 ("cheap even on context
   data") against findings §3.9:240 (21 s added at 10^5 for a two-part line key) and §3.10's
   pending segment-locator numbers. The rule may still be right; its stated justification is not.
5. **A14 versus the findings on two tool facts and one tier.** DECISIONS.md:1041-1042 says
   `ORIG_FID` from `Intersect`; findings §2:64 says `FID_<input>`. DECISIONS.md:1043-1046 says
   tier 2 "is what runs until the image is rebuilt"; findings §3.8-3.9 measure it over budget and
   wrong on every split group. DECISIONS.md:1039 undercounts tier 1 (findings §1, B17 draft).
   Already listed in findings §7; repeated here because T0.1 case 12 (TASKS.md:275-288), T4.10
   (TASKS.md:1615-1621) and T4.11(1) (TASKS.md:1647-1649, "passes under both capability tiers")
   still carry the tier vocabulary and the retired tier.
6. **A14's plan-time capability check versus B14.** DECISIONS.md:1052-1054 fails at plan time "a
   stage that dissolves on a lineage-bearing handle with an incapable adapter"; DECISIONS.md:
   2050-2056 records that plan time cannot see which port methods a body calls. The check has no
   derivation, before or after the §7 rewording.
7. **Terminology `row shape` entry versus T4.1.** 01-terminology.md:90 writes
   `@row_shape(out=Rows(...))`; TASKS.md:1281 writes `@row_shape(**outputs: Rows)` keyed by the
   output parameter's name, and A12.11 keys `simplify.collapsed_points`. Cosmetic if `out` is an
   example; misleading if read as a fixed keyword.
8. **Findings §5 versus the checkout.** findings :33-34 and :383-384 say `template_code/ag/` is
   not in this checkout. It is, at `docs/refactor/template_code/ag/`. The call-site counts in §1
   were taken over `generalization/` and `custom_tools/` for that reason and are still valid
   counts of the current repository; the "location is staging because the gate imports the
   modules" reasoning stands on its own.
9. **Findings §3.9 note versus A18's silence.** The findings ask that "`SINGLE_PART` splits at
   junctions" be stated in `dissolve`'s contract via A18 (§10.4). A18 (DECISIONS.md:1356-1365) is
   about the single-part *assertion* being debug-mode and says nothing about what a group is.
   Not a contradiction; the sentence has no home until B18 settles which method it describes.
10. **`FieldType.BIGINT`** is cited by A10.1 (DECISIONS.md:421) and A13 (:1029) and absent from
    the template enum (`table_ops.py:34-41`). Known: B1, T0.1.
11. **T4.11(1) obtains "the reported parents" from the Protocol**, and the Protocol has no parents
    channel except `dissolve`'s (TASKS.md:1647-1649 against :1019). Same root as item 2, listed
    because it is the sentence that fixes the channel's location (§2.2).

---

## Summary

- **Verdict:** ready to design ports and decorators once §3.1 to §3.4 are written. The working
  assumption holds: native index pairs at the port, `lineage_id` above it, no mechanism in any
  signature, decorator or call site. The leaks are confined to A14, T4.10, T4.11 and T0.1 case 12.
- **Blocking:** the parents out-param on every `MINT` method, not only `dissolve` (§3.1); the id
  space of the parents table at the port and at the domain boundary (§3.1); `option` versus
  `dissolve_multipart` (§3.2); the `statistics` value type (§3.3); A12.5a sign-off (§3.4).
- **Not blocking, cheap now:** per-output-part statistics as a contract line (§3.5).
- **Decide first:** §3.1. It is forced by three written items (T4.11 drives the Protocol; A12.4
  mints from the pairs; B6 fixed the parameter shape), it changes ten signatures, and every other
  open item is either a docstring sentence or adapter-internal.
- **Decide second:** B18, because `dissolve` is the method the sketch and the conformance case
  are written against.
- **Revisit, not now:** A15.1's "ask on every `MINT` call" against the measured line cost (§2.3),
  once the segment-locator numbers and A15.7's budget are recorded.
