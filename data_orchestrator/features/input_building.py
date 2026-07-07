# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main building path

building_path = Path.joinpath(
    Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.building.lower()}.gdb"
)

# Setup feature class paths

# N10 generalized data
bygningspunkt_n10 = Path.joinpath(building_path, dn.BygningsPunkt_N10)
grunnriss_n10 = Path.joinpath(building_path, dn.Grunnriss_N10)
turisthytte_n10 = Path.joinpath(building_path, dn.TuristHytte_N10)

# N50 generalized data
anleggslinje_n50 = Path.joinpath(building_path, dn.AnleggsLinje_N50)

# Create dataset for imports

DATA = [bygningspunkt_n10, grunnriss_n10, turisthytte_n10, anleggslinje_n50]
