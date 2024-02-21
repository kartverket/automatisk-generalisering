# Importing modules
import arcpy


# Importing custom modules
import config
import input_data.input_n50
from custom_tools import custom_arcpy
from custom_tools.polygon_processor import PolygonProcessor
from input_data import input_symbology

# Importing environment settings
from env_setup import environment_setup

environment_setup.general_setup()

# Importing file manager
from file_manager.n100.file_manager_buildings import Building_N100


def main():
    """
    replace with docstring
    """
    propagate_displacement_building_polygons()
    features_500_m_from_building_polygons()
    apply_symbology_to_layers()
    resolve_building_conflict_building_polygon()
    creating_road_buffer()
    invisible_building_polygons_to_point()
    intersecting_building_polygons_to_point()
    merging_points_invisible_and_intersecting_building_polygons()


def propagate_displacement_building_polygons():
    """
    replace with docstring
    """
    print(
        "REMEMBER TO  SWITCH TO NEW DISPLACEMENT FEATURE AFTER GENERALIZATION OF ROADS"
    )
    print("Propogate displacement ...")
    # Copying layer so no changes are made to the original
    arcpy.management.Copy(
        in_data=Building_N100.join_and_add_fields__building_polygons_final__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
    )

    # Selecting propogate displacement features 500 meters from building polgyons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=config.displacement_feature,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        output_name=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        search_distance="500 Meters",
    )

    # Running propogate displacement for building polygons
    arcpy.cartography.PropagateDisplacement(
        in_features=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        displacement_features=Building_N100.propagate_displacement_building_polygons__displacement_feature_1000_m_from_building_polygon__n100.value,
        adjustment_style="SOLID",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement_building_polygons__building_polygon_pre_propogate_displacement__n100.value,
        out_data=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
    )


def features_500_m_from_building_polygons():
    """
    replace with docstring
    """
    print("Selecting features 500 meter from building polygon ...")
    # Selecting begrensningskurve 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
        search_distance="500 Meters",
    )

    # Selecting roads 500 meters from building polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        output_name=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        search_distance="500 Meters",
    )


def apply_symbology_to_layers():
    """
    replace with docstring
    """
    print("Applying symbology ...")
    # Applying symbology to building polygons
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.grunnriss.value,
        output_name=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
    )
    # Applying symbology to roads
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.features_500_m_from_building_polygons__selected_roads__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.veg_sti.value,
        output_name=Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
    )

    # Applying symbology to begrensningskurve (limiting curve)
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.features_500_m_from_building_polygons__selected_begrensningskurve__n100.value,
        in_symbology_layer=input_symbology.SymbologyN100.begrensnings_kurve.value,
        output_name=Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
    )


def resolve_building_conflict_building_polygon():

    """
    replace with docstring
    """

    # Selecting hospital and churches from n50
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_data.input_n50.BygningsPunkt,
        expression="BYGGTYP_NBR IN (970, 719, 671)",
        output_name=Building_N100.resolve_building_conflict_building_selected_hospital_church_points__n100.value,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=Building_N100.resolve_building_conflict_building_selected_hospital_church_points__n100.value,
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
        in_table=Building_N100.resolve_building_conflict_building_selected_hospital_church_points__n100.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block,
    )
    # Polygon prosessor

    input_building_points = (
        Building_N100.resolve_building_conflict_building_selected_hospital_church_points__n100.value
    )
    output_polygon_feature_class = (
        Building_N100.resolve_building_conflict_building_polygon__hospital_church_polygons__n100.value
    )
    building_symbol_dimensions = {
        1: (145, 145),
        2: (145, 145),
        3: (195, 145),
        4: (40, 40),
        5: (80, 80),
        6: (30, 30),
        7: (45, 45),
        8: (45, 45),
        9: (53, 45),
    }
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    print("Polygon prosessor...")
    polygon_process = PolygonProcessor(
        input_building_points,
        output_polygon_feature_class,
        building_symbol_dimensions,
        symbol_field_name,
        index_field_name,
    )
    polygon_process.run()

    # Resolving Building Conflicts for building polygons
    print("Resolving building conflicts ...")
    # Setting scale to 1: 100 000
    arcpy.env.referenceScale = "100000"

    # Barriers: roads, begrensningskurve, hospital and church squares
    input_barriers = [
        [
            Building_N100.apply_symbology_to_layers__roads__n100__lyrx.value,
            "false",
            "15 Meters",
        ],
        [
            Building_N100.apply_symbology_to_layers__begrensningskurve__n100__lyrx.value,
            "false",
            "15 Meters",
        ],
        [
            Building_N100.resolve_building_conflict_building_polygon__hospital_church_polygons__n100.value,
            "false",
            "15 Meters",
        ],
    ]

    # Resolve Building Polygon with the barriers
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.apply_symbology_to_layers__building_polygon__n100__lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="30 meters",
        minimum_size="1 meters",
    )

    # Copying and assigning new name to layer
    arcpy.management.Copy(
        in_data=Building_N100.propagate_displacement_building_polygons__after_propogate_displacement__n100.value,
        out_data=Building_N100.resolve_building_conflict_building_polygon__after_RBC__n100.value,
    )
    print("Finished")


def invisible_building_polygons_to_point():
    """
    replace with docstring
    """
    print("Transforming polygons marked with invisibility 1 to points ...")

    # Making new feature layer of polygons that is invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflict_building_polygon__after_RBC__n100.value,
        expression="invisibility = 1",
        output_name=Building_N100.invisible_building_polygons_to_point__invisible_polygons__n100.value,
    )

    # Making new feature layer of polygons that is NOT invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflict_building_polygon__after_RBC__n100.value,
        expression="invisibility = 0",
        output_name=Building_N100.invisible_building_polygons_to_point__not_invisible_polygons__n100.value,
    )

    # Polygon to point
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.invisible_building_polygons_to_point__invisible_polygons__n100.value,
        out_feature_class=Building_N100.invisible_building_polygons_to_point__invisible_polygons_to_points__n100.value,
    )

    print("Finished.")


def creating_road_buffer():
    """
    replace with docstring
    """

    print("Creating road buffer ...")
    # Dictionary with SQL queries and their corresponding buffer widths
    sql_queries = {
        "MOTORVEGTYPE = 'Motorveg'": 42.5,
        """ 
        SUBTYPEKODE = 3 
        Or MOTORVEGTYPE = 'Motortrafikkveg' 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Motortrafikkveg') 
        Or (SUBTYPEKODE = 2 And MOTORVEGTYPE = 'Ikke motorveg') 
        Or (SUBTYPEKODE = 4 And MOTORVEGTYPE = 'Ikke motorveg') 
        """: 22.5,
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
        """: 7.5,
    }

    selection_name_base = Building_N100.creating_road_buffer__selection__n100.value
    buffer_name_base = Building_N100.creating_road_buffer__buffers__n100.value

    # List to store the road buffer outputs
    road_buffer_output_names = []

    # Counter for naming the individual road type selections
    counter = 1

    # Loop through the dictionary (Key: SQL query and Value: width) to create buffers around the different roads
    for sql_query, original_width in sql_queries.items():
        selection_output_name = f"{selection_name_base}_{counter}"
        buffer_width = original_width + 15
        buffer_output_name = f"{buffer_name_base}_{buffer_width}m_{counter}"

        # Selecting road types and making new feature layer based on SQL query
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
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
        output=Building_N100.creating_road_buffer__merged_buffers__n100.value,
    )


def intersecting_building_polygons_to_point():

    print("Finding intersecting points... ")

    # Selecting buildings that DO NOT overlap with road buffer layer and will be kept as polygons
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.invisible_building_polygons_to_point__not_invisible_polygons__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.creating_road_buffer__merged_buffers__n100.value,
        inverted=True,
        output_name=Building_N100.intersecting_building_polygons_to_point__final_building_polygons__n100.value,
    )

    # Selecting buildings that overlap with road buffer layer and will be transformed to points
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.invisible_building_polygons_to_point__not_invisible_polygons__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=Building_N100.creating_road_buffer__merged_buffers__n100.value,
        inverted=False,
        output_name=Building_N100.intersecting_building_polygons_to_point__building_polygons_intersecting__n100.value,
    )

    # Transforming these polygons to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.intersecting_building_polygons_to_point__building_polygons_intersecting__n100.value,
        out_feature_class=Building_N100.intersecting_building_polygons_to_point__building_points__n100.value,
    )


def merging_points_invisible_and_intersecting_building_polygons():

    print("Merging points...")
    arcpy.management.Merge(
        inputs=[
            Building_N100.intersecting_building_polygons_to_point__building_points__n100.value,
            Building_N100.invisible_building_polygons_to_point__invisible_polygons_to_points__n100.value,
        ],
        output=Building_N100.merging_points_invisible_and_intersecting_building_polygons__final_building_points__n100.value,
    )


if __name__ == "__main__":
    main()