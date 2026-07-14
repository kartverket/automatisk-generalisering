# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from pathlib import Path
from collections import defaultdict

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.param_utils import initialize_params
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    EliminateSmallPolygonsParameters,
)

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
    min_area = fetch_min_area(map_scale=map_scale, target=target)
    sql = ", ".join([f"'{lu}'" for lu in allowed])

    data_selection(
        input_fc=input_fc,
        files=files,
        target=target,
        min_area=min_area,
        sql=sql,
    )
    if boundary:
        boundary_adjustments(files=files, target=target, boundary=boundary, sql=sql)
    rewrite_attribute_info(files=files, target=target, boundary=boundary is not None)

    arcpy.management.CopyFeatures(
        in_features=files["copy_of_input"],
        out_feature_class=output_fc,
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
        "copy_of_input": wfm.build_file_path(
            file_name="copy_of_input", file_type="gdb"
        ),
        "target": wfm.build_file_path(file_name="target", file_type="gdb"),
        "near": wfm.build_file_path(file_name="near", file_type="gdb"),
        "dissolved_allowed": wfm.build_file_path(
            file_name="dissolved_allowed", file_type="gdb"
        ),
        "not_dissolved_allowed": wfm.build_file_path(
            file_name="not_dissolved_allowed", file_type="gdb"
        ),
        "spatial_join_output": wfm.build_file_path(
            file_name="spatial_join_output", file_type="gdb"
        ),
        "near_expanded": wfm.build_file_path(
            file_name="near_expanded", file_type="gdb"
        ),
    }


def fetch_min_area(map_scale: str, target: str) -> int:
    """
    Fetches the minimum area for the target feature in the given map scale.
    """
    params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"
    params = initialize_params(
        params_path=params_path,
        class_name="EliminateSmallPolygons",
        map_scale=map_scale.upper(),
        dataclass=EliminateSmallPolygonsParameters,
    )
    return params.min_area[target]


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
    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{target}' AND Shape_Area < {min_area}",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["target"]
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="BOUNDARY_TOUCHES",
        select_features=files["target"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="SUBSET_SELECTION",
        where_clause=f"arealdekke IN ({sql})",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["near"]
    )


def boundary_adjustments(files: dict, target: str, boundary: str, sql: str) -> None:
    """
    Collects data that is connected to target and near features and investigates whether
    they are completely surrounded by the boundary feature. If so, they are also changed
    to the target land use.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        boundary (str): Boundary feature class for aggregation
        sql (str): SQL query string for selecting allowed land use types
    """
    lyr_1 = "lyr_1"
    lyr_2 = "lyr_2"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=lyr_1
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_1,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke IN ({sql})",
    )

    arcpy.management.Dissolve(
        in_features=lyr_1,
        out_feature_class=files["dissolved_allowed"],
        dissolve_field="arealdekke",
        multi_part="SINGLE_PART",
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files["dissolved_allowed"], out_layer=lyr_2
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=lyr_2,
        overlap_type="INTERSECT",
        select_features=files["near"],
        selection_type="NEW_SELECTION",
    )

    arcpy.analysis.Erase(
        in_features=files["copy_of_input"],
        erase_features=lyr_2,
        out_feature_class=files["not_dissolved_allowed"],
    )

    arcpy.analysis.SpatialJoin(
        target_features=lyr_2,
        join_features=files["not_dissolved_allowed"],
        out_feature_class=files["spatial_join_output"],
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_ALL",
    )

    id_to_area = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["spatial_join_output"], ["TARGET_FID", "arealdekke_1"]
    ) as cursor:
        for id, area in cursor:
            id_to_area[id].add(area)

    ids_to_keep = [
        id for id, areas in id_to_area.items() if areas.issubset({target, boundary})
    ]
    ids = ", ".join([f"{id}" for id in ids_to_keep])
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lyr_2,
        selection_type="NEW_SELECTION",
        where_clause=f"OBJECTID IN ({ids})",
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
    arcpy.management.Merge(inputs=[lyr_1, files["near"]], output=files["near_expanded"])


def rewrite_attribute_info(files: dict, target: str, boundary: bool) -> None:
    """
    Changes attribute information of adjacent geometries to fit with new status.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
        boundary (bool): Whether boundary features are used or not
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=files["near_expanded"] if boundary else files["near"],
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])
