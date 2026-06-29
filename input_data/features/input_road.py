# Libraries

from paths import GIS_FILES_ROOT
from input_data.input_data_names import DataNames as dn

from pathlib import Path

# Setup main road path

road_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "road.gdb")

# Setup feature class paths and create dataset for imports

DATA = {
    # Raw data
    dn.elveg_and_sti: Path.joinpath(road_path, dn.elveg_and_sti),
    dn.vegsperring: Path.joinpath(road_path, dn.vegsperring),
    # N50 generalized data (= input to N100 generalization)
    dn.VegSti_N50: Path.joinpath(road_path, dn.VegSti_N50),
}
