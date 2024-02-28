import arcpy
import os
import logging
import random

import env_setup.global_config
from env_setup import environment_setup
from custom_tools import custom_arcpy
from input_data import input_n50
from env_setup import setup_directory_structure
from file_manager.n100.file_manager_buildings import Building_N100

# THIS IS WORK IN PROGRESS NOT READY FOR USE


class PartitionIterator:
    """THIS IS WORK IN PROGRESS NOT READY FOR USE"""

    def __init__(
        self,
        inputs,
        outputs,
        root_file_partition_iterator,
        scale,
        output_feature_class,
        custom_functions=None,
        feature_count="15000",
        partition_method="FEATURES",
    ):
        """
        Initialize the PartitionIterator with input datasets for partitioning and processing.

        :param inputs: A dictionary of input feature class paths with their aliases.
        :param root_file_partition_iterator: Base path for in progress outputs.
        :param scale: Scale for the partitions.
        :param output_feature_class: The output feature class for final results.
        :param feature_count: Feature count for cartographic partitioning.
        :param partition_method: Method used for creating cartographic partitions.
        """
        self.inputs = inputs
        self.outputs = outputs
        self.root_file_partition_iterator = root_file_partition_iterator
        self.scale = scale
        self.output_feature_class = output_feature_class
        self.feature_count = feature_count
        self.partition_method = partition_method
        self.partition_feature = (
            f"{root_file_partition_iterator}_partition_feature_{scale}"
        )
        self.custom_functions = custom_functions or []
        self.file_mapping = None
        self.alias = list(self.inputs.keys())
        self.original_input_path = list(self.inputs.values())
        self.final_append_features = {}

    def setup_arcpy_environment(self):
        # Set up the ArcPy environment
        environment_setup.general_setup()

    def create_cartographic_partitions(self):
        """
        Creates cartographic partitions based on the input feature classes.
        """
        arcpy.cartography.CreateCartographicPartitions(
            in_features=self.original_input_path,
            out_features=self.partition_feature,
            feature_count=self.feature_count,
            partition_method=self.partition_method,
        )
        print(f"Created partitions in {self.partition_feature}")

    def pre_iteration(self):
        """
        Determine the maximum OBJECTID for partitioning.
        """
        try:
            # Use a search cursor to find the maximum OBJECTID
            with arcpy.da.SearchCursor(
                self.partition_feature,
                ["OBJECTID"],
                sql_clause=(None, "ORDER BY OBJECTID DESC"),
            ) as cursor:
                max_object_id = next(cursor)[0]

            print(f"Maximum OBJECTID found: {max_object_id}")

            for alias in self.alias:
                # Dynamically generate the path for each alias
                final_append_feature_path = f"{self.root_file_partition_iterator}_{alias}_final_append_feature_{self.scale}"
                # Store or use this path as needed, for example:
                self.final_append_features[alias] = final_append_feature_path

            for alias, path in self.final_append_features.items():
                if arcpy.Exists(path):
                    arcpy.management.Delete(path)

            return max_object_id
        except Exception as e:
            print(f"Error in finding max OBJECTID: {e}")

    def prepare_input_data(self):
        for alias, input_feature in zip(self.alias, self.original_input_path):
            # Copy the input feature class to a new location
            input_data_copy = f"{self.root_file_partition_iterator}_{alias}_input_copy"
            arcpy.management.Copy(in_data=input_feature, out_data=input_data_copy)
            print(f"Copied {input_data_copy}")

            # Add a partition selection field to the copied feature class
            partition_field = "partition_select"
            arcpy.AddField_management(
                in_table=input_data_copy, field_name=partition_field, field_type="LONG"
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
                expression="!OBJECTID!",
            )
            print(f"Calculated field {orig_id_field}")

            # Update file mapping for the input feature class
            self.file_mapping[alias] = {"current_output": input_data_copy}

    def custom_function(inputs):
        outputs = []
        return outputs

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
        for alias, input_feature in zip(self.alias, self.original_input_path):
            dummy_iteration_feature = f"{root_file_partition_iterator}_{alias}_dummy_iteration_feature_{scale}"
            if arcpy.Exists(dummy_iteration_feature):
                arcpy.management.Delete(dummy_iteration_feature)

            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(dummy_iteration_feature),
                out_name=os.path.basename(dummy_iteration_feature),
                template=input_data_copy,
            )
            print(f"Created {dummy_iteration_feature}")

        aliases_feature_counts = {alias: 0 for alias in self.alias}

        for object_id in range(1, max_object_id + 1):
            for alias in self.alias:
                # Retrieve the output path for the current alias
                output_path = self.outputs.get(alias)

                if object_id == 1:
                    # Check if the output path exists and delete if it does but only first iteration
                    if arcpy.Exists(output_path):
                        arcpy.Delete_management(output_path)
                        print(f"Deleted existing output: {output_path}")

            print(f"\nProcessing OBJECTID {object_id}")
            iteration_partition = f"{partition_feature}_{object_id}"

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=partition_feature,
                expression=f"OBJECTID = {object_id}",
                output_name=iteration_partition,
            )

            # Check for features for each alias and set features_present accordingly
            for alias in self.alias:
                input_data_copy = self.file_mapping[alias]["current_output"]
                base_partition_selection = (
                    f"in_memory/{alias}_partition_base_select_{scale}"
                )
                # base_partition_selection = f"{root_file_partition_iterator}_{alias}_partition_base_select_1_{scale}_{object_id}"

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
                    if arcpy.Exists(iteration_append_feature):
                        arcpy.management.Delete(iteration_append_feature)

                    arcpy.management.CreateFeatureclass(
                        out_path=os.path.dirname(iteration_append_feature),
                        out_name=os.path.basename(iteration_append_feature),
                        template=input_data_copy,
                    )
                    print(f"Created {iteration_append_feature}")

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
                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=input_data_copy,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE,
                        select_features=iteration_partition,
                        output_name=base_partition_selection_2,
                        selection_type=custom_arcpy.SelectionType.NEW_SELECTION.value,
                        search_distance="500 Meters",
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

                    # self.file_mapping[alias] = {
                    #     "iteration_selection_output": iteration_append_feature
                    # }
                    print(
                        f"iteration partition {base_partition_selection_2} appended to {iteration_append_feature}"
                    )
                else:
                    # print(f"attempting to map {alias} to {dummy_iteration_feature}")
                    # self.file_mapping[alias] = {
                    #     "iteration_selection_output": dummy_iteration_feature
                    # }
                    print(
                        f"iteration partition {object_id} has no features for {alias} in the partition feature"
                    )

                # If no aliases had features, skip the rest of the processing for this object_id
            if aliases_with_features == 0:
                for alias in self.alias:
                    # base_partition_selection = f"{root_file_partition_iterator}_{alias}_partition_base_select_1_{scale}_{object_id}"
                    partition_target_selection = f"{root_file_partition_iterator}_{alias}_partition_target_selection_{scale}"

                    base_partition_selection = (
                        f"in_memory/{alias}_partition_base_select_{scale}"
                    )
                    base_partition_selection_2 = (
                        f"in_memory/{alias}_partition_base_select_2_{scale}"
                    )
                    # partition_target_selection = (
                    #     f"in_memory/{alias}_partition_target_selection_{scale}"
                    # )
                    # iteration_partition = f"{partition_feature}_{object_id}"
                    try:
                        arcpy.Delete_management(base_partition_selection)
                        arcpy.Delete_management(base_partition_selection_2)
                        arcpy.Delete_management(partition_target_selection)
                        # arcpy.Delete_management(iteration_partition)
                    except:
                        pass
                try:
                    iteration_partition = f"{partition_feature}_{object_id}"
                    arcpy.Delete_management(iteration_partition)
                except:
                    pass
                print(f"Finished iteration {object_id}")
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
                    # iteration_append_feature = self.file_mapping[alias][
                    #     "iteration_selection_output"
                    # ]
                    # iteration_append_feature = f"{root_file_partition_iterator}_{alias}_iteration_append_feature_{scale}"

                    if not arcpy.Exists(output_path):
                        print(f"template feature: \n{iteration_append_feature}")
                        # Create a new feature class at the output path
                        arcpy.CreateFeatureclass_management(
                            out_path=os.path.dirname(output_path),
                            out_name=os.path.basename(output_path),
                            template=iteration_append_feature,
                        )
                        print(f"Created new feature class: {output_path}")

                    partition_target_selection = f"{root_file_partition_iterator}_{alias}_partition_target_selection_{scale}"

                    # partition_target_selection = (
                    #     f"in_memory/{alias}_partition_target_selection_{scale}"
                    # )
                    custom_arcpy.select_attribute_and_make_permanent_feature(
                        input_layer=iteration_append_feature,
                        expression=f"{partition_field} = 1",
                        output_name=partition_target_selection,
                    )

                    # if arcpy.Exists(partition_target_selection):
                    #     desc = arcpy.Describe(partition_target_selection)
                    #     print(
                    #         f"Exists: {partition_target_selection}, Type: {desc.datasetType}"
                    #     )
                    # else:
                    #     print(f"Does not exist: {partition_target_selection}")
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
                        f"No features found in {alias} for OBJECTID {object_id} to append to {output_path}"
                    )

            for alias in self.alias:
                # base_partition_selection = f"{root_file_partition_iterator}_{alias}_partition_base_select_1_{scale}_{object_id}"
                partition_target_selection = f"{root_file_partition_iterator}_{alias}_partition_target_selection_{scale}"

                base_partition_selection = (
                    f"in_memory/{alias}_partition_base_select_{scale}"
                )
                base_partition_selection_2 = (
                    f"in_memory/{alias}_partition_base_select_2_{scale}"
                )
                # partition_target_selection = (
                #     f"in_memory/{alias}_partition_target_selection_{scale}"
                # )
                # iteration_partition = f"{partition_feature}_{object_id}"
                try:
                    arcpy.Delete_management(base_partition_selection)
                    arcpy.Delete_management(base_partition_selection_2)
                    arcpy.Delete_management(partition_target_selection)
                    # arcpy.Delete_management(iteration_partition)
                except:
                    pass
            try:
                iteration_partition = f"{partition_feature}_{object_id}"
                arcpy.Delete_management(iteration_partition)
            except:
                pass
            print(f"Finished iteration {object_id}")

    def run(self):
        self.setup_arcpy_environment()
        self.create_cartographic_partitions()

        max_object_id = self.pre_iteration()

        # Initialize the file mapping for each alias
        self.file_mapping = {
            alias: {
                "current_output": None,
                "func_output": None,
                "iteration_selection_output": None,
            }
            for alias in self.alias
        }

        self.prepare_input_data()

        # Call partition_iteration without looping over each alias here.
        # Ensure partition_iteration is designed to handle all aliases internally.
        self.partition_iteration(
            # Assuming partition_iteration is adjusted to accept a list of current_outputs and final_append_feature_paths
            # You may need to adjust how you pass parameters based on the actual requirements of partition_iteration.
            [
                self.file_mapping[alias]["current_output"] for alias in self.alias
            ],  # List of current outputs for all aliases
            self.partition_feature,
            max_object_id,
            self.root_file_partition_iterator,
            self.scale,
            "partition_select",
            "id_field",
            [
                self.final_append_features.get(alias) for alias in self.alias
            ],  # List of final append feature paths for all aliases
        )


if __name__ == "__main__":
    # Define your input feature classes and their aliases
    building_points = "building_points"
    building_polygons = "building_polygons"

    inputs = {
        building_points: Building_N100.adding_matrikkel_as_points__matrikkel_bygningspunkt__n100.value,
        building_polygons: input_n50.Grunnriss,
    }

    outputs = {
        building_points: Building_N100.iteration__partition_iterator_final_output_points__n100.value,
        building_polygons: Building_N100.iteration__partition_iterator_final_output_polygons__n100.value,
    }

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator = PartitionIterator(
        inputs=inputs,
        outputs=outputs,
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        scale=env_setup.global_config.scale_n100,
        output_feature_class=Building_N100.iteration__partition_iterator_final_output__n100.value,
        # Add other parameters like custom_functions if you have any
    )

    # Run the partition iterator
    partition_iterator.run()


"""
Needs to look closer at defining varaibles inside local loops
Need to look closer at unpacking self in variables and potentially loops:


            for alias, input_feature in zip(self.alias, self.original_input_path):
                input_data_copy = (
                    f"{self.root_file_partition_iterator}_{alias}_input_copy"
                )
"""
