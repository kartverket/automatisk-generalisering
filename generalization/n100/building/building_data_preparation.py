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
from custom_tools import custom_arcpy
import config
from setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)

input_n100.BegrensningsKurve
sql_expr_begrensningskurve_waterfeatures = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"


custom_arcpy.attribute_select_and_make_feature_layer(input_n100.BegrensningsKurve, sql_expr_begrensningskurve_waterfeatures, "begrensningskurve_waterfeatures")