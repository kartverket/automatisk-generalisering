import arcpy
import math
from typing import Union, List, Dict, Tuple

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology


class PointDisplacementUsingBuffers:
    def __init__(
        self,
        input_road_lines: str,
        sql_selection_query: dict,
        output_road_buffer_base: str,
        buffer_displacement_meter: int = 30,
        building_symbol_dimensions: Dict[int, Tuple[int, int]] = None,
    ):
        self.input_road_lines = input_road_lines
        self.sql_selection_query = sql_selection_query
        self.output_road_buffer_base = output_road_buffer_base

        self.buffer_displacement_meter = buffer_displacement_meter
        self.building_symbol_dimensions = building_symbol_dimensions

        self.largest_road_dimension = None
        self.buffer_displacement_meter = buffer_displacement_meter
        self.maximum_buffer_increase_tolerance = None
        self.tolerance = None
        self.target_value = None
        self.previous_value = 0
        self.current_value = 0
        self.rest_value = 0
        self.iteration_fixed_buffer_addition = 0
        self.increments = []

    def finding_dimensions(self, buffer_displacement_meter):
        """
        Finds the smallest building symbol dimension and the largest road dimension.
        """
        if not self.building_symbol_dimensions:
            raise ValueError("building_symbol_dimensions is required.")

        smallest_building_dimension = min(
            min(dimensions) for dimensions in self.building_symbol_dimensions.values()
        )
        maximum_buffer_increase_tolerance = smallest_building_dimension / 2

        self.maximum_buffer_increase_tolerance = maximum_buffer_increase_tolerance
        self.tolerance = self.maximum_buffer_increase_tolerance - 1
        self.largest_road_dimension = max(self.sql_selection_query.values())

        self.maximum_buffer_increase_tolerance = maximum_buffer_increase_tolerance

        self.target_value = self.largest_road_dimension + buffer_displacement_meter

    def calculate_buffer_increments(self):
        iteration_buffer_factor = 0

        found_valid_increment = False

        while iteration_buffer_factor < 1:
            next_buffer_factor = iteration_buffer_factor + 0.001

            if not found_valid_increment:
                increment_value = next_buffer_factor * self.largest_road_dimension
            else:
                increment_value = (
                    next_buffer_factor * self.largest_road_dimension
                ) - self.previous_value

            if increment_value >= self.tolerance:
                if not found_valid_increment:
                    iteration_buffer_factor = next_buffer_factor - 0.001
                iteration_buffer_factor = round(iteration_buffer_factor, 3)
                self.increments.append((iteration_buffer_factor, 0))
                self.current_value = (
                    iteration_buffer_factor * self.largest_road_dimension
                )
                self.previous_value = self.current_value
                found_valid_increment = True
                iteration_buffer_factor = next_buffer_factor

                continue

            iteration_buffer_factor = next_buffer_factor
            self.current_value = iteration_buffer_factor * self.largest_road_dimension

        if self.previous_value != self.current_value:
            self.current_value = self.largest_road_dimension
            increase_from_last_cleanup = self.current_value - self.previous_value

            self.rest_value = self.tolerance - increase_from_last_cleanup

            self.rest_value = round(self.rest_value, 1)
            self.increments.append((1, self.rest_value))
            self.current_value = self.rest_value
        else:
            self.current_value = 0

        self.target_value = self.buffer_displacement_meter

        while self.current_value <= self.target_value:
            missing_value = self.target_value - self.current_value

            if missing_value <= self.tolerance:
                self.increments.append((1, self.buffer_displacement_meter))

                break

            increment_value = min(self.tolerance, missing_value)
            self.iteration_fixed_buffer_addition = increment_value + self.current_value

            self.increments.append((1, self.iteration_fixed_buffer_addition))
            self.current_value = self.iteration_fixed_buffer_addition

        print(self.increments)

        return self.increments

    def process_buffer_factor(
        self, factor: Union[int, float], fixed_addition: Union[int, float]
    ):
        """
        Processes a single buffer factor by creating buffers and displacing points.
        """
        factor_name = str(factor).replace(".", "_")
        fixed_addition_name = str(fixed_addition).replace(".", "_")

        output_road_buffer = f"{self.output_road_buffer_base}_factor_{factor_name}_add_{fixed_addition_name}"
        line_to_buffer_symbology = LineToBufferSymbology(
            input_road_lines=self.input_road_lines,
            sql_selection_query=self.sql_selection_query,
            output_road_buffer=output_road_buffer,
            buffer_factor=factor,
            fixed_buffer_addition=fixed_addition,
        )
        line_to_buffer_symbology.run()

    def run(self):
        self.finding_dimensions(self.buffer_displacement_meter)
        self.calculate_buffer_increments()

        for factor, addition in self.increments:
            self.process_buffer_factor(factor, addition)


if __name__ == "__main__":
    environment_setup.main()

    point_displacement = PointDisplacementUsingBuffers(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_road_buffer_base=Building_N100.line_to_buffer_symbology___buffer_symbology___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
    )
    point_displacement.run()
