# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main road path

road_path = Path.joinpath(Path(input_data_folder), "raw_data", "road.gdb")

# Setup feature class paths

# Raw data
elveg_and_sti = Path.joinpath(road_path, "elveg_and_sti")
vegsperring = Path.joinpath(road_path, "vegsperring")

# N50 generalized data (= input to N100 generalization)
vegsti_n50 = Path.joinpath(road_path, "VegSti_N50")

# Create dataset for imports

DATA = [elveg_and_sti, vegsperring, vegsti_n50]
