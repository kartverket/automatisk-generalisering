import arcpy
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
        iterations = []

        while total_buffer_needed > 0:
            best_factor = 0
            best_addition = 0
            best_increase = 0

            for factor in self.buffer_factors:
                increase = (
                    largest_road_dimension * factor
                ) + self.fixed_buffer_addition
                if maximum_buffer_increase_tolerance > increase > best_increase:
                    best_increase = increase
                    best_factor = factor
                    best_addition = self.fixed_buffer_addition

            if best_increase == 0 or total_buffer_needed - best_increase <= 0:
                iterations.append((1, total_buffer_needed))
                total_buffer_needed = 0
            else:
                iterations.append((best_factor, best_addition))
                total_buffer_needed -= best_increase

            self.fixed_buffer_addition = (
                0  # Resetting fixed addition to 0 for next iterations
            )

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
