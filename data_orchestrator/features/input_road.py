# Libraries

from paths import GIS_FILES_ROOT

from pathlib import Path

# Setup main road path

road_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "road.gdb")

# Setup feature class paths

# Raw data
elveg_and_sti = Path.joinpath(road_path, "elveg_and_sti")
vegsperring = Path.joinpath(road_path, "vegsperring")

# N50 generalized data (= input to N100 generalization)
vegsti_n50 = Path.joinpath(road_path, "VegSti_N50")

# Create dataset for imports

DATA = [elveg_and_sti, vegsperring, vegsti_n50]
