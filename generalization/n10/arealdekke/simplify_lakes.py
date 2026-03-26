# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.attribute_changer import create_new_fc

# ========================
# Program
# ========================


@timing_decorator
def simplify_lakes(input_fc: str, output_fc: str) -> None:
    """
    Simplifies lakes by removing unneccessary detailed features and object types.

    What it removes:
        - ...

    Args:
        input_fc (str): Feature class with land use data, including lakes to be modified
        output_fc (str): Feature class with fixed lakes, modified to a complete land use data set
    """
    # 1) Sets up WorkFileManager
    fc = Arealdekke_N10.simplify_lakes__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # 2) Creates temporary files
    files = create_wfm_gdbs(wfm=wfm)

    # 3) Copies input data to separate feature class
    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    # ...
    fetch_relevant_data(files=files)
    simplify_and_smooth_lakes(files=files)
    adjust_not_lakes(files=files)
    fetch_original_data(files=files, output_fc=output_fc)


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of simplifying lakes.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    copy_of_input = wfm.build_file_path(file_name="copy_of_input", file_type="gdb")
    lakes = wfm.build_file_path(file_name="lakes", file_type="gdb")
    not_lakes = wfm.build_file_path(file_name="not_lakes", file_type="gdb")
    simplified_lakes = wfm.build_file_path(
        file_name="simplified_lakes", file_type="gdb"
    )
    smoothed_lakes = wfm.build_file_path(file_name="smoothed_lakes", file_type="gdb")
    polyfied_land_use = wfm.build_file_path(
        file_name="polyfied_land_use", file_type="gdb"
    )
    not_lakes_no_overlap = wfm.build_file_path(
        file_name="not_lakes_no_overlap", file_type="gdb"
    )
    spatial_join = wfm.build_file_path(file_name="spatial_join", file_type="gdb")
    merged = wfm.build_file_path(file_name="merged", file_type="gdb")
    not_lakes_dissolved = wfm.build_file_path(
        file_name="not_lakes_dissolved", file_type="gdb"
    )
    final_spatial_join = wfm.build_file_path(
        file_name="final_spatial_join", file_type="gdb"
    )

    return {
        "copy_of_input": copy_of_input,
        "lakes": lakes,
        "not_lakes": not_lakes,
        "simplified_lakes": simplified_lakes,
        "smoothed_lakes": smoothed_lakes,
        "polyfied_land_use": polyfied_land_use,
        "not_lakes_no_overlap": not_lakes_no_overlap,
        "spatial_join": spatial_join,
        "merged": merged,
        "not_lakes_dissolved": not_lakes_dissolved,
        "final_spatial_join": final_spatial_join,
    }


@timing_decorator
def fetch_relevant_data(files: dict) -> None:
    """
    Separates data into lakes and not lakes.

    Args:
        files (dict): Dictionary with all the working files
    """
    water_fields = ["'Ferskvann_innsjo_tjern'", "'Ferskvann_innsjo_tjern_regulert'"]
    sql = f"arealdekke IN ({', '.join(water_fields)})"

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="NEW_SELECTION", where_clause=sql
    )

    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["lakes"]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="SWITCH_SELECTION"
    )

    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["not_lakes"]
    )


@timing_decorator
def simplify_and_smooth_lakes(files: dict) -> None:
    """
    Simplifies the lakes to avoid huge amounts of details and smooths it afterwards.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.cartography.SimplifyPolygon(
        in_features=files["lakes"],
        out_feature_class=files["simplified_lakes"],
        algorithm="WEIGHTED_AREA",
        tolerance=5,
        error_option="RESOLVE_ERRORS",
        collapsed_point_option="NO_KEEP",
    )

    arcpy.cartography.SmoothPolygon(
        in_features=files["simplified_lakes"],
        out_feature_class=files["smoothed_lakes"],
        algorithm="BEZIER_INTERPOLATION",
        error_option="RESOLVE_ERRORS",
    )


@timing_decorator
def adjust_not_lakes(files: dict) -> None:
    """
    Erases overlap of water from other land use types
    and fills in holes that have been created.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.management.FeatureToPolygon(
        in_features=[files["not_lakes"], files["smoothed_lakes"]],
        out_feature_class=files["polyfied_land_use"],
    )

    arcpy.analysis.Erase(
        in_features=files["polyfied_land_use"],
        erase_features=files["smoothed_lakes"],
        out_feature_class=files["not_lakes_no_overlap"],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["not_lakes_no_overlap"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="WITHIN",
        select_features=files["not_lakes"],
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.analysis.SpatialJoin(
        target_features=land_use_lyr,
        join_features=files["not_lakes_no_overlap"],
        out_feature_class=files["spatial_join"],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="BOUNDARY_TOUCHES",
    )

    arcpy.management.CalculateField(
        in_table=files["not_lakes_no_overlap"],
        field="JOIN_FID",
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )

    arcpy.management.Merge(
        inputs=[files["not_lakes_no_overlap"], files["spatial_join"]],
        output=files["merged"],
    )

    arcpy.management.Dissolve(
        in_features=files["merged"],
        out_feature_class=files["not_lakes_dissolved"],
        dissolve_field="JOIN_FID",
        multi_part="SINGLE_PART",
    )

    arcpy.management.DeleteField(in_table=files["not_lakes_dissolved"], drop_field="JOIN_FID")


@timing_decorator
def fetch_original_data(files: dict, output_fc: str) -> None:
    """
    ...
    """
    arcpy.analysis.SpatialJoin(
        target_features=files["not_lakes_dissolved"],
        join_features=files["not_lakes"],
        out_feature_class=files["final_spatial_join"],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="LARGEST_OVERLAP",
    )

    create_new_fc(input_fc=files["copy_of_input"], output_fc=output_fc)


# ========================
# Helper functions
# ========================


#
