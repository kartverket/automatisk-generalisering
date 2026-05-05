# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main train path

train_path = Path.joinpath(Path(input_data_folder), "raw_data", "railway.gdb")

# Setup feature class paths

# N50 generalized data
bane_n50 = Path.joinpath(train_path, "Bane_N50")
jernbanestasjon_n50 = Path.joinpath(train_path, "JernbaneStasjon_N50")

# Create dataset for imports

DATA = [bane_n50, jernbanestasjon_n50]
