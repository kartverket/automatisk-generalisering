import arcpy
import math
from typing import Union, List, Dict, Tuple

from env_setup import environment_setup
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values
from file_manager.n100.file_manager_buildings import Building_N100
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.decorators.partition_io_decorator import partition_io_decorator


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
        input_road_lines: str,
        input_building_points: str,
        output_building_points: str,
        sql_selection_query: dict,
        root_file: str,
        buffer_displacement_meter: int = 30,
        building_symbol_dimensions: Dict[int, Tuple[int, int]] = None,
        input_misc_objects: Dict[str, List[Union[str, int]]] = None,
        write_work_files_to_memory: bool = True,
        keep_work_files: bool = False,
    ):
        """
        Initialize the BufferDisplacement class with the necessary input data and configuration.

        Args:
            See class docstring.
        """

        self.input_road_lines = input_road_lines
        self.input_building_points = input_building_points
        self.sql_selection_query = sql_selection_query
        self.root_file = root_file
        self.input_misc_objects = input_misc_objects
        self.output_building_points = output_building_points

        self.current_building_points = self.input_building_points

        self.write_work_files_to_memory = write_work_files_to_memory
        self.keep_work_files = keep_work_files

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

        self.file_location = None
        self.unique_id = id(self)

        self.output_road_buffer = None
        self.misc_buffer_output = None
        self.merged_barrier_output = None
        self.output_building_points_to_polygon = None
        self.erased_building_polygons = None
        self.output_feature_to_points = None

        self.working_files_list = []
        self.working_files_list_2 = []

    def initialize_work_file_location(self):
        """
        Determines the file location for temporary work files, either in memory or on disk, based on class parameters.
        """
        temporary_file = "in_memory\\"
        permanent_file = f"{self.root_file}_"
        if self.root_file is None:
            if not self.write_work_files_to_memory:
                raise ValueError(
                    "Need to specify root_file path to write to disk for work files."
                )
            if self.keep_work_files:
                raise ValueError(
                    "Need to specify root_file path and write to disk to keep_work_files."
                )

        if self.write_work_files_to_memory:
            self.file_location = temporary_file
        else:
            self.file_location = permanent_file

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
        factor_name = str(factor).replace(".", "_")
        fixed_addition_name = str(fixed_addition).replace(".", "_")

        self.output_road_buffer = f"{self.file_location}_road_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
        self.working_files_list.append(self.output_road_buffer)

        line_to_buffer_symbology = LineToBufferSymbology(
            input_road_lines=self.input_road_lines,
            sql_selection_query=self.sql_selection_query,
            output_road_buffer=self.output_road_buffer,
            root_file=self.root_file,
            buffer_factor=factor,
            fixed_buffer_addition=fixed_addition,
            keep_work_files=self.keep_work_files,
            write_work_files_to_memory=self.write_work_files_to_memory,
        )
        line_to_buffer_symbology.run()

        misc_buffer_outputs = []

        for feature_name, feature_details in self.input_misc_objects.items():
            feature_path, buffer_width = feature_details
            calculated_buffer_width = (buffer_width * factor) + fixed_addition
            self.misc_buffer_output = f"{self.file_location}_{feature_name}_buffer_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
            self.working_files_list.append(self.misc_buffer_output)

            if buffer_width == 0:
                arcpy.analysis.PairwiseBuffer(
                    in_features=feature_path,
                    out_feature_class=self.misc_buffer_output,
                    buffer_distance_or_field=f"0,1 Meters",
                )
            else:
                arcpy.analysis.PairwiseBuffer(
                    in_features=feature_path,
                    out_feature_class=self.misc_buffer_output,
                    buffer_distance_or_field=f"{calculated_buffer_width} Meters",
                )
            misc_buffer_outputs.append(self.misc_buffer_output)

        self.merged_barrier_output = f"{self.file_location}_merged_barriers_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
        self.working_files_list.append(self.merged_barrier_output)

        arcpy.management.Merge(
            inputs=[self.output_road_buffer] + misc_buffer_outputs,
            output=self.merged_barrier_output,
        )

        self.output_building_points_to_polygon = f"{self.root_file}_building_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
        self.working_files_list.append(self.output_building_points_to_polygon)

        building_polygons = PolygonProcessor(
            input_building_points=self.current_building_points,
            output_polygon_feature_class=self.output_building_points_to_polygon,
            building_symbol_dimensions=self.building_symbol_dimensions,
            symbol_field_name="symbol_val",
            index_field_name="OBJECTID",
        )
        building_polygons.run()

        self.erased_building_polygons = f"{self.file_location}_erased_buildings_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
        self.working_files_list.append(self.erased_building_polygons)

        arcpy.analysis.Erase(
            in_features=self.output_building_points_to_polygon,
            erase_features=self.merged_barrier_output,
            out_feature_class=self.erased_building_polygons,
        )

        self.output_feature_to_points = f"{self.root_file}_output_feature_to_points_factor_{factor_name}_add_{fixed_addition_name}__{self.unique_id}"
        self.working_files_list_2.append(self.output_feature_to_points)

        arcpy.management.FeatureToPoint(
            in_features=self.erased_building_polygons,
            out_feature_class=self.output_feature_to_points,
            point_location="INSIDE",
        )

        self.current_building_points = self.output_feature_to_points

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
        self.initialize_work_file_location()
        self.finding_dimensions(self.buffer_displacement_meter)
        self.calculate_buffer_increments()

        for factor, addition in self.increments:
            self.process_buffer_factor(factor, addition)

            if not self.keep_work_files:
                self.delete_working_files(*self.working_files_list)

        arcpy.management.Copy(
            in_data=self.current_building_points,
            out_data=self.output_building_points,
        )
        if not self.keep_work_files:
            self.delete_working_files(*self.working_files_list_2)


if __name__ == "__main__":
    environment_setup.main()

    misc_objects = {
        "begrensningskurve": [
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            0,
        ],
        "urban_areas": [
            Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
            1,
        ],
        "bane_station": [
            Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
            1,
        ],
        "bane_lines": [
            Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            1,
        ],
    }

    point_displacement = BufferDisplacement(
        input_road_lines=Building_N100.data_preparation___unsplit_roads___n100_building.value,
        input_building_points=Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
        input_misc_objects=misc_objects,
        output_building_points=Building_N100.line_to_buffer_symbology___buffer_displaced_building_points___n100_building.value,
        sql_selection_query=N100_SQLResources.road_symbology_size_sql_selection.value,
        root_file=Building_N100.line_to_buffer_symbology___root_buffer_displaced___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        buffer_displacement_meter=N100_Values.buffer_clearance_distance_m.value,
        write_work_files_to_memory=True,
        keep_work_files=False,
    )
    point_displacement.run()

    point_displacement.finding_dimensions(point_displacement.buffer_displacement_meter)
    point_displacement.calculate_buffer_increments()
    print(type(point_displacement.increments))
