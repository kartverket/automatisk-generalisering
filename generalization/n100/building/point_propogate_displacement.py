# Importing modules
import arcpy

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    """
    Summary:
        Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.

    Details:
        1. `setup_arcpy_environment`:
            Sets up the ArcPy environment based on predefined settings defined in `general_setup`.

        2. `propagate_displacement_building_points`:
            Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.
    """
    environment_setup.main()
    propagate_displacement_building_points()


@timing_decorator
def propagate_displacement_building_points():
    """
    Summary:
        Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.

    Details:
        - It copies the original dataset to prevent overwriting the data since PropagateDisplacement modifiy the input data.
        - When using Propagate Displacement, the adjustment style chosen for this process is "SOLID" to prevent the change of shape of input polygons (though not relevant for building points).
    """

    print("Point propogate displacement ...")

    arcpy.management.Copy(
        in_data=Building_N100.calculate_point_values___points_going_into_propagate_displacement___n100_building.value,
        out_data=Building_N100.point_propagate_displacement___points_after_propagate_displacement___n100_building.value,
    )

    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.point_propagate_displacement___points_after_propagate_displacement___n100_building.value,
        displacement_features=Building_N100.data_selection___displacement_feature___n100_building.value,
        adjustment_style="SOLID",
    )


if __name__ == "__main__":
    main()
