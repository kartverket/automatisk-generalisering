import arcpy

import config
from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100
from input_data import input_n100


def main():
    setup_arcpy_environment()
    propagate_displacement()


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def propagate_displacement():
    arcpy.management.Copy(
        in_data=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        out_data=Building_N100.propagate_displacement__bygningspunkt_pre_displacement__n100.value,
    )

    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        displacement_features=config.displacement_feature,
        adjustment_style="SOLID",
    )


if __name__ == "__main__":
    main()
