"""
Script to build the network of rivers that can be traversed.
"""

import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point
import config

bias = 0  # Bias for flowing "down"
height_river_path = config.output_folder + r"\river_basin_combined_3D.shp"

gdf = gpd.read_file(height_river_path)
G = nx.Graph()

# Build the network of rivers
for idx, row in gdf.iterrows():
    coords = list(row.geometry.coords)
    start = Point(coords[0])
    end = Point(coords[-1])
    start_elev = start.z
    end_elev = end.z

    G.add_node(start, pos=(start.x, start.y, start.z))
    G.add_node(end, pos=(end.x, end.y, end.z))

    G.add_edge(
        start,
        end,
        weight=abs(start_elev - end_elev),
        elevation_change=end_elev - start_elev,
    )


def correct_river_flow(G):
    """
    DFS to correct river flow direction, starting from the lowest point
    """
    visited = set()
    lowest_node = min(G.nodes, key=lambda n: G.nodes[n]["pos"][2])

    stack = [lowest_node]

    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    start_elev = G.nodes[node]["pos"][2]
                    end_elev = G.nodes[neighbor]["pos"][2]
                    if (end_elev + bias) > start_elev:
                        # If the flow is incorrect, adjust the elevation_change
                        G[node][neighbor]["elevation_change"] = (
                            end_elev + bias
                        ) - start_elev
                    stack.append(neighbor)
    return G


G = correct_river_flow(G)


def visualize_network():
    pos = {n: (data["pos"][0], data["pos"][1]) for n, data in G.nodes(data=True)}
    edge_colors = [
        "blue" if G[u][v]["elevation_change"] > 0 else "red" for u, v in G.edges
    ]
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=50,
        font_size=7,
        edge_color=edge_colors,
        edge_cmap=plt.cm.Blues,
        width=2,
    )
    plt.show()


visualize_network()
