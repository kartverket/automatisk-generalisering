# Importing modules
import arcpy

# Importing custom files
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100

# Import custom modules
from custom_tools import custom_arcpy
from env_setup import environment_setup


def main():
    environment_setup.main()
    removing_building_points_in_water_features()


def removing_building_points_in_water_features():

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=Building_N100.point_cleanup___water_features___n100_building.value,
    )

    # Select points that DO NOT intersect any waterfeatures
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.point_cleanup___water_features___n100_building.value,
        output_name=Building_N100.point_cleanup___points_that_do_not_intersect_water_features___n100_building.value,
        inverted=True,
    )

    # Select points that intersects water feature buffer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___begrensningskurve_buffer_erase_1___n100_building.value,
        output_name=Building_N100.point_cleanup___points_intersecting_buffer___n100_building.value,
    )

    arcpy.management.Merge(
        inputs=[
            Building_N100.point_cleanup___points_that_do_not_intersect_water_features___n100_building.value,
            Building_N100.point_cleanup___points_intersecting_buffer___n100_building.value,
        ],
        output=Building_N100.polygon_to_point___merged_points_final___n100_building.value,
    )


if __name__ == "__main__":
    main()
