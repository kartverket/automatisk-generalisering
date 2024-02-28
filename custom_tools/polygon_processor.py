import numpy as np
import arcpy
import os
from tqdm import tqdm
import random
from multiprocessing import Pool, cpu_count

import config
from env_setup import environment_setup
from file_manager.n100.file_manager_buildings import Building_N100
from env_setup import setup_directory_structure


class PolygonProcessor:
    """
    Example
    -------
    To use PolygonProcessor to convert building points to polygons:

    >>> building_symbol_dimensions = {1: (145, 145), 2: (195, 145)}
    >>> polygon_processor = PolygonProcessor(
    ...     input_building_points="path/to/input/building_points",
    ...     output_polygon_feature_class="path/to/output/polygon_feature_class",
    ...     building_symbol_dimensions=building_symbol_dimensions,
    ...     symbol_field_name="symbol_type_field",
    ...     index_field_name="object_id_field"
    ... )
    >>> polygon_processor.run()

    Processes building point data to generate polygon feature classes keeping the attributes.

    This class converts point geometries into polygon geometries based on given symbol dimensions.
    It handles batch processing, joining additional fields, and cleaning up temporary data.

    Parameters
    ----------
    input_building_points : str
        The path to the input building points feature class.
    output_polygon_feature_class : str
        The path to the output polygon feature class.
    building_symbol_dimensions : dict
        A dictionary mapping symbol types to their width and height dimensions.
    symbol_field_name : str
        The name of the field in the input feature class that contains symbol type information.
    index_field_name : str
        The name of the field in the input feature class used for indexing during join operations.

    Attributes
    ----------
    input_building_points : str
        The input building points feature class.
    output_polygon_feature_class : str
        The output polygon feature class.
    spatial_reference_system : SpatialReference
        The spatial reference system used for the feature classes.
    building_symbol_dimensions : dict
        The dimensions for each symbol type.
    symbol_field_name : str
        The field name for symbol type.
    index_field_name : str
        The field name for indexing.
    origin_id_field : str
        The generated unique field name for joining operations.
    IN_MEMORY_WORKSPACE : str
        The in-memory workspace used for temporary storage.
    TEMPORARY_FEATURE_CLASS_NAME : str
        The name of the temporary feature class.
    BATCH_PERCENTAGE : float
        The percentage of the total data processed in each batch.
    NUMBER_OF_SUBSETS : int
        The number of subsets to divide the data into for processing.
    PERCENTAGE_OF_CPU_CORES : float
        The percentage of CPU cores to use for parallel processing.
    """

    # Initialization
    def __init__(
        self,
        input_building_points,
        output_polygon_feature_class,
        building_symbol_dimensions,
        symbol_field_name,
        index_field_name,
    ):
        self.input_building_points = input_building_points
        self.output_polygon_feature_class = output_polygon_feature_class
        self.building_symbol_dimensions = building_symbol_dimensions
        self.symbol_field_name = symbol_field_name
        self.index_field_name = index_field_name
        # Delay initialization of attributes that depend on external resources
        self.spatial_reference_system = None
        self.origin_id_field = None
        # Constants and configurations
        self.IN_MEMORY_WORKSPACE = config.default_project_workspace
        self.TEMPORARY_FEATURE_CLASS_NAME = "temporary_polygon_feature_class"
        self.BATCH_PERCENTAGE = 0.02
        self.NUMBER_OF_SUBSETS = 5
        self.PERCENTAGE_OF_CPU_CORES = 1.0

    # Utility Functions
    def generate_unique_field_name(self, dataset, base_name):
        existing_field_names = [field.name for field in arcpy.ListFields(dataset)]
        unique_name = base_name
        while unique_name in existing_field_names:
            unique_name = f"{base_name}_{random.randint(0, 9)}"
        return unique_name

    # Core Processing Functions
    def calculate_well_known_text_polygon(self, arguments):
        """
        Generates the Well-Known Text (WKT) representation of a polygon based on input arguments.
        Args:
            arguments (tuple): A tuple containing index, x-coordinate, y-coordinate, object ID, and symbol type.
        Returns:
            tuple: A tuple containing the object ID and its corresponding WKT polygon.
        """
        index, x_coordinate, y_coordinate, object_id, symbol_val = arguments
        polygon_width, polygon_height = self.building_symbol_dimensions[symbol_val]
        half_width = polygon_width / 2
        half_height = polygon_height / 2
        x_offsets = np.array([-half_width, half_width, half_width, -half_width])
        y_offsets = np.array([-half_height, -half_height, half_height, half_height])
        corner_x_values = x_coordinate + x_offsets
        corner_y_values = y_coordinate + y_offsets
        polygon_corners = list(zip(corner_x_values, corner_y_values))
        polygon_corners.append(polygon_corners[0])  # Close the polygon
        return object_id, self.convert_corners_to_wkt(polygon_corners)

    def convert_corners_to_wkt(self, polygon_corners):
        """
        Converts a list of polygon corner coordinates to a Well-Known Text (WKT) string.
        Args:
            polygon_corners (list): A list of tuples representing the coordinates of the polygon corners.
        Returns:
            str: The WKT representation of the polygon.
        """
        coordinate_strings = ", ".join(f"{x} {y}" for x, y in polygon_corners)
        return f"POLYGON (({coordinate_strings}))"

    # Data Handling and Batch Processing
    def create_output_feature_class_if_not_exists(self):
        """
        Deletes and creates an output feature class.
        This ensures that a fresh feature class is created each time the script runs.
        """
        if arcpy.Exists(self.output_polygon_feature_class):
            arcpy.management.Delete(self.output_polygon_feature_class)

        output_workspace, output_class_name = os.path.split(
            self.output_polygon_feature_class
        )
        arcpy.CreateFeatureclass_management(
            output_workspace,
            output_class_name,
            "POLYGON",
            spatial_reference=self.spatial_reference_system,
        )

        arcpy.management.AddField(
            in_table=self.output_polygon_feature_class,
            field_name=self.origin_id_field,
            field_type="LONG",
        )

    def process_data_in_batches(self, well_known_text_data):
        """
        Processes data in batches and appends the results to the output feature class.
        Args:
            well_known_text_data (list): A list of tuples containing object IDs and their WKT polygons.
        """
        temporary_feature_class = (
            f"{self.IN_MEMORY_WORKSPACE}/{self.TEMPORARY_FEATURE_CLASS_NAME}"
        )
        arcpy.CreateFeatureclass_management(
            self.IN_MEMORY_WORKSPACE,
            self.TEMPORARY_FEATURE_CLASS_NAME,
            "POLYGON",
            spatial_reference=self.spatial_reference_system,
        )
        arcpy.AddField_management(temporary_feature_class, self.origin_id_field, "LONG")

        total_rows = len(well_known_text_data)
        batch_size = int(total_rows * self.BATCH_PERCENTAGE)
        subset_size = len(well_known_text_data) // self.NUMBER_OF_SUBSETS

        for subset_index in range(self.NUMBER_OF_SUBSETS):
            start_index = subset_index * subset_size
            end_index = (
                start_index + subset_size
                if subset_index < self.NUMBER_OF_SUBSETS - 1
                else len(well_known_text_data)
            )
            subset_data = well_known_text_data[start_index:end_index]

            for batch_start in tqdm(range(0, len(subset_data), batch_size)):
                batch_end = min(batch_start + batch_size, len(subset_data))
                batch = subset_data[batch_start:batch_end]
                with arcpy.da.InsertCursor(
                    temporary_feature_class, [self.origin_id_field, "SHAPE@"]
                ) as cursor:
                    for object_id, wkt in batch:
                        polygon = arcpy.FromWKT(wkt, self.spatial_reference_system)
                        cursor.insertRow([object_id, polygon])

            arcpy.Append_management(
                temporary_feature_class, self.output_polygon_feature_class, "NO_TEST"
            )
            arcpy.DeleteRows_management(temporary_feature_class)

    # Field Management and Cleanup
    def add_fields_with_join(self):
        """
        Joins fields from the input building points to the output polygon feature class.
        """
        # Add index to the join field in the output feature class
        arcpy.management.AddIndex(
            self.output_polygon_feature_class,
            self.origin_id_field,
            f"{self.origin_id_field}_index",
        )
        arcpy.management.JoinField(
            self.output_polygon_feature_class,
            self.origin_id_field,
            self.input_building_points,
            self.index_field_name,
        )

    def delete_origin_id_field(self):
        """
        Deletes the origin_id_field from the output feature class.
        """
        try:
            arcpy.management.DeleteField(
                self.output_polygon_feature_class, self.origin_id_field
            )
            print(f"Field {self.origin_id_field} deleted successfully.")
        except Exception as e:
            print(f"Error deleting field {self.origin_id_field}: {e}")

    # Main Execution
    def run(self):
        """
        Orchestrates the process of converting building points to polygons.
        """
        self.spatial_reference_system = arcpy.SpatialReference(
            environment_setup.project_spatial_reference
        )
        self.origin_id_field = self.generate_unique_field_name(
            self.input_building_points, "match_id"
        )

        self.create_output_feature_class_if_not_exists()

        # Preparing data for processing
        input_data_array = arcpy.da.FeatureClassToNumPyArray(
            self.input_building_points,
            ["SHAPE@X", "SHAPE@Y", self.index_field_name, self.symbol_field_name],
        )
        data_to_be_processed = [
            (
                index,
                row["SHAPE@X"],
                row["SHAPE@Y"],
                row[self.index_field_name],
                row[self.symbol_field_name],
            )
            for index, row in enumerate(input_data_array)
        ]

        # Parallel processing setup
        number_of_cores = int(cpu_count() * self.PERCENTAGE_OF_CPU_CORES)
        with Pool(processes=number_of_cores) as processing_pool:
            well_known_text_data = processing_pool.map(
                self.calculate_well_known_text_polygon, data_to_be_processed
            )

        # Processing data in batches
        self.process_data_in_batches(well_known_text_data)
        arcpy.Delete_management(
            f"{self.IN_MEMORY_WORKSPACE}/{self.TEMPORARY_FEATURE_CLASS_NAME}"
        )

        print("starting adding fields with join")

        # Adding fields with join
        self.add_fields_with_join()

        # Delete the origin_id_field
        self.delete_origin_id_field()

        print(f"Output feature class: {self.output_polygon_feature_class} completed.")


if __name__ == "__main__":
    # Example parameters - replace these with actual values suitable for your test
    input_building_points = (
        Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
    )
    output_polygon_feature_class = (
        Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value
    )
    building_symbol_dimensions = {
        1: (145, 145),
        2: (145, 145),
        3: (195, 145),
        4: (40, 40),
        5: (80, 80),
        6: (30, 30),
        7: (45, 45),
        8: (45, 45),
        9: (53, 45),
    }
    symbol_field_name = "symbol_val"
    index_field_name = "OBJECTID"

    polygon_processor = PolygonProcessor(
        input_building_points,
        output_polygon_feature_class,
        building_symbol_dimensions,
        symbol_field_name,
        index_field_name,
    )
    polygon_processor.run()
