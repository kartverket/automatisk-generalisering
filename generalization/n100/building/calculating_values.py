# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from file_manager.n100.file_manager_buildings import TemporaryFiles
from file_manager.n100.file_manager_buildings import PermanentFiles

# Importing general packages
import arcpy

# Importing environment
environment_setup.setup(
    workspace=config.n100_building_workspace
)


def main():
    """
    Adding required fields for bygningspunkt for symbology and resolve building conflicts: angle, hierarchy and invisibility.
    And adding additional information such as source information making it possible to know if a point was added from grunnriss or not.
    """
    table_management()


def table_management():
    """
    Adding required fields for bygningspunkt for symbology and resolve building conflicts: angle, hierarchy and invisibility.
    Creates a symbology value field based on NBR values
    Also adds additional information such as source information making it possible to know if a point was added from grunnriss or not.
    """

    # Reclassify the sykehus from matrikkel to another NBR value
    code_block_hospital = (
        "def hospital_nbr(nbr):\n"
        "    mapping = {970: 729, 719: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    # Reclassify the sykehus from grunnriss to another NBR value
    arcpy.CalculateField_management(
        in_table=TemporaryFiles.matrikkel_bygningspunkt.value,
        field="BYGGTYP_NBR",
        expression="hospital_nbr(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital,
    )

    # Define the output name
    merged_bygningspunkt_matrikkel = "merged_bygningspunkt_matrikkel"

    # Merge the bygningspunkt and matrikkel
    arcpy.management.Merge(
        inputs=[input_n50.BygningsPunkt, TemporaryFiles.matrikkel_bygningspunkt.value],
        output=merged_bygningspunkt_matrikkel,
    )

    # Adding a field to indicate that the merged bygningspunkt and matrikkel does not come from grunnriss
    arcpy.AddField_management(
        in_table=merged_bygningspunkt_matrikkel,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=merged_bygningspunkt_matrikkel,
        field="grunnriss",
        expression="0",
    )

    points_created_from_grunnriss = TemporaryFiles.merged_points_final.value
    # Adding a field to indicate that points resulting from grunnriss is tracked
    arcpy.AddField_management(
        in_table=points_created_from_grunnriss,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=points_created_from_grunnriss,
        field="grunnriss",
        expression="1",
    )

    # Reclassify the sykehus from grunnriss to another NBR value
    arcpy.CalculateField_management(
        in_table=points_created_from_grunnriss,
        field="BYGGTYP_NBR",
        expression="hospital_nbr(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital,
    )

    # Define the output name
    merged_points = "merged_points"

    # Merge the bygningspunkt and matrikkel
    arcpy.management.Merge(
        inputs=[merged_bygningspunkt_matrikkel, points_created_from_grunnriss],
        output=merged_points,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=merged_points,
        field_name="symbol_val",
        field_type="LONG",
    )

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
        in_table=merged_points,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block,
    )

    # Define output name
    undefined_nbr_values = (
        PermanentFiles.n100_building_points_undefined_nbr_values.value
    )

    expression_no_nbr = "symbol_val = -99"

    # Selecting undefined NBR values and make a permanent feature of them
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=merged_points,
        expression=expression_no_nbr,
        output_name=undefined_nbr_values,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=False,
    )

    # Define output name
    bygningspunkt_pre_symbology = TemporaryFiles.bygningspunkt_pre_symbology.value

    # Selecting defined NBR values
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=merged_points,
        expression=expression_no_nbr,
        output_name=bygningspunkt_pre_symbology,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
        inverted=True,
    )

    # Adding agnle, hierarchy and invisibility fields to the bygningspunkt pre symbology and setting them to 0
    # Define field information
    fields_to_add = [["angle", "LONG"], ["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=bygningspunkt_pre_symbology,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=bygningspunkt_pre_symbology,
        expression_type="PYTHON3",
        fields=fields_to_calculate,
    )

    code_block_hierarchy = """def determineHierarchy(symbol_val):\n
        if symbol_val in [1, 2, 3]:\n
            return 1\n
        elif symbol_val == 6:\n
            return 2\n
        else:\n
            return 3\n"""

    # Then run CalculateField with the new code block
    arcpy.management.CalculateField(
        in_table=bygningspunkt_pre_symbology,
        field="hierarchy",
        expression="determineHierarchy(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_hierarchy,
    )


