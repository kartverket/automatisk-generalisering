"""
THIS DOCUMENT SHOWS EXAMPLES OF FILE STRUCTURE TO KEEP THE CODE READABLE 






------------ DOCSTRINGS -------------------------------------------------------------------------------------------------







------------ IMPORTS -------------------------------------------------------------------------------------------------




Separate between these

1: Modules
2: Custom modules / scripts
3: Environment setup

EXAMPLE: 

# Importing modules
import arcpy
import os
import time

# Importing custom modules
import config
from custom_tools import custom_arcpy
from input_data import input_n50
from input_data import input_n100

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment setup
from env_setup import environment_setup

# Environment setup
environment_setup.general_setup()








------------ GENERAL FILE STRUCTURE -------------------------------------------------------------------------------------------------


Separate different functions and logics using hashtags like this structure: 

###################################### Selecting hospital and churches from all building points ################################################










------------ FILE MANAGER STRUCTURE -------------------------------------------------------------------------------------------------

for files use this structure:  

####################################################
########### HOSPITAL AND CHURCH CLUSTERS ###########
####################################################

for functions use this structure:

# Functon: hospital_church_selections

"""
