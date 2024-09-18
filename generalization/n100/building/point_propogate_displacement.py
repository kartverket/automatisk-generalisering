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
    Propagates displacement for building points to ensure their alignment with roads is adjusted
    after the road generalization process.
    """
    environment_setup.main()
    propagate_displacement_building_points()


@timing_decorator
def propagate_displacement_building_points():
    """
    First copies the data to be able to compare the changes due to PropagateDisplacement modifies input. Then propagates
    displacement for building polygons to ensure their alignment with roads is adjusted after the road generalization process.
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
