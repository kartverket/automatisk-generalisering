import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator
from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from input_data import input_n10
from generalization.n10.arealdekke.overall_tools.area_merger import area_merger

from composition_configs import core_config
from pathlib import Path
from custom_tools.general_tools.param_utils import initialize_params
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    buff_small_polygon_segments_parameters,
)
from generalization.n10.arealdekke.overall_tools.overlap_merger import (
    create_overlapping_land_use,
)

arcpy.env.overwriteOutput = True


@timing_decorator
def buff_small_polygon_segments(
    target: str, input_fc: str, output_fc: str, locked_fc: set, map_scale: str
):
    """
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
    working_fc = Arealdekke_N10.buffed_polygon_segments__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)
    files = files_setup(wfm=wfm)

    params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"
    scale_parameters = initialize_params(
        params_path=params_path,
        class_name="BuffSmallPolygonSegments",
        map_scale=map_scale,
        dataclass=buff_small_polygon_segments_parameters,
    )
    min_width = scale_parameters.min_width[target]

    extract_data(files=files, target_fc=target, locked_fc=locked_fc, input_fc=input_fc)
    find_segments_under_min(files=files, min_width=min_width)
    choose_target_areas(files=files)
    get_shared_locked_boundary(files=files, min_width=min_width)
    buff_small_segments(files=files, min_width=min_width)

    create_overlapping_land_use(
        input_fc=files[fc.target_fc],
        buffered_fc=files[fc.small_segments_locked_buffed_dissolved],
        output_fc=output_fc,
    )

    wfm.delete_created_files()


class fc(Enum):
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
    locked_fc_line_intersecting = "locked_fc_line_intersecting"
    locked_fc_outward_buffer = "locked_fc_outward_buffer"
    only_small_segments_centre = "only_small_segments_centre"
    test = "test"
    work_fc = "work_fc"
    output_fc = "output_fc"


@timing_decorator
def files_setup(wfm: WorkFileManager) -> dict:

    # Extract data
    target_fc = wfm.build_file_path(file_name="target_fc", file_type="gdb")
    locked_fc = wfm.build_file_path(file_name="locked_fc", file_type="gdb")

    # Get shared boundary
    locked_areas_outside_buffer = wfm.build_file_path(
        file_name="locked_areas_outside_buffer", file_type="gdb"
    )
    locked_fc_line = wfm.build_file_path(file_name="locked_fc_line", file_type="gdb")
    locked_fc_line_clipped = wfm.build_file_path(
        file_name="locked_fc_line_clipped", file_type="gdb"
    )
    locked_fc_line_intersecting = wfm.build_file_path(
        file_name="locked_fc_line_intersecting", file_type="gdb"
    )
    locked_fc_outward_buffer = wfm.build_file_path(
        file_name="locked_fc_outward_buffer", file_type="gdb"
    )

    # Find segments under min
    input_polygon_edge = wfm.build_file_path(
        file_name="input_polygon_edge", file_type="gdb"
    )
    input_polygon_minus_buffer = wfm.build_file_path(
        file_name="input_polygon_minus_buffer", file_type="gdb"
    )
    core_of_segments_wide_enough = wfm.build_file_path(
        file_name="core_of_segments_wide_enough", file_type="gdb"
    )
    segments_wide_enough = wfm.build_file_path(
        file_name="segments_wide_enough", file_type="gdb"
    )
    core_wide_enough_segments_singlepart = wfm.build_file_path(
        file_name="core_wide_enough_segments_singlepart", file_type="gdb"
    )
    segments_too_small = wfm.build_file_path(
        file_name="segments_too_small", file_type="gdb"
    )
    segments_too_small_single = wfm.build_file_path(
        file_name="segments_too_small_single", file_type="gdb"
    )

    # Choose target areas
    overkill_buffer = wfm.build_file_path(file_name="overkill_buffer", file_type="gdb")
    areas_chosen = wfm.build_file_path(file_name="areas_chosen", file_type="gdb")

    # Buff small segments
    only_small_segments_centre = wfm.build_file_path(
        file_name="only_small_segments_centre", file_type="gdb"
    )
    centre_line = wfm.build_file_path(file_name="centre_line", file_type="gdb")
    small_segments_centre = wfm.build_file_path(
        file_name="small_segments_centre", file_type="gdb"
    )
    small_segments_enlarged = wfm.build_file_path(
        file_name="small_segments_enlarged", file_type="gdb"
    )
    small_segments_locked_buffed_merged = wfm.build_file_path(
        file_name="small_segments_locked_buffed_merged", file_type="gdb"
    )
    small_segments_locked_buffed_dissolved = wfm.build_file_path(
        file_name="small_segments_locked_buffed_dissolved", file_type="gdb"
    )

    # Other
    test = wfm.build_file_path(file_name="test", file_type="gdb")
    work_fc = wfm.build_file_path(file_name="work_fc", file_type="gdb")
    output_fc = wfm.build_file_path(file_name="output_fc", file_type="gdb")

    return {
        fc.target_fc: target_fc,
        fc.locked_fc: locked_fc,
        fc.locked_areas_outside_buffer: locked_areas_outside_buffer,
        fc.locked_fc_line: locked_fc_line,
        fc.locked_fc_line_clipped: locked_fc_line_clipped,
        fc.input_polygon_edge: input_polygon_edge,
        fc.input_polygon_minus_buffer: input_polygon_minus_buffer,
        fc.core_of_segments_wide_enough: core_of_segments_wide_enough,
        fc.segments_wide_enough: segments_wide_enough,
        fc.core_wide_enough_segments_singlepart: core_wide_enough_segments_singlepart,
        fc.segments_too_small: segments_too_small,
        fc.segments_too_small_single: segments_too_small_single,
        fc.overkill_buffer: overkill_buffer,
        fc.areas_chosen: areas_chosen,
        fc.locked_fc_line_intersecting: locked_fc_line_intersecting,
        fc.locked_fc_outward_buffer: locked_fc_outward_buffer,
        fc.only_small_segments_centre: only_small_segments_centre,
        fc.centre_line: centre_line,
        fc.small_segments_centre: small_segments_centre,
        fc.small_segments_enlarged: small_segments_enlarged,
        fc.small_segments_locked_buffed_merged: small_segments_locked_buffed_merged,
        fc.small_segments_locked_buffed_dissolved: small_segments_locked_buffed_dissolved,
        fc.test: test,
        fc.work_fc: work_fc,
        fc.output_fc: output_fc,
    }


@timing_decorator
def extract_data(files: dict, target_fc: str, locked_fc: set, input_fc) -> None:

    # Extract the target fc from the data layer.
    target_fc_lyr = "target_fc_lyr"
    where = f"arealdekke='{target_fc}'"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc, out_layer=target_fc_lyr, where_clause=where
    )
    arcpy.management.CopyFeatures(
        in_features=target_fc_lyr, out_feature_class=files[fc.target_fc]
    )

    # Extract the locked areas from the data layer that share a line with the target fc.
    if locked_fc:
        locked_fc_lyr = "locked_fc_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=input_fc,
            out_layer=locked_fc_lyr,
        )

        arcpy.management.SelectLayerByLocation(
            in_layer=locked_fc_lyr,
            overlap_type="SHARE_A_LINE_SEGMENT_WITH",
            select_features=target_fc_lyr,
            selection_type="NEW_SELECTION",
        )
        arcpy.management.CopyFeatures(
            in_features=locked_fc_lyr, out_feature_class=files[fc.locked_fc]
        )


@timing_decorator
def find_segments_under_min(files: dict, min_width: int) -> None:

    # Create a lyr with the outline of the input polygon
    input_polygon_lyr = "input_polygon_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.target_fc], out_layer=input_polygon_lyr
    )
    arcpy.management.PolygonToLine(
        in_features=input_polygon_lyr, out_feature_class=files[fc.input_polygon_edge]
    )

    # Use polygon outline to create a negative buffer
    input_polygon_edge_lyr = "input_polygon_edge_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.input_polygon_edge], out_layer=input_polygon_edge_lyr
    )

    arcpy.analysis.Buffer(
        in_features=input_polygon_edge_lyr,
        out_feature_class=files[fc.input_polygon_minus_buffer],
        buffer_distance_or_field=f"{min_width/2} Meters",
        line_side="FULL",
    )

    # Areas not intersecting the minus buffer are large enough. Extract them into its own layer.
    input_polygon_minus_buffer_lyr = "input_polygon_minus_buffer_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.input_polygon_minus_buffer],
        out_layer=input_polygon_minus_buffer_lyr,
    )
    arcpy.analysis.Erase(
        in_features=input_polygon_lyr,
        erase_features=input_polygon_minus_buffer_lyr,
        out_feature_class=files[fc.core_of_segments_wide_enough],
    )

    # Create a full buffer for the core of the wide enough segments to get them back to their original size
    core_of_segments_wide_enough_lyr = "core_of_segments_wide_enough_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.core_of_segments_wide_enough],
        out_layer=core_of_segments_wide_enough_lyr,
    )

    arcpy.management.RepairGeometry(
        in_features=core_of_segments_wide_enough_lyr, delete_null="DELETE_NULL"
    )
    arcpy.management.MultipartToSinglepart(
        in_features=core_of_segments_wide_enough_lyr,
        out_feature_class=files[fc.core_wide_enough_segments_singlepart],
    )

    core_wide_enough_segments_singlepart_lyr = (
        "core_wide_enough_segments_singlepart_lyr"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.core_wide_enough_segments_singlepart],
        out_layer=core_wide_enough_segments_singlepart_lyr,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=core_wide_enough_segments_singlepart_lyr,
        out_feature_class=files[fc.segments_wide_enough],
        buffer_distance_or_field=f"{min_width/2} Meters",
    )

    # Remove the large enough segments from the original polyon
    segments_wide_enough_lyr = "segments_wide_enough_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.segments_wide_enough], out_layer=segments_wide_enough_lyr
    )
    arcpy.analysis.Erase(
        in_features=input_polygon_lyr,
        erase_features=segments_wide_enough_lyr,
        out_feature_class=files[fc.segments_too_small],
    )


@timing_decorator
def choose_target_areas(files: dict) -> None:

    # Create an overkill buffer that includes the small segments and some of the area around.
    segments_too_small_single_lyr = "segments_too_small_single_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.segments_too_small],
        out_layer=segments_too_small_single_lyr,
    )

    arcpy.analysis.Buffer(
        in_features=segments_too_small_single_lyr,
        out_feature_class=files[fc.overkill_buffer],
        buffer_distance_or_field="15 Meters",
        line_side="FULL",
    )

    # Clip original polygon to get area with the too small segments
    overkill_buffer_lyr = "overkill_buffer_lyr"
    original_polygon_lyr = "original_polygon_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.overkill_buffer], out_layer=overkill_buffer_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.target_fc], out_layer=original_polygon_lyr
    )

    try:
        arcpy.analysis.PairwiseClip(
            in_features=original_polygon_lyr,
            clip_features=overkill_buffer_lyr,
            out_feature_class=files[fc.areas_chosen],
        )
    except:
        arcpy.analysis.Clip(
            in_features=original_polygon_lyr,
            clip_features=overkill_buffer_lyr,
            out_feature_class=files[fc.areas_chosen],
        )


@timing_decorator
def get_shared_locked_boundary(files: dict, min_width: int) -> None:

    # Select all locked polygons who intersect the overkill buffer
    overkill_lyr = "overkill_lyr"
    locked_fc_lyr = "locked_fc_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.overkill_buffer], out_layer=overkill_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc], out_layer=locked_fc_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=locked_fc_lyr,
        overlap_type="INTERSECT",
        select_features=overkill_lyr,
        selection_type="NEW_SELECTION",
    )

    # Make the selected polygons into polylines
    arcpy.management.PolygonToLine(
        in_features=locked_fc_lyr, out_feature_class=files[fc.locked_fc_line]
    )

    # Clip the polylines to the overkill buffer
    locked_fc_line_lyr = "locked_fc_line_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_fc_line], out_layer=locked_fc_line_lyr
    )
    arcpy.analysis.Clip(
        in_features=locked_fc_line_lyr,
        clip_features=overkill_lyr,
        out_feature_class=files[fc.locked_fc_line_clipped],
    )

    try:
        arcpy.analysis.PairwiseClip(
            in_features=locked_fc_line_lyr,
            clip_features=overkill_lyr,
            out_feature_class=files[fc.locked_fc_line_clipped],
        )
    except:
        arcpy.analysis.Clip(
            in_features=locked_fc_line_lyr,
            clip_features=overkill_lyr,
            out_feature_class=files[fc.locked_fc_line_clipped],
        )

    # Find the intersection between the target polygon and the locked fc
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

    # Erase the original locked fc from the new buffer.
    locked_areas_outside_buffer_lyr = "locked_areas_outside_buffer_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.locked_areas_outside_buffer],
        out_layer=locked_areas_outside_buffer_lyr,
    )
    arcpy.analysis.Erase(
        in_features=locked_areas_outside_buffer_lyr,
        erase_features=locked_fc_lyr,
        out_feature_class=files[fc.locked_fc_outward_buffer],
    )


@timing_decorator
def buff_small_segments(files: dict, min_width: int) -> None:

    # Use collapse hydro polygon to find the centre line of the segments
    chosen_areas_lyr = "chosen_areas_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.areas_chosen], out_layer=chosen_areas_lyr
    )

    arcpy.cartography.CollapseHydroPolygon(
        in_features=chosen_areas_lyr,
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE",
    )

    # Erase large enough areas from the centre line and the locked area buffer
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

    # Buff the centre line to min width
    only_small_segments_centre_lyr = "only_small_segments_centre_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.only_small_segments_centre],
        out_layer=only_small_segments_centre_lyr,
    )

    try:
        arcpy.analysis.PairwiseBuffer(
            in_features=only_small_segments_centre_lyr,
            out_feature_class=files[fc.small_segments_enlarged],
            buffer_distance_or_field=f"{min_width/2} Meters",
        )

    except:
        arcpy.analysis.Buffer(
            in_features=only_small_segments_centre_lyr,
            out_feature_class=files[fc.small_segments_enlarged],
            buffer_distance_or_field=f"{min_width/2} Meters",
        )

    # Dissolve the locked fc buffed segments with the rest of the target polygon.
    small_segments_enlarged_lyr = "small_segments_enlarged_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.small_segments_enlarged],
        out_layer=small_segments_enlarged_lyr,
    )
    arcpy.management.Merge(
        inputs=[locked_fc_outward_buffer_lyr, small_segments_enlarged_lyr],
        output=files[fc.small_segments_locked_buffed_merged],
    )

    small_segments_locked_buffed_merged_lyr = "small_segments_locked_buffed_merged_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.small_segments_locked_buffed_merged],
        out_layer=small_segments_locked_buffed_merged_lyr,
    )
    arcpy.management.Dissolve(
        in_features=small_segments_locked_buffed_merged_lyr,
        out_feature_class=files[fc.small_segments_locked_buffed_dissolved],
    )


if __name__ == "__main__":
    buff_small_polygon_segments(
        target_fc="Ferskvann_elv_bekk",
        input_fc=input_n10.Arealdekke_Buskerud,
        locked_fc=["Samferdsel"],
        output_fc="output",
        map_scale="N10",
    )
