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

    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[fc.segments_too_small],
        out_line_feature_class=files[fc.centre_line],
        merge_adjacent_input_polygons="NO_MERGE",
    )


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
        fc.target_fc: wfm.build_file_path(file_name="target_fc", file_type="gdb"),
        fc.input_polygon_edge: wfm.build_file_path(
            file_name="input_polygon_edge", file_type="gdb"
        ),
        fc.input_polygon_minus_buffer: wfm.build_file_path(
            file_name="input_polygon_minus_buffer", file_type="gdb"
        ),
        fc.core_of_segments_wide_enough: wfm.build_file_path(
            file_name="core_of_segments_wide_enough", file_type="gdb"
        ),
        fc.core_wide_enough_segments_singlepart: wfm.build_file_path(
            file_name="core_wide_enough_segments_singlepart", file_type="gdb"
        ),
        fc.segments_wide_enough: wfm.build_file_path(
            file_name="segments_wide_enough", file_type="gdb"
        ),
        fc.segments_too_small: wfm.build_file_path(
            file_name="segments_too_small", file_type="gdb"
        ),
        fc.centre_line: wfm.build_file_path(file_name="centre_line", file_type="gdb"),
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
