import re
import arcpy

import env_setup.global_config
from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from file_manager.n100.file_manager_roads import Road_N100
from input_data import input_roads
from input_data import input_n50
from input_data import input_other
import config
from env_setup import environment_setup
from custom_tools.general_tools.file_utilities import WorkFileManager


class PrintClass:
    def __init__(
        self,
        string_inputs,
        list_inputs,
        dict_inputs,
        dict_of_list_inputs,
        list_of_dicts_inputs,
        dictionary_of_dictionaries_inputs,
        root_file=None,
        structure_with_files=None,
    ):
        self.string_inputs = string_inputs
        self.list_inputs = list_inputs
        self.dict_inputs = dict_inputs
        self.dict_of_list_inputs = dict_of_list_inputs
        self.list_of_dicts_inputs = list_of_dicts_inputs
        self.dictionary_of_dictionaries_inputs = dictionary_of_dictionaries_inputs
        self.root_file = root_file
        self.structure_with_files = structure_with_files

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=False,
            keep_files=False,
        )

        self.output_files_files = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.structure_with_files,
            keys_to_update="output",
        )
        # print(f"output_files_files:\n{self.output_files_files}\n")
        self.work_file_manager.list_contents(
            data=self.output_files_files, title="Output files"
        )

        self.output_files_files_2 = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.output_files_files,
            add_key="new_output",
        )
        self.work_file_manager.list_contents(
            data=self.output_files_files_2, title="New output files"
        )

        self.output_files_files_3 = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.output_files_files,
            add_key="new_type",
            file_type="lyrx",
        )
        self.work_file_manager.list_contents(
            data=self.output_files_files_3, title="New output lyrx files"
        )

        self.road_lyrx = "road_lyrx"
        self.building_lyrx = "building_lyrx"
        self.water_lyrx = "water_lyrx"
        self.railroad_tracks_lyrx = "railroad_tracks_lyrx"
        self.railroad_stations_lyrx = "railroad_stations_lyrx"
        self.river_lyrx = "river_lyrx"
        self.list_of_lyrx_files = [
            self.road_lyrx,
            self.building_lyrx,
            self.water_lyrx,
            self.railroad_tracks_lyrx,
            self.railroad_stations_lyrx,
            self.river_lyrx,
        ]
        self.list_of_lyrx_files = self.work_file_manager.setup_work_file_paths(
            instance=self, file_structure=self.list_of_lyrx_files, file_type="lyrx"
        )
        self.work_file_manager.list_contents(
            data=self.list_of_lyrx_files, title="List of Lyrx files"
        )

    def print_inputs_pre_work_manger(self):
        print("Printing inputs pre-work manager:\n")
        print(f"String input: {self.string_inputs}")
        print(f"List input: {self.list_inputs}")
        print(f"Dict input: {self.dict_inputs}")
        print(f"Dict of list input: {self.dict_of_list_inputs}")
        print(f"List of dicts input: {self.list_of_dicts_inputs}")
        print(f"Dict of dicts input: {self.dictionary_of_dictionaries_inputs}")
        print("\n")

    def print_inputs_post_work_manger(self):
        string_inputs_post_work_manger = self.work_file_manager.setup_work_file_paths(
            instance=self, file_structure=self.string_inputs
        )
        list_inputs_post_work_manger = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.list_inputs,
        )
        dict_inputs_post_work_manger = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.dict_inputs,
        )
        dict_of_list_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self,
                file_structure=self.dict_of_list_inputs,
            )
        )
        list_of_dicts_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self, file_structure=self.list_of_dicts_inputs
            )
        )
        dictionary_of_dictionaries_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self,
                file_structure=self.dictionary_of_dictionaries_inputs,
            )
        )

        print("Printing inputs post-work manager:\n")
        print(f"String input: {string_inputs_post_work_manger}")
        print(f"List input: {list_inputs_post_work_manger}")
        print(f"Dict input: {dict_inputs_post_work_manger}")
        print(f"Dict of list input: {dict_of_list_inputs_post_work_manger}")
        print(f"List of dicts input: {list_of_dicts_inputs_post_work_manger}")
        print(
            f"Dict of dicts input: {dictionary_of_dictionaries_inputs_post_work_manger}"
        )

    def copy_files(self):
        def copy_func(input_file, lyrx_file, output_file):
            arcpy.management.Copy(input_file, output_file)
            print(
                f"\n\nCopied:\n{input_file}\nOutput:\n{output_file}\nLyrx file:\n{lyrx_file}"
            )

        self.work_file_manager.apply_to_structure(
            data=self.output_files_files,
            func=copy_func,
            input_file="input",
            lyrx_file="lyrx",
            output_file="output",
        )

    def run(self):
        # self.print_inputs_pre_work_manger()
        # self.print_inputs_post_work_manger()
        # print(f"Structure:\n{self.output_files_files}\n\n")
        # print(f"Structure:\n{self.output_files_files_2}\n\n")
        # print(f"Created files:\n{self.work_file_manager.created_paths}\n")
        # self.copy_files()
        self.work_file_manager.list_contents(
            data=self.work_file_manager.created_paths, title="Created files"
        )
        # self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
    string_inputs = "value1"

    list_inputs = ["value1", "value2", "value3"]

    dict_inputs = {
        "key": "value",
        "key2": "value2",
        "key3": "value3",
    }

    dict_of_list_inputs = {
        "key": ["value1", "value2", "value3"],
        "key2": ["value4", "value5", "value6"],
        "key3": ["value7", "value8", "value9"],
    }

    list_of_dicts_inputs = [
        {"key": "value1", "key2": "value2", "key3": "value3"},
        {"key": "value4", "key2": "value5", "key3": "value6"},
        {"key": "value7", "key2": "value8", "key3": "value9"},
    ]

    dictionary_of_dictionaries_inputs = {
        "key1": {
            "key11": "value11",
            "key12": "value12",
        },
        "key2": {
            "key21": "value21",
            "key22": "value22",
        },
        "key3": {
            "key31": "value31",
            "key32": "value32",
        },
    }

    example_structure = [
        {
            "lyrx": "road.lyrx",
            "gdb": "road.gdb",
            "output": "output.gdb",
        },
        {
            "lyrx": "building.lyrx",
            "gdb": "building.gdb",
            "output": "output.gdb",
        },
        {
            "lyrx": "water.lyrx",
            "gdb": "water.gdb",
            "output": "output.gdb",
        },
        {
            "lyrx": "railroad_tracks.lyrx",
            "gdb": "railroad_tracks.gdb",
            "output": "output.gdb",
        },
        {
            "lyrx": "railroad_stations.lyrx",
            "gdb": "railroad_stations.gdb",
            "output": "output.gdb",
        },
        {
            "lyrx": "river.lyrx",
            "gdb": "river.gdb",
            "output": "output.gdb",
        },
    ]
    example_structure_2 = [
        {
            "input": Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
            "lyrx": "road_1.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
            "lyrx": "road_2.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___road_n100_input_data___n100_building.value,
            "lyrx": "road_3.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
            "lyrx": "road_4.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            "lyrx": "road_5.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
            "lyrx": "road_6.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
            "lyrx": "road_7.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
            "lyrx": "road_8.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
            "lyrx": "road_9.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___matrikkel_input_data___n100_building.value,
            "lyrx": "road_10.lyrx",
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___displacement_feature___n100_building.value,
            "lyrx": "road_11.lyrx",
            "output": "output",
        },
    ]

    example_structure_3 = [
        {
            "input": Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___road_n100_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        },
        {
            "input": Building_N100.data_selection___displacement_feature___n100_building.value,
        },
    ]

    print_class = PrintClass(
        string_inputs=string_inputs,
        list_inputs=list_inputs,
        dict_inputs=dict_inputs,
        dict_of_list_inputs=dict_of_list_inputs,
        list_of_dicts_inputs=example_structure,
        dictionary_of_dictionaries_inputs=dictionary_of_dictionaries_inputs,
        structure_with_files=example_structure_2,
        root_file=Building_N100.point_resolve_building_conflicts___new_workfile_managger___n100_building.value,
    )
    print_class.run()
