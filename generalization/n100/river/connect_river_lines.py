import arcpy
import os
import networkx as nx

from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.custom_arcpy import OverlapType, SelectionType
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_rivers import River_N100
import generalization.n100.river.config as river_config


class ConnectRiverLines:
    """
    Class for connecting river lines within a specified basin by processing hydro polygons
    and ensuring connectivity through a minimum spanning tree approach.
    """

    def __init__(
        self,
        connect_river_lines_config: logic_config.ConnectRiverLinesKwargs,
    ):
        """
        Creates an instance of ConnectRiverLines.
        """
        environment_setup.main()

        self.output_processed_feature = (
            connect_river_lines_config.output_processed_feature
        )
        self.basin = connect_river_lines_config.basin
        self.work_file_manager = WorkFileManager(
            config=connect_river_lines_config.work_file_manager_config
        )

        self.basin_selection = "basin_selection"
        self.basin_lines = "basin_lines"
        self.basin_lines_selection = "basin_lines_selection"
        self.basin_polygons = "basin_polygons"
        self.polygons_near_lines = "polygons_near_lines"
        self.basin_polygons_layer = "basin_polygons_layer"
        self.polygons_near_polygons = "polygons_near_polygons"
        self.polygons_near_rivers = "polygons_near_rivers"
        self.polygons_near_rivers_selection = "polygons_near_rivers_selection"
        self.polygons_near_rivers_boundaries = "polygons_near_rivers_boundaries"
        self.outside_basin_lines_selection = "outside_basin_lines_selection"
        self.collapse_hydro_polygon = "collapse_hydro_polygon"
        self.polygon_intersection_lines = "polygon_intersection_lines"
        self.intersection_midpoints = "intersection_midpoints"
        self.intersection_midpoints_merged = "intersection_midpoints_merged"
        self.polygon_intersection_points = "polygon_intersection_points"
        self.polygon_intersection_points_merged = "polygon_intersection_points_merged"
        self.connected_river_lines = "connected_river_lines"
        self.minimal_connected_river_lines = "minimal_connected_river_lines"
        self.final_connected_river_lines = "final_connected_river_lines"

        self.gdb_files_list = [
            self.basin_selection,
            self.basin_lines,
            self.basin_lines_selection,
            self.basin_polygons,
            self.polygons_near_lines,
            self.basin_polygons_layer,
            self.polygons_near_polygons,
            self.polygons_near_rivers,
            self.polygons_near_rivers_selection,
            self.polygons_near_rivers_boundaries,
            self.outside_basin_lines_selection,
            self.collapse_hydro_polygon,
            self.polygon_intersection_lines,
            self.intersection_midpoints,
            self.intersection_midpoints_merged,
            self.polygon_intersection_points,
            self.polygon_intersection_points_merged,
            self.connected_river_lines,
            self.minimal_connected_river_lines,
            self.final_connected_river_lines,
        ]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    @timing_decorator
    def prepare_data(self) -> None:
        """
        Prepare data by selecting relevant features based on the basin and performing
        spatial operations.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=river_config.basin_path,
            expression=f"vassOmr = '{self.basin}'",
            output_name=self.basin_selection,
            selection_type=SelectionType.NEW_SELECTION.value,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=river_config.grense_path,
            overlap_type=OverlapType.INTERSECT.value,
            select_features=self.basin_selection,
            output_name=self.basin_lines,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.basin_lines,
            expression="objtype = 'ElvBekk'",
            output_name=self.basin_lines_selection,
            selection_type=SelectionType.NEW_SELECTION.value,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=river_config.omrade_path,
            overlap_type=OverlapType.INTERSECT.value,
            select_features=self.basin_selection,
            output_name=self.basin_polygons,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.basin_polygons,
            overlap_type=OverlapType.WITHIN_A_DISTANCE.value,
            select_features=self.basin_lines_selection,
            output_name=self.polygons_near_lines,
            search_distance="0.1 Meters",
        )

        arcpy.management.MakeFeatureLayer(
            self.basin_polygons,
            self.basin_polygons_layer,
        )

        arcpy.analysis.SpatialJoin(
            target_features=self.basin_polygons,
            join_features=self.basin_polygons_layer,
            out_feature_class=self.polygons_near_polygons,
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_COMMON",
            match_option=OverlapType.WITHIN_A_DISTANCE.value,
            search_radius="0.1 Meters",
        )

        # Remove self-matches (TARGET_FID == JOIN_FID)
        with arcpy.da.UpdateCursor(
            self.polygons_near_polygons,
            ["TARGET_FID", "JOIN_FID"],
        ) as cursor:
            for target, join in cursor:
                if target == join:
                    cursor.deleteRow()

        arcpy.management.Merge(
            [
                self.polygons_near_lines,
                self.polygons_near_polygons,
            ],
            self.polygons_near_rivers,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.polygons_near_rivers,
            expression="objtype IN ('Elv', 'Innsjø')",
            output_name=self.polygons_near_rivers_selection,
            selection_type=SelectionType.NEW_SELECTION.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.polygons_near_rivers,
            expression="objtype IN ('Havflate')",
            output_name=River_N100.river_connected___havflate___n100.value,
            selection_type=SelectionType.NEW_SELECTION.value,
        )

        arcpy.management.PolygonToLine(
            in_features=self.polygons_near_rivers_selection,
            out_feature_class=self.polygons_near_rivers_boundaries,
        )

        arcpy.analysis.Erase(
            in_features=self.basin_lines_selection,
            erase_features=self.polygons_near_rivers_selection,
            out_feature_class=self.outside_basin_lines_selection,
        )

        arcpy.cartography.CollapseHydroPolygon(
            in_features=self.polygons_near_rivers_selection,
            out_line_feature_class=self.collapse_hydro_polygon,
            connecting_features=self.outside_basin_lines_selection,
        )

    @timing_decorator
    def process_polygons(self) -> None:
        """
        Process hydro polygons to create connected river lines within the basin.
        """
        if arcpy.Exists(self.connected_river_lines):
            arcpy.management.Delete(self.connected_river_lines)

        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.connected_river_lines),
            out_name=os.path.basename(self.connected_river_lines),
            geometry_type="POLYLINE",
            spatial_reference=self.collapse_hydro_polygon,
        )

        # Build graph from collapsed hydro polygons
        G = nx.Graph()

        with arcpy.da.SearchCursor(
            self.collapse_hydro_polygon,
            ["OID@", "SHAPE@"],
        ) as cursor:
            for oid, geom in cursor:
                if geom is None:
                    continue

                start = (
                    round(geom.firstPoint.X, 3),
                    round(geom.firstPoint.Y, 3),
                )
                end = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))

                G.add_edge(start, end, fid=oid, weight=geom.length)

        if G.number_of_nodes() == 0:
            print("Empty graph, skipping")

        final_oids = set()

        T_metric = nx.minimum_spanning_tree(G, weight="weight")
        for u, v in T_metric.edges():
            final_oids.add(G[u][v]["fid"])

        if final_oids:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.collapse_hydro_polygon,
                expression=f"OBJECTID IN ({','.join(map(str, final_oids))})",
                output_name=self.minimal_connected_river_lines,
            )

            arcpy.management.Append(
                inputs=[self.minimal_connected_river_lines],
                target=self.connected_river_lines,
                schema_type="NO_TEST",
            )
        else:
            arcpy.management.Append(
                inputs=[self.collapse_hydro_polygon],
                target=self.connected_river_lines,
                schema_type="NO_TEST",
            )

        arcpy.management.CalculateField(
            self.connected_river_lines,
            "objtype",
            "'generated_centerline'",
            "PYTHON3",
        )

        arcpy.management.Merge(
            inputs=[
                self.outside_basin_lines_selection,
                self.connected_river_lines,
            ],
            output=self.output_processed_feature,
        )

    @timing_decorator
    def run(self) -> None:
        """
        Run the river line connection process for a specified basin.
        """
        self.prepare_data()
        self.process_polygons()

        self.work_file_manager.delete_created_files()


if __name__ == "__main__":
    basin = "TANA/TANAFJORDEN SØR"
    root = River_N100.river_connected___connected_river_lines_root___n100.value
    output_fc = River_N100.river_connected___connected_river_lines___n100.value
    config = logic_config.ConnectRiverLinesKwargs(
        work_file_manager_config=core_config.WorkFileConfig(root),
        output_processed_feature=output_fc,
        basin=basin,
    )

    connector = ConnectRiverLines(config)
    connector.run()
