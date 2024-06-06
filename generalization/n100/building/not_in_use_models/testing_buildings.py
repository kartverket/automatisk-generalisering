import arcpy


from typing import Union, List, Dict, Tuple
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from input_data import input_n100
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from custom_tools.general_tools.polygon_processor import PolygonProcessor


class DictionaryBuffer1:
    def __init__(self, input_dict: dict, output_dict: dict):
        self.input_dict = input_dict
        self.output_dict = output_dict

    def run(self):
        for key in self.input_dict:
            input_params = self.input_dict[key]
            output_path = self.output_dict.get(key)

            if not output_path:
                raise ValueError(f"Output path for {key} is missing.")

            input_path = input_params[0]
            buffer_distance_or_field = input_params[1]

            print(
                f"Executing PairwiseBuffer for {key} with input: {input_path}, output: {output_path}, distance: {buffer_distance_or_field}"
            )

            arcpy.analysis.PairwiseBuffer(
                in_features=input_path,
                out_feature_class=output_path,
                buffer_distance_or_field=f"{buffer_distance_or_field} Meters",
            )

            print(f"Buffering completed for {key}. Output saved to {output_path}.")


# Example usage
input_dict_1 = {
    "object_1": ["path/to/input1.shp", "100"],
    "object_2": ["path/to/input2.shp", "200"],
}

output_dict_1 = {
    "object_1": "path/to/output1.shp",
    "object_2": "path/to/output2.shp",
}


class DictionaryBuffer2:
    def __init__(self, input_dict: dict, output_dict: dict):
        self.input_dict = input_dict
        self.output_dict = output_dict

    @partition_io_decorator(
        input_param_names=["input_dict"],
        output_param_names=["output_dict"],
    )
    def run(self):
        for key in self.input_dict:
            input_params = self.input_dict[key]
            output_paths = self.output_dict.get(key)

            if not output_paths or len(output_paths) < 2:
                raise ValueError(f"Output paths for {key} are missing or incomplete.")

            input_path1 = input_params[0]
            input_path2 = input_params[1]
            buffer_distance = input_params[2]

            output_path1 = output_paths[0]
            output_path2 = output_paths[1]

            buffer_distance1 = f"{int(buffer_distance) * 2} Meters"  # Example logic for different distances
            buffer_distance2 = f"{int(buffer_distance) * 0.5} Meters"  # Example logic for different distances

            print(
                f"Executing PairwiseBuffer for {key} with input: {input_path1}, output: {output_path1}, distance: {buffer_distance1}"
            )

            arcpy.analysis.PairwiseBuffer(
                in_features=input_path1,
                out_feature_class=output_path1,
                buffer_distance_or_field=buffer_distance1,
            )

            print(
                f"Executing PairwiseBuffer for {key} with input: {input_path2}, output: {output_path2}, distance: {buffer_distance2}"
            )

            arcpy.analysis.PairwiseBuffer(
                in_features=input_path2,
                out_feature_class=output_path2,
                buffer_distance_or_field=buffer_distance2,
            )

            print(
                f"Buffering completed for {key}. Outputs saved to {output_path1} and {output_path2}."
            )


if __name__ == "__main__":
    environment_setup.main()

    input_dict = {
        "building_points": [
            Building_N100.building_point_buffer_displacement__buildings_study_area__n100.value,
            Building_N100.building_point_buffer_displacement__begrensningskurve_study_area__n100.value,
            "10",
        ],
        "train_stations": [input_n100.JernbaneStasjon, input_n100.Bane, "10"],
    }

    output_dict = {
        "building_points": [
            Building_N100.testing_building___building_point_1___n100_building.value,
            Building_N100.testing_building___building_point_2___n100_building.value,
        ],
        "train_stations": [
            Building_N100.testing_building___training_point_1___n100_building.value,
            Building_N100.testing_building___training_point_2___n100_building.value,
        ],
    }

    buffer_operation = DictionaryBuffer2(
        input_dict=input_dict,
        output_dict=output_dict,
    )
    buffer_operation.run()

    input_dict = {
        "building_points": [
            ("building_points", "input"),
            ("building_points", "context"),
            "10",
        ],
        "train_stations": [
            ("train_stations", "input"),
            ("train_stations", "context"),
            "10",
        ],
    }

    output_dict = {
        "building_points": [
            ("building_points", "buffer_1"),
            ("building_points", "buffer_2"),
        ],
        "train_stations": [
            ("train_stations", "buffer_1"),
            ("train_stations", "buffer_2"),
        ],
    }
