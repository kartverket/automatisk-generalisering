import arcpy
import os
import re
import shutil
import random
import json
from typing import Dict, Tuple, Literal, Union, List
import time
from datetime import datetime
import pprint
import inspect

from composition_configs.core_config import PartitionIOConfig
from composition_configs import core_config
import env_setup.global_config
import config
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
from custom_tools.decorators.timing_decorator import timing_decorator

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools.polygon_processor import PolygonProcessor


from custom_tools.generalization_tools.building.buffer_displacement import (
    BufferDisplacement,
)
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


class PartitionIterator:
    """
    This class handles processing of processing intense operations for large data sources using partitions.
    Differentiating between which data is important and which are needed for context it processes as little
    data as possible saving time. It then iterates over the partitions selecting data, and doing any amount
    of logic on the selections, finally appending the defined result to an output file.

    **Alias and Type Terminology:**

    - **Alias:** A named reference to a dataset. Each alias represents a specific dataset that will be used
      as an input during partitioning. Aliases allow the class to organize and reference datasets
      consistently across different logics.

    - **Type:** Each alias can have multiple types, indicating different versions the dataset can be accessed during
      partitioning process. A type holds a path. This makes it so that if you run multiple logics in partition iterator
      you can still access any of the outputs at any point for each alias.

    **Setting Up `alias_path_data` and `alias_path_outputs`:**

    - **`alias_path_data`**: A dictionary used to define the input datasets for the class. Each key is an alias,
      and its value is a list of tuples where the first element is a type, and the second element is the path to the dataset.
      The type of must be either 'input', 'context', 'reference' in `alias_path_data`. In a sense alias_path_data
      works to load in all the data you are going to use in an instance of partition iterator.
      So if you have different logics using inputs all the data used by all logics are entered in alias_path_data.


    - **`alias_path_outputs`**: A dictionary used to define the output datasets for the class. Each key is an alias,
      and its value is a list of tuples where the first element is the output type (e.g., 'processed_output') and
      the second element is the path where the output should be saved. This means that you can have multiple outputs
      for each alias.

    **Important: Reserved Types for Alias:**

    The following types are reserved for use by the class and should not be used to create new output types in logic configs:
      - **"input"**:
        Used for input datasets provided to the class. Is the focus of the processing. If you in a config want to use
        the partition selection of the original input data as an input this is the type which should be used.
      - **"context"**:
        Represents context data used during processing. This data is not central and will be selected based on proximity
        to input data. If you in a config want to use the partition selection of the original context data as an input
        this is the type which should be used.
      - **"reference"**:
        Represents reference datasets that are completely static and will not be processed in any way.
        An example could be a lyrx file.
      - **"input_copy"**:
        Internal type used to hold a copy of the global input data. Should not be used in configs.
      - **"context_copy"**:
        Internal type used to hold a copy of the global context data. Should not be used in configs.

    New types should only be created during the outputs from configs in custom_functions, and they should not use any
    of the reserved types listed above if you intend it to be a new output. So for instance an operation doing a buffer
    on the "input" type of alias should not have an output using the "input" type, but for instance "buffer". If you
    in the next config want to use the buffer output, use the "buffer" type for the alias as an input for the next config.

    **Custom Function Configuration:**

    - The `custom_functions` parameter is a list of function configurations, where each configuration describes
      a custom function (standalone or a method of a class) to be executed during the partitioning process.
    - The input and output parameters needs to be defined using the partition_io_decorator. A logic can have multiple
      input and output parameter. for each function are defined as tuples of `(alias, type)`. The alias refers
      to a named dataset, while the type specifies whether the dataset is used as an input or an output.
    - Custom functions must be decorated with the `partition_io_decorator` to mark which parameters are inputs
      and which are outputs. Only parameters marked as inputs or outputs will be managed by this system.
    - Outputs can create new types associated with an alias, and these new types will have paths dynamically
      generated by the class. These new types can then be used as inputs for other functions in subsequent
      iterations.
    - The class itself can write any existing alias to its final output, but it cannot create new types for
      the alias.

    **Important Notes:**

    - Any function (or class method) included in `custom_functions` must be decorated with the `partition_io_decorator`.
      For class methods, this means the method being used in `custom_functions`, not the entire class, must be decorated.
    - During processing, the class dynamically resolves the paths for both input and output datasets based on the
      `(alias, type)` tuples. New paths for outputs will be created automatically, and these outputs can then be used
      in future iterations as inputs with the corresponding alias and type.
    - Multiple outputs for a single alias can exist, but only previously defined types can be used as inputs for
      the class’s output.

    Args:
        alias_path_data (Dict[str, Tuple[str, str]]):
            A dictionary where the key is an alias (representing a dataset), and the value is a tuple containing
            the type of data (e.g., 'input', 'context') and the path to the dataset.
        alias_path_outputs (Dict[str, Tuple[str, str]]):
            A dictionary where the key is an alias (representing a dataset), and the value is a tuple containing
            the type of output and the path where the results should be saved.
        root_file_partition_iterator (str):
            The base path for intermediate outputs generated during the partitioning process.
        custom_functions (list, optional):
            A list of configurations for the custom functions that will be executed during the partitioning process.
            Each function must be configured with the `partition_io_decorator` and have its input/output parameters
            specified.
        dictionary_documentation_path (str, optional):
            The path where documentation related to the partitioning process (e.g., JSON logs) will be stored.
        feature_count (str, optional):
            The maximum number of features allowed in each partition. Default is "15000".
        partition_method (Literal['FEATURES', 'VERTICES'], optional):
            The method used to create partitions, either by the number of features ('FEATURES') or vertices ('VERTICES').
            Default is 'FEATURES'.
        search_distance (str, optional):
            The distance within which context features are selected relative to input features. Default is '500 Meters'.
        context_selection (bool, optional):
            Whether to enable context feature selection based on proximity to input features. Default is True.
        delete_final_outputs (bool, optional):
            Whether to delete existing final outputs before starting the partitioning process. Default is True.
        safe_output_final_cleanup (bool, optional):
            Whether to enable safe deletion of outputs during cleanup. Default is True.
        object_id_field (str, optional):
            The field representing the object ID used during partitioning. Default is "OBJECTID".
    """

    # Class-level constants
    PARTITION_FIELD = "partition_select"
    ORIGINAL_ID_FIELD = "original_id_field"

    def __init__(
        self,
        partition_io_config: core_config.PartitionIOConfig,
        alias_path_data: Dict[
            str, Tuple[Literal["input", "context", "reference"], str]
        ],
        alias_path_outputs: Dict[str, Tuple[str, str]],
        root_file_partition_iterator: str,
        custom_functions=None,
        dictionary_documentation_path: str = None,
        feature_count: int = 15000,
        run_partition_optimization: bool = True,
        partition_method: Literal["FEATURES", "VERTICES"] = "FEATURES",
        search_distance: str = "500 Meters",
        context_selection: bool = True,
        delete_final_outputs: bool = True,
        safe_output_final_cleanup: bool = True,
        object_id_field: str = "OBJECTID",
    ):
        """
        Initializes the PartitionIterator with input and output datasets, custom functions, and configuration
        for partitioning and processing.

        Args:
            See class docstring.
        """

        # Raw inputs and initial setup
        self.nested_input_object_tag: Dict[str, Dict[str, str]] = {}
        self.nested_output_object_tag: Dict[str, Dict[str, str]] = {}

        input_entries_resolved = [
            core_config.ResolvedEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
                input_type=e.input_type.value,
            )
            for e in partition_io_config.input_config.entries
        ]

        output_entries_resolved = [
            core_config.ResolvedEntry(
                object=e.object,
                tag=e.tag,
                path=e.path,
            )
            for e in partition_io_config.output_config.entries
        ]

        self.resolve_partition_io_config(
            entries=input_entries_resolved,
            target_dict=self.nested_input_object_tag,
        )

        self.resolve_partition_io_config(
            entries=output_entries_resolved,
            target_dict=self.nested_output_object_tag,
        )

        self.raw_input_data = alias_path_data
        self.raw_output_data = alias_path_outputs or {}
        self.root_file_partition_iterator = root_file_partition_iterator
        if "." in dictionary_documentation_path:
            self.dictionary_documentation_path = re.sub(
                r"\.[^.]*$", "", dictionary_documentation_path
            )
        else:
            self.dictionary_documentation_path = dictionary_documentation_path

        self.search_distance = search_distance
        self.feature_count = feature_count
        self.run_partition_optimization = run_partition_optimization
        self.final_partition_feature_count = 0
        self.partition_method = partition_method
        self.object_id_field = object_id_field
        self.selection_of_context_features = context_selection
        self.delete_final_outputs_bool = delete_final_outputs
        self.safe_final_output_cleanup = safe_output_final_cleanup

        # Initial processing results
        self.nested_alias_type_data = {}
        self.nested_final_outputs = {}

        # Variables related to features and iterations
        self.partition_feature = f"{root_file_partition_iterator}_partition_feature"
        self.used_partition_size = None
        self.max_object_id = None
        self.current_iteration_id = None
        self.iteration_file_paths_list = []
        self.first_call_directory_documentation = True
        self.error_log = {}

        # Variables related to custom operations
        self.custom_functions = custom_functions or []
        self.custom_func_io_params = {}
        self.types_to_update = []

        self.total_start_time = None
        self.iteration_times_with_input = []
        self.iteration_start_time = None

    @staticmethod
    def resolve_partition_io_config(
        entries: List[core_config.ResolvedEntry],
        target_dict: Dict[str, Dict[str, str]],
    ) -> None:
        for entry in entries:
            if entry.object not in target_dict:
                target_dict[entry.object] = {}
            target_dict[entry.object][entry.tag] = entry.path

    @staticmethod
    def unpack_alias_path(alias_path, target_dict):
        """
        Populates target dictionaries with inputs from input parameters.
        """
        for alias, info in alias_path.items():
            if alias not in target_dict:
                target_dict[alias] = {}

            for i in range(0, len(info), 2):
                type_info = info[i]
                path_info = info[i + 1]
                target_dict[alias][type_info] = path_info

    def configure_alias_and_type(
        self,
        alias,
        type_name,
        type_path,
    ):
        """
        What:
            Configures an alias by adding or updating a type with a specified path.
            This function checks if the given alias exists within the `nested_alias_type_data` attribute.
            If the alias does not exist, it creates a new entry for it. Then, it associates the provided
            `type_name` with the given `type_path` under the specified alias.
        Args:
            alias (str): The alias to be configured. If it does not exist, a new one will be created.
            type_name (str): The name of the type to be added or updated under the alias.
            type_path (str): The path associated with the specified type.
        """

        if alias not in self.nested_alias_type_data:
            print(
                f"Alias '{alias}' not found in nested_alias_type_data. Creating new alias."
            )
            self.nested_alias_type_data[alias] = {"dummy_used": False}

        self.nested_alias_type_data[alias][type_name] = type_path
        print(f"Set path for type '{type_name}' in alias '{alias}' to: {type_path}")

    def _create_cartographic_partitions(self, feature_count: int) -> None:
        """
        What:
            Creates cartographic partitions based on the given feature_count.
            Overwrites any existing partition feature.

        Args:
            feature_count (int): The feature count used to limit partition size.
        """
        self.delete_feature_class(self.partition_feature)

        all_features = [
            path
            for alias, types in self.nested_alias_type_data.items()
            for type_key, path in types.items()
            if type_key in ["input_copy", "context_copy"] and path is not None
        ]

        if all_features:
            arcpy.cartography.CreateCartographicPartitions(
                in_features=all_features,
                out_features=self.partition_feature,
                feature_count=feature_count,
                partition_method=self.partition_method,
            )
        else:
            raise ValueError("No input or context features available for partitioning.")

    def _count_maximum_objects_in_partition(self) -> int:
        """
        What:
            Loops through each partition, selects it, and counts the number of input and context features
            found within the search distance buffer for that partition.

        How:
            Uses select_partition_feature, _process_inputs_in_partition, and _process_context_features
            to perform selections and access updated count values.
            Cleans up temp iteration files after each partition.

        Returns:
            int: The highest number of total features (input + context) across all partitions.
        """
        self.find_maximum_object_id()
        total_processed_objects = 0
        max_partition_load = 0
        aliases = list(self.nested_alias_type_data.keys())

        for object_id in range(1, self.max_object_id + 1):
            iteration_partition = (
                f"{self.root_file_partition_iterator}_partition_{object_id}"
            )
            total_processed_objects = 0
            self.iteration_file_paths_list.clear()

            self.select_partition_feature(iteration_partition, object_id)

            inputs_present = self._process_inputs_in_partition(
                aliases, iteration_partition, object_id
            )
            if not inputs_present:
                self.delete_iteration_files(*self.iteration_file_paths_list)
                continue

            self._process_context_features(aliases, iteration_partition, object_id)

            total_processed_objects += sum(
                self.nested_alias_type_data[alias].get("processed_objects_count", 0)
                for alias in aliases
            )
            max_partition_load = max(max_partition_load, total_processed_objects)

            print(
                f"\nPartition: {object_id}\nCurrent total found: {total_processed_objects}\nCrurrent maxumum found: {max_partition_load}"
            )

            self.delete_iteration_files(*self.iteration_file_paths_list)

        return max_partition_load

    def _find_partition_size(self) -> int:
        """
        What:
            Iteratively finds the largest feature_count value that produces partitions whose
            max buffered processing load (input + context) does not exceed max_allowed_objects.

        How:
            Starts with feature_count = max_allowed_objects and decreases until a valid config is found.

        Returns:
            int: The highest valid feature_count to use in partition creation.

        Raises:
            RuntimeError: If no valid feature count is found.
        """
        candidate = int(self.feature_count)

        max_found = int(self.feature_count * 1.01)
        min_candidate = self.feature_count
        current_iteration_number = 0
        previous_iteration_number = 0
        attempts = 0

        def _find_increment(current_number: int) -> int:
            min_increment = int(self.feature_count * 0.01)
            overage = current_number - min_candidate
            reduce = max(min_increment, int(overage * 0.5) + min_increment)
            return reduce

        while max_found > min_candidate:
            attempts += 1
            print(
                f"\n\nAttempt: {attempts}\nTesting candidate feature_count: {candidate}"
            )
            self._create_cartographic_partitions(feature_count=candidate)

            self.find_maximum_object_id()
            current_iteration_number = self.max_object_id

            if current_iteration_number == previous_iteration_number:
                reduce_with = int(self.feature_count * 0.01)
                candidate = int(candidate - reduce_with)
                previous_iteration_number = self.max_object_id
                print(
                    f"Identical partition generated. Reduced feature_count with: {reduce_with}"
                )
                continue

            previous_iteration_number = current_iteration_number

            max_found = self._count_maximum_objects_in_partition()

            print(f" -> max partition load found: {max_found}")
            if max_found <= min_candidate:
                print(f"Selected feature_count: {candidate}")
                self.final_partition_feature_count = candidate
                return candidate

            reduce_with = _find_increment(current_number=max_found)
            print(f"Reducing with: {reduce_with}")
            candidate = int(candidate - reduce_with)

        raise RuntimeError(
            f"No valid feature count found below max={self.feature_count}. "
            f"Minimum candidate tested was {min_candidate}."
        )

    def create_cartographic_partitions(self):
        """
        First deletes existing partitioning feature if it exists.
        Then creates partitioning feature using input and context features as the in_features.
        """
        self.delete_feature_class(self.partition_feature)

        all_features = [
            path
            for alias, types in self.nested_alias_type_data.items()
            for type_key, path in types.items()
            if type_key in ["input_copy", "context_copy"] and path is not None
        ]

        print(f"all_features: {all_features}")
        if all_features:
            arcpy.cartography.CreateCartographicPartitions(
                in_features=all_features,
                out_features=self.partition_feature,
                feature_count=self.feature_count,
                partition_method=self.partition_method,
            )
            print(f"Created partitions in {self.partition_feature}")
        else:
            print("No input or context features available for creating partitions.")

    @staticmethod
    def delete_feature_class(feature_class_path, alias=None, output_type=None):
        """Deletes a feature class if it exists."""
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)
            if alias and output_type:
                print(
                    f"Deleted existing output feature class for '{alias}' of type '{output_type}': {feature_class_path}"
                )
            else:
                print(f"Deleted feature class: {feature_class_path}")

    @staticmethod
    def is_safe_to_delete(file_path: str, safe_directory: str) -> bool:
        """
        What:
            Check if the file path is within the specified safe directory.

        Args:
            file_path (str): The path of the file to check.
            safe_directory (str): The directory considered safe for deletion.

        Returns:
            bool: True if the file is within the safe directory, False otherwise.
        """
        # Ensure safe directory ends with a backslash for correct comparison
        if not safe_directory.endswith(os.path.sep):
            safe_directory += os.path.sep
        return file_path.startswith(safe_directory)

    def delete_final_outputs(self):
        """
        Deletes all existing final output files if they exist and are in the safe directory and self.delete_final_outputs_bool is True.
        """

        # Check if deletion is allowed
        if not self.delete_final_outputs_bool:
            print("Deletion of final outputs is disabled.")
            return

        # Construct the safe directory path
        local_root_directory = config.output_folder
        project_root_directory = env_setup.global_config.main_directory_name
        safe_directory = rf"{local_root_directory}\{project_root_directory}"

        for alias in self.nested_final_outputs:
            for _, output_file_path in self.nested_final_outputs[alias].items():
                if self.is_safe_to_delete(output_file_path, safe_directory):
                    if arcpy.Exists(output_file_path):
                        arcpy.management.Delete(output_file_path)
                        print(f"Deleted file: {output_file_path}")
                else:
                    print(
                        f"""Skipped deletion for {output_file_path}, the provided path is not in safe directory.
                        If you intend to delete this file outside of the project directory change the 
                        'safe_output_final_cleanup' param to 'false'
                        """
                    )

    def delete_iteration_files(self, *file_paths):
        """Deletes multiple feature classes or files from a list."""
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    @staticmethod
    def create_feature_class(full_feature_path, template_feature):
        """Creates a new feature class from a template feature class, given a full path."""
        out_path, out_name = os.path.split(full_feature_path)
        if arcpy.Exists(full_feature_path):
            arcpy.management.Delete(full_feature_path)
            print(f"Deleted existing feature class: {full_feature_path}")

        arcpy.management.CreateFeatureclass(
            out_path=out_path, out_name=out_name, template=template_feature
        )
        print(f"Created feature class: {full_feature_path}")

    def create_dummy_features(self, types_to_include: list = None):
        """
        What:
            Creates dummy features for aliases for types specified in types_to_include.

        Args:
            types_to_include (list): A list of types for which dummy features should be created.
        """
        if types_to_include is None:
            types_to_include = ["input_copy", "context_copy"]

        for alias, alias_data in self.nested_alias_type_data.items():
            for type_info, path in list(alias_data.items()):
                if type_info in types_to_include and path:
                    dummy_feature_path = (
                        f"{self.root_file_partition_iterator}_{alias}_dummy_feature"
                    )
                    PartitionIterator.create_feature_class(
                        full_feature_path=dummy_feature_path,
                        template_feature=path,
                    )
                    print(
                        f"Created dummy feature class for {alias} of type {type_info}: {dummy_feature_path}"
                    )
                    # Update alias state to include this new dummy type and its path
                    self.configure_alias_and_type(
                        alias=alias,
                        type_name="dummy",
                        type_path=dummy_feature_path,
                    )

    def reset_dummy_used(self):
        """Sets the dummy_used to false"""
        for alias in self.nested_alias_type_data:
            self.nested_alias_type_data[alias]["dummy_used"] = False

    def update_empty_alias_type_with_dummy_file(self, alias, type_info):
        # Check if the dummy type exists in the alias nested_alias_type_data
        if "dummy" in self.nested_alias_type_data[alias]:
            # Check if the input type exists in the alias nested_alias_type_data
            if (
                type_info in self.nested_alias_type_data[alias]
                and self.nested_alias_type_data[alias][type_info] is not None
            ):
                # Get the dummy path from the alias nested_alias_type_data
                dummy_path = self.nested_alias_type_data[alias]["dummy"]
                # Set the value of the existing type_info to the dummy path
                self.nested_alias_type_data[alias][type_info] = dummy_path
                self.nested_alias_type_data[alias]["dummy_used"] = True
                print(
                    f"The '{type_info}' for alias '{alias}' was updated with dummy path: {dummy_path}"
                )
            else:
                print(
                    f"'{type_info}' does not exist for alias '{alias}' in nested_alias_type_data."
                )
        else:
            print(
                f"'dummy' type does not exist for alias '{alias}' in nested_alias_type_data."
            )

    @staticmethod
    def create_directory_json_documentation(
        root_path: str,
        dir_name: str,
        iteration: bool,
    ) -> str:
        """
        What:
            Creates a directory at the given root_path for the target_dir.
        Args:
            root_path (str): The root directory where dir_name will be located
            dir_name (str): The target where the created directory should be placed
            iteration (bool): Boolean flag indicating if the iteration_documentation should be added
        Returns:
            str: A string containing the absolute path of the created directory.
        """

        # Determine base directory
        directory_path = os.path.join(root_path, f"{dir_name}")

        # Ensure that the directory exists
        os.makedirs(directory_path, exist_ok=True)

        if iteration:
            iteration_documentation_dir = os.path.join(directory_path, "iteration")
            os.makedirs(iteration_documentation_dir, exist_ok=True)

            return iteration_documentation_dir

        return directory_path

    @staticmethod
    def write_data_to_json(
        data: dict,
        file_path: str,
        file_name: str,
        object_id: int = None,
    ) -> None:
        """
         What:
             Writes dictionary into a json file.

        Args:
            data (dict): The data to write.
            file_path (str): The complete path (directory+file_name) where the file should be created
            file_name (str): The name of the file to create
            object_id (int): If provided, object_id will also be part of the file name.
        """

        if object_id:
            complete_file_path = os.path.join(
                file_path, f"{file_name}_{object_id}.json"
            )
        else:
            complete_file_path = os.path.join(file_path, f"{file_name}.json")

        with open(complete_file_path, "w") as f:
            json.dump(data, f, indent=4)

    def export_dictionaries_to_json(
        self,
        file_path: str = None,
        alias_type_data: dict = None,
        final_outputs: dict = None,
        file_name: str = None,
        iteration: bool = False,
        object_id: int = None,
    ) -> None:
        """
        What:
            Handles the export of alias type data and final outputs into separate json files.

        Args:
            file_path (str): The complete file path where to create the output directories.
            alias_type_data (dict): The alias type data to export.
            final_outputs (dict): The final outputs data to export.
            file_name (str): The name of the file to create
            iteration (bool): Boolean flag indicating if the iteration_documentation should be added
            object_id (int): Object ID to be included in the file name if it's an iteration (`iteration==True`). If `None`, will not be used.
        """

        if file_path is None:
            file_path = self.dictionary_documentation_path
        if alias_type_data is None:
            alias_type_data = self.nested_alias_type_data
        if final_outputs is None:
            final_outputs = self.nested_final_outputs

        if self.first_call_directory_documentation and os.path.exists(file_path):
            shutil.rmtree(file_path)
            self.first_call_directory_documentation = False

        alias_type_data_directory = self.create_directory_json_documentation(
            file_path, "alias_type", iteration
        )
        final_outputs_directory = self.create_directory_json_documentation(
            file_path, "outputs", iteration
        )

        self.write_data_to_json(
            alias_type_data, alias_type_data_directory, file_name, object_id
        )
        self.write_data_to_json(
            final_outputs, final_outputs_directory, file_name, object_id
        )

    def create_error_log_directory(self):
        """
        Creates an error_log directory inside self.dictionary_documentation_path.
        Returns the path to the error_log directory.
        """
        return self.create_directory_json_documentation(
            root_path=self.dictionary_documentation_path,
            dir_name="error_log",
            iteration=False,
        )

    def save_error_log(self, error_log):
        """
        Saves the error log to a JSON file in the error_log directory.
        """
        error_log_directory = self.create_error_log_directory()
        # Check if error log is empty
        if not error_log:
            self.write_data_to_json(
                data=error_log,
                file_path=error_log_directory,
                file_name="no_errors",
            )
        else:
            self.write_data_to_json(
                data=error_log, file_path=error_log_directory, file_name="error_log"
            )

    @staticmethod
    def generate_unique_field_name(input_feature, field_name):
        """Generates a unique field name"""
        existing_field_names = [field.name for field in arcpy.ListFields(input_feature)]
        unique_field_name = field_name
        while unique_field_name in existing_field_names:
            unique_field_name = f"{unique_field_name}_{random.randint(0, 9)}"
        return unique_field_name

    def find_maximum_object_id(self):
        """
        Determine the maximum OBJECTID for partitioning.
        """
        try:
            # Use a search cursor to find the maximum OBJECTID
            with arcpy.da.SearchCursor(
                self.partition_feature,
                self.object_id_field,
                sql_clause=(None, f"ORDER BY {self.object_id_field} DESC"),
            ) as cursor:
                self.max_object_id = next(cursor)[0]

            print(f"Maximum {self.object_id_field} found: {self.max_object_id}")

        except Exception as e:
            print(f"Error in finding max {self.object_id_field}: {e}")

    def prepare_input_data(self):
        """
        Copies the input data, and set the path of the copy to type input_copy in self.nested_alias_type_data.
        From now on when the PartitionIterator access the global data for an alias it uses input_copy.
        If context_selection bool is True, it will only select context features within the search_distance of
        an input_copy feature, then similar to input data set the new context feature as context_copy.
        """
        for alias, types in self.nested_alias_type_data.items():
            if "input" in types:
                input_data_path = types["input"]
                input_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_input_data_copy"
                )

                arcpy.management.Copy(
                    in_data=input_data_path,
                    out_data=input_data_copy,
                )
                print(f"Copied input nested_alias_type_data for: {alias}")

                # Add a new type for the alias the copied input nested_alias_type_data
                self.configure_alias_and_type(
                    alias=alias,
                    type_name="input_copy",
                    type_path=input_data_copy,
                )

                # Making sure the field is unique if it exists a field with the same name
                self.PARTITION_FIELD = self.generate_unique_field_name(
                    input_feature=input_data_copy,
                    field_name=self.PARTITION_FIELD,
                )

                self.ORIGINAL_ID_FIELD = self.generate_unique_field_name(
                    input_feature=input_data_copy,
                    field_name=self.ORIGINAL_ID_FIELD,
                )

                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=self.PARTITION_FIELD,
                    field_type="LONG",
                )
                print(f"Added field {self.PARTITION_FIELD}")

                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=self.ORIGINAL_ID_FIELD,
                    field_type="LONG",
                )
                print(f"Added field {self.ORIGINAL_ID_FIELD}")

                arcpy.CalculateField_management(
                    in_table=input_data_copy,
                    field=self.ORIGINAL_ID_FIELD,
                    expression=f"!{self.object_id_field}!",
                )
                print(f"Calculated field {self.ORIGINAL_ID_FIELD}")

        for alias, types in self.nested_alias_type_data.items():
            if "context" in types:
                context_data_path = types["context"]
                context_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_context_data_copy"
                )
                if self.selection_of_context_features:
                    PartitionIterator.create_feature_class(
                        full_feature_path=context_data_copy,
                        template_feature=context_data_path,
                    )

                    for input_alias, input_types in self.nested_alias_type_data.items():
                        if "input_copy" in input_types:
                            input_data_copy = input_types["input_copy"]

                            context_features_near_input_selection = f"memory/{alias}_context_features_near_{input_alias}_selection"

                            custom_arcpy.select_location_and_make_feature_layer(
                                input_layer=context_data_path,
                                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                                select_features=input_data_copy,
                                output_name=context_features_near_input_selection,
                                search_distance=self.search_distance,
                            )
                            arcpy.management.Append(
                                inputs=context_features_near_input_selection,
                                target=context_data_copy,
                                schema_type="NO_TEST",
                            )
                            arcpy.management.Delete(
                                context_features_near_input_selection
                            )
                    print(f"Processed context feature for: {alias}")

                else:
                    arcpy.management.Copy(
                        in_data=context_data_path,
                        out_data=context_data_copy,
                    )
                    print(f"Copied context data for: {alias}")

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="context_copy",
                    type_path=context_data_copy,
                )

    def select_partition_feature(self, iteration_partition, object_id):
        """
        Selects partition feature based on OBJECTID.
        """
        self.iteration_file_paths_list.append(iteration_partition)
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.partition_feature,
            expression=f"{self.object_id_field} = {object_id}",
            output_name=iteration_partition,
        )

    def process_input_features(
        self,
        alias,
        iteration_partition,
        object_id,
    ) -> bool:
        """
        What:
            For an alias makes selection for the partitioning feature being iterated over.
            It selects objects with their centerpoint inside the partitioning feature marking it as the objects
            being generalized in the partitioning feature, but also the objects within a distance so it is taken into consideration.
            The selection path is marked as type input in the self.nested_alias_type_data.
            It also counts the objects for input features, if the count is 0 for the input feature the iteration return false.
            If there is 0 objects in the iteration it loads in the dummy feature.
        Returns:
            bool: Returns true or false based if there is an input feature present for the partition.
        """
        if "input_copy" not in self.nested_alias_type_data[alias]:
            # If there are no inputs to process, return None for the aliases and a flag indicating no input was present.
            return None, False

        if "input_copy" in self.nested_alias_type_data[alias]:
            input_path = self.nested_alias_type_data[alias]["input_copy"]
            input_features_center_in_partition_selection = f"memory/{alias}_input_features_center_in_partition_selection_{object_id}"
            self.iteration_file_paths_list.append(
                input_features_center_in_partition_selection
            )

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_path,
                overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
                select_features=iteration_partition,
                output_name=input_features_center_in_partition_selection,
            )

            count_points = file_utilities.count_objects(
                input_layer=input_features_center_in_partition_selection
            )

            self.nested_alias_type_data[alias]["count"] = count_points

            if count_points > 0:
                print(f"{alias} has {count_points} features in {iteration_partition}")

                arcpy.CalculateField_management(
                    in_table=input_features_center_in_partition_selection,
                    field=self.PARTITION_FIELD,
                    expression="1",
                )

                input_data_iteration_selection = f"{self.root_file_partition_iterator}_{alias}_input_data_iteration_selection_{object_id}"
                self.iteration_file_paths_list.append(input_data_iteration_selection)

                PartitionIterator.create_feature_class(
                    full_feature_path=input_data_iteration_selection,
                    template_feature=input_features_center_in_partition_selection,
                )

                arcpy.management.Append(
                    inputs=input_features_center_in_partition_selection,
                    target=input_data_iteration_selection,
                    schema_type="NO_TEST",
                )

                input_features_within_distance_of_partition_selection = f"memory/{alias}_input_features_within_distance_of_partition_selection_{object_id}"
                self.iteration_file_paths_list.append(
                    input_features_within_distance_of_partition_selection
                )

                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=input_path,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                    select_features=iteration_partition,
                    output_name=input_features_within_distance_of_partition_selection,
                    selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                    search_distance=self.search_distance,
                )

                arcpy.management.SelectLayerByLocation(
                    in_layer=input_features_within_distance_of_partition_selection,
                    overlap_type="HAVE_THEIR_CENTER_IN",
                    select_features=iteration_partition,
                    selection_type="REMOVE_FROM_SELECTION",
                )

                arcpy.CalculateField_management(
                    in_table=input_features_within_distance_of_partition_selection,
                    field=self.PARTITION_FIELD,
                    expression="0",
                )

                arcpy.management.Append(
                    inputs=input_features_within_distance_of_partition_selection,
                    target=input_data_iteration_selection,
                    schema_type="NO_TEST",
                )

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="input",
                    type_path=input_data_iteration_selection,
                )

                count_processed_objects = file_utilities.count_objects(
                    input_layer=input_data_iteration_selection
                )

                self.nested_alias_type_data[alias][
                    "processed_objects_count"
                ] = count_processed_objects

                print(
                    f"iteration partition {input_features_within_distance_of_partition_selection} appended to {input_data_iteration_selection}"
                )
                # Return the processed input features and a flag indicating successful operation
                return True
            else:
                # Loads in dummy feature for this alias for this iteration and sets dummy_used = True
                self.update_empty_alias_type_with_dummy_file(
                    alias,
                    type_info="input",
                )
                print(
                    f"iteration partition {object_id} has no features for {alias} in the partition feature"
                )
            # If there are no inputs to process, return None for the aliases and a flag indicating no input was present.
            return False

    def _process_inputs_in_partition(
        self,
        aliases,
        iteration_partition,
        object_id,
    ) -> bool:
        """
        What:
            Process input features using process_input_features function using it on all alias with an input type.
            If there are one or more input features present it returns true.
        Returns:
            bool: Returns true or false based if there are input features present for the partition.
        """
        inputs_present_in_partition = False
        for alias in aliases:
            if "input_copy" in self.nested_alias_type_data[alias]:
                # Using process_input_features to check whether inputs are present
                input_present = self.process_input_features(
                    alias, iteration_partition, object_id
                )
                # Sets inputs_present_in_partition as True if any alias in partition has input present. Otherwise, it remains False.
                inputs_present_in_partition = (
                    inputs_present_in_partition or input_present
                )
        return inputs_present_in_partition

    def process_context_features(self, alias, iteration_partition, object_id):
        """
        Selects objects within self.search_distance for a context feature and sets the selection as type context.
        If there is no objects within the distance dummy data is loaded in instead.
        """
        if "context_copy" in self.nested_alias_type_data[alias]:
            context_path = self.nested_alias_type_data[alias]["context_copy"]
            context_data_iteration_selection = f"{self.root_file_partition_iterator}_{alias}_context_data_iteration_selection_{object_id}"
            self.iteration_file_paths_list.append(context_data_iteration_selection)

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=context_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=context_data_iteration_selection,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                search_distance=self.search_distance,
            )

            count_points = file_utilities.count_objects(
                input_layer=context_data_iteration_selection
            )

            self.nested_alias_type_data[alias]["count"] = count_points

            if count_points > 0:
                print(f"{alias} has {count_points} features in {iteration_partition}")

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="context",
                    type_path=context_data_iteration_selection,
                )

                count_processed_objects = file_utilities.count_objects(
                    input_layer=context_data_iteration_selection
                )

                self.nested_alias_type_data[alias][
                    "processed_objects_count"
                ] = count_processed_objects
            else:
                # Loads in dummy feature for this alias for this iteration and sets dummy_used = True
                self.update_empty_alias_type_with_dummy_file(
                    alias,
                    type_info="context",
                )
                print(
                    f"iteration partition {object_id} has no features for {alias} in the partition feature"
                )

    def _process_context_features(self, aliases, iteration_partition, object_id):
        """Processes context features fo all alias with a context type using process_context_features"""
        for alias in aliases:
            self.process_context_features(alias, iteration_partition, object_id)

    @staticmethod
    def format_time(seconds):
        """
        What:
            Converts seconds to a formatted string: HH:MM:SS.

        Args:
            seconds (float): Time in seconds.

        Returns:
            str: Formatted time string.
        """
        seconds = int(seconds)  # Convert to integer for rounding
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} hours, {minutes} minutes, {seconds} seconds"

    def track_iteration_time(self, object_id, inputs_present_in_partition):
        """
        What:
            Tracks the iteration time and estimate the remaining time. It adds the time of iterations
            with input features to a list, using the average time of this list as baseline for remaining time.

        Args:
            object_id (int): The ID of the current partition iteration.
            inputs_present_in_partition (bool): Flag indicating if there were input features in the iteration.
        """
        iteration_time = time.time() - self.iteration_start_time
        if inputs_present_in_partition:
            self.iteration_times_with_input.append(iteration_time)
            average_runtime_per_iteration = sum(self.iteration_times_with_input) / len(
                self.iteration_times_with_input
            )
        else:
            average_runtime_per_iteration = (
                sum(self.iteration_times_with_input)
                / len(self.iteration_times_with_input)
                if self.iteration_times_with_input
                else 0
            )

        total_runtime = time.time() - self.total_start_time
        remaining_iterations = self.max_object_id - object_id
        estimated_remaining_time = remaining_iterations * average_runtime_per_iteration

        formatted_total_runtime = self.format_time(total_runtime)
        formatted_estimated_remaining_time = self.format_time(estimated_remaining_time)

        current_time_date = datetime.now().strftime("%m-%d %H:%M:%S")

        print(f"\nCurrent time: {current_time_date}")
        print(f"Current runtime: {formatted_total_runtime}")
        print(f"Estimated remaining time: {formatted_estimated_remaining_time}")

    def _inject_partition_field_to_custom_functions(self):
        """
        Injects self.PARTITION_FIELD into custom functions that declare 'partition_field_name' in their params.
        This enables any logic to receive the dynamically generated partition field if it supports it.
        """
        for func_config in self.custom_functions:
            params = func_config.get("params", {})

            # Check directly in the params dict first
            if "partition_field_name" in params:
                params["partition_field_name"] = self.PARTITION_FIELD
                continue

            # Fall back to checking method signature if not explicitly defined
            target_callable = None
            if "class" in func_config:
                cls = func_config["class"]
                method = func_config["method"]
                try:
                    target_callable = getattr(cls, method)
                except AttributeError:
                    continue
            elif "func" in func_config:
                target_callable = func_config["func"]

            if target_callable:
                try:
                    sig = inspect.signature(target_callable)
                    if "partition_field_name" in sig.parameters:
                        params["partition_field_name"] = self.PARTITION_FIELD
                except (TypeError, ValueError):
                    # Happens if the target isn't introspectable — ignore
                    continue

    def find_io_params_custom_logic(self, object_id: int):
        """
        What:
            Find and resolve the input and output (IO) parameters for custom logic functions.

        How:
            This function iterates over a list of custom functions, which could be either standalone
            functions or class methods. For each function, it checks if it has partition IO metadata.
            Functions needs to be decorated with the partition_io_decorator. In this function
            input and output refers to the parameters of the custom_functions and not alias types.

        Args:
            object_id (int): The identifier for the object that the IO parameters will be associated with.
        """
        for custom_func in self.custom_functions:
            if "class" in custom_func:  # Class method
                func = custom_func["class"]
                method = getattr(func, custom_func["method"])
            else:  # Standalone function
                method = custom_func["func"]

            if hasattr(method, "_partition_io_metadata"):
                metadata = method._partition_io_metadata
                input_params = metadata.get("inputs", [])
                output_params = metadata.get("outputs", [])

                self.resolve_io_params(
                    params=input_params,
                    custom_func=custom_func,
                    object_id=object_id,
                )
                self.resolve_io_params(
                    params=output_params,
                    custom_func=custom_func,
                    object_id=object_id,
                )

    def resolve_io_params(self, params: list, custom_func: dict, object_id: int):
        """
        What:
            Resolve the paths for input or output parameters of custom functions.

        How:
            This function takes a set of input or output parameters and resolves their paths by iterating
            over the parameters and processing them, depending on their type (tuple, dict, list, etc.).
            It uses a helper function `resolve_param` to recursively resolve each parameter's path.

        Args:
            params (list): A list of parameters to be resolved.
            custom_func (dict): The custom function containing the parameters to resolve.
            object_id (int): The identifier for the object related to these parameters.
        """

        def resolve_param(param_info):
            if isinstance(param_info, tuple) and len(param_info) == 2:
                return self._handle_tuple_param(param_info, object_id)
            elif isinstance(param_info, dict):
                return {key: resolve_param(value) for key, value in param_info.items()}
            elif isinstance(param_info, list):
                return [resolve_param(item) for item in param_info]
            else:
                return param_info

        for param in params:
            param_info_list = custom_func["params"].get(param, [])
            if not isinstance(param_info_list, list):
                param_info_list = [param_info_list]

            resolved_paths = [
                resolve_param(param_info) for param_info in param_info_list
            ]
            print(f"Printing param_info_list:\n{param_info_list}")
            if len(resolved_paths) == 1:
                custom_func["params"][param] = resolved_paths[0]
            else:
                custom_func["params"][param] = resolved_paths

    def _handle_tuple_param(self, param_info: tuple, object_id: int) -> str:
        """
        What:
            Handle the resolution of parameters that are tuples of (alias, alias_type).

        How:
            - This method first checks if the `alias_type` needs to be dynamically updated (if it
              belongs to `self.types_to_update`). If so, a new path is constructed for the alias and
              alias_type during each iteration.
            - If the alias and alias_type are static (i.e., they exist in `self.nested_alias_type_data`),
              it retrieves and uses the existing path without updating it.
            - If the alias_type is neither in `self.types_to_update` nor static, it constructs a new
              path and adds the alias_type to `self.types_to_update` for future updates during iterations.

        Why:
            - Some alias types are static and only need to be resolved once, which is why their paths
              are stored in `self.nested_alias_type_data`.
            - Other alias types require dynamic path reconstruction for each iteration, which is why
              they are tracked in `self.types_to_update` to ensure they are updated accordingly.

        Args:
            param_info (tuple): A tuple containing an alias and its associated alias_type.
            object_id (int): The identifier for the object related to these parameters.

        Returns:
            str: The resolved path based on the alias and alias_type.
        """

        alias, alias_type = param_info

        if alias_type in self.types_to_update:
            resolved_path = self.construct_path_for_alias_type(
                alias,
                alias_type,
                object_id,
            )
            print(
                f"Updated path for {param_info}: {resolved_path} (type is in types_to_update)"
            )
        elif (
            alias in self.nested_alias_type_data
            and alias_type in self.nested_alias_type_data[alias]
        ):
            resolved_path = self.nested_alias_type_data[alias][alias_type]
            print(f"Using existing path for {param_info}: {resolved_path}")
        else:
            resolved_path = self.construct_path_for_alias_type(
                alias,
                alias_type,
                object_id,
            )
            self.types_to_update.append(alias_type)
            print(
                f"Constructed new path for {param_info}: {resolved_path} and added {alias_type} to types_to_update"
            )

        self.configure_alias_and_type(alias, alias_type, resolved_path)

        return resolved_path

    def construct_path_for_alias_type(self, alias, alias_type, object_id) -> str:
        """
        Construct a new path for a given alias and type specific to the current iteration.
        """
        base_path = self.root_file_partition_iterator
        constructed_path = f"{base_path}_{alias}_{alias_type}_{object_id}"
        return constructed_path

    def execute_custom_functions(self):
        """
        What:
            Execute custom functions with the resolved input and output paths.

        How:
            This function iterates through custom functions and handles them differently based
            on whether they are class methods or standalone functions. It extracts the required
            parameters, resolves their paths, and logs these parameters before executing the
            corresponding class methods or standalone functions.

            For class methods, it separates parameters for class instantiation and method execution.
            For standalone functions, it directly prepares and resolves parameters for function execution.
        """

        for custom_func in self.custom_functions:
            resolved_params = {}  # Initialize resolved_params

            if "class" in custom_func:
                # Handle class methods
                func_class = custom_func["class"]
                method = getattr(func_class, custom_func["method"])

                # Prepare parameters for the class instantiation and method call
                class_params = {}
                method_params = {}

                for param, path in custom_func["params"].items():
                    # Determine if the parameter is for the constructor or method
                    if param in func_class.__init__.__code__.co_varnames:
                        class_params[param] = path
                    else:
                        method_params[param] = path

                # Log the class parameters
                print(f"Class parameters for {func_class.__name__}:")
                pprint.pprint(class_params, indent=4)

                # Log the method parameters
                print(f"Method parameters for {method.__name__}:")
                pprint.pprint(method_params, indent=4)

                # Instantiate the class with the required parameters
                instance = func_class(**class_params)
                # Call the method with the required parameters
                method(instance, **method_params)

            else:
                # Handle standalone functions
                method = custom_func["func"]

                # Prepare parameters for the function call
                func_params = custom_func["params"]
                resolved_params = {param: path for param, path in func_params.items()}

                # Log the function parameters
                print(f"Function parameters for {method.__name__}:")
                pprint.pprint(resolved_params, indent=4)

                # Execute the function with resolved parameters
                method(**resolved_params)

    def resilient_execute_custom_functions(self, object_id: int):
        """
        What:
            Helper function to execute custom functions with retry logic to handle potential failures
            caused by unreliable 3rd party logic.

        Args:
            object_id (int): The current object_id being processed (for logging).
        """
        max_retries = 50

        for attempt in range(max_retries):
            try:
                self.execute_custom_functions()
                break  # If successful, exit the retry loop
            except Exception as e:
                error_message = str(e)
                print(f"Attempt {attempt + 1} failed with error: {error_message}")

                # Initialize the log for this iteration if not already done
                if object_id not in self.error_log:
                    self.error_log[object_id] = {
                        "Number of retries": 0,
                        "Error Messages": {},
                    }

                # Update the log with the retry attempt and error message
                self.error_log[object_id]["Number of retries"] += 1
                self.error_log[object_id]["Error Messages"][attempt + 1] = error_message

                if attempt + 1 == max_retries:
                    print("Max retries reached.")
                    self.save_error_log(self.error_log)
                    raise Exception(error_message)

    def append_iteration_to_final(self, alias: str, object_id: int):
        """
        What:
            Append the result of the current iteration to the final output for a given alias.

        How:
            - This method checks if the given `alias` exists in `self.nested_final_outputs`. If it does not,
              the function exits.
            - For each type associated with the alias, it retrieves the corresponding feature class and appends
              the result of the current iteration to the final output path.
            - If the alias is marked as a dummy feature (indicated by `dummy_used` in `self.nested_alias_type_data`),
              the iteration is skipped.
            - It selects the features from the input feature class based on a specific partition field and appends
              them to the final output. If the final output does not exist, it creates the output; otherwise, it appends to it.

        Why:
            This function is necessary to accumulate the results of each iteration for the given alias in a final output,
            ensuring the results from multiple iterations are combined into a single dataset.

        Args:
            alias (str): A string representing the alias whose output data is to be updated.
            object_id (int): The identifier for the current iteration.
        """

        # Guard clause if alias doesn't exist in nested_final_outputs
        if alias not in self.nested_final_outputs:
            return

        # For each type under current alias, append the result of the current iteration
        for type_info, final_output_path in self.nested_final_outputs[alias].items():
            # Skipping append if the alias is a dummy feature
            if self.nested_alias_type_data[alias]["dummy_used"]:
                continue

            input_feature_class = self.nested_alias_type_data[alias][type_info]

            if (
                not arcpy.Exists(input_feature_class)
                or int(arcpy.GetCount_management(input_feature_class).getOutput(0)) <= 0
            ):
                print(
                    f"No features found in partition target selection: {input_feature_class}"
                )
                continue

            partition_target_selection = (
                f"memory/{alias}_{type_info}_partition_target_selection_{object_id}"
            )
            self.iteration_file_paths_list.append(partition_target_selection)
            self.iteration_file_paths_list.append(input_feature_class)

            # Apply feature selection
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=input_feature_class,
                expression=f"{self.PARTITION_FIELD} = 1",
                output_name=partition_target_selection,
            )

            if not arcpy.Exists(final_output_path):
                arcpy.management.CopyFeatures(
                    in_features=partition_target_selection,
                    out_feature_class=final_output_path,
                )

            else:
                arcpy.management.Append(
                    inputs=partition_target_selection,
                    target=final_output_path,
                    schema_type="NO_TEST",
                )

    @staticmethod
    def delete_fields(feature_class_path: str, fields_to_delete: list):
        """
        What:
            Deletes specified fields from the given feature class if they exist.

        Args:
            feature_class_path (str): The path to the feature class.
            fields_to_delete (list): A list of field names to delete.
        """
        for field_name in fields_to_delete:
            try:
                # Check if the field exists
                if arcpy.ListFields(feature_class_path, field_name):
                    # Delete the field if it exists
                    arcpy.management.DeleteField(feature_class_path, field_name)
                    print(f"Field '{field_name}' deleted successfully.")
                else:
                    print(f"Field '{field_name}' does not exist.")
            except arcpy.ExecuteError as e:
                print(f"An error occurred while deleting field '{field_name}': {e}")

    def cleanup_final_outputs(self):
        """
        Cleanup function to delete unnecessary fields from final output feature classes.
        """
        fields_to_delete = [self.PARTITION_FIELD]

        for alias, output_paths in self.nested_final_outputs.items():
            for output_type, feature_class_path in output_paths.items():
                print(f"Cleaning up fields in {feature_class_path}...")
                self.delete_fields(feature_class_path, fields_to_delete)

    def partition_iteration(self):
        """
        What:
            Processes each data partition in multiple iterations.

        How:
            - Iterates over partitions based on `object_id`, from 1 to `max_object_id`.
            - For each iteration:
                - Creates and resets dummy features.
                - Deletes files from the previous iteration and clears the file path list.
                - Backs up the original parameters for custom functions.
                - Selects a partition feature and processes the inputs for that partition.
                - If inputs are present:
                    - Processes context features.
                    - Finds input/output parameters for custom logic.
                    - Exports data from the iteration to JSON.
                    - Executes custom functions.
                    - Appends the output of the current iteration to the final outputs.
        """

        aliases = self.nested_alias_type_data.keys()
        self.find_maximum_object_id()

        self.create_dummy_features(types_to_include=["input_copy", "context_copy"])
        self.reset_dummy_used()

        self.delete_iteration_files(*self.iteration_file_paths_list)
        self.iteration_file_paths_list.clear()

        original_custom_func_params = {
            id(custom_func): dict(custom_func["params"])
            for custom_func in self.custom_functions
        }

        for object_id in range(1, self.max_object_id + 1):
            self.current_iteration_id = object_id
            self.iteration_start_time = time.time()
            print(f"\nProcessing Partition: {object_id} out of {self.max_object_id}")
            self.reset_dummy_used()
            for custom_func in self.custom_functions:
                custom_func["params"] = dict(
                    original_custom_func_params[id(custom_func)]
                )

            self.iteration_file_paths_list.clear()
            iteration_partition = f"{self.partition_feature}_{object_id}"
            self.select_partition_feature(iteration_partition, object_id)

            inputs_present_in_partition = self._process_inputs_in_partition(
                aliases, iteration_partition, object_id
            )

            if inputs_present_in_partition:
                self._process_context_features(aliases, iteration_partition, object_id)
                self.find_io_params_custom_logic(object_id)
                self._inject_partition_field_to_custom_functions()
                self.export_dictionaries_to_json(
                    file_name="iteration",
                    iteration=True,
                    object_id=object_id,
                )

                self.resilient_execute_custom_functions(object_id)

            if inputs_present_in_partition:
                for alias in aliases:
                    self.append_iteration_to_final(alias, object_id)
                self.delete_iteration_files(*self.iteration_file_paths_list)
            else:
                self.delete_iteration_files(*self.iteration_file_paths_list)
            self.track_iteration_time(object_id, inputs_present_in_partition)

    @timing_decorator
    def run(self):
        """
        What:
            Orchestrates the entire workflow for the class, from data preparation to final output generation.

        How:
            - Initializes by unpacking input and output paths into `nested_alias_type_data` and `nested_final_outputs`.
            - Exports the initialized dictionaries to JSON for future reference.
            - Prepares the input data, including deleting old final outputs and processing the raw input data.
            - Creates cartographic partitions to organize the data.
            - Runs the partition iteration process by calling `partition_iteration`.
            - Once iterations are complete, it cleans up final outputs, and logs any errors that occurred.
        """

        self.total_start_time = time.time()
        self.unpack_alias_path(
            alias_path=self.raw_input_data, target_dict=self.nested_alias_type_data
        )
        self.unpack_alias_path(
            alias_path=self.raw_output_data, target_dict=self.nested_final_outputs
        )

        self.export_dictionaries_to_json(file_name="post_initialization")

        print("\nStarting Data Preparation...")
        self.delete_final_outputs()
        self.prepare_input_data()
        self.export_dictionaries_to_json(file_name="post_data_preparation")
        if self.run_partition_optimization:
            self._find_partition_size()

        print("\nCreating Cartographic Partitions...")
        if not self.run_partition_optimization:
            self.final_partition_feature_count = self.feature_count
        self._create_cartographic_partitions(
            feature_count=self.final_partition_feature_count
        )

        print("\nStarting on Partition Iteration...")
        self.partition_iteration()
        self.export_dictionaries_to_json(file_name="post_runtime")
        self.cleanup_final_outputs()
        self.save_error_log(self.error_log)


if __name__ == "__main__":
    environment_setup.main()
    # Define your input feature classes and their aliases
    building_points = "building_points"
    building_polygons = "building_polygons"
    church_hospital = "church_hospital"
    restriction_lines = "restriction_lines"
    bane = "bane"
    river = "river"
    train_stations = "train_stations"
    urban_area = "urban_area"
    roads = "roads"

    inputs = {
        building_points: [
            "input",
            Building_N100.point_propagate_displacement___points_after_propagate_displacement___n100_building.value,
        ],
        building_polygons: [
            "context",
            input_n50.Grunnriss,
        ],
        bane: [
            "context",
            input_n50.Bane,
        ],
        river: [
            "reference",
            input_n50.ElvBekk,
        ],
    }

    outputs = {
        building_points: [
            "polygon_processor",
            Building_N100.iteration__partition_iterator_final_output_points__n100.value,
        ],
    }

    inputs3 = {
        building_points: [
            "input",
            Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
        ],
        roads: [
            "input",
            Building_N100.data_preparation___unsplit_roads___n100_building.value,
        ],
        river: [
            "context",
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        ],
        urban_area: [
            "context",
            Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        ],
        train_stations: [
            "reference",
            Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        ],
        bane: [
            "context",
            input_n100.Bane,
        ],
    }

    outputs3 = {
        building_points: [
            "buffer_displacement",
            Building_N100.line_to_buffer_symbology___buffer_displaced_building_points___n100_building.value,
        ],
    }
    misc_objects = {
        "begrensningskurve": [
            ("river", "context"),
            0,
        ],
        "urban_areas": [
            ("urban_area", "context"),
            1,
        ],
        "bane_station": [
            ("train_stations", "reference"),
            1,
        ],
        "bane_lines": [
            ("bane", "context"),
            1,
        ],
    }

    buffer_displacement_config = {
        "class": BufferDisplacement,
        "method": "run",
        "params": {
            "input_road_lines": ("roads", "input"),
            "input_building_points": ("building_points", "input"),
            "input_misc_objects": misc_objects,
            "output_building_points": ("building_points", "buffer_displacement"),
            "sql_selection_query": N100_SQLResources.new_road_symbology_size_sql_selection.value,
            "root_file": Building_N100.line_to_buffer_symbology___test___n100_building.value,
            "building_symbol_dimensions": N100_Symbology.building_symbol_dimensions.value,
            "buffer_displacement_meter": N100_Values.buffer_clearance_distance_m.value,
            "write_work_files_to_memory": True,
            "keep_work_files": False,
        },
    }

    input_dict = {
        "building_points": [
            ("building_points", "input"),
            ("river", "input"),
            "10",
        ],
        "train_stations": [
            ("train_stations", "input"),
            ("bane", "input"),
            "10",
        ],
    }

    output_dict = {
        "building_points": [
            ("building_points", "buffer_1"),
            ("river", "buffer_1"),
        ],
        "train_stations": [
            ("train_stations", "buffer_1"),
            ("bane", "buffer_1"),
        ],
    }

    select_hospitals_config = {
        "func": custom_arcpy.select_attribute_and_make_permanent_feature,
        "params": {
            "input_layer": ("building_points", "input"),
            "output_name": ("building_points", "hospitals_selection"),
            "expression": "symbol_val IN (1, 2, 3)",
        },
    }

    polygon_processor_config = {
        "class": PolygonProcessor,
        "method": "run",
        "params": {
            "input_building_points": ("building_points", "hospitals_selection"),
            "output_polygon_feature_class": ("building_points", "polygon_processor"),
            "building_symbol_dimensions": N100_Symbology.building_symbol_dimensions.value,
            "symbol_field_name": "symbol_val",
            "index_field_name": "OBJECTID",
        },
    }

    partition_iterator = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[select_hospitals_config, polygon_processor_config],
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        dictionary_documentation_path=Building_N100.iteration___json_documentation___building_n100.value,
        feature_count="800000",
    )

    # Run the partition iterator
    partition_iterator.run()
    # partition_iterator.find_io_params_custom_logic(1)

    # partition_iterator.find_io_params_custom_logic(3)

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator_2 = PartitionIterator(
        alias_path_data=inputs3,
        alias_path_outputs=outputs3,
        custom_functions=[buffer_displacement_config],
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        dictionary_documentation_path=Building_N100.iteration___json_documentation___building_n100.value,
        feature_count="33000",
    )

    # Run the partition iterator
    # partition_iterator_2.run()
