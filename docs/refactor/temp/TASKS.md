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
**and** every A-item in its `doc migration` line has:

1. been moved to its `destination:` — an ADR, a module or class docstring, `02-runtime.md`,
   `03-architecture.md`, or the validation vocabulary;
2. been struck in DECISIONS.md with a pointer to where it landed — do not leave a copy in both
   places, because two copies diverge; **and**
3. had **every `01-terminology.md` entry citing it repointed to that destination.**

Step 3 is not housekeeping. The glossary's authority column cites A-ids, and those A-ids live only
here — so without it the citations decay silently as temp empties, and the completion test would
otherwise pass at the exact moment every one of them becomes a dead reference to a deleted
directory.

**Grep after editing, not only before.** An edit can look applied and still fail: a phrase that
wraps across a line break is no longer greppable, so a term you just added is not findable by the
next person or by the checks below. This has already happened once, to the `mint generation`
addition in A9.10.

**Completion test.** `docs/refactor/temp/` is deletable when:

1. every task below is `done`; **and**
2. every A-item has landed at its `destination:`, whether it rode on a task or not; **and**
3. every B-item is either resolved into an A-item or promoted into a real document as a stated
   open question; **and**
4. **no `01-terminology.md` entry cites an A-id any more** — every authority column points at a
   real document. Without this clause the test passes precisely when the glossary's citations all
   become dead references.

**Run `python3 docs/refactor/temp/check_consistency.py`** rather than checking by eye. It covers
clauses 1, 3 and 4 mechanically, plus dependency ordering and both directions of the
terminology/DECISIONS cross-reference. It exits non-zero, so it can go into CI unchanged, and it
dies with this directory. Every check in it was added because it found a real defect — the
docstring says which.

**Not every A-item rides on a task.** A1.1, A1.2 and A1.3 are guidance — code organisation,
operation granularity, and `Toolbox` as an explicit parameter — with nothing to build. They
migrate through **T7.1**, a documentation-only task, so that the test above stays mechanical
rather than needing a judgment call about which decisions "count".

If temp still has content and every task is `done`, something did not migrate. If a task is
`done` and its A-items are still here, the task was closed early.

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
| 1 | T0.1 | **GATE** — 64-bit storage capability | scheduled (slice 0) |
| 1b | T0.6 | **GATE** — disk-backed map cost, and copy-vs-map cost | (a) scheduled (slice 0); (b) blocked — B9 |
| 1c | T7.4 | Layering and private-access checks, both platforms `[INDEPENDENT]` | **done** (slice 0) |
| 2 | T0.2 | Per-feature id in `PartitionIterator` | not started |
| 3 | T1.1 | Shadow centroid selection and comparison | not started |
| 4 | T1.3 | Synthetic transform suite | not started |
| 5 | T1.4 | **GATE** — national-scale shadow run | not started |
| 6 | T2.1 | Structured `Attr` `[INDEPENDENT]` | not started |
| 7 | T2.7 | `Row` slots and value-type docstrings `[INDEPENDENT]` | not started |
| 8 | T2.5 | Linear referencing on `Geometry` `[INDEPENDENT]` | not started |
| 9 | T2.6 | Raster `sample_at` `[INDEPENDENT]` | not started |
| 10 | T2.2 | `update_rows` | not started |
| 11 | T2.8 | `join_field` unique-key contract | not started |
| 12 | T0.3 | Fix `resolve_ramps` inversion | not started |
| 13 | T0.4 | Rename the published `objid` mapping | **blocked** — B9 |
| 14 | T2.9 | Port surface surgery — splits, `DANGLE`, delete `union` | not started |
| 15 | T2.10 | `dissolve(statistics=…)` and the `ranks` fix | not started |
| 16 | T2.4 | Parents out-param and column constants | not started |
| 16b | T2.12 | `TableOps.create_workspace` | not started |
| 16c | T2.13 | Call identity: per-call workspace and scope namespace | not started |
| 17 | T3.1 | Native index behind the port | not started |
| 18 | T3.3 | Dispatch minter-id registry | not started |
| 19 | T3.4 | Ingest step and cross-run re-allocation | not started |
| 20 | T3.5 | Per-job log artifact and counter checkpoint | not started |
| 20b | T3.6 | Lineage retention alongside products | not started |
| 20c | T3.7 | Foreign-id guard | not started |
| 21 | T3.2 | Work-key API | not started |
| 22 | T4.1 | `@row_shape` types and CI check | not started |
| 23 | T4.2 | Declare shapes across the port surface | not started |
| 24 | T4.3 | Generic lineage facade | not started |
| 25 | T4.5 | Disk-backed id map | not started |
| 26 | T4.4 | Lineage-aware `read_rows` → `write_table` pipe | not started |
| 27 | T4.6 | Mint, edges, and the per-operation sweep | not started |
| 28 | T4.8 | Stage-exit sweep | not started |
| 29 | T4.9 | Derived scope rule | not started |
| 30 | T4.12 | Mint-generation join check | not started |
| 31 | T4.13 | Lost-ref detectors | not started |
| 32 | T4.10 | Adapter parents capability | not started |
| 33 | T4.11 | Adapter conformance suite | not started |
| 33b | T4.14 | Dissolve parents track (B17) `[PARALLEL]` | not started |
| 34 | T5.1 | Fan-in log merge and `DROPPED` promotion | not started |
| 35 | T5.2 | Completeness assertions | not started |
| 36 | T5.3 | Origin-closure check and `DISPLACEMENT_FEATURE` fix | not started |
| 37 | T5.4 | Ownership-assignment verification | not started |
| 38 | T6.1 | Edge storage format | not started |
| 39 | T6.2 | Lineage walk API, with boundary-crossing and named degradation | not started |
| 40 | T7.1 | Documentation-only migration (A1.x) | not started |
| 41 | T7.2 | `LineageRoot` → `OriginRoot` rename `[INDEPENDENT]` | **done** (slice 0) |
| 42 | T7.3 | Consistency checks `[INDEPENDENT]` | **done** |
| 43 | T7.5 | `run_partition_optimization` default bug `[INDEPENDENT]` | not started |
| 44 | T7.6 | Legacy lint baseline: undefined names `[INDEPENDENT]` | not started |
| 45 | T7.7 | Legacy lint baseline: the remaining entries, per directory `[INDEPENDENT]` | not started |
| — | B2 | Q-C investigation `[INDEPENDENT]` | not started |

---

## 1. T0.1 — GATE: 64-bit storage capability

**status:** scheduled — slice 0, 2026-09-22. Not run. **Owner and date: <NAME, DATE>.**

**Run sheet** (prepared in slice 0; the script and the cases are as written below).

- *Image:* `ghcr.io/kartverket/arcpy-linux:12.0`, the `base` stage of `Dockerfile`. Record the
  digest the run used (`docker inspect --format '{{index .RepoDigests 0}}' <image>`) in the
  finding, per case 11.
- *Data:* a directory on the Linux filesystem (a named volume or WSL ext4), not a bind-mounted
  Windows path; `--workdir` points into it. Case 11 also needs `--archive-gdb`, a geodatabase
  created by the pipeline's archive path.
- *Commands*, from the repository root, the script copied into the container by `COPY . /app`:

  ```
  docker build --target base -t ag-gate .
  docker run --rm -v ag_gates:/data ag-gate \
      python docs/refactor/temp/t0_1_bigint_gate.py --workdir /data/t0_1 \
      --image-ref ghcr.io/kartverket/arcpy-linux:12.0 \
      --archive-gdb /data/t0_1/archive_probe.gdb \
      2>&1 | tee docs/refactor/temp/logs/<YYYYMMDD_HHMMSS>_t0_1_bigint_gate.txt
  ```

  A first pass with `--skip-large` gives every case but the 10^6 concatenation group in
  minutes; the full run then adds that one case. `--only <case>` reruns a single case.
- *Where the finding goes:* the raw log under `docs/refactor/temp/logs/`, and the written
  finding as `docs/refactor/temp/findings/t0_1_bigint_gate.md`, stating whether
  `FieldType.BIGINT` is viable, the per-tool type-survival table, and the answers to the "if
  this fails" branches. It resolves B1 into an A-item and is consumed by slice 2a.
- *Windows Pro cross-check* (optional): the same command under an ArcGIS Pro Python
  environment, with its own log; name any divergence in the finding.

**what done means**

Twelve cases run against a file geodatabase **created the way the pipeline creates them**, results
recorded in a short written finding. Cases 2–4, 6–9 and 11 exist because the original five could
all pass while the field is broken. The concatenation group-size case is there for a different
reason: A14's tier 2 is what runs on the current image, and this environment is already being stood
up.

1. Write a value just under 2⁵³ — passes, reads back unchanged.
2. Write **2⁵³ + 1**, not 2⁵³ — **recorded whether it errors or silently coerces.** This
   determines whether a runtime guard suffices or a static one is required. The value matters:
   **2⁵³ is exactly representable as a float**, so a float-coercing path returns it unchanged and
   the case passes while proving nothing. Note what this case is *for*: 2⁵³ + 1 is outside anything
   A10.1's layout produces (maximum magnitude 2⁵² − 1), so it tests the **storage guard sitting
   behind the allocator's own bound checks**, not the range real ids occupy.
3. Round-trip through `write_rows` → `read_rows`, asserting **`type(value) is int`** and not only
   equality. `4503599627370495.0 == 4503599627370495` is `True`, so an equality-only assertion
   passes on a value that has already been through a float. The type assertion is not about value
   loss — it catches **a float path reaching integer decode arithmetic**, which is where
   T3.7(b)'s `minter_id` extraction breaks. Batching also puts the coercion boundary further from
   the domain code that produced the value, so a write-then-read test is not sufficient either.
4. **Typical generated ids, not only extremes.** `minter_id ≥ 1` means every generated id has
   magnitude **≥ 2³²** (A10.1's layout), so any 32-bit path corrupts *all* of them while small raw
   ingest ids pass unharmed. Extremes alone do not cover this: it is the ordinary case that
   breaks. Covers a LONG output schema, an `int32` dtype, and a where-clause literal parsed as
   int32.
5. Predicate-filter on the field.
6. **The type-survival case.** A `CARRY` shape means the field rides through an operation
   untouched, so every `ONE + CARRY` row in A12.11 is a tool that must preserve the field's
   **type**, not only its value. **No Esri documentation settles any of this**, which is why it is
   a test.

   The list is derived from that table, with the arcpy tool the adapter is expected to compile to.
   **The arcpy adapter implements none of these yet** — `adapters/arcpy/` holds only
   `predicates.py` — so these are intended mappings, and any method the adapter later compiles
   differently has to be re-tested. T4.11 is where that stops being a manual obligation.

   | port method | expected arcpy tool | what to record |
   |---|---|---|
   | `map_fields` | `ExportFeatures` **with `FieldMappings`** | type |
   | `merge` | `Merge` **with `FieldMappings`** | type |
   | `copy` | `CopyFeatures` | type |
   | `select` | `Select` | type |
   | `buffer` | `PairwiseBuffer` | type |
   | `simplify` | `SimplifyLine` / `SimplifyPolygon` | type |
   | `smooth` | `SmoothLine` / `SmoothPolygon` | type |
   | `centroid` | `FeatureToPoint(point_location="CENTROID")` | type |
   | `point_on_surface` | `FeatureToPoint(point_location="INSIDE")` | type |
   | `collapse_to_point` | `FeatureToPoint` | type |
   | `convex_hull` | `MinimumBoundingGeometry(geometry_type="CONVEX_HULL")` | type |
   | `select_network` | no single tool — an adapter-composed selection | covered by the rows for the tools it composes |
   | `densify` | `Densify` — in place | n/a by construction |
   | `snap` | `Snap` — in place | n/a by construction |
   | `make_valid` | `RepairGeometry` — in place | n/a by construction |
   | `propagate_displacement` | `PropagateDisplacement` — in place | n/a by construction |
   | `displace_features` | `ResolveRoadConflicts` / `ResolveBuildingConflicts` — in place | n/a by construction |
   | `simplify.collapsed_points` | the tool's derived point output | **presence; if absent, a native-index reference column**; then type |
   | `displace_features.displacement` | the tool's displacement output | **columns, mapping shape**, then presence and type — see B11 |
   | `select_network.dropped` | the complement selection | covered by the rows for the tools it composes |

   **`map_fields` runs first.** It is `ONE + CARRY` under A12.11a, it goes through field mappings
   where a type change is most likely, and it is the exact call B9(d) is about. Note the tool:
   **Feature Class To Feature Class is deprecated in favour of Export Features** — confirmed on the
   tool page, which states the replacement without naming the version — so test `ExportFeatures`,
   the one the adapter will use.

   **The in-place editors are "n/a by construction"**: they modify geometry on an existing table
   and create no new schema, so there is nothing for a field to be re-typed into. Confirm cheaply;
   do not spend the afternoon there. The three cartography tools state it in the same words —
   *"This tool does not produce output layers... it alters the geometry of the source feature
   classes of the input layers"* — which is also why `displace_features`' only new artifact is its
   displacement output.

   **For the three derived outputs, record whether `lineage_id` is present at all, before its
   type.** A12.11 declares them `ONE + CARRY`, which assumes the tool copies the input's attributes
   onto the secondary output. Some arcpy secondary outputs carry only a native-id reference back
   to the input instead. If any of these do, **the `CARRY` declaration contradicts the data and
   that output should be `FOREIGN`**, with the adapter translating the reference — a finding
   against A12.11, not merely a tool quirk, and it belongs in the written finding as such.

   **The tool pages already predict the `collapsed_points` answer, checked 2026-09-14.** Both
   `SimplifyLine` and `SimplifyPolygon` say
   *"The output point feature class will not contain these fields"*, meaning the input's fields, so `lineage_id` is expected to be absent. Neither
   page names a reference column on the points; `InLine_FID` and `InPoly_FID` are documented on
   the main output only. `SimplifyLine` stores *"the endpoints of lines that are smaller than the
   spatial tolerance"*, which may mean two points per collapsed line. And `SimplifyPolygon` emits
   points for *"any polygons that are removed because they are smaller than the minimum area"*,
   which answers T4.2's pre-check from the documentation. The case still runs, because
   documentation is not behaviour. See B16.

   `PairwiseDissolve` is **not** in scope — `GROUP + MINT`, so nothing is carried through it.

   **Record per tool: preserved; or downcast to what; and whether an adapter-level fix restores it**
   — an explicit field mapping declaring BigInteger output, for instance. Severity depends on which
   type it became; see **if this fails**.
7. **The overlay-duplicate case**, in two tools. `Intersect` with `lineage_id` present on **both**
   inputs, and **`JoinField` with a lineage-bearing join table**. Separate from case 6 because the
   question is not type survival but **whether a duplicate appears and under what name**. ArcPy is
   likely to suffix rather than error.

   Two tools rather than one because B10's duplicate rule is **adapter-declared**, and a rule
   generalised from a single tool is not a rule. `JoinField` is also the in-place route T2.8
   flagged, so it is the case a domain call is most likely to hit. **The finding states whether
   the two agree.** If they do not, the adapter needs a naming rule **per tool** rather than one
   per backend, and B10 has to say so.
8. **`JoinField` with a BIGINT key.** T2.2, fan-out in T3.4 and T4.5's Path A all join on it.
   Distinct from case 7: this one is about the key's type, that one about the carried field's name.
9. **The `TableToNumPyArray` dtype for a BIGINT field**, recorded verbatim. That is T4.5's Path B
   build route, and A15.3's packed layout assumes `int64`.
10. File-geodatabase version: community reports say a target fgdb at version 10.0 or below rejects
    the Pro 3.2 field types, while the docs say the fgdb version has not changed since 10.0.
    Ambiguous enough to test rather than reason about.
11. **The exact ArcPy build and image reference**, recorded. If the Windows Pro cross-check below
    is run, record its build too and name any divergence between the two. Test the **archive
    creation path** as well as scratch — B9 may put `lineage_id` on the archived product, and an
    archive written by a different code path is a different test.
12. **The concatenation group-size case.** Measures the cost and completeness of a `CONCATENATE`
    statistic over one large group — 10⁵ and 10⁶ collinear segments dissolving to one part — so
    that any proposal to carry parents through a concatenated text cell is judged on numbers.
    Record per size: whether it truncates silently, errors, or grows; the output field's type and
    declared length; the string length; parsed tokens against the group size; whether the parsed
    set equals the input set; elapsed time added over the same dissolve without statistics.

    **Measured on Pro 3.7.2, 2026-09-15:** complete at both sizes, 46 s added at 10⁵ and 7,841 s at
    10⁶, and under single-part output the statistic is computed per key, not per output part
    (`temp/findings/n1_correspondence.md` §3.8, §3.9). CONCATENATE is retired (A14.1); the case
    stays so the number is reproducible. The TEXT-key variant is **not** re-measured: the 15,930 s
    figure from the dry run is dropped rather than confirmed, since nothing depends on it.

**Where it runs.** T0.1 is a one-off gate, not a CI step, and it runs **in the Linux production
image**. That is the environment whose results count: production is Linux, and field-type
behaviour is exactly the kind of thing that can differ between builds. **Windows Pro is an
optional cross-check**, useful as a divergence detector since the team develops there, but a pass
on Windows Pro does not substitute for a pass in the image.

Esri documents the 53-bit limit, and says values outside it error in Pro while in other clients
they may be rounded and break functionality:
<https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm>.
That is the documented behaviour; cases 2, 3, 6 and 7 check what this build actually does.

The finding states whether `FieldType.BIGINT` is viable, and if not, which fallback is chosen.

**files touched** a throwaway script, `docs/refactor/temp/t0_1_bigint_gate.py` (written, not yet
run), plus a written finding in `docs/refactor/temp/`.

**depends on** nothing.

**decision refs** A10.1, A12.11, A12.11a, A14, A15.3, A15.5, B1, B9, B10, B11, B16.

**doc migration** none — this resolves B1 into an A-item, which is then written into the new ADR
on lineage id allocation by T3.3.

**if this fails**

If file gdb cannot hold a 53-bit integer, A10.1's layout does not survive as written. The fallback
is a text field (works everywhere, slower joins) or two LONG columns (int performance, compound
predicates). **Either changes the declared field type at every call site that stores a
`lineage_id`** — a domain-visible schema change, not an adapter swap. Affected: T3.4, T3.5, T4.1,
T4.2, T4.3, T4.6, and every later task. This is why it is first despite being small.

**If a carrying tool changes the type (case 6), severity depends on which type it became.** The two
outcomes are not the same failure and must not be recorded as one:

- **LONG, or any 32-bit type — a blocker.** Every generated id has magnitude ≥ 2³², so this
  corrupts *all* of them while leaving small raw ingest ids intact, which is the shape that makes
  it survive a casual test. **It escalates to the TEXT / paired-LONG decision only if the adapter
  cannot fix it** — an explicit field mapping declaring BigInteger output is an adapter change, not
  a schema change, and should be tried first. If it does escalate, **the fallbacks have to pass
  the same carrying tools before they are compared**: TEXT can be truncated by a field mapping's
  length, and paired LONG only works if both halves are carried together by every tool in the
  table. A fallback assumed to pass is the same mistake one level down.
- **DOUBLE — an adapter-level fix, not a fallback trigger.** It is **lossless for every id
  A10.1's layout can produce**; that is exactly what the 53-bit budget buys, so there is no value
  corruption to find. What it breaks is **integer arithmetic**: `>>` and `&` raise `TypeError` on a
  float, and numpy bit operations reject `float64`. That is T3.7(b)'s `minter_id` extraction, and
  it fails at the guard rather than in the data.

**If a derived output has no `lineage_id` (case 6), what follows depends on whether a native-index
reference is there instead.** The ids axis is semantic — A12.10's test is *ids change when the
feature stops standing for the same real-world object, not when its geometry kind changes* — but
semantics only choose between declarations the data can support:

- **`lineage_id` absent, reference column present.** `CARRY` is still achievable: the port reports
  the native correspondence and the facade stamps from it (A11.11). The obligation falls on the
  adapter or port, and T4.11 is where it gets tested.
- **Neither present, on `simplify.collapsed_points`.** This can be an adapter implementation
  choice rather than a finding against A12.11, because the output has a second source. Collapsed
  features are the input rows missing from `simplify`'s main output, which is `ONE + CARRY` and
  carries `lineage_id`: the adapter derives them by set difference on `lineage_id` between input
  and main output, then converts those rows to points. They keep their attributes, so `CARRY`
  holds by construction — no spatial synthesis and no `NONE`. It is the boundary diff's own
  mechanism, reused, and it depends on the main output carrying `lineage_id`, which `simplify`'s
  own row in case 6 already tests.

  **It is only an adapter choice if the port contract defines `collapsed_points` precisely**, and
  the two routes do not agree by default. The derivation equals the tool's output only if **every**
  row missing from the main output is a collapse — check whether `SimplifyPolygon`'s minimum-area
  removal emits points, because if it drops rows for other reasons the derivation labels those
  collapsed too. The routes also place the point differently: the tool at the collapse location,
  the derivation at a centroid or inside point. So the contract must say *every input row absent
  from the main output, at a stated point rule*; the derivation then **is** the contract and the
  tool route has to match it. **That definition belongs in `simplify`'s docstring, written at
  T4.2.**
- **Neither present, with no alternative source.** *Then* it is a finding against A12.11: `CARRY`
  has nothing to stamp from and `FOREIGN` needs refs, so neither is declarable. Today the only
  output in this position is `displace_features.displacement`.

**`displace_features.displacement` is not decided here.** Both its axes are open, including the
possibility that its mapping shape has no legal cell at all. **See B11**, which this case feeds
rather than answers.

**The concatenation case is answered.** It neither truncated nor errored; it was over budget by
two orders of magnitude and per-key rather than per-part, which retired the mechanism (A14.1, B17).
The `COUNT`-beside-`CONCATENATE` detector this paragraph once proposed for T4.10 is moot.

**If `collapsed_points` were ever redeclared `FOREIGN`, the cost is larger than one table row.**
`FOREIGN` is terminal for lineage (A12.9), so the id would not continue through it — and
`collapsed_points` is the **worked case in A16.2** and the entire premise of **T4.8**'s stage-exit
sweep. Both would have to be rewritten around a different example, or the sweep would be solving a
problem that no longer exists. Name that cost before taking the option.

---

## 1b. T0.6 — GATE: disk-backed map cost, and copy-versus-map cost

**status:** (a) scheduled — slice 0, 2026-09-22, not run; (b) blocked — B9.
**Owner and date for (a): <NAME, DATE>.**

**Run sheet for (a)** (prepared in slice 0; the measurement script is still to be written, as
a throwaway under `docs/refactor/temp/`, against the packed layout A15.3 specifies and the
`JoinField` path).

- *Image:* `ghcr.io/kartverket/arcpy-linux:12.0`, the `base` stage of `Dockerfile`; record the
  digest, and the kernel and cgroup version of the host (`uname -r`,
  `stat -fc %T /sys/fs/cgroup`) and of the production cluster, and name any mismatch.
- *Data:* the three sizes (a 70K handle, the national road network, the largest input
  available) staged onto a Linux volume, never a bind-mounted Windows path.
- *Memory:* `--memory` set to the production pod limit, `<POD_LIMIT — obtain from the
  platform team; not recorded in the design record>`, with the WSL2 VM cap above it. Report
  peak memory as the cgroup accounts it (`memory.peak` under cgroup v2), not RSS.
- *Command shape*, one run per size and per path:

  ```
  docker run --rm --memory=<POD_LIMIT> --memory-swap=<POD_LIMIT> -v ag_gates:/data ag-gate \
      python docs/refactor/temp/t0_6_id_map_cost.py --workdir /data/t0_6 \
      --subject <path in /data> --path packed|joinfield [--cache-bytes N] \
      2>&1 | tee docs/refactor/temp/logs/<YYYYMMDD_HHMMSS>_t0_6_<size>_<path>.txt
  ```

  For the packed path, sweep `--cache-bytes` on the largest map until lookup thrashes
  (measurement 3).
- *Where the finding goes:* the raw logs under `docs/refactor/temp/logs/`, and the written
  finding as `docs/refactor/temp/findings/t0_6_id_map_cost.md`: the rows-versus-build-time
  curve for both paths, whether peak memory is flat, the cache size at which lookup thrashes,
  that the joined `lineage_id` arrives as BigInteger, and the in-memory budget A15.3 declares.
  It is consumed at T4.5 and, for the resource-ceiling method, at 2a.

**what done means**

Two measurements on real data. Both are "measure before building on an assumption", and neither
needs any of the new code to exist.

**Not an afternoon any more.** That estimate predates the validity conditions below. (a) now means
staging the national inputs onto a Linux volume, running at the production pod limit rather than a
comfortable one, sweeping cache sizes on the largest map, and getting the production cluster's
kernel and cgroup version from someone with cluster access, and running `JoinField` at the same
three sizes. Budget **a few days for (a)**, an estimate dominated by data staging and the cache
sweep rather than by the runs themselves. `JoinField`'s runtime at national scale is unknown;
revise the estimate once the smallest size has been timed. (b)
waits on B9 and is not in that budget.

**(a) The disk-backed id map.** No facade required — this measures the mechanism A15.3 specifies,
not the dict it replaced. **The dict is not a candidate**, so do not benchmark it as one: it was
rejected for having an unbounded worst case, not for being slow.

Three numbers for the packed path, plus the `JoinField` path below, and the task is not done
without all of them:

1. **A rows-versus-build-time curve**, not a single pass/fail on one input. Several sizes spanning
   the real range — a 70K handle, a national road network in the low millions, and the largest
   input available. One point sets nothing, and "provisional" then becomes permanent by default.
2. **Peak memory as the cgroup accounts it** for the packed path, confirming it is flat across that
   range rather than a function of rows. This is the property A15.3 asserts; unmeasured, it is only
   an assertion. Not RSS: see the metric paragraph below.
3. **The block-cache size at which lookup starts thrashing** on the largest map, with the subject
   read in map order as A15.3 requires. This decides whether the packed path is viable at all, and
   nothing else in the plan would catch a cache sized too small.

**And the `JoinField` path, at the same three sizes.** A15.3 names it the preferred ArcPy form:
no Python-side map at all, the translation done by a `join_field` against a temp table. Measuring
only the packed path would give a fallback three numbers and leave the path production runs
unmeasured. Materialise the map as a file-geodatabase table, join it onto the subject keyed on the
subject's **OBJECTID**, and record:

- **build time** against rows, as for measurement 1 — map-table write plus the join, reported
  separately so the join's own scaling is visible;
- **peak memory as the cgroup accounts it**, as for measurement 2. "Bounded by the GP tool" is an
  assertion in A15.3 too, and this is where it gets a number;
- **that the joined `lineage_id` arrives as BigInteger** — type survival through the one tool this
  path depends on.

Measurement 3 is packed-only: `JoinField` has no block cache to size. **The finding reports both
paths side by side.**

**If `JoinField` holds** — build time acceptable across the curve and memory flat — then on the
arcpy backend the packed path's numbers **stop being a gate input**: nothing production runs
depends on them. A15.3 still keeps both paths permanent, and the review's F24 proposes deferring
the packed path until a backend needs it; a holding `JoinField` is what makes that proposal live.
It is **not** decided here — F24 is a separate design conversation.

**Outputs**, split by what the finding is authoritative for:

- **The in-memory budget**, a direct output: A15.3's declared constant, provisionally 64 MB.
  Memory behaviour is what this environment measures authoritatively, so the number is used as is.
- **The resource ceiling, as a shape and a method, not a value.** The curve's shape, plus the
  procedure for turning a build-time tolerance into a row count. The value itself is **calibrated
  on the pod at construction** per A11.4a, because absolute build time is only indicative here.

**Where it runs, and which metric it reports.** Production is the **Linux image**; the team
develops on Windows. T0.6 is a one-off gate, not a CI step.

The metric has to be the one the platform kills on: a **cgroup** limit, which is what Kubernetes
evicts and OOMKills against — not a Windows working set, which is a different accounting of a
different thing. Within the cgroup, **mmap-ed pages may be charged differently from an explicit
fixed-size read buffer**; measure that difference rather than assuming the two are
interchangeable, since A15.3's entire claim is about a bounded buffer.

All three measurements run in the image, which has ArcPy, under `docker run --memory=…` — one
environment, no split. The conditions that make the result valid:

- **Test data on the Linux filesystem** (a named volume or WSL ext4), not a bind-mounted Windows
  path. The file-sharing layer would distort both build time and thrash.
- **`--memory` set to the production pod limit**, not a comfortable number. The kernel page cache
  is charged to the cgroup, and a generous limit lets it hide an undersized block cache — the
  failure measurement 3 exists to catch. The WSL2 VM's own memory cap must be above this limit.
- **Record the image reference, and the kernel and cgroup version** in both the test environment
  and the production cluster. Name any mismatch; v1 and v2 account for page cache differently.
- **Report the curve's shape and whether peak memory stays flat**, not absolute times. Dev
  hardware is not the pod's.

"Authoritative" is scoped accordingly: **authoritative for memory behaviour and scaling,
indicative for absolute build time.** A11.4a calibrates the resource ceiling at pod construction,
so no absolute number from here is used directly.

**(b) Copy versus map-only.** **Waiting on B9** — if the archived product does not carry
`lineage_id`, the map-only branch is unreachable, every cross-run input is copied, and this
measurement has no subject. Do not run it before B9 answers; (a) does not depend on B9 and
proceeds.

Bytes and wall-clock for copying a national N50 product, against bytes and wall-clock for
producing its four-column ingest map over the same dataset.

This is the number A24.1's second row rests on. The expected ratio is large — the map moves two
integer columns where the copy moves geometry plus every attribute — but it has never been
measured, and an N100 run takes that branch on **every execution**, so a wrong assumption here is
paid continuously rather than once.

**Before (b) runs, revise the comparison.** As written above it compares copy against map
production only. The map-only branch also pays fan-out's join over the same dataset, and
T3.7(a)'s check, on every run. Not redesigned now; that waits for B9.

**files touched** a throwaway script plus a written finding in `docs/refactor/temp/`.

**depends on** (a) nothing; (b) B9.

**decision refs** A15.3, A15.1, A24.1, A11.4a, B9.

**doc migration** none — (a) confirms or replaces A15.3, which migrates at T4.5; (b) confirms
A24.1's copy rule, which migrates at T3.4.

**if this fails**

*(a)* Three distinct failures, with different consequences:

- **Build time grows unacceptably with rows** — the map itself is the wrong mechanism, not its
  storage. T4.5 changes shape, T4.3 and T4.6 inherit whatever replaces it, and A15.1's "mint
  always, scope only the diff" cost model needs rechecking.
- **Peak memory, as the cgroup accounts it, tracks row count** — the packed layout is not doing
  what A15.3 claims; find out why before building on it, because the bounded-memory property is the entire justification for
  accepting the time cost.
- **`JoinField` does not hold** — build time grows badly with rows, or its memory tracks row count.
  Then the packed path is not a fallback but the production path on arcpy, and measurements 2 and
  3 carry the whole gate. Record the failure shape; `AddJoin` followed by `CalculateField` is the
  usual alternative join form, and is worth one run before concluding that arcpy has no join path.
- **The cache must be large to avoid thrashing** — either the sequential-access construction is
  not holding (check the read loop honours map order, per A15.3) or the packed path is unviable
  and `join_field` becomes mandatory rather than preferred, which makes T3.1's join-key contract
  a blocker rather than a nicety.

*(b)* If map-only is not materially cheaper than copying, A24.1's second row collapses into the
first and every input is copied. That is a simpler design, not a broken one — but it makes ingest
a full national copy on every run, which changes T3.4's cost profile and is worth knowing before
building the join path in fan-out.

**why it is a gate and why it is here** This was specified before the design was written and was
missing from the first version of this plan. Left unmeasured, the number surfaces during T4.5
implementation — after T4.3 and T4.4 have been built against an assumption that may not hold. It
costs an afternoon now and a rewrite later.

---

## 1c. T7.4 — Layering and private-access checks, run on both platforms `[INDEPENDENT]`

**status:** done — slice 0, 2026-09-22. Landed as `.importlinter` at the repository root (rebuilt
against `findings/project_tree.md` §6, twenty-four contracts over eighteen rows, each broken once
with a probe module), `[tool.ruff]` `SLF001` scoped to `src/ag/generalization/`, the `arcpy`
marker with `tests/conftest.py`, `.pre-commit-config.yaml` as the one list of checks, and
`.github/workflows/checks.yml` running it on both runners. The package-coverage meta-check is
row 1's `exhaustive = true`, which import-linter 2.15 supports, so no hand-written check exists.
The `ag.helpers` row of the template's contract became row 2 of the new file
(`helpers` below `operations` inside `ag.generalization`). Text below is as written before the
task ran.

**what done means** Three checks that **fix existing configuration**. They were found while
writing B10 but do not resolve it and do not depend on it; B10's facade-side pieces stay with
T4.3. Placed early because none of this needs lineage, the gap is live today, and `SLF001` is
clean now, which is the cheapest moment it will ever be to turn on.

- **`ag.helpers` added to the `layers` contract** in `template_code/.importlinter`, between
  `ag.operations` and `ag.staging`. B10 break-tested this: a `helpers` module importing
  `ag.runtime` passes the current config and breaks the amended one. `helpers → adapters` and
  `helpers → staging` are already caught by the two `protected` contracts, so only the upward
  direction is missing.
- **A package-coverage meta-check** in the permanent unit tests: every top-level package under
  `ag/` appears in the `layers` stack or in an explicit exempt list, read from `.importlinter` and
  the directory listing. `helpers/` would have failed it from the start, and `lineage/` will exist
  before anyone remembers its row. **Break it on purpose once** by removing `ag.helpers` from the
  stack, and confirm it fails.
- **ruff `SLF001`** (private-member-access) enabled on `operations/`, `helpers/` and `pipelines/`.
  It catches reach-through such as `tb.geometry._port`, which no import rule can see. B10 verified
  it is clean on all three packages today and that it exempts the namedtuple API.

**Prerequisite, found while writing this task: nothing runs these contracts in CI.** The only
workflow is `.github/workflows/black_linter.yml`. There is no pre-commit config, the root
`pyproject.toml` selects only ruff `F401` and `I`, and `import-linter` is not installed in any
environment. `03-architecture.md` lists "`.importlinter` exists and passes in CI" as a graduation
condition. So this task **adds the `lint-imports` step as well as the new row**. Otherwise the
row is one more passing convention.

**Where it runs.** Every check this task adds runs in **pre-commit and in CI on both
`windows-latest` and `ubuntu-latest`**: the team develops on Windows and production is Linux. The
same matrix covers the existing pure-Python checks, `temp/check_consistency.py` and
`check_terminology.py`. **Test CRLF line endings and path handling specifically**, since those
scripts parse Markdown with line-anchored regexes and build paths from `__file__`.

**CI has no arcpy installed, on purpose, and that is load-bearing.** It makes an `import arcpy`
anywhere outside the adapter a CI failure, which enforces the no-arcpy-in-core rule for free.
Adapter tests carry a pytest **`arcpy` marker** and CI runs **`-m "not arcpy"`**. An *unmarked*
arcpy test then fails on `ImportError` instead of being skipped silently, which is the property
the marker exists for.

**files touched** `template_code/.importlinter`, `pyproject.toml` (ruff `SLF001` per-path scope,
pytest marker registration), `template_code/tests/unit/` (the meta-check), a new CI workflow under
`.github/workflows/`, a new `.pre-commit-config.yaml`.

**depends on** nothing.

**decision refs** B10 (where the three gaps were found; this task does not resolve it); A26 (the
Python target, 3.13, which the CI matrix and the three `pyproject.toml` settings state).

**doc migration** none. `03-architecture.md` §4.1's table gains the tightened `helpers/` row when
the contract lands.

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

## 10. T2.2 — `update_rows`

**status:** not started

*(no longer `[INDEPENDENT]`: it depends on T0.1 and carries a lineage-motivated contract.)*

**what done means** `TableOps.update_rows(input, key, fields, rows)` exists: bulk, keyed, no
iteration protocol exposed. Writes only changed rows and only the named fields. Accepts
`Row.geometry`, so snap and displace are covered without a rebuild. The arcpy adapter compiles it
to a keyed cursor pass; the docstring names `UPDATE … FROM` and pandas merge-and-assign as the
equivalents that keep it portable.

- **The key field may not appear in `fields`; the call is rejected if it does.** The reason is this
  signature, not a general rule about re-keying: `rows` carries one value per field per row, so
  with `key ∈ fields` a row is matched on `row[key]` and then written back that same value — a
  guaranteed no-op. The rule rejects a caller error. It needs no lineage knowledge, and it lives in
  the port contract and docstring.
- **It does not guard `lineage_id` in general.** Keyed on `lineage_id`, `update_rows` cannot
  rewrite it at all; the real exposure is `lineage_id` written under a different key, or by
  `calculate_field`. That is A12.11a's option for T2.8, not this task's check.

**files touched** `template_code/ag/ports/table_ops.py`,
`template_code/ag/adapters/arcpy/` (implementation).

**depends on** T0.1 — the key is a `lineage_id`, so the field type must be settled.

**decision refs** A4.1, A4.2, A4.3, A12.11a.

**doc migration** A4.1–A4.3 → ADR-0004 amendment and `ports/table_ops.py`.

---

## 11. T2.8 — `join_field` unique-key contract

**status:** not started

**what done means** B4 resolved and written down: either `join_field` declares that its join key
must be unique — with a check — or the grammar gains a way for an in-place mutator to declare a
cardinality change. A non-unique join key changes row count with no output parameter to declare,
so the `@row_shape` grammar cannot currently see it.

**the other half of A12.6's definition.** A12.11a records an option for the same definition to
settle: have it declare **which parameter names the fields a mutator writes or drops** — `fields`
for `update_rows` and `delete_fields`, the target field for `calculate_field` — so the facade can
reject `lineage_id` there generically, without per-method argument parsing. It is an option, not a
decision. Two things to weigh if it is taken:

- **`join_field` belongs in that list.** Its `fields` parameter can name `lineage_id`, and joining
  a lineage-bearing table produces exactly B10's duplicate case: the target ends up carrying the
  *join* table's ids alongside its own.
- **The lineage layer legitimately writes `lineage_id` through the ports** — T4.5 Path A's map
  join and T3.4's fan-out join both do. So the rejection applies to **domain calls through the
  facade** only, with the lineage layer calling the **unwrapped port** — the `Protocol`
  implementation beneath the facade, not a named adapter, since T4.5's Path B exists precisely for
  backends other than arcpy. B10 carries the closed list of sanctioned bypasses and the layering
  check over it; do not restate the list here.

**files touched** `template_code/ag/ports/table_ops.py`.

**depends on** nothing.

**decision refs** A12.6, A12.11a, B4.

**doc migration** A12.6 → `ports/row_shape.py` (the in-place-mutator problem) and
`ports/table_ops.py` (the resulting `join_field` contract). Resolves B4 into an A-item, which
lands in the same two places.

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

**status:** blocked — B9, whether the delivered copy needs a key back to the archive

**what done means** `_apply_product_schema` no longer maps a field to a bare `objid`. Either the
column is dropped from the published schema, or it is named so that it does not read as a stable
identity (`run_object_id` or similar). Shipping `objid` binds consumers to an identity that
re-mints on every dissolve.

**files touched** `template_code/ag/operations/road/__init__.py`.

**depends on** **B9.** The two options are not equivalent until B9 answers whether the delivered
copy needs a key back to the archive. If it does, "drop the column" is off the table and the
remaining question is what the renamed column holds — B9(b)1's one-join candidate, or a third id
with its own map.

**decision refs** A19, B3, B9.

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
- **`DissolveOption` removed** (B18, A18 amended): `dissolve` is single-part by contract, and its
  docstring says that on lines a group splits at every junction. `dissolve_multipart` and an
  unsplit method are not added; the real call sites that will need them are listed under A18 for
  `04-migration.md`.
- **Every port handle parameter is annotated `In`, `Out`, T2.8's mutator marker or `ParentsOut`**
  (A12.5a), written with the signatures rather than after them. No check yet; T4.1 adds it.
- **Whether `FeatureToLine` (planarise at intersections) becomes a port method** is decided
  here, since `run_dissolve_with_intersections` needs it twice on the national road set (B20).

**files touched** `template_code/ag/ports/geometry_ops.py`, `template_code/ag/ports/cartographic_ops.py`,
`template_code/ag/ports/table_ops.py` (annotations), and every call site in
`template_code/ag/operations/`.

**depends on** T2.8, for the in-place mutator marker only.

- **Single-part is a debug-mode assertion, not a port invariant** (A18). arcpy `Describe` gives
  `shapeType`, never part count — `isMultipart` and `partCount` are *geometry* properties, so an
  unconditional invariant costs a per-row scan at every output boundary. Record this in the
  `geometry_ops.py` docstring alongside the note that a multipart dissolve, if ever needed,
  becomes a separate `dissolve_multipart` method rather than an argument, which is what keeps
  `@row_shape` static.

- **Record the two parameters that must not be added** (A17.3): `select` has no `residual` and
  `snap` has no `displacement`. Both appeared in a design sketch and neither is in the port;
  `DROPPED` comes from the boundary diff, so `residual` is not needed for lineage and has no
  caller. A one-line "deliberately absent" note in each docstring, in the same style as
  `geometry_ops.py`'s existing note on arcpy's `Identity`.

**decision refs** A5.4, A5.5, A5.6, A12.5a, A17.3, A18, B18, B20.

**doc migration** A5.4–A5.6, A17.3 and A18 → `ports/geometry_ops.py`.

**must land before T4.2** — the shape declarations are written against the split surface.

**note** A18 rides here rather than on a task of its own: it is a docstring statement about the
same method list this task is already editing, and it had no task at all before — under the
three-clause completion test it would never have migrated.

---

## 15. T2.10 — `dissolve(statistics=…)` and the `ranks` fix

**status:** not started
*(merged: former T2.11)*

**what done means**

- `dissolve` takes `statistics: tuple[StatisticSpec, ...] = ()` with `Statistic` limited to
  `MIN`, `MAX`, `SUM`, `MEAN`, `COUNT` (A9.12), so a collapse can state its combining rule
  (`statistics=(StatisticSpec(RANK, Statistic.MAX, RANK),)`), making A9.10's requirement
  expressible. The docstring states null handling and output types and forbids `lineage_id` as a
  source, as A9.12 lists them.
- **Every statistic is evaluated over the parents of each output row** (A9.11), and the docstring
  says so. The engine's own statistics option is measured per key under single-part output and is
  not used; the adapter computes the rule from the parents pairs joined to the input attributes
  (B17's recommendation, adapter-internal). Consequence: `statistics=` is not free, and it depends
  on the parents path of T2.4 even on a handle with no lineage.
- Both `join_field(... join=ranks ...)` calls are deleted — `operations/road/__init__.py:663` and
  `:932`.
- `Network.ranks` and `ConflictResolution.ranks` handles and their `StageInput`s are deleted.
- `RANK` survives the dissolve at `:648` as a statistic rather than being restored by a join keyed
  on an id the dissolve just re-minted.
- `ROAD_RANKS` may remain a `StageOutput` as a diagnostic; nothing reads it back by id.

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/operations/road/__init__.py`, `template_code/ag/pipelines/road/n100.py`.

**depends on** T2.4.

**decision refs** A9.10, A9.11, A9.12, A17.5, A17.6, B19.

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
- **Every port method with an output declared `ids=MINT`** takes an optional
  `parents: ScratchHandle | None` receiving a TABLE of `(PARENT_ID, CHILD_ID)` rows, one per
  (input row, output row) pair, in native indices (A11.15). `PARENT_ID` references the `subject=`
  input only; the parameter is `parents`, or `<output>_parents` on a method with several `MINT`
  outputs (none today). The parameter carries the `ParentsOut` marker (A12.5a).
- **`ports/errors.py` exists** with the three engine-neutral errors a caller can see from a
  lineage-bearing port call: `ParentsUnavailableError` (parents requested and the adapter cannot
  produce them for this method, A14.1); `UnmatchedInputError` (an input the method could not have
  discarded is in no pair, B17's guard); `EmptyGeometryError` (a null or empty shape in a subject,
  raised before the tool runs). Adapters raise these from the parents path, never engine
  exceptions. The facade's own errors — A11.4a's ceilings, A11.15(d) — live in `lineage/`, not
  here. Placed in this task because two of the three are parents errors and this task already
  owns the port-side parents constants; written in the same pass as the ports.

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/ports/cartographic_ops.py`, new `template_code/ag/ports/errors.py`,
`template_code/ag/operations/road/__init__.py`.

**depends on** T2.9.

**decision refs** A11.1, A11.15, A12.2, A12.5a, A14.1, B6.

**doc migration** the constants rationale → `ports/geometry_ops.py`. A11.1's parents-versus-log
distinction → the new ADR on lineage, at T4.6.

**naming** This mechanism was called *correspondence* throughout the design discussion. It is
**parents** everywhere — the parameter, the constants, the prose. `source_rows` was rejected
because `source` already means `ExternalSource` in this repository.

---

## 16b. T2.12 — `TableOps.create_workspace`

**status:** not started

**what done means** `TableOps.create_workspace(*, path: str, fmt: WorkspaceFormat) -> None`
exists and creates one empty workspace. `WorkspaceFormat` lives in `ports/`, since a port
signature names it; `staging/workspace.py` keeps the join rule, name legality and the name
budget. `ScratchFileManager.create_workspaces` calls the method through the toolbox `runtime/`
hands it, once for the stage workspace and once per operation workspace, and creates the
sidecar directories itself. Both adapters implement it, the in-memory one by recording the
workspace, and the conformance suite has its cases: the workspace exists afterwards; creating
one that already exists is a `PortContractError`; a path whose parent is missing is an
`EngineError` naming the tool.

**files touched** `ports/table_ops.py`, `ports/` (the new home of `WorkspaceFormat`),
`staging/workspace.py`, `staging/scratch.py`, both adapters, `tests/conformance/`. Lands in
slice 1c of `findings/implementation_plan.md`.

**depends on** nothing.

**decision refs** A5.7, B21.

**doc migration** A5.7 → `ports/table_ops.py`, the `staging/scratch.py` docstring and
`02-runtime.md` §4.2.

---

## 16c. T2.13 — Call identity: per-call workspace and scope namespace

**status:** not started

**what done means** `Stage` gives each `OperationCall` a call identity in declaration order:
the operation's short name, with `_2`, `_3`, ... on repeats, and rejects at import two
different functions (different `qualified_name`) that share a short name in one stage. The
stage entry point binds one scratch scope per call with the call identity as its namespace,
and one materialiser per call. `ScratchFileManager` renders the operation workspace from the
call identity and raises on a repeated (trail, leaf) within one call rather than returning a
second path. Tests: two calls of one operation in a stage get two workspaces and pairwise
unequal internal handles; the repeated-(trail, leaf) contract raises; the same-short-name
check fires with both qualified names in the message.

**files touched** `core/pipeline.py` (Task B), `staging/scratch.py`, `runtime/stage_entry.py`
(slice 1c of `findings/implementation_plan.md`). `core/handles.py` already stamps the
scope's namespace and names internal handles by trail and leaf; nothing there changes.

**depends on** nothing.

**decision refs** A29, A15.3.

**doc migration** A29 → the `Stage` docstring in `core/pipeline.py`, the `staging/scratch.py`
docstring and `02-runtime.md` §4.2.

---

## 17. T3.1 — Native index behind the port

**status:** not started

**what done means** A port-level accessor exposes the storage format's own row index —
`OBJECTID` in a file gdb, `fid` in GeoPackage — with a contract stating it is **valid only until
this dataset is next written**. The docstring records that backends differ on stability
(GeoPackage rowid stable, Postgres `ctid` moves on update), so an adapter may have to materialise
a surrogate.

**And the contract states whether the index is addressable as a join key**, not only readable
through an accessor. These are different guarantees: `OBJECTID` is a real column in a file gdb and
can be a `join_field` key; a backend whose row index is not a column cannot. T4.5's preferred
`join_field` path depends on this, and where it is absent that backend permanently gets the packed
form instead. An adapter declares which it provides.

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

A distinct run-scoped step, before any stage executes, that allocates a dense positive
`lineage_id` to every feature of **every input the run reads from outside itself** — not only
`ExternalSource`. Cross-run `Derived` and `ProductIdentity` inputs are re-allocated too (A24).

- **The ingest map records four columns**, not two:
  `(native_index, incoming_lineage_id, new_lineage_id, boundary_kind)`, with
  `incoming_lineage_id` null where there is none and
  `boundary_kind ∈ {RAW, CROSS_RUN, LOST_HISTORY}`. The incoming id is what lets a resolver cross a run boundary; without it, A23's
  trace-to-RAW question is unanswerable. `boundary_kind` is not redundant with a null incoming id,
  which covers both `RAW` and `LOST_HISTORY` — a walk must report the first as complete and the
  second as truncated (A24.1, A21).
- **Copying is a three-way rule** driven by whether a stable incoming id exists, not by the
  declared type:
  - `ExternalSource` → **copy**, rewriting ids.
  - `Derived` / `ProductIdentity` **with** `lineage_id` → **map only**; fan-out applies it by
    joining on `incoming_lineage_id`.
  - `Derived` / `ProductIdentity` **without** `lineage_id` → **copy**, same as `ExternalSource`.
- A **cold start** (A22) needs no code path of its own: the incoming id column is empty, so the
  rule above routes it to the copy branch by itself. Verify this with a test that runs a stage
  against an input carrying no `lineage_id` at all.
- Raw ids do **not** use the minter/counter layout, so ingest consumes no `minter_id`. Ingest may
  run one job per input for I/O parallelism; each draws a **disjoint range** from one run-scoped
  counter, and the range is recorded in the artifact.
- Fan-out applies the map and still allocates nothing (A6.6 as clarified by A24.1).

**files touched** `template_code/ag/runtime/`, `template_code/ag/staging/`.

**depends on** T0.1, T3.3.

**decision refs** A10.6, A10.7, A22, A24, A24.1, A6.6.

**doc migration** A10.6, A10.7, A24, A24.1 → the ADR from T3.3 and `02-runtime.md` §6. A22 →
`02-runtime.md` §6.1.

**note on the copy** A10.6's coupling argument — that a map keyed on a *native index* can only be
joined while those indices are still valid — applies to `ExternalSource` and **not** to a
cross-run `Derived`, which carries `lineage_id` as an ordinary data column that survives download
unchanged. That is why the second row above is map-only. Measure before assuming: an N100 run
ingests a national N50 product on every execution, so this branch runs constantly.

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

## 20b. T3.6 — Lineage retention alongside published products

**status:** not started

**what done means** A published product's **edge log and ingest map are archived with the
product** and readable for as long as it is — they are part of the product, not run scratch.
Retention is declared where the product's own retention is declared, not in run-scratch policy.

A missing hop degrades **explicitly**: the resolver reports
`traced to N50 feature 8814402, prior history unavailable (N50 run log not retained)` rather than
terminating silently at an id that looks raw. Because a re-allocation boundary produces dense
positive ids indistinguishable by inspection from raw ingest ids, the resolver must learn which
kind of boundary it reached from the ingest map's own record — so the map must say so.

**files touched** `template_code/ag/staging/`, `template_code/ag/products.py`,
`docs/refactor/02-runtime.md` §4.1.

**depends on** T3.4, T3.5.

**decision refs** A21, A23.

**doc migration** A21 → the ADR from T3.3 and `02-runtime.md` §4.1. A23 → the new ADR on lineage
and, for the resolver contract, `ag/lineage/query.py`.

**why this is not optional** A23 makes trace-to-source a requirement, and it is answerable only
from every intermediate run's edges plus each boundary's map. Without retention the requirement
fails on the second hop.

---

## 20c. T3.7 — Foreign-id guard

**status:** not started

**what done means** Two checks, because one of them does not catch the failure that matters.

**(a) Map membership — the detector for a missed join.** For any input that came through a
**map-only** boundary (A24.1's second row), the post-join dataset's `lineage_id` column equals
that map's `new_lineage_id` column **as a multiset**.

Multiset, not subset: a run X raw id and a run Y `new_lineage_id` are both dense positives, so a
stranded `42` can coincide with another row's legitimately allocated `42` in the same map and pass
a membership test. Multiset equality catches it on multiplicity — the correct new id is missing
and `42` appears twice. Same technique as A7.2's shadow comparison.

**(b) Range check — the general guard.** Every `lineage_id` in a lineage-bearing input falls
within this run's allocated ranges:

```
id > 0   →  inside one of the ingest ranges recorded in this run's ingest artifact
id < 0   →  minter_id(id) is present in this run's dispatch registry
```

This catches ids from nowhere at all — a hand-edited dataset, a field carried in from outside the
system. It does **not** reliably catch a missed join: `minter_id` and raw ids are both dense from
1 in every run, so a stranded prior-run id usually lands inside a legitimate range. That is why
(a) exists and why (a) is the one to implement first.

- Both run at **stage entry**, over each lineage-bearing `StageInput`, **folded into A13's
  existing existence check** — the input is read once and asserted against three times. This is
  the earliest point a foreign id is observable, and the failing pod names the input.
- Runs again at **fan-in** as defence in depth, where the merged logs and the dispatch registry
  are both already open.
- Both are **grouped scans, not per-row loops**: (a) is one grouped count on each side, and the
  map is already open because fan-out has just used it; (b) extracts `minter_id` arithmetically
  from negative ids and compares the distinct set against the registry, and buckets positive ids
  against the ingest ranges. For (b) a min/max hull check is **not** sufficient — ingest ranges are
  disjoint intervals, so a foreign id can sit inside the hull while belonging to no range.

**files touched** `template_code/ag/runtime/stage_entry.py`, `template_code/ag/lineage/`,
`template_code/ag/core/validation.py`.

**depends on** T3.3, T3.4.

**decision refs** A25, A25.1, A13, A24, A24.1.

**doc migration** A25 and A25.1 → `02-runtime.md` §8 and the lineage module docstring.

**why this is not belt-and-braces any more** Under copy-everything ingest, the copy was already
correct before any stage ran and a foreign id was not representable. Under A24.1's map-only
branch, correctness is established by **fan-out applying the join** — so if fan-out misses it, the
dataset carries the prior run's ids and B7 returns silently, in exactly the form A24 exists to
prevent. **Check (a) is the only detector for that.** Check (b) does not substitute for it: a
stranded prior-run id is, by construction, numerically ordinary.

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

- `Rows(cardinality, ids, subject=… | context=… | refs=…)` exists, with `cardinality ∈ {ONE, MANY,
  GROUP}` and `ids ∈ {CARRY, MINT, FOREIGN}`.
- `@row_shape(**outputs: Rows)` attaches declarations to a Protocol method without changing its
  signature, so structural typing still holds and adapters need no decoration.
- CI check rejects, each with its specific reason in the message: an output parameter with no
  declaration; either axis missing; a `MINT` with no subject; a `FOREIGN` with no refs; a subject
  or reference naming a parameter that does not exist; and the three illegal cells —
  `MANY + CARRY`, `GROUP + CARRY`, `GROUP + FOREIGN`.
- The `MANY + CARRY` message states the primary reason: **this is the inheritance model A11.2
  rejects** — five split pieces all keeping id 1 leaves the log unable to express a partial drop.
  The grammar rule and A11.2 are the same rule stated twice.
- **A method with no output handle is outside the grammar, and the check says so explicitly.**
  `count`, `exists`, `data_type_of` and `describe_fields` return values, not rows. The exclusion is
  written into the check and `row_shape.py`'s docstring rather than implied by the absence of an
  output parameter, so a later reader cannot mistake an undeclared query for a missed declaration.
  In-place mutators (A12.6) are **not** covered by this exclusion: they have no output parameter
  but do change a handle, and T2.8 settles how they declare.

**files touched** new `template_code/ag/ports/row_shape.py`,
`template_code/tests/unit/test_row_shape.py`.

**B12 resolved by A12.5a.** The annotations (`In`, `Out`, T2.8's mutator marker, `ParentsOut`)
land with the ports in T2.9; this task adds the check: an `Out` parameter with no `@row_shape`
entry; a `@row_shape` key naming a parameter that is not `Out`; a `subject`, `context` or `refs`
value naming a parameter that is not `In`; `ParentsOut` exempt from the first rule. **Break it on
purpose once**: remove one `@row_shape` entry and one `Out` annotation, and confirm each fails
with its own message.

**depends on** T2.4, T2.9.

**decision refs** A12.1–A12.6, A12.5a.

**doc migration** A12.1–A12.4 → `ports/row_shape.py`; A12.5 → `02-runtime.md` §8.

---

## 23. T4.2 — Declare shapes across the port surface

**status:** not started

**what done means** Every output parameter of every `GeometryOps`, `CartographicOps` and
`TableOps` method carries a `@row_shape` declaration matching A12.11's table, including A12.11a's
`map_fields` row. The CI check from T4.1 passes. `collapse_to_point` is declared `ONE + CARRY`,
with the precedent stated in its docstring in A12.10's reworded form: *ids change when the feature
stops standing for the same real-world object, not when its geometry kind changes.*

- **A12.11's rows and the Protocol's methods match in both directions.** Every row names a method
  that exists, and every row-producing method has a row. One direction is not enough: a
  declaration naming a method that does not exist passes every check that iterates over methods.
  Today the drift is `nearest_neighbor` / `all_neighbors` against the Protocol's single
  `nearest_neighbors`, and `buffer_dissolve`, `extract_vertex`, `spatial_join_all` declared but not
  yet split out by T2.9. **This check can be one-shot**, run while declaring, since A12.11's table
  migrates away when this task closes; T4.1's CI check is what persists.
- **`displace_features.displacement` is not declared from A12.11 until B11 resolves.** Both its
  axes are open, and one branch has no legal cell.
- **`simplify`'s docstring defines `collapsed_points`** as *every input row absent from the main
  output, at a stated point rule*. **Before writing that definition, check whether
  `SimplifyPolygon`'s minimum-area removal emits points**: if the tool drops rows for reasons other
  than collapse, the derivation and the tool's own output disagree, and the definition has to pick
  one. This is what lets the adapter derive `collapsed_points` by set difference when the tool's
  output lacks both `lineage_id` and a reference (T0.1's type-survival case).

**files touched** `template_code/ag/ports/geometry_ops.py`,
`template_code/ag/ports/cartographic_ops.py`, `template_code/ag/ports/table_ops.py`.

**depends on** T4.1, T2.9, T2.2 — the two-way check must see `update_rows`.

**decision refs** A12.10, A12.11, A12.11a, A12.12, B11.

**doc migration** A12.10–A12.12 and **A12.11a** → the port module docstrings. A12.11a is named
explicitly because the range does not cover a suffixed id.

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

Owns B10's facade-side pieces, if B10 is adopted:

- **the post-call assertion**: after every port call that produces or mutates a lineage-bearing
  handle, `lineage_id` exists with the declared type, and no adapter-declared duplicate of it
  exists. One `describe_fields`, no row scan. Pure Python, so it runs identically in every
  environment, local Windows runs included;
- **no accessor to the inner port** on the facade;
- **the `lineage/` protected contract** in `.importlinter`, with `allowed_importers` set from where
  ingest, fan-out and fan-in actually live, not from B10's minimal probe;
- **the mint surface choice**: a public `ag.lineage.api` module the domain may import, or `mint`
  reached through the `Toolbox`. B10 records that both cost one contract.

And the parents channel's facade side (A11.15):

- the facade passes **its own** scratch handle as `parents=` on every `MINT` call whose subject is
  lineage-bearing, reads the native pairs, maps them to `lineage_id` and mints (A12.4);
- when the domain passed `parents=` too, the facade writes the `lineage_id` relation to the
  domain's handle; the port never sees the domain's handle;
- a domain `parents=` on a subject without `lineage_id` raises in the facade, before the port call.

**note** A15.1's "ask on every `MINT` call" versus "only when diff-tracked" is a live cost decision
on lines (parents resolution is not free there); T4.14 records the numbers and the revisit is
listed under it. Nothing in this task's interface changes either way.

**files touched** new `template_code/ag/lineage/` package,
`template_code/ag/runtime/stage_entry.py`, `template_code/.importlinter`.

**depends on** T4.2.

**decision refs** A11.11, A11.12, A11.15, A15.1, B10.

**doc migration** A11.11 → the new ADR on lineage and `03-architecture.md` §4. A11.12 and A15.1 →
the lineage module docstring — A15.1 is the cost model the facade is built around ("mint always,
scope only the boundary diff") and belongs beside the code that implements it.

---

## 25. T4.5 — Disk-backed id map

**status:** not started

**what done means** **Two paths, both built and both tested.** Which one runs is a backend
property, so the packed form is not a contingency for the other — it is permanently what a backend
without an addressable row index gets.

**Path A — `join_field` (preferred where available).** Materialize the map with `write_table`,
then `join_field(input=subject, key=<native index>, join=<map>, join_key=…)`. No Python-side map
at all, so the memory is the GP tool's and bounded by it. Requires T3.1's join-key contract.

**Path B — packed arrays.** `int64` arrays on pod-local disk, fixed-size block cache, and a peak
memory figure — as the cgroup accounts it — declared as a constant (A15.3, provisionally 64 MB
from T0.6). Same code path at 70K rows and at 280M.

- **The map is sorted by lookup key and the subject is read in the same order.** This is what makes
  a fixed small cache sufficient at any map size; random access would need a cache proportional to
  the map and the bounded-memory property would be false. **It constrains the read loop, not only the
  layout** — a map sorted at build time is defeated by a consumer reading in a different order, so
  say so in the docstring of both, and check it in review.
- **Two ceilings, design checked first** (A11.4a): a design ceiling of 10M rows, invariant across
  environments, and a resource ceiling from T0.6 that moves with the pod. A resource ceiling below
  the design ceiling is legal and tripping it is not a code defect. Messages name which tripped.

**Both paths:** cache keyed on `ScratchHandle` (frozen, hashable, `path` set `compare=False`, so a
materialized copy equals its declaration); invalidated on any call naming the handle as an output;
in-place mutators do not invalidate. A **row-count** check per operation is the independent guard,
and a mismatch drops the cache — so a stale cache is a miss, never wrong data.

**files touched** `template_code/ag/lineage/`, `template_code/ag/adapters/arcpy/`.

**depends on** T4.3, T0.6, T3.1.

**decision refs** A15.3, A15.3a, A11.4a.

**doc migration** A15.3 → the lineage module docstring; A15.3a → `02-runtime.md` §2.7; A11.4a's
ceilings → the lineage module docstring, A11.4a's rule → `02-runtime.md` §2.4.

**notes** Full id-set validation was rejected: it reads every id, which is the same scan as
rebuilding, so it saves the construction and not the I/O. **The in-memory dict was rejected for
having an unbounded worst case, not for being slow** — a benchmark showing it faster on a small
handle is not an argument for reinstating it.

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

**B13 resolved by A12.7a, signed 2026-09-21.** `write_rows` and `write_table` take a required
call-site keyword declaring the ids axis (`CARRY` from a handle, `FOREIGN` with refs, or `MINT`),
and A12.7's error rule becomes three checks. Acceptance additions, from
`PROPOSALS-2026-09-14.md` §3: the five template write sites each carry their declaration
(`:243` `nodes` MINT; `:322` `displacement` FOREIGN with refs to the road features through the
carried `VERTEX_SOURCE`; `:453` `match_report` CARRY from `unmatched`; `:542` `rank_table` CARRY
from `penalised`; `:592` `merge_report` FOREIGN with refs to `candidates`); omitting the keyword
is a pyright error; a `CARRY` write whose rows were rebuilt without ids fails with a message
naming the write; `SNAP_DISPLACEMENT` passes. This task also states what a ref column holds when
the ref names a handle that is itself `FOREIGN`. The text below is the question as it stood.

*As it stood:* two of the four "no call-site change" sites (`:323`, `:593`)
read a `FOREIGN` handle, and the error rule above fires on `SNAP_DISPLACEMENT`, which A15.6 calls
legal. A proposal (a required call-site ids declaration on writes) awaits sign-off and would
replace this acceptance text.

**depends on** T4.3.

**decision refs** A12.7, A12.7a, B13.

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
- `EdgeKind` has four values, **all runtime-derived, none declared**: `PARENTS_CONSUMED` (every parent
  absent from this operation's outputs), `PARENTS_KEPT` (at least one parent survives), `DROPPED` (no
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
in none of `O`, `T`, `D`: it is `PARENTS_CONSUMED` at the operation boundary because `collapsed_points`
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

- **`diff-tracked`** — the handle reaches a `StageOutput`. Determines whether the boundary diff runs.
- **lineage-bearing** — the declaration chain terminates in `CARRY` or `MINT`. Determines whether a
  `lineage_id` column exists.

A `FOREIGN`-terminal handle can be `diff-tracked` without being `lineage-bearing`, and that is legal:
`SNAP_DISPLACEMENT` is exactly that. The boundary diff skips non-bearing handles, completeness
ignores them, and A13's input verification applies to lineage-**bearing** inputs only.

A plan-time check rejects a `FOREIGN`-terminal handle named as the `subject` of a downstream
`CARRY` or `MINT`. It does **not** reject a `FOREIGN` handle reaching a `StageOutput`.

**files touched** `template_code/ag/lineage/`, `template_code/ag/core/validation.py`.

**depends on** T4.6.

**open: B14.** The task says lineage-bearing is computed from the stage declaration and operation
wiring, but plan time does not see the port calls inside operation bodies, where `@row_shape`
applies. The derivation mechanism is unstated.

**decision refs** A12.9, A15.2, A15.6, B14.

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

**decision refs** A9.10, A17.5, B15.

**doc migration** none beyond A9.10, which migrates at T2.10.

**known limit** This catches generation mismatches, not **granularity** mismatches.
`operations/road/__init__.py:315` joins `paired.near_fid` (a vertex-row reference) against
`vertices_after.FEATURE_ID` (feature-level), which fans out under any id model. Not caught here,
and not blocking.

**second known limit, B15** Only `join_field` is checked. A lookup written as `read_rows` then
`Attr.in_` crosses a mint just as silently — `thin_road_network`'s `merge_report` exemption does.

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

**what done means** The arcpy adapter honours `parents=` (A11.15) on every method it names in its
capability record, and publishes that record at construction as a set of method names declared
`ids=MINT` — no tier and no vendor parameter in it (A14.1). Sources, adapter-internal: for
`aggregate` and `collapse_to_centerline` the tools' own `OUTPUT_FID`/`INPUT_FID` tables; for
`dissolve` and `buffer_dissolve` the keyed resolver of B17 for polygons and points, and for lines
whichever locator T4.14 names; for `clip` and `difference` a work key stamped on a copy of the
input; for the other `MANY + MINT` methods the engine's native reference field. A method the
adapter cannot honour raises `ParentsUnavailableError` (T2.4). Unkeyed spatial reconstruction is
not implemented. A plan-time check fails a stage that uses a lineage-bearing handle with a `MINT`
method outside the record, before fan-out rather than in the pod.

**files touched** `template_code/ag/adapters/arcpy/`, `template_code/ag/core/validation.py`.

**The concatenation path is retired** (T0.1 case 12, A14.1): over budget by two orders of
magnitude and per-key under single-part output. Nothing here builds on it.

**follow-up (B14): the plan-time derivation.** Acceptance: `validate()` obtains the set of port
methods an operation calls — from the recording spy's trace or from a declaration, B14's choice —
and the capability check fires on a fixture stage whose operation calls a `MINT` method outside
the record.

**depends on** T4.2.

**decision refs** A11.15, A14.1, B14, B17.

**doc migration** A14 → `adapters/arcpy/` package docstring; the plan-time check → `02-runtime.md`
§8.

**resolved** The probe runs at adapter construction, which has arcpy; `validate()` takes the
resulting capability record as an argument — data, not a call. No exemption needed (A14).

---

## 33. T4.11 — Adapter conformance suite

**status:** not started

**what done means** Three halves.

**(1) `MINT` parents.** One case per `MINT` method: run it over a known input set, obtain the
pairs through the Protocol's `parents=` out-param (A11.15), and assert they match the oracle. The
oracle for `dissolve` is the engine's own lineage table on builds that have one (Pro 3.7) and the
recorded goldens (`temp/goldens/`) elsewhere; for `aggregate` and `collapse_to_centerline` the
tools' tables are the source, so the case checks the pair table against a hand-built fixture. The
suite passes on the 3.6 image and on 3.7 with the same code.

**(1a) Native-index stability.** One case asserts that a `MINT` method leaves its `input` handle's
native indices unchanged across the call (A9.2), on every adapter: read the index set before and
after, assert equality. Acceptance: fails when a method is compiled to write its input in place.

**(1b) Image checks.** On `arcpy-linux`: the locale decimal mark in any text the adapter parses;
`memory\\name` scratch paths; and the keyed resolver's locators on the same goldens. Acceptance:
the goldens replay on the image with the same pairs as on Windows.

**(2) `CARRY` presence and type.** One case per `CARRY` method in A12.11 and A12.11a: assert
`lineage_id` **exists with the declared type on each output**. This makes T0.1's type-survival
case permanent. T0.1 only tests the *intended* arcpy mappings, because no adapter method exists
yet; here "re-test when the adapter changes" stops being a manual obligation and becomes a gate.
Where a tool's output lacks the field and the adapter stamps from a native-index reference or
derives the output by set difference (`simplify.collapsed_points`), the case tests that route.

**(3) In-place cartography tools leave their input unchanged.** `ResolveRoadConflicts`,
`ResolveBuildingConflicts` and `PropagateDisplacement` all alter the source feature class of their
input. Behind `displace_features` and `propagate_displacement`, a case asserts **the input handle's
geometry is unchanged after the call**. The adapter must compile them copy-then-edit; otherwise it
mutates a handle another operation, or a retry of the same one, may read.

**Where it runs — not a CI step.** Conformance needs ArcPy and CI has none. It **gates image
promotion**: run in the freshly built Linux image, triggered by image rebuilds and by changes under
`adapters/arcpy/`. It is also runnable **locally against Windows Pro**, as a convenience and a
divergence detector, and in the image under Docker. It is not a pre-commit hook, for the same
reason it is not CI.

**Open: licence activation.** Whether running the image needs a Pro licence activated, and where
that happens, decides whether the promotion gate can run automatically or needs a licensed runner.
Record the answer here when known.

**files touched** `template_code/tests/` — adapter conformance path TBD. Tests carry the `arcpy`
pytest marker (see T7.4).

**depends on** T4.10.

**decision refs** A9.2, A11.15, A14.1, A12.11, A12.11a.

**doc migration** none.

---

## 33b. T4.14 — Dissolve parents track (B17) `[PARALLEL]`

**status:** not started

**Does not block the port track.** Everything above the port is settled by A11.15 and A14.1; this
task produces the evidence B17 needs to name one locator per geometry type, using the staging code
in `docs/refactor/temp/` (`dissolve_parents.py`, `arcpy_part_locator.py`, `n1_fixtures.py`,
`n1_parents_gate.py`, `goldens/`). Each item has one line of acceptance.

**harness**

- **Logging.** `n1_parents_gate.py` tees stdout to `<workdir>\logs\<timestamp>_<cases>.txt`
  regardless of runner; child runs append to the same file. Acceptance: a run started from the
  editor runner leaves a complete log without a shell redirect.
- **Baselines in the capped child.** The plain dissolve of a timing point runs in the child
  interpreter under the same timeout. Acceptance: a baseline timeout is recorded as "tool alone
  over budget on this shape" and the locators for that point are skipped, not attempted.
- **Dissolve-output cache.** Dissolve outputs and native tables are cached per (fixture, tool,
  parameters), each with a `.done` marker written last. Acceptance: a second run of the correctness
  ladder performs no dissolve.
- **Pathological fixture gate.** `lattice_long_vertexed` is excluded from `--confirm-large` unless
  `--include-pathological` is passed; its 10^6 plain-dissolve baseline is recorded as 5,088 s.
  Acceptance: `--confirm-large` alone never dissolves that fixture at 10^6.

**evidence for lines**

- **Real-data probe on the largest partition selection.** "Worst" is the partition whose
  selection (processing rows plus halo, as `PartitionIterator` selects them) is largest, taken
  from the ramps stage's input `data_preparation___road_single_part_2___n100_road` with the
  iterator's own code, optimisation off, 35,000 elements and a 500 m radius
  (`data_preparation_2.py:403-407`); exported by `temp/n1_real_partition.py`. The probe reports
  the largest key size against processing + halo rows, the parts that key produces, p50/p95/max
  vertices per input and output parts per input, on the whole selection and on the ramps subset
  the live dissolve sees; and, count only, the largest group of the 12-field key over the whole
  stage input, which is the unpartitioned national dissolve's key (B20). Acceptance: the numbers
  are in `temp/findings/n1_correspondence.md` §3 with the partition id named and
  `largest key <= processing + halo rows` printed true. **Measured 2026-09-17** (findings §3.11,
  logs `20260917_143734_real_partition.txt`, `20260917_150715_…`, `20260917_150945_…`): partition
  18, 36,407 rows, largest key 15,392, 15,392 <= 34,780 + 1,627 true. Still to run: the plain
  bracket, both locators against the table, the absent-input classification, and the national
  count on the chain's input rather than its output.
- **Both locators against the native table on the real partition** (pair for pair, partition,
  first ten mismatches, time added over plain), on the five-field key, on the ramps subset and
  on the whole selection as one group; this is the primary evidence for the line locator.
  Acceptance: one locator is named for lines in B17, with the numbers beside A15.7.
- **Correctness and timing ladders re-run with logging**, secondary to the real partition; the
  point and segment locators compared on the lattices at 10^4 and timed at 10^4 and 10^5.
  Acceptance: the numbers are beside the real-partition ones in B17.
- **STRESS margin**, no stage uses these values: an export at 250,000 elements and a 5,000 m
  radius, probed with the five-field key and as one group; optionally the same on the national
  chain's input if the locators stay under A15.7's minute. Acceptance: recorded in the findings
  as margin, never quoted as a partition's load.
- **`SplitLine` candidate** on `lattice_long_vertexed` at 10^5: `SplitLine` (`ORIG_FID`) →
  dissolve → join the two pair tables. Acceptance: time, output geometry equality with the plain
  dissolve, and whether the joined parents equal the native table at 10^4 are recorded.
- **Locator stage profile.** Acceptance: the dominant stage (points, write, join, read and filter)
  is named from measurements before any optimisation, and the optimisation is measured against it.
- **10^6 confirmation — dropped, 2026-09-17**: the largest key in the largest ramps partition is
  15,392 of 36,407 rows, and the national chain's largest input key is 121,341 of 2,320,817
  (findings §3.13), so no dissolve the pipeline runs has a 10^6-row group. What the national
  chain has is a 2.3·10^6-row unpartitioned call whose plain dissolve alone exceeds 270 s; that
  is B20's decision 3, not a locator size question. Acceptance: B20 carries the numbers.

**follow-ups, each a decision to record**

- **A15.1 revisit**: "ask for parents on every `MINT` call" versus "only when diff-tracked", once
  the line numbers and A15.7 exist. Acceptance: A15.1 gains a superseding note or a confirmation.
- **Owner of the empty-geometry guard**: the adapter's pre-call check, `validate_geometry`, or
  both. Acceptance: one sentence in `GeometryOps`'s class docstring or `02-runtime.md` §2.4.
- **`buffer_dissolve` positive-only**: check the 6 `ALL` call sites (A5.6) for a zero or negative
  distance; decide port rule or adapter limit. Acceptance: the sentence lands in the docstring or
  in A14.1's error list.
- **Record `case_aggregate_pass_through`'s result** (does `AggregatePolygons`' table list a
  pass-through input) and the `cluster_points` tool mapping, which `03-architecture.md` §2.2 never
  names. Acceptance: both in the findings file §1 and the port docstrings.
- **B20, the unpartitioned national dissolve chain**: the probe's national count is its first
  number. Acceptance: B20's three decisions have an owner and the count is beside them.

**files touched** `docs/refactor/temp/n1_parents_gate.py`, `docs/refactor/temp/n1_fixtures.py`,
`docs/refactor/temp/arcpy_part_locator.py`, `docs/refactor/temp/findings/n1_correspondence.md`.

**depends on** nothing.

**decision refs** A9.11, A15.1, A15.7, B17, B20.

**doc migration** B17 → `adapters/arcpy/` package docstring when resolved; A15.7 →
`02-runtime.md` §8.

---

## 34. T5.1 — Fan-in log merge and `DROPPED` promotion

**status:** not started

**what done means** Fan-in merges the K job logs and the dispatch registry. `DROPPED` is promoted
only where the dropping job owns the id:
`D = { d ∈ ⋃ D_job : owner(root(d)) == job(d) }`, with `root(d)` resolved through that job's own
log and `owner` from the fan-out assignment. `PARENTS_CONSUMED` and `PARENTS_KEPT` need no ownership check —
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
I  = lineage ids in the stage's PROCESSING StageInputs, own features only
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
its raw ancestors.

- **Forward walks return a set, not a single value** — a feature consumed by a second pipeline
  gets a forward edge there and continues in its own, so branching is normal and the contract says
  so.
- **Walks cross run boundaries** by alternating: N:M edges inside a run, then a 1:1 hop through
  that boundary's ingest map on `incoming_lineage_id`, then the prior run's edges (A24.1). This is
  what makes A23's trace-to-RAW question answerable across the scale ladder.
- **A missing hop terminates with a named boundary**, never silently:
  `traced to N50 feature 8814402, prior history unavailable (N50 run log not retained)`. A
  re-allocation boundary produces dense positive ids that look exactly like raw ingest ids, so the
  resolver must take the distinction from the ingest map's record rather than from the id's shape.

**files touched** `template_code/ag/lineage/query.py`.

**depends on** T6.1, T3.6.

**decision refs** A20, A21, A23, A24.1.

**doc migration** A20 and A23's resolver contract → `ag/lineage/query.py`.

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

## 40. T7.1 — Documentation-only migration

**status:** not started

**what done means** A1.1, A1.2 and A1.3 have landed at their destinations and are struck from
DECISIONS.md. Nothing is built; these are guidance with no corresponding work, and this task
exists so the completion test stays mechanical.

- A1.1 (operations are a package; `__init__.py` is a reading convenience) → `03-architecture.md`
  §5 and the `operations/` package docstring.
- A1.2 (granularity is set by what must be visible outside the function) → `02-runtime.md` §2.4.
- A1.3 (`Toolbox` explicit, never a module singleton; constructor injection for large tools) →
  ADR-0008, amended with the incremental-port argument.

**files touched** `docs/refactor/03-architecture.md`, `docs/refactor/02-runtime.md`,
`docs/refactor/decisions/0008-toolbox-passed-explicitly.md`,
`template_code/ag/operations/__init__.py`.

**depends on** nothing.

**decision refs** A1.1, A1.2, A1.3.

**doc migration** A1.1, A1.2, A1.3 — this task is the migration.

---

## 41. T7.2 — `LineageRoot` → `OriginRoot` rename `[INDEPENDENT]`

**status:** done — slice 0, 2026-09-22, inside `template_code/` and in `01-terminology.md` and
`02-runtime.md` §2.2. `tools/run_example.py` prints the same derivation as before the rename.
B8 resolved.

**what done means** `LineageRoot` is renamed `OriginRoot` and `lineage_roots()` becomes
`origin_roots()`, aligning the object-level vocabulary with `Derived.origin`. After this, "lineage"
unqualified means feature-level — the `lineage_id` and the edge log — and object-level provenance
is consistently "origin".

**files touched** `template_code/ag/core/data_objects.py:147` (the `TypeAlias`) and `:185`,
`:196`; `template_code/ag/core/locations.py:47`, `:87`;
`template_code/ag/core/policy.py:54`, `:98`, `:105`;
`template_code/ag/core/validation.py:53`, `:443`; `docs/refactor/01-terminology.md`;
`docs/refactor/02-runtime.md` §2.2.

**depends on** nothing.

**decision refs** B8.

**doc migration** resolves B8; updates the `01-terminology.md` entry.

**why it is independent** This touches existing, working code for a naming reason only. It has no
lineage dependency and can be done by anyone at any point — but it should be done *before* the
lineage vocabulary lands in the same documents, or both meanings of "lineage" appear in
`02-runtime.md` §2.2 simultaneously.

---

## 42. T7.3 — Consistency checks `[INDEPENDENT]`

**status:** done

**what done means** Two scripts, split by lifetime, each exiting non-zero so either can go
into CI unchanged.

- `docs/refactor/temp/check_consistency.py` — **temp-lifetime.** A-orphan, dangling-ref,
  ordering, B-referenced, and the two terminology checks that cover *A-id* citations.
  Deleted with this directory.
- `docs/refactor/check_terminology.py` — **permanent.** Every `file.md#anchor` an entry
  cites resolves, and every headword appears in the document it cites. These outlive the
  migration: after it, the authority column stops citing A-ids and starts citing ADRs and
  docstrings, and the same two questions still need answering. There are already 43 anchor
  citations predating the lineage work that nothing verified.

Each check's docstring records the defect that prompted it, and both carry the
green-by-coincidence note: a rule that never fires is worse than no rule.

**files touched** `docs/refactor/temp/check_consistency.py`,
`docs/refactor/check_terminology.py`.

**depends on** nothing.

**decision refs** none — this is tooling for the migration protocol, not a design decision.
Listed because new code with no owner is the exact orphan shape these scripts detect.

**doc migration** none. When temp/ is deleted, `check_terminology.py` stays and the
completion test's clause 4 becomes its permanent job.

**known failures on first run, not yet fixed** `check_terminology.py` reports two
pre-existing defects outside the lineage scope, left for a decision rather than silenced:

- `driven port` — `03-architecture.md:531` says "ports are **driven** (secondary)", never
  the noun phrase. Note `driving adapter` *does* appear, so the pair is inconsistent.
- `scale constant` — `02-runtime.md:343` describes the concept fully and never uses the
  words.

Both are one-line fixes in the authority document, the same fix `mint generation` got in
A9.10. Adding them to `HEADWORD_VARIANCE` instead would hide a real defect.

---

## 43. T7.5 — `run_partition_optimization` default bug `[INDEPENDENT]`

**status:** not started

**what done means** `PartitionRunConfig.run_partition_optimization` no longer defaults to
`require("SELECT_STUDY_AREA")` (`composition_configs/core_config.py:232`) — a raw environment
string, truthy even when it reads `"False"`, tied to an unrelated setting, and evaluated at import
time. Found by the N:1 real-data probe (2026-09-17), which had to pass `False` explicitly. The
same variable is parsed three different ways today (`generalization/n100/river/data_preparation.py:25`,
`generalization/n100/road/data_preparation_2.py:67-70`,
`generalization/n100/building/data_preparation.py:133`).

- one boolean parser in `paths.py` (`require_bool(name)`: `true`/`false`, case-insensitive,
  anything else raises);
- a dedicated `RUN_PARTITION_OPTIMIZATION` setting read through it, with the dataclass default a
  plain `False` and the caller passing the parsed value;
- `SELECT_STUDY_AREA` read through the same parser at its three sites.

Acceptance: `SELECT_STUDY_AREA=False` no longer enables optimisation; a unit test covers the parser
on `true`, `False`, `""` and an unset variable.

**files touched** `composition_configs/core_config.py`, `paths.py`, the three data-preparation
modules, `tests/`.

**depends on** nothing.

**decision refs** none — a defect in the current code, not a design item.

**doc migration** none.

---

## 44. T7.6 — Legacy lint baseline: undefined names `[INDEPENDENT]`

**status:** not started

**what done means** The six legacy files whose `F821` baseline entries in `pyproject.toml`
(`[tool.ruff.lint.per-file-ignores]`) exist because they use a name that is never defined are
fixed, and their entries are removed, so `ruff check` holds them to the full rule set. These
are latent `NameError`s, which is why they come before the rest of the baseline:
- `generalization/n10/landForms/hoydetall.py`
- `generalization/n100/road/testing_file.py`
- `generalization/n100/road/vir_test/test1.py`
- `generalization/n100/road/vir_test/test2.py`
- `generalization/n250/road/data_preparation_2.py`
- `generalization/n250/road/ramps_point.py`

Fixing means deciding per site whether the name was meant to be a parameter, an import or a
dead branch; it is a behaviour change in legacy code and is reviewed as one. `F821` has no
autofix.

**files touched** the six files above; `pyproject.toml` (entries removed).

**depends on** nothing.

**decision refs** A28.

**doc migration** none.

---

## 45. T7.7 — Legacy lint baseline: the remaining entries, per directory `[INDEPENDENT]`

**status:** not started

**what done means** Every remaining baseline entry (`F811` redefinition of an unused name,
`F841` unused variable, `F541` f-string without placeholders) is removed from
`pyproject.toml`, one reviewed change per directory, each by the developer who owns that
package; after the last one the baseline section of `pyproject.toml` is empty and the comment
introducing it is deleted. `F401` and `I001` stay held back on the legacy directories; that is
not part of this task. The entries, by directory:
- `custom_tools/generalization_tools`: `resolve_building_conflicts.py`, `resolve_road_conflicts.py`
- `generalization/n10`: `area_aggregator.py`, `eliminate_small_polygons.py`, `replace_uncategorized.py`, `ledning.py`, `hoydepunkt_innsjo.py`, `hoydetall.py`
- `generalization/n100`: `data_preparation.py`, `removing_points_and_erasing_polygons_in_water_features.py`, `extend_river_line.py`, `mst_loop.py`, `unconnected_river_geometry.py`, `clean_elveg_and_sti.py`, `data_preparation_2.py`, `ramps.py`, `resolve_road_conflict_preparation.py`, `testing_file.py`, `test1.py`, `test2.py`
- `generalization/n250`: `data_preparation_2.py`, `ramps_point.py`
- `repository root`: `main_on_cloud.py`
- `temp_skip_folder`: `gcs_client.py`
- `tests_legacy`: `test_arealdekket_class.py`, `test_category_class.py`

`F541`'s fix is safe and cosmetic (`ruff check --fix --select F541 <file>`); `F811` and `F841`
are fixed by hand, because removing a duplicate import or an assignment is a change a reviewer
should see. A directory counts as done when `ruff check` on it passes with no baseline entry.

**files touched** the files above; `pyproject.toml`.

**depends on** T7.6 (the undefined names first).

**decision refs** A28.

**doc migration** none.

---

# Found while writing this

Open items noticed during transcription. **None of these are resolved.** They are listed rather
than decided, per the constraint on this pass.

1. **A19 and A20 have `destination: TBD`.** Published identity has no ADR and no settled design
   (B3). The lineage query module does not exist, so A20's home is provisional.

2. **T1.3 and T4.11 have no test directory.** `tests/invariance/` is named in
   `01-terminology.md` as a driving adapter but does not exist, and there is no adapter conformance
   path. Someone has to choose.

3. **CLOSED — A14's capability check and the no-arcpy rule.** No exemption is needed. The probe
   runs at **adapter construction**, which already has arcpy; `validate()` takes the resulting
   capability record as an **argument** — data, not a call. `02-runtime.md` §8's "no cluster, no
   credentials, no data, no ArcPy" stands unchanged. Recorded in A14 and T4.10.

4. **CLOSED — A16's `I` is PROCESSING-only.** Completeness asks whether the stage lost something it
   was *responsible for*, and a stage is not responsible for reference data.

   Verified against the `DISPLACEMENT` stage rather than reasoned about: `buildings` (PROCESSING)
   flows through `simplify_polygons` and `propagate_displacement`, both `ONE + CARRY`, so every
   building id reaches `O` via `displaced` — assertion (1) holds. `displacement_feature` ids are
   minted by `build_displacement_feature`'s dissolve, so they are in `to_ids` — assertion (2)
   holds. The context road ids land in `T` via `from_ids` without ever entering `I`, and are not in
   `D` because the boundary diff does not call a row dropped when it appears in an emitted edge's
   `from_ids` — assertion (3) holds.

   **That verification surfaced B7**, which is a genuine hole and is not closed: a `Derived`
   `StageInput` can come from a previous run, carrying ids from that run's `minter_id` space.

5. **"Registry" is now overloaded three ways.** `StageRegistry` (existing), the dispatch registry
   (A10.3), and the work-key registry (A9.5). Ruled **keep, qualified** — `01-terminology.md` §2
   carries the collision entry and every use names which registry it means.

6. **T3.2's module has no home.** The work-key API is not a port, not an operation and not a
   helper in the current sense. `helpers/` or a new peer package — undecided.

7. **CLOSED — A7 now has per-item destinations.** Section-level migration was the risk: half the
   shadow-experiment technique written up and half not, with nothing recording which half. A7.1,
   A7.4 and A7.7 retire with `partition_iterator.py`; the other seven land in `02-runtime.md` §7 or
   §7.2. See the per-item table in DECISIONS.md under A7.

8. **`extract_vertex` (ONE + FOREIGN) has exactly one known caller**, `mst_loop.py:153` with
   `point_location="MID"`. That is enough to justify the split under A5.6, but it is thin, and the
   `START` / `END` positions may have no caller at all.

9. **B7 — cross-run `lineage_id` collision.** Found while verifying item 4. A `Derived` or
   `ProductIdentity` `StageInput` can resolve to a previous run's archived version
   (`pipelines/building/n100_stages.py:158`), whose ids were minted in that run's `minter_id`
   space. A10.2's uniqueness holds only within a run. Registered in DECISIONS.md as **B7**, not
   resolved.

10. **B8 — `LineageRoot` → `OriginRoot` is a code rename.** The collision ruling is settled but the
    work was not scoped; it touches `data_objects.py`, `locations.py`, `policy.py` and
    `validation.py`. Now **T7.2**.
