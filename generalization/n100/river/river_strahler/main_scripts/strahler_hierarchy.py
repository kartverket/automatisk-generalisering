"""
This script calculates Strahler values for river segments using a directed graph approach.
It processes river data either from a shapefile or from feature classes in a geodatabase,
and outputs the Strahler values for each river segment.

Instructions:
1. Set the 'use_shapefile' variable to True or False.
   - True: The script will process the river data from the specified shapefile.
   - False: The script will process the river data from the specified geodatabase and drainage basin.

2. Set the 'use_common_ancestor' variable to True or False.
   - True: The script will use the common ancestor logic to avoid incrementing Strahler values 
     for segments that diverge and rejoin. This ensures more accurate Strahler values but increases
     the time complexity.
   - False: The script will skip the common ancestor check, resulting in faster processing but 
     potentially less accurate Strahler values in cases of divergence and rejoining.
"""
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
import arcpy
import re
import config


def main():
    n50_path = config.n50_path
    drainage_basin_path = config.drainage_basin_path
    output_folder = config.output_folder
    output_gdb = config.output_gdb

    use_shapefile = True
    use_common_ancestor = True
    shapefile_path = config.output_folder + r"\final_flipped_rivers.shp"

    if use_shapefile:
        print(f"Processing shapefile: {shapefile_path}")
        strahler_fc = build_network_and_calculate_strahler(
            shapefile_path, use_common_ancestor
        )
        convert_to_gdb(strahler_fc, output_gdb)
    else:
        basin_list = ["HERREGÅRDSBEKKEN"]

        total_basins = len(basin_list)
        for i, basin in enumerate(basin_list):
            print(f"Processing basin {i + 1}/{total_basins}: {basin}")
            output_fc = join_river_and_basin(
                n50_path, drainage_basin_path, output_folder, basin
            )
            if output_fc is None:
                print(f"Skipping basin {basin} due to previous errors.")
                continue

            strahler_fc = build_network_and_calculate_strahler(
                output_fc, use_common_ancestor
            )
            convert_to_gdb(strahler_fc, output_gdb)


def sanitize_filename(name):
    """Sanitizes a filename by replacing invalid characters with underscores."""
    return re.sub(r"[^a-zA-Z0-9_ØÆÅæøå]", "_", name)


def get_all_basins(gdb_path, feature_class, column_name):
    """
    Retrieves all unique basin names from a specified feature class.

    Parameters:
    gdb_path (str): Path to the geodatabase.
    feature_class (str): Name of the feature class containing basin data.
    column_name (str): Name of the column containing basin names.

    Returns:
    list: List of unique basin names.
    """
    arcpy.env.workspace = gdb_path
    unique_values = set()
    with arcpy.da.SearchCursor(feature_class, [column_name]) as cursor:
        for row in cursor:
            unique_values.add(row[0])
    return list(unique_values)


def join_river_and_basin(gdb_path, drainage_basin_path, output_folder, basin):
    """
    Joins river and basin data for a specified basin and saves the result to a shapefile.

    Parameters:
    gdb_path (str): Path to the geodatabase containing river data.
    drainage_basin_path (str): Path to the shapefile or geodatabase containing basin data.
    output_folder (str): Directory where the output shapefile will be saved.
    basin (str): Name of the drainage basin.

    Returns:
    str: Path to the output shapefile containing the joined river and basin data.
    """
    arcpy.env.workspace = gdb_path

    rivers_fc = "ElvBekk"
    basins_fc = drainage_basin_path

    basin = sanitize_filename(basin)

    output_fc = output_folder + f"\\river_basin_combined_{basin}.shp"

    if arcpy.Exists("rivers_layer"):
        arcpy.management.Delete("rivers_layer")
    if arcpy.Exists("basins_layer"):
        arcpy.management.Delete("basins_layer")

    arcpy.MakeFeatureLayer_management(rivers_fc, "rivers_layer")
    arcpy.MakeFeatureLayer_management(basins_fc, "basins_layer")

    basin_query = f"nedborfelt = '{basin}'"
    arcpy.SelectLayerByAttribute_management(
        "basins_layer", "NEW_SELECTION", basin_query
    )

    arcpy.SelectLayerByLocation_management("rivers_layer", "INTERSECT", "basins_layer")
    arcpy.CopyFeatures_management("rivers_layer", output_fc)
    print(f"Rivers within the specified basin saved to: {output_fc}")

    arcpy.management.Delete("rivers_layer")
    arcpy.management.Delete("basins_layer")

    return output_fc


def build_network_and_calculate_strahler(rivers_fc, use_common_ancestor):
    """
    Builds a directed graph from river segments and calculates Strahler numbers.

    Parameters:
    rivers_fc (str): Path to the feature class containing river data.
    use_common_ancestor (bool): Whether to use common ancestor logic to avoid incrementing Strahler values
                                for segments that diverge and rejoin.

    Returns:
    str: Path to the output shapefile with updated Strahler values.
    """
    strahler_df = gpd.read_file(rivers_fc)

    def extract_start_end_coords(geometry):
        """Extracts the start and end coordinates from a line segments geometry."""
        coords = list(geometry.coords)
        start = Point(coords[0])
        end = Point(coords[-1])
        return start, end

    G = nx.DiGraph()

    for idx, row in strahler_df.iterrows():
        start, end = extract_start_end_coords(row.geometry)
        G.add_edge(start, end, index=idx)

    def remove_cycles(G):
        """
        Removes cycles from the graph.

        Parameters:
        G (networkx.DiGraph): Directed graph representing the river network.
        """
        cycles = list(nx.simple_cycles(G))
        while cycles:
            for cycle in cycles:
                highest_upstream_node = min(
                    cycle, key=lambda node: list(G.nodes).index(node)
                )
                out_edges = list(G.out_edges(highest_upstream_node))
                if out_edges:
                    edge_to_remove = out_edges[0]
                    if G.has_edge(*edge_to_remove):
                        G.remove_edge(*edge_to_remove)
                        break
            cycles = list(nx.simple_cycles(G))

    def precompute_ancestors(G):
        """
        Precomputes the ancestors for each node in the graph.

        Parameters:
        G (networkx.DiGraph): Directed graph representing the river network.

        Returns:
        dict: A dictionary mapping each node to its set of ancestors.
        """
        return {node: set(nx.ancestors(G, node)) for node in G.nodes}

    def find_common_ancestor(precomputed_ancestors, node1, node2):
        """
        Finds the common ancestor of two nodes.

        Parameters:
        precomputed_ancestors (dict): A dictionary mapping each node to its set of ancestors.
        node1 (node): The first node.
        node2 (node): The second node.

        Returns:
        node: The common ancestor of the two nodes, or None if no common ancestor exists.
        """
        common_ancestors = precomputed_ancestors[node1] & precomputed_ancestors[node2]
        if common_ancestors:
            return max(common_ancestors, key=lambda x: list(G.nodes).index(x))
        return None

    def calculate_strahler(G, use_common_ancestor):
        """
        Calculates Strahler numbers for the graph.

        Parameters:
        G (networkx.DiGraph): Directed graph representing the river network.
        use_common_ancestor (bool): Whether to use common ancestor logic to avoid incrementing Strahler values
                                    for segments that diverge and rejoin.
        """
        strahler_numbers = {}
        precomputed_ancestors = precompute_ancestors(G)

        for node in nx.topological_sort(G):
            in_edges = list(
                G.in_edges(node, data=True)
            )  # Get all incoming edges to the current node
            if not in_edges:
                max_strahler = 1  # If no incoming edges, assign strahler number 1
            else:
                max_strahler = max(
                    strahler_numbers[e[2]["index"]] for e in in_edges
                )  # Find max Strahler number from incoming edges to the node
                if (
                    sum(
                        strahler_numbers[e[2]["index"]] == max_strahler
                        for e in in_edges
                    )
                    > 1
                ):  # Check if more than 1 incomming edge have the same max strahler
                    increase = True
                    if use_common_ancestor:
                        for i in range(len(in_edges)):
                            for j in range(i + 1, len(in_edges)):
                                common_ancestor = find_common_ancestor(
                                    precomputed_ancestors,
                                    in_edges[i][0],
                                    in_edges[j][0],
                                )
                                if common_ancestor:
                                    increase = False
                                    break
                            if not increase:
                                break
                    if increase:
                        max_strahler += 1  # Increment Strahler number if multiple edges have the same strahler value
            for _, _, data in G.out_edges(node, data=True):
                strahler_numbers[data["index"]] = max_strahler
        for idx in range(len(strahler_df)):
            strahler_df.at[idx, "strahler"] = strahler_numbers.get(idx, 1)

    remove_cycles(G)
    calculate_strahler(G, use_common_ancestor)

    output_strahler_fc = rivers_fc.replace(".shp", "_strahler.shp")
    strahler_df.to_file(output_strahler_fc)
    print(f"Updated rivers with Strahler values saved to: {output_strahler_fc}")

    return output_strahler_fc


def convert_to_gdb(shapefile, output_gdb):
    """Converts a shapefile to a feature class in a geodatabase."""
    gdb_fc_name = shapefile.split("\\")[-1].replace(".shp", "")
    arcpy.FeatureClassToFeatureClass_conversion(shapefile, output_gdb, gdb_fc_name)
    print(f"Converted {shapefile} to {output_gdb}\\{gdb_fc_name}")


if __name__ == "__main__":
    main()
