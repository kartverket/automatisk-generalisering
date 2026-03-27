# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_arealdekke_flate
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
dissolve_file = "dissolve"
elim_file = "eliminate"
gangsykkel_file = "gangsykkel"
attribute_file = "attribute_changer"
area_line_merger = "area_line_merger"
island_merger = "island_merger"
simplify_polygon = "simplify_polygon"
expansion_controller = "expansion_controller"
buff_polygon_segments = "buff_polygon_segments"
river_file = "river_file"
innsjo_file = "innsjo_file"


class Arealdekke_N10(Enum):
    # ========================================
    #                     arealdekke dissolver
    # ========================================

    dissolve_arealdekke_root = file_manager.generate_file_name_gdb(
        script_source_name=dissolve_file, description="dissolve_arealdekke_root"
    )
    dissolve_arealdekke_partition_root = file_manager.generate_file_name_gdb(
        script_source_name=dissolve_file,
        description="dissolve_arealdekke_partition_root",
    )

    areal_dissolve_documentation = file_manager.generate_general_subdirectory(
        description="areal_dissolve_documentation",
    )

    dissolve_arealdekke = file_manager.generate_file_name_gdb(
        script_source_name=dissolve_file, description="arealdekke"
    )
    dissolve_arealdekke_docu = file_manager.generate_file_name_gdb(
        script_source_name=dissolve_file, description="arealdekke_docu"
    )

    # ========================================
    #                     gangsykkel dissolver
    # ========================================

    gangsykkel_root = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel_root"
    )

    dissolve_gangsykkel = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel"
    )
    dissolve_gangsykkel2 = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel2"
    )
    dissolve_gangsykkel3 = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel3"
    )

    # ========================================
    #                 eliminate small polygons
    # ========================================

    elim_documentation = file_manager.generate_general_subdirectory(
        description="elim_documentation",
    )

    elim_root = file_manager.generate_file_name_gdb(
        script_source_name=elim_file, description="elim_root"
    )

    elim_output = file_manager.generate_file_name_gdb(
        script_source_name=elim_file, description="output"
    )

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
        script_source_name=area_line_merger, description="area_line_merger_start"
    )

    area_line_merger__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_line_merger, description="area_line_merger"
    )

    area_line_merger_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_line_merger, description="area_line_merger_output"
    )

    # ========================================
    #                            ISLAND MERGER
    # ========================================

    island_merger__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=island_merger, description="island_merger"
    )

    island_merger_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=island_merger, description="island_merger_output"
    )

    # ========================================
    #                        SIMPLIFY LAND USE
    # ========================================

    simplified_polygons__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=simplify_polygon, description="simplified_polygons"
    )

    # ========================================
    #                     
    # ========================================

    expansion_controller__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=expansion_controller, description="expansion_controller"
    )

    expansion_controller_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=expansion_controller,
        description="expansion_controller_output",
    )

    # ========================================
    #                              BUFF RIVERS
    # ========================================

    generalise_rivers__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=river_file, description="buffed_small_rivers"
    )

    # ========================================
    #              BUFF SMALL POLYGON SEGMENTS
    # ========================================

    buffed_polygon_segments__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=buff_polygon_segments, description="buffed_polygon_segments"
    )

    # ========================================
    #                   INNSJO HØYDE INTERVALL
    # ========================================

    innsjo_hoydeintervall__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=innsjo_file, description="hoyde_intervall"
    )
