import arcpy
from typing import List


from file_manager import WorkFileManager
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup

from composition_configs import logic_config


class DissolveWithIntersections:
    """
    What:
        Dissolve an input line feature class (optionally on fields), then either:
        - For each SQL: select dissolved -> FeatureToLine -> collect and finally Merge to final output
        - If no SQL list: FeatureToLine the dissolved dataset and Copy to final output

    How:
        - Uses WorkFileManager to create work paths (in-memory or on-disk) and clean up afterward.
        - Selection step writes a feature layer if in-memory, otherwise a permanent feature class.
        - The per-SQL FeatureToLine outputs are accumulated and merged (same as the original design).

    Args (via cfg):
        - input_line_feature (GDB path or InjectIO)
        - output_processed_feature (GDB path or InjectIO)
        - work_file_manager_config (root_file, write_to_memory, keep_files)
        - dissolve_fields: Optional[List[str]]
        - sql_expressions: Optional[List[str]]
    """

    def __init__(self, dissolve_intersections_config: logic_config.DissolveInitKwargs):
        self.cfg = dissolve_intersections_config
        self.wfm = WorkFileManager(
            config=dissolve_intersections_config.work_file_manager_config
        )

        self.dissolved_feature = self.wfm.build_file_path("dissolved_feature", "gdb")

        self.write_work_files_to_memory = (
            dissolve_intersections_config.work_file_manager_config.write_to_memory
        )

        self.list_of_output_files: List[str] = []

        if self.cfg.sql_expressions:
            self.line_sql_selection: List[str] = [
                self.wfm.build_file_path("selection", "gdb", index=i)
                for i, _ in enumerate(self.cfg.sql_expressions)
            ]
            self.feature_to_line: List[str] = [
                self.wfm.build_file_path("feature_to_line", "gdb", index=i)
                for i, _ in enumerate(self.cfg.sql_expressions)
            ]
        else:
            self.line_sql_selection = [
                self.wfm.build_file_path("line_sql_selection", "gdb")
            ]
            self.feature_to_line = [self.wfm.build_file_path("feature_to_line", "gdb")]

    def _dissolve_feature(self) -> None:
        if not self.cfg.dissolve_fields:
            arcpy.analysis.PairwiseDissolve(
                in_features=self.cfg.input_line_feature,
                out_feature_class=self.dissolved_feature,
                multi_part="SINGLE_PART",
            )
        else:
            arcpy.analysis.PairwiseDissolve(
                in_features=self.cfg.input_line_feature,
                out_feature_class=self.dissolved_feature,
                dissolve_field=self.cfg.dissolve_fields,
                multi_part="SINGLE_PART",
            )

    @staticmethod
    def _create_intersections(input_line: str, output: str) -> None:
        arcpy.management.FeatureToLine(
            in_features=input_line,
            out_feature_class=output,
        )

    def _select_into(self, sql_expression: str, selection_output: str) -> None:
        """
        Selects from the dissolved feature using the given SQL into either:
        - a feature layer (in-memory mode), or
        - a permanent feature class (disk mode)
        """
        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.dissolved_feature,
                expression=sql_expression,
                output_name=selection_output,
            )
        else:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.dissolved_feature,
                expression=sql_expression,
                output_name=selection_output,
            )

    def _process_single_feature(
        self, sql_expression: str, selection_path: str, feature_to_line_path: str
    ) -> None:
        self._select_into(sql_expression, selection_path)

        self._create_intersections(
            input_line=selection_path,
            output=feature_to_line_path,
        )

        self.list_of_output_files.append(feature_to_line_path)

    def _process_selected_feature(self) -> None:
        if self.cfg.sql_expressions:
            for idx, sql_expression in enumerate(self.cfg.sql_expressions):
                selection_path = self.line_sql_selection[idx]
                feature_to_line_path = self.feature_to_line[idx]
                self._process_single_feature(
                    sql_expression, selection_path, feature_to_line_path
                )
        else:
            self._create_intersections(
                input_line=self.dissolved_feature,
                output=self.feature_to_line[0],
            )

            arcpy.management.CopyFeatures(
                in_features=self.feature_to_line[0],
                out_feature_class=self.cfg.output_processed_feature,
            )

    def run(self) -> None:
        self._dissolve_feature()
        self._process_selected_feature()

        if self.cfg.sql_expressions:
            arcpy.management.Merge(
                inputs=self.list_of_output_files,
                output=self.cfg.output_processed_feature,
            )

        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
