import numpy as np
import arcpy
import os
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()


# Path to your input feature class
input_feature_class = Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value

# Create a feature layer from the feature class
arcpy.MakeFeatureLayer_management(input_feature_class, "feature_layer")

# Construct the SQL query
query = """ "subtypekode" = 4 AND "motorvegtype" = 'Motorveg' """

custom_arcpy.select_attribute_and_make_permanent_feature(
    input_layer="feature_layer",
    expression=query,
)
# Perform the selection
arcpy.SelectLayerByAttribute_management("feature_layer", "NEW_SELECTION", query)


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


field_value_to_width = {
    1.1: 20,
    1.2: 30,
    2: 27.5,
    3: 22.5,
    4: 27.5,
    5: 20,
    6: 20,
    7: 7.5,
    8: 7.5,
    9: 20,
    10: 7.5,
    11: 7.5,
}


if __name__ == "__main__":
    main()
