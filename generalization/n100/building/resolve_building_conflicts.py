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
            "input_layer": Building_N100.preparation_begrensningskurve__selected_waterfeatures_from_begrensningskurve__n100.value,
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

    # Define input barriers
    input_barriers = [
        [
            Building_N100.apply_symbology__veg_sti_selection__n100_lyrx.value,
            "false",
            "10 Meters",
        ],
        [
            Building_N100.apply_symbology__begrensningskurve_selection__n100_lyrx.value,
            "false",
            "5 Meters",
        ],
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=Building_N100.apply_symbology__drawn_polygon_selection__n100_lyrx.value,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="10 meters",
        minimum_size="10 meters",
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


# def resolve_building_conflicts():
#     # Resolve Building Conflicts
#     print("Starting Resolve Building Conflicts 1")
#     arcpy.env.referenceScale = "100000"
#
#     fields_to_calculate_first = [["hierarchy", "1"], ["invisibility", "0"]]
#
#     arcpy.management.CalculateFields(
#         in_table=selection_grunnriss,
#         expression_type="PYTHON3",
#         fields=fields_to_calculate_first,
#     )
#
#     # Defining variables for Resolve Building Conflicts
#     input_buildings = [lyrx_grunnriss]
#
#     input_barriers = [
#         [lyrx_veg_sti, "false", "10 Meters"],
#         [lyrx_begrensnings_kurve, "false", "5 Meters"],
#     ]
#
#     arcpy.cartography.ResolveBuildingConflicts(
#         in_buildings=input_buildings,
#         invisibility_field="invisibility",
#         in_barriers=input_barriers,
#         building_gap="10 meters",
#         minimum_size="10 meters",
#         hierarchy_field="hierarchy",
#     )
#
#     input_barriers_second = [
#         [lyrx_veg_sti, "false", "25 Meters"],
#         [lyrx_begrensnings_kurve, "false", "15 Meters"],
#     ]
#
#     arcpy.cartography.ResolveBuildingConflicts(
#         in_buildings=input_buildings,
#         invisibility_field="invisibility",
#         in_barriers=input_barriers_second,
#         building_gap="10 meters",
#         minimum_size="10 meters",
#         hierarchy_field="hierarchy",
#     )
#
#     fields_to_calculate = [["hierarchy", "0"]]
#
#     arcpy.management.CalculateFields(
#         in_table=selection_grunnriss,
#         expression_type="PYTHON3",
#         fields=fields_to_calculate,
#     )
#
#     code_block_hierarchy = """def determineHierarchy(symbol_val):\n
#         if symbol_val in [1, 2, 3]:\n
#             return 1\n
#         else:\n
#             return None\n"""
#
#     # Then run CalculateField with the new code block
#     arcpy.management.CalculateField(
#         in_table=selection_bygningspunkt,
#         field="hierarchy",
#         expression="determineHierarchy(!symbol_val!)",
#         expression_type="PYTHON3",
#         code_block=code_block_hierarchy,
#     )
#
#     print("Starting Resolve Building Conflicts 2")
#     # Defining variables for Resolve Building Conflicts
#     input_buildings2 = [lyrx_bygningspunkt, lyrx_grunnriss]
#
#     arcpy.cartography.ResolveBuildingConflicts(
#         in_buildings=input_buildings2,
#         invisibility_field="invisibility",
#         in_barriers=input_barriers,
#         building_gap="25 meters",
#         minimum_size="10 meters",
#         hierarchy_field="hierarchy",
#     )
#
#     # Sql expression to bring along bygningspunkt which are kept + church and hospital
#     sql_expression_resolve_building_conflicts = (
#         "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
#     )
#
#     custom_arcpy.select_attribute_and_make_permanent_feature(
#         input_layer=selection_bygningspunkt,
#         expression=sql_expression_resolve_building_conflicts,
#         output_name=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_1__n100.value,
#     )
#
#     # code_block_hierarchy = """def determineHierarchy(symbol_val):\n
#     #     if symbol_val in [1, 2, 3]:\n
#     #         return 0\n
#     #     elif symbol_val == 6:\n
#     #         return None\n
#     #     else:\n
#     #         return None\n"""
#     #
#     # # Then run CalculateField with the new code block
#     # arcpy.management.CalculateField(
#     #     in_table=resolve_building_conflicts_bygningspunkt_result_1,
#     #     field="hierarchy",
#     #     expression="determineHierarchy(!symbol_val!)",
#     #     expression_type="PYTHON3",
#     #     code_block=code_block_hierarchy,
#     # )
#     #
#     # arcpy.management.CalculateFields(
#     #     in_table=selection_grunnriss,
#     #     expression_type="PYTHON3",
#     #     fields=fields_to_calculate,
#     # )
#
#     custom_arcpy.apply_symbology(
#         input_layer=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_1__n100.value,
#         in_symbology_layer=symbology_bygningspunkt,
#         output_name=lyrx_bygningspunkt,
#     )
#
#     input_barriers2 = [
#         [lyrx_veg_sti, "true", "25 Meters"],
#         [lyrx_begrensnings_kurve, "false", "15 Meters"],
#     ]
#
#     print("Starting Resolve Building Conflicts 3")
#     # Defining variables for Resolve Building Conflicts
#     input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
#     arcpy.cartography.ResolveBuildingConflicts(
#         in_buildings=input_buildings3,
#         invisibility_field="invisibility",
#         in_barriers=input_barriers2,
#         building_gap="55 meters",
#         minimum_size="10 meters",
#         hierarchy_field="hierarchy",
#     )
#
#     custom_arcpy.select_attribute_and_make_permanent_feature(
#         input_layer=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_1__n100.value,
#         expression=sql_expression_resolve_building_conflicts,
#         output_name=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_2__n100.value,
#     )
#
#     custom_arcpy.apply_symbology(
#         input_layer=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_2__n100.value,
#         in_symbology_layer=symbology_bygningspunkt,
#         output_name=lyrx_bygningspunkt,
#     )
#
#     input_barriers3 = [
#         [lyrx_veg_sti, "true", "95 Meters"],
#         [lyrx_begrensnings_kurve, "false", "45 Meters"],
#     ]
#
#     print("Starting Resolve Building Conflicts 3")
#     # Defining variables for Resolve Building Conflicts
#     input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
#     arcpy.cartography.ResolveBuildingConflicts(
#         in_buildings=input_buildings3,
#         invisibility_field="invisibility",
#         in_barriers=input_barriers3,
#         building_gap="150 meters",
#         minimum_size="10 meters",
#         hierarchy_field="hierarchy",
#     )
#
#     custom_arcpy.select_attribute_and_make_permanent_feature(
#         input_layer=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_2__n100.value,
#         expression=sql_expression_resolve_building_conflicts,
#         output_name=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_3__n100.value,
#     )
#
#     custom_arcpy.apply_symbology(
#         input_layer=Building_N100.resolve_building_conflicts__conflicts_bygningspunkt_result_3__n100.value,
#         in_symbology_layer=symbology_bygningspunkt,
#         output_name=lyrx_bygningspunkt,
#     )


if __name__ == "__main__":
    main()
