import arcpy
import os
import networkx as nx

from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_rivers import River_N100
import generalization.n100.river.config as config


class ConnectRiverLines:
    """
    Class to connect river lines within a specified basin by processing hydro polygons
    and ensuring connectivity through a minimum spanning tree approach.
    """

    def __init__(
        self,
        basin: str,
        connect_river_lines_config: logic_config.ConnectRiverLinesKwargs,
    ):
        """_summary_

        Args:
            basin (str): The basin identifier to process.
            connect_river_lines_config (logic_config.ConnectRiverLinesKwargs): A configuration instance containing parameters for the process.
        """
        environment_setup.main()
        self.basin = basin
        self.work_file_manager = WorkFileManager(
            config=connect_river_lines_config.work_file_manager_config
        )

    @timing_decorator
    def prepare_data(self):
        """
        Prepare data by selecting relevant features based on the basin and performing spatial operations.
        """
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=config.basin_path,
            expression=f"vassOmr = '{self.basin}'",
            output_name=River_N100.selecting_basin___basin_selection___n100.value,
            selection_type="NEW_SELECTION",
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=config.grense_path,
            overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
            select_features=River_N100.selecting_basin___basin_selection___n100.value,
            output_name=River_N100.selecting_basin___basin_lines___n100.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=River_N100.selecting_basin___basin_lines___n100.value,
            expression="objtype = 'ElvBekk'",
            output_name=River_N100.selecting_basin___basin_lines_selection___n100.value,
            selection_type="NEW_SELECTION",
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=config.omrade_path,
            overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
            select_features=River_N100.selecting_basin___basin_selection___n100.value,
            output_name=River_N100.selecting_basin___basin_polygons___n100.value,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=River_N100.selecting_basin___basin_polygons___n100.value,
            overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
            select_features=River_N100.selecting_basin___basin_lines_selection___n100.value,
            output_name=River_N100.selecting_basin___polygons_near_lines___n100.value,
            search_distance="1 Meters",
        )

        arcpy.management.MakeFeatureLayer(
            River_N100.selecting_basin___basin_polygons___n100.value,
            River_N100.selecting_basin___basin_polygons_copy___n100.value,
        )

        arcpy.analysis.SpatialJoin(
            target_features=River_N100.selecting_basin___basin_polygons___n100.value,
            join_features=River_N100.selecting_basin___basin_polygons_copy___n100.value,
            out_feature_class=River_N100.selecting_basin___polygons_near_polygons___n100.value,
            join_operation="JOIN_ONE_TO_MANY",
            join_type="KEEP_COMMON",
            match_option="WITHIN_A_DISTANCE",
            search_radius="1 Meters",
        )

        # Remove self-matches (TARGET_FID == JOIN_FID)
        with arcpy.da.UpdateCursor(
            River_N100.selecting_basin___polygons_near_polygons___n100.value,
            ["TARGET_FID", "JOIN_FID"],
        ) as cursor:
            for target, join in cursor:
                if target == join:
                    cursor.deleteRow()

        arcpy.management.Merge(
            [
                River_N100.selecting_basin___polygons_near_lines___n100.value,
                River_N100.selecting_basin___polygons_near_polygons___n100.value,
            ],
            River_N100.selecting_basin___polygons_near_rivers___n100.value,
        )

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=River_N100.selecting_basin___polygons_near_rivers___n100.value,
            expression="objtype IN ('Elv', 'Innsjø')",
            output_name=River_N100.selecting_basin___polygons_near_rivers_selection___n100.value,
            selection_type="NEW_SELECTION",
        )

        arcpy.cartography.CollapseHydroPolygon(
            in_features=River_N100.selecting_basin___polygons_near_rivers_selection___n100.value,
            out_line_feature_class=River_N100.river_connected___collapse_hydro_polygon___n100.value,
            connecting_features=River_N100.selecting_basin___basin_lines_selection___n100.value,
        )

        arcpy.management.FeatureVerticesToPoints(
            River_N100.selecting_basin___basin_lines_selection___n100.value,
            River_N100.intersection_points___river_endpoints___n100.value,
            "BOTH_ENDS",
        )

        arcpy.analysis.Intersect(
            [River_N100.selecting_basin___polygons_near_rivers_selection___n100.value],
            River_N100.intersection_points___polygon_intersection_lines___n100.value,
            output_type="LINE",
        )

        arcpy.analysis.Intersect(
            [
                River_N100.intersection_points___polygon_intersection_lines___n100.value,
                River_N100.river_connected___collapse_hydro_polygon___n100.value,
            ],
            River_N100.intersection_points___intersection_midpoints___n100.value,
            output_type="POINT",
        )

        arcpy.management.FeatureVerticesToPoints(
            River_N100.intersection_points___intersection_midpoints___n100.value,
            River_N100.intersection_points___intersection_midpoints_merged___n100.value,
            "ALL",
        )

        arcpy.analysis.Intersect(
            [River_N100.selecting_basin___polygons_near_rivers_selection___n100.value],
            River_N100.intersection_points___polygon_intersection_points___n100.value,
            output_type="POINT",
        )

        arcpy.management.FeatureVerticesToPoints(
            River_N100.intersection_points___polygon_intersection_points___n100.value,
            River_N100.intersection_points___polygon_intersection_points_merged___n100.value,
            "ALL",
        )

        arcpy.management.Merge(
            [
                River_N100.intersection_points___intersection_midpoints_merged___n100.value,
                River_N100.intersection_points___polygon_intersection_points_merged___n100.value,
                River_N100.intersection_points___river_endpoints___n100.value,
            ],
            River_N100.intersection_points___combined_intersection_points___n100.value,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=River_N100.intersection_points___combined_intersection_points___n100.value,
            overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
            select_features=River_N100.selecting_basin___polygons_near_rivers_selection___n100.value,
            output_name=River_N100.intersection_points___endpoints_matching___n100.value,
            search_distance="1 Meters",
        )

    @timing_decorator
    def process_polygons(self):
        """
        Process hydro polygons to create connected river lines within the basin.
        """
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(
                River_N100.river_connected___connected_river_lines___n100.value
            ),
            out_name=os.path.basename(
                River_N100.river_connected___connected_river_lines___n100.value
            ),
            geometry_type="POLYLINE",
            spatial_reference=River_N100.selecting_basin___polygons_near_rivers_selection___n100.value,
        )

        # Build graph from collapsed hydro polygons
        G = nx.Graph()

        with arcpy.da.SearchCursor(
            River_N100.river_connected___collapse_hydro_polygon___n100.value,
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

        # THE FOLLOWING CODE DEPENDS ON NO GEOMETRY HOLES
        # # Build list of terminal nodes
        # terminals = set()
        # with arcpy.da.SearchCursor(
        #     River_N100.intersection_points___endpoints_matching___n100.value,
        #     ["SHAPE@XY"],
        # ) as cursor:
        #     for (xy,) in cursor:
        #         x, y = xy
        #         terminals.add((round(x, 3), round(y, 3)))
        # terminals = list(terminals)
        # Compute shortest paths only between terminal pairs
        # for i in range(len(terminals)):
        #     for j in range(i + 1, len(terminals)):
        #         u = terminals[i]
        #         v = terminals[j]
        #         try:
        #             path = nx.shortest_path(G, u, v, weight="weight")
        #         except nx.NetworkXNoPath:
        #             continue

        #         for uu, vv in zip(path[:-1], path[1:]):
        #             final_oids.add(G[uu][vv]["fid"])

        # TEMPORARY CODE WHILE FKB HAS GEOMETRY HOLES NOT FIXED
        T_metric = nx.minimum_spanning_tree(G, weight="weight")
        for u, v in T_metric.edges():
            final_oids.add(G[u][v]["fid"])

        if final_oids:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=River_N100.river_connected___collapse_hydro_polygon___n100.value,
                expression=f"OBJECTID IN ({','.join(map(str, final_oids))})",
                output_name=River_N100.river_connected___minimal_connected_river_lines___n100.value,
            )

            arcpy.management.Append(
                inputs=[
                    River_N100.river_connected___minimal_connected_river_lines___n100.value
                ],
                target=River_N100.river_connected___connected_river_lines___n100.value,
                schema_type="NO_TEST",
            )
        else:
            arcpy.management.Append(
                inputs=[
                    River_N100.river_connected___collapse_hydro_polygon___n100.value
                ],
                target=River_N100.river_connected___connected_river_lines___n100.value,
                schema_type="NO_TEST",
            )

        arcpy.management.CalculateField(
            River_N100.river_connected___connected_river_lines___n100.value,
            "objtype",
            "'generated_centerline'",
            "PYTHON3",
        )

        arcpy.management.Merge(
            inputs=[
                River_N100.selecting_basin___basin_lines_selection___n100.value,
                River_N100.river_connected___connected_river_lines___n100.value,
            ],
            output=River_N100.river_connected___final_connected_river_lines___n100.value,
        )

        self.work_file_manager.delete_created_files()


@timing_decorator
def run(basin: str):
    """
    Run the river line connection process for a specified basin.

    Args:
        basin (str): The basin being processed.
    """
    root = River_N100.river_connected___connected_river_lines_root___n100.value
    config = logic_config.ConnectRiverLinesKwargs(
        work_file_manager_config=core_config.WorkFileConfig(root),
        maximum_length=500,
        root_file=root,
        sql_expressions=None,
    )

    connector = ConnectRiverLines(basin, config)
    connector.prepare_data()
    connector.process_polygons()


if __name__ == "__main__":
    basin = "ROLLA"
    run(basin)
