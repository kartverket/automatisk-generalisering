import arcpy
import math
from typing import Union, List, Dict, Tuple

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from input_data import input_n100
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.decorators.partition_io_decorator import partition_io_decorator


class BufferDisplacement:
    def __init__(
        self,
        input_road_lines: str,
        input_building_points: str,
        output_building_points: str,
        sql_selection_query: dict,
        output_road_buffer_base: str,
        buffer_displacement_meter: int = 30,
        building_symbol_dimensions: Dict[int, Tuple[int, int]] = None,
        input_misc_objects: Dict[str, List[Union[str, int]]] = None,
    ):
        self.input_road_lines = input_road_lines
        self.input_building_points = input_building_points
        self.sql_selection_query = sql_selection_query
        self.output_road_buffer_base = output_road_buffer_base
        self.input_misc_objects = input_misc_objects
        self.output_building_points = output_building_points

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

        self.current_building_points = self.input_building_points

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

        output_road_buffer = f"{self.output_road_buffer_base}_road_factor_{factor_name}_add_{fixed_addition_name}"
        line_to_buffer_symbology = LineToBufferSymbology(
            input_road_lines=self.input_road_lines,
            sql_selection_query=self.sql_selection_query,
            output_road_buffer=output_road_buffer,
            buffer_factor=factor,
            fixed_buffer_addition=fixed_addition,
        )
        line_to_buffer_symbology.run()

        misc_buffer_outputs = []

        for feature_name, feature_details in self.input_misc_objects.items():
            feature_path, buffer_width = feature_details
            calculated_buffer_width = (buffer_width * factor) + fixed_addition
            misc_buffer_output = f"{self.output_road_buffer_base}_{feature_name}_buffer_factor_{factor_name}_add_{fixed_addition_name}"

            if buffer_width == 0:
                arcpy.management.Copy(
                    in_data=feature_path,
                    out_data=misc_buffer_output,
                )
            else:
                arcpy.analysis.PairwiseBuffer(
                    in_features=feature_path,
                    out_feature_class=misc_buffer_output,
                    buffer_distance_or_field=f"{calculated_buffer_width} Meters",
                )
            misc_buffer_outputs.append(misc_buffer_output)

        merged_barrier_output = f"{self.output_road_buffer_base}_merged_barriers_factor_{factor_name}_add_{fixed_addition_name}"
        arcpy.management.Merge(
            inputs=[output_road_buffer] + misc_buffer_outputs,
            output=merged_barrier_output,
        )

        output_building_points = f"{self.output_road_buffer_base}_building_factor_{factor_name}_add_{fixed_addition_name}"

        building_polygons = PolygonProcessor(
            input_building_points=self.current_building_points,
            output_polygon_feature_class=output_building_points,
            building_symbol_dimensions=self.building_symbol_dimensions,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        building_polygons.run()

        output_feature_to_point = f"{self.output_road_buffer_base}_erased_buildings_factor_{factor_name}_add_{fixed_addition_name}"
        arcpy.analysis.PairwiseErase(
            in_features=output_building_points,
            erase_features=merged_barrier_output,
            out_feature_class=output_feature_to_point,
        )

        output_feature_to_points = f"{self.output_road_buffer_base}_output_feature_to_points_factor_{factor_name}_add_{fixed_addition_name}"

        arcpy.management.FeatureToPoint(
            in_features=output_feature_to_point,
            out_feature_class=output_feature_to_points,
            point_location="INSIDE",
        )

        self.current_building_points = output_feature_to_points

    @partition_io_decorator(
        input_param_names=[
            "input_road_lines",
            "input_building_points",
            "input_misc_objects",
        ],
        output_param_names=["output_building_points"],
    )
    def run(self):
        self.finding_dimensions(self.buffer_displacement_meter)
        self.calculate_buffer_increments()

        for factor, addition in self.increments:
            self.process_buffer_factor(factor, addition)

        arcpy.management.Copy(
            in_data=self.current_building_points,
            out_data=self.output_building_points,
        )


if __name__ == "__main__":
    environment_setup.main()

    misc_objects = {
        "begrensningskurve": [
            Building_N100.building_point_buffer_displacement__begrensningskurve_study_area__n100.value,
            0,
        ],
        "urban_areas": [
            Building_N100.building_point_buffer_displacement__selection_urban_areas__n100.value,
            1,
        ],
        "bane_station": [
            input_n100.JernbaneStasjon,
            1,
        ],
        "bane_lines": [
            input_n100.Bane,
            1,
        ],
    }

    point_displacement = BufferDisplacement(
        input_road_lines=Building_N100.building_point_buffer_displacement__roads_study_area__n100.value,
        input_building_points=Building_N100.building_point_buffer_displacement__buildings_study_area__n100.value,
        input_misc_objects=misc_objects,
        output_building_points=Building_N100.line_to_buffer_symbology___buffer_displaced_building_points___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        output_road_buffer_base=Building_N100.line_to_buffer_symbology___test___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        buffer_displacement_meter=N100_Values.buffer_clearance_distance_m.value,
    )
    point_displacement.run()

    misc_objects = {
        "begrensningskurve": (
            ("begrensningskurve", "context"),
            0,
        ),
        "urban_areas": (
            ("urban_areas", "context"),
            1,
        ),
        "bane_station": (
            ("bane_station", "context"),
            1,
        ),
        "bane_lines": (
            ("bane_lines", "context"),
            1,
        ),
    }
