from rootpath import detect
import sys, os

def add_subdirs_to_path(dir_path):
    for root, dirs, files in os.walk(dir_path):
        sys.path.append(root)
        for dir_name in dirs:
            sys.path.append(os.path.join(root, dir_name))

root_path = detect()
add_subdirs_to_path(root_path)

# Importing custom files relative to the root path
import custom_arcpy
import config
import environment_setup
import input_n100
import  input_n50

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)



# print(input_n100.BegrensingsKurve)
# print(r"C:\GIS_Files\n100.gdb\BegrensningsKurve")
#
# # Selecting water features to use as barriers and creating a temporary layer feature
# water_expr = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"
# # custom_arcpy.attribute_select_and_make_feature_layer(
# #     r"C:\GIS_Files\n100.gdb\BegrensingsKurve", water_expr, "n100_begrensingskurve_waterfeatures"
# # )
# custom_arcpy.attribute_select_and_make_feature_layer(input_n100.BegrensingsKurve, water_expr, "n100_begrensingskurve_waterfeatures")



# custom_arcpy.attribute_select_and_make_permanent_feature(
#     input_n100.BegrensingsKurve,
#     water_expr,
#     "n100_begrensingskurve_waterfeatures_copy2",
# )
# n100_begrensingskurve_waterfeatures = "n100_begrensingskurve_waterfeatures_copy2"


