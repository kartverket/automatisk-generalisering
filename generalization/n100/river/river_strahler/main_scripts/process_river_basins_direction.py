"""
This script processes river network data to correct the direction of river segments.
It reads river and basin data, extracts elevation information, constructs 3D river 
networks, identifies and corrects flow direction errors, and outputs the corrected 
river segments to a shapefile.

Instructions:
1. Configure the input paths and parameters in the 'config' module:
   - n50_path: Path to the geodatabase containing river network data.
   - drainage_basin_path: Path to the shapefile or geodatabase containing drainage basin data.
   - output_folder: Directory where output shapefiles will be saved.
   - raster_path: Path to the raster file used for extracting elevation data.

2. Set the 'basin_list' variable to include the names of drainage basins to process. You can use the get_all_basins() function
to get a list of all possible basins in the feature class.
"""
import arcpy
import geopandas as gpd
from shapely.geometry import Point, LineString
import networkx as nx
import config
import re

def main():
    gdb_path = config.n50_path
    drainage_basin_path = config.drainage_basin_path
    output_folder = config.output_folder
    raster_path = config.raster_path
    basin_list = ["VEGÅRSVASSDRAGET"] 

    all_flipped_paths = []
    total_flipped_segments = 0
    total_segments = 0
    total_basins = len(basin_list)

    for i, basin in enumerate(basin_list):
        print(f"Processing basin {i + 1}/{total_basins}: {basin}")
        output_fc = join_river_and_basin(basin, gdb_path, drainage_basin_path, output_folder)
        if output_fc is None:
            print(f"Skipping basin {basin} due to previous errors.")
            continue
        updated_lines_fc, intermediate_files = extract_height_and_reconstruct_3d_lines(output_fc, raster_path)
        flipped_fc, num_flipped_segments, num_segments = build_network_and_flip_lines(updated_lines_fc, output_fc, output_folder)
        if flipped_fc:
            all_flipped_paths.append(flipped_fc)
        total_flipped_segments += num_flipped_segments
        total_segments += num_segments

    if all_flipped_paths:
        arcpy.Merge_management(all_flipped_paths, f"{output_folder}\\final_flipped_rivers.shp")
    else:
        print("No basins required flipping. No merged shapefile created.")

def sanitize_filename(name):
    """Sanitizes a filename by replacing invalid characters with underscores."""
    return re.sub(r'[^a-zA-Z0-9_ØÆÅæøå]', '_', name)

def sanitize_query_string(value):
    """Sanitizes a query string by doubling single quotes."""
    return value.replace("'", "''")

def join_river_and_basin(basin, gdb_path, drainage_basin_path, output_folder):
    """
    Joins river and basin data for a specified basin, and saves the result to a shapefile.

    Parameters:
    basin (str): Name of the drainage basin.
    gdb_path (str): Path to the geodatabase containing river data.
    drainage_basin_path (str): Path to the shapefile or geodatabase containing basin data.
    output_folder (str): Directory where the output shapefile will be saved.

    Returns:
    str: Path to the output shapefile containing the joined river and basin data.
    """
    shp_path = drainage_basin_path

    arcpy.env.workspace = gdb_path

    rivers_fc = "ElvBekk"
    basins_fc = shp_path  

    sanitized_basin = sanitize_filename(basin)
    output_fc = f"{output_folder}\\river_basin_combined_{sanitized_basin}.shp"

    if arcpy.Exists("rivers_layer"):
        arcpy.management.Delete("rivers_layer")
    if arcpy.Exists("basins_layer"):
        arcpy.management.Delete("basins_layer")

    arcpy.MakeFeatureLayer_management(rivers_fc, "rivers_layer")
    arcpy.MakeFeatureLayer_management(basins_fc, "basins_layer")

    sanitized_basin_value = sanitize_query_string(basin)
    basin_query = f"nedborfelt = '{sanitized_basin_value}'"

    print(f"Executing query: {basin_query}")

    try:
        arcpy.SelectLayerByAttribute_management("basins_layer", "NEW_SELECTION", basin_query)
    except Exception as e:
        print(f"Error selecting basin with query: {basin_query}")
        print(e)
        return None

    arcpy.SelectLayerByLocation_management("rivers_layer", "INTERSECT", "basins_layer")
    arcpy.CopyFeatures_management("rivers_layer", output_fc)
    print(f"Rivers within the specified basin saved to: {output_fc}")

    arcpy.management.Delete("rivers_layer")
    arcpy.management.Delete("basins_layer")
    
    return output_fc

def extract_height_and_reconstruct_3d_lines(output_fc, raster_path):
    """
    Extracts elevation data for river segments and reconstructs 3D river lines.

    Parameters:
    output_fc (str): Path to the output feature class containing river data.
    raster_path (str): Path to the raster file used for extracting elevation data.

    Returns:
    tuple: Paths to the updated 3D lines feature class and intermediate files.
    """
    output_points_fc = output_fc.replace(".shp", "_points.shp")
    height_points_fc = output_fc.replace(".shp", "_height_points.shp")
    updated_lines_fc = output_fc.replace(".shp", "_3D.shp")

    arcpy.FeatureVerticesToPoints_management(output_fc, output_points_fc, "BOTH_ENDS")
    arcpy.sa.ExtractValuesToPoints(output_points_fc, raster_path, height_points_fc, interpolate_values="NONE", add_attributes="VALUE_ONLY")

    height_gdf = gpd.read_file(height_points_fc)

    def create_3d_lines(df):
        """
        Creates 3D line geometries from point elevation data.

        Parameters:
        df (GeoDataFrame): DataFrame containing point geometries with elevation data.

        Returns:
        GeoDataFrame: DataFrame containing 3D line geometries.
        """
        grouped = df.groupby("ORIG_FID")
        lines = []

        for name, group in grouped:
            points = [Point(xy) for xy in zip(group.geometry.x, group.geometry.y, group["RASTERVALU"])]
            lines.append(LineString(points))
        
        return gpd.GeoDataFrame(geometry=lines, crs=df.crs)

    lines_gdf = create_3d_lines(height_gdf)
    lines_gdf.to_file(updated_lines_fc)
    print(f"New 3D lines feature class created: {updated_lines_fc}")
    
    return updated_lines_fc, [output_points_fc, height_points_fc]

def build_network_and_flip_lines(updated_lines_fc, original_fc, output_folder):
    """
    Builds a 3D river network, identifies and flips incorrectly oriented river segments.

    Parameters:
    updated_lines_fc (str): Path to the updated 3D lines feature class.
    original_fc (str): Path to the original feature class containing river data.
    output_folder (str): Directory where the output shapefile will be saved.

    Returns:
    tuple: Path to the flipped river basin shapefile, number of flipped segments, and total number of segments.
    """
    flipped_river_basin_path = original_fc.replace(".shp", "_flipped.shp")

    river_height_df = gpd.read_file(updated_lines_fc)

    def extract_start_end_coords_with_z(line):
        """Extracts start and end coordinates with elevation (z-value) from a line."""
        coords = list(line.coords)
        start = tuple(coords[0])
        end = tuple(coords[-1])
        return start, end

    G_3d = nx.Graph()

    for idx, row in river_height_df.iterrows():
        start, end = extract_start_end_coords_with_z(row.geometry)
        G_3d.add_edge(start, end, index=idx, z_value=max(start[2], end[2]))

    starting_node = None
    min_z = float('inf')

    for node in G_3d.nodes:
        z_value = node[2]
        degree = G_3d.degree(node)
        if degree == 1 and z_value < min_z:
            min_z = z_value
            starting_node = node

    if not starting_node:
        raise ValueError("Could not find a valid starting node.")

    def find_and_remove_cycles(G):
        """Finds and removes cycles in the graph, returning removed edges."""
        removed_edges = []
        while True:
            try:
                cycle = nx.find_cycle(G)
                max_z_edge = max(cycle, key=lambda edge: G.get_edge_data(*edge)['z_value'])
                G.remove_edge(*max_z_edge)
                removed_edges.append(max_z_edge)
            except nx.NetworkXNoCycle:
                break
        return removed_edges

    removed_edges = find_and_remove_cycles(G_3d)

    river_df = gpd.read_file(original_fc)
    original_fids = river_df.index
    data = river_df["geometry"]
    flipped_val = [0] * len(data)
    to_be_flipped_df = gpd.GeoDataFrame({
        "geometry": data,
        "flipped": flipped_val,
        "original_fid": original_fids
    })

    def extract_start_end_coords(line):
        """Extracts start and end coordinates from a line segment."""
        coords = list(line.coords)
        start = tuple(coords[0][:2])
        end = tuple(coords[-1][:2])
        return start, end

    G = nx.Graph()

    for idx, row in to_be_flipped_df.iterrows():
        start, end = extract_start_end_coords(row.geometry)
        G.add_edge(start, end, index=idx)

    starting_node_2d = (starting_node[0], starting_node[1])

    def dfs_check_flip(G, start_node, to_be_flipped_df):
        """Performs DFS to check and mark segments that need to be flipped."""
        stack = [start_node]
        visited = set()
        visited_edges = set()

        while stack:
            current_node = stack.pop()
            
            if current_node in visited:
                continue

            visited.add(current_node)
            
            for neighbor in G.neighbors(current_node):
                edge_data = G.get_edge_data(current_node, neighbor)
                segment_index = edge_data['index']
                if segment_index in visited_edges:
                    continue

                visited_edges.add(segment_index)
                start, end = extract_start_end_coords(to_be_flipped_df.at[segment_index, 'geometry'])
                
                if (current_node == end) and (neighbor == start):
                    to_be_flipped_df.at[segment_index, 'flipped'] = 0
                elif (current_node == start) and (neighbor == end):
                    to_be_flipped_df.at[segment_index, 'flipped'] = 1
                
                stack.append(neighbor)

    dfs_check_flip(G, starting_node_2d, to_be_flipped_df)

    num_segments = len(to_be_flipped_df)
    num_flipped_segments = to_be_flipped_df['flipped'].sum()

    segments_to_flip = to_be_flipped_df[to_be_flipped_df['flipped'] == 1]

    arcpy.env.workspace = output_folder
    arcpy.env.overwriteOutput = True
    arcpy.management.CopyFeatures(original_fc, flipped_river_basin_path)
    arcpy.management.MakeFeatureLayer(flipped_river_basin_path, "river_basin_layer")

    for idx, row in segments_to_flip.iterrows():
        original_fid = row['original_fid']
        arcpy.management.SelectLayerByAttribute("river_basin_layer", "NEW_SELECTION", f"\"FID\" = {original_fid}")
        arcpy.edit.FlipLine("river_basin_layer")

    arcpy.management.Delete("river_basin_layer")
    print("Saved updated shapefile to:", flipped_river_basin_path)

    # Reintroduce removed edges
    for edge in removed_edges:
        G_3d.add_edge(*edge)

    return flipped_river_basin_path, num_flipped_segments, num_segments

def get_all_basins(feature_class, column_name, gdb_path):
    arcpy.env.workspace = gdb_path
    unique_values = set()
    with arcpy.da.SearchCursor(feature_class, [column_name]) as cursor:
        for row in cursor:
            unique_values.add(row[0])

    return list(unique_values)

if __name__ == "__main__":
    main()
