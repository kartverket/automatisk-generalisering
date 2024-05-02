# Importing modules
import arcpy

# Importing custom modules
import config
from custom_tools import custom_arcpy
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("points_propogate_displacement.py")
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
        in_data=Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value,
        out_data=Building_N100.point_propogate_displacement___points_pre_propogate_displacement___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN IN ('Asker', 'Oslo')",
        output_name=Building_N100.point_propogate_displacement___area_oslo_asker___n100_building.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=Building_N100.point_propogate_displacement___area_oslo_asker___n100_building.value,
        output_name=Building_N100.point_propogate_displacement___points_in_area_oslo_asker___n100_building.value,
    )

    # Selecting propogate displacement features 500 meters from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.point_propogate_displacement___points_in_area_oslo_asker___n100_building.value,
        output_name=Building_N100.point_propogate_displacement___displacement_feature_500m_from_point___n100_building.value,
        search_distance="500 Meters",
    )

    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.point_propogate_displacement___points_in_area_oslo_asker___n100_building.value,
        displacement_features=Building_N100.point_propogate_displacement___displacement_feature_500m_from_point___n100_building.value,
        adjustment_style="SOLID",
    )

    arcpy.management.Copy(
        in_data=Building_N100.point_propogate_displacement___points_in_area_oslo_asker___n100_building.value,
        out_data=Building_N100.point_propogate_displacement___points_after_propogate_displacement___n100_building.value,
    )


if __name__ == "__main__":
    main()
