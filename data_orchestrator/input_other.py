# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main river basin path

river_basin_path = Path.joinpath(
    Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.river_basin.lower()}.gdb"
)

# Setup feature class paths

RiverBasins = str(Path.joinpath(river_basin_path, dn.Nedborfelt_Vassdragsomr))

# Create dataset for imports

DATA = [RiverBasins]
