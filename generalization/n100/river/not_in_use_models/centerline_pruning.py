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

    # Load the network and the connection nodes
    G = load_network_from_features(centerline_feature)
    connection_nodes = load_start_nodes(connection_node_feature)

    # Compute the heuristic Steiner Tree
    steiner_tree = heuristic_steiner_tree(G, connection_nodes)

    # Save the pruned network
    print("Saving pruned network...")
    save_pruned_network(steiner_tree, pruned_centerline_output, G)


def setup_arcpy_environment():
    environment_setup.main()

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


def heuristic_steiner_tree(G, terminal_nodes):
    # G is the full graph, terminal_nodes are the nodes that must be connected (red points in your case)
    # Create a graph that includes only the terminal nodes and the lines that directly connect them
    steiner_tree = nx.Graph()

    # Add all terminal nodes to the Steiner Tree
    for node in terminal_nodes:
        steiner_tree.add_node(node)

    # Find all shortest paths between pairs of terminal nodes and add them to the Steiner Tree
    for node1 in terminal_nodes:
        for node2 in terminal_nodes:
            if node1 != node2 and not steiner_tree.has_edge(node1, node2):
                # Find the shortest path in the original graph
                path = nx.shortest_path(G, source=node1, target=node2)
                # Add the edges of this path to the Steiner Tree
                nx.add_path(steiner_tree, path)

    # Now remove edges that are not necessary to maintain connectivity between terminal nodes
    edges_to_remove = []
    for u, v in steiner_tree.edges():
        steiner_tree.remove_edge(u, v)
        if not nx.is_connected(steiner_tree.subgraph(terminal_nodes)):
            # If removing this edge disconnects any two terminal nodes, we must keep it
            steiner_tree.add_edge(u, v)
        else:
            # Otherwise, this edge is redundant and can be removed
            edges_to_remove.append((u, v))
    steiner_tree.remove_edges_from(edges_to_remove)

    return steiner_tree


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
