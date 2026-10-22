import arcpy
from env_setup import environment_setup
from file_manager import WorkFileManager
from composition_configs import core_config
from collections import defaultdict
import os

import logging

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)


logger = logging.getLogger(__name__)


class IntegrateDiffCheck:
    """
    Runs arcpy integrate then checks for differences,
    checks for differences by making a neighbour graph before and after integration
    and comparing the graphs to identify changes in topology.
    """

    def __init__(self, feature_class: str, wfm: WorkFileManager):
        environment_setup.main()
        self.feature_class = f"{feature_class}_copy"
        arcpy.management.CopyFeatures(feature_class, self.feature_class)
        self.wfm = wfm
        self.neighbour_graph_before = defaultdict(set)
        self.neighbour_graph_after = defaultdict(set)
        self.differences: dict[int, dict[str, set[int]]] = {}

    def run_integration(self):
        self.neighbour_graph_before = self._create_neighbour_graph()
        count_before = self.get_featureclass_count()

        arcpy.management.Integrate(self.feature_class, "0.1 Meters")

        count_after = self.get_featureclass_count()
        if count_before != count_after:
            logger.info(
                "Feature class count changed after integration: before=%d, after=%d",
                count_before,
                count_after,
            )
            logger.info("This means that oids may have changed due to integration.")

        self.neighbour_graph_after = self._create_neighbour_graph()
        self.differences = self._compare_graphs()

        self.log_differences()

    def _create_neighbour_graph(self):
        adjacency = defaultdict(set)
        near_table = self.wfm.build_file_path("IntegrateDiff_near_table", "gdb")
        arcpy.analysis.GenerateNearTable(
            in_features=self.feature_class,
            near_features=self.feature_class,
            out_table=near_table,
            search_radius="0 Meters",
            closest="ALL",
        )
        with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
            for in_fid, near_fid in cursor:
                if in_fid == near_fid:
                    continue
                adjacency[in_fid].add(near_fid)

        return adjacency

    def _compare_graphs(self):
        differences = {}

        all_keys = set(self.neighbour_graph_before) | set(self.neighbour_graph_after)

        for key in all_keys:
            before = self.neighbour_graph_before.get(key, set())
            after = self.neighbour_graph_after.get(key, set())

            added = after - before
            removed = before - after

            if added or removed:
                differences[key] = {
                    "added": added,
                    "removed": removed,
                }

        return differences

    def log_differences(self):
        if not self.differences:
            logger.info("No differences found after integration.")
            return

        for key, change in self.differences.items():
            added = ", ".join(map(str, change["added"]))
            removed = ", ".join(map(str, change["removed"]))
            logger.info(
                "Feature ID %s: Added neighbours: [%s], Removed neighbours: [%s]",
                key,
                added,
                removed,
            )

    def get_featureclass_count(self):
        return int(arcpy.management.GetCount(self.feature_class).getOutput(0))


if __name__ == "__main__":
    feature_class = (
        r"C:\temp\211026\Symbology_Fixed.gdb\data_selection___nvdb_roads___n100_road"
    )
    wfm = WorkFileManager(
        config=core_config.WorkFileConfig(
            root_file=r"C:\temp\211026\Symbology_Fixed.gdb\data_selection___nvdb_roads___n100_road"
        )
    )
    checker = IntegrateDiffCheck(feature_class, wfm)
    checker.run_integration()
    checker.log_differences()
