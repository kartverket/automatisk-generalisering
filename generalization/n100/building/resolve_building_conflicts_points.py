# Importing modules
import arcpy
import time

# Importing custom files
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


iteration_fc = config.resolve_building_conflicts_iteration_feature


def main():
    """
    This script resolves building conflicts, both building polygons and points
    """
    environment_setup.main()
    rbc_selection()
    apply_symbology()
    resolve_building_conflicts()


def rbc_selection():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN = 'Asker'",
        output_name=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
    )

    # List of dictionaries containing parameters for each selection
    selections = [
        {
            "input_layer": Building_N100.simplify_polygons___final___n100_building.value,
            "output_name": Building_N100.rbc_selection__grunnriss_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.data_preparation___unsplit_roads___n100_building.value,
            "output_name": Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
            "output_name": Building_N100.rbc_selection__bygningspunkt_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.data_preparation___begrensningskurve_buffer_erase_2___n100_building.value,
            "output_name": Building_N100.rbc_selection__begrensningskurve_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.points_to_squares___transform_points_to_square_polygons___n100_building.value,
            "output_name": Building_N100.rbc_selection__drawn_polygon_selection_rbc__n100.value,
        },
    ]

    # Loop over the selections and apply the function
    for selection in selections:
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=selection["input_layer"],
            overlap_type=custom_arcpy.OverlapType.INTERSECT,
            select_features=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
            output_name=selection["output_name"],
        )


def apply_symbology():
    # List of dictionaries containing parameters for each symbology application
    symbology_configs = [
        {
            "input_layer": Building_N100.rbc_selection__bygningspunkt_selection_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.bygningspunkt.value,
            "output_name": Building_N100.apply_symbology__bygningspunkt_selection__n100_lyrx.value,
        },
        {
            "input_layer": Building_N100.rbc_selection__grunnriss_selection_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.grunnriss.value,
            "output_name": Building_N100.apply_symbology__grunnriss_selection__n100_lyrx.value,
        },
        {
            "input_layer": Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.veg_sti.value,
            "output_name": Building_N100.apply_symbology__veg_sti_selection__n100_lyrx.value,
        },
        {
            "input_layer": Building_N100.rbc_selection__begrensningskurve_selection_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.begrensnings_kurve_buffer.value,
            "output_name": Building_N100.apply_symbology__begrensningskurve_selection__n100_lyrx.value,
        },
        {
            "input_layer": Building_N100.rbc_selection__drawn_polygon_selection_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.drawn_polygon.value,
            "output_name": Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
        },
    ]

    # Loop over the symbology configurations and apply the function
    for symbology_config in symbology_configs:
        custom_arcpy.apply_symbology(
            input_layer=symbology_config["input_layer"],
            in_symbology_layer=symbology_config["in_symbology_layer"],
            output_name=symbology_config["output_name"],
        )


def resolve_building_conflicts():
    arcpy.env.referenceScale = "100000"

    print("Starting Resolve Building Conflicts 1 for drawn polygons")
    # Define input barriers

    input_barriers_1 = [  # NB: confusing name?? input_barriers_1
        [
            Building_N100.apply_symbology__veg_sti_selection__n100_lyrx.value,
            "false",
            "30 Meters",
        ],
        [
            Building_N100.apply_symbology__begrensningskurve_selection__n100_lyrx.value,
            "false",
            "1 Meters",
        ],
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers_1,
        building_gap="45 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )

    # Sql expression to bring along bygningspunkt which are kept + church and hospital
    sql_expression_resolve_building_conflicts = (
        "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.rbc_selection__drawn_polygon_selection_rbc__n100.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.resolve_building_conflicts__drawn_polygons_result_1__n100.value,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.resolve_building_conflicts__drawn_polygons_result_1__n100.value,
        in_symbology_layer=Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
        output_name=Building_N100.resolve_building_conflicts__drawn_polygon_RBC_result_1__n100_lyrx.value,
    )

    arcpy.management.FeatureToPoint(
        in_features=Building_N100.resolve_building_conflicts__drawn_polygons_result_1__n100.value,
        out_feature_class=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100.value,
        point_location="INSIDE",
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100.value,
        in_symbology_layer=SymbologyN100.bygningspunkt.value,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx.value,
    )

    print("Starting resolve building conflicts 2")

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers_1,
        building_gap="45 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100.value,
        in_symbology_layer=SymbologyN100.bygningspunkt.value,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_final__n100_lyrx.value,
    )


if __name__ == "__main__":
    main()
