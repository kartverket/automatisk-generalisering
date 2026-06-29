# Libraries

from paths import GIS_FILES_ROOT
from input_data.input_data_names import DataNames as dn

from pathlib import Path

# Setup main area path

area_path = Path.joinpath(Path(GIS_FILES_ROOT), "raw_data", "area.gdb")

# Setup feature class paths and create dataset for imports

DATA = {
    # Test data
    dn.Arealdekke_Test: Path.joinpath(area_path, dn.Arealdekke_Test),
    # Raw data
    dn.ArealdekkeFlate: Path.joinpath(area_path, dn.ArealdekkeFlate),
    dn.Fishnet_500m: Path.joinpath(area_path, dn.Fishnet_500m),
    # N10 generalized data
    dn.ArealdekkeFlate_N10: Path.joinpath(area_path, dn.ArealdekkeFlate_N10),
    # N50 generalized data
    dn.AdminFlate_N50: Path.joinpath(area_path, dn.ArealdekkeFlate_N50),
    dn.AdminGrense_N50: Path.joinpath(area_path, dn.AdminGrense_N50),
    dn.ArealdekkeFlate_N50: Path.joinpath(area_path, dn.AdminFlate_N50),
    dn.Begrensningskurve_N50: Path.joinpath(area_path, dn.Begrensningskurve_N50),
}
