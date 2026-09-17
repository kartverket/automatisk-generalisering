# Lineage at a dissolve: what was tested, what it proves, how `lineage_id` is handled

**Status:** STAGING conclusion, 2026-09-17. It synthesises `n1_correspondence.md` (§1–§3.13),
`lineage_seam_readiness.md`, `PATCH-2026-09-17.patch` and the run logs under
`C:\temp\t0_1\logs\` (copies in `docs/refactor/temp/logs/`). Decisions quoted as *decided* are
either A-items in `DECISIONS.md`, items in the patch awaiting sign-off, or the user's four
decisions of 2026-09-17, each named where it is used. The patch is unapplied; this document does
not change it.

**How to read the labels.** Every claim carries one of three words. **Measured**: a number in a
named log or a findings section that quotes one. **Inferred**: a conclusion drawn from measured
numbers, with the reasoning stated. **Decided**: a rule someone chose, cited to its item. An
inference is never written as a measurement.

**Vocabulary** follows `01-terminology.md`: *parents* (which input rows produced an output row),
*row shape* (the per-output declaration `@row_shape(<output>=Rows(cardinality, ids, subject))`),
*lineage-bearing* (a handle whose declaration chain ends in `CARRY` or `MINT`), *combining rule*
(`dissolve(statistics=…)`), *mint* (allocate a `lineage_id` and record an edge). The word
"correspondence" is retired and appears here only in the findings file's name.

---

## 1. The question

A dissolve takes many rows and returns fewer. Under the identity model, every row of a
lineage-bearing handle carries one `lineage_id` (A9.1), and the relation "these inputs became
that output" cannot live in a scalar field, so it lives in **edges** (A11.1): `(operation, kind,
from_ids, to_ids)`. To write an edge for a dissolve, the runtime must know, for every output
row, the native indices of the input rows that were merged into it — its *parents*. A dissolve
that cannot report that is under-specified as a dissolve: "a statement about the geometry
operation, not about lineage" (A11.11). *Decided.*

Two facts about the port surface frame everything below. The row-shape grammar declares a
dissolve `GROUP + MINT` (A12.1, A12.11): many subject rows per output row, and new ids. And the
lineage facade, not the adapter, mints: the port reports parents "in its own vocabulary — native
indices; the layer above maps to `lineage_id`" (A11.11). So the investigation's question was
narrow: **by which mechanism does an adapter produce `(output_index, input_index)` pairs for a
dissolve, at what cost, and how far can the pairs be trusted?** Everything above the port was
already settled or is settled by the patch (§5).

---

## 2. What was tested

All runs on Windows, ArcGIS Pro 3.7.2 unless noted. The production image is `arcpy-linux:12.0`,
a Pro 3.6-era build (Dockerfile); nothing here ran in it.

| mechanism or fixture | run on | sizes | build | source |
|---|---|---|---|---|
| **CONCATENATE** statistic carrying a work key (A14 tier 2) | collinear 1 m segments, one key, one part | 10^5, 10^6 | 3.6.2 (2026-09-14 dry run), 3.7.2 (2026-09-15) | console pasted into `n1_correspondence.md` §3.8; no log file existed yet |
| **Statistics scope**: CONCATENATE + COUNT under `SINGLE_PART` | split-group lines (rows 1–3 touching, 4–5 100 m away), two squares 100 m apart; `PairwiseDissolve` and `Dissolve` | 5 and 2 rows | 3.7.2 | §3.9; `20260917_123529_statistics_per_part_or_per_group.txt` |
| **Native lineage table** (`out_lineage_table`) | split fixtures; collinear one part and two parts | 10^5 | 3.7.2 | §3.9 (2026-09-15 fast pass, pasted) |
| **Keyed resolver**, point locator, first version | split fixtures, boundary shapes, collinear one and two parts | ≤ 10^5 | 3.7.2 | §3.9; goldens in `docs/refactor/temp/goldens/` |
| **Synthetic ladders**: collinear one/two parts, lattice segmented, lattice long vertexed, lattice long plain; three locators vs the table | correctness at 10^2–10^4, timing at 10^4–10^5 | up to 10^5 | 3.7.2 | `20260917_180332_resolver_correctness_ladder_resolver_timing_ladder.txt` (the earlier `…164945` run is superseded, §9) |
| **Real ramps partition**: `PartitionIterator` on the ramps stage input, 35,000 elements, 500 m halo | `data_preparation___road_single_part_2___n100_road`, 2,038,774 rows → largest of 151 partitions | 36,407 rows | 3.7.2 | `20260917_143734_real_partition.txt`; probes `…150715`, `…161959`, `…163642` |
| **STRESS selection**: 250,000 elements, 5,000 m halo (no stage uses these) | same input → largest of 22 partitions | 267,429 rows | 3.7.2 | `20260917_171519_real_partition.txt`; probe `…181205` (the `…172545` run is superseded, §9) |
| **National chain input**: `run_dissolve_with_intersections`'s own input, probed whole | `data_preparation___road_single_part___n100_road` | 2,320,817 rows | 3.7.2 | `20260917_191748_real_data_group_sizes.txt` |
| **Ramps subset** of each real input (non-ramp centrelines within 400 m of ramps, what `dissolve_and_return_connection` sees) | inside each real probe | 1,451 / 11,468 / 109,825 rows | 3.7.2 | the probe logs above |

Two things were not tested and are listed so they are not assumed: any run in the Linux image,
and any polygon dissolve on real data (the polygon path was exercised on synthetic squares and
the goldens only).

---

## 3. What each result proves, and how far

### 3.1 Statistics are computed per dissolve key, not per output part

**Measured.** With `SINGLE_PART` output, both `PairwiseDissolve` and `Dissolve` wrote, on every
part of a key that split into two parts, the statistics of the whole key: `1;2;3;4;5` and
COUNT 5 on both line parts whose true parent sets are {1,2,3} and {4,5}; `1;2` and COUNT 2 on two
disjoint squares (`20260917_123529_…`, and the 2026-09-15 fast pass quoted in §3.9). Both
geometry types, both tools, Pro 3.7.2.

**What it proves.** A statistic cannot carry parents: on any key that splits, it names every
input of the key as a parent of every part. That alone retires CONCATENATE as a parents
mechanism, before any cost is considered. It also means the engine's own statistics option does
not implement the combining-rule contract, which is per output row (A9.11 in the patch; *decided*
there): the adapter must compute combining rules itself from the parents pairs (B17, *decided*
as the recommended mechanism).

**Limit.** Tested on two-part keys of five and two rows. Nothing suggests size changes it, and the
tool pages say nothing either way; it was not re-tested at scale because the conclusion does not
depend on scale.

### 3.2 CONCATENATE: growth, formatting, BIGINTEGER

**Measured** (§3.8, Pro 3.7.2): on one group dissolving to one part, CONCATENATE added 42.6–46.1 s
over a 1.4 s dissolve at 10^5 rows and 7,840.8 s over a 38.3 s dissolve at 10^6. Both cells were
complete: 100,000 and 1,000,000 tokens, every value parsed back, lengths 588,893 and 6,888,884
characters. LONG values were written in exponent form whenever that form is no longer than the
digits, ties to exponent (`1e+04`), with the locale's decimal comma (`1,2e+06`): 10 and 19 such
tokens. `BIGINTEGER` is rejected by every statistic, COUNT included (ERROR 003911).

**Inferred.** Between the two sizes the added time grows as n^2.23 (log10 of 7,840.8/46.1); the
findings file's earlier n^2.27 came from the 2026-09-14 pair 41.2 s / 7,595 s on 3.6.2. Two points
describe two numbers, not a law. The 10^6 figure is 2.2 hours against a one-minute budget
(A15.7 in the patch).

**Limit.** The locale formatting was observed on Norwegian Windows; the image's locale is
untested. A 15,930 s TEXT-key figure from the 2026-09-14 dry run has no surviving log and is
dropped, not confirmed.

### 3.3 The native lineage table: cost, omissions, availability

**Measured.** `PairwiseDissolve(..., out_lineage_table)` exists on Pro 3.7.2 (seventh parameter
in `arcpy.Usage` and `GetParameterInfo`), writes `OUTPUT_FID`/`INPUT_FID` at the given path
only, never at `<output>_Tbl`, and writes nothing for `MULTI_PART` (§3.9). Its cost, added over
the plain dissolve of the same rows:

| shape | rows | plain | added by the table | source |
|---|---|---|---|---|
| collinear, one part | 100,000 | 1.6 s | **110.4 s** | §3.9 (fast pass) |
| collinear, two parts | 100,000 | 1.3 s | 44.8 s | §3.9 |
| real ramps partition, five-field key | 36,407 | 3.3 s / 8.2 s (two runs) | **0.8 s / 0.7 s** | `…161959`, `…163642` |
| STRESS selection, five-field key | 267,429 | 15.0 s | 2.2 s | `…181205` |
| STRESS selection, one group | 267,429 | 14.2 s | 2.6 s | `…181205` |
| national input, one group | 2,320,817 | 157.5 s | 24.8 s | `…191748` |

On real data the table omits inputs: 5 of 36,407, 16 and 20 of 267,429, 76 of 2,320,817, and 12
of the 109,825-row ramps subset. Every one inspected is a two-vertex segment of 0.04–0.09 m, above
the 0.02 m XY tolerance, lying at distance 0.0 on a same-key part in **both** the plain and the
lineage output, with no same-key duplicate (`…163642`, `…181205`). The diagnostic's verdict for
all of them: *omitted parent* — the tool merged them and the table does not list them.

**Inferred.** The cost tracks the number of (input, part) pairs per part, not the row count: the
one-part fixture puts 10^5 inputs on one part and costs 110 s; real data has 1.1–1.24 inputs per
part and costs one to 25 seconds across two orders of magnitude of rows. Five points, consistent;
still a hypothesis, since no fixture varied inputs-per-part alone.

**What it proves.** The table is exact on everything but sub-decimetre segments, cheap on real
shapes, and unusable in production for two reasons that have nothing to do with cost: it does not
exist in the image, and it is not portable. It omits non-degenerate inputs under the degenerate
definition the project keeps (§5, decision 1), so as an oracle it is *qualified*: a conformance
case asserts resolver ⊇ table, not equality (B17, *decided*).

**Limit.** Measured on lines only; no polygon dissolve was run with the table on real data.

### 3.4 The plain and the lineage dissolve outputs are not the same output

**Measured.** With the table requested, the output had one more part than without (25,367 vs
25,366 on partition 18; `…161959`, `…163642`). Bucketed matching by key, length and centroid
found 14 lineage parts and 13 plain parts without an identical twin at 36,407 rows, 27/26 and
631/748 at 267,429 rows (five-field key and one group), 4,719/4,826 at 2.3 million rows as one
group (`…163642`, `…181205`, `…191748`). Every unmatched part had a same-key counterpart at
distance 0.0 whose length differed by centimetres: the two runs split the same chains at slightly
different places, clustered around the tiny segments.

**What it proves.** The tool page's "a slightly different algorithm is applied" means a
different output, not only a different part order. A locator compared against the table must run
on the lineage run's output; in production only the plain output exists, and that is what the
resolver runs on. The two are equivalent as geometry within tolerance and not identical as rows.

### 3.5 The segment locator reproduces the table exactly on every real fixture

**Measured.** The keyed resolver with the line locator that joins input lines to output parts on
a shared segment (`SHARE_A_LINE_SEGMENT_WITH`), key-filtered:

| fixture | rows | result against the table | `require_matched` | added over plain | source |
|---|---|---|---|---|---|
| ramps partition 18, five-field key | 36,407 | **pair sets equal**, partitions equal; pairs the 5 omitted inputs too | ok | 20.4 s | `…163642` |
| ramps subset of it | 1,451 | equal | ok | 2.9 s | `…163642` |
| STRESS, five-field key | 267,429 | **equal**; 10 of the 16 omitted inputs paired, 6 not | **raised, 6 unmatched** | 47.7 s (join 43.7 s) | `…181205` |
| STRESS ramps subset | 11,468 | equal | ok | 1.6 s | `…181205` |
| national ramps subset | 109,825 | equal; 6 of 12 omitted inputs not paired | **raised, 6 unmatched** | 41.7 s | `…191748` |
| every synthetic fixture at 10^2–10^4, including inputs split into up to 72 parts | ≤ 10,512 | equal on all | ok | ≤ 0.7 s | `…180332` |
| lattice segmented at 10^5 | 100,800 | (timing only) | ok | 5.4 s | `…180332` |

**The second pass is load-bearing on real data, not only on stress shapes.** *Measured*: on two
of the three real runs the segment locator left sub-decimetre inputs unpaired — 6 of 16 on the
STRESS five-field key, 6 of 12 on the national ramps subset — and each of them is non-degenerate
under decision 1 (0.04–0.09 m, above the 0.02 m tolerance), so `require_matched` raised
(`…181205` line "6 non-degenerate input(s) matched no output part", `…191748` likewise). Partition
18 passed only because the locator happened to pair all five there. Every one of those inputs
lies at distance 0.0 on a same-key part (§3.3), which is exactly what decision 2's proximity pass
resolves. *Inferred*: with the second pass the adopted line path passes on all three real runs;
without it, it fails on two. **Those segments are the second pass's test fixture**: the 16 and 12
OIDs are in the logs, and the pass is done when each is paired with the part it lies on and the
run prints the count resolved by proximity.

**Where it is not exact.** With a whole real selection dissolved as *one* group — a shape no
stage uses — inputs are split at every crossing of any road, and slivers shorter than an input
segment appear: 265 of 267,429 inputs with fewer parts than the table and 121 unmatched at STRESS
size; 719 fewer, 1,315 extra and 59 unmatched at 2.3 million rows, in 869 s (`…181205`,
`…191748`). On the 11,468-row ramps subset as one group, one input missed two parts of 0.3 m.

**Decided.** The segment locator is the line locator (B17, and the user's decision 4). It gains
a second pass (decision 2, §5.5) that closes the sliver class by proximity.

**Limit.** Real-data evidence is the ramps stage's input and its subsets; the two failure classes
are on geometry the pipeline should not produce (sub-decimetre segments, single-group national
dissolves). Cost at 10^6 real rows is not measured (§4).

### 3.6 The point locator's two failure modes

**Measured.** The locator that places one representative point per input part (half-length for
a line) and joins it to parts within tolerance:

1. **Inputs that become several parts.** On every synthetic fixture where an input is split
   (lattice long vertexed and long plain: parts per input up to 72) it pairs each input with one
   part and, where the point lands on a junction node, with the parts of crossing lines: 146
   inputs with fewer parts and 146 with extra at 10^4 (`…180332`). On the STRESS selection as one
   group: 2,937 fewer, 223 extra (`…181205`).
2. **Unmatched inputs on the real partition.** 904 of 36,407 inputs matched no part on partition
   18 (`…163642`), against 0 on the STRESS selection with the same code. The cause is **not
   established**; it is an open diagnostic (§8). It also crashed on the national input on a
   multipart geometry with an empty part ("attempted on an empty geometry", `…191748`); that
   guard is in place.

A variant that takes the point from `FeatureToPoint(INSIDE)` instead of a Python loop is faster
(3.8 s against 17.6 s at 10^5 on the segmented lattice, `…180332`) but misses the second part of
a multipart input on the goldens and 1,084 inputs on the two-part collinear fixture at 10^4.

**What it proves.** A single point cannot represent an input that the dissolve splits, and lines
are split at every same-key junction (§3.7). The point locator is therefore not a line locator.
For polygons and points — one label point per part, no splitting by a dissolve — nothing
measured here disqualifies it, but nothing on real data confirms it either.

**Decided.** Point locator for polygons and points, adopted pending the diagnostic of the 904
unmatched inputs (decision 4, §8): if the cause is line-specific, polygons close; if it is in the
points write step or the spatial join, the polygon path shares it.

### 3.7 Real line inputs are already planarised — for the ramps stage

**Measured.** On the ramps stage's input, an input becomes one part at the 95th percentile and
two at most, on the largest partition and on the STRESS selection under the five-field key
(`…163642`, `…181205`). Under one key over the whole selection the maximum is 25; over the
national input as one group, 223.

**Inferred.** Data preparation runs `run_dissolve_with_intersections` twice before the ramps
stage (`data_preparation_2.py:336-346`), and that chain planarises the network, so by the time
the ramps dissolve runs, same-key junctions already coincide with input endpoints. That is why
the five-field key barely splits anything and why the point locator's first failure mode does
not bite there.

**Scope of the statement.** It is about `road_single_part_2` only. It says nothing about the
national chain's own input, about other dissolve sites, or about any polygon input. The
single-group numbers show what happens when the key is coarser than the planarisation.

### 3.8 Real key sizes: partitioned stages versus the ingest chain

**Measured.**

| input | rows | largest key | parts it became | source |
|---|---|---|---|---|
| ramps stage, largest partition (35,000 elements + 500 m halo) | 34,780 + 1,627 halo = 36,407 | 15,392 (five-field key) | 13,310 | `…143734`, `…150715` |
| STRESS selection (250,000 + 5,000 m; no stage uses these) | 243,862 + 23,567 = 267,429 | 112,331 | 96,185 | `…171519`, `…181205` |
| national chain input, twelve-field key | 2,320,817 | 121,341 | (plain dissolve did not finish in 270 s) | `…191748` |
| national chain input, one group | 2,320,817 | 2,320,817 | 1,873,487 | `…191748` |

**What it proves.** No dissolve the pipeline runs has a 10^6-row *group*. The largest partitioned
group is 1.5·10^4 rows; the largest national one is 1.2·10^5, and its 155,944-part output group
(counted on the chain's output on 2026-09-15) is that key re-cut, not a larger input. What the
national chain has is a 2.3·10^6-row *call* whose plain dissolve alone exceeds four and a half
minutes, twice per run.

**Decided.** `run_dissolve_with_intersections` is ingest: it runs before `lineage_id` exists and
produces no parents (decision 3). Consequence: there is no traceability past data preparation,
and partitioning that chain is a precondition if traceability there is ever wanted. Its runtime
and container fitness are a separate task under the Kubernetes work (B20).

---

## 4. Cost and scaling, stated honestly

The budget (A15.7 in the patch, *decided*): lineage overhead under one minute added over a
commonly used GP tool, under five minutes and never over fifteen for fan-out and fan-in, measured
as time added over the bare tool on the same input.

**Measured points for the adopted line path** (segment locator, added over plain):

| rows in the call | largest key → parts | added seconds | of which spatial join | source |
|---|---|---|---|---|
| 1,451 (subset) | 687 → 503 | 2.9 | — | `…163642` |
| 11,468 (subset) | 4,755 → 3,463 | 1.6 | 1.4 | `…181205` |
| 36,407 (partition 18) | 15,392 → 13,310 | 20.4 | 5.1 | `…163642` |
| 100,800 (lattice, one key, one part each) | 100,800 → 100,800 | 5.4 | — | `…180332` |
| 109,825 (subset) | 47,312 → 31,735 | 41.7 | 40.5 | `…191748` |
| 267,429 (STRESS, five-field key) | 112,331 → 96,185 | 47.7 | 43.7 | `…181205` |
| 2,320,817 (national, one group) | 2,320,817 → 1,873,487 | 869 | 827 | `…191748` |

The fixed costs are small: reading both key lists at 10^5 rows takes about 0.06 s each, the
group-size pre-pass (a `Counter` over the dissolve field) 0.06 s at 1.66 million rows per second
(§3.9, `…150715`); the resolver's own Python is a few seconds at 36,407 rows.

**Inferred.** The cost is in the spatial join, and it tracks the number of (input, part) pairs
the join has to test, not the row count alone: the 100,800-row lattice costs less than the
36,407-row partition because every lattice input meets exactly one part and real roads meet
several candidates within the search extent. Pipeline data has about one pair per input (1.1–1.2
inputs per part), and on that shape the measured points are near-linear in rows.

**What is not established.**

- **The budget at 10^6 real rows.** A power fit through the two real five-field points
  (36,407 → 20.4 s, 267,429 → 47.7 s) extrapolates to roughly 150–180 s at 10^6; the measured
  2.3 million-row single-group call took 869 s. Neither is a budget claim: no stage dissolves
  10^6 rows in one call, and no such call was measured on the pipeline's key.
- **Polygon cost on real data**: nothing measured.
- **Any number in the image**: nothing ran there.

**The guard.** The group-size pre-pass is what stops an unexpected shape from becoming an hour:
the adapter counts rows per key before dissolving (0.06 s at 10^5) and knows the largest group
before any join runs. What it does with a group over a declared ceiling is A11.4a's two-ceiling
pattern applied to parents; the threshold is not set here.

---

## 5. How `lineage_id` is handled, end to end

One dissolve call, followed from the operation body to the edge log. Item numbers are the
authority; anything not yet decided is marked **OPEN**.

### 5.1 The call site

An operation body calls `tb.geometry.dissolve(input=roads, output=dissolved, fields=(ROAD_CLASS,))`
and, if it wants the parent set for its own logic, passes `parents=` a scratch handle (T2.4,
A11.15). Nothing at the call site names a mechanism, a tier or an engine; the toolbox call is the
same under every adapter (readiness audit §2.11). *Decided.* Under B18 (*decided*, option b)
`dissolve` is single-part by contract and takes no option; a multipart dissolve would be a
separate method. On lines, single-part output means one row per connected part **and a split at
every junction of the same key** (§3.7); the contract states it.

### 5.2 What the Protocol declares

On the port Protocol, not the adapter, `dissolve` carries
`@row_shape(output=Rows(cardinality=GROUP, ids=MINT, subject="input"))` (A12.1, A12.11): many
subject rows per output row, new ids, edges recorded. Its handle parameters are annotated `In`,
`Out`, and the parents out-param `ParentsOut` (A12.5a in the patch, *decided* there; the
`ParentsOut` marker is exempt from the rule that every `Out` has a row shape, because the parents
table is a relation the facade consumes, not a row-shaped output). The combining rule is typed
`statistics: tuple[StatisticSpec, ...]` with `Statistic ∈ {MIN, MAX, SUM, MEAN, COUNT}` (A9.12)
and evaluated over each output row's parents (A9.11).

### 5.3 The facade decides to ask for parents

The lineage facade wraps the port and reads `dissolve.__row_shape__` from the Protocol
(A11.11). The output is `MINT`, so if the subject handle is lineage-bearing (A15.6) the facade
passes **its own** scratch handle as `parents=` (A11.15 c). It does so on every `MINT` call whose
subject is lineage-bearing, whether or not the output is diff-tracked (A15.1). **OPEN**: A15.1's
"cheap even on context data" was written before the line cost was measured; whether to ask only
when the output is diff-tracked is listed for revisit under T4.14, and it changes the facade's
condition, not the port.

### 5.4 The adapter produces native pairs

The adapter's `dissolve` runs the engine's dissolve, then fills the parents table with
`(PARENT_ID, CHILD_ID)` rows in **native indices**, one per (input row, output row) pair, parents
from the `subject=` input only (A11.15 a). How, per geometry type (B17, *decided*, mechanism
adapter-internal per A14.1):

- **Before the tool**: a pass over the subject's size token rejects any null or empty shape with
  the row indices (`EmptyGeometryError`, T2.4's `ports/errors.py`); an empty polyline was seen to
  empty a whole dissolve output silently (§3.9).
- **Keys**: one pass counts rows per dissolve key on the input and on the output (the pre-pass).
  A key with one output part is resolved by attribute alone: every input with that key is a
  parent of that part. A key with several parts goes to the locator.
- **Lines**: the segment locator — one spatial join of the subject rows against the output parts
  on a shared segment, kept only where the part belongs to the same key as the input.
- **Polygons and points**: the point locator — one representative point per input part (a point
  guaranteed inside a polygon, the point itself for a point), one spatial join within the
  engine's XY tolerance, same key filter. Adopted pending the §8 diagnostic (decision 4).
- **Every pair is checked against its key** by the engine-free resolver: a pair whose output is
  not a part of the input's key raises (`LocatorContractError`). Cross-key coincidence — shared
  edges, overlaps — therefore cannot pair wrongly, because the locator never sees another key's
  parts.
- **Native sources where they exist**: `aggregate` and `collapse_to_centerline` read the engine's
  own parents table (their geometry moves, so no locator could be right); `clip` and `difference`
  stamp a work key on a copy of the input (A14.1). None of this is visible above the port.

### 5.5 The guard and the second pass

An input in no pair is not silently dropped. **Decided** (decision 1): *degenerate* means empty,
or length or area at or below the engine's XY tolerance; a point is never degenerate. **Decided**
(decision 2): before judging, the segment locator makes a second pass over inputs left without a
parent, within a small multiple of the XY tolerance: exactly one same-key part in range pairs;
several pair with all and are flagged; none raises. The count resolved by proximity is printed
per call. Then `require_matched`: any remaining unmatched input that is not degenerate raises
`UnmatchedInputError` naming the rows (T2.4's errors). A dissolve never discards non-degenerate
geometry, so an unmatched one means the precondition failed or the tool misbehaved, and the
lineage layer is never handed an absence to turn into `DROPPED`.

The 4–9 cm two-vertex segments the native table omits (§3.3) are non-degenerate under this
definition. They are a data-quality defect with its own task (§8), not a reason to widen the
guard. **And they are why the second pass is not optional**: on two of the three real runs the
segment locator left 6 of them unpaired and `require_matched` raised (§3.5); the second pass
pairs them with the part they lie on, at distance 0.0, and the guard then has nothing to raise
on. Until the data-quality task removes them, the second pass is what lets a real partition
dissolve without an error.

### 5.6 The facade maps pairs to `lineage_id`, carries or mints

The facade reads the native pairs and maps each input index to that row's `lineage_id` through
the id map (A15.3: disk-backed, sorted by lookup key; on this engine preferably a `join_field`
against a temporary table so the memory is the tool's). Per output row (A12.4): **one parent →
carry** its id, no edge; **two or more parents → mint** a new id from the pod's minter (A10.1:
signed 64-bit, negative for generated, `minter_id` in the high bits) and record the parents.
Ids are never collapsed back to a previous value (A11.3). The `lineage_id` column is created
unconditionally on the `MINT` output (A13).

### 5.7 Edges and DROPPED

Edges are emitted at the **operation boundary**, from net effect, not per port call (A11.4). Kind
is derived, never declared (A11.5): `PARENTS_CONSUMED` when every parent is absent from the
operation's outputs, `PARENTS_KEPT` when at least one survives, `CREATED` when `from_ids` is
empty. `DROPPED` comes only from the boundary diff — an input id that reaches no output and no
edge (A11.7) — and is promoted at fan-in only for features the job owns (A16.1). Completeness is
checked per stage from set membership, not from kinds (A11.6, A16). **OPEN**: B10's post-call
assertion that `lineage_id` survives every call on a lineage-bearing handle, and B14's plan-time
derivation of which port methods an operation calls (which A14.1's capability check needs).

### 5.8 What the domain gets

If the operation passed its own `parents=`, the facade writes the **same relation in
`lineage_id`** to the domain's handle — the same two columns, holding ids the domain can join —
because the native index is behind the port and the domain has nothing to join it to (A11.15 c,
A9.2). The port never receives the domain's handle. A domain `parents=` on a subject without
`lineage_id` raises in the facade before the port is called (A11.15 d). Combining rules the
domain asked for (`statistics=`) are computed by the adapter from the same pairs, per output row
(A9.11), never through the engine's statistics option (§3.1).

---

## 6. What this means for the other cardinalities

**1:1 (`ONE + CARRY`)**: ids ride along as attributes; no parents, no edge (A11.12). The open
question there is B10, that nothing yet asserts the column survives a tool.

**1:N (`MANY + MINT`)**: parents come from the engine's native reference where it exists —
`ORIG_FID` from `explode_multipart` and `split_at_points`, `FID_<input>` from `intersection`,
`TARGET_FID`/`JOIN_FID`, `IN_FID`/`NEAR_FID` and `InPoly_FID` for the `FOREIGN` methods — and from
a work key stamped on a copy of the input for `clip` and `difference`, whose tools emit none
(A14.1, findings §2). The facade mints per output row exactly as for a dissolve; the parents
table is the same shape.

**N:M**: none on the port surface (A5.4 deleted `union`; overlays declare one subject and a
context). The one N:M chain in the pipeline, `run_dissolve_with_intersections`, is ingest
(decision 3) and produces no parents.

**GROUP methods**, from the §1 inventory (*decided* in B17 and A14.1):

| method | mechanism | status |
|---|---|---|
| `dissolve` | keyed resolver: segment locator for lines, point locator for polygons and points | lines measured; polygons pending the §8 diagnostic |
| `buffer_dissolve` | keyed resolver with the input's own geometry for representative points, positive distances only | inferred from the dissolve results; not measured |
| `aggregate` | the engine's own parents table | documented; pass-through behaviour probed, result not yet recorded |
| `cluster_points` | the engine's table if the tool is `AggregatePoints` | the port's tool mapping is unrecorded |
| `collapse_to_centerline` | the engine's own parents table (geometry moves; nothing else can be right) | documented; the repository already reads it |

---

## 7. Portability

What carries to a non-ArcGIS engine, and what does not.

- **The pair table carries.** `(PARENT_ID, CHILD_ID)` in native indices is what every engine can
  produce and what the facade consumes; PostGIS `array_agg` or a spatial join yields it directly.
  It is the port's vocabulary (A11.11, A11.15) and the conformance suite's assertion.
- **The algorithm's preconditions carry, as statements.** Attribute join for single-part keys;
  for multi-part keys, a representative point of every input part lies within the engine's
  tolerance of the part it became, and no input of a dissolve is discarded unless degenerate. Both
  hold for any dissolve by construction and are checkable by any engine's spatial predicates.
- **Tolerance is an engine concept.** "Degenerate" and the locators' search radius are stated in
  *the engine's* XY tolerance, never in metres in a port contract (decision 1, readiness audit
  §2.10). Each adapter reads its own.
- **Line merging differs between engines.** Where an engine splits a merged line at junctions,
  and what it does with sub-resolution segments, is engine behaviour: this engine splits same-key
  junctions under single-part output and absorbs 4–9 cm segments into neighbours (§3.3, §3.7).
  Another engine will place splits elsewhere, so a cross-engine test compares the **partition of
  inputs into parents** and the lineage invariants, not output geometry or part counts.
- **What stays adapter-side**: the native table as an oracle (this engine only, 3.7 only), the
  work-key stamp for `clip` and `difference`, the specific join predicates, and the capability
  record's probe (A14.1).

---

## 8. Open items and where they live

| item | recorded in | blocks port design? |
|---|---|---|
| **Diagnostic of the 904 unmatched inputs** (point locator, partition 18): for 10 of them print the input OID, the representative point as computed and as read back from the points feature class, its distance to its own input and to the part the table lists, curves/Z/M on the input; compare the points feature class's spatial reference, XY resolution and tolerance with the input's; print the join's match option and search radius. Line-specific cause → polygons and points close; a cause in the points write step or the join → fix, re-run the polygon fixtures and goldens, then close | B17 (decision 4); T4.14 | no — adapter-internal |
| **Second pass** of the segment locator over unparented inputs, within a small multiple of the XY tolerance, count printed per call | decision 2; T4.14 harness | no |
| **Sub-decimetre input segments** (4–9 cm, two vertices): a data-quality task upstream of the dissolve, not a guard change | decision 1; new task to open | no |
| **National chain** (`run_dissolve_with_intersections`): ingest, no parents, no traceability past data preparation; its runtime (plain dissolve over 270 s, twice per run) and container shape are a Kubernetes-track task; partitioning is a precondition for any future traceability | decision 3; B20 | no |
| **The 16:48 geodatabase anomaly**: the same feature class read as 45,020 rows at 16:48 and 2,320,817 at 19:17, both in one run's outputs; the earlier read is discarded, the cause (a concurrent write, a stale state) is not known | `n1_correspondence.md` §3.13 | no |
| A15.1 revisit: ask for parents on every `MINT` call, or only when the output is diff-tracked, now that line cost is measured | T4.14 follow-ups | no (facade condition) |
| B14: plan-time derivation of which port methods an operation calls, needed by A14.1's capability check | B14; T4.10 follow-up | no |
| B10: post-call assertion that `lineage_id` survives a call | B10 | no |
| `cluster_points` tool mapping; `aggregate` pass-through result from `case_aggregate_pass_through` | T4.14 follow-ups | no |
| Polygon dissolve on real data: unmeasured | T4.14 | no |
| Anything in the Linux image: unmeasured (locale, `memory\` paths, the locators) | T4.11 case (1b) | no |
| `run_partition_optimization` defaulting to a raw `SELECT_STUDY_AREA` string | T7.5 in the patch | no |
| The patch's B17 text predates decisions 1–4 and still reads "conditional"; its closing wording is this document's §3.5–§3.8 and §5.5 | PATCH-2026-09-17 | no |
| **Column order of the parents table.** The port constants are `PARENT_ID, CHILD_ID` (T2.4) and the prose here writes the pair as (parent = input, child = output); the staging resolver's `ParentPair` is `(output_index, input_index)` and the native table's columns are `OUTPUT_FID, INPUT_FID`. One order has to be written into the port contract and the adapter mapped to it | T2.4; B17 | no — a docstring and one mapping |
| **The oracle describes a different output than production runs on.** Conformance compares the resolver against the lineage table on the lineage run's output (§3.4), while production resolves parents on the plain output, which the table never describes. The suite therefore proves the resolver on an output that differs from the production one by split placement; a case that runs the resolver on the plain output and checks its partition against the lineage run's partition would close the gap | T4.11 | no |
| **A real polygon partition run**: nothing polygon-shaped from the pipeline has been dissolved with parents; the point locator's real-data evidence is lines only, and the 904-unmatched diagnostic above decides whether that path is even sound | T4.14 | no |
| **Unmeasured costs**: the work-key stamp on a copy of the input for `clip` and `difference` (A14.1) has no timing at any size; and the group ceiling the pre-pass guards against (§4) has no value set, so today the pre-pass counts and nothing acts on the count | T4.14; A11.4a's pattern | no |

None of these blocks port or decorator design: the readiness audit's four blocking items
(A11.15, B18, B19, A12.5a) are drafted in the patch, and every row above is adapter-internal, a
facade condition, a runtime gap, or a data-quality task.

---

## 9. Chronology

- **2026-09-14 (Pro 3.6.2, dry run).** T0.1's gate: BigInteger refused by every statistic;
  CONCATENATE on LONG exact but exponent-formatted with a locale comma; a TEXT-key 10^6 run
  reported at 15,930 s (no log survives; dropped, `n1_correspondence.md` §3.1).
- **2026-09-15.** CONCATENATE re-measured: 46.1 s at 10^5, 7,840.8 s at 10^6 (§3.8). Local Pro
  upgraded to 3.7.2. Fast pass: statistics per group on both tools and both fixtures; native
  table at the given path, 110.4 s added at 10^5 one part; first point locator 0.4 s on the join
  path, 21.3 s on a two-part 10^5 key; boundary fixtures all equal to the table; goldens recorded
  (8). Findings file written; first B17 draft. **Wrong along the way**: the first gate compared
  the resolver's pairs on the plain output against a table describing the lineage output, and
  read the swapped part numbering as a mismatch; fixed by running locators on the lineage output
  and comparing partitions too. The B17 draft claimed same-key parts "cannot share a boundary";
  the junction fixture showed same-key line parts share nodes by construction, and the claim was
  rewritten (A14.1's text).
- **2026-09-17, morning.** Readiness audit (`lineage_seam_readiness.md`): ports and decorators
  can be designed once A11.15, B18, B19 and A12.5a land; the mechanism is adapter-internal.
  Patch drafted with those items, A14.1, A15.7, B17 open, T4.14; second locator (segment) and
  the lattice fixtures added; harness given a fixture cache, capped child runs and a size
  ladder.
- **2026-09-17, 14:37–15:09.** Export helper partitions the ramps input with `PartitionIterator`
  itself (151 partitions, 27 min); probe on partition 18: largest key 15,392 ≤ 34,780 + 1,627;
  table 4.6 s (no bracket yet); national count. **Wrong along the way**: the national count was
  made on the chain's *output* and its 155,944 read as an input group; corrected the same day to
  "indicative only", then replaced by the input count (121,341) at 19:17.
- **2026-09-17, 16:19.** Probe re-run with the plain bracket: table 0.8 s added over 3.3 s; five
  non-degenerate absent inputs; one extra part. **Wrong along the way**: the locator step read
  the key with the synthetic fixtures' field `grp` and failed; fixed by making the key fields a
  required keyword argument.
- **2026-09-17, 16:36.** Locators against the table on partition 18: segment exact in 20.4 s,
  midpoint 904 unmatched; the five absent inputs diagnosed as omitted 5 cm parents; the extra
  part traced to a different split placement.
- **2026-09-17, 16:48–17:25.** National count on the chain's input read 45,020 rows (discarded at
  19:17, §3.13); ladders and STRESS export (22 partitions, 6 min); STRESS probe. **Wrong along
  the way**: the resolver's pair validation kept one set of parts per input (inputs × parts
  memory); it ran out of memory on the STRESS key and on the 10^5 lattice, and had inflated every
  earlier 10^4 timing (midpoint 11.3 s → 2.7 s after the fix). Fixed, unit-tested at
  40,000 × 40,000, and re-run.
- **2026-09-17, 18:03–18:12.** Valid ladders and STRESS probe: segment 5.4 s at 10^5 lattice, 47.7 s
  on the 267,429-row five-field key, pair sets equal; single-group failure classes recorded.
- **2026-09-17, 19:17.** National chain input probed whole: 2,320,817 rows, largest key 121,341,
  plain dissolve over 270 s; as one group 157.5 s, table 24.8 s, segment locator 869 s; midpoint
  crashed on an empty part (guard added).
- **2026-09-17, evening.** The user's four decisions (degenerate threshold, second pass, the
  chain as ingest, B17's closing) and this document.

---

## Summary

- **Settled.** A dissolve reports parents as `(PARENT_ID, CHILD_ID)` in native indices through
  an out-param on every `MINT` method; the facade maps them to `lineage_id`, carries for one
  parent, mints for two or more, and derives edges and `DROPPED` at the operation boundary.
  Nothing about the mechanism appears at the call site or in a port signature.
- **Settled by measurement.** Statistics are per key, so CONCATENATE is dead twice over; the
  native lineage table is exact except on sub-decimetre segments, cheap on real shapes, absent
  from the image, and therefore a qualified oracle only; the segment locator reproduces it
  exactly on every real fixture at 20–48 s added over plain; the point locator cannot represent
  split inputs and is for polygons and points only.
- **Settled by decision.** Degenerate is the engine's XY tolerance; the segment locator gets a
  proximity second pass; the national dissolve chain is ingest with no traceability past it;
  no 10^6-row group exists in the pipeline.
- **Open.** Why 904 inputs went unmatched on partition 18, which gates the polygon path; the
  sub-decimetre segments as a data-quality task; the national chain's shape under Kubernetes;
  cost at 10^6 real rows and anything in the image, both unmeasured.
- **Take-away.** `lineage_id` at a dissolve is produced above the port from a pair table the
  adapter fills by joining inputs to the parts they became, key by key, with an error rather
  than a silent drop whenever a non-degenerate input finds no part.
