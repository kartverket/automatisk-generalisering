import arcpy
from typing import List, Dict

from custom_tools.general_tools.file_utilities import WorkFileManager
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100
import config
from input_data.input_symbology import SymbologyN100
from input_data import input_roads


class ThinRoadNetwork:
    def __init__(
        self,
        road_network_input: str,
        root_file: str,
        road_network_output: str,
        minimum_length: str,
        invisibility_field_name: str,
        hierarchy_field_name: str,
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.road_network_input = road_network_input
        self.road_network_output = road_network_output
        self.minimum_length = minimum_length
        self.invisibility_field_name = invisibility_field_name
        self.hierarchy_field_name = hierarchy_field_name
        self.write_work_files_to_memory = write_work_files_to_memory

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=write_work_files_to_memory,
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

    def thin_road_network_output_selection(self):
        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.road_network_input,
                expression=f"{self.invisibility_field_name} = 0",
                output_name=self.thin_road_network_output,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.road_network_input,
                expression=f"{self.invisibility_field_name} = 0",
                output_name=self.thin_road_network_output,
            )

    @partition_io_decorator(
        input_param_names=["road_network_input"],
        output_param_names=["road_network_output"],
    )
    def run(self):
        environment_setup.main()
        self.thin_road_network()
        self.thin_road_network_output_selection()
        self.work_file_manager.delete_created_files()
