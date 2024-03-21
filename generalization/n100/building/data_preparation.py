# Importing packages
import arcpy

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator
from custom_tools import custom_arcpy
from constants.n100_constants import N100_SQLResources


@timing_decorator("data_preparation.py")
def main():
    """
    Summary:
        This is the main function of building data preparation, which aims to prepare the data for future building generalization processing.
    """

    environment_setup.main()
    # begrensningskurve_land_and_water_bodies()
    # begrensningskurve_river()
    # merge_begrensningskurve_all_water_features()
    # unsplit_roads()
    matrikkel_and_n50_not_in_urban_areas()
    adding_field_values_to_matrikkel()
    merge_matrikkel_and_n50_points()
    selecting_polygons_not_in_urban_areas()
    reclassifying_polygon_values()
    polygon_selections_based_on_size()


@timing_decorator
def begrensningskurve_land_and_water_bodies():
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

    # Defining the SQL selection expression for water features for begrensningskurve (not river)
    sql_expr_begrensningskurve_waterfeatures_not_river = "OBJTYPE = 'Innsjøkant' Or OBJTYPE = 'InnsjøkantRegulert' Or OBJTYPE = 'Kystkontur'"

    # Creating a temporary feature of water features from begrensningskurve
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures_not_river,
        output_name=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression="""OBJTYPE NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
        output_name=Building_N100.data_preparation___selected_land_features_area___n100_building.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___selected_land_features_area___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.BOUNDARY_TOUCHES.value,
        select_features=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building.value,
        output_name=Building_N100.data_preparation___land_features_near_water___n100_building.value,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.data_preparation___land_features_near_water___n100_building.value,
        out_feature_class=Building_N100.data_preparation___land_features_buffer___n100_building.value,
        buffer_distance_or_field="15 Meters",
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building.value,
        out_feature_class=Building_N100.data_preparation___begrensningskurve_waterfeatures_buffer___n100_building.value,
        buffer_distance_or_field="45 Meters",
    )

    arcpy.analysis.PairwiseErase(
        in_features=Building_N100.data_preparation___begrensningskurve_waterfeatures_buffer___n100_building.value,
        erase_features=Building_N100.data_preparation___selected_land_features_area___n100_building.value,
        out_feature_class=Building_N100.data_preparation___begrensningskurve_buffer_erase_1___n100_building.value,
    )

    arcpy.analysis.PairwiseErase(
        in_features=Building_N100.data_preparation___begrensningskurve_buffer_erase_1___n100_building.value,
        erase_features=Building_N100.data_preparation___land_features_buffer___n100_building.value,
        out_feature_class=Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
    )


@timing_decorator
def begrensningskurve_river():

    sql_expr_begrensningskurve_river_outline = "OBJTYPE = 'ElvBekkKant'"

    # Creating a temporary feature of rivers from begrensningskurve
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_river_outline,
        output_name=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_rivers___n100_building.value,
    )

    # Creating small buffer around begrensningskurve rivers

    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_rivers___n100_building.value,
        out_feature_class=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_rivers_buffer___n100_building.value,
        buffer_distance_or_field="0.1 Meters",
    )


@timing_decorator
def merge_begrensningskurve_all_water_features():

    # Merge begrensningskurve buffers (water bodies and rivers)
    arcpy.management.Merge(
        inputs=[
            Building_N100.data_preperation___waterfeatures_from_begrensningskurve_rivers_buffer___n100_building.value,
            Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
        ],
        output=Building_N100.data_preparation___merged_begrensningskurve_all_waterbodies___n100_building.value,
    )


@timing_decorator
def unsplit_roads():
    """
    Summary:
        This function unsplit a line feature of roads to reduce the number of objects in future processing.

    Details:
        - It takes the input line feature `input_n100.VegSti` and removes any geometric splits.
        - The feature is dissolved based on the fields "subtypekode," "motorvegtype," and "UTTEGNING" to merge segments with the same values in these fields.
    Note:
        - In the future when the inputs make spatial selections of the features used for context for processing like roads this step is redundant and will instead increase processing time.
    """

    arcpy.UnsplitLine_management(
        in_features=input_n100.VegSti,
        out_feature_class=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        dissolve_field=["subtypekode", "motorvegtype", "UTTEGNING"],
    )


@timing_decorator
def matrikkel_and_n50_not_in_urban_areas():
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
        output_name=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
    )

    # Selecting urban areas from n50 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.ArealdekkeFlate,
        expression=urban_areas_sql_expr,
        output_name=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
    )

    # Creating a buffer of the urban selection of n100 to take into account symbology
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        out_feature_class=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        buffer_distance_or_field="50 Meters",
        method="PLANAR",
    )

    # Removing areas from n50 urban areas from the buffer of n100 urban areas resulting in areas in n100 which no longer are urban
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
        erase_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        out_feature_class=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
    )

    # Selecting matrikkel building points based on this new urban selection layer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_other.matrikkel_bygningspunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
        output_name=Building_N100.data_preparation___matrikkel_points___n100_building.value,
    )

    # Selecting n50 so they are not in urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_n50.BygningsPunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        output_name=Building_N100.data_preparation___n50_points___n100_building.value,
        inverted=True,
    )


@timing_decorator
def adding_field_values_to_matrikkel():

    # Adding transferring the NBR value to the matrikkel building points
    arcpy.AddField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field_name="BYGGTYP_NBR",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field="BYGGTYP_NBR",
        expression="!bygningstype!",
    )


@timing_decorator
def merge_matrikkel_and_n50_points():

    # Merge the n50 building point and matrikkel
    arcpy.management.Merge(
        inputs=[
            Building_N100.data_preparation___n50_points___n100_building.value,
            Building_N100.data_preparation___matrikkel_points___n100_building.value,
        ],
        output=Building_N100.data_preperation___matrikkel_n50_points_merged___n100_building.value,
    )


@timing_decorator
def selecting_polygons_not_in_urban_areas():
    print(
        "might want to remove this copyl ater when we have another script for just copying the database"
    )
    # Copy the input data to not modify the original fields.
    arcpy.management.Copy(
        in_data=input_n50.Grunnriss,
        out_data=Building_N100.data_preparation___grunnriss_copy___n100_building.value,
    )

    # Selecting n50 building points based on this new urban selection layer
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_n50.Grunnriss,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
        output_name=Building_N100.data_preparation___n50_polygons___n100_building.value,
    )


@timing_decorator
def reclassifying_polygon_values():
    # Reclassify the hospitals and churches to NBR value 729 ("other buildings" / "andre bygg")
    reclassify_hospital_church_polygons = (
        "def reclassify(nbr):\n"
        "    mapping = {970: 729, 719: 729, 671: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___n50_polygons___n100_building.value,
        field="BYGGTYP_NBR",
        expression="reclassify(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=reclassify_hospital_church_polygons,
    )


def polygon_selections_based_on_size():

    # Selecting only building polygons over 2500 (the rest will be transformed to points due to size)
    grunnriss_minimum_size = 2500
    sql_expression_too_small_polygons = f"Shape_Area < {grunnriss_minimum_size}"
    sql_expression_correct_size_polygons = f"Shape_Area >= {grunnriss_minimum_size}"

    # Polygons over or equal to 2500 Square Meters are selected
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___grunnriss_copy___n100_building.value,
        expression=sql_expression_correct_size_polygons,
        output_name=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
    )

    # Polygons under 2500 Square Meters are selected
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.data_preparation___grunnriss_copy___n100_building.value,
        expression=sql_expression_too_small_polygons,
        output_name=Building_N100.data_preparation___polygons_that_are_too_small___n100_building.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )

    # Transforming small building polygons into points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.data_preparation___polygons_that_are_too_small___n100_building.value,
        out_feature_class=Building_N100.data_preparation___points_created_from_small_polygons___n100_building.value,  # Sent to polygon to point - to get merged as an additional input
    )


if __name__ == "__main__":
    main()
