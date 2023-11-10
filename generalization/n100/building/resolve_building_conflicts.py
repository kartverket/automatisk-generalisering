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
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Start timing
start_time = time.time()

# Importing environment
environment_setup.general_setup()

iteration_fc = config.resolve_building_conflicts_iteration_feature


def main():
    # creating_append_layers()
    # pre_calculation()
    # iterate_through_selections()
    # rbc_iteration()
    resolve_building_conflicts()


def creating_append_layers():
    # Define the name for the new, empty feature class
    byggningspunkt_append = "looping_rbc_results_bygningspunkt"
    grunriss_append = "looping_rbc_results_grunnriss"

    # Create a new feature class using the original one as a template
    arcpy.CreateFeatureclass_management(
        out_path=config.default_project_workspace,
        out_name=byggningspunkt_append,
        template=TemporaryFiles.bygningspunkt_pre_symbology.value,
    )

    arcpy.CreateFeatureclass_management(
        out_path=config.default_project_workspace,
        out_name=grunriss_append,
        template=TemporaryFiles.simplified_grunnriss_n100.value,
    )


def pre_calculation():
    fields_to_calculate_first = [["hierarchy", "1"], ["invisibility", "0"]]

    arcpy.management.CalculateFields(
        in_table=TemporaryFiles.simplified_grunnriss_n100.value,
        expression_type="PYTHON3",
        fields=fields_to_calculate_first,
    )

    code_block_hierarchy = """def determineHierarchy(symbol_val):\n
        if symbol_val in [1, 2, 3]:\n
            return 1\n
        else:\n
            return None\n"""

    # Then run CalculateField with the new code block
    arcpy.management.CalculateField(
        in_table=TemporaryFiles.bygningspunkt_pre_symbology.value,
        field="hierarchy",
        expression="determineHierarchy(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_hierarchy,
    )


def iterate_through_selections():
    # Define your initial data
    input_polygon_layer = iteration_fc
    id_field = "OID"
    unique_ids = [
        row[0] for row in arcpy.da.SearchCursor(input_polygon_layer, [id_field])
    ]

    # Loop through each unique ID to perform the selections and apply symbology
    for unique_id in unique_ids:
        # Construct names for selection outputs
        selection_grunnriss = f"grunnriss_selection_pre_rbc_{unique_id}"
        selection_veg_sti = f"veg_sti_selection_pre_rbc_{unique_id}"
        selection_bygningspunkt = f"bygningspunkt_selection_pre_rbc_{unique_id}"
        selection_begrensningskurve = f"begrensningskurve_selection_pre_rbc_{unique_id}"

        sql_expression_selection_fc = f"{id_field} = {unique_id}"
        output_name_selection_fc = f"selection_fc_{unique_id}"

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=input_polygon_layer,
            expression=sql_expression_selection_fc,
            output_name=output_name_selection_fc,
        )

        # Define selections for this unique_id
        selections = [
            {
                "input_layer": TemporaryFiles.simplified_grunnriss_n100.value,
                "output_name": selection_grunnriss,
            },
            {
                "input_layer": TemporaryFiles.unsplit_veg_sti_n100.value,
                "output_name": selection_veg_sti,
            },
            {
                "input_layer": TemporaryFiles.bygningspunkt_pre_symbology.value,
                "output_name": selection_bygningspunkt,
            },
            {
                "input_layer": TemporaryFiles.begrensningskurve_buffer_waterfeatures.value,
                "output_name": selection_begrensningskurve,
            },
        ]

        selection_layers = {}  # To store references to the created layers

        # Create selections and store references to layers
        for selection in selections:
            layer = custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=selection["input_layer"],
                overlap_type=custom_arcpy.OverlapType.INTERSECT,
                select_features=output_name_selection_fc,
                output_name=selection["output_name"],
            )
            selection_layers[selection["output_name"]] = layer


def rbc_iteration():
    arcpy.env.referenceScale = "100000"
    input_polygon_layer = iteration_fc
    id_field = "OID"
    unique_ids = [
        row[0] for row in arcpy.da.SearchCursor(input_polygon_layer, [id_field])
    ]

    for unique_id in unique_ids:
        print(f"Processing ID: {unique_id} out of {len(unique_ids)}")
        if unique_id == 4:
            print("Skipping ID: 4")
            continue
        # Construct names for selection outputs
        selection_grunnriss = f"grunnriss_selection_pre_rbc_{unique_id}"
        selection_veg_sti = f"veg_sti_selection_pre_rbc_{unique_id}"
        selection_bygningspunkt = f"bygningspunkt_selection_pre_rbc_{unique_id}"
        selection_begrensningskurve = f"begrensningskurve_selection_pre_rbc_{unique_id}"

        lyrx_bygningspunkt = (
            rf"{config.symbology_output_folder}\lyrx_bygningspunkt_{unique_id}.lyrx"
        )
        lyrx_grunnriss = (
            rf"{config.symbology_output_folder}\lyrx_grunnriss_{unique_id}.lyrx"
        )
        lyrx_veg_sti = (
            rf"{config.symbology_output_folder}\lyrx_veg_sti_{unique_id}.lyrx"
        )
        lyrx_begrensnings_kurve = rf"{config.symbology_output_folder}\lyrx_begrensnings_kurve_{unique_id}.lyrx"

        # Defining symbology layers
        symbology_veg_sti = SymbologyN100.veg_sti.value
        symbology_begrensnings_kurve = SymbologyN100.begrensnings_kurve.value
        symbology_bygningspunkt = SymbologyN100.bygningspunkt.value
        symbology_grunnriss = SymbologyN100.grunnriss.value

        symbology_configs = [
            {
                "input_layer": selection_grunnriss,
                "in_symbology_layer": symbology_grunnriss,
                "output_name": lyrx_grunnriss,
            },
            {
                "input_layer": selection_veg_sti,
                "in_symbology_layer": symbology_veg_sti,
                "output_name": lyrx_veg_sti,
            },
            {
                "input_layer": selection_bygningspunkt,
                "in_symbology_layer": symbology_bygningspunkt,
                "output_name": lyrx_bygningspunkt,
            },
            {
                "input_layer": selection_begrensningskurve,
                "in_symbology_layer": symbology_begrensnings_kurve,
                "output_name": lyrx_begrensnings_kurve,
            },
        ]

        # Loop over the symbology configurations and apply the function
        for symbology_config in symbology_configs:
            custom_arcpy.apply_symbology(
                input_layer=symbology_config["input_layer"],
                in_symbology_layer=symbology_config["in_symbology_layer"],
                output_name=symbology_config["output_name"],
            )

        # Resolve Building Conflicts
        print(
            f"Starting Resolve Building Conflicts 1 of {unique_id} out of {len(unique_ids)}"
        )

        # Defining variables for Resolve Building Conflicts
        input_buildings = [lyrx_grunnriss]

        input_barriers_nudge = [
            [lyrx_veg_sti, "false", "5 Meters"],
            [lyrx_begrensnings_kurve, "false", "5 Meters"],
        ]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=input_buildings,
            invisibility_field="invisibility",
            in_barriers=input_barriers_nudge,
            building_gap="5 meters",
            minimum_size="10 meters",
            hierarchy_field="hierarchy",
        )
        print(
            f"Starting Resolve Building Conflicts 2  {unique_id} out of {len(unique_ids)}"
        )

        input_barriers = [
            [lyrx_veg_sti, "false", "10 Meters"],
            [lyrx_begrensnings_kurve, "false", "5 Meters"],
        ]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=input_buildings,
            invisibility_field="invisibility",
            in_barriers=input_barriers,
            building_gap="10 meters",
            minimum_size="10 meters",
            hierarchy_field="hierarchy",
        )

        fields_to_calculate = [["hierarchy", "0"]]

        arcpy.management.CalculateFields(
            in_table=selection_grunnriss,
            expression_type="PYTHON3",
            fields=fields_to_calculate,
        )

        print(
            f"Starting Resolve Building Conflicts 3  {unique_id} out of {len(unique_ids)}"
        )
        # Defining variables for Resolve Building Conflicts
        input_buildings2 = [lyrx_bygningspunkt, lyrx_grunnriss]

        arcpy.cartography.ResolveBuildingConflicts(
            in_buildings=input_buildings2,
            invisibility_field="invisibility",
            in_barriers=input_barriers,
            building_gap="25 meters",
            minimum_size="10 meters",
            hierarchy_field="hierarchy",
        )

        # Sql expression to bring along bygningspunkt which are kept + church and hospital
        sql_expression_resolve_building_conflicts = (
            "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
        )

        resolve_building_conflicts_bygningspunkt_result_1 = (
            f"resolve_building_conflicts_bygningspunkt_result_1{unique_id}"
        )
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=selection_bygningspunkt,
            expression=sql_expression_resolve_building_conflicts,
            output_name=resolve_building_conflicts_bygningspunkt_result_1,
        )
        #
        # code_block_hierarchy = """def determineHierarchy(symbol_val):\n
        #     if symbol_val in [1, 2, 3]:\n
        #         return 0\n
        #     else:\n
        #         return None\n"""
        #
        # # Then run CalculateField with the new code block
        # arcpy.management.CalculateField(
        #     in_table=resolve_building_conflicts_bygningspunkt_result_1,
        #     field="hierarchy",
        #     expression="determineHierarchy(!symbol_val!)",
        #     expression_type="PYTHON3",
        #     code_block=code_block_hierarchy,
        # )
        #
        # custom_arcpy.apply_symbology(
        #     input_layer=resolve_building_conflicts_bygningspunkt_result_1,
        #     in_symbology_layer=symbology_bygningspunkt,
        #     output_name=lyrx_bygningspunkt,
        # )
        #
        # input_barriers2 = [
        #     [lyrx_veg_sti, "true", "25 Meters"],
        #     [lyrx_begrensnings_kurve, "false", "15 Meters"],
        # ]
        #
        # print(
        #     f"Starting Resolve Building Conflicts 3 {unique_id} out of {len(unique_ids)}"
        # )
        # # Defining variables for Resolve Building Conflicts
        # input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
        # arcpy.cartography.ResolveBuildingConflicts(
        #     in_buildings=input_buildings3,
        #     invisibility_field="invisibility",
        #     in_barriers=input_barriers2,
        #     building_gap="35 meters",
        #     minimum_size="10 meters",
        #     hierarchy_field="hierarchy",
        # )
        #

    #
    # input_barriers2 = [
    #     [lyrx_veg_sti, "true", "25 Meters"],
    #     [lyrx_begrensnings_kurve, "false", "15 Meters"],
    # ]
    #
    # print("Starting Resolve Building Conflicts 3")
    # # Defining variables for Resolve Building Conflicts
    # input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
    # arcpy.cartography.ResolveBuildingConflicts(
    #     in_buildings=input_buildings3,
    #     invisibility_field="invisibility",
    #     in_barriers=input_barriers2,
    #     building_gap="35 meters",
    #     minimum_size="10 meters",
    #     hierarchy_field="hierarchy",
    # )


def resolve_building_conflicts():
    ####################################################
    # Working iterator ove study areas using admin flate
    ####################################################

    # # Define your initial data
    # input_polygon_layer = input_n100.AdminFlate
    # id_field = "OBJECTID"
    # unique_ids = []
    #
    # selection_grunnriss = "grunnriss_selection_pre_rbc"
    # selection_veg_sti = "veg_sti_selection_pre_rbc"
    # selection_bygningspunkt = "bygningspunkt_selection_pre_rbc"
    # selection_begrensningskurve = "begrensningskurve_selection_pre_rbc"
    #
    # # Create a SearchCursor to loop through the polygon layer and collect unique IDs
    # with arcpy.da.SearchCursor(input_polygon_layer, [id_field]) as cursor:
    #     for row in cursor:
    #         unique_ids.append(row[0])
    #
    # # Loop through each unique ID to perform the selections
    # for unique_id in unique_ids:
    #     sql_expression_admin_flate = f"{id_field} = {unique_id}"
    #     output_name_admin_flate = f"admin_flate_selection_{unique_id}"
    #
    #     custom_arcpy.select_attribute_and_make_permanent_feature(
    #         input_layer=input_polygon_layer,
    #         expression=sql_expression_admin_flate,
    #         output_name=output_name_admin_flate,
    #     )
    #
    #     selections = [
    #         {
    #             "input_layer": TemporaryFiles.simplified_grunnriss_n100.value,
    #             "output_name": f"{selection_grunnriss}_{unique_id}",
    #         },
    #         {
    #             "input_layer": TemporaryFiles.unsplit_veg_sti_n100.value,
    #             "output_name": f"{selection_veg_sti}_{unique_id}",
    #         },
    #         {
    #             "input_layer": TemporaryFiles.bygningspunkt_pre_symbology.value,
    #             "output_name": f"{selection_bygningspunkt}_{unique_id}",
    #         },
    #         {
    #             "input_layer": TemporaryFiles.begrensningskurve_buffer_waterfeatures.value,
    #             "output_name": f"{selection_begrensningskurve}_{unique_id}",
    #         },
    #     ]
    #
    #     for selection in selections:
    #         custom_arcpy.select_location_and_make_permanent_feature(
    #             input_layer=selection["input_layer"],
    #             overlap_type=custom_arcpy.OverlapType.INTERSECT,
    #             select_features=output_name_admin_flate,
    #             output_name=selection["output_name"],
    #         )
    #
    #         # Defining symbology layers
    #         symbology_veg_sti = SymbologyN100.veg_sti.value
    #         symbology_begrensnings_kurve = SymbologyN100.begrensnings_kurve.value
    #         symbology_bygningspunkt = SymbologyN100.bygningspunkt.value
    #         symbology_grunnriss = SymbologyN100.grunnriss.value
    #
    #         # Apply symbology to selections
    #
    #         lyrx_bygningspunkt = (
    #             rf"{config.symbology_output_folder}\lyrx_bygningspunkt.lyrx"
    #         )
    #         lyrx_grunnriss = rf"{config.symbology_output_folder}\lyrx_grunnriss.lyrx"
    #         lyrx_veg_sti = rf"{config.symbology_output_folder}\lyrx_veg_sti.lyrx"
    #         lyrx_begrensnings_kurve = (
    #             rf"{config.symbology_output_folder}\lyrx_begrensnings_kurve.lyrx"
    #         )
    #
    #         # List of dictionaries containing parameters for each symbology application
    #         symbology_configs = [
    #             {
    #                 "input_layer": selection_bygningspunkt,
    #                 "in_symbology_layer": symbology_bygningspunkt,
    #                 "output_name": lyrx_bygningspunkt,
    #             },
    #             {
    #                 "input_layer": selection_grunnriss,
    #                 "in_symbology_layer": symbology_grunnriss,
    #                 "output_name": lyrx_grunnriss,
    #             },
    #             {
    #                 "input_layer": selection_veg_sti,
    #                 "in_symbology_layer": symbology_veg_sti,
    #                 "output_name": lyrx_veg_sti,
    #             },
    #             {
    #                 "input_layer": selection_begrensningskurve,
    #                 "in_symbology_layer": symbology_begrensnings_kurve,
    #                 "output_name": lyrx_begrensnings_kurve,
    #             },
    #         ]
    #
    #         # Loop over the symbology configurations and apply the function
    #         for symbology_config in symbology_configs:
    #             custom_arcpy.apply_symbology(
    #                 input_layer=symbology_config["input_layer"],
    #                 in_symbology_layer=symbology_config["in_symbology_layer"],
    #                 output_name=symbology_config["output_name"],
    #             )
    #
    #         # Resolve Building Conflicts
    #         print("Starting Resolve Building Conflicts 1")
    #         arcpy.env.referenceScale = "100000"
    #
    #         fields_to_calculate_first = [["hierarchy", "1"], ["invisibility", "0"]]
    #
    #         arcpy.management.CalculateFields(
    #             in_table=selection_grunnriss,
    #             expression_type="PYTHON3",
    #             fields=fields_to_calculate_first,
    #         )
    #
    #         # Defining variables for Resolve Building Conflicts
    #         input_buildings = [lyrx_grunnriss]
    #
    #         input_barriers = [
    #             [lyrx_veg_sti, "false", "10 Meters"],
    #             [lyrx_begrensnings_kurve, "false", "5 Meters"],
    #         ]
    #
    #         arcpy.cartography.ResolveBuildingConflicts(
    #             in_buildings=input_buildings,
    #             invisibility_field="invisibility",
    #             in_barriers=input_barriers,
    #             building_gap="10 meters",
    #             minimum_size="10 meters",
    #             hierarchy_field="hierarchy",
    #         )
    #
    #         fields_to_calculate = [["hierarchy", "0"], ["invisibility", "0"]]
    #
    #         arcpy.management.CalculateFields(
    #             in_table=selection_grunnriss,
    #             expression_type="PYTHON3",
    #             fields=fields_to_calculate,
    #         )
    #
    #         code_block_hierarchy = """def determineHierarchy(symbol_val):\n
    #             if symbol_val in [1, 2, 3]:\n
    #                 return 1\n
    #             else:\n
    #                 return None\n"""
    #
    #         # Then run CalculateField with the new code block
    #         arcpy.management.CalculateField(
    #             in_table=selection_bygningspunkt,
    #             field="hierarchy",
    #             expression="determineHierarchy(!symbol_val!)",
    #             expression_type="PYTHON3",
    #             code_block=code_block_hierarchy,
    #         )
    #
    #         print("Starting Resolve Building Conflicts 2")
    #         # Defining variables for Resolve Building Conflicts
    #         input_buildings2 = [lyrx_bygningspunkt, lyrx_grunnriss]
    #
    #         arcpy.cartography.ResolveBuildingConflicts(
    #             in_buildings=input_buildings2,
    #             invisibility_field="invisibility",
    #             in_barriers=input_barriers,
    #             building_gap="25 meters",
    #             minimum_size="10 meters",
    #             hierarchy_field="hierarchy",
    #         )
    #
    #         # Sql expression to bring along bygningspunkt which are kept + church and hospital
    #         sql_expression_resolve_building_conflicts = (
    #             "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    #         )
    #
    #         resolve_building_conflicts_bygningspunkt_result_1 = (
    #             "resolve_building_conflicts_bygningspunkt_result_1"
    #         )
    #         custom_arcpy.select_attribute_and_make_permanent_feature(
    #             input_layer=selection_bygningspunkt,
    #             expression=sql_expression_resolve_building_conflicts,
    #             output_name=resolve_building_conflicts_bygningspunkt_result_1,
    #         )
    #
    #         code_block_hierarchy = """def determineHierarchy(symbol_val):\n
    #             if symbol_val in [1, 2, 3]:\n
    #                 return 0\n
    #             elif symbol_val == 6:\n
    #                 return None\n
    #             else:\n
    #                 return None\n"""
    #
    #         # Then run CalculateField with the new code block
    #         arcpy.management.CalculateField(
    #             in_table=resolve_building_conflicts_bygningspunkt_result_1,
    #             field="hierarchy",
    #             expression="determineHierarchy(!symbol_val!)",
    #             expression_type="PYTHON3",
    #             code_block=code_block_hierarchy,
    #         )
    #
    #         arcpy.management.CalculateFields(
    #             in_table=selection_grunnriss,
    #             expression_type="PYTHON3",
    #             fields=fields_to_calculate,
    #         )
    #
    #         custom_arcpy.apply_symbology(
    #             input_layer=resolve_building_conflicts_bygningspunkt_result_1,
    #             in_symbology_layer=symbology_bygningspunkt,
    #             output_name=lyrx_bygningspunkt,
    #         )
    #
    #         input_barriers2 = [
    #             [lyrx_veg_sti, "true", "25 Meters"],
    #             [lyrx_begrensnings_kurve, "false", "15 Meters"],
    #         ]
    #
    #         print("Starting Resolve Building Conflicts 3")
    #         # Defining variables for Resolve Building Conflicts
    #         input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
    #         arcpy.cartography.ResolveBuildingConflicts(
    #             in_buildings=input_buildings3,
    #             invisibility_field="invisibility",
    #             in_barriers=input_barriers2,
    #             building_gap="35 meters",
    #             minimum_size="10 meters",
    #             hierarchy_field="hierarchy",
    #         )
    #
    #         input_barriers2 = [
    #             [lyrx_veg_sti, "true", "25 Meters"],
    #             [lyrx_begrensnings_kurve, "false", "15 Meters"],
    #         ]
    #
    #         print("Starting Resolve Building Conflicts 3")
    #         # Defining variables for Resolve Building Conflicts
    #         input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
    #         arcpy.cartography.ResolveBuildingConflicts(
    #             in_buildings=input_buildings3,
    #             invisibility_field="invisibility",
    #             in_barriers=input_barriers2,
    #             building_gap="35 meters",
    #             minimum_size="10 meters",
    #             hierarchy_field="hierarchy",
    #         )
    #
    #         arcpy.management.Delete(selection["output_name"])
    #
    #     arcpy.management.Delete(in_data=output_name_admin_flate)
    #
    # exit()

    #####################################################
    # Testing Resolve Building Conflicts for know area
    #####################################################

    # Choosing study area
    sql_expression_admin_flate = "NAVN = 'Asker'"
    output_name_admin_flate = "admin_flate_selection"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression=sql_expression_admin_flate,
        output_name=output_name_admin_flate,
    )

    selection_grunnriss = "grunnriss_selection_pre_rbc"
    selection_veg_sti = "veg_sti_selection_pre_rbc"
    selection_bygningspunkt = "bygningspunkt_selection_pre_rbc"
    selection_begrensningskurve = "begrensningskurve_selection_pre_rbc"

    # List of dictionaries containing parameters for each selection
    selections = [
        {
            "input_layer": TemporaryFiles.simplified_grunnriss_n100.value,
            "output_name": selection_grunnriss,
        },
        {
            "input_layer": TemporaryFiles.unsplit_veg_sti_n100.value,
            "output_name": selection_veg_sti,
        },
        {
            "input_layer": TemporaryFiles.bygningspunkt_pre_symbology.value,
            "output_name": selection_bygningspunkt,
        },
        {
            "input_layer": TemporaryFiles.begrensningskurve_buffer_waterfeatures.value,
            "output_name": selection_begrensningskurve,
        },
    ]

    # Loop over the selections and apply the function
    for selection in selections:
        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=selection["input_layer"],
            overlap_type=custom_arcpy.OverlapType.INTERSECT,  # Assuming all use INTERSECT
            select_features=output_name_admin_flate,
            output_name=selection["output_name"],
        )

    # Defining symbology layers
    symbology_veg_sti = SymbologyN100.veg_sti.value
    symbology_begrensnings_kurve = SymbologyN100.begrensnings_kurve.value
    symbology_bygningspunkt = SymbologyN100.bygningspunkt.value
    symbology_grunnriss = SymbologyN100.grunnriss.value

    # Apply symbology to selections

    lyrx_bygningspunkt = rf"{config.symbology_output_folder}\lyrx_bygningspunkt.lyrx"
    lyrx_grunnriss = rf"{config.symbology_output_folder}\lyrx_grunnriss.lyrx"
    lyrx_veg_sti = rf"{config.symbology_output_folder}\lyrx_veg_sti.lyrx"
    lyrx_begrensnings_kurve = (
        rf"{config.symbology_output_folder}\lyrx_begrensnings_kurve.lyrx"
    )

    # List of dictionaries containing parameters for each symbology application
    symbology_configs = [
        {
            "input_layer": selection_bygningspunkt,
            "in_symbology_layer": symbology_bygningspunkt,
            "output_name": lyrx_bygningspunkt,
        },
        {
            "input_layer": selection_grunnriss,
            "in_symbology_layer": symbology_grunnriss,
            "output_name": lyrx_grunnriss,
        },
        {
            "input_layer": selection_veg_sti,
            "in_symbology_layer": symbology_veg_sti,
            "output_name": lyrx_veg_sti,
        },
        {
            "input_layer": selection_begrensningskurve,
            "in_symbology_layer": symbology_begrensnings_kurve,
            "output_name": lyrx_begrensnings_kurve,
        },
    ]

    # Loop over the symbology configurations and apply the function
    for symbology_config in symbology_configs:
        custom_arcpy.apply_symbology(
            input_layer=symbology_config["input_layer"],
            in_symbology_layer=symbology_config["in_symbology_layer"],
            output_name=symbology_config["output_name"],
        )

    # Resolve Building Conflicts
    print("Starting Resolve Building Conflicts 1")
    arcpy.env.referenceScale = "100000"

    fields_to_calculate_first = [["hierarchy", "1"], ["invisibility", "0"]]

    arcpy.management.CalculateFields(
        in_table=selection_grunnriss,
        expression_type="PYTHON3",
        fields=fields_to_calculate_first,
    )

    # Defining variables for Resolve Building Conflicts
    input_buildings = [lyrx_grunnriss]

    input_barriers = [
        [lyrx_veg_sti, "false", "10 Meters"],
        [lyrx_begrensnings_kurve, "false", "5 Meters"],
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="10 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )

    input_barriers_second = [
        [lyrx_veg_sti, "false", "25 Meters"],
        [lyrx_begrensnings_kurve, "false", "15 Meters"],
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings,
        invisibility_field="invisibility",
        in_barriers=input_barriers_second,
        building_gap="10 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )

    fields_to_calculate = [["hierarchy", "0"]]

    arcpy.management.CalculateFields(
        in_table=selection_grunnriss,
        expression_type="PYTHON3",
        fields=fields_to_calculate,
    )

    code_block_hierarchy = """def determineHierarchy(symbol_val):\n
        if symbol_val in [1, 2, 3]:\n
            return 1\n
        else:\n
            return None\n"""

    # Then run CalculateField with the new code block
    arcpy.management.CalculateField(
        in_table=selection_bygningspunkt,
        field="hierarchy",
        expression="determineHierarchy(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_hierarchy,
    )

    print("Starting Resolve Building Conflicts 2")
    # Defining variables for Resolve Building Conflicts
    input_buildings2 = [lyrx_bygningspunkt, lyrx_grunnriss]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings2,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="25 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )

    # Sql expression to bring along bygningspunkt which are kept + church and hospital
    sql_expression_resolve_building_conflicts = (
        "(invisibility = 0) OR (symbol_val IN (1, 2, 3))"
    )

    resolve_building_conflicts_bygningspunkt_result_1 = (
        "resolve_building_conflicts_bygningspunkt_result_1"
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=selection_bygningspunkt,
        expression=sql_expression_resolve_building_conflicts,
        output_name=resolve_building_conflicts_bygningspunkt_result_1,
    )

    # code_block_hierarchy = """def determineHierarchy(symbol_val):\n
    #     if symbol_val in [1, 2, 3]:\n
    #         return 0\n
    #     elif symbol_val == 6:\n
    #         return None\n
    #     else:\n
    #         return None\n"""
    #
    # # Then run CalculateField with the new code block
    # arcpy.management.CalculateField(
    #     in_table=resolve_building_conflicts_bygningspunkt_result_1,
    #     field="hierarchy",
    #     expression="determineHierarchy(!symbol_val!)",
    #     expression_type="PYTHON3",
    #     code_block=code_block_hierarchy,
    # )
    #
    # arcpy.management.CalculateFields(
    #     in_table=selection_grunnriss,
    #     expression_type="PYTHON3",
    #     fields=fields_to_calculate,
    # )

    custom_arcpy.apply_symbology(
        input_layer=resolve_building_conflicts_bygningspunkt_result_1,
        in_symbology_layer=symbology_bygningspunkt,
        output_name=lyrx_bygningspunkt,
    )

    input_barriers2 = [
        [lyrx_veg_sti, "true", "25 Meters"],
        [lyrx_begrensnings_kurve, "false", "15 Meters"],
    ]

    print("Starting Resolve Building Conflicts 3")
    # Defining variables for Resolve Building Conflicts
    input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings3,
        invisibility_field="invisibility",
        in_barriers=input_barriers2,
        building_gap="55 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )

    resolve_building_conflicts_bygningspunkt_result_2 = (
        "resolve_building_conflicts_bygningspunkt_result_2"
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=resolve_building_conflicts_bygningspunkt_result_1,
        expression=sql_expression_resolve_building_conflicts,
        output_name=resolve_building_conflicts_bygningspunkt_result_2,
    )

    custom_arcpy.apply_symbology(
        input_layer=resolve_building_conflicts_bygningspunkt_result_2,
        in_symbology_layer=symbology_bygningspunkt,
        output_name=lyrx_bygningspunkt,
    )

    input_barriers3 = [
        [lyrx_veg_sti, "true", "95 Meters"],
        [lyrx_begrensnings_kurve, "false", "45 Meters"],
    ]

    print("Starting Resolve Building Conflicts 3")
    # Defining variables for Resolve Building Conflicts
    input_buildings3 = [lyrx_bygningspunkt, lyrx_grunnriss]
    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings3,
        invisibility_field="invisibility",
        in_barriers=input_barriers3,
        building_gap="150 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )

    resolve_building_conflicts_bygningspunkt_result_3 = (
        "resolve_building_conflicts_bygningspunkt_result_3"
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=resolve_building_conflicts_bygningspunkt_result_2,
        expression=sql_expression_resolve_building_conflicts,
        output_name=resolve_building_conflicts_bygningspunkt_result_3,
    )

    custom_arcpy.apply_symbology(
        input_layer=resolve_building_conflicts_bygningspunkt_result_3,
        in_symbology_layer=symbology_bygningspunkt,
        output_name=lyrx_bygningspunkt,
    )


# resolve_building_conflicts()

# main()


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
