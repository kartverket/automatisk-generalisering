import arcpy

from custom_tools.general_tools.file_utilities import WorkFileManager
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy


class ThinRoadNetwork:
    def __init__(
        self,
        road_network_input: str,
        root_file: str,
        road_network_output: str,
        minimum_length: str,
        invisibility_field_name: str,
        hierarchy_field_name: str,
        special_selection_sql: str | None = None,
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.road_network_input = road_network_input
        self.road_network_output = road_network_output
        self.minimum_length = minimum_length
        self.invisibility_field_name = invisibility_field_name
        self.hierarchy_field_name = hierarchy_field_name
        if write_work_files_to_memory:
            print("Writing to memory Currently not supported.")
        self.write_work_files_to_memory = False  # Currently not supporting memory
        self.special_selection_sql = special_selection_sql

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=self.write_work_files_to_memory,
            keep_files=keep_work_files,
        )

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
    def count_objects(input_layer):
        count = int(arcpy.management.GetCount(input_layer).getOutput(0))
        return count

    def generate_output(self, iteration_index):
        road_output = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure="thin_roads_output",
            index=iteration_index,
        )
        return road_output

    def thin_road_network_output_selection(self, input, selection_output):
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

    def thin_road_cycle(self):
        input_count = self.count_objects(input_layer=self.road_network_input)

        print(f"Starting thin roads cycle with: {input_count}")

        start_count = input_count
        end_count = 0
        iteration_number = 0

        current_input = self.road_network_input

        while start_count > end_count:
            iteration_number = iteration_number + 1
            print(f"Starting iteration: {iteration_number}")

            current_output = self.generate_output(iteration_index=iteration_number)

            self.thin_road_network_output_selection(
                input=current_input,
                selection_output=current_output,
            )

            end_count = self.count_objects(input_layer=current_output)
            start_count = self.count_objects(input_layer=current_input)
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
