"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/road/tuning/n100.py`.

Road tuning at N100. One `replace` delta per config, and nothing else.

READ THIS AS A DIFF. Everything not mentioned here is the base value in
example_road_tuning/__init__.py, and everything mentioned here is either an N100
cartographic constant or a road-specific N100 judgement. That is the whole point of
base-plus-one-delta: a reviewer sees exactly what N100 changes, on one screen.

`dump_tuning.py n100 road` prints the resolved result, which is what makes the
no-merge-mechanism rule verifiable rather than aspirational - every value below is
module-level `replace` evaluated at import, so the dump is a read, not a
simulation.
"""

from __future__ import annotations

from dataclasses import replace

from ag.operations.road.tuning import (
    HIERARCHY_BASE,
    JOIN_ADMIN_BASE,
    MERGE_DIVIDED_BASE,
    NETWORK_WEIGHTS_BASE,
    RAILWAY_CLEARANCE_BASE,
    RAMP_BASE,
    SELECT_SOURCE_ROADS_BASE,
    SIMPLIFY_BASE,
    SMOOTH_BASE,
    SNAP_BASE,
    THIN_ROAD_BASE,
)
from ag.tuning.scale import n100 as scale

NETWORK_WEIGHTS = replace(NETWORK_WEIGHTS_BASE, local=0.25)
"""Local roads matter less at N100 than at N50 - most of them do not survive.

DECLARED ONCE AND REFERENCED BY BOTH configs below, which is what stops
calculate_road_hierarchy assigning ranks that thin_road_network then spends against
a different weighting. That failure has no error, it just drops arterials and keeps
farm tracks.
"""

SELECT_SOURCE_ROADS = replace(SELECT_SOURCE_ROADS_BASE, minimum_class=4)
"""Classes 1-3 do not appear at this scale at all."""

JOIN_ADMIN = JOIN_ADMIN_BASE
"""Unchanged at this scale - the join radius is a property of the admin data, not of
the map.

RE-EXPORTED RATHER THAN OMITTED, so the pipeline module reads every config from one
module and a reader can see this was a decision rather than an oversight. A `None`
placeholder here would be a trap; a plain alias is a diff that says "no change".
"""

HIERARCHY = replace(HIERARCHY_BASE, weights=NETWORK_WEIGHTS)

MERGE_DIVIDED = replace(MERGE_DIVIDED_BASE, max_separation_m=60.0)
"""Wider than base: at N100 carriageways 60m apart still print as one road."""

THIN_ROAD = replace(
    THIN_ROAD_BASE,
    minimum_length_m=scale.MINIMUM_VISIBLE_LENGTH_M,
    weights=NETWORK_WEIGHTS,
)
"""The cartographic constant does the work. Change MINIMUM_VISIBLE_LENGTH_M and
river pruning moves with it, which is the intended coupling."""

RAMP = replace(RAMP_BASE, cluster_radius_m=scale.INTERCHANGE_CLUSTER_RADIUS_M)

SNAP = replace(SNAP_BASE, tolerance_m=15.0)

RAILWAY_CLEARANCE = replace(
    RAILWAY_CLEARANCE_BASE, min_clearance_m=scale.MINIMUM_FEATURE_SEPARATION_M
)

SIMPLIFY = replace(SIMPLIFY_BASE, tolerance_m=scale.SIMPLIFICATION_TOLERANCE_M)

SMOOTH = replace(SMOOTH_BASE, tolerance_m=scale.SMOOTHING_TOLERANCE_M)
