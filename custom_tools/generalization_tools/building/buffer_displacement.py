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
        buffer_factors: List[Union[int, float]],
        buffer_displacement_meter: int = 30,
        fixed_buffer_addition: Union[int, float] = 0,
        building_symbol_dimensions: Dict[int, Tuple[int, int]] = None,
    ):
        self.input_road_lines = input_road_lines
        self.sql_selection_query = sql_selection_query
        self.output_road_buffer_base = output_road_buffer_base
        self.buffer_factors = buffer_factors
        self.buffer_displacement_meter = buffer_displacement_meter
        self.fixed_buffer_addition = fixed_buffer_addition
        self.building_symbol_dimensions = building_symbol_dimensions

    def finding_dimensions(self) -> Tuple[int, int]:
        """
        Finds the smallest building symbol dimension and the largest road dimension.
        """
        if not self.building_symbol_dimensions:
            raise ValueError("building_symbol_dimensions is required.")

        smallest_building_dimension = min(
            min(dimensions) for dimensions in self.building_symbol_dimensions.values()
        )
        largest_road_dimension = max(self.sql_selection_query.values())

        return smallest_building_dimension, largest_road_dimension

    def calculate_iterations(
        self, smallest_building_dimension: int, largest_road_dimension: int
    ) -> List[Tuple[float, float]]:
        """
        Calculate the necessary buffer factors for the iterations.
        """
        maximum_buffer_increase_tolerance = smallest_building_dimension / 2
        total_buffer_needed = self.buffer_displacement_meter
        largest_buffer = (largest_road_dimension * 1) + self.buffer_displacement_meter

        # Determine the number of iterations needed
        num_iterations = int(largest_buffer / maximum_buffer_increase_tolerance) + 1
        increments = []

        current_buffer = 0
        for i in range(num_iterations - 1):
            # Calculate the remaining buffer needed to avoid exceeding the total buffer
            remaining_buffer_needed = largest_buffer - current_buffer
            buffer_increase = min(
                maximum_buffer_increase_tolerance - 1, remaining_buffer_needed
            )
            increments.append(buffer_increase)
            current_buffer += buffer_increase

        # Ensure the final increment meets the exact buffer displacement needed
        final_increment = total_buffer_needed - sum(increments)
        increments.append(final_increment)

        # Create iterations with buffer factors and fixed buffer additions
        iterations = [
            (increment / largest_road_dimension, 0) for increment in increments[:-1]
        ]
        iterations.append((1, increments[-1]))

        # Print debug information
        print(f"buffer displacement: {self.buffer_displacement_meter}")
        print("Increments for each iteration:", increments)
        print("Calculated iterations:", iterations)

        return iterations

    def process_buffer_factor(self, factor: Union[int, float]):
        """
        Processes a single buffer factor by creating buffers and displacing points.
        """
        factor_name = str(factor).replace(".", "_")
        output_road_buffer = f"{self.output_road_buffer_base}_factor_{factor_name}"
        line_to_buffer_symbology = LineToBufferSymbology(
            input_road_lines=self.input_road_lines,
            sql_selection_query=self.sql_selection_query,
            output_road_buffer=output_road_buffer,
            buffer_factor=factor,
            fixed_buffer_addition=self.fixed_buffer_addition,
        )
        line_to_buffer_symbology.run()

    def run(self):
        smallest_building_dimension, largest_road_dimension = self.finding_dimensions()
        print(f"Smallest building symbol dimension: {smallest_building_dimension}")
        print(f"Largest road dimension: {largest_road_dimension}")

        iterations = self.calculate_iterations(
            smallest_building_dimension, largest_road_dimension
        )
        print(f"Calculated iterations: {iterations}")

        # for factor in self.buffer_factors:
        #     self.process_buffer_factor(factor)


if __name__ == "__main__":
    environment_setup.main()

    point_displacement = PointDisplacementUsingBuffers(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_road_buffer_base=Building_N100.line_to_buffer_symbology___buffer_symbology___n100_building.value,
        buffer_factors=[0.5, 0.75, 1],
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
    )
    point_displacement.run()
