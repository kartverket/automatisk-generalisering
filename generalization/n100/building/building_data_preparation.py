# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


def main():
    """
    This function prepares data selection of the following features:
    - Begrensningskurve water features to be used as a berrier
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

    # Defining the output name
    output_name_begrensningskurve_waterfeatures = "begrensningskurve_waterfeatures"

    # Creating a temporary feature of water features from begrensningskurve
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures,
        output_name=output_name_begrensningskurve_waterfeatures,
    )


    # Defining the buffer distance used for the buffer of begrensningskurve water features
    buffer_distance_begrensningskurve_waterfeatures = "20 Meters"

    # Defining the output name
    begrensningskurve_buffer_waterfeatures = TemporaryFiles.begrensningskurve_buffer_waterfeatures.value

    # Creating a buffer of the water features begrensningskurve to take into account symbology of the water features
    arcpy.analysis.PairwiseBuffer(
        in_features=output_name_begrensningskurve_waterfeatures,
        out_feature_class=begrensningskurve_buffer_waterfeatures,
        buffer_distance_or_field=buffer_distance_begrensningskurve_waterfeatures,
        dissolve_option="NONE",
        dissolve_field=None,
        method="PLANAR",
    )

    # Adding hierarchy and invisibility fields to the begrensningskurve_waterfeatures_buffer and setting them to 0
    # Define field information
    fields_to_add = [["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=begrensningskurve_buffer_waterfeatures,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=begrensningskurve_buffer_waterfeatures,
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
    unsplit_veg_sti_n100 = TemporaryFiles.unsplit_veg_sti_n100.value
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
    matrikkel_bygningspunkt = TemporaryFiles.matrikkel_bygningspunkt.value

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


adding_matrikkel_as_points()


def selecting_grunnriss_for_generalization():
    """
    Selects grunnriss features for generalization based on a given SQL expression.

    This function first selects all grunnriss features that are not churches or hospitals based on the NBR values (970, 719, 671).
    These selected features are then used for polygon generalization.

    Additionally, this function transforms the selected hospitals and churches into points using the 'CENTROID' method.
    These points are used for point generalization.
    """

    # Expression to be able to select churchs and hospitals
    grunnriss_nbr_sql_expr = "BYGGTYP_NBR IN (970, 719, 671)"

    # Output feature name definition
    grunnriss_selection_n50 = TemporaryFiles.grunnriss_selection_n50.value

    # Selecting grunnriss which are not churches or hospitals using inverted selection
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.Grunnriss,
        expression=grunnriss_nbr_sql_expr,
        output_name=grunnriss_selection_n50,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )

    # Output feeature name definition
    kirke_sykehus_grunnriss_n50 = "kirke_sykehus_grunnriss_n50"

    # Selecting grunnriss features not inverted based on sql expression above to select churches and hospitals
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.Grunnriss,
        expression=grunnriss_nbr_sql_expr,
        output_name=kirke_sykehus_grunnriss_n50,
    )

    # Defining output feature name
    kirke_sykehus_points_n50 = TemporaryFiles.kirke_sykehus_points_n50.value

    # Transforming selected churches and hospitals into points
    arcpy.FeatureToPoint_management(
        in_features=kirke_sykehus_grunnriss_n50,
        out_feature_class=kirke_sykehus_points_n50,
        point_location="CENTROID",
    )
