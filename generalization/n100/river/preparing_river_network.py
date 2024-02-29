# Importing modules
import arcpy

import config

# Importing custom tools
from custom_tools import custom_arcpy
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_rivers import River_N100


def main():
    """
    Summary:
        This script prepares the river network for the 1:100,000 scale by setting line directions and thinning hydrology lines.

    Details:
        1. `set_line_direction`:
            Sets the direction of each stream segment in the river network based on downhill flow.

        2. `thin_hydrology_lines`:
            Thins the hydrology lines in the river network to optimize for the 1:100,000 scale.
            The function thins the river network, removing line segments based on hierarchy, direction, length and spacing between features

    """
    environment_setup.main()
    set_line_direction()


# This function sets the direction of each stream segment in the river network
def set_line_direction():
    arcpy.topographic.SetLineDirection(
        in_line_features="placeholder",
        digital_elevation_model="placeholder_for_DTM",
        line_direction="DOWNHILL_FLOW",
    )


# This function thins the river network
def thin_hydrology_lines():
    arcpy.topographic.ThinHydrologyLines(
        in_features="placeholder_for_streamnetwork",
        invisibility_field="invisibility",
        min_length="500",
        min_spacing="100",
        hierarchy_field="Strahler_placeholder",
        intersecting_features=River_N100.selecting_water_polygons__centerline__n100.value,
        unsplit_lines="UNSPLIT_LINES",
        use_angles="NO_USE_ANGLES",
    )
    # Selecting featueres that have visibility value 0 from Thin Hydrology Lines
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer="placeholder_from_function_above",
        expression="invisibility = 0",
        output_name=River_N100.thin_hydrology_lines__visible_streams__n100.value,
        selection_type="NEW_SELECTION",
    )


if __name__ == "__main__":
    main()
