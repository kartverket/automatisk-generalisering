import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import config


def load_shapefile(shapefile_path):
    """
    Load a shapefile and return a GeoDataFrame.

    Parameters:
    shapefile_path (str): Path to the shapefile.

    Returns:
    gpd.GeoDataFrame: The loaded GeoDataFrame.
    """
    return gpd.read_file(shapefile_path)


def create_network(gdf):
    """
    Create a network from a GeoDataFrame of line segments.

    Parameters:
    gdf (gpd.GeoDataFrame): GeoDataFrame containing line segments.

    Returns:
    nx.Graph: The created network.
    """
    G = nx.Graph()

    for idx, row in gdf.iterrows():
        line = row.geometry
        start = (line.coords[0][0], line.coords[0][1])
        end = (line.coords[-1][0], line.coords[-1][1])
        G.add_edge(start, end, index=idx)

    return G


def find_and_display_cycles(G):
    """
    Find and display cycles in the network.

    Parameters:
    G (nx.Graph): The network graph.
    """
    cycles = list(nx.cycle_basis(G))
    cycle_edges = set()

    for cycle in cycles:
        for i in range(len(cycle)):
            edge = (cycle[i], cycle[(i + 1) % len(cycle)])
            if G.has_edge(*edge):
                cycle_edges.add((cycle[i], cycle[(i + 1) % len(cycle)]))

    pos = {node: node for node in G.nodes}

    plt.figure(figsize=(10, 10))
    nx.draw(
        G, pos, node_color="blue", edge_color="black", with_labels=False, node_size=10
    )
    nx.draw_networkx_edges(G, pos, edgelist=cycle_edges, edge_color="red", width=2)

    plt.title("Network with Cycles Highlighted")
    plt.show()


if __name__ == "__main__":
    shapefile_path = config.output_folder + r"\final_flipped_rivers_old.shp"
    gdf = load_shapefile(shapefile_path)
    G = create_network(gdf)
    find_and_display_cycles(G)
