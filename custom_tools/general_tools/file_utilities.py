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
        with arcpy.da.SearchCursor(
            self.input_fc, ["SHAPE@"]
        ) as s_cursor, arcpy.da.InsertCursor(self.output_fc, ["SHAPE@"]) as i_cursor:
            for row in s_cursor:
                i_cursor.insertRow(row)
        print("Appended geometry to the feature class.")


class WorkFileManager:
    def __init__(
        self,
        unique_id: int,
        root_file: str = None,
        write_to_memory: bool = True,
        keep_files: bool = False,
    ):
        self.unique_id = unique_id
        self.root_file = root_file
        self.write_to_memory = write_to_memory
        self.keep_files = keep_files

        if not self.write_to_memory and not self.root_file:
            raise ValueError(
                "Need to specify root_file path to write to disk for work files."
            )

        if self.keep_files and not self.root_file:
            raise ValueError(
                "Need to specify root_file path and write to disk to keep work files."
            )

        self.file_location = "memory/" if self.write_to_memory else f"{self.root_file}_"

    def _build_file_path(self, file_name: str) -> str:
        return f"{self.file_location}{file_name}_{self.unique_id}"

    def setup_work_file_paths(self, instance, file_names):
        """
        Generates file paths and sets them as attributes on the instance.
        Updates the file_names list with the new paths.
        Can handle a list of file names or a list of lists of file names.
        """
        if isinstance(file_names[0], list):
            for sublist in file_names:
                for i, name in enumerate(sublist):
                    path = self._build_file_path(name)
                    setattr(instance, name, path)
                    sublist[i] = path
        else:
            for i, name in enumerate(file_names):
                path = self._build_file_path(name)
                setattr(instance, name, path)
                file_names[i] = path

    def _build_file_path_lyrx(self, file_name: str) -> str:
        return f"{self.file_location}{file_name}_{self.unique_id}.lyrx"

    def setup_work_file_paths_lyrx(self, instance, file_names):
        """
        Generates file paths and sets them as attributes on the instance.
        Updates the file_names list with the new paths.
        Can handle a list of file names or a list of lists of file names.
        """
        if isinstance(file_names[0], list):
            for sublist in file_names:
                for i, name in enumerate(sublist):
                    path = self._build_file_path_lyrx(name)
                    setattr(instance, name, path)
                    sublist[i] = path
        else:
            for i, name in enumerate(file_names):
                path = self._build_file_path_lyrx(name)
                setattr(instance, name, path)
                file_names[i] = path

    def cleanup_files(self, file_paths):
        """
        Deletes files. Can handle a list of file paths or a list of lists of file paths.
        """
        if isinstance(file_paths[0], list):
            for sublist in file_paths:
                for path in sublist:
                    self._delete_file(path)
        else:
            for path in file_paths:
                self._delete_file(path)

    @staticmethod
    def _delete_file(file_path: str):
        try:
            if arcpy.Exists(file_path):
                arcpy.management.Delete(file_path)
                print(f"Deleted: {file_path}")
            else:
                print(f"File did not exist: {file_path}")
        except arcpy.ExecuteError as e:
            print(f"Error deleting file {file_path}: {e}")


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
