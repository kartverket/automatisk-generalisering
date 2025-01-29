# DOCSTRING

"""
MAIN

    Summary:
        Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.

    Details:
        1. `setup_arcpy_environment`:
            Sets up the ArcPy environment based on predefined settings defined in `general_setup`.

        2. `propagate_displacement_building_points`:
            Makes sure that the building points are moved correspondingly to the displacement the road features have been moved during its generalization.

SUBFUNCTIONS

    Summary:
        Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
        This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
        the `general_setup` function from the `environment_setup` module.

    Details:
        - It calls the `general_setup` function from the `environment_setup` module to set up the ArcPy environment based on predefined settings.

"""

# IMPORTS

"""
# Importing packages
import arcpy

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator
from custom_tools import custom_arcpy

"""
