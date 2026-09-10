# Lineage and Identity — Task Plan

**Status:** STAGING. This directory is not a permanent home.

## How to use these two files

[DECISIONS.md](DECISIONS.md) holds the rationale: what was decided, why, and — where a position
reversed — what it replaced and why the reversal happened. It is stable. Edits to it are
supersessions appended in place, never rewrites.

This file holds the work. Every task carries `decision refs` pointing at the A-items that justify
it, so no task needs conversation history to be actionable.

**Updating status.** Edit the `status` line in place: `not started` → `in progress` → `done`, or
`blocked` with a one-line reason. Status lives here and nowhere else, so progress survives a
context compaction or a three-month gap.

**Migration protocol.** A task is not done when the code works. It is done when the code works
**and** every A-item in its `doc migration` line has been moved to its `destination:` in
DECISIONS.md — an ADR, a module or class docstring, `02-runtime.md`, `03-architecture.md`, or the
validation vocabulary. Move the content, then strike the A-item in DECISIONS.md with a pointer to
where it landed. Do not leave a copy in both places; two copies diverge.

**Completion test.** `docs/refactor/temp/` is deletable when every task below is `done` and every
A-item in DECISIONS.md has landed at its destination. The remaining B-items must by then be either
resolved into A-items or promoted into a real document as stated open questions. If temp still has
content and every task is done, something did not migrate.

## Ordering

This is a **linearization by recommended implementation order**, not a subject grouping. The
earlier Groups 0–6 were subject-based and several were declared parallel; that structure is gone.

Ordering principles, in priority order:

1. **Gates first.** T0.1 and T1.4 each gate large amounts of downstream work and can invalidate
   settled decisions. They go as early as their dependencies allow.
2. **Then dependency order.**
3. **Then cheap-and-independent**, so useful work is available while a gate is in flight.

## Independent track

Tasks marked **`[INDEPENDENT]`** have nothing to do with lineage. They touch the port surface or
the row model for their own reasons, have no lineage dependency, and can be picked up in parallel
— including by someone not following the lineage design at all. They are listed in position but
can move freely.

## Merged tasks

Six pairs accumulated across design passes and would have edited the same file for the same
reason. Merged, with the retired id noted in the surviving task:

| merged | into | reason |
|---|---|---|
| T0.5 (delete `union`) | **T2.9** | Both are surgery on the `GeometryOps` method list. |
| T2.3 (parents constants) | **T2.4** | The constants exist only to serve the parents out-param. |
| T2.11 (A17.5 ranks fix) | **T2.10** | The fix is not possible without the `statistics` parameter; one change. |
| A17.4 / A17.7 fixes | **T2.1** | The uncompilable `Attr` subqueries are fixed by the structured-`Attr` rewrite, in the same files. |
| T4.7 (edge types + per-op sweep) | **T4.6** | Mint, the provisional buffer, the collapse and the sweep are one subsystem with one acceptance test. |
| T1.2 (comparison + log) | **T1.1** | T1.1 alone produces a shadow output nobody reads; the comparison is what makes it checkable. |

**Not merged, deliberately:** T0.3 and T0.4 are both template fixes but touch unrelated files for
unrelated reasons. T4.4 (pipe) and T4.5 (cache) both live in the facade but are independent
mechanisms with independent acceptance. T3.1 (native index) and T3.2 (work key) are both identity
work but have different lifetimes and different modules.

---

## Order at a glance

| # | id | task | status |
|---|---|---|---|
| 1 | T0.1 | **GATE** — 64-bit storage capability | not started |
| 2 | T0.2 | Per-feature id in `PartitionIterator` | not started |
| 3 | T1.1 | Shadow centroid selection and comparison | not started |
| 4 | T1.3 | Synthetic transform suite | not started |
| 5 | T1.4 | **GATE** — national-scale shadow run | not started |
| 6 | T2.1 | Structured `Attr` `[INDEPENDENT]` | not started |
| 7 | T2.7 | `Row` slots and value-type docstrings `[INDEPENDENT]` | not started |
| 8 | T2.5 | Linear referencing on `Geometry` `[INDEPENDENT]` | not started |
| 9 | T2.6 | Raster `sample_at` `[INDEPENDENT]` | not started |
| 10 | T2.2 | `update_rows` `[INDEPENDENT]` | not started |
| 11 | T2.8 | `join_field` unique-key contract | not started |
| 12 | T0.3 | Fix `resolve_ramps` inversion | not started |
| 13 | T0.4 | Rename the published `objid` mapping | not started |
| 14 | T2.9 | Port surface surgery — splits, `DANGLE`, delete `union` | not started |
| 15 | T2.10 | `dissolve(statistics=…)` and the `ranks` fix | not started |
| 16 | T2.4 | Parents out-param and column constants | not started |
| 17 | T3.1 | Native index behind the port | not started |
| 18 | T3.3 | Dispatch minter-id registry | not started |
| 19 | T3.4 | Ingest step | not started |
| 20 | T3.5 | Per-job log artifact and counter checkpoint | not started |
| 21 | T3.2 | Work-key API | not started |
| 22 | T4.1 | `@row_shape` types and CI check | not started |
| 23 | T4.2 | Declare shapes across the port surface | not started |
| 24 | T4.3 | Generic lineage facade | not started |
| 25 | T4.5 | Id-map cache | not started |
| 26 | T4.4 | Lineage-aware `read_rows` → `write_table` pipe | not started |
| 27 | T4.6 | Mint, edges, and the per-operation sweep | not started |
| 28 | T4.8 | Stage-exit sweep | not started |
| 29 | T4.9 | Derived scope rule | not started |
| 30 | T4.12 | Mint-generation join check | not started |
| 31 | T4.13 | Lost-ref detectors | not started |
| 32 | T4.10 | Adapter parents capability | not started |
| 33 | T4.11 | Adapter conformance suite | not started |
| 34 | T5.1 | Fan-in log merge and `DROPPED` promotion | not started |
| 35 | T5.2 | Completeness assertions | not started |
| 36 | T5.3 | Origin-closure check and `DISPLACEMENT_FEATURE` fix | not started |
| 37 | T5.4 | Ownership-assignment verification | not started |
| 38 | T6.1 | Edge storage format | not started |
| 39 | T6.2 | Lineage walk API | not started |
| — | B2 | Q-C investigation `[INDEPENDENT]` | not started |

---

## 1. T0.1 — GATE: 64-bit storage capability

**status:** not started

**what done means**

Five cases run against a file geodatabase **created the way the pipeline creates them**, results
recorded in a short written finding:

1. Write a value just under 2⁵³ — passes, reads back unchanged.
2. Write a value just over 2⁵³ — **recorded whether it errors or silently coerces.** This
   determines whether a runtime guard suffices or a static one is required.
3. Round-trip through `write_rows` → `read_rows` — batching puts the coercion boundary further
   from the domain code that produced the value, so a write-then-read test is not sufficient.
4. Predicate-filter on the field.
5. File-geodatabase version: community reports say a target fgdb at version 10.0 or below rejects
   the Pro 3.2 field types, while the docs say the fgdb version has not changed since 10.0.
   Ambiguous enough to test rather than reason about.

The finding states whether `FieldType.BIGINT` is viable, and if not, which fallback is chosen.

**files touched** a throwaway script plus a written finding in `docs/refactor/temp/`.

**depends on** nothing.

**decision refs** A10.1, B1.

**doc migration** none — this resolves B1 into an A-item, which is then written into the new ADR
on lineage id allocation by T3.3.

**if this fails**

If file gdb cannot hold a 53-bit integer, A10.1's layout does not survive as written. The fallback
is a text field (works everywhere, slower joins) or two LONG columns (int performance, compound
predicates). **Either changes the declared field type at every call site that stores a
`lineage_id`** — a domain-visible schema change, not an adapter swap. Affected: T3.4, T3.5, T4.1,
T4.2, T4.3, T4.6, and every later task. This is why it is first despite being small.

---

## 2. T0.2 — Per-feature id in `PartitionIterator`

**status:** not started

**what done means** Every processing input carries a per-feature id field, unique within the run
of the iterator, surviving the operations the iterator drives. `PARTITION_ID_FIELD` is on the
partition polygons and `PARTITION_FIELD` is 1/0, so neither serves — this is a new field.

**files touched** `custom_tools/general_tools/partition_iterator.py`.

**depends on** nothing.

**decision refs** A7.4.

**doc migration** none — transitional, retires with `partition_iterator.py`.

---

## 3. T1.1 — Shadow centroid selection and comparison

**status:** not started
*(merged: former T1.2)*

**what done means**

- `_extract_partition_output` produces a second, silent extraction using `HAVE_THEIR_CENTER_IN`
  against `iteration_partition`, appended to a parallel output path. Not selectable by callers.
- Orphan handling: features whose centroid falls in no partition are tested once against the
  dissolved union of `self.partition_feature` — **not** `partition_features_all`, which is
  accumulated during iteration and answers differently depending on order — then assigned to the
  nearest polygon, ties to lowest partition index.
- At completion, control and test are compared by **multiset equality on (id, geometry)**: hash
  each, build a `Counter` on each side, compare. Not count-plus-bidirectional-existence, which is
  sufficient only if control has no coincident geometries.
- CLIP-extraction outputs are excluded from the comparison; `PairwiseClip` modifies geometry so
  nothing can hash-match.
- Per-run JSON written through the existing `write_documentation`, containing: the multiset
  verdict; mismatches **classified by direction**, with `PARTITION_FIELD` null/0/1 recorded for
  each; per-partition counters; the claim record `(per_feature_id, partition_id, claim_reason ∈
  {centroid_in, nearest_orphan})`; and the drift distribution, **read separately for line and
  polygon inputs**.

**files touched** `custom_tools/general_tools/partition_iterator.py` (hook at `:1847`, logging via
`:769`).

**depends on** T0.2.

**decision refs** A7.1, A7.2, A7.3, A7.5, A7.6, A7.7, A7.8, A7.10.

**doc migration** none directly — feeds T1.4.

**note for whoever picks this up** A mismatch is not automatically a failure. A geometry present in
test but absent from control, whose `PARTITION_FIELD` is null, is a feature created during
processing that **control drops today** — the improvement case, not the risk case. A strict
equality gate would misread it.

---

## 4. T1.3 — Synthetic transform suite

**status:** not started

**what done means** A test harness driving `PartitionIterator` over synthetic data with known
cardinality, since generalization gives no natural oracle — reducing feature count is the job.
Transforms:

- point moved randomly within the context radius
- line extended by a random distance within the context radius
- polygon buffered on one side by a random radius within the context radius
- **a no-op control** — any disagreement here is a harness bug, not a method result
- **a deliberate-drop transform** (delete every Nth) — confirms the harness does not report false
  loss when loss is intended
- **a directed boundary case** — a feature constructed so its centroid provably crosses a known
  interior partition boundary, rather than relying on random movement to hit one

Each run produces the same JSON as T1.1.

**files touched** `tests/` — path TBD, no invariance test directory exists yet.

**depends on** T1.1.

**decision refs** A7.9.

**doc migration** none.

**note** The suite's orphan rate is *not* an estimate of the production rate. Adversarial movement
at the data edge pushes centroids out routinely; production does not.

---

## 5. T1.4 — GATE: national-scale shadow run

**status:** not started

**what done means** A full national run with the shadow active, producing: a multiset verdict
across all outputs; the drift distribution for lines and for polygons; the orphan count and rate;
and a written judgment on whether centroid selection is safe to adopt.

**The number that matters is margin**, not pass/fail: maximum drift against halo width. Single-digit
metres against a 500 m halo is a two-order-of-magnitude margin and is the answer to the "some
methods are 95–99% deterministic" concern. A boolean verdict answers nothing.

**files touched** none — this is a run and a report.

**depends on** T1.3.

**decision refs** A6.1–A6.6, A7.5, A8.

**doc migration** on success, A6 and A8 move to `02-runtime.md` §7 and the new ADR on partition
ownership; A7 moves to `02-runtime.md` §7.2.

**if this fails**

A6 does not survive as written and fan-in ownership must be reconsidered. The field-carried and
CLIP alternatives were both rejected for reasons that do not go away (A6.1), so a failure here
means a new mechanism, not a fallback to an old one. Affected: A6 in full, A7, T5.4, and the
ownership half of T5.1. The lineage work (T3.x, T4.x) does not depend on this and continues —
which is why T1.4 is started early and left in flight rather than blocking.

---

## 6. T2.1 — Structured `Attr` `[INDEPENDENT]`

**status:** not started
*(merged: the A17.4 and A17.7 call-site fixes)*

**what done means**

- `Attr.cmp(field, op, value)`, `Attr.in_(field, values)`, `Attr.is_null(field)` exist and compile
  through the arcpy adapter with correct identifier quoting per workspace type.
- `Attr.raw(cql)` exists as the escape hatch, and a unit test asserts its call-site count against a
  pinned number, so adding one is a deliberate edit to a test.
- The three uncompilable subqueries are rewritten: `operations/road/__init__.py:678` and `:942`
  (subqueries against a `ScratchHandle`), and
  `operations/building/__init__.py` `data_selection` — `Attr("byggtyp_nbr in (select code from
  codes)")` becomes `Attr.in_(BUILDING_TYPE, codes)` with the lookup read via `read_rows` first.
- The 39 `deleteRow()` sites have a target form: `select(where=~Attr.in_(id, ids))`.

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/adapters/arcpy/predicates.py`, `template_code/ag/operations/road/__init__.py`,
`template_code/ag/operations/building/__init__.py`,
`template_code/tests/unit/test_predicates.py`.

**depends on** nothing.

**decision refs** A2.1, A2.2, A2.3, A17.4, A17.7.

**doc migration** A2.1–A2.3 → new ADR amending ADR-0001. A17.4 and A17.7 retire with the fix.

**note** A17.7 matters beyond the fix: `data_selection` is the one place in the template
demonstrating the *legitimate* domain-key lookup pattern (A17.6), and it is currently written in
the form that cannot compile.

---

## 7. T2.7 — `Row` slots and value-type docstrings `[INDEPENDENT]`

**status:** not started

**what done means** `Row` is `@dataclass(frozen=True, slots=True)`. The `AttributeValue`
docstring states that BLOB and Raster values are out of scope and that the answer if they arrive
is a reference in a TEXT field with bytes in a side store, not widening the union. The
`Coordinate` docstring states why it stays z-free — sampled elevations land in fields, not in
geometry — so the omission is not "fixed" later.

**files touched** `template_code/ag/ports/table_ops.py`, `template_code/ag/ports/geometry.py`.

**depends on** nothing.

**decision refs** A4.4, A4.5, A4.6, A5.3.

**doc migration** A4.4–A4.6 and A5.3 → the two module docstrings.

**note** `slots=True` is free but is *not* where the memory is; see B5.

---

## 8. T2.5 — Linear referencing on `Geometry` `[INDEPENDENT]`

**status:** not started

**what done means** `Geometry` gains methods covering roughly 43 existing call sites:
`measureOnLine` (13), `queryPointAndDistance` (13), `positionAlongLine` (10), `segmentAlongLine`
(7), plus length and area. Per-value math with no dataset, so they are `Geometry` methods and not
`GeometryOps`. Each has a shapely and a PostGIS equivalent named in the docstring
(`project` / `ST_LineLocatePoint`, `interpolate` / `ST_LineInterpolatePoint`, `substring` /
`ST_LineSubstring`).

**files touched** `template_code/ag/ports/geometry.py`.

**depends on** nothing.

**decision refs** A5.1.

**doc migration** A5.1 → `ports/geometry.py`.

---

## 9. T2.6 — Raster `sample_at` `[INDEPENDENT]`

**status:** not started

**what done means** `GeometryOps.sample_at(raster, points) -> tuple[float | None, ...]` exists and
covers `LineZValueTool`'s two-pass shape: collect points, window-load each raster once to the
bounding box, index in memory. The docstring states why this is a method and not a fifth port —
the project enriches vector work from raster and generates contours, but never delivers a raster
product.

**files touched** `template_code/ag/ports/geometry_ops.py`, `docs/refactor/03-architecture.md` §2.1.

**depends on** nothing.

**decision refs** A5.2, A4.6.

**doc migration** A5.2 → `ports/geometry_ops.py` and `03-architecture.md` §2.1.

---

## 10. T2.2 — `update_rows` `[INDEPENDENT]`

**status:** not started

**what done means** `TableOps.update_rows(input, key, fields, rows)` exists: bulk, keyed, no
iteration protocol exposed. Writes only changed rows and only the named fields. Accepts
`Row.geometry`, so snap and displace are covered without a rebuild. The arcpy adapter compiles it
to a keyed cursor pass; the docstring names `UPDATE … FROM` and pandas merge-and-assign as the
equivalents that keep it portable.

**files touched** `template_code/ag/ports/table_ops.py`,
`template_code/ag/adapters/arcpy/` (implementation).

**depends on** T0.1 — the key is a `lineage_id`, so the field type must be settled.

**decision refs** A4.1, A4.2, A4.3.

**doc migration** A4.1–A4.3 → ADR-0004 amendment and `ports/table_ops.py`.

---

## 11. T2.8 — `join_field` unique-key contract

**status:** not started

**what done means** B4 resolved and written down: either `join_field` declares that its join key
must be unique — with a check — or the grammar gains a way for an in-place mutator to declare a
cardinality change. A non-unique join key changes row count with no output parameter to declare,
so the `@row_shape` grammar cannot currently see it.

**files touched** `template_code/ag/ports/table_ops.py`.

**depends on** nothing.

**decision refs** A12.6, B4.

**doc migration** resolves B4 into an A-item; that item then lands in `ports/table_ops.py`.

---

## 12. T0.3 — Fix `resolve_ramps` inversion

**status:** not started

**what done means** `resolve_ramps` selects `is_ramp = 0` as its base and merges the reinstated and
collapsed ramp geometry into it, so `output_lines` contains all non-ramp roads plus the new
connector geometry. This matches `generalization/n100/road/ramps.py:56-61`, where `delete_ramps`
removes ramps from the copy and the output is all remaining roads plus `new_lines`. Today the
template does the opposite and every non-ramp road vanishes.

**files touched** `template_code/ag/operations/road/__init__.py`.

**depends on** nothing.

**decision refs** A17.2.

**doc migration** A17.2 retires with the fix.

**why it is early despite being small** This is the file people copy when writing their first
operation.

---

## 13. T0.4 — Rename the published `objid` mapping

**status:** not started

**what done means** `_apply_product_schema` no longer maps a field to a bare `objid`. Either the
column is dropped from the published schema, or it is named so that it does not read as a stable
identity (`run_object_id` or similar). Shipping `objid` binds consumers to an identity that
re-mints on every dissolve.

**files touched** `template_code/ag/operations/road/__init__.py`.

**depends on** nothing.

**decision refs** A19, B3.

**doc migration** none — A19 stays open until B3 resolves.

---

## 14. T2.9 — Port surface surgery

**status:** not started
*(merged: former T0.5, delete `union`)*

**what done means**

- `GeometryOps.union` deleted — zero callers in the repo, and `geometry_ops.py`'s own rule is that
  a method with no caller is not shipped.
- Four methods split, each pair with distinct row semantics:
  `buffer` / `buffer_dissolve`; `spatial_join` / `spatial_join_all`;
  `nearest_neighbor` / `all_neighbors`; `extract_vertex` / `extract_vertices`.
- `VertexPosition` gains `DANGLE`.
- Docstrings record that three of the four splits close a **pre-existing expressibility gap**:
  `spatial_join` cannot express 18 of 30 real call sites and `nearest_neighbors` cannot express 25
  of 28, because the port fixed the minority behaviour.

**files touched** `template_code/ag/ports/geometry_ops.py`, and every call site in
`template_code/ag/operations/`.

**depends on** nothing.

**decision refs** A5.4, A5.5, A5.6.

**doc migration** A5.4–A5.6 → `ports/geometry_ops.py`.

**must land before T4.2** — the shape declarations are written against the split surface.

---

## 15. T2.10 — `dissolve(statistics=…)` and the `ranks` fix

**status:** not started
*(merged: former T2.11)*

**what done means**

- `dissolve` takes a `statistics` parameter so a collapse can state its combining rule
  (`statistics=((RANK, MAX),)`), making A9.10's requirement expressible.
- Both `join_field(... join=ranks ...)` calls are deleted — `operations/road/__init__.py:663` and
  `:932`.
- `Network.ranks` and `ConflictResolution.ranks` handles and their `StageInput`s are deleted.
- `RANK` survives the dissolve at `:648` as a statistic rather than being restored by a join keyed
  on an id the dissolve just re-minted.
- `ROAD_RANKS` may remain a `StageOutput` as a diagnostic; nothing reads it back by id.

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/operations/road/__init__.py`, `template_code/ag/pipelines/road/n100.py`.

**depends on** nothing.

**decision refs** A9.10, A17.5, A17.6.

**doc migration** A9.10 → new ADR on identity and `02-runtime.md` §2.4. A17.5 and A17.6 retire with
the fix, except A17.6's closing paragraph, which becomes a note in `02-runtime.md` §2.4 recording
that the road pipeline has **no** natural domain-key lookup and the omission is deliberate.

**note** A17.6: removing these consumers removes a non-adjacent stage dependency, and that is a
decision rather than a side effect. Non-adjacent edges stay legal;
`derive_stage_dependencies` still computes them. What is forbidden is the **id-keyed** version. The
legitimate pattern is preserved in the building pipeline at
`pipelines/building/n100_stages.py:78`.

---

## 16. T2.4 — Parents out-param and column constants

**status:** not started
*(merged: former T2.3, the constants)*

**what done means**

- Port-owned constants exist and replace bare string literals at every call site:
  `NEAR_INPUT_ID`, `NEAR_TARGET_ID`, `JOIN_TARGET_ID`, `JOIN_SOURCE_ID`, `VERTEX_SOURCE`,
  `FEATURE_REF`, `PARENT_ID`, `CHILD_ID`. `operations/road/__init__.py` currently writes
  `key="near_fid"` and `join_key="input_fid"` as literals.
- `dissolve` takes an optional `parents: ScratchHandle | None` receiving a TABLE of
  `(PARENT_ID, CHILD_ID)` rows, one per contributing input row.
- Only `dissolve` gets the parameter. `aggregate`, `collapse_to_point`, `cluster_points` and
  `collapse_to_centerline` have no caller wanting the parent set; the signature shape is fixed so
  adding it later is uniform (B6).

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/ports/cartographic_ops.py`, `template_code/ag/operations/road/__init__.py`.

**depends on** T2.9.

**decision refs** A11.1, A12.2, B6.

**doc migration** the constants rationale → `ports/geometry_ops.py`. A11.1's parents-versus-log
distinction → the new ADR on lineage, at T4.6.

**naming** This mechanism was called *correspondence* throughout the design discussion. It is
**parents** everywhere — the parameter, the constants, the prose. `source_rows` was rejected
because `source` already means `ExternalSource` in this repository.

---

## 17. T3.1 — Native index behind the port

**status:** not started

**what done means** A port-level accessor exposes the storage format's own row index —
`OBJECTID` in a file gdb, `fid` in GeoPackage — with a contract stating it is **valid only until
this dataset is next written**. The docstring records that backends differ on stability
(GeoPackage rowid stable, Postgres `ctid` moves on update), so an adapter may have to materialise
a surrogate.

**files touched** `template_code/ag/ports/table_ops.py`.

**depends on** nothing.

**decision refs** A9.1, A9.2.

**doc migration** A9.2 → `ports/table_ops.py`. A9.1's table → the new ADR on identity and
`01-terminology.md`.

---

## 18. T3.3 — Dispatch minter-id registry

**status:** not started

**what done means** Orchestration hands each dispatched job a `minter_id` from a single
run-scoped monotonic counter, across every job in every stage. `minter_id = 0` is reserved
invalid. The counter asserts `1 ≤ minter_id ≤ 2²⁰−1`. A **dispatch registry**
(`minter_id → stage, partition_index`) is written as a run artifact and merged at fan-in alongside
the job logs. A retry reuses its job's `minter_id` rather than drawing a new one.

**files touched** `template_code/ag/orchestrator/`.

**depends on** T0.1.

**decision refs** A10.1, A10.2, A10.3, A10.4.

**doc migration** A10.1–A10.5 and A21 → a new ADR on lineage id allocation. This is where T0.1's
finding is written up.

---

## 19. T3.4 — Ingest step

**status:** not started

**what done means**

- A distinct run-scoped step, before any stage executes, copies each `ExternalSource` the run's
  selected pipelines actually read, and allocates a dense positive `lineage_id` to every source
  feature.
- Raw ids do **not** use the minter/counter layout, so ingest consumes no `minter_id`. Ingest may
  run one job per source for I/O parallelism; each draws a **disjoint range** from one run-scoped
  counter.
- The **ingest map** (`native_index → lineage_id`, per source) and the per-source range are written
  as a run artifact.
- Fan-out reads the copy, not the original, and still mints nothing.
- `Derived` inputs are untouched — they already carry ids.

**files touched** `template_code/ag/runtime/`, `template_code/ag/staging/`.

**depends on** T0.1, T3.3.

**decision refs** A10.6, A10.7, A6.6.

**doc migration** A10.6, A10.7 → the ADR from T3.3 and `02-runtime.md` §6.

**note** The copy is not for troubleshooting convenience. A map keyed on the source's native index
can only be joined while those indices are still valid, i.e. inside fan-out's download path, which
couples ingest to fan-out's implementation. The copy decouples it.

---

## 20. T3.5 — Per-job log artifact and counter checkpoint

**status:** not started

**what done means** The per-job lineage log is an output artifact written **pod-local and uploaded
on success**, never streamed to shared storage — otherwise a dead attempt's records collide with
its retry's. Midpoint restart persists the local counter's high-water mark in the checkpoint and
resumes from *n+1*. A job exceeding 2³²−1 mints fails loudly rather than wrapping into another
minter's space. If live progress is wanted it goes to a separate diagnostic channel that fan-in
never reads.

**files touched** `template_code/ag/runtime/stage_entry.py`, `template_code/ag/staging/`.

**depends on** T3.3.

**decision refs** A10.4, A10.5, A15.4.

**doc migration** A10.4, A10.5 → the ADR from T3.3; ADR-0009 amendment for the checkpoint.

---

## 21. T3.2 — Work-key API

**status:** not started

**what done means**

- A flat allocator produces `work_key_001`, `work_key_002`, … Callers never name a field.
- Tier 1 verbs exist: `allocate(input, type)`, `key.name`, `key.lookup(input)`,
  `key.carry(source, output)`, `key.where_in(ids)`. Plus a `GENERATED` sentinel.
- Keys are **operation-scoped**, swept at operation exit. A stage-level sweep runs as a backstop and
  should find nothing.
- The sweep does two jobs, and the second is the enforcement: delete registered fields from every
  declared output including TABLEs, **and fail on any field matching the naming convention that is
  not in the registry**.
- The registry records `(name, operation, dataset)` into operation metadata.
- The four verbatim "ensure the field exists and equals the OID" guards are gone —
  `railways_generalization.py:755` and `:1421`, `line_topology.py:1913` and `:1931`.

**files touched** new module under `template_code/ag/` — path TBD, `helpers/` or a peer of
`staging/`.

**depends on** T2.1 (for `where_in`).

**decision refs** A9.3–A9.9.

**doc migration** A9.3–A9.7 → the new module's docstring; A9.5 also → `02-runtime.md` §8.
A9.8, A9.9 → `04-migration.md`.

---

## 22. T4.1 — `@row_shape` types and CI check

**status:** not started

**what done means**

- `Rows(cardinality, identity, subject=… | refs=…)` exists, with `cardinality ∈ {ONE, MANY,
  GROUP}` and `identity ∈ {CARRY, MINT, FOREIGN}`.
- `@row_shape(**outputs: Rows)` attaches declarations to a Protocol method without changing its
  signature, so structural typing still holds and adapters need no decoration.
- CI check rejects, each with its specific reason in the message: an output parameter with no
  declaration; either axis missing; a `MINT` with no subject; a `FOREIGN` with no refs; a subject
  or reference naming a parameter that does not exist; and the three illegal cells —
  `MANY + CARRY`, `GROUP + CARRY`, `GROUP + FOREIGN`.
- The `MANY + CARRY` message states the primary reason: **this is the inheritance model A11.2
  rejects** — five split pieces all keeping id 1 leaves the log unable to express a partial drop.
  The grammar rule and A11.2 are the same rule stated twice.

**files touched** new `template_code/ag/ports/row_shape.py`,
`template_code/tests/unit/test_row_shape.py`.

**depends on** T2.4.

**decision refs** A12.1–A12.6.

**doc migration** A12.1–A12.4 → `ports/row_shape.py`; A12.5 → `02-runtime.md` §8.

---

## 23. T4.2 — Declare shapes across the port surface

**status:** not started

**what done means** Every output parameter of every `GeometryOps`, `CartographicOps` and
`TableOps` method carries a `@row_shape` declaration matching A12.11's table. The CI check from
T4.1 passes. `collapse_to_point` is declared `ONE + CARRY`, with the precedent stated in its
docstring: identity changes when the feature's correspondence to a real-world object changes, not
when its geometry kind changes.

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/ports/cartographic_ops.py`, `template_code/ag/ports/table_ops.py`.

**depends on** T4.1, T2.9.

**decision refs** A12.10, A12.11, A12.12.

**doc migration** A12.10–A12.12 → the port module docstrings.

**note** A12.12 records why vertex extraction is `FOREIGN` and not `MINT`, including the rejected
split into `vertices_to_points`. Keep that rationale in the docstring — it is the case people will
re-propose.

---

## 24. T4.3 — Generic lineage facade

**status:** not started

**what done means** One facade class wraps each of the three handle-bearing ports, reading
`__row_shape__` **from the Protocol** rather than from the adapter instance, so adapters need no
decoration and cannot drift. Composed in `runtime/`, with one `cast` at the composition root and a
conformance test asserting every Protocol method is reachable through the facade. Operations see
`tb.geometry` typed as `GeometryOps` and receive no injected `lineage`.

**files touched** new `template_code/ag/lineage/` package,
`template_code/ag/runtime/stage_entry.py`.

**depends on** T4.2.

**decision refs** A11.11, A11.12, A15.1.

**doc migration** A11.11 → the new ADR on lineage and `03-architecture.md` §4.

---

## 25. T4.5 — Id-map cache

**status:** not started

**what done means** A `native_index → lineage_id` map is cached **pod-scoped**, keyed on
`ScratchHandle` (frozen, hashable, `path` set `compare=False`, so a materialized copy equals its
declaration). Invalidated on any call naming the handle as an output; in-place mutators do not
invalidate. A **row-count** check per operation is the independent guard — metadata in a file gdb,
one aggregate in SQL. A mismatch drops the cache, so a stale cache is a miss and never wrong data.

**files touched** `template_code/ag/lineage/`.

**depends on** T4.3.

**decision refs** A15.3.

**doc migration** A15.3 → the lineage module docstring.

**note** Full id-set validation was rejected: it reads every id, which is the same scan as
rebuilding, so it saves the dict construction and not the I/O.

---

## 26. T4.4 — Lineage-aware `read_rows` → `write_table` pipe

**status:** not started

**what done means** `read_rows` on a lineage-bearing handle returns a private tracked iterable of
`(Row, id)` yielding plain `Row`; `write_rows` and `write_table` unwrap and stamp. The facade does
the wrapping, so adapters return plain rows and never see lineage. Writing to a scoped output with
untracked rows and no explicit `mint(parents=…)` is an **error**, not a silent skip. The four
direct pipe sites carry lineage with no call-site change:
`operations/road/__init__.py:323`, `:454`, `:543`, `:593`. The fifth, `:243`
(`_build_topology`'s `nodes`), uses explicit mint.

**files touched** `template_code/ag/lineage/`, `template_code/ag/ports/table_ops.py`.

**depends on** T4.3.

**decision refs** A12.7.

**doc migration** A12.7 → `ports/table_ops.py` and the lineage module docstring.

**note** `Row.parents` was rejected: it would spread lineage into every adapter constructing a
`Row`, change `Row.__eq__`, and give domain code a field to branch on.

---

## 27. T4.6 — Mint, edges, and the per-operation sweep

**status:** not started
*(merged: former T4.7, edge types and the sweep)*

**what done means**

- `LineageEdge(operation, kind, from_ids, to_ids)` and `JobLineageLog(minter_id, stage, edges)`
  exist. No own/context flag on either — the writer cannot know it.
- `EdgeKind` has four values, **all runtime-derived, none declared**: `TRANSFORMED` (every parent
  absent from this operation's outputs), `DERIVED` (at least one parent survives), `DROPPED` (no
  children), `CREATED` (`from_ids == ()`).
- The facade mints on `MINT` shapes, recording a **provisional** edge into a pod-local buffer.
- At operation exit the sweep reads each Out's id set and collapses the buffer to net effect.
  Backward-walk termination is **in the Ins, or surviving in an Out, or not minted this
  operation** — all three clauses. Without the middle one, `resolve_ramps` emits `(1..5) → g5` and
  `(1..5) → g9` instead of `(1..5) → g5` and `g5 → g9`.
- `DROPPED` is derived from the boundary diff and never from a port call.
- `CARRY` with no parent **fails**; it does not mint. `FOREIGN` never gets a `lineage_id` and never
  emits an edge, and a null ref column is legitimate data.
- A test covers the `resolve_ramps` multi-output shape specifically.

**files touched** `template_code/ag/lineage/`, `template_code/ag/runtime/stage_entry.py`.

**depends on** T4.3, T3.4.

**decision refs** A11.2–A11.9, A11.12, A11.14, A13.

**doc migration** A11.1–A11.10 and A11.14 → the new ADR on lineage. A11.4's authoring consequence
and A11.13 → `02-runtime.md` §2.4. A11.8, A11.9, A11.12, A13 → the lineage module docstring.

---

## 28. T4.8 — Stage-exit sweep

**status:** not started

**what done means** At stage exit within the pod, `DROPPED` is emitted for every id terminating in
a handle that no `StageOutput` names. Without it, `simplify`'s `collapsed_points` case leaves an id
in none of `O`, `T`, `D`: it is `TRANSFORMED` at the operation boundary because `collapsed_points`
is a real Out, but `ConflictResolution.collapsed_points` never becomes a `StageOutput`.

**files touched** `template_code/ag/runtime/stage_entry.py`.

**depends on** T4.6.

**decision refs** A16.2.

**doc migration** A16.2 → `02-runtime.md` §8.

---

## 29. T4.9 — Derived scope rule

**status:** not started

**what done means** Two properties are computed from the stage declaration and the operation
wiring, and they are distinct:

- **in scope** — the handle reaches a `StageOutput`. Determines whether the boundary diff runs.
- **lineage-bearing** — the declaration chain terminates in `CARRY` or `MINT`. Determines whether a
  `lineage_id` column exists.

A `FOREIGN`-terminal handle can be in scope without being lineage-bearing, and that is legal:
`SNAP_DISPLACEMENT` is exactly that. The boundary diff skips non-bearing handles, completeness
ignores them, and A13's input verification applies to lineage-**bearing** inputs only.

A plan-time check rejects a `FOREIGN`-terminal handle named as the `subject` of a downstream
`CARRY` or `MINT`. It does **not** reject a `FOREIGN` handle reaching a `StageOutput`.

**files touched** `template_code/ag/lineage/`, `template_code/ag/core/validation.py`.

**depends on** T4.6.

**decision refs** A12.9, A15.2, A15.6.

**doc migration** A15.2, A15.6 → the lineage module docstring and `01-terminology.md`; A12.9 →
`02-runtime.md` §8.

**note** A15.2's superseded form — "descends from a PROCESSING `StageInput` **and** reaches a
`StageOutput`" — broke on `DISPLACEMENT_FEATURE`, whose only ancestors are CONTEXT inputs. That
bug is why A15.6 splits the two properties instead of adding an exemption.

---

## 30. T4.12 — Mint-generation join check

**status:** not started
*(renumbered from T2.9, which depended on T4.2 and so could not sit in the T2 range)*

**what done means** A check flags any `join_field` whose join handle is separated from its input by
a `MINT` in the declaration chain — within a stage from the operation wiring, across stages from
the stage graph. An id-keyed join across a cardinality change matches nothing, because the two
sides are different mint generations.

**files touched** `template_code/ag/core/validation.py`.

**depends on** T4.2.

**decision refs** A9.10, A17.5.

**doc migration** none beyond A9.10, which migrates at T2.10.

**known limit** This catches generation mismatches, not **granularity** mismatches.
`operations/road/__init__.py:315` joins `paired.near_fid` (a vertex-row reference) against
`vertices_after.FEATURE_ID` (feature-level), which fans out under any id model. Not caught here,
and not blocking.

---

## 31. T4.13 — Lost-ref detectors

**status:** not started

**what done means** Three detectors for the A11.13 gap, where a `FOREIGN` ref column is dropped
mid-manipulation and the rebuild mints with empty parents:

- **per-operation** `CREATED` ∧ `DROPPED` co-occurrence — WARNING. Precise, fires immediately.
- **job-exit** `CREATED` ∧ `DROPPED` co-occurrence — WARNING. The net for the cross-operation case
  (extract in A, rebuild in B, same pod). Unpromoted drops include context features, giving this
  one a false-positive floor.
- **mint-site**: `mint(parents=())` in an operation that read a `FOREIGN`-derived handle — **ERROR**.
  Attribution is coarse but the combination is narrow, and the failure is bad enough for two
  independent detectors.

**files touched** `template_code/ag/lineage/`, `template_code/ag/runtime/stage_entry.py`.

**depends on** T4.6, T4.8.

**decision refs** A11.13.

**doc migration** A11.13 → `02-runtime.md` §2.4.

**failure signature this catches** the map shows the feature; the log says its parents were
removed.

---

## 32. T4.10 — Adapter parents capability

**status:** not started

**what done means** The arcpy adapter probes capability at construction with
`arcpy.GetParameterInfo("analysis.PairwiseDissolve")` rather than reading a version table, and
selects a tier: native `out_lineage_table` (Pro 3.7+), work-key synthesis through
`concatenation_separator` (Pro 3.0+, and what runs on the current 3.6 image), or declared
unsupported. Spatial reconstruction is not implemented — an unavailable method is preferable to a
silently wrong one. A plan-time check fails a stage that dissolves on a lineage-scoped handle with
an incapable adapter, before fan-out rather than in the pod.

**files touched** `template_code/ag/adapters/arcpy/`, `template_code/ag/core/validation.py`.

**depends on** T4.2.

**decision refs** A14.

**doc migration** A14 → `adapters/arcpy/` package docstring; the plan-time check → `02-runtime.md`
§8.

**open** See "found while writing this", item 3 — the plan-time check needs arcpy, and `validate()`
is specified to run without it.

---

## 33. T4.11 — Adapter conformance suite

**status:** not started

**what done means** One case per `MINT` method: run it over a known input set and assert the
reported parents match. The suite passes under **both** capability tiers, since tier 2 runs on the
current image and tier 1 later on the same code.

**files touched** `template_code/tests/` — adapter conformance path TBD.

**depends on** T4.10.

**decision refs** A14.

**doc migration** none.

---

## 34. T5.1 — Fan-in log merge and `DROPPED` promotion

**status:** not started

**what done means** Fan-in merges the K job logs and the dispatch registry. `DROPPED` is promoted
only where the dropping job owns the id:
`D = { d ∈ ⋃ D_job : owner(root(d)) == job(d) }`, with `root(d)` resolved through that job's own
log and `owner` from the fan-out assignment. `TRANSFORMED` and `DERIVED` need no ownership check —
presence in the job's declared output already witnesses it. Fan-in selection itself emits no
`DROPPED` (A6.5).

**files touched** `template_code/ag/runtime/`.

**depends on** T4.8, T3.5.

**decision refs** A16.1, A6.5.

**doc migration** A16.1 → `02-runtime.md` §8.

---

## 35. T5.2 — Completeness assertions

**status:** not started

**what done means** The three assertions run at fan-in over all objects in the stage:

```
I  = lineage ids in the stage's StageInputs (own features)
O  = lineage ids in the stage's StageOutputs
T  = { f ∈ from_ids of any edge : f ∉ O }
D  = ⋃ from_ids over promoted DROPPED edges

(1)  I − O − T − D          == ∅
(2)  O − I − ⋃to_ids(edges) == ∅
(3)  T ∩ D                  == ∅
```

`T` is computed from **set membership, not from `EdgeKind`** — kind-driven completeness is wrong in
both directions when a collapse partially consumes its parents. The docstring records that this
check can only run at fan-in with data, outside the "nothing that can fail at plan may be deferred
to the pod" layering every other check obeys.

**files touched** `template_code/ag/runtime/`, `docs/refactor/02-runtime.md` §8.

**depends on** T5.1.

**decision refs** A11.6, A16, A16.3.

**doc migration** A11.6, A16, A16.3 → `02-runtime.md` §8.

---

## 36. T5.3 — Origin-closure check and `DISPLACEMENT_FEATURE` fix

**status:** not started

**what done means** A fan-in check asserts every `from_id` in an edge belongs to an object in the
output's `origin` closure. `DISPLACEMENT_FEATURE`'s origin is corrected to include `N100_ROAD`
alongside `NVDB_ROADS` — `build_displacement_feature` consumes `roads_generalized`, and the current
declaration at `pipelines/building/n100_objects.py:55` omits it.

**files touched** `template_code/ag/runtime/`,
`template_code/ag/pipelines/building/n100_objects.py`.

**depends on** T5.1.

**decision refs** A16.4, A17.1.

**doc migration** A16.4 → `02-runtime.md` §8. A17.1 retires with the fix.

**note** Legality is safe today — `NVDB_ROADS` is already the strictest term — but the origin is
factually incomplete, and this check finds it on the first run.

---

## 37. T5.4 — Ownership-assignment verification

**status:** not started

**what done means** Fan-in recomputes the ownership assignment — a pure function of data and
partition geometry — and asserts it matches what fan-out wrote. Determinism that genuinely holds is
spent on verification rather than assumed.

**files touched** `template_code/ag/runtime/`.

**depends on** T1.4.

**decision refs** A15.4, A6.

**doc migration** A15.4 → the lineage module docstring and `02-runtime.md` §7.

---

## 38. T6.1 — Edge storage format

**status:** not started

**what done means** A storage format for the merged edge set, chosen for the resolver rather than
for readability. No materialised ancestry — ancestry sets compound without bound through repeated
dissolves. Sized against A15.5's worst case: an aggregating collapse produces one edge whose
`from_ids` is every input row, so volume is proportional to input there, not to change.

**files touched** `template_code/ag/lineage/`.

**depends on** T5.1.

**decision refs** A15.5, A20.

**doc migration** A15.5 → the new ADR on lineage.

---

## 39. T6.2 — Lineage walk API

**status:** not started

**what done means** An API over the edges answering both directions: given a raw id, walk forward
to its current identity or the operation where it was dropped; given a generated id, walk back to
its raw ancestors. **Forward walks return a set, not a single value** — a feature consumed by a
second pipeline gets a forward edge there and continues in its own, so branching is normal and the
contract says so.

**files touched** `template_code/ag/lineage/query.py`.

**depends on** T6.1.

**decision refs** A20.

**doc migration** A20 → `ag/lineage/query.py`.

---

## B2 — Q-C investigation `[INDEPENDENT]`

**status:** not started

**what done means** The river strahler code is read and Q-C is closed: either `GraphOps` stays
pure-value as `ports/graph_ops.py` currently proposes, or it becomes dataset-aware. Either way
`NodeId` becomes `NewType("NodeId", int)` with the docstring recording why `NewType` is right here
when `core/types.py` chose `TypeAlias` for its strings — node ids have one construction site.

**files touched** `template_code/ag/ports/graph_ops.py`,
`docs/refactor/03-architecture.md` §9.

**depends on** nothing.

**decision refs** A3, B2.

**doc migration** A3 → `ports/graph_ops.py` and `03-architecture.md` §9; resolves B2.

**note** Deferring stays cheap: if the answer is dataset-aware, only `_build_topology` changes and
no operation signature does.

---

# Found while writing this

Open items noticed during transcription. **None of these are resolved.** They are listed rather
than decided, per the constraint on this pass.

1. **A19 and A20 have `destination: TBD`.** Published identity has no ADR and no settled design
   (B3). The lineage query module does not exist, so A20's home is provisional.

2. **T1.3 and T4.11 have no test directory.** `tests/invariance/` is named in
   `01-terminology.md` as a driving adapter but does not exist, and there is no adapter conformance
   path. Someone has to choose.

3. **A14's plan-time capability check may not fit `validate()`.** `02-runtime.md` §8 specifies
   validation as running with "no cluster, no credentials, no data, no ArcPy" — but the capability
   probe calls `arcpy.GetParameterInfo`. Either the check lives somewhere else, or `validate()`
   takes a pre-probed capability record as an argument. Not resolved.

4. **A16's `I` is underspecified for CONTEXT inputs.** It reads "lineage ids in the stage's
   StageInputs (own features)", but ownership is defined for partitioned processing inputs, not for
   context. A15.2 deliberately dropped the PROCESSING clause from *scope*; whether `I` should keep
   it is a separate question and was never asked.

5. **"Registry" is now overloaded three ways.** `StageRegistry` (existing), the dispatch registry
   (A10.3), and the work-key registry (A9.5). `01-terminology.md` §2 already has a collision entry
   for the word.

6. **T3.2's module has no home.** The work-key API is not a port, not an operation and not a
   helper in the current sense. `helpers/` or a new peer package — undecided.

7. **A7's `PartitionIterator` changes have no doc destination.** They are transitional and retire
   with the file, but if the shadow experiment produces a durable technique it should be written
   down somewhere before `partition_iterator.py` is deleted.

8. **`extract_vertex` (ONE + FOREIGN) has exactly one known caller**, `mst_loop.py:153` with
   `point_location="MID"`. That is enough to justify the split under A5.6, but it is thin, and the
   `START` / `END` positions may have no caller at all.
