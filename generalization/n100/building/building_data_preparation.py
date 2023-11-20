# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from file_manager.n100.file_manager_buildings import Building_N100


# Importing general packages
import arcpy

# Importing environment
environment_setup.general_setup()


def main():
    """
    This function prepares data selection of the following features:
    - Begrensningskurve water features to be used as a barrier
    - Unsplit veg sti to be used as a barrier
    - Matrikkel bygningspunkt to add building points removed by urban areas in n50
    - Grunnriss selection for generalization and transforming church and hospital grunnriss to points.
    """
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
    # Defining the SQL selection expression for water features for begrensningskurve
    sql_expr_begrensningskurve_waterfeatures = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"

    # Creating a temporary feature of water features from begrensningskurve
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures,
        output_name=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
    )

    # Creating a buffer of the water features begrensningskurve to take into account symbology of the water features
    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        out_feature_class=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100.value,
        buffer_distance_or_field="20 Meters",
        dissolve_option="NONE",
        dissolve_field=None,
        method="PLANAR",
    )

    # Adding hierarchy and invisibility fields to the preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100 and setting them to 0
    # Define field information
    fields_to_add = [["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100.value,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100.value,
        expression_type="PYTHON3",
        fields=fields_to_calculate,
    )


def preperation_vegsti():
    """
    Unsplit the lines in the specified feature class based on the given fields, to speed up future processing speed
    when using this as a barrier.

    Parameters:
        input_n100 (str): The path to the input feature class containing the lines to be unsplit.
        output_feature_class (str): The name of the output feature class to be created.
        fields (List[str]): The list of fields to use for unsplitting the lines.
    """
    unsplit_veg_sti_n100 = Building_N100.unsplit_veg_sti_n100.value
    arcpy.UnsplitLine_management(
        in_features=input_n100.VegSti,
        out_feature_class=unsplit_veg_sti_n100,
        dissolve_field=["subtypekode", "motorvegtype", "UTTEGNING"],
    )


def adding_matrikkel_as_points():
    """
    Adds building points from matrikkel for areas which no longer are urban areas.

    This function performs the following steps:
    1. Selects features and creates a layer from the input_n100.ArealdekkeFlate layer which are urban.
    2. Selects features and creates a layer from the input_n50.ArealdekkeFlate layer which are urban.
    3. Adds a buffer to the urban selection from n100 as a short hand for symbology.
    4. Removes areas from n50 urban areas from the buffer of n|50 urban areas resulting in areas in n100 which no longer are urban.
    5. Selects matrikkel bygningspunkter based on this new urban selection layer, and adds NBR values to the created points.
    """

    # Defining sql expression to select urban areas
    urban_areas_sql_expr = "OBJTYPE = 'Tettbebyggelse' Or OBJTYPE = 'Industriområde' Or OBJTYPE = 'BymessigBebyggelse'"

    # Defining output names
    urban_selection_n100 = "urban_selection_n100"

    # Selecting urban areas from n100 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n100.ArealdekkeFlate,
        expression=urban_areas_sql_expr,
        output_name=urban_selection_n100,
    )

    # Defining output names
    urban_selection_n50 = "urban_selection_n50"

    # Selecting urban areas from n50 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.ArealdekkeFlate,
        expression=urban_areas_sql_expr,
        output_name=urban_selection_n50,
    )

    # Defining output names
    urban_selection_n100_buffer = "urban_selection_n100_buffer"

    # Creating a buffer of the urban selection of n100 to take into account symbology
    arcpy.PairwiseBuffer_analysis(
        in_features=urban_selection_n100,
        out_feature_class=urban_selection_n100_buffer,
        buffer_distance_or_field="50 Meters",
        dissolve_option="NONE",
        dissolve_field=None,
        method="PLANAR",
    )

    # Defining output names
    no_longer_urban_n100 = "no_longer_urban_n100"

    # Removing areas from n50 urban areas from the buffer of n100 urban areas resulting in areas in n100 which no longer are urban
    arcpy.PairwiseErase_analysis(
        in_features=urban_selection_n50,
        erase_features=urban_selection_n100_buffer,
        out_feature_class=no_longer_urban_n100,
    )

    # Defining output names
    matrikkel_bygningspunkt = Building_N100.matrikkel_bygningspunkt.value

    # Selecting matrikkel bygningspunkter based on this new urban selection layer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_other.matrikkel_bygningspunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=no_longer_urban_n100,
        output_name=matrikkel_bygningspunkt,
    )

    # Deleting temporary files no longer needed
    arcpy.Delete_management(urban_selection_n100_buffer)
    arcpy.Delete_management(no_longer_urban_n100)

    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(
        in_table=matrikkel_bygningspunkt,
        field_name="BYGGTYP_NBR",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=matrikkel_bygningspunkt,
        field="BYGGTYP_NBR",
        expression="!bygningstype!",
    )

    ###### NEED TO REMEBER TO REMOVE NBR VALUES NOT WANTED TO BE DELIVERED############
    print(
        " ###### NEED TO REMEBER TO REMOVE NBR VALUES NOT WANTED TO BE DELIVERED############"
    )


def selecting_grunnriss_for_generalization():
    """
    Selects grunnriss features for generalization based on a given SQL expression.

    This function first selects all grunnriss features that are not churches or hospitals based on the NBR values (970, 719, 671).
    These selected features are then used for polygon generalization.

    Additionally, this function transforms the selected hospitals and churches into points using the 'CENTROID' method.
    These points are used for point generalization.
    """

    # Reclassify the sykehus from grunnriss to another NBR value
    code_block_hospital = (
        "def hospital_nbr(nbr):\n"
        "    mapping = {970: 729, 719: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    # Reclassify the sykehus from grunnriss to another NBR value
    arcpy.CalculateField_management(
        in_table=input_n50.Grunnriss,
        field="BYGGTYP_NBR",
        expression="hospital_nbr(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital,
    )

    # Expression to be able to select churchs and hospitals
    sql_nrb_code_sykehus = "BYGGTYP_NBR IN (970, 719)"
    sql_nbr_code_kirke = "BYGGTYP_NBR IN (671)"

    # Defining output names
    grunnriss_selection_not_church = "grunnriss_selection_not_church"

    # Selecting grunnriss which are not churches or hospitals using inverted selection
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.Grunnriss,
        expression=sql_nbr_code_kirke,
        output_name=grunnriss_selection_not_church,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )

    # Output feature name definition
    grunnriss_selection_n50 = Building_N100.grunnriss_selection_n50.value

    grunnriss_minimum_size = 1500
    sql_expression_too_small_grunnriss = f"Shape_Area < {grunnriss_minimum_size}"
    sql_expression_correct_size_grunnriss = f"Shape_Area >= {grunnriss_minimum_size}"

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=grunnriss_selection_not_church,
        expression=sql_expression_correct_size_grunnriss,
        output_name=grunnriss_selection_n50,
    )

    # Define output feature name
    too_small_grunnriss = "too_small_grunnriss"

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=grunnriss_selection_not_church,
        expression=sql_expression_too_small_grunnriss,
        output_name=too_small_grunnriss,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Defining output feature name
    small_grunnriss_points_n50 = Building_N100.small_grunnriss_points_n50.value

    # Transforming selected churches and hospitals into points
    arcpy.FeatureToPoint_management(
        in_features=too_small_grunnriss,
        out_feature_class=small_grunnriss_points_n50,
        point_location="CENTROID",
    )

    # Output feeature name definition
    kirke_sykehus_grunnriss_n50 = "kirke_sykehus_grunnriss_n50"

    # Selecting grunnriss features not inverted based on sql expression above to select churches and hospitals
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.Grunnriss,
        expression=sql_nrb_code_sykehus,
        output_name=kirke_sykehus_grunnriss_n50,
    )

    # Defining output feature name
    kirke_sykehus_points_n50 = Building_N100.kirke_sykehus_points_n50.value

    # Transforming selected churches and hospitals into points
    arcpy.FeatureToPoint_management(
        in_features=kirke_sykehus_grunnriss_n50,
        out_feature_class=kirke_sykehus_points_n50,
        point_location="CENTROID",
    )


def removing_overlapping_byggningspunkt_and_grunnriss_matrikkel():
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_n50.BygningsPunkt,
        overlap_type=custom_arcpy.OverlapType.WITHIN,
        select_features=input_n50.Grunnriss,
        output_name="NEEDS UPDATE",
        inverted=True,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.matrikkel_bygningspunkt.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN,
        select_features=input_n50.Grunnriss,
        output_name="NEEDS UPDATE",
        inverted=True,
    )


# removing_overlapping_byggningspunkt_and_grunnriss_matrikkel()
preparation_begrensningskurve()
