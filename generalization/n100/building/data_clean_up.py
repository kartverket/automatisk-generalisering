import arcpy

# Importing custom files relative to the root path
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100


# Main function
@timing_decorator("data_clean_up.py")
def main():
    environment_setup.main()
    keep_necessary_fields()


@timing_decorator
def keep_necessary_fields():
    # Provide the path to your feature class
    feature_class_to_clean_up = (
        Building_N100.simplify_polygons___aggregated_polygons_to_points___n100_building.value
    )  # Switch out to correct feature class

    # List of field names to keep
    fields_to_keep = [
        "FIELD1",
        "FIELD2",
        "FIELD3",
        # Add more field names as needed
    ]

    # Get a list of all fields in the feature class
    all_fields = [field.name for field in arcpy.ListFields(feature_class_to_clean_up)]

    # Identify fields to delete (inverse of fields to keep)
    fields_to_delete = [field for field in all_fields if field not in fields_to_keep]

    # Check if there are fields to delete
    if fields_to_delete:
        try:
            arcpy.management.DeleteField(feature_class_to_clean_up, fields_to_delete)
            print(f"Deleted fields: {fields_to_delete}")

            # Print the fields that are kept
            print(f"Kept fields: {fields_to_keep}")
        except arcpy.ExecuteError:
            print(arcpy.GetMessages(2))
    else:
        print("No fields to delete.")


def add_last_edited_date():

    arcpy.AddField_management(
        in_table=Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value,
        field_name="symbol_val",
        field_type="SHORT",
    )

    # Determining and assigning symbol val
    arcpy.CalculateField_management(
        in_table=Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value,
        field="symbol_val",
        expression="determineVal(!BYGGTYP_NBR!)",
        expression_type="PYTHON3",
        code_block=N100_SQLResources.nbr_symbol_val_code_block.value,
    )


if __name__ == "__main__":
    main()
