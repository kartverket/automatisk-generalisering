from env_setup import environment_setup
from input_data import input_n50
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    """
    Summary:
        This is the main function of river data preparation, which aims to prepare the data for future river generalization processing.

    Details:
        1. `selecting_polygon_features`:
            This function creates new feature classes based on SQL-expressions: the first one to be used to generate centerlines, while the second
            is used to fill geometry gaps in the river network.
    """
    environment_setup.main()
    selecting_polygon_features()


def selecting_polygon_features():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression="OBJTYPE IN ('FerskvannTørrfall', 'Innsjø', 'InnsjøRegulert', 'ElvBekk')",
        output_name=River_N100.selecting_water_polygons__centerline__n100.value,
        selection_type="NEW_SELECTION",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression="OBJTYPE IN ('FerskvannTørrfall', 'Innsjø', 'InnsjøRegulert', 'Havflate', 'ElvBekk')",
        output_name=River_N100.selecting_water_polygons__geometry_gaps__n100.value,
        selection_type="NEW_SELECTION",
    )


if __name__ == "__main__":
    main()
