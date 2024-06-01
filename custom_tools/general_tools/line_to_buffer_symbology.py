import arcpy
import os

from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

from custom_tools.general_tools.polygon_processor import PolygonProcessor
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy


class LineToBufferSymbology:
    def __init__(
        self,
        input_road_lines,
        sql_selection_query,
        output_feature_class,
    ):
        self.input_road_lines = input_road_lines
        self.sql_selection_query = sql_selection_query
        self.output_feature_class = output_feature_class

    def selecting_different_road_lines(self, selection_output_name):
        """
        Selects road lines based on the provided SQL query and creates a feature layer.
        """
        custom_arcpy.select_attribute_and_make_feature_layer(
            input_layer=self.input_road_lines,
            expression=self.sql_selection_query,
            output_name=selection_output_name,
        )

    def creating_buffer_from_selected_lines(self):
        pass

    def run(self):
        self.selecting_different_road_lines()
        self.creating_buffer_from_selected_lines()


if __name__ == "__main__":
    line_to_buffer_symbology = LineToBufferSymbology(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_feature_class=Building_N100.line_to_buffer_symbology___buffer_symbology___n100_building.value,
    )
    line_to_buffer_symbology.run()
