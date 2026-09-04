"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/pipelines/road/n100.py`.

The complete (N100, road) pipeline in one file.

Contrast with the building example, which splits objects and stages across two
modules. THAT IS A LAYOUT CHOICE, NOT A MODEL CHANGE - the declarations are
identical either way.

Declaration order: Derived -> Handles -> Stages -> Pipeline.

NOTE WHAT IS NO LONGER HERE: source and product declarations. Every external source
lives in sources.py and every published identity in products.py, each declared once
for the whole project. This module imports the symbols it reads and publishes.

That is a change from the earlier draft, which had each pipeline re-declare the
sources it used and relied on value equality over (scale, dataset) to link them.
The property that motivated it - no pipeline imports another pipeline - is
preserved, because both are leaf modules. What it cost was a real leak: location,
classification and data_type were all compare=False, so a second declaration of
NVDB_Roads that omitted `classification` compared equal, linked as the same
identity, and gave the omitting pipeline CLOUD_OK for restricted data with no error
anywhere. sources.py says why in full.

WHAT MOVES ACROSS THE WIRE, AND WHEN

  StageInput   is DOWNLOADED. Fan-out reads it from the location pinned at plan
               time, cuts it into K partition payloads (or writes it ONCE at a
               shared key, if it is unpartitioned context), and each worker pulls
               its own.
  StageOutput  is UPLOADED. Fan-in merges the K partition results and writes them to
               locations.scratch_location - a path computed mechanically from the
               PRODUCING STAGE, never declared, and never anywhere near the object's
               origin.
  Publish      is the pipeline's handoff. It promotes a Derived to a ProductIdentity
               that other pipelines read as a StageInput, and it is the one place a
               human may assert a product is LESS restricted than what produced it.

  everything else never leaves the pod. A handle no StageOutput names has no
  identity, no location, and nothing uploads it. That is not an optimisation to
  implement; it is what happens when nobody declares it.

WHAT THIS EXAMPLE SHOWS THAT BUILDING DOES NOT

  - a genuine multi-origin JOIN (admin attributes merged into road records)
  - operations with several inputs and several outputs throughout
  - a Derived consumed by TWO stages, one of them NON-ADJACENT (ROAD_RANKS, made in
    stage 1, read by stages 2 and 3)
  - publication from a NON-FINAL stage (junction points, out of stage 2)
  - PER-OUTPUT reclassification: one product declassified, two not
  - an output whose ORIGIN includes the restricted source, where the roads' does not
  - one shared sub-config (NETWORK_WEIGHTS) read by two operations
  - the product that building_n100 consumes, closing the cross-pipeline loop
"""

from __future__ import annotations

from ag.core.types import Classification, DataType, InputRole, ObjectName, Scale
from ag.core.data_objects import Derived
from ag.operations.road import (
    calculate_road_hierarchy,
    finalize_road_attributes,
    join_admin_attributes,
    merge_divided_highways,
    resolve_ramps,
    resolve_road_railway_conflicts,
    select_source_roads,
    simplify_road_geometry,
    smooth_road_geometry,
    snap_to_source_geometry,
    thin_road_network,
)
from ag.operations.road.tuning import n100 as tuning
from ag.core.operations import Handles, handle
from ag.core.pipeline import Pipeline, Publish, Stage, StageInput, StageOutput
from ag.products import (
    N50_ROAD,
    N100_RAILWAY,
    N100_ROAD,
    N100_ROAD_JUNCTION_POINTS,
    N100_ROAD_SNAP_DISPLACEMENT,
)
from ag.sources import ADMIN_AREAS, NVDB_ROADS

TABLE = DataType.TABLE


# ---------------------------------------------------------------------------
# Derived objects.
#
# Each one is a thing that gets UPLOADED at the end of the stage that makes it, and
# DOWNLOADED again by every stage that reads it. That round trip is the cost a stage
# boundary buys, which is why intermediates between operations are not Derived.
#
# Location is not declared and cannot be - Derived has no `location` parameter. It is
# computed from the run and the producing stage by locations.scratch_location.
#
# The `name` strings stay literals, deliberately: they are declared once, no consumer
# requires them to match their symbol, and they are part of a run-scratch path, so a
# rename would move a live object's location. Uniqueness within the pipeline is a
# check (check_derived_names_unique), not a naming mechanism. See Derived's docstring.
# ---------------------------------------------------------------------------

SELECTED_ROADS = Derived("selected_roads", origin=(N50_ROAD, ADMIN_AREAS))

ROAD_RANKS = Derived("road_ranks", origin=(N50_ROAD, ADMIN_AREAS), data_type=TABLE)
"""A lookup table produced in stage 1 and read by BOTH stage 2 and stage 3.

The dependency graph is a graph, not a chain. Nothing in the model requires a stage
to read only its predecessor, and the non-adjacent edge (selection -> conflict
resolution) appears in derive_stage_dependencies without anyone declaring it.

It is also cheap: a table is unpartitioned CONTEXT, so fan-out writes it once at a
shared key and all K workers read the same object.
"""

THINNED_ROADS = Derived("thinned_roads", origin=(N50_ROAD, ADMIN_AREAS))

JUNCTION_POINTS = Derived("road_junction_points", origin=(N50_ROAD, ADMIN_AREAS))
"""Produced in stage 2 and published from there - a pipeline's products need not
come from its final stage. Nothing in the model prefers the last one; publication is
a property of the object, not of position."""

SNAP_DISPLACEMENT = Derived(
    "snap_displacement", origin=(N50_ROAD, NVDB_ROADS), data_type=TABLE
)
"""THE ONE OBJECT HERE WHOSE ORIGIN INCLUDES NVDB_ROADS, and the contrast is the
whole lesson of the origin-versus-legality split.

THINNED_ROADS was snapped onto NVDB positions and still keeps NVDB out of its
origin, because snapping only MOVES vertices - no NVDB data ends up inside a road
record. Its legality still becomes PREM_ONLY, because legality is computed over the
stage wiring instead. See data_objects and policy.classification_of.

A displacement measurement is different in kind. The numbers ARE NVDB data: add them
back to the snapped geometry and you have reconstructed the source positions
exactly. So NVDB is genuinely part of what this table IS, not merely something that
influenced it.
"""

ROAD = Derived("road", origin=(N50_ROAD, ADMIN_AREAS))
"""The headline product, published as N100_ROAD.

NOTE ITS ORIGIN IS ENTIRELY CLOUD_OK - both N50_ROAD and ADMIN_AREAS are on gs://
with no restriction. Its computed CLASSIFICATION is nonetheless PREM_ONLY, because
NVDB_ROADS reaches the stage that produces its ancestor. See the Publish below.
"""


# ---------------------------------------------------------------------------
# Workspace handles. One class per stage, one stage workspace per class.
#
# THE NAME IS THE ATTRIBUTE. `Selection.filtered` is a ScratchHandle whose `name` is
# "filtered" and whose `namespace` is "Selection", both stamped by
# ScratchHandle.__set_name__ when the class body executes. The name is never written
# twice, an LSP rename moves the definition and every use together, and two handles
# in one stage cannot collide because two attributes in one class body cannot.
#
# The `namespace` is what makes `Network.ranks` and `ConflictResolution.ranks`
# different VALUES rather than merely different symbols, and it is what
# check_stage_uses_own_handles compares against `Stage.handles`.
#
# These are local to this file and mean nothing outside the pod. A handle is a place,
# not a thing: no identity, no location, no legality.
# ---------------------------------------------------------------------------


class Selection(Handles):
    raw_roads = handle()
    admin = handle(TABLE)

    filtered = handle()
    geometry_errors = handle()
    enriched = handle()
    match_report = handle(TABLE)

    ranked = handle()
    rank_table = handle(TABLE)


class Network(Handles):
    roads_in = handle()
    nvdb_reference = handle()
    ranks = handle(TABLE)

    merged = handle()
    merge_report = handle(TABLE)
    thinned = handle()
    dropped = handle()
    ramp_lines = handle()

    snapped = handle()
    ramp_points = handle()
    displacement = handle(TABLE)


class ConflictResolution(Handles):
    network_in = handle()
    railway = handle()
    ranks = handle(TABLE)

    deconflicted = handle()
    conflicts = handle()
    simplified = handle()
    collapsed_points = handle()
    smoothed = handle()

    final = handle()


# ---------------------------------------------------------------------------
# Stage 1
# ---------------------------------------------------------------------------

SELECTION = Stage(
    name="selection",
    scale=Scale.N100,
    object_name=ObjectName.ROAD,
    handles=Selection,
    context_radius_m=0.0,
    inputs=(
        StageInput(obj=N50_ROAD, handle=Selection.raw_roads, role=InputRole.PROCESSING),
        StageInput(obj=ADMIN_AREAS, handle=Selection.admin, role=InputRole.CONTEXT),
    ),
    outputs=(
        StageOutput(obj=SELECTED_ROADS, handle=Selection.ranked),
        StageOutput(obj=ROAD_RANKS, handle=Selection.rank_table),
    ),
    operations=(
        select_source_roads(
            source=Selection.raw_roads,
            output=Selection.filtered,
            geometry_errors=Selection.geometry_errors,
            config=tuning.SELECT_SOURCE_ROADS,
        ),
        join_admin_attributes(
            roads=Selection.filtered,
            areas=Selection.admin,
            output=Selection.enriched,
            match_report=Selection.match_report,
            config=tuning.JOIN_ADMIN,
        ),
        calculate_road_hierarchy(
            roads=Selection.enriched,
            geometry_errors=Selection.geometry_errors,
            match_report=Selection.match_report,
            output=Selection.ranked,
            rank_table=Selection.rank_table,
            config=tuning.HIERARCHY,
        ),
    ),
)
"""Three operations, all per-feature, so context_radius_m=0.

A zero radius is a CLAIM ABOUT THE LOGIC, not an oversight: nothing here consults a
neighbour, so a partition boundary cannot change a result. Worth writing explicitly
so a reviewer can challenge it.

TWO DOWNLOADS, TWO UPLOADS, FOUR HANDLES THAT NEVER LEAVE. `filtered`,
`geometry_errors`, `enriched` and `match_report` are all read by a later operation in
this stage and named by no StageOutput, so they cost nothing beyond local disk. Only
`ranked` and `rank_table` become objects and get uploaded.

THIS IS WHAT THE TWO VOCABULARIES BUY. Moving calculate_road_hierarchy into stage 2
would be a one-line edit here and in the stage 2 declaration - the operation itself
does not change, because it never knew which stage it was in. What WOULD change is
that `geometry_errors` and `match_report` become objects with a round trip each.

`handles=Selection` is not decoration. It is what lets
check_stage_uses_own_handles catch the ordinary copy-paste of a `Network.` handle
into this stage - which type-checks, and otherwise fails in the pod as a missing
dataset after fan-out has already moved the data.

Alone in its stage because selection changes feature density substantially, so the
partitioning that suits the raw N50 product does not suit what follows.
"""


# ---------------------------------------------------------------------------
# Stage 2
# ---------------------------------------------------------------------------

NETWORK = Stage(
    name="network",
    scale=Scale.N100,
    object_name=ObjectName.ROAD,
    handles=Network,
    context_radius_m=5000.0,
    inputs=(
        StageInput(
            obj=SELECTED_ROADS, handle=Network.roads_in, role=InputRole.PROCESSING
        ),
        StageInput(
            obj=NVDB_ROADS, handle=Network.nvdb_reference, role=InputRole.CONTEXT
        ),
        StageInput(obj=ROAD_RANKS, handle=Network.ranks, role=InputRole.CONTEXT),
    ),
    outputs=(
        StageOutput(obj=THINNED_ROADS, handle=Network.snapped),
        StageOutput(obj=JUNCTION_POINTS, handle=Network.ramp_points),
        StageOutput(obj=SNAP_DISPLACEMENT, handle=Network.displacement),
    ),
    operations=(
        merge_divided_highways(
            roads=Network.roads_in,
            output=Network.merged,
            merge_report=Network.merge_report,
            config=tuning.MERGE_DIVIDED,
        ),
        thin_road_network(
            roads=Network.merged,
            ranks=Network.ranks,
            merge_report=Network.merge_report,
            output=Network.thinned,
            dropped=Network.dropped,
            config=tuning.THIN_ROAD,
        ),
        resolve_ramps(
            roads=Network.thinned,
            dropped=Network.dropped,
            output_lines=Network.ramp_lines,
            output_points=Network.ramp_points,
            config=tuning.RAMP,
        ),
        snap_to_source_geometry(
            roads=Network.ramp_lines,
            reference=Network.nvdb_reference,
            output=Network.snapped,
            displacement=Network.displacement,
            config=tuning.SNAP,
        ),
    ),
)
"""Four operations, THREE stage outputs, and the widest radius in either example.

WHY 5000 AND NOT 1500. Building's displacement chains locally - a displaced feature
pushes its neighbour, which pushes its neighbour. Network THINNING is different in
kind: whether a segment survives depends on the connectivity of the network around
it, so a segment can be kept solely because it is the only link between two distant
components. Get the radius wrong and a partition sees a dead end where the real
network continues, drops the segment, and fan-in stitches together a network with
holes in it. No error - just a map missing roads.

THREE INPUTS, THREE DIFFERENT TRANSFER SHAPES. `roads_in` is PROCESSING, so it is
cut into K payloads. `nvdb_reference` is spatial CONTEXT, so each pod gets the
features within 5000m of its own extent. `ranks` is a TABLE and therefore
unpartitioned context: fan-out writes it ONCE at a shared key and all K workers read
the same object. At K=50 that is the difference between one transfer and fifty for
identical bytes.

MULTI-OUTPUT OPERATIONS THAT END DIFFERENTLY. `merge_report` and `dropped` are
second outputs that a later operation in this stage reads and nothing uploads.
`ramp_points` and `displacement` are second outputs that ARE named by StageOutputs
and become products. Same shape in the operation signature; entirely different cost.

THE TAINT ENTERS HERE. NVDB_ROADS is PREM_ONLY and arrives as CONTEXT. It
contributes no data to THINNED_ROADS or JUNCTION_POINTS - snap_to_source_geometry
only moves vertices - which is why it is absent from their origins. It still makes
everything this stage produces PREM_ONLY, because snapped centrelines encode the
source positions they were pulled onto. SNAP_DISPLACEMENT is the exception that
proves the rule: it names NVDB_ROADS in its origin because its values ARE the source
positions, expressed as offsets.
"""


# ---------------------------------------------------------------------------
# Stage 3
# ---------------------------------------------------------------------------

CONFLICT_RESOLUTION = Stage(
    name="conflict_resolution",
    scale=Scale.N100,
    object_name=ObjectName.ROAD,
    handles=ConflictResolution,
    context_radius_m=1500.0,
    inputs=(
        StageInput(
            obj=THINNED_ROADS,
            handle=ConflictResolution.network_in,
            role=InputRole.PROCESSING,
        ),
        StageInput(
            obj=N100_RAILWAY, handle=ConflictResolution.railway, role=InputRole.CONTEXT
        ),
        StageInput(
            obj=ROAD_RANKS, handle=ConflictResolution.ranks, role=InputRole.CONTEXT
        ),
    ),
    outputs=(StageOutput(obj=ROAD, handle=ConflictResolution.final),),
    operations=(
        resolve_road_railway_conflicts(
            roads=ConflictResolution.network_in,
            railway=ConflictResolution.railway,
            output=ConflictResolution.deconflicted,
            conflicts=ConflictResolution.conflicts,
            config=tuning.RAILWAY_CLEARANCE,
        ),
        simplify_road_geometry(
            roads=ConflictResolution.deconflicted,
            output=ConflictResolution.simplified,
            collapsed_points=ConflictResolution.collapsed_points,
            config=tuning.SIMPLIFY,
        ),
        smooth_road_geometry(
            roads=ConflictResolution.simplified,
            barriers=ConflictResolution.railway,
            output=ConflictResolution.smoothed,
            config=tuning.SMOOTH,
        ),
        finalize_road_attributes(
            roads=ConflictResolution.smoothed,
            ranks=ConflictResolution.ranks,
            conflicts=ConflictResolution.conflicts,
            collapsed_points=ConflictResolution.collapsed_points,
            output=ConflictResolution.final,
        ),
    ),
)
"""Four operations, one output, five intermediates that never leave the pod.

READING ROAD_RANKS HERE IS THE NON-ADJACENT EDGE. It was produced in stage 1 and
uploaded then; this stage downloads it again, two stages later. Nobody declared
selection -> conflict_resolution; derive_stage_dependencies finds it because
ROAD_RANKS appears in one stage's outputs and another's inputs.

`railway` IS READ BY TWO OPERATIONS - once as the thing to move away from, once as a
smoothing barrier. Reading a handle is unconstrained; only WRITING must be unique
(check_one_writer_per_handle). One download, two consumers.

finalize_road_attributes TAKES NO CONFIG. Nothing about it is tuned per scale, so it
declares nothing, and its OperationCall.parameters is empty. The run manifest records
that honestly rather than inventing an empty config object.

Separated from NETWORK because thinning changes the feature count dramatically -
whatever partition size suited the full network is wrong for the thinned one. This
is the grouping criterion doing real work: it is not "these feel related", it is
"the data has changed enough that re-partitioning is warranted".

Radius drops to 1500: conflict resolution and smoothing are local, and carrying
5000m of halo through this stage would be paying network-thinning's cost for
operations that do not need it. THAT is the argument for the split, and it is
measurable - run both groupings and compare total context volume against saved round
trips.
"""


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

ROAD_N100 = Pipeline(
    scale=Scale.N100,
    object_name=ObjectName.ROAD,
    stages=(SELECTION, NETWORK, CONFLICT_RESOLUTION),
    publishes=(
        Publish(obj=ROAD, identity=N100_ROAD, reclassify_to=Classification.CLOUD_OK),
        Publish(obj=JUNCTION_POINTS, identity=N100_ROAD_JUNCTION_POINTS),
        Publish(obj=SNAP_DISPLACEMENT, identity=N100_ROAD_SNAP_DISPLACEMENT),
    ),
)
"""PLACEMENT: NVDB_ROADS is on s3://, so the whole pipeline runs on-prem - decided
once, here, never mid-pipeline. Its other three external inputs are on GCS, read over
outbound HTTPS. That is the ordinary case.

Note `external_inputs` is not passed. It is a derived property over the stages,
because a hand-written list would be a second artifact restating what the stages
already declare - and since placement is its only consumer, a stale list means a
pipeline silently scheduled in the wrong environment.

PUBLISH IS THE HANDOFF, AND IT IS WHERE THE STORAGE TIER CHANGES. Everything a stage
uploads goes to locations.scratch_location under the run's own prefix, and lives only
as long as that prefix is retained - retention there IS the resume window. A
published object instead goes to its ProductIdentity's declared archive location.

  THE GAP THIS CLOSES. `Publish` used to name a dataset STRING and no location, so
  the only place a location for (N100, Road) existed was the consuming pipeline's
  Source declaration - a product's destination written down by whoever happened to
  read it, and no location at all for a product nobody consumed. Now both sides
  reference N100_ROAD, declared once in products.py.

THREE PUBLICATIONS, ONE RECLASSIFICATION. All three compute to PREM_ONLY: NVDB_ROADS
reached the network stage, and policy.classification_of joins over everything that
reached a stage, context included.

  ROAD               reclassified to CLOUD_OK, which is why N100_ROAD's declared
                     location is a gs:// bucket. The assertion: at N100, with
                     SIMPLIFICATION_TOLERANCE_M=30 and SMOOTHING_TOLERANCE_M=75
                     applied after snapping, the geometry no longer resolves what
                     made the NVDB source restricted. That is a claim about CONTENT
                     that no machine can evaluate, so it lives here, greppable, and
                     takes effect at the moment of the on-prem to cloud copy.

                     Note it cites two values that now live in
                     example_scale_tuning/n100.py. Changing either of them changes
                     what this assertion is claiming, which is an argument for the
                     resolved-config dump being part of the review.

  JUNCTION_POINTS    NOT reclassified. Point positions at interchanges are far
                     closer to the source geometry than a smoothed centreline is, so
                     the same argument does not carry. It stays PREM_ONLY and
                     publishes to the s3:// location on its identity.

  SNAP_DISPLACEMENT  NOT reclassified, and this one is not a judgement call at all.
                     The table is the difference between the published geometry and
                     the restricted source; publishing it beside a declassified ROAD
                     would hand back exactly what declassifying ROAD asserted was
                     gone. Anyone proposing to reclassify this is proposing to
                     publish NVDB.

THIS IS WHY RECLASSIFICATION IS PER OUTPUT AND NOT PER PIPELINE. A blanket
per-pipeline declassification would have swept both the junction points and the
displacement table along with the road product, silently, and nobody reviewing the
pipeline would have seen two further decisions being made.

CLOSING THE LOOP: example_building_n100_objects reads N100_ROAD as a StageInput.
This Publish is what produces that identity, so StageRegistry.identity_producer()
links them and building_n100 depends on this pipeline's conflict_resolution stage.
"""
