# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.validation import check_valid_feature_class
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.overall_tools.overlap_merger import (
    create_overlapping_land_use,
)
from generalization.n10.arealdekke.parameters.parameter_worker import (
    get_min_width,
)

# ========================
# Classes
# ========================


class fc(StrEnum):
    """
    What:
        Enum class used to easier spot when a filepath does not exist in the files dictionary.
    """

    target_fc = "target_fc"
    locked_fc = "locked_fc"
    locked_areas_outside_buffer = "locked_areas_outside_buffer"
    input_polygon_edge = "input_polygon_edge"
    input_polygon_minus_buffer = "input_polygon_minus_buffer"
    core_of_segments_wide_enough = "core_of_segments_wide_enough"
    segments_wide_enough = "segments_wide_enough"
    core_wide_enough_segments_singlepart = "core_wide_enough_segments_singlepart"
    segments_too_small = "segments_too_small"
    segments_too_small_single = "segments_too_small_single"
    overkill_buffer = "overkill_buffer"
    areas_chosen = "areas_chosen"
    centre_line = "centre_line"
    small_segments_centre = "small_segments_centre"
    small_segments_enlarged = "small_segments_enlarged"
    small_segments_locked_buffed_merged = "small_segments_locked_buffed_merged"
    small_segments_locked_buffed_dissolved = "small_segments_locked_buffed_dissolved"
    locked_fc_line = "locked_fc_line"
    locked_fc_line_clipped = "locked_fc_line_clipped"
    locked_fc_line_clipped_n_buffed_fc = "locked_fc_line_clipped_n_buffed_fc"
    locked_fc_line_intersecting = "locked_fc_line_intersecting"
    locked_fc_outward_buffer = "locked_fc_outward_buffer"
    only_small_segments_centre = "only_small_segments_centre"
    test = "test"
    work_fc = "work_fc"
    output_fc = "output_fc"


# ========================
# Main function
# ========================


@timing_decorator
def buff_small_polygon_segments(
    target: str, input_fc: str, output_fc: str, locked_fc: set, map_scale: str
) -> None:
    """
    What:
        Function that detects and buffers small polygon segments from input_fc, having
        land use type equal target. Finally, the funtion dissolves the buffered
        geometries into the input data.

    Args:
        target (str): The land use type of the segments to be buffered
        input_fc (str): The feature class containing the original data with type 'target'
        output_fc (str): The feature class to store the buffered data
        locked_fc (set): A set of feature classes representing locked areas
        map_scale (str): The map scale for the operation
    """
    print(
        f"\n{'====='*15}\nBuffering small segments of '{target}' at map scale '{map_scale}'\n{'====='*15}\n"
    )

    working_fc = Arealdekke_N10.buffed_polygon_segments__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)
    min_width = get_min_width(
        map_scale=map_scale,
        target=target,
    )

    extract_data(files=files, target_fc=target, input_fc=input_fc, locked_fc=locked_fc)

    if check_valid_feature_class(files[fc.target_fc], level=2):
        find_segments_under_min(files=files, min_width=min_width)
        choose_target_areas(files=files, min_width=min_width)
        get_shared_locked_boundary(files=files, min_width=min_width)
        buff_small_segments(files=files, min_width=min_width)

        create_overlapping_land_use(
            input_fc=files[fc.target_fc],
            buffered_fc=files[fc.small_segments_locked_buffed_dissolved],
            output_fc=output_fc,
        )
    else:
        arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=output_fc)

    # wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def file_setup(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of buffer thin areas.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        fc.target_fc: wfm.build_file_path(file_name=fc.target_fc, file_type="gdb"),
        fc.locked_fc: wfm.build_file_path(file_name=fc.locked_fc, file_type="gdb"),
        fc.locked_areas_outside_buffer: wfm.build_file_path(
            file_name=fc.locked_areas_outside_buffer, file_type="gdb"
        ),
        fc.locked_fc_line: wfm.build_file_path(
            file_name=fc.locked_fc_line, file_type="gdb"
        ),
        fc.locked_fc_line_clipped: wfm.build_file_path(
            file_name=fc.locked_fc_line_clipped, file_type="gdb"
        ),
        fc.locked_fc_line_clipped_n_buffed_fc: wfm.build_file_path(
            file_name=fc.locked_fc_line_clipped_n_buffed_fc, file_type="gdb"
        ),
        fc.input_polygon_edge: wfm.build_file_path(
            file_name=fc.input_polygon_edge, file_type="gdb"
        ),
        fc.input_polygon_minus_buffer: wfm.build_file_path(
            file_name=fc.input_polygon_minus_buffer, file_type="gdb"
        ),
        fc.core_of_segments_wide_enough: wfm.build_file_path(
            file_name=fc.core_of_segments_wide_enough, file_type="gdb"
        ),
        fc.segments_wide_enough: wfm.build_file_path(
            file_name=fc.segments_wide_enough, file_type="gdb"
        ),
        fc.core_wide_enough_segments_singlepart: wfm.build_file_path(
            file_name=fc.core_wide_enough_segments_singlepart, file_type="gdb"
        ),
        fc.segments_too_small: wfm.build_file_path(
            file_name=fc.segments_too_small, file_type="gdb"
        ),
        fc.segments_too_small_single: wfm.build_file_path(
            file_name=fc.segments_too_small_single, file_type="gdb"
        ),
        fc.overkill_buffer: wfm.build_file_path(
            file_name=fc.overkill_buffer, file_type="gdb"
        ),
        fc.areas_chosen: wfm.build_file_path(
            file_name=fc.areas_chosen, file_type="gdb"
        ),
        fc.locked_fc_line_intersecting: wfm.build_file_path(
            file_name=fc.locked_fc_line_intersecting, file_type="gdb"
        ),
        fc.locked_fc_outward_buffer: wfm.build_file_path(
            file_name=fc.locked_fc_outward_buffer, file_type="gdb"
        ),
        fc.only_small_segments_centre: wfm.build_file_path(
            file_name=fc.only_small_segments_centre, file_type="gdb"
        ),
        fc.centre_line: wfm.build_file_path(file_name=fc.centre_line, file_type="gdb"),
        fc.small_segments_centre: wfm.build_file_path(
            file_name=fc.small_segments_centre, file_type="gdb"
        ),
        fc.small_segments_enlarged: wfm.build_file_path(
            file_name=fc.small_segments_enlarged, file_type="gdb"
        ),
        fc.small_segments_locked_buffed_merged: wfm.build_file_path(
            file_name=fc.small_segments_locked_buffed_merged, file_type="gdb"
        ),
        fc.small_segments_locked_buffed_dissolved: wfm.build_file_path(
            file_name=fc.small_segments_locked_buffed_dissolved, file_type="gdb"
        ),
        fc.test: wfm.build_file_path(file_name=fc.test, file_type="gdb"),
        fc.work_fc: wfm.build_file_path(file_name=fc.work_fc, file_type="gdb"),
        fc.output_fc: wfm.build_file_path(file_name=fc.output_fc, file_type="gdb"),
    }


def extract_data(files: dict, target_fc: str, input_fc: str, locked_fc: str) -> None:
    """
    What:
        Extracts data for the program from the parameters and insert them into the files dictionary.
        For locked files, only the areas that share a boundry with the target polygons are selected and
        stored.
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc,
        out_layer=land_use_lyr,
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke='{target_fc}'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[fc.target_fc]
    )

    if int(arcpy.management.GetCount(locked_fc)[0]) > 0:
        arcpy.management.MakeFeatureLayer(
            in_features=locked_fc,
            out_layer=land_use_lyr,
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=land_use_lyr,
            overlap_type="SHARE_A_LINE_SEGMENT_WITH",
            select_features=files[fc.target_fc],
            selection_type="NEW_SELECTION",
        )
        arcpy.management.CopyFeatures(
            in_features=land_use_lyr, out_feature_class=files[fc.locked_fc]
        )


def find_segments_under_min(files: dict, min_width: int) -> None:
    """
    What:
        Finds areas under a minimum criteria set in the parameters folder.
    How:
        - Create a lyr with the outline of the input polygon
        - Use polygon outline to create a negative buffer
        - Areas not intersecting the minus buffer are large enough. Extract them into its own layer.
        - Create a full buffer for the core of the wide enough segments to get them back to their
            original size
        - Remove the large enough segments from the original polyon
    """
    arcpy.management.PolygonToLine(
        in_features=files[fc.target_fc], out_feature_class=files[fc.input_polygon_edge]
    )
    arcpy.analysis.Buffer(
        in_features=files[fc.input_polygon_edge],
        out_feature_class=files[fc.input_polygon_minus_buffer],
        buffer_distance_or_field=f"{min_width/2} Meters",
        line_side="FULL",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.target_fc],
        erase_features=files[fc.input_polygon_minus_buffer],
        out_feature_class=files[fc.core_of_segments_wide_enough],
    )
    arcpy.management.RepairGeometry(
        in_features=files[fc.core_of_segments_wide_enough], delete_null="DELETE_NULL"
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files[fc.core_of_segments_wide_enough],
        out_feature_class=files[fc.core_wide_enough_segments_singlepart],
    )
    arcpy.analysis.PairwiseBuffer(
        in_features=files[fc.core_wide_enough_segments_singlepart],
        out_feature_class=files[fc.segments_wide_enough],
        buffer_distance_or_field=f"{min_width/2} Meters",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.target_fc],
        erase_features=files[fc.segments_wide_enough],
        out_feature_class=files[fc.segments_too_small],
    )


def choose_target_areas(files: dict, min_width: int) -> None:
    """
    What:
        Clips the original polygon to only include 15 meters around the too small segments.
    How:
    - Creates an overkill buffer that includes the small segments and some of the area around.
    - Clip original polygon to get area with the too small segments.
    """
    arcpy.analysis.Buffer(
        in_features=files[fc.segments_too_small],
        out_feature_class=files[fc.overkill_buffer],
        buffer_distance_or_field=f"{min_width} Meters",
        line_side="FULL",
    )
    arcpy.analysis.PairwiseClip(
        in_features=files[fc.target_fc],
        clip_features=files[fc.overkill_buffer],
        out_feature_class=files[fc.areas_chosen],
    )


def get_shared_locked_boundary(files: dict, min_width: int) -> None:
    """
    What:
        Finds the boundaries between the target polygon and the locked polygons. Then, it creates a
        buffer going outwards from the locked areas.
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files[fc.overkill_buffer],
        selection_type="NEW_SELECTION",
    )

    arcpy.management.PolygonToLine(
        in_features=land_use_lyr, out_feature_class=files[fc.locked_fc_line]
    )

    arcpy.analysis.PairwiseClip(
        in_features=files[fc.locked_fc_line],
        clip_features=files[fc.overkill_buffer],
        out_feature_class=files[fc.locked_fc_line_clipped],
    )

    locked_fc_line_clipped_lyr = "locked_fc_line_clipped_lyr"
    areas_chosen_lyr = "areas_chosen_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc_line_clipped],
        out_layer=locked_fc_line_clipped_lyr,
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.areas_chosen], out_layer=areas_chosen_lyr
    )

    locked_fc_line_clipped_n_buffed_fc = "in_memory/locked_fc_line_clipped_n_buffed_fc"
    areas_chosen_within_locked_fc = "in_memory/areas_chosen_within_locked_fc"
    areas_chosen_within_locked_buffed_fc = (
        "in_memory/areas_chosen_within_locked_buffed_fc"
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=locked_fc_line_clipped_lyr,
        out_feature_class=locked_fc_line_clipped_n_buffed_fc,
        buffer_distance_or_field=f"{min_width/2} Meters",
    )

    locked_fc_line_clipped_n_buffed_lyr = "locked_fc_line_clipped_n_buffed_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=locked_fc_line_clipped_n_buffed_fc,
        out_layer=locked_fc_line_clipped_n_buffed_lyr,
    )

    arcpy.analysis.Intersect(
        in_features=[[locked_fc_line_clipped_n_buffed_lyr], [areas_chosen_lyr]],
        out_feature_class=areas_chosen_within_locked_fc,
    )

    areas_chosen_within_locked_lyr = "areas_chosen_within_locked_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=areas_chosen_within_locked_fc,
        out_layer=areas_chosen_within_locked_lyr,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=areas_chosen_within_locked_lyr,
        out_feature_class=areas_chosen_within_locked_buffed_fc,
        buffer_distance_or_field=f"{min_width/2} Meter",
    )

    areas_chosen_within_locked_buffed_lyr = "areas_chosen_within_locked_buffed_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=areas_chosen_within_locked_buffed_fc,
        out_layer=areas_chosen_within_locked_buffed_lyr,
    )

    arcpy.analysis.Intersect(
        in_features=[
            [locked_fc_line_clipped_lyr],
            [areas_chosen_within_locked_buffed_lyr],
        ],
        out_feature_class=files[fc.locked_fc_line_intersecting],
    )

    locked_fc_line_intersecting_lyr = "locked_fc_line_intersecting_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc_line_intersecting],
        out_layer=locked_fc_line_intersecting_lyr,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=locked_fc_line_intersecting_lyr,
        out_feature_class=files[fc.locked_areas_outside_buffer],
        buffer_distance_or_field=f"{min_width/2} Meter",
    )

    locked_areas_outside_buffer_lyr = "locked_areas_outside_buffer_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_areas_outside_buffer],
        out_layer=locked_areas_outside_buffer_lyr,
    )
    arcpy.analysis.Erase(
        in_features=locked_areas_outside_buffer_lyr,
        erase_features=files[fc.locked_fc_line],
        out_feature_class=files[fc.locked_fc_outward_buffer],
    )


def buff_small_segments(files: dict, min_width: int) -> None:
    """
    What:
        Finds the centre line of the small polygon segments. Then erases large enough areas and
        buffed locked areas from them. Lastly, the line segments are buffed to the minimum width
        requirement for the target polygon and dissolved with the locked areas buffers.
    """

    chosen_areas_lyr = "chosen_areas_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.areas_chosen], out_layer=chosen_areas_lyr
    )

    arcpy.cartography.CollapseHydroPolygon(
        in_features=chosen_areas_lyr,
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE",
    )

    centre_line_lyr = "centre_line_lyr"
    large_segments_lyr = "large_segments_lyr"
    locked_fc_outward_buffer_lyr = "locked_fc_outward_buffer_lyr"

    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.centre_line], out_layer=centre_line_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.segments_wide_enough], out_layer=large_segments_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc_outward_buffer],
        out_layer=locked_fc_outward_buffer_lyr,
    )
    arcpy.analysis.Erase(
        in_features=centre_line_lyr,
        erase_features=large_segments_lyr,
        out_feature_class=files[fc.small_segments_centre],
    )

    small_segments_centre_lyr = "small_segments_centre_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.small_segments_centre], out_layer=small_segments_centre_lyr
    )
    arcpy.analysis.Erase(
        in_features=small_segments_centre_lyr,
        erase_features=locked_fc_outward_buffer_lyr,
        out_feature_class=files[fc.only_small_segments_centre],
    )

    only_small_segments_centre_lyr = "only_small_segments_centre_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.only_small_segments_centre],
        out_layer=only_small_segments_centre_lyr,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=only_small_segments_centre_lyr,
        out_feature_class=files[fc.small_segments_locked_buffed_dissolved],
        buffer_distance_or_field=f"{min_width/2} Meters",
    )


if __name__ == "__main__":
    # """
    target = "ElvFlate"
    locked = "Samferdsel"

    input_fc = Arealdekke_N10.attribute_changer_output__n10_land_use.value

    lyr1 = "lyr1"
    lyr2 = "lyr2"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc, out_layer=lyr1, where_clause=f"arealdekke='{target}'"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc, out_layer=lyr2, where_clause=f"arealdekke='{locked}'"
    )

    buff_small_polygon_segments(
        target=target,
        input_fc=lyr1,
        output_fc=Arealdekke_N10.elim_output.value,
        locked_fc=lyr2,
        map_scale="N10",
    )
    # """
