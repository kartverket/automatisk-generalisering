import numpy as np
import arcpy
import os
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

from env_setup import environment_setup
from file_manager.n100.file_manager_buildings import Building_N100


def setup_arcpy_environment():
    """
    Sets up the ArcPy environment based on predefined settings.
    """
    environment_setup.main()


def calculate_well_known_text_polygon(arguments):
    """
    Generates the Well-Known Text (WKT) representation of a polygon based on input arguments.
    Args:
        arguments (tuple): A tuple containing index, x-coordinate, y-coordinate, object ID, and symbol type.
    Returns:
        tuple: A tuple containing the object ID and its corresponding WKT polygon.
    """
    index, x_coordinate, y_coordinate, object_id, symbol_type = arguments
    polygon_width, polygon_height = building_symbol_dimensions[symbol_type]
    half_width = polygon_width / 2
    half_height = polygon_height / 2
    x_offsets = np.array([-half_width, half_width, half_width, -half_width])
    y_offsets = np.array([-half_height, -half_height, half_height, half_height])
    corner_x_values = x_coordinate + x_offsets
    corner_y_values = y_coordinate + y_offsets
    polygon_corners = list(zip(corner_x_values, corner_y_values))
    polygon_corners.append(polygon_corners[0])  # Close the polygon
    return object_id, convert_corners_to_wkt(polygon_corners)


def convert_corners_to_wkt(polygon_corners):
    """
    Converts a list of polygon corner coordinates to a Well-Known Text (WKT) string.
    Args:
        polygon_corners (list): A list of tuples representing the coordinates of the polygon corners.
    Returns:
        str: The WKT representation of the polygon.
    """
    coordinate_strings = ", ".join(f"{x} {y}" for x, y in polygon_corners)
    return f"POLYGON (({coordinate_strings}))"


def process_data_in_batches(well_known_text_data, spatial_reference, output_path):
    """
    Processes data in batches and appends the results to the output feature class.
    Args:
        well_known_text_data (list): A list of tuples containing object IDs and their WKT polygons.
        spatial_reference (SpatialReference): The spatial reference for the output feature class.
        output_path (str): Path for the output feature class.
    """
    temporary_feature_class = f"{IN_MEMORY_WORKSPACE}/{TEMPORARY_FEATURE_CLASS_NAME}"
    arcpy.CreateFeatureclass_management(
        IN_MEMORY_WORKSPACE,
        TEMPORARY_FEATURE_CLASS_NAME,
        "POLYGON",
        spatial_reference=spatial_reference,
    )
    arcpy.AddField_management(temporary_feature_class, "origin_id", "LONG")

    total_rows = len(well_known_text_data)
    batch_size = int(total_rows * BATCH_PERCENTAGE)
    subset_size = len(well_known_text_data) // NUMBER_OF_SUBSETS

    for subset_index in range(NUMBER_OF_SUBSETS):
        start_index = subset_index * subset_size
        end_index = (
            start_index + subset_size
            if subset_index < NUMBER_OF_SUBSETS - 1
            else len(well_known_text_data)
        )
        subset_data = well_known_text_data[start_index:end_index]

        for batch_start in tqdm(range(0, len(subset_data), batch_size)):
            batch_end = min(batch_start + batch_size, len(subset_data))
            batch = subset_data[batch_start:batch_end]
            with arcpy.da.InsertCursor(
                temporary_feature_class, ["origin_id", "SHAPE@"]
            ) as cursor:
                for object_id, wkt in batch:
                    polygon = arcpy.FromWKT(wkt, spatial_reference)
                    cursor.insertRow([object_id, polygon])

        arcpy.Append_management(temporary_feature_class, output_path, "NO_TEST")
        arcpy.DeleteRows_management(temporary_feature_class)


def create_output_feature_class_if_not_exists(output_path, spatial_reference):
    """
    Creates an output feature class if it does not already exist.
    Args:
        output_path (str): The path where the output feature class will be created.
        spatial_reference (SpatialReference): The spatial reference to be used for the feature class.
    """
    if not arcpy.Exists(output_path):
        output_workspace, output_class_name = os.path.split(output_path)
        arcpy.CreateFeatureclass_management(
            output_workspace,
            output_class_name,
            "POLYGON",
            spatial_reference=spatial_reference,
        )
        arcpy.management.AddField(
            in_table=output_path,
            field_name="origin_id",
            field_type="LONG",
        )


def add_fields_with_join():
    arcpy.management.JoinField(
        in_data=output_polygon_feature_class,
        in_field="origin_id",
        join_table=input_building_points,
        join_field="OBJECTID",
    )


def main():
    """
    Main function to execute the process of converting building points to polygons.
    IMPORTANT: Make sure that this function is called in an if __name__ == "__main__": block.
    Due to parallel processing this deos not work when called without the if __name__ == "__main__": block.
    """
    setup_arcpy_environment()
    create_output_feature_class_if_not_exists(
        output_polygon_feature_class, spatial_reference_system
    )

    input_data_array = arcpy.da.FeatureClassToNumPyArray(
        input_building_points, ["SHAPE@X", "SHAPE@Y", "OBJECTID", "symbol_val"]
    )
    data_to_be_processed = [
        (index, row["SHAPE@X"], row["SHAPE@Y"], row["OBJECTID"], row["symbol_val"])
        for index, row in enumerate(input_data_array)
    ]

    number_of_cores = int(cpu_count() * PERCENTAGE_OF_CPU_CORES)
    with Pool(processes=number_of_cores) as processing_pool:
        well_known_text_data = processing_pool.map(
            calculate_well_known_text_polygon, data_to_be_processed
        )

    process_data_in_batches(
        well_known_text_data, spatial_reference_system, output_polygon_feature_class
    )
    print(f"Output feature class: {output_polygon_feature_class} completed.")
    add_fields_with_join()


# Constants and configurations
IN_MEMORY_WORKSPACE = "in_memory"
TEMPORARY_FEATURE_CLASS_NAME = "temporary_polygon_feature_class"
BATCH_PERCENTAGE = 0.02
NUMBER_OF_SUBSETS = 5
PERCENTAGE_OF_CPU_CORES = 1.0

# Input and output paths
input_building_points = (
    Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value
)
output_polygon_feature_class = (
    Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value
)
spatial_reference_system = arcpy.SpatialReference(25833)

# Define polygon dimensions for each building symbol type
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

if __name__ == "__main__":
    main()
