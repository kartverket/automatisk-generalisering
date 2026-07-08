# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from pathlib import Path

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
    input_fc: str, output_fc: str, map_scale: str, target: str
) -> None:
    """
    Changes surrounding features around the target features to the same land use value as target.

    Args:
        input_fc (str): Feature class containing the input data
        output_fc (str): Feature class where the result is stored
        map_scale (str): Current map scale
        target (str): Name of the land use type to consider in this process
    """
    working_fc = Arealdekke_N10.category_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    min_area = fetch_min_area(map_scale=map_scale, target=target)

    data_selection(input_fc=input_fc, files=files, min_area=min_area)
    rewrite_attribute_info(files=files, target=target)

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
    }


def fetch_min_area(map_scale: str, target: str) -> int:
    """
    Fetches the minimum area for the target feature in the given map scale.
    """
    params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"
    params = initialize_params(
        params_path=params_path,
        class_name="EliminateSmallPolygons",
        map_scale=map_scale,
        dataclass=EliminateSmallPolygonsParameters,
    )
    return params.min_area[target]


def data_selection(input_fc: str, files: dict, min_area: int) -> None:
    """
    Selects and copies relevant data into separate feature classes.

    Args:
        input_fc (str): Feature class with input data
        files (dict): Dictionary with all the working files
        min_area (int): Minimum area of the target area to be considered
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
        where_clause=f"arealdekke = 'Høyblokkbebyggelse' AND Shape_Area < {min_area}",
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
        where_clause="arealdekke NOT IN ('ElvFlate', 'Innsjo', 'InnsjoRegulert', 'Kanal', 'Hav', 'Høyblokkbebyggelse', 'Samferdsel')",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["near"]
    )


def rewrite_attribute_info(files: dict, target: str) -> None:
    """
    Changes attribute information of adjacent geometries to fit with new status.

    Args:
        files (dict): Dictionary with all the working files
        target (str): Target land use to change to for the relevant features
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=land_use_lyr,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=files["near"],
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(land_use_lyr, ["arealdekke"]) as cur:
        for _ in cur:
            cur.updateRow([target])
