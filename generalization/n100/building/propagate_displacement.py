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
    setup_arcpy_environment()
    propagate_displacement_building_points()


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def propagate_displacement_building_points():
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
