"""
Stage implementations for n100 road generalization pipeline.

Each stage file contains a single stage function that handles a specific processing step.
Stages are created using the make_stage() factory to reduce boilerplate.
"""

from .thin_road import thin_road_stage
from .ramps import ramps_stage

__all__ = [
    "thin_road_stage",
    "ramps_stage",
]
