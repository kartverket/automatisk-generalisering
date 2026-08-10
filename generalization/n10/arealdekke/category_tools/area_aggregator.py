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
    near = "near"
    dissolved_allowed = "dissolved_allowed"
    not_dissolved_allowed = "not_dissolved_allowed"
    spatial_join_output = "spatial_join_output"
    near_expanded = "near_expanded"


# ========================
# Main function
# ========================


@timing_decorator
def aggregate_category(
    target: str,
    input_fc: str,
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
    if int(arcpy.management.GetCount(files[Names.target])[0]) > 0:
        if boundary:
            boundary_adjustments(input_fc=input_fc, files=files, target=target, boundary=boundary, sql=sql)
        rewrite_attribute_info(
            input_fc=input_fc, files=files, target=target, boundary=boundary is not None
        )

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
    arcpy.MakeFeatureLayer_management(
        in_features=input_fc, out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}' AND Shape_Area < {min_area}",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.target]
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="BOUNDARY_TOUCHES",
        select_features=files[Names.target],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="SUBSET_SELECTION",
        where_clause=f"arealdekke IN ({sql})",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files[Names.near]
    )


def boundary_adjustments(input_fc: str, files: dict, target: str, boundary: str, sql: str) -> None:
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
    """
    lyr_1 = "lyr_1"
    lyr_2 = "lyr_2"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc, out_layer=lyr_1
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_1,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke IN ({sql})",
    )

    arcpy.management.Dissolve(
        in_features=lyr_1,
        out_feature_class=files[Names.dissolved_allowed],
        dissolve_field="arealdekke",
        multi_part="SINGLE_PART",
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files[Names.dissolved_allowed], out_layer=lyr_2
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_2,
        overlap_type="INTERSECT",
        select_features=files[Names.near],
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Erase(
        in_features=input_fc,
        erase_features=lyr_2,
        out_feature_class=files[Names.not_dissolved_allowed],
    )

    arcpy.analysis.SpatialJoin(
        target_features=lyr_2,
        join_features=files[Names.not_dissolved_allowed],
        out_feature_class=files[Names.spatial_join_output],
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
    )

    id_to_area = defaultdict(set)
    with arcpy.da.SearchCursor(
        files[Names.spatial_join_output], ["TARGET_FID", "arealdekke_1"]
    ) as cursor:
        for id, area in cursor:
            id_to_area[id].add(area)

    ids_to_keep = [
        id for id, areas in id_to_area.items() if areas.issubset({target, boundary})
    ]
    where_clause = (
        f"OBJECTID IN ({','.join(map(str, ids_to_keep))})" if ids_to_keep else "1=0"
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_2,
        selection_type="NEW_SELECTION",
        where_clause=where_clause,
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_1,
        overlap_type="INTERSECT",
        select_features=lyr_2,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_1,
        selection_type="SUBSET_SELECTION",
        where_clause=f"arealdekke NOT IN ('{boundary}')",
    )
    arcpy.management.Merge(inputs=[lyr_1, files[Names.near]], output=files[Names.near_expanded])


def rewrite_attribute_info(input_fc: str, files: dict, target: str, boundary: bool) -> None:
    """
    Changes attribute information of adjacent geometries to fit with new status.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        boundary (bool): Whether boundary features are used or not
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_fc, out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=files[Names.near_expanded] if boundary else files[Names.near],
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])
