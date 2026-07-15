# Libraries

import arcpy

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    fc,
    find_segments_under_min,
)
from generalization.n10.arealdekke.parameters.parameter_worker import get_min_width
from generalization.n10.arealdekke.overall_tools.area_aggregator import (
    aggregate_small_features,
)

# ========================
# Main function
# ========================


@timing_decorator
def remove_thin_tracks(
    target: str,
    input_fc: str,
    complete_fc: str,
    map_scale: str,
    track_type: str = "Samferdsel",
):
    """
    For areas of type target, remove all thin tracks of 'track_type'
    that goes through the area. This area should be replaced with the target
    area.

    Args:
        target (str): The target area type
        input_fc (str): The input feature class (only target areas)
        complete_fc (str): The complete feature class (entire land use dataset)
        map_scale (str): The current work map scale
        track_type (str, optional): The type of track to remove - defaults to "Samferdsel"
    """
    working_fc = Arealdekke_N10.thin_tracks_remover__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    width = get_min_width(
        map_scale=map_scale,
        target=target,
    )

    fetch_data(
        files=files,
        target=track_type,
        input_fc=input_fc,
        complete_fc=complete_fc,
        width=width,
    )
    if int(arcpy.management.GetCount(files[fc.target_fc])[0]) != 0:
        find_segments_under_min(files=files, min_width=width)
        filter_candidates(files=files)
        cleanup(files=files, target=target, complete_fc=complete_fc)

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of removing thin tracks.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that is keeping the temporary files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "input_without_target": wfm.build_file_path(
            file_name="input_without_target", file_type="gdb"
        ),
        fc.target_fc: wfm.build_file_path(
            file_name=fc.target_fc.value, file_type="gdb"
        ),
        fc.input_polygon_edge: wfm.build_file_path(
            file_name=fc.input_polygon_edge.value, file_type="gdb"
        ),
        fc.input_polygon_minus_buffer: wfm.build_file_path(
            file_name=fc.input_polygon_minus_buffer.value, file_type="gdb"
        ),
        fc.core_of_segments_wide_enough: wfm.build_file_path(
            file_name=fc.core_of_segments_wide_enough.value, file_type="gdb"
        ),
        fc.core_wide_enough_segments_singlepart: wfm.build_file_path(
            file_name=fc.core_wide_enough_segments_singlepart.value, file_type="gdb"
        ),
        fc.segments_wide_enough: wfm.build_file_path(
            file_name=fc.segments_wide_enough.value, file_type="gdb"
        ),
        fc.segments_too_small: wfm.build_file_path(
            file_name=fc.segments_too_small.value, file_type="gdb"
        ),
        "close_features": wfm.build_file_path(
            file_name="close_features", file_type="gdb"
        ),
        "aggregated_features": wfm.build_file_path(
            file_name="aggregated_features", file_type="gdb"
        ),
        "aggregated_target": wfm.build_file_path(
            file_name="aggregated_target", file_type="gdb"
        ),
        "aggregated_surrounding": wfm.build_file_path(
            file_name="aggregated_surrounding", file_type="gdb"
        ),
        "aggregated_target_complete": wfm.build_file_path(
            file_name="aggregated_target_complete", file_type="gdb"
        ),
        "invert_buffer": wfm.build_file_path(
            file_name="invert_buffer", file_type="gdb"
        ),
        "singlepart": wfm.build_file_path(file_name="singlepart", file_type="gdb"),
        "filtered_candidates": wfm.build_file_path(
            file_name="filtered_candidates", file_type="gdb"
        ),
        "mask": wfm.build_file_path(file_name="mask", file_type="gdb"),
        "mask_singlepart": wfm.build_file_path(
            file_name="mask_singlepart", file_type="gdb"
        ),
        "to_adjust": wfm.build_file_path(file_name="to_adjust", file_type="gdb"),
        "temporary_complete": wfm.build_file_path(
            file_name="temporary_complete", file_type="gdb"
        ),
        "test_output": wfm.build_file_path(file_name="test_output", file_type="gdb"),
    }


def fetch_data(
    files: dict, target: str, input_fc: str, complete_fc: str, width: int
) -> None:
    """
    Fetches the data of target that goes through or close to the input_fc.
    Prepares the data for further processing.

    Args:
        files (dict): Dictionary with all the temporary files
        target (str): The target area type (for this function)
        input_fc (str): The input feature class (only the main target features)
        complete_fc (str): The complete feature class (entire land use dataset)
        width (int): The minimum width of the target area type
    """
    lyr = f"{target}_lyr"
    arcpy.management.MakeFeatureLayer(in_features=complete_fc, out_layer=lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}'",
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr,
        overlap_type="INTERSECT",
        select_features=input_fc,
        selection_type="SUBSET_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=lyr, out_feature_class=files[fc.target_fc]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}'",
    )

    arcpy.analysis.Erase(
        in_features=lyr,
        erase_features=files[fc.target_fc],
        out_feature_class=files["input_without_target"],
    )

    for in_fc, tol, out_key in [
        [input_fc, width * 2 / 3, "aggregated_target"],
        [files[fc.target_fc], 0.1, "aggregated_surrounding"],
    ]:
        arcpy.management.CopyFeatures(
            in_features=in_fc, out_feature_class=files["close_features"]
        )
        aggregate_small_features(files=files, tol=tol)
        arcpy.management.CopyFeatures(
            in_features=files["aggregated_features"], out_feature_class=files[out_key]
        )


def filter_candidates(files: dict) -> None:
    """
    Processes the candidates of thin tracks so that
    only correct pieces are deleted and preserved.

    Args:
        files (dict): Dictionary with all the temporary files
    """
    arcpy.management.EliminatePolygonPart(
        in_features=files["aggregated_target"],
        out_feature_class=files["aggregated_target_complete"],
        condition="PERCENT",
        part_area_percent="90",
    )
    arcpy.analysis.Buffer(
        in_features=files["aggregated_target_complete"],
        out_feature_class=files["invert_buffer"],
        buffer_distance_or_field="-1 Meters",
    )

    arcpy.management.MultipartToSinglepart(
        in_features=files[fc.segments_too_small], out_feature_class=files["singlepart"]
    )

    lyr_1 = "lyr_1"
    arcpy.management.MakeFeatureLayer(in_features=files["singlepart"], out_layer=lyr_1)
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_1,
        overlap_type="INTERSECT",
        select_features=files["invert_buffer"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=lyr_1, out_feature_class=files["filtered_candidates"]
    )

    arcpy.analysis.Erase(
        in_features=files["aggregated_surrounding"],
        erase_features=files["aggregated_target_complete"],
        out_feature_class=files["mask"],
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files["mask"], out_feature_class=files["mask_singlepart"]
    )
    arcpy.analysis.Erase(
        in_features=files["filtered_candidates"],
        erase_features=files["mask_singlepart"],
        out_feature_class=files["to_adjust"],
    )

    lyr_2 = "lyr_2"
    arcpy.management.MakeFeatureLayer(
        in_features=files["mask_singlepart"], out_layer=lyr_2
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_2,
        overlap_type="INTERSECT",
        select_features=files["input_without_target"],
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.Append(
        inputs=lyr_2, target=files["to_adjust"], schema_type="NO_TEST"
    )


def cleanup(files: dict, target: str, complete_fc: str) -> None:
    """
    Cleans up the temporary files and saves the final output.

    Args:
        files (dict): Dictionary with all the temporary files
        target (str): The target area type
        complete_fc (str): The complete feature class
    """
    with arcpy.da.UpdateCursor(files["to_adjust"], ["arealdekke"]) as cursor:
        for row in cursor:
            row[0] = target
            cursor.updateRow(row)

    arcpy.analysis.Erase(
        in_features=complete_fc,
        erase_features=files["to_adjust"],
        out_feature_class=files["temporary_complete"],
    )

    arcpy.management.Merge(
        inputs=[files["temporary_complete"], files["to_adjust"]], output=complete_fc
    )
