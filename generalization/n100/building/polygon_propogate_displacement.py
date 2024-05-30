# Importing modules
import arcpy

# Importing custom modules
import config
from custom_tools import custom_arcpy

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

    # Selecting propogate displacement features 500 meters from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___displacement_feature_500m_from_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        displacement_features=Building_N100.polygon_propogate_displacement___displacement_feature_500m_from_polygon___n100_building.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
    )


if __name__ == "__main__":
    main()
