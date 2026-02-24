# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_hoyde
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
innsjo_file = "innsjo"


class Landuse_N10(Enum):
    # ========================================
    #                   INNSJO HØYDE INTERVALL
    # ========================================

    hoydeintervall__n10_landuse = file_manager.generate_file_name_gdb(
        script_source_name=innsjo_file, description="hoyde_intervall"
    )