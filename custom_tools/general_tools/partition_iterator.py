import arcpy
import os
import re
import shutil
import random
import json
from typing import Dict, Tuple, Literal
import time
from datetime import datetime
import pprint

import env_setup.global_config
import config
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from custom_tools.decorators.timing_decorator import timing_decorator

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools.polygon_processor import PolygonProcessor


from custom_tools.generalization_tools.building.buffer_displacement import (
    BufferDisplacement,
)
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


class PartitionIterator:
    """THIS IS WORK IN PROGRESS NOT READY FOR USE YET"""

    # Class-level constants
    PARTITION_FIELD = "partition_select"
    ORIGINAL_ID_FIELD = "original_id_field"

    def __init__(
        self,
        alias_path_data: Dict[
            str, Tuple[Literal["input", "context", "reference"], str]
        ],
        alias_path_outputs: Dict[str, Tuple[str, str]],
        root_file_partition_iterator: str,
        scale: str,
        custom_functions=None,
        dictionary_documentation_path: str = None,
        feature_count: str = "15000",
        partition_method: Literal["FEATURES", "VERTICES"] = "FEATURES",
        search_distance: str = "500 Meters",
        context_selection: bool = True,
        safe_output_final_cleanup: bool = True,
        object_id_field: str = "OBJECTID",
    ):
        """
        Initialize the PartitionIterator with input datasets for partitioning and processing.

        :param alias_path_data: A nested dictionary of input feature class paths with their aliases.
        :param root_file_partition_iterator: Base path for in progress outputs.
        :param scale: Scale for the partitions.
        :param alias_path_outputs: A nested dictionary of output feature class for final results.
        :param feature_count: Feature count for cartographic partitioning.
        :param partition_method: Method used for creating cartographic partitions.
        """

        # Raw inputs and initial setup
        self.raw_input_data = alias_path_data
        self.raw_output_data = alias_path_outputs or {}
        self.root_file_partition_iterator = root_file_partition_iterator
        if "." in dictionary_documentation_path:
            self.dictionary_documentation_path = re.sub(
                r"\.[^.]*$", "", dictionary_documentation_path
            )
        else:
            self.dictionary_documentation_path = dictionary_documentation_path

        self.scale = scale
        self.search_distance = search_distance
        self.feature_count = feature_count
        self.partition_method = partition_method
        self.object_id_field = object_id_field
        self.selection_of_context_features = context_selection
        self.safe_final_output_cleanup = safe_output_final_cleanup

        # Initial processing results
        self.nested_alias_type_data = {}
        self.nested_final_outputs = {}

        # Variables related to features and iterations
        self.partition_feature = f"{root_file_partition_iterator}_partition_feature"
        self.max_object_id = None
        self.current_iteration_id = None
        self.iteration_file_paths_list = []
        self.first_call_directory_documentation = True

        # Variables related to custom operations
        self.custom_functions = custom_functions or []
        self.custom_func_io_params = {}
        self.types_to_update = []

        self.total_start_time = None
        self.iteration_times_with_input = []
        self.iteration_start_time = None

    def unpack_alias_path_data(self, alias_path_data):
        """
        Process initial alias_path_data for inputs and outputs.
        """
        for alias, info in alias_path_data.items():
            if alias not in self.nested_alias_type_data:
                self.nested_alias_type_data[alias] = {}

            for i in range(0, len(info), 2):
                type_info = info[i]
                path_info = info[i + 1]
                self.nested_alias_type_data[alias][type_info] = path_info

    def unpack_alias_path_outputs(self, alias_path_outputs):
        """
        Process initial alias_path_outputs for outputs.
        """
        for alias, info in alias_path_outputs.items():
            if alias not in self.nested_final_outputs:
                self.nested_final_outputs[alias] = {}

            for i in range(0, len(info), 2):
                type_info = info[i]
                path_info = info[i + 1]
                self.nested_final_outputs[alias][type_info] = path_info

    def configure_alias_and_type(
        self,
        alias,
        type_name,
        type_path,
    ):
        # Check if alias exists, if not, create it
        if alias not in self.nested_alias_type_data:
            print(
                f"Alias '{alias}' not found in nested_alias_type_data. Creating new alias."
            )
            self.nested_alias_type_data[alias] = {}

        self.nested_alias_type_data[alias][type_name] = type_path
        print(f"Set path for type '{type_name}' in alias '{alias}' to: {type_path}")

    def create_new_alias(
        self,
        alias,
        initial_type_name=None,
        initial_type_path=None,
    ):
        # Check if alias already exists
        if alias in self.nested_alias_type_data:
            raise ValueError(f"Alias {alias} already exists.")

        # Initialize nested_alias_type_data for alias
        if initial_type_name:
            # Create alias with initial type and path
            self.nested_alias_type_data[alias] = {initial_type_name: initial_type_path}
        else:
            # Initialize alias as an empty dictionary
            self.nested_alias_type_data[alias] = {}

        print(
            f"Created new alias '{alias}' in nested_alias_type_data with type '{initial_type_name}' and path: {initial_type_path}"
        )

    def create_cartographic_partitions(self):
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
        """Deletes all existing final output files if they exist and are in the safe directory."""
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
        """Deletes multiple feature classes or files. Detailed alias and output_type logging is not available here."""
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

    def create_dummy_features(self, types_to_include=["input_copy", "context_copy"]):
        """
        Creates dummy features for aliases with specified types.

        Args:
            types_to_include (list): Types for which dummy features should be created.
        """
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
        target_dir: str,
        iteration: bool,
    ) -> str:
        """
        Creates a directory at the given root_path for the target_dir.
        Args:
            root_path: The root directory where initial structure is created
            target_dir: The target where the created directory should be placed
            iteration: Boolean flag indicating if the iteration_documentation should be added
        Returns:
            A string containing the absolute path of the created directory.
        """

        # Determine base directory
        directory_path = os.path.join(root_path, f"{target_dir}")

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
        object_id=None,
    ) -> None:
        """
        Writes dictionary into a json file.

           Args:
               data: The data to write.
               file_path: The complete path (directory+file_name) where the file should be created
               file_name: The name of the file to create
               object_id: If provided, object_id will also be part of the file name.
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
        object_id=None,
    ) -> None:
        """
        Handles the export of alias type data and final outputs into separate json files.

        Args:
            file_path: The complete file path where to create the output directories.
            alias_type_data: The alias type data to export.
            final_outputs: The final outputs data to export.
            file_name: The name of the file to create
            iteration: Boolean flag indicating if the iteration_documentation should be added
            object_id: Object ID to be included in the file name if it's an iteration (`iteration==True`). If `None`, will not be used.
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

    @staticmethod
    def generate_unique_field_name(input_feature, field_name):
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
    ):
        """
        Process input features for a given partition.
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

            count_points = int(
                arcpy.management.GetCount(
                    input_features_center_in_partition_selection
                ).getOutput(0)
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

    def _process_inputs_in_partition(self, aliases, iteration_partition, object_id):
        inputs_present_in_partition = False
        for alias in aliases:
            if "input_copy" in self.nested_alias_type_data[alias]:
                # Using process_input_features to check whether inputs are present
                input_present = self.process_input_features(
                    alias, iteration_partition, object_id
                )
                # Sets inputs_present_in_partition as True if any alias in partition has input present. Otherwise it remains False.
                inputs_present_in_partition = (
                    inputs_present_in_partition or input_present
                )
        return inputs_present_in_partition

    def process_context_features(self, alias, iteration_partition, object_id):
        """
        Process context features for a given partition if input features are present.
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

            count_points = int(
                arcpy.management.GetCount(context_data_iteration_selection).getOutput(0)
            )

            self.nested_alias_type_data[alias]["count"] = count_points

            if count_points > 0:
                print(f"{alias} has {count_points} features in {iteration_partition}")

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="context",
                    type_path=context_data_iteration_selection,
                )
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
        for alias in aliases:
            self.process_context_features(alias, iteration_partition, object_id)

    @staticmethod
    def format_time(seconds):
        """
        Convert seconds to a formatted string: HH:MM:SS.

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
        Track the iteration time and estimate the remaining time.

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

    def find_io_params_custom_logic(self, object_id):
        """
        Find and resolve the IO parameters for custom logic functions.
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

                print(f"\nResolving IO Params for object_id {object_id}")
                print(f"Before resolving: {custom_func['params']}")

                self.resolve_io_params(
                    param_type="input",
                    params=input_params,
                    custom_func=custom_func,
                    object_id=object_id,
                )
                self.resolve_io_params(
                    param_type="output",
                    params=output_params,
                    custom_func=custom_func,
                    object_id=object_id,
                )

                print(f"After resolving: {custom_func['params']}")

    def resolve_io_params(self, param_type, params, custom_func, object_id):
        """
        Resolve paths for input/output parameters of custom functions.
        """

        def resolve_param(param_info):
            if isinstance(param_info, tuple) and len(param_info) == 2:
                return self._handle_tuple_param(param_info, object_id)
            elif isinstance(param_info, dict):
                return {k: resolve_param(v) for k, v in param_info.items()}
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
            if len(resolved_paths) == 1:
                custom_func["params"][param] = resolved_paths[0]
            else:
                custom_func["params"][param] = resolved_paths

            print(
                f"Resolved {param_type} path for {param}: {custom_func['params'][param]}"
            )

    def _handle_tuple_param(self, param_info, object_id):
        """
        Handle the resolution of parameters that are tuples of (alias, alias_type).
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

    def construct_path_for_alias_type(self, alias, alias_type, object_id):
        """
        Construct a new path for a given alias and type specific to the current iteration.
        """
        base_path = self.root_file_partition_iterator
        constructed_path = f"{base_path}_{alias}_{alias_type}_{object_id}"
        return constructed_path

    def execute_custom_functions(self):
        """
        Execute custom functions with the resolved input and output paths.
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
                resolved_params = {**class_params, **method_params}
            else:
                # Handle standalone functions
                method = custom_func["func"]

                # Prepare parameters for the function call
                func_params = custom_func["params"]
                resolved_params = {param: path for param, path in func_params.items()}

                # Log the function parameters
                print(f"Function parameters for {method.__name__}: {resolved_params}")

                # Execute the function with resolved parameters
                method(**resolved_params)

    def append_iteration_to_final(self, alias, object_id):
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

    def partition_iteration(self):
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
                self.export_dictionaries_to_json(
                    file_name="iteration",
                    iteration=True,
                    object_id=object_id,
                )
                self.execute_custom_functions()
            if inputs_present_in_partition:
                for alias in aliases:
                    self.append_iteration_to_final(alias, object_id)
                self.delete_iteration_files(*self.iteration_file_paths_list)
            else:
                self.delete_iteration_files(*self.iteration_file_paths_list)
            self.track_iteration_time(object_id, inputs_present_in_partition)

    @timing_decorator
    def run(self):
        self.total_start_time = time.time()
        self.unpack_alias_path_data(self.raw_input_data)

        if self.raw_output_data is not None:
            self.unpack_alias_path_outputs(self.raw_output_data)

        self.export_dictionaries_to_json(file_name="post_initialization")
        print("Initialization done\n")

        print("\nStarting Data Preparation...")
        self.delete_final_outputs()
        self.prepare_input_data()
        self.export_dictionaries_to_json(file_name="post_data_preparation")

        print("\nCreating Cartographic Partitions...")
        self.create_cartographic_partitions()

        print("\nStarting on Partition Iteration...")
        self.partition_iteration()
        self.export_dictionaries_to_json(file_name="post_runtime")


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
            "sql_selection_query": N100_SQLResources.road_symbology_size_sql_selection.value,
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
        scale=env_setup.global_config.scale_n100,
        dictionary_documentation_path=Building_N100.iteration___json_documentation___building_n100.value,
        feature_count="400000",
    )

    # Run the partition iterator
    # partition_iterator.run()

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator_2 = PartitionIterator(
        alias_path_data=inputs3,
        alias_path_outputs=outputs3,
        custom_functions=[buffer_displacement_config],
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        scale=env_setup.global_config.scale_n100,
        dictionary_documentation_path=Building_N100.iteration___json_documentation___building_n100.value,
        feature_count="33000",
    )

    # Run the partition iterator
    partition_iterator_2.run()
