import arcpy
from enum import Enum


from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.file_utilities import (
    WorkFileManager,
    deleting_added_field_from_feature_to_x,
)
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.file_utilities import (
    deleting_added_field_from_feature_to_x,
)
from env_setup import environment_setup
from constants.n100_constants import (
    N100_Symbology,
    N100_SQLResources,
    N100_Values,
    NvdbAlias,
    MediumAlias,
)
from file_manager.n100.file_manager_roads import Road_N100


class CreateIntersections:
    def __init__(
        self,
        input_line_feature: str,
        root_file: str,
        output_processed_feature: str,
        list_of_sql_expressions: list = None,
        write_work_files_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        self.input_line_feature = input_line_feature
        self.root_file = root_file
        self.output_processed_feature = output_processed_feature
        self.list_of_sql_expressions = list_of_sql_expressions
        self.write_work_files_to_memory = write_work_files_to_memory
        self.keep_work_files = keep_work_files

        self.list_of_output_files = []

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=self.root_file,
            write_to_memory=self.write_work_files_to_memory,
            keep_files=self.keep_work_files,
        )

        if self.list_of_sql_expressions:
            self.line_sql_selection = self.work_file_manager.setup_dynamic_file_paths(
                base_name="selection", count=len(self.list_of_sql_expressions)
            )
            self.feature_to_line = self.work_file_manager.setup_dynamic_file_paths(
                base_name="feature_to_line", count=len(self.list_of_sql_expressions)
            )
        else:
            self.line_sql_selection = "line_sql_selection"
            self.feature_to_line = "feature_to_line"

            self.gdb_files_list = [self.line_sql_selection, self.feature_to_line]
            self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
                instance=self,
                file_structure=self.gdb_files_list,
            )

    @staticmethod
    def _create_intersections(input_line: str, output: str):
        arcpy.management.FeatureToLine(
            in_features=input_line,
            out_feature_class=output,
        )

    def _process_single_feature(
        self, sql_expression: str, selection_path: str, feature_to_line_path: str
    ) -> None:
        """
        Processes a single SQL expression by creating the selection and converting it to a line feature.

        Args:
            sql_expression (str): The SQL expression to use for selection.
            selection_path (str): The file path for the selected feature.
            feature_to_line_path (str): The file path for the resulting line feature.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.input_line_feature,
            expression=sql_expression,
            output_name=selection_path,
        )
        self._create_intersections(
            input_line=selection_path, output=feature_to_line_path
        )
        deleting_added_field_from_feature_to_x(
            input_file_feature=feature_to_line_path,
            field_name_feature=selection_path,
        )
        self.list_of_output_files.append(feature_to_line_path)

    def _process_selected_feature(self):
        if self.list_of_sql_expressions:
            for idx, sql_expression in enumerate(self.list_of_sql_expressions):
                selection_path = self.line_sql_selection[idx]
                feature_to_line_path = self.feature_to_line[idx]

                self._process_single_feature(
                    sql_expression, selection_path, feature_to_line_path
                )
        else:
            # Fallback for a single static file scenario.
            self._create_intersections(output=self.feature_to_line)
            deleting_added_field_from_feature_to_x(
                input_file_feature=self.feature_to_line,
                field_name_feature=self.input_line_feature,
            )
            arcpy.management.CopyFeatures(
                in_features=self.feature_to_line,
                out_feature_class=self.output_processed_feature,
            )

    def run(self):
        # self._process_selected_feature()
        self._process_selected_feature()
        if self.list_of_sql_expressions:
            arcpy.management.Merge(
                inputs=self.list_of_output_files,
                output=self.output_processed_feature,
            )
        self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
    create_intersections = CreateIntersections(
        input_line_feature=Road_N100.data_selection___nvdb_roads___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root___n100_road.value,
        output_processed_feature=f"{Road_N100.data_preparation___dissolved_road_feature_2___n100_road.value}_alt",
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections.run()
