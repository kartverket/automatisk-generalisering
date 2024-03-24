import arcpy
import os
import re
import shutil
import random
import json
from typing import Dict, Tuple, Literal

import env_setup.global_config
from env_setup import environment_setup
from custom_tools import custom_arcpy
from custom_tools.timing_decorator import timing_decorator

from input_data import input_n50
from file_manager.n100.file_manager_buildings import Building_N100

# THIS IS WORK IN PROGRESS NOT READY FOR USE YET


class PartitionIterator:
    """THIS IS WORK IN PROGRESS NOT READY FOR USE YET"""

    # Class-level constants
    PARTITION_FIELD = "partition_select"
    ORIGINAL_ID_FIELD = "original_id_field"

    def __init__(
        self,
        alias_path_data: Dict[str, Tuple[Literal["input", "context"], str]],
        alias_path_outputs: Dict[str, Tuple[str, str]],
        root_file_partition_iterator: str,
        scale: str,
        custom_functions=None,
        dictionary_documentation_path: str = None,
        feature_count: str = "15000",
        partition_method: Literal["FEATURES", "VERTICES"] = "FEATURES",
        search_distance: str = "500 Meters",
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

        # Initial processing results
        self.nested_alias_type_data = {}
        self.nested_final_outputs = {}

        # Variables related to features and iterations
        self.partition_feature = (
            f"{root_file_partition_iterator}_partition_feature_{scale}"
        )
        self.max_object_id = None
        self.iteration_file_paths_list = []
        self.first_call_directory_documentation = True

        # Variables related to custom operations
        self.custom_functions = custom_functions or []

        # self.handle_data_export(
        #     file_path=self.dictionary_documentation_path,
        #     alias_type_data=self.nested_alias_type_data,
        #     final_outputs=self.nested_final_outputs,
        #     file_name="initialization",
        #     iteration=False,
        #     object_id=None,
        # )

    def unpack_alias_path_data(self, alias_path_data):
        # Process initial alias_path_data for inputs and outputs
        for alias, info in alias_path_data.items():
            type_info, path_info = info
            if alias not in self.nested_alias_type_data:
                self.nested_alias_type_data[alias] = {}
            self.nested_alias_type_data[alias][type_info] = path_info

    def unpack_alias_path_outputs(self, alias_path_outputs):
        self.nested_final_outputs = {}
        for alias, info in alias_path_outputs.items():
            type_info, path_info = info
            if alias not in self.nested_final_outputs:
                self.nested_final_outputs[alias] = {}
            self.nested_final_outputs[alias][type_info] = path_info

    def configure_alias_and_type(
        self,
        alias,
        type_name,
        type_path,
    ):
        # Check if alias exists
        if alias not in self.nested_alias_type_data:
            print(f"Alias '{alias}' not found in nested_alias_type_data.")
            return

        # Update path of an existing type or add a new type with the provided path
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

    def delete_feature_class(self, feature_class_path, alias=None, output_type=None):
        """Deletes a feature class if it exists."""
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)
            if alias and output_type:
                print(
                    f"Deleted existing output feature class for '{alias}' of type '{output_type}': {feature_class_path}"
                )
            else:
                print(f"Deleted feature class: {feature_class_path}")

    def delete_final_outputs(self):
        """Deletes all final output files if they exist."""
        for alias in self.nested_final_outputs:
            for _, output_file_path in self.nested_final_outputs[alias].items():
                if arcpy.Exists(output_file_path):
                    arcpy.management.Delete(output_file_path)
                    print(f"Deleted file: {output_file_path}")

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
                    dummy_feature_path = f"{self.root_file_partition_iterator}_{alias}_dummy_{self.scale}"
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

    def initialize_dummy_used(self):
        # Assuming `aliases` is a list of all your aliases
        for alias in self.nested_alias_type_data:
            self.nested_alias_type_data[alias]["dummy_used"] = False

    def reset_dummy_used(self):
        # Assuming `aliases` is a list of all your aliases
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

    def create_directory(
        self,
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
            iteration_documentation_dir = os.path.join(
                directory_path, "iteration_documentation"
            )
            os.makedirs(iteration_documentation_dir, exist_ok=True)

            return iteration_documentation_dir

        return directory_path

    def write_data_to_json(
        self,
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

    def handle_data_export(
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

        alias_type_data_directory = self.create_directory(
            file_path, "nested_alias_type_data", iteration
        )
        final_outputs_directory = self.create_directory(
            file_path, "nested_final_outputs", iteration
        )

        self.write_data_to_json(
            alias_type_data, alias_type_data_directory, file_name, object_id
        )
        self.write_data_to_json(
            final_outputs, final_outputs_directory, file_name, object_id
        )

    def generate_unique_field_name(self, input_feature, field_name):
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
                    f"{self.root_file_partition_iterator}_{alias}_input_copy"
                )
                # self.delete_feature_class(input_data_copy)
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

            if "context" in types:
                context_data_path = types["context"]
                context_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_context_copy"
                )

                arcpy.management.Copy(
                    in_data=context_data_path,
                    out_data=context_data_copy,
                )
                print(f"Copied context nested_alias_type_data for: {alias}")

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="context_copy",
                    type_path=context_data_copy,
                )

    def custom_function(inputs):
        outputs = []
        return outputs

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
        print(f"\nCreated partition selection for OBJECTID {object_id}")

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
            input_features_partition_selection = (
                f"in_memory/{alias}_partition_base_select_{self.scale}"
            )
            self.iteration_file_paths_list.append(input_features_partition_selection)

            custom_arcpy.select_location_and_make_feature_layer(
                input_layer=input_path,
                overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
                select_features=iteration_partition,
                output_name=input_features_partition_selection,
            )

            aliases_with_features = {}
            count_points = int(
                arcpy.management.GetCount(input_features_partition_selection).getOutput(
                    0
                )
            )
            aliases_with_features[alias] = count_points

            if aliases_with_features[alias] > 0:
                print(f"{alias} has {count_points} features in {iteration_partition}")

                arcpy.CalculateField_management(
                    in_table=input_features_partition_selection,
                    field=self.PARTITION_FIELD,
                    expression="1",
                )

                iteration_append_feature = f"{self.root_file_partition_iterator}_{alias}_iteration_append_feature_{self.scale}"
                self.iteration_file_paths_list.append(iteration_append_feature)

                PartitionIterator.create_feature_class(
                    full_feature_path=iteration_append_feature,
                    template_feature=input_features_partition_selection,
                )

                arcpy.management.Append(
                    inputs=input_features_partition_selection,
                    target=iteration_append_feature,
                    schema_type="NO_TEST",
                )

                input_features_partition_context_selection = f"in_memory/{alias}_input_features_partition_context_selection_{self.scale}"
                self.iteration_file_paths_list.append(
                    input_features_partition_context_selection
                )

                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=input_path,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                    select_features=iteration_partition,
                    output_name=input_features_partition_context_selection,
                    selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                    search_distance=self.search_distance,
                )

                arcpy.management.SelectLayerByLocation(
                    in_layer=input_features_partition_context_selection,
                    overlap_type="HAVE_THEIR_CENTER_IN",
                    select_features=iteration_partition,
                    selection_type="REMOVE_FROM_SELECTION",
                )

                arcpy.CalculateField_management(
                    in_table=input_features_partition_context_selection,
                    field=self.PARTITION_FIELD,
                    expression="0",
                )

                arcpy.management.Append(
                    inputs=input_features_partition_context_selection,
                    target=iteration_append_feature,
                    schema_type="NO_TEST",
                )

                self.configure_alias_and_type(
                    alias=alias,
                    type_name="input",
                    type_path=iteration_append_feature,
                )

                print(
                    f"iteration partition {input_features_partition_context_selection} appended to {iteration_append_feature}"
                )
                # Return the processed input features and a flag indicating successful operation
                return aliases_with_features, True
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
            return None, False

    def _process_inputs_in_partition(self, aliases, iteration_partition, object_id):
        inputs_present_in_partition = False
        for alias in aliases:
            if "input_copy" in self.nested_alias_type_data[alias]:
                # Using process_input_features to check whether inputs are present
                _, input_present = self.process_input_features(
                    alias, iteration_partition, object_id
                )
                # Sets inputs_present_in_partition as True if any alias in partition has input present. Otherwise it remains False.
                inputs_present_in_partition = (
                    inputs_present_in_partition or input_present
                )
        return inputs_present_in_partition

    def process_context_features(self, alias, iteration_partition):
        """
        Process context features for a given partition if input features are present.
        """
        if "context_copy" in self.nested_alias_type_data[alias]:
            context_path = self.nested_alias_type_data[alias]["context_copy"]
            context_selection_path = f"{self.root_file_partition_iterator}_{alias}_context_iteration_selection"
            self.iteration_file_paths_list.append(context_selection_path)

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=context_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=context_selection_path,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                search_distance=self.search_distance,
            )

            self.configure_alias_and_type(
                alias=alias,
                type_name="context",
                type_path=context_selection_path,
            )

    def _process_context_features_and_others(
        self, aliases, iteration_partition, object_id
    ):
        for alias in aliases:
            if "context_copy" not in self.nested_alias_type_data[alias]:
                # Loads in dummy feature for this alias for this iteration and sets dummy_used = True
                self.update_empty_alias_type_with_dummy_file(
                    alias,
                    type_info="context",
                )
                print(
                    f"iteration partition {object_id} has no context features for {alias} in the partition feature"
                )
            else:
                self.process_context_features(alias, iteration_partition)

    def append_iteration_to_final(self, alias):
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
                f"in_memory/{alias}_{type_info}_partition_target_selection_{self.scale}"
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
        self.initialize_dummy_used()

        self.delete_iteration_files(*self.iteration_file_paths_list)
        self.iteration_file_paths_list.clear()

        for object_id in range(1, self.max_object_id + 1):
            self.reset_dummy_used()
            self.handle_data_export(
                file_name="iteration_start",
                iteration=True,
                object_id=object_id,
            )
            self.iteration_file_paths_list.clear()
            iteration_partition = f"{self.partition_feature}_{object_id}"
            self.select_partition_feature(iteration_partition, object_id)

            inputs_present_in_partition = self._process_inputs_in_partition(
                aliases, iteration_partition, object_id
            )
            if inputs_present_in_partition:
                self._process_context_features_and_others(
                    aliases, iteration_partition, object_id
                )
            if inputs_present_in_partition:
                for alias in aliases:
                    self.append_iteration_to_final(alias)
                self.delete_iteration_files(*self.iteration_file_paths_list)
            else:
                self.delete_iteration_files(*self.iteration_file_paths_list)

            self.handle_data_export(
                file_name="iteration_end",
                iteration=True,
                object_id=object_id,
            )

    @timing_decorator
    def run(self):
        self.unpack_alias_path_data(self.raw_input_data)
        if self.raw_output_data is not None:
            self.unpack_alias_path_outputs(self.raw_output_data)

        self.handle_data_export(file_name="post_alias_unpack")

        self.delete_final_outputs()
        self.prepare_input_data()

        self.create_cartographic_partitions()

        self.partition_iteration()
        self.handle_data_export(file_name="post_everything")


if __name__ == "__main__":
    environment_setup.main()
    # Define your input feature classes and their aliases
    building_points = "building_points"
    building_polygons = "building_polygons"
    church_hospital = "church_hospital"
    restriction_lines = "restriction_lines"

    inputs = {
        building_points: [
            "input",
            Building_N100.data_preparation___matrikkel_bygningspunkt___n100_building.value,
        ],
        building_polygons: [
            "input",
            input_n50.Grunnriss,
        ],
    }

    outputs = {
        building_points: [
            "input",
            Building_N100.iteration__partition_iterator_final_output_points__n100.value,
        ],
        building_polygons: [
            "input",
            Building_N100.iteration__partition_iterator_final_output_polygons__n100.value,
        ],
    }

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        scale=env_setup.global_config.scale_n100,
        dictionary_documentation_path=Building_N100.iteration___partition_iterator_json_documentation___building_n100.value,
    )

    # Run the partition iterator
    partition_iterator.run()

    # inputs_2 = {
    #     church_hospital: [
    #         "input",
    #         Building_N100.polygon_propogate_displacement___hospital_church_points___n100_building.value,
    #     ],
    #     restriction_lines: [
    #         "input",
    #         Building_N100.polygon_propogate_displacement___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
    #     ],
    # }
    #
    # outputs_2 = {
    #     church_hospital: [
    #         "input",
    #         f"{Building_N100.iteration__partition_iterator_final_output_points__n100.value}_church_hospital",
    #     ],
    #     restriction_lines: [
    #         "input",
    #         f"{Building_N100.iteration__partition_iterator_final_output_polygons__n100.value}_restriction_lines",
    #     ],
    # }
    #
    # partition_iterator_2 = PartitionIterator(
    #     alias_path_data=inputs_2,
    #     alias_path_outputs=outputs_2,
    #     root_file_partition_iterator=f"{Building_N100.iteration__partition_iterator__n100.value}_2",
    #     scale=env_setup.global_config.scale_n100,
    # )
    #
    # # Run the partition iterator
    # partition_iterator_2.run()


""""
Can I use pattern matching (match) to find the alias for each param?



self.nested_alias_type_data = {
    'alias_1': {
        'input': 'file_path_1',
        'function_1': 'file_path_3',
        'function_2': 'file_path_4',
    },
    
    'alias_2': {
        'context': 'file_path_2',
        'function_1': 'file_path_5',
        'function_2': 'file_path_6',
    },


inputs = {
    alias_1: [
        "input",
        file_path_1,
    ],
    alias_2: [
        "context",
        file_path_2,
    ],
}

outputs = {
    alias_1: [
        "function_1",
        file_path_3,
    ],
    alias_2: [
        "function_2",
        file_path_6,
    ],
}

custom_functions = {
    "function_1": {
        "function": function_1,
        "inputs": ["alias_1":input, "alias_2":context],
        "outputs": ["alias_1":function_1],
        "additional_params": {
            "building_symbol_dimensions": building_symbol_dimensions,
            "symbol_field_name": "symbol_val",
            "index_field_name": "OBJECTID",
        },
        
    "function_2": {
        "function": function_2,
        "inputs": ["alias_1":function_1, "alias_2":context],
        "outputs": ["alias_2":function_2],
        "additional_params": {
            "building_symbol_dimensions": building_symbol_dimensions,
            "symbol_field_name": "symbol_val",
            "index_field_name": "OBJECTID",
        },
        

partition_iterator = PartitionIterator(
    alias_path_data=inputs,
    alias_path_outputs=outputs,
    root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
    scale=env_setup.global_config.scale_n100,
)

partition_iterator.run()
        
"""

# Thoughts on PartitionIterator:

"""
Building_N100.iteration___json_documentation_after___building_n100.value

"""
