import arcpy
import os
import random
import json

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
    ORIGINAL_ID_FIELD = "orig_id_field"

    def __init__(
        self,
        alias_path_data,
        root_file_partition_iterator,
        scale,
        alias_path_outputs,
        custom_functions=None,
        feature_count="15000",
        partition_method="FEATURES",
        search_distance="500 Meters",
        object_id_field="OBJECTID",
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

        self.data = {}
        self.alias_path_data = alias_path_data
        self.alias_path_outputs = alias_path_outputs or {}
        print("\nInitializing with alias_path_outputs = ", alias_path_outputs)
        self.root_file_partition_iterator = root_file_partition_iterator
        self.scale = scale
        self.output_feature_class = alias_path_outputs
        self.feature_count = feature_count
        self.partition_method = partition_method
        self.partition_feature = (
            f"{root_file_partition_iterator}_partition_feature_{scale}"
        )
        self.custom_functions = custom_functions or []
        self.iteration_file_paths = []
        self.final_outputs = {}
        self.search_distance = search_distance
        self.object_id_field = object_id_field

        self.input_data_copy = None
        self.max_object_id = None
        self.final_append_feature = None

    def integrate_initial_data(self, alias_path_data):
        # Process initial alias_path_data for inputs and outputs
        for alias, info in alias_path_data.items():
            type_info, path_info = info
            if alias not in self.data:
                self.data[alias] = {}
            self.data[alias][type_info] = path_info

            # for func_name, specs in custom_function_specs.items():
            #     for alias, types in specs.items():
            #         for type_info in types:
            #             self.update_alias_state(
            #                 alias=alias,
            #                 type_info=type_info,
            #                 path=None,
            #             )

    def unpack_alias_path_outputs(self, alias_path_outputs):
        self.final_outputs = {}
        for alias, info in alias_path_outputs.items():
            type_info, path_info = info
            if alias not in self.final_outputs:
                self.final_outputs[alias] = {}
            self.final_outputs[alias][type_info] = path_info
            print("\nUnpacking alias_path_outputs = ", alias_path_outputs)

    def integrate_results(self):
        for alias, types in self.final_outputs.items():
            for type_info, final_output_path in types.items():
                iteration_output_path = self.data[alias][type_info]

    def update_alias_state(self, alias, type_info, path=None):
        if alias not in self.data:
            self.data[alias] = {}
        self.data[alias][type_info] = path

    def add_type_to_alias(self, alias, new_type, new_type_path=None):
        """Adds a new type with optional file path to an existing alias."""
        if alias not in self.data:
            print(f"Alias '{alias}' not found in data.")
            return

        if new_type in self.data[alias]:
            print(
                f"Type '{new_type}' already exists for alias '{alias}'. Current path: {self.data[alias][new_type]}"
            )
            return

        self.data[alias][new_type] = new_type_path
        print(
            f"Added type '{new_type}' to alias '{alias}' in data with path: {new_type_path}"
        )

    def create_new_alias(self, alias, initial_states):
        if alias in self.data:
            raise ValueError(f"Alias {alias} already exists.")
        self.data[alias] = initial_states

    def get_path_for_alias_and_type(self, alias, type_info):
        return self.data.get(alias, {}).get(type_info)

    def create_cartographic_partitions(self):
        print("Debugging self.data before partition creation:", self.data)
        all_features = [
            path
            for alias, types in self.data.items()
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
        for alias in self.final_outputs:
            for _, output_file_path in self.final_outputs[alias].items():
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
        for alias, alias_data in self.data.items():
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
                    self.update_alias_state(
                        alias=alias,
                        type_info="dummy",
                        path=dummy_feature_path,
                    )

    def initialize_dummy_used(self):
        # Assuming `aliases` is a list of all your aliases
        for alias in self.data:
            self.data[alias]["dummy_used"] = False

    def reset_dummy_used(self):
        # Assuming `aliases` is a list of all your aliases
        for alias in self.data:
            self.data[alias]["dummy_used"] = False

    def update_alias_with_dummy_if_needed(self, alias, type_info):
        # Check if the dummy type exists in the alias data
        if "dummy" in self.data[alias]:
            # Check if the input type exists in the alias data
            if (
                type_info in self.data[alias]
                and self.data[alias][type_info] is not None
            ):
                # Get the dummy path from the alias data
                dummy_path = self.data[alias]["dummy"]
                # Set the value of the existing type_info to the dummy path
                self.data[alias][type_info] = dummy_path
                self.data[alias]["dummy_used"] = True
                print(
                    f"The '{type_info}' for alias '{alias}' was updated with dummy path: {dummy_path}"
                )
            else:
                print(f"'{type_info}' does not exist for alias '{alias}' in data.")
        else:
            print(f"'dummy' type does not exist for alias '{alias}' in data.")

    def write_data_to_json(self, file_name):
        with open(file_name, "w") as file:
            json.dump(self.data, file, indent=4)

    def pre_iteration(self):
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
                max_object_id = next(cursor)[0]

            print(f"Maximum {self.object_id_field} found: {max_object_id}")

            return max_object_id
        except Exception as e:
            print(f"Error in finding max {self.object_id_field}: {e}")

    def prepare_input_data(self):
        for alias, types in self.data.items():
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
                print(f"Copied input data for: {alias}")

                # Add a new type for the alias the copied input data
                self.add_type_to_alias(
                    alias=alias,
                    new_type="input_copy",
                    new_type_path=input_data_copy,
                )

                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=self.PARTITION_FIELD,
                    field_type="LONG",
                )
                print(f"Added field {self.PARTITION_FIELD}")

                # Making sure the field is unique if it exists a field with the same name
                existing_field_names = [
                    field.name for field in arcpy.ListFields(input_data_copy)
                ]
                unique_orig_id_field = self.ORIGINAL_ID_FIELD
                while unique_orig_id_field in existing_field_names:
                    unique_orig_id_field = (
                        f"{self.ORIGINAL_ID_FIELD}_{random.randint(0, 9)}"
                    )
                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=unique_orig_id_field,
                    field_type="LONG",
                )
                print(f"Added field {unique_orig_id_field}")

                arcpy.CalculateField_management(
                    in_table=input_data_copy,
                    field=unique_orig_id_field,
                    expression=f"!{self.object_id_field}!",
                )
                print(f"Calculated field {unique_orig_id_field}")

                # Update the instance variable if a new unique field name was created
                self.ORIGINAL_ID_FIELD = unique_orig_id_field

            if "context" in types:
                context_data_path = types["context"]
                context_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_context_copy"
                )
                # self.delete_feature_class(input_data_copy)
                arcpy.management.Copy(
                    in_data=context_data_path,
                    out_data=context_data_copy,
                )
                print(f"Copied context data for: {alias}")

                self.add_type_to_alias(
                    alias=alias,
                    new_type="context_copy",
                    new_type_path=context_data_copy,
                )

    def custom_function(inputs):
        outputs = []
        return outputs

    def select_partition_feature(self, iteration_partition, object_id):
        """
        Selects partition feature based on OBJECTID.
        """
        self.iteration_file_paths.append(iteration_partition)
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.partition_feature,
            expression=f"{self.object_id_field} = {object_id}",
            output_name=iteration_partition,
        )
        print(f"Created partition selection for OBJECTID {object_id}")

    def process_input_features(
        self,
        alias,
        iteration_partition,
        object_id,
    ):
        """
        Process input features for a given partition.
        """
        if "input_copy" not in self.data[alias]:
            return None, False

        if "input_copy" in self.data[alias]:
            input_path = self.data[alias]["input_copy"]
            input_features_partition_selection = (
                f"in_memory/{alias}_partition_base_select_{self.scale}"
            )
            self.iteration_file_paths.append(input_features_partition_selection)

            input_feature_count = custom_arcpy.select_location_and_make_feature_layer(
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
                # aliases_with_features += 1

                arcpy.CalculateField_management(
                    in_table=input_features_partition_selection,
                    field=self.PARTITION_FIELD,
                    expression="1",
                )

                iteration_append_feature = f"{self.root_file_partition_iterator}_{alias}_iteration_append_feature_{self.scale}"
                self.iteration_file_paths.append(iteration_append_feature)

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
                self.iteration_file_paths.append(
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

                self.update_alias_state(
                    alias=alias,
                    type_info="input",
                    path=iteration_append_feature,
                )

                print(
                    f"iteration partition {input_features_partition_context_selection} appended to {iteration_append_feature}"
                )
                return aliases_with_features, True
            else:
                # Loads in dummy feature for this alias for this iteration and sets dummy_used = True
                self.update_alias_with_dummy_if_needed(
                    alias,
                    type_info="input",
                )
                print(
                    f"iteration partition {object_id} has no features for {alias} in the partition feature"
                )
            return None, False

    def _process_inputs_in_partition(self, aliases, iteration_partition, object_id):
        inputs_present_in_partition = False
        for alias in aliases:
            if "input_copy" in self.data[alias]:
                _, input_present = self.process_input_features(
                    alias, iteration_partition, object_id
                )
                inputs_present_in_partition = (
                    inputs_present_in_partition or input_present
                )
        return inputs_present_in_partition

    def process_context_features(self, alias, iteration_partition):
        """
        Process context features for a given partition if input features are present.
        """
        if "context_copy" in self.data[alias]:
            context_path = self.data[alias]["context_copy"]
            context_selection_path = f"{self.root_file_partition_iterator}_{alias}_context_iteration_selection"
            self.iteration_file_paths.append(context_selection_path)

            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=context_path,
                overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                select_features=iteration_partition,
                output_name=context_selection_path,
                selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                search_distance=self.search_distance,
            )

            self.update_alias_state(
                alias=alias,
                type_info="context",
                path=context_selection_path,
            )

    def _process_context_features_and_others(
        self, aliases, iteration_partition, object_id
    ):
        for alias in aliases:
            if "context_copy" not in self.data[alias]:
                # Loads in dummy feature for this alias for this iteration and sets dummy_used = True
                self.update_alias_with_dummy_if_needed(
                    alias,
                    type_info="context",
                )
                print(
                    f"iteration partition {object_id} has no context features for {alias} in the partition feature"
                )
            else:
                self.process_context_features(alias, iteration_partition)

    def append_iteration_to_final(self, alias):
        # Guard clause if alias doesn't exist in final_outputs
        if alias not in self.final_outputs:
            return

        # For each type under current alias, append the result of the current iteration
        for type_info, final_output_path in self.final_outputs[alias].items():
            if self.data[alias]["dummy_used"]:
                continue

            input_feature_class = self.data[alias][type_info]

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
            self.iteration_file_paths.append(partition_target_selection)
            self.iteration_file_paths.append(input_feature_class)

            # Apply feature selection
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=input_feature_class,
                expression=f"{self.PARTITION_FIELD} = 1",
                output_name=partition_target_selection,
            )

            # Number of features before append/copy
            orig_num_features = (
                int(arcpy.GetCount_management(final_output_path).getOutput(0))
                if arcpy.Exists(final_output_path)
                else 0
            )
            print(f"\nNumber of features originally in the file: {orig_num_features}")

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

            # Number of features after append/copy
            new_num_features = int(
                arcpy.GetCount_management(final_output_path).getOutput(0)
            )
            print(f"\nNumber of features after append/copy: {new_num_features}")

    def _append_iteration_to_final_and_others(self, alias):
        self.append_iteration_to_final(alias)

    def partition_iteration(self):
        aliases = self.data.keys()
        max_object_id = self.pre_iteration()

        # self.delete_existing_outputs()
        self.create_dummy_features(types_to_include=["input_copy", "context_copy"])
        self.initialize_dummy_used()

        self.delete_iteration_files(*self.iteration_file_paths)
        self.iteration_file_paths.clear()

        for object_id in range(1, max_object_id + 1):
            self.reset_dummy_used()
            self.iteration_file_paths.clear()
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
                self.delete_iteration_files(*self.iteration_file_paths)
            else:
                self.delete_iteration_files(*self.iteration_file_paths)

    @timing_decorator
    def run(self):
        self.integrate_initial_data(self.alias_path_data)
        if self.alias_path_outputs is not None:
            self.unpack_alias_path_outputs(self.alias_path_outputs)
        print("\nAfter unpacking, final_outputs = ", self.final_outputs)
        self.delete_final_outputs()
        self.prepare_input_data()
        self.create_cartographic_partitions()

        self.write_data_to_json(
            Building_N100.iteration___json_documentation_before___building_n100.value
        )

        self.partition_iteration()

        self.write_data_to_json(
            Building_N100.iteration___json_documentation_after___building_n100.value
        )


if __name__ == "__main__":
    environment_setup.main()
    # Define your input feature classes and their aliases
    building_points = "building_points"
    building_polygons = "building_polygons"

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
    )

    # Run the partition iterator
    partition_iterator.run()


""""
Can I use pattern matching (match) to find the alias for each param?



self.data = {
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
Working on append_iteration_to_final need it to select the correct file from nested dictionary based on type for alias

"""
