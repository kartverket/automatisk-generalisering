import arcpy
import networkx as nx
import os
from itertools import combinations
import math

from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    setup_arcpy_environment()
    print("Pruning centerline...")
    G = load_network_from_features(centerline_feature)
    start_nodes = load_start_nodes(connection_node_feature)

    # Find all shortest paths between start nodes in the original network
    paths_graph = find_shortest_paths(G, start_nodes)

    # Compute the MST of the graph that includes all shortest paths
    mst = compute_mst(paths_graph)

    # Prune the MST to remove unnecessary edges
    pruned_mst = prune_mst(mst, start_nodes)
    print("Saving pruned network...")
    save_pruned_network(pruned_mst, pruned_centerline_output, G)


def setup_arcpy_environment():
    environment_setup.general_setup()

    arcpy.management.CopyFeatures(
        in_features=River_N100.river_centerline__study_centerline__n100.value,
        out_feature_class=f"{River_N100.river_centerline__study_centerline__n100.value}_copy",
    )


lake_feature = River_N100.river_centerline__study_lake__n100.value
centerline_feature = f"{River_N100.river_centerline__study_centerline__n100.value}_copy"
river_feature = River_N100.river_centerline__study_rivers__n100.value
connection_node_feature = River_N100.river_centerline__study_dangles__n100.value
pruned_centerline_output = River_N100.centerline_pruning__pruned_centerline__n100.value


def load_network_from_features(centerline_feature):
    G = nx.Graph()
    with arcpy.da.SearchCursor(centerline_feature, ["SHAPE@"]) as cursor:
        for row in cursor:
            polyline = row[0]
            for part in polyline:
                for i in range(len(part) - 1):
                    start_point = part[i]
                    end_point = part[i + 1]
                    # Set the 'pos' attribute for each node
                    G.add_node(
                        (start_point.X, start_point.Y),
                        pos=(start_point.X, start_point.Y),
                    )
                    G.add_node(
                        (end_point.X, end_point.Y), pos=(end_point.X, end_point.Y)
                    )
                    # Calculate the distance between points as the weight
                    weight = math.hypot(
                        end_point.X - start_point.X, end_point.Y - start_point.Y
                    )
                    G.add_edge(
                        (start_point.X, start_point.Y),
                        (end_point.X, end_point.Y),
                        weight=weight,
                    )
    return G


def load_start_nodes(connection_node_feature):
    # Load the connection nodes from the feature class
    start_nodes = []
    with arcpy.da.SearchCursor(connection_node_feature, ["SHAPE@"]) as cursor:
        for row in cursor:
            point = row[0].firstPoint
            start_nodes.append((point.X, point.Y))
    return start_nodes


def find_shortest_paths(G, start_nodes):
    # Create a new graph to hold all shortest paths
    paths_graph = nx.Graph()

    # Find all shortest paths between start nodes
    for node1, node2 in combinations(start_nodes, 2):
        if nx.has_path(G, node1, node2):
            path = nx.shortest_path(G, source=node1, target=node2)
            nx.add_path(paths_graph, path)

    return paths_graph


def compute_mst(H):
    # Compute the MST of the graph with all shortest paths
    return nx.minimum_spanning_tree(H)


def prune_mst(mst, start_nodes):
    # Convert start_nodes to a set for faster lookup
    start_nodes_set = set(start_nodes)
    # Copy MST to avoid modifying it while iterating
    pruned_mst = mst.copy()
    # Remove leaf nodes that are not in start_nodes
    for node in list(pruned_mst.nodes):  # List to make a copy of nodes for iteration
        if node not in start_nodes_set and pruned_mst.degree(node) == 1:
            pruned_mst.remove_node(node)
    return pruned_mst


def prune_network_with_mst(G, start_nodes):
    # Create a complete graph for the start nodes
    complete_graph = nx.complete_graph(start_nodes)

    # Initialize H as an empty graph
    H = nx.Graph()

    # For each edge in the complete graph, check if there is a path in G
    for u, v in complete_graph.edges():
        if u != v and nx.has_path(G, u, v):
            # If a path exists, find the shortest path and add all its edges to H
            path = nx.shortest_path(G, source=u, target=v)
            # Get the positions to calculate the weight
            positions = nx.get_node_attributes(G, "pos")
            for i in range(len(path) - 1):
                # Calculate the weight as the Euclidean distance between points
                weight = math.hypot(
                    positions[path[i + 1]][0] - positions[path[i]][0],
                    positions[path[i + 1]][1] - positions[path[i]][1],
                )
                H.add_edge(path[i], path[i + 1], weight=weight)

    # Now H is a graph where all start nodes are connected if a path exists in G
    # Find the Minimum Spanning Tree of this new graph
    mst = nx.minimum_spanning_tree(H, weight="weight")
    return mst


def save_pruned_network(pruned_network, pruned_centerline_output, G):
    # Ensure the workspace is set to the geodatabase directory
    arcpy.env.workspace = os.path.dirname(pruned_centerline_output)

    # Get the spatial reference from the input centerline feature
    sr = arcpy.Describe(centerline_feature).spatialReference

    # Check if the output feature class already exists; if so, delete it
    if arcpy.Exists(pruned_centerline_output):
        arcpy.Delete_management(pruned_centerline_output)

    # Create a new feature class for the pruned centerline output
    arcpy.CreateFeatureclass_management(
        out_path=os.path.dirname(pruned_centerline_output),
        out_name=os.path.basename(pruned_centerline_output),
        geometry_type="POLYLINE",
        spatial_reference=sr,
    )
    print(f"Created feature class at {pruned_centerline_output}")

    # Insert the pruned edges into the new feature class
    with arcpy.da.InsertCursor(pruned_centerline_output, ["SHAPE@"]) as cursor:
        for u, v in pruned_network.edges():
            # Retrieve the path as a list of points from the original graph G
            path = nx.shortest_path(G, source=u, target=v)
            points = [
                arcpy.Point(G.nodes[p]["pos"][0], G.nodes[p]["pos"][1]) for p in path
            ]
            # Create a polyline from the ordered list of points
            line = arcpy.Polyline(arcpy.Array(points), sr)
            cursor.insertRow([line])


if __name__ == "__main__":
    main()
