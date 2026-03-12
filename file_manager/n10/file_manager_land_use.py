# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_arealdekke_flate
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
attribute_file = "attribute_changer"
area_line_merger = "area_line_merger"


class Land_use_N10(Enum):
    # ========================================
    #                        ATTRIBUTE CHANGER
    # ========================================

    attribute_changer__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=attribute_file, description="attribute_changer"
    )

    attribute_changer_documentation__n10_land_use = (
        file_manager.generate_general_subdirectory(
            description="attribute_changer_documentation"
        )
    )

    attribute_changer_root__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=attribute_file, description="attribute_changer_root"
    )

    attribute_changer_partition_root__n10_land_use = (
        file_manager.generate_file_name_gdb(
            script_source_name=attribute_file,
            description="attribute_changer_partition_root",
        )
    )

    attribute_changer_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=attribute_file, description="attribute_changer_output"
    )

    # ========================================
    #                         AREA LINE MERGER
    # ========================================

    area_line_merger_start__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_line_merger, description="area_line_merger"
    )

    area_line_merger__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_line_merger, description="area_line_merger"
    )

    area_line_merger_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_line_merger, description="area_line_merger_output"
    )
