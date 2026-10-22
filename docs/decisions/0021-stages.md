# ADR-0021: Stages: identities, inputs and execution

**Status:** Accepted, 2026-10-22.

**Scope:** `ag/core/pipeline.py`, `ag/generalization/sources.py`,
`ag/generalization/products.py`, `ag/core/locations.py`, and the stage-level model that
fan-out, fan-in and resume implement. Absorbs A31.1 to A31.7. Partition ownership (A6, A7, A8)
joins when it migrates.

Related: ADR-0019 (what crosses a port), ADR-0020 (operations), ADR-0017 (row shape; section
RS-2 relates to ST-2).

## Direction

1. Every external source and every product is declared once, centrally, as a symbol, and both
   sides of a publication reference the symbol. The legality of what we produce is computed
   over the wiring, never declared on the product.
2. A stage input declares a role, which tells fan-out how that source is treated, and has a
   spatiality read from its object's data type, never declared.
3. Only PROCESSING inputs can become stage outputs, though they need not. A CONTEXT input
   serves only as context for the PROCESSING inputs and never becomes an output.
4. The stage is the resume granularity. The design neither plans for nor depends on intra-pod
   checkpoints.

## ST-1 Sources and products

**Direction.** External sources and products are each declared in one leaf module as symbols,
an external source with its classification required and a product carrying none; pipelines
import those leaves and never each other.

**Details.**

- **ST-D1** `sources.py` holds every `ExternalSource` in the project; `classification` is
  required, with no default; `eq=False`. A new restricted source is a `TypeError` at import
  until its legality is stated, and appears as a diff in the one file that shows everything
  entering the project under what restriction.
- **ST-D2** `products.py` holds every `ProductIdentity`: scale, dataset and location;
  `eq=False`; no `classification` field.
- **ST-D3** Both sides of a publication reference the symbol:
  `Publish(obj=..., identity=..., reclassify_to=...)` and `StageInput(obj=<the identity>,
  ...)`. `.importlinter` keeps both modules leaves that import only the core.
- **ST-D4** `identity_producer` and `check_no_self_read` are lookups keyed on the object, so
  find-references on a symbol answers who produces it and who reads it.
- **ST-D5** The legality of something we produce is computed over the stage wiring that
  produced it. The one human assertion that generalization removed a restriction lives on
  `reclassify_to`, at one auditable point.
- **ST-D6** `policy.classification_of` resolves a published `ProductIdentity` to the
  producing stage's computation with `reclassify_to` applied. An identity nothing here
  publishes falls back to rules and fails closed.
- **ST-D7** No pipeline imports another pipeline. Pipelines import the leaves.
- **ST-D8** `locations.py` owns environment prefixing: the remote-path builders
  (`scratch_location`, `scratch_dump_location`, `payload_location` and the archive location)
  live there.
- **ST-D9** `Scale` and `ObjectName` are `StrEnum`, so a member renders as its value in a
  path builder; `RAW` is `Scale.RAW`. `ObjectName` is closed, so adding an object edits a
  shared module.
- **ST-D10** `scale` and `object_name` are repeated on every `Stage`. A plan-time check
  confirms they agree with the pipeline, since the `Stage` is constructed before the
  `Pipeline`.

## ST-2 Stage inputs: role and spatiality

**Direction.** The role is declared per stage input and belongs to it, not to the object;
spatiality is read from the object's data type; fan-out's treatment of a source follows from
both and from the context radius, and from nothing else.

**Details.**

- **ST-D11** PROCESSING: the stage acts on the whole source. Fan-out applies no filter; every
  row is processed in its partition, with the context around the partition. CONTEXT: the
  source matters only as context for the PROCESSING inputs. Fan-out filters a spatial CONTEXT
  input to the context radius around the PROCESSING rows and sends a non-spatial one whole.
  The role belongs to the stage input, not to the object: the same water layer is PROCESSING
  in the stage that generalises it and CONTEXT in the stage that moves buildings away from
  it.
- **ST-D12** `FEATURE_CLASS` and `RASTER` are spatial; `TABLE` and `SYMBOLOGY` are not.
  `DataType.spatial` says so, and no module re-derives it.
- **ST-D13** Transfer: spatial PROCESSING is partitioned with halo overlap; spatial CONTEXT is
  context-filtered, then partitioned with the same overlap; non-spatial PROCESSING is
  rejected at declaration; non-spatial CONTEXT is sent whole to every pod, written once at a
  shared key.
- **ST-D14** The context filter keeps CONTEXT rows within the stage's context radius of any
  PROCESSING row, before partitioning; at 0 m, the rows that intersect one. The filter
  distance is the radius, with no second number. Overlap applies to both partitioned roles: a
  PROCESSING row within the radius of a partition but outside it reaches that partition too
  and fan-in discards it; a CONTEXT row within the radius reaches it.
- **ST-D15** Non-spatial PROCESSING is rejected when the `StageInput` is constructed, with a
  break-it case. There is no other guard: 0 m with spatial context is legal.
- **ST-D16** A stage output derives only from PROCESSING inputs: every output row originates
  from a PROCESSING input. Values taken from a CONTEXT input (an attribute joined from a
  table, a value sampled from a raster, symbology a tool applies) may shape or annotate those
  rows. A row that originates from a CONTEXT input never becomes output, whether or not
  PROCESSING rows are mixed in. Found in review until a static check exists; the check needs
  an operation-level subject marker, which is open. Scratch intermediates built from a
  CONTEXT input are legal inside a stage and reach the scratch dump. An object built from a
  CONTEXT input that a later stage must read is produced in a stage where its source is
  PROCESSING.
- **ST-D17** The context radius is a claim about the logic. Operations never see partitions
  (ADR-0019 PC-D2), so the radius is the one place a stage author reasons about partition
  boundaries; 0 m states that nothing in the stage consults a neighbour, and the model does
  not guard it.
- **ST-D18** Rasters are spatial and take either role; transfer is tile selection or clipping
  to the partition plus its halo, not row filtering. The mechanism is open until a stage
  declares a raster input.
- **ST-D19** Symbology files are non-spatial CONTEXT inputs: an `ExternalSource` with
  `data_type=DataType.SYMBOLOGY`, a settable location and a classification, reaching every
  pod whole. Every table and every symbology file is a stage input with a settable storage
  location, never baked into the container image. The member is `SYMBOLOGY`, not a generic
  `FILE`, so the next file kind gets its own decision.
- **ST-D20** Numeric symbol dimensions are a project-wide Python resource that reaches
  operations as config fields varying by pipeline (ADR-0020 OP-4), never a stage input.
- **ST-D21** The port-level subject and context of the row-shape grammar relate to the roles
  and are not the same thing (ADR-0017 RS-2). The grammar declares, per port method, which
  input's rows carry identity into an output; the roles declare, per stage input, whether a
  source may become stage output. At both levels, only the subject carries identity into
  outputs, and a context influences without contributing identity.
- **ST-D22** `DataType` has four members and a `spatial` property; `InputRole` has two
  members and a docstring stating the rule and the four transfers. Fan-out reads three
  declared facts, the role, the radius and the object's data type, and nothing else; fan-in
  keeps non-spatial outputs by id ownership. A `PREM_ONLY` classification on a table or
  symbology file pins the stage on-prem like any other input.

## ST-3 Resume

**Direction.** A pod lost mid-stage restarts the stage, and the resilience budget goes into
not losing pods.

**Details.**

- **ST-D23** The stage workspace is pod-local. `--invalidate-from <stage>` is the only resume
  mechanism; a pod lost to OOMKill, eviction or node maintenance restarts from the beginning
  of its stage.
- **ST-D24** An operator whose runtime approaches its stage's total re-run cost is promoted
  to its own stage: a declaration change, not an architecture change. Whether the trade pays
  is Q-G, measurable once one operator is reimplemented.

## Rejected

- **ST-R1** Each pipeline declaring its own sources, linked by value equality on
  `(scale, dataset)`. An omitted classification compares equal to a stated one and schedules
  restricted data into the cloud with no error; a product's location is written by whoever
  reads it, and an unread product has none. Reopening this changes Direction 1.
- **ST-R2** A classification field on a product identity. A second, unreviewed home for the
  judgement on `reclassify_to`; the two drift. Reopening this changes Direction 1.
- **ST-R3** Alternatives to two declared roles: deriving the role from the data; a third role
  for the non-spatial case. The same object takes both roles in different stages; a third
  role duplicates the data type, mixes two questions in one enum and collides with existing
  words. Reopening either changes Direction 2 and 3.
- **ST-R5** A generic `FILE` data type. It invites opaque inputs. Reopened by a second file
  kind whose transfer and legality rules are identical to symbology's; until then, the next
  file kind gets its own member and its own decision.
- **ST-R6** Intra-pod resume. The stage workspace is pod-local, so resuming from operation N
  means persisting inter-operation handles to run-scratch, roughly 2K transfers plus a merge
  per stage, the cost stage grouping exists to avoid. Reopened by a stage whose re-run cost
  makes a checkpoint pay after promoting its expensive operator to its own stage has been
  tried; the mint counter then becomes checkpoint state.
