"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/building/tuning/n100.py`.

Building tuning at N100. One `replace` delta per config, and nothing else.

Note it spends the SAME scale constants the road pipeline does. That is the whole
point of tuning/scale/: SIMPLIFICATION_TOLERANCE_M is a fact about the map at
1:100 000, not about roads, and buildings simplified to a different tolerance than
roads is a cartographic inconsistency that no per-pipeline review would catch -
each pipeline looks internally consistent and the map is not.
"""

from __future__ import annotations

from dataclasses import replace

from ag.operations.building.tuning import (
    DISPLACEMENT_FEATURE_BASE,
    SIMPLIFY_POLYGONS_BASE,
)
from ag.tuning.scale import n100 as scale

SIMPLIFY_POLYGONS = replace(
    SIMPLIFY_POLYGONS_BASE, tolerance_m=scale.SIMPLIFICATION_TOLERANCE_M
)

DISPLACEMENT_FEATURE = replace(
    DISPLACEMENT_FEATURE_BASE, buffer_m=scale.MINIMUM_FEATURE_SEPARATION_M
)
"""Buildings must end up at least a printable separation from a road centreline, so
the displacement buffer IS the separation constant - not a number tuned in isolation
until the map looked right."""
