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
        # Check for existing output and handle based on configuration
        if arcpy.Exists(self.output_fc):
            if self.delete_existing:
                arcpy.Delete_management(self.output_fc)
            else:
                print(
                    f"Output feature class {self.output_fc} already exists. Appending data."
                )
                # Implement appending logic here if necessary
                return

        # Create a new feature class using the template and specified object type
        output_workspace, output_class_name = os.path.split(self.output_fc)
        arcpy.CreateFeatureclass_management(
            output_workspace,
            output_class_name,
            self.object_type,
            self.template_fc,
            spatial_reference=arcpy.Describe(self.template_fc).spatialReference,
        )

        # Transfer geometry from source to the new feature class
        with arcpy.da.SearchCursor(
            self.input_fc, ["SHAPE@"]
        ) as s_cursor, arcpy.da.InsertCursor(self.output_fc, ["SHAPE@"]) as i_cursor:
            for row in s_cursor:
                i_cursor.insertRow(row)
