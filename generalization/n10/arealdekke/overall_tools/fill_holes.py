# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    LINE,
)
from generalization.n10.arealdekke.category_tools.thin_poly_to_point import (
    create_split_points,
    data_preparation,
    split_polygons,
)

# ========================
# Class
# ========================


class names(StrEnum):
    complete = "complete"
    filtered_lines = "filtered_lines"
    qualified_small = "qualified_small"
    qualified_as_line = "qualified_as_line"
    input_as_line = "input_as_line"
    touching_lines = "touching_lines"
    touching_points = "touching_points"
    identical = "identical"
    line_endpoints = "line_endpoints"
    endpoint_buffer = "endpoint_buffer"
    spatial_join = "spatial_join"
    cutlines = "cutlines"
    split_result = "split_result"


# ========================
# Main function
# ========================


@timing_decorator
def fill_holes(input_fc: str, output_fc: str) -> None:
    """
    Adjusts the input geometries with topologycal errors so that the output
    geometries are valid and do not contain any holes.

    Args:
        input_fc (str): The feature class with polygon geometries to be processed
        output_fc (str): The feature class where the result should be saved
    """
    # Set up WorkFileManager
    fc = Arealdekke_N10.fill_holes__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = file_setup(wfm=wfm)
    min_size = 20  # Minimum size of a polygon of any kind
    width = 10  # General width large enough to cover any hole

    data_sorting(input_fc=input_fc, files=files, min_size=min_size)
    data_preparation(complete_fc=input_fc, files=files)
    create_split_points(files=files, width=width)
    split_polygons(files=files, width=width)


# ========================
# Helper functions
# ========================


def file_setup(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of filling holes.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        names.complete: wfm.build_file_path(file_name=names.complete, file_type="gdb"),
        #
        # Holes:
        names.qualified_small: wfm.build_file_path(file_name=names.qualified_small, file_type="gdb"),
        #
        names.qualified_as_line: wfm.build_file_path(file_name=names.qualified_as_line, file_type="gdb"),
        names.input_as_line: wfm.build_file_path(file_name=names.input_as_line, file_type="gdb"),
        names.touching_lines: wfm.build_file_path(file_name=names.touching_lines, file_type="gdb"),
        names.touching_points: wfm.build_file_path(file_name=names.touching_points, file_type="gdb"),
        names.identical: wfm.build_file_path(file_name=names.identical, file_type="gdb"),
        names.filtered_lines: wfm.build_file_path(file_name=names.filtered_lines, file_type="gdb"),
        names.line_endpoints: wfm.build_file_path(file_name=names.line_endpoints, file_type="gdb"),
        names.endpoint_buffer: wfm.build_file_path(file_name=names.endpoint_buffer, file_type="gdb"),
        names.spatial_join: wfm.build_file_path(file_name=names.spatial_join, file_type="gdb"),
        names.cutlines: wfm.build_file_path(file_name=names.cutlines, file_type="gdb"),
        names.split_result: wfm.build_file_path(file_name=names.split_result, file_type="gdb"),
    }


def data_sorting(input_fc: str, files: dict, min_size: int) -> None:
    """
    Sorts the data in the input feature class into different working files.

    Args:
        input_fc (str): The feature class with polygon geometries to be processed
        files (dict): Dictionary with all the working files
        min_size (int): Minimum size of a polygon that can be left alone
    """
    # Fetch line layers and create a complete
    # set of polygons covering the entire area
    active_line_layers = [val for val in LINE.values() if arcpy.Exists(val)]
    arcpy.management.FeatureToPolygon(
        in_features=[input_fc] + active_line_layers,
        out_feature_class=files[names.complete],
    )

    # Removes the input from the complete set
    # => the remaining polygons are the holes
    arcpy.analysis.Erase(
        in_features=files[names.complete],
        erase_features=input_fc,
        out_feature_class=files[names.qualified_small],
    )

    # For all landd use types, fetch polygons smaller than
    # the minimum size and add them to the holes
    land_use_lyr = "land_use_lyr"
    land_use_types = {
        row[0]
        for row in arcpy.da.SearchCursor(input_fc, ["arealdekke"])
    }
    for land_use in land_use_types:
        arcpy.management.MakeFeatureLayer(
            in_features=input_fc,
            out_layer=land_use_lyr,
            where_clause=f"arealdekke = '{land_use}' AND Shape_Area < {min_size}",
        )
        arcpy.management.Append(
            inputs=land_use_lyr, target=files[names.qualified_small], schema_type="NO_TEST"
        )

    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[names.qualified_small],
        out_line_feature_class=files[names.filtered_lines],
        merge_adjacent_input_polygons="NO_MERGE"
    )






















@timing_decorator
def fill_holes_2(
    input_fc: str, output_fc: str, target: str, locked_categories: set
) -> None:
    """
    Fills holes in the polygons of the input feature class and saves the result in the output feature class.

    Args:
        input_fc (str): The feature class with polygon geometries to be processed
        output_fc (str): The feature class where the result should be saved
        target (str): Land use category that is being processed
        locked_categories (set): Set of land use categories that should not be modified during the process
    """
    # Set up WorkFileManager
    fc = Arealdekke_N10.fill_holes__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    # Create temporary file for filled holes
    files = create_wfm_gdbs(wfm=wfm)

    # Fill holes in the input feature class and save them in a new feature class
    remove_locked_features_from_input(
        input_fc=input_fc, files=files, locked_categories=locked_categories
    )
    find_holes(files=files, target=target)
    match_holes_with_surrounding_features(
        files=files, output_fc=output_fc, target=target
    )

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of filling holes.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "copy_of_input": wfm.build_file_path(
            file_name="copy_of_input", file_type="gdb"
        ),
        "complete": wfm.build_file_path(file_name="complete", file_type="gdb"),
        "locked_features": wfm.build_file_path(
            file_name="locked_features", file_type="gdb"
        ),
        "complete_without_locked": wfm.build_file_path(
            file_name="complete_without_locked", file_type="gdb"
        ),
        "holes": wfm.build_file_path(file_name="holes", file_type="gdb"),
        "target_features": wfm.build_file_path(
            file_name="target_features", file_type="gdb"
        ),
        "intersecting_features": wfm.build_file_path(
            file_name="intersecting_features", file_type="gdb"
        ),
        "spatial_join": wfm.build_file_path(file_name="spatial_join", file_type="gdb"),
        "merged_data": wfm.build_file_path(file_name="merged_data", file_type="gdb"),
        "dissolved_data": wfm.build_file_path(
            file_name="dissolved_data", file_type="gdb"
        ),
        "remaining_features": wfm.build_file_path(
            file_name="remaining_features", file_type="gdb"
        ),
    }


def remove_locked_features_from_input(
    input_fc: str, files: dict, locked_categories: set
) -> None:
    """
    Removes the features of the locked categories from the input feature class to avoid modifying these during the process.

    Args:
        input_fc (str): The feature class with polygon geometries to be processed
        files (dict): Dictionary with all the working files
        locked_categories (set): Set of land use categories that should not be modified during the process
    """
    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    # Create Polygons of the holes
    active_line_layers = [key for key in LINE.keys() if arcpy.Exists(key)]
    arcpy.management.FeatureToPolygon(
        in_features=[files["copy_of_input"]] + active_line_layers,
        out_feature_class=files["complete"],
    )

    land_use_lyr = "land_use_lyr"

    locked_categories_sql = ", ".join(
        [f"'{category}'" for category in locked_categories]
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke IN ({locked_categories_sql})",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["locked_features"]
    )

    arcpy.analysis.Erase(
        in_features=files["complete"],
        erase_features=land_use_lyr,
        out_feature_class=files["complete_without_locked"],
    )

    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


def find_holes(files: dict, target: str) -> None:
    """
    Finds holes in the input feature class and saves them in a temporary file.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Land use category that is being processed
    """
    # Collect the holes and store them in a separate feature class
    arcpy.analysis.Erase(
        in_features=files["complete_without_locked"],
        erase_features=files["copy_of_input"],
        out_feature_class=files["holes"],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    # Collect the features of the target category and store them in a separate feature class
    sql = f"arealdekke = '{target}'"
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="NEW_SELECTION", where_clause=sql
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["target_features"]
    )
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)

    # Collect the features that are intersecting with the holes and store them in a separate feature class
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files["holes"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["intersecting_features"]
    )
    arcpy.management.DeleteFeatures(in_features=land_use_lyr)


def match_holes_with_surrounding_features(
    files: dict, output_fc: str, target: str
) -> None:
    """
    Matches the hole geometries with the surrounding features and merges these together.

    Args:
        files (dict): Dictionary with all the working files
        output_fc (str): Feature class to store the final output
        target (str): Land use category that is being processed
    """
    match_attribute = "JOIN_FID"

    existing_fields = [f.name for f in arcpy.ListFields(files["holes"])]
    while match_attribute in existing_fields:
        arcpy.management.DeleteField(
            in_table=files["holes"], drop_field=match_attribute
        )
        existing_fields = [f.name for f in arcpy.ListFields(files["holes"])]

    arcpy.management.CalculateField(
        in_table=files["intersecting_features"],
        field=match_attribute,
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )

    arcpy.analysis.SpatialJoin(
        target_features=files["holes"],
        join_features=files["intersecting_features"],
        out_feature_class=files["spatial_join"],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    arcpy.management.Merge(
        inputs=[files["spatial_join"], files["intersecting_features"]],
        output=files["merged_data"],
    )

    arcpy.management.Dissolve(
        in_features=files["merged_data"],
        out_feature_class=files["dissolved_data"],
        dissolve_field=match_attribute,
    )

    # Fetch original attributes
    changed_geometries = {
        oid: geom
        for oid, geom in arcpy.da.SearchCursor(
            files["dissolved_data"], [match_attribute, "SHAPE@"]
        )
    }

    with arcpy.da.UpdateCursor(
        files["intersecting_features"], ["OID@", "SHAPE@"]
    ) as cursor:
        for oid, _ in cursor:
            if oid in changed_geometries:
                cursor.updateRow([oid, changed_geometries[oid]])

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["spatial_join"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"{match_attribute} IS NULL",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["remaining_features"]
    )

    with arcpy.da.UpdateCursor(files["remaining_features"], ["arealdekke"]) as cursor:
        for _ in cursor:
            cursor.updateRow([target])

    arcpy.management.Merge(
        inputs=[
            files["copy_of_input"],
            files["locked_features"],
            files["target_features"],
            files["intersecting_features"],
            files["remaining_features"],
        ],
        output=output_fc,
    )


if __name__ == "__main__":
    fill_holes(
        input_fc=Arealdekke_N10.arealdekke_class_final__n10_land_use.value,
        output_fc=None
    )