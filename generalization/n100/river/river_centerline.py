import arcpy
import multiprocessing
from multiprocessing import Pool, Manager
from tqdm import tqdm

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    environment_setup.main()
    prepare_data()
    create_dangles()


def prepare_data():
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__river_area_selection__n100.value,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        output_name=River_N100.river_centerline__rivers_near_waterfeatures__n100.value,
    )

    arcpy.management.CopyFeatures(
        in_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        out_feature_class=River_N100.short__water_feature__n100.value,
    )
    print(f"Created {River_N100.short__water_feature__n100.value}")

    arcpy.analysis.PairwiseErase(
        in_features=River_N100.river_centerline__rivers_near_waterfeatures__n100.value,
        erase_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        out_feature_class=River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value,
    )
    print(
        f"Created {River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value}"
    )

    # In the future implement a logic which could use the centroid of the lake to create lines for more center logic
    # arcpy.management.FeatureToPoint(
    #     in_features=River_N100.river_centerline__rivers_near_waterfeatures__n100.value,
    #     out_feature_class=River_N100.short__water_feature_centroid__n100.value,
    #     point_location="INSIDE",
    # )
    print(
        "In the future implement a logic which could use the centroid of the lake to create lines for more center logic"
    )

    arcpy.cartography.CollapseHydroPolygon(
        in_features=River_N100.short__water_feature__n100.value,
        out_line_feature_class=River_N100.river_centerline__water_feature_collapsed__n100.value,
        connecting_features=River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value,
    )
    print(f"Created {River_N100.river_centerline__water_feature_collapsed__n100.value}")


def create_dangles():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        expression="OBJECTID = 4703",
        output_name=River_N100.river_centerline__study_lake__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.river_centerline__rivers_near_waterfeatures_erased__n100.value,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=River_N100.river_centerline__study_lake__n100.value,
        output_name=River_N100.river_centerline__study_rivers__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.river_centerline__water_feature_collapsed__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.river_centerline__study_lake__n100.value,
        output_name=River_N100.river_centerline__study_lake_collapsed__n100.value,
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.river_centerline__study_centerline__n100.value,
        out_feature_class=f"{River_N100.river_centerline__study_dangles__n100.value}_not_selected",
        point_location="DANGLE",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=f"{River_N100.river_centerline__study_dangles__n100.value}_not_selected",
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=River_N100.river_centerline__study_rivers__n100.value,
        output_name=River_N100.river_centerline__study_dangles__n100.value,
    )


if __name__ == "__main__":
    main()
