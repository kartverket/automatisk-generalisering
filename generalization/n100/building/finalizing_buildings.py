# Importing modules
import arcpy

# Importing custom files
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from file_manager.n100.file_manager_buildings import Building_N100


# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


def main():
    environment_setup.main()
    removing_points_in_and_close_to_urban_areas()
    selecting_all_tourist_cabins()
    building_polygons_to_line()
    selecting_hospital_and_churches_for_pictogram_featureclass()
    assigning_final_file_names()


@timing_decorator
def removing_points_in_and_close_to_urban_areas():
    """
    Summary:
        Selects and processes building points based on their proximity to urban areas, keeping those further away and merging specific points.
    """
    # Defining sql expression to select urban areas
    urban_areas_sql_expr = "objtype = 'Tettbebyggelse' Or objtype = 'Industriområde' Or objtype = 'BymessigBebyggelse'"

    # Selecting urban areas from n100 using sql expression
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        expression=urban_areas_sql_expr,
        output_name=Building_N100.finalizing_buildings___urban_areas___n100_building.value,
    )

    # Selecting building points that are further away than 50 Meters from urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___merging_final_points___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.finalizing_buildings___urban_areas___n100_building.value,
        search_distance="50 Meters",
        inverted=True,
        output_name=Building_N100.finalizing_buildings___points_not_close_to_urban_areas___n100_building.value,
    )

    # Selecting building points that are CLOSE to urban areas
    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Building_N100.removing_overlapping_polygons_and_points___merging_final_points___n100_building.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
        select_features=Building_N100.finalizing_buildings___urban_areas___n100_building.value,
        search_distance="50 Meters",
        output_name=Building_N100.finalizing_buildings___points_too_close_to_urban_areas___n100_building.value,
    )

    # Selecting hospital and churches and tourist huts - to merge back in with the points further than 50 Merers away from urban areas
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___points_too_close_to_urban_areas___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671, 956)",
        output_name=Building_N100.finalizing_buildings___selecting_hospital_and_churches_in_urban_areas___n100_building.value,
    )

    # Merging hospital and churches in urban areas with points that are further away from urban areas than 50 Meters
    arcpy.management.Merge(
        inputs=[
            Building_N100.finalizing_buildings___selecting_hospital_and_churches_in_urban_areas___n100_building.value,
            Building_N100.finalizing_buildings___points_not_close_to_urban_areas___n100_building.value,
        ],
        output=Building_N100.finalizing_buildings___all_points_not_in_urban_areas___n100_building.value,
    )


@timing_decorator
def selecting_all_tourist_cabins():
    """
    Summary:
        Selects building points categorized as tourist cabins and distinguishes them from other building points.
    """
    selecting_tourist_cabins = "byggtyp_nbr = 956"

    # Selecting all building points categorized as tourist cabins
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___all_points_not_in_urban_areas___n100_building.value,
        expression=selecting_tourist_cabins,
        output_name=Building_N100.finalizing_buildings___tourist_cabins___n100_building.value,
    )
    # Selecting all other building points (not tourist cabins)
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___all_points_not_in_urban_areas___n100_building.value,
        expression=selecting_tourist_cabins,
        output_name=Building_N100.finalizing_buildings___all_points_except_tourist_cabins___n100_building.value,
        inverted=True,
    )


def building_polygons_to_line():
    """
    Summary:
        Converts building polygons to lines
    """
    arcpy.management.PolygonToLine(
        in_features=Building_N100.removing_overlapping_polygons_and_points___building_polygons_not_intersecting_church_hospitals___n100_building.value,
        out_feature_class=Building_N100.finalizing_buildings___polygon_to_line___n100_building.value,
        neighbor_option="IDENTIFY_NEIGHBORS",
    )

    arcpy.analysis.SpatialJoin(
        target_features=Building_N100.finalizing_buildings___polygon_to_line___n100_building.value,
        join_features=Building_N100.removing_overlapping_polygons_and_points___building_polygons_not_intersecting_church_hospitals___n100_building.value,
        out_feature_class=Building_N100.finalizing_buildings___polygon_to_line_joined_fields___n100_building.value,
        match_option="SHARE_A_LINE_SEGMENT_WITH",
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.finalizing_buildings___polygon_to_line_joined_fields___n100_building.value,
        field="objtype",
        expression='"Takkant"',
        expression_type="PYTHON3",
    )


def selecting_hospital_and_churches_for_pictogram_featureclass():
    """
    Summary:
        Selects building points categorized as hospitals or churches for inclusion in a pictogram feature class.
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.finalizing_buildings___all_points_except_tourist_cabins___n100_building.value,
        expression="byggtyp_nbr IN (970, 719, 671)",
        output_name=Building_N100.finalizing_buildings___hospitals_and_churches_pictogram___n100_building.value,
    )


@timing_decorator
def assigning_final_file_names():
    """
    Summary:
        Copies final feature classes to their respective output file locations in the "final_outputs.gdb"
    """
    arcpy.management.CopyFeatures(
        Building_N100.finalizing_buildings___tourist_cabins___n100_building.value,
        Building_N100.TuristHytte.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.finalizing_buildings___all_points_except_tourist_cabins___n100_building.value,
        Building_N100.BygningsPunkt.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.removing_overlapping_polygons_and_points___building_polygons_not_intersecting_church_hospitals___n100_building.value,
        Building_N100.Grunnriss.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.finalizing_buildings___polygon_to_line_joined_fields___n100_building.value,
        Building_N100.OmrissLinje.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.finalizing_buildings___hospitals_and_churches_pictogram___n100_building.value,
        Building_N100.Piktogram.value,
    )


if __name__ == "__main__":
    main()
