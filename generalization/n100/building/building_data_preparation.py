# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# from file_manager.n100.file_manager_buildings import file_manager, file_keys

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


def main():
    preparation_begrensningskurve()
    preperation_vegsti()
    adding_matrikkel_as_points()
    selecting_grunnriss_for_generalization()


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
    output_name_buffer_begrensningskurve_waterfeatures = (
        "begrensningskurve_waterfeatures_20m_buffer"
    )
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
    """
    Unsplit the lines in the specified feature class based on the given fields.

    Parameters:
        input_n100 (str): The path to the input feature class containing the lines to be unsplit.
        output_feature_class (str): The name of the output feature class to be created.
        fields (List[str]): The list of fields to use for unsplitting the lines.

    Returns:
        None
    """
    unsplit_veg_sti_n100 = "unsplit_veg_sti_n100"
    arcpy.UnsplitLine_management(
        input_n100.VegSti,
        unsplit_veg_sti_n100,
        ["subtypekode", "motorvegtype", "UTTEGNING"],
    )


def adding_matrikkel_as_points():
    """
    Generates a selection of areas that are no longer considered urban based on specific criteria.

    This function performs the following steps:
    1. Selects features from the input_n100.ArealdekkeFlate layer where the OBJTYPE is 'Tettbebyggelse', 'Industriområde', or 'BymessigBebyggelse'.
    2. Creates a feature layer called 'urban_selection_n100' based on the selected features.
    3. Selects features from the input_n50.ArealdekkeFlate layer where the OBJTYPE is 'Tettbebyggelse', 'Industriområde', or 'BymessigBebyggelse'.
    4. Creates a feature layer called 'urban_selection_n50' based on the selected features.
    5. Performs a pairwise buffer analysis on the 'urban_selection_n100' layer with a buffer distance of 50 Meters, resulting in a new feature layer called 'urban_selection_n100_buffer'.
    6. Performs a pairwise erase analysis on the 'urban_selection_n50' layer using the 'urban_selection_n100_buffer' layer as the erase feature, resulting in a new feature layer called 'no_longer_urban_n100'.

    Parameters:
    None

    Returns:
    None
    """
    sql_expr = "OBJTYPE = 'Tettbebyggelse' Or OBJTYPE = 'Industriområde' Or OBJTYPE = 'BymessigBebyggelse'"
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_n100.ArealdekkeFlate, sql_expr, "urban_selection_n100"
    )
    urban_selection_n100 = "urban_selection_n100"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_n50.ArealdekkeFlate, sql_expr, "urban_selection_n50"
    )
    urban_selection_n50 = "urban_selection_n50"

    arcpy.PairwiseBuffer_analysis(
        urban_selection_n100,
        "urban_selection_n100_buffer",
        "50 Meters",
        "NONE",
        "",
        "PLANAR",
    )
    urban_selection_n100_buffer = "urban_selection_n100_buffer"

    arcpy.PairwiseErase_analysis(
        urban_selection_n50, urban_selection_n100_buffer, "no_longer_urban_n100"
    )
    no_longer_urban_n100 = "no_longer_urban_n100"

    matrikkel_bygningspunkt = "matrikkel_bygningspunkt"
    custom_arcpy.select_location_and_make_permanent_feature(
        input_other.matrikkel_bygningspunkt,
        custom_arcpy.OverlapType.INTERSECT,
        no_longer_urban_n100,
        matrikkel_bygningspunkt,
    )

    arcpy.Delete_management(urban_selection_n100_buffer)
    arcpy.Delete_management(no_longer_urban_n100)

    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(matrikkel_bygningspunkt, "BYGGTYP_NBR", "LONG")
    arcpy.CalculateField_management(
        matrikkel_bygningspunkt, "BYGGTYP_NBR", "!bygningstype!"
    )

    ###### NEED TO REMEBER TO REMOVE NBR VALUES NOT WANTED TO BE DELIVERED############




def selecting_grunnriss_for_generalization():
    """
    Selects grunnriss features for generalization based on a given SQL expression.

    This function first selects all grunnriss features that are not churches or hospitals based on the NBR values (970, 719, 671).
    These selected features are then used for polygon generalization.

    Additionally, this function transforms the selected hospitals and churches into points using the 'CENTROID' method.
    These points are used for point generalization.
    """

    sql_expr = "BYGGTYP_NBR IN (970, 719, 671)"
    grunnriss_selection_n50 = "grunnriss_selection_n50"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_n50.Grunnriss,
        sql_expr,
        grunnriss_selection_n50,
        custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )

    kirke_sykehus_grunnriss_n50 = "kirke_sykehus_grunnriss_n50"
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_n50.Grunnriss, sql_expr, kirke_sykehus_grunnriss_n50
    )

    kirke_sykehus_points_n50 = "kirke_sykehus_points_n50"
    arcpy.FeatureToPoint_management(
        kirke_sykehus_grunnriss_n50, kirke_sykehus_points_n50, "CENTROID"
    )
