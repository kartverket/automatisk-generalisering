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

    hoydetall_global__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_global"
    )

    hoydetall_out_of_bounds_areas__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_out_of_bounds_areas"
    )

    hoydetall_annotation_contours__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_annotation_contours"
    )

    hoydetall_valid_contours__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_valid_contours"
    )

    hoydetall_point_1km__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_point_1km"
    )

    hoydetall_output__n10_landforms = file_manager.generate_file_name_gdb(
        script_source_name=hoyde_file, description="hoydetall_output"
    )
