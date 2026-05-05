# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main building path

building_path = Path.joinpath(Path(input_data_folder), "raw_data", "building.gdb")

# Setup feature class paths

# N10 generalized data
bygningspunkt_n10 = Path.joinpath(building_path, "BygningsPunkt_N10")
grunnriss_n10 = Path.joinpath(building_path, "Grunnriss_N10")
turisthytte_n10 = Path.joinpath(building_path, "TuristHytte_N10")

# N50 generalized data
anleggslinje_n50 = Path.joinpath(building_path, "AnleggsLinje_N50")

# Create dataset for imports

DATA = [bygningspunkt_n10, grunnriss_n10, turisthytte_n10, anleggslinje_n50]
