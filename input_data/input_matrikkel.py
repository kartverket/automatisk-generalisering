# Libraries

from paths import GIS_FILES_ROOT

from pathlib import Path

# Setup main matrikkel path

matrikkel_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "matrikkel.gdb")

# Setup feature class paths

# Raw data
bygning = Path.joinpath(matrikkel_path, "bygning")

# Create dataset for imports

DATA = [bygning]
