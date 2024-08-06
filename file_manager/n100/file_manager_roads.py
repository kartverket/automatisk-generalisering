# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager


# Initialize BaseFileManager
scale = global_config.scale_n100
object_name = global_config.object_veg_sti
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_selection = "data_selection"
data_preparation = "data_preparation"


class RoadN100(Enum):
    data_selection___example___n100_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="example",
    )
