import arcpy
from typing import List, Dict

from custom_tools.general_tools.file_utilities import WorkFileManager
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n100.file_manager_buildings import Building_N100
import config
from input_data.input_symbology import SymbologyN100
from input_data import input_roads


class ResolveRoadConflicts:
    def __init__(
        self,
        input_list_of_dicts_data_structure: List[Dict[str, str]] = None,
        root_file: str = None,
        hierarchy_field: str = "hierarchy",
        map_scale: str = "100000",
        output_road_feature: str = None,
        output_displacement_feature: str = None,
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.input_line_dictionary = input_list_of_dicts_data_structure
        self.root_path = root_file

        self.map_scale = map_scale
        self.hierarchy_field = hierarchy_field
        self.displacement_feature = output_displacement_feature
        self.output_road_feature = output_road_feature

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=root_file,
            write_to_memory=write_work_files_to_memory,
            keep_files=keep_work_files,
        )

        self.line_copy = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.input_line_dictionary,
            add_key="line_copy",
        )

        self.output_lyrx_features = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.line_copy,
            add_key="lyrx_output",
            file_type="lyrx",
        )
        self.output_merge_feature = "merge_road_feature"

        self.gdb_files_list = [self.output_merge_feature]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    def copy_input_layers(self):
        def copy_input(
            input_line_feature: str = None,
            line_copy_feature: str = None,
        ):
            arcpy.management.CopyFeatures(
                in_features=input_line_feature,
                out_feature_class=line_copy_feature,
            )

        self.work_file_manager.apply_to_structure(
            data=self.output_lyrx_features,
            func=copy_input,
            input_line_feature="input_line_feature",
            line_copy_feature="line_copy",
        )

    def apply_symbology(self):
        def apply_symbology(
            input_line_feature: str = None,
            input_lyrx_feature: str = None,
            output_name: str = None,
            grouped_lyrx: bool = False,
            target_layer_name: str = None,
        ):
            if grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=input_line_feature,
                    in_symbology_layer=input_lyrx_feature,
                    output_name=output_name,
                    grouped_lyrx=grouped_lyrx,
                    target_layer_name=target_layer_name,
                )
            if not grouped_lyrx:
                custom_arcpy.apply_symbology(
                    input_layer=input_line_feature,
                    in_symbology_layer=input_lyrx_feature,
                    output_name=output_name,
                )

        self.work_file_manager.apply_to_structure(
            data=self.output_lyrx_features,
            func=apply_symbology,
            input_line_feature="line_copy",
            input_lyrx_feature="input_lyrx_feature",
            output_name="lyrx_output",
            grouped_lyrx="grouped_lyrx",
            target_layer_name="target_layer_name",
        )

    def resolve_road_conflicts(self):
        resolve_road_conflicts_inputs = self.work_file_manager.extract_key_all(
            data=self.output_lyrx_features, key="lyrx_output"
        )

        arcpy.cartography.ResolveRoadConflicts(
            in_layers=resolve_road_conflicts_inputs,
            hierarchy_field=self.hierarchy_field,
            out_displacement_features=self.displacement_feature,
        )

        resolve_road_conflicts_output = self.work_file_manager.extract_key_by_alias(
            data=self.output_lyrx_features,
            unique_alias="road",
            key="lyrx_output",
        )
        arcpy.management.CopyFeatures(
            in_features=resolve_road_conflicts_output,
            out_feature_class=self.output_road_feature,
        )

    def run(self):
        arcpy.env.referenceScale = self.map_scale
        environment_setup.main()
        self.copy_input_layers()
        self.apply_symbology()
        self.resolve_road_conflicts()

        self.work_file_manager.list_contents(
            data=self.output_lyrx_features, title="output_lyrx_features"
        )


if __name__ == "__main__":
    environment_setup.main()

    input_data_structure = [
        {
            "unique_alias": "road",
            "input_line_feature": input_roads.road_output_1,
            "input_lyrx_feature": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_bru_L2",
        },
        {
            "unique_alias": "railroad",
            "input_line_feature": Road_N100.data_selection___railroad___n100_road.value,
            "input_lyrx_feature": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        },
        {
            "unique_alias": "begrensningskurve",
            "input_line_feature": Road_N100.data_selection___begrensningskurve___n100_road.value,
            "input_lyrx_feature": SymbologyN100.begrensnings_kurve_line.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
    ]

    resolve_road_conflicts = ResolveRoadConflicts(
        input_list_of_dicts_data_structure=input_data_structure,
        root_file=Road_N100.test1___root_file___n100_road.value,
        output_road_feature=Road_N100.testing_file___roads_area_lyrx___n100_road.value,
        output_displacement_feature=Road_N100.testing_file___displacement_feature_after_resolve_road_conflict___n100_road.value,
        map_scale="100000",
    )
    resolve_road_conflicts.run()
