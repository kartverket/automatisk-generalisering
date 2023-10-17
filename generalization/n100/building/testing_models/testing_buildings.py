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
import arcpy.management

# import sys
# sys.path.append("C:\\Users\\oftell\\PycharmProjects\\kv_general_py\\kv_git_projects")
#
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from generalization.n100.building import building_data_preparation
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import temp_files

# Importing environment



# def main():
#     building_data_preparation.main()
#
# main()
# arcpy.PairwiseBuffer_analysis(temp_files.selection_fc.value, "testing_file_manager_buffer", "5000 Meters", "NONE", "", "PLANAR")




