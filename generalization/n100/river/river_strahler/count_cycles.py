import geopandas as gpd
from shapely.geometry import LineString
import networkx as nx
import matplotlib.pyplot as plt
import config

river_height_path = config.output_folder + r"\river_basin_combined_3D.shp"

river_height_df = gpd.read_file(river_height_path)

data = river_height_df["geometry"]
to_be_flipped_df = gpd.GeoDataFrame({
    "geometry": data,
})

def extract_start_end_coords(line):
    coords = list(line.coords)
    start = tuple(coords[0])
    end = tuple(coords[-1])
    return start, end

G = nx.Graph()

for idx, row in to_be_flipped_df.iterrows():
    start, end = extract_start_end_coords(row.geometry)
    G.add_edge(start, end, index=idx)

def count_edges_in_cycles(G):
    cycles = nx.cycle_basis(G)
    edges_in_cycles = set()
    for cycle in cycles:
        cycle_edges = list(zip(cycle, cycle[1:] + [cycle[0]]))
        edges_in_cycles.update(cycle_edges)
    return len(edges_in_cycles), edges_in_cycles

num_edges_in_cycles, edges_in_cycles = count_edges_in_cycles(G)
total_edges = len(G.edges)

print(f"Number of edges in cycles: {num_edges_in_cycles}")
print(f"Total edges: {total_edges}")
print(f"Percentage of edges in cycles: {100 * num_edges_in_cycles / total_edges:.2f}%")


def display_graph_with_cycles(G, edges_in_cycles):
    pos = {node: node[:2] for node in G.nodes}
    edge_colors = ['red' if edge in edges_in_cycles or (edge[1], edge[0]) in edges_in_cycles else 'black' for edge in G.edges]
    nx.draw(G, pos, with_labels=True, node_size=50, font_size=3, edge_color=edge_colors)
    plt.show()

display_graph_with_cycles(G, edges_in_cycles)