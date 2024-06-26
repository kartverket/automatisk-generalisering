# Importing packages
import arcpy

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from input_data import input_symbology
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


@timing_decorator
def main():
    """
    Summary:
        This is the main function of building data preparation, which aims to prepare the data for future building generalization processing.
    """

    environment_setup.main()
    begrensningskurve_land_and_water_bodies()
    begrensningskurve_river()
    merge_begrensningskurve_all_water_features()
    unsplit_roads()
    railway_station_points_to_polygons()
    selecting_urban_areas_by_sql()
    adding_matrikkel_points_to_areas_that_are_no_longer_urban_in_n100()
    selecting_n50_points_not_in_urban_areas()
    adding_field_values_to_matrikkel()
    merge_matrikkel_n50_and_touristcabins_points()
    selecting_polygons_not_in_urban_areas()
    reclassifying_polygon_values()
    polygon_selections_based_on_size()


@timing_decorator
def begrensningskurve_land_and_water_bodies():
    """
    Summary:
        Processes land and water body features from the begrensningskurve dataset.

    Details:
        This function extracts non-river water features (e.g., lake edges, coastal contours) from the begrensningskurve dataset and nearby land features.
        It selects these water features based on predefined object types and creates buffers around them.
        Additionally, it selects land features adjacent to the water bodies and creates buffers around them as well.
        Finally, it erases overlapping areas between land and water body buffers to delineate distinct land and water body regions.
    """

    # Defining the SQL selection expression for water features for begrensningskurve (not river)
    sql_expr_begrensningskurve_waterfeatures_not_river = "objtype = 'Innsjøkant' Or objtype = 'InnsjøkantRegulert' Or objtype = 'Kystkontur'"

    # Creating a temporary feature of water features from begrensningskurve
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.BegrensningsKurve,
        expression=sql_expr_begrensningskurve_waterfeatures_not_river,
        output_name=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression="""objtype NOT IN ('ElvBekk', 'Havflate', 'Innsjø', 'InnsjøRegulert')""",
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
        buffer_distance_or_field=f"{N100_Values.building_water_intrusion_distance_m.value} Meters",
    )

    water_feature_buffer_width = (
        N100_Values.building_water_intrusion_distance_m.value + 30
    )
    arcpy.analysis.PairwiseBuffer(
        in_features=Building_N100.data_preperation___waterfeatures_from_begrensningskurve_not_rivers___n100_building.value,
        out_feature_class=Building_N100.data_preparation___begrensningskurve_waterfeatures_buffer___n100_building.value,
        buffer_distance_or_field=f"{water_feature_buffer_width} Meters",
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
    """
    Summary:
        Extracts river features from the begrensningskurve dataset and creates buffers around them.

    Details:
        This function selects river outlines from the begrensningskurve dataset based on a predefined object type ('ElvBekkKant').
        It then creates a small buffer around the selected river features.
        The resulting river outlines and their corresponding buffers are stored as separate feature classes.
    """

    sql_expr_begrensningskurve_river_outline = "objtype = 'ElvBekkKant'"

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
    """
    Summary:
        Merges water feature buffers from begrensningskurve dataset.

    Details:
        This function merges buffers representing water bodies and rivers from the begrensningskurve dataset into a single feature class.
    """

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
        Unsplits road features.

    Details:
        This function unsplit road features in a specified feature class based on certain attributes.
    """

    arcpy.UnsplitLine_management(
        in_features=input_n100.VegSti,
        out_feature_class=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        dissolve_field=["subtypekode", "motorvegtype", "uttegning"],
    )


@timing_decorator
def railway_station_points_to_polygons():
    arcpy.management.Copy(
        in_data=input_n100.JernbaneStasjon,
        out_data=Building_N100.data_preparation___railway_station_points_from_n100___n100_building.value,
    )
    # Railway stations from input data
    railway_stations = input_n100.JernbaneStasjon

    # Adding symbol_val field
    arcpy.AddField_management(
        in_table=railway_stations,
        field_name="symbol_val",
        field_type="SHORT",
    )

    # Assigning symbol_val
    arcpy.CalculateField_management(
        in_table=railway_stations, field="symbol_val", expression="10"
    )

    # Polygon prosessor
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        railway_stations,  # input
        Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,  # output
        N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Applying symbology to polygonprocessed railwaystations
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.railway_station_squares.value,
        output_name=Building_N100.data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx.value,
    )


@timing_decorator
def selecting_urban_areas_by_sql():
    # Defining sql expression to select urban areas

    # Selecting urban areas from n100 using sql expression
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.ArealdekkeFlate,
        expression=N100_SQLResources.urban_areas.value,
        output_name=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
    )

    # Selecting urban areas from n50 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=input_n50.ArealdekkeFlate,
        expression=N100_SQLResources.urban_areas.value,
        output_name=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
    )

    # Creating a buffer of the urban selection of n100 to take into account symbology
    arcpy.PairwiseBuffer_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        out_feature_class=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        buffer_distance_or_field=f"{N100_Values.buffer_clearance_distance_m.value} Meters",
        method="PLANAR",
    )

    # Removing areas from n50 urban areas from the buffer of n100 urban areas resulting in areas in n100 which no longer are urban
    arcpy.PairwiseErase_analysis(
        in_features=Building_N100.data_preparation___urban_area_selection_n50___n100_building.value,
        erase_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        out_feature_class=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
    )


@timing_decorator
def adding_matrikkel_points_to_areas_that_are_no_longer_urban_in_n100():
    # Selecting matrikkel building points in areas that were urban in n50, but are NOT longer urban in n100
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_other.matrikkel_bygningspunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___no_longer_urban_areas___n100_building.value,
        output_name=Building_N100.data_preparation___matrikkel_points___n100_building.value,
    )


@timing_decorator
def selecting_n50_points_not_in_urban_areas():
    # Selecting n50 so they are not in urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_n50.BygningsPunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        output_name=Building_N100.data_preparation___n50_points___n100_building.value,
        inverted=True,
    )

    # Making sure we are not loosing churches or hospitals
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_n50.BygningsPunkt,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.data_preparation___urban_area_selection_n100_buffer___n100_building.value,
        output_name=Building_N100.data_preparation___n50_points_in_urban_areas___n100_building.value,
    )

    sql_church_hospitals = "byggtyp_nbr IN (970, 719, 671)"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___n50_points_in_urban_areas___n100_building.value,
        expression=sql_church_hospitals,
        output_name=Building_N100.data_preparation___churches_and_hospitals_in_urban_areas___n100_building.value,
    )


@timing_decorator
def adding_field_values_to_matrikkel():
    """
    Summary:
        Adds field values to matrikkel building points.

    Details:
        This function adds a new field called 'byggtyp_nbr' of type 'LONG' to the matrikkel building points dataset.
        Then, it copies values from an existing field ('bygningstype') into the newly added 'byggtyp_nbr' field for each record.
    """

    # Adding transferring the NBR value to the matrikkel building points
    arcpy.AddField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field_name="byggtyp_nbr",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field="byggtyp_nbr",
        expression="!bygningstype!",
    )


@timing_decorator
def merge_matrikkel_n50_and_touristcabins_points():
    """
    Summary:
        Merges points from the n50 building dataset, the matrikkel dataset and tourist cabins.

    Details:
        This function combines points from the n50 building dataset, the matrikkel dataset and the tourist cabins into a single feature class.
    """

    # Merge the n50 building point, matrikkel and tourist cabins
    arcpy.management.Merge(
        inputs=[
            Building_N100.data_preparation___n50_points___n100_building.value,
            Building_N100.data_preparation___matrikkel_points___n100_building.value,
            Building_N100.data_preparation___churches_and_hospitals_in_urban_areas___n100_building.value,
            input_n50.TuristHytte,
        ],
        output=Building_N100.data_preperation___matrikkel_n50_touristcabins_points_merged___n100_building.value,
    )


@timing_decorator
def selecting_polygons_not_in_urban_areas():
    """
    Summary:
        Selects polygons not within urban areas.

    Details:
        This function copies the input data to preserve the original fields, ensuring no modifications are made to the original dataset.
        Then, it selects building polygons from the copied data based on their spatial relationship with a layer representing areas no longer classified as urban.
        Polygons that do not intersect with the specified urban area layer are retained and stored as a new feature layer.
    """

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
    """
    Summary:
        Reclassifies the values of hospitals and churches in the specified polygon layer to a new value (729), corresponding to "other buildings".

    Details:
        This function defines a reclassification scheme for hospitals and churches within a polygon layer. Hospitals and churches are identified by their respective values in the 'byggtyp_nbr' field.
        These values (970, 719, and 671) are mapped to a new value (729) representing "other buildings" using a Python dictionary.
        The reclassification is applied to the 'byggtyp_nbr' field.
    """

    # Reclassify the hospitals and churches to NBR value 729 ("other buildings" / "andre bygg")
    reclassify_hospital_church_polygons = (
        "def reclassify(nbr):\n"
        "    mapping = {970: 729, 719: 729, 671: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___n50_polygons___n100_building.value,
        field="byggtyp_nbr",
        expression="reclassify(!byggtyp_nbr!)",
        expression_type="PYTHON3",
        code_block=reclassify_hospital_church_polygons,
    )


@timing_decorator
def polygon_selections_based_on_size():
    """
    Summary:
        Selects building polygons based on their size and converts small polygons to points.

    Details:
        This function performs a selection on building polygons based on their size. It first defines a minimum size threshold of 2500 square units.
        Then, it selects polygons that meet this threshold (polygons over or equal to 2500 square meters) and those that do not (polygons under 2500 square meters).
        The selected polygons over the minimum size are retained for further processing, while the smaller polygons are transformed into points.
    """

    # Selecting only building polygons over 2500 (the rest will be transformed to points due to size)
    sql_expression_too_small_polygons = (
        f"Shape_Area < {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )
    sql_expression_correct_size_polygons = (
        f"Shape_Area >= {N100_Values.minimum_selection_building_polygon_size_m2.value}"
    )

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
