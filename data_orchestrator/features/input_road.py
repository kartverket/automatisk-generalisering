# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main road path

road_path = Path.joinpath(Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.road.lower()}.gdb")

# Setup feature class paths

# Raw data
elveg_and_sti = Path.joinpath(road_path, dn.elveg_and_sti)
vegsperring = Path.joinpath(road_path, dn.vegsperring)

# N50 generalized data (= input to N100 generalization)
vegsti_n50 = Path.joinpath(road_path, dn.VegSti_N50)

# Create dataset for imports

DATA = [elveg_and_sti, vegsperring, vegsti_n50]
