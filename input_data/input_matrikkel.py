# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main matrikkel path

matrikkel_path = Path.joinpath(Path(input_data_folder), "raw_data", "matrikkel.gdb")

# Setup feature class paths

# Raw data
bygning = Path.joinpath(matrikkel_path, "bygning")

# Create dataset for imports

DATA = [bygning]
