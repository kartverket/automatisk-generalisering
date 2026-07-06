# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main matrikkel path

matrikkel_path = Path.joinpath(
    Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.matrikkel.lower()}.gdb"
)

# Setup feature class paths

# Raw data
bygning = Path.joinpath(matrikkel_path, dn.bygning)

# Create dataset for imports

DATA = [bygning]
