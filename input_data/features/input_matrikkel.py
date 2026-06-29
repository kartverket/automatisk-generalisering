# Libraries

from paths import GIS_FILES_ROOT
from input_data.input_data_names import DataNames as dn

from pathlib import Path

# Setup main matrikkel path

matrikkel_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "matrikkel.gdb")

# Setup feature class paths and create dataset for imports

DATA = {
    # Raw data
    dn.bygning: Path.joinpath(matrikkel_path, dn.bygning)
}
