# Importing modules
import arcpy

# Importing custom modules
import config
import input_data.input_n50
from custom_tools import custom_arcpy
from custom_tools.polygon_processor import PolygonProcessor
from input_data import input_symbology
from constants.n100_constants import N100Symbology

# Importing environment settings
from env_setup import environment_setup

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("polygon_propogate_displacement.py")
def main():
    """
    Summary:
        This script first propagates displacement for building polygons to ensure their alignment with roads
        at a scale of 1:100,000. Next, it resolves conflicts among all building polygons in Norway,
        considering various barriers such as roads, waterfeatures, hospital and churches, ensuring proper placement and scaling.

        Following conflict resolution, the script transforms building polygons marked as invisible into points.
        It also identifies visible building polygons that intersect roads and transforms them into points.
        Building polygons that do not intersect roads remain unchanged.

        The final output consists of two layers: a building polygon layer and a building point layer.

    Details:

        1. `propagate_displacement_building_polygons`:
            Copies building polygons and propagates displacement based on nearby generalized road features, moving the buildings.

        2. `features_500_m_from_building_polygons`:
            Identifies and selects water features and roads within a 500-meter radius of building polygons, making sure only necessary data is processed.

        3. `apply_symbology_to_layers`:
            Applies N100 symbology to building polygons, roads, and water features

        4. `resolve_building_conflict_building_polygon`:
            Resolves conflicts among building polygons, using roads, water features, hospital and churches as barriers

        5. `creating_road_buffer`:
            Generates buffer zones around various road types based on the thickness of their symbology

        6. `invisible_building_polygons_to_point`:
            Converts invisible building polygons into points

        7. `intersecting_building_polygons_to_point`:
            Identifies intersecting building polygons and converts them into points.
            Building polygons that are not made invisible by the previous function,
            nor intersecting roads will be kept as they are.

        8. `merging_invisible_intersecting_points`:
            Combines points derived from invisible and intersecting building polygons.
    """

    environment_setup.main()
    propagate_displacement_building_polygons()
    features_500_m_from_building_polygons()
    apply_symbology_to_layers()
    resolve_building_conflict_building_polygon()
    creating_road_buffer()
    invisible_building_polygons_to_point()
    intersecting_building_polygons_to_point()
    merging_invisible_intersecting_points()
    removing_small_building_polygons()
    small_building_polygons_to_points()


@timing_decorator
def propagate_displacement_building_polygons():
    """
    Summary:
        Selects displacement features located within a 500-meter radius from building polygons
        and propagates displacement for the building polygons.

    Details:
        This function selects displacement features within a specified distance (500 meters) from the building polygons
        and applies a displacement operation to ensure the building polygons align appropriately with surrounding features,
        such as roads or other structures.
    """

    print("MAKE SURE TO SWITCH TO NEW DISPLACEMENT FEATURE (AFTER ROAD GENERALIZATION")

    print("Propogate displacement ...")
    # Copying layer so no changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.simplify_polygons___final___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
    )

    # Selecting propogate displacement features 500 meters from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___displacement_feature_1000m_from_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        displacement_features=Building_N100.polygon_propogate_displacement___displacement_feature_1000m_from_polygon___n100_building.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___pre_displacement___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___after_displacement___n100_building.value,
    )


@timing_decorator
def features_500_m_from_building_polygons():
    """
    Summary:
        Selects waterfeatures and roads located 500 meters from building polygons.

    Details:
        **`Search distance is 500 Meters`**

    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preperation___selected_waterfeatures_from_begrensningskurve___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___after_displacement___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.data_preparation___unsplit_veg_sti___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.polygon_propogate_displacement___after_displacement___n100_building.value,
        output_name=Building_N100.polygon_propogate_displacement___roads_500m_from_displaced_polygon___n100_building.value,
        search_distance="500 Meters",
    )


@timing_decorator
def apply_symbology_to_layers():
    """
    Summary:
        Applies symbology (lyrx files) to building polygons, roads, and water barriers.

    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___after_displacement___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.grunnriss.value,
        output_name=Building_N100.polygon_propogate_displacement___building_polygon___n100_building_lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___roads_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.veg_sti.value,
        output_name=Building_N100.polygon_propogate_displacement___roads___n100_building_lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.begrensnings_kurve_line.value,
        output_name=Building_N100.polygon_propogate_displacement___begrensningskurve___n100_building_lyrx.value,
    )


@timing_decorator
def resolve_building_conflict_building_polygon():
    """
    Summary:
        Resolves conflicts among building polygons considering roads, water features, hospitals, and churches as barriers.

    Details:
        This function resolves conflicts among building polygons by taking into account various barriers such as roads,
        water features, hospitals, and churches. To incorporate hospital and church points as barriers, these points are first
        transformed into polygons using the dimensions of their symbology.
    """

    # Selecting hospital and churches from n50
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_data.input_n50.BygningsPunkt,
        expression="BYGGTYP_NBR IN (970, 719, 671)",
        output_name=Building_N100.polygon_propogate_displacement___hospital_church_points___n100_building.value,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=Building_N100.polygon_propogate_displacement___hospital_church_points___n100_building.value,
        field_name="symbol_val",
        field_type="LONG",
    )

    # Calculating symbol val
    code_block = (
        "def determineVal(nbr):\n"
        "    if nbr == 970:\n"
        "        return 1\n"
        "    elif nbr == 719:\n"
        "        return 2\n"
        "    elif nbr == 671:\n"
        "        return 3\n"
        "    elif nbr in [111,112,121,122,131,133,135,136,141,142,143,144,145,146,159,161,162,171,199,524]:\n"
        "        return 4\n"
        "    elif nbr in [113,123,124,163]:\n"
        "        return 5\n"
        "    elif nbr in [151,152,211,212,214,221,231,232,233,243,244,311,312,313,321,322,323,330,411,412,415,416,4131,441,521,522,523,529,532,621,641,642,643,651,652,653,661,662,672,673,674,675,731,821,822,319,329,449,219,659,239,439,223,611,649,229,419,429,623,655,664,679,824]:\n"
        "        return 6\n"
        "    elif nbr in [531,612,613,614,615,616,619,629,819,829,669,533,539]:\n"
        "        return 7\n"
        "    elif nbr in [721,722,723,732,739,729]:\n"
        "        return 8\n"
        "    elif nbr in [172,181,182,183,193,216,241,245,248,654,999,249,840]:\n"
        "        return 9\n"
        "    else:\n"
        "        return -99\n"
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.polygon_propogate_displacement___hospital_church_points___n100_building.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block,
    )
    # Polygon prosessor
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        Building_N100.polygon_propogate_displacement___hospital_church_points___n100_building.value,  # input
        Building_N100.polygon_propogate_displacement___hospital_church_squares___n100_building.value,  # output
        N100Symbology.building_symbol_dimensions.value,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Applying symbology to polygonprocessed hospital and churches
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.polygon_propogate_displacement___hospital_church_squares___n100_building.value,
        in_symbology_layer=input_symbology.SymbologyN100.grunnriss.value,
        output_name=Building_N100.polygon_propogate_displacement___polygonprocessor_symbology___n100_building_lyrx.value,
    )

    # Resolving Building Conflicts for building polygons
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    # Barriers: roads, begrensningskurve, hospital and church squares
    input_barriers = [
        [
            Building_N100.polygon_propogate_displacement___roads___n100_building_lyrx.value,
            "false",
            "45 Meters",
        ],
        [
            Building_N100.polygon_propogate_displacement___begrensningskurve___n100_building_lyrx.value,
            "false",
            "45 Meters",
        ],
        [
            Building_N100.polygon_propogate_displacement___polygonprocessor_symbology___n100_building_lyrx.value,
            "false",
            "45 Meters",
        ],
    ]

    # Resolve Building Conflict with building polygons and barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.polygon_propogate_displacement___building_polygon___n100_building_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="45 meters",
        minimum_size="1 meters",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.polygon_propogate_displacement___after_displacement___n100_building.value,
        out_data=Building_N100.polygon_propogate_displacement___after_rbc___n100_building.value,
    )
    print("Finished")


@timing_decorator
def creating_road_buffer():
    """
    Summary:
        Creates buffers around different types of roads based on specified criteria, and merges all the buffers into one single layer.

    Details:
        This function generates buffers around various types of roads by applying predefined SQL queries
        to select specific road types and associated buffer widths. Each SQL query corresponds to a particular
        road type, and the resulting buffers provide spatial context and aid in urban infrastructure analysis.
    """

    print("Creating road buffer ...")
    # Dictionary with SQL queries and their corresponding buffer widths
    sql_queries = {
        "MOTORVEGTYPE = 'Motorveg'": 43,
        """ 
        SUBTYPEKODE = 3 
        Or MOTORVEGTYPE = 'Motortrafikkveg' 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Motortrafikkveg') 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Ikke motorveg') 
        Or (SUBTYPEKODE = 4 And MOTORVEGTYPE = 'Ikke motorveg') 
        """: 23,
        """
        SUBTYPEKODE = 1
        Or SUBTYPEKODE = 5
        Or SUBTYPEKODE = 6
        Or SUBTYPEKODE = 9
        """: 20,
        """
        SUBTYPEKODE = 7
        Or SUBTYPEKODE = 8
        Or SUBTYPEKODE = 10
        Or SUBTYPEKODE =11
        """: 8,
    }

    selection_name_base = (
        Building_N100.polygon_propogate_displacement___road_buffer_selection___n100_building.value
    )
    buffer_name_base = (
        Building_N100.polygon_propogate_displacement___road_buffers___n100_building.value
    )

    # List to store the road buffer outputs
    road_buffer_output_names = []

    # Counter for naming the individual road type selections
    counter = 1

    # Loop through the dictionary (Key: SQL query and Value: width) to create buffers around the different roads
    for sql_query, original_width in sql_queries.items():
        selection_output_name = f"{selection_name_base}_{counter}"
        buffer_width = original_width + 15
        buffer_output_name = f"{buffer_name_base}_{buffer_width}m_{counter}"

        print(selection_output_name)
        print(buffer_output_name)

        # Selecting road types and making new feature layer based on SQL query
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Building_N100.data_preparation___unsplit_veg_sti___n100_building.value,
            expression=sql_query,
            output_name=selection_output_name,
        )

        # Making a buffer around each road type with specified width + 15 meters
        arcpy.analysis.PairwiseBuffer(
            in_features=selection_output_name,
            out_feature_class=buffer_output_name,
            buffer_distance_or_field=f"{buffer_width} Meters",
        )

        # Add buffer output names to list
        road_buffer_output_names.append(buffer_output_name)
        # Increase the counter by 1
        counter += 1

    # Merge all buffers into a single feature class
    arcpy.management.Merge(
        inputs=road_buffer_output_names,
        output=Building_N100.polygon_propogate_displacement___merged_road_buffers___n100_building.value,
    )


@timing_decorator
def invisible_building_polygons_to_point():
    """
    Summary:
        Converts invisible building polygons to points and separates them from non-invisible polygons.

    Details:
        This function identifies building polygons marked as invisible (invisibility = 1) within the building
        polygon layer resulting from the conflict resolution process. It creates a new feature layer containing
        these invisible polygons and another layer for non-invisible polygons (invisibility = 0). Subsequently,
        the invisible polygons are transformed into points to represent their locations more accurately. The final
        output consists of two layers: one with invisible polygons transformed into points and another with non-invisible
        polygons.
    """
    print("Transforming polygons marked with invisibility 1 to points ...")

    # Making new feature layer of polygons that is invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___after_rbc___n100_building.value,
        expression="invisibility = 1",
        output_name=Building_N100.polygon_propogate_displacement___invisible_polygons_after_rbc___n100_building.value,
    )

    # Making new feature layer of polygons that is NOT invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___after_rbc___n100_building.value,
        expression="invisibility = 0",
        output_name=Building_N100.polygon_propogate_displacement___not_invisible_polygons_after_rbc___n100_building.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_propogate_displacement___invisible_polygons_after_rbc___n100_building.value,
        out_feature_class=Building_N100.polygon_propogate_displacement___invisible_polygons_to_points___n100_building.value,
    )

    print("Finished.")


@timing_decorator
def intersecting_building_polygons_to_point():
    """
    Summary:
        Identifies ibuilding polygons that intersects road and converts them into points.

    Details:
        This function first identifies building polygons that intersect with the road buffer layer and selects
        them for transformation into points. It performs two selection operations based on intersection with
        the road buffer layer: one for buildings that do not overlap (inverted=True) and will be retained as
        polygons, and another for buildings that do overlap (inverted=False) and will be transformed into points.
    """
    print("Finding intersecting points... ")

    # Selecting buildings that DO NOT overlap with road buffer layer and will be kept as polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.polygon_propogate_displacement___merged_road_buffers___n100_building.value,
        inverted=True,  # Inverted
        output_name=Building_N100.polygon_propogate_displacement___building_polygons_not_invisible_not_intersecting___n100_building.value,
    )

    # Selecting buildings that overlap with road buffer layer and will be transformed to points
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___not_invisible_polygons_after_rbc___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.polygon_propogate_displacement___merged_road_buffers___n100_building.value,
        inverted=False,
        output_name=Building_N100.polygon_propogate_displacement___building_polygons_intersecting_road___n100_building.value,
    )

    # Transforming these polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_propogate_displacement___building_polygons_intersecting_road___n100_building.value,
        out_feature_class=Building_N100.polygon_propogate_displacement___intersecting_polygons_to_points___n100_building.value,
    )


@timing_decorator
def merging_invisible_intersecting_points():
    """
    Summary:
        Merges points representing intersecting building polygons and invisible polygons.

    Details:
        This function merges two sets of points: one set representing building polygons that intersect with roads,
        and another set representing invisible building polygons transformed into points. It combines these points
        into a single feature class.
    """
    print("Merging points...")
    arcpy.management.Merge(
        inputs=[
            Building_N100.polygon_propogate_displacement___intersecting_polygons_to_points___n100_building.value,
            Building_N100.polygon_propogate_displacement___invisible_polygons_to_points___n100_building.value,
        ],
        output=Building_N100.polygon_propogate_displacement___final_merged_points___n100_building.value,
    )


@timing_decorator
def removing_small_building_polygons():
    """
    Summary:
        Removes small building polygons from the input layer based on a specified area threshold.

    Details:
        This function removes building polygons from the input layer that have a shape area smaller than
        a specified threshold (3200 square meters).
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area > 3200",
        output_name=Building_N100.polygon_propogate_displacement___building_polygons_final___n100_building.value,
    )


def small_building_polygons_to_points():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.polygon_propogate_displacement___building_polygons_not_invisible_not_intersecting___n100_building.value,
        expression="Shape_Area < 3200",
        output_name=Building_N100.polygon_propogate_displacement___small_building_polygons___n100_building.value,
    )

    # Transforming small polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.polygon_propogate_displacement___small_building_polygons___n100_building.value,
        out_feature_class=Building_N100.polygon_propogate_displacement___small_building_polygons_to_point___n100_building.value,
    )


if __name__ == "__main__":
    main()
