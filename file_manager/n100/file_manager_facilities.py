# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_bygg_og_anlegg
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
ledning_file = "ledning"

class Facility_N100(Enum):
    # ========================================
    #                                  LEDNING
    # ========================================

    ledning__n100_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="ledning"
    )

    ledning_output__n100_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="ledning_output"
    )

    mast_output__n100_facility = file_manager.generate_file_name_gdb(
        script_source_name=ledning_file, description="mast_output"
    )
