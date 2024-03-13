# Importing modules
import arcpy
import time

# Importing custom files
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100

# Import custom modules
from custom_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.polygon_processor import PolygonProcessor


def main():
    environment_setup.main()
    removing_building_points_in_water_features()
    polygons_too_close_to_building_points()
    merging_points()


def removing_building_points_in_water_features():

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=Building_N100.point_cleanup___water_features___n100_building.value,
    )

    # Select points that intersect water features
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.point_cleanup___water_features___n100_building.value,
        output_name=Building_N100.point_cleanup___points_that_intersect_water_features___n100_building.value,
    )

    # Select points that do NOT intersect water feature buffer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_cleanup___points_that_intersect_water_features___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___begrensningskurve_buffer_erase_1___n100_building.value,
        output_name=Building_N100.point_cleanup___points_not_intersecting_buffer___n100_building.value,
        inverted=True,  # Inverted
    )


def polygons_too_close_to_building_points():

    # Checking if building polygons intersect with building squares (representing point symbology)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___building_polygons_final___n100_building.value,
        output_name=Building_N100.point_cleanup___points_50m_from_building_polygons___n100_building.value,
        search_distance="50 Meters",
    )

    # Polygon prosessor to transform building points to squares, representing the points symbology.
    building_symbol_dimensions = {
        1: (145, 145),
        2: (145, 145),
        3: (195, 145),
        4: (40, 40),
        5: (80, 80),
        6: (30, 30),
        7: (45, 45),
        8: (45, 45),
        9: (53, 45),
    }
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        Building_N100.point_cleanup___points_50m_from_building_polygons___n100_building.value,  # input
        Building_N100.point_cleanup___building_points_to_squares___n100_building.value,  # output
        building_symbol_dimensions,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Checking which building polygons DO NOT intersect with building squares (representing point symbology)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.point_cleanup___building_points_to_squares___n100_building.value,
        output_name=Building_N100.point_cleanup___polygons_not_too_close_to_squares___n100_building.value,
        search_distance="15 Meters",
        inverted=True,  # Inverted
    )

    # Checking which building polygons intersect with building squares (representing point symbology)
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.point_cleanup___building_points_to_squares___n100_building.value,
        output_name=Building_N100.point_cleanup___polygons_too_close_to_squares___n100_building.value,
        search_distance="15 Meters",
        inverted=False,  # NOT Inverted
    )
    # Transforming the polygons that overlap with points to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.point_cleanup___polygons_too_close_to_squares___n100_building.value,
        out_feature_class=Building_N100.point_cleanup___building_points_final___n100_building.value,
    )


def merging_points():
    # Layers to merge
    merge_list = [
        Building_N100.point_cleanup___building_points_final___n100_building.value,
        Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        Building_N100.polygon_propogate_displacement___small_building_polygons_to_point___n100_building.value,
    ]
    # Merge the new points with other building points
    arcpy.management.Merge(
        inputs=merge_list,
        output=Building_N100.point_cleanup___building_points_merged_final__n100_building.value,
    )


if __name__ == "__main__":
    main()
