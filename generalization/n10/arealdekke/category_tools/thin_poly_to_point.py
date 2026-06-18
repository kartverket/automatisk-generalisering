# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    fc,
    find_segments_under_min,
    get_min_width,
)

input_fc = (
    r"C:\GIS_Files\ag_outputs\n10\land_use.gdb\E_gangsykkel___gangsykkel___n10_land_use"
)


# ========================
# Main function
# ========================


@timing_decorator
def pointify_thin_poly(
    target: str, input_fc: str, output_fc: str, locked_fc: str, map_scale: str
):
    """
    ...
    """
    working_fc = Arealdekke_N10.poly_to_point__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    width = get_min_width(map_scale=map_scale, target=target)
    data_selection(input_fc=input_fc, files=files, target=target)
    find_segments_under_min(files=files, min_width=width)
    create_and_filter_line_data(files=files)
    create_points(files=files)
    remove_small_pieces(input_fc=input_fc, files=files)
    split_qualified_pieces(input_fc=input_fc, files=files, target=target)


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of pointifying thin polygons.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
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
        fc.centre_line: wfm.build_file_path(
            file_name=fc.centre_line.value, file_type="gdb"
        ),
        "filtered_lines": wfm.build_file_path(
            file_name="filtered_lines", file_type="gdb"
        ),
        "points": wfm.build_file_path(file_name="points", file_type="gdb"),
        "small_areas_single": wfm.build_file_path(
            file_name="small_areas_single", file_type="gdb"
        ),
        "qualified_small": wfm.build_file_path(file_name="qualified_small", file_type="gdb"),
        "erased_small_areas": wfm.build_file_path(
            file_name="erased_small_areas", file_type="gdb"
        ),
        "qualified_as_line": wfm.build_file_path(file_name="qualified_as_line", file_type="gdb"),
        "input_as_line": wfm.build_file_path(file_name="input_as_line", file_type="gdb")
    }


def data_selection(input_fc: str, files: dict, target: str) -> None:
    """
    Selects and copies relevant data into separate feature classes.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Name of the feature to consider during pointifying
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[fc.target_fc]
    )


def create_and_filter_line_data(files: dict) -> None:
    """
    Creates centre lines of the small polygon parts, and filter those that are large enough.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[fc.segments_too_small],
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE",
    )

    land_use_lyr = "land_use_lyr"
    tol = 15  # Tolerance in m for valid length
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.centre_line],
        out_layer=land_use_lyr,
        where_clause=f"Shape_Length >= {tol}",
    )

    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["filtered_lines"]
    )


def create_points(files: dict) -> None:
    """
    Creates points along the created centre lines.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.management.GeneratePointsAlongLines(
        Input_Features=files["filtered_lines"],
        Output_Feature_Class=files["points"],
        Point_Placement="DISTANCE",
        Distance=20,
        Include_End_Points="END_POINTS",
    )


def remove_small_pieces(input_fc: str, files: dict) -> None:
    """
    Removes the polygon parts that has been pointifyied and replace these areas with largest adjacent category.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
    """
    arcpy.management.MultipartToSinglepart(
        in_features=files[fc.segments_too_small],
        out_feature_class=files["small_areas_single"],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["small_areas_single"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="CONTAINS",
        select_features=files["filtered_lines"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(in_features=land_use_lyr, out_feature_class=files["qualified_small"])

    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=files["qualified_small"],
        out_feature_class=files["erased_small_areas"],
    )

def split_qualified_pieces(input_fc: str, files: dict, target: str) -> None:
    """
    Splits the qualified small pieces depending on adjacent features.

    Method:
        - Detect points along the polygon with 3 intersecting areas
        - Split the qualified polygons orthogonal to the direction of the polygon 

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Name of the land use type to adjust
    """
    arcpy.management.FeatureToLine(in_features=files["qualified_small"], out_feature_class=files["qualified_as_line"])

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByLocation(in_layer=land_use_lyr, overlap_type="INTERSECT", select_features=files["qualified_small"], selection_type="NEW_SELECTION")
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=land_use_lyr, selection_type="SUBSET_SELECTION", where_clause=f"arealdekke <> '{target}'")

    arcpy.management.FeatureToLine(in_features=land_use_lyr, out_feature_class=files["input_as_line"])



# ========================

if __name__ == "__main__":
    import os

    gdb = os.path.dirname(input_fc)
    pattern = "poly_to_point"

    for dirpath, dirnames, filenames in arcpy.da.Walk(gdb, datatype="FeatureClass"):
        for feature in filenames:
            if feature.startswith(pattern):
                full_path = os.path.join(dirpath, feature)
                arcpy.management.Delete(full_path)

    pointify_thin_poly(
        target="Skog", input_fc=input_fc, output_fc="", locked_fc="", map_scale="N10"
    )
