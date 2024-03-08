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
        output_feature_class,
        custom_functions=None,
        feature_count="15000",
        partition_method="FEATURES",
        search_distance="500 Meters",
        object_id_field="OBJECTID",
    ):
        """
        Initialize the PartitionIterator with input datasets for partitioning and processing.

        :param alias_path_inputs: A dictionary of input feature class paths with their aliases.
        :param root_file_partition_iterator: Base path for in progress outputs.
        :param scale: Scale for the partitions.
        :param output_feature_class: The output feature class for final results.
        :param feature_count: Feature count for cartographic partitioning.
        :param partition_method: Method used for creating cartographic partitions.
        """
        self.data = {
            alias: {"type": type_info, "path": path_info}
            for alias, (type_info, path_info) in alias_path_data.items()
        }

        self.root_file_partition_iterator = root_file_partition_iterator
        self.scale = scale
        self.output_feature_class = output_feature_class
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

    def create_cartographic_partitions(self):
        """
        Creates cartographic partitions based on all available feature classes,
        including inputs and context features.
        """
        all_features = [details["path"] for alias, details in self.data.items()]

        arcpy.cartography.CreateCartographicPartitions(
            in_features=all_features,
            out_features=self.partition_feature,
            feature_count=self.feature_count,
            partition_method=self.partition_method,
        )
        print(f"Created partitions in {self.partition_feature}")

    def delete_feature_class(
        self,
        feature_class_path,
    ):
        """Deletes a feature class if it exists.

        Args:
            feature_class_path (str): The path to the feature class to be deleted.
        """
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)
            print(f"Deleted feature class: {feature_class_path}")

    def create_feature_class(
        self,
        out_path,
        out_name,
        template_feature,
    ):
        """Creates a new feature class from a template feature class.

        Args:
            out_path (str): The output path where the feature class will be created.
            out_name (str): The name of the new feature class.
            template_feature (str): The path to the template feature class.
        """
        full_out_path = os.path.join(
            out_path,
            out_name,
        )
        if arcpy.Exists(full_out_path):
            arcpy.management.Delete(full_out_path)
            print(f"Deleted existing feature class: {full_out_path}")

        arcpy.management.CreateFeatureclass(
            out_path=out_path,
            out_name=out_name,
            template=template_feature,
        )
        print(f"Created feature class: {full_out_path}")

    def delete_iteration_files(self, *file_paths):
        """Deletes multiple feature classes or files.

        Args:
            *file_paths: A variable number of file paths to delete.
        """
        for file_path in file_paths:
            try:
                if arcpy.Exists(file_path):
                    arcpy.Delete_management(file_path)
                    print(f"Deleted iteration file: {file_path}")

            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

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
        # Iterate only over 'input' type data in self.data
        for alias, details in self.data.items():
            if details["type"] == "input":
                input_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_input_copy"
                )
                arcpy.management.Copy(
                    in_data=details["path"],
                    out_data=input_data_copy,
                )
                print(f"Copied input data for: {alias}")

                self.data[alias]["path"] = input_data_copy

                partition_field = "partition_select"
                arcpy.AddField_management(
                    in_table=input_data_copy,
                    field_name=partition_field,
                    field_type="LONG",
                )
                print(f"Added field {partition_field}")

                # Add a unique ID field to the copied feature class, ensuring it's a new field
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

    def delete_existing_outputs(self):
        for alias, details in self.data.items():
            if details["type"] == "output":
                output_path = details["path"]
                self.delete_feature_class(output_path)
                print(f"Deleted existing feature class: {output_path}")

    def create_dummy_features(self, alias, details):
        dummy_feature_path = (
            f"{self.root_file_partition_iterator}_{alias}_dummy_{self.scale}"
        )
        self.create_feature_class(
            out_path=os.path.dirname(dummy_feature_path),
            out_name=os.path.basename(dummy_feature_path),
            template_feature=details["path"],
        )

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

    def process_input_features(self, alias, details, iteration_partition):
        """
        Process input features for a given partition.
        """
        input_features_partition_selection = (
            f"in_memory/{alias}_partition_base_select_{self.scale}"
        )
        self.iteration_file_paths.append(input_features_partition_selection)

        input_feature_count = custom_arcpy.select_location_and_make_feature_layer(
            input_layer=details["path"],
            overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
            select_features=iteration_partition,
            output_name=input_features_partition_selection,
        )
        return input_feature_count > 0

    def process_context_features(self, alias, details, iteration_partition):
        """
        Process context features for a given partition if input features are present.
        """
        context_selection_path = (
            f"{self.root_file_partition_iterator}_{alias}_context_iteration_selection"
        )
        self.iteration_file_paths.append(context_selection_path)

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=details["path"],
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

        self.partition_iteration(
            [self.file_mapping[alias]["current_output"] for alias in self.alias],
            self.partition_feature,
            max_object_id,
            self.root_file_partition_iterator,
            self.scale,
            "partition_select",
            "id_field",
            [self.final_append_features.get(alias) for alias in self.alias],
        )


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
        building_points: Building_N100.iteration__partition_iterator_final_output_points__n100.value,
        building_polygons: Building_N100.iteration__partition_iterator_final_output_polygons__n100.value,
    }

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator = PartitionIterator(
        alias_path_data=inputs,
        # alias_path_outputs=outputs,
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        scale=env_setup.global_config.scale_n100,
        output_feature_class=Building_N100.iteration__partition_iterator_final_output__n100.value,
        # Add other parameters like custom_functions if you have any
    )

    # Run the partition iterator
    partition_iterator.run()
