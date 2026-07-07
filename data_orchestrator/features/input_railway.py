# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main train path

train_path = Path.joinpath(
    Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.railway.lower()}.gdb"
)

# Setup feature class paths

# N50 generalized data
bane_n50 = Path.joinpath(train_path, dn.Bane_N50)
jernbanestasjon_n50 = Path.joinpath(train_path, dn.JernbaneStasjon_N50)

# Create dataset for imports

DATA = [bane_n50, jernbanestasjon_n50]
