import arcpy
from enum import Enum


from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.file_utilities import (
    WorkFileManager,
    deleting_added_field_from_feature_to_x,
)
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.file_utilities import (
    deleting_added_field_from_feature_to_x,
)
from custom_tools.general_tools.graph import GISGraph
from env_setup import environment_setup
from constants.n100_constants import MediumAlias

from file_manager.n100.file_manager_roads import Road_N100


class RemoveRoadTriangles:
    def __init__(
        self,
        input_line_feature: str,
        minimum_length: int,
        root_file: str,
        output_processed_feature: str,
        write_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.input_line_feature = input_line_feature
        self.minimum_length = minimum_length
        self.root_file = root_file
        self.output_processed_feature = output_processed_feature

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=self.root_file,
            write_to_memory=write_to_memory,
            keep_files=keep_work_files,
        )

        self.dissolved_feature = "dissolved_feature"
        self.internal_root = "internal_root"
        self.line_nodes = "line_nodes"
        self.line_1_cycle = "line_1_cycle"
        self.short_roads = "short_roads"

        self.gdb_files_list = [
            self.dissolved_feature,
            self.internal_root,
            self.line_nodes,
            self.line_1_cycle,
            self.short_roads,
        ]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    def simplify_road_network(self):
        dissolve_obj = DissolveWithIntersections(
            input_line_feature=self.input_line_feature,
            root_file=self.internal_root,
            output_processed_feature=self.dissolved_feature,
            dissolve_field_list=["MEDIUM"],
            list_of_sql_expressions=[
                f" MEDIUM = '{MediumAlias.tunnel}'",
                f" MEDIUM = '{MediumAlias.bridge}'",
                f" MEDIUM = '{MediumAlias.on_surface}'",
            ],
        )
        dissolve_obj.run()

    def create_start_end_nodes(self):
        arcpy.management.FeatureVerticesToPoints(
            in_features=self.dissolved_feature,
            out_feature_class=self.line_nodes,
            point_location="BOTH_ENDS",
        )

    def remove_1_cycle_roads(self):
        detect_1_cycle_roads = GISGraph(
            input_path=self.line_nodes,
            object_id="OBJECTID",
            original_id="ORIG_FID",
            geometry_field="SHAPE",
        )
        road_1_cycle_sql = detect_1_cycle_roads.select_1_cycle()
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            expression=road_1_cycle_sql,
            output_name=self.line_1_cycle,
        )

    def filter_short_roads(self):
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            expression=f"Shape_Length <= {self.minimum_length}",
            output_name=self.short_roads,
        )

    def create_output(self):
        arcpy.management.CopyFeatures(
            in_features=self.line_nodes,
            out_feature_class=self.output_processed_feature,
        )

    def run(self):
        self.simplify_road_network()
        self.create_start_end_nodes()
        self.remove_1_cycle_roads()
        # self.create_output()
        # self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()

    remove_road_triangles = RemoveRoadTriangles(
        input_line_feature=Road_N100.data_preparation___resolve_road_conflicts___n100_road.value,
        minimum_length=500,
        root_file=Road_N100.testing_file___remove_triangles_root___n100_road.value,
        output_processed_feature=Road_N100.testing_file___removed_triangles___n100_road.value,
    )
    remove_road_triangles.run()
