# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_arealdekke_flate
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
innsjo_file = "innsjo"
polygon_file="polygon"
river_file="river"


class Landuse_N10(Enum):
    # ========================================
    #                   INNSJO HØYDE INTERVALL
    # ========================================

    hoydeintervall__n10_landuse = file_manager.generate_file_name_gdb(
        script_source_name=innsjo_file, description="hoyde_intervall"
    )

    # ========================================
    #                  BUFF RIVERS AREALDEKKET
    # ========================================
    arealdekket_river__n10_landuse=file_manager.generate_file_name_gdb(
        script_source_name=river_file, description="buffed_small_rivers"
    )

    # ========================================
    #                ADJUST LAKES AREALDEKKET
    # ========================================
    arealdekket_lake__n10_landuse=file_manager.generate_file_name_gdb(
        script_source_name=innsjo_file, description="fixing_arealdekket_innsjo"
    )

    # ========================================
    #         BUFF SMALL POLYGON SEGMENTS TOOL
    # ========================================

    buffed_polygon_segments__n10_landuse = file_manager.generate_file_name_gdb(
        script_source_name=polygon_file, description="buffed_polygon_segments"
    )