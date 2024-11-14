import arcpy

from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import environment_setup


def main():
    environment_setup.main()
    run_cleanup()


def run_cleanup():
    keep_necessary_fields(
        input_layers=[
            Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
            Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
            Building_N100.data_preparation___unsplit_roads___n100_building.value,
            Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            Building_N100.point_resolve_building_conflicts___building_points_squares___n100_building.value,
        ],
    )


def keep_necessary_fields(input_layers: list[str], list_of_fields: list[str] = None):
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
        :param list_of_fields:
        :param input_layers:
    """
    # Provide the path to your feature class
    if list_of_fields is None:
        list_of_fields = []

    important_processing_fields = [
        "symbol_val",
        "invisibility",
        "hierarchy",
        "byggtyp_nbr",
        "angle",
    ]

    symbology_fields = [
        "subtypekode",
        "motorvegtype",
        "UTTEGNING",
        "SUBTYPEKODE",
        "MOTORVEGTYPE",
    ]

    # List of field names to keep
    fields_to_keep = (
        [
            "OBJECTID",
            "Shape_Area",
            "shape_Area",
            "Shape",
            "shape",
            "Shape_Length",
            "shape_Length",
        ]
        + important_processing_fields
        + symbology_fields
        + list_of_fields
    )

    # Process each input layer
    for feature_class_to_clean_up in input_layers:
        # Get a list of all fields in the feature class
        all_fields = [
            field.name for field in arcpy.ListFields(feature_class_to_clean_up)
        ]

        # Identify fields to delete (inverse of fields to keep)
        fields_to_delete = [
            field for field in all_fields if field not in fields_to_keep
        ]

        # Check if there are fields to delete
        if fields_to_delete:
            try:
                arcpy.management.DeleteField(
                    feature_class_to_clean_up, fields_to_delete
                )
                print(
                    f"Deleted fields in {feature_class_to_clean_up}: {fields_to_delete}"
                )

                # Print the fields that are kept
                print(f"Kept fields in {feature_class_to_clean_up}: {fields_to_keep}")
            except arcpy.ExecuteError:
                print(arcpy.GetMessages(2))
        else:
            print(f"No fields to delete in {feature_class_to_clean_up}.")


if __name__ == "__main__":
    main()
