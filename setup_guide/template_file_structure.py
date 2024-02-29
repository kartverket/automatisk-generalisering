# DOCSTRING

"""
    # Summary:
    Finds hospital and church clusters.
    A cluster is defined as two or more points that are closer together than 200 meters.

    # Details:
    - Hospitals are selected based on 'BYGGTYP_NBR' values 970 and 719.
    - Churches are selected based on 'BYGGTYP_NBR' value 671.

    # Parameters
     The tool FindPointClusters have a search distance of 200 meters and minimum points of 2.

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
