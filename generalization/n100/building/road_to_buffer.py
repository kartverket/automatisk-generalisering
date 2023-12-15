import numpy as np
import arcpy
import os

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    setup_arcpy_environment()
    # selecting_raod_segments()
    creating_raod_buffer()


# Path to your input feature class
# input_feature_class = Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value
input_feature_class = Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


#
# field_value_to_width = {
#     1.1: 20,
#     1.2: 30,
#     2: 27.5,
#     3: 22.5,
#     4: 27.5,
#     5: 20,
#     6: 20,
#     7: 7.5,
#     8: 7.5,
#     9: 20,
#     10: 7.5,
#     11: 7.5,
# }


def selecting_raod_segments():
    # Construct the SQL queries
    sql_europa_veg = """ "subtypekode" = 4 AND "motorvegtype" = 'Motorveg' AND "UTTEGNING" IS NULL """
    sql_4_motorveg_nedklassifisert = """ "subtypekode" = 4 AND "motorvegtype" = 'Motorveg' AND "UTTEGNING" = 'nedklassifisering' """
    sql_riksveg_motorveg = """ "subtypekode" = 4 AND "motorvegtype" = 'Riksveg' """

    # Width of road segments
    sql_europa_veg_width = 42.5
    sql_4_motorveg_nedklassifisert = 22.5

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer="feature_layer",
        expression=sql_4_motorveg_nedklassifisert,
        output_name=Building_N100.roads_to_polygon__selection_large_roads__n100.value,
    )


def creating_raod_buffer():
    arcpy.analysis.PairwiseBuffer(
        in_features=input_feature_class,
        out_feature_class=Building_N100.roads_to_polygon__roads_buffer__n100.value,
        buffer_distance_or_field="35.0 Meters",
        # dissolve_option="ALL",
    )


if __name__ == "__main__":
    main()
