import arcpy

import config
from custom_tools.general_tools import file_utilities
from custom_tools.general_tools import partition_iterator
from file_manager import WorkFileManager
from composition_configs import WorkFileConfig
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator

from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy

from constants.n100_constants import FieldNames, MediumAlias


class ThinRoadNetwork:
    def __init__(
        self,
        road_network_input: str,
        road_network_output: str,
        work_file_manager_config: WorkFileConfig,
        minimum_length: str,
        invisibility_field_name: str,
        hierarchy_field_name: str,
        special_selection_sql: str | None = None,
    ):
        self.road_network_input = road_network_input
        self.road_network_output = road_network_output
        self.minimum_length = minimum_length
        self.invisibility_field_name = invisibility_field_name
        self.hierarchy_field_name = hierarchy_field_name
        self.partition_field_name = PartitionIterator.PARTITION_FIELD
        self.special_selection_sql = special_selection_sql

        self.write_work_files_to_memory = work_file_manager_config.write_to_memory

        if self.write_work_files_to_memory:
            print("Writing to memory Currently not supported. Set to false")
            self.write_work_files_to_memory = False

        self.work_file_manager = WorkFileManager(config=work_file_manager_config)

        self.thin_road_network_output = "thin_road_network_output"
        self.gdb_files_list = [self.thin_road_network_output]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    def thin_road_network(self):
        arcpy.cartography.ThinRoadNetwork(
            in_features=self.road_network_input,
            minimum_length=self.minimum_length,
            invisibility_field=self.invisibility_field_name,
            hierarchy_field=self.hierarchy_field_name,
        )

    def thin_road_network_output_selection_old(self):
        if self.special_selection_sql:
            sql_expression = (
                f"{self.special_selection_sql} OR {self.invisibility_field_name} = 0"
            )
        else:
            sql_expression = f"{self.invisibility_field_name} = 0"

        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.road_network_input,
                expression=sql_expression,
                output_name=self.road_network_output,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.road_network_input,
                expression=sql_expression,
                output_name=self.road_network_output,
            )

    @staticmethod
    def count_objects_old(input_layer):
        count = int(arcpy.management.GetCount(input_layer).getOutput(0))
        return count

    def thin_road_network_output_selection(
        self,
        input,
        selection_output,
        root_file,
        dissolved_output,
    ):
        arcpy.cartography.ThinRoadNetwork(
            in_features=input,
            minimum_length=self.minimum_length,
            invisibility_field=self.invisibility_field_name,
            hierarchy_field=self.hierarchy_field_name,
        )

        if self.special_selection_sql:
            sql_expression = (
                f"{self.special_selection_sql} OR {self.invisibility_field_name} = 0"
            )
        else:
            sql_expression = f"{self.invisibility_field_name} = 0"

        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=input,
                expression=sql_expression,
                output_name=selection_output,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=input,
                expression=sql_expression,
                output_name=selection_output,
            )

        dissolve_obj = DissolveWithIntersections(
            input_line_feature=selection_output,
            root_file=root_file,
            output_processed_feature=dissolved_output,
            dissolve_field_list=FieldNames.road_all_fields()
            + [self.partition_field_name],
            list_of_sql_expressions=[
                f" MEDIUM = '{MediumAlias.tunnel}'",
                f" MEDIUM = '{MediumAlias.bridge}'",
                f" MEDIUM = '{MediumAlias.on_surface}'",
            ],
        )
        dissolve_obj.run()

    def thin_road_cycle(self):
        input_count = file_utilities.count_objects(input_layer=self.road_network_input)

        print(f"Starting thin roads cycle with: {input_count}")

        start_count = input_count
        end_count = 0
        iteration_number = 0

        current_input = self.road_network_input

        while start_count > end_count:
            iteration_number = iteration_number + 1
            print(f"Starting iteration: {iteration_number}")

            thin_selection = self.work_file_manager.generate_output(
                instance=self,
                name="thin_road_selection",
                iteration_index=iteration_number,
            )
            root = self.work_file_manager.generate_output(
                instance=self,
                name="dissolve_root",
                iteration_index=iteration_number,
            )
            current_output = self.work_file_manager.generate_output(
                instance=self,
                name="dissolved_roads",
                iteration_index=iteration_number,
            )

            self.thin_road_network_output_selection(
                input=current_input,
                selection_output=thin_selection,
                root_file=root,
                dissolved_output=current_output,
            )

            end_count = file_utilities.count_objects(input_layer=current_output)
            start_count = file_utilities.count_objects(input_layer=current_input)
            print(f"start count: {start_count}\nend count {end_count}\n")
            current_input = current_output

        print(f"Copying: {current_output}")
        arcpy.management.Copy(in_data=current_output, out_data=self.road_network_output)

    @partition_io_decorator(
        input_param_names=["road_network_input"],
        output_param_names=["road_network_output"],
    )
    def run(self):
        environment_setup.main()
        self.thin_road_network()
        self.thin_road_cycle()
        self.work_file_manager.delete_created_files()
