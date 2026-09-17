# N:1 parents for `GROUP` port methods — findings, 2026-09-15

**Status:** STAGING finding. Nothing here is decided. Proposed text for `DECISIONS.md` and
`TASKS.md` is quoted verbatim in §6 and §7, ready to paste after review.

**Vocabulary.** The investigation prompt and this file's name say *correspondence*.
`01-terminology.md` §3 retires that word for **parents** (A11.1), so the text below says
parents, the code says `dissolve_parents` / `ParentPair`, and only the filename keeps the
prompt's word.

**Where the evidence comes from**, because the four kinds are mixed and must not be read as
one:

| kind | what |
|---|---|
| measured | the T0.1 Windows dry run on Pro 3.6.2, 2026-09-14/15. Only the scratch geodatabases survive (`C:\temp\t0_1\`); no stdout log was kept |
| documented | Esri tool pages fetched 2026-09-15 at `doc.esri.com` (the `pro.arcgis.com` URLs now redirect there) |
| search snippet | Esri Community pages that did not render through the fetch; only the search engine's summary of them was readable |
| inferred | arithmetic over the measured numbers, and reasoning from the settled A-items |

**Platform.** `Dockerfile` and `.devcontainer` pin `ghcr.io/kartverket/arcpy-linux:12.0`;
`requirements.txt` says the arcpy environment is "ArcGIS Pro 3.6 / Python 3.13". The prompt
says the local Pro is now 3.7.2; the dry run was on 3.6.2. **The image does not have
`out_lineage_table`** (new at 3.7, §3.5), so option B cannot run in production until the
image is rebuilt. Everything in the gate that says "Pro version" exists to record which
build produced which number.

---

## 1. Inventory of `GROUP` (N:1) and N:M port methods

Port methods from A12.11; arcpy tools from `03-architecture.md` §2.2 and T0.1's mapping
table; call-site counts are over the *current* repository (`generalization/`,
`custom_tools/`), which is where the tools are called today. (An earlier version of this file
said the template was absent from the checkout; it is at `docs/refactor/template_code/ag/`.
The counts stand: the template's operations raise `NotImplementedError` and call no tool.)

| port method | shape | arcpy tool | native parents output | moves geometry while merging | option C precondition | worst-case group size | call sites today |
|---|---|---|---|---|---|---|---|
| `dissolve` | GROUP + MINT | `PairwiseDissolve` (`Dissolve` at most sites) | **Pro 3.7+ only:** `out_lineage_table` → `OUTPUT_FID`, `INPUT_FID`, SINGLE_PART only ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/pairwise-dissolve.html)). `Dissolve` has none | no | **yes** — a dissolve never moves an input; every input part lies inside its output part | A15.5's blob: every road in a partition, 10^5–10^6 (T0.1 case 12) | `Dissolve` 52, `PairwiseDissolve` 5 |
| `buffer_dissolve` | GROUP + MINT | `PairwiseBuffer(dissolve_option=ALL\|LIST)` | none — the page says `ORIG_FID` is **dropped** for ALL and LIST ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/pairwise-buffer.html)) | no for a positive distance (adds area outward; the input lies inside its own buffer) | **yes for positive distances only**, with the *input's* representative point; a zero or negative distance breaks it | same as `dissolve` — `build_displacement_feature` is A15.5's case | `PairwiseBuffer` 16, `Buffer` 66; A5.6 counts 6 with `ALL` |
| `aggregate` | GROUP + MINT | `AggregatePolygons` | **yes**: `out_table` → `OUTPUT_FID`, `INPUT_FID`, default name `<out>_tbl`, "use this table to derive necessary attributes … from their source features" ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/aggregate-polygons.html)). The repo already passes `out_table` (`simplify_polygons.py:67`) | yes — gaps are filled and `ORTHOGONAL` reshapes; `minimum_area` **drops** small inputs | partial: an input that survives lies inside its aggregate; a dropped input has no output (correctly unmatched) | clusters of buildings within `aggregation_distance`: tens, not thousands | `AggregatePolygons` 4 |
| `cluster_points` | GROUP + MINT | **not recorded** in `03-architecture.md` §2.2; `AggregatePoints` is the obvious candidate | if `AggregatePoints`: **yes**, `<out>_Tbl` with `OUTPUT_FID`, `INPUT_FID` ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/aggregate-points.html)) | output is a polygon around the points | yes if the tool is `AggregatePoints` (points lie inside the hull); unknown otherwise | unknown; A5.6 already flags `minimum_count` as an unstated contract | `AggregatePoints` 0 |
| `collapse_to_centerline` | GROUP + MINT | `MergeDividedRoads`; `CollapseDualLinesToCenterline` | **yes, both**: `MergeDividedRoads(out_table=)` → `OUTPUT_FID`, `INPUT_FID` ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/merge-divided-roads.html)); the repo reads it at `ramps.py:3852`. `CollapseDualLinesToCenterline` writes `LeftLn_FID`, `RightLn_FID` on the output and carries no input attributes ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/collapse-dual-lines-to-centerline.html)) | **yes** — a new centreline between the carriageways | **no** | pairs by construction (2 → 1), plus unmerged roads 1 → 1 | `MergeDividedRoads` 8 |
| N:M | — | none on the port surface | — | — | — | — | A5.4 deleted `union`; overlays declare subject + context, not two subjects |

**Not on the port surface, but N:1 tools the repository calls today.** T2.9 and T4.2 should
decide whether each becomes a method, and if so which cell it lands in:

| tool | sites | native parents | note |
|---|---|---|---|
| `CollapseRoadDetail` | 5 | **none** documented ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/collapse-road-detail.html)) | replaces small configurations with "a simplified depiction"; geometry moves; would be A14 tier 4 |
| `CollapseHydroPolygon` | 8 | `InPoly_FID`, `InLine_FID` on the lines, plus `DecodeID` tables ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/cartography/collapse-hydro-polygon.html)) | polygon → lines is 1:N; `merge_adjacent_input_polygons` makes it N:M |
| `UnsplitLine` | 4 | none | this is `Dissolve(unsplit_lines=UNSPLIT_LINES)`; **`PairwiseDissolve` has no `unsplit_lines`** and `Dissolve` has no lineage table |
| `Eliminate` | 5 | none | polygons merged into a neighbour; geometry of the survivor grows, the eliminated one has no output |
| `DeleteIdentical`, `Integrate` | 8, 7 | none | not merges: a drop (boundary diff) and an in-place snap |

---

## 2. 1:N sanity check (`MANY` methods)

| port method | tool | native reference | needs a stamped index |
|---|---|---|---|
| `explode_multipart` | `MultipartToSinglepart` | `ORIG_FID` ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/multipart-to-singlepart.html)) | no |
| `split_at_points` | `SplitLineAtPoint` | `ORIG_FID` and `ORIG_SEQ` ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/split-line-at-point.html)) | no |
| `intersection` | `PairwiseIntersect` / `Intersect` | `FID_<input name>` per input under `join_attributes=ALL` or `ONLY_FID`; the fetched pages describe the options without naming the fields; **not `ORIG_FID`** — A14's "`ORIG_FID` from … `Intersect`" is wrong on the name | no, unless `NO_FID` is passed |
| `clip` | `PairwiseClip` | **none** — "all the attributes of the Input Features", no FID field ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/pairwise-clip.html)) | **yes** |
| `difference` | `PairwiseErase` | **none** ([page](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/pairwise-erase.html)) | **yes** |
| `extract_vertices` | `FeatureVerticesToPoints` | `ORIG_FID` — not re-fetched today; `line_topology.py` already relies on it | no |
| `validate_geometry` | `CheckGeometry` | `FEATURE_ID` — not re-fetched today | no |
| `spatial_join_all` | `SpatialJoin(ONE_TO_MANY)` | `TARGET_FID`, `JOIN_FID` — not re-fetched today; the locator in this finding depends on `JOIN_FID` | no |
| `all_neighbors` | `GenerateNearTable` | `IN_FID`, `NEAR_FID` — not re-fetched | no |
| `simplify.collapsed_points` | `SimplifyLine/Polygon` point output | `InLine_FID` / `InPoly_FID`, observed in the dry run (B16) | no |

**Neither works:** none found. `clip` and `difference` are the two `MANY + MINT` methods that
need A14's tier-2 stamp; a stamped work key survives both tools because they copy input
attributes.

---

## 3. Verification of the prompt's claims

### 3.1 Growth rate

Reproduced from the table's two points: log10(7595 / 41.2) = 2.27, log10(37.2 / 1.1) = 1.53.
Two points fix an exponent but cannot show it is a power law; "about n^2.27" is a description
of two numbers, not a law. The prompt's 7,595.1 s and 7,632.3 s are the same run: added over
plain, and total elapsed. **The 15,930 s TEXT figure has no surviving evidence**: `C:\temp\t0_1\` holds one 10^6
geodatabase (`concat_1000000_3.gdb`, finished 2026-09-15 05:48, the LONG run) and no log. My
notes from 2026-09-15 01:25 record the figure, which fits a run started at 20:52 on 09-14, but
its geodatabase is gone. Re-measure before citing it anywhere.

### 3.2 The plain dissolve is superlinear

Same two points; same caveat. It matters for option C only in that C adds a fixed pass on
top of whatever the dissolve costs; it does not change C's own growth.

### 3.3 Value formatting

The rule "exponent form when no longer than plain digits, ties to exponent" reproduces every
number in the prompt, by arithmetic rather than by re-running:

| size | plain digits | separators | exponent savings | predicted cell | prompt |
|---|---|---|---|---|---|
| 10^5 | 488,895 | 99,999 | 1 (`100000` → `1e+05`) | 588,893 | 588,893 |
| 10^6 | 5,888,896 | 999,999 | 11 (`100000`…`900000` save 1 each, `1000000` saves 2) | 6,888,884 | 6,888,884 |

Exponent tokens: 9 ties (`10000`…`90000`) + 1 at 10^5 = 10; 9 ties + 9 + 1 at 10^6 = 19. **The
tie rule is evidenced only by the token counts**, since a tie saves no characters. The locale
claim (`,` on Norwegian Windows) is from the dry run; the image's locale is untested, and
`_parse_tokens` already handles both marks.

### 3.4 BIGINTEGER rejected by every statistic

From the dry-run notes on 3.6.2, not re-verified. The tool page says nothing about
BigInteger; it only splits numeric fields (any statistic) from text fields. The re-check on
3.7.2 is the existing `_statistics_accepted` probe, printed at the start of
`case_concatenate_group_size`.

### 3.5 Statistics per group, not per part — unverified, and decisive if true

Both tool pages are silent. Search snippets of the Esri Community pages (the pages themselves
did not render) say the statistics "from all features that share the same dissolve field
values are calculated or concatenated — even if those features remain separate", name
**both** `Dissolve` and `Pairwise Dissolve`, cite NIM013409 and NIM035670, and say Esri
planned a fix via `PairwiseDissolve` for 3.7 — which is plausibly the lineage table itself.
Sources, all snippet-level:
[Ideas post](https://community.esri.com/t5/arcgis-pro-ideas/make-the-dissolve-tool-smarter-when-specifying-not/idi-p/924506),
[question thread](https://community.esri.com/t5/arcgis-pro-questions/question-regarding-dissolve-and-its-quot-create/td-p/1391618),
[older thread](https://community.esri.com/t5/geoprocessing-questions/dissolve-statistics-for-each-contiguous-unit-rather-than-all/td-p/213115).

If PairwiseDissolve behaves this way, two things follow, and the second is outside this
question's scope:

1. Option A over-attributes on every split group — a correctness defect, not a speed one.
2. **T2.10's `dissolve(statistics=((RANK, MAX),))` computes the combining rule over the whole
   group, not the part.** A9.10 and A11.14 treat the combining rule as domain logic the collapse
   executes; the engine would execute it at the wrong granularity on every group that splits.
   This does not contradict those A-items, but it means T2.10 needs the same probe before it
   relies on the tool. `case_statistics_per_part_or_per_group` runs both tools on both
   fixtures and prints the verdict.

### 3.6 The Pro 3.7 lineage table

Confirmed on the page fetched 2026-09-15 and in the 3.7 What's new list:

- syntax `PairwiseDissolve(in_features, out_feature_class, {dissolve_field}, {statistics_fields}, {multi_part}, {concatenation_separator}, {out_lineage_table})` — **the keyword is `out_lineage_table`**, seventh position;
- fields `OUTPUT_FID`, `INPUT_FID`, one row per participating input per output;
- created "only when `multi_part` is set to `SINGLE_PART` and a valid output table path is provided", **and** "will have the same name as the Output Feature Class with `_Tbl` appended" — both sentences are on the page; the gate records which one happens;
- "a slightly different algorithm is applied … slight differences in part order could occur";
- "could take a considerable amount of time depending on the size and complexity of the input".

`INPUT_FID` is an input ObjectID, so it needs the input's native index to be stable across the
call — exactly A9.2's contract, and T3.1's business.

### 3.7 The candidate method

Agreed in substance; three changes made in the implementation, each for a reason:

1. **The locator is handed the candidate parts, not only the inputs.** `PartLocator.locate`
   takes `LocateRequest(input_indices, output_indices)` per multi-part key, all keys in one
   call. Key filtering is then structural: the resolver rejects any returned pair whose output
   is not among that input's key's parts (`LocatorContractError`). The prompt's
   `locate(input_indices=…)` would leave filtering to each locator's discipline.
2. **No hit is reported, not swallowed.** `dissolve_parents` returns
   `ParentsResolution(pairs, unmatched_input_indices)`, and `require_matched` is the adapter
   contract on it: every unmatched input must be **degenerate** — empty geometry, or length
   (lines) or area (polygons) at or below the engine's XY tolerance; a point is never
   degenerate — or it raises `UnmatchedInputError` naming the inputs. A dissolve never drops
   non-degenerate geometry, so anything else means the precondition failed, and the adapter
   raises rather than let the lineage layer derive `DROPPED` from it. The adapter classifies
   (`degenerate_inputs`, reading only the size token by ObjectID); the resolver cannot. That is A14's own principle ("prefer an unavailable method to a silently wrong
   one") and the failure class T0.1 calls severe (silent truncation surfacing a stage later as
   A16's assertion 1). The resolver has no geometry and cannot classify; the adapter can.
3. **One bulk spatial join, not per-key loops.** A whole road category is one key with 10^5
   inputs and hundreds of parts; a Python loop is O(inputs × parts). The ArcPy locator writes
   one representative point per input part to `memory`, runs one `SpatialJoin` (one-to-many,
   intersect, search radius = the output's XY tolerance) against the dissolve output, and
   keeps a hit only when the part belongs to the same request as the point.

Two things the prompt's sketch places that are not decided here: the module location
(`adapters/_support/` is as good as any; the engine-free half must be importable by every
adapter and by the conformance suite) and whether the locator lives on the adapter or is
passed in.

### 3.8 Addendum: `case_concatenate_group_size` re-run on the current local build, 2026-09-15

Supersedes the numbers in §3.1–§3.4. The case does not print the Pro version;
`case_native_lineage_table` does. The user reports the local install as **Pro 3.7.2** on
2026-09-15; whether this run preceded or followed the upgrade from 3.6.2 is not in the
output, so the BigInteger rejection below is confirmed on 3.7.2 only if the run came after it.

| group | plain dissolve mean (spread) | COUNT added | CONCATENATE + COUNT added | cell length | exponent tokens | verdict |
|---|---|---|---|---|---|---|
| 10^5 | 1.4 s (0.2) | −0.1 s | **46.1 s** | 588,893 | 10 | complete, every value parsed back |
| 10^6 | 38.3 s (0.8) | −0.1 s | **7,840.8 s** | 6,888,884 | 19 | complete, every value parsed back |

- BIGINTEGER is rejected by CONCATENATE and by COUNT on this build too (ERROR 003911: "not of
  type SHORT | LONG | FLOAT | DOUBLE | TEXT | OBJECTID | DATE | GUID").
- The formatting rule is confirmed on all 24 probe values: ties go to exponent (`1e+04`),
  the decimal mark is the locale's comma (`1,2e+06`, `1,234e+08`), and every token parsed back
  exactly.
- Growth between the two points: CONCATENATE n^2.23, plain dissolve n^1.44.
- Against the one-minute budget (§6): 10^5 passes narrowly, 10^6 fails by two orders of
  magnitude. §4's conclusion on option A stands.

### 3.9 Addendum: the fast pass on Pro 3.7.2, 2026-09-15 (10^5 only)

The build is printed by the cases themselves: **3.7.2**. The second `case_concatenate_group_size`
run (42.6 s added at 10^5) was made after the upgrade was reported, so the BigInteger
rejection in §3.4 and §3.8 is a 3.7.2 result.

**Statistics are per group, not per part — verified.** Both `PairwiseDissolve` and `Dissolve`,
on the line fixture and the polygon twin: every output part carries `1;2;3;4;5` / COUNT 5 and
`1;2` / COUNT 2. §3.5's conditional is now unconditional: option A names the wrong parents on
every split group, and **T2.10's `dissolve(statistics=…)` combining rule executes over the
group, not the part**, on this engine. That is a mechanism defect under A9.10 and A11.14,
not a contradiction of them, and it needs a decision (§10).

**Native lineage table (option B), measured.**

| observation | result |
|---|---|
| keyword | `out_lineage_table`, seventh in both `arcpy.Usage` and `GetParameterInfo` |
| where written | **at the given path only**; `<output>_Tbl` is not created when a path is given |
| MULTI_PART with a path | no error, no table anywhere |
| fields | `OBJECTID`, `OUTPUT_FID` (Integer), `INPUT_FID` (Integer) |
| split fixtures | correct partition on lines and polygons |
| 10^5, one part | **110.4 s added** over a 1.6 s dissolve (114.1 s in the second run); table read 0.1 s; 100,000 rows, distinct `INPUT_FID` = group size |
| 10^5, two parts | 44.8 s added over a 1.3 s dissolve |

B already misses the one-minute budget at 10^5 on a single-part group, and by more on one
part than on two, so its cost is not a function of part count alone. The 10^6 figure is not
yet measured and may be hours.

**Option C, measured.**

| observation | result |
|---|---|
| pre-pass, 10^5 rows | `Counter` over one field 0.06 s (1.66 M rows/s); `(OID, key)` list 0.06 s; two-field key 0.07 s |
| 10^5, one part (join path) | **0.4 s added**; 100,000 pairs; every input paired once; pair set equal to the native table |
| 10^5, two parts (locator path) | **21.3 s added** (21.2 s in the locator); 100,000 pairs; every input paired once; partition equal to the native table (see the defect below) |
| shared edge, overlap, junction with distinct keys | correct, pair-for-pair equal to the native table |
| junction, one key | `SINGLE_PART` splits the three lines into **three parts** at the junction; resolver pairs each correctly and equals the native table |
| multipart input spanning two parts | input 3 pairs with both parts, `[[1,2,3],[3,4]]`, equal to the native table |
| zero-length inputs | see below |

**Defect in the first gate run, fixed.** At 10^5 two parts the pair sets differed while both
sides had one pair per input: the resolver ran on the plain dissolve's output and the table
described the lineage dissolve's output, whose part order is swapped — the page's "slight
differences in part order" warning, observed. Every locator now runs against the one dissolve
whose table it is compared with, and `compare_with_native` also reports the numbering-free
partition and the two per-input diagnostics.

**The zero-length fixture found something else.** A polyline built from two identical
points is stored as an **empty** geometry (`SHAPE@` reads back `None`), and with two such rows
in the input `PairwiseDissolve` produced **no output rows at all**, including for the normal
10 m line in the same key, with no error and an empty lineage table. **The tool emptied the
whole output silently.** The resolver reported all three inputs unmatched, which is the case
the adapter rule in §3.7 exists for: input 1 is not degenerate, so `require_matched` raises.

The adapter therefore has two guards, in this order: **before the tool**, `find_empty_geometries`
scans the size token of every input row and raises `EmptyGeometryError` with the offending
ObjectIDs, so the dissolve is never called on such an input; **after the tool**, the unmatched
rule above is the second guard for anything else the tool discards. Whether real pipeline data
carries empty geometries is a separate question for `validate_geometry`; the pre-call guard
does not wait for that answer.

**Note for A18 and `dissolve`'s docstring.** `SINGLE_PART` on lines does not mean "one feature
per connected group": it splits at every junction, so a Y of three same-key lines becomes
three outputs. The port contract should say so, because a caller reading "group" as
"connected component" would be wrong on every road network.

### 3.10 Addendum: the second pass on 3.7.2 — what the artifacts show

The four runs of §8 were made on 2026-09-15 (16:02–17:xx local). Their console output is
not in hand yet; the cache markers, the cached baselines and the copied goldens already say
the following.

**Goldens: 8 of 8 replay exactly** through `dissolve_parents` without ArcPy
(`test_goldens.py`). Per locator on the small fixtures:

| fixture | midpoint | feature_to_point | segment |
|---|---|---|---|
| shared edge, overlap, junction with distinct keys, split lines, split polygons, zero length | = native | = native | = native (lines) |
| junction, one key | = native (3 parts, 3 hits) | = native | = native |
| multipart input spanning two parts | = native (5 pairs) | **misses the second part** (4 pairs; one point per *feature*) | = native |

So `FeatureToPoint(INSIDE)` is disqualified as the point source for multipart inputs, as its
docstring predicted; it stays a candidate only where inputs are known single-part.

**Segment build method:** XYToLine 1.8 s against InsertCursor 12.3 s at 10^5; XYToLine is
cached and built every later fixture. The 10^6 collinear fixture took 14.1 s to build.

**Plain-dissolve baselines (cached, one measurement each):**

| fixture | 10^4 | 10^5 | 10^6 |
|---|---|---|---|
| collinear, one part | 0.53 s | 1.67 s | 36.95 s |
| lattice segmented | 0.90 s | 2.65 s | not run (no 10^6 fixture built: no locator was predicted under the timeout, or `--confirm-large` did not reach it) |
| lattice long vertexed | 1.52 s | 35.93 s | **5,087.93 s** |

The last number is the **tool's own cost**, before any lineage: dissolving 1,418 long lines
with a vertex at every crossing into about 10^6 single parts took 1.4 h, growing as n^2.15
between 10^5 and 10^6. The segmented lattice with the same output count dissolves in 2.65 s at
10^5. Whatever the locators cost on that fixture, the dissolve itself is two orders of
magnitude over the budget on that input shape, which is a finding about `SINGLE_PART` on
long vertexed lines rather than about parents. Whether real road data looks like (b) or (a)
is exactly what the real-data probe is for.

### 3.11 Real data, 2026-09-17

Three runs on Pro 3.7.2, logs under `C:\temp\t0_1\logs\` (`20260917_143734_real_partition.txt`,
`20260917_150715_real_data_group_sizes.txt`, `20260917_150945_real_data_group_sizes.txt`).

**The input and the partition.** `C:\GIS_Files\ag_outputs\n100\road.gdb\data_preparation___road_single_part_2___n100_road`,
the ramps stage's input, 2,038,774 rows (the national set). `n1_real_partition.py` partitioned it
with `PartitionIterator` itself, optimisation off, 35,000 elements and a 500 m radius (the ramps
stage's values, `data_preparation_2.py:403-407`): 151 partitions, 140 with processing rows,
27 min 8 s. The largest selection is **partition 18: 34,780 processing + 1,627 halo = 36,407
rows**.

**Partition 18, the five-field ramps key:**

| measure | value |
|---|---|
| distinct keys | 44 |
| largest key | 15,392 rows (`VegSenterlinje / T / Udefinert / P / enkelBilveg`) |
| verification | 15,392 <= 34,780 + 1,627: True |
| vertices per input p50 / p95 / max | 9 / 49 / 1,028 |
| plain dissolve / with the lineage table, capped child (second run, `20260917_161959_…`) | 3.3 s → 25,366 parts / 4.1 s → 25,367 parts; **table added over plain: 0.8 s** (the first run's 4.6 s had no bracket) |
| parts of the largest key | 13,310 |
| output parts per input p50 / p95 / max | 1 / 1 / 2 |
| inputs absent from the lineage table | 5, **none degenerate**: OIDs 8701, 11698, 12323, 22388, 35933; outcome decided by the per-OID diagnostic (next run) |

**The ramps subset** (`dissolve_and_return_connection`'s rows: non-ramp centrelines within 400 m
of ramps): 1,451 rows, largest key 687, plain 2.0 s and 2.9 s with the table (0.9 s added),
1,068 parts either way, parts per input max 1, nothing absent.

**National count, corrected.** The 12-field key counted over the same feature class gave
2,038,774 rows, 80,482 distinct keys, largest 155,944 (`Traktorveg`). That feature class is the
**output** of `run_dissolve_with_intersections` plus a multipart explosion
(`data_preparation_2.py:336-351`), so 155,944 is the largest group of the chain's output parts:
an **indicative figure only**, a bound in neither direction, since `FeatureToLine` splits rows.
The count that matters is on the chain's input,
`Road_N100.data_preparation___road_single_part___n100_road` (`file_manager_roads.py:126`; the
`MultipartToSinglepart` output at `data_preparation_2.py:331`), and is the next run.

**What follows, each with its scope.**

1. **10^6 is synthetic for partitioned stages.** The largest partition key is 15,392 against a
   36,407-row bound. T4.14's 10^6 confirmation is dropped for partitioned stages; for the
   national chain it stays open under B20 until the `road_single_part` count exists.
2. **The ramps stage's input is already split at junctions**: parts per input is 1 at p95 and 2
   at most, because the two `run_dissolve_with_intersections` rounds planarise the network before
   it. This is a statement about `road_single_part_2` only, not about the national chain's own
   input and not about any other dissolve site. On this input the point locator's interior-split
   weakness does not occur; the line decision for this stage rests on the midpoint-on-node risk
   and on measured time, which the next run provides by comparing both locators against the
   table on the partition itself.
3. **The native lineage table costs 0.8 s added over a 3.3 s plain dissolve on this shape**
   (36,407 rows, 1.2 inputs per part), against 110 s added at 10^5 on the collinear one-part
   fixture. "The cost scales with inputs per part" now has its bracket and stays a hypothesis
   until the STRESS single-key run puts one part-rich real group beside it. B remains
   unavailable in `arcpy-linux:12.0`, and portability keeps the keyed resolver as the production
   path; B is a possible ArcGIS fast path later, not a change now — **unless the diagnostic in
   item 4 shows the table omitting non-degenerate parents, in which case B is unfit as a fast
   path and an incomplete oracle**, and T4.11's `dissolve` oracle must be qualified.
3a. **The lineage run produced one more part than the plain run** (25,367 against 25,366 on the
   partition; equal on the subset). The tool page's "a slightly different algorithm is applied"
   is observed on real data as a different output, not only a different part order. Every
   locator is therefore compared against the lineage run's own output, never the plain one; the
   next run identifies the extra part by bucketed matching (key, length and centroid rounded to
   the XY tolerance) and names its contributing inputs.
4. **Five inputs absent from the lineage table** on the partition, none on the subset, and
   **none degenerate**: each has length above the XY tolerance and no pair. The next run's
   per-OID diagnostic decides among three outcomes: *dropped by the tool* (absent from both the
   plain and the lineage output, in which case `require_matched` raising is the right behaviour
   and the table is intact); *duplicate or overlap* with a same-key input that is in the table
   (a table convention to record); or *omitted parent* (lies on a lineage part and no duplicate
   explains it, the case that disqualifies B). The locators' fate for those five is reported
   beside it, not used as the rule.
5. **A15.5's worst case, as a partition produces it**: 36,407 rows in 44 keys, the largest 15,392
   rows becoming 13,310 parts; not a one-part 10^5–10^6 blob.

**Third run, 2026-09-17 16:36 (`20260917_163642_real_data_group_sizes.txt`): the locators, the
absent inputs and the extra part, all measured.** Plain dissolve 8.2 s this time (3.3 s in the
previous run: machine noise), with the table 8.8 s, **table added 0.7 s**; subset 1.6 s / 1.7 s.

| locator, partition 18 (36,407 rows, 25,367 parts) | added over plain | against the table |
|---|---|---|
| **segment** (`SHARE_A_LINE_SEGMENT_WITH`) | **20.4 s** (join 5.1 s; the rest is key reads and the resolver, to be split next run) | **pair sets equal, partitions equal**: all 36,403 table pairs reproduced, plus one pair for each of the five absent inputs; `require_matched` ok |
| midpoint (one point per part) | 31.3 s (points 5.8 s, write 6.2 s, join 3.1 s) | **904 non-degenerate inputs unmatched**, 905 matched to fewer parts than the table, `require_matched` raised |

On the ramps subset both locators reproduce the table exactly (0.7 s and 0.4 s).

**Decision this supports: the segment locator for lines.** It is exact where the table is
exact, it is cheaper, and the point locator misses 2.5 % of the inputs on real data (cause not
yet diagnosed; the point lands off its own part by more than the 0.02 m tolerance, or the
`memory` write loses precision — a follow-up, not a blocker, since the segment locator is the
candidate). Its 20 s on the largest ramps partition is under A15.7's minute, and about 15 s of
it is outside the join (key reads plus the Python resolver), which the next run splits out.

**The five absent inputs are 5 cm segments** (length 0.050–0.054 m, two vertices, above the
0.02 m XY tolerance, so non-degenerate under the current definition), each lying at distance
0.0 on a same-key part in *both* outputs, with no same-key duplicate. Outcome for all five:
**omitted parent** — the tool merged them and the table does not list them. The bucketed match
explains the extra part: the 14 lineage and 13 plain parts unmatched by bucket all have a
same-key counterpart at 0.0 m with a length differing by centimetres, and the ones carrying
absent inputs pair up as differently split chains around the tiny segments (lineage 21468 +
21469 = 126.08 m against plain 21589 + 21590 = 126.06 m, both with input 8701 on them). So the
two runs split the same chain at slightly different places near sub-decimetre segments, and the
lineage run drops those segments from the table.

**Consequence for B.** By the rule stated above, the native table omits non-degenerate parents:
**B is unfit as a fast path and is an incomplete oracle** as it stands. Two readings remain for
the user to choose between, and they are a definition question, not a mechanism one:

- keep "degenerate" at the XY tolerance: then the table is incomplete, the segment locator is
  the better oracle (it reported every table pair and the five more), and T4.11's `dissolve`
  case should assert *resolver ⊇ table* rather than equality;
- widen "degenerate" to segments the engine absorbs (here under about 6 cm, three times the
  tolerance, or under the XY resolution times some factor): then the table is complete under
  that definition, and the guard's threshold must be written as the engine's, not the
  tolerance's. The 5 cm segments are artefacts of `FeatureToLine` at near-coincident nodes,
  which argues for cleaning them upstream rather than for widening the guard.

Either way the segment locator's result stands.

### 3.12 Steps 2–5, 2026-09-17 (logs `…164844`, `…164945`, `…171519`, `…172545`)

**Step 2, the national count on the chain's input, is not comparable yet.**
`data_preparation___road_single_part___n100_road` holds **45,020 rows** (4,822 twelve-field keys,
largest 1,264), while its downstream `road_single_part_2` holds 2,038,774. Either the two feature
classes come from different runs (a study-area run and a national run; `data_selection_and_validation`
selects on `SELECT_STUDY_AREA`), or `FeatureToLine` multiplies rows 45-fold, which no road network
does. Until the user confirms which run produced each, the national key size for B20 is unknown;
if the two are from one run, the national dissolve's largest input group is 1,264 rows and the
155,944 output figure is entirely splitting.

**Step 3, the correctness ladder (10^2–10^4, against the native table):**

| fixture | midpoint | feature_to_point | segment |
|---|---|---|---|
| collinear one part, two parts | equal | equal, except **1,084 unmatched** on two parts at 10^4 | equal |
| lattice segmented | equal | equal | equal |
| lattice long vertexed (parts per input up to 72) | fewer parts **and** parts native does not list, at every size | same | **equal** |
| lattice long plain (crossings without vertices) | same failure | same | **equal** |

So on every fixture where an input becomes several parts, only the segment locator is right; the
point locators pair an input with one part and, when the point sits on a node, with crossing
lines' parts. This matches the real partition (§3.11).

**Step 3, the timing ladder** (added over plain, child interpreter): collinear one part 0.4 s and
0.6 s at 10^4 / 10^5 (join path). Lattice segmented 10^4: midpoint 11.3 s, feature_to_point 7.0 s,
segment 5.5 s. Lattice long vertexed 10^5 (450 inputs, 100,800 parts): midpoint 4.1 s,
feature_to_point 3.2 s, segment 11.0 s (join 8.8 s), fitted exponent 0.93, predicted 94 s at 10^6.
The first attempt at lattice segmented 10^5 and at the STRESS locators failed with `MemoryError`
(two timeouts were the same thing thrashing) in the resolver's own pair validation, which built
one set of the key's parts *per input* — inputs × parts entries, 10^10 on the STRESS key. Fixed
on 2026-09-17 (`dissolve_parents._located_pairs`, now one set per request; a 40,000 × 40,000 unit
test would have caught it) and re-run (`…180332`, `…181205`); the earlier 10^4 lattice numbers
were inflated by the same bug (midpoint 11.3 s then, 2.7 s now). **Valid ladder timings, added
over plain:**

| fixture, 10^5 | midpoint | feature_to_point | segment | segment fit → 10^6 |
|---|---|---|---|---|
| collinear one part (join path) | 0.7 s | — | — | — |
| lattice segmented (100,800 inputs, 100,800 parts) | 17.6 s | 3.8 s | **5.4 s** | 0.64 → 24 s |
| lattice long vertexed (450 inputs, 100,800 parts) | 1.4 s | 1.1 s | 9.4 s | 0.88 → 71 s |

Every locator is under A15.7's minute at 10^5 on every synthetic shape; the point locators are
cheaper where they are wrong.

**Step 4, the STRESS export** (250,000 elements, 5,000 m radius, no stage uses these): 22 partitions,
6 min 4 s; largest = partition 12, **243,862 processing + 23,567 halo = 267,429 rows**.

**Step 5, the STRESS probe** (re-run `…181205` after the resolver fix; the dissolve numbers from
both runs agree):

| | five-field key | whole selection as one group |
|---|---|---|
| largest key | 112,331 rows → 96,185 parts | 267,429 rows → 243,128 parts |
| plain dissolve / with table | 15.0 s / 17.2 s, **table added 2.2 s** | 14.2 s / 16.9 s, **added 2.6 s** |
| output parts per input p95 / max | 1 / 2 | 1 / **25** |
| inputs absent from the table | 16, all omitted parents, two-vertex segments of 0.04–0.09 m | 20, all omitted parents |
| parts unmatched by bucket, lineage / plain | 27 / 26 | 631 / 748 |
| **segment locator** | **47.7 s** added (join 43.7 s); **pair sets equal**, partitions equal; **6 of the 16 tiny absent inputs unmatched** → `require_matched` raised | 36.1 s; **not equal**: 265 inputs with fewer parts, 11 with extra, **121 unmatched** → raised |
| midpoint locator | 53.3 s (Python point loop 40.0 s); 2 fewer, 1 extra, 0 unmatched | 51.9 s; 2,937 fewer, 223 extra, 9 unmatched |

The ramps subset at this size (11,468 rows, largest key 4,755): both locators equal to the table
(segment 1.6 s, midpoint 2.7 s). As one group: segment misses two parts of one input (a 0.3 m
sliver part with two contributors, no shared segment found); midpoint 542 fewer, 5 extra.

**What this settles.**

- **On the pipeline's own key the segment locator is exact at every real size**: 36,407 rows in
  20 s, 267,429 rows in 48 s added over plain, under A15.7's minute even at seven times the ramps
  stage's partition limit. Its cost is the spatial join (92 % of it); the resolver and key reads
  are a few seconds. It is the line locator for B17.
- **Two residual failure classes, both on geometry the pipeline should not be producing:**
  (a) **sub-decimetre input segments** (4–9 cm, two vertices): the native table omits all of
  them, and the segment locator pairs some and misses others (6 of 16 here), so a "shared
  segment" test at the 0.02 m tolerance is marginal on them; (b) **sliver output parts** shorter
  than one input segment, produced when a single-key dissolve splits an input mid-segment at a
  crossing (single-group STRESS: 265 inputs of 267,429 affected; ramps subset as one group: one
  input, a 0.3 m part). Neither occurs on the five-field key at partition sizes, where the
  match is exact. The guard (`require_matched`) raised in both cases, as designed: the tool did
  not drop those inputs, the locator did not find them, and nothing became `DROPPED` silently.
- **Consequences to decide**: whether "degenerate" is defined by the XY tolerance (then both the
  table and the segment locator are incomplete on the 4–9 cm artefacts and the guard will raise on
  real partitions until they are cleaned upstream) or by a length the engine demonstrably absorbs
  (about 0.1 m here); and whether the segment locator gains a second pass for parts left without
  a parent — a `distanceTo` within tolerance against the same key's inputs — which would close
  class (b) at the cost of one more join on the unparented parts only.
- The native table's added cost stays at 1–3 s from 36k to 267k rows in one group (1.1–1.2
  inputs per part), so "cost scales with inputs per part" now has four points against the 110 s
  one-part fixture: consistent, still a hypothesis. It remains unavailable in the image and omits
  the tiny segments at every size.
- The lineage run's output diverges from the plain run's as the group grows: 1 part at 36k rows,
  27 at 112k, 631 at 267k as one group. Locators are judged against the lineage output when the
  table is the oracle; in production they run on the plain output, the only one that exists.

**STRESS** results above are a margin, never a partition's load.

### 3.13 The national chain's input, 2026-09-17 (`…191748`)

`data_preparation___road_single_part___n100_road`, the input of `run_dissolve_with_intersections`,
probed directly (no export: it is one unpartitioned call in the pipeline). **It holds 2,320,817
rows**, not the 45,020 the count-only run reported at 16:48 for the same path; the user confirms
both feature classes are from one run, so the earlier figure was read from a different state of
that geodatabase (a pipeline writing to it, or a stale copy) and is discarded. The chain's output
has 2,038,774 rows, so `FeatureToLine` does not multiply rows; it re-cuts them.

| | twelve-field key (the chain's own) | whole input as one group |
|---|---|---|
| rows / distinct keys | 2,320,817 / 80,482 | 2,320,817 / 1 |
| largest key | **121,341** rows (`Traktorveg`) | 2,320,817 |
| vertices per input p50 / p95 / max | 10 / 67 / 5,087 | same |
| plain dissolve | **TIMED OUT at 270 s**: the tool alone is over budget | 157.5 s |
| with the lineage table | not measured | 182.2 s, **table added 24.8 s** |
| output parts | — | 1,873,487; parts per input p95 2, **max 223** |
| inputs absent from the table | — | 76 |
| parts unmatched by bucket | — | 4,719 / 4,826 |
| segment locator | — | **869 s** (join 827 s); 719 fewer, 1,315 extra, 59 unmatched → raised |
| midpoint locator | — | raised `The operation was attempted on an empty geometry` (a multipart with an empty part; guard added) |

The ramps subset of the national input (109,825 rows, largest key 47,312 → 31,735 parts): plain
8.1 s, table added 0.4 s, segment locator **41.7 s, pair sets equal**, 6 tiny inputs unmatched.

**What follows.**

- **The national dissolve's largest input group is 1.2·10^5 rows**, the same order as the STRESS
  key and one below 10^6. The 155,944-part output group is that key re-cut, not 1,264 rows
  merged. T4.14 item 14 for the national chain: a 10^6-row *group* does not occur there either;
  what occurs is a 2.3·10^6-row *call*.
- **The unpartitioned national dissolve is over every budget by itself**: the plain dissolve on
  the twelve-field key did not finish in 270 s, and the pipeline runs that chain twice. This is
  B20's decision 3 with numbers: the chain has to become a partitioned stage (or be declared
  ingest, before `lineage_id`), and parents for it are a partition-size question, not a
  national one.
- As one group over 2.3·10^6 rows the native table still adds only 25 s (1.24 inputs per part),
  the fifth point for the inputs-per-part hypothesis; the segment locator's 869 s and its 2,034
  disagreements are what a single-group dissolve of a whole country looks like, and no stage does
  that.

---

## 4. Options, challenged

**A. CONCATENATE (tier 2).** Dead, on two measured grounds: 2.2 h at 10^6 against a
one-minute budget (§6), and wrong on every split group because statistics are per group
(§3.9). It is not an oracle either: an oracle that is right only on fixtures that do not
split cannot check the case that matters. **The native table is the only `dissolve`
oracle.** Tier 2's stamp survives for `clip` and `difference`, where the tool copies
attributes and nothing splits by key.

**B. Native lineage table.** Unavailable on the image, and **measured over budget at 10^5**:
110 s added on a single-part group against a one-minute budget (§3.9). Two structural limits
that C does not have: SINGLE_PART only, and it is `PairwiseDissolve`-specific, so it covers
neither `Dissolve(unsplit_lines=…)` nor `buffer_dissolve`. Its strength is that it is the
tool's own answer, which is what an oracle should be; the fixtures show it agrees with C on
every shape tried.

**C. Key join + spatial lookup.** Runs on both builds and on any engine with a spatial join.
Measured at 10^5: 0.4 s on the join path, 21 s on the point-locator path (§3.9), against
110 s for B and 43–46 s for A. Its correctness rests on a precondition that holds for
dissolve by construction; the boundary fixtures all agree with the native table.

**Which path is production depends on geometry type.** For polygons, A15.5's blob is a
single-part key and the join path is the common case. **For lines it is the opposite**: a
road key (`vegkategori`, `typeveg`, …) dissolves into many parts, since `SINGLE_PART` splits
at every junction (§3.9), so the locator path is the production path for every line
dissolve, not an edge case. That changes what the locator has to get right on lines, and it
is why there are two:

- the **point locator** (one representative point per input part) is complete only when no
  input is split by the dissolve. A line with interior vertices at junctions becomes several
  parts, and one point finds one of them; a half-length point that lands on a junction node
  is within tolerance of every part meeting there, including parts of crossing lines of the
  same key. Both are within-key errors the key filter cannot see;
- the **segment locator** (`SHARE_A_LINE_SEGMENT_WITH` between input lines and output parts)
  pairs an input with every part it became and with nothing that merely touches it. It is the
  candidate production locator for lines; the lattice fixtures (§8) measure both.

Open risk: the lattice timings at 10^5 and the fitted 10^6 prediction are not yet measured.

**Real data narrows this (§3.11), for the ramps stage only.** Its input is already planarised,
so an input becomes at most two parts and the interior-split case does not arise there; the
choice between the point and segment locators on that stage rests on the midpoint-on-node risk
and on measured time, and the primary evidence is the comparison of both locators against the
native table on the real partition, with the synthetic ladder second. The native table itself
cost 4.6 s with the table on 36,407 rows, far from the 110 s of the one-part fixture; that
does not change the production path, which stays the keyed resolver for portability and
because the image has no Pro 3.7, but it removes the budget objection to B as an ArcGIS-only
fast path later.

**D. C with B as fast path.** Dead on the numbers: B is the slow path at every size measured.

**Where I disagree with the review's lean:** nothing on the direction, one thing on the
framing. "C everywhere its precondition holds, B as the oracle" treats B as a test-only
artifact, but for `aggregate` and `collapse_to_centerline` the native table is the **only**
correct source (geometry moves, so C cannot hold), it is on the 3.6 image today, and the
repository already consumes it. B is the production path there, not the oracle.

### 4.1 Recommendation per method

| method | recommend | reason |
|---|---|---|
| `dissolve` | **C** in production on every build: the point locator for polygons, the segment locator for lines (pending the real-partition comparison, then the lattice numbers); **B** as the only conformance oracle, on builds that have it | C is the only path available on the image and portable; B's cost depends on shape (110 s at 10^5 on a one-part group, 4.6 s on a real 36,407-row partition, §3.11) and its part order differs from the plain run |
| `buffer_dissolve` | **C**, using the *input's* geometry for representative points, **for positive distances only** | no native output; with a positive distance the input lies inside its own buffer, so the precondition holds; a zero or negative distance (polygon shrink) breaks it and the adapter must reject it. Alternative compile: `buffer` (`ORIG_FID`) then `dissolve` (C) — same resolver, one extra tool |
| `aggregate` | **B** (`out_table`) | native, on 3.6, already used; geometry moves, so C is not guaranteed. An input absent from the table and from the output is a legitimate drop (`minimum_area`) |
| `cluster_points` | **B** if the tool is `AggregatePoints`; **undecidable** until the mapping is recorded | the docs never name the tool |
| `collapse_to_centerline` | **B** (`MergeDividedRoads(out_table=)`; `LeftLn_FID`/`RightLn_FID` for the dual-lines tool) | geometry moves; nothing else can be right. `CollapseRoadDetail`, if it ever becomes a method, is tier 4 |
| bespoke matcher | none needed | every method above has a native table or satisfies C |

---

## 5. What was built

| file | what | verified by |
|---|---|---|
| `docs/refactor/temp/dissolve_parents.py` | engine-free resolver: `DissolveKey`, `ParentPair`, `LocateRequest`, `PartLocator` (Protocol), `dissolve_parents()` → `ParentsResolution`, `require_matched` (the degenerate-or-error contract) | 15 unit tests, pyright clean |
| `docs/refactor/temp/test_dissolve_parents.py` | the tests, no ArcPy; `test_cross_key_pair_from_the_locator_is_rejected` fails if a locator does not filter by key; `test_unmatched_non_degenerate_input_raises` pins the adapter contract | `python3 test_dissolve_parents.py`: 15 passed (pytest is not installed on this machine; the file is pytest-collectable) |
| `docs/refactor/temp/arcpy_part_locator.py` | `ArcpyPartLocator` (point locator, `point_source` per part in Python or `FeatureToPoint(INSIDE)`), `ArcpySegmentLocator` (`SHARE_A_LINE_SEGMENT_WITH`), both with per-stage `last_timings`; `find_empty_geometries` / `assert_no_empty_geometries` (pre-call guard), `degenerate_inputs` (post-call classification) | pyright clean apart from the expected missing `arcpy`; the first point locator ran on 2026-09-15 (§3.9); the rest **not executed** |
| `docs/refactor/temp/n1_fixtures.py` | fixture cache with `.done` markers, cached baselines, the two segment writers, the collinear and three lattice generators, golden writer | compiles; lattice arithmetic smoke-tested; **not executed** |
| `docs/refactor/temp/n1_parents_gate.py` | the nine cases of §8, child-interpreter timing with timeout, the size ladder, `--confirm-large`, `--write-goldens`, the real-data probe | compiles; comparison diagnostics smoke-tested with a stubbed `arcpy`; **not executed** |
| `docs/refactor/temp/test_goldens.py`, `goldens/*.json` | no-ArcPy replay of the eight recorded goldens through the resolver | `python3 test_goldens.py`: 8 of 8 replayed exactly (recorded on Pro 3.7.2, 2026-09-15) |
| `docs/refactor/temp/t0_1_bigint_gate.py` | restored to its committed content, Black-formatted | compiles |

Location is staging, beside the gate, because the gate is what imports the modules and B17 is
still open; the template at `docs/refactor/template_code/ag/` is untouched, and the engine-free
half moves under `ports/` or `adapters/` when B17 resolves (T4.14).

**Status, 2026-09-17.** Everything in the table has now run on Pro 3.7.2 (2026-09-15): the
fixtures, the small cases, the correctness ladder at 10^2–10^4 and the timing ladder at 10^4 and
10^5, plus 10^6 for the collinear and long-vertexed fixtures. The goldens replay 8 of 8. The
console output of the ladders was not captured (no log file yet; T4.14's first harness item), so
their numbers are not in this file; the cache artifacts in §3.10 are.

Known unverified points, to read from the gate output: `memory\name` with a backslash on
Linux (the documented form; untested there); `FeatureToPoint(INSIDE)` needing an Advanced
licence; `XYToLine(line_type="PLANAR")` and `NumPyArrayToTable` into `memory` on this build;
the child interpreter's start-up time against the 90 s allowance.

---

## 6. Draft B-item for `DECISIONS.md` (paste-ready)

> **2026-09-17:** superseded by `findings/PATCH-2026-09-17.patch`, which drafts B17 as an open
> item, A14.1, A15.7 and the task rewordings as one reviewable patch. The text below is the
> 2026-09-15 draft, kept for the record.

Time budgets: **none are recorded in `DECISIONS.md` or `TASKS.md`.** The only figures are the
ones the user stated in conversation on 2026-09-15 — under one minute added over a commonly
used GP tool; under five minutes and never over fifteen for fan-out and fan-in. The draft
below cites them as user guidance and asks for them to be written down; it does not invent
others.

```
**B17. `GROUP` parents: the tier list in A14 is wrong on two facts and the production path is
not decided.** Found by the N:1 investigation of 2026-09-15
(`temp/findings/n1_correspondence.md`).

**Facts, verified against the tool pages on 2026-09-15.**

- Tier 1 undercounts native support. `AggregatePolygons(out_table=)`,
  `AggregatePoints` (`<out>_Tbl`) and `MergeDividedRoads(out_table=)` all emit an
  `OUTPUT_FID` / `INPUT_FID` table on Pro 3.6, and `CollapseDualLinesToCenterline` writes
  `LeftLn_FID` / `RightLn_FID`. The repository already reads the MergeDividedRoads table
  (`generalization/n100/road/ramps.py:3852`). Only `dissolve` and `buffer_dissolve` lack a
  native answer on the image.
- `Intersect` emits `FID_<input>` per input, not `ORIG_FID`. `PairwiseClip` and
  `PairwiseErase` emit no reference at all, so `clip` and `difference` are the two
  `MANY + MINT` methods that need tier 2's stamp.
- Tier 2 is unfit as the runtime path for `dissolve`, on two independent grounds, both
  measured on Windows Pro 3.7.2 on 2026-09-15. Cost: CONCATENATE over one 10^6 group adds
  7,841 s to a 38 s dissolve, 43–46 s at 10^5. Correctness: with `SINGLE_PART`, both
  `PairwiseDissolve` and `Dissolve` compute every statistic over the whole dissolve group
  and repeat it on each output part, so tier 2 names the wrong parents on every group that
  splits. The same holds for the `statistics=` combining rule T2.10 adds: it executes over
  the group, not the part.
- Tier 1 for `dissolve` (`out_lineage_table`) is new at Pro 3.7; the image is 3.6. Measured
  on 3.7.2: 110 s added at 10^5 on a single-part group, already over the budget below. The
  table is written at the given path only, and only for `SINGLE_PART`.
- The keyed resolver, measured on the same build: 0.4 s at 10^5 on a single-part group, 21 s
  on a two-part group, equal to the lineage table on every fixture including shared edges,
  overlaps, junctions and a multipart input spanning two parts.

**Proposal, not a decision.** Replace A14's tier 3 with a keyed spatial resolver as the
production path for `dissolve` and `buffer_dissolve`:

1. dissolve; 2. count output parts per key; 3. single-part keys resolve by attribute join;
4. multi-part keys resolve by one representative point per input part, joined to the parts of
   the same key within the XY tolerance; 5. an unmatched input is reported to the adapter,
   which raises unless the input is degenerate, since a dissolve never drops geometry.

The engine-free half (`dissolve_parents`, with `require_matched`) and two ArcPy locators
exist in `temp/` with unit tests and recorded goldens. Native tables stay the production path
where they exist (`aggregate`, `collapse_to_centerline`) and are the **only** conformance
oracle for `dissolve`, on builds that have one. CONCATENATE is retired outright: it is over
budget and, since statistics are per group, wrong on any fixture that splits, so it cannot
serve as an oracle either.

**Why tier 3's objection does not apply, and what replaces it.** A14 rejected spatial
reconstruction as "wrong at coincident boundaries". *Across* keys the key filter closes that:
the locator is handed only its own key's parts and the resolver rejects a cross-key pair, so a
shared edge or an overlap between keys cannot pair wrongly. *Within* a key the geometry
differs by type. Polygon parts of one key share at most a vertex, or they would have dissolved
together, so a label point cannot be ambiguous. Line parts of one key **share junction nodes
by construction** — `SINGLE_PART` splits at every junction — and that leaves two within-key
risks a point cannot avoid: an **interior split**, where an input with vertices at junctions
becomes several parts and one point finds one of them; and a **midpoint on a node**, where the
half-length point sits within tolerance of every part meeting there, including parts of
crossing lines. The line locator therefore matches by shared segment, not by point, and the
lattice fixtures measure both against the native table.

**Budget the results are judged against.** No figure is recorded in this file or in TASKS.md.
The user's guidance of 2026-09-15: lineage overhead on a commonly used GP tool under one
minute; fan-out and fan-in under five minutes, never over fifteen; measured as time added
over the bare tool, at A15.5's worst-case sizes. Record these as an A-item (A15.7?) when
this B-item resolves, so the next gate has a number to fail against.

**Affects.** T0.1 (five cases added, see the findings file), T4.10 (tier selection and "spatial
reconstruction is not implemented"), T4.11 (which oracle runs on which build), T2.10 (the
combining-rule granularity), T2.9 (`cluster_points`' tool is unrecorded; `UnsplitLine` has no
`PairwiseDissolve` form), A14 (rewording in the findings file §7).

**Also affects T2.10 directly**, and this is the part that touches settled ground: A9.10 and
A11.14 place the combining rule inside the collapse, and the engine executes it per group.
`dissolve(statistics=((RANK, MAX),))` on a road category that splits into parts gives every
part the category-wide maximum. **Recommended:** the adapter computes every combining rule
itself as a group-by over the parents pairs joined to the input attributes — per part by
construction, one pass over a table it already has, engine-neutral, and the same code for
every statistic the port names. "Single-part keys only" is not an option: it would exclude
nearly every line key, since `SINGLE_PART` splits at junctions. Accepting per-group semantics
would make the combining rule silently wrong on the common case. See §10 for the T2.10
wording.

**Resolves when** the 10^6 numbers for B and C are recorded beside the budget above, and the
T2.10 question has an owner.
`destination:` A14's replacement text; `adapters/arcpy/` package docstring; `02-runtime.md` §8
for the budget.
```

---

## 7. A14 wording that exposes the mechanism, with proposed rewording

A14's first sentence has the right shape: *"the layer above asks for parents and does not
care how they are produced."* The passages below contradict it.

| A14 / T4.10 text | problem | proposed wording |
|---|---|---|
| "Capability is **probed at adapter construction** by `arcpy.GetParameterInfo("analysis.PairwiseDissolve")` … and checked at plan time … a stage that dissolves on a lineage-bearing handle with an incapable adapter fails before fan-out" | the capability record is keyed on one vendor parameter, so plan-time validation learns *which tier* the adapter runs. Under the resolver every adapter can report `dissolve` parents, and the record should say *which methods*, not *how* | "The adapter publishes a capability record naming the `GROUP + MINT` methods for which it can report parents. How it reports them is adapter-internal and not in the record. `validate()` fails a stage that uses a lineage-bearing handle with a method the record does not name." |
| "3. **Reconstructed spatially.** Expensive and wrong at coincident boundaries. Prefer an unavailable method to a silently wrong one." | rejects the mechanism B17 proposes, on a ground the key filter removes | "3. **Resolved by key and location.** Attribute join for single-part keys; one representative point per input part against the same key's parts for multi-part keys. Unkeyed reconstruction stays rejected: prefer an unavailable method to a silently wrong one, and an unmatched non-degenerate input is an error, not a `DROPPED`." |
| "`ORIG_FID` from `MultipartToSinglepart` / `Intersect` covers most `MANY + MINT` cases" | `Intersect` writes `FID_<input>`; `clip` and `difference` have nothing | "`ORIG_FID` from `MultipartToSinglepart` and `SplitLineAtPoint`, `FID_<input>` from `Intersect`; `clip` and `difference` need the stamp. `AggregatePolygons`, `AggregatePoints` and `MergeDividedRoads` emit `OUTPUT_FID`/`INPUT_FID` tables; `CollapseDualLinesToCenterline` writes `LeftLn_FID`/`RightLn_FID`." |
| "2. … **This is what runs until the image is rebuilt**, and it stays as the fallback afterwards." | measured false on both grounds (§3.8, §3.9) | "2. **Synthesised via a work key.** The stamp that `clip` and `difference` need. For `dissolve`, CONCATENATE is retired: it is quadratic-plus in group size and, since statistics are per group, wrong on every split group. It is not an oracle either." |
| "Esri's lineage table is slow on large inputs and requires single-part output, so an adapter may prefer synthesis on size — an adapter-internal decision." | states a cost that was not measured, and "synthesis" now means the wrong thing | drop the sentence; the gate measures it |
| T4.10: "Spatial reconstruction is not implemented — an unavailable method is preferable to a silently wrong one." | same as tier 3 | "The keyed resolver is implemented once, engine-free, with the locator per adapter; unkeyed reconstruction is not." |
| T4.10: "selects a tier: native … work-key synthesis … or declared unsupported" | the tier vocabulary leaks into the task's acceptance | "reports parents for `dissolve` through the keyed resolver, for `aggregate` and `collapse_to_centerline` through the tools' own tables; probes at construction only for the oracle the conformance suite may use" |

One naming point outside A14: the prompt's `dissolve_correspondence` is `dissolve_parents` in
the code, per `01-terminology.md` §3.

---

## 8. Gate additions and how to run them

The N:1 cases now live in their own script, `docs/refactor/temp/n1_parents_gate.py`, with
the T0.1 conventions and the T0.1 helpers imported; `t0_1_bigint_gate.py` is back to its
committed content (Black-formatted). What moved it out: the fixture cache, the
child-interpreter timing and the size ladder.

**Test-speed discipline built in:** fixtures are built once per (shape, size, generator
version) under `<workdir>\fixtures` with a `.done` marker written last, and tools never write
into the cache; the plain-dissolve baseline is measured once per fixture and cached, with no
bracketing; each fixture is dissolved once per size and every locator runs against that
output; large timed runs happen in a child interpreter with a timeout of `--timeout-factor`
(default 3) times the one-minute budget plus interpreter start-up, and "TIMED OUT after N s"
is the recorded result; correctness runs at 10^2–10^4 against the native table, timing at 10^4
and 10^5, the exponent is fitted from those two and the 10^6 time predicted, and 10^6 runs
only with `--confirm-large` and only for a locator predicted under the timeout; the segment
build method (InsertCursor versus NumPyArrayToTable + XYToLine) is measured once at 10^5 and
the faster one cached.

| case | what it prints |
|---|---|
| `case_fixture_build_method` | InsertCursor against XYToLine at 10^5; writes the faster to the cache |
| `case_native_lineage_table` | the split-group checks and the MULTI_PART probe (timing was settled on 2026-09-15) |
| `case_statistics_per_part_or_per_group` | CONCATENATE + COUNT on both fixtures, both tools, verdict PER GROUP / PER PART |
| `case_aggregate_pass_through` | `AggregatePolygons(out_table=)` on two near squares and one far one: is the pass-through input listed |
| `case_boundary_fixtures` | shared edge, overlap, junctions (distinct keys, one key), empty geometries with the pre-call guard, multipart spanning two parts, both split groups; one dissolve with the table, every locator against it, per-input diagnostics, `require_matched`; `--write-goldens` records each |
| `case_group_size_prepass_timing` | key reads and the empty-geometry pre-check at 10^4 and 10^5 |
| `case_resolver_correctness_ladder` | every fixture (collinear one part, collinear two parts, lattice segmented, lattice long vertexed, lattice long plain) at 10^2, 10^3, 10^4 against the native table, pair for pair and as a partition, with "inputs matched to fewer parts than native" and "inputs matched to parts native does not list" |
| `case_resolver_timing_ladder` | collinear one part, lattice segmented, lattice long vertexed at 10^4 and 10^5, each locator in a child with the locator's stage split (points, write, join, read and filter), the fitted exponent, the predicted 10^6 time, and 10^6 when confirmed and predicted under the timeout |
| `case_real_data_group_sizes` | on a real N100 partition (`--real-fc`): the largest dissolve-key groups per geometry type and how many parts the largest key produces |

The lattice fixtures, all one key: (a) segmented, one input per cell edge with shared
vertices at crossings; (b) long lines with a vertex at every crossing, k even, so half-length
points fall on nodes; (c) long lines crossing without shared vertices, to see whether the
dissolve splits them. `size` is the target number of cell edges, so the three produce
comparable output part counts.

Commands, from the project root on Windows (the `:RunArc` runner passes arguments through),
in this order, each with stdout redirected:

```
python docs\refactor\temp\n1_parents_gate.py --workdir C:\temp\t0_1 --only case_fixture_build_method --only case_boundary_fixtures --only case_aggregate_pass_through --write-goldens > C:\temp\t0_1\n1_small.txt

python docs\refactor\temp\n1_parents_gate.py --workdir C:\temp\t0_1 --only case_resolver_correctness_ladder > C:\temp\t0_1\n1_lattice_correctness.txt

python docs\refactor\temp\n1_parents_gate.py --workdir C:\temp\t0_1 --only case_group_size_prepass_timing --only case_resolver_timing_ladder > C:\temp\t0_1\n1_timing.txt

python docs\refactor\temp\n1_parents_gate.py --workdir C:\temp\t0_1 --only case_resolver_timing_ladder --confirm-large > C:\temp\t0_1\n1_timing_1e6.txt
```

Then copy `C:\temp\t0_1\goldens\*.json` into `docs/refactor/temp/goldens/` and run
`python3 docs/refactor/temp/test_goldens.py`. The 10^6 native-table timing is not run: B's
production role is settled at 10^5 (§3.9) and it remains an oracle on small fixtures only.

**Real-data probe (T4.14 item 10), three runs in order.** "Worst" is the partition whose
selection, processing rows plus halo as `PartitionIterator` selects them, is largest, taken from
the ramps stage's input with the iterator's own code (optimisation off, 35,000 elements, 500 m
radius, `data_preparation_2.py:403-407`). Every run tees to `<workdir>\logs\`; `:RunArc` on the
named file.

1. Export helper, on `n1_real_partition.py`:
   ```
   :RunArc --workdir C:\temp\t0_1 --road-fc <path to data_preparation___road_single_part_2___n100_road> --scratch-gdb C:\temp\t0_1\real.gdb
   ```
   Prints the input row count, one progress line per partition (id, processing, halo, running
   max), and the exported path. Expect roughly rows / 35,000 partitions at 5–15 s each. Needs no
   `.env`: the helper gives the four import-time variables dummy values and applies the
   pipeline's arcpy settings (EPSG:25833, XY tolerance 0.02 m, resolution 0.01 m) itself.
2. Probe on the partition and on the ramps subset, on `n1_parents_gate.py`:
   ```
   :RunArc --workdir C:\temp\t0_1 --only case_real_data_group_sizes --real-fc C:\temp\t0_1\real.gdb\largest_partition
   ```
   Verification line: `largest key <= processing + halo rows`. The lineage dissolve runs in the
   capped child; a timeout reads "tool alone over budget on this shape".
3. National count only, the 12-field key of the unpartitioned `run_dissolve_with_intersections`
   (B20), on `n1_parents_gate.py`:
   ```
   :RunArc --workdir C:\temp\t0_1 --only case_real_data_group_sizes --real-count-only --real-fc <path to data_preparation___road_single_part_2___n100_road>
   ```

Note for the record: `dissolve_relevant_roads` in `ramps.py:163` is dead code; the live dissolve
is `dissolve_and_return_connection` (`ramps.py:256`), over non-ramp centrelines within 400 m of
ramps, which is what the second run's "ramps_subset" block measures.

---

## 10. Decisions this raises

1. **Adopt the keyed resolver as `dissolve`'s production path for polygons and points** (B17),
   with the native table as the conformance oracle on builds that have it. **Lines are
   conditional** on the comparison of both locators against the native table on the real
   partition (primary) and on the synthetic ladder (secondary). **10^6 is dropped for
   partitioned stages** (§3.11) and stays open for the national chain under B20 until the
   `road_single_part` count exists. Drafted as B17 in `PATCH-2026-09-17.patch`, beside this file.
1a. **Five inputs absent from the lineage table** on the real partition: degenerate, or a table
   defect? The next run classifies them; if any is non-degenerate, the oracle itself has a gap
   to record before it judges the resolver.
2. **T2.10's `statistics=` executes per group on this engine.** Recommended: the adapter
   computes combining rules as a group-by over the parents pairs joined to the input
   attributes; the tool's own `statistics_fields` is never used. This touches A9.10 and
   A11.14's mechanism, not their rule. Draft wording for T2.10's "what done means", to paste:

   > - `dissolve` takes a `statistics` parameter so a collapse can state its combining rule
   >   (`statistics=((RANK, MAX),)`), making A9.10's requirement expressible.
   > - **The adapter computes every statistic per output part from the parents pairs joined
   >   to the input attributes, never through the engine's own statistics option.** Measured
   >   on Pro 3.7.2 (2026-09-15): with `SINGLE_PART`, both `Dissolve` and `PairwiseDissolve`
   >   compute statistics over the whole dissolve group and repeat the value on every part,
   >   so a `MAX` on a road category that splits at junctions would be the category-wide
   >   maximum on every part. Restricting the parameter to single-part keys is not an
   >   alternative: `SINGLE_PART` splits lines at every junction, so nearly every line key
   >   is multi-part.
   > - Consequence: `statistics=` depends on the parents mechanism (T4.10) and lands after
   >   it, and its conformance case asserts per-part values on a fixture whose key splits.
3. **Record the time budgets in DECISIONS.** Every judgment in this file cites figures that
   exist only in conversation.
4. **`SINGLE_PART` on lines splits at junctions.** State it in `dissolve`'s contract (T2.9,
   A18), since "group" is not "connected component".
5. **Empty geometry silently empties a dissolve.** Decide whether `validate_geometry` or the
   adapter's unmatched-input rule is the guard, or both.

---

## 9. Claims in the prompt I could not verify, or found wrong

| claim | status |
|---|---|
| 7,595 s CONCATENATE at 10^6 (table) and 7,632 s (ratio) | the same run: added over plain, and total elapsed; re-measured as 7,840.8 s added (§3.8) |
| 15,930 s TEXT run at 10^6 | **no surviving evidence**; only my session notes. Re-measure |
| n^2.27, n^1.53 | arithmetic reproduced; two points, not a law |
| formatting rule and both cell lengths | reproduced by arithmetic; the tie-to-exponent half rests on token counts, not lengths |
| Norwegian decimal comma on the Linux image | untested |
| BIGINTEGER rejected by every statistic | **confirmed on 3.7.2** (ERROR 003911, CONCATENATE and COUNT) |
| statistics per group, not per part | **confirmed on 3.7.2, both tools, both fixtures** (§3.9) |
| "Those sources are about Dissolve, not PairwiseDissolve" | moot: PairwiseDissolve measured the same |
| `out_lineage_table` keyword | **confirmed** on the page, in `arcpy.Usage` and in `GetParameterInfo` on 3.7.2 |
| "both 'a valid output table path' and '`_Tbl` appended'" | **measured**: written at the given path only; `_Tbl` not created; nothing for MULTI_PART |
| "different algorithm, part order may differ" | **observed**: the lineage run numbered the two 10^5 parts in the opposite order to the plain run |
| "lineage calculation can be slow" | **measured**: 110 s added at 10^5, over the one-minute budget |
| local Pro is 3.7.2 | **confirmed** by the cases' own print |
| A14's "`ORIG_FID` from … `Intersect`" | **wrong**: `FID_<input>` |
| A14's tier 1 list | **incomplete**: three tools with native tables on 3.6 are missing |
| `03-architecture.md` names `cluster_points`' tool | **it does not** |
| worst-case group size from code | the ramps stage partitions at 35,000 elements (`data_preparation_2.py:403`); **measured** on its input: largest partition 36,407 rows incl. halo, largest key 15,392 rows → 13,310 parts (§3.11) |
| "is 10^6 a real size?" | **no for partitioned stages** (15,392 of 36,407). **Open for the unpartitioned national chain** (B20): 155,944 is an indicative figure from that chain's output, not its input; the `road_single_part` count is pending |
| the first national count (155,944) | **misread once** as the input group size; it was counted on `road_single_part_2`, the chain's output after `FeatureToLine`, which splits rows and so bounds nothing |
| `CheckGeometry`, `FeatureVerticesToPoints`, `SpatialJoin`, `GenerateNearTable` field names | from memory and repository usage, not re-fetched today |
| `memory\name` on Linux, `search_radius` at 0.001 m, `positionAlongLine` on zero length | untested locator behaviours; the gate output will show them |
