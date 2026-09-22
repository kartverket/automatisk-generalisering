"""TEMPLATE — not shipped. Target module: `src/ag/products.py`.

Every published identity in the project. One declaration each, nowhere else.

A LEAF MODULE, same contract as sources.py: core_types and data_objects only.

WHAT THIS CLOSES

`Publish` used to name a dataset string and no location, so the only place a
location for (N100, Road) existed was the CONSUMING pipeline's Source declaration.
Two consequences, both bad: a product's destination was written down by whoever
happened to read it, and a product nobody consumed had no location anywhere.

Now both sides reference one symbol:

    Publish(obj=ROAD, identity=N100_ROAD, reclassify_to=Classification.CLOUD_OK)
    StageInput(obj=N100_ROAD, handle=Selection.raw_roads, role=InputRole.PROCESSING)

So a product has a location whether or not anything reads it,
StageRegistry.identity_producer becomes a lookup keyed on the object rather than a
(scale, dataset) string match, and find-references on N100_ROAD answers "who
produces this and who reads it" in one query.

NO CLASSIFICATION HERE. The legality of something we produce is computed over the
stage wiring that produced it, and the single human assertion that generalization
removed a restriction lives on `reclassify_to` at the Publish, where it is a
reviewable diff at one auditable point. A classification on the identity would be a
second home for that judgement, unreviewed, and the two would drift.

AN IDENTITY MAY HAVE NO PRODUCER IN THIS PROJECT. N100_RAILWAY is declared here and
nothing in these examples publishes it. That is correct and the model handles it: if
a railway pipeline exists and publishes the identity, an edge appears and it runs
first; if not, consumers read the archived version at this location. Nothing in a
consuming pipeline changes either way.
"""

from __future__ import annotations

from ag.core.types import DataType, Scale
from ag.core.data_objects import ProductIdentity

# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------

N50_ROAD = ProductIdentity(
    scale=Scale.N50,
    dataset="Road",
    location="gs://kv-products/n50/road.gdb",
)
"""The ladder input to road_n100.

DECLARED AT N50, not N100. Pointing a pipeline's ladder input at its own scale is
the self-read that check_no_self_read exists to catch, and which the one-producer
rule would not, because there would still be exactly one producer.
"""

N100_ROAD = ProductIdentity(
    scale=Scale.N100,
    dataset="Road",
    location="gs://kv-products/n100/road.gdb",
)
"""road_n100's headline product, and building_n100's displacement input.

The gs:// location is legitimate only BECAUSE road_n100's Publish reclassifies to
CLOUD_OK - everything its conflict resolution stage produces computes to PREM_ONLY,
since NVDB_ROADS reached the network stage. check_publications is what enforces the
consistency; see the Publish in example_road_n100.
"""

N100_ROAD_JUNCTION_POINTS = ProductIdentity(
    scale=Scale.N100,
    dataset="RoadJunctionPoints",
    location="s3://kv-products-prem/n100/road_junction_points.gdb",
)
"""Published from a NON-FINAL stage, and NOT reclassified, so it goes to on-prem
storage. Point positions at interchanges sit far closer to the source geometry than
a smoothed centreline does."""

N100_ROAD_SNAP_DISPLACEMENT = ProductIdentity(
    scale=Scale.N100,
    dataset="RoadSnapDisplacement",
    location="s3://kv-products-prem/n100/road_snap_displacement.gdb",
    data_type=DataType.TABLE,
)
"""The QA table, on-prem and not reclassifiable. It is the difference between the
published geometry and the restricted source; publishing it beside a declassified
N100_ROAD would hand back exactly what declassifying N100_ROAD asserted was gone."""


# ---------------------------------------------------------------------------
# Railway - consumed here, produced elsewhere or not at all
# ---------------------------------------------------------------------------

N100_RAILWAY = ProductIdentity(
    scale=Scale.N100,
    dataset="Railway",
    location="gs://kv-products/n100/railway.gdb",
)


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

N50_BUILDING_POLYGONS = ProductIdentity(
    scale=Scale.N50,
    dataset="BuildingPolygons",
    location="gs://kv-products/n50/building_polygons.gdb",
)

N100_BUILDING_POLYGONS = ProductIdentity(
    scale=Scale.N100,
    dataset="BuildingPolygons",
    location="gs://kv-products/n100/building_polygons.gdb",
)
