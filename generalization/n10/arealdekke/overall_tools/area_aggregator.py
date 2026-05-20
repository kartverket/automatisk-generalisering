# ========================
# Libraries
# ========================


import arcpy

arcpy.env.overwriteOutput = True

from pathlib import Path

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.param_utils import initialize_params
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.overall_tools.attribute_changer import (
    attribute_changer,
)
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    buff_small_polygon_segments_parameters,
    EliminateSmallPolygonsParameters,
)
from input_data.input_test_data import arealdekke_3

# ========================
# Helper functions
# ========================


def create_wfm_gdbs(wfm: WorkFileManager):
    """
    Creates all the temporarily files that are going to be used
    during the process of aggregating small polygons.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "pre_processed": wfm.build_file_path(
            file_name="pre_processed", file_type="gdb"
        ),
        "features": wfm.build_file_path(file_name="features", file_type="gdb"),
        "small_features": wfm.build_file_path(
            file_name="small_features", file_type="gdb"
        ),
        "small_features_buffered": wfm.build_file_path(file_name="small_features_buffered", file_type="gdb"),
        "small_features_dissolved": wfm.build_file_path(file_name="small_features_dissolved", file_type="gdb")
    }


def fetch_parameters(feature: str, map_scale: str) -> list:
    """
    Retrieves relevant minimum criterias for the relevant feature type.

    Args:
        feature (str): Name of the feature type to investigate
        map_scale (str): Current map scale

    Returns:
        list: A list of the relevant parameteres for this specific feature
    """
    params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"

    categories = [
        ["EliminateSmallPolygons", EliminateSmallPolygonsParameters, "min_area"],
        [
            "BuffSmallPolygonSegments",
            buff_small_polygon_segments_parameters,
            "min_width",
        ],
    ]

    params = []

    for name, param_class, call in categories:
        scale_parameters = initialize_params(
            params_path=params_path,
            class_name=name,
            map_scale=map_scale,
            dataclass=param_class,
        )

        params.append(getattr(scale_parameters, call)[feature])

    return params


def data_selection(files: dict, feature: str, tol: int) -> None:
    """
    Selects the relevant data needed for this process and stores it in separate feature classes.

    Args:
        files (dict): Dictionary with all the working files
        feature (str): Name of the feature type to fetch
        tol (int): Size tolerance for small enough area of the features
    """
    feature_lyr = "feature_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["pre_processed"], out_layer=feature_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=feature_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{feature}'",
    )

    arcpy.management.CopyFeatures(
        in_features=feature_lyr, out_feature_class=files["features"]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=feature_lyr,
        selection_type="SUBSET_SELECTION",
        where_clause=f"Shape_Area < {tol}",
    )

    arcpy.management.CopyFeatures(
        in_features=feature_lyr, out_feature_class=files["small_features"]
    )


def connect_small_features(files: dict, tol: int) -> None:
    """
    ...
    """
    arcpy.analysis.Buffer(in_features=files["small_features"], out_feature_class=files["small_features_buffered"], buffer_distance_or_field=tol)

    arcpy.management.Dissolve(in_features=files["small_features_buffered"], out_feature_class=files["small_features_dissolved"], dissolve_field=[], multi_part="SINGLE_PART")


# ========================
# Program
# ========================


@timing_decorator
def aggregate_areas(input_data: str, feature: str, map_scale: str) -> None:
    """
    Function that aggregates small polygons located near each other and dissolves it into one larger feature.

    Process:
    1) Fetches the features of the relevant feature type and select the small ones
    2) Identify close, topologically relations between features
    If any:
    3) Aggregate the near features together into larger, like taking a rubber band around them

    Args:
        input_data (str): Feature class to be edited
        feature (str): The feature / land use type to be edited
        map_scale (str): The current map scale to generalize to
    """
    fc = Arealdekke_N10.area_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    attribute_changer(input_fc=input_data, output_fc=files["pre_processed"])

    area, width = fetch_parameters(feature=feature, map_scale=map_scale)

    data_selection(files=files, feature=feature, tol=area)
    connect_small_features(files=files, tol=width)


# ========================

if __name__ == "__main__":
    feature = "Innsjo"
    map_scale = "N10"

    aggregate_areas(input_data=arealdekke_3, feature=feature, map_scale=map_scale)
