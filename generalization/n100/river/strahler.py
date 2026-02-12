import arcpy
from collections import deque
import networkx as nx

from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.custom_arcpy import OverlapType, SelectionType
from env_setup import environment_setup
from file_manager.n100.file_manager_rivers import River_N100
from file_manager.work_file_manager import WorkFileManager


class RiverStrahler:
    """
    Class for computing Strahler stream order for river lines.
    """

    def __init__(
        self,
        river_strahler_config: logic_config.RiverStrahlerKwargs,
    ):
        """
        Creates an instance of RiverStrahler.
        """
        environment_setup.main()

        self.input_fc = river_strahler_config.input_line_feature
        self.output_fc = river_strahler_config.output_processed_feature
        self.havflate_fc = river_strahler_config.havflate_feature
        self.UG = nx.Graph()  # Undirected graph
        self.G = nx.DiGraph()  # Directed graph
        self.work_file_manager = WorkFileManager(
            config=river_strahler_config.work_file_manager_config
        )

        self.endpoint_feature = "endpoint_feature"
        self.sink_feature = "sink_feature"

        self.gdb_files_list = [
            self.endpoint_feature,
            self.sink_feature,
        ]

        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    @timing_decorator
    def build_undirected_graph(self) -> None:
        """
        Build an undirected graph from the river lines feature class.
        """
        with arcpy.da.SearchCursor(self.input_fc, ["OID@", "SHAPE@"]) as cursor:
            for oid, geom in cursor:
                if geom is None:
                    continue

                start = (round(geom.firstPoint.X, 3), round(geom.firstPoint.Y, 3))
                end = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))

                self.UG.add_edge(start, end, index=oid)

    @timing_decorator
    def find_havflate_nodes(self) -> set:
        """
        Find nodes touching polygons with objtype havflate as they are guaranteed sinks.
        """
        arcpy.management.FeatureVerticesToPoints(
            self.input_fc,
            self.endpoint_feature,
            "BOTH_ENDS",
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.endpoint_feature,
            overlap_type=OverlapType.INTERSECT.value,
            select_features=self.havflate_fc,
            output_name=self.sink_feature,
            selection_type=SelectionType.NEW_SELECTION.value,
        )

        hav_nodes = set()

        with arcpy.da.SearchCursor(self.sink_feature, ["SHAPE@"]) as cur:
            for (pt_geom,) in cur:
                pt = pt_geom.firstPoint
                hav_nodes.add((round(pt.X, 3), round(pt.Y, 3)))

        return hav_nodes

    @timing_decorator
    def orient_graph(self, hav_nodes) -> None:
        """
        Orient all edges to be pointing towards the sinks and build a directed graph.
        """
        queue = deque(hav_nodes)
        visited = set(hav_nodes)
        parent = {}

        while queue:
            node = queue.popleft()
            for nbr in self.UG.neighbors(node):
                if nbr not in visited:
                    visited.add(nbr)
                    parent[nbr] = node
                    queue.append(nbr)

        # Build directed graph
        for u, v, data in self.UG.edges(data=True):
            oid = data["index"]

            if parent.get(u) == v:
                self.G.add_edge(u, v, index=oid)
            elif parent.get(v) == u:
                self.G.add_edge(v, u, index=oid)

    @timing_decorator
    def compute_strahler(self) -> dict:
        """
        Compute Strahler stream order for each edge in the graph.
        """
        strahler = {}

        for node in nx.topological_sort(self.G):
            in_edges = list(self.G.in_edges(node, data=True))

            if not in_edges:
                order = 1
            else:
                max_order = max(strahler[e[2]["index"]] for e in in_edges)
                count_max = sum(strahler[e[2]["index"]] == max_order for e in in_edges)
                order = max_order + 1 if count_max > 1 else max_order

            for _, _, data in self.G.out_edges(node, data=True):
                strahler[data["index"]] = order

        return strahler

    @timing_decorator
    def write_output(self, strahler_dict: dict) -> None:
        """
        Write the Strahler order to the output feature class.
        """
        arcpy.management.CopyFeatures(self.input_fc, self.output_fc)

        fields = [f.name for f in arcpy.ListFields(self.output_fc)]
        if "strahler" not in fields:
            arcpy.management.AddField(self.output_fc, "strahler", "LONG")

        with arcpy.da.UpdateCursor(self.output_fc, ["OID@", "strahler"]) as cursor:
            for oid, _ in cursor:
                cursor.updateRow([oid, strahler_dict.get(oid, 1)])

    @timing_decorator
    def run(self) -> None:
        """
        Run the Strahler computation process.
        """
        self.build_undirected_graph()
        hav_nodes = self.find_havflate_nodes()
        self.orient_graph(hav_nodes)
        strahler = self.compute_strahler()
        self.write_output(strahler)

        self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    root = River_N100.river_strahler___root___n100.value
    input_fc = River_N100.river_cycles___removed_cycles___n100.value
    output_fc = River_N100.river_strahler___calculated_strahler___n100.value
    havflate_fc = River_N100.river_connected___havflate___n100.value

    config = logic_config.RiverStrahlerKwargs(
        input_line_feature=input_fc,
        work_file_manager_config=core_config.WorkFileConfig(root),
        output_processed_feature=output_fc,
        havflate_feature=havflate_fc,
    )

    river_strahler = RiverStrahler(config)
    river_strahler.run()
