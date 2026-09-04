"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/pipelines/building/n100_stages.py`.

The stage declarations for (N100, building).

In reality this is `pipelines/building/n100/stages.py`.

THE THREE VOCABULARIES MEET HERE AND NOWHERE ELSE:

    inputs/outputs=     DataObjects. ExternalSource, ProductIdentity or Derived. They
                        have identity, lineage, legality, and (for the first two) a
                        remote location.
    handles=            the stage's handle class. Every declared handle must come
                        from it; check_stage_uses_own_handles enforces that.
    operations=         ScratchHandles and configs. Named slots in the pod's
                        workspace, plus one frozen tuning record per operation.

Splitting the objects into a separate module is a LAYOUT CHOICE. example_road_n100
puts everything in one file and the declarations are identical.
"""

from __future__ import annotations

from ag.core.types import DataType, InputRole, ObjectName, Scale
from ag.pipelines.building.n100_objects import DISPLACED, DISPLACEMENT_FEATURE, SELECTED
from ag.operations.building.tuning import n100 as tuning
from ag.operations.building import (
    build_displacement_feature,
    data_selection,
    propagate_displacement,
    simplify_polygons,
)
from ag.core.operations import Handles, handle
from ag.core.pipeline import Pipeline, Publish, Stage, StageInput, StageOutput
from ag.products import N50_BUILDING_POLYGONS, N100_BUILDING_POLYGONS, N100_ROAD
from ag.sources import MUNICIPALITY_CODES, NVDB_ROADS

# ---------------------------------------------------------------------------
# Workspace handles. One class per stage.
#
# A handle is a PLACE. A DataObject is a THING. Which of these places ever becomes a
# thing is decided below, by whether a StageOutput names it. The ones that do not are
# invisible outside the pod.
# ---------------------------------------------------------------------------


class Selection(Handles):
    raw_buildings = handle()
    municipality_codes = handle(DataType.TABLE)
    selected = handle()


class Displacement(Handles):
    buildings = handle()
    roads_source = handle()
    roads_generalized = handle()

    simplified = handle()
    displacement_feature = handle()
    displaced = handle()


# ---------------------------------------------------------------------------
# Stage 1
# ---------------------------------------------------------------------------

SELECTION = Stage(
    name="selection",
    scale=Scale.N100,
    object_name=ObjectName.BUILDING,
    handles=Selection,
    context_radius_m=0.0,
    inputs=(
        StageInput(
            obj=N50_BUILDING_POLYGONS,
            handle=Selection.raw_buildings,
            role=InputRole.PROCESSING,
        ),
        StageInput(
            obj=MUNICIPALITY_CODES,
            handle=Selection.municipality_codes,
            role=InputRole.CONTEXT,
        ),
    ),
    outputs=(StageOutput(obj=SELECTED, handle=Selection.selected),),
    operations=(
        data_selection(
            source=Selection.raw_buildings,
            codes=Selection.municipality_codes,
            output=Selection.selected,
        ),
    ),
)
"""Alone in its own stage because it re-partitions.

Selection changes the data enough that the extents differ afterwards, so whatever
partitioning suited the raw N50 product does not suit what comes next.

context_radius_m=0 because selection is per-feature - nothing here depends on a
neighbour, so no halo is needed. Worth stating explicitly rather than leaving
implicit: a zero radius is a claim about the logic, not an oversight.

MUNICIPALITY_CODES is CONTEXT and non-spatial, so fan-out replicates it whole to
every pod and writes it ONCE at a shared key rather than K times.

data_selection takes NO CONFIG. It has nothing tunable, so it declares nothing, and
its OperationCall.parameters is empty.
"""


# ---------------------------------------------------------------------------
# Stage 2
# ---------------------------------------------------------------------------

DISPLACEMENT = Stage(
    name="displacement",
    scale=Scale.N100,
    object_name=ObjectName.BUILDING,
    handles=Displacement,
    context_radius_m=1500.0,
    inputs=(
        StageInput(
            obj=SELECTED, handle=Displacement.buildings, role=InputRole.PROCESSING
        ),
        StageInput(
            obj=NVDB_ROADS, handle=Displacement.roads_source, role=InputRole.CONTEXT
        ),
        StageInput(
            obj=N100_ROAD,
            handle=Displacement.roads_generalized,
            role=InputRole.CONTEXT,
        ),
    ),
    outputs=(
        StageOutput(obj=DISPLACED, handle=Displacement.displaced),
        StageOutput(obj=DISPLACEMENT_FEATURE, handle=Displacement.displacement_feature),
    ),
    operations=(
        simplify_polygons(
            input=Displacement.buildings,
            output=Displacement.simplified,
            config=tuning.SIMPLIFY_POLYGONS,
        ),
        build_displacement_feature(
            roads=Displacement.roads_source,
            generalized_roads=Displacement.roads_generalized,
            output=Displacement.displacement_feature,
            config=tuning.DISPLACEMENT_FEATURE,
        ),
        propagate_displacement(
            input=Displacement.simplified,
            displacement=Displacement.displacement_feature,
            output=Displacement.displaced,
        ),
    ),
)
"""Three operations, one partitioning, one round trip.

READING N100_ROAD IS THE CROSS-PIPELINE EDGE. It is a ProductIdentity that
example_road_n100 publishes, so StageRegistry.identity_producer() resolves it to that
pipeline's conflict_resolution stage and road_n100 runs first. Nothing declares that
ordering. Within a run it pins to that stage's output; outside one, to the archived
version at the location declared in products.py.

Its gs:// location is consistent only BECAUSE road's Publish carries an explicit
reclassification - the product computes PREM_ONLY, since restricted NVDB data reaches
the stage that makes it.

WHAT NEVER LEAVES THE POD: `simplified`. Written by an operation, read by another,
named by no StageOutput, so it has no identity, no location, and nothing uploads it.
A full round trip saved - and since a .gdb is a directory tree, a saved round trip is
an archive plus an unarchive, not merely a copy.

DISPLACEMENT_FEATURE IS DIFFERENT, AND THAT IS A DECISION. It is now a real
StageOutput, so it is uploaded and the objects module's Derived for it is load
bearing rather than documentation. The alternative - a Derived declared for lineage
review beside a bare handle doing the actual wiring - was a third state with no
meaning: nothing uploaded it, warn_unused_handles could not see it, and the lineage
it documented was not the lineage the runtime used. Either an object crosses a
boundary and is a Derived, or it does not and is a handle.

THE COST: context_radius_m=1500 covers the whole chain, not just the worst single
operation. propagate_displacement works on simplify_polygons' output, so the
requirement compounds - displace A, A now conflicts with B, displacing B, which
affects C. That is the trade for grouping, and it fails SILENTLY: a radius tuned on
a rural test extent can be correct there and wrong in Oslo, producing slightly-wrong
geometry rather than an error. 1500 is a measured number, not a guess.

IF MEASUREMENT SAYS THE COMPOUNDED HALO COSTS MORE than the round trip saved, split
this into two stages. THAT CHANGE TOUCHES ONLY THIS FILE. No operation declaration
moves and no object declaration moves, because a ScratchHandle does not know which
stage it lives in and a Derived does not know which stage produces it.
"""


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

BUILDING_N100 = Pipeline(
    scale=Scale.N100,
    object_name=ObjectName.BUILDING,
    stages=(SELECTION, DISPLACEMENT),
    publishes=(Publish(obj=DISPLACED, identity=N100_BUILDING_POLYGONS),),
)
"""The development artifact. Dissolves at flatten().

PLACEMENT: NVDB_ROADS is on s3://, so this whole pipeline runs on-prem - decided
once, here, never mid-pipeline. Its other external inputs are on GCS, which an
on-prem pod reads over outbound HTTPS. That is the ordinary case, not an edge case.

LEGALITY: DISPLACED comes out PREM_ONLY. Not because of its `origin` - that is
N50_BUILDING_POLYGONS, which is CLOUD_OK - but because NVDB_ROADS reached the stage
that produced it. Displaced building footprints partially encode the road centrelines
they were pushed away from, so the conservative default is correct here.

Which makes N100_BUILDING_POLYGONS' gs:// location in products.py an INCONSISTENCY
this example deliberately leaves standing, for check_publications to catch: there is
no `reclassify_to` on this Publish, so a PREM_ONLY product is bound for cloud
storage. The fix is a human decision - either a reviewed reclassification here, or an
s3:// location on the identity - and the point of the check is that it fires before
any pod is created rather than at the end of a three-hour run.
"""
