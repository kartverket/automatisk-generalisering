from dataclasses import field

import arcpy
import os
import re

import env_setup.global_config


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


class WorkFileManager2:
    general_files_directory_name = env_setup.global_config.general_files_name
    lyrx_directory_name = env_setup.global_config.lyrx_directory_name

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
        self.created_paths = []

        if not self.write_to_memory and not self.root_file:
            raise ValueError(
                "Need to specify root_file path to write to disk for work files."
            )

        if self.keep_files and not self.root_file:
            raise ValueError(
                "Need to specify root_file path and write to disk to keep work files."
            )

        self.file_location = "memory/" if self.write_to_memory else f"{self.root_file}_"

    def modify_path(self) -> str:
        """
        Modifies the given path by removing the unwanted portion up to the scale directory.

        Returns:
            str: The modified path.
        """
        # Define regex pattern to find the scale directory (ends with a digit followed by \\)
        match = re.search(r"\\\w+\d0\\", self.root_file)
        if not match:
            raise ValueError("Scale directory pattern not found in the path.")
        if self.write_to_memory:
            raise ValueError(
                "Other file types than gdb are not supported in memory mode."
            )

        # Extract the root up to the scale directory
        scale_path = self.root_file[: match.end()]

        return scale_path

    def _build_file_path(
        self,
        file_name: str,
        file_type: str = "gdb",
    ) -> str:
        """
        Constructs a file path based on the file name and type.
        """

        if file_type == "gdb":
            path = f"{self.file_location}{file_name}_{self.unique_id}"
        else:
            scale_path = self.modify_path()

            if file_type == "lyrx":
                path = rf"{scale_path}{self.lyrx_directory_name}\{file_name}_{self.unique_id}.lyrx"

            else:
                path = rf"{scale_path}{self.general_files_directory_name}\{file_name}_{self.unique_id}.{file_type}"

        self.created_paths.append(path)
        return path

    def setup_work_file_paths(
        self,
        instance,
        file_structure,
        keys_to_update=None,
        add_key=None,
        file_type="gdb",
    ):
        """
        Generates file paths for supported structures and sets them as attributes on the instance.

        Parameters:
        - instance: The class instance to set attributes on.
        - file_structure: The input structure (str, list, dict) containing file names.
        - keys_to_update: (Optional) Keys to update in the file_structure. Pass "ALL" to update all keys.
        - add_key: (Optional) Add a new key to the structure with constructed paths.
        - file_type: The type of file for path construction (default: "gdb").
        """
        if isinstance(file_structure, str):
            path = self._build_file_path(file_structure, file_type)
            setattr(instance, file_structure, path)
            return path

        if isinstance(file_structure, list):
            updated_list = [
                self.setup_work_file_paths(
                    instance, item, keys_to_update, add_key, file_type
                )
                for item in file_structure
            ]
            setattr(instance, "file_list", updated_list)
            return updated_list

        if isinstance(file_structure, dict):
            updated = {}
            for key, value in file_structure.items():
                if keys_to_update == "ALL" or (
                    keys_to_update and key in keys_to_update
                ):
                    updated_value = self.setup_work_file_paths(
                        instance,
                        value,
                        keys_to_update=None,
                        add_key=None,
                        file_type=file_type,
                    )
                    updated[key] = updated_value
                    setattr(instance, key, updated_value)
                else:
                    updated[key] = value

            if add_key:
                # Construct paths for the added key and set them as an attribute
                added_path = self._build_file_path(
                    file_name=add_key, file_type=file_type
                )
                updated[add_key] = added_path
                setattr(instance, add_key, added_path)

            return updated

        raise TypeError(f"Unsupported file structure type: {type(file_structure)}")

    def delete_created_files(
        self,
        delete_targets=None,
        exceptions=None,
        delete_files=None,
    ):
        """
        Deletes created file paths, optionally filtering by targets or exceptions.

        Parameters:
        - delete_targets: (Optional) List of paths to delete. Defaults to all created paths.
        - exceptions: (Optional) List of paths to exclude from deletion.
        - delete_files: (Optional) Boolean flag to determine whether to delete files.
                        Defaults to the value of `self.keep_files`.
        """
        # Default to `self.keep_files` if `delete_files` is not explicitly provided
        if delete_files is None:
            delete_files = not self.keep_files

        if not delete_files:
            print("Deletion is disabled. No files deleted.")
            return

        # Use all tracked paths if delete_targets is not provided
        targets = delete_targets or self.created_paths

        # Apply exceptions, if provided
        if exceptions:
            targets = [path for path in targets if path not in exceptions]

        for path in targets:
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

    @staticmethod
    def apply_to_dicts(data_list, func, **key_map):
        """
        Applies a function to each dictionary in a list by matching specified keys.

        Args:
            data_list (list[dict]): The list of dictionaries to process.
            func (callable): The function to apply. The keys in `key_map` should match the function parameters.
            **key_map (str): Mapping of function parameter names to dictionary keys.

        Raises:
            KeyError: If a required key is missing from a dictionary.
        """
        if isinstance(data_list, list) and all(
            isinstance(item, dict) for item in data_list
        ):
            print(f"\n\ndata_list is a list: {data_list}\n\n")

        for dictionary in data_list:
            try:
                # Map function parameters to the corresponding dictionary values
                func(**{param: dictionary[key] for param, key in key_map.items()})
            except KeyError as e:
                raise KeyError(f"Missing key {e} in dictionary: {dictionary}")


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
