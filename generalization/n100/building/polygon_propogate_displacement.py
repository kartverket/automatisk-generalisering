# Importing modules
import arcpy

# Importing custom modules
import config
from custom_tools.general_tools import custom_arcpy

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    """
    Propagates displacement for building polygons to ensure their alignment with roads is adjusted
    after the road generalization process.
    """
    environment_setup.main()
    propagate_displacement_building_polygons()


@timing_decorator
def propagate_displacement_building_polygons():
    """
    First selects displacement features within a specified distance (500 meters) from the building polygons, then propagates
    displacement for building polygons to ensure their alignment with roads is adjusted after the road generalization process.
    """

    print("MAKE SURE TO SWITCH TO NEW DISPLACEMENT FEATURE (AFTER ROAD GENERALIZATION")

    print("Propogate displacement ...")
    # Copying layer so no changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.simplify_polygons___spatial_join_polygons___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        displacement_features=Building_N100.data_selection___displacement_feature___n100_building.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
    )


if __name__ == "__main__":
    main()
