# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_elv_bekk
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
river_file = "elv"


class Elv_Bekk_N10(Enum):
    # ========================================
    #               ELV BEARBEIDET AREALDEKKE
    # ========================================

    arealdekke_elv__n10_elv_bekk = file_manager.generate_file_name_gdb(
        script_source_name=river_file, description="arealdekke_elv"
    )