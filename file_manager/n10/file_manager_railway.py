# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_bane
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
railway_file = "railway_n10"


class Railway_N10(Enum):
    # ========================================
    #                              Jernbaner
    # ========================================

    input_railway_n10 = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="fkb"
    )
    output_railway_n10 = file_manager.generate_file_name_gdb(
        script_source_name=railway_file, description="fkb_generalisert"
    )
