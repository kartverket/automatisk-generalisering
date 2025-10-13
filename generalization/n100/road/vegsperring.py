# Importing packages
from collections import defaultdict
import arcpy
import numpy as np
import math
import os

arcpy.env.overwriteOutput = True

# Importing custom input files modules
from input_data import input_n100

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
]


@timing_decorator
def main():
    """
    """

##################
# Help functions
##################

##################
# Main functions
##################

if __name__ == "__main__":
    main()
