import arcpy

# Importing custom files relative to the root path
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.geometry_tools import GeometryValidator

# Importing temporary files
from file_manager.n100.file_manager_buildings import Building_N100

# Import modules
import datetime as dt


# Main function
@timing_decorator
def main():
    """
    What:
        Deletes all fields for each feature expect the fields which should be kept in the delivered product.
        Then adds last edited date and finally checks and potentially repairs the geometry of each feature.
    How:
        keep_necessary_fields:
            It runs the keep_necessary_fields function for each feature keeping only required fields.

        add_last_edited_date_to_all_feature_classes:
            Adds a 'last_edited_date' field to specified feature classes and sets it to the current date and time.

        check_and_repair_geometry:
            Checks and potentially repairs geometry for the final outputs.
    Why:
        For each feature there should be no other field present other than the ones which is specified.
    """

    environment_setup.main()
    keep_necessary_fields(
        input_layer=Building_N100.BygningsPunkt.value,
        list_of_fields=[
            "objtype",
            "byggtyp_nbr",
            "målemetode",
            "nøyaktighet",
            "last_edited_date",
        ],
    )
    keep_necessary_fields(
        input_layer=Building_N100.Grunnriss.value,
        list_of_fields=["objtype", "byggtyp_nbr", "last_edited_date"],
    )
    keep_necessary_fields(
        input_layer=Building_N100.TuristHytte.value,
        list_of_fields=[
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
        input_layer=Building_N100.OmrissLinje.value,
        list_of_fields=["objtype", "målemetode", "nøyaktighet", "last_edited_date"],
    )
    keep_necessary_fields(
        input_layer=Building_N100.Piktogram.value,
        list_of_fields=["byggtyp_nbr", "last_edited_date"],
    )

    check_and_repair_geometry()

    add_last_edited_date_to_all_feature_classes()


@timing_decorator
def keep_necessary_fields(input_layer: str, list_of_fields: list[str]):
    """
    What:
        Deletes all fields from the input feature class except for a fields specified in a list.

    How:
        Retrieves all fields from the input feature. It has a static set of fields always to be kept regardless
        of parameter input. It then removes all static and provided fields from the list of fields to remove.
        Then deletes all unspecified fields.

    Args:
        input_layer (str): The input feature to clean up.
        list_of_fields (list[str]): The fields to be kept in addition to static fields.
    """
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
    """
    Adds a 'last_edited_date' field to specified feature classes and sets it to the current date and time.
    """
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

        print(f"Added last edited date: '{current_date}' for '{feature_class}'.")


def check_and_repair_geometry():
    """
    Checks and potentially repairs geometry for the final outputs.
    """
    input_features_validation = {
        "building_points": Building_N100.BygningsPunkt.value,
        "building_polygons": Building_N100.Grunnriss.value,
        "tourist_huts": Building_N100.TuristHytte.value,
        "omriss_linje": Building_N100.OmrissLinje.value,
        "piktogram": Building_N100.Piktogram.value,
    }

    data_validation = GeometryValidator(
        input_features=input_features_validation,
        output_table_path=Building_N100.data_cleanup___geometry_validation___n100_building.value,
    )
    data_validation.check_repair_sequence()


if __name__ == "__main__":
    main()
