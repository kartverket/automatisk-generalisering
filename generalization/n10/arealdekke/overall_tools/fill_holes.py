# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from collections import defaultdict
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
    surrounding_features = "surrounding_features"
    surrounding_lines = "surrounding_lines"
    intersecting_lines = "intersecting_lines"
    join_land_use = "join_land_use"


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
    create_split_points(files=files, width=width / 10)
    split_polygons(files=files, width=width)
    match_holes_with_surrounding_features(
        files=files, input_fc=input_fc, output_fc=output_fc
    )

    wfm.delete_created_files()


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
        names.qualified_small: wfm.build_file_path(
            file_name=names.qualified_small, file_type="gdb"
        ),
        #
        names.qualified_as_line: wfm.build_file_path(
            file_name=names.qualified_as_line, file_type="gdb"
        ),
        names.input_as_line: wfm.build_file_path(
            file_name=names.input_as_line, file_type="gdb"
        ),
        names.touching_lines: wfm.build_file_path(
            file_name=names.touching_lines, file_type="gdb"
        ),
        names.touching_points: wfm.build_file_path(
            file_name=names.touching_points, file_type="gdb"
        ),
        names.identical: wfm.build_file_path(
            file_name=names.identical, file_type="gdb"
        ),
        names.filtered_lines: wfm.build_file_path(
            file_name=names.filtered_lines, file_type="gdb"
        ),
        names.line_endpoints: wfm.build_file_path(
            file_name=names.line_endpoints, file_type="gdb"
        ),
        names.endpoint_buffer: wfm.build_file_path(
            file_name=names.endpoint_buffer, file_type="gdb"
        ),
        names.spatial_join: wfm.build_file_path(
            file_name=names.spatial_join, file_type="gdb"
        ),
        names.cutlines: wfm.build_file_path(file_name=names.cutlines, file_type="gdb"),
        names.split_result: wfm.build_file_path(
            file_name=names.split_result, file_type="gdb"
        ),
        names.surrounding_features: wfm.build_file_path(
            file_name=names.surrounding_features, file_type="gdb"
        ),
        names.surrounding_lines: wfm.build_file_path(
            file_name=names.surrounding_lines, file_type="gdb"
        ),
        names.intersecting_lines: wfm.build_file_path(
            file_name=names.intersecting_lines, file_type="gdb"
        ),
        names.join_land_use: wfm.build_file_path(
            file_name=names.join_land_use, file_type="gdb"
        ),
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
    land_use_types = {row[0] for row in arcpy.da.SearchCursor(input_fc, ["arealdekke"])}
    for land_use in land_use_types:
        arcpy.management.MakeFeatureLayer(
            in_features=input_fc,
            out_layer=land_use_lyr,
            where_clause=f"arealdekke = '{land_use}' AND Shape_Area < {min_size}",
        )
        arcpy.management.Append(
            inputs=land_use_lyr,
            target=files[names.qualified_small],
            schema_type="NO_TEST",
        )

    arcpy.management.RepairGeometry(
        in_features=files[names.qualified_small],
        delete_null="DELETE_NULL",
        validation_method="ESRI",
    )

    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[names.qualified_small],
        out_line_feature_class=files[names.filtered_lines],
        merge_adjacent_input_polygons="NO_MERGE",
    )


def match_holes_with_surrounding_features(
    files: dict, input_fc: str, output_fc: str
) -> None:
    """
    Adds correct land use categories to the holes based on the surrounding features.

    Args:
        files (dict): Dictionary with all the working files
        input_fc (str): Original feature class used as source for the land use categories
        output_fc (str): The feature class where the result should be saved
    """
    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=files[names.split_result],
        out_feature_class=files[names.surrounding_features],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[names.surrounding_features], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files[names.split_result],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.PolygonToLine(
        in_features=land_use_lyr, out_feature_class=files[names.surrounding_lines]
    )

    arcpy.analysis.Intersect(
        in_features=[files[names.surrounding_lines], files[names.split_result]],
        out_feature_class=files[names.intersecting_lines],
        output_type="LINE",
    )

    arcpy.analysis.SpatialJoin(
        target_features=files[names.split_result],
        join_features=files[names.intersecting_lines],
        out_feature_class=files[names.join_land_use],
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    poly_to_area = {
        oid: area
        for oid, area in arcpy.da.SearchCursor(land_use_lyr, ["OID@", "arealdekke"])
    }

    line_to_poly = {}
    with arcpy.da.SearchCursor(
        files[names.intersecting_lines],
        ["OID@", "LEFT_FID", "RIGHT_FID", "Shape_Length"],
    ) as cursor:
        for oid, left, right, length in cursor:
            if left != -1 and left in poly_to_area:
                line_to_poly[oid] = [poly_to_area[left], length]
            elif right != -1 and right in poly_to_area:
                line_to_poly[oid] = [poly_to_area[right], length]

    split_fields = {field.name for field in arcpy.ListFields(files[names.split_result])}
    if "arealdekke" not in split_fields:
        arcpy.management.AddField(
            in_table=files[names.split_result],
            field_name="arealdekke",
            field_type="TEXT",
            field_length=100,
        )

    join_to_line = defaultdict(list)
    with arcpy.da.SearchCursor(
        files[names.join_land_use], ["TARGET_FID", "JOIN_FID"]
    ) as cursor:
        for target_oid, line_oid in cursor:
            if line_oid != -1:
                join_to_line[target_oid].append(line_oid)

    target_to_category = {}
    for target_oid, line_oids in join_to_line.items():
        valid_lines = [line_oid for line_oid in line_oids if line_oid in line_to_poly]
        if not valid_lines:
            continue

        # Choose surrounding category from the longest shared border segment.
        prioritized_lines = sorted(
            valid_lines, key=lambda x: line_to_poly[x][1], reverse=True
        )

        i = 0
        invalid_categories = ["samferdsel"]
        while len(prioritized_lines) > i:
            chosen_line = prioritized_lines[i]
            if line_to_poly[chosen_line][0].lower() not in invalid_categories:
                target_to_category[target_oid] = line_to_poly[chosen_line][0]
                i += len(prioritized_lines)
            i += 1

    with arcpy.da.UpdateCursor(
        files[names.split_result], ["OID@", "arealdekke"]
    ) as cursor:
        for oid, _ in cursor:
            if oid in target_to_category:
                cursor.updateRow([oid, target_to_category[oid]])

    arcpy.management.Merge(
        inputs=[files[names.split_result], files[names.surrounding_features]],
        output=output_fc,
    )
