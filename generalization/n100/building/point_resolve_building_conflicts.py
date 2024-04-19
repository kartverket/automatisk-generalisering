# Importing modules
import arcpy
import time

# Importing custom files
import config
from custom_tools import custom_arcpy
from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology
from custom_tools.polygon_processor import PolygonProcessor
from env_setup import environment_setup

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


iteration_fc = config.resolve_building_conflicts_iteration_feature


@timing_decorator("point_resolve_building_conflicts.py")
def main():
    """
    This script resolves building conflicts, both building polygons and points
    """
    environment_setup.main()
    building_points_to_squares()
    selecting_data_with_area()
    apply_symbology_to_the_layers()
    resolve_building_conflicts_1()
    building_polygons_to_keep_after_rbc_1()
    transforming_invisible_polygons_to_points_and_then_to_squares()
    adding_symbology_to_layers_being_used_for_rbc_2()
    resolve_building_conflicts_2()
    selecting_features_to_be_kept_after_rbc_2()
    transforming_squares_back_to_points()
    merging_building_points()
    assigning_final_names()


@timing_decorator
def building_points_to_squares():

    # Transforms all the building points to squares
    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.building_point_buffer_displacement__displaced_building_points__n100.value,
        output_polygon_feature_class=Building_N100.point_resolve_building_conflicts___transform_points_to_square_polygons___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()


@timing_decorator
def selecting_data_with_area():
    # Selects data in Asker and Oslo only
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN IN ('Asker', 'Oslo')",
        output_name=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
    )

    # List of dictionaries containing parameters for each selection
    selections = [
        {
            "input_layer": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
            "output_name": Building_N100.point_resolve_building_conflicts___building_polygon_selection_rbc___n100_building.value,
        },
        {
            "input_layer": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "output_name": Building_N100.point_resolve_building_conflicts___road_selection_rbc___n100_building.value,
        },
        {
            "input_layer": Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value,
            "output_name": Building_N100.point_resolve_building_conflicts___building_point_selection_rbc___n100_building.value,
        },
        {
            "input_layer": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "output_name": Building_N100.point_resolve_building_conflicts___begrensningskurve_selection_rbc___n100_building.value,
        },
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___transform_points_to_square_polygons___n100_building.value,
            "output_name": Building_N100.point_resolve_building_conflicts___squares_selection_rbc___n100_building.value,
        },
    ]

    # Loop over list and make selections
    for selection in selections:
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=selection["input_layer"],
            overlap_type=custom_arcpy.OverlapType.INTERSECT,
            select_features=Building_N100.point_resolve_building_conflicts___selection_area_resolve_building_conflicts___n100_building.value,
            output_name=selection["output_name"],
        )


@timing_decorator
def apply_symbology_to_the_layers():
    # List of dictionaries containing parameters for each symbology application
    symbology_configs = [
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___building_point_selection_rbc___n100_building.value,
            "in_symbology_layer": SymbologyN100.bygningspunkt.value,
            "output_name": Building_N100.point_resolve_building_conflicts___bygningspunkt_selection___n100_building_lyrx.value,
        },
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___building_polygon_selection_rbc___n100_building.value,
            "in_symbology_layer": SymbologyN100.grunnriss.value,
            "output_name": Building_N100.point_resolve_building_conflicts___grunnriss_selection___n100_building_lyrx.value,
        },
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___road_selection_rbc___n100_building.value,
            "in_symbology_layer": SymbologyN100.veg_sti.value,
            "output_name": Building_N100.point_resolve_building_conflicts___veg_sti_selection___n100_building_lyrx.value,
        },
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___begrensningskurve_selection_rbc___n100_building.value,
            "in_symbology_layer": SymbologyN100.begrensnings_kurve_buffer.value,
            "output_name": Building_N100.point_resolve_building_conflicts___begrensningskurve_selection___n100_building_lyrx.value,
        },
        {
            "input_layer": Building_N100.point_resolve_building_conflicts___squares_selection_rbc___n100_building.value,
            "in_symbology_layer": SymbologyN100.drawn_polygon.value,
            "output_name": Building_N100.point_resolve_building_conflicts___squares_selection___n100_building_lyrx.value,
        },
    ]

    # Loop over the symbology configurations and apply the function
    for symbology_config in symbology_configs:
        custom_arcpy.apply_symbology(
            input_layer=symbology_config["input_layer"],
            in_symbology_layer=symbology_config["in_symbology_layer"],
            output_name=symbology_config["output_name"],
        )


def barriers_for_rbc():

    input_barriers_for_rbc = [
        [
            Building_N100.point_resolve_building_conflicts___veg_sti_selection___n100_building_lyrx.value,
            "false",
            "30 Meters",
        ],
        [
            Building_N100.point_resolve_building_conflicts___begrensningskurve_selection___n100_building_lyrx.value,
            "false",
            "1 Meters",
        ],
        [
            Building_N100.data_preparation___railway_stations_to_polygons_symbology___n100_building_lyrx.value,
            "false",
            "1 Meters",
        ],
        [
            Building_N100.polygon_resolve_building_conflicts___railway_buffer___n100_building_lyrx.value,
            "false",
            "45 Meters",
        ],
    ]

    return input_barriers_for_rbc


@timing_decorator
def resolve_building_conflicts_1():
    arcpy.env.referenceScale = "100000"

    print("Starting Resolve Building Conflicts 1 for drawn polygons")

    # Input point squares and building polygons
    input_buildings_rbc_1 = [
        Building_N100.point_resolve_building_conflicts___grunnriss_selection___n100_building_lyrx.value,
        Building_N100.point_resolve_building_conflicts___squares_selection___n100_building_lyrx.value,
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings_rbc_1,
        invisibility_field="invisibility",
        in_barriers=barriers_for_rbc(),
        building_gap="45 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )

    # Sql expression to select buildingspoints that are visible + church and hospital points
    sql_expression_resolve_building_conflicts = (
        "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___squares_selection_rbc___n100_building.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building.value,
    )


def building_polygons_to_keep_after_rbc_1():

    # Sql expression to keep only building polygons that are visible (0) after the tool has run
    sql_expression_resolve_building_conflicts_polygon = "invisibility = 0"

    # Selecting building polygons that are visible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygon_selection_rbc___n100_building.value,
        expression=sql_expression_resolve_building_conflicts_polygon,
        output_name=Building_N100.point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building.value,
    )


def transforming_invisible_polygons_to_points_and_then_to_squares():

    # Sql expression to keep only building polygons that have invisbility value 1 after the tool has run
    sql_expression_resolve_building_conflicts_polygon = "invisibility = 1"

    # Selecting building polygons that are invisible
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygon_selection_rbc___n100_building.value,
        expression=sql_expression_resolve_building_conflicts_polygon,
        output_name=Building_N100.point_resolve_building_conflicts___building_polygons_invisible_result_1___n100_building.value,
    )

    # Building polygons that are made invisible are transformed to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.point_resolve_building_conflicts___building_polygons_invisible_result_1___n100_building.value,
        out_feature_class=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_result_1___n100_building.value,
        point_location="INSIDE",
    )

    # Transforms all the building points to squares
    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_result_1___n100_building.value,
        output_polygon_feature_class=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()


def adding_symbology_to_layers_being_used_for_rbc_2():

    # Building squares (from points, transformed to squares in the first function) that are kept after rbc 1
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building.value,
        in_symbology_layer=SymbologyN100.drawn_polygon.value,
        output_name=Building_N100.point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building_lyrx.value,
    )
    # Building polygons kept after rbc 1
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building.value,
        in_symbology_layer=SymbologyN100.grunnriss.value,
        output_name=Building_N100.point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building_lyrx.value,
    )
    # Squares made from points, which again comes from invisible building polygons after rbc 1
    custom_arcpy.apply_symbology(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building.value,
        in_symbology_layer=SymbologyN100.drawn_polygon.value,
        output_name=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building_lyrx.value,
    )


def resolve_building_conflicts_2():

    print("Starting resolve building conflicts 2")

    input_buildings_rbc_2 = [
        Building_N100.point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building_lyrx.value,
        Building_N100.point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building_lyrx.value,
        Building_N100.point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building_lyrx.value,
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings_rbc_2,
        invisibility_field="invisibility",
        in_barriers=barriers_for_rbc(),
        building_gap="45 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )


def selecting_features_to_be_kept_after_rbc_2():

    sql_expression_resolve_building_conflicts = (
        "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    )

    # Selecting polygons that are to be kept after rbc 2
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_to_keep_after_rbc1___n100_building.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.point_resolve_building_conflicts___building_polygons_rbc2___n100_building.value,
    )

    # Selecting squares from points
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___squares_to_keep_after_rbc1___n100_building.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.point_resolve_building_conflicts___squares_from_points_rbc2___n100_building.value,
    )
    # Selecting squares from polygons (polygons that were transformed to points and then squares)
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.point_resolve_building_conflicts___building_polygons_to_points_and_then_squares___n100_building.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.point_resolve_building_conflicts___squares_from_polygons_rbc2___n100_building.value,
    )


def transforming_squares_back_to_points():

    # Squares from points are transformed back to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.point_resolve_building_conflicts___squares_from_points_rbc2___n100_building.value,
        out_feature_class=Building_N100.point_resolve_building_conflicts___squares_from_points_transformed_back_to_points___n100_building.value,
        point_location="INSIDE",
    )

    # Squares from polygons are transformed to points
    arcpy.management.FeatureToPoint(
        in_features=Building_N100.point_resolve_building_conflicts___squares_from_polygons_rbc2___n100_building.value,
        out_feature_class=Building_N100.point_resolve_building_conflicts___squares_from_polygons_transformed_to_points___n100_building.value,
        point_location="INSIDE",
    )


def merging_building_points():

    arcpy.management.Merge(
        inputs=[
            Building_N100.point_resolve_building_conflicts___squares_from_points_transformed_back_to_points___n100_building.value,
            Building_N100.point_resolve_building_conflicts___squares_from_polygons_transformed_to_points___n100_building.value,
        ],
        output=Building_N100.point_resolve_building_conflicts___final_points_merged___n100_building.value,
    )


def assigning_final_names():

    arcpy.management.CopyFeatures(
        Building_N100.point_resolve_building_conflicts___building_polygons_rbc2___n100_building.value,
        Building_N100.point_resolve_building_conflicts___building_polygons_final___n100_building.value,
    )

    arcpy.management.CopyFeatures(
        Building_N100.point_resolve_building_conflicts___final_points_merged___n100_building.value,
        Building_N100.point_resolve_building_conflicts___building_points_final___n100_building.value,
    )


if __name__ == "__main__":
    main()
