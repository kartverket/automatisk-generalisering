# Libraries

from paths import GIS_FILES_ROOT
from input_data.input_data_names import DataNames as dn

from pathlib import Path

# Setup main building path

building_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "building.gdb")

# Setup feature class paths and create dataset for imports

DATA = {
    # N10 generalized data
    dn.BygningsPunkt_N10: Path.joinpath(building_path, dn.BygningsPunkt_N10),
    dn.Grunnriss_N10: Path.joinpath(building_path, dn.Grunnriss_N10),
    dn.TuristHytte_N10: Path.joinpath(building_path, dn.TuristHytte_N10),
    # N50 generalized data
    dn.AnleggsLinje_N50: Path.joinpath(building_path, dn.AnleggsLinje_N50),
}
