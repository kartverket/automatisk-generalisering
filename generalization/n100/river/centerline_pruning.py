import arcpy
import networkx as nx
import os

from shapely.geometry import Point
from shapely.ops import nearest_points


from env_setup import environment_setup
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    setup_arcpy_environment()
    G = load_network_from_features(centerline_feature)
    start_nodes = load_start_nodes(connection_node_feature)
    pruned_network = prune_network_with_mst(G, start_nodes)
    save_pruned_network(pruned_network, pruned_centerline_output)


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
                # Make sure you're getting the points correctly
                for i in range(len(part) - 1):
                    start_point = part[i]
                    end_point = part[i + 1]
                    G.add_edge(
                        (start_point.X, start_point.Y), (end_point.X, end_point.Y)
                    )
                    # Print diagnostic information to ensure nodes are added

    return G


def load_start_nodes(connection_node_feature):
    # Load the connection nodes from the feature class
    start_nodes = []
    with arcpy.da.SearchCursor(connection_node_feature, ["SHAPE@"]) as cursor:
        for row in cursor:
            point = row[0].firstPoint
            start_nodes.append((point.X, point.Y))
    return start_nodes


tolerance = 0.1  # Adjust the tolerance value as needed


def prune_network_with_mst(G, start_nodes):
    # Create a complete graph for the start nodes
    complete_graph = nx.complete_graph(start_nodes)

    # Initialize H as an empty graph
    H = nx.Graph()

    # For each edge in the complete graph, check if there is a path in G
    for u, v in complete_graph.edges():
        if u != v:
            # Check if there is a direct path in G or a path through intermediary nodes
            if nx.has_path(G, u, v):
                # If a path exists, find the shortest path and add all its edges to H
                path = nx.shortest_path(G, source=u, target=v)
                for i in range(len(path) - 1):
                    H.add_edge(path[i], path[i + 1])

    # Now H is a graph where all start nodes are connected if a path exists in G
    # Find the Minimum Spanning Tree of this new graph
    mst = nx.minimum_spanning_tree(H)
    return mst


def save_pruned_network(pruned_network, pruned_centerline_output):
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
            # Debugging: Check if we're adding edges
            print(f"Adding edge from {u} to {v}")
            line = arcpy.Polyline(arcpy.Array([arcpy.Point(*u), arcpy.Point(*v)]), sr)
            cursor.insertRow([line])


if __name__ == "__main__":
    main()
