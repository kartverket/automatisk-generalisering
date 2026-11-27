"""Project path bindings.

``GIS_FILES_ROOT`` points at the input directory containing ``raw_data/`` and
``symbology/``. ``GIS_OUTPUTS_ROOT`` optionally points at the directory that holds
``ag_outputs/``; set it to a writable location such as ``/tmp/GIS_Files`` when the
inputs are on a read-only mount. When unset, the parent of ``GIS_FILES_ROOT`` is used.
``GIS_ROAD_RESULTS_ROOT`` optionally points at the directory holding the road pipeline's
``ag_outputs/`` (for example the PVC, when ``GIS_OUTPUTS_ROOT`` is pod-local). When unset,
``GIS_OUTPUTS_ROOT`` is used.
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
GIS_OUTPUTS_ROOT = (
    Path(os.environ["GIS_OUTPUTS_ROOT"])
    if "GIS_OUTPUTS_ROOT" in os.environ
    else GIS_FILES_ROOT.parent
)
GIS_ROAD_RESULTS_ROOT = Path(
    os.environ.get("GIS_ROAD_RESULTS_ROOT", str(GIS_OUTPUTS_ROOT))
)
PYTHONPATH = Path(require("PYTHONPATH"))


def road_result_path(output_path: str) -> str:
    """Rebase a path under ``GIS_OUTPUTS_ROOT`` onto ``GIS_ROAD_RESULTS_ROOT``."""
    relative = Path(output_path).relative_to(GIS_OUTPUTS_ROOT)
    return str(GIS_ROAD_RESULTS_ROOT / relative)
