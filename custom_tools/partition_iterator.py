import arcpy
import os
import logging
import random

import env_setup.global_config
from env_setup import environment_setup
from custom_tools import custom_arcpy
from env_setup import setup_directory_structure
from file_manager.n100.file_manager_buildings import Building_N100

# THIS IS WORK IN PROGRESS NOT READY FOR USE


class PartitionIterator:
    """THIS IS WORK IN PROGRESS NOT READY FOR USE"""

    def __init__(
        self,
        inputs,
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
        self.final_append_feature = (
            f"{root_file_partition_iterator}_{self.alias}_final_append_feature_{scale}"
        )

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

            # Handle the error or raise it

            for alias, input_feature in zip(self.alias, self.original_input_path):
                if arcpy.Exists(self.final_append_feature):
                    arcpy.management.Delete(self.final_append_feature)
            return max_object_id, self.final_append_feature
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
            orig_id_field = "id_field"
            while orig_id_field in existing_field_names:
                orig_id_field = f"{orig_id_field}_{random.randint(0, 9)}"
            arcpy.AddField_management(
                in_table=input_data_copy, field_name=orig_id_field, field_type="LONG"
            )
            print(f"Added field {orig_id_field}")

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
        for object_id in range(1, max_object_id + 1):
            iteration_partition = f"{partition_feature}_{object_id}"

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=partition_feature,
                expression=f"OBJECTID = {object_id}",
                output_name=iteration_partition,
            )

            for alias, input_feature in zip(self.alias, self.original_input_path):
                iteration_append_feature = f"{self.root_file_partition_iterator}_{self.alias}_iteration_append_feature_{self.scale}"
                if arcpy.Exists(iteration_append_feature):
                    arcpy.management.Delete(iteration_append_feature)

                arcpy.management.CreateFeatureclass(
                    out_path=os.path.dirname(iteration_append_feature),
                    out_name=os.path.basename(iteration_append_feature),
                    template=self.input_data_copy,
                )
                print(f"Created {iteration_append_feature}")

                feature_present_in_partition = False

                base_partition_selection = f"{self.root_file_partition_iterator}_{self.alias}_partition_base_select_{self.scale}"

                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=self.input_data_copy,
                    overlap_type=custom_arcpy.OverlapType.HAVE_THEIR_CENTER_IN.value,
                    select_features=iteration_partition,
                    output_name=self.base_partition_selection,
                )

                count_points = int(
                    arcpy.management.GetCount(self.base_partition_selection).getOutput(
                        0
                    )
                )
                if feature_present_in_partition > 0:
                    points_exist = True
                    print(
                        f"iteration partition {object_id} has {feature_present_in_partition} building points"
                    )

                    arcpy.CalculateField_management(
                        in_table=self.base_partition_selection,
                        field=partition_field,
                        expression="1",
                    )

                    arcpy.management.Append(
                        inputs=self.base_partition_selection,
                        target=self.iteration_append_feature,
                        schema_type="NO_TEST",
                    )

                    base_partition_selection_2 = f"{self.root_file_partition_iterator}_{self.alias}_partition_base_select_2_{self.scale}"

                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=self.input_data_copy,
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
                        inputs=self.base_partition_selection_2,
                        target=self.iteration_append_feature,
                        schema_type="NO_TEST",
                    )

                    for func in self.custom_functions:
                        # Determine inputs for the current function
                        inputs = [
                            self.file_mapping[fc]["current_output"] or fc
                            for fc in self.input_feature_classes
                        ]

                        # Call the function and get outputs
                        outputs = func(inputs)

                        # Update file mapping with the outputs
                        for fc, output in zip(self.input_feature_classes, outputs):
                            self.file_mapping[fc]["current_output"] = output

                    if not arcpy.Exists(self.final_append_feature):
                        # Create the final output feature class using the schema of the first erased feature
                        arcpy.management.CreateFeatureclass(
                            out_path=os.path.dirname(self.final_append_feature),
                            out_name=os.path.basename(self.final_append_feature),
                            template=self.iteration_append_feature,
                        )
                        print(f"Created {self.final_append_feature}")
                    selected_features_from_partition = f"{self.root_file_partition_iterator}_{self.alias}_iteration_select_feature_from_partition_{self.scale}"
                    custom_arcpy.select_attribute_and_make_feature_layer(
                        input_layer=self.iteration_append_featur,
                        expression=f"{partition_field} = 1",
                        output_name=self.selected_features_from_partition,
                    )

                    arcpy.management.Append(
                        inputs=self.selected_features_from_partition,
                        target=self.final_append_feature,
                        schema_type="NO_TEST",
                    )

    def run(self):
        self.setup_arcpy_environment()
        self.create_cartographic_partitions()

        max_object_id = self.pre_iteration()

        # Initialize the file mapping for each alias
        self.file_mapping = {alias: {"current_output": None} for alias in self.alias}

        self.prepare_input_data()

        # Partition iteration for each object ID
        for alias in self.alias:
            current_output = self.file_mapping[alias]["current_output"]
            self.partition_iteration(
                current_output,
                self.partition_feature,
                max_object_id,
                self.root_file_partition_iterator,
                self.scale,
                "partition_select",  # Assuming this is the partition field
                "id_field",  # Assuming this is the original ID field
                self.final_append_feature,
            )


if __name__ == "__main__":
    # Define your input feature classes and their aliases
    inputs = {
        "building_points": f"{Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value}",
        "building_polygons": f"{Building_N100.simplify_building_polygons__simplified_grunnriss__n100.value}",
    }

    # Instantiate PartitionIterator with necessary parameters
    partition_iterator = PartitionIterator(
        inputs=inputs,
        root_file_partition_iterator=Building_N100.iteration__partition_iterator__n100.value,
        scale=env_setup.global_config.scale_n100,
        output_feature_class=Building_N100.iteration__partition_iterator_final_output__n100.value,
        # Add other parameters like custom_functions if you have any
    )

    # Run the partition iterator
    partition_iterator.run()