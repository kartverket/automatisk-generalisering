import arcpy
from typing import List, Dict

from composition_configs import logic_config


def collapse_road(
    collapse_road_config: logic_config.CollapseRoadDetailsKwargs,
):
    merge_distance = f"{collapse_road_config.merge_distnace_m} Meters"

    if collapse_road_config.collapse_field_name is not None:
        arcpy.cartography.CollapseRoadDetail(
            in_features=collapse_road_config.input_road_line,
            collapse_distance=merge_distance,
            output_feature_class=collapse_road_config.output_road_line,
            locking_field=collapse_road_config.collapse_field_name,
        )

    else:
        arcpy.cartography.CollapseRoadDetail(
            in_features=collapse_road_config.input_road_line,
            collapse_distance=merge_distance,
            output_feature_class=collapse_road_config.output_road_line,
        )
