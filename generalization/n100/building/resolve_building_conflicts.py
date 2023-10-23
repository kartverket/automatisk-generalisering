import arcpy

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
    pass


def resolve_building_conflicts():
    sql_expression_admin_flate = "NAVN = 'Asker'"
    output_name_admin_flate = "admin_flate_selection"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression=sql_expression_admin_flate,
        output_name=output_name_admin_flate,
    )

    selection_grunnriss = "grunnriss_selection_pre_rbc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=TemporaryFiles.grunnriss_selection_n50.value,
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



resolve_building_conflicts()