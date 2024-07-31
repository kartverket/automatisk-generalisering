"""
This script extracts height data for river points, reconstructs 3D river lines, and saves the new 3D lines to a shapefile.
"""
import arcpy
import geopandas as gpd
from shapely.geometry import Point, LineString
import config

raster_path = config.raster_path
output_fc = config.output_folder + r"\river_basin_combined.shp"
output_points_fc = config.output_folder + r"\river_points.shp"
height_points_fc = config.output_folder + r"\height_points.shp"
updated_lines_fc = config.output_folder + r"\river_basin_combined_3D.shp"

arcpy.FeatureVerticesToPoints_management(output_fc, output_points_fc, "BOTH_ENDS") # ALL BOTH_ENDS

# Extract height values to points
arcpy.sa.ExtractValuesToPoints(output_points_fc, raster_path, height_points_fc, interpolate_values="NONE", add_attributes="VALUE_ONLY")

height_gdf = gpd.read_file(height_points_fc)

# Function to reconstruct lines with z-coordinates
def create_3d_lines(df):
    grouped = df.groupby("ORIG_FID")
    lines = []

    for name, group in grouped:
        points = [Point(xy) for xy in zip(group.geometry.x, group.geometry.y, group["RASTERVALU"])]
        lines.append(LineString(points))
    
    return gpd.GeoDataFrame(geometry=lines, crs=df.crs)

lines_gdf = create_3d_lines(height_gdf)

lines_gdf.to_file(updated_lines_fc)

print(f"New 3D lines feature class created: {updated_lines_fc}")