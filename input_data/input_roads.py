# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main road path

road_path = Path.joinpath(Path(input_data_folder), "raw_data", "Roads.gdb")

# Setup feature class paths

elveg_and_sti = Path.joinpath(road_path, "elveg_and_sti")
vegsperring = Path.joinpath(road_path, "Vegsperring")

# Create dataset for imports

DATA = [elveg_and_sti, vegsperring]
