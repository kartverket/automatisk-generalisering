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

import os

from pathlib import Path

###########################
# Functionality
###########################


def require(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise RuntimeError(
            f"Required environment variable {name} is not set!\nSee .env.example for the contract."
        ) from None


def load_env(env_path: Path = Path(".env")):
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


###########################
# File Paths
###########################

load_env()

DEFAULT_PROJECT_WORKSPACE = Path(require("DEFAULT_PROJECT_WORKSPACE"))
GIS_FILES_ROOT = Path(require("GIS_FILES_ROOT"))
PYTHONPATH = Path(require("PYTHONPATH"))
