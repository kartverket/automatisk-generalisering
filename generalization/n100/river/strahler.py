import arcpy
import networkx as nx

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager.n100.file_manager_rivers import River_N100


class RiverStrahler:
    def __init__(self, input_fc: str, output_fc: str):
        """
        Class to compute Strahler stream order for river lines.

        Args:
            input_fc (str): input feature class path
            output_fc (str): output feature class path
        """
        environment_setup.main()
        self.input_fc = input_fc
        self.output_fc = output_fc
        self.G = nx.DiGraph()

    def build_graph(self):
        """
        Build a directed graph from the river lines feature class.
        """
        with arcpy.da.SearchCursor(self.input_fc, ["OID@", "SHAPE@"]) as cursor:
            for oid, geom in cursor:
                if geom is None:
                    continue

                start = (round(geom.firstPoint.X, 3), round(geom.firstPoint.Y, 3))
                end = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))

                self.G.add_edge(start, end, index=oid, weight=geom.length)

    def compute_strahler(self):
        """
        Compute Strahler stream order for each edge in the graph.
        Returns:
            dict: mapping of edge index to Strahler order
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

    def write_output(self, strahler_dict: dict):
        """
        Write the Strahler order to the output feature class.

        Args:
            strahler_dict (dict): mapping of edge index to Strahler order
        """
        arcpy.management.CopyFeatures(self.input_fc, self.output_fc)

        fields = [f.name for f in arcpy.ListFields(self.output_fc)]
        if "strahler" not in fields:
            arcpy.management.AddField(self.output_fc, "strahler", "LONG")

        with arcpy.da.UpdateCursor(self.output_fc, ["OID@", "strahler"]) as cursor:
            for oid, _ in cursor:
                cursor.updateRow([oid, strahler_dict.get(oid, 1)])

    @timing_decorator
    def run(self):
        """
        Run the Strahler computation process.
        """
        self.build_graph()
        strahler = self.compute_strahler()
        self.write_output(strahler)


if __name__ == "__main__":
    input_fc = River_N100.river_triangles___output___n100_river.value
    output_fc = River_N100.river_strahler___output___n100_river.value
    RiverStrahler(input_fc, output_fc).run()
