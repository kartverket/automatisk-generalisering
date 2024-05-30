import arcpy
import networkx as nx
import os
from itertools import combinations
import math

from env_setup import environment_setup
from file_manager.n100.file_manager_rivers import River_N100


def main():
    environment_setup.main()
    copy_input_featrues()
    print("Pruning centerline...")

    # Load the network and the connection nodes
    G = load_network_from_features(centerline_feature)
    connection_nodes = load_start_nodes(connection_node_feature)

    # Compute minimum spanning tree for collapsed network
    mst_tree = minimum_spanning_tree_for_terminals(G, connection_nodes)

    # Save the pruned network
    print("Saving pruned network...")
    save_pruned_network(mst_tree, pruned_centerline_output, G)


def copy_input_featrues():
    arcpy.management.CopyFeatures(
        in_features=River_N100.river_centerline__study_centerline__n100.value,
        out_feature_class=f"{River_N100.river_centerline__study_centerline__n100.value}_copy",
    )

    arcpy.management.CopyFeatures(
        in_features=River_N100.river_centerline__study_lake_collapsed__n100.value,
        out_feature_class=f"{River_N100.river_centerline__study_lake_collapsed__n100.value}_copy",
    )


lake_feature = River_N100.river_centerline__study_lake__n100.value
centerline_feature = (
    f"{River_N100.river_centerline__study_lake_collapsed__n100.value}_copy"
)
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


def minimum_spanning_tree_for_terminals(G, terminal_nodes):
    # Ensure all terminal nodes are in the same connected component
    connected_subgraph = max(
        (G.subgraph(c) for c in nx.connected_components(G)), key=len
    )
    connected_terminals = set(connected_subgraph.nodes()).intersection(
        set(terminal_nodes)
    )

    # Check if there are terminal nodes not in the largest connected component
    isolated_terminals = set(terminal_nodes) - connected_terminals
    if isolated_terminals:
        print(
            f"Warning: The following terminal nodes are in isolated subgraphs and cannot be connected: {isolated_terminals}"
        )
        # To handle potential nodes which can not be connected

    # Create a complete graph for the connected terminal nodes with the shortest path distance as edge weight
    complete_graph = nx.Graph()
    for u, v in combinations(
        connected_terminals, 2
    ):  # All pairs of connected terminal nodes
        try:
            distance = nx.shortest_path_length(
                connected_subgraph, source=u, target=v, weight="weight"
            )
            complete_graph.add_edge(u, v, weight=distance)
        except nx.NetworkXNoPath:
            print(f"No path between terminal nodes {u} and {v}.")
            continue

    # Calculate the MST of the complete graph
    mst = nx.minimum_spanning_tree(complete_graph, weight="weight")

    # Translate the MST back to the original graph's terms
    mst_full = nx.Graph()
    for u, v in mst.edges():
        path = nx.shortest_path(G, source=u, target=v)
        for i in range(len(path) - 1):
            mst_full.add_edge(
                path[i], path[i + 1], weight=G[path[i]][path[i + 1]]["weight"]
            )

    return mst_full


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
            # Make sure to check if the path exists before trying to retrieve it
            if nx.has_path(G, u, v):
                path = nx.shortest_path(G, source=u, target=v)
                points = [
                    arcpy.Point(G.nodes[p]["pos"][0], G.nodes[p]["pos"][1])
                    for p in path
                ]
                # Create a polyline from the ordered list of points
                line = arcpy.Polyline(arcpy.Array(points), sr)
                cursor.insertRow([line])


if __name__ == "__main__":
    main()
