# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_arealdekke_flate
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
rullebane_file = "rullebane"


class Land_Use_N100(Enum):
    # ========================================
    #                                RULLEBANE
    # ========================================

    rullebane__n100_land_use = file_manager.generate_file_name_gdb(
        script_source_name=rullebane_file, description="rullebane"
    )

    rullebane_output__n100_land_use = file_manager.generate_file_name_gdb(
        script_source_name=rullebane_file, description="rullebane_output"
    )
