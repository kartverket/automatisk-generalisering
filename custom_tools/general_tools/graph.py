import arcpy
import networkx as nx

from collections import defaultdict


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
        Sets up the GISGraph with parameters.

        Note: Data is not loaded automatically. Call one of the
        select_x_cycle functions to load the data appropriately and
        perform cycle detection.

        :param input_path: Full path to the GDB feature class containing point data.
        :param object_id: Field name uniquely identifying each point.
        :param original_id: Field name representing the original line ID (shared by endpoints).
        :param geometry_field: Field name containing geometry (default "SHAPE").
        :param directed: Whether to use a directed graph (default False).
        """
        self.input_path = input_path
        self.object_id = object_id
        self.original_id = original_id
        self.geometry_field = geometry_field
        self.directed = directed
        # The graph will be loaded later
        self.graph = None

    def load_data(self, cycle_mode: int = 1):
        """
        Loads data from the GDB feature class and builds the graph.

        If cycle_mode is 2 (for 2-cycle detection), we create a MultiGraph
        to preserve parallel edges. For other modes, a standard Graph (or DiGraph)
        is created.

        :param cycle_mode: 1 for self-loops; 2 for 2-cycles; (3 and 4 can be added similarly).
        """
        if cycle_mode == 2:
            # Use a MultiGraph to allow parallel edges
            self.graph = nx.MultiDiGraph() if self.directed else nx.MultiGraph()
        else:
            self.graph = nx.DiGraph() if self.directed else nx.Graph()

        data_rows = []
        fields = [self.object_id, self.original_id, self.geometry_field]

        # Read data using ArcPy's SearchCursor
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

        # Helper: convert geometry to a hashable node key
        def geometry_to_node_key(geom):
            """
            Converts a geometry to a hashable tuple.
            If geom is already a tuple (x,y), it is returned as such.
            Otherwise, we assume it is an ArcPy geometry.
            """
            if isinstance(geom, tuple):
                x = round(geom[0], 10)
                y = round(geom[1], 10)
            else:
                # Assuming geom is an ArcPy geometry
                x = round(geom.firstPoint.X, 11)
                y = round(geom.firstPoint.Y, 11)
            return (x, y)

        # Build edge tuples. For each line (with exactly two endpoints) create an edge
        edges_to_add = []
        for line_id, endpoints in lines.items():
            if len(endpoints) == 2:
                point_a, point_b = endpoints
                node_key_a = geometry_to_node_key(point_a[self.geometry_field])
                node_key_b = geometry_to_node_key(point_b[self.geometry_field])

                # Optionally add nodes with attributes
                if node_key_a not in self.graph:
                    self.graph.add_node(
                        node_key_a, geometry=point_a[self.geometry_field]
                    )
                if node_key_b not in self.graph:
                    self.graph.add_node(
                        node_key_b, geometry=point_b[self.geometry_field]
                    )

                # In both simple Graph and MultiGraph, we add the edge with original_line_id
                edges_to_add.append(
                    (node_key_a, node_key_b, {"original_line_id": line_id})
                )

        self.graph.add_edges_from(edges_to_add)

    def detect_cycle(self):
        """
        Uses Networkx's methods to detect cycles in the graph.
        For undirected graphs, cycle_basis is used.

        :return: Tuple (cycle_found, cycle_info).
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

    def get_cycle_line_sql(self, cycle_mode: int = 1):
        """
        After the graph is loaded, detects cycles of the specified mode,
        collects the original_line_id values from edges in those cycles, and
        returns a SQL expression to select the corresponding records.

        :param cycle_mode: 1 for self-loops; 2 for 2-cycles; 3 for 3-node cycles; 4 for 4-node cycles.
        :return: A SQL expression string (or None if no cycles detected).
        """
        cycle_line_ids = set()
        if cycle_mode == 1:
            # Detect self-loops
            for node in self.graph.nodes():
                if self.graph.has_edge(node, node):
                    # In a MultiGraph, there might be multiple self-loops.
                    # For MultiGraph, iterate over all self-loop edges.
                    if self.graph.is_multigraph():
                        for _, edge_data in self.graph[node][node].items():
                            if edge_data and "original_line_id" in edge_data:
                                cycle_line_ids.add(edge_data["original_line_id"])
                    else:
                        edge_data = self.graph.get_edge_data(node, node)
                        if edge_data and "original_line_id" in edge_data:
                            cycle_line_ids.add(edge_data["original_line_id"])
        elif cycle_mode == 2:
            # Detect 2-cycles using a MultiGraph.
            # A 2-cycle (parallel edges) exists if two nodes have two or more edges between them.
            for u, v in self.graph.edges():
                if self.graph.number_of_edges(u, v) >= 2:
                    # Retrieve all edge data between u and v
                    if self.graph.is_multigraph():
                        for _, edge_data in self.graph[u][v].items():
                            if edge_data and "original_line_id" in edge_data:
                                cycle_line_ids.add(edge_data["original_line_id"])
                    else:
                        # Should not happen for a simple graph
                        edge_data = self.graph.get_edge_data(u, v)
                        if edge_data and "original_line_id" in edge_data:
                            cycle_line_ids.add(edge_data["original_line_id"])
        elif cycle_mode == 3:
            # Detect cycles with exactly 3 nodes using cycle_basis
            cycles = nx.cycle_basis(self.graph)
            for cycle in cycles:
                if len(cycle) == 3:
                    n = len(cycle)
                    for i in range(n):
                        u = cycle[i]
                        v = cycle[(i + 1) % n]
                        edge_data = self.graph.get_edge_data(u, v)
                        if edge_data and "original_line_id" in edge_data:
                            cycle_line_ids.add(edge_data["original_line_id"])
        elif cycle_mode == 4:
            # Detect cycles with exactly 4 nodes using cycle_basis
            cycles = nx.cycle_basis(self.graph)
            for cycle in cycles:
                if len(cycle) == 4:
                    n = len(cycle)
                    for i in range(n):
                        u = cycle[i]
                        v = cycle[(i + 1) % n]
                        edge_data = self.graph.get_edge_data(u, v)
                        if edge_data and "original_line_id" in edge_data:
                            cycle_line_ids.add(edge_data["original_line_id"])
        else:
            raise ValueError("Unsupported cycle_mode. Choose 1, 2, 3 or 4.")

        if cycle_line_ids:
            # Build a SQL expression
            ids_str = ", ".join(str(x) for x in cycle_line_ids)
            sql = f"{self.object_id} IN ({ids_str})"
            return sql
        else:
            return None

    def select_1_cycle(self):
        """
        Loads data configured for self-loop (1-cycle) detection,
        then returns a SQL expression for selecting those cycles.
        """
        self.load_data(cycle_mode=1)
        return self.get_cycle_line_sql(cycle_mode=1)

    def select_2_cycle(self):
        """
        Loads data configured for 2-cycle detection (using a MultiGraph),
        then returns a SQL expression for selecting those cycles.
        """
        self.load_data(cycle_mode=2)
        return self.get_cycle_line_sql(cycle_mode=2)

    def select_3_cycle(self):
        """
        Loads data into a simple graph (sufficient for 3-node cycle detection),
        then returns a SQL expression for selecting 3-cycles.
        """
        self.load_data(cycle_mode=3)
        return self.get_cycle_line_sql(cycle_mode=3)

    def select_4_cycle(self):
        """
        Loads data into a simple graph (sufficient for 4-node cycle detection),
        then returns a SQL expression for selecting 4-cycles.
        """
        self.load_data(cycle_mode=4)
        return self.get_cycle_line_sql(cycle_mode=4)

    def print_graph_info(self):
        if self.graph is not None:
            print("Number of nodes:", self.graph.number_of_nodes())
            print("Number of edges:", self.graph.number_of_edges())
        else:
            print("Graph not loaded yet.")
