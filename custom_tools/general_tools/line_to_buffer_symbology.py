import arcpy

from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from file_manager.work_file_manager import WorkFileManager
from custom_tools.general_tools import file_utilities
from composition_configs import logic_config, core_config


class LineToBufferSymbology:
    def __init__(
        self,
        line_to_buffer_config: logic_config.LineToBufferSymbologyKwargs,
    ):
        """
        What:
            Creates a polygon representation of the line symbolgy given provided line dimensions.

        Args:
            See class docstring.
        """
        self.input_road_lines = line_to_buffer_config.input_line
        self.output_road_buffer = line_to_buffer_config.output_line

        self.sql_selection_query = line_to_buffer_config.sql_selection_query

        self.buffer_factor = line_to_buffer_config.buffer_distance_factor
        self.fixed_buffer_addition = line_to_buffer_config.buffer_distance_addition

        self.wfm = WorkFileManager(
            config=line_to_buffer_config.work_file_manager_config
        )

        self.write_work_files_to_memory = (
            line_to_buffer_config.work_file_manager_config.write_to_memory
        )

        if self.buffer_factor == 0:
            raise ValueError(
                "buffer_factor should not be 0 to avoid non-buffer creation."
            )

    def selecting_different_road_lines(
        self, sql_query: str, selection_output_name: str
    ):
        """
        What:
            Selects road lines based on the provided SQL query and creates a feature layer or a permanent feature class
            depending on the `write_work_files_to_memory` flag.

        Args:
            sql_query (str): The SQL query string used to select the road lines.
            selection_output_name (str): The name for the output feature layer or file.
        """

        if self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_feature_layer(
                input_layer=self.input_road_lines,
                expression=sql_query,
                output_name=selection_output_name,
            )

        if not self.write_work_files_to_memory:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.input_road_lines,
                expression=sql_query,
                output_name=selection_output_name,
            )

    def creating_buffer_from_selected_lines(
        self, selection_output_name, buffer_width, buffer_output_name
    ):
        """
        Creates a buffer around the selected road lines.
        """

        adjusted_buffer_width = (
            buffer_width * self.buffer_factor
        ) + self.fixed_buffer_addition

        if file_utilities.feature_has_rows(selection_output_name):
            arcpy.analysis.PairwiseBuffer(
                in_features=selection_output_name,
                out_feature_class=buffer_output_name,
                buffer_distance_or_field=f"{adjusted_buffer_width} Meters",
            )

    @staticmethod
    def merge_buffers(buffer_output_names, merged_output_name):
        """
        Merges multiple buffer outputs into a single feature class.
        """
        arcpy.management.Merge(inputs=buffer_output_names, output=merged_output_name)

    def process_query_buffer_width_pair(self, sql_query, original_width, counter):
        """
        Processes a SQL query to select road lines and create buffers based on buffer width.
        """

        selection_output_name = self.wfm.build_file_path(
            file_name="road_selection",
            file_type="gdb",
            index=counter,
        )
        buffer_output_name = self.wfm.build_file_path(
            file_name="line_buffer",
            file_type="gdb",
            index=counter,
        )

        self.selecting_different_road_lines(
            sql_query=sql_query,
            selection_output_name=selection_output_name,
        )
        self.creating_buffer_from_selected_lines(
            selection_output_name=selection_output_name,
            buffer_width=original_width,
            buffer_output_name=buffer_output_name,
        )

        return buffer_output_name

    def process_queries(self):
        """
        Processes all SQL queries to create buffers and handle merging.
        """
        buffer_output_names = []
        counter = 1

        for sql_query, original_width in self.sql_selection_query.items():
            buffer_output_name = self.process_query_buffer_width_pair(
                sql_query, original_width, counter
            )

            if file_utilities.feature_has_rows(buffer_output_name):
                buffer_output_names.append(buffer_output_name)
            counter += 1

        self.merge_buffers(buffer_output_names, self.output_road_buffer)

    def run(self):
        self.process_queries()
        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
