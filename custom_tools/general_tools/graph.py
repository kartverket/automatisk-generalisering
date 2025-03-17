import arcpy
import networkx as nx
from collections import defaultdict

from file_manager.n100.file_manager_roads import Road_N100


class GISGraph:
    def __init__(
        self,
        input_path: str,
        object_id: str,
        original_id: str,
        geometry_field: str = "SHAPE",
        directed: bool = False,
    ):
        """
        Constructs a graph from a GDB point feature class.

        :param input_path: Full path to the GDB feature class containing point data.
                           Example: r'C:\path\to\your.gdb\point_feature_class'
        :param object_id: Name of the field uniquely identifying each point (e.g., "OBJECTID").
        :param original_id: Name of the field representing the original line ID shared by two endpoints.
        :param geometry_field: Name of the geometry field (defaults to "SHAPE").
        :param directed: Whether the graph is directed. Defaults to False (undirected).
        """
        self.input_path = input_path
        self.object_id = object_id
        self.original_id = original_id
        self.geometry_field = geometry_field
        self.directed = directed

        # Create a Networkx graph (DiGraph if directed, Graph if undirected)
        self.graph = nx.DiGraph() if directed else nx.Graph()

        # Load data from the GDB and build the graph
        self._load_data()

    def _load_data(self):
        """
        Reads point features from the input GDB feature class using ArcPy,
        groups them by the original line ID, and creates edges between nodes
        (points) that share the same original line ID (if exactly two exist).
        """
        data_rows = []
        fields = [self.object_id, self.original_id, self.geometry_field]

        # Use ArcPy's SearchCursor to iterate over the feature class
        with arcpy.da.SearchCursor(self.input_path, fields) as cursor:
            for row in cursor:
                # print(f"Processing row 0:\n{row[0]}")
                # print(f"Processing row 1:\n{row[1]}")
                # print(f"Processing row 2:\n{row[2]}")
                row_dict = {
                    self.object_id: row[0],
                    self.original_id: row[1],
                    self.geometry_field: row[2],
                }
                data_rows.append(row_dict)

        # Group points by their original line ID
        lines = defaultdict(list)
        for row in data_rows:
            lines[row[self.original_id]].append(row)

        # For each group, if there are exactly two points, create an edge
        for line_id, endpoints in lines.items():
            if len(endpoints) == 2:
                point_a, point_b = endpoints
                node_a = point_a[self.object_id]
                node_b = point_b[self.object_id]

                # Add nodes with attributes (geometry and original_line_id)
                print(
                    f"Adding nodes {node_a} and {node_b} with original_line_id {line_id}\n"
                )
                print(f"geom node a: {point_a[self.geometry_field]}")
                print(f"geom node b: {point_b[self.geometry_field]}")
                if node_a not in self.graph:
                    self.graph.add_node(
                        node_a,
                        geometry=point_a[self.geometry_field],
                        original_line_id=line_id,
                    )
                if node_b not in self.graph:
                    self.graph.add_node(
                        node_b,
                        geometry=point_b[self.geometry_field],
                        original_line_id=line_id,
                    )

                # Create an edge between the two nodes and store the original line id as an attribute
                self.graph.add_edge(node_a, node_b, original_line_id=line_id)
                print(
                    f"Added edge between {node_a} and {node_b} with original_line_id {line_id}"
                )

    def detect_cycle(self):
        """
        Uses Networkx's built-in methods to detect cycles in the graph.

        For an undirected graph, the cycle_basis method is used. For directed graphs,
        find_cycle is employed.

        :return: A tuple (cycle_found, cycle_info) where cycle_found is True if a cycle exists.
                 For undirected graphs, cycle_info is a list of cycles (each cycle is a list of nodes).
                 For directed graphs, cycle_info is the first cycle found.
        """
        if self.directed:
            try:
                cycle = nx.find_cycle(self.graph, orientation="original")
                return True, cycle
            except nx.exception.NetworkXNoCycle:
                return False, None
        else:
            cycles = nx.cycle_basis(self.graph)
            if cycles:
                return True, cycles
            else:
                return False, None

    def print_graph_info(self):
        """
        Prints a summary of the graph (number of nodes and edges).
        """
        print("Number of nodes:", self.graph.number_of_nodes())
        print("Number of edges:", self.graph.number_of_edges())

    # After cycle detection, you might mark nodes that are in a cycle:
    def mark_cycle_nodes(self):
        cycle_found, cycle_info = self.detect_cycle()
        if cycle_found:
            if self.directed:
                # For a directed graph, cycle_info is a list of edges in the cycle.
                for u, v, _ in cycle_info:
                    self.graph.nodes[u]["cycle"] = True
                    self.graph.nodes[v]["cycle"] = True
            else:
                # For an undirected graph, cycle_info is a list of cycles (each a list of nodes).
                for cycle in cycle_info:
                    for node in cycle:
                        self.graph.nodes[node]["cycle"] = True


# Example usage
if __name__ == "__main__":
    # Path to the GDB feature class
    input_feature_class = Road_N100.testing_file___removed_triangles___n100_road.value

    # Instantiate the GISGraph with appropriate field names
    gis_graph = GISGraph(
        input_path=input_feature_class,
        object_id="OBJECTID",
        original_id="ORIG_FID",
        geometry_field="SHAPE",
        directed=False,
    )

    gis_graph.print_graph_info()

    cycle_found, cycle_info = gis_graph.detect_cycle()
    if cycle_found:
        print("Cycle detected:")
        print(cycle_info)
    else:
        print("No cycles detected.")
