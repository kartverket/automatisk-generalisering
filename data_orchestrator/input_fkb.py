# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main fkb water path

fkb_water_path = Path.joinpath(
    Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.fkb_water.lower()}.gdb"
)

# Setup feature class paths

VannLinje = str(Path.joinpath(fkb_water_path, dn.fkb_vann_grense))
VannFlate = str(Path.joinpath(fkb_water_path, dn.fkb_vann_omrade))
VannPunkt = str(Path.joinpath(fkb_water_path, dn.fkb_vann_posisjon))

# Create dataset for imports

DATA = [VannLinje, VannFlate, VannPunkt]
