import numpy as np
import arcpy
import os


from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()


# Path to your input feature class
# input_feature_class = Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value
input_feature_class = Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


if __name__ == "__main__":
    main()
