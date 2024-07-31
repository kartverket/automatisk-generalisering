"""
This script builds a network from the river segments and uses DFS to flip the lines in the correct order.
"""
import geopandas as gpd
from shapely.geometry import LineString
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import arcpy
import config

river_height_path = config.output_folder + r"\river_basin_combined_3D.shp"
river_basin_path = config.output_folder + r"\river_basin_combined.shp"
flipped_river_basin_path = config.output_folder + r"\flipped_river_basin_combined.shp"

river_height_df = gpd.read_file(river_height_path)

data = river_height_df["geometry"]
flipped_val = [0] * len(data)
to_be_flipped_df = gpd.GeoDataFrame({
    "geometry": data,
    "flipped": flipped_val
})

print(to_be_flipped_df.head())
print(to_be_flipped_df["geometry"].iloc[0])

def extract_start_end_coords(line):
    coords = list(line.coords)
    start = tuple(coords[0])
    end = tuple(coords[-1])
    return start, end

G = nx.Graph()

for idx, row in to_be_flipped_df.iterrows():
    start, end = extract_start_end_coords(row.geometry)
    G.add_edge(start, end, index=idx)

def display_graph():
    pos = {node: node[:2] for node in G.nodes}
    nx.draw(G, pos, with_labels=True, node_size=50, font_size=8, arrows=True)
    plt.show()

starting_node = None
min_z = float('inf')

# Finds the lowest node with only one edge = Staring node
for node in G.nodes:
    z_value = node[2]
    degree = G.degree(node)
    if degree == 1 and z_value < min_z:
        min_z = z_value
        starting_node = node

print(f'Starting node: {starting_node}')

def dfs_check_flip(G, start_node, to_be_flipped_df):
    stack = [start_node]
    visited = set()

    while stack:
        current_node = stack.pop()
        
        if current_node in visited:
            continue

        visited.add(current_node)
        
        for neighbor in G.neighbors(current_node):
            if neighbor not in visited:
                edge_data = G.get_edge_data(current_node, neighbor)
                segment_index = edge_data['index']
                start, end = extract_start_end_coords(to_be_flipped_df.at[segment_index, 'geometry'])
                
                if (current_node, neighbor) == (start, end):
                    to_be_flipped_df.at[segment_index, 'flipped'] = 1
                
                stack.append(neighbor)

dfs_check_flip(G, starting_node, to_be_flipped_df)

segments_to_flip = to_be_flipped_df[to_be_flipped_df['flipped'] == 1]

arcpy.env.workspace = config.output_folder
arcpy.env.overwriteOutput = True
arcpy.management.CopyFeatures(river_basin_path, flipped_river_basin_path)
arcpy.management.MakeFeatureLayer(flipped_river_basin_path, "river_basin_layer")

# Flip the lines that need to be flipped
for idx, row in segments_to_flip.iterrows():
    # Select the line by its FID
    arcpy.management.SelectLayerByAttribute("river_basin_layer", "NEW_SELECTION", f"\"FID\" = {idx}")
    arcpy.edit.FlipLine("river_basin_layer")

arcpy.management.Delete("river_basin_layer")
print("Saved updated shapefile to:", flipped_river_basin_path)