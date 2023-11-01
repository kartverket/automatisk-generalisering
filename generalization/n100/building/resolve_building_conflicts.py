import arcpy
import os

# Importing custom files relative to the root path
import config
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing environment
environment_setup.setup(workspace=config.n100_building_workspace)


def main():
    resolve_building_conflicts()


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
    #         print(f"{selection['output_name']} created.")
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
    print("Starting Resolve Building Conflicts")
    # Defining variables for Resolve Building Conflicts
    arcpy.env.referenceScale = "100000"
    input_buildings = [lyrx_bygningspunkt, lyrx_grunnriss]

    input_barriers = [
        [lyrx_veg_sti, "false", "0 Meters"],
        [lyrx_begrensnings_kurve, "false", "0 Meters"],
    ]

    arcpy.cartography.ResolveBuildingConflicts(
        in_buildings=input_buildings,
        invisibility_field="invisibility",
        in_barriers=input_barriers,
        building_gap="25 meters",
        minimum_size="10 meters",
        hierarchy_field="hierarchy",
    )


# # Defining variables for Resolve Building Conflicts
# input_buildings = [selection_grunnriss, selection_bygningspunkt]
#
# input_barriers = [
#     [selection_veg_sti, False, "0 Meters"],
#     [selection_begrensningskurve, False, "0 Meters"],
# ]
#
# arcpy.cartography.ResolveBuildingConflicts(
#     in_buildings=input_buildings,
#     invisibility_field="invisibility",
#     in_barriers=input_barriers,
#     building_gap="10 meters",
#     minimum_size="15 meters",
#     hierarchy_field="hierarchy",
# )


# custom_arcpy.apply_symbology(
#     input_layer="aaaaaaaaaaaaaa_FeatureToPoin",
#     in_symbology_layer=SymbologyN100.bygningspunkt.value,
#     output_name=r"C:\GIS_Files\symbology\test\sykehus_test.lyrx",
# )
main()
