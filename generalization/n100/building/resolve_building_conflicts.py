import arcpy
import os
import time

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import setup_directory_structure


# Importing environment
environment_setup.general_setup()

iteration_fc = config.resolve_building_conflicts_iteration_feature


def main():
    # Start timing
    start_time = time.time()
    rbc_selection()
    apply_symbology()
    resolve_building_conflicts()

    # End timing
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as string
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(hours), int(minutes), seconds
    )

    print(f"The script took {time_str} to complete.")


def rbc_selection():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression="NAVN = 'Asker'",
        output_name=Building_N100.rbc_selection__selection_area_resolve_building_conflicts__n100.value,
    )

    # List of dictionaries containing parameters for each selection
    selections = [
        {
            "input_layer": Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value,
            "output_name": Building_N100.rbc_selection__grunnriss_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.preperation_veg_sti__unsplit_veg_sti__n100.value,
            "output_name": Building_N100.rbc_selection__veg_sti_selection_rbc_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
            "output_name": Building_N100.rbc_selection__bygningspunkt_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.preparation_begrensningskurve__begrensningskurve_buffer_erase_2__n100.value,
            "output_name": Building_N100.rbc_selection__begrensningskurve_selection_rbc__n100.value,
        },
        {
            "input_layer": Building_N100.points_to_polygon__transform_points_to_square_polygons__n100.value,
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
            "in_symbology_layer": SymbologyN100.begrensnings_kurve.value,
            "output_name": Building_N100.apply_symbology__begrensningskurve_selection__n100_lyrx.value,
        },
        {
            "input_layer": Building_N100.rbc_selection__drawn_polygon_selection_rbc__n100.value,
            "in_symbology_layer": SymbologyN100.drawn_plygon.value,
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

    input_barriers_1 = [
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
        building_gap="15 meters",
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
        building_gap="15 meters",
        minimum_size="1 meters",
        hierarchy_field="hierarchy",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_1__n100.value,
        expression=sql_expression_resolve_building_conflicts,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_result_2__n100.value,
    )

    custom_arcpy.apply_symbology(
        input_layer=Building_N100.resolve_building_conflicts__building_points_RBC_result_2__n100.value,
        in_symbology_layer=SymbologyN100.bygningspunkt.value,
        output_name=Building_N100.resolve_building_conflicts__building_points_RBC_result_2__n100_lyrx.value,
    )

    # print("Starting Resolve Building Conflicts 2 for drawn polygons")
    # # Define input barriers
    #
    # input_barriers_2 = [
    #     [
    #         Building_N100.apply_symbology__veg_sti_selection__n100_lyrx.value,
    #         "false",
    #         "45 Meters",
    #     ],
    #     [
    #         Building_N100.apply_symbology__begrensningskurve_selection__n100_lyrx.value,
    #         "false",
    #         "25 Meters",
    #     ],
    # ]
    #
    # arcpy.cartography.ResolveBuildingConflicts(
    #     in_buildings=Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
    #     invisibility_field="invisibility",
    #     in_barriers=input_barriers_2,
    #     building_gap="45 meters",
    #     minimum_size="1 meters",
    #     hierarchy_field="hierarchy",
    # )
    #
    # sql_expression_resolve_building_conflicts = (
    #     "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    # )
    #
    # custom_arcpy.select_attribute_and_make_permanent_feature(
    #     input_layer=Building_N100.resolve_building_conflicts__drawn_polygons_result_1__n100.value,
    #     expression=sql_expression_resolve_building_conflicts,
    #     output_name=Building_N100.resolve_building_conflicts__drawn_polygons_result_2__n100.value,
    # )
    #
    # custom_arcpy.apply_symbology(
    #     input_layer=Building_N100.resolve_building_conflicts__drawn_polygons_result_2__n100.value,
    #     in_symbology_layer=Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
    #     output_name=Building_N100.resolve_building_conflicts__drawn_polygon_RBC_result_2__n100_lyrx.value,
    # )


if __name__ == "__main__":
    main()
