import arcpy
from typing import Union

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools import custom_arcpy


class LineToBufferSymbology:
    def __init__(
        self,
        input_road_lines: str,
        sql_selection_query: dict,
        output_road_buffer: str,
        buffer_factor: Union[int, float] = 1,
        fixed_buffer_addition: Union[int, float] = 0,
    ):
        """
        Initializes the LineToBufferSymbology class with the specified parameters.

        :param input_road_lines: Path to the input road lines.
        :param sql_selection_query: Dictionary containing SQL queries and associated buffer widths.
        :param output_road_buffer: Path to save the output road buffer.
        :param buffer_factor: Multiplicative factor to adjust buffer widths, avoid using 0.
        :param fixed_buffer_addition: Additional fixed width to add to buffer widths.
        """
        self.input_road_lines = input_road_lines
        self.sql_selection_query = sql_selection_query
        self.output_road_buffer = output_road_buffer
        self.buffer_factor = buffer_factor
        self.fixed_buffer_addition = fixed_buffer_addition

        self.working_files_list = []

        if buffer_factor == 0:
            raise ValueError(
                "buffer_factor should not be 0 to avoid non-buffer creation."
            )

    def selecting_different_road_lines(self, sql_query, selection_output_name):
        """
        Selects road lines based on the provided SQL query and creates a feature layer.
        """

        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=self.input_road_lines,
            expression=sql_query,
            output_name=selection_output_name,
        )
        self.working_files_list.append(selection_output_name)

    def creating_buffer_from_selected_lines(
        self, selection_output_name, buffer_width, buffer_output_name
    ):
        """
        Creates a buffer around the selected road lines.
        """
        count_result = arcpy.GetCount_management(selection_output_name)
        feature_count = int(count_result.getOutput(0))

        adjusted_buffer_width = (
            buffer_width * self.buffer_factor
        ) + self.fixed_buffer_addition

        if feature_count > 0:
            arcpy.analysis.PairwiseBuffer(
                in_features=selection_output_name,
                out_feature_class=buffer_output_name,
                buffer_distance_or_field=f"{adjusted_buffer_width} Meters",
            )
            self.working_files_list.append(buffer_output_name)

    def merge_buffers(self, buffer_output_names, merged_output_name):
        """
        Merges multiple buffer outputs into a single feature class.
        """
        arcpy.management.Merge(inputs=buffer_output_names, output=merged_output_name)
        print(f"Merged buffers into {merged_output_name}")

    def process_each_query(self, sql_query, original_width, counter):
        """
        Processes each SQL query to select road lines and create buffers.
        """
        selection_output_name = f"in_memory/road_selection_{counter}"
        buffer_output_name = f"in_memory/line_buffer_{counter}"

        self.selecting_different_road_lines(sql_query, selection_output_name)
        self.creating_buffer_from_selected_lines(
            selection_output_name, original_width, buffer_output_name
        )

        return buffer_output_name

    def delete_working_files(self, *file_paths):
        """
        Deletes multiple feature classes or files.
        """
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    def delete_feature_class(self, feature_class_path):
        """
        Deletes a feature class if it exists.
        """
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    def process_queries(self):
        """
        Processes all SQL queries to create buffers and handle merging.
        """
        buffer_output_names = []
        counter = 1

        for sql_query, original_width in self.sql_selection_query.items():
            buffer_output_name = self.process_each_query(
                sql_query, original_width, counter
            )
            buffer_output_names.append(buffer_output_name)
            counter += 1

        self.merge_buffers(buffer_output_names, self.output_road_buffer)
        self.delete_working_files(*self.working_files_list)

    def run(self):
        self.process_queries()


if __name__ == "__main__":
    environment_setup.main()
    line_to_buffer_symbology = LineToBufferSymbology(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_road_buffer=Building_N100.line_to_buffer_symbology___test___n100_building.value,
        buffer_factor=1,  # This is an optional parameter not needed unless you want another value than 1
        fixed_buffer_addition=0,  # This is an optional parameter not needed unless you want another value than 0
    )
    line_to_buffer_symbology.run()
