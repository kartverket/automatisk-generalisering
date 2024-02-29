# Importing custom files relative to the root path
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from file_manager.n100.file_manager_buildings import Building_N100

# Importing general packages
import arcpy
from collections import Counter

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("calculating_values.py")
def main():
    """
    Summary:
        Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.

    Details:
        1. `table_management`:
            Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility. Creates a symbology value field based on NBR values and logs undefined NBR values, reclassifying them to 729. Ensures that building types which should not be delivered are correctly reclassified.
    """
    environment_setup.main()
    table_management()


@timing_decorator
def table_management():
    """
    Summary:
        Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.
        Creates a symbology value field based on NBR values and logs undefined NBR values, reclassifying them to 729.
        Ensures that building types which should not be delivered are correctly reclassified.

    Details:
        - Reclassify the sykehus from matrikkel to another NBR value.
        - Reclassify the sykehus from grunnriss to another NBR value.
        - Merge the n50 building point and points added from matrikkel.
        - Adding a field to indicate that the merged building point and matrikkel does not come from grunnriss.
        - Adding a field to indicate that points resulting from grunnriss are tracked.
        - Reclassify the sykehus from grunnriss to another NBR value.
        - Merge the merged building point from n50 and matrikkel with points created from grunnriss.
        - Adding a symbology value field based on NBR values.
        - Code block to transform BYGGTYP_NBR values without symbology to other buildings (729).
        - Code block to update the symbol_val to reflect the new BYGGTYP_NBR.
        - Adding angle, hierarchy, and invisibility fields to the building point pre symbology and setting them to 0.
        - Calculate fields.
        - Code block hierarchy logic where churches and hospitals have hierarchy of 1, farms have hierarchy of 2 and the rest of the hierarchy is 3.
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

    # Merge the n50 building point and matrikkel
    arcpy.management.Merge(
        inputs=[
            input_n50.BygningsPunkt,
            Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        ],
        output=Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
    )

    # Adding a field to indicate that the merged building point and matrikkel does not come from grunnriss
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

    # Merge the merged building point from n50 and matrikkel with points created from grunnriss
    arcpy.management.Merge(
        inputs=[
            Building_N100.table_management__merged_bygningspunkt_n50_matrikkel__n100.value,
            Building_N100.grunnriss_to_point__merged_points_created_from_grunnriss__n100.value,
        ],
        output=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
    )

    try:
        # Attempt to add the field
        arcpy.AddField_management(
            in_table=Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value,
            field_name="symbol_val",
            field_type="LONG",
        )
        print("Field 'symbol_val' added successfully.")
    except arcpy.ExecuteError:
        print("Field 'symbol_val' already exists.")

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
        "def symbol_val_to_nbr(symbol_val, byggtyp_nbr):\n"
        "    if symbol_val == -99:\n"
        "        return 729\n"
        "    return byggtyp_nbr"
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
        expression="symbol_val_to_nbr(!symbol_val!, !BYGGTYP_NBR!)",
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

    # Adding agnle, hierarchy and invisibility fields to the building point pre symbology and setting them to 0
    # Define field information
    fields_to_add = [["angle", "LONG"], ["hierarchy", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["angle", "0"], ["hierarchy", "0"], ["invisibility", "0"]]

    # Feature class to check fields existence
    point_feature_class = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )

    # Check if fields already exist
    existing_fields = arcpy.ListFields(point_feature_class)
    existing_field_names = [field.name.lower() for field in existing_fields]
    fields_to_add_names = [field[0].lower() for field in fields_to_add]

    if not all(
        field_name in existing_field_names for field_name in fields_to_add_names
    ):
        # Add fields
        arcpy.management.AddFields(
            in_table=point_feature_class,
            field_description=fields_to_add,
        )

        # Calculate fields
        arcpy.management.CalculateFields(
            in_table=point_feature_class,
            expression_type="PYTHON3",
            fields=fields_to_calculate,
        )
    else:
        print("Fields already exist. Skipping adding and calculating fields.")

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


if __name__ == "__main__":
    main()
