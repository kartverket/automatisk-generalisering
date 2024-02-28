# Importing modules
import arcpy

# Importing custom files
from custom_tools import custom_arcpy
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing environment
from env_setup import environment_setup

# Environment setup
environment_setup.general_setup()

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("building_data_preparation.py")
def main():
    """
    Summary:
        This is the main function of building data preparation, which aims to prepare the data for future building generalization processing.

    Details:
        1. `preparation_begrensningskurve`:
            This function creates a buffer for water features using the water features (begrensningskurve for vann). It prepares the data for future building placement on the water features edge.

        2. `preperation_veg_sti`:
            This function unsplits a line feature of roads to reduce the number of objects in future processing.

        3. `adding_matrikkel_as_points`:
            This function adds building points from the cadastre (matrikkel) for areas that are no longer considered urban after the generalization of land cover (arealdekke).
            It also adds the required fields and values for future analysis.

        4. `selecting_grunnriss_for_generalization`:
            This function selects building polygons (grunnriss) to be generalized. Smaller polygons, churches and hospitals are excluded, transformed into points, and sent to building point generalization.
    """

    preparation_begrensningskurve()
    preperation_veg_sti()
    adding_matrikkel_as_points()
    selecting_grunnriss_for_generalization()


###################################### Preparing begrensningskurve (limitation curve) ################################################


@timing_decorator
def preparation_begrensningskurve():
    """
    Summary:
        This function creates a buffer for water features using the "begrensningskurve" feature. It prepares the data for future building placement on the water's edge.

    Details:
        - Using the object types ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert') in the "begrensningskurve" feature in SQL expressions to select water features and in inverse to select land features.
        - Create a temporary feature of water features from the "begrensningskurve" using the defined SQL expression.
        - Select land features using an inverted selection using the defined SQL expression.
        - Identify land features near water features by selecting those that boundary-touch with water features to reduce the amount of processing.
        - Apply a 15-meter buffer to the identified land features to create buffered land features, this is the distance objects is allowed to be overlapping water features in the final output.
        - Apply a 45-meter buffer to the selected water features to create buffered water features, this is to make sure features are not going past the water barrier and is instead pushed towrds land instead of further inside waterfeatures.
        - Erase buffered water features from the buffered land features to create a final set of waterfeature buffer which is used throughout this generalization of buildings.

    Note:
        - Additional logic may be required for rivers separately in future development as narrow polygons gets completly removed due to the land buffer being to large for the rivers. In processes actually needing barriers this will allow objects to cross narrow rivers.
    """

    # Defining the SQL selection expression for water features for begrensningskurve
    sql_expr_begrensningskurve_waterfeatures = "OBJTYPE = 'ElvBekkKant' Or OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"

    # Creating a temporary feature of water features from begrensningskurve
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures,
        output_name=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression="""OBJTYPE NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
        output_name=Building_N100.preparation_begrensningskurve__selected_land_features_area__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preparation_begrensningskurve__selected_land_features_area__n100.value,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        output_name=Building_N100.preparation_begrensningskurve__land_features_near_water__n100.value,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.preparation_begrensningskurve__land_features_near_water__n100.value,
        out_feature_class=Building_N100.preparation_begrensningskurve__land_features_buffer__n100.value,
        buffer_distance_or_field="15 Meters",
    )
    print("Buffered land features created")

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        out_feature_class=Building_N100.preparation_begrensningskurve__begrensningskurve_waterfeatures_buffer__n100.value,
        buffer_distance_or_field="45 Meters",
    )
    print("Buffered water features created")

    arcpy.analysis.PairwiseErase(
        in_features=Building_N100.preparation_begrensningskurve__begrensningskurve_waterfeatures_buffer__n100.value,
        erase_features=Building_N100.preparation_begrensningskurve__selected_land_features_area__n100.value,
        out_feature_class=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_1__n100.value,
    )
    print(
        f"Erased 1 completed {Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_1__n100.value} created"
    )

    arcpy.analysis.PairwiseErase(
        in_features=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_1__n100.value,
        erase_features=Building_N100.preparation_begrensningskurve__land_features_buffer__n100.value,
        out_feature_class=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
    )
    print(
        f"Erased 2 completed {Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value} created"
    )
    print("Need to apply better logic for rivers separatly at a later point")
    # Needs to use a different logic for narrow rivers, and instead use the centerline and a small buffer around it which is added to the feature class

    # Adding hierarchy and invisibility fields to the preparation_begrensningskurve__begrensningskurve_buffer_waterfeatures__n100 and setting them to 0
    # Define field information
    fields_to_add = [["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
        expression_type="PYTHON3",
        fields=fields_to_calculate,
    )


###################################### Preparing roads ################################################


@timing_decorator
def preperation_veg_sti():
    """
    Summary:
        This function unsplit a line feature of roads to reduce the number of objects in future processing.

    Details:
        - It takes the input line feature `input_n100.VegSti` and removes any geometric splits.
        - The feature is dissolved based on the fields "subtypekode," "motorvegtype," and "UTTEGNING" to merge segments with the same values in these fields.
    Note:
        - In the future when the inputs makes spatial selections of the features used for context for processing like roads this step is redundant and will instead increase processing time.
    """

    arcpy.UnsplitLine_management(
        in_features=input_n100.VegSti,
        out_feature_class=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        dissolve_field=["subtypekode", "motorvegtype", "UTTEGNING"],
    )


###################################### Adding matrikkel-points (cadastre) for areas which are no longer urban ################################################


@timing_decorator
def adding_matrikkel_as_points():
    """
    Summary:
        This function adds building points from the matrikkel dataset for areas that are no longer considered urban after the generalization of 'ArealdekkeFlate'. It also adds the required fields and values for future analysis.

    Details:
        - Define an SQL expression to select urban areas ('Tettbebyggelse', 'Industriområde', 'BymessigBebyggelse') in the 'ArealdekkeFlate' dataset.
        - Select urban areas from 'ArealdekkeFlate' in both n100 and n50 datasets using the defined SQL expression.
        - Create a buffer of the selected urban areas from n100 to take into consideration that points should not be too close to urban areas.
        - Remove areas from n50 urban areas that intersect with the buffer of n100 urban areas, resulting in areas in n100 that are no longer considered urban.
        - Select matrikkel bygningspunkter based on the new urban selection layer.
        - Transfer the NBR (building type) value to the matrikkel_bygningspunkt dataset by adding a new field "BYGGTYP_NBR" of type LONG and calculating its values from the "bygningstype" field.
    Note:
        - Should consider removing the logic of adding a buffer to the urban areas to prevent points to close to urban areas and instead using urban areas as a barrier feature in future processing.
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


###################################### Transforms hospitals and churches polygons to points ################################################


@timing_decorator
def selecting_grunnriss_for_generalization():
    """
    Summary:
        This function selects building polygons (grunnriss) to be generalized. Smaller polygons and churches or hospitals are excluded, transformed into points, and sent to building point generalization.

    Details:
        - Reclassify hospitals and churches from polygons to 'NBR 729' (other buildings).
        - Select grunnriss that are not churches or hospitals using inverted selection.
        - Select grunnriss that are large enough based on a minimum polygon size of 1500 square meters.
        - Transform small grunnriss features into points by calculating centroids.
        - Select grunnriss features that represent churches and hospitals.
        - Transform selected church and hospital grunnriss features into points by calculating centroids.

    Parameters:
        - Minimum Polygon Size: The minimum size of polygons, in square meters. It currently at **'1500 Meters'**.
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


###################################### FILL ################################################


@timing_decorator
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


if __name__ == "__main__":
    main()
