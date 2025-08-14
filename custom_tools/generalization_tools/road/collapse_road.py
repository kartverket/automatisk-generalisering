import arcpy
from typing import List, Dict

from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100
import config
from input_data.input_symbology import SymbologyN100
from input_data import input_roads


@partition_io_decorator(
    input_param_names=["road_network_input"], output_param_names=["road_network_output"]
)
def collapse_road(
    road_network_input: str,
    road_network_output: str,
    merge_distance: str,
    collapse_field_name: str = None,
):
    if collapse_field_name is not None:
        arcpy.cartography.CollapseRoadDetail(
            in_features=road_network_input,
            out_feature_class=road_network_output,
            collapse_distance=merge_distance,
            collapse_field=collapse_field_name,
        )

    else:
        arcpy.cartography.CollapseRoadDetail(
            in_features=road_network_input,
            collapse_distance=merge_distance,
            output_feature_class=road_network_output,
        )
