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
dissolve_file = "dissolve"
island_merger = "island_merger"
area_aggregator = "area_aggregator"
category_aggregator = "category_aggregator"
elim_file = "eliminate"
gangsykkel_file = "gangsykkel"
buff_polygon_segments = "buff_polygon_segments"
simplify_polygon = "simplify_polygon"

overlap_remover = "overlap_remover"
passability = "passability"
innsjo_file = "innsjo_file"
arealdekke_class = "arealdekke_class"
category_class = "category_class"
overlap_merger = "overlap_merger"
fill_holes = "fill_holes"
small_features_changer = "small_features_changer"
poly_to_point = "poly_to_point"
remove_thin_tracks = "remove_thin_tracks"
river_lines = "river_lines"


class Arealdekke_N10(Enum):
    # ========================================
    #                     arealdekke dissolver
    # ========================================

    identity = file_manager.generate_file_name_gdb(
        script_source_name=dissolve_file, description="identity"
    )

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

    # ========================================
    #                     gangsykkel dissolver
    # ========================================

    gangsykkel_root = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel_root"
    )

    dissolve_gangsykkel = file_manager.generate_file_name_gdb(
        script_source_name=gangsykkel_file, description="gangsykkel"
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
    #                          OVERLAP REMOVER
    # ========================================

    overlap_remover__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=overlap_remover, description="overlap_remover"
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
    #                              PASSABILITY
    # ========================================

    passability__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=passability, description="passability"
    )

    passability_work_file__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=passability, description="passability_work_file"
    )

    # ========================================
    #                        SIMPLIFY LAND USE
    # ========================================

    simplified_polygons__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=simplify_polygon, description="simplified_polygons"
    )

    # ========================================
    #              BUFF SMALL POLYGON SEGMENTS
    # ========================================

    buffed_polygon_segments__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=buff_polygon_segments, description="buffed_polygon_segments"
    )

    river_lines__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=river_lines, description="river_lines"
    )

    # ========================================
    #                   INNSJO HØYDE INTERVALL
    # ========================================

    innsjo_hoydeintervall__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=innsjo_file, description="hoyde_intervall"
    )

    # ========================================
    #                         AREALDEKKE CLASS
    # ========================================

    arealdekke_class_in_progress__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=arealdekke_class, description="in_progress_files"
    )

    arealdekke_processed_categories__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=arealdekke_class, description="final_categories"
    )

    arealdekke_class_final__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=arealdekke_class, description="final_file"
    )

    # ========================================
    #                           CATEGORY CLASS
    # ========================================

    category_class_in_progress__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=category_class, description="in_progress_files"
    )

    # ========================================
    #                           OVERLAP MERGER
    # ========================================

    overlap_merger__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=overlap_merger, description="overlap_merger"
    )

    # ========================================
    #                               FILL HOLES
    # ========================================

    fill_holes__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=fill_holes, description="fill_holes"
    )

    # ========================================
    #                   SMALL FEATURES CHANGER
    # ========================================

    small_features_changer__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=small_features_changer, description="small_features_changer"
    )

    # ========================================
    #                          AREA AGGREGATOR
    # ========================================

    area_aggregator__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_aggregator, description="area_aggregator"
    )

    area_aggregator_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=area_aggregator, description="area_aggregator_output"
    )

    # ========================================
    #                      CATEGORY AGGREGATOR
    # ========================================

    category_aggregator__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=category_aggregator, description="category_aggregator"
    )

    category_aggregator_output__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=category_aggregator, description="category_aggregator_output"
    )

    # ========================================
    #                         POLYGON TO POINT
    # ========================================

    poly_to_point__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=poly_to_point, description="poly_to_point"
    )

    poly_to_point_points__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=poly_to_point, description="poly_to_point_points"
    )

    # ========================================
    #                      THIN TRACKS REMOVER
    # ========================================

    thin_tracks_remover__n10_land_use = file_manager.generate_file_name_gdb(
        script_source_name=remove_thin_tracks, description="thin_tracks_remover"
    )
