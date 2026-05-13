"""
Project paths bindings.

Derives every project path from one environment variable (GIS_FILES_ROOT),
which points at the data root containing the canonical project layout.

Canonical layout under GIS_FILES_ROOT — see docs/canonical_layout.md:
  ag_inputs/        read-only inputs, supplied by data hydration
    raw_data/       Source data
      area.gdb        Area source data
      building.gdb    Building source data 
      matrikkel.gdb   Matrikkel source data
      railway.gdb     Railway source data
      road.gdb        Road source data
    symbology/      .lyrx symbology files
      n100
      n250
      ...
  ag_outputs/       writable, pipeline-controlled structure
    n100/           N100 outputs
    ...
"""

###########################
# Libraries
###########################

from pathlib import Path

from env_load import require

###########################
# File Paths
###########################

DEFAULT_PROJECT_WORKSPACE = Path(require("DEFAULT_PROJECT_WORKSPACE"))
GIS_FILES_ROOT = Path(require("GIS_FILES_ROOT"))
PYTHONPATH = Path(require("PYTHONPATH"))
