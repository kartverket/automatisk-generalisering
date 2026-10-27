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


class IntegrateDiff:
    """
    Runs arcpy integrate with tolerance = XYTolerance then checks for differences,
    checks for differences by making a neighbour graph before and after integration
    and comparing the graphs to identify changes in topology.
    creates a feature class containing the parts that changed called {self.feature_class}_changed

    important note:
    OIDs may change after integration.
    Changes are tracked by if connected features change after integration,
    so there is possibility small changes that dont affect connections between features are not in {self.feature_class}_changed

    """

    def __init__(self, feature_class: str):
        environment_setup.main()
        self.feature_class = feature_class
        self.wfm = WorkFileManager(
            config=core_config.WorkFileConfig(root_file=feature_class)
        )
        self.neighbour_graph_before = defaultdict(set)
        self.neighbour_graph_after = defaultdict(set)
        self.differences: dict[int, dict[str, set[int]]] = {}
        self.uniq_id = "unique_id"

    def run_integration(self):
        arcpy.management.AddField(self.feature_class, self.uniq_id, "LONG")
        arcpy.management.CalculateField(
            self.feature_class, self.uniq_id, "!OBJECTID!", "PYTHON3"
        )

        self.neighbour_graph_before = self._create_neighbour_graph(stage="before")
        count_before = self.get_featureclass_count()

        arcpy.management.Integrate(self.feature_class, arcpy.env.XYTolerance)

        count_after = self.get_featureclass_count()
        if count_before != count_after:
            logger.info(
                "Feature class count changed after integration: before=%d, after=%d",
                count_before,
                count_after,
            )
            logger.info("This means that oids may have changed due to integration.")

        self.neighbour_graph_after = self._create_neighbour_graph(stage="after")
        self.differences = self._compare_graphs()

        self.log_differences()
        self.wfm.delete_created_files()
        arcpy.management.DeleteField(self.feature_class, self.uniq_id)

    def _create_neighbour_graph(self, stage: str) -> defaultdict[int, set[int]]:
        adjacency: defaultdict[int, set[int]] = defaultdict(set)
        near_table = self.wfm.build_file_path(
            file_name=f"IntegrateDiff_near_table_{stage}", file_type="gdb"
        )
        arcpy.analysis.GenerateNearTable(
            in_features=self.feature_class,
            near_features=self.feature_class,
            out_table=near_table,
            search_radius="0 Meters",
            closest="ALL",
        )
        with arcpy.da.SearchCursor(
            self.feature_class, ["OID@", self.uniq_id]
        ) as cursor:
            oid_to_uniq_id: dict[int, int] = {oid: uid for oid, uid in cursor}

        with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
            for in_fid, near_fid in cursor:
                if in_fid == near_fid:
                    continue
                adjacency[oid_to_uniq_id[in_fid]].add(oid_to_uniq_id[near_fid])

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

        changed_oids = set()
        added_connections_count = 0
        removed_connections_count = 0
        for key, change in self.differences.items():
            added_connections_count += len(change["added"])
            removed_connections_count += len(change["removed"])
            for changed in change["added"]:
                changed_oids.add(changed)
            for changed in change["removed"]:
                changed_oids.add(changed)
            changed_oids.add(key)
        logger.info(
            "Added connections: %s, Removed connections: %s",
            added_connections_count,
            removed_connections_count,
        )

        if changed_oids:
            layer = f"{self.feature_class}_layer"
            arcpy.management.MakeFeatureLayer(self.feature_class, layer)
            arcpy.management.SelectLayerByAttribute(
                layer,
                "NEW_SELECTION",
                f"{self.uniq_id} IN ({','.join(map(str, changed_oids))})",
            )
            arcpy.management.CopyFeatures(layer, f"{self.feature_class}_changed")

    def get_featureclass_count(self):
        return int(arcpy.management.GetCount(self.feature_class).getOutput(0))


if __name__ == "__main__":
    feature_class = ""
    checker = IntegrateDiff(feature_class)
    checker.run_integration()
