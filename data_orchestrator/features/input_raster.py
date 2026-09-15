# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup raster directory paths

dom_10m = Path.joinpath(Path(GIS_FILES_ROOT), dn.raw_data, dn.dom_10m)
