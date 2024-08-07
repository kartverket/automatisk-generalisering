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
    Summary:
        This script first propagates displacement for building polygons to ensure their alignment with roads
        at a scale of 1:100,000. Next, it resolves conflicts among all building polygons in Norway,
        considering various barriers such as roads, waterfeatures, hospital and churches, ensuring proper placement and scaling.

    """
    environment_setup.main()
    propagate_displacement_building_polygons()


@timing_decorator
def propagate_displacement_building_polygons():
    """
    Summary:
        Selects displacement features located within a 500-meter radius from building polygons
        and propagates displacement for the building polygons.

    Details:
        This function selects displacement features within a specified distance (500 meters) from the building polygons
        and applies a displacement operation to ensure the building polygons align appropriately with surrounding features,
        such as roads or other structures.
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
