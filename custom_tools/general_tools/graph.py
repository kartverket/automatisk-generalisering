import arcpy
import networkx as nx
from collections import defaultdict

from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.file_utilities import WorkFileManager
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
        Instead of using the raw object_id, nodes are created based on their
        geometry to merge intersections properly.
        """
        data_rows = []
        fields = [self.object_id, self.original_id, self.geometry_field]

        # Use ArcPy's SearchCursor to iterate over the feature class
        with arcpy.da.SearchCursor(self.input_path, fields) as cursor:
            for row in cursor:
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

        # Helper function: convert geometry to a hashable node key.

        def geometry_to_node_key(geom):
            """
            Converts a geometry to a hashable tuple. If `geom` is a tuple, assume it is already (x, y).
            Otherwise, assume it is an ArcPy geometry and extract the firstPoint.
            The tolerance (tol) can be used if needed.
            """
            if isinstance(geom, tuple):
                x = round(geom[0], 10)  # Adjust precision as needed
                y = round(geom[1], 10)
            else:
                # Assuming geom is an ArcPy geometry
                x = round(geom.firstPoint.X, 11)
                y = round(geom.firstPoint.Y, 11)
            return (x, y)

        # Build a list of edge tuples to add using add_edges_from.
        edges_to_add = []
        for line_id, endpoints in lines.items():
            if len(endpoints) == 2:
                point_a, point_b = endpoints
                node_key_a = geometry_to_node_key(point_a[self.geometry_field])
                node_key_b = geometry_to_node_key(point_b[self.geometry_field])

                # Optionally, add nodes with attributes (like full geometry)
                if node_key_a not in self.graph:
                    self.graph.add_node(
                        node_key_a, geometry=point_a[self.geometry_field]
                    )
                if node_key_b not in self.graph:
                    self.graph.add_node(
                        node_key_b, geometry=point_b[self.geometry_field]
                    )

                # Create an edge with the original_line_id as an attribute.
                edges_to_add.append(
                    (node_key_a, node_key_b, {"original_line_id": line_id})
                )

        # Add all edges at once.
        self.graph.add_edges_from(edges_to_add)

    def detect_cycle(self):
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
        print("Number of nodes:", self.graph.number_of_nodes())
        print("Number of edges:", self.graph.number_of_edges())

    def mark_cycle_nodes(self):
        cycle_found, cycle_info = self.detect_cycle()
        if cycle_found:
            if self.directed:
                for u, v, _ in cycle_info:
                    self.graph.nodes[u]["cycle"] = True
                    self.graph.nodes[v]["cycle"] = True
            else:
                for cycle in cycle_info:
                    for node in cycle:
                        self.graph.nodes[node]["cycle"] = True

    def get_cycle_line_sql(self):
        """
        Detects cycles in the graph, collects the original line IDs from edges that are part of the cycle,
        and returns a SQL expression that can be used to select the original lines.

        :return: A SQL expression (string) that selects records with original_line_id in the cycle,
                 or None if no cycle is found.
        """
        cycle_found, cycle_info = self.detect_cycle()
        if not cycle_found:
            return None

        cycle_line_ids = set()

        if self.directed:
            # For directed graphs, cycle_info is a list of edges (u, v, orientation)
            for u, v, _ in cycle_info:
                edge_data = self.graph.get_edge_data(u, v)
                if edge_data and "original_line_id" in edge_data:
                    cycle_line_ids.add(edge_data["original_line_id"])
        else:
            # For undirected graphs, cycle_info is a list of cycles (each cycle is a list of nodes).
            # For each cycle, loop pairwise (wrapping around) to get the edge between adjacent nodes.
            for cycle in cycle_info:
                n = len(cycle)
                for i in range(n):
                    u = cycle[i]
                    v = cycle[(i + 1) % n]  # Wrap around to the first node.
                    edge_data = self.graph.get_edge_data(u, v)
                    if edge_data and "original_line_id" in edge_data:
                        cycle_line_ids.add(edge_data["original_line_id"])

        if cycle_line_ids:
            # Build a SQL expression. Adjust quoting if your original_line_id is text.
            ids_str = ", ".join(str(x) for x in cycle_line_ids)
            sql = f"{self.object_id} IN ({ids_str})"
            return sql
        else:
            return None


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

    sql_expression = gis_graph.get_cycle_line_sql()
    print(sql_expression)

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___resolve_road_conflicts___n100_road.value,
        expression=sql_expression,
        output_name=f"{Road_N100.testing_file___removed_triangles___n100_road.value}_cycle_edges_selection",
    )
