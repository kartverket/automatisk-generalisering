import arcpy

# Importing custom files relative to the root path
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100


# Main function
def main():
    environment_setup.main()
    clean_up_fields_delete()


@timing_decorator
def clean_up_fields_delete():
    # Provide the path to your feature class
    feature_class_to_clean_up = (
        Building_N100.grunnriss_to_point__grunnriss_feature_to_point__n100.value
    )  # Switch out to correct feature class

    # List of field names to delete
    fields_to_delete = [
        "CLUSTER_ID",
        "COLOR_ID",
        "symbol_val",
        "angle",
        "hierarchy",
        "invisibility",
        "ORIG_FID",
        "InBld_FID" "TARGET_FID",
        "BLD_STATUS",
        "InBld_FID_1",
        "BLD_STATUS_1",
    ]

    # Get a list of all fields in the feature class
    all_fields = [field.name for field in arcpy.ListFields(feature_class_to_clean_up)]

    # Identify fields to keep (inverse of fields to delete)
    fields_to_keep = [field for field in all_fields if field not in fields_to_delete]

    # Check if there are fields to keep
    if fields_to_keep:
        try:
            arcpy.management.DeleteField(feature_class_to_clean_up, fields_to_delete)
            print(f"Deleted fields: {fields_to_delete}")

            # Optionally, print the fields that are kept
            print(f"Kept fields: {fields_to_keep}")
        except arcpy.ExecuteError:
            print(arcpy.GetMessages(2))
    else:
        print("No fields to keep.")


if __name__ == "__main__":
    main()
