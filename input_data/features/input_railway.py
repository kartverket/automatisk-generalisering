# Libraries

from paths import GIS_FILES_ROOT
from input_data.input_data_names import DataNames as dn

from pathlib import Path

# Setup main train path

train_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "railway.gdb")

# Setup feature class paths and create dataset for imports

DATA = {
    # N50 generalized data
    dn.Bane_N50: Path.joinpath(train_path, dn.Bane_N50),
    dn.JernbaneStasjon_N50: Path.joinpath(train_path, dn.JernbaneStasjon_N50),
}
