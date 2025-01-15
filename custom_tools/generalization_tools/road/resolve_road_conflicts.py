import arcpy
from typing import Union, List, Dict, Tuple

from custom_tools.general_tools.file_utilities import WorkFileManager2
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100


class ResolveRoadConflicts:
    def __init__(
        self,
        input_feature_file_lyrx_dict: Dict[str, List[str]],
        output_road_feature: str,
        output_displacement_feature: str,
        root_file: str = None,
        hierarchy_field: str = "hierarchy",
        map_scale: str = "100000",
        write_work_files_to_memory: bool = True,
        keep_work_files: bool = False,
    ):
        self.input_line_dictionary = input_feature_file_lyrx_dict
        self.root_path = root_file

        self.map_scale = map_scale
        self.hierarchy_field = hierarchy_field

        self.selection_copy = None
        for feature, input_layer in self.input_line_dictionary.items():
            line_feature, _ = input_layer
            self.selection_copy = ""

        self.work_file_manager = WorkFileManager2(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

    def copy_input_layers(self):
        for feature, input_layer in self.input_line_dictionary.items():
            line_feature, _ = input_layer
            _, lyrx_feature = input_layer

            feature_name = f"{self.root_path}_{feature}"
            lyrx_name = f"{self.root_path}_{lyrx_feature}"
            print(f"Feature feature is:\n{line_feature}")

            print(f"Lyrx feature is:\n{lyrx_feature}")

    def resolve_road_conflicts(self):
        arcpy.cartography.ResolveRoadConflicts(
            in_layers=[
                Road_N100.testing_file___roads_area_lyrx___n100_road.value,
                Road_N100.testing_file___railway_area_lyrx___n100_road.value,
                Road_N100.testing_file___begrensningskurve_water_area_lyrx___n100_road.value,
            ],
            hierarchy_field=self.hierarchy_field,
            out_displacement_features=Road_N100.testing_file___displacement_feature_after_resolve_road_conflict___n100_road.value,
        )

    def run(self):
        arcpy.env.referenceScale = self.map_scale
        environment_setup.main()
        self.resolve_road_conflicts()


if __name__ == "__main__":
    # environment_setup.main()
    resolve_road_conflicts = ResolveRoadConflicts(
        input_feature_file_lyrx_dict={
            "feature_name": [
                Road_N100.testing_file___roads_area___n100_road.value,
                Road_N100.testing_file___roads_area_lyrx___n100_road.value,
            ],
            "feature_name_2": [
                Road_N100.testing_file___roads_area___n100_road.value,
                Road_N100.testing_file___roads_area_lyrx___n100_road.value,
            ],
        },
        root_file=Building_N100.data_preparation___root_file_line_symbology___n100_building.value,
        output_road_feature=Road_N100.testing_file___roads_area_lyrx___n100_road.value,
        output_displacement_feature=Road_N100.testing_file___displacement_feature_after_resolve_road_conflict___n100_road.value,
    )
    resolve_road_conflicts.copy_input_layers()
