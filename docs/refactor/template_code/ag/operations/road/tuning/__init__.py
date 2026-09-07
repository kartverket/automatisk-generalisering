"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/road/tuning/__init__.py`.

BASE road configs. Every field stated exactly once.

In reality this is `generalization/road/tuning/__init__.py`, with `n50.py` and
`n100.py` beside it holding one `replace` delta each.

BASE PLUS ONE DELTA. NO RESOLUTION MECHANISM.

There is deliberately no `resolve(operation, scale, object)` walking object defaults,
then scale defaults, then overrides. The moment that exists, no value has a single
home and answering "what is N100's road thinning length" requires running code
rather than reading a line. Sharing happens because a line of code references a
constant - that is the whole mechanism.

Two rules that keep it that way:

  ONE DELTA LAYER. Object base -> scale delta, and that is the end. Wanting a third
  layer is the signal that a value should be promoted to a named constant in
  tuning/scale/ instead, where the sharing is legible.

  NO DEFAULTS ON CONFIG FIELDS. The dataclasses in operations.py deliberately give
  no field a default. A default plus a partial per-scale config answers one question
  in two files, and the reader cannot tell from either which one won. State every
  field here; express a scale as a `replace` diff you can read at a glance.

KEEP NESTING SHALLOW. `replace(BASE, weights=replace(BASE.weights, ...))` is
tolerable at one level and unreadable at two. A sub-config shared across operations -
NetworkWeightsConfig, read by both hierarchy and thinning - is the case that earns
the nesting: declare it once per scale and reference it from both.
"""

from __future__ import annotations

from ag.operations.road import (
    HierarchyConfig,
    JoinAdminConfig,
    MergeDividedConfig,
    NetworkWeightsConfig,
    RailwayClearanceConfig,
    RampConfig,
    SelectSourceRoadsConfig,
    SimplifyConfig,
    SmoothConfig,
    SnapConfig,
    ThinRoadConfig,
)

NETWORK_WEIGHTS_BASE = NetworkWeightsConfig(
    arterial=1.0,
    collector=0.7,
    local=0.4,
)

SELECT_SOURCE_ROADS_BASE = SelectSourceRoadsConfig(minimum_class=1)

JOIN_ADMIN_BASE = JoinAdminConfig(search_radius_m=25.0)

HIERARCHY_BASE = HierarchyConfig(
    weights=NETWORK_WEIGHTS_BASE,
    repaired_geometry_penalty=1,
)

MERGE_DIVIDED_BASE = MergeDividedConfig(max_separation_m=40.0)

THIN_ROAD_BASE = ThinRoadConfig(
    minimum_length_m=250.0,
    weights=NETWORK_WEIGHTS_BASE,
)

RAMP_BASE = RampConfig(cluster_radius_m=80.0)

SNAP_BASE = SnapConfig(tolerance_m=10.0)

RAILWAY_CLEARANCE_BASE = RailwayClearanceConfig(min_clearance_m=25.0)

SIMPLIFY_BASE = SimplifyConfig(tolerance_m=10.0)

SMOOTH_BASE = SmoothConfig(tolerance_m=25.0)
