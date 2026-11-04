"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/pipelines/building/n100_objects.py`.

The object declarations for (N100, building).

In reality this is `pipelines/building/n100/objects.py`.

WHAT THIS FILE USED TO BE, AND WHY IT CHANGED

It used to open with four `Source(...)` declarations and describe itself as "THE ONLY
PLACE LOCATION AND LEGALITY ARE DECLARED for this pipeline". That per-pipeline
locality is what sources.py and products.py replaced. The reason is in sources.py in
full; the short version is that this file and example_road_n100 both declared
NVDB_Roads, only one of them stated its classification, and value equality on
(scale, dataset) with `classification` marked compare=False made the two the same
identity - so the omitting pipeline computed CLOUD_OK for restricted data.

The reviewer property is not lost, it moved up a level: sources.py is now the one
file that shows everything entering the PROJECT, under what restriction, which is
strictly more useful than one file per pipeline showing a slice.

What remains here is what is genuinely local: the objects this pipeline creates.
"""

from __future__ import annotations

from ag.core.types import DataType
from ag.core.data_objects import Derived
from example_pipelines.products import N50_BUILDING_POLYGONS, N100_ROAD
from example_pipelines.sources import MUNICIPALITY_CODES, NVDB_ROADS

# ---------------------------------------------------------------------------
# Derived objects.
#
# `origin` names LINEAGE ROOTS ONLY, and it means LINEAGE - what dataset this
# fundamentally IS. Not what influenced it. Not what it was computed alongside.
#
# There is no `location` parameter, and no predecessor to declare: that
# DISPLACED comes from SELECTED is already stated by the operation wiring in
# stages.py, and restating it here would be maintenance with no information gained.
# ---------------------------------------------------------------------------

SELECTED = Derived("selected_polygons", origin=(N50_BUILDING_POLYGONS,))
DISPLACED = Derived("displaced_polygons", origin=(N50_BUILDING_POLYGONS,))
"""Both are building data, and they keep that origin for their whole life.

DISPLACED was moved using road geometry, but no road data was merged into it, so
N100_ROAD and NVDB_ROADS stay out of its origin. That is what the user-facing
question "what dataset is this?" should answer.

Legality is a different question with a different answer. DISPLACED is PREM_ONLY
despite this CLOUD_OK origin, because restricted data reached the stage that produced
it - see policy.classification_of, which walks the stage wiring rather than origin.

THE DISPLACEMENT FEATURE HAS NO DERIVED. The displacement stage buffers and dissolves
its CONTEXT roads into a blob that propagate_displacement reads; every row of that blob
originates from CONTEXT inputs, and only rows originating from PROCESSING inputs may
become stage output. So it is a scratch handle in stages.py, crosses no boundary, and
has no origin to declare. Either an object crosses a boundary and is a Derived, or it
does not and is a handle; this one does not.
"""

ADDRESSED_BUILDINGS = Derived(
    "addressed_buildings",
    origin=(N50_BUILDING_POLYGONS, MUNICIPALITY_CODES),
    data_type=DataType.FEATURE_CLASS,
)
"""TWO origins, because data is genuinely combined - a table join merges attributes
from MUNICIPALITY_CODES into the building records. Contrast DISPLACED, where the
roads only influenced geometry and contributed no data."""
