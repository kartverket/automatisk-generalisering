import arcpy
import os


class FeatureClassCreator:
    def __init__(
        self,
        template_fc,
        input_fc,
        output_fc,
        object_type="POLYGON",
        delete_existing=False,
    ):
        """
        Initializes the FeatureClassCreator with required parameters.

        Parameters:
        - template_fc (str): The path to the template feature class used to define the schema.
        - input_fc (str): The path to the input feature class from which to append the geometry.
        - output_fc (str): The path to the output feature class to create and append to.
        - object_type (str): The type of geometry for the new feature class ("POINT", "MULTIPOINT", "LINE", "POLYLINE", "POLYGON", or "MULTIPATCH").
        - delete_existing (bool): Whether to delete the existing output feature class if it exists. If set to False the geometry will be appended to the existing output feature class.

        Example Usage:
        --------------
        >>> feature_creator = FeatureClassCreator(
        ...     template_fc='path/to/template_feature_class',
        ...     input_fc='path/to/input_feature_class',
        ...     output_fc='path/to/output_feature_class',
        ...     object_type='POLYGON',
        ...     delete_existing=True
        ... )
        >>> feature_creator.run()

        This initializes the creator with all parameters and creates a new feature class based on the provided template,
        optionally deleting any existing feature class at the output path, and appends the geometry from the input feature class.
        """
        self.template_fc = template_fc
        self.input_fc = input_fc
        self.output_fc = output_fc
        self.object_type = object_type
        self.delete_existing = delete_existing

    def run(self):
        """
        Executes the process of creating a new feature class and appending geometry from the input feature class.
        """
        if arcpy.Exists(self.output_fc):
            if self.delete_existing:
                # Deletes the output file if it exists and delete_existing boolean is set to True
                arcpy.Delete_management(self.output_fc)
                print(f"Deleted existing feature class: {self.output_fc}")
                # Creates a new feature class after deletion
                self._create_feature_class()
            else:
                # If output exists and delete_existing is set to False, just append data.
                print(
                    f"Output feature class {self.output_fc} already exists. Appending data."
                )
        else:
            if self.delete_existing:
                print("Output feature class does not exist, so it was not deleted.")
            # If output does not exist, create a new feature class
            self._create_feature_class()

        # Append geometry as the final step, occurring in all scenarios.
        self._append_geometry()

    def _create_feature_class(self):
        """
        Creates a new feature class using the specified template and object type.
        """
        output_workspace, output_class_name = os.path.split(self.output_fc)
        arcpy.CreateFeatureclass_management(
            output_workspace,
            output_class_name,
            self.object_type,
            self.template_fc,
            spatial_reference=arcpy.Describe(self.template_fc).spatialReference,
        )
        print(f"Created new feature class: {self.output_fc}")

    def _append_geometry(self):
        """
        Appends geometry from the input feature class to the output feature class.
        This method assumes the output feature class already exists or was just created.
        """
        with (
            arcpy.da.SearchCursor(self.input_fc, ["SHAPE@"]) as s_cursor,
            arcpy.da.InsertCursor(self.output_fc, ["SHAPE@"]) as i_cursor,
        ):
            for row in s_cursor:
                i_cursor.insertRow(row)
        print("Appended geometry to the feature class.")


def compare_feature_classes(feature_class_1, feature_class_2):
    # Get count of features in the first feature class
    count_fc1 = int(arcpy.GetCount_management(feature_class_1)[0])

    # Get count of features in the second feature class
    count_fc2 = int(arcpy.GetCount_management(feature_class_2)[0])

    # Calculate the difference
    difference = count_fc2 - count_fc1

    # Determine the appropriate message
    if difference > 0:
        print(f"There are {difference} more features in the second feature class.")
    elif difference < 0:
        print(f"There are {-difference} fewer features in the second feature class.")
    else:
        print("Both feature classes have the same number of features.")


def reclassify_value(
    input_table: str,
    target_field: str,
    target_value: str,
    replace_value: str,
    reference_field: str = None,
    logic_format: str = "PYTHON3",
) -> None:
    update_missing_block = f"""def Reclass(value):
        if value == {target_value}:
            return {replace_value}
        else:
            return value
    """

    value_field = reference_field if reference_field else target_field

    arcpy.management.CalculateField(
        in_table=input_table,
        field=target_field,
        expression=f"Reclass(!{value_field}!)",
        expression_type=logic_format,
        code_block=update_missing_block,
    )


def deleting_added_field_from_feature_to_x(
    input_file_feature: str = None,
    field_name_feature: str = None,
) -> None:
    directory_path, split_file_name = os.path.split(field_name_feature)

    print("Directory path:", directory_path)
    print("Filename:", split_file_name)
    esri_added_prefix = "FID_"
    generated_field_name = f"{esri_added_prefix}{split_file_name}"[:64]
    generated_field_name_with_underscore = (
        f"{generated_field_name[:-1]}_"
        if len(generated_field_name) == 64
        else generated_field_name
    )

    # List fields in the feature
    feature_fields = arcpy.ListFields(input_file_feature)
    list_of_fields = [field_object.name for field_object in feature_fields]

    if generated_field_name in list_of_fields:
        field_to_delete = generated_field_name
    elif generated_field_name_with_underscore in list_of_fields:
        field_to_delete = generated_field_name_with_underscore
    else:
        raise ValueError(
            f"""
                The generated field name by Esri Geoprocessing tool did not match the predicted naming convention for the file:\n
                {input_file_feature}\n
                Expected name (without underscore): {generated_field_name}\n
                Expected name (with underscore): {generated_field_name_with_underscore}\n
                Available fields:\n{list_of_fields}
            """
        )

    try:
        arcpy.management.DeleteField(
            in_table=input_file_feature,
            drop_field=field_to_delete,
        )
        print(f"Deleted field: {field_to_delete}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_all_fields(input_fields, *added_field_sets):
    """
    Combines an input fields list with any number of additional field sets.
    Assumes each added field set is a list of [field_name, field_type] pairs.
    """
    combined = list(input_fields)
    for fields in added_field_sets:
        combined.extend([item[0] for item in fields])
    return combined


def count_objects(input_layer):
    count = int(arcpy.management.GetCount(input_layer).getOutput(0))
    return count
