import arcpy
import math
from typing import Union, List, Dict, Tuple

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from composition_configs import logic_config, core_config
from file_manager.work_file_manager import WorkFileManager
from custom_tools.general_tools import file_utilities


class BufferDisplacement:
    """
    This class handles the displacement of building points relative to road buffers based on specified buffer increments.
    It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
    displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

    **Buffer Displacement Logic:**

    - **Road Buffers:** Buffers are created for road features based on a factor and a fixed buffer addition value.
    - **Building Points:** Building points are processed by converting them into polygons, erasing any that overlap
    with the generated road buffers or other barrier features, and then converting them back into points.
    - **Miscellaneous Objects:** Optional miscellaneous features can be buffered along with roads, and merged into a
    unified barrier layer to control building point displacement.

    **Increment Calculation:**
    The buffer increments are calculated based on the largest road dimension and building symbol dimensions. The process
    ensures that buffers gradually increase up to the target displacement value, while adhering to a set tolerance level.

    **Work File Management:**
    The class can optionally store working files either in memory or on disk, depending on the parameters provided. It
    can also automatically clean up working files if unless keep_work_files is set to False.

    Args:
        input_road_lines (str):
            Path to the input road line features to be buffered.
        input_building_points (str):
            Path to the input building points that will be displaced.
        output_building_points (str):
            Path where the final displaced building points will be stored.
        sql_selection_query (dict):
            A dictionary where the keys are  SQL queries to select from the input road features based on attribute values,
            and the values are the corresponding buffer widths representing the road symbology.
        root_file (str):
            The base path for storing work files, required if `write_work_files_to_memory` is False or
            `keep_work_files` is True.
        buffer_displacement_meter (int, optional):
            The buffer displacement distance in meters. Default is 30 meters.
        building_symbol_dimensions (Dict[int, Tuple[int, int]], optional):
            A dictionary mapping building symbols to their dimensions, used to ensure displacement calculations account for building size.
        input_misc_objects (Dict[str, List[Union[str, int]]], optional):
            A dictionary of miscellaneous objects that will also be buffered, where each entry includes the feature name and a buffer width.
        write_work_files_to_memory (bool, optional):
            If True, work files are written to memory. Default is True.
        keep_work_files (bool, optional):
            If True, work files are retained after the process is complete. Default is False.
    """

    def __init__(
        self,
        buffer_displacement_config: logic_config.BufferDisplacementKwargs,
    ):
        """
        Initialize the BufferDisplacement class with the necessary input data and configuration.

        Args:
            See class docstring.
        """

        self.input_road_lines = buffer_displacement_config.input_road_line
        self.input_building_points = buffer_displacement_config.input_building_points
        self.input_line_barriers = buffer_displacement_config.input_line_barriers

        self.output_building_points = buffer_displacement_config.output_building_points

        self.sql_selection_query = buffer_displacement_config.sql_selection_query
        self.building_symbol_dimensions = (
            buffer_displacement_config.building_symbol_dimension
        )

        self.wfm_config = buffer_displacement_config.work_file_manager_config
        self.wfm = WorkFileManager(config=self.wfm_config)

        self.current_building_points = self.input_building_points

        self.buffer_displacement_meter = (
            buffer_displacement_config.displacement_distance_m
        )

        self.largest_road_dimension = None
        self.maximum_buffer_increase_tolerance = None
        self.tolerance = None
        self.target_value = None
        self.previous_value = 0
        self.current_value = 0
        self.rest_value = 0
        self.iteration_fixed_buffer_addition = 0
        self.increments = []

        self.file_location = None
        self.unique_id = id(self)

        self.output_road_buffer = None
        self.misc_buffer_output = None
        self.merged_barrier_output = None
        self.output_building_points_to_polygon = None
        self.erased_building_polygons = None
        self.output_feature_to_points = None

    def finding_dimensions(self, buffer_displacement_meter: int):
        """
        Finds the smallest building symbol dimension and the largest road dimension to calculate the maximum
        buffer tolerance and target displacement value to prevent loosing buildings due to large increases.
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

    def calculate_buffer_increments(self) -> list:
        """
        What:
            Calculates incremental buffer steps based on the road and building dimensions and tolerance, ensuring that
            buffer increments increase gradually until the target displacement value is reached.

        Returns:
            list: A list of tuples where each tuple contains a buffer factor and the corresponding buffer addition.
        """
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
        What:
            Processes a single buffer factor, creating buffers for the roads and any miscellaneous features, and then
            displaces the building points based on the calculated buffers.

        Args:
            factor (Union[int, float]): The buffer factor to be applied.
            fixed_addition (Union[int, float]): The fixed buffer addition value to be applied.
        """
        factor_str = str(factor).replace(".", "_")
        fixed_addition_str = str(fixed_addition).replace(".", "_")

        self.output_road_buffer = self.wfm.build_file_path(
            file_name=f"road_facter_{factor_str}_add_{fixed_addition_str}",
        )

        if file_utilities.feature_has_rows(feature=self.input_road_lines):
            line_to_buffer_symbology = LineToBufferSymbology(
                logic_config.LineToBufferSymbologyKwargs(
                    input_line=self.input_road_lines,
                    output_line=self.output_road_buffer,
                    sql_selection_query=self.sql_selection_query,
                    work_file_manager_config=self.wfm_config,
                    buffer_distance_factor=factor,
                    buffer_distance_addition=fixed_addition,
                )
            )
            line_to_buffer_symbology.run()

        misc_buffer_outputs = []

        for feature_name, feature_details in self.input_line_barriers.items():
            feature_path, buffer_width = feature_details
            calculated_buffer_width = (buffer_width * factor) + fixed_addition
            self.misc_buffer_output = self.wfm.build_file_path(
                file_name=f"{feature_name}_buffer_factor_{factor_str}_add_{fixed_addition_str}",
                file_type="gdb",
            )

            if buffer_width == 0:
                arcpy.analysis.PairwiseBuffer(
                    in_features=feature_path,
                    out_feature_class=self.misc_buffer_output,
                    buffer_distance_or_field="0.1 Meters",
                )
            else:
                arcpy.analysis.PairwiseBuffer(
                    in_features=feature_path,
                    out_feature_class=self.misc_buffer_output,
                    buffer_distance_or_field=f"{calculated_buffer_width} Meters",
                )
            misc_buffer_outputs.append(self.misc_buffer_output)

        self.merged_barrier_output = self.wfm.build_file_path(
            file_name=f"merged_barriers_factor_{factor_str}_add_{fixed_addition_str}",
            file_type="gdb",
        )
        inputs = [self.output_road_buffer] + misc_buffer_outputs
        inputs = [p for p in inputs if p and file_utilities.feature_has_rows(p)]

        if len(inputs) == 1:
            arcpy.management.CopyFeatures(
                in_features=inputs[0],
                out_feature_class=self.merged_barrier_output,
            )
        else:
            arcpy.management.Merge(
                inputs=inputs,
                output=self.merged_barrier_output,
            )

        self.output_building_points_to_polygon = self.wfm.build_file_path(
            file_name=f"building_factor_{factor_str}_add_{fixed_addition_str}",
            file_type="gdb",
        )

        file_utilities.print_feature_info(
            file_path=self.current_building_points,
            description="Building Points in to polygon_processor",
        )

        building_polygons = PolygonProcessor(
            input_building_points=self.current_building_points,
            output_polygon_feature_class=self.output_building_points_to_polygon,
            building_symbol_dimensions=self.building_symbol_dimensions,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        building_polygons.run()

        self.erased_building_polygons = self.wfm.build_file_path(
            file_name=f"erased_buildings_factor_{factor_str}_add_{fixed_addition_str}",
            file_type="gdb",
        )

        arcpy.analysis.Erase(
            in_features=self.output_building_points_to_polygon,
            erase_features=self.merged_barrier_output,
            out_feature_class=self.erased_building_polygons,
        )

        building_count = file_utilities.feature_has_rows(self.erased_building_polygons)
        if building_count:
            print(
                f"\nErased buildings: {file_utilities.count_objects(self.erased_building_polygons)}\n"
            )
        else:
            print(
                f"\nErased buildings: {file_utilities.feature_has_rows(self.erased_building_polygons)}\n"
            )

        self.output_feature_to_points = self.wfm.build_file_path(
            file_name=f"output_feature_to_points_factor_{factor_str}_add_{fixed_addition_str}",
            file_type="gdb",
        )

        arcpy.management.FeatureToPoint(
            in_features=self.erased_building_polygons,
            out_feature_class=self.output_feature_to_points,
            point_location="INSIDE",
        )

        self.current_building_points = self.output_feature_to_points

        building_count = file_utilities.feature_has_rows(self.current_building_points)
        if building_count:
            print(
                f"\nBuilding Points end of loop: {file_utilities.count_objects(self.current_building_points)}\n"
            )
        else:
            print(
                f"\nBuilding Points end of loop: {file_utilities.feature_has_rows(self.current_building_points)}\n"
            )

        print(
            f"current_building_points path end of loop:\n{self.current_building_points}"
        )

    def delete_working_files(self, *file_paths):
        """
        Deletes multiple feature classes or files.

        Args:
            *file_paths: Paths of files to be deleted.
        """
        for file_path in file_paths:
            self.delete_feature_class(file_path)
            print(f"Deleted file: {file_path}")

    @staticmethod
    def delete_feature_class(feature_class_path: str):
        """
        Deletes a feature class if it exists.

        Args:
            feature_class_path (str): Path to the feature class to be deleted.
        """
        if arcpy.Exists(feature_class_path):
            arcpy.management.Delete(feature_class_path)

    @partition_io_decorator(
        input_param_names=[
            "input_road_lines",
            "input_building_points",
            "input_misc_objects",
        ],
        output_param_names=["output_building_points"],
    )
    def run(self):
        """
        Executes the buffer displacement process, running the calculations for buffer increments, applying buffers,
        displacing building points, and writing the final output.
        """
        self.finding_dimensions(self.buffer_displacement_meter)
        self.calculate_buffer_increments()

        has_features = False
        if file_utilities.feature_has_rows(self.input_road_lines):
            has_features = True
        for feature_name, feature_details in self.input_line_barriers.items():
            feature_path, _ = feature_details
            if file_utilities.feature_has_rows(feature_path):
                has_features = True

        if has_features:
            for factor, addition in self.increments:
                self.process_buffer_factor(factor, addition)

                self.wfm.delete_created_files(
                    exceptions=[
                        self.current_building_points,
                        self.output_feature_to_points,
                    ]
                )

        arcpy.management.Copy(
            in_data=self.current_building_points,
            out_data=self.output_building_points,
        )
        self.wfm.delete_created_files()


if __name__ == "__main__":
    environment_setup.main()
