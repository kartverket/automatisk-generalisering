# Lineage and Identity — Decision Record

**Status:** STAGING. This directory is not a permanent home.

Every entry here has a `destination:` naming the real document that absorbs it once its task
completes. `temp/` is deleted when every task in [TASKS.md](TASKS.md) is done and every A-item
below has landed at its destination. Until then this file is the authority for anything it
covers.

**This is a rationale record, and it is append-only in spirit.** Later work supersedes entries;
it does not rewrite them. Where a position reversed, the superseded text and the reason for the
reversal both stay — the reasoning behind a reversal is usually the load-bearing part, and it is
what stops the same ground being re-argued in six months.

**A-numbering is stable.** Other documents and task entries reference A-ids. Never renumber.

---

# A. Settled

## A1. Code organisation

**A1.1** `template_code/ag/operations/road/__init__.py` is a reading convenience, not a layout
rule. The target is a package. `@operation` reads the name from `fn.__name__` and
`OperationCall` holds a live `fn`, so module layout is free — splitting into `ramps.py`,
`thinning.py` and so on changes only the stage file's import line.
`destination:` `03-architecture.md` §5, plus the `operations/` package docstring.

**A1.2** Operation granularity is set by *what must be visible outside the function*: declared
`In`/`Out` handles in the dependency graph, a scratch workspace, one config in the run manifest,
a checkable contract. Split when another operation reads the intermediate, when the halves want
different tuning, or when they belong in different stages. Otherwise one operation with
undecorated helpers. A file like `generalization/n100/road/ramps.py` maps to **one**
`@operation` plus roughly twenty helpers.
`destination:` `02-runtime.md` §2.4.

**A1.3** `Toolbox` stays an explicit parameter. A module-level singleton was considered and
rejected: it would prevent two pipelines running different adapters in one process, which is
exactly the incremental-port path. For a large tool, bind `tb` and `scratch` once in a plain
class constructor rather than threading them through forty signatures — constructor injection,
not ambient state.
`destination:` ADR-0008 (amend with the incremental-port argument and the constructor-injection
guidance).

## A2. Predicates

**A2.1** `Attr` becomes **structured leaves** — `Attr.cmp(field, op, value)`,
`Attr.in_(field, values)`, `Attr.is_null(field)` — with `Attr.raw(cql)` as a rare, greppable
escape hatch guarded by a call-site count test.

Rationale: an opaque CQL2 string forces every adapter to write a parser before it can quote
identifiers correctly (`AddFieldDelimiters` differs by workspace type), and it admits
expressions no adapter can compile. The template already contains two — `Attr("... in (select
... from merge_report)")` at `operations/road/__init__.py:678` and `:942` are subqueries against
a `ScratchHandle`.
**`Attr.cmp`'s operator set** *(decided 2026-09-21)*: `=`, `<>`, `<`, `<=`, `>`, `>=` and `LIKE`;
`value` is an `AttributeValue` other than `None`, and a null test goes through `Attr.is_null`,
because `= NULL` is never true in SQL and no adapter should have to special-case it.
`destination:` new ADR; amends ADR-0001.

**A2.2** Three independent needs converged on `Attr.in_`: the predicate design itself, the 39
`deleteRow()` sites (which become `select(where=~Attr.in_(id, ids))`), and `key.where_in` in the
work-key API. A fourth arrived later — see A17.7.
`destination:` same ADR as A2.1.

**A2.3** Known limit: this catches structure and types at import, not wrong field names. Schema
declarations on handles would catch those. Deferred, and additive to A2.1.
`destination:` same ADR as A2.1, as a stated non-goal.

## A3. Graph port

`NodeId` stays `int`. Widening to `Hashable` costs real memory at hundreds of thousands to
millions of nodes and may be unimplementable for a non-networkx adapter. Multi-dataset entity
keys (`line_topology.py`'s `tuple[str, int]`) get an int mapping in the helper — the same move
`_node_rows` already makes.

Refinement: `NodeId = NewType("NodeId", int)`. This does **not** contradict `core/types.py`'s
`TypeAlias`-over-`NewType` rationale, which applies to strings crossing many boundaries; node
ids have exactly one construction site, which is the textbook `NewType` case. Say so in the
code, or someone will "fix" the inconsistency.
`destination:` `ports/graph_ops.py` docstring; Q-C resolution in `03-architecture.md` §9.

## A4. Row IO

**A4.1** Bulk read/write replaces cursors. 308 `SearchCursor` → `read_rows`; 80 `insertRow` →
`write_rows`; 39 `deleteRow` → `select` with a negated predicate.
`destination:` ADR-0004 (amend with the counts).

**A4.2** The **90 `updateRow` sites are the only real constraint** — read, compute in Python,
write back. The 101 `CalculateField` sites already cover the expression-only case. The
side-table-plus-`join_field` answer is more portable but costs a full write plus a join where
there was one in-place pass.
`destination:` ADR-0004.

**A4.3** Add `update_rows(input, key, fields, rows)` — bulk, keyed, no iteration protocol, so it
does not reintroduce what ADR-0004 removed. Writes M changed rows, not N. Must allow
`Row.geometry` so snap and displace are covered. Requires a stable key, which `lineage_id`
provides.
`destination:` `ports/table_ops.py` docstring; ADR-0004 amendment.

**A4.4** `Row` gets `slots=True`. Note this is *not* where the memory is:
`custom_tools/general_tools/line_topology.py:1233-1235` caches whole polylines, and
`Ring = tuple[tuple[float, float], ...]` costs roughly 110 bytes per coordinate against 16 raw.
If memory becomes binding, `Ring` is the lever, not `Row`. `partition_iterator.py` already sizes
partitions by `count_vertices`, which confirms vertex volume is the real axis.
`destination:` `ports/table_ops.py` and `ports/geometry.py` docstrings.

**A4.5** `AttributeValue` cannot carry BLOB or Raster values. No loss today —
`generalization/n100/road/dam.py:148` already excludes those field types. If a BLOB need
arrives, the answer is a reference in a TEXT field with bytes in a side store, **not** widening
the union, because bytes in a `Row` makes memory unbounded. Write this into the
`AttributeValue` docstring so the future decision starts from the right question.
`destination:` `ports/table_ops.py`, `AttributeValue` docstring.

**A4.6** Raster needs no widening: `sample_at(raster, points) -> tuple[float | None, ...]`
returns floats into DOUBLE fields, which is what `custom_tools/general_tools/geometry_tools.py`'s
`LineZValueTool` already does. Contour generation is a dataset-level operation. Neither puts
raster data in a row, so `Coordinate` stays z-free — state the reason, so nobody "fixes" it.
`destination:` `ports/geometry.py`, `Coordinate` docstring.

## A5. Missing port capability

**A5.1 Linear referencing**, roughly 43 sites across nine files: `measureOnLine` 13,
`queryPointAndDistance` 13, `positionAlongLine` 10, `segmentAlongLine` 7, plus `SHAPE@LENGTH` 4
and `SHAPE@AREA` 2. These belong as `Geometry` methods — per-value math, no dataset — not
`GeometryOps`.
`destination:` `ports/geometry.py`.

**A5.2 Raster sampling** has no port at all. `DataType.RASTER` exists but `Toolbox` has four
ports and none reads a pixel. `FillLineGaps` takes `raster_paths`
(`composition_configs/logic_config.py:424`) and samples elevation via `RasterHandle` /
`LineZValueTool` (`custom_tools/general_tools/geometry_tools.py:900`). Scope is narrow —
sample-at-points plus contour generation, never a raster product — so it is a `GeometryOps`
method, not a fifth port.
`destination:` `ports/geometry_ops.py`; `03-architecture.md` §2.1 (why it is not a port).

**A5.3** Confirmed already covered, recorded so it is not re-investigated: multipart
(`Geometry.parts`), Z/M (correctly omitted — `hasZ` 1 hit, `SHAPE@Z` 0), and the absence of
domains, subtypes, relationship classes, Network Analyst and Spatial Analyst anywhere in the
repo.
`destination:` `ports/geometry.py` docstring.

**A5.4** Delete `GeometryOps.union` — zero callers in the entire repo (every `.union(` is a
Python set or geometry union). By `geometry_ops.py`'s own "a method with no caller is not
shipped" rule it should not exist, and its absence makes the N:M lineage grammar question moot.
`destination:` `ports/geometry_ops.py`.

**A5.5** `VertexPosition` is missing `DANGLE`, used at five sites
(`unconnected_river_geometry.py`, `river_centerline.py`, `mst_loop.py`,
`n100/road/data_preparation_2.py`, `n250/road/data_preparation_2.py`). Dangle extraction is 0-to-2
rows per feature — a filter, so `MANY` — and it is how river and road topology gaps are found.
`destination:` `ports/geometry_ops.py`, `VertexPosition`.

**A5.6** Four port methods are split because their row semantics vary by argument. Three fix a
**pre-existing expressibility gap** where the port silently fixed one behaviour and the majority
of real call sites use the other — independent of lineage.

| method | port today | real usage | cells | split into |
|---|---|---|---|---|
| `buffer` | no `dissolve_option`, fixed at NONE | 19 `NONE`, **6 `ALL`** | ONE+CARRY / GROUP+MINT | `buffer` / `buffer_dissolve` |
| `spatial_join` | no `join_operation` | 12 `ONE_TO_ONE`, **18 `ONE_TO_MANY`** | ONE+FOREIGN / MANY+FOREIGN | `spatial_join` / `spatial_join_all` |
| `nearest_neighbors` | `closest_count: int = 1` | 3 `CLOSEST`, **25 `ALL`** | ONE+FOREIGN / MANY+FOREIGN | `nearest_neighbor` / `all_neighbors` |
| `extract_vertices` | `position: VertexPosition` | ALL, BOTH_ENDS, END, MID, DANGLE | ONE / MANY | `extract_vertex` / `extract_vertices` |

`all_neighbors` rather than `neighbors_within`: the latter implies a distance bound when the
varying parameter is count.

Varying arguments that do **not** move the cell, so no split: `dissolve.option` (both
`GROUP+MINT`; `SINGLE_PART` only produces finer groups), `simplify.collapsed_points` and
`collapse_to_centerline.pairs` (an optional output or grouping source, cell fixed),
`explode_multipart` on single-part input (data-dependent; `MANY` covers it degenerately).

> *Superseded in part, 2026-09-17 (B18).* `dissolve.option` is no longer an argument: `dissolve` is
> single-part by contract and `DissolveOption` leaves the port (A18, amended). The other three
> entries stand.

Two need a contract rather than a split: `cluster_points.minimum_count` (what happens to points
below the threshold is undocumented — state it), and `join_field` with a non-unique key, which
fans out on *data* rather than an argument and so cannot be split (see B4).

**Discriminators needed: zero.** Splitting covers every case in the surface.
`destination:` `ports/geometry_ops.py`.

**A5.7 Workspace creation is a `TableOps` method.** *Decided 2026-09-21; resolves B21.*
`TableOps.create_workspace(*, path: str, fmt: WorkspaceFormat) -> None` creates one empty
workspace. It sits in the catalog conversation where `exists` and `data_type_of` already live.
`ScratchFileManager.create_workspaces` calls it through the toolbox that `runtime/` hands it, so
`staging/` still imports no engine (`03-architecture.md` §4.1) and the manager still owns every
path in the pod scratch root (`02-runtime.md` §4.2): the port creates what the manager names
and chooses nothing. `WorkspaceFormat` moves from `staging/workspace.py` to `ports/`, because a
port signature now names it; `staging/workspace.py` keeps the join rule, name legality and the
name budget. Every adapter implements the method, the in-memory one by recording the workspace,
and the conformance suite covers it on every adapter.

> *Considered and rejected:* a creation callable injected into the manager by `runtime/` and
> taken from the adapter, which opens a second channel from adapter to staging that bypasses
> the `Toolbox`; and lazy creation by the adapter on the first write into a missing workspace,
> which hides a failure inside an unrelated call and makes the scratch dump's layout depend on
> call order.

`destination:` `ports/table_ops.py`; `staging/scratch.py` docstring; `02-runtime.md` §4.2.

## A6. Partitioning — ownership

**A6.1 Fan-in selects by centroid, not by a carried field and not by clipping.**

> *Superseded:* an earlier position carried ownership as a durable field, and a later one
> resolved it through a fan-out ownership lookup table. Both fell to two cases: "join largest
> feature within distance" makes `PARTITION_FIELD` a field-map collision because it exists on
> both sides of the join, and a feature with four parents holding mixed values has no defensible
> answer. The deeper reason is structural — ownership as an ordinary attribute asks every
> operation to preserve something it has no reason to know about, which is the class of
> invariant `02-runtime.md` §7.2 opens by saying erodes.

Decisive property: fan-in centroid selection **adds no new correctness requirement**. Every
failure mode reduces to §7.1 halo adequacy, which is already unconditional and mechanically
tested. Field-SELECT adds a requirement reducible to nothing but discipline. CLIP actively
violates §7.2 — clipping at extent boundaries makes output geometry K-dependent, so the K=4 vs
K=16 diff can never pass.
`destination:` `02-runtime.md` §7; new ADR on partition ownership.

**A6.2** Preconditions: partitions tile without overlap (validate `custom_partition_feature` for
this, not just geometry type); a half-open boundary convention; displacement well inside the
halo.
`destination:` `02-runtime.md` §7.

**A6.3** Selection is **total by construction**: claim if the centroid is in my polygon, *or* if
it is in no polygon and my polygon is nearest. Ties resolve to lowest partition index, in one
shared helper rather than a rule restated in two places. Only the outer boundary of the union
can orphan a feature; interior crossings are claimed by the neighbour.
`destination:` `02-runtime.md` §7.

**A6.4** Non-spatial TABLE outputs have no centroid (`ROAD_RANKS` is one). They are kept by
ownership-of-id against the fan-out assignment.
`destination:` `02-runtime.md` §7.

**A6.5** Fan-in selection is **not** a `DROPPED` event. The same feature appears in several jobs
as context; discarding non-owning copies is deduplication of one identity.
`destination:` `02-runtime.md` §7; lineage module docstring.

**A6.6 Fan-out and fan-in mint nothing.** Both only select. This holds only while no
partitioning strategy clips geometry; if one is introduced, fan-in becomes a minter and takes an
ordinary minter id.

*Clarified by A24.1:* fan-out **applies** the ingest map to a cross-run `Derived` input by joining
on `incoming_lineage_id`. That is not minting — ingest allocated the ids, fan-out writes them
where the copy branch would have written them earlier. No exception to this rule.
`destination:` `02-runtime.md` §7.

## A7. Partitioning — the validation experiment

Run centroid selection as a silent shadow alongside the current attribute selection in
`PartitionIterator`, compare at the end, log the result per run. This validates A6 before the
stage architecture depends on it.

**A7.1** Hook: `custom_tools/general_tools/partition_iterator.py:1847`
(`_extract_partition_output`) already receives `iteration_partition`, the polygon
`HAVE_THEIR_CENTER_IN` needs. `write_documentation` (`:769`) already jsonifies dataclasses.

**A7.2** Comparison must be **multiset equality on (id, geometry)**, not count plus bidirectional
existence. Count-plus-existence is sufficient only if control has no coincident geometries;
adding the id makes it airtight regardless. With a unique id, comparing id multisets alone
settles loss and duplication. Implementation: hash, build a `Counter` on each side, compare —
O(n), no pairwise matching.

**A7.3** Exact comparison is valid because both extractions are pure selections over the same
iteration output, so matching features are bit-identical. This is also why CLIP outputs must be
excluded — `PairwiseClip` modifies geometry.

**A7.4** Add a per-feature id to `PartitionIterator`. `PARTITION_ID_FIELD` (`:1825`) is on the
partition polygons, and the only per-feature field is `PARTITION_FIELD` (1/0).

**A7.5** Log the **drift distribution** (pre- to post-processing centroid distance), not
pass/fail. Margin is the answer to the "95–99% deterministic" worry; a boolean is not. Read line
and polygon distributions separately — arcpy's "center" is the midpoint for lines and the
centroid for polygons, so line drift will be wider.

**A7.6** Classify mismatch direction before concluding. Present in test but absent from control,
with a null `PARTITION_FIELD`, means the feature was created during processing and **control
drops it today** — the improvement case, not the risk case. A strict equality gate would misread
it as failure.

**A7.7** Orphan handling: test "in no partition" once against the dissolved union, then
nearest-polygon only on that small set. Use `self.partition_feature` (complete from the start),
**not** `partition_features_all` (accumulated during iteration, so it answers differently
depending on order).

**A7.8** Record the claim, not just the result: `(per_feature_id, partition_id, claim_reason ∈
{centroid_in, nearest_orphan})`. Keep per-partition counters even though the verdict is global,
so a failure is diagnosable without re-running.

**A7.9** Synthetic suite with known cardinality — generalization gives no natural oracle, since
reducing feature count is the job. Transforms: point moved randomly within the context radius;
line extended; polygon one-sided buffer. Add a no-op control (any disagreement is a harness
bug), a deliberate-drop transform (confirms no false loss reporting), and a **directed** boundary
case rather than relying on random movement to hit one. The suite's orphan rate is not an
estimate of the production rate.

**A7.10** Scope boundary: `PartitionIterator` owns "I do not lose or duplicate data because of
partitioning." Drift and bleed are the domain's to monitor. The warning carries a magnitude
(orphan count, drift distribution), not a boolean.

**Destinations, per item.** Section-level destinations were removed here: if half the technique
is written up and half is not, nothing records which half.

| item | destination |
|---|---|
| A7.1 | retires with `partition_iterator.py` — hook location only |
| A7.2 | `02-runtime.md` §7.2 — multiset-on-(id, geometry) is the general comparison technique |
| A7.3 | `02-runtime.md` §7.2 — why pure selections permit exact comparison, and why CLIP cannot |
| A7.4 | retires with `partition_iterator.py` |
| A7.5 | `02-runtime.md` §7.2 — drift distribution over pass/fail, and the line/polygon split |
| A7.6 | `02-runtime.md` §7.2 — directional classification before verdict |
| A7.7 | retires with `partition_iterator.py` — but the dissolved-union-then-nearest ordering goes to `02-runtime.md` §7 as part of A6.3 |
| A7.8 | `02-runtime.md` §7.2 — the claim record shape |
| A7.9 | `02-runtime.md` §7.2 — the synthetic-oracle technique, including the no-op and deliberate-drop controls |
| A7.10 | `02-runtime.md` §7 — the ownership/drift responsibility split |

## A8. Why the future fan-in is structurally easier

Recorded because it justifies A7 being conservative rather than optimistic: validating under the
harder constraint means a pass there certainly holds under batch fan-in.

The current fan-in makes K independent, unverifiable, irreversible decisions; the future one
makes a single reversible decision with all evidence present.

- **Exactly-once becomes an assertion rather than an invariant.** In isolation, pod *i* cannot
  know whether *j* also appended, and OIDs are reassigned so attribution is lost. In batch,
  duplication is a group-by and loss is a set difference, both computable before anything is
  written.
- **Predicate versus assignment.** Isolation requires a provably mutually-exclusive-and-exhaustive
  predicate; batch just assigns.
- **Ties resolve once, visibly**, instead of K pods independently computing the same tiebreak
  with no way to verify each other.
- **Retry safety** — §7.4 already states "all appending [must] happen in fan-in."

`destination:` `02-runtime.md` §7.

## A9. Identity model

**A9.1** Three roles.

| | purpose | field cardinality | lifetime |
|---|---|---|---|
| native index | iteration, in-dataset keying | 1:1 | until the dataset is next written |
| `work_key_NNN` | algorithm row keys, new-object identity within an operation | 1:1 | operation-scoped |
| `lineage_id` | lineage, forensics, and id-keyed joins **only within a span with no cardinality change** | **1:1 — one row, one id** | whole run |

> **Note.** The lineage *relation* is N:M and lives in the edges, never in the field — a scalar
> cannot hold a set, which is the founding argument for the edge mechanism (A11.1). Do not read
> the 1:1 as an accident: it is the uniqueness assertion that alarms on accidental fan-out from a
> bad join.

> *Superseded (twice).* An earlier three-id proposal (OID / SOID / ROID) collapsed. `SOID` as
> specified was many-to-many and therefore not a column — the delimited-string workaround is
> exactly `ramps.py`'s `orig_lines_id` and `line_topology.py`'s `CONCATENATE_obj_id_txt`, which
> the refactor is removing. `ROID` at 1:1 loses splits: when road X becomes three pieces and one
> later disappears, X's id is still present and the forensic query reports nothing missing. The
> two purposes collapsed into one field plus drop diagnostics.
>
> *Superseded again.* That field was called `origin_id` and was renamed `lineage_id`, because it
> is re-minted on cardinality change — it holds current identity, and origin is recoverable only
> through the log. `origin_id` no longer exists anywhere.
>
> *Superseded a third time.* The cardinality column read "1:N across a split," which describes
> the inheritance model A11.2 explicitly rejects. Under minting, `1 → (g1..g5)` is five distinct
> ids. The error mattered: a reader concluding duplicates are expected does not build the
> uniqueness assertion.

`destination:` new ADR on identity; `01-terminology.md`.

**A9.2** Native index goes behind the port. Contract is narrow: **valid until this dataset is
next written**. Backends differ — GeoPackage rowid is stable, Postgres `ctid` moves on update —
so this is a real contract line, not a passthrough.
`destination:` `ports/table_ops.py`.

**A9.3** `work_key` is a flat allocator — `work_key_001`, `work_key_002` — not a
`ScratchScope`-style trail. The divergence is principled: a scratch dataset's leaf name is a
literal *because a human reads it in a scratch dump*; a work-key name is read by nobody outside
the allocating pod, so it needs uniqueness and brevity, not meaning. Two consequences:
allocation order need not be deterministic (the name never escapes), and cross-pod collisions
are irrelevant.
`destination:` work-key module docstring.

**A9.4** `work_key` is **operation-scoped**, swept at operation exit. Stage scope was considered
and rejected: `OperationFn` is `Callable[..., None]` and operations communicate only through
handles, so operation A has no channel to tell B the name it allocated. A field that must cross
an operation boundary is a **declared domain field with a real name**, not an allocated one.
`ramps.py`'s `obj_id_txt` and `line_topology.py`'s `ORIGINAL_ID` both stay inside one operation,
so this is sufficient. Keep a stage-level sweep as a backstop that should find nothing.
`destination:` work-key module docstring.

**A9.5** The sweep has two jobs, and the second is the enforcement: delete registered fields from
outputs, **and fail on any field matching the naming convention that is not in the registry** —
that is someone bypassing the API. The registry records `(name, operation, dataset)` into
operation metadata, which gives diagnosability without putting it in the name.
`destination:` work-key module docstring; `02-runtime.md` §8.

**A9.6** Ordering: `_apply_product_schema` uses `map_fields(keep_unmapped=False)` and already
drops unmapped fields, so the sweep is redundant there. It is the *only* protection for
`ROAD_RANKS`, `SNAP_DISPLACEMENT` and `JUNCTION_POINTS`, which do not go through product
mapping. It must run on every declared output including TABLEs.
`destination:` work-key module docstring.

**A9.7** Work-key API surface, ranked by evidence.

*Tier 1 — duplicated call sites today:* `allocate(input, type)`; `key.name`;
`key.lookup(input) -> Mapping[native_index, int]` (`line_topology.py:1560` plus open-coded
copies); `key.carry(source, output)` (`:2252`, `:2277`); `key.where_in(ids)` (replaces
`_where_in_ints` at `:811` with its `AddFieldDelimiters` quoting).

*Tier 2:* a `GENERATED` sentinel matching `line_topology.py`'s existing
`GENERATED_ORIGINAL_ID_SENTINEL = -1`.

*Out of scope:* dissolve-with-CONCATENATE parsing — that is "which inputs became this output,"
which belongs to the parents mechanism (A11.1).
`destination:` work-key module docstring.

**A9.8** Evidence for the API: the same seven-line "ensure the field exists and equals the OID"
guard appears verbatim at `railways_generalization.py:755` and `:1421`, and again at
`line_topology.py:1913` and `:1931`. Nine spellings of one concept across the repo:
`orig_ob_id`, `dang_id`, `obj_id_txt`, `orig_lines_id`, `uid`, `ramp_id`, `src_oid`,
`line_gap_original_id`, `bufferID`.
`destination:` `04-migration.md`.

**A9.9** Scope shrinks with `lineage_id`. Of roughly 14 allocate sites: **Cause A** (mint a local
id because nothing on the input is worth preserving — `src_oid`, `orig_ob_id`) disappears
entirely; **Cause B** (cardinality change, a scalar cannot hold the answer — `obj_id_txt` +
CONCATENATE) goes to the parents mechanism; **Cause C** (new-object identity, algorithm row keys
— `dang_id`, `ramp_id`, `ORIGINAL_ID`) is what the API is for.
`destination:` `04-migration.md`.

**A9.10** Per-feature data that must survive a cardinality change travels **as an attribute on
the feature**. Where a COLLAPSE must carry an attribute, the combining rule is stated at the call
site (`dissolve(statistics=((RANK, MAX),))`) — visible and arguable, unlike a silently empty
join.

Where an operation must join, it joins on a **domain key** — a field whose value is determined by
the data (`kommunenummer`, `vegkategori`, a source system's own id) — never on `lineage_id`. A
domain key's value is preserved by attribute propagation through COLLAPSE and SPLIT;
`lineage_id` is re-minted. Ids either side of a cardinality change belong to different
**mint generations** and will not join. A `lineage_id`-keyed join is valid only across a span with
no cardinality change, which is not locally checkable, so it is not a pattern to reach for.
`destination:` new ADR on identity; `02-runtime.md` §2.4.

**A9.11 A combining rule is evaluated over the parents of each output row.** The combining rule
"reduces several parents' values to one" (`01-terminology.md`, *combining rule*); parents are "which
input rows produced an output row". So the value written on an output row of a `GROUP` method is
the rule over that row's parents and nothing wider. Under single-part output a dissolve key that
splits into several parts has several output rows, each with its own parent set and its own
value. An engine whose own statistics option computes over the whole key does not implement this
contract, and the adapter must not use that option to satisfy it; the measurement that found one
doing so is in `temp/findings/n1_correspondence.md` §3.9. How the adapter meets the contract is B17's.
`destination:` `ports/geometry_ops.py`, `dissolve` docstring; A11.14 gains a pointer.

**A9.12 The `statistics` value type.** `dissolve` takes
`statistics: tuple[StatisticSpec, ...] = ()`, where `StatisticSpec(source, statistic, output)` is
a frozen dataclass — the source field, the statistic, the output field name — and `Statistic` is a
project enum with exactly `MIN`, `MAX`, `SUM`, `MEAN`, `COUNT`. No `FIRST`, no `LAST`, no
`CONCATENATE`: the first two depend on row order, which is not a contract (A15.4); the third was
measured at 7,841 s over one 10^6 group and was the transport of a retired mechanism (A14.1). The
docstring states **null handling** — a null source value is skipped, `COUNT` counts non-null
values, an output row whose parents are all null gets null — and **output types** — `MIN`, `MAX`
and `SUM` keep the source field's type, `MEAN` is DOUBLE, `COUNT` is LONG — and **forbids
`lineage_id` as a source** (A9.10: ids never combine). Per-output-row evaluation is A9.11.
`destination:` `ports/geometry_ops.py`, beside the enums.

## A10. `lineage_id` layout and allocation

**A10.1** `lineage_id` is a signed 64-bit field (`FieldType.BIGINT`), but the usable range is
**53 bits, not 63**. ArcGIS Pro's big integer and 64-bit Object ID types are limited to safe
integers below 2⁵³ — a client API constraint, per Esri's documentation and the 3.2 geodatabase
release notes.

```
raw       = positive, allocated densely from 1 at ingest
generated = negative; magnitude = [ minter_id (20) | local counter (32) ]

magnitude ≤ 2⁵² − 1 = 4,503,599,627,370,495        one bit under the ceiling
```

- `minter_id`: 20 bits → 1,048,575 usable values (0 reserved invalid). Against partition counts
  of 10 to thousands across roughly 10 stages and several pipelines, about 30× headroom. Because
  a retry reuses its minter id (A10.4), this budget covers *logical jobs*, not attempts.
- local counter: 32 bits → 4,294,967,295 ids per job. Against the worst case known (river gap
  generation, about 8M features), about 500×.
- Raw ids are dense sequential from 1, so their ceiling is total ingested features per run —
  nowhere near the limit, and they share the same field and the same 2⁵³ budget.

Signed rather than unsigned because unsigned is unavailable in Postgres, SQLite/GeoPackage and
ArcGIS BigInteger alike. Negative-for-generated rather than a high bit, because setting bit 63
makes every decode a two's-complement problem in Python; it also matches
`line_topology.py:1337`'s existing `GENERATED_ORIGINAL_ID_SENTINEL = -1`.

**The 53-bit ceiling is ArcPy-specific.** SQLite/GeoPackage `INTEGER` and Postgres `BIGINT` are
genuinely 64-bit. The layout is fixed at the most restrictive backend because widening later is a
domain-visible schema change at every call site that stores a lineage id, not an adapter swap.

> *Superseded:* the layout was originally sign + minter (24) + counter (39) = 63 bits of
> magnitude, on the assumption that a signed 64-bit field gives 63 usable bits. It does not,
> under ArcPy. Ten bits over.

`destination:` new ADR on lineage id allocation.

**A10.2** `minter_id` is **run-scoped**, not stage-scoped. A per-stage pod index collides
in-band: stage 1 pod 42 mints `g(42,1)`, that feature flows into stage 2, stage 2 pod 42 mints
its own `g(42,1)` — two features, one id, one dataset. Orchestration hands out a monotonic
minter id across every job in every stage at dispatch; no data read required, since stage and
partition index are known then. `minter_id = 0` is reserved invalid so a zero minter is
detectable as a bug. The dispatch counter asserts `1 ≤ minter_id ≤ 2²⁰−1`.
`destination:` same ADR as A10.1; `02-runtime.md` §6.

**A10.3** Flat counter rather than separate stage and partition bit fields, because partition
counts range from 10 to thousands and per-component budgets overflow independently. With only 20
bits for the minter this argument is stronger, not weaker. Decomposition lives in a **dispatch
registry** (`minter_id → stage, partition_index`), merged at fan-in alongside the job logs — the
same shape as the work-key registry.

> *Superseded:* pods writing placeholder ids for fan-in to swap. That is a transitive
> multi-table rewrite — generated ids reference other generated ids as parents in the log — where
> a missed reference fails silently.

`destination:` same ADR as A10.1.

**A10.4** No attempt number in the prefix. A retry reuses its minter id; safety comes from
**wholesale replacement of the job's artifacts**, not from deterministic re-mint (mint order
follows tool row iteration order, which is not contractually stable). This requires the per-job
log to be an output artifact written pod-local and uploaded on success, never streamed to shared
storage — otherwise a dead attempt's records collide with the retry's. Live progress, if wanted,
goes to a separate diagnostic channel fan-in never reads.
`destination:` same ADR as A10.1; `02-runtime.md` §7.4.

**A10.5** Midpoint restart persists the counter high-water mark in the checkpoint and continues
from *n+1*. Minter id is stable per logical job; the counter is checkpoint state. A job exceeding
2³²−1 mints must fail loudly rather than wrap into another minter's space.
`destination:` same ADR as A10.1; ADR-0009.

**A10.6 Ingest is a distinct, copying step**, run-scoped, before any stage executes.

*Why distinct:* `NVDB_ROADS` is read by road `NETWORK` and building `DISPLACEMENT`. If each
fan-out allocated, the same source feature would get different ids per stage. Allocation happens
once per source per run, so **fan-out mints nothing** (A6.6) survives intact. Ingest covers
`ExternalSource` only; `Derived` inputs already carry ids.

*Why copying rather than a side map — **for `ExternalSource` only**:* a map keyed on the source's
native index can only be joined while those indices are still valid, i.e. inside fan-out's
download path, which couples ingest to fan-out's implementation. The copy decouples it.
Troubleshooting value is a bonus, not the justification.

> *Narrowed by A24.* This argument was written for `ExternalSource` and does **not** generalise.
> A cross-run `Derived` or `ProductIdentity` input already carries `lineage_id` as an ordinary
> **data column**, which survives download unchanged — so its map is keyed on a stable value and
> can be applied at any point, including after download. The coupling the copy exists to break is
> not present. See A24.1 for the resulting three-way rule.

*Why at all:* native indices are unique per source object, not across the run — `N50_ROAD`
OBJECTID 1 and `LAKES` OBJECTID 1 are both 1, and the object half of a composite key is
unrecoverable from a feature carrying only the id after cross-object derivation.

*Consequence:* the "no raw id ≤ 0" assertion disappears; both halves now come from our own
allocator rather than from source data we do not control.
`destination:` same ADR as A10.1; `02-runtime.md` §6.

**A10.7** Raw ids **do not use the minter/counter layout** — they are dense positive integers, so
ingest consumes no `minter_id`. Ingest may still run one job per source for I/O parallelism; each
job draws a **disjoint range** from a single run-scoped counter, and the per-source range is
recorded in the ingest artifact alongside the `native_index → lineage_id` map.

Allocation order need not be deterministic. Cross-run comparison is out of scope (A21), and
within a run the artifact records the assignment, so nothing depends on reproducing it.
`destination:` same ADR as A10.1.

## A11. Lineage — what it is and where it lives

**A11.1** The **parents handle** and the **lineage log** are different mechanisms, not
alternatives.

- *Parents handle* — in-band, one operation, scratch-scoped, consumed by domain code that acts on
  the parent set. Optional out-param on collapse methods.
- *Lineage log* — out-of-band, run-scoped, write-only. Nothing in the pipeline reads it mid-run.
  If domain code could read it, every operation could depend on every prior operation's metadata
  through a back door.

Chaining parents handles across twelve stages to answer "where did raw id 1 go" would mean
persisting every one of them — building a lineage log by accident, with per-method plumbing
instead of one mechanism.

> *Naming note.* This mechanism was called *correspondence* through most of the design
> discussion, including in the port parameter name and the column constants. It is **parents**
> everywhere: the out-param is `parents:`, the table columns are `PARENT_ID` and `CHILD_ID`.
> `source_rows` was considered and rejected because `source` already means `ExternalSource` in
> this repository (`01-terminology.md` §2).

`destination:` new ADR on lineage; lineage module docstring.

**A11.2 Mint on any net cardinality change, including 1:N.**

> *Considered and rejected:* letting split pieces inherit the parent id. It fails on the case
> generalization produces constantly — a road splits into five, two stubs are dropped, three
> survive. Inheritance forces the log to say both `1 DROPPED` and `1 present in output`. With
> minting: `1 → (g1..g5)`, then `g3 DROPPED`, `g4 DROPPED`.

`destination:` same ADR as A11.1.

**A11.3 Never collapse an id back to a previous value.** If `g1..g5` re-merge, mint a new id.
Checking whether the parent set matches a prior mint gives the wrong answer precisely when
generalization is working — if a stub was dropped in between, the result is not the original
feature. The id records that a change happened; the log records what it was; equivalence is
derived at query time.
`destination:` same ADR as A11.1.

**A11.4 Edges are emitted at operation boundaries from net effect, not per port call.**
Split-and-remerge inside one operation is invisible. This completes the split: intra-operation
cardinality churn is `work_key`'s problem, net cross-boundary change is lineage's.

*Consequence for operation-authoring guidance:* an operation that both splits and drops reports
only the surviving children — "road 1 became 3 pieces" without recording that 40% of it
vanished. Operation boundaries are therefore load-bearing for forensic resolution.
`destination:` same ADR as A11.1; `02-runtime.md` §2.4 (the authoring consequence).

**A11.4a Mint from the pre-explosion handle, never from the exploded one.**

When an operation explodes a handle to compute something and then creates features from the
result, the `mint(parents=…)` subject must be the **pre-explosion** handle with the surviving
parents named — not the exploded intermediate.

**The reason is semantic, and it holds whatever the id map costs.** Minting an exploded
intermediate **pollutes the lineage graph with rows that are not features**. Candidate connection
points, near-table rows and segment twins are *observations* of a feature, not features in their
own right — the same distinction that makes `extract_vertices` `FOREIGN` rather than `MINT`
(A12.12). Mint them and a backward walk from a river traverses thousands of candidates before
reaching anything a cartographer would recognise, which stops answering the question the log
exists for. The graph is the deliverable; its size is not the argument.

**Map size is the consequence, not the basis.** Under A15.3's disk-backed map a 280M-row subject
is slow rather than fatal, so cost alone would only ever justify a performance note.

Worked evidence, `custom_tools/general_tools/line_topology.py` as called by
`generalization/n100/river/fix_river_topology_gaps.py`:

| handle | rows | reaches the output? |
|---|---|---|
| `input_lines` → `lines_copy` | ~70K rivers | **yes** — `_write_output` is `CopyFeatures(lines_copy, output_lines)` |
| `conn_endpoints` (`FeatureVerticesToPoints … BOTH_ENDS`) | 2× parents | no — feeds `GenerateNearTable`, read into Python |
| segmented twins, near tables, candidate FC | millions | no — read to build a Python `PlanByParent` |
| generated connectors | ~10⁴ | yes — inserted into `lines_copy` by `_insert_generated_lines` |

The correct subject is `lines_copy` at ~70K rows. Minting from the candidate set instead would be
~8M rows on the basin measured, and the largest basin is 35× that — roughly 280M.

**`ORIGINAL_ID` is not a `lineage_id`, and `FillLineGaps` retires it.** An earlier draft claimed
`_GeneratedLineRecord.parent_original_id` already *is* the `mint(parents=…)` argument. It is not:
`line_gap_original_id` is an OID copy, one of the nine spellings A9.8 lists. It serves two roles,
and the two-field split (A9.1) separates them:

- *algorithm row key* — keying `PlanByParent`, adjacency, the `ParentId` space. `lines_copy` is a
  copy of the input, so its rows already carry unique `lineage_id`s; the algorithm keys on those
  and needs no separate key.
- *parent reference on generated lines* — becomes a read of the input's `lineage_id`, passed to
  `mint(parents=…)`.

`GENERATED_ORIGINAL_ID_SENTINEL = -1` is subsumed too: minted ids are negative by construction
(A10.1), so generated rows stay distinguishable by sign without a sentinel.

> *Corrects A9.9*, which classes `ORIGINAL_ID` under Cause C (algorithm row keys) alongside
> `dang_id` and `ramp_id`. That is right for the first role and wrong for the second — the site is
> split between the two causes, not assigned to one.

**The enforcement gap.** For a `FOREIGN` explosion this rule is already structural: A12.9's
plan-time check rejects a `FOREIGN`-terminal handle named as the `subject` of a downstream `CARRY`
or `MINT`, and `extract_vertices` is `MANY + FOREIGN`. For a **`MINT`** explosion it is not, and
**a plan-time check cannot close it** — `explode_multipart` then `dissolve` is legitimate and
common, so "a `MANY` in the ancestry, later used as a `MINT` subject" would flag correct code.

**Two runtime ceilings close it, and they are different kinds of claim.** The facade knows a
subject's row count *before* it builds the map, so both are cheap.

| | **design ceiling** | **resource ceiling** |
|---|---|---|
| what it asserts | what a legitimate subject looks like | what this pod can build in acceptable time |
| value | 10M rows, provisional | method from T0.6's curve, calibrated on the pod |
| varies by environment | **no** | yes |
| lives | a constant in the lineage module, challengeable in review like a `context_radius_m` | the composition root, resolved at pod construction |
| tripping it means | **fix the operation** | resize the pod, or accept the build time |

Keeping them separate is the point. A single resource-derived ceiling would let a well-provisioned
pod silently permit minting 280M candidates while a small one flags it — making a **design** error
environment-dependent, which is the prod-only failure class this rule exists to remove. Minting an
exploded intermediate is wrong at any pod size.

**The design ceiling is checked first.** For a 280M subject, *fix the operation* is the useful
message regardless of what the pod could have built; resource-first would report a resource
problem for a design bug and send someone to resize a node.

**A resource ceiling below the design ceiling is legal, and tripping it is not a code defect.**
A small pod may be unable to build a legitimate 8M subject in acceptable time even though 8M is
well within design. The two are **independent bounds, not a nested pair** — the natural reading of
"two ceilings" is that design is the tighter one, and that is not guaranteed. There the fix is the
pod or the time tolerance, never the operation.

The messages name which ceiling tripped, because the fixes differ:

```
lineage design ceiling exceeded: operation resolve_river_gaps, handle candidates,
subject 280,431,902 rows (design ceiling 10,000,000).
A subject this large usually means minting from an exploded intermediate — see A11.4a.

lineage map budget exceeded: operation X, handle Y, subject 8,400,000 rows
(this pod's budget 6,000,000, set from build-time measurement).
The subject is within design; resize the pod or raise the build-time tolerance.
```

Either way the result is a traceback naming the call site, reproducible on the same input, instead
of an OOMKill that appears only in production. That trade — hours of bisection against a one-line
answer — is the one we rank first.
`destination:` `02-runtime.md` §2.4 for the rule; the lineage module docstring for the ceilings.

**A11.5 Kind is derived by the runtime, never declared.** `EdgeKind` has four values.

> *Renamed.* `TRANSFORMED` and `DERIVED` became `PARENTS_CONSUMED` and `PARENTS_KEPT`.
> `DERIVED` was one capitalisation from `Derived`, the `DataObject` a stage produces — two
> unrelated concepts that **sound identical spoken aloud**, with no way to disambiguate by ear in
> a review. The replacements are verbose, which is fine in an enum read from logs, and they name
> the distinction that is the whole point of having two values.

| value | derived from |
|---|---|
| `PARENTS_CONSUMED` | every parent absent from this operation's outputs |
| `PARENTS_KEPT` | at least one parent survives in an output |
| `DROPPED` | no children |
| `CREATED` | `from_ids == ()` |

`CREATED` is required, not optional: without it assertion (2) in A16 fails on every legitimately
created feature. It covers both `mint(parents=())` for domain-built rows and parentless rows a
port method emits, under one mechanism, and contributes nothing to `T`.
`destination:` same ADR as A11.1.

**A11.6 Kind is descriptive; completeness is computed from set membership.** Partial consumption
— a dissolve where some parents also survive — makes kind-driven completeness wrong in both
directions: classify PARENTS_KEPT and the consumed parents go unaccounted; classify PARENTS_CONSUMED and
the survivors are counted twice. Use `T = { f ∈ from_ids of any edge : f ∉ O }`. Mixed edges then
need no special case, and completeness depends on data rather than on a label that could be
wrong.

> *Superseded:* an earlier formulation had only PARENTS_CONSUMED and DROPPED feeding completeness,
> with PARENTS_KEPT excluded by its label. Assertion (3) caught `T ∩ D` but nothing caught `T ∩ O`.

`destination:` same ADR as A11.1; `02-runtime.md` §8.

**A11.7 `DROPPED` is shape-independent** — derived from the boundary diff, never from a port
call. `select` is a pure preserve and is the most common producer of drops; `thin_road_network`
drops through domain logic.
`destination:` same ADR as A11.1.

**A11.8** Backward-walk termination: **in the Ins, or surviving in an Out, or not minted this
operation.** Without the middle clause, `resolve_ramps` — which mints centrelines into
`output_lines` and then junction points from them into `output_points` — emits `(1..5) → g5` and
`(1..5) → g9`, losing the real edge and making `g9` a sibling of its own parent. This bites on
any multi-output operation where an intermediate survives.
`destination:` lineage module docstring.

**A11.9 No dev-wired composition object.** The transitive mint chain composes on its own:
`g9 ← g5 ← (road_1..road_5)` falls out of the port calls with nothing wired.
`destination:` lineage module docstring.

**A11.10 Primary or majority parent stays out of the edge.** Where one parent is the cartographic
owner that is a domain attribute on the feature. Two reasons: putting it in the edge gives
someone a reason to read the lineage log mid-run, which is the coupling A11.1 rules out; and
set-level majority is partition-dependent and therefore meaningless — a lake-to-centerline merge
might be majority-river globally and not in a given partition. Object membership is declared by
`StageOutput`, never computed from data.
`destination:` same ADR as A11.1.

**A11.11 Lineage lives above the ports, not in the adapter and not in operation bodies.** The
port reports row parentage in its own vocabulary — native indices; the layer above maps to
`lineage_id`, mints, writes the field, records the edge. "A dissolve that cannot report which
input rows it combined is under-specified as a dissolve" is a statement about the geometry
operation, not about lineage.

> *Considered and rejected:* per-method wrappers implementing the Protocol. Roughly 40 delegating
> methods, two implementations of one Protocol free to drift, easy to use wrongly.

Chosen: `@row_shape` declarations on the Protocol, read by one generic facade. The facade looks
up `GeometryOps.dissolve.__row_shape__` — on the **Protocol**, not the adapter instance — so
adapters need no decoration and cannot drift. Cost is one `cast` at the composition root plus a
conformance test asserting every Protocol method is reachable; the same trade as
`ports/toolbox.py`'s single load-bearing cast.
`destination:` same ADR as A11.1; `03-architecture.md` §4.

**A11.12** Operations do **not** receive an injected `lineage`. The facade mints;
`mint(parents=...)` appears only where rows are built in Python with no handle to point at.

`CARRY` + no parent **fails, it does not mint**. `CARRY` needs no parents table — ids ride along
as attributes — so a parentless row appears as a null `lineage_id` and the boundary sweep already
sees it. Minting there would hide a mis-declared method: `CARRY` says output rows keep the
subject's id, so a row without one means the declaration should have been `MINT`. Same principle
as detect-unregistered being the enforcement in the work-key sweep (A9.5).

`FOREIGN` never gets a `lineage_id`, parented or not, and never emits an edge. A null in the ref
column is legitimate data — `spatial_join` with no match, `nearest_neighbor` with nothing in
range — so the sweep must not treat a null ref like a null `lineage_id`.
`destination:` lineage module docstring.

**A11.13** A `FOREIGN` output carries no `lineage_id`, so the per-row obligation that catches a
broken chain does not apply to it. When a `FOREIGN` handle's ref column feeds a rebuild — extract
vertices, manipulate points, write new geometry — **the ref column is the lineage path**, and
dropping it mid-manipulation is undetectable at the point it happens. The rebuild then mints with
empty parents, emits `CREATED`, and the boundary diff reports the parent features `DROPPED`: the
map shows the feature, the log says it was removed. Carry the ref column through every
intermediate structure and pass it to `mint(parents=...)`.
`destination:` `02-runtime.md` §2.4, alongside A11.4's authoring consequence.

**A11.14** A combining rule on a collapse (`dissolve(statistics=((RANK, MAX),))`) is **domain
logic executing inside the collapse**. The edge records that the collapse happened and which
parents fed it — never which parent's value survived. The log does not know, and should not:
this is A11.10's rule reaching the same conclusion from the other direction. Set-level primacy is
partition-dependent and would give someone a reason to read the log mid-run.

If which-parent-won matters downstream, the combining rule writes it as a **domain attribute**
chosen by the domain — a value the data determines, on the feature, propagating through later
collapses like any other attribute. Never an id, for A9.10's reason.
`destination:` same ADR as A11.1.

> *See A9.11 (2026-09-17):* the combining rule is evaluated over the parents of each output row,
> never over the whole key.

**A11.15 Parents are an out-param on every `MINT` method, in native indices at the port.**

Every port method with an output declared `ids=MINT` carries
`parents: ScratchHandle | None = None`. When it is not `None` the adapter writes a TABLE of
`(PARENT_ID, CHILD_ID)` rows to it, one row per (input row, output row) pair, both columns in the
port's own vocabulary: the input's native index and the output's native index (A11.11). When it is
`None` the adapter produces no parents and pays nothing for them.

Four rules, in addition:

(a) **`PARENT_ID` references the `subject=` input only.** A method with a `context=` input
(`clip`, `intersection`, `difference`) never reports context rows as parents; the context
influenced the geometry without contributing identity (A12.2).

(b) **Naming.** The parameter is `parents` when the method has one `MINT` output and
`<output>_parents` when it has several. No method on the surface today needs the second form:
every `MINT` method in A12.11 has a single `MINT` output, and the secondary outputs
(`simplify.collapsed_points`, `displace_features.displacement`, `select_network.dropped`) are
`CARRY` or open under B11. The second form is reserved so that a future method does not invent a
third.

(c) **The facade always passes its own scratch handle to the port**, reads the native pairs, maps
them to `lineage_id` and mints (A11.11, A12.4). When the domain also passed `parents=`, the facade
writes the **`lineage_id` relation** to the domain's handle — the same `(PARENT_ID, CHILD_ID)`
columns, holding `lineage_id` values — so the domain never sees a native index (A9.2). The port
never receives the domain's handle.

(d) **A domain `parents=` request on a subject without `lineage_id` raises**, in the facade, before
the port is called. There is nothing to translate the pairs to, and a silently native-indexed
table would be exactly the join A9.10 forbids.

The lineage facade is a caller in its own right. It passes its handle on every `MINT` call whose
subject is lineage-bearing (A15.6). This is why the channel is on the Protocol and not private to
the facade: the conformance suite drives the Protocol directly (T4.11, B10) and asserts the
reported pairs.

Supersedes T2.4's "only `dissolve` gets the parameter" and narrows B6 to the domain-facing
question: which methods have a domain caller wanting the set. B6 is otherwise unchanged.
`destination:` `ports/geometry_ops.py` and `ports/cartographic_ops.py` (the parameter, once per
method); the lineage module docstring (the facade's use, (c) and (d)).

## A12. The `@row_shape` grammar

**A12.1** `Rows(cardinality=..., ids=..., subject=... | refs=...)`. Two independent axes rather
than a single enum, because one+new is a real declarable judgment that a single enum had no cell
for.

- `cardinality` — rows per subject row: `ONE`, `MANY`, `GROUP`
- `ids` — `CARRY` (keep the subject's id), `MINT` (new ids, edges recorded), `FOREIGN` (no
  `lineage_id`; declared columns hold subject ids as foreign keys, so `refs={COL: "subject"}`
  replaces `subject=`)

> *Renamed.* The second axis was `identity=`. `ProductIdentity` is older and more load-bearing,
> and an unqualified "identity" in review could mean either. `ids=` says what the axis controls.

Deliberately not naming a value `TRANSFORM`: that word was an `EdgeKind`, and `EdgeKind` is
runtime-derived. Reusing it would blur declared against derived.

| | CARRY | MINT | FOREIGN |
|---|---|---|---|
| **ONE** | legal | legal | legal |
| **MANY** | **illegal** | legal | legal |
| **GROUP** | **illegal** | legal | **illegal** |

Three illegal cells, and the CI failure message states the reason:

- `GROUP + CARRY` — many parents, one row; a scalar cannot hold a set. The founding argument for
  the edge mechanism (A11.1).
- `GROUP + FOREIGN` — same.
- `MANY + CARRY` — **primary reason: this is the inheritance model A11.2 rejects.** Five split
  pieces all keeping id 1 leaves the log unable to express a partial drop. Secondary: the id
  repeats, breaking the 1:1 field cardinality that is the fan-out alarm (A9.1). *This grammar
  rule and A11.2 are the same rule stated twice.*

Together: **`CARRY` implies `ONE`.**

Cost, to state at the declaration: `ONE + MINT` emits one edge per row, O(input rows) — the most
expensive shape in the system, against one edge per group for `GROUP + MINT` and zero for
`ONE + CARRY`. Not a reason to forbid it, but it should be a deliberate choice with the cost
stated, or it becomes the default for anything that feels transformative and log volume grows on
the wrong axis.

> *Superseded (twice).* The grammar was first a single `SHAPE` enum of `PRESERVE / COLLAPSE /
> SPLIT / NONE`; then `NONE` was dropped and `REFERENCE` and `EXPAND` added; then the whole enum
> was replaced by these two axes. `REFERENCE` became `ids=FOREIGN` and `EXPAND` became
> `MANY + FOREIGN`, both folding into the grid rather than remaining special cases.

`destination:` new `ports/row_shape.py` module docstring; new ADR on lineage declaration.

**A12.2** `subject` versus `context` **is** PROCESSING versus CONTEXT, not a mirror of it —
the words are the same on purpose. `intersection` output rows *are* pieces of the roads; the
overlay influenced the result without contributing identity. Declaring both as subjects would
make every admin polygon an ancestor of every road piece.

> *Renamed.* The second was `reference=`, which collided with `snap(reference=…)` — a dataset
> being snapped to, semantically close enough to blur. `context=` also makes the
> PROCESSING/CONTEXT correspondence literal rather than something the docstring has to explain.

`destination:` `ports/row_shape.py`.

**A12.3** `NONE` is dropped. The template contains no genuine aggregate output — every table
write is per-feature or per-vertex — so every output declares a subject, and anything that cannot
must be argued rather than defaulting to an escape hatch. Re-adding the member later is a
one-line change.
`destination:` `ports/row_shape.py`.

**A12.4** Per-row behaviour comes from the parents table, not from the declaration: a dissolve
group with one parent carries the id and emits no edge; only groups with ≥2 mint. Same for
`MANY`. Methods that are mostly 1:1 in practice cost almost nothing, so no separate shape is
needed for them. This is runtime behaviour *inside* a cell and is not an argument for legalising
`GROUP + CARRY`.
`destination:` `ports/row_shape.py`.

**A12.5** CI check: every output parameter declares both axes; every `MINT` has a subject; every
`FOREIGN` has refs; the three illegal cells are rejected with their specific reason; every
subject and reference names a real input parameter. This replaces the type-checker guarantee the
wrapper approach would have given, and it is what makes forgetting impossible.
`destination:` `tests/unit/test_row_shape.py`; `02-runtime.md` §8.

**A12.5a Port handle parameters carry a direction.** Port Protocol handle parameters are annotated
`In` / `Out` from `core.operations`, plus a third marker for in-place mutators (T2.8) and a distinct
**`ParentsOut`** marker for the parents out-param of A11.15. T4.1's check then rejects: an `Out`
parameter with no `@row_shape` entry; a `@row_shape` key naming a parameter that is not `Out`; a
`subject`, `context` or `refs` value naming a parameter that is not `In`. **`ParentsOut` is exempt
from the first rule**: the parents table is a relation the facade consumes, not a row-shaped
output, and it never gets a `Rows` declaration. Rejected: a parameter-name convention, and the
"named by some declaration" rule, both for the reasons in `PROPOSALS-2026-09-14.md` §2.

**Timing: the annotations are written with the ports, in T2.9, not in T4.1.** The ports are about
to be written; annotating them afterwards means writing every signature twice. T4.1 adds the check
against annotations that already exist, and breaks it on purpose once. Resolves B12.
`destination:` `ports/row_shape.py` docstring; `02-runtime.md` §8 with A12.5.

**A12.6** In-place mutators (`add_field`, `calculate_field`, `join_field`, `delete_fields`) have
no output parameter and need a definition of "output parameter" that covers them. Most are
`ONE + CARRY`. `join_field` against a non-unique key **fans out rows**, a cardinality change the
grammar currently cannot see because there is no output param to declare — see B4.
`destination:` `ports/row_shape.py`.

**A12.7** The `read_rows → write_table` pipe defeats the grammar — the subject is a handle that is
not a parameter of `write_table`. Four of the five template sites pass the generator straight
through with no intervening transformation:

```
operations/road/__init__.py:454   match_report
operations/road/__init__.py:543   rank_table
operations/road/__init__.py:593   merge_report
operations/road/__init__.py:323   _vertex_deltas output
```

Solved by a **lineage-aware pipe**: `read_rows` on a scoped handle returns a private tracked
iterable of `(Row, id)` yielding plain `Row`; `write_rows` / `write_table` unwrap and stamp. The
facade does the wrapping, so adapters return plain rows and never see lineage. Writing to a
scoped output with untracked rows and no explicit `mint(parents=...)` is an error, not a silent
skip. The fifth site (`:243`, `_build_topology`'s `nodes`, built by `_node_rows` from graph
results) takes the explicit path.

> *Rejected:* `Row.parents`. It would spread lineage into every adapter constructing a `Row`,
> change `Row.__eq__`, and give domain code a field to branch on — the mid-run log read arriving
> by a different door.

> *Superseded in part, 2026-09-21 (A12.7a).* "Four of the five template sites carry lineage with
> no call-site change" and the error rule above are replaced by A12.7a. The tracked iterable
> stands, as the verification of a `CARRY` declaration rather than its source.

`destination:` `ports/table_ops.py`; lineage module docstring.

**A12.7a Writes declare their ids axis at the call site.** *Signed 2026-09-21 as proposed in
`PROPOSALS-2026-09-14.md` §3; resolves B13.* `write_rows` and `write_table` take a required
keyword, with no default, declaring the output's ids axis, in handles rather than parameter
names:

- **`CARRY` from a source handle.** The rows carry that handle's `lineage_id`, verified by
  whatever T4.4's pipe mechanism turns out to be.
- **`FOREIGN` with refs as a column → handle mapping.** No `lineage_id`; the named columns hold
  the handles' ids.
- **`MINT`.** Each row's id comes from `mint(parents=…)`, as A11.12 already permits for rows built
  in Python.

Required, so pyright reports an omission at the call site: A12.5's "forgetting is impossible"
extended to the one row-producing method it could not reach. The spelling, a `Rows`-like value
or three small constructors, is T4.4's to settle. The declaration is write-only for domain
code, the same class of statement as `mint(parents=…)`, so it reopens neither A11.12 nor the
rejection of `Row.parents`.

A12.7's error rule becomes three checks: for `CARRY`, the rows carry the source handle's ids; for
`MINT`, every row carries a mint; for `FOREIGN`, no `lineage_id` is written and the ref columns
exist. `SNAP_DISPLACEMENT` declares `FOREIGN`, and the contradiction with A15.6 is gone. The
axis is decoupled from the pipe mechanism, so the review's F25 stays open and unaffected.

Consequence for A12.5's check, recorded with the signature because the check is written before
the write methods land: an `Out` parameter whose row is declared at the call site is a category
of the grammar. The check requires the keyword on those two methods instead of a `@row_shape`
entry, and it is not an exemption: omitting the keyword fails.

Still open, carried from the proposal: what a ref column holds when the ref names a handle that
is itself `FOREIGN`. T4.4 states it.
`destination:` `ports/table_ops.py` (`write_rows` and `write_table` docstrings); the lineage
module docstring (the three checks).

**A12.8 — SUPERSEDED.** It argued that `validate_geometry`'s error rows are `PRESERVE` because
"the distinction is row correspondence, not feature-ness." That correction was right against the
single-axis grammar, where non-feature rows had nowhere else to go. The two-axis grid gives them
a home: they are `MANY + FOREIGN`. What the grid bought is precisely the ability to say "these
rows reference a subject without being it," which neither `PRESERVE` nor the discarded `NONE`
could express.
`destination:` none — superseded, retained as rationale only.

**A12.9** `FOREIGN` is terminal for lineage. Nothing downstream of a `FOREIGN` output can be
lineage-bearing without a `MINT` re-entering the chain. The plan-time check is **not** "a
`FOREIGN`-derived handle reaches a `StageOutput`" — that is legal, and `SNAP_DISPLACEMENT` is the
legitimate case. It is: **a `FOREIGN`-terminal handle is named as the `subject` of a downstream
`CARRY` or `MINT`.**
`destination:` `02-runtime.md` §8.

**A12.10** `collapse_to_point` is `ONE + CARRY`. A small building rendered as a point is the same
building at a coarser scale, and `MINT` would cost one edge per row on a high-volume operation.

**The precedent, since this is what people will cite:** *ids change when the feature stops
standing for the same real-world object, not when its geometry kind changes.* A polygon becoming
a point still stands for the same building — `CARRY`. Two carriageways becoming one centreline
stand for something the parents did not — `MINT`. The test at a new call site is "would I want
the log to record a transformation here?", and the edge-per-row cost is the tiebreaker when the
answer is genuinely unclear.

> *Reworded.* The original said "when the feature's **correspondence** to a real-world object
> changes" — using, in the sentence people will quote most often, the exact word retired in
> favour of `parents` (A11.1).

`ONE + MINT` stays legal and is currently empty. A lake polygon becoming a river centerline is
its likely first inhabitant: the centerline corresponds to a different object than the lake.
`destination:` `ports/cartographic_ops.py`; `ports/row_shape.py` (the precedent).

**A12.11** Reworked declarations across the port surface.

| method | cardinality | ids | subject / context / refs |
|---|---|---|---|
| `copy`, `select`, `densify`, `snap`, `make_valid`, `point_on_surface`, `centroid`, `convex_hull` | ONE | CARRY | `input` |
| `buffer` | ONE | CARRY | `input` |
| `buffer_dissolve` | GROUP | MINT | `input` |
| `simplify`, `smooth`, `displace_features` | ONE | CARRY | `input` |
| `simplify.collapsed_points` | ONE | CARRY | `input` |
| `displace_features.displacement` | ONE | CARRY | `input` |
| `propagate_displacement` | ONE | CARRY | subject `input`, context `displacement` |
| `merge` | ONE | CARRY | `inputs` |
| `select_network`, `select_network.dropped` | ONE | CARRY | `input` |
| `collapse_to_point` | ONE | CARRY | `input` |
| `extract_vertex` | ONE | FOREIGN | `{VERTEX_SOURCE: "input"}` |
| `extract_vertices` | MANY | FOREIGN | `{VERTEX_SOURCE: "input"}` |
| `validate_geometry` | MANY | FOREIGN | `{FEATURE_REF: "input"}` |
| `spatial_join` | ONE | FOREIGN | `{JOIN_TARGET_ID: "target", JOIN_SOURCE_ID: "join"}` |
| `spatial_join_all` | MANY | FOREIGN | same |
| `nearest_neighbor` | ONE | FOREIGN | `{NEAR_INPUT_ID: "input", NEAR_TARGET_ID: "near"}` |
| `all_neighbors` | MANY | FOREIGN | same |
| `explode_multipart`, `split_at_points` | MANY | MINT | `input` |
| `intersection`, `difference` | MANY | MINT | subject `input`, context `overlay` |
| `clip` | MANY | MINT | subject `input`, context `boundary` |
| `dissolve`, `aggregate`, `cluster_points`, `collapse_to_centerline` | GROUP | MINT | `input` |
| `union` | — | — | deleted (A5.4) |

`destination:` `ports/geometry_ops.py`, `ports/cartographic_ops.py`, `ports/table_ops.py`.

**A12.11a `map_fields` is `ONE + CARRY`.** One row, added to the table above:

| method | cardinality | ids | subject / context / refs |
|---|---|---|---|
| `map_fields` | ONE | CARRY | `input` |

Found by sweeping the port Protocols against A12.11 and A12.6 while writing B9: `map_fields` was
in neither. It **has an output parameter** (`ports/table_ops.py:156-163`), so A12.6's in-place
category does not cover it and A12.11 is its home. `ONE + CARRY` because it renames and drops
fields and does not touch row identity — the row count and the subject's ids are unchanged.

**This row is what makes `map_fields`' output lineage-bearing, which is what puts it inside B10's
scope.** The two together turn B9(d)'s silent drop into an error naming `map_fields`: the
declaration says the output carries the subject's ids, and the post-call assertion checks that it
does. Neither alone is enough — an undeclared method is outside the assertion's scope, and a
declaration with nothing checking it is a comment.

T4.1's CI check would have caught the omission independently, since it rejects an output parameter
with no declaration; recording it here means T4.2 does not discover it as a surprise.

**"The only method in neither" is a claim about today's Protocol, not a closed one.** T2.2 adds
`update_rows`, an **in-place mutator keyed on `lineage_id`** — A12.6's category, not this one.
Two separate things came out of looking at it.

**A port contract worth stating on its own terms: the key field may not appear in `fields`.**
`update_rows(input, key, fields, rows)` carries one value per field per row, so with `key ∈
fields` a row is matched on `row[key]` and then written back that same value — a guaranteed no-op.
The rule rejects a caller error, and it is about this signature rather than about re-keying in
general: `UPDATE … SET key = … FROM …` is well-defined, and a port method shaped to express it
would be a different method. No lineage knowledge is involved.

**It does not, however, cover the lineage exposure.** Keyed on `lineage_id`, `update_rows` cannot
rewrite `lineage_id` at all. The real exposure is `lineage_id` written **under a different key**,
or written by `calculate_field`, which has no key and no `fields`.

**An option for T2.8 to weigh when it settles A12.6's in-place-mutator definition — an option, not
a decision.** Have that definition declare **which parameter names the fields a mutator writes or
drops**: `fields` for `update_rows` and `delete_fields`, the target field for `calculate_field`.
The facade then rejects `lineage_id` appearing in that parameter, generically. This is a
per-method *declaration* read by generic logic — the same pattern as `subject=` and `refs=` — so
it does not hit B10's objection, which is to argument-parsing logic written per method inside the
facade. It complements B10 rather than replacing it: the post-call assertion remains the only
thing that sees tool-behaviour renames and type downcasts, neither of which any declaration can
predict.

Two smaller findings from the same sweep are task acceptance criteria rather than decisions, and
are recorded at **T4.1** (queries are outside the grammar, stated rather than implied) and **T4.2**
(A12.11's rows and the Protocol's methods must match in **both** directions — `nearest_neighbor`,
`all_neighbors`, `buffer_dissolve`, `extract_vertex` and `spatial_join_all` are declared here and
absent from the Protocol, being T2.9's splits).
`destination:` `ports/table_ops.py`, with A12.11.

**A12.12 Vertex extraction is `FOREIGN`, not `MINT`.**

> *Considered and rejected:* splitting into `extract_vertices` (measurement, FOREIGN) and
> `vertices_to_points` (vertices that become features, MINT). The intent argument is right — the
> pipeline does take lines to vertices, manipulate the points and rebuild geometry that reaches an
> output — but `MANY + MINT` mints on the vertex axis, which is the growth the design rejected
> elsewhere and which `partition_iterator.py` already sizes partitions to avoid. On a road network
> with roughly 10M vertices that is 10M ids and 10M edges to produce on the order of 10⁴ rebuilt
> features.
>
> The lineage path is not cut by `FOREIGN`: the vertex rows carry the parent's id in the declared
> ref column, so the domain reads it and passes it to the rebuild's `mint(parents=...)`, which
> records the edge that matters — *parent features → rebuilt line* — at the right granularity and
> roughly 500× smaller.
>
> If a case exists where extracted points are themselves published features, model it as extract
> (`FOREIGN`) → `write_rows` with explicit mint, which mints only the points that survive. A scan
> of 20+ `FeatureVerticesToPoints` call sites found no such case; every one is measurement or an
> intermediate feeding a rebuild.

`destination:` `ports/geometry_ops.py`.

## A13. Field handling in the lineage layer

- `lineage_id` created unconditionally on `MINT` outputs, never on `CARRY`. The declaration says
  which, so no "if not exists" check — the defensive idiom being deleted from
  `railways_generalization.py`.
- Verify `lineage_id` exists on **lineage-bearing** inputs (A15.6) before resolving. Missing means
  an earlier operation broke the chain; fail there rather than producing an empty map.
- **And verify every id belongs to this run** — see A25. Same scan, two assertions; do not pay for
  the read twice.
- Type is `FieldType.BIGINT` (A10.1, B1).
- Publish-time removal has the same gap as the work-key sweep (A9.6).

`destination:` lineage module docstring.

## A14. Adapter parents capability

> *Superseded 2026-09-17 by A14.1 below.* The tier list is kept as rationale. Two of its tool facts
> were wrong, and its runtime path was measured over budget and wrong on every split group
> (`temp/findings/n1_correspondence.md` §1, §3.8, §3.9, §7).

The fallback belongs in the adapter; the layer above asks for parents and does not care how they
are produced. Tiers in preference order:

1. **Native.** `PairwiseDissolve(out_lineage_table=...)` emits `OUTPUT_FID`/`INPUT_FID` — but that
   parameter is **new at Pro 3.7**, and the image is Pro 3.6 / Enterprise 12.0, so it is one
   release away rather than unavailable. `ORIG_FID` from `MultipartToSinglepart` / `Intersect`
   covers most `MANY + MINT` cases already; `array_agg` in PostGIS; `group_concat` in SpatiaLite.
2. **Synthesised via a work key.** Stamp a scoped key on the input, pass it through the backend's
   aggregation (`concatenation_separator`, unchanged since Pro 3.0), parse back. The CONCATENATE
   pattern, written once in the adapter rather than open-coded in `ramps.py`. **This is what runs
   until the image is rebuilt**, and it stays as the fallback afterwards.
3. **Reconstructed spatially.** Expensive and wrong at coincident boundaries. Prefer an
   unavailable method to a silently wrong one.
4. **Unsupported, declared.** The method raises on a lineage-bearing handle.

Capability is **probed at adapter construction** by `arcpy.GetParameterInfo("analysis.PairwiseDissolve")`,
not read from a version table, and **checked at plan time** against stage wiring: a stage that
dissolves on a lineage-bearing handle with an incapable adapter fails before fan-out, not in the
pod.

**This needs no exemption from the no-arcpy rule.** `02-runtime.md` §8 specifies `validate()` as
running with "no cluster, no credentials, no data, no ArcPy". The probe happens at adapter
construction, which already has arcpy; `validate()` receives the resulting **capability record as
an argument** — data, not a call. The rule stands unchanged. The conformance suite must pass under both tiers, since tier 2 runs first and tier 1 later
on the same code.

Esri's lineage table is slow on large inputs and requires single-part output, so an adapter may
prefer synthesis on size — an adapter-internal decision.
`destination:` `adapters/arcpy/` package docstring; `02-runtime.md` §8 (the plan-time check).

**A14.1 Adapter parents capability, restated.** *The layer above asks for parents and does not
care how they are produced.* That sentence of A14 stands; the rest is restated without the tier
vocabulary.

- **The capability record names methods, not mechanisms.** The adapter publishes, at construction,
  the set of methods declared `ids=MINT` for which it can honour `parents=` (A11.15). How it does
  so is adapter-internal and not in the record. `validate()` receives the record as data (A14's
  no-exemption argument stands) and fails a stage that uses a lineage-bearing handle with a `MINT`
  method the record does not name — subject to B14, which records that plan time cannot yet see
  which port methods an operation calls.
- **The native references engines provide, corrected.** `ORIG_FID` from `MultipartToSinglepart`
  and `SplitLineAtPoint`; `FID_<input>` from `Intersect`, not `ORIG_FID`; nothing from
  `PairwiseClip` and `PairwiseErase`, so `clip` and `difference` stamp a work key on a copy of the
  input; `OUTPUT_FID`/`INPUT_FID` tables from `AggregatePolygons`, `AggregatePoints` and
  `MergeDividedRoads` on the current image; `LeftLn_FID`/`RightLn_FID` from
  `CollapseDualLinesToCenterline`; `PairwiseDissolve`'s lineage table from Pro 3.7, single-part
  output only.
- **CONCATENATE is retired**, as a runtime path and as an oracle: 7,841 s added over one 10^6
  group, and the statistic is computed per dissolve key rather than per output part, so it names
  the wrong parents on every key that splits.
- **Unkeyed spatial reconstruction stays rejected.** Prefer an unavailable method to a silently
  wrong one. B17's keyed resolver is not that: it is handed only its own key's parts and the
  resolver rejects a cross-key pair.
- **An adapter that cannot honour `parents=` for a method raises** `ParentsUnavailableError` from
  `ports/errors.py` (T2.4); it never returns an empty table.

`destination:` `adapters/arcpy/` package docstring; `02-runtime.md` §8 (the plan-time check, with
B14's caveat).

## A15. Scope, cost, session lifetime

**A15.1 Mint always; scope only the boundary diff.** Minting is O(cardinality changes) and cheap
even on context data. The diff is O(rows in every Out) per operation and is the expensive one. So
scope affects one runtime mechanism and never appears in operation bodies.
`destination:` lineage module docstring.

**A15.2 A handle is `diff-tracked` if it reaches a `StageOutput`.** Derived from the stage
declaration and the operation wiring, never declared.

> *Renamed.* This property was "in scope", which collided with `ScratchScope` and left
> "scoped handle" ambiguous against `lineage-bearing` (A15.6). `diff-tracked` says exactly what
> follows from it: the boundary diff tracks this handle.

> *Superseded:* "descends from a PROCESSING `StageInput` **and** reaches a `StageOutput`." The
> `DISPLACEMENT` stage breaks it — `displacement_feature` is a `StageOutput` whose only ancestors
> are CONTEXT inputs (`roads_source`, `roads_generalized`), so `DISPLACEMENT_FEATURE` would get no
> lineage ids at all, and A13's input check would then fail whenever another pipeline read it. The
> cost the PROCESSING clause was buying lands on the In side, not on the diff, which is bounded by
> Out size either way.

`destination:` lineage module docstring; `02-runtime.md` §8.

**A15.3 The id map is disk-backed by default, with a fixed in-memory budget.**

Packed `int64` arrays on pod-local disk, a fixed-size block cache, and **a peak memory figure —
as the cgroup accounts it — that we declare as a constant rather than as a function of the
handle**. The same code path at 70K rows and at 280M.

> *Superseded (the metric).* This entry and the paragraphs below originally named the bounded
> property as the process's resident set size. That is the wrong accounting for the failure this
> entry exists to prevent: Kubernetes evicts and OOM-kills against the pod's **cgroup** memory
> limit, and the cgroup charges file page cache — which reading a disk-backed map generates —
> that resident set size does not report. A map flat by resident set size could still be killed.
> Changed when T0.6 fixed its measurement to the cgroup figure; the asserted property now names
> the same thing T0.6 measures.

> *Superseded.* This entry specified an in-memory dict, pod-scoped, with structural invalidation
> and a row-count guard — a *cached-then-spilled-under-pressure* design. The mechanism below keeps
> the invalidation and the count guard; what changes is that the map never lives in an unbounded
> dict in the first place.

**Why a sizing answer was rejected.** Any O(rows) scheme has an input that breaks it, and the
input we have not seen is the 45,000 km² basin. A job failing on memory unexpectedly is
unacceptable, and an **OOMKill is the worst case against our first priority**: no traceback,
appears in production and not in development, not reproducible on a smaller dataset. Priorities
here are diagnosis speed, then data quality, then runtime durability, with raw speed below all
three — so trading time for a bounded, diagnosable failure mode is the correct direction, and
spill-and-reload under a minute is a non-issue.

**This is a deliberate trade, recorded so it is not optimised back.** A future reader will see a
disk-backed map where a dict would be faster on every input they have to hand. The dict is not an
optimisation of this design; it is a different design with an unbounded worst case, and it was
**rejected on that ground rather than on measurement** — so a benchmark showing the dict faster on
a 70K handle is not an argument against this entry.

**The budget is a declared constant: provisionally 64 MB, owned by T0.6.** Without a number the
bounded-memory property is asserted rather than established, and the first implementer picks one
with no basis. T0.6 produces it alongside the build-time curve, and must measure
**peak memory as the cgroup accounts it** and **the block-cache size at which lookup starts
thrashing on a large map** — the second is what
decides whether the packed path is viable at all, and nothing else in the plan would catch it.

**A small budget is achievable by construction, not by luck.** Sort the map by the lookup key and
read the subject in the same order, and lookups are sequential, so a handful of blocks suffices at
any map size. A random access pattern would need a cache proportional to the map, and "peak memory
is a constant" would quietly become false. The ordering is part of the mechanism, not an optimisation
of it.

**That ordering constrains the facade's read loop, not only the map's layout.** A map sorted at
build time is still defeated by a consumer that reads the subject in a different order. Whoever
implements parents resolution has to honour it, and the map and the loop will not necessarily be
written by the same person at the same time — so this is a code-review point, and it belongs in
the docstring of both.

**On ArcPy the preferred form has no Python-side map at all.** The translation can be a
`join_field` against a temp table rather than a Python lookup, in which case the memory is the GP
tool's and bounded by it — better than managing a budget. Prefer it where the adapter can express it.

> **Capability check.** The facade can build this today in principle — materialize the map with
> `write_table`, then `join_field(input=subject, key=<native index>, join=<map>, join_key=…)`, and
> the key is unique so B4's fan-out concern does not apply. But it rests on a contract **A9.2 does
> not currently make**: A9.2 exposes the native index as an *accessor*, and this path needs it
> *addressable as a join key*. True for `OBJECTID` in a file gdb; not guaranteed for a backend
> whose row index is not a column. T3.1 must extend the contract to say which.

**Both paths are permanent, and the packed form is not a contingency.** Whether `join_field` is
available is a **backend property**, so a backend without an addressable row index gets the packed
form forever — it needs building and testing regardless of how T3.1 resolves for arcpy. Read as
dead code once file-gdb works, it will rot and then fail on the first adapter that needs it.

**Consequence for pod sizing:** lineage overhead becomes a declared constant rather than a function
of row count, so it does not enter partition sizing at all. Sizing stays purely about the GP tools'
own memory.

**Retained from the superseded entry:** `ScratchHandle` is a frozen dataclass with `path` set
`compare=False`, so it hashes and a materialized copy equals its declaration — the stage entry
point already relies on this to build `{declared: materialized}`. Invalidate on any call naming
the handle as an output; in-place mutators do not invalidate, since row identity is unchanged. A
**row-count** check per operation is the independent guard.

> *Considered and rejected:* full id-set validation per operation. It reads every id, which is the
> same scan as rebuilding the map, so it saves the construction and not the I/O — 30–50%, not 90%.
> Structural invalidation is sufficient because every id change goes through a port call that
> names the handle as an output, and the facade sees all of them.

`destination:` lineage module docstring.

**A15.3a Lineage overhead must never cap a domain parameter.**

Where a tuning value drives volume — a search distance, a buffer tolerance, a cluster radius — the
ceiling on that value is a cartographic judgment. **If lineage machinery lowers it, lineage is
setting the data quality ceiling**, which the priority order in A15.3 does not permit: data quality
outranks runtime durability and raw speed both.

Worked case, and the reason this is written down: river gap-connection candidate count scales with
the square of the search distance, and the domain already caps that distance for its own reasons.
That cap must stay as high as the domain wants it. Rivers are the evidence; the rule is general,
and someone widening a buffer tolerance later should find it here.

This is what the disk-backed map buys beyond diagnosability — volume stops being a lineage concern
at all. It is also why A11.4a's argument is semantic rather than sized: the candidates are never
minted, so they never enter a map however many there are.
`destination:` `02-runtime.md` §2.7, beside tuning, as a constraint on what tuning may be limited
by.

**A15.4** `LineageSession` is pod-local. The provisional edge buffer is per-operation; the id-map
cache is pod-scoped. Nothing crosses the pod boundary except written artifacts. Cross-pod
information comes from stable artifacts only: the ingest map, the dispatch registry, the fan-out
ownership assignment.

The rule is "derived from stable artifacts," **not** "deterministic" — mint order follows tool row
iteration order and is not stable, which is why retries rely on wholesale replacement (A10.4).
Where determinism does hold — ownership assignment is a pure function of data and partition
geometry — spend it on verification: recompute at fan-in and assert it matches what fan-out wrote.
`destination:` lineage module docstring; `02-runtime.md` §7.

**A15.5** Log volume is proportional to change **except for aggregating collapses, which are
proportional to input**. `build_displacement_feature` is the pathological case: buffer every road,
merge, dissolve into one blob, producing a single edge whose `from_ids` is every road in the
partition.

> *Superseded:* "cost is proportional to change, not row count," stated without the exception.

`destination:` new ADR on lineage.

**A15.6** Two properties, deliberately two words. A handle is **`diff-tracked`** if it reaches a
`StageOutput` (A15.2). A handle is **`lineage-bearing`** if its declaration chain terminates in
`CARRY` or `MINT`. A `FOREIGN`-terminal handle can be `diff-tracked` without being
`lineage-bearing` — `SNAP_DISPLACEMENT` is exactly that, and it is legal.

Consequences: the boundary diff skips non-bearing handles, since there are no ids to diff;
completeness ignores them; and A13's input verification applies to **`lineage-bearing`** inputs
only.

Recorded separately because one word doing two jobs is what produced the `DISPLACEMENT_FEATURE`
bug that killed the PROCESSING clause (A15.2).
`destination:` lineage module docstring; `01-terminology.md`.

**A15.7 Time budgets for lineage overhead.** Measured as **time added over the bare tool** on the
same input in the same process, never as total tool time:

| where | budget |
|---|---|
| a commonly used GP tool (dissolve, buffer, intersect, …) | **under 1 minute** added |
| fan-out, fan-in | **under 5 minutes**, never over 15 |

Judged at A15.5's worst-case sizes. Guidelines, not assertions, and they rank below diagnosis
speed, data quality and durability (A15.3); a mechanism that is correct but takes an hour does not
pass. Stated by the user on 2026-09-15; until this entry they existed only in conversation, and
every judgment in `temp/findings/n1_correspondence.md` cites them.
`destination:` `02-runtime.md` §8, beside the validation vocabulary; the lineage module docstring.

## A16. Completeness assertions

Per stage, at fan-in, across **all objects in that stage** — edges cross objects, as when a lake
polygon is consumed into a river feature.

```
I  = lineage ids in the stage's PROCESSING StageInputs, own features only
O  = lineage ids in the stage's StageOutputs
T  = { f ∈ from_ids of any edge : f ∉ O }
D  = ⋃ from_ids over promoted DROPPED edges

(1)  I − O − T − D          == ∅     nothing vanished unaccounted
(2)  O − I − ⋃to_ids(edges) == ∅     nothing appeared unaccounted
(3)  T ∩ D                  == ∅     nothing both consumed and dropped
```

**`I` is PROCESSING-only.** Completeness asks whether the stage lost something it was
*responsible for*, and a stage is not responsible for reference data. Note this is a different
question from A15.2's `diff-tracked`, which deliberately dropped its PROCESSING clause — that
property decides whether a handle gets ids at all; this one decides what must be accounted for.

Verified against the `DISPLACEMENT` stage rather than reasoned about. `buildings` (PROCESSING)
flows through `simplify_polygons` and `propagate_displacement`, both `ONE + CARRY`, so every
building id reaches `O` via `displaced` — (1) holds. `displacement_feature` ids are minted by
`build_displacement_feature`'s dissolve, so they are in `to_ids` — (2) holds. Context road ids
land in `T` via `from_ids` without ever entering `I`, and are not in `D` because the boundary diff
does not call a row dropped when it appears in an emitted edge's `from_ids` — (3) holds.

`PARENTS_KEPT` contributes nothing to completeness by construction, since its parents are in `O` and
therefore excluded from `T`. `CREATED` contributes nothing because its `from_ids` is empty.

**A16.1** Promotion applies to `DROPPED` only:

```
D = { d ∈ ⋃_jobs D_job : owner(root(d)) == job(d) }
```

`root(d)` resolves back through that job's own log to a raw id; `owner` is the fan-out assignment.
`PARENTS_CONSUMED` and `PARENTS_KEPT` need no ownership check — the resulting id's presence in the job's
declared output already witnesses it, because the partition machinery filtered outputs to owned
features. **This is why the record format must not carry an own/context flag: the writer cannot
know it.** It also removes the deduplication problem — a feature dropped as context in job x and
kept as own in job z produces one record in the stage log, from z's output, and x's record is
simply not promoted.

**A16.2** A **stage-exit sweep** is needed in addition to the per-operation sweep, emitting
`DROPPED` for ids terminating in handles that no `StageOutput` names. `simplify`'s
`collapsed_points` is the case: a collapsed feature is `PARENTS_CONSUMED` at the operation boundary
because `collapsed_points` is a real Out, but `ConflictResolution.collapsed_points` is never a
`StageOutput`, so without this the id is in none of `O`, `T`, `D`.

**A16.3** This assertion can only run in fan-in, with data — outside the "nothing that can fail at
plan may be deferred to the pod" layering that every other check in the family obeys. State that
explicitly or someone will try to move it.

**A16.4 Origin-closure check:** every `from_id` in an edge should belong to an object in the
output's `origin` closure. Too-wide origin is safe; too-narrow is a legality bug, since legality
is computed from it.

`destination:` `02-runtime.md` §8 (the validation vocabulary), for all of A16.

## A17. Defects found in the template

**A17.1** `DISPLACEMENT_FEATURE = Derived("displacement_feature", origin=(NVDB_ROADS,))`
(`pipelines/building/n100_objects.py:55`), but `build_displacement_feature` also consumes
`roads_generalized`, which is `N100_ROAD`. The origin is factually incomplete. Legality is safe —
`NVDB_ROADS` is already the strictest term — but A16.4 would flag it on the first run.

**A17.2** `resolve_ramps` is **inverted**, not merely simplified. It selects `is_ramp = 1`,
collapses, and writes only that to `output_lines`, so every non-ramp road vanishes — and since
`ramp_lines → snap_to_source_geometry → snapped → StageOutput(THINNED_ROADS)`, the stage's road
output is ramps only. The real `generalization/n100/road/ramps.py:56-61` does the opposite:
`delete_ramps` removes ramps from the copy, then copies **all remaining roads** to the output and
appends `new_lines`. Fix: select `is_ramp = 0` as the base, merge the reinstated and collapsed ramp
geometry into it.

**A17.3** Two invented parameters appeared in the design sketch and are **not** in the port:
`select` has no `residual` and `snap` has no `displacement` (`_vertex_deltas` computes displacement
separately). Since `DROPPED` comes from the boundary diff, `residual` is not needed for lineage and
has no caller. Recorded so neither is added by mistake.

**A17.4** `Attr` subqueries against a `ScratchHandle` at `operations/road/__init__.py:678` and
`:942` — no adapter can compile them.

**A17.5** The two `ranks` joins are broken **and** deleting them alone loses data.

`thin_road_network:663` and `finalize_road_attributes:932` both join `ROAD_RANKS` on the feature
id. `thin_road_network:648` dissolves on `(ROAD_CLASS,)` only, so `RANK` is not a dissolve field
and the dissolve drops it — the join exists to restore it, and restores it keyed on an id the
dissolve just re-minted, so it restores nothing.

The defect is upstream: **`dissolve` has no way to carry a non-key attribute through a collapse.**
arcpy has `statistics_fields`; the port has nothing, so A9.10's combining-rule requirement is not
expressible today.

Fix in three parts: add a `statistics` parameter to `dissolve`; delete both `join_field(...
join=ranks ...)` calls; delete the `Network.ranks` and `ConflictResolution.ranks` handles and their
`StageInput`s. `ROAD_RANKS` may remain a `StageOutput` as a diagnostic, but nothing reads it back
by id.

> *Superseded:* an earlier reading called the joins "redundant, just delete them," on the
> assumption that `RANK` travels as an attribute. It does not survive the dissolve.

**A17.6** Removing the `ROAD_RANKS` consumers removes a non-adjacent stage dependency (SELECTION →
CONFLICT_RESOLUTION, skipping NETWORK). **This is a decision, not a side effect, and it does not
deprecate non-adjacent edges.** `derive_stage_dependencies` still computes them and the model
still permits them: a dependency is between objects, not between adjacent stages.

What the template was teaching is the **id-keyed** version, which the ID model forbids — the edge
required per-feature data to survive two stages unchanged, and re-minting makes that impossible.
The legitimate form is A9.10's: a non-adjacent lookup joined on a **domain key**.

**The road pipeline has no natural instance.** `ROAD_RANKS` carried a per-feature value, which no
domain key can key, which is exactly why it must be an attribute. The consumers are deleted rather
than replaced, and this entry records that the omission is deliberate.

**The lesson is preserved in the building pipeline**, which already demonstrates the legitimate
pattern: `MUNICIPALITY_CODES` is a non-spatial `ExternalSource` wired as a CONTEXT `StageInput`
(`pipelines/building/n100_stages.py:78`) and consumed by `data_selection` on the domain key
`byggtyp_nbr`. Replicated whole to every pod, joined on a value the data determines, immune to
re-minting.

**A17.7** That exemplar is currently written as
`Attr("byggtyp_nbr in (select code from codes)")` — one of A17.4's uncompilable subqueries. Under
structured `Attr` it becomes `Attr.in_(BUILDING_TYPE, codes)` with the small lookup read via
`read_rows` first. The one place demonstrating the good pattern needs the same fix as the two
demonstrating the bad one.

`destination:` for all of A17 — the fixes themselves, in `template_code/`. These entries retire
when the code is corrected; they are not documentation.

## A18. Multipart

Single-part is a **debug-mode assertion, not a port invariant**. arcpy `Describe` gives
`shapeType` ("Polyline"), never part count; `isMultipart` and `partCount` are *geometry*
properties, and all repo uses (4 and 7 respectively) are inside cursors. An unconditional
invariant costs a per-row scan at every output boundary.

If a multipart dissolve is ever needed it becomes a separate `dissolve_multipart` method, which
keeps `@row_shape` static.
`destination:` `ports/geometry_ops.py`.

> *Amended 2026-09-17 (B18, option b).* `dissolve` is **single-part by contract** and
> `DissolveOption` leaves the port; A5.6's "does not move the cell" clause is superseded. One output
> row per connected single part of each key — on lines that is a split at every junction
> (`temp/findings/n1_correspondence.md` §3.9), so a group is not a connected component. A multipart dissolve
> becomes `dissolve_multipart` when a caller appears. Real call sites that pass `MULTI_PART` or
> `UNSPLIT_LINES` today, for T2.9 and `04-migration.md`: `MULTI_PART` at
> `generalization/n100/river/mst_loop.py:500`, `generalization/n100/land_use/rullebane.py:400`,
> `generalization/n10/landForms/hoydetall.py:793`, `custom_tools/general_tools/geometry_tools.py:48`,
> and `generalization/n100/road/testing_file.py:463` (a test file); `UNSPLIT_LINES` at
> `generalization/n100/river/preparing_river_network.py:48`,
> `generalization/n10/facilities/railways_generalization.py:406`,
> `generalization/n100/land_use/rullebane.py:128`; plus four `UnsplitLine` tool calls
> (`extend_river_line.py:207`, `:224`, `unconnected_river_geometry.py:80`,
> `clean_elveg_and_sti.py:625`). Unsplit is not a dissolve option: it is a merge at pseudonodes,
> `GROUP + MINT`, and `PairwiseDissolve` has no such option, so it becomes its own method when a
> caller is migrated.

## A19. Published identity

Deferred, and it **cannot be `lineage_id`** — it needs cross-run stability and `lineage_id`
re-mints on every dissolve.

The cheap insurance now is a naming decision: `_apply_product_schema` maps `FEATURE_ID → "objid"`,
and shipping that binds consumers to an identity that is not stable. Rename or drop it.

The hard core is feature matching, not id assignment: derivable for 1:1 lineage to a stable source
(NVDB ids are stable), not for generated features.
`destination:` TBD — no ADR exists and the design is not settled. See B3.

## A20. Query contract

Forward walks **branch**. A road consumed by `build_displacement_feature` in the building pipeline
gets a forward edge there *and* continues in the road pipeline, so "where did road 17 go"
legitimately returns a set. The query API contract must say so.

Storage format is chosen for the resolver, not for readability — the query is an API over edges,
not a text search over log files. No materialised ancestry: ancestry sets compound without bound
through repeated dissolves.
`destination:` TBD — the lineage query module does not exist yet. `ag/lineage/query.py` when it
does.

## A21. Cross-run lineage: a retention policy, not a non-goal

> *Superseded.* This entry read "Out of scope. Minter ids are run-scoped and two runs both use
> minter 7." That was written believing cross-run inputs were an edge case. They are the normal
> mode: the scale ladder is RAW → N10 → N25 → N50 → N100, and an N100 run reading an archived
> national N50 product is the ordinary case, not a corner. A21 cannot be a non-goal because A23
> depends on it.

**Retention.** A published product's **edge log and ingest map are archived alongside the
product, for as long as the product is readable.** They are part of the product, not run
scratch. Deleting them does not corrupt anything — it truncates history, which is why the
degradation below must be explicit rather than silent.

**Degradation is named, never inferred.** The walk terminates with a stated boundary, and the
statement comes from the ingest map's `boundary_kind` column (A24.1) — never from the shape of an
id or from a null:

```
traced to RAW feature 44120                                          complete
traced to N50 feature 8814402, prior history unavailable             truncated — LOST_HISTORY
traced to N50 feature 8814402, prior run log not retained            truncated — retention gap
```

A positive id from a re-allocation boundary is indistinguishable from a raw ingest id by
inspection — both are dense positives from our own allocator — and `incoming_lineage_id = null`
covers both `RAW` and `LOST_HISTORY`. Neither the id nor the null is sufficient, which is why
A24.1 carries a fourth column rather than leaving the resolver to infer.

`destination:` new ADR on lineage id allocation; retention rules also into `02-runtime.md` §4.1
alongside the storage scopes.

## A22. Cold start is a requirement

**A job for one scale must be runnable without first re-running every prior scale in the same
run.** Reading an archived N50 product to produce N100 is the normal mode.

Recorded because the whole design has assumed it without stating it, and two decisions turn on
it: A21 could not stay a non-goal, and A24's re-allocation exists to make a cold start
indistinguishable from any other ingest.

The mechanical consequence: **a cold start is just an ingest where the incoming id column is
empty.** No separate code path, no mode flag.
`destination:` `02-runtime.md` §6.1, beside run selection and closure.

## A23. Traceability to source is a requirement

**From a job's output it must be possible to find which original source data a feature came
from.** Also assumed throughout and never stated.

It splits in two, and only one half was ever covered:

| question | answerable from |
|---|---|
| "which N50 feature did this N100 feature come from" | this run's edge log alone |
| "which RAW feature did this ultimately come from" | every intermediate run's edge log **and** each boundary's ingest map |

**No id scheme avoids the second.** Global uniqueness removes a mapping hop; it does not remove
the need for the prior run's edges, because an id without its history is just a name. This is the
argument that kills "make ids globally unique instead of re-allocating" — it buys a hop and not
resolvability.

`destination:` new ADR on lineage; the second row also into `ag/lineage/query.py` as the
resolver's contract.

## A24. Cross-run inputs are re-allocated at ingest

Resolves B7.

**Cross-run inputs arrive in at least four states**, and this is the primary argument:

| state | incoming ids | incoming edges |
|---|---|---|
| produced by a previous run | yes, from an unknown minter space | yes, if retained |
| produced before the lineage system existed | none | none |
| produced by a run whose log was purged | yes | no |
| from a third party | none | none |

**Global uniqueness has nothing to be unique about in states 2 and 4.** Any scheme that relies on
incoming ids being globally distinct has no defined behaviour for half the cases. Re-allocation
handles all four identically: allocate fresh, record what is known. A cold start (A22) is state 2
or 4 and needs no special path.

The collision that prompted this is real but secondary: `minter_id` is run-scoped (A10.2), so run
X's `g(7,5)` and run Y's `g(7,5)` are different features with the same value, and reading X's
product into Y puts both in one id space.

**The layout does not change.** 20-bit minter, 32-bit counter, no run field, no TEXT ids. B1's
TEXT fallback is a degraded option we would be paying to buy global uniqueness that A23 shows does
not deliver resolvability anyway.
`destination:` new ADR on lineage id allocation.

**A24.1 The ingest map records the incoming id, and copying is a three-way rule.**

A10.6 specified the map as `native_index → lineage_id` because it was written for
`ExternalSource`, which has no incoming id. For a cross-run input it must record four columns:

```
(native_index, incoming_lineage_id, new_lineage_id, boundary_kind)
```

`boundary_kind ∈ {RAW, CROSS_RUN, LOST_HISTORY}`.

**The fourth column is not redundant with `incoming_lineage_id` being null**, and A21 fails
without it. A true `ExternalSource` and a legacy N50 product whose ids were never allocated
*both* arrive with `incoming_lineage_id = null`, and they must terminate a walk differently:

| `boundary_kind` | incoming id | the walk reports |
|---|---|---|
| `RAW` | null | `traced to RAW feature X` — **complete** |
| `CROSS_RUN` | present | continue into the prior run's log via `incoming_lineage_id` |
| `LOST_HISTORY` | null | `traced to N50 feature X, prior history unavailable` — **truncated** |

Reporting a truncation as a complete trace is exactly the silent degradation A21 forbids, and
nullability cannot distinguish the two.

**The column records what ingest knew.** A `CROSS_RUN` boundary whose prior log turns out to have
been purged also degrades to truncated, but that is discovered at *walk* time rather than ingest
time, and carries a different message (`prior run log not retained` rather than
`prior history unavailable`). The resolver handles both; only the second is knowable at ingest.

That one extra column makes the chain **alternate cleanly**: N:M edges inside a run, a **1:1 map
at each boundary**. The boundary hop is always 1:1 because ingest allocates exactly one new id per
incoming feature — no cardinality change happens at a boundary, by construction. Without the
column the resolver cannot cross a boundary at all and A23's second question is unanswerable.

Copying then depends on whether a stable incoming id exists, not on the object's declared type:

| input | stable incoming id | ingest does |
|---|---|---|
| `ExternalSource` | no | **copy**, rewriting ids — A10.6's coupling argument applies |
| `Derived` / `ProductIdentity` **with** `lineage_id` | yes | **map only**; fan-out applies it by joining on `incoming_lineage_id` |
| `Derived` / `ProductIdentity` **without** `lineage_id` (legacy, purged, third-party) | no | **copy** — same as `ExternalSource` |

Row three is A22's cold start, and it needs no separate path: the incoming id column is empty, so
the rule routes it to the copy branch on its own.

**This does not break A6.6.** Fan-out *applies* a map ingest already produced; it allocates
nothing. Add that clarification to A6.6 rather than treating the join as an exception.
`destination:` new ADR on lineage id allocation; `02-runtime.md` §6.

## A25. The foreign-id guard

**Every `lineage_id` in a lineage-bearing input must fall within this run's allocated ranges.**

```
id > 0   →  inside one of the ingest ranges recorded in this run's ingest artifact
id < 0   →  minter_id(id) is present in this run's dispatch registry
```

**Why it became load-bearing.** Under copy-everything ingest, the copy was already correct before
any stage ran — a foreign id was not representable. Under A24.1's map-only branch, correctness is
established by **fan-out applying the join**. If fan-out misses it, the dataset carries the prior
run's ids and B7 is back, silently, in exactly the form A24 exists to prevent. This guard was
belt-and-braces when it was first raised; with map-only it is **the only detector for a missed
join**.

**A25.1 The range check alone is close to blind for the failure A25 exists to catch.**

Under map-only ingest, a row fan-out failed to join keeps the *prior run's* id. Ask A25 whether
that id is in range:

- a stranded `g(7,5)` — `minter_id` is dense from 1 in every run (A10.2), so minter 7 is in this
  run's dispatch registry as soon as the run has a few jobs. **Passes.**
- a stranded raw id — raw ids are dense positives from 1 in every run (A10.7), so it sits inside a
  legitimate ingest range. **Passes.**

The range check fires only by numeric luck. It is still worth keeping — it catches ids from
nowhere at all, such as a hand-edited dataset or a field carried in from outside the system — but
it is not the detector for a missed join.

**The exact check is membership in the map.** For an input that came through a **map-only**
boundary, the post-join dataset's `lineage_id` column must equal that map's `new_lineage_id`
column **as a multiset**. Any unjoined row fails regardless of what its stranded id looks like.

Multiset, not subset: a run X raw id and a run Y `new_lineage_id` are both dense positives, so a
stranded `42` can coincide with another row's legitimately allocated `42` in the same map and
survive a membership test. Under multiset equality it cannot — the correct new id is absent *and*
`42` appears twice, so the comparison fails on multiplicity even where it survives on membership.
This is the same technique A7.2 uses for the partition shadow comparison, for the same reason.

Cost is unchanged: one grouped count on each side, not a per-row loop. The map is already open,
because fan-out has just used it.

**It runs where a stage would notice**, not only at fan-in:

- **Stage entry**, over each lineage-bearing `StageInput`, folded into A13's existing
  existence check so the input is read once and asserted twice. This is the earliest point a
  foreign id is observable and the pod that fails names the input.
- **Fan-in**, as defence in depth, where the merged logs and the dispatch registry are both
  already open.

**Cost is one grouped scan, not a per-row loop.** Both halves are aggregates: extract `minter_id`
arithmetically from negative ids and compare the *distinct* set against the registry; bucket
positive ids against the ingest ranges. A per-row check is not needed and a min/max hull check is
not sufficient — ingest ranges are disjoint intervals, so a foreign id can sit inside the hull
while belonging to no range.

`destination:` `02-runtime.md` §8; the lineage module docstring for the stage-entry half.

## A26. Python target

*Decided 2026-09-21.* The target is **Python 3.13**. There is no fixed lower constraint: the
project follows its runtimes upward, and the target is the lowest Python minor version across
the supported runtimes (the ArcGIS Pro interpreter the team develops with, and the Linux image).
Nothing is in production yet, so no older build constrains it. Three settings in
`pyproject.toml` state it and always change together: `requires-python`, pyright's
`pythonVersion` and Black's `target-version`. CI runs the pure-core suite on that version. The
floor is raised only when every supported runtime has moved, in one pull request that changes
the three settings and runs pyright and the core suite.
`destination:` `docs/contributing/python-version.md`; `pyproject.toml`.

> *Landed 2026-09-22 (slice 0)* in `docs/contributing/python-version.md` and `pyproject.toml`,
> with one amendment: the target is stated in **four** places, not three, because
> `.python-version` pins the interpreter uv creates the environment with, locally and in CI
> (A27); and the formatter setting is
> ruff's `target-version` (ruff format replaced Black for the new code in slice 0), with Black
> inferring its target from `requires-python` for the legacy packages. The text above stays as
> decided; the page is now the authority.
>
> *2026-10-02:* Black retired altogether (A28); ruff's `target-version` is the formatter
> setting for the whole repository.

## A27. Environment and tool management: uv

*Decided 2026-09-30.* **uv manages the project environment and the tools.** `uv.lock` is
committed and written only by uv: `uv sync --extra dev` creates `.venv` from it, `uv lock`
regenerates it when a pin in `pyproject.toml` changes, and nobody edits it by hand. The
pre-commit hooks and CI run every tool through `uv run --locked --extra dev <tool>`, so a
check runs the pinned version whatever a machine has on `PATH` and whether or not an
environment is activated; `--locked` fails when the lock file is behind `pyproject.toml`.
`.python-version` pins the interpreter uv uses, and is one of the four places the Python
target is stated (A26). Dependencies stay in the standard `pyproject.toml` tables
(`[project]`, `[project.optional-dependencies]`); uv-specific extensions such as
`[tool.uv.sources]` and workspaces are not used, so `pip install -e ".[dev]"` remains a
working fallback. If uv is ever replaced, the work is regenerating the lock file in the new
tool's format and changing the hook invocations and the CI step; the dependency declarations
do not change. The alternative, hooks that run whatever tool `PATH` resolves, was rejected:
`language: system` cannot enforce a version by design, and a check that passes using an
unpinned tool is not the check that was configured.
`destination:` `docs/contributing/toolchain.md`; `pyproject.toml`; `.pre-commit-config.yaml`.

> *Landed 2026-09-30 (slice 0)* in `docs/contributing/toolchain.md`, `.pre-commit-config.yaml`,
> `.github/workflows/checks.yml`, `.python-version` and `uv.lock`. The page is the authority.

## A28. One formatter, and lint on the legacy packages

*Decided 2026-10-02.* **Ruff is the only formatter, over the whole repository; Black is
retired.** Slice 0 had kept Black over the legacy packages so that their formatting stayed
untouched until migration. That split cannot be expressed in an editor (VS Code binds one
formatter per language, not per directory), so format-on-save could reach only one scope, and
the legacy code, which keeps receiving work for months, would have been formatted by hand or
not at all. Measured first: ruff's formatter changes 35 of the legacy files relative to Black,
and the syntax tree of every file is identical before and after, so the cost was one
whitespace-only commit, recorded in `.git-blame-ignore-revs`.

**Lint runs on the legacy packages too.** After Black left, legacy code had no check in CI at
all (pyright, pytest, the import contracts and the scans all cover `src/ag`, `tests/` and
`tools/` only). Ruff lints it with `F`, `E9`, `I` and `SLF001`, with two rules held back under
the legacy directories by root-anchored `per-file-ignores`: `F401` and `I001`, whose autofixes
remove or reorder imports, against the legacy convention of side-effect imports. The findings
present when linting was switched on form a per-file baseline in `pyproject.toml`, one entry
per file with the rules it fails; each entry is a tracked task, removed when the file is
cleaned, the undefined-name (`F821`) files first because those are latent `NameError`s. The
alternative, excluding the legacy packages from lint, was rejected: it would have left the
code that is still changing with the weakest check in the repository. The exclusion patterns
are root-anchored because a bare name (`"generalization"`) matches that name anywhere in the
tree, which had silently excluded `src/ag/generalization/` from formatting and linting.
`destination:` `docs/contributing/toolchain.md`; `pyproject.toml`.

> *Landed 2026-10-02* in `pyproject.toml`, `.pre-commit-config.yaml`, `tools/format.sh`,
> `.vscode/`, `.git-blame-ignore-revs` and `docs/contributing/toolchain.md`. The page is the
> authority.

---

# B. Open

These are **not settled**. Nothing below should be treated as a decision.

**B1. 64-bit storage capability.** The port must declare a field type meaning 64-bit integer,
distinct from LONG, and the ArcPy / file-gdb adapter must actually deliver it. Python ints are
arbitrary-precision, so an oversized value fails or coerces at the write boundary — which batching
puts further from the domain code that produced it. If file gdb cannot hold it, the fallback is a
text field (works everywhere, slower joins) or two LONG columns (int performance, compound
predicates), and **either changes the declared field type at every call site that stores a lineage
id** — a domain-visible schema change, not an adapter swap. Must be settled before adapter one.
Resolved by T0.1.

**B2. Q-C — `GraphOps` dataset-awareness.** Formally open pending the strahler code
(`ports/graph_ops.py:5`). Deferring is cheap: only `_build_topology` changes, no operation
signature does.

**B3. Published identity.** See A19.

**B4. `join_field` fan-out.** A non-unique join key changes row count with no output parameter to
declare. Needs either a declaration mechanism for in-place mutators, or a contract that
`join_field` requires a unique join key — checkable, and probably correct.

**B5. Ring representation.** Whether `Ring` needs a denser form than
`tuple[tuple[float, float], ...]` for the basin-scale cases. Measure before deciding; the alias is
the documented widening point.

**B6. Parents out-param beyond `dissolve`.** `aggregate`, `collapse_to_point`, `cluster_points`
and `collapse_to_centerline` have no caller wanting the parent set. Fix the signature shape now,
add the parameter when a caller appears.

> *Narrowed 2026-09-17 by A11.15.* Every `MINT` method carries the parameter; B6 now asks only
> which methods have a **domain** caller wanting the set.

**B7 — RESOLVED into A24, A24.1, A21, A22 and A23.** Kept here for the record because the framing
below was wrong in a way worth remembering: it treated cross-run inputs as an edge case. They are
the normal mode — RAW → N10 → N25 → N50 → N100 means an N100 run reading an archived national N50
product is the ordinary path. The collision described below is real but turned out to be the
*secondary* argument; the primary one is that incoming ids are absent entirely in two of the four
cross-run states, so global uniqueness has nothing to be unique about. Original text:

**A `lineage_id` read from a previous run can collide with one minted in this run.**

Found while verifying A16's `I` against the `DISPLACEMENT` stage.
`pipelines/building/n100_stages.py:158` states it plainly:

> Within a run it pins to that stage's output; **outside one, to the archived version at the
> location declared in `products.py`.**

So a `Derived` or `ProductIdentity` `StageInput` may come from a **previous run**, carrying
`lineage_id`s minted in that run's `minter_id` space. A10.2's uniqueness argument holds only
*within* a run, and A21 explicitly makes minter ids run-scoped — two runs both use minter 7. Run X
mints `g(7,5)`; run Y mints `g(7,5)`; if run Y reads run X's `N100_ROAD` as context, both values
exist in run Y's id space naming different features.

Consequences if unaddressed: a forward walk merges two unrelated lineages; the mint-generation
join check (T4.12) sees one generation where there are two; and assertion (2)'s `to_ids` can
collide with a context input's ids.

A10.6's ingest re-allocates for `ExternalSource` only, on the assumption that `Derived` inputs
"already carry ids" — that is the assumption that breaks. They carry ids from *another* run.

Not resolved. The shape of the answer is one of: route cross-run `Derived` inputs through
ingest-style re-allocation; put the run id in the log rather than the id bits, plus a rule that
cross-run ids are never minted against; or make `minter_id` globally unique rather than
run-scoped. Each has a different cost and none is chosen here.

**B8 — RESOLVED 2026-09-22 by T7.2 (slice 0).** Renamed in `template_code/` and in
`01-terminology.md` and `02-runtime.md` §2.2; every lift now carries `OriginRoot` and
`origin_roots()`. The item as written: `LineageRoot` → `OriginRoot` is a code rename, not a doc
change. The ruling is settled; the work is not scoped. `LineageRoot` is a `TypeAlias` at `core/data_objects.py:147` with uses in
`locations.py`, `policy.py` and `validation.py`, plus a `lineage_roots()` function that presumably
becomes `origin_roots()`. Aligning it with `Derived.origin` removes the object-level/feature-level
"lineage" ambiguity, but it touches existing code rather than only the new design. Needs a task.

**B9. Which artifacts carry `lineage_id` across a run boundary?**

**Two hops, answerable separately.** Naming them first, because conflating them is what makes this
look binary when it is not:

| hop | from → to | what a missing key costs |
|---|---|---|
| **1. cross-run ingest** | archived product → the next run that reads it | `LOST_HISTORY` (A24.1). Applies **only** if the *archive* lacks ids. |
| **2. consumer diagnosis** | delivered copy → archived product | the route back is a spatial match. Lineage itself is untouched. |

Hop 2 having no key does **not** create a `LOST_HISTORY` boundary. If the archive keeps
`lineage_id`, the chain is intact and complete; what degrades is how fast a human gets from a
consumer's complaint to the edge log. Separately answerable is not independent, though: the
one-join candidate in (b)1 is only available if hop 1 is answered "the archive carries it".

**The document assumes an answer and never states it, reading both ways.**

Publish strips it:

- A13's last bullet treats publish-time removal as a given, with the same gap as the work-key
  sweep (A9.6). `_apply_product_schema` runs `map_fields` with `keep_unmapped=False`, so a column
  not in the mapping is gone.
- A19 says an unstable identity must not be shipped to consumers, and `lineage_id` re-mints on
  every dissolve.
- T0.4 permits dropping the published id column outright.

It survives:

- A24.1's second row (`Derived` / `ProductIdentity` **with** `lineage_id` → **map only**) exists
  only if a cross-run input arrives carrying one.
- T3.7(a)'s stage-entry half, T0.6(b)'s copy-versus-map measurement and A23's trace-to-RAW all
  assume the same.

If the *archive* does not carry it, **every cross-run input is `LOST_HISTORY`**: the map-only
branch is unreachable, ingest copies on every run, and the edge log archived by T3.6 is keyed on
ids no readable product carries — retained, and unjoinable to anything.

**(a) Are the two artifacts the same today?** In the template, yes. `finalize_road_attributes`
calls `_apply_product_schema` as its last step (`operations/road/__init__.py:947`), so the
consumer schema is applied *inside the stage operation*, before the handle ever becomes a
`StageOutput`. `Publish` (`pipelines/road/n100.py:454`) then moves that already-mapped object to
its `ProductIdentity`'s archive location. There is one artifact, and it is the consumer schema.

**(b) Hop 2: how do you get from a consumer-reported feature back to its archived feature?** This
is the diagnosis-speed case the B-item exists for — a consumer says "this road is wrong", and the
question is how many steps separate that report from the edge log. Two questions, and the second
is the one that is easy to miss:

1. **Is there a hop at all?** With no key whatsoever in the delivered copy, the only route back is
   a spatial match. State whether a **run-scoped key under a non-identity name** — T0.4's
   `run_object_id` — is that hop. T0.4 currently offers "drop it" and "rename it" as equivalent
   options; if the key is the hop, they are not equivalent and T0.4 must choose.

   **State what value that key would hold.** The candidate is the **`lineage_id` value itself
   under a non-identity name** — then the hop is one join against the archive and nothing new is
   allocated. Any other value is a **third id**, needing its own allocation site and its own
   published-key → `lineage_id` map maintained at publish time: a new artifact with its own
   retention question. Recorded explicitly so a third id is not minted by default, as the path of
   least resistance from "don't ship `lineage_id`".

   The cost of the candidate is that the bits are shipped even though the name says not to rely on
   them: A19's protection becomes naming and documentation rather than absence, and a consumer who
   keys on it anyway gets an identity that re-mints. Whether that is acceptable is part of this
   question, not separate from it.

2. **Does the hop survive past the run that produced it?** A consumer reporting a problem in last
   quarter's N100 is holding a key from a run whose archive may be gone. A run-scoped key is only
   as good as the archive it keys into, so state:

   - whether **every delivered product version is guaranteed a retained archived counterpart**,
     given T3.6's retention rule — and specifically whether a re-run *replaces* the archived
     version, which would strand every key held by consumers of the delivered copy it replaced;
   - whether the **delivered product records which run produced it**. Without that, a run-scoped
     key is ambiguous across runs: the same `run_object_id` names a different feature in each run,
     and the consumer's report does not say which one they hold.

**(c) What depends on B9:** T0.4 (whether the key is dropped or named, and whether that is a
choice at all), T0.6(b) (the copy-versus-map measurement only has a subject if map-only is
reachable), the map-only branch in T3.4, T3.7(a)'s stage-entry guard, T3.6's retention rule, and
T6.2's boundary-crossing walk.

**(d) FINDING — the in-run stage output already loses `lineage_id`.** Verified against the
template. Recorded as a finding rather than a resolution: it constrains the answer without
supplying it.

- `_apply_product_schema` maps `{FEATURE_ID, ROAD_CLASS, RANK, "edited"}` with
  `keep_unmapped=False` (`ports/table_ops.py:162` is where that default lives). `lineage_id` is
  not in the mapping and there is no reason it would be — the mapping is the *consumer* schema.
- `ConflictResolution.final` is `ROAD`, published as `N100_ROAD` (A17.1), and `N100_ROAD` is a
  CONTEXT `StageInput` to the building pipeline's `DISPLACEMENT` in the **same run**
  (`pipelines/building/n100_stages.py:128-132`).
- A16's `DISPLACEMENT` verification rests on exactly that column: *"Context road ids land in `T`
  via `from_ids` without ever entering `I`"*. Those ids come from the column the mapping drops.

**What this forces and what it does not.** It forces the **in-run stage output to carry
`lineage_id`**. Moving mapping to a publish step is the natural way to get there, not the only
one — mapping inside the operation with `lineage_id` included in the mapping satisfies it too.
Either way the archive's own schema is untouched by this argument, because within a run
`DISPLACEMENT` reads the stage output and not the archive.

**A separate argument does bear on the archive, and it is not a resolution either.**
`n100_stages.py:158` makes one `StageInput` resolve two ways: *"Within a run it pins to that
stage's output; outside one, to the archived version at the location declared in `products.py`."*
If the two schemas differ, the same `StageInput` yields complete lineage in-run and a
`LOST_HISTORY` boundary on a cold start. **Completeness would then depend on run selection rather
than on the data** — the same feature traces differently depending on which pipelines happened to
be in the run. That contradicts A22's "a cold start is just an ingest where the incoming id column
is empty. No separate code path, no mode flag", and it is not reproducible across run selections,
which is the environment-dependent failure class this design keeps removing. That argues for
archive = working schema. Left open.

Related: B3 and A19 answer the neighbouring question — what the *stable* published identity is.
B9 is narrower and answerable first: it asks what is physically present on which artifact, not
what identity consumers should be given. B10 is the neighbouring *mechanical* question: nothing
currently notices when `lineage_id` goes missing, wherever it goes missing.

**A proposed resolution awaits sign-off** in `PROPOSALS-2026-09-14.md` §1 — not settled, and not
to be treated as settled until it is written here as an A-item.

**B10. Nothing asserts that `lineage_id` survives an operation.**

B9(d) exposes this rather than depending on it: `map_fields` is one way to lose the column, and
the design has no check that would name it.

**The existing checks do not cover it.** A11.12 fails a `CARRY` output whose `lineage_id` is
**null**. In B9(d) the column is **absent**, which is a different failure. T4.6's sweep reading a
missing field gets whatever the adapter raises — on ArcPy, a field-not-found error when the cursor
is constructed. That is loud and in the right run, but it is not a lineage message and it **does
not name the call that dropped the field**: the reader sees a cursor failing on a field they did
not know was expected, one operation after the `map_fields` that removed it. A13 asserts existence
on **inputs**; nothing asserts it on outputs.

And `map_fields` is not the only way:

| call | how it loses `lineage_id` |
|---|---|
| `map_fields(keep_unmapped=False)` | the field is simply not in the mapping |
| `delete_fields` | a working-field cleanup that sweeps it up |
| tool behaviour, no argument at all | an overlay where both inputs carry `lineage_id` and the backend renames one, most likely by suffixing — the field is present under a name nothing reads |

**Proposal, not a decision: a post-call assertion, not a pre-call rejection.**

Rejecting a call *before* it runs means the facade parses each method's field-dropping arguments —
`map_fields`'s `mapping`, `delete_fields`'s field list, `merge`'s field map. That is per-method
logic in the generic facade, which is exactly what A11.11 rejected when it chose one generic facade
over roughly 40 delegating wrappers. The third row of the table also has no argument to parse.

Instead: **after every port call that produces or mutates a lineage-bearing handle, assert that
`lineage_id` exists on that handle with the declared type.**

**Scope has to be "produces or mutates", not "produces".** A12.6's in-place mutators have no
output parameter, and `delete_fields` is one of them — the second row of the table above. An
output-only rule would never run after the call most likely to drop the field. For an in-place
mutator the handle checked is the **input**, since that is the thing being changed. Cost is
identical either way: one `describe_fields` per call, no row scan, no per-method knowledge — the
facade already knows which handles are lineage-bearing, because `@row_shape` told it. It runs
immediately after the call, so the error names the call.

It catches three things with one assertion:

1. **the absent column** — B9(d)'s case, named at the `map_fields` that caused it;
2. **a rename from tool behaviour** — the duplicate case, which no argument-parsing check could
   see;
3. **a type downcast** — T0.1's type-survival case enforced at runtime on every call rather than once in a
   throwaway script.

**The duplicate-field rule belongs to the adapter, not the facade.** That the backend suffixes a
duplicate is **what T0.1's overlay-duplicate case will confirm, not something established here** — and the obvious
pattern does not generalise. `lineage_id` is **exactly 10 characters**, so a backend with a
10-character field-name limit (shapefile) cannot produce `lineage_id_1` at all, and whatever it
produces instead will not match a `lineage_id*` glob. So the **adapter declares its
duplicate-naming rule and the facade consumes it** — the same shape as A14's capability record:
data supplied by the adapter, not knowledge embedded in the facade.

Given that rule, **fail on any field it identifies as a duplicate of `lineage_id`.** A stray
duplicate is not inert: it carries the *context* input's ids forward through later operations,
where a join or a sweep may pick it up as if it were the subject's. This is the same move as
A9.5's fail-on-any-unregistered-field, and for the same reason — a naming convention is only a
detector if something fails on it.

**The exemptions are a closed list, and one principle covers the four production ones.**
**Stage-level data movement is not an operation, and the facade wraps operations.** Ingest,
fan-out, fan-in and publish move features between stages without transforming them, so the
facade's per-call obligations do not apply and must not be made to:

| site | why it cannot go through the facade | task |
|---|---|---|
| ingest | stamps `lineage_id` onto copied inputs and builds the map — it *creates* the ids the facade would be asserting. Lives in `runtime/` and `staging/` | T3.4 |
| fan-out | partition selection, which mints nothing (A6.6); through the facade it would read as a transform | T3.4 |
| fan-in | **A6.5**: discarding the non-owning copies is deduplication of one identity, not a drop. Through the facade the boundary diff would record **every discarded context copy as `DROPPED`**. Also `runtime/` | T5.1 |
| the publish step | produces the delivered copy | — (pending B9) |

**The conformance suite is a fifth site with a different reason**, not an instance of the
principle: T4.11 drives the `Protocol` directly because the `Protocol` is what it conforms. It is
test code and excludable by path; the four rows above are production code.

Everything else writing `lineage_id` is a bug, including the A12.11a/T2.8 case of a domain call
naming it in a mutator's field list.

**Check the domain side, not the allowlist.** The obvious enforcement — *only the composition
root, `lineage/` and the publish step may obtain an unwrapped port* — is the wrong shape. That
allowlist grew by three sites in a single pass, two of them in `runtime/` rather than `lineage/`,
and it will grow again with every runtime step added. An allowlist edited whenever the runtime
grows is one that gets widened to `runtime/` for convenience, which is most of the system.

Invert it. The property being protected is that **domain code never writes `lineage_id` outside
the facade**, so check the domain side, where the list is closed and small: **`operations/`,
`helpers/` and `pipelines/` may not obtain an unwrapped port.** They already only have the
`Toolbox` passed in (A1.3). Everything outside the domain packages is unconstrained by this check,
and the sanctioned sites above stay written down as documentation of why they differ, not as the
enforcement.

**What the check inspects, and what it already gets for free.** "May not obtain an unwrapped port"
is mechanically checkable only as an **import rule**: the domain packages may not import
`adapters/`, nor any `runtime/` or `lineage/` module that hands out a raw port. Most of that is
already written down — `03-architecture.md` §4.1's table and `template_code/.importlinter` between
them forbid `operations/`, `helpers/` and `pipelines/` from importing `adapters/` and `staging/`.
**Run by hand against the template as it stands, all seven contracts pass.** They are **not run in
CI**: the repository's only workflow is `black --check`, and `03-architecture.md` lists "`.importlinter`
exists and passes in CI" as a graduation condition, not a present fact. Until T7.4 adds that step,
every contract here is a convention that happens to pass.

Three deltas, the first measured rather than assumed:

**1. `helpers/` is missing from the layers contract, and `operations/` is not.** Adding `ag.helpers`
to the stack between `ag.operations` and `ag.staging` keeps all seven contracts. Break-tested in
both directions rather than reasoned about: a `helpers` module importing `ag.runtime` **breaks the
amended contract and passes the current one**, while the same probe under `operations` is already
caught by the existing stack. So `operations/` and `pipelines/` need nothing; `helpers/` is a real
hole, currently invisible because `ag/helpers/` holds only `__init__.py`.

**The hole is only the upward direction.** Probing the two obvious companions, `helpers →
adapters` and `helpers → staging` are **both already caught** — not by the layers stack but by the
two `protected` contracts, which are allow-lists and therefore deny a package that is not named in
them. That is exactly the property the config's own comment claims for choosing `protected` over
`forbidden`, confirmed here by a package that nobody remembered to add. The layers stack has the
opposite default, which is why the upward imports slip through.

**2. `lineage/` does not exist yet and needs a row — but not a blanket one.** Forbidding the domain
packages from importing `lineage/` outright would flag correct code: operations call
`mint(parents=…)` explicitly (A11.12, A11.13, and A12.7's `_build_topology` nodes site). The row
must forbid only the modules that hand out raw ports. Two ways to arrange that, for T4.3 to choose:

- a **public lineage API module** the domain may import, with the rest of the package forbidden; or
- **`mint` reached through the `Toolbox`/facade**, so the domain never imports `lineage/` at all.
  This fits A11.12's "operations do not receive an injected `lineage`" more closely.

**Whichever is chosen, the row should be `protected` rather than `forbidden`** — on the evidence
above, where the two `protected` contracts covered a package nobody had remembered while the layers
contract did not, because **a layers contract permits any package it does not list**. The config
already argues this for `adapters/` and `staging/`; `lineage/` is the same kind of package and the
argument transfers unchanged.

**Both options cost one contract, so this does not tilt the choice.** Probed rather than assumed:
a `protected` contract on `ag.lineage` with `allowed_importers = ag.runtime`, plus one
`ignore_imports` line `ag.operations.** -> ag.lineage.api`, **admits the public module and still
denies every other `ag.lineage.*` module** to the same package. One wrinkle worth knowing before
T4.3 picks: an `ignore_imports` entry that matches nothing is a **hard error**, not a no-op, so
there is one line per domain package that actually imports the API — the list cannot rot silently,
but it is added to as packages start using it.

**`allowed_importers = ag.runtime` in that probe was the minimum needed to run the test, not the
proposal.** The table above already puts ingest partly in `staging/`, and fan-out and fan-in
elsewhere in `runtime/`. The real list is T4.3's to set from where those three actually land.

**A meta-check, because the `helpers/` hole was found by accident.** Nothing notices a package that
is in no contract. The check is small and needs no new tool: **assert that every top-level package
under `ag/` appears in the layers stack or in an explicit exempt list**, read from `.importlinter`
and the directory listing. `helpers/` would have failed it from the day the file was written, and
`lineage/` will exist before anyone thinks to add its row.

**3. The facade exposes no accessor to the port it wraps** — the part that is code rather than
configuration.

**Private-attribute reach-through is also checkable, and cheaper than expected.** An operation
legitimately holds the facade-wrapped `Toolbox`; `tb.geometry._port` needs no import and passes
every layering contract. **ruff `SLF001`** (private-member-access), scoped to `operations/`,
`helpers/` and `pipelines/`, catches exactly that. Verified rather than assumed:

- run over the three domain packages today: **clean, no hits**;
- the guessed false positive does not occur — `SLF001` exempts the namedtuple API (`_replace`,
  `_asdict`, `_fields`) and `self`/`cls` access, and a probe confirmed it flags `tb._port` while
  passing all three of those in the same file.

So the proposal is: one new layers row, one `lineage/` row whose shape T4.3 decides, one API
omission, and `SLF001` on three packages — no bespoke check written.

**One case examined and found not to need an exemption.** A field-mapped `merge` where one input
omits `lineage_id` produces **nulls**, not an absent column — so A11.12's sweep already fails on
it and this assertion is not the mechanism. In-run, an input lacking ids can only be a `FOREIGN`
handle, and A12.9's plan-time check already rejects a `FOREIGN` handle as a `CARRY` subject. No
second exemption found.

`destination:` if adopted, the lineage module docstring beside A13, `02-runtime.md` §8, and
`03-architecture.md` §4.1 for the import rules. The `.importlinter` row and the `SLF001` scoping
are code changes owned by T4.3, not documentation. At the `02-runtime.md` §8 destination, note that
the post-call assertion is **pure Python**: it runs in every environment, local Windows runs
included, and it is the runtime backstop for anything the image-only conformance suite (T4.11)
missed.

**B11. How is `displace_features.displacement` declared?**

A12.11 declares it `ONE + CARRY`. **Both axes are in question, and one branch has no legal cell.**

**The ids axis.** The competing reading is that the output is an **observation about a feature
rather than the feature** — amount and direction of displacement, the distinction A11.4a and
A12.12 already draw — and A12.10's test turns on exactly that: *ids change when the feature stops
standing for the same real-world object.* A displacement polygon does not stand for the road.

`SNAP_DISPLACEMENT` is worth citing as an **analogy, not a precedent**: it is `FOREIGN` for a
*structural* reason — it derives from vertex extraction through `_vertex_deltas` (A17.3, A12.12) —
rather than from the semantic argument above. The analogy still bites, because **two displacement
artifacts declared differently would read as inconsistent**, and the inconsistency would be
invisible: each reads defensibly on its own.

**The cardinality axis.** `ONE` asserts one output row per input road. **The tool page does not
state this**: it describes the output only as polygons containing "the degree and direction of road
displacement that took place", with no per-feature cardinality and no field list. Three shapes are
possible and they are not equally survivable:

| mapping | declaration | status |
|---|---|---|
| 1:1 | `ONE` + whichever ids axis wins | fine |
| 1:N — several polygons per road, with a reference column | **`MANY + FOREIGN`** | legal, no problem |
| **N:1** — one polygon spanning several roads | **`GROUP`** | **no legal cell** |

N:1 is the branch with nowhere to go. `GROUP + FOREIGN` and `GROUP + CARRY` are both illegal cells,
and `GROUP + MINT` is legal but wrong: it would make displacement polygons **features**, with
minted ids and edges, which is precisely what they are not.

**The escape hatch is more expensive than it was.** Re-adding `NONE` is **not** the one-line change
A12.3 recorded — that remark was written against the old single `SHAPE` enum. Under the two-axis
grammar an output with no subject has **no value on either axis**, since cardinality is defined as
rows per subject row. It is a third kind of declaration outside the grid, and it costs: T4.1's
missing-axis check needs an explicit exemption rather than a new member, and the facade needs a
rule for an output that is neither lineage-bearing nor ref-bearing — a state it currently has no
branch for. The alternative, **having the adapter synthesise refs spatially**, is A14's third tier
of four, "expensive and wrong at coincident boundaries" — and displacement polygons at a junction
are close to the worst case for it.

**Partly measurable, and T0.1 carries the measurement.** Semantics decide `CARRY` versus `FOREIGN`;
what is *declarable* depends on what the tool emits. T0.1 records, for this output, **its columns —
any per-feature reference in particular — and the mapping shape**.

**Row count cannot establish `ONE`.** Equal counts are consistent with a shuffled mapping or a
partial one. The mapping shape is read from a reference column if one exists, and recorded as
**undeterminable** if none does.

So the two questions resolve in sequence, not independently:

- **with a native-index reference**, the ids axis is decided on semantics, and either `CARRY` or
  `FOREIGN` is achievable — the port reports the correspondence and the facade stamps from it
  (A11.11). Note what a *scalar* reference can express: **1:1 or 1:N**, since N:1 has several
  inputs to point at. A delimited reference is not excluded by that — A14's tier 2 parses one
  inside the adapter as sanctioned transport — but parsing it yields an **N:1 relation**, which
  lands back on `GROUP`, where `FOREIGN` and `CARRY` are illegal and `MINT` makes displacement
  polygons features. The shape is what has no cell, not the encoding;
- **with no reference**, neither is declarable. The port can only report correspondence the tool
  provides, so `CARRY` has nothing to stamp from and is as undeclarable as `FOREIGN`. The choice is
  then `NONE` or spatial synthesis, and the semantic argument above does not enter it.

Its only consumer is `propagate_displacement`, which reads it as **context** — so the blast radius
is small either way, which is why this is a B-item rather than a blocker.
`destination:` `ports/cartographic_ops.py` with A12.11, once resolved.

> *See the open note below B16 (2026-09-21):* leaving this output undeclared and declaring
> `simplify.collapsed_points` while the adapter refuses it are two answers to one question; the
> pattern is settled when B11 or B16 is decided.

**B12. T4.1's check cannot identify an output parameter.** Found by the 2026-09-14 review (F6),
verified. A12.5 and T4.1 reject "an output parameter with no declaration", but every handle
parameter on the port Protocols is typed `ScratchHandle`; the `In`/`Out` aliases
(`core/operations.py:231-235`) are used only by operations. The only thing that marks a port
parameter as an output is the declaration being checked, so the rule cannot fire — the
green-by-coincidence failure, in the check the grammar rests on. A proposal (annotate port
parameters with `In`/`Out`, in T4.1's scope, as A12.5a) awaits sign-off in
`PROPOSALS-2026-09-14.md` §2.

> *Resolved 2026-09-17 into A12.5a*, with the annotations pulled forward to T2.9 and a
> `ParentsOut` marker exempt from the output-declaration rule.

**B13. `write_rows` and `write_table` have no row shape, and A12.7 contradicts A15.6.** Found by
the review (F5), verified against the template. Both writes have an `output` parameter
(`ports/table_ops.py:209-225`) and no row in A12.11 or A12.11a. Two of A12.7's four "no call-site
change" sites read a `FOREIGN` handle: `_vertex_deltas` pipes `paired`, a `nearest_neighbors`
output over `extract_vertices` outputs, into `displacement`, which is
`StageOutput(SNAP_DISPLACEMENT)` (`operations/road/__init__.py:322-329`,
`pipelines/road/n100.py:300`); `merge_divided_highways` pipes `paired`, a `spatial_join` output,
into `merge_report` (`:592-596`, `:611`). A12.7's rule — untracked rows written to a scoped output
with no explicit mint are an error — fires on the first, which A15.6 calls legal. On the second it
fires only if `merge_report` counts as diff-tracked, which A15.2's "reaches a `StageOutput`" does
not settle for an input that feeds only a predicate. Also unsettled: what a ref column holds when
the handle it refers to is itself `FOREIGN`. A proposal (a required call-site ids declaration on
writes, as A12.7a) awaits sign-off in `PROPOSALS-2026-09-14.md` §3.

> *Resolved 2026-09-21 into A12.7a*, signed as proposed. The sub-question about a ref column
> whose ref names a `FOREIGN` handle stays with T4.4.

**B14. `lineage-bearing` has no stated plan-time derivation.** Found while verifying B13.
A15.2, A15.6 and T4.9 say the property is computed from "the stage declaration and the operation
wiring", and A12.9's check runs at plan time. But `@row_shape` sits on **port** methods, and plan
time sees only `@operation` In/Out handles: nothing in the planner observes which port calls an
operation body makes (`02-runtime.md` §9, "declarations need no data or ArcPy"). The one component
that executes bodies without data is the recording spy (`adapters/fakes/recording_toolbox.py`,
driven by `tools/run_example.py`); a trace of its recorded calls is the obvious candidate, not a
decision — bodies that branch on read data would trace partially. The gap is general, not specific
to writes.

A related consequence, also not decided: A12.9 rejects a `FOREIGN`-terminal handle as the subject
of a downstream `CARRY`, and A12.11 declares `select`, `copy` and `map_fields` `ONE + CARRY`. So
filtering or copying a near table — `GenerateNearTable` then select by distance, common in the
real codebase — would be rejected, though no template instance does it today.

**B15. `merge_report`'s exemption matches ids from before two mints.** Found while verifying B13.
`merge_report` holds ids of the carriageway *candidates* (`operations/road/__init__.py:592-596`).
`thin_road_network` uses it as `exempt=Attr(FEATURE_ID in (select … from merge_report))` on
`reranked_edges` (`:678`), which descends from `collapse_to_centerline` (`GROUP + MINT`) and then
`dissolve` (`GROUP + MINT`). Under A9.10 the exemption can match nothing. A17.4 records the
predicate as uncompilable; this is a separate defect in what it compares. T4.12 checks `join_field`
only, so a lookup done as read-then-`Attr.in_` is outside its reach.

**B16. The vendor documentation contradicts `simplify.collapsed_points` as `ONE + CARRY`.** Found
while writing T0.1's script. A12.11 assumes the point output copies the input's attributes. The
`SimplifyLine` and `SimplifyPolygon` tool pages, checked 2026-09-14, both say *"The output line
[polygon] feature class contains all the fields from the input feature class.*
*The output point feature class will not contain these fields."* Neither page documents a
reference column on the points. `SimplifyLine` also stores *"the endpoints"* of a collapsed line, which may be two rows per
input — `MANY`, not `ONE`. T0.1's type-survival case checks the behaviour. If it confirms the
documentation, the "neither present" branch of T0.1's "if this fails" applies: the set-difference
derivation, conditional on the port contract T4.2 writes. Not decided here, and T0.1 has not run.

> **Open note on B16 and B11, 2026-09-21: a declared-but-unavailable optional output has no
> settled pattern.**
> The two items are handled differently today. For `simplify.collapsed_points`, slice 3 of
> `findings/implementation_plan.md` declares the output on the Protocol per A12.11, implements
> it in the in-memory adapter, and has the ArcPy adapter raise `CapabilityError` when it is
> requested, until B16 is answered. For `displace_features.displacement`, B11 leaves the
> output undeclared altogether. Both are optional outputs an adapter cannot yet honour, and one
> pattern should cover them. It is settled when B16 or B11 is decided, whichever comes first,
> and it includes which error a caller sees: the plan places `CapabilityError` under
> `AdapterDefectError`, which means the adapter is wrong, and a known, declared limitation is
> not a defect. The precedent for the other reading is `ParentsUnavailableError`, a `PortError`
> (A14.1). No change is made now.

**B17. Which mechanism produces `dissolve` parents.** Open. Everything above the port is settled
(A11.15, A14.1); this is the adapter's choice, judged against A15.7. Evidence in `temp/findings/n1_correspondence.md`, measured on Pro 3.7.2 on 2026-09-15:

- **CONCATENATE is dropped**, as the runtime path and as an oracle (A14.1).
- **The native lineage table** is the production source for `aggregate` and
  `collapse_to_centerline`, whose tools emit it on the current image and whose geometry moves, so
  nothing else can be right. For `dissolve` it is the **conformance oracle only**: new at Pro 3.7,
  absent from the image, 110 s added at 10^5 against a 1-minute budget, single-part output only,
  and its part order differs from the plain run.
- **The keyed resolver** (`temp/dissolve_parents.py`: attribute join for single-part keys, a
  key-filtered spatial lookup for multi-part keys, one bulk join per call) is **adopted for
  polygons and points**: 0.4 s at 10^5 on the join path, equal to the native table on every
  fixture, the eight goldens replaying without ArcPy. **Lines are conditional** on T4.14: single-part
  output splits at every junction, so the locator path is the production path for every line key; a
  point finds one part of a split input and can land on a junction node; the segment locator
  (shared-segment join) that closes both gaps has its lattice numbers and the real-data key sizes
  still pending. The resolver's precondition — an input's representative point lies within the
  engine's tolerance of the part it became — holds for a dissolve by construction and for
  `buffer_dissolve` at positive distances only.
- **Two adapter guards** either way: before the tool, an empty shape in the subject raises
  `EmptyGeometryError` with the row indices (an empty polyline emptied a whole PairwiseDissolve
  output silently); after it, an unmatched input raises `UnmatchedInputError` unless it is
  degenerate — empty, or length or area at or below the engine's XY tolerance. The adapter never
  turns an unmatched input into `DROPPED` (A11.7 stands).
- **Combining rules** (A9.11) are recommended to be computed by the adapter as a group-by over the
  parents pairs joined to the input attributes — per output row by construction, one pass over a
  table it already has — never through the engine's own statistics option.
- **Real data, 2026-09-17** (findings §3.11): the ramps stage's input partitioned by
  `PartitionIterator` itself at the stage's 35,000 / 500 m gives, as its largest selection,
  36,407 rows (34,780 + 1,627 halo) in 44 keys, the largest key 15,392 rows becoming 13,310
  parts; output parts per input 1 at p95, 2 at most, because that input is already planarised.
  The native lineage table cost **0.8 s added over a 3.3 s plain dissolve** there, against
  110 s added at 10^5 on the one-part fixture: its cost is shape-dependent (a hypothesis with
  one bracket), B stays unavailable in the image, and portability keeps the keyed resolver as
  the production path. The lineage run also produced one more part than the plain run (25,367
  against 25,366), so locators are always judged against the lineage run's own output. Five
  non-degenerate inputs were absent from the table; a per-input diagnostic decides whether the
  tool dropped them, a same-key duplicate absorbed them, or the table omitted parents it merged
  — the last case makes B unfit as a fast path and an incomplete oracle. **Measured
  (findings §3.11, third run): all five are omitted parents** — 5 cm segments the tool merged
  and the table does not list — so the table is incomplete under the current definition of
  degenerate (the XY tolerance), and T4.11's `dissolve` case should assert resolver ⊇ table
  unless "degenerate" is widened to what the engine absorbs, a definition the user decides.
  **On that partition the segment locator reproduced every table pair and paired the five
  absent inputs, in 20 s added over plain; the point locator left 904 inputs unmatched.** The
  synthetic ladder agrees: on every fixture where an input becomes several parts the segment
  locator is exact and both point locators are not. The segment locator is therefore the line
  candidate, and its cost is measured (after fixing the resolver's own pair validation, which
  had built one set of parts per input — inputs x parts memory — fixed 2026-09-17 and
  unit-tested at 40,000 x 40,000): 5.4 s at 10^5 on the segmented lattice, and on the STRESS
  margin (250,000 elements, 5,000 m radius, no stage uses these) **47.7 s added over plain on a
  267,429-row selection whose largest five-field key is 112,331 rows into 96,185 parts, pair
  sets equal to the table** — 92 % of it in the spatial join. Two residual failure classes, both
  on geometry the pipeline should not produce: sub-decimetre input segments (4–9 cm), which the
  table omits and the segment locator finds only partly; and sliver output parts shorter than an
  input segment when a single-key dissolve splits inputs mid-segment (265 of 267,429 inputs as one
  group; none on the five-field key). The guard raised in both cases rather than dropping
  silently. Two decisions follow: the degenerate threshold (XY tolerance, or a length the engine
  absorbs, about 0.1 m), and whether the segment locator gains a distance-based second pass for
  parts left without a parent. A 10^6 group does not occur in a partitioned stage.

Resolves when the real-partition comparison and the ladder are recorded and one locator per
geometry type is named.
`destination:` `adapters/arcpy/` package docstring.

**B18 — RESOLVED 2026-09-17, option (b), into the amendment on A18 and the supersession on A5.6.**
`dissolve` is single-part by contract; `DissolveOption` leaves the port; `dissolve_multipart` and
an unsplit method are added when callers are migrated. The question, kept for the record: A5.6 kept
`option: DissolveOption` as an argument because it does not move the row-shape cell, while A18 and
T2.9 said a multipart dissolve becomes a separate method. Both could not be the port; the real
call sites are listed under A18.

**B19 — RESOLVED 2026-09-17 into A9.12.** `statistics=((RANK, MAX),)` had an example and no type;
A9.12 gives it `Statistic` and `StatisticSpec`, and A9.11 its semantics.

**B20. Lineage through `run_dissolve_with_intersections`.** Found by the N:1 real-data probe
(2026-09-17). `generalization/n100/road/data_preparation_2.py:336-346` runs, twice, on the
**national, unpartitioned** road set: `PairwiseDissolve` on the 12-field key
(`FieldNames.road_input_fields`) → `FeatureToLine` → `Merge`
(`custom_tools/generalization_tools/road/dissolve_with_intersections.py:62-140`). In the grammar
that is `GROUP + MINT` followed by `MANY + MINT`, an N:M chain, and it is the largest dissolve the
pipeline runs — the ramps partition dissolve is bounded by 35,000 rows plus halo, this one by the
national key. Three decisions:

1. **Does it run before `lineage_id` exists?** If the chain is part of ingest (data preparation
   before the first `StageInput`), no edges are needed and the parents question does not arise.
   `data_preparation_2.run` is the live pipeline entry (`main_on_prem.py:155`), so where the
   lineage boundary sits in it is a T3.4 question.
2. **Otherwise, how do parents pass through the chain?** `dissolve` reports pairs (A11.15);
   `FeatureToLine` would need to be a port method with its own `MANY + MINT` declaration and pairs
   (T2.9 decides), and the facade composes the two mints; `Merge` is `ONE + CARRY`. Per-medium
   selection between them is `select`, `ONE + CARRY`.
3. **Is an unpartitioned national call acceptable in the container design at all?** The runtime
   schedules only stages, fan-out → K pods → fan-in (02-runtime §2.3). A national dissolve is a
   K = 1 stage with the whole dataset in one pod, or a partitioned dissolve whose groups cross
   partition borders and depend on the halo, which changes which parents a pod can see. Neither
   is decided, and A15.5's worst case was written for the partitioned form.

The first number this item needs is the 12-field key counted on the chain's **input**,
`Road_N100.data_preparation___road_single_part___n100_road` (`file_manager_roads.py:126`, the
`MultipartToSinglepart` output at `data_preparation_2.py:331`). The count made on 2026-09-17 ran
on `road_single_part_2`, the chain's **output** (2,038,774 rows, 80,482 keys, largest 155,944):
an indicative figure only, since `FeatureToLine` splits rows and output parts per key bound the
input in neither direction. **Measured on the input on 2026-09-17** (findings §3.13): 2,320,817
rows, 80,482 keys, largest key **121,341** rows; the plain dissolve on that key **did not finish
in 270 s**, and as one group it took 157.5 s with the native table adding 24.8 s and the segment
locator 869 s. So a 10^6-row group does not occur here either, but a 2.3·10^6-row *call* does, and
it is over every budget on its own: decision 3 is the live one, and the answer the numbers point
to is a partitioned stage (or ingest before `lineage_id`), with parents a partition-size question.
`destination:` `02-runtime.md` §2.3 for decision 3; `ports/geometry_ops.py` for decision 2; T3.4
for decision 1.

**B21 — RESOLVED 2026-09-21, option (a), into A5.7.** The question, kept for the record: who
creates a workspace. `ScratchFileManager.create_workspaces` was unimplemented in the template
and its docstring named `CreateFileGDB`, which `staging/` may not call; no A-item, ADR or port
method covered it (`findings/template_review.md` §4, §7). Options were (a) a `TableOps` method,
(b) a callable injected into the manager by `runtime/`, (c) lazy creation by the adapter.
