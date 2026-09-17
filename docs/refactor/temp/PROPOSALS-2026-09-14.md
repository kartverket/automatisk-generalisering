# Proposals awaiting sign-off, 2026-09-14

**Status:** TEMPORARY. Written in response to REVIEW-2026-09-14.md. Nothing here is settled. Each
section is a recommendation that the user accepts or amends. The A-item is written into
DECISIONS.md only after that. Delete this file once every section has been resolved into
DECISIONS.md or rejected.

Sections:
1. B9: which artifacts carry `lineage_id` across a run boundary
2. B12 (F6): T4.1's check has no way to find an output parameter
3. B13 (F5): writes have no row shape, and A12.7 contradicts A15.6

---

## 1. B9 — which artifacts carry `lineage_id` across a run boundary

### Recommendation in one paragraph

**The archive keeps the working schema, including `lineage_id`.** A **delivered copy** is a
separate artifact made by a publish step that applies the consumer schema. It carries two things:

- the `lineage_id` value under a non-identity name;
- a per-row identifier for the run that produced it.

Hop 1 is then intact by construction. Hop 2 is one join, against an archive version guaranteed to
still exist.

### Hop 1: cross-run ingest. Recommended: the archive carries `lineage_id`.

Two independent arguments reach this, and neither depends on hop 2.

- **B9(d)** forces the **in-run** stage output to carry `lineage_id`. `N100_ROAD` is a CONTEXT
  input to building `DISPLACEMENT` in the same run (`pipelines/building/n100_stages.py:128-132`),
  and A16's verification of that stage reads the column.
- **`n100_stages.py:161` together with A22** (the docstring opens at :158, which is what B7 and
  B9 cite; the quoted sentence is at :161) forces the **archive** to match the in-run output.
  One `StageInput` pins to the stage output in-run and to the archive otherwise (§6.2). If the two
  schemas differ, the same feature traces completely in one run selection and hits `LOST_HISTORY`
  in another. That violates A22's "no separate code path, no mode flag".

Consequences:

- A24.1's map-only row becomes reachable. T0.6(b), T3.4's map-only branch and T3.7(a)'s stage-entry
  guard all have a subject.
- The edge log and ingest map that T3.6 archives key into ids a readable product actually carries.
- **The archive stops being the consumer schema.** Today N100_ROAD's archive location
  (`gs://kv-products/n100/road.gdb`, `products.py`) *is* what consumers read
  (`products.py` docstring: "consumers read the archived version at this location"). Under this
  recommendation it is what **pipelines** read. That is the largest change, and it is why hop 2
  needs a location of its own (open question Q1 below).
- **Classification is unaffected.** `lineage_id` values come from our own allocator and encode
  nothing about the source, so `reclassify_to` at the Publish carries over to both artifacts.

### Hop 2: consumer diagnosis. Recommended: lineage value under a non-identity name, plus a run id.

**Options weighed:**

| option | hop cost | new artifacts | cost to A19 |
|---|---|---|---|
| no key | spatial lookup against the archive | none | none |
| **`lineage_id` value, non-identity name, plus run id** | **one join** | **none** | protection becomes naming plus documentation |
| a third id | one join plus a map lookup | an allocator and a published-key → `lineage_id` map with its own retention | none on paper; in practice the same, since that id is also run-scoped |

**Why the second.** Diagnosis speed ranks first. The third option costs an allocation site and a
retained map, and its id is no more stable than `lineage_id`: it is minted per run too. So it buys
only a name that looks safer. A19's real objection is consumers binding to an identity that
re-mints. A run-id column on the same row makes the re-minting visible in the data itself, since a
key is meaningless without the run it came from. It is a stronger signal than a name.

**Stated honestly, the cost:**

- A19's protection becomes naming plus documentation rather than absence. A consumer who keys on
  the column across deliveries gets an identity that changes under them, and nothing technical
  stops them.
- **The key only helps while the consumer's copy still has the column.** Consumers load products
  into their own databases, reproject and clip them. A report that arrives as "this road at this
  location" is a spatial lookup against the archive with or without the key. The key speeds up
  the case where the consumer can hand back a row. It does not remove the spatial path.

**The run identifier is a per-row column, not only dataset metadata.** File-geodatabase metadata
and sidecar manifests are lost on the first load into another system; a column is not. It is
constant per delivery and compresses to almost nothing.

### What changes in publish when mapping moves out of `finalize_road_attributes`

B9(a) verified that mapping is inside the operation today: `finalize_road_attributes` calls
`_apply_product_schema` at `operations/road/__init__.py:947`.

1. **The operation stops mapping.** `finalize_road_attributes` ends at `flagged → output`.
   `_apply_product_schema` is deleted from `operations/road/`. `ROAD` leaves the stage with the
   working schema: `FEATURE_ID`, `ROAD_CLASS`, `RANK`, `edited`, `lineage_id`, geometry.
2. **The mapping is declared with the publication**, not in an operation body. It is a product
   property. `Publish` already carries the one other per-product human judgement, `reclassify_to`
   (`core/pipeline.py:195`), so the natural home is `Publish(obj=ROAD, identity=N100_ROAD,
   reclassify_to=…, delivered_schema=…)`. The alternative is `ProductIdentity`. Choosing between
   them is part of the new publish task, not this proposal. The `Publish` home keeps
   `products.py` a leaf with no field vocabulary.
3. **A publish step executes it.** It is stage-level data movement under B10's principle. It
   produces the delivered copy outside the facade, and it resolves B10's "the publish step — pending
   B9" row. It needs a `TableOps` for `map_fields`, so it runs where ports exist: fan-in or a
   dedicated publish job. That is the new task's decision.
4. **A9.6 stops holding for `ROAD`.** It says the work-key sweep is redundant on `ROAD` because
   product mapping drops unmapped fields. With mapping moved, the sweep is the only protection on
   the archive, as it already is for `ROAD_RANKS`, `SNAP_DISPLACEMENT` and `JUNCTION_POINTS`. On
   the delivered copy the mapping still drops them.
5. **A13's last bullet moves.** "Publish-time removal has the same gap as the work-key sweep" now
   describes the delivered copy only. The archive does not remove `lineage_id`.
6. **B10's post-call assertion does not apply to the delivered copy.** The copy is not
   lineage-bearing by design, and the publish step is not an operation. Its own check is that the
   mapped key column and the run-id column exist. That is one `describe_fields`, the same shape as
   B10's assertion.
7. **The other two publications need no delivered copy** unless they have a consumer schema.
   `JUNCTION_POINTS` and `SNAP_DISPLACEMENT` are published unmapped today. They stay single-artifact:
   the archive is also what their consumers read. `delivered_schema` is optional on `Publish`.

### B9(b)2: the two retention questions

**Is every delivered version guaranteed a retained archived counterpart?** Recommended: **yes, by
two rules.**

- **Archive versions are immutable.** A re-run writes a new version and never replaces one. §6.2
  already pins every identity to a concrete version at plan time. Nothing states that a version,
  once written, is never overwritten, and replacement would strand every key held by consumers of
  the copy it replaced.
- **An archive version, with its edge log and ingest map (A21, T3.6), is retained at least as long
  as any delivered copy made from it is supported.** The duration is a policy decision this
  proposal does not make (Q2).

**Does the delivered product record which run produced it?** Recommended: **yes**, as the per-row
run-identifier column above. Without it, the same key names a different feature in every run, and
a consumer's report cannot say which one they hold.

### Open questions this proposal cannot answer

- **Q1. Where does the delivered copy live?** The design has one location per `ProductIdentity`,
  and today it serves both pipelines and consumers. Options include a second location on the
  identity, a delivery location derived by `locations.py`, or an external delivery system outside
  this project.
- **Q2. How long is a delivered version supported?** This sets the retention floor for the archive
  version.
- **Q3. Are there internal non-pipeline readers of the archive** (for example, cartographers
  opening it in Pro)? If so, they see the working schema after this change.

### Tasks that change once B9 resolves this way

| task or item | what changes |
|---|---|
| **T0.4** | Unblocked. No longer "drop or rename". The delivered copy carries the `lineage_id` value under a non-identity name chosen here, plus the run-id column. Files grow from `operations/road/__init__.py` to the `Publish` declaration; the mechanism moves to the new publish task. |
| **new publish task** (proposed id **T3.8**, placed after T3.6) | The publish step: `delivered_schema` on `Publish` (or `ProductIdentity`), where the step runs, the delivered-copy location (Q1), the key and run-id columns, and its own existence check. Resolves B10's pending exemption row. Doc migration: the resulting A-item into `02-runtime.md` §2.2 and §4.1. |
| **T0.6(b)** | Unblocked, since map-only is reachable. Revise the comparison first, as T0.6 already says: fan-out's join and T3.7(a)'s check are paid on every run. |
| **T3.4** | The map-only branch is reachable. State that ingest reads the **archive** version, never a delivered copy. |
| **T3.6** | Two rules added: archive versions are immutable, and are retained for at least the support life of any delivered copy made from them (Q2). The run-id column is what ties a delivered copy to its archive version. |
| **T3.7(a)** | The stage-entry guard has a subject. Not otherwise changed here. The review's F3, that the multiset check cannot run per pod, is a separate finding and is not acted on. |
| **T6.2** | A second entry point: a delivered key plus run id resolves to an archive version's `lineage_id`, then the ordinary walk. The resolver needs a run id → archive version lookup. |
| **B10** | The "publish step — pending B9" row gets its task (T3.8) and its reason: it produces the delivered copy and is not an operation. |
| **A9.6** | Amended: the sweep is no longer redundant on `ROAD`. |
| **A13** | Last bullet scoped to the delivered copy. |
| **A19 / B3** | A19's "cheap insurance" is resolved by T0.4 as above. B3 (a stable published identity) stays open and is untouched. |
| **01-terminology.md** | **Publish** gains the delivered copy. **archive** says pipelines read it. New entry **delivered copy**. |
| **02-runtime.md** §2.2, §4.1 | Publish produces two artifacts when a delivered schema is declared, and archive versions are immutable. |

---

## 2. B12 (F6) — T4.1's check has no way to find an output parameter

### Verified

- Every handle parameter on `GeometryOps`, `TableOps` and `CartographicOps` is annotated
  `ScratchHandle`. There is no direction.
- `In` and `Out` are `Annotated[ScratchHandle, Direction.IN/OUT]` in `core/operations.py:217-235`.
  They are used only by operations, where `@operation` reads them with
  `get_type_hints(include_extras=True)` (`core/operations.py:560`).
- T4.1's check "rejects an output parameter with no declaration". With no direction on port
  parameters, the only way to know a parameter is an output is the declaration being checked. The
  rule cannot fire.
- **Scratch run, no template edit.** `get_type_hints(include_extras=True)` on a `Protocol` method
  keeps `Annotated` intact, including inside `tuple[In, ...]` and `Out | None`. Every public method
  of the three Protocols resolves under `get_type_hints` today, so no annotation is hidden behind
  `TYPE_CHECKING`.

### Options weighed

| option | fires on an undeclared output? | weakness |
|---|---|---|
| parameter-name convention (`output`, `parents`, …) | only for names on the list | green by coincidence the first time a method names its output `errors` or `dropped` |
| every `ScratchHandle` parameter must appear in some declaration, as output key or as subject/context/ref | yes | cannot say whether the parameter is an undeclared output or an unclassified input, so the message cannot name the fix; **passes an output mis-declared as `context=`**; forces a `context=` for every non-subject input (`snap.reference`, `split_at_points.points`, `collapse_to_centerline.pairs` have none in A12.11) |
| **annotate port handle parameters with `In` / `Out`** | **yes** | touches every Protocol signature once; in-place mutators need a third marker |

### Recommendation

**Annotate port Protocol handle parameters with the existing `In`/`Out` aliases.** The T4.1
check walks `tuple` and `Optional` arguments to the `Annotated` inside, then rejects:

1. an `Out` parameter with no `@row_shape` entry;
2. a `@row_shape` key naming a parameter that is not `Out`;
3. a `subject`, `context` or `refs` value naming a parameter that is not `In`.

Rules 2 and 3 are what the "named by some declaration" option cannot express.

The recommendation adds no layering edge, since the ports already import `ScratchHandle` from
`ag.core.operations`. It needs no adapter change, because `Annotated[ScratchHandle, …]` is
`ScratchHandle` to pyright and structural typing is unchanged. And it reuses the mechanism
`@operation` already has.

**In-place mutators need a third marker.** `calculate_field.input` is neither read-only nor a new
output. That is exactly A12.6's missing "definition of output parameter that covers them", which
T2.8 owns. The marker's name and home are T2.8's to settle. So **T4.1 gains a dependency on T2.8**:
its check cannot classify a mutator's handle until that definition exists.

**Timing: in T4.1's scope, not now.** T2.9 splits four methods, T2.4 adds `parents`, T2.2 adds
`update_rows` and T2.10 adds `statistics`. Annotating before them means annotating signatures that
are about to change, and with no check yet to keep new ones honest. At T4.1 the annotation and the
check land together, and the check is what makes the annotation non-optional. T4.1 sits after all
of those at position 22.

### Proposed A-item

**A12.5a** — *T4.1's output-parameter rule needs a direction on port parameters.* Port Protocol
handle parameters are annotated `In`/`Out` from `core.operations` (a third marker for in-place
mutators per T2.8). The CI check applies rules 1 to 3 above. Rejected: the naming convention, and
the "named by some declaration" rule, both for the reasons in the table.

- `destination:` `ports/row_shape.py` docstring; `02-runtime.md` §8 with A12.5.
- **migrating task:** T4.1.

**T4.1 acceptance additions:**

- every port handle parameter carries `In`, `Out` or T2.8's mutator marker;
- the check applies rules 1 to 3;
- **break it on purpose once**: remove one `@row_shape` entry and one `Out` annotation, and confirm
  each fails with its own message.

**T4.1 depends on** T2.4, T2.8.

---

## 3. B13 (F5) — writes have no row shape, and A12.7 contradicts A15.6

### Verified against the template

- **`_vertex_deltas` (`operations/road/__init__.py:299-329`).** `paired` is the output of
  `nearest_neighbors` over two `extract_vertices` outputs. `write_table` at :322 pipes
  `read_rows(input=paired)` into `output`. The caller `snap_to_source_geometry` passes
  `output=displacement` (:776-779), which is `Network.displacement` →
  `StageOutput(obj=SNAP_DISPLACEMENT)` (`pipelines/road/n100.py:300`). `paired` is
  `FOREIGN`-terminal, so the rows are untracked, and the output is diff-tracked. **A12.7's rule
  errors. A15.6 says this output is legal.** Confirmed.
- **`merge_divided_highways` (:592-596).** `paired` is `_pair_carriageways`' output, a
  `spatial_join` (:611), so it is `FOREIGN`. The write target `merge_report` is not a
  `StageOutput`. It is diff-tracked **only transitively**: `thin_road_network` reads it, and that
  operation's output reaches `snapped`. A15.2's "reaches a `StageOutput`" does not say whether
  reaching through an input that only feeds a predicate counts. **Under the literal reading the
  rule errors here too.** Under a narrower reading it does not. Either way the first site is
  enough to establish the contradiction.
- `write_rows` and `write_table` have an `output` parameter (`ports/table_ops.py:209-225`) and no
  row in A12.11 or A12.11a.

### The core problem

The ids axis of a write is **intent**, and only the author has it. Untracked rows reaching a
diff-tracked output can mean two different things:

- a legitimate `FOREIGN` table (`SNAP_DISPLACEMENT`);
- a `CARRY` whose lineage was lost when rows were rebuilt in Python.

Nothing can tell the two apart from the rows alone. A12.7's rule picked "lost" for every case. The
reviewer's second suggestion, deriving the axis from the pipe's source, picks "whatever the source
was", and so can never detect the loss.

### Options weighed

| option | detects lost lineage | plan-time visible | depends on the pipe mechanism (F25) |
|---|---|---|---|
| derive the axis from the pipe's source handle | **no** — it infers from the rows the rule is meant to judge | only if the recording spy tags `read_rows` iterables, which is F25's question | yes |
| declare the axis on the handle (`handle(TABLE, ids=…)`) | yes, for declared handles | yes | no — but contradicts A15.2 and A15.6 ("derived, never declared") and does not reach `scratch(…)` handles |
| a new port method `export_table(input, output, fields)` declared `ONE + CARRY` | yes, for untransformed pipes | yes | no — but a `FOREIGN` input then trips A12.9 (see B14), and Python-built rows still need something else |
| **a required call-site declaration on `write_rows` / `write_table`** | **yes** | **yes, through the recording spy's recorded arguments** | **no** |

### Recommendation

**`write_rows` and `write_table` take a required keyword declaring the output's ids axis, with
handles rather than parameter names:**

- **CARRY from a source handle.** Rows carry that handle's `lineage_id`, verified by whatever T4.4's
  pipe mechanism turns out to be.
- **FOREIGN with refs as a column → handle mapping.** No `lineage_id`; the named columns hold the
  handles' ids.
- **MINT.** Each row's id comes from `mint(parents=…)`, as A11.12 already permits for Python-built
  rows.

The spelling, whether a `Rows`-like value or three small constructors, is T4.4's to settle.
Required, with no default, so pyright reports an omission at the call site. That is A12.5's
"forgetting is impossible", extended to the one row-producing method it could not reach.

Why this and not the others:

- It puts the declaration where the intent is. It is write-only for domain code: nothing reads it
  back. So it is the same class of statement as `mint(parents=…)` and does not reopen A11.12 or
  A12.7's `Row.parents` rejection.
- **It decouples the axis from the pipe mechanism.** A12.7's tracked iterable (or F25's
  attribute-stamping alternative) becomes the **verification** of a `CARRY` declaration, not its
  source. F25 stays open and unaffected.
- It is visible without data. The recording spy records call arguments, so a plan-time derivation
  (B14) can read it.

**A12.7's error rule is amended** from "untracked rows written to a scoped output with no explicit
mint is an error" to three checks:

- **CARRY:** the rows carry the source handle's ids.
- **MINT:** every row carries a mint.
- **FOREIGN:** no `lineage_id` is written, and the ref columns exist.

`SNAP_DISPLACEMENT` declares `FOREIGN`, and the contradiction is gone. A12.7's promise of "no
call-site change" is withdrawn. It was wrong for two of its four sites, and the remaining two gain
one keyword each.

**Not recommended, and the branch stops here:** deriving the axis from the pipe's source at plan
time needs the spy to tag `read_rows` iterables and follow them into `write_*`. That is the same
object-identity mechanism F25 challenges. Adopting it would decide F25 as a side effect, so it is
listed rather than pursued.

### One sub-question the recommendation exposes, not decided

**What a ref column holds when the ref names a `FOREIGN` handle.** In `_vertex_deltas` the natural
refs for `displacement` point at the road features. But `paired`'s own refs point at **vertex rows**
from `extract_vertices`, and vertex rows carry no `lineage_id`. The column that reaches the write
has to be the carried `VERTEX_SOURCE`, joined through (A11.13). A12.11's refs definition,
"declared columns hold subject ids", does not say what happens when the subject is itself
`FOREIGN`. Recorded in B13; T4.4 has to state it.

### Proposed A-item

**A12.7a** — *Writes declare their ids axis at the call site.* This supersedes A12.7's "four sites
carry lineage with no call-site change" and its error rule. The content is the recommendation above.

- `destination:` `ports/table_ops.py` (`write_rows` and `write_table` docstrings); the lineage
  module docstring (the three checks).
- **migrating task:** T4.4.

**T4.4 acceptance additions:** the five template write sites, each with its declaration:

| site | declaration |
|---|---|
| `:243` `nodes` (`_build_topology`) | MINT |
| `:322` `displacement` (`_vertex_deltas`) | FOREIGN, refs to the road features through the carried `VERTEX_SOURCE` |
| `:453` `match_report` | CARRY from `unmatched` |
| `:542` `rank_table` | CARRY from `penalised` |
| `:592` `merge_report` | FOREIGN, refs to `candidates` |

Plus: omitting the keyword is a pyright error; a `CARRY` write whose rows were rebuilt without ids
fails with a message naming the write; `SNAP_DISPLACEMENT` passes.

**T4.4 depends on** T4.3, T4.1 (the `ids` values are T4.1's types).
