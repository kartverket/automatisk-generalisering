# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100

# from file_manager.n100.file_manager_buildings import file_manager, file_keys

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


def main():
    preparation_begrensningskurve()
    preperation_vegsti()
    preperation_arealdekke_flate()



def preparation_begrensningskurve():
    """
    A function that prepares the begrensningskurve by performing the following steps:
    1. Defining the SQL selection expression for water features for begrensningskurve and creating a temporary feature layer.
    2. Creating a buffer of the water features begrensningskurve to take into account symbology of the water features.
    3. Adding hierarchy and invisibility fields to the begrensningskurve_waterfeatures_buffer and setting them to 0.
    """
    # Defining the SQL selection expression for water features for begrensningskurve, then using that selection to create a temporary feature layer
    sql_expr_begrensningskurve_waterfeatures = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_n100.BegrensningsKurve,
        sql_expr_begrensningskurve_waterfeatures,
        "begrensningskurve_waterfeatures",
    )
    output_name_begrensningskurve_waterfeatures = "begrensningskurve_waterfeatures"

    # Creating a buffer of the water features begrensningskurve to take into account symbology of the water features
    buffer_distance_begrensningskurve_waterfeatures = "20 Meters"
    # output_name_buffer_begrensningskurve_waterfeatures = f"begrensningskurve_waterfeatures_{buffer_distance_begrensningskurve_waterfeatures.replace(' ', '')}_buffer"
    output_name_buffer_begrensningskurve_waterfeatures = "begrensningskurve_waterfeatures_20m_buffer"
    arcpy.analysis.PairwiseBuffer(
        output_name_begrensningskurve_waterfeatures,
        output_name_buffer_begrensningskurve_waterfeatures,
        buffer_distance_begrensningskurve_waterfeatures,
        "NONE",
        "",
        "PLANAR",
    )

    # Adding hierarchy and invisibility fields to the begrensningskurve_waterfeatures_buffer and setting them to 0
    arcpy.management.AddFields(
        output_name_buffer_begrensningskurve_waterfeatures,
        [["hierarchy", "LONG"], ["invisibility", "LONG"]],
    )
    arcpy.management.CalculateFields(
        output_name_buffer_begrensningskurve_waterfeatures,
        "PYTHON3",
        [["hierarchy", "0"], ["invisibility", "0"]],
    )


def preperation_vegsti():
    arcpy.UnsplitLine_management(input_n100.VegSti, "unsplit_veg_sti_n100", ["subtypekode", "motorvegtype", "UTTEGNING"])
    unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"

def preperation_arealdekke_flate():
    sql_expr = "OBJTYPE = 'Tettbebyggelse' Or OBJTYPE = 'Industriområde' Or OBJTYPE = 'BymessigBebyggelse'"
    custom_arcpy.select_location_and_make_permanent_feature(input_n100.ArealdekkeFlate, sql_expr, "urban_selection_n100")
    urban_selection_n100 = "urban_selection_n100"

    custom_arcpy.select_location_and_make_permanent_feature(input_n50.ArealdekkeFlate, sql_expr, "urban_selection_n50")
    urban_selection_n50 = "urban_selection_n50"



