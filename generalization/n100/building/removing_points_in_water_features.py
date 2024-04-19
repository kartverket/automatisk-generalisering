# Importing modules
import arcpy

# Importing custom files
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from input_data.input_symbology import SymbologyN100

# Import custom modules
from custom_tools import custom_arcpy
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("removing_points_in_water_features.py")
def main():
    environment_setup.main()
    removing_points_in_water_features()


@timing_decorator
def removing_points_in_water_features():
    """
    Summary:
        Removes points within water features.

    Details:
        This function selects water features from the input layer based on a predefined SQL expression.
        Then, it selects points that do not intersect with any water features and retains them.
    """

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=Building_N100.removing_points_in_water_features___water_features___n100_building.value,
    )

    # Select points that DO NOT intersect any waterfeatures
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_points_RBC_final___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.removing_points_in_water_features___water_features___n100_building.value,
        output_name=Building_N100.removing_points_in_water_features___final_points___n100_building.value,
        inverted=True,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.removing_points_in_water_features___final_points___n100_building.value,
        in_symbology_layer=SymbologyN100.bygningspunkt.value,
        output_name=Building_N100.removing_points_in_water_features___final_points___n100_lyrx.value,
    )


if __name__ == "__main__":
    main()
