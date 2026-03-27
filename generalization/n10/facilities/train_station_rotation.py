# Imports
import arcpy
from math import degrees, atan2
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from input_data import input_roads
from road.point_rotation_tool import tool

arcpy.env.overwriteOutput = True


def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N10.train_station__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    tool(
        in_features_line=files[fc.non_overlapping_roads],
        in_features_point=files[fc.roadblocks_preprocessed],
        out_feature_class=files[fc.roadblocks_done],
        rotation_difference=90,
    )


class fc(Enum):
    target_roads = "target_roads"
    additional_roads = "additional_roads"
    non_processed_roadblocks = "non_processed_roadblocks"

    non_overlapping_roads = "non_overlapping_roads"
    target_additional_combined = "target_additional_combined"
    roadblocks_preprocessed = "roadblocks_preprocessed"

    target_area = "target_area"
    target_roads_adjusted = "target_roads_adjusted"
    target_roads_adjusted_single = "target_roads_adjusted_single"
    target_roads_fully_adjusted = "target_roads_fully_adjusted"

    target_roads_w_bearing = "target_roads_w_bearing"

    roadblocks_done = "roadblocks_done"


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:

    non_overlapping_roads = wfm.build_file_path(
        file_name="non_overlapping_roads", file_type="gdb"
    )
    roadblocks_preprocessed = wfm.build_file_path(
        file_name="roadblocks_preprocessed", file_type="gdb"
    )
    roadblocks_done = wfm.build_file_path(file_name="roadblocks_done", file_type="gdb")

    return {
        fc.non_overlapping_roads: non_overlapping_roads,
        fc.roadblocks_preprocessed: roadblocks_preprocessed,
        fc.roadblocks_done: roadblocks_done,
    }


@timing_decorator
def fetch_data(files: dict) -> None:

    orig_points_unsnapped_lyr = "orig_points_unsnapped_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_roads.road_vegsperring, out_layer=orig_points_unsnapped_lyr
    )

    orig_road_lyr = "orig_road_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_roads.road_veglenke, out_layer=orig_road_lyr
    )

    arcpy.edit.Snap(
        in_features=orig_points_unsnapped_lyr,
        snap_environment=[[orig_road_lyr, "EDGE", "0.05"]],
    )

    arcpy.management.CopyFeatures(
        in_features=orig_points_unsnapped_lyr,
        out_feature_class=files[fc.roadblocks_preprocessed],
    )
    arcpy.management.CopyFeatures(
        in_features=orig_road_lyr, out_feature_class=files[fc.non_overlapping_roads]
    )


if __name__ == "__main__":
    main()
