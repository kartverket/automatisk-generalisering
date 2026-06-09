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
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    buff_small_polygon_segments_parameters,
    EliminateSmallPolygonsParameters,
)
from generalization.n10.arealdekke.overall_tools.overlap_remover import remove_overlaps

# ========================
# Program
# ========================


@timing_decorator
def aggregate_areas(input_fc: str, output_fc: str, map_scale: str) -> None:
    """
    Function that aggregates small polygons located near each other and dissolves it into one larger feature.

    Process:
    1) Fetches the features of the relevant feature type and select the small ones
    2) Identify close, topologically relations between features
    If any:
    3) Aggregate the near features together into larger, like taking a rubber band around them

    Args:
        input_fc (str): Feature class to be edited
        output_fc (str): Output feature class for aggregated features
        map_scale (str): The current map scale to generalize to
    """
    fc = Arealdekke_N10.area_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    print(
        f"\n{'====='*15}\nAggregating small polygons at map scale '{map_scale}'\n{'====='*15}\n"
    )

    features = {"Innsjo": 1/2}

    files = create_wfm_gdbs(wfm=wfm)

    arcpy.management.CopyFeatures(
        in_features=input_fc, out_feature_class=files["copy_of_input"]
    )

    for feature in features.keys():
        area, width = fetch_parameters(feature=feature, map_scale=map_scale)

        tol = width * features[feature]

        data_selection(files=files, feature=feature, area_tol=area, tol=tol)
        aggregate_small_features(files=files, tol=tol)
        combine_datasets(files=files)
        remove_overlaps(
            input_fc=files["copy_of_input"],
            buffered_fc=files["aggregated_features"],
            locked_fc="",
            output_fc=files["processed_features"],
            changed_area=feature,
        )

        arcpy.management.CopyFeatures(
            in_features=files["processed_features"],
            out_feature_class=files["copy_of_input"],
        )

    arcpy.management.CopyFeatures(
        in_features=files["copy_of_input"], out_feature_class=output_fc
    )

    wfm.delete_created_files()


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
    print("🗂️  Temporarily files created")
    return {
        "copy_of_input": wfm.build_file_path(
            file_name="copy_of_input", file_type="gdb"
        ),
        "features": wfm.build_file_path(file_name="features", file_type="gdb"),
        "small_features": wfm.build_file_path(
            file_name="small_features", file_type="gdb"
        ),
        "large_features": wfm.build_file_path(
            file_name="large_features", file_type="gdb"
        ),
        "close_features": wfm.build_file_path(
            file_name="close_features", file_type="gdb"
        ),
        "aggregated_features": wfm.build_file_path(
            file_name="aggregated_features", file_type="gdb"
        ),
        "processed_features": wfm.build_file_path(
            file_name="processed_features", file_type="gdb"
        ),
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

    print(f"⚙️  Parameters fetched for feature '{feature}' at map scale '{map_scale}'")

    return params


def data_selection(files: dict, feature: str, area_tol: int, tol: int) -> None:
    """
    Selects the relevant data needed for aggregation and stores it in separate feature classes.

    Args:
        files (dict): Dictionary with all the working files
        feature (str): Name of the feature type to fetch
        area_tol (int): Area tolerance for small enough area of the features
        tol (int): Size tolerance for close proximity of the features
    """
    feature_lyr = "feature_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"], out_layer=feature_lyr
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
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{feature}' AND Shape_Area <= {area_tol}",
    )
    arcpy.management.CopyFeatures(
        in_features=feature_lyr, out_feature_class=files["small_features"]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=feature_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"arealdekke = '{feature}' AND Shape_Area > {area_tol}",
    )
    arcpy.management.CopyFeatures(
        in_features=feature_lyr, out_feature_class=files["large_features"]
    )

    arcpy.management.MakeFeatureLayer(
        in_features=files["features"], out_layer=feature_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=feature_lyr,
        overlap_type="WITHIN_A_DISTANCE",
        select_features=files["small_features"],
        search_distance=tol,
    )
    arcpy.management.CopyFeatures(
        in_features=feature_lyr, out_feature_class=files["close_features"]
    )

    print(
        f"📡 Relevant data fetched for feature '{feature}' with specific tolerances:\n"
        f"   • 🟦 Area = {area_tol} m²\n"
        f"   • 📏 Proximity = {tol} m"
    )


def aggregate_small_features(files: dict, tol: int) -> None:
    """
    Aggregates the small features together into larger features.

    Args:
        files (dict): Dictionary with all the working files
        tol (int): Size tolerance for how close the features should be to be aggregated together
    """
    arcpy.cartography.AggregatePolygons(
        in_features=files["close_features"],
        out_feature_class=files["aggregated_features"],
        aggregation_distance=tol,
    )

    print(f"🧩  Small polygons aggregated together with proximity tolerance of {tol} m")


def combine_datasets(files: dict) -> None:
    """
    Combines dataset to get complete set of features.

    Args:
        files (dict): Dictionary with all the working files
    """
    feature_lyr = "feature_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["large_features"], out_layer=feature_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=feature_lyr,
        overlap_type="INTERSECT",
        select_features=files["aggregated_features"],
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.Append(
        inputs=feature_lyr, target=files["aggregated_features"], schema_type="NO_TEST"
    )

    print(
        "🔗  Large and aggregated features successfully combined into a complete dataset\n"
    )
