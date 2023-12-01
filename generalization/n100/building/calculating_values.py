# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from file_manager.n100.file_manager_buildings import Building_N100
from file_manager.n100.file_manager_buildings import PermanentFiles

# Importing general packages
import arcpy
from collections import Counter

# Importing environment
environment_setup.general_setup()


def main():
    """
    Adding required fields for all point files from different sources (grunnriss, matrikkel, n50_bygningspunkt) for symbology and resolve building conflicts: angle, hierarchy and invisibility.
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
        in_table=Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        field="BYGGTYP_NBR",
        expression="hospital_nbr(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital,
    )
    print(
        "#######################NEEDS TO IMPLEMENT LATEST LOGIC FROM DATA PREPERATION! #######################"
    )

    # Merge the n50 bygningspunkt and matrikkel
    arcpy.management.Merge(
        inputs=[
            input_n50.BygningsPunkt,
            Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        ],
        output=Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
    )

    # Adding a field to indicate that the merged bygningspunkt and matrikkel does not come from grunnriss
    arcpy.AddField_management(
        in_table=Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
        field="grunnriss",
        expression="0",
    )

    # Adding a field to indicate that points resulting from grunnriss is tracked
    arcpy.AddField_management(
        in_table=Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
        field="grunnriss",
        expression="1",
    )

    # Reclassify the sykehus from grunnriss to another NBR value
    arcpy.CalculateField_management(
        in_table=Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
        field="BYGGTYP_NBR",
        expression="hospital_nbr(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital,
    )

    # Merge the merged bygningspunkt from n50 and matrikkel with points created from grunnriss
    arcpy.management.Merge(
        inputs=[
            Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
            Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
        ],
        output=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
    )

    # Adding a symbology value field based on NBR values
    arcpy.AddField_management(
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field_name="symbol_val",
        field_type="LONG",
    )
    print(
        f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value} merged"
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
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block,
    )

    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        expression="symbol_val = -99",
        output_name=Building_N100.table_management__selection_bygningspunkt_with_undefined_nbr_values__n100.value,
    )
    print("start cursor")

    # Counter to store the count of each unique BYGGTYP_NBR
    nbr_counter = Counter()

    # Iterate over the rows in the feature class
    with arcpy.da.SearchCursor(
        Building_N100.table_management__selection_bygningspunkt_with_undefined_nbr_values__n100.value,
        ["BYGGTYP_NBR", "symbol_val"],
    ) as cursor:
        for nbr, symbol_val in cursor:
            if symbol_val == -99:
                nbr_counter[nbr] += 1

    # Calculate the total count
    total_count = sum(nbr_counter.values())

    # Writing the counts to a log file
    with open(
        Building_N100.table_management__building_points_with_undefined_nbr_values__n100.value,
        "w",
    ) as log_file:
        for nbr, count in nbr_counter.items():
            log_file.write(f"BYGGTYP_NBR: {nbr}, Count: {count}\n")
        # Write the total count at the end
        log_file.write(f"Total Rows without defined symbology: {total_count}\n")

    print(
        f"Log file created at: {Building_N100.table_management__building_points_with_undefined_nbr_values__n100.value}"
    )

    # Code block to transform BYGGTYP_NBR values without symbology to other buildings (729)
    code_block_symbol_val_to_nbr = (
        "def symbol_val_to_nbr(symbol_val):\n"
        "    if symbol_val == -99:\n"
        "        return 729\n"
        "    return symbol_val"
    )

    # Code block to update the symbol_val to reflect the new BYGGTYP_NBR
    code_block_update_symbol_val = (
        "def update_symbol_val(symbol_val):\n"
        "    if symbol_val == -99:\n"
        "        return 8\n"
        "    return symbol_val"
    )

    # Applying the symbol_val_to_nbr logic
    arcpy.CalculateField_management(
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field="BYGGTYP_NBR",
        expression="symbol_val_to_nbr(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_symbol_val_to_nbr,
    )

    # Applying the update_symbol_val logic
    arcpy.CalculateField_management(
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field="symbol_val",
        expression="update_symbol_val(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_update_symbol_val,
    )

    # Adding agnle, hierarchy and invisibility fields to the bygningspunkt pre symbology and setting them to 0
    # Define field information
    fields_to_add = [["angle", "LONG"], ["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]]

    # Add fields
    arcpy.management.AddFields(
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field_description=fields_to_add,
    )

    # Calculate fields
    arcpy.management.CalculateFields(
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
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
        in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
        field="hierarchy",
        expression="determineHierarchy(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_hierarchy,
    )


def clean_up_fields_keep():
    # Provide the path to your feature class
    feature_class_to_clean_up = ""

    # List of field names to keep
    fields_to_keep = ["Field1", "Field2", "Field3"]

    # Get a list of all fields in the feature class
    all_fields = [field.name for field in arcpy.ListFields(feature_class_to_clean_up)]

    # Identify fields to delete
    fields_to_delete = [field for field in all_fields if field not in fields_to_keep]

    # Check if there are fields to delete
    if fields_to_delete:
        try:
            # Start editing the feature class
            with arcpy.da.Editor(arcpy.env.workspace) as edit:
                # Delete the specified fields
                arcpy.management.DeleteField(
                    feature_class_to_clean_up, fields_to_delete
                )
                print(f"Deleted fields: {fields_to_delete}")
        except arcpy.ExecuteError:
            print(arcpy.GetMessages(2))
    else:
        print("No fields to delete.")


def clean_up_fields_delete():
    # Provide the path to your feature class
    feature_class_to_clean_up = ""

    # List of field names to delete
    fields_to_delete = ["Field1", "Field2", "Field3"]

    # Get a list of all fields in the feature class
    all_fields = [field.name for field in arcpy.ListFields(feature_class_to_clean_up)]

    # Identify fields to keep (inverse of fields to delete)
    fields_to_keep = [field for field in all_fields if field not in fields_to_delete]

    # Check if there are fields to keep
    if fields_to_keep:
        try:
            # Start editing the feature class
            with arcpy.da.Editor(arcpy.env.workspace) as edit:
                # Delete the specified fields
                arcpy.management.DeleteField(
                    feature_class_to_clean_up, fields_to_delete
                )
                print(f"Deleted fields: {fields_to_delete}")

                # Optionally, print the fields that are kept
                print(f"Kept fields: {fields_to_keep}")
        except arcpy.ExecuteError:
            print(arcpy.GetMessages(2))
    else:
        print("No fields to keep.")


if __name__ == "__main__":
    main()
