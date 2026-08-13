# Libraries

from importlib.metadata import files

import arcpy
import os

arcpy.env.overwriteOutput = True

from collections import defaultdict, Counter
from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.parameters.parameter_worker import get_min_area

# ========================
# Class
# ========================


class Names(StrEnum):
    target = "target"
    near_1 = "near_1"
    near_2 = "near_2"
    working_features = "working_features"
    temp_output_1 = "temp_output_1"
    temp_output_2 = "temp_output_2"
    dissolved_allowed = "dissolved_allowed"
    spatial_join_target = "spatial_join_target"
    spatial_join_other = "spatial_join_other"
    dissolved_boundary = "dissolved_boundary"
    boundary_lines = "boundary_lines"
    too_small = "too_small"
    should_split = "should_split"
    near_lines = "near_lines"
    all_points = "all_points"
    near_points = "near_points"
    cutlines = "cutlines"
    splitted_features = "splitted_features"
    splitted_features_cleaned = "splitted_features_cleaned"
    splitted_features_multipart = "splitted_features_multipart"
    candidates = "candidates"
    enlarge_1 = "enlarge_1"
    enlarge_2 = "enlarge_2"
    final_enlarged_target = "final_enlarged_target"
    allowed_areas = "allowed_areas"
    attr_join_1 = "attr_join_1"
    attr_join_2 = "attr_join_2"


# ========================
# Main function
# ========================


@timing_decorator
def aggregate_category(
    target: str,
    input_fc: str,
    output_fc: str,
    map_scale: str,
    allowed: list,
    boundary: str = None,
) -> None:
    """
    Changes surrounding features around the target features to the same land use value as target.

    Args:
        target (str): Name of the land use type to consider in this process
        input_fc (str): Feature class containing the input data
        output_fc (str): Feature class where the result is stored
        map_scale (str): Current map scale
        allowed (list): List of allowed land use types to be considered for aggregation
        boundary (str, optional): Boundary feature class for aggregation - defaults to None
    """
    print(f"{'===' * 20}\nStarting Area Aggregation for {target}\n{'===' * 20}\n")

    working_fc = Arealdekke_N10.category_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    min_area = get_min_area(map_scale=map_scale, target=target)
    sql = ", ".join([f"'{lu}'" for lu in allowed])

    data_selection(
        input_fc=input_fc,
        files=files,
        target=target,
        min_area=min_area,
        sql=sql,
    )

    if int(arcpy.management.GetCount(files[Names.target])[0]) < 1:
        return

    oid_to_dissolved = group_inside_boundary(
        input_fc=input_fc,
        files=files,
        target=target,
        boundary=boundary,
        sql=sql,
        max_area=min_area * 2,
    )
    oid_to_dissolved = find_large_allowed_features(
        files=files, max_area=min_area * 2, oid_match=oid_to_dissolved
    )
    rewrite_attribute_info_small(files=files, target=target, oid_match=oid_to_dissolved)
    create_split_points(files=files, split_area=boundary, min_area=min_area)
    create_cutlines(files=files)
    enlarge_small_features(
        files=files, target=target, allowed=allowed, min_area=min_area
    )
    clean_areas(files=files, boundary=allowed + [target])
    fetch_orig_attributes(input_fc=input_fc, output_fc=output_fc, files=files, sql=sql)

    print(f"\n{'===' * 20}\n")

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporary files that are going to
    be used during the process of area aggregation.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }


def data_selection(
    input_fc: str, files: dict, target: str, min_area: int, sql: str
) -> None:
    """
    Selects and copies relevant data into separate feature classes.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Target land use to consider
        min_area (int): Minimum area of the target area to be considered
        sql (str): SQL query string for selecting allowed land use types
    """
    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(in_features=input_fc, out_layer=land_use_lyr)

    # Fetches target features under size limit
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}' AND Shape_Area < {min_area}",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.target]
    )

    # Fetches relevant nearby features that is allowed to change
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke IN ({sql})",
    )
    arcpy.management.Dissolve(
        in_features=land_use_lyr,
        out_feature_class=files[Names.dissolved_allowed],
        dissolve_field="arealdekke",
        multi_part="SINGLE_PART",
    )
    arcpy.management.Delete(land_use_lyr)
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.dissolved_allowed], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="BOUNDARY_TOUCHES",
        select_features=files[Names.target],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.near_1]
    )
    arcpy.management.Delete(land_use_lyr)

    # Combines filtered data and store the remaining in output
    arcpy.management.Merge(
        inputs=[files[Names.target], files[Names.near_1]],
        output=files[Names.working_features],
    )
    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=files[Names.working_features],
        out_feature_class=files[Names.temp_output_1],
    )
    print("✅ Data Selection\t\t| Completed")


def group_inside_boundary(
    input_fc: str, files: dict, target: str, boundary: str, sql: str, max_area: int
) -> dict:
    """
    Collects data that is connected to target and near features and investigates whether
    they are completely surrounded by the boundary feature. If so, they are also changed
    to the target land use.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        boundary (str): Boundary feature class for aggregation
        sql (str): SQL query string for selecting allowed land use types
        max_area (int): Maximum area to be considered relevant

    Returns:
        dict: A dictionary mapping target feature IDs to sets of connected feature IDs
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)

    # Finds intersecting features
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke NOT IN ({sql})",
    )

    # Performes spatial join to identify surrounded targets
    arcpy.analysis.SpatialJoin(
        target_features=files[Names.target],
        join_features=files[Names.near_1],
        out_feature_class=files[Names.spatial_join_target],
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    arcpy.analysis.SpatialJoin(
        target_features=files[Names.near_1],
        join_features=land_use_lyr,
        out_feature_class=files[Names.spatial_join_other],
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    oid_match_target = defaultdict(set)
    with arcpy.da.SearchCursor(
        files[Names.spatial_join_target], ["TARGET_FID", "JOIN_FID"]
    ) as cursor:
        for target_oid, join_oid in cursor:
            if join_oid != -1:
                oid_match_target[target_oid].add(join_oid)

    oid_match_other = defaultdict(set)
    with arcpy.da.SearchCursor(
        files[Names.spatial_join_other], ["TARGET_FID", "arealdekke_1", "Shape_Area"]
    ) as cursor:
        for oid, arealdekke, area in cursor:
            if area > max_area:
                continue
            oid_match_other[oid].add(arealdekke)

    allowed = (
        set(sql.split(",")) | {target, boundary}
        if boundary
        else set(sql.split(",")) | {target}
    )

    oid_match_other = {
        oid: areas for oid, areas in oid_match_other.items() if areas.issubset(allowed)
    }

    relevant_oids = set(oid_match_other) & set(
        oid for oids in oid_match_target.values() for oid in oids
    )

    arcpy.management.Delete(land_use_lyr)
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.dissolved_allowed],
        out_layer=land_use_lyr,
        where_clause=(
            f"OBJECTID IN ({','.join(map(str, relevant_oids))})"
            if relevant_oids
            else "1=0"
        ),
    )

    for in_f, out_f in [
        [files[Names.temp_output_1], files[Names.temp_output_2]],
        [files[Names.near_1], files[Names.near_2]],
    ]:
        arcpy.analysis.PairwiseErase(
            in_features=in_f, erase_features=land_use_lyr, out_feature_class=out_f
        )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])

    arcpy.management.Append(
        inputs=[land_use_lyr], target=files[Names.temp_output_2], schema_type="NO_TEST"
    )
    arcpy.management.Delete(land_use_lyr)

    print("📍 Boundary Grouping\t\t| Completed")

    return oid_match_target


def find_large_allowed_features(files: dict, max_area: int, oid_match: dict) -> dict:
    """
    Identifies and processes allowed features that exceed the specified maximum area.

    Args:
        files (dict): Dictionary with all the working files
        max_area (int): Maximum area to be considered relevant
        oid_match (dict): Dictionary mapping target feature IDs to sets of connected feature IDs

    Returns:
        dict: Updated oid_match dictionary
    """
    where_clause = f"Shape_Area > {max_area}"
    large_polygons = {
        row[0]
        for row in arcpy.da.SearchCursor(
            files[Names.near_1], ["OID@"], where_clause=where_clause
        )
    }

    is_large = large_polygons.__contains__

    print(
        f"🔎 Large Features\t\t| Found {len(large_polygons)} feature(s) > {max_area} area"
    )

    return {
        oid: [[o, "l"] if is_large(o) else [o, "s"] for o in oids]
        for oid, oids in oid_match.items()
    }


def rewrite_attribute_info_small(files: dict, target: str, oid_match: dict) -> None:
    """
    Selects and updates the attribute information of small features that are
    connected to target features having connections to small features only.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        oid_match (dict): Dictionary mapping target feature IDs to sets of connected feature IDs
    """
    keep = set()
    for oids in oid_match.values():
        if any(size == "l" for _, size in oids):
            keep.update(oid for oid, _ in oids)

    sql = f"OBJECTID NOT IN ({','.join(map(str, keep))})" if keep else "1=0"

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.near_2], out_layer=land_use_lyr, where_clause=sql
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])

    arcpy.management.Merge(
        inputs=[land_use_lyr, files[Names.temp_output_2]],
        output=files[Names.temp_output_1],
    )

    arcpy.analysis.Erase(
        in_features=files[Names.near_2],
        erase_features=land_use_lyr,
        out_feature_class=files[Names.near_1],
    )
    arcpy.management.Delete(land_use_lyr)

    print("📝 Attribute Update\t\t| Small feature attributes rewritten")


def create_split_points(files: dict, split_area: str, min_area: int) -> None:
    """
    Find nearby boundary features and create points at the endpoints of these lines.
    The points that are shared with only one line as well as intersecting the
    area of interest are kept.

    Args:
        files (dict): Dictionary with all the working files
        split_area (str): Name of the boundary feature class to consider for splitting
        min_area (int): Minimum area threshold for the features to be considered
    """
    # Fetching border features
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.temp_output_1], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{split_area}'",
    )

    arcpy.management.Dissolve(
        in_features=land_use_lyr,
        out_feature_class=files[Names.dissolved_boundary],
        dissolve_field="arealdekke",
        multi_part="SINGLE_PART",
    )
    arcpy.management.Delete(land_use_lyr)

    # Dividing features of interest into small and large
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.near_1], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"Shape_Area < {min_area}",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.too_small]
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr, selection_type="SWITCH_SELECTION"
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.should_split]
    )
    arcpy.management.Delete(land_use_lyr)

    # Creating lines of the split features
    arcpy.cartography.CollapseHydroPolygon(
        in_features=files[Names.dissolved_boundary],
        out_line_feature_class=files[Names.boundary_lines],
    )

    line_lyr = "line_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.boundary_lines], out_layer=line_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=line_lyr,
        overlap_type="BOUNDARY_TOUCHES",
        select_features=files[Names.should_split],
        selection_type="NEW_SELECTION",
    )

    arcpy.management.CopyFeatures(
        in_features=line_lyr, out_feature_class=files[Names.near_lines]
    )
    arcpy.management.Delete(line_lyr)

    # Fetching the closest dead end points
    endpoint_count = Counter()

    with arcpy.da.SearchCursor(files[Names.near_lines], ["SHAPE@"]) as cursor:
        for (shape,) in cursor:
            endpoint_count[(shape.firstPoint.X, shape.firstPoint.Y)] += 1
            endpoint_count[(shape.lastPoint.X, shape.lastPoint.Y)] += 1

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files[Names.all_points]),
        out_name=os.path.basename(files[Names.all_points]),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(files[Names.near_lines]).spatialReference,
    )

    with arcpy.da.InsertCursor(files[Names.all_points], ["SHAPE@XY"]) as icur:
        for xy, count in endpoint_count.items():
            if count == 1:
                icur.insertRow([xy])

    point_lyr = "point_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.all_points], out_layer=point_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=point_lyr,
        overlap_type="INTERSECT",
        select_features=files[Names.near_1],
        selection_type="NEW_SELECTION",
    )

    arcpy.management.CopyFeatures(
        in_features=point_lyr, out_feature_class=files[Names.near_points]
    )
    arcpy.management.Delete(point_lyr)

    print(
        f"✂️ Split Points\t\t\t| Created {arcpy.management.GetCount(files[Names.near_points])[0]} point(s) for features > {min_area} m²"
    )


def create_cutlines(files: dict, cutline_length: int = 100) -> None:
    """
    Creates cutlines at the endpoints of the nearby lines to split the features of interest.

    Args:
        files (dict): Dictionary with all the working files
        cutline_length (int): Length of the cutlines to be created (default is 100)
    """
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files[Names.cutlines]),
        out_name=os.path.basename(files[Names.cutlines]),
        geometry_type="POLYLINE",
        spatial_reference=arcpy.Describe(files[Names.near_points]).spatialReference,
    )

    with arcpy.da.InsertCursor(files[Names.cutlines], ["SHAPE@"]) as icur:
        with arcpy.da.SearchCursor(files[Names.near_points], ["SHAPE@XY"]) as scur:
            for ((x, y),) in scur:
                # North - South line
                icur.insertRow(
                    [
                        arcpy.Polyline(
                            arcpy.Array(
                                [
                                    arcpy.Point(x - cutline_length, y),
                                    arcpy.Point(x + cutline_length, y),
                                ]
                            )
                        )
                    ]
                )
                # East - West line
                icur.insertRow(
                    [
                        arcpy.Polyline(
                            arcpy.Array(
                                [
                                    arcpy.Point(x, y - cutline_length),
                                    arcpy.Point(x, y + cutline_length),
                                ]
                            )
                        )
                    ]
                )

    print(
        f"📏 Cutlines\t\t\t| Created {arcpy.management.GetCount(files[Names.cutlines])[0]} cutlines"
    )


def enlarge_small_features(
    files: dict, target: str, allowed: list, min_area: int
) -> None:
    """
    Dissolves the built up areas iteratively until all target features meet the
    minimum area requirement or no more nearby features can be enlarged.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        allowed (list): List of allowed land use types for enlargement
        min_area (int): Minimum area requirement for the features
    """
    arcpy.management.FeatureToPolygon(
        in_features=[files[Names.should_split], files[Names.cutlines]],
        out_feature_class=files[Names.splitted_features],
        attributes="ATTRIBUTES",
    )

    land_use_lyr = "land_use_lyr"
    sql = ", ".join(f"'{lu}'" for lu in allowed + [target])
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.temp_output_1],
        out_layer=land_use_lyr,
        where_clause=f"arealdekke NOT IN ({sql})",
    )

    arcpy.analysis.Erase(
        in_features=files[Names.splitted_features],
        erase_features=land_use_lyr,
        out_feature_class=files[Names.splitted_features_cleaned],
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files[Names.splitted_features_cleaned],
        out_feature_class=files[Names.splitted_features_multipart],
    )
    arcpy.management.Delete(land_use_lyr)

    arcpy.management.Merge(
        inputs=[files[Names.splitted_features_multipart], files[Names.too_small]],
        output=files[Names.candidates],
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.candidates], out_layer=land_use_lyr
    )

    main_target = files[Names.target]
    target_lyr = "target_lyr"
    arcpy.management.MakeFeatureLayer(in_features=main_target, out_layer=target_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=target_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"Shape_Area < {min_area}",
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="INTERSECT",
        select_features=target_lyr,
        selection_type="NEW_SELECTION",
    )

    previous = sum(
        1
        for row in arcpy.da.SearchCursor(target_lyr, ["Shape_Area"])
        if row[0] < min_area
    )

    iterations = 0

    while True:
        iterations += 1
        arcpy.management.Merge(
            inputs=[land_use_lyr, main_target], output=files[Names.enlarge_1]
        )
        arcpy.management.CalculateField(
            in_table=files[Names.enlarge_1],
            field="arealdekke",
            expression=f"'{target}'",
            expression_type="PYTHON3",
        )
        arcpy.management.Dissolve(
            in_features=files[Names.enlarge_1],
            out_feature_class=files[Names.enlarge_2],
            dissolve_field="arealdekke",
            multi_part="SINGLE_PART",
        )

        main_target = files[Names.enlarge_2]

        arcpy.management.MakeFeatureLayer(in_features=main_target, out_layer=target_lyr)
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=target_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"Shape_Area < {min_area}",
        )

        current = sum(
            1
            for row in arcpy.da.SearchCursor(target_lyr, ["Shape_Area"])
            if row[0] < min_area
        )

        if current == 0:
            print(
                "✅ Enlargement\t\t\t| All polygons meet the minimum area requirement"
            )
            break
        elif current >= previous:
            print("⛔ Enlargement\t\t\t| No additional polygons can be enlarged")
            break

        arcpy.management.SelectLayerByLocation(
            in_layer=land_use_lyr,
            overlap_type="INTERSECT",
            select_features=target_lyr,
            selection_type="NEW_SELECTION",
        )

        if arcpy.management.GetCount(land_use_lyr)[0] == 0:
            print(
                "🚫 Enlargement\t\t\t| No nearby features available for further enlargement"
            )
            break

        previous = current

    arcpy.management.Delete(land_use_lyr)

    print(
        f"📈 Area Enlargement\t\t| {iterations} iterations completed (minimum {min_area} m² achieved)"
    )


def clean_areas(files: dict, boundary: list) -> None:
    """
    Removes overlapping areas so that the different feature classes creates one complete dataset.

    Args:
        files (dict): Dictionary with all the working files
        boundary (list): List of boundary feature classes for aggregation
    """
    boundary_lyr = "boundary_lyr"
    sql = ", ".join(f"'{b}'" for b in boundary)
    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.temp_output_1],
        out_layer=boundary_lyr,
        where_clause=f"arealdekke NOT IN ({sql})",
    )
    arcpy.analysis.Erase(
        in_features=files[Names.enlarge_2],
        erase_features=boundary_lyr,
        out_feature_class=files[Names.final_enlarged_target],
    )

    arcpy.analysis.Erase(
        in_features=files[Names.should_split],
        erase_features=files[Names.final_enlarged_target],
        out_feature_class=files[Names.allowed_areas],
    )
    arcpy.management.Delete(boundary_lyr)

    print("🧹 Cleanup\t\t\t| Boundary and split features removed")


def fetch_orig_attributes(input_fc: str, output_fc: str, files: dict, sql: str) -> None:
    """
    Fetches original attributes for the edited features and merges the features together into the final output.

    Args:
        input_fc (str): Feature class with input data
        output_fc (str): Feature class where the result is stored
        files (dict): Dictionary with all the working files
        sql (str): SQL query string for selecting allowed land use types
    """
    orig_fields = {field.name for field in arcpy.ListFields(files[Names.target])}

    arcpy.analysis.SpatialJoin(
        target_features=files[Names.final_enlarged_target],
        join_features=files[Names.target],
        out_feature_class=files[Names.attr_join_1],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    delete_fields = [
        field.name
        for field in arcpy.ListFields(files[Names.attr_join_1])
        if field.name not in orig_fields and not field.required
    ]

    arcpy.management.DeleteField(
        in_table=files[Names.attr_join_1],
        drop_field=delete_fields,
    )

    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc,
        out_layer=land_use_lyr,
        where_clause=f"arealdekke IN ({sql})",
    )

    arcpy.analysis.SpatialJoin(
        target_features=files[Names.allowed_areas],
        join_features=land_use_lyr,
        out_feature_class=files[Names.attr_join_2],
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )
    arcpy.management.Delete(land_use_lyr)

    delete_fields = [
        field.name
        for field in arcpy.ListFields(files[Names.attr_join_2])
        if field.name not in orig_fields and not field.required
    ]

    arcpy.management.DeleteField(
        in_table=files[Names.attr_join_2],
        drop_field=delete_fields,
    )

    arcpy.management.Merge(
        inputs=[
            files[Names.temp_output_1],
            files[Names.attr_join_1],
            files[Names.attr_join_2],
        ],
        output=output_fc,
    )

    print("🎉 Final Output\t\t\t| Original attributes restored")


if __name__ == "__main__":
    aggregate_category(
        input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
        output_fc=Arealdekke_N10.category_aggregator_output__n10_land_use.value,
        map_scale="N10",
        target="Høyblokkbebyggelse",
        allowed=["Bebygd"],
        boundary="Samferdsel",
    )