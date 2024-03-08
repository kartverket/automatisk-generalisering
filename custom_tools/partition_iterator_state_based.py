import arcpy
import os
import random

import env_setup.global_config
from env_setup import environment_setup
from custom_tools import custom_arcpy
from input_data import input_n50
from file_manager.n100.file_manager_buildings import Building_N100

# THIS IS WORK IN PROGRESS NOT READY FOR USE YET


class PartitionIterator:
    """THIS IS WORK IN PROGRESS NOT READY FOR USE YET"""

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

        :param alias_path_data: A dictionary of input feature class paths with their aliases.
        :param root_file_partition_iterator: Base path for in progress outputs.
        :param scale: Scale for the partitions.
        :param alias_path_outputs: The output feature class for final results.
        :param feature_count: Feature count for cartographic partitioning.
        :param partition_method: Method used for creating cartographic partitions.
        """
        self.data = {}
        for alias, info in alias_path_data.items():
            type_info, path_info = info
            if alias not in self.data:
                self.data[alias] = {}
            self.data[alias][type_info] = path_info

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
        self.final_append_features = {}
        self.search_distance = search_distance
        self.object_id_field = object_id_field

    def integrate_initial_data(self, alias_path_data, custom_function_specs):
        # Process initial alias_path_data for inputs and outputs
        for alias, (type_info, path_info) in alias_path_data.items():
            self.update_alias_state(
                alias=alias,
                type_info=type_info,
                path=path_info,
            )

            for func_name, specs in custom_function_specs.items():
                for alias, types in specs.items():
                    for type_info in types:
                        self.update_alias_state(
                            alias=alias,
                            type_info=type_info,
                            path=None,
                        )

    def update_alias_state(self, alias, type_info, path=None):
        if alias not in self.data:
            self.data[alias] = {}
        self.data[alias][type_info] = path

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
            if type_key in ["input", "context"] and path is not None
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
        """Deletes a feature class if it exists, with an optional detailed print statement for output feature classes."""
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)
            if alias and output_type:
                print(
                    f"Deleted existing output feature class for '{alias}' of type '{output_type}': {feature_class_path}"
                )
            else:
                print(f"Deleted feature class: {feature_class_path}")

    def delete_existing_outputs(self):
        for alias, output_info in self.output_feature_class.items():
            output_type, output_path = output_info
            current_path = self.data.get(alias, {}).get(output_type)
            if current_path == output_path and arcpy.Exists(current_path):
                PartitionIterator.delete_feature_class(
                    current_path,
                    alias=alias,
                    output_type=output_type,
                )
            else:
                print(
                    f"Output feature class for '{alias}' of type '{output_type}' does not exist or path does not match: {current_path}"
                )

    def delete_iteration_files(self, *file_paths):
        """Deletes multiple feature classes or files. Detailed alias and output_type logging is not available here."""
        for file_path in file_paths:
            self.delete_feature_class(file_path)

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

    def create_dummy_features(self, types_to_include=["input", "context"]):
        """
        Creates dummy features for aliases with specified types.

        Args:
            types_to_include (list): Types for which dummy features should be created.
        """
        for alias, types in self.data.items():
            # Check if alias has any of the specified types with valid paths
            for type_info, path in types.items():
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
                arcpy.management.Copy(
                    in_data=input_data_path,
                    out_data=input_data_copy,
                )
                print(f"Copied input data for: {alias}")

                # Update the path for 'input' type to the new copied path
                self.update_alias_state(
                    alias=alias,
                    type_info="input",
                    path=input_data_copy,
                )

                partition_field = "partition_select"
                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=partition_field,
                    field_type="LONG",
                )
                print(f"Added field {partition_field}")

                existing_field_names = [
                    field.name for field in arcpy.ListFields(input_data_copy)
                ]
                orig_id_field = "orig_id_field"
                while orig_id_field in existing_field_names:
                    orig_id_field = f"{orig_id_field}_{random.randint(0, 9)}"
                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=orig_id_field,
                    field_type="LONG",
                )
                print(f"Added field {orig_id_field}")

                arcpy.CalculateField_management(
                    in_table=input_data_copy,
                    field=orig_id_field,
                    expression=f"!{self.object_id_field}!",
                )
                print(f"Calculated field {orig_id_field}")

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

    def process_input_features(self, alias, iteration_partition):
        """
        Process input features for a given partition.
        """
        if "input" in self.data[alias]:
            input_path = self.data[alias]["input"]
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

            aliases_with_features = 0

            count_points = int(
                arcpy.management.GetCount(input_features_partition_selection).getOutput(
                    0
                )
            )
            input_features_partition_selection[alias] = count_points

            # Check if there are features for this alias
            if count_points > 0:
                print(f"{alias} has {count_points} features in {iteration_partition}")
                aliases_with_features += 1

                iteration_append_feature = f"{self.root_file_partition_iterator}_{alias}_iteration_append_feature_{self.scale}"
                self.iteration_file_paths.append(iteration_append_feature)
            return input_feature_count > 0

    def process_context_features(self, alias, iteration_partition):
        """
        Process context features for a given partition if input features are present.
        """
        if "context" in self.data[alias]:
            context_path = self.data[alias]["context"]
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

    def partition_iteration(
        self,
        input_data_copy,
        partition_feature,
        max_object_id,
        root_file_partition_iterator,
        scale,
        partition_field,
        orig_id_field,
        final_append_feature,
    ):
        self.delete_existing_outputs()
        self.create_dummy_features(types_to_include=["input", "context"])

        for object_id in range(1, max_object_id + 1):
            self.iteration_file_paths.clear()

            iteration_partition = f"{self.partition_feature}_{object_id}"
            self.select_partition_feature(iteration_partition, object_id)

            inputs_present_in_partition = False

            # Processing 'input' type features.
            for alias, details in self.data.items():
                if details["type"] == "input":
                    inputs_present = self.process_input_features(
                        alias, details, iteration_partition
                    )
                    inputs_present_in_partition |= inputs_present

            # Processing 'context' type features only if 'input' features are present.
            if inputs_present_in_partition:
                for alias, details in self.data.items():
                    if details["type"] == "context":
                        self.process_context_features(
                            alias, details, iteration_partition
                        )

        # Creating dummy features and selecting partition features for all types.
        for alias, details in self.data.items():
            dummy_feature_path = (
                f"{self.root_file_partition_iterator}_{alias}_dummy_{self.scale}"
            )
            self.create_feature_class(
                out_path=os.path.dirname(dummy_feature_path),
                out_name=os.path.basename(dummy_feature_path),
                template_feature=details["path"],
            )

        for object_id in range(1, max_object_id + 1):
            self.iteration_file_paths.clear()
            iteration_partition = f"{self.partition_feature}_{object_id}"
            # Flag to check if any input features exist in this partition.
            inputs_present_in_partition = False

            # Processing 'input' type features
            for alias, details in self.data.items():
                if details["type"] == "input":
                    input_features_partition_selection = (
                        f"in_memory/{alias}_partition_base_select_{scale}"
                    )
                    self.iteration_file_paths.append(input_features_partition_selection)
                    input_feature_count = custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=details["path"],
                        overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
                        select_features=iteration_partition,
                        output_name=input_features_partition_selection,
                    )

                    if input_feature_count > 0:
                        inputs_present_in_partition = True
                    # Processing 'context' type features only if 'input' features are present in this partition.
                    if inputs_present_in_partition:
                        for alias, details in self.data.items():
                            if details["type"] == "context":
                                context_selection_path = f"{self.root_file_partition_iterator}_{alias}_context_iteration_selection_{object_id}"
                                self.iteration_file_paths.append(context_selection_path)

                                custom_arcpy.select_location_and_make_permanent_feature(
                                    input_layer=details["path"],
                                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                                    select_features=iteration_partition,
                                    output_name=context_selection_path,
                                    selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                                    search_distance=self.search_distance,
                                )

        aliases_feature_counts = {alias: 0 for alias in self.alias}

        for object_id in range(1, max_object_id + 1):
            self.iteration_file_paths.clear()
            for alias in self.alias:
                # Retrieve the output path for the current alias
                output_path = self.outputs.get(alias)

                if object_id == 1:
                    self.delete_feature_class(output_path)

            print(f"\nProcessing {self.object_id_field} {object_id}")
            iteration_partition = f"{partition_feature}_{object_id}"
            self.iteration_file_paths.append(iteration_partition)

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=partition_feature,
                expression=f"{self.object_id_field} = {object_id}",
                output_name=iteration_partition,
            )

            # Check for features for each alias and set features_present accordingly
            for alias in self.alias:
                input_data_copy = self.file_mapping[alias]["current_output"]
                base_partition_selection = (
                    f"in_memory/{alias}_partition_base_select_{scale}"
                )
                self.iteration_file_paths.append(base_partition_selection)

                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=input_data_copy,
                    overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
                    select_features=iteration_partition,
                    output_name=base_partition_selection,
                )

                aliases_with_features = 0

                count_points = int(
                    arcpy.management.GetCount(base_partition_selection).getOutput(0)
                )
                aliases_feature_counts[alias] = count_points

                # Check if there are features for this alias
                if count_points > 0:
                    print(
                        f"{alias} has {count_points} features in {iteration_partition}"
                    )
                    aliases_with_features += 1

                    iteration_append_feature = f"{root_file_partition_iterator}_{alias}_iteration_append_feature_{scale}"
                    self.iteration_file_paths.append(iteration_append_feature)

                    self.create_feature_class(
                        out_path=os.path.dirname(iteration_append_feature),
                        out_name=os.path.basename(iteration_append_feature),
                        template_feature=input_data_copy,
                    )

                    arcpy.CalculateField_management(
                        in_table=base_partition_selection,
                        field=partition_field,
                        expression="1",
                    )

                    arcpy.management.Append(
                        inputs=base_partition_selection,
                        target=iteration_append_feature,
                        schema_type="NO_TEST",
                    )

                    base_partition_selection_2 = (
                        f"in_memory/{alias}_partition_base_select_2_{scale}"
                    )
                    self.iteration_file_paths.append(base_partition_selection_2)

                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=input_data_copy,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                        select_features=iteration_partition,
                        output_name=base_partition_selection_2,
                        selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                        search_distance=self.search_distance,
                    )

                    arcpy.management.SelectLayerByLocation(
                        in_layer=base_partition_selection_2,
                        overlap_type="HAVE_THEIR_CENTER_IN",
                        select_features=iteration_partition,
                        selection_type="REMOVE_FROM_SELECTION",
                    )

                    arcpy.CalculateField_management(
                        in_table=base_partition_selection_2,
                        field=partition_field,
                        expression="0",
                    )

                    arcpy.management.Append(
                        inputs=base_partition_selection_2,
                        target=iteration_append_feature,
                        schema_type="NO_TEST",
                    )

                    print(
                        f"iteration partition {base_partition_selection_2} appended to {iteration_append_feature}"
                    )
                else:
                    print(
                        f"iteration partition {object_id} has no features for {alias} in the partition feature"
                    )

                # If no aliases had features, skip the rest of the processing for this object_id
            if aliases_with_features == 0:
                for alias in self.alias:
                    self.delete_iteration_files(*self.iteration_file_paths)
                continue

            for func in self.custom_functions:
                try:
                    pass
                    # Determine inputs for the current function
                    # inputs = [
                    #     self.file_mapping[fc]["func_output"] or fc
                    #     for fc in self.input_feature_classes
                    # ]

                    # Call the function and get outputs
                    outputs = func(inputs)

                    # Update file mapping with the outputs
                    for fc, output in zip(self.input_feature_classes, outputs):
                        self.file_mapping[fc]["current_output"] = output
                except:
                    print(f"Error in custom function: {func}")

                # Process each alias after custom functions
            for alias in self.alias:
                if aliases_feature_counts[alias] > 0:
                    # Retrieve the output path for the current alias
                    output_path = self.outputs.get(alias)
                    iteration_append_feature = f"{root_file_partition_iterator}_{alias}_iteration_append_feature_{scale}"

                    if not arcpy.Exists(output_path):
                        self.create_feature_class(
                            out_path=os.path.dirname(output_path),
                            out_name=os.path.basename(output_path),
                            template_feature=iteration_append_feature,
                        )

                    partition_target_selection = (
                        f"in_memory/{alias}_partition_target_selection_{scale}"
                    )
                    self.iteration_file_paths.append(partition_target_selection)

                    custom_arcpy.select_attribute_and_make_permanent_feature(
                        input_layer=iteration_append_feature,
                        expression=f"{partition_field} = 1",
                        output_name=partition_target_selection,
                    )

                    print(
                        f"for {alias} in {iteration_append_feature} \nThe input is: {partition_target_selection}\nAppending to {output_path}"
                    )

                    arcpy.management.Append(
                        inputs=partition_target_selection,
                        target=output_path,
                        schema_type="NO_TEST",
                    )
                else:
                    print(
                        f"No features found in {alias} for {self.object_id_field} {object_id} to append to {output_path}"
                    )

            for alias in self.alias:
                self.delete_iteration_files(*self.iteration_file_paths)
            print(f"Finished iteration {object_id}")

    def run(self):
        environment_setup.main()
        self.create_cartographic_partitions()

        max_object_id = self.pre_iteration()

        self.prepare_input_data()

        # self.partition_iteration(
        #     [self.file_mapping[alias]["current_output"] for alias in self.alias],
        #     self.partition_feature,
        #     max_object_id,
        #     self.root_file_partition_iterator,
        #     self.scale,
        #     "partition_select",
        #     "id_field",
        #     [self.final_append_features.get(alias) for alias in self.alias],
        # )


if __name__ == "__main__":
    # Define your input feature classes and their aliases
    building_points = "building_points"
    building_polygons = "building_polygons"

    inputs = {
        building_points: [
            "input",
            Building_N100.data_preparation___matrikkel_bygningspunkt___n100_building.value,
        ],
        building_polygons: [
            "context",
            input_n50.Grunnriss,
        ],
    }

    outputs = {
        building_points: [
            "output",
            Building_N100.iteration__partition_iterator_final_output_points__n100.value,
        ],
        building_polygons: [
            "output",
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