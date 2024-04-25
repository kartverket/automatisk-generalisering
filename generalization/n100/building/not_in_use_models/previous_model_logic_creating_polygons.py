import arcpy
import os
from tqdm import tqdm
import time
from file_manager.n100.file_manager_buildings import Building_N100

start_time = time.time()

# Define input and output paths
input_buildings = (
    Building_N100.calculate_point_values___points_pre_resolve_building_conflicts___n100_building.value
)
out_feature_path = f"{Building_N100.building_point_buffer_displacement__iteration_points_to_square_polygons__n100.value}_2"

# Define sizes for each symbol_val as (width, height)
symbol_sizes = {
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

# Get spatial reference from input feature class
spatial_ref = arcpy.Describe(input_buildings).spatialReference

# Create the output feature class
arcpy.CreateFeatureclass_management(
    os.path.dirname(out_feature_path),
    os.path.basename(out_feature_path),
    "POLYGON",
    spatial_reference=spatial_ref,
)
arcpy.AddField_management(out_feature_path, "ID", "Long")
arcpy.AddField_management(
    out_feature_path, "symbol_val", "Long"
)  # To store the symbol value

# Insert cursor for the output feature class
insert_cursor = arcpy.da.InsertCursor(out_feature_path, ["ID", "symbol_val", "SHAPE@"])

# Get the total number of rows for progress tracking
total_rows = int(arcpy.GetCount_management(input_buildings)[0])

# Search cursor for the input feature class
# Search cursor for the input feature class with tqdm for progress
with arcpy.da.SearchCursor(
    input_buildings, ["SHAPE@XY", "OBJECTID", "symbol_val"]
) as cursor:
    for row in tqdm(cursor, total=total_rows, desc="Processing"):
        x, y = row[0]
        object_id = row[1]
        symbol_val = row[2]

        # Get size for the current symbol
        size_x, size_y = symbol_sizes.get(
            symbol_val, (40, 40)
        )  # Default size if symbol_val not found

        # Create polygon coordinates
        coords = [
            arcpy.Point(x - size_x / 2, y - size_y / 2),
            arcpy.Point(x - size_x / 2, y + size_y / 2),
            arcpy.Point(x + size_x / 2, y + size_y / 2),
            arcpy.Point(x + size_x / 2, y - size_y / 2),
            arcpy.Point(x - size_x / 2, y - size_y / 2),  # Close the polygon
        ]

        # Create a polygon object
        polygon = arcpy.Polygon(arcpy.Array(coords), spatial_ref)

        # Insert new row
        insert_cursor.insertRow((object_id, symbol_val, polygon))

# Clean up
del insert_cursor

end_time = time.time()
elapsed_time = end_time - start_time
time_str = "{:02} hours, {:02} minutes, {:.2f} seconds".format(
    int(divmod(elapsed_time, 3600)[0]),
    int(divmod(divmod(elapsed_time, 3600)[1], 60)[0]),
    divmod(divmod(elapsed_time, 3600)[1], 60)[1],
)
print(f"create_and_process_squares took {time_str} to complete.")
