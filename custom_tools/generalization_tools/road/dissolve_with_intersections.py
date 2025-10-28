import arcpy
from enum import Enum


from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.file_utilities import (
    deleting_added_field_from_feature_to_x,
)

from file_manager import WorkFileManager
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup

from composition_configs import core_config, logic_config


class DissolveWithIntersections:
    def __init__(self, dissolve_intersections_config: logic_config.DissolveInitKwargs):
        self.cfg = dissolve_intersections_config
        self.wfm = WorkFileManager(
            config=dissolve_intersections_config.work_file_manager_config
        )

        self.dissolved = self.wfm.build_file_path("dissolved_feature", "gdb")

        if dissolve_intersections_config.sql_expressions:
            self.selection_paths = [
                self.wfm.build_file_path(f"selection_{i}", "gdb")
                for i, _ in enumerate(dissolve_intersections_config.sql_expressions)
            ]
            self.ftl_paths = [
                self.wfm.build_file_path(f"feature_to_line_{i}", "gdb")
                for i, _ in enumerate(dissolve_intersections_config.sql_expressions)
            ]
        else:
            self.selection_paths = [
                self.wfm.build_file_path("line_sql_selection", "gdb")
            ]
            self.ftl_paths = [self.wfm.build_file_path("feature_to_line", "gdb")]

    # --- internals ---------------------------------------------------------

    def _dissolve(self) -> None:
        if not self.cfg.dissolve_fields:
            arcpy.analysis.PairwiseDissolve(
                in_features=self.cfg.input_line_feature,
                out_feature_class=self.dissolved,
                multi_part="SINGLE_PART",
            )
        else:
            arcpy.analysis.PairwiseDissolve(
                in_features=self.cfg.input_line_feature,
                out_feature_class=self.dissolved,
                dissolve_field=self.cfg.dissolve_fields,
                multi_part="SINGLE_PART",
            )

    @staticmethod
    def _feature_to_line(input_line: str, output_fc: str) -> None:
        arcpy.management.FeatureToLine(
            in_features=input_line,
            out_feature_class=output_fc,
        )

    def _process_one(self, sql: str, selection_fc: str, ftl_fc: str) -> None:
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved,
            expression=sql,
            output_name=selection_fc,
        )
        self._feature_to_line(selection_fc, ftl_fc)

        self._create_intersections(
            input_line=selection_path,
            output=feature_to_line_path,
        )

        """deleting_added_field_from_feature_to_x(
            input_file_feature=feature_to_line_path,
            field_name_feature=selection_path,
        )"""

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
            self._create_intersections(
                input_line=self.dissolved_feature, output=self.feature_to_line
            )
            """deleting_added_field_from_feature_to_x(
                input_file_feature=self.feature_to_line,
                field_name_feature=self.dissolved_feature,
            )"""
            arcpy.management.CopyFeatures(
                in_features=self.ftl_paths[0],
                out_feature_class=self.cfg.output_processed_feature,
            )

    # --- public API --------------------------------------------------------

    def run(self) -> None:
        self._dissolve()
        self._process()

        if self.cfg.sql_expressions:
            arcpy.management.Merge(
                inputs=self.ftl_paths,
                output=self.cfg.output_processed_feature,
            )

        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
