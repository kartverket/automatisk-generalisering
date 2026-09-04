# Migration

**Status:** TARGET — not yet implemented

**Owns:** what changes in the current codebase, in what order, and the measurements that
justify the port split.

**Does not own:** the target design. Runtime is [02-runtime](02-runtime.md), structure is
[03-architecture](03-architecture.md), vocabulary is [01-terminology](01-terminology.md).

**Deleted when:** the migration completes. This document does **not** graduate — it is
disposable by construction. Anything in it still worth knowing at that point has already
become an ADR.

---

## 1. What dissolves

`custom_tools/` is six different things and splits six ways:

| current | destination |
|---|---|
| `general_tools/custom_arcpy.py` | `adapters/arcpy/`; `SelectionType`/`OverlapType` replaced by CQL2-named `Relation` |
| `general_tools/geometry_tools.py` (2327 lines) | `helpers/lines.py`, `points.py`; primitive parts become port methods |
| `general_tools/line_topology.py` (6581 lines) | per [03-architecture §3.3](03-architecture.md#33-decomposition-line_topologypy) |
| `general_tools/{isolated_line_remover,line_segmenter}.py` | `helpers/lines.py` |
| `general_tools/polygon_processor.py` | `helpers/polygons.py` |
| `general_tools/line_to_buffer_symbology.py` | `helpers/lines.py` |
| `general_tools/append_features.py` | likely a `GeometryOps` method |
| `general_tools/graph.py` | `adapters/networkx/graph_ops.py` |
| `general_tools/partition_iterator.py` (2142 lines) | `runtime/fan_out.py` + `runtime/fan_in.py` |
| `general_tools/file_utilities.py` | `staging/` |
| `general_tools/validation.py` | arcpy existence/count checks → port methods |
| `general_tools/print_logger.py` | `observability/`; its `global_config` path building dies with the layout |
| `general_tools/param_utils.py` | dissolves with the config model |
| `general_tools/study_area_selector.py` | `tools/` at repo root |
| `generalization_tools/{building,road}/*` | `operations/building/`, `operations/road/` |
| `development_tools/*` | `tools/` at repo root |
| `decorators/timing_decorator.py` | `observability/` |
| `decorators/partition_io_decorator.py` | delete, already dead |

| current | fate |
|---|---|
| `paths.py`, `GIS_FILES_ROOT`, `env_setup/project_layout.py` | gone. Layout is not a concept when storage is not a tree. |
| `file_manager/**` (15 modules; `file_manager_buildings.py` alone declares ~187 files) | gone. Declared handles are per-stage symbols; intermediates get no entry at all. |
| `data_orchestrator/**` — `PIPELINE_INPUT`, `data_validator`, `FolderSpec`, `find_gdb` | gone. External inputs are `ExternalSource` declarations in `sources.py`; other pipelines' products are `ProductIdentity` in `products.py`. ADR-0012. |
| `BaseFileManager` / `ProjectLayout(GIS_FILES_ROOT.parent)` | gone. Same reason. |
| `WorkFileManager._modify_path`, `_session_prefix`, `_global_counter` | gone. Scratch paths carry no scale and no project layout; names need only be unique within a pod. |
| `PartitionIterator`'s object/tag two-level key | collapses to a single name. |
| `constants/n100_constants.py` | splits by what each value *is*: cartographic facts about the map to `tuning/scale/n100.py`, road-specific values to `pipelines/road/tuning/n100.py` as a `replace` delta. ADR-0013. |
| `composition_configs/core_config.py` | the enums that name a real runtime distinction survive in `core/types.py`; `WorkFileConfig` and the partition IO/run configs dissolve into `Stage` fields and `ScratchFileManager`. |
| `composition_configs/logic_config.py` (728 lines) | dissolves into port signatures and one frozen config dataclass per operation, declared beside the operation and valued in the tuning modules. The `*Kwargs` classes are the right shape already; what changes is that IO and plumbing come out, leaving only what is tuned. ADR-0013. |
| `temp_skip_folder/core/infrastructure/archive/` | six-method `ArchiveClient` ABC → two-method Protocol; three clients → `adapters/storage/`. |
| `env_setup/environment_setup.py` | arcpy env config → `adapters/arcpy/session.py`. |

The present design routes cross-pipeline flow through the archive while intra-pipeline flow
goes through a registry: two mechanisms for one thing. Removing that accident is what makes
this a real migration rather than a relabeling.

The image split (slim orchestrator, heavy runtime) falls out of the import direction for
free but does not justify the structure: one orchestrator pod per run against K partition
pods means the heavy image dominates pulls.

---

## 2. The terminology rename

An earlier draft of these documents used "container" for a `.gdb` or `.gpkg`, which collides
with the OCI sense. The current vocabulary:

| was | is |
|---|---|
| container (of data) | workspace |
| `ContainerFormat` | `WorkspaceFormat` |
| stage / operation container | stage / operation workspace |
| pod workspace | pod scratch root |
| `staging/container.py` | `staging/workspace.py` |
| `staging/workspace.py` | `staging/scratch.py` |

The last two rows are target module names; the executable companion keeps `staging` as one
module and splits later.

The rename was applied to [`template_code/`](template_code/README.md) in the same pass that produced ADRs
0011–0013 — `ContainerFormat` → `WorkspaceFormat`, `stage_container()` / `operation_container()`
→ `stage_workspace()` / `operation_workspace()`, and the prose that argued for the old word. No
code carries the old names.

This section exists only for readers of the earlier drafts and goes when they do. The durable
part is the retirement of "container" for data, in
[01-terminology §3](01-terminology.md#3-retired-and-discouraged).

---

## 3. Sequencing

1. **The partition-invariance harness** (K=4 vs K=16 diff) against the *current*
   implementation. [02-runtime §7.2](02-runtime.md#72-partition-invariance-is-testable--build-it-first)
   calls this the one thing to start now: it finds today's violations mechanically, and it is
   the only credible answer to "did the rewrite preserve semantics" for geometric logic. It
   gets harder once the old implementation stops running.
2. **`ports/table_ops.py` + `ports/geometry.py` + arcpy adapter + contract tests.** Smaller
   and less contentious than geometry, and it forces the cursor and `Geometry`-value
   decisions early — the ones most likely to be wrong and most expensive to reverse.
3. **`ports/geometry_ops.py` + the `Predicate` algebra + adapter + contract tests**, for one
   real stage's worth of operations.
4. **`.importlinter` contracts**, as soon as two of the layers in
   [03-architecture §4.1](03-architecture.md#41-the-rules) exist.

---

## Appendix A: measurements

Run from the repo root. Every command re-runs; the value of this appendix is that the numbers
can be regenerated rather than trusted.

| measure | value | command |
|---|---|---|
| tool call sites, modern form, by toolbox | 2578 total — management 1728, da 485, analysis 262, cartography 78, edit 13, other 12 | `rg -o --no-filename "arcpy\.(management\|analysis\|cartography\|conversion\|edit\|da\|topographic\|gapro\|sa)\.[A-Za-z_]+" -g '*.py' . \| cut -d. -f2 \| sort \| uniq -c \| sort -rn` |
| tool call sites, legacy `arcpy.Foo_management()` form | 223 | `rg -o --no-filename "arcpy\.[A-Za-z]+_(management\|analysis\|cartography\|conversion\|edit\|ddd\|sa\|na)\b" -g '*.py' . \| wc -l` |
| **tool call sites, total** | **2801** | sum of the two above |
| cartography toolbox, both forms | 78 across 16 distinct tools (ThinRoadNetwork 21, MergeDividedRoads 9, CollapseHydroPolygon 8, …) | `rg -o --no-filename "arcpy\.cartography\.[A-Za-z_]+\|arcpy\.[A-Za-z]+_cartography\b" -g '*.py' . \| sort \| uniq -c \| sort -rn` |
| cursor call sites | 483 (no legacy `arcpy.SearchCursor` form present) | `rg -o --no-filename "arcpy\.da\.(Search\|Update\|Insert)Cursor" -g '*.py' . \| wc -l` |
| make-layer/select triple | 616 (modern 567 + legacy 49) | `rg -o --no-filename "arcpy\.management\.(MakeFeatureLayer\|SelectLayerByLocation\|SelectLayerByAttribute)\|arcpy\.(MakeFeatureLayer\|SelectLayerByLocation\|SelectLayerByAttribute)_management" -g '*.py' . \| wc -l` |
| `CopyFeatures` (materialisation, counted separately) | 282 (modern 266 + legacy 16) | `rg -o --no-filename "arcpy\.management\.CopyFeatures\|arcpy\.CopyFeatures_management" -g '*.py' . \| wc -l` |
| files importing arcpy | 113 of 257 `.py` | `rg -l "^\s*import arcpy" -g '*.py' . \| wc -l` |
| `line_topology.py` | 6581 lines | `wc -l custom_tools/general_tools/line_topology.py` |

Use `rg -o … | wc -l` rather than `rg -c`: `-c` counts matching *lines*, which undercounts
lines holding more than one call.

The cartography share — 78 of 2801 tool call sites, 2.8% — is the basis for the three-port
split in [03-architecture §2.1](03-architecture.md#21-the-six). It is a call-site count in
this repository, not a claim about arcpy's surface area.

The make-layer/select triple and `CopyFeatures` are listed separately because they are
different concerns: the triple is the selection idiom that
[ADR-0001](decisions/0001-selection-is-a-predicate-value.md) replaces, while `CopyFeatures`
is materialisation and survives as `select`'s output write.
