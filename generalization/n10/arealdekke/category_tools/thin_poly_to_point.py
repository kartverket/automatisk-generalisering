# Libraries

import arcpy
import numpy as np
import os

arcpy.env.overwriteOutput = True

from collections import Counter

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import (
    fc,
    find_segments_under_min,
    get_min_width,
)

# ========================
# Main function
# ========================


@timing_decorator
def pointify_thin_poly(
    target: str,
    input_fc: str,
    output_fc: str,
    locked_fc: str,
    complete_fc: str,
    map_scale: str,
):
    """
    Identifies thin areas of the target (type of arealdekke) and creates a line of points instead.
    The area that were replaced with points is changed to the biggest adjacent area type.

    Args:
        target (str): Name of the arealdekke type to consider
        input_fc (str): Path to the input feature class with target objects only
        output_fc (str): Path to the output feature class where the edited target features should be saved
        locked_fc (str): Path to feature class with locked features
        complete_fc (str): Path to feature class containing the entire and complete land use dataset
        map_scale (str): String representing the working map scale
    """
    working_fc = Arealdekke_N10.poly_to_point__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    width = get_min_width(map_scale=map_scale, target=target)
    locked_categories = {
        row[0] for row in arcpy.da.SearchCursor(locked_fc, ["arealdekke"])
    }

    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files[fc.target_fc]
    )

    find_segments_under_min(files=files, min_width=width)
    create_and_filter_line_data(files=files)
    create_points(files=files)
    remove_small_pieces(input_fc=input_fc, files=files)
    data_preparation(complete_fc=complete_fc, files=files, target=target)
    create_split_points(files=files, width=width)
    split_polygons(files=files, width=width)
    rewrite_attribute(
        files=files, output_fc=output_fc, locked_categories=locked_categories
    )

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of pointifying thin polygons.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that is keeping the files

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
        "small_areas_single": wfm.build_file_path(
            file_name="small_areas_single", file_type="gdb"
        ),
        "qualified_small": wfm.build_file_path(
            file_name="qualified_small", file_type="gdb"
        ),
        "erased_small_areas": wfm.build_file_path(
            file_name="erased_small_areas", file_type="gdb"
        ),
        "qualified_as_line": wfm.build_file_path(
            file_name="qualified_as_line", file_type="gdb"
        ),
        "input_as_line": wfm.build_file_path(
            file_name="input_as_line", file_type="gdb"
        ),
        "touching_lines": wfm.build_file_path(
            file_name="touching_lines", file_type="gdb"
        ),
        "touching_points": wfm.build_file_path(
            file_name="touching_points", file_type="gdb"
        ),
        "identical": wfm.build_file_path(file_name="identical", file_type="gdb"),
        "line_endpoints": wfm.build_file_path(
            file_name="line_endpoints", file_type="gdb"
        ),
        "endpoint_buffer": wfm.build_file_path(
            file_name="endpoint_buffer", file_type="gdb"
        ),
        "spatial_join": wfm.build_file_path(file_name="spatial_join", file_type="gdb"),
        "cutlines": wfm.build_file_path(file_name="cutlines", file_type="gdb"),
        "split_result": wfm.build_file_path(file_name="split_result", file_type="gdb"),
        "intersected_lines": wfm.build_file_path(
            file_name="intersected_lines", file_type="gdb"
        ),
        "test": wfm.build_file_path(file_name="test", file_type="gdb"),
    }


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
    tol = 15  # TODO: Tolerance in m for valid length
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
        Output_Feature_Class=Arealdekke_N10.poly_to_point_points__n10_land_use.value,
        Point_Placement="DISTANCE",
        Distance=20,  # TODO: Need to get a system for taking care of distance tolerances
        Include_End_Points="NO_END_POINTS",
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
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["qualified_small"]
    )

    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=files["qualified_small"],
        out_feature_class=files["erased_small_areas"],
    )


def data_preparation(complete_fc: str, files: dict, target: str) -> None:
    """
    Prepares the data for splitting.

    Args:
        complete_fc (str): Feature class with the complete dataset
        files (dict): Dictionary with all the working files
        target (str): Name of the land use type to adjust
    """
    arcpy.management.FeatureToLine(
        in_features=files["qualified_small"],
        out_feature_class=files["qualified_as_line"],
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=complete_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files["qualified_small"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="SUBSET_SELECTION",
        where_clause=f"arealdekke <> '{target}'",
    )

    arcpy.management.FeatureToLine(
        in_features=land_use_lyr, out_feature_class=files["input_as_line"]
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files["input_as_line"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files["qualified_as_line"],
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Erase(
        in_features=land_use_lyr,
        erase_features=files["qualified_as_line"],
        out_feature_class=files["touching_lines"],
    )


def create_split_points(files: dict, width: int) -> None:
    """
    Create and filter points where the original data should be splitted.

    Args:
        files (dict): Dictionary with all the working files
        width (int): Minimum width of the target feature
    """
    # A: Touching points
    create_featureclass_point(
        files["touching_points"],
        arcpy.Describe(files["touching_lines"]).spatialReference,
    )
    arcpy.management.AddField(files["touching_points"], "Line_ID", "LONG")
    insert_line_endpoints(
        files["touching_lines"], files["touching_points"], include_oid=True
    )

    # B: Remove points overlapping qualified lines
    delete_points_by_location(
        files["touching_points"], files["qualified_as_line"], invert=True
    )

    # C + D: Remove non-duplicate and then remove duplicate
    delete_non_duplicate_points(files["touching_points"], files["identical"])

    # E: Line endpoints from filtered lines
    create_featureclass_point(
        files["line_endpoints"],
        arcpy.Describe(files["filtered_lines"]).spatialReference,
    )
    insert_line_endpoints(files["filtered_lines"], files["line_endpoints"])

    # F: Buffer endpoints and delete touching points inside buffer
    buffer_and_delete(
        files["line_endpoints"],
        files["touching_points"],
        files["endpoint_buffer"],
        width * 2,
    )


def split_polygons(files: dict, width: int) -> None:
    """
    Split the thin polygons into multiple parts.

    Args:
        files (dict): Dictionary with all the working files
        width (int): Minimum width of the target feature
    """
    arcpy.analysis.SpatialJoin(
        target_features=files["touching_points"],
        join_features=files["qualified_small"],
        out_feature_class=files["spatial_join"],
    )

    # A: Select relevant areas
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["qualified_small"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=files["touching_points"],
        selection_type="NEW_SELECTION",
    )

    # B: Create cutlines
    cutlines = []

    centerlines = {  # Pre-load centerlines for fast lookup
        oid: geom
        for oid, geom in arcpy.da.SearchCursor(
            files["filtered_lines"], ["InPoly_FID", "SHAPE@"]
        )
    }

    point_dict = {}  # Spatial indexing of points
    with arcpy.da.SearchCursor(files["spatial_join"], ["SHAPE@", "ORIG_FID"]) as search:
        for geom, oid in search:
            point_dict.setdefault(oid, []).append(geom)

    with arcpy.da.SearchCursor(land_use_lyr, ["SHAPE@", "ORIG_FID"]) as search:
        for geom, oid in search:
            if oid not in point_dict:
                continue
            if oid not in centerlines:
                continue
            centerline = centerlines[oid]
            for pt in point_dict[oid]:
                cutline = make_orthogonal_cutline(pt, centerline, length=width)
                cutlines.append(cutline)

    if cutlines:
        arcpy.management.CopyFeatures(
            in_features=cutlines, out_feature_class=files["cutlines"]
        )

        # C: Split the polygons
        arcpy.management.FeatureToPolygon(
            in_features=[files["qualified_small"], files["cutlines"]],
            out_feature_class=files["split_result"],
        )
    else:
        arcpy.management.CopyFeatures(
            in_features=files["qualified_small"],
            out_feature_class=files["split_result"],
        )


def rewrite_attribute(files: dict, output_fc: str, locked_categories: set) -> None:
    """
    Fetches the original 'arealdekke' attribute value to the splitted features.

    Args:
        files (dict): Dictionary with all the working files
        output_fc (str): Where to store the final output
        locked_categories (set): A set containing the name of all land use
                                 categories that are locked
    """
    arcpy.analysis.Intersect(
        in_features=[files["input_as_line"], files["split_result"]],
        out_feature_class=files["intersected_lines"],
        join_attributes="ALL",
        output_type="LINE",
    )

    attr_sql = "(" + ",".join([f"'{cat}'" for cat in locked_categories]) + ")"

    line_lyr = "line_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["intersected_lines"],
        out_layer=line_lyr,
        where_clause=f"arealdekke NOT IN {attr_sql}",
    )

    search_field = f"FID_{os.path.basename(files['split_result'])}"

    best_lines = {}

    with arcpy.da.SearchCursor(
        line_lyr, ["arealdekke", search_field, "Shape_Length"]
    ) as search:
        for area, poly_id, length in search:
            if poly_id not in best_lines:
                best_lines[poly_id] = [length, area]
            elif best_lines[poly_id][0] < length:
                best_lines[poly_id] = [length, area]

    with arcpy.da.UpdateCursor(files["split_result"], ["OID@", "arealdekke"]) as update:
        for oid, area in update:
            try:
                update.updateRow([oid, best_lines[oid][-1]])
            except:
                continue

    arcpy.management.Merge(
        inputs=[files["erased_small_areas"], files["split_result"]],
        output=output_fc,
    )


# ========================


def create_featureclass_point(path: str, spatial_ref) -> None:
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(path),
        out_name=os.path.basename(path),
        geometry_type="POINT",
        spatial_reference=spatial_ref,
    )


def insert_line_endpoints(
    line_fc: str, point_fc: str, include_oid: bool = False
) -> None:
    "Fetches the endpoints of the lines and stores them in an own featureclass"
    fields_in = ["OID@", "SHAPE@"] if include_oid else ["SHAPE@"]
    fields_out = ["SHAPE@", "Line_ID"] if include_oid else ["SHAPE@"]

    with arcpy.da.SearchCursor(line_fc, fields_in) as search, arcpy.da.InsertCursor(
        point_fc, fields_out
    ) as insert:
        for row in search:
            geom = row[-1]
            oid = row[0] if include_oid else None
            for part in geom:
                if len(part) < 2:
                    continue
                start, end = part[0], part[-1]
                in_row = [start, oid] if include_oid else [start]
                out_row = [end, oid] if include_oid else [end]
                insert.insertRow(in_row)
                insert.insertRow(out_row)


def delete_points_by_location(
    point_fc: str, select_fc: str, invert: bool = False
) -> None:
    "Deletes a selection of the point data"
    lyr = "tmp_point_lyr"
    arcpy.management.MakeFeatureLayer(point_fc, lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=lyr,
        overlap_type="INTERSECT",
        select_features=select_fc,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT" if invert else "NOT_INVERT",
    )

    arcpy.management.DeleteFeatures(lyr)


def delete_non_duplicate_points(fc: str, identical_fc: str) -> None:
    "Finds identical points in the datasets and erase all that do not have any duplicate"
    arcpy.management.FindIdentical(
        in_dataset=fc, out_dataset=identical_fc, fields=["SHAPE"], xy_tolerance=1
    )

    featseq = Counter(
        row[0] for row in arcpy.da.SearchCursor(identical_fc, ["FEAT_SEQ"])
    )
    del_featseq = {seq for seq, num in featseq.items() if num < 2}
    del_ids = [
        str(oid)
        for oid, seq in arcpy.da.SearchCursor(identical_fc, ["IN_FID", "FEAT_SEQ"])
        if seq in del_featseq
    ]

    if del_ids:
        sql = f"OBJECTID IN ({','.join(del_ids)})"
        lyr = "temp_fc_lyr"
        arcpy.management.MakeFeatureLayer(fc, lyr)
        arcpy.management.SelectLayerByAttribute(lyr, "NEW_SELECTION", sql)
        arcpy.management.DeleteFeatures(lyr)

    arcpy.management.DeleteIdentical(fc, ["SHAPE"], xy_tolerance=1)


def buffer_and_delete(
    point_fc_1: str, point_fc_2: str, buffer_fc: str, distance: int
) -> None:
    "Buffers the points and deletes the points in the second dataset that intersect with the buffers"
    arcpy.analysis.Buffer(point_fc_1, buffer_fc, distance)
    delete_points_by_location(point_fc_2, buffer_fc)


def make_orthogonal_cutline(
    point: arcpy.PointGeometry, centerline_geom: arcpy.Polyline, length: int = 50
) -> arcpy.Polyline:
    "Creates an orthogonal cutline from a point on the tangent of a centerline"
    point: arcpy.Point = point.firstPoint
    # Nearest point on centerline
    nearest = centerline_geom.snapToLine(point)
    pos = centerline_geom.measureOnLine(nearest)

    # Get tangent
    offset = 0.1
    line_length = centerline_geom.length

    pos1 = max(0, pos - offset)
    pos2 = min(line_length, pos + offset)

    p_before = centerline_geom.positionAlongLine(pos1).firstPoint
    p_after = centerline_geom.positionAlongLine(pos2).firstPoint

    dx = p_after.X - p_before.X
    dy = p_after.Y - p_before.Y

    # Compute orthogonal vector
    nx, ny = -dy, dx

    # Normalize
    mag = np.sqrt(nx**2 + ny**2)

    if mag < 1e-9:
        p1 = arcpy.Point(point.X, point.Y + length)
        p2 = arcpy.Point(point.X, point.Y - length)
        return arcpy.Polyline(arcpy.Array([p1, p2]))

    nx /= mag
    ny /= mag

    # Build line
    p1 = arcpy.Point(point.X + nx * length, point.Y + ny * length)
    p2 = arcpy.Point(point.X - nx * length, point.Y - ny * length)

    return arcpy.Polyline(arcpy.Array([p1, p2]))
