# Importing modules
import arcpy
import time

# Importing custom files

from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100

# Import custom modules
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup


def removing_building_points_in_water_features():

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=Building_N100.last_point_removal___water_features___n100_building.value,
    )

    # Select points that intersect water features
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_2__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.last_point_removal___water_features___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___displacement_feature_1000m_from_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_2__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.last_point_removal___water_features___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___displacement_feature_1000m_from_polygon___n100_building.value,
        search_distance="500 Meters",
    )
