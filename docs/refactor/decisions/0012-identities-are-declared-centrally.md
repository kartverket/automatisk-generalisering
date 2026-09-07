# ADR-0012: Sources and products are declared once, centrally, as symbols

**Status:** Accepted

**Supersedes:** the per-pipeline source declaration described in
[02-runtime §2.2](../02-runtime.md#22-data-objects).

## Context

The earlier model had one type, `Source`, covering both external data and other
pipelines' products, declared independently by each pipeline that read it. Value
equality on `(scale, dataset)` linked the independent declarations, with `location`,
`classification` and `data_type` all `compare=False`, and `check_sources_agree`
reconciling location disagreements after the fact.

Two defects followed, and only one of them was the one the check looked for.

**A silent misclassification path.** `classification: Classification | None = None`
made omission the path of least resistance. Two declarations of `NVDB_Roads` — one
stating `PREM_ONLY`, one omitting it — compared equal, hashed equal, and linked as one
identity. `policy.classification_of` joins over the `Source` objects reached by *that
pipeline's* wiring, so the omitting pipeline computed `CLOUD_OK` for restricted data
and scheduled itself into the cloud. No error anywhere: `check_sources_agree` compared
locations, and legality was not what it compared.

**A product with no location.** `Publish` named a `dataset` string and nothing else, so
the only place a location for `(N100, Road)` existed was the *consuming* pipeline's
`Source` declaration. A product's destination was written down by whoever happened to
read it, and a product nobody consumed had no location at all. `01-terminology` named
an identity registry mapping `(scale, dataset)` to a location; no such artifact
existed.

## Decision

Two leaf modules, and a type split.

**`sources.py`** holds every `ExternalSource` in the project. `classification` is
**required** — no default, not optional. `eq=False`.

**`products.py`** holds every `ProductIdentity`: scale, dataset, and location.
`eq=False`. **No `classification` field.**

Both sides of a publication reference the symbol:

```python
Publish(obj=ROAD, identity=N100_ROAD, reclassify_to=Classification.CLOUD_OK)
StageInput(obj=N100_ROAD, handle=Selection.raw_roads, role=InputRole.PROCESSING)
```

`import-linter` contracts keep both modules leaves.

## Consequences

**A new restricted source is a `TypeError` at import** until someone states its
legality, and it appears as a diff in one reviewable file.

**`check_sources_agree` is deleted.** With one declaration site there is nothing to
reconcile, and the `compare=False` markers went with it.

**`identity_producer` is a lookup keyed on an object**, not a `(scale, dataset)` string
match. `check_no_self_read` likewise. Find-references on `N100_ROAD` answers "who
produces this and who reads it" in one query.

**`ProductIdentity` carries no classification, deliberately.** The legality of
something we produce is computed over the stage wiring that produced it, and the single
human assertion that generalization removed a restriction lives on `reclassify_to`, at
one auditable point. A classification on the identity would be a second, unreviewed
home for that judgement, and the two would drift.

**`policy.classification_of` gained a case it could not previously express.** A
`ProductIdentity` some pipeline here publishes resolves to that stage's computation
*with the Publish's `reclassify_to` applied*, so a consumer reading a declassified
product gets `CLOUD_OK` rather than the producer's raw `PREM_ONLY`. An identity nothing
here publishes falls back to rules and fails closed.

**The reviewer property moved up a level rather than being lost.** Each pipeline's
objects module used to be "the only place location and legality are declared *for this
pipeline*". `sources.py` is now the one file showing everything entering the *project*,
under what restriction — strictly more useful than one file per pipeline showing a
slice.

**"No pipeline imports another pipeline" is preserved.** That property was the reason
for independent re-declaration; it survives, because pipelines import a leaf rather
than each other.

**`locations.py` gained an owner for environment prefixing.** With external locations
in one place, the four remote-path builders — `scratch_location`,
`scratch_dump_location`, `payload_location` and the archive location — moved into one
module, and the argument for why writing run-scoped data to the runtime environment's
own storage is always equally or more restrictive is stated once rather than in one
docstring of the four.

**ADR-0003 enumerates `DataObject` as `Source` / `Derived`** in its context paragraph. It is now
`ExternalSource | ProductIdentity | Derived`, and the same sentence's "carries identity, lineage,
legality and a remote location" is true only of `ExternalSource` — `ProductIdentity` carries a
location but no classification, `Derived` neither. The decision that ADR records — `ScratchHandle`,
not `DataObject`, at the port boundary — is unaffected, and if anything strengthened: a port that
took a `DataObject` would now have three types of planning vocabulary to drag into every adapter
instead of two. Recorded here rather than by editing ADR-0003.

## Also decided here

**`Scale` and `ObjectName` are `StrEnum`.** They reach four path builders, the
coarser-feeds-finer check, run selection, and published product names. `StrEnum` so a
member renders as its value in an f-string and no path builder has to remember
`.value`. `RAW` folded in as `Scale.RAW`. A closed `ObjectName` means adding an object
edits a shared module; at single digits of objects changing once a year, that is the
intended trade.

**`scale` and `object_name` stay repeated on every `Stage`.** Two to nine call sites per
pipeline, enum members so a typo does not compile, and a `Stage` that could not say
what it is without a `Pipeline` lookup would make every consumer of a bare `Stage`
worse. `check_stage_tags_match_pipeline` confirms agreement at plan time — it cannot be
an import-time check, because the `Stage` is constructed first.
