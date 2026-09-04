# Template code

**Status:** TEMPLATE — not shipped, not imported by anything in this repository.

**Owns:** nothing. Every design decision here belongs to a document or an ADR; this is
those decisions expressed as type-checked Python so they can be run, and so the source
tree in [03-architecture §7](../03-architecture.md#7-the-tree) is checkable with `ls`
rather than being prose that drifts.

**Does not own:** any decision. Where this code and a document disagree, **the document
is right and this is the bug** — with one exception, recorded below.

**Graduates when:** `src/ag/` exists. At that point `ag/` moves there wholesale and this
directory is deleted, not archived.

---

## Read this first

This is **not the system**. `ag/staging/scratch.py` is not the `ScratchFileManager` that
will run in a pod; it is what one would look like. Every module says so in its first
line. Nothing here is packaged, nothing is on `PYTHONPATH`, and no production module
imports it.

It exists for two reasons:

1. **It runs.** `tools/run_example.py` flattens two worked pipelines and prints the
   dependency graph, the topological order, per-stage internal-vs-exported handles,
   lineage against legality, the publication table, and placement — none of which is
   declared anywhere. If the derivation rules in 02-runtime are wrong, this is where it
   shows.
2. **It stops the documents drifting.** They already did once: an audit found the
   validation list wrong in five places, three code examples that would not run, a
   legality error, and an ADR numbering conflict. Co-locating the code with the docs
   makes the next drift a single reviewable diff instead of two directories nobody puts
   side by side.

## Running it

```
cd docs/refactor/template_code
python3 tools/run_example.py            # the whole derivation, end to end
python3 tools/dump_tuning.py n100 road  # resolved configs for one (scale, object)
pytest tests/                           # declaration tests; the arcpy one skips
lint-imports                            # the layer contracts in .importlinter
~/.local/share/nvim/mason/bin/pyright   # uses this directory's pyrightconfig.json
```

`conftest.py` puts this directory on `sys.path`; the two `tools/` scripts do the same
inline. The real distribution is installed, so `ag` resolves from the installed package
and none of that exists ([03-architecture §7.1](../03-architecture.md#71-srcag)).

Operations raise `NotImplementedError` with the tool sequence they would run. That is
deliberate: the design claim is about *declarations*, and every declaration is real.

## Layout

Mirrors [03-architecture §7](../03-architecture.md#7-the-tree) exactly, so the tree can
be diffed against the document rather than trusted.

| here | target | holds |
|---|---|---|
| `ag/core/` | `src/ag/core/` | types, data objects, handles, `@operation`, Stage, graph, policy, planning, locations, validation |
| `ag/sources.py` | `src/ag/sources.py` | every `ExternalSource` in the project. Leaf. |
| `ag/products.py` | `src/ag/products.py` | every `ProductIdentity`. Leaf. |
| `ag/classification_rules.py` | same | the whole policy, for a security reviewer |
| `ag/operations/<object>/` | same | operations, their config classes, and `tuning/` |
| `ag/tuning/scale/` | same | cartographic constants shared across objects |
| `ag/pipelines/<object>/` | same | the stage and pipeline declarations |
| `ag/staging/` | same | `workspace.py` (format), `scratch.py` (pod paths), `transfer.py` |
| `ag/runtime/` | same | `stage_entry.py` — the pod dispatch loop and output sweep |
| `ag/orchestrator/` | same | `execute.py` |
| `tools/`, `tests/` | repo root | dev scripts; declaration tests |

**Four packages are directories with only a docstring**, and that is deliberate:
`ports/`, `adapters/`, `helpers/`, `observability/`. They are designed and undecided
only in their details, so omitting them would make the tree read as "the port design is
not real" — the one misreading the documents work hardest to prevent. Each `__init__.py`
names what belongs there and links the section and ADRs that already settled it.

`runtime/` and `orchestrator/` are likewise partial: `fan_out`, `partition`, `fan_in`,
`jobs`, `metadata`, `log_merge` and `cli` are all designed and unwritten.

## The one place this code leads the documents

Everything else follows the docs. The exception, recorded so it is not read as drift:

**`ag/core/operations.py` has no `Toolbox`.** 02-runtime §2.4 and ADR-0008 say an
operation takes `tb: Toolbox` and calls ports; this template's operations name arcpy
tools directly in their `NotImplementedError` strings, because `ports/` is not written.
When it is, `@operation`'s parameter classifier must admit `Toolbox` as a fifth kind
alongside `In`, `Out`, `config` and `ScratchScope` — today it rejects anything else at
decoration. Noted in `ag/ports/__init__.py` too, where whoever does the work will be.

## What is verified, and by what

| claim | check |
|---|---|
| every declaration type-checks | `pyright` — 0 errors |
| the derivation rules produce the documented graph | `tools/run_example.py` |
| declarations need no data and no arcpy (02-runtime §2.6) | import with `arcpy` blocked |
| the layering in 03-architecture §4.1 holds | `.importlinter` |
| a misspelled parameter fails at import, not in a pod | `tests/unit/test_road_operations.py` |
| tuning resolves by reading, not computing (ADR-0013) | `tools/dump_tuning.py` |

## Conventions

- **`ag/pipelines/` and `ag/operations/` modules are worked examples**, and say `EXAMPLE`
  in their first line. Road is the fuller of the two: a genuine multi-origin join,
  multi-output operations, a non-adjacent stage edge, publication from a non-final
  stage, and per-output reclassification.
- **Everything else is the model itself** and says `TEMPLATE`. That distinction matters:
  copying an example is expected, copying `staging/scratch.py` into production is not.
- The building pipeline deliberately leaves one inconsistency standing —
  `N100_BUILDING_POLYGONS` is a `gs://` location for a product that computes
  `PREM_ONLY` with no `reclassify_to` — so `check_publications` has something real to
  catch. See `ag/pipelines/building/n100_stages.py`.
