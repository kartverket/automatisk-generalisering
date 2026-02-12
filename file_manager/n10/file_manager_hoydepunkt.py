# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_hoydepunkt
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
hoydepunkt = "hoydepunkt"


class Hoydepunkt_N10(Enum):
    # ========================================
    #                               Hoydepunkt
    # ========================================

    hoydepunkt_n10 = file_manager.generate_file_name_gdb(
        script_source_name=hoydepunkt, description="hoydepunkt"
    )
