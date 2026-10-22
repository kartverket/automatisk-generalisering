# Proposals awaiting sign-off, 2026-10-14 (revised 2026-10-16)

**Status:** TEMPORARY. Written for the input-role model the architect settled on 2026-10-12.
Nothing here is settled until it is written into DECISIONS.md. Each section is a
recommendation that the architect accepts or amends. Delete this file once every section has
been resolved into DECISIONS.md or rejected.

**Form.** This is a correction to the model the design should always have had, not a new
direction. The records and documents are corrected to state the model; they do not record
that something previously read otherwise. Decided items are corrected in place; signing the
exact corrected text below, item by item, is the architect's agreement to each change. Legacy
behaviour appears in this file as evidence and nowhere in the corrected records.

`check_consistency.py` parses no note form. What it needs from the corrected records: every
`**A31.x**` sub-item cited by id in a TASKS.md task (section 1 names the tasks), B24 and B25
named somewhere in TASKS.md (section 5), and the headword of every terminology row that
cites an A-id present in DECISIONS.md (section 7). Nothing else it checks is touched.

Line numbers refer to commit c581f1e on branch `slice_1a_row_shape`.

Sections:
1. A31: stage inputs have a role and a spatiality (the new decided item)
2. Corrected text for the affected decided items
3. `DISPLACEMENT_FEATURE`: scratch handle
4. `ADMIN_AREAS`: fixture fix
5. New open items and task notes
6. What PR 3 (row-shape grammar) must do differently
7. Corrections to documents and code after the go
8. Whether the model gets an ADR

Appendix A: the scope list (classified).

---

## 1. A31 — stage inputs have a role and a spatiality

### Verified (evidence; stays in this file)

- Legacy pre-filters context against every processing input before partitioning
  (`custom_tools/general_tools/partition_iterator.py:908-959`), selects context per partition
  within the search distance (`:1119-1167`), and appends processing rows within the search
  distance of a partition but not centre-in as `PARTITION_FIELD=0` (`:1044-1077`): the
  PROCESSING overlap. At a search distance of 0 the pre-filter is skipped and the per-partition
  selection keeps the context intersecting the partition (`:1146-1152`), which is what the
  model specifies at 0 m. Legacy declares vector only (`composition_configs/core_config.py:34-40`).
- No ADR states the context model. ADR-0021 ST-1shows `role=InputRole.PROCESSING` in an
  example; ADR-0019 PC-1 and ADR-0019 PC-3 are role-neutral.
- The canonical statement, `02-runtime.md:255-259`, says context inputs are "selected within
  `context_radius_m`" with no referent, says nothing about overlap for either role, and
  derives the non-spatial case from the data ("is context in the operative sense").
  `src/ag/core/types.py:109-123` (`InputRole`) repeats it. `DataType` (`:101-106`) has three
  members and no spatial property.
- `Stage`, `StageInput`, `ExternalSource` are not in `src/` yet. The plan lifts
  `core/pipeline.py` under Task B as "rename only" (`findings/implementation_plan.md:91,
  482-483, 896-902`), citing `findings/template_review.md:52` "keep as is (rename only)".

### Proposed A-item

**A31. Stage inputs: role and spatiality**

*Decided 2026-10-12.* A stage input has two independent properties.

**A31.1 The input role is declared; spatiality is derived.** `StageInput.role` is
`InputRole.PROCESSING` or `InputRole.CONTEXT` and answers one question: may this input's rows
become stage output? Roles belong to the stage input, not to the object. The same water
layer is PROCESSING in the stage that generalises it and CONTEXT in the stage that moves
buildings away from it. Whether an input is spatial is read from its object's `DataType` and
is never declared: `FEATURE_CLASS` and `RASTER` are spatial; `TABLE` and `SYMBOLOGY` are
not. `DataType` has the member `SYMBOLOGY` and a `spatial` property. Declarations of mostly
spatial data pay nothing for the second axis.

**A31.2 Fan-out's transfer follows from both properties.**

| | spatial | non-spatial |
|---|---|---|
| PROCESSING | partitioned, with halo overlap | rejected at declaration |
| CONTEXT | context filter, then partitioned with the same overlap | sent whole to every pod, written once at a shared key |

- The **context filter** keeps the CONTEXT rows within `context_radius_m` of any PROCESSING
  row of the stage, before partitioning; at 0 m it keeps the rows that intersect a PROCESSING
  row. The filter distance is the stage's context radius; there is no second number. Reason:
  an upstream radius computed ahead of time adds complexity for little gain and fails
  silently, since a context set filtered with the wrong radius looks exactly like a correct
  one.
- **Overlap** applies to both partitioned roles. A PROCESSING row within the radius of a
  partition but outside it reaches that partition too, and fan-in discards it (A6.1). A
  CONTEXT row within the radius of a partition reaches it; at 0 m, the rows intersecting the
  partition do.
- **Non-spatial PROCESSING is rejected** when the `StageInput` is constructed. There is nothing
  to partition, so the model defines no behaviour for it; the guard fails closed. It is a
  construction-time check in `core/pipeline.py` with a break-it case (A30), recorded in the
  plan for the Task B lift.
- **The radius is a claim about the logic.** Operations never see partitions (ADR-0019 PC-1), so
  `context_radius_m` is the one place a stage author reasons about partition boundaries. A
  0 m radius states that nothing in the stage consults a neighbour. The model does not guard
  it; a reviewer can challenge it.

**A31.3 Only rows originating from PROCESSING inputs may become stage outputs.** Stage
outputs are the only data that leaves a stage. A CONTEXT row may affect an output and never
becomes one: buildings moved away from water carry the buildings' lineage, and the water is
a spatial influence. Scratch intermediates built from CONTEXT rows are legal inside a stage;
they reach the scratch dump like every other handle (02-runtime §4.3) and nothing reads them
as an input. An object derived from CONTEXT rows that a later stage must read (a water
buffer, a displacement feature) is produced in a stage where its source is PROCESSING.
Enforced by review of the stage declarations only, until B24 resolves. The fixtures under
`tests/fixtures/example_pipelines/` are examples of the rule, not an enforcement of it.

**A31.4 Rasters are spatial** and take either role. Transfer is tile selection or clipping to
the partition plus its halo, not row filtering. The project produces no raster products;
raster use is value extraction (A5.2). The mechanism is open (B25) until a stage declares a
`RASTER` input.

**A31.5 Symbology files are non-spatial CONTEXT inputs.** A `.lyrx` file is a symbology
blueprint with no data, consumed by arcpy tools such as `ResolveRoadConflicts`. It is declared
as an `ExternalSource` with `data_type=DataType.SYMBOLOGY`, a settable location and a
classification, and reaches every pod whole. All tables and all symbology files are stage
inputs with a settable storage location, never baked into the container image. Reason: some
carry attributes that must stay on-prem, and one rule for all of them is more consistent
than a split by author. The member is `SYMBOLOGY`, not a generic `FILE`, so the next file kind
gets its own decision. Numeric symbol dimensions (`building_symbol_dimension`, buffer
factors) are a different thing: a project-wide Python resource that reaches operations as
config dataclass fields varying by pipeline (ADR-0020 OP-4), never a stage input. Deriving them
from `.lyrx` files is possible later and not planned. This settles 03-architecture §7.5 and
Q-D for both.

**A31.6 Port-level `subject`/`context` relate to the stage roles; they are not the same
thing.** The row-shape grammar (A12) declares, per port method, which input parameter's
rows carry identity into an output. The stage roles declare, per stage input, which rows may
become stage output. A port `subject` may be fed from a CONTEXT stage input
(`build_displacement_feature` buffers CONTEXT roads into a scratch blob); a port `context=`
may be fed from a PROCESSING-derived intermediate (`propagate_displacement` reads the blob as
`context` and the simplified buildings as `subject`). What holds at both levels: only the
subject carries identity into outputs, and a context influences without contributing
identity. The word `context` is shared on purpose for that reason, and for no other.

**A31.7 Rejected.** A third role for the non-spatial case (`REFERENCE`, `SHARED` or
`NON_SPATIAL`): it duplicates what `DataType` already says, mixes two questions in one enum,
and each candidate word collides with an existing use (`reference` is a port parameter,
`shared` is ordinary prose). A generic `FILE` data type: invites opaque inputs. The trade
accepted: at a stage declaration a reader must know the data type to see that a table is
sent whole, so the `InputRole.CONTEXT` docstring and 02-runtime §2.3 state both transfers
side by side.

`destination:` `02-runtime.md` §2.3 (A31.1, A31.2, A31.3, A31.7), §7.1 (overlap), §8 (the
guard); `03-architecture.md` §7.5 (A31.5); `core/types.py` (`InputRole` and `DataType`
docstrings); `core/pipeline.py` guard (Task B); `01-terminology.md`; the ADR of section 8 if
written.

**Hook consequence.** `check_consistency` requires every `A31.x` to be cited by id in a
TASKS.md task. Proposed citations: T3.4 gains A31.1, A31.2 and A31.7; T5.3 gains A31.3; T2.6
gains A31.4; T4.11 gains A31.5; T4.9 and T2.4 gain A31.6. The terminology rows of section 7
that cite A31 need their headwords in the item text; "input role", "spatial", "context
filter" and "SYMBOLOGY" are all present above.

---

## 2. Corrected text for the affected decided items

Each block is the exact replacement text for the passage named, ready to sign. Where only
one sentence changes, the whole passage is still given so the signed text is complete.

### A12.2 (replaces DECISIONS.md:901-910)

**A12.2** `subject` versus `context` at the port level is related to, not the same as,
PROCESSING versus CONTEXT at the stage level (A31.6). A port `subject` names the input
parameter whose rows carry identity into an output; a port `context` names an input that
influenced the output without contributing identity. `intersection` output rows *are* pieces
of the roads; the overlay influenced the result without contributing identity. Declaring both
as subjects would make every admin polygon an ancestor of every road piece. A port `subject`
may be fed from a CONTEXT stage input (`build_displacement_feature`), and a port `context=`
from a PROCESSING-derived intermediate (`propagate_displacement`); what holds at both levels
is that only the subject carries identity into outputs.

> *Renamed.* The second was `reference=`, which collided with `snap(reference=…)` — a dataset
> being snapped to, semantically close enough to blur. `context=` shares its word with
> `InputRole.CONTEXT` because both mean "influences, never becomes".

`destination:` `ports/row_shape.py`.

### A15.2 (replaces DECISIONS.md:1234-1248)

**A15.2 A handle is `diff-tracked` if it reaches a `StageOutput`.** Derived from the stage
declaration and the operation wiring, never declared. Under A31.3 every `StageOutput` descends
from a PROCESSING `StageInput`, so the rule needs no PROCESSING clause.

> *Renamed.* This property was "in scope", which collided with `ScratchScope` and left
> "scoped handle" ambiguous against `lineage-bearing` (A15.6). `diff-tracked` says exactly what
> follows from it: the boundary diff tracks this handle.

`destination:` lineage module docstring; `02-runtime.md` §8.

(The *Superseded* blockquote at `:1241-1246` is deleted.)

### A15.6, last sentence (replaces DECISIONS.md:1382-1383; the `destination:` line at 1384 stays)

Recorded separately because one word doing two jobs would make `SNAP_DISPLACEMENT` look like
an exemption instead of a legal case.

### A16 (replaces DECISIONS.md:1416-1426)

**The reading of `T`, and the derivation behind the corrected text (evidence; stays here).**
`T = { f ∈ from_ids of any edge : f ∉ O }` must range over the lineage edges and not over
`DROPPED` edges: every promoted drop `d` is a `from_id` of its own `DROPPED` edge and is not in
`O`, so under the other reading it is in both `T` and `D` and (3) fails whenever `D` is
non-empty. A16's existing verification already assumes this ("not in `D` because the boundary
diff does not call a row dropped when it appears in an emitted edge's `from_ids`"); the
corrected text states it. Pod `k` of `DISPLACEMENT` receives `B = B_own ∪ B_halo` (PROCESSING
buildings, own plus overlap) and `R = R_s ∪ R_g` (CONTEXT roads within the radius of a
PROCESSING row):

| step | declaration (A12.11) | ids out | edge |
|---|---|---|---|
| `simplify_polygons`: `densify`, `simplify` | `ONE + CARRY` twice | `simplified` carries `B` | none |
| `build_displacement_feature`: `buffer`, `merge` | `ONE + CARRY` twice | `merged` carries `R` | none |
| `build_displacement_feature`: `dissolve` | `GROUP + MINT` | `displacement_feature` holds parts `P` | `E1`: `PARENTS_CONSUMED`, `from_ids = R`, `to_ids = P` |
| `propagate_displacement` | `ONE + CARRY`, subject `input`, context `displacement` | `displaced` carries `B` | none: a context contributes no identity |
| stage-exit sweep (A16.2) | | `P` terminates in an unnamed handle | `E2_i`: `DROPPED`, `from_ids = {p_i}` |
| fan-in ownership (A6.1, A6.5) | | `B_own` kept, `B_halo` discarded without an event | none |

`I = B_own`; `O = B_own`; `T = R`; `D = P` if the `E2_i` are promoted, else `∅`. No part id is
in `T`. (1) `B_own − B_own − R − D = ∅`. (2) `B_own − B_own − P = ∅`. (3) `R ∩ D = ∅` whether
or not the drops are promoted. Across the stage the same, with `I = O =` every building.

**Corrected text:**

**`I` is PROCESSING-only.** Completeness asks whether the stage lost something it was
*responsible for*, and a stage is not responsible for its CONTEXT inputs (A31.3). Note this is
a different question from A15.2's `diff-tracked`, which decides whether a handle gets ids at
all; this one decides what must be accounted for. `T` ranges over the lineage edges
(`PARENTS_CONSUMED`, `PARENTS_KEPT`, `CREATED`), not over `DROPPED` edges: a promoted drop is a
`from_id` of its own `DROPPED` edge and is not in `O`, so the other reading would put it in
both `T` and `D` and (3) could never hold.

Verified against the `DISPLACEMENT` stage rather than reasoned about. `buildings`
(PROCESSING) flows through `simplify_polygons` and `propagate_displacement`, both
`ONE + CARRY`, so every building id reaches `O` via `displaced` — (1) holds, and `O` is `I`, so
(2) holds. `build_displacement_feature`'s dissolve mints the parts of `displacement_feature`,
a scratch handle, from the CONTEXT road ids: the road ids land in `T` via `from_ids` without
ever entering `I`, and the part ids are in `to_ids`. `propagate_displacement` reads the parts
as `context`, so they enter no further lineage edge, and the stage-exit sweep emits `DROPPED`
for each part (A16.2). `D` holds at most part ids and `T` holds road ids, so (3) holds whether
or not those drops are promoted (T5.1).

The same correction applies to the transcription note in TASKS.md:2354-2362 (the first two
paragraphs of "Found while writing this" item 4), which repeats the old verification and the
phrase "reference data"; the B7 paragraph at 2364-2366 stays.

### A16.1, last paragraph (replaces DECISIONS.md:1438-1443; the first sentence is unchanged)

`PARENTS_CONSUMED` and `PARENTS_KEPT` need no ownership check — the resulting id's presence in the job's
declared output already witnesses it, because the partition machinery filtered outputs to owned
features. **This is why the record format must not carry an own/halo-copy flag: the writer
cannot know it.** It also removes the deduplication problem — a feature dropped as a halo copy
in job x and kept as own in job z produces one record in the stage log, from z's output, and
x's record is simply not promoted. A halo copy is a PROCESSING row a pod received through the
overlap (A31.2). How a record about an id the job itself minted is promoted is open (T5.1).

### A17.1 (replaces DECISIONS.md:1463-1466)

**A17.1** `DISPLACEMENT_FEATURE` is declared as a `Derived` and wired as a `StageOutput`
(`pipelines/building/n100_objects.py:55`, `n100_stages.py:135`), but every row of it
originates from CONTEXT inputs (`roads_source`, `roads_generalized`), which A31.3 forbids. It
is a scratch handle: the `Derived` and the `StageOutput` are deleted (T5.3). Nothing reads it
and the pipeline does not publish it.

### A6.2 (replaces DECISIONS.md:207-210)

**A6.2** Preconditions: the partition polygons tile without overlap (validate
`custom_partition_feature` for this, not just geometry type), while each pod's payload
extends past its polygon by `context_radius_m` (A31.2); a half-open boundary convention;
displacement well inside the halo.
`destination:` `02-runtime.md` §7.

### A6.5 (replaces DECISIONS.md:222-224)

**A6.5** Fan-in selection is **not** a `DROPPED` event. The same PROCESSING feature appears in
several jobs as a halo copy; discarding non-owning copies is deduplication of one identity.
`destination:` `02-runtime.md` §7; lineage module docstring.

### B9(d), third bullet (replaces DECISIONS.md:2076-2077; same text at PROPOSALS-2026-09-14.md:32-34)

- The CONTEXT road ids enter the building stage's log as `from_ids` of
  `build_displacement_feature`'s dissolve edge (A15.5), which is A20's forward branch. The walk
  from a road into the building pipeline depends on the column the mapping drops.

The conclusion, that the in-run stage output must carry `lineage_id`, stands on A20 instead
of on A16's example. Section 1 of the 2026-09-14 proposals should be re-read with that
substitution before it is signed.

### Checked, no correction

A6.4, A6.6, A15.1, A15.5, A17.5, A17.6, A20, A25.1, A5.2, A11.15(a), A12.1, A12.11, A16.2,
A16.4: consistent with the model, or wording that would not mislead someone implementing
`src/`. Left as they are.

---

## 3. `DISPLACEMENT_FEATURE`: scratch handle

### Verified

- `tests/fixtures/example_pipelines/pipelines/building/n100_stages.py:114-155`: the
  `DISPLACEMENT` stage declares `SELECTED` PROCESSING, `NVDB_ROADS` and `N100_ROAD` CONTEXT,
  and two outputs, `DISPLACED` and `DISPLACEMENT_FEATURE`. `build_displacement_feature`
  (`operations/building/__init__.py:89-106`) writes `displacement_feature` from the two
  CONTEXT handles only. Illegal under A31.3.
- Why it is a `StageOutput`: `n100_objects.py:60-67` and `n100_stages.py:173-179` give the
  reason as the no-third-state rule, "either an object crosses a boundary and is a `Derived`,
  or it does not and is a handle"; a `Derived` declared for lineage review beside a bare handle
  was meaningless. Not inspection by cartographers; no diagnostic need is recorded anywhere.
- Nothing reads it. No other stage names the `Derived`, `BUILDING_N100` does not publish it,
  and nothing else in `tests/` or `docs/` outside `docs/refactor/temp` refers to it.

### Options weighed

| | legal under A31.3 | fixture change | records touched |
|---|---|---|---|
| **(a) scratch handle** | yes | delete one `Derived`, one `StageOutput`, one import, two docstring paragraphs | A15.2, A16, A17.1, T5.3 |
| (b) a stage in the road pipeline where roads are PROCESSING | yes | a new stage, `Derived`, product and cross-pipeline read | the same, plus A16's example moves |
| (c) keep as is | no | none | the declaration fixture would contradict A31.3 |

### Recommendation

**(a). `displacement_feature` becomes a scratch handle.** The no-third-state rule still holds
and resolves the other way: the handle crosses no boundary, so it is a handle. The scratch
dump (02-runtime §4.3) keeps the blob reachable for troubleshooting on the dump's retention,
which is how every intermediate is inspected. If a displacement feature is ever wanted as a
product, that is option (b), declared in the road pipeline when the need appears.

Fixture changes, listed because the fixtures are inert and no check covers them:

1. `pipelines/building/n100_objects.py:55-67`: delete the `DISPLACEMENT_FEATURE` `Derived` and
   its docstring; add two sentences under `DISPLACED` saying why the displacement feature has
   no `Derived` (built from CONTEXT rows, crosses no boundary; A31.3).
2. `pipelines/building/n100_stages.py:24`: drop `DISPLACEMENT_FEATURE` from the import.
3. `pipelines/building/n100_stages.py:135`: delete the `StageOutput`.
4. `pipelines/building/n100_stages.py:173-179`: replace the "THAT IS A DECISION" paragraph
   with one stating that the blob is scratch, built from CONTEXT inputs, dropped at stage exit
   and present in the scratch dump.
5. `pipelines/building/n100_stages.py:58`: `displacement_feature = handle()` stays.
6. `operations/building/tuning/`: the `DISPLACEMENT_FEATURE` config is unrelated; unchanged.

---

## 4. `ADMIN_AREAS`: fixture fix

`sources.py:65-74` declares `ADMIN_AREAS` with `data_type=DataType.TABLE` and the docstring
"Non-spatial, so CONTEXT in the operative sense", while `join_admin_attributes` overlays it
with `intersection` and `difference` (`operations/road/__init__.py:355-356`) and searches it
with `nearest_neighbors` (`:439-444`). The example overlays it, so it is a feature class.
Tables are non-spatial; using one as geometry is a user error that needs no check and fails
loudly in the adapter. The guard that stays is the one for non-spatial PROCESSING (A31.2),
which is about a case the model does not define, not about user error.

Fixture changes:

1. `sources.py:70`: drop `data_type=DataType.TABLE` (the default is `FEATURE_CLASS`).
2. `sources.py:72-74`: "Municipality and county polygons. Spatial CONTEXT where read: filtered
   to the halo of the stage's PROCESSING roads, then partitioned with overlap."
3. Road `SELECTION` (`pipelines/road/n100.py:214-255`) keeps `context_radius_m=0.0` and its
   docstring: at 0 m the context filter keeps the areas intersecting a road, and the
   docstring already says the radius is a claim a reviewer can challenge.

---

## 5. New open items and task notes

### B24. A static check for A31.3

**B24. Can A31.3 be checked at plan time?** Opened 2026-10-14 with A31. Not today.
`OperationCall` records only undifferentiated `In` and `Out` handles
(`src/ag/core/operations.py`); the row-shape `subject`/`context` lives on port methods, which
plan time never sees (B14). A static check needs an operation-level subject marker: `Out`
metadata naming the `In` parameter whose rows carry identity into it, carried by the same
`Annotated` mechanism as the direction markers, which touches `core/operations.py`. With it, a
validation walk from each `StageOutput` back through subject edges to a `StageInput` requires
`PROCESSING` at the end, with a break-it case (A30). A weak proxy is available earlier: every
root in a `StageOutput`'s `origin` reachable through a PROCESSING `StageInput` chain. Not part
of A31; A31.3 is enforced by review until this resolves.
`destination:` `02-runtime.md` §8 when resolved.

### B25. Raster transfer under fan-out

**B25. How a `RASTER` input reaches a pod.** Opened 2026-10-14 with A31.4. Tile selection or
clipping, to the partition plus its halo, for both roles. Legacy precedent is
`find_rasters_for_vector_extent` (`custom_tools/general_tools/geometry_tools.py:1600`, used by
`generalization/n100/river/fix_river_topology_gaps.py`), which selects the tiles intersecting
the processing extent and has no overlap. Due when a stage declares a `RASTER` input, which
`sample_at` (T2.6, A5.2) will be the first to need.
`destination:` `02-runtime.md` §2.3 when resolved.

B24 is named in T4.9's note and B25 in T2.6's note, for `check_consistency`'s B-referenced
rule.

### Task notes (TASKS.md)

- **T5.1** (fan-in log merge and `DROPPED` promotion): **open gap, recorded, not resolved.** The
  promotion rule `owner(root(d)) == job(d)` has no value for a record about an id the job
  itself minted, in two cases. (i) The displacement blob: `root(p_i)` resolves through a
  `GROUP` mint to several CONTEXT road ids with several owners, and the dissolve edge is a
  `PARENTS_CONSUMED` edge whose `to_ids` no output witnesses, so A16.1's "needs no ownership
  check" argument does not cover it; A20's forward walk from a road assumes the edge is in
  the merged log. (ii) The general case, which rules out "promote every record about a
  job-minted id": pods x and z both `GROUP`-mint over building b, a halo copy in x and owned
  in z; fan-in keeps g_z and discards g_x without an event; promoting x's `PARENTS_CONSUMED`
  edge would record b consumed twice, once into an id that exists nowhere. A16's assertions
  hold under any resolution (section 2); what is open is which records of a job's own mints
  enter the stage log.
- **T5.3** (`:2033-2053`, order table `:147`): retitle "Origin-closure check". Delete the
  origin fix; add the fixture changes of section 3 as the task's second half, citing A31.3.
  `decision refs` gain A31.3; A17.1 retires with the fixture change.
- **T4.9 note** (`:1735-1737`): "Under A31.3 every `StageOutput` descends from a PROCESSING
  `StageInput`, so A15.2 needs no PROCESSING clause. A15.6's split stands on
  `SNAP_DISPLACEMENT`. A static check for A31.3 is B24."
- **T3.4**: fan-out's order: apply the ingest map on the whole input; filter spatial CONTEXT
  to the halo of PROCESSING rows (intersects, at 0 m); partition both roles with overlap;
  write non-spatial CONTEXT once at the shared key.
- **T0.1 case 6** (`:248-264`), **T4.11(3)** (`:1863-1867`): the `displace_features` contract
  names its symbology input: a `SYMBOLOGY` CONTEXT `StageInput`, sent whole, declared with a
  location. Where that parameter sits on the port is B11's to settle.
- **T2.6** (`:862-879`): the raster reaches the pod as a `RASTER` `StageInput` tile-clipped to
  partition plus halo (B25); the window is the payload, not the national raster.
- **T2.9** (`:996`): "`Schema.__post_init__` (`src/ag/ports/table_ops.py:37-51`) keys
  spatiality on `is DataType.FEATURE_CLASS`, which makes `RASTER` geometry-less. When the port
  surface is next touched it uses `DataType.spatial`, and rejects `RASTER` and `SYMBOLOGY`
  outright: rows are never written to either."

---

## 6. What PR 3 (row-shape grammar, branch `slice_1a_row_shape`) must do differently

PR 3 has not written `ports/row_shape.py` on this branch yet. When it does:

1. **A12.2 is struck into `row_shape.py` in its corrected form** (section 2): the docstring
   states the port-level meaning (subject carries identity, context influences without
   contributing identity) and says the pair is related to, not the same as, `InputRole`,
   citing A31.6.
2. **The `row_shape` docstring must not equate `subject`/`context` with `InputRole`.** It may
   say the word `context` is shared because both senses mean "influences, never becomes", and
   give the two counter-examples (`build_displacement_feature`, `propagate_displacement`).
3. The terminology rows for **subject** and **context (row-shape)** (`01-terminology.md:93-94`)
   are rewritten per section 7 and cite A12.2 and A31.6; when A12.2 is struck, the authority
   cell repoints to `ports/row_shape.py` and A31.6.
4. `Schema.__post_init__` in `src/ag/ports/table_ops.py` is in PR 3's directory but not in its
   scope; it stays as is under the T2.9 note.
5. Nothing in PR 3 needs `InputRole`, `DataType.SYMBOLOGY` or the `spatial` property.

---

## 7. Corrections to documents and code after the go

What the edit phase does once sections 1 to 5 are signed, in priority order. Exact wording
is drafted then. Template code is not edited; the plan lines that govern a lift are.

**Code (`src/`), with tests.**

- `src/ag/core/types.py`: `DataType` gains `SYMBOLOGY = "symbology"` and a `spatial` property
  (`self in (FEATURE_CLASS, RASTER)`), with a docstring stating that spatiality is derived here
  and never declared. `InputRole` docstring rewritten to A31.1 to A31.3 and A31.7's trade,
  both transfers side by side; the radius sentence of A31.2 goes where `context_radius_m` is
  declared (Task B), not here.
- `tests/unit/core/test_types.py`: `spatial` over every member, and a member-set tripwire in
  the style of `len(Classification) == 2` (`:68`).
- No change under `src/ag/ports/` (PR 3 scope; T2.9 note).

**PR 3.** Section 6.

**Plan.**

- `findings/implementation_plan.md:91, 482-483, 896-902` (Task B): "rename only" becomes
  "rename plus one construction guard: `StageInput` rejects a non-spatial object with role
  PROCESSING, with a break-it case (A30); and the `context_radius_m` docstring states that
  operations never see partitions (ADR-0019 PC-1), so the radius is the one place a stage author
  reasons about partition boundaries, and that 0 m is a claim about the logic a reviewer can
  challenge". `findings/template_review.md:52`: "keep as is" becomes "keep with changes",
  naming the guard and the docstring.
- `findings/implementation_plan.md:769-771` (slice 5 `fan_out.py`): per-partition payloads
  for PROCESSING and spatial CONTEXT (filtered first; intersects at 0 m), shared payload for
  non-spatial CONTEXT, non-spatial PROCESSING rejected at declaration, rasters per B25.
  `:752-758`: `Stage` carries role, radius and, through the object, `DataType`; no field is
  added, one guard is. `:776-778, 802-804`: "discarded context copies" and "own/context flag"
  become halo-copy wording. `:670-672, 694-699`: slice 3's `build_displacement_feature` run
  produces a scratch handle. `:1448-1450`: "`StyleOps`" becomes "SYMBOLOGY inputs (A31.5,
  B11)".

**Design documents.**

- `02-runtime.md:255-259` (§2.3): replaced by A31.1 to A31.3 and A31.7's trade, with the
  table; at 0 m the filter is "intersects". Heading unchanged (hook anchor). `:922-924` (§11
  symbology item): deleted; A31.5 lands in §2.3 and 03-architecture §7.5. `:661-663` (§6.3):
  "K payloads and one shared payload for non-spatial inputs". `:721-726` (§7.1): "its
  partition's PROCESSING rows plus those within the halo, and the CONTEXT rows within the
  halo"; "halo context" becomes "halo copy". `:796-838` (§8): the non-spatial PROCESSING guard
  added to the inside-a-stage checks. `:48-53` (§1.2): fan-out "context filter, partition with
  overlap"; fan-in "select centre-in, append".
- `03-architecture.md:777-790` (§7.5): rewritten per A31.5: `.lyrx` files are `SYMBOLOGY`
  stage inputs; numeric symbol dimensions are config dataclass fields per ADR-0020 OP-4, never a
  stage input. `:865-866` (Q-D): closed. `:135-138`: "(non-spatial context inputs, sent whole
  to every pod)".
- `01-terminology.md`: row 93 (**subject**) and 94 (**context (row-shape)**) rewritten to
  "related, not identical" with the two counter-examples, citing A12.2 and A31.6. Row 127
  (**.lyrx**): a `SYMBOLOGY` stage input, non-spatial CONTEXT, sent whole, from a settable
  location, never in the image. Row 51 (**fan-out**): filters and partitions the spatial
  inputs, writes K payloads plus one shared payload, records K. Row 55 (**halo**): also the
  context-filter distance; at 0 m the filter is "intersects". New rows: **input role**
  (A31.1), **spatial** (A31.1; distinct from the `Spatial` predicate), **context filter**
  (A31.2), **SYMBOLOGY** (DataType) (A31.5). Collisions table: "context" has three senses
  (stage role, row-shape, halo copy) and one unrelated one (observability).

**Fixtures (`tests/fixtures/example_pipelines/`).** Sections 3 and 4, plus:

- `pipelines/road/n100.py:26-29`: "cuts it into K overlapping payloads, CONTEXT after the
  context filter; a non-spatial input is written once". `:112-113`: "a table is non-spatial,
  so as CONTEXT it is sent whole". `:343-348`: `roads_in` partitioned with 5000 m overlap;
  `nvdb_reference` filtered to within 5000 m of any `SELECTED_ROADS` row, then partitioned
  with the same overlap; `ranks` non-spatial CONTEXT, sent whole.
- `sources.py:92-93`: "the non-spatial CONTEXT transfer at its cheapest".
- `operations/building/__init__.py:123`: "as a halo row for another".

**Hook scripts.** No change needed: neither hook has a fixed term list, and the new rows'
headwords appear in the texts they cite.

---

## 8. Whether the model gets an ADR

**Recommendation: yes, one ADR, "Stage inputs have a role and a spatiality", written in the
same edit phase with A31 as its draft.** The model touches three design documents, and
README:35-36 says the documents keep two sentences and a link while the argument lives in the
ADR; A31 retires to its destination like every other A-item, and an ADR is the destination
that survives `docs/refactor/temp/`. Against: no ADR is contradicted, so nothing forces one.
The architect decides; if no ADR, A31 lands in 02-runtime §2.3 with a *Landed* note.

---

## Appendix A: the scope list

Status: WRONG contradicts the model; AMBIGUOUS can be read either way or misleads by
omission; CONSISTENT agrees. "no change" marks hits left alone because they would not
mislead someone implementing `src/`. Template code is listed only where a plan line governs a
lift into `src/`.

### Legacy evidence

- `partition_iterator.py:908-959` context pre-filter against processing inputs; `:1119-1167`
  per-partition context selection; `:1044-1077` processing overlap tagged `PARTITION_FIELD=0`.
  At a search distance of 0 the pre-filter is skipped and the per-partition selection keeps
  context intersecting the partition (`:923-925`, `:1146-1152`), as the model specifies.
- `composition_configs/core_config.py:34-40`: vector only.
- `geometry_tools.py:1600`: raster tiles intersecting the extent, no overlap.

### Decided items

| item | lines | status | action |
|---|---|---|---|
| A12.2 | 901-910 | WRONG | Corrected, section 2. |
| A15.2 note | 1241-1246 | WRONG | Corrected, section 2. |
| A16 | 1417, 1421-1426 | WRONG (formulas CONSISTENT) | Corrected, section 2. |
| A16.1 | 1440-1443 | AMBIGUOUS | Corrected, section 2. |
| A17.1 | 1463-1466 | AMBIGUOUS | Corrected, section 2. |
| A15.6 | 1382-1383 | AMBIGUOUS | Corrected, section 2. |
| A6.2 | 207-210 | AMBIGUOUS | Corrected, section 2 (fan-out implementer). |
| A6.5 | 222-224 | AMBIGUOUS | Corrected, section 2 (fan-in implementer). |
| A16.2, A6.6, A15.1, A15.5, A20, A25.1, A5.2, A11.15(a) | various | AMBIGUOUS wording | no change. |
| A6.4, A17.6, A17.5, A12.11, A12.1, A12.3, A12.5, A12.5a, A12.7a, A12.9, A6.1, A6.3, A7.x, A8, A9.6, A9.10, A10.6, A11.4a, A11.10, A13, A17.7, A4.6 | various | CONSISTENT | no change. |

### Open items and tasks

| item | lines | status | action |
|---|---|---|---|
| B9(d) | DECISIONS 2066-2083; PROPOSALS-09-14 32-34 | AMBIGUOUS | Corrected, section 2. |
| B11 | 2346-2347 | CONSISTENT | Symbology parameter of `displace_features` settles here. |
| B20, B22, B10 table | | CONSISTENT / wording | no change. |
| T5.3 | TASKS 2033-2053, 147 | WRONG | Section 5. |
| T4.9 note | 1735-1737 | WRONG | Section 5. |
| "Found while writing" 4 | 2354-2362 | WRONG | With A16, section 2. |
| T5.1, T3.4, T0.1, T4.11, T2.6, T2.9 | | gaps | Section 5. |
| T3.7, T4.6, T4.13 | 1372-1374, 1660, 1778 | AMBIGUOUS wording | no change. |
| T5.2 and the rest | | CONSISTENT | no change. |
| REVIEW-2026-09-14 :99, :103-104, F13 | | stale | One-off file; not edited. |

### ADRs

None states the context model. ADR-0021 ST-1shows `role=` in an example; ADR-0019 PC-1and
ADR-0019 PC-3are role-neutral. Nothing to correct.

### Documents, plan, code, fixtures

| file:lines | status | action |
|---|---|---|
| 02-runtime.md:255-259 | WRONG | Section 7. |
| 02-runtime.md:922-924 | WRONG | Deleted, section 7. |
| 02-runtime.md:48-53, 661-663, 721-732, 796-838 | AMBIGUOUS | Section 7. |
| 02-runtime.md:849-855, 867-877, 93-94, 459-461 | AMBIGUOUS | no change. |
| 02-runtime.md: rest | CONSISTENT | no change. |
| 03-architecture.md:777-790 (§7.5) | WRONG | Section 7. |
| 03-architecture.md:865-866 (Q-D) | WRONG | Closed, section 7. |
| 03-architecture.md:135-138 | AMBIGUOUS | Section 7. |
| 03-architecture.md:653-663 (`pod_role`) | AMBIGUOUS | no change. |
| 01-terminology.md:93, 127 | WRONG | Section 7. |
| 01-terminology.md:94, 51, 55; new rows | AMBIGUOUS / gap | Section 7. |
| 01-terminology.md:181 | AMBIGUOUS | no change (retired row). |
| 04-migration.md, README.md, docs/contributing/* | CONSISTENT / none | no change. |
| findings/implementation_plan.md:769-771 | WRONG | Section 7. |
| findings/implementation_plan.md:91, 482-483, 896-902; template_review.md:52 | AMBIGUOUS | Govern the Task B lift; section 7. |
| findings/implementation_plan.md:752-758, 776-778, 802-804, 670-672, 694-699, 1448-1450 | AMBIGUOUS | Section 7. |
| findings/implementation_plan.md:673-677, 704-707, 1486, 150; template_review.md:149; project_tree.md:659; seam_readiness, lineage_conclusion, port_values_evidence | AMBIGUOUS | no change. |
| PATCH-2026-09-17.patch | WRONG by reference | Historical; not edited. |
| src/ag/core/types.py:110-116 | WRONG | Section 7. |
| src/ag/core/types.py:101-106 | needs | Section 7. |
| src/ag/core/types.py:158-172 | CONSISTENT | no change; the rule is stated without "durable". |
| src/ag/ports/table_ops.py:37-51 | AMBIGUOUS | T2.9 note. |
| src/ag/core/handles.py | CONSISTENT | no change. |
| tests/unit/core/test_types.py | gap | Section 7. |
| fixtures: building/n100_stages.py:135, 143-148, 173-179; n100_objects.py:55-67 | WRONG | Section 3. |
| fixtures: sources.py:65-74 | WRONG | Section 4. |
| fixtures: road/n100.py:343-348, 112-113; sources.py:72-74 | WRONG | Section 7. |
| fixtures: road/n100.py:26-29; sources.py:92-93; operations/building/__init__.py:118-124 | AMBIGUOUS | Section 7. |
| fixtures: road/n100.py:214-255 (SELECTION at 0 m) | CONSISTENT | Unchanged; 0 m is legal. |
| fixtures: SNAP_DISPLACEMENT | CONSISTENT | no change. |
| fixtures: the rest | CONSISTENT | no change. |
| fixtures status | | Inert: import `ag.core.pipeline`, `ag.core.data_objects`, `ag.core.policy`, none in `src/`; excluded from ruff, pyright and pytest. |
