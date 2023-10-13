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


def preparation_begrensningskurve():
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
    output_name_buffer_begrensningskurve_waterfeatures = f"begrensningskurve_waterfeatures_{buffer_distance_begrensningskurve_waterfeatures.replace(' ', '')}_buffer"
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
    return output_name_buffer_begrensningskurve_waterfeatures


# def testing_file_manager_old():
#     output_name_unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
#     arcpy.UnsplitLine_management(
#         input_n100.VegSti,
#         output_name_unsplit_veg_sti_n100,
#         ["subtypekode", "motorvegtype", "UTTEGNING"],
#     )
#
#     sql_expr_arealdekke_urban_n100 = "OBJTYPE = 'Tettbebyggelse' Or OBJTYPE = 'Industriområde' Or OBJTYPE = 'BymessigBebyggelse'"
#     output_name_arealdekke_urban_n100 = "arealdekke_urban_n100"
#     custom_arcpy.select_attribute_and_make_permanent_feature(
#         input_n100.ArealdekkeFlate,
#         sql_expr_arealdekke_urban_n100,
#         output_name_arealdekke_urban_n100,
#         custom_arcpy.SelectionType.NEW_SELECTION,
#     )
#
#     output_name_unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
#     file_manager.add_file(
#         "output_name_unsplit_veg_sti_n100", output_name_unsplit_veg_sti_n100
#     )
#
#
# def test_file_manger():
#     custom_arcpy.select_attribute_and_make_permanent_feature(
#         input_n100.AdminFlate, "NAVN = 'Oslo'", "selection_fc"
#     )
#
#     selection_fc = "selection_fc"
#     return  selection_fc

