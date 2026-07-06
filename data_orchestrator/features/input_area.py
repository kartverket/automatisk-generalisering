# Libraries

from pathlib import Path

from data_orchestrator.data_names import DataNames as dn
from paths import GIS_FILES_ROOT

# Setup main area path

area_path = Path.joinpath(Path(GIS_FILES_ROOT), dn.raw_data, f"{dn.area.lower()}.gdb")

# Setup feature class paths

# Test data
# arealdekke_test = Path.joinpath(area_path, dn.ArealdekkeTest)

# Raw data
arealdekkeflate = Path.joinpath(area_path, dn.ArealdekkeFlate)
fishnet = Path.joinpath(area_path, dn.Fishnet_500m)

# N10 generalized data
arealdekkeflate_n10 = Path.joinpath(area_path, dn.ArealdekkeFlate_N10)

# N50 generalized data
adminflate_n50 = Path.joinpath(area_path, dn.AdminFlate_N50)
admingrense_n50 = Path.joinpath(area_path, dn.AdminGrense_N50)
arealdekkeflate_n50 = Path.joinpath(area_path, dn.ArealdekkeFlate_N50)
begrensningskurve_n50 = Path.joinpath(area_path, dn.Begrensningskurve_N50)

# Create dataset for imports

DATA = [
    # arealdekke_test,
    arealdekkeflate,
    fishnet,
    arealdekkeflate_n10,
    adminflate_n50,
    admingrense_n50,
    arealdekkeflate_n50,
    begrensningskurve_n50,
]
