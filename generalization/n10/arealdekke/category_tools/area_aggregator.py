# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from collections import defaultdict
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
    near_expanded = "near_expanded"


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

    # wfm.delete_created_files()


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
        arcpy.analysis.Erase(
            in_features=in_f, erase_features=land_use_lyr, out_feature_class=out_f
        )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])

    arcpy.management.Append(
        inputs=[land_use_lyr], target=files[Names.temp_output_2], schema_type="NO_TEST"
    )

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


"""
def rewrite_attribute_info(
    input_fc: str, files: dict, target: str, boundary: bool
) -> None:
    
    Changes attribute information of adjacent geometries to fit with new status.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        boundary (bool): Whether boundary features are used or not
    
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=files[Names.near_expanded] if boundary else files[Names.near],
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])
"""


if __name__ == "__main__":
    # Example usage
    aggregate_category(
        input_fc=Arealdekke_N10.attribute_changer_output__n10_land_use.value,
        output_fc=Arealdekke_N10.category_aggregator_output__n10_land_use.value,
        map_scale="N10",
        target="Høyblokkbebyggelse",
        allowed=["Bebygd"],
        boundary="Samferdsel",
    )
