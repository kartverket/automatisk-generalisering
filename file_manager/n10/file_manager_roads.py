# Imports
from enum import Enum
from env_setup import global_config
from file_manager.base_file_manager import BaseFileManager

# Initialize BaseFileManager
scale = global_config.scale_n10
object_name = global_config.object_veg_sti
file_manager = BaseFileManager(scale=scale, object_name=object_name)


# All scripts
data_selection = "data_selection"


class Road_N10(Enum):
    # ========================================
    #             DATA SELECTION
    # ========================================

    data_selection___trails_root___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails_root",
    )

    data_selection___barmarksloype___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="barmarksloype",
    )

    data_selection___sti___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="sti",
    )

    data_selection___traktorveg___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="traktorveg",
    )

    data_selection___trails___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails",
    )

    data_selection___not_trails___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="not_trails",
    )

    data_selection___barmarksloype_buffered___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="barmarksloype_buffered",
        )
    )

    data_selection___sti_buffered___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="sti_buffered",
    )

    data_selection___traktorveg_buffered___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="traktorveg_buffered",
        )
    )

    data_selection___barmarksloype_buffered_dissolved___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="barmarksloype_buffered_dissolved",
        )
    )

    data_selection___sti_buffered_dissolved___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="sti_buffered_dissolved",
        )
    )

    data_selection___traktorveg_buffered_dissolved___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="traktorveg_buffered_dissolved",
        )
    )

    data_selection___trails_buffered___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails_buffered",
    )

    data_selection___parallell_trails_overlaps___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="parallell_trails_overlaps",
        )
    )

    data_selection___large_overlap_trail_pairs___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="large_overlap_trail_pairs",
        )
    )

    data_selection___parallell_trails_overlaps_singlepart___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="parallell_trails_overlaps_singlepart",
        )
    )

    data_selection___long_overlaps___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="long_overlaps",
    )

    data_selection___trails_with_overlap___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_with_overlap",
        )
    )

    data_selection___trails_with_overlap_dissolved___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_with_overlap_dissolved",
        )
    )

    data_selection___trail_points___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trail_points",
    )

    data_selection___trail_points_near_table___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trail_points_near_table",
        )
    )

    data_selection___near_table_stats___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="near_table_stats",
    )

    data_selection___trails_in_overlap_to_remove___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_in_overlap_to_remove",
        )
    )

    data_selection___trails_in_overlap_to_keep___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_in_overlap_to_keep",
        )
    )

    data_selection___trails_to_remove___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails_to_remove",
    )

    data_selection___dangles_not_covered___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="dangles_not_covered",
        )
    )

    data_selection___dangles_not_covered_singlepart___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="dangles_not_covered_singlepart",
        )
    )

    data_selection___long_dangles_not_covered___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="long_dangles_not_covered",
        )
    )

    data_selection___trails_to_remove_without_dangles___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_to_remove_without_dangles",
        )
    )

    data_selection___trails_to_keep___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails_to_keep",
    )

    data_selection___trails_to_keep_singlepart___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="trails_to_keep_singlepart",
        )
    )

    data_selection___dangles_not_wanted___n10_road = (
        file_manager.generate_file_name_gdb(
            script_source_name=data_selection,
            description="dangles_not_wanted",
        )
    )

    data_selection___dangles_to_remove___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="dangles_to_remove",
    )

    data_selection___trails_final___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="trails_final",
    )

    data_selection___roads_final___n10_road = file_manager.generate_file_name_gdb(
        script_source_name=data_selection,
        description="roads_final",
    )
