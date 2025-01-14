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


class WorkFileManager:
    general_files_directory_name = env_setup.global_config.general_files_name
    lyrx_directory_name = env_setup.global_config.lyrx_directory_name

    def __init__(
        self,
        unique_id: int,
        root_file: str = None,
        write_to_memory: bool = True,
        keep_files: bool = False,
    ):
        self.unique_id = unique_id
        self.root_file = root_file
        self.write_to_memory = write_to_memory
        self.keep_files = keep_files
        self.created_paths = []

        if not self.write_to_memory and not self.root_file:
            raise ValueError(
                "Need to specify root_file path to write to disk for work files."
            )

        if self.keep_files and not self.root_file:
            raise ValueError(
                "Need to specify root_file path and write to disk to keep work files."
            )

        self.file_location = "memory/" if self.write_to_memory else f"{self.root_file}_"

    def modify_path(self) -> str:
        """
        Modifies the given path by removing the unwanted portion up to the scale directory.

        Returns:
            str: The modified path.
        """
        # Define regex pattern to find the scale directory (ends with a digit followed by \\)
        match = re.search(r"\\\w+\d0\\", self.root_file)
        if not match:
            raise ValueError("Scale directory pattern not found in the path.")
        if self.write_to_memory:
            raise ValueError(
                "Other file types than gdb are not supported in memory mode."
            )

        # Extract the root up to the scale directory
        scale_path = self.root_file[: match.end()]

        return scale_path

    def _build_file_path(
        self,
        file_name: str,
        file_type: str = "gdb",
    ) -> str:
        """
        Constructs a file path based on the file name and type.
        """

        if file_type == "gdb":
            path = f"{self.file_location}{file_name}_{self.unique_id}"
        else:
            scale_path = self.modify_path()

            if file_type == "lyrx":
                path = rf"{scale_path}{self.lyrx_directory_name}\{file_name}_{self.unique_id}.lyrx"

            else:
                path = rf"{scale_path}{self.general_files_directory_name}\{file_name}_{self.unique_id}.{file_type}"

        self.created_paths.append(path)
        return path

    def setup_work_file_paths(
        self,
        instance,
        file_structure,
        keys_to_update=None,
        add_key=None,
        file_type="gdb",
    ):
        """
        Generates file paths for supported structures and sets them as attributes on the instance.
        """
        if isinstance(file_structure, str):
            return self._build_file_path(file_structure, file_type)

        if isinstance(file_structure, list):
            return [
                self.setup_work_file_paths(
                    instance, item, keys_to_update, add_key, file_type
                )
                for item in file_structure
            ]

        if isinstance(file_structure, dict):
            updated = {}
            for key, value in file_structure.items():
                if keys_to_update == "ALL" or (
                    keys_to_update and key in keys_to_update
                ):
                    updated[key] = self.setup_work_file_paths(
                        instance,
                        value,
                        keys_to_update,
                        add_key=None,
                        file_type=file_type,
                    )
                else:
                    updated[key] = value
            if add_key:
                updated[add_key] = self._build_file_path(
                    file_name=add_key, file_type=file_type
                )
            return updated

        raise TypeError(f"Unsupported file structure type: {type(file_structure)}")

    def delete_created_files(self, delete_targets=None, exceptions=None):
        """
        Deletes created file paths, optionally filtering by targets or exceptions.

        Parameters:
        - delete_targets: (Optional) List of paths to delete. Defaults to all created paths.
        - exceptions: (Optional) List of paths to exclude from deletion.
        """
        # Use all tracked paths if delete_targets is not provided
        targets = delete_targets or self.created_paths

        # Apply exceptions, if provided
        if exceptions:
            targets = [path for path in targets if path not in exceptions]

        for path in targets:
            self._delete_file(path)

    def print_created_files(self):
        print(f"Created files: {self.created_paths}")

    def cleanup_files(self, file_paths):
        """
        Deletes files. Can handle a list of file paths or a list of lists of file paths.
        """
        if isinstance(file_paths[0], list):
            for sublist in file_paths:
                for path in sublist:
                    self._delete_file(path)
        else:
            for path in file_paths:
                self._delete_file(path)

    @staticmethod
    def _delete_file(file_path: str):
        try:
            if arcpy.Exists(file_path):
                arcpy.management.Delete(file_path)
                print(f"Deleted: {file_path}")
            else:
                print(f"File did not exist: {file_path}")
        except arcpy.ExecuteError as e:
            print(f"Error deleting file {file_path}: {e}")

    @staticmethod
    def match_listed_dictionary(listed_dictionary, input_file_key, matching_file_key):
        for listed_dict, dictionary in enumerate(listed_dictionary):
            input_file = dictionary[input_file_key]
            matching_file = dictionary[matching_file_key]

            print(
                f"Matching logic:\nInput file: {input_file}\nOutput file: {matching_file}\n"
            )

    @staticmethod
    def apply_to_dicts(data_list, func, **key_map):
        """
        Applies a function to each dictionary in a list by matching specified keys.

        Args:
            data_list (list[dict]): The list of dictionaries to process.
            func (callable): The function to apply. The keys in `key_map` should match the function parameters.
            **key_map (str): Mapping of function parameter names to dictionary keys.

        Raises:
            KeyError: If a required key is missing from a dictionary.
        """
        if isinstance(data_list, list) and all(
            isinstance(item, dict) for item in data_list
        ):
            print(f"\n\ndata_list is a list: {data_list}\n\n")

        for dictionary in data_list:
            try:
                # Map function parameters to the corresponding dictionary values
                func(**{param: dictionary[key] for param, key in key_map.items()})
            except KeyError as e:
                raise KeyError(f"Missing key {e} in dictionary: {dictionary}")


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
            keep_files=True,
        )

        self.selection_files_list_of_dict = (
            self.work_file_manager.setup_work_file_paths(
                instance=self,
                file_structure=self.list_of_dicts_inputs,
                keys_to_update=["gdb"],
            )
        )

        self.output_files_files = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.structure_with_files,
            keys_to_update="output",
            file_type="txt",
        )
        print(f"output_files_files:\n{self.output_files_files}\n")

        self.output_files_files_2 = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.structure_with_files,
            add_key="output",
            file_type="txt",
        )
        print(f"output_files_files 2:\n{self.output_files_files_2}\n")

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
            keys_to_update=["gdb"],
        )
        dict_of_list_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self, file_structure=self.dict_of_list_inputs
            )
        )
        list_of_dicts_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self, file_structure=self.list_of_dicts_inputs
            )
        )
        dictionary_of_dictionaries_inputs_post_work_manger = (
            self.work_file_manager.setup_work_file_paths(
                instance=self, file_structure=self.dictionary_of_dictionaries_inputs
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
        print("\n")
        print(f"single key update test\n: {self.selection_files_list_of_dict}\n")

    @staticmethod
    def matching_logic(input_file, matching_file):
        print(f"Matching logic for {input_file} and {matching_file}")

    def selection_logic(self):
        for listed_dict, dictionary in enumerate(self.selection_files_list_of_dict):
            # Ensure the item is a dictionary
            if not isinstance(dictionary, dict):
                raise TypeError(
                    f"Expected a dictionary at index {dictionary}, got {type(listed_dict)}"
                )

            # Access the values
            input_file = dictionary["gdb"]
            matching_file = dictionary["lyrx"]
            print(f"Input file: {input_file}")
            print(f"Matching file: {matching_file}")
            self.matching_logic(input_file=input_file, matching_file=matching_file)
            print("\n")

    def some_logic(self):
        print("{}some logic func\n")

        def something_func(input_file, matching_file, output_file):
            print(
                f"Input file:{input_file}\nMatching file:{matching_file}\nOutput file: {output_file}\n"
            )

        WorkFileManager.apply_to_dicts(
            data_list=self.selection_files_list_of_dict,
            func=something_func,
            input_file="gdb",
            matching_file="lyrx",
            output_file="output",
        )

    def copy_files(self):
        def copy_func(input_file, output_file):
            arcpy.management.Copy(input_file, output_file)
            print(f"Copied {input_file} to {output_file}")

        WorkFileManager.apply_to_dicts(
            data_list=self.structure_with_files,
            func=copy_func,
            input_file="input",
            output_file="output",
        )

    def run(self):
        # self.print_inputs_pre_work_manger()
        # self.print_inputs_post_work_manger()
        # print("\n")
        # self.selection_logic()
        # print("testing workfile manger func\n")
        # WorkFileManager.match_listed_dictionary(
        #     listed_dictionary=self.selection_files_list_of_dict,
        #     input_file_key="gdb",
        #     matching_file_key="lyrx",
        # )
        # self.some_logic()
        # self.copy_files()
        print(f"{self.work_file_manager.print_created_files()}")


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
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___road_n100_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___matrikkel_input_data___n100_building.value,
            "output": "output",
        },
        {
            "input": Building_N100.data_selection___displacement_feature___n100_building.value,
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
    input_output_file_dict = {
        input_n100.BegrensningsKurve: Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        input_n100.ArealdekkeFlate: Building_N100.data_selection___land_cover_n100_input_data___n100_building.value,
        input_roads.road_output_1: Building_N100.data_selection___road_n100_input_data___n100_building.value,
        input_n100.JernbaneStasjon: Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
        input_n100.Bane: Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        input_n50.ArealdekkeFlate: Building_N100.data_selection___land_cover_n50_input_data___n100_building.value,
        input_n50.BygningsPunkt: Building_N100.data_selection___building_point_n50_input_data___n100_building.value,
        input_n50.Grunnriss: Building_N100.data_selection___building_polygon_n50_input_data___n100_building.value,
        input_n50.TuristHytte: Building_N100.data_selection___tourist_hut_n50_input_data___n100_building.value,
        input_other.matrikkel_bygningspunkt: Building_N100.data_selection___matrikkel_input_data___n100_building.value,
        config.displacement_feature: Building_N100.data_selection___displacement_feature___n100_building.value,
    }

    print_class = PrintClass(
        string_inputs=string_inputs,
        list_inputs=list_inputs,
        dict_inputs=dict_inputs,
        dict_of_list_inputs=dict_of_list_inputs,
        list_of_dicts_inputs=example_structure,
        dictionary_of_dictionaries_inputs=dictionary_of_dictionaries_inputs,
        structure_with_files=example_structure_3,
        root_file=Building_N100.point_resolve_building_conflicts___new_workfile_managger___n100_building.value,
    )
    print_class.run()
