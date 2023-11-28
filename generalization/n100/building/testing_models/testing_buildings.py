import numpy as np
import arcpy
import time
from tqdm import tqdm
from multiprocessing import Pool

import config
from env_setup import environment_setup
from file_manager.n100.file_manager_buildings import Building_N100

environment_setup.general_setup()


input_buildings = (
    Building_N100.table_management__bygningspunkt_pre_resolve_building_conflicts__n100.value
)
out_feature_path = (
    Building_N100.resolve_building_conflicts__transform_points_to_square_polygons__n100.value
)
out_feature_path2 = f"{Building_N100.resolve_building_conflicts__transform_points_to_square_polygons__n100.value}_2"

spatial_reference = arcpy.SpatialReference(25833)

# Define sizes for each symbol_val
symbol_sizes = {
    1: (145, 145),
    2: (145, 145),
    3: (145, 195),
    4: (40, 40),
    5: (80, 80),
    6: (30, 30),
    7: (45, 45),
    8: (45, 45),
    9: (53, 45),
}


def main():
    create_and_process_squares()


def create_and_process_squares():
    print("Overwrite output setting:", arcpy.env.overwriteOutput)
    start_time = time.time()

    # Load your points into a NumPy array
    arr = arcpy.da.FeatureClassToNumPyArray(
        input_buildings, ["SHAPE@X", "SHAPE@Y", "OBJECTID", "symbol_val"]
    )

    # Function to calculate square corners (to be used in multiprocessing)
    def calculate_square_corners(i, x, y, object_id, symbol_val):
        length, width = symbol_sizes[symbol_val]
        half_length = length / 2
        half_width = width / 2

        x_offsets = np.array([-half_length, half_length, half_length, -half_length])
        y_offsets = np.array([-half_width, -half_width, half_width, half_width])
        x_v = x + x_offsets
        y_v = y + y_offsets
        return i, list(zip(x_v, y_v)), object_id

    # Prepare data for multiprocessing
    data_for_multiprocessing = [
        (i, row["SHAPE@X"], row["SHAPE@Y"], row["OBJECTID"], row["symbol_val"])
        for i, row in enumerate(arr)
    ]

    # Calculate square corners in parallel
    with Pool() as pool:
        results = pool.starmap(calculate_square_corners, data_for_multiprocessing)

    # Sort results by the original index
    results.sort(key=lambda x: x[0])

    # Create polygons and structure the array
    data = []
    for _, corners, object_id in tqdm(results, total=len(results)):
        square_corners = [arcpy.Point(x, y) for x, y in corners]
        polygon = arcpy.Polygon(arcpy.Array(square_corners), spatial_reference)
        data.append((polygon, object_id))

    dtype = [("Shape", "O"), ("OBJECTID", "i4")]
    structured_array = np.array(data, dtype=dtype)
    arcpy.da.NumPyArrayToFeatureClass(
        structured_array, out_feature_path, ["Shape", "OBJECTID"], spatial_reference
    )

    # Timing
    end_time = time.time()
    elapsed_time = end_time - start_time
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(divmod(elapsed_time, 3600)[0]),
        int(divmod(divmod(elapsed_time, 3600)[1], 60)[0]),
        divmod(divmod(elapsed_time, 3600)[1], 60)[1],
    )
    print(f"create_and_process_squares took {time_str} to complete.")


def create_squares_method_1_old():
    print("Overwrite output setting:", arcpy.env.overwriteOutput)
    # Start timing
    start_time = time.time()

    # Load your points into a NumPy array
    arr = arcpy.da.FeatureClassToNumPyArray(
        input_buildings,
        [
            "SHAPE@X",
            "SHAPE@Y",
            "OBJECTID",
            "symbol_val",
        ],
    )

    # Now, create the polygons and structure the array
    data = []
    for i in tqdm(range(len(arr)), total=len(arr)):
        # Extract OBJECTID and symbol_val
        object_id = arr["OBJECTID"][i]
        symbol_val = arr["symbol_val"][i]

        # Determine the size of the square based on symbol_val
        length, width = symbol_sizes.get(symbol_val)
        half_length = length / 2
        half_width = width / 2

        # Calculate offsets and vertices
        x_offsets = np.array([-half_length, half_length, half_length, -half_length])
        y_offsets = np.array([-half_width, -half_width, half_width, half_width])
        x_v = arr["SHAPE@X"][i] + x_offsets
        y_v = arr["SHAPE@Y"][i] + y_offsets
        square_corners = [arcpy.Point(x, y) for x, y in zip(x_v, y_v)]

        # Create polygon
        polygon = arcpy.Polygon(arcpy.Array(square_corners), spatial_reference)

        # Append polygon and OBJECTID to data array
        data.append((polygon, object_id))

    # Define the data type for each field
    dtype = [("Shape", "O"), ("OBJECTID", "i4")]

    # Create a structured NumPy array
    structured_array = np.array(data, dtype=dtype)

    # Convert the structured array of polygons back to a feature class
    arcpy.da.NumPyArrayToFeatureClass(
        structured_array, out_feature_path, ["Shape", "OBJECTID"], spatial_reference
    )

    # End timing
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as string
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(hours), int(minutes), seconds
    )

    print(f"create_squares_method_1 took {time_str} to complete.")


def create_squares_method_2():
    # Start timing
    start_time = time.time()

    # Load your points into a NumPy array
    arr = arcpy.da.FeatureClassToNumPyArray(input_buildings, ["SHAPE@X", "SHAPE@Y"])

    # Define the square size (side length)
    square_size = 50  # Example size, adjust as needed

    # Calculate the square vertices
    vertices = np.zeros(len(arr), dtype=[("POLYGON", "O")])

    for i, point in tqdm(enumerate(arr), total=len(arr)):
        x, y = point["SHAPE@X"], point["SHAPE@Y"]
        half_d = square_size / 2

        # Calculate the corners of the square
        square_corners = [
            (x - half_d, y - half_d),
            (x + half_d, y - half_d),
            (x + half_d, y + half_d),
            (x - half_d, y + half_d),
        ]

        # Create a Polygon object for each set of vertices
        vertices[i]["POLYGON"] = arcpy.Polygon(
            arcpy.Array([arcpy.Point(*coords) for coords in square_corners])
        )

    # Convert the array of polygons back to a feature class
    arcpy.da.NumPyArrayToFeatureClass(
        vertices, out_feature_path2, "POLYGON", spatial_reference
    )

    # End timing
    end_time = time.time()

    # Calculate elapsed time
    elapsed_time = end_time - start_time

    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format as string
    time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
        int(hours), int(minutes), seconds
    )

    print(f"create_squares_method_2 took {time_str} to complete.")


main()
