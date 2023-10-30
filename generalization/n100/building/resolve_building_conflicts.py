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

    # Choosing study area 
    sql_expression_admin_flate = "NAVN = 'Asker'"
    output_name_admin_flate = "admin_flate_selection"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression=sql_expression_admin_flate,
        output_name=output_name_admin_flate,
    )
    # Making selections based on spatial relation to study area 
    selection_grunnriss = "grunnriss_selection_pre_rbc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=TemporaryFiles.simplified_grunnriss_n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=output_name_admin_flate,
        output_name=selection_grunnriss,
    )

    selection_veg_sti = "veg_sti_selection_pre_rbc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=TemporaryFiles.unsplit_veg_sti_n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=output_name_admin_flate,
        output_name=selection_veg_sti,
    )

    selection_bygningspunkt = "bygningspunkt_selection_pre_rbc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=TemporaryFiles.bygningspunkt_pre_symbology.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=output_name_admin_flate,
        output_name=selection_bygningspunkt,
    )

    selection_begrensningskurve = "begrensningskurve_selection_pre_rbc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=TemporaryFiles.begrensningskurve_buffer_waterfeatures.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT,
        select_features=output_name_admin_flate,
        output_name=selection_begrensningskurve,
    )

    # Defining symbology layers
    symbology_veg_sti = SymbologyN100.veg_sti.value
    symbology_begrensnings_kurve = SymbologyN100.begrensnings_kurve.value
    symbology_bygningspunkt = SymbologyN100.bygningspunkt.value
    symbology_grunnriss = SymbologyN100.grunnriss.value

    feature_selection_veg_sti = (
        selection_veg_sti  # "veg_sti_selection_pre_rbc_feature_layer"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=selection_veg_sti,
        out_layer=feature_selection_veg_sti,
    )

    feature_selection_begrensningskurve = selection_begrensningskurve  # "begrensningskurve_selection_pre_rbc_feature_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=selection_begrensningskurve,
        out_layer=feature_selection_begrensningskurve,
    )

    feature_selection_grunnriss = (
        selection_grunnriss  # "grunnriss_selection_pre_rbc_feature_layer"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=selection_grunnriss,
        out_layer=feature_selection_grunnriss,
    )

    feature_selection_bygningspunkt = (
        selection_bygningspunkt  # "bygningspunkt_selection_pre_rbc_feature_layer"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=selection_bygningspunkt,
        out_layer=feature_selection_bygningspunkt,
    )

    # Apply symbology from layer 
    arcpy.management.ApplySymbologyFromLayer(
        in_layer=selection_veg_sti,
        in_symbology_layer=symbology_veg_sti,
        update_symbology="MAINTAIN",
    )

    arcpy.management.ApplySymbologyFromLayer(
        in_layer=selection_begrensningskurve,
        in_symbology_layer=symbology_begrensnings_kurve,
        update_symbology="MAINTAIN",
    )

    arcpy.management.ApplySymbologyFromLayer(
        in_layer=selection_bygningspunkt,
        in_symbology_layer=symbology_bygningspunkt,
        update_symbology="MAINTAIN",
    )

    arcpy.management.ApplySymbologyFromLayer(
        in_layer=selection_grunnriss,
        in_symbology_layer=symbology_grunnriss,
        update_symbology="MAINTAIN",
    )

    lyrx_bygningspunkt = rf"{config.symbology_output_folder}\lyrx_bygningspunkt.lyrx"
    arcpy.SaveToLayerFile_management(
        in_layer=selection_bygningspunkt,
        out_layer=lyrx_bygningspunkt,
        is_relative_path="ABSOLUTE",
    )

    lyrx_veg_sti = rf"{config.symbology_output_folder}\lyrx_veg_sti.lyrx"
    arcpy.SaveToLayerFile_management(
        in_layer=selection_veg_sti,
        out_layer=lyrx_veg_sti,
        is_relative_path="ABSOLUTE",
    )

    lyrx_begrensnings_kurve = (
        rf"{config.symbology_output_folder}\lyrx_begrensnings_kurve.lyrx"
    )
    arcpy.SaveToLayerFile_management(
        in_layer=selection_begrensningskurve,
        out_layer=lyrx_begrensnings_kurve,
        is_relative_path="ABSOLUTE",
    )

    lyrx_grunnriss = rf"{config.symbology_output_folder}\lyrx_grunnriss.lyrx"
    arcpy.SaveToLayerFile_management(
        in_layer=selection_grunnriss,
        out_layer=lyrx_grunnriss,
        is_relative_path="ABSOLUTE",
    )

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



