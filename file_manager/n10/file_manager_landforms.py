# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_hoyde
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
hoyde_file = "hoyde"


class Landform_N10(Enum):
    # ========================================
    #                              HOYDEKURVER
    # ========================================

    hoydetall__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall"
    )

    hoydetall_output__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_output"
    )
