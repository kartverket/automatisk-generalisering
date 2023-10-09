# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing general packages
import arcpy

# Importing sub models
from generalization.n100.building import building_data_preparation

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)

# def main:
#
