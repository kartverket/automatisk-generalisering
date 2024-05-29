import arcpy

# Importing custom files relative to the root path
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100

# Import modules
import datetime as dt


# Main function
@timing_decorator
def main():
    environment_setup.main()
    keep_necessary_fields(
        Building_N100.BygningsPunkt.value,
        ["objtype", "byggtyp_nbr", "målemetode", "nøyaktighet", "last_edited_date"],
    )
    keep_necessary_fields(
        Building_N100.Grunnriss.value, ["objtype", "byggtyp_nbr", "last_edited_date"]
    )
    keep_necessary_fields(
        Building_N100.TuristHytte.value,
        [
            "objtype",
            "byggtyp_nbr",
            "betjeningsgrad",
            "hytteeier",
            "hyttetilgjengelighet",
            "navn",
            "målemetode",
            "nøyaktighet",
            "last_edited_date",
        ],
    )
    keep_necessary_fields(
        Building_N100.OmrissLinje.value,
        ["objtype", "målemetode", "nøyaktighet", "last_edited_date"],
    )
    keep_necessary_fields(
        Building_N100.Piktogram.value, ["byggtyp_nbr", "last_edited_date"]
    )
    add_last_edited_date_to_all_feature_classes()


@timing_decorator
def keep_necessary_fields(input_layer, list_of_fields):
    # Provide the path to your feature class
    feature_class_to_clean_up = input_layer

    # List of field names to keep
    fields_to_keep = [
        "OBJECTID",
        "Shape_Area",
        "Shape",
        "Shape_Length",
    ] + list_of_fields

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


def add_last_edited_date_to_all_feature_classes():
    all_final_layers = [
        Building_N100.BygningsPunkt.value,
        Building_N100.Grunnriss.value,
        Building_N100.TuristHytte.value,
        Building_N100.OmrissLinje.value,
        Building_N100.Piktogram.value,
    ]

    for layer in all_final_layers:
        feature_class = layer
        field_name = "last_edited_date"

        # Check if the field already exists
        existing_fields = [field.name for field in arcpy.ListFields(feature_class)]
        if field_name in existing_fields:
            print(f"The field '{field_name}' already exists in '{feature_class}'.")
        else:
            # Add the field if it doesn't exist
            arcpy.AddField_management(
                in_table=feature_class,
                field_name=field_name,
                field_type="DATE",
            )

        # Calculate last_edited_date
        current_date = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        arcpy.CalculateField_management(
            in_table=feature_class,
            field=field_name,
            expression=f"'{current_date}'",
            expression_type="PYTHON3",
        )


if __name__ == "__main__":
    main()
