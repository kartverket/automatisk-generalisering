# Importing modules
import numpy as np
import arcpy

# Importing custom modules
import config
from input_data import input_n100
from custom_tools import custom_arcpy

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100


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
    setup_arcpy_environment()
    propagate_displacement_building_points()


def setup_arcpy_environment():
    """
    Summary:
        Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
        This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
        the `general_setup` function from the `environment_setup` module.

    Details:
        - It calls the `general_setup` function from the `environment_setup` module to set up the ArcPy environment based on predefined settings.
    """

    environment_setup.general_setup()


def propagate_displacement_building_points():
    """
    Summary:
        Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.

    Details:
        - It copies the original dataset to prevent overwriting the data since PropagateDisplacement modifiy the input data.
        - When using Propagate Displacement, the adjustment style chosen for this process is "SOLID" to prevent the change of shape of input polygons (though not relevant for building points).
    """

    arcpy.management.Copy(
        in_data=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        out_data=Building_N100.propagate_displacement__bygningspunkt_pre_propogate_displacement__n100.value,
    )

    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        displacement_features=config.displacement_feature,
        adjustment_style="SOLID",
    )


if __name__ == "__main__":
    main()
