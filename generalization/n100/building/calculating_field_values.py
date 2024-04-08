# Importing custom files relative to the root path
from custom_tools import custom_arcpy
from env_setup import environment_setup
from input_data import input_n50
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_SQLResources

# Importing general packages
import arcpy
from collections import Counter

# Importing timing decorator
from custom_tools.timing_decorator import timing_decorator


@timing_decorator("calculating_field_values.py")
def main():
    """
    Summary:
        Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.

    Details:
        1. `table_management`:
            Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility. Creates a symbology value field based on NBR values and logs undefined NBR values, reclassifying them to 729. Ensures that building types which should not be delivered are correctly reclassified.
    """
    environment_setup.main()
    reclassifying_hospital_and_church_points_from_matrikkel()
    adding_original_source_to_points()
    merge_matrikkel_and_n50_with_points_from_grunnriss()
    find_undefined_nbr_values()
    find_each_unique_nbr_value()
    calculate_angle_and_visibility_for_points()
    calculate_hierarchy_for_points()


@timing_decorator
def reclassifying_hospital_and_church_points_from_matrikkel():
    # Reclassify hospitals and churches from matrikken to another NBR value ("Other buildings" / "Andre bygg")
    code_block_hospital_church = (
        "def reclassify(nbr):\n"
        "    mapping = {970: 729, 719: 729, 671: 729}\n"
        "    return mapping.get(nbr, nbr)"
    )

    arcpy.CalculateField_management(
        in_table=Building_N100.data_preparation___matrikkel_points___n100_building.value,
        field="BYGGTYP_NBR",
        expression="reclassify(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_hospital_church,
    )


@timing_decorator
def adding_original_source_to_points():
    # Adding a field to indicate that the merged building point and matrikkel does not come from grunnriss
    arcpy.AddField_management(
        in_table=Building_N100.data_preperation___matrikkel_n50_points_merged___n100_building.value,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.data_preperation___matrikkel_n50_points_merged___n100_building.value,
        field="grunnriss",
        expression="0",
    )

    # Adding a field to indicate that points resulting from grunnriss is tracked
    arcpy.AddField_management(
        in_table=Building_N100.polygon_to_point___merged_points_final___n100_building.value,
        field_name="grunnriss",
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=Building_N100.polygon_to_point___merged_points_final___n100_building.value,
        field="grunnriss",
        expression="1",
    )


@timing_decorator
def merge_matrikkel_and_n50_with_points_from_grunnriss():
    # Merge the merged building point from n50 and matrikkel with points created from grunnriss
    arcpy.management.Merge(
        inputs=[
            Building_N100.data_preperation___matrikkel_n50_points_merged___n100_building.value,
            Building_N100.polygon_to_point___merged_points_final___n100_building.value,
        ],
        output=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
    )

    arcpy.AddField_management(
        in_table=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        field_name="symbol_val",
        field_type="SHORT",
    )

    # Determining and assigning symbol val
    arcpy.CalculateField_management(
        in_table=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_symbol_val_code_block.value,
    )


@timing_decorator
def find_undefined_nbr_values():
    custom_arcpy.select_attribute_and_make_feature_layer(
        input_layer=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        expression="symbol_val = -99",
        output_name=Building_N100.calculating_field_values___selection_building_points_with_undefined_nbr_values___n100_building.value,
    )


@timing_decorator
def find_each_unique_nbr_value():
    # Counter to store the count of each unique BYGGTYP_NBR
    nbr_counter = Counter()

    # Iterate over the rows in the feature class
    with arcpy.da.SearchCursor(
        Building_N100.calculating_field_values___selection_building_points_with_undefined_nbr_values___n100_building.value,
        ["BYGGTYP_NBR", "symbol_val"],
    ) as cursor:
        for nbr, symbol_val in cursor:
            if symbol_val == -99:
                nbr_counter[nbr] += 1

    # Calculate the total count
    total_count = sum(nbr_counter.values())

    # Writing the counts to a log file
    with open(
        Building_N100.calculating_field_values___building_points_with_undefined_nbr_values___n100_building.value,
        "w",
    ) as log_file:
        for nbr, count in nbr_counter.items():
            log_file.write(f"BYGGTYP_NBR: {nbr}, Count: {count}\n")
        # Write the total count at the end
        log_file.write(f"Total Rows without defined symbology: {total_count}\n")

    print(
        f"Log file created at: {Building_N100.calculating_field_values___building_points_with_undefined_nbr_values___n100_building.value}"
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
        in_table=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        field="BYGGTYP_NBR",
        expression="symbol_val_to_nbr(!symbol_val!, !BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=code_block_symbol_val_to_nbr,
    )

    # Applying the update_symbol_val logic
    arcpy.CalculateField_management(
        in_table=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        field="symbol_val",
        expression="update_symbol_val(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=code_block_update_symbol_val,
    )


@timing_decorator
def calculate_angle_and_visibility_for_points():
    # Feature class to check fields existence
    point_feature_class = (
        Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value
    )

    # List of fields to add and calculate
    fields_to_add = [["angle", "LONG"], ["invisibility", "LONG"]]
    fields_to_calculate = [["angle", "0"], ["invisibility", "0"]]

    # Check if the fields exist in the feature class
    existing_fields = [field.name for field in arcpy.ListFields(point_feature_class)]

    # Add fields if they don't exist
    for field_name, field_type in fields_to_add:
        if field_name not in existing_fields:
            arcpy.AddField_management(point_feature_class, field_name, field_type)

    # Calculate values for each field
    for field_name, field_value in fields_to_calculate:
        arcpy.management.CalculateField(
            in_table=point_feature_class,
            field=field_name,
            expression=field_value,
            expression_type="PYTHON3",
        )


@timing_decorator
def calculate_hierarchy_for_points():
    # Then run CalculateField with the new code block
    arcpy.management.CalculateField(
        in_table=Building_N100.calculate_field_values___points_pre_resolve_building_conflicts___n100_building.value,
        field="hierarchy",
        expression="determineHierarchy(!symbol_val!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.symbol_val_to_hierarchy.value,
    )


if __name__ == "__main__":
    main()
