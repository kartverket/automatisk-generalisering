# from generalization.n100.building import building_data_preparation
# from file_manager.n100.file_manager_buildings import file_manager, file_keys
# from custom_tools import custom_arcpy
# from input_data import input_n100
#
#
# building_data_preparation()
# input_file = file_manager.get_file(file_keys.selection_fc)
#
# custom_arcpy.select_location_and_make_feature_layer(input_n100.BygningsPunkt, input_file, custom_arcpy.OverlapType.WITHIN, "testing_file_manager2")
#

# import sys
# sys.path.append("C:\\Users\\oftell\\PycharmProjects\\kv_general_py\\kv_git_projects")
#
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)

input_n50.check_paths()
input_n100.check_paths()
