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
    preperation_veg_sti()
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
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures,
        output_name=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
    )

    # Adding hierarchy and invisibility fields to the preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100 and setting them to 0
    # Define field information
    fields_to_add = [["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        expression_type="PYTHON3",
        fields=fields_to_calculate,
    )


def preperation_veg_sti():
    """
    Unsplit the lines in the specified feature class based on the given fields, to speed up future processing speed
    when using this as a barrier.

    Parameters:
        input_n100 (str): The path to the input feature class containing the lines to be unsplit.
        output_feature_class (str): The name of the output feature class to be created.
        fields (List[str]): The list of fields to use for unsplitting the lines.
    """
    arcpy.UnsplitLine_management(
        in_features=input_n100.VegSti,
        out_feature_class=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
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

    # Selecting urban areas from n100 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n100.ArealdekkeFlate,
        expression=urban_areas_sql_expr,
        output_name=Building_N100.adding_matrikkel_as_points__urban_area_selection_n100__n100.value,
    )

    # Selecting urban areas from n50 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.ArealdekkeFlate,
        expression=urban_areas_sql_expr,
        output_name=Building_N100.adding_matrikkel_as_points__urban_area_selection_n50__n100.value,
    )

    # Creating a buffer of the urban selection of n100 to take into account symbology
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.adding_matrikkel_as_points__urban_area_selection_n100__n100.value,
        out_feature_class=Building_N100.adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100.value,
        buffer_distance_or_field="50 Meters",
        dissolve_option="NONE",
        dissolve_field=None,
        method="PLANAR",
    )

    # Removing areas from n50 urban areas from the buffer of n100 urban areas resulting in areas in n100 which no longer are urban
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.adding_matrikkel_as_points__urban_area_selection_n50__n100.value,
        erase_features=Building_N100.adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100.value,
        out_feature_class=Building_N100.adding_matrikkel_as_points__no_longer_urban_areas__n100.value,
    )

    # Selecting matrikkel bygningspunkter based on this new urban selection layer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_other.matrikkel_bygningspunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.adding_matrikkel_as_points__no_longer_urban_areas__n100.value,
        output_name=Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
    )

    # # Deleting temporary files no longer needed
    # arcpy.Delete_management(
    #     Building_N100.adding_matrikkel_as_points__urban_area_selection_n100_buffer__n100.value
    # )
    # arcpy.Delete_management(
    #     Building_N100.adding_matrikkel_as_points__no_longer_urban_areas__n100.value
    # )

    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(
        in_table=Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        field_name="BYGGTYP_NBR",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
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

    # Selecting grunnriss which are not churches or hospitals using inverted selection
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.Grunnriss,
        expression=sql_nbr_code_kirke,
        output_name=Building_N100.selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )

    # Selecting grunnriss which are large enough
    grunnriss_minimum_size = 1500
    sql_expression_too_small_grunnriss = f"Shape_Area < {grunnriss_minimum_size}"
    sql_expression_correct_size_grunnriss = f"Shape_Area >= {grunnriss_minimum_size}"

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100.value,
        expression=sql_expression_correct_size_grunnriss,
        output_name=Building_N100.selecting_grunnriss_for_generalization__large_enough_grunnriss__n100.value,
    )

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.selecting_grunnriss_for_generalization__selected_grunnriss_not_church__n100.value,
        expression=sql_expression_too_small_grunnriss,
        output_name=Building_N100.selecting_grunnriss_for_generalization__too_small_grunnriss__n100.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Transforming small grunnriss features into points
    arcpy.FeatureToPoint_management(
        in_features=Building_N100.selecting_grunnriss_for_generalization__too_small_grunnriss__n100.value,
        out_feature_class=Building_N100.selecting_grunnriss_for_generalization__points_created_from_small_grunnriss__n100.value,
        point_location="CENTROID",
    )

    # Selecting grunnriss features not inverted based on sql expression above to select churches and hospitals
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.Grunnriss,
        expression=sql_nbr_code_kirke,
        output_name=Building_N100.selecting_grunnriss_for_generalization__grunnriss_kirke__n100.value,
    )

    # Transforming selected churches and hospitals into points
    arcpy.FeatureToPoint_management(
        in_features=Building_N100.selecting_grunnriss_for_generalization__grunnriss_kirke__n100.value,
        out_feature_class=Building_N100.selecting_grunnriss_for_generalization__kirke_points_created_from_grunnriss__n100.value,
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
        input_layer=Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN,
        select_features=input_n50.Grunnriss,
        output_name="NEEDS UPDATE",
        inverted=True,
    )


# removing_overlapping_byggningspunkt_and_grunnriss_matrikkel()
# main()
