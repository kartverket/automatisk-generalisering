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
# Constants
# ========================


LINE = {"ElvFlate": Arealdekke_N10.river_lines__n10_land_use.value}


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
    areas_chosen_within_locked_fc = "areas_chosen_within_locked_fc"
    areas_chosen_within_locked_buffed_fc = "areas_chosen_within_locked_buffed_fc"
    locked_fc_line_intersecting = "locked_fc_line_intersecting"
    locked_fc_outward_buffer = "locked_fc_outward_buffer"
    only_small_segments_centre = "only_small_segments_centre"
    mini_buffer = "mini_buffer"
    should_expand_candidates = "should_expand_candidates"
    should_expand = "should_expand"
    lines_to_keep_multipart = "lines_to_keep_multipart"
    lines_to_expand = "lines_to_expand"
    areas_to_delete = "areas_to_delete"
    intermediate_target = "intermediate_target"
    intermediate_lines = "intermediate_lines"


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
    to_line = target in LINE

    extract_data(files=files, target_fc=target, input_fc=input_fc, locked_fc=locked_fc)

    if check_valid_feature_class(files[fc.target_fc], level=2):
        find_segments_under_min(files=files, min_width=min_width)
        choose_target_areas(files=files, min_width=min_width)
        get_shared_locked_boundary(files=files, min_width=min_width)
        buff_small_segments(files=files, min_width=min_width, to_line=to_line)

        create_overlapping_land_use(
            input_fc=files[fc.target_fc],
            buffered_fc=files[fc.small_segments_locked_buffed_dissolved],
            output_fc=output_fc,
        )

        if to_line:
            snap_lines(land_use_fc=output_fc, target=target, files=files)
    else:
        arcpy.management.CopyFeatures(in_features=input_fc, out_feature_class=output_fc)

    print(f"\n✅ Buffering of small segments finished!\n{'====='*15}\n")

    wfm.delete_created_files()


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
        fc.areas_chosen_within_locked_fc: wfm.build_file_path(
            file_name=fc.areas_chosen_within_locked_fc, file_type="gdb"
        ),
        fc.areas_chosen_within_locked_buffed_fc: wfm.build_file_path(
            file_name=fc.areas_chosen_within_locked_buffed_fc, file_type="gdb"
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
        fc.mini_buffer: wfm.build_file_path(file_name=fc.mini_buffer, file_type="gdb"),
        fc.should_expand_candidates: wfm.build_file_path(
            file_name=fc.should_expand_candidates, file_type="gdb"
        ),
        fc.should_expand: wfm.build_file_path(
            file_name=fc.should_expand, file_type="gdb"
        ),
        fc.lines_to_keep_multipart: wfm.build_file_path(
            file_name=fc.lines_to_keep_multipart, file_type="gdb"
        ),
        fc.lines_to_expand: wfm.build_file_path(
            file_name=fc.lines_to_expand, file_type="gdb"
        ),
        fc.areas_to_delete: wfm.build_file_path(
            file_name=fc.areas_to_delete, file_type="gdb"
        ),
        fc.intermediate_target: wfm.build_file_path(
            file_name=fc.intermediate_target, file_type="gdb"
        ),
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
        fc.intermediate_lines: wfm.build_file_path(
            file_name=fc.intermediate_lines, file_type="gdb"
        ),
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

    print("📦 Data extracted for target and locked areas")


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

    print(
        f"🔎 Segments under {min_width} meters found and extracted from target polygon"
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
    print("🎯 Target areas chosen for further processing")


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
    if int(arcpy.management.GetCount(land_use_lyr)[0]) > 0:
        arcpy.management.PolygonToLine(
            in_features=land_use_lyr, out_feature_class=files[fc.locked_fc_line]
        )
        arcpy.analysis.PairwiseClip(
            in_features=files[fc.locked_fc_line],
            clip_features=files[fc.overkill_buffer],
            out_feature_class=files[fc.locked_fc_line_clipped],
        )
        arcpy.analysis.PairwiseBuffer(
            in_features=files[fc.locked_fc_line_clipped],
            out_feature_class=files[fc.locked_fc_line_clipped_n_buffed_fc],
            buffer_distance_or_field=f"{min_width/2} Meters",
        )
        arcpy.analysis.Intersect(
            in_features=[
                files[fc.locked_fc_line_clipped_n_buffed_fc],
                files[fc.areas_chosen],
            ],
            out_feature_class=files[fc.areas_chosen_within_locked_fc],
        )
        arcpy.analysis.PairwiseBuffer(
            in_features=files[fc.areas_chosen_within_locked_fc],
            out_feature_class=files[fc.areas_chosen_within_locked_buffed_fc],
            buffer_distance_or_field=f"{min_width/2} Meter",
        )
        arcpy.analysis.Intersect(
            in_features=[
                files[fc.locked_fc_line_clipped],
                files[fc.areas_chosen_within_locked_buffed_fc],
            ],
            out_feature_class=files[fc.locked_fc_line_intersecting],
        )
        arcpy.analysis.PairwiseBuffer(
            in_features=files[fc.locked_fc_line_intersecting],
            out_feature_class=files[fc.locked_areas_outside_buffer],
            buffer_distance_or_field=f"{min_width/2} Meter",
        )
        arcpy.analysis.Erase(
            in_features=files[fc.locked_areas_outside_buffer],
            erase_features=land_use_lyr,
            out_feature_class=files[fc.locked_fc_outward_buffer],
        )

    print(
        "↔️ Shared boundaries between target and locked areas found and buffered outwards"
    )


def extract_below_limit(files: dict, min_width: int) -> None:
    """
    What:
        Extracts segments that are narrower than the minimum width requirement
        of the target polygon and stores them as line features in the specified
        output feature class.

        Centre lines passing through these narrow areas are removed from the
        complete line set, which is subsequently buffered by the minimum width.
        Extracted narrow segments must also exceed a length tolerance to be
        considered visible. Segments shorter than this tolerance are merged back
        into the remaining line set and buffered to the minimum width instead.
    """
    lim = min_width / 2
    arcpy.analysis.PairwiseBuffer(
        in_features=files[fc.input_polygon_edge],
        out_feature_class=files[fc.mini_buffer],
        buffer_distance_or_field=f"{lim / 2} Meters",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.areas_chosen],
        erase_features=files[fc.mini_buffer],
        out_feature_class=files[fc.should_expand_candidates],
    )
    arcpy.analysis.PairwiseBuffer(
        in_features=files[fc.should_expand_candidates],
        out_feature_class=files[fc.should_expand],
        buffer_distance_or_field=f"{lim / 2} Meters",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.small_segments_centre],
        erase_features=files[fc.should_expand],
        out_feature_class=files[fc.lines_to_keep_multipart],
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files[fc.lines_to_keep_multipart],
        out_feature_class=files[fc.intermediate_lines],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.intermediate_lines],
        out_layer=land_use_lyr,
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="Shape_Length < 10",
    )
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    arcpy.analysis.Buffer(
        in_features=files[fc.intermediate_lines],
        out_feature_class=files[fc.areas_to_delete],
        buffer_distance_or_field=f"{lim} Meters",
        line_side="FULL",
        line_end_type="FLAT",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.target_fc],
        erase_features=files[fc.areas_to_delete],
        out_feature_class=files[fc.intermediate_target],
    )
    arcpy.management.CopyFeatures(
        in_features=files[fc.intermediate_target], out_feature_class=files[fc.target_fc]
    )

    arcpy.analysis.Erase(
        in_features=files[fc.small_segments_centre],
        erase_features=files[fc.intermediate_lines],
        out_feature_class=files[fc.lines_to_expand],
    )

    print(
        f"📏 Especially small segments thinner than {lim} meters extracted from target polygon and stored in separate file."
    )


def buff_small_segments(files: dict, min_width: int, to_line: bool = False) -> None:
    """
    What:
        Finds the centre line of the small polygon segments. Then erases large enough areas and
        buffed locked areas from them. Lastly, the line segments are buffed to the minimum width
        requirement for the target polygon and dissolved with the locked areas buffers.
    """
    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[fc.areas_chosen],
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE",
    )
    arcpy.analysis.Erase(
        in_features=files[fc.centre_line],
        erase_features=files[fc.segments_wide_enough],
        out_feature_class=files[fc.small_segments_centre],
    )

    if to_line:
        extract_below_limit(files=files, min_width=min_width)

    lines_to_expand = (
        files[fc.lines_to_expand] if to_line else files[fc.small_segments_centre]
    )
    status: bool = arcpy.Exists(files[fc.locked_fc_outward_buffer])

    if status:
        arcpy.analysis.Erase(
            in_features=lines_to_expand,
            erase_features=files[fc.locked_fc_outward_buffer],
            out_feature_class=files[fc.only_small_segments_centre],
        )
    arcpy.analysis.PairwiseBuffer(
        in_features=files[fc.only_small_segments_centre] if status else lines_to_expand,
        out_feature_class=files[fc.small_segments_locked_buffed_dissolved],
        buffer_distance_or_field=f"{min_width/2} Meters",
    )

    print("⭕ Small segments buffered and dissolved with locked areas buffers")


def snap_lines(land_use_fc: str, target: str, files: dict) -> None:
    """
    What:
        Snaps the lines in input_fc to the lines in line_fc.
    """
    line_fc = LINE[target]

    arcpy.edit.Snap(
        in_features=files[fc.intermediate_lines],
        snap_environment=[[land_use_fc, "EDGE", "2.5 Meters"]],
    )
    arcpy.analysis.Erase(
        in_features=files[fc.intermediate_lines],
        erase_features=land_use_fc,
        out_feature_class=line_fc,
    )
    arcpy.edit.Snap(
        in_features=line_fc,
        snap_environment=[[land_use_fc, "EDGE", "1 Meters"]],
    )
