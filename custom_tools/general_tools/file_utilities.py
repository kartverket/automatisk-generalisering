from dataclasses import field

import arcpy
import os
import re
from typing import Union, List, Dict, Any

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


class WorkFileManager:
    """
    What:
        This class handles the creation and deletion of work files used in other classes or processes.
        It is designed to make it easy to switch between writing to disk and in-memory, and to
        delete/stop deleting work files to better troubleshoot issues.
        This class is not intended to be used to create final outputs of logics or processes.

    How:
        The same instance of WorkFileManager can create and manage different structures containing files.
        for each call of the setup_work_file_paths is designed to take a single structure. Each file path
        generated by the WorkFileManager is tracked by the created_paths attribute so if you do not need
        stage the deletion of the files you can simply call the delete_created_files method without
        any parameters.

    Args:
        unique_id (int): Used to generate unique file names, can be self value or an iterated number.
        root_file (str): The core file name used to generate unique file names.
        write_to_memory (bool): Defaults to True, write to memory if True, write to disk if False.
        keep_files (bool): Defaults to False, delete work files if True, keep work files if False.
    """

    general_files_directory_name = env_setup.global_config.general_files_name
    lyrx_directory_name = env_setup.global_config.lyrx_directory_name

    def __init__(
        self,
        unique_id: int,
        root_file: str = None,
        write_to_memory: bool = True,
        keep_files: bool = False,
    ):
        """
        Initializes the WorkFileManager with the desired parameters.

        Args:
            See class docstring.
        """

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

    def _modify_path(self) -> tuple[str, str]:
        """
        What:
            Modifies the given path by removing the unwanted portion up to the scale directory.

        Returns:
            tuple[str,str]: The modified path.
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

        # Extract the origin file name from the remaining path
        origin_file_name = self.root_file[match.end() :].rstrip("\\")
        return scale_path, origin_file_name

    def _build_file_path(
        self,
        file_name: str,
        file_type: str = "gdb",
        index: int = None,
    ) -> str:
        """
        Generates a file path based on the file name, type, and an optional index.

        Args:
            file_name (str): The name of the file.
            file_type (str): The type of file to generate the path for.
            index (int, optional): An optional index to append for uniqueness.

        Returns:
            str: A string representing the file path.
        """
        suffix = f"___{index}" if index is not None else ""
        if file_type == "gdb":
            path = f"{self.file_location}{file_name}_{self.unique_id}{suffix}"
        else:
            scale_path, origin_file_name = self._modify_path()

            if file_type == "lyrx":
                path = rf"{scale_path}{self.lyrx_directory_name}\{origin_file_name}_{file_name}_{self.unique_id}{suffix}.lyrx"
            else:
                path = rf"{scale_path}{self.general_files_directory_name}\{origin_file_name}_{file_name}_{self.unique_id}{suffix}.{file_type}"

        if path in self.created_paths:
            raise ValueError(
                f"Duplicate path detected: {path}. "
                "This may lead to unexpected behavior. Ensure unique file names or indices."
            )

        self.created_paths.append(path)
        return path

    def setup_work_file_paths(
        self,
        instance: object,
        file_structure: Any,
        keys_to_update: str = None,
        add_key: str = None,
        file_type: str = "gdb",
        index: int = None,
    ) -> Any:
        """
        What:
            Generates file paths for supported structures and sets them as attributes on the instance.
            Currently tested and supported structures include:
            - str
            - list[str]
            - dict[str, str]
            - list[dict[str, str]]

        Args:
            instance (object): The instance to set the file paths as attributes on.
            file_structure (Any): The input structure to process and return.
            keys_to_update (str, optional): Keys to update if file_structure is a dictionary.
            add_key (str, optional): An additional key to add to the dictionary.
            file_type (str, optional): The type of file path to generate. Defaults to "gdb".
            index (int, optional): Index to ensure uniqueness in file names when processing lists of dicts.

        Returns:
            Any: The same structure as file_structure, updated with generated file paths.
        """

        def process_item(item, idx=None):
            """Processes a single item, determining its type and handling it accordingly."""
            if isinstance(item, str):
                return self._build_file_path(item, file_type, index=idx)
            elif isinstance(item, dict):
                return process_dict(item, idx)
            elif isinstance(item, list):
                return process_list(item)
            else:
                raise TypeError(f"Unsupported file structure type: {type(item)}")

        def process_list(items):
            """Processes a list structure."""
            if all(isinstance(item, dict) for item in items):
                # List of dictionaries
                return [process_dict(item, idx) for idx, item in enumerate(items)]
            else:
                # List of other items (e.g., strings)
                return [process_item(item) for item in items]

        def process_dict(dictionary, idx=None):
            """Processes a dictionary structure."""
            updated_dict = {}
            for key, value in dictionary.items():
                if keys_to_update == "ALL" or (
                    keys_to_update and key in keys_to_update
                ):
                    updated_dict[key] = process_item(value, idx)
                else:
                    updated_dict[key] = value

            if add_key:
                updated_dict[add_key] = self._build_file_path(
                    add_key, file_type, index=idx
                )

            return updated_dict

        # Determine the type of the top-level structure and process accordingly
        return process_item(file_structure)

    def delete_created_files(
        self,
        delete_targets: list[str] = None,
        exceptions: list[str] = None,
        delete_files: list[str] = None,
    ):
        """
        What:
            Deletes the created paths, defaults to deleting all created paths,
            but can target or exclude specific paths.

        Args:
            delete_targets (list[str], optional): List of paths to delete. Defaults to None.
            exceptions (list[str], optional): List of paths to exclude from deletion. Defaults to None.
            delete_files (bool, optional): Whether to delete files. Defaults to None, which uses `self.keep_files`.
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
    def list_contents(data: Any, title: str = "Contents"):
        """
        Pretty prints the contents of a data structure (list, dict, or other serializable objects).

        Args:
            data (Any): The data structure to print (list, dict, or other serializable objects).
            title (str, optional): A title to display before printing. Defaults to "Contents".
        """
        print(f"\n{f' Start of: {title} ':=^120}")
        if isinstance(data, (list, dict)):
            import pprint

            pprint.pprint(data, indent=4)
        else:
            print(data)
        print(f"{f' End of: {title} ':=^120}\n")

    @staticmethod
    def _delete_file(file_path: str):
        """
        Deletes a file from disk.
        """
        try:
            if arcpy.Exists(file_path):
                arcpy.management.Delete(file_path)
                print(f"Deleted: {file_path}")
            else:
                print(f"File did not exist: {file_path}")
        except arcpy.ExecuteError as e:
            print(f"Error deleting file {file_path}: {e}")

    @staticmethod
    def apply_to_structure(data, func, **key_map):
        """
        What:
            Applies a function to elements within a supported data structure.
            Designed to work with dictionaries, lists of dictionaries, and extensible for other structures.

        How:
            Maps specified keys in the data structure to the function's parameters
            and applies the function to each valid element.

        Args:
            data (Union[dict, list[dict]]): The data structure to process.
            func (callable): The function to apply. The keys in `key_map` should match the function parameters.
            **key_map (str): Mapping of function parameter names to keys in the data structure.

        Raises:
            TypeError: If the data type is unsupported.
            KeyError: If a required key is missing in a dictionary.
        """

        def process_item(item):
            """Helper function to process a single dictionary."""
            try:
                func(**{param: item[key] for param, key in key_map.items()})
            except KeyError as e:
                raise KeyError(f"Missing key {e} in dictionary: {item}")

        if isinstance(data, dict):
            process_item(data)

        elif isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                for item in data:
                    process_item(item)
            else:
                raise TypeError(
                    "List must contain only dictionaries. "
                    f"Found invalid item in list: {data}"
                )

        else:
            raise TypeError(
                f"Unsupported data type: {type(data)}. "
                "Expected a dictionary or a list of dictionaries."
            )


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
