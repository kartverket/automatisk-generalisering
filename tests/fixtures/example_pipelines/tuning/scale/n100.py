"""TEMPLATE / EXAMPLE — a worked pipeline. Target: `src/ag/tuning/scale/n100.py`.

Cartographic constants at N100. Shared across every object at this scale.

Plain module-level floats, not a dataclass. There is nothing to validate and nothing
to pass around: a config module references one by name, and that reference IS the
sharing mechanism. No registry, no lookup, no merge.
"""

from __future__ import annotations

MINIMUM_VISIBLE_LENGTH_M = 400.0
"""Below this a linear feature does not read as a feature at 1:100 000.

Spent by road thinning and by river pruning. If those two ever want different
values, that is a signal one of them is not actually asking the visibility question
- promote the difference to a second named constant rather than diverging silently.
"""

MINIMUM_FEATURE_SEPARATION_M = 50.0
"""Below this two features touch on the printed map. Drives conflict clearance."""

SIMPLIFICATION_TOLERANCE_M = 30.0
"""Vertex reduction tolerance. The value that, together with the smoothing tolerance
below, road_n100's Publish cites when it asserts the product no longer resolves what
made NVDB restricted."""

SMOOTHING_TOLERANCE_M = 75.0
"""Bend smoothing tolerance. See SIMPLIFICATION_TOLERANCE_M."""

INTERCHANGE_CLUSTER_RADIUS_M = 120.0
"""Ramps within this of each other are one interchange."""
