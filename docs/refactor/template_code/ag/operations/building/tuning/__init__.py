"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/operations/building/tuning/__init__.py`.

BASE building configs. Every field stated exactly once.

In reality `generalization/building/tuning/__init__.py`.

SAME SHAPE AS THE ROAD TUNING PACKAGE, DELIBERATELY. dump_tuning.py resolves
`example_<object>_tuning.<scale>` for any object, so a one-off flat layout for the
smaller pipeline would mean the tool that makes the no-resolution-mechanism rule
verifiable only works for pipelines big enough to have bothered. Two operations is
enough to be worth the package.
"""

from __future__ import annotations

from ag.operations.building import DisplacementFeatureConfig, SimplifyPolygonsConfig

SIMPLIFY_POLYGONS_BASE = SimplifyPolygonsConfig(tolerance_m=10.0)

DISPLACEMENT_FEATURE_BASE = DisplacementFeatureConfig(buffer_m=20.0)
