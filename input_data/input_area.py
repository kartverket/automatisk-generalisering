# Libraries

from config import input_data_folder

from pathlib import Path

# Setup main area path

area_path = Path.joinpath(Path(input_data_folder), "raw_data", "area.gdb")

# Setup feature class paths

# N10 generalized data
arealdekkeflate_n10 = Path.joinpath(area_path, "ArealdekkeFlate_N10")

# N50 generalized data
adminflate_n50 = Path.joinpath(area_path, "AdminFlate_N50")
admingrense_n50 = Path.joinpath(area_path, "AdminGrense_N50")
arealdekkeflate_n50 = Path.joinpath(area_path, "ArealdekkeFlate_N50")
begrensningskurve_n50 = Path.joinpath(area_path, "Begrensningskurve_N50")

# Create dataset for imports

DATA = [
    arealdekkeflate_n10,
    adminflate_n50,
    admingrense_n50,
    arealdekkeflate_n50,
    begrensningskurve_n50,
]
