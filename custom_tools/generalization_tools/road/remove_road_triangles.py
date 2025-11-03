import arcpy
import os

from collections import defaultdict
from itertools import combinations
from tqdm import tqdm

from constants.n100_constants import MediumAlias
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.graph import GISGraph
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100

from generalization.n100.road.dam import get_endpoints


class RemoveRoadTriangles:
    """
    Class initializing a process to remove road triangles from a road network.
    1-cycle, 2-cycle and 3-cycle road triangles are removed based on a minimum length.
    1-cycle roads are removed first, then 2-cycle roads and finally 3-cycle roads.
    1-cycle roads are removed completely, while for 2-cycle and 3-cycle roads one or two
    of the segments are kept based on specific hierachy rules.
    """

    def __init__(
        self,
        input_line_feature: str,
        maximum_length: int,
        root_file: str,
        output_processed_feature: str,
        hierarchy_field: str = None,
        write_to_memory: bool = False,
        keep_work_files: bool = False,
    ):
        """
        Creates an instance of RemoveRoadTriangles.

        :param ...
        """
        self.input_line_feature = input_line_feature
        self.maximum_length = maximum_length
        self.root_file = root_file
        self.output_processed_feature = output_processed_feature
        self.hierarchy_field = hierarchy_field

        self.work_file_manager = WorkFileManager(
            unique_id=id(self),
            root_file=self.root_file,
            write_to_memory=write_to_memory,
            keep_files=keep_work_files,
        )

        self.copy_of_input_feature = "copy_of_input_feature"
        self.dissolved_feature = "dissolved_feature"
        self.internal_root = "internal_root"
        self.line_nodes = "line_nodes"
        self.line_1_cycle = "line_1_cycle"
        self.filtered_1_cycle_roads = "filtered_1_cycle_roads"
        self.removed_1_cycle_roads = "removed_1_cycle_roads"
        self.line_2_cycle = "line_2_cycle"
        self.filtered_2_cycle_roads = "filtered_2_cycle_roads"
        self.removed_2_cycle_roads = "removed_2_cycle_roads"
        self.line_3_cycle = "line_3_cycle"
        self.filtered_3_cycle_roads = "filtered_3_cycle_roads"
        self.removed_3_cycle_roads = "removed_3_cycle_roads"
        self.remove_layer = "remove_layer"
        self.add_layer = "add_layer"
        self.short_roads = "short_roads"

        self.gdb_files_list = [
            self.copy_of_input_feature,
            self.dissolved_feature,
            self.internal_root,
            self.line_nodes,
            self.line_1_cycle,
            self.filtered_1_cycle_roads,
            self.removed_1_cycle_roads,
            self.line_2_cycle,
            self.filtered_2_cycle_roads,
            self.removed_2_cycle_roads,
            self.line_3_cycle,
            self.filtered_3_cycle_roads,
            self.removed_3_cycle_roads,
            self.remove_layer,
            self.add_layer,
            self.short_roads,
        ]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    ###################
    # Helper functions
    ###################

    def simplify_road_network(
        self,
        input_feature: str = None,
        dissolve_feature: str = None,
        output_feature: str = None,
    ):
        """
        Dissolves the road network and creates a feature class
        with start and end points of each dissolved line.

        :param ...
        """
        dissolve_obj = DissolveWithIntersections(
            input_line_feature=input_feature,
            root_file=self.internal_root,
            output_processed_feature=dissolve_feature,
            dissolve_field_list=["MEDIUM"],
            list_of_sql_expressions=[
                f" MEDIUM = '{MediumAlias.tunnel}'",
                f" MEDIUM = '{MediumAlias.bridge}'",
                f" MEDIUM = '{MediumAlias.on_surface}'",
            ],
        )
        dissolve_obj.run()

        arcpy.management.FeatureVerticesToPoints(
            in_features=dissolve_feature,
            out_feature_class=output_feature,
            point_location="BOTH_ENDS",
        )

    def filter_short_roads(
        self,
        input_feature: str,
        output_feature: str,
        mode: int,
    ):
        """
        Selects roads or cycles with road(s) shorter than minimum length.
        If 2- or 3-cycle mode, selects cycles where at least one of the roads
        is shorter than minimum length. If no one are found, creates an empty feature class.

        :param input_feature (str): Input feature class with roads
        :param output_feature (str): Output feature class with filtered roads
        :param mode (int): Mode for cycle type (1, 2 or 3)
        """
        if mode == 1:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=input_feature,
                expression=f"Shape_Length <= {self.maximum_length}",
                output_name=output_feature,
            )
            return
        oid_to_geom = {
            oid: geom
            for oid, geom in arcpy.da.SearchCursor(input_feature, ["OID@", "SHAPE@"])
        }
        oid_geom_connections = set()
        for oid1, oid2 in combinations(oid_to_geom.keys(), 2):
            geom1 = oid_to_geom[oid1]
            geom2 = oid_to_geom[oid2]
            if geom1.intersect(geom2, 1):
                if (
                    geom1.length < self.maximum_length
                    or geom2.length < self.maximum_length
                ):
                    oid_geom_connections.add((oid1, oid2))
        oids = sorted({oid for pair in oid_geom_connections for oid in pair})
        if not oids:
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(output_feature),
                out_name=os.path.basename(output_feature),
                geometry_type="POLYLINE",
                spatial_reference=arcpy.Describe(input_feature).spatialReference,
            )
            return
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=input_feature,
            expression=f"OBJECTID IN ({','.join(map(str, oids))})",
            output_name=output_feature,
        )

    def find_geom_to_insert(
        self, oid_to_geom: dict, road_geom: arcpy.Geometry, tolerance: float = 1e-6
    ) -> arcpy.Polyline:
        """
        Gets a road geometry that should be removed and returns the corresponding equal
        or longer geometry that overlaps completely with this (within a tolerance).

        Args:
            oid_to_geom (dict): Dictionary containing road instances of longer, dissolved
            segments
            road_geometry (arcpy.Geometry): The geometry of the road instance that should
            be removed
            tolerance (float, optional): A search tolerance if there are no 100% overlap
            (default: 1e-6)

        Returns:
            arcpy.Polyline: The geometry to be removed from the original dataset
        """
        max_len = 800
        geom_to_insert = None
        for geom, length in oid_to_geom.values():
            if geom.equals(road_geom):
                if length < max_len:
                    geom_to_insert = geom
                break
            if geom.contains(road_geom):
                if not geom.touches(road_geom):
                    if length < max_len:
                        geom_to_insert = geom
                    break
            if geom.buffer(tolerance).contains(road_geom) and not geom.buffer(
                tolerance
            ).touches(road_geom):
                if length < max_len:
                    geom_to_insert = geom
                break
        return geom_to_insert

    def point_on_any_line(
        self,
        point_geom: arcpy.PointGeometry,
        line_geoms: list,
        tol: float = 0.0,
    ) -> bool:
        """
        Determine wether or not a point geometry is connected to a polyline or not.

        Args:
            point_geom (arcpy.PointGeometry): The point to be investigated
            line_geoms (list): List of information for the polylines
            tol (float, optional): A tolerance of what is categorized as connected or not
            (default: 0.0)

        Returns:
            bool: True if the point is connected to a line, False otherwise
        """
        for row in line_geoms:
            line_geom = row[1]
            if line_geom is None:
                continue
            if line_geom.distanceTo(point_geom) <= tol:
                return True
        return False

    @timing_decorator
    def select_segments_to_remove(
        self,
        road_cycles: str,
    ):
        """
        Selects which segments to remove based on hierarchy rules.

        :param road_cycles (str): Feature class with road cycles
        """
        # Fetches the original road geometries
        oid_to_geom = {
            oid: [geom, length]
            for oid, geom, length in arcpy.da.SearchCursor(
                road_cycles, ["OID@", "SHAPE@", "Shape_Length"]
            )
        }

        # Dissolves the geometries into one instance per cycle
        dissolved_fc = r"in_memory\dissolved_fc"
        arcpy.management.Dissolve(
            in_features=road_cycles,
            out_feature_class=dissolved_fc,
            dissolve_field=[],
            multi_part="SINGLE_PART",
        )

        # Fetches the original input data with correct attributes
        arcpy.management.MakeFeatureLayer(
            in_features=self.input_line_feature,
            out_layer="input_line_layer",
        )
        arcpy.management.SelectLayerByLocation(
            in_layer="input_line_layer",
            overlap_type="INTERSECT",
            select_features=dissolved_fc,
            selection_type="NEW_SELECTION",
        )

        # The dissolved geometries
        clusters = {
            oid: geom
            for oid, geom in arcpy.da.SearchCursor(dissolved_fc, ["OID@", "SHAPE@"])
        }

        single_loops = {}
        road_systems = {}
        for oid, cluster in tqdm(
            clusters.items(),
            desc="Identifies complex loops",
            colour="yellow",
            leave=False,
        ):
            start, end = get_endpoints(cluster)
            start, end = start.firstPoint, end.firstPoint
            sx, sy = round(start.X, 3), round(start.Y, 3)
            ex, ey = round(end.X, 3), round(end.Y, 3)
            if sx == ex and sy == ey:
                single_loops[oid] = cluster
            else:
                road_systems[oid] = cluster

        # Creates the new remove and add layer
        if arcpy.Exists(self.remove_layer):
            arcpy.management.Delete(self.remove_layer)
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.remove_layer),
            out_name=os.path.basename(self.remove_layer),
            geometry_type="POLYLINE",
            spatial_reference=arcpy.Describe(self.input_line_feature).spatialReference,
        )
        if arcpy.Exists(self.add_layer):
            arcpy.management.Delete(self.add_layer)
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.add_layer),
            out_name=os.path.basename(self.add_layer),
            geometry_type="POLYLINE",
            spatial_reference=arcpy.Describe(self.input_line_feature).spatialReference,
        )
        arcpy.management.AddField(self.add_layer, "medium", "TEXT")

        # Constants used for the prioritizing of the road segments
        pri_list_vegkategori = [
            "E",
            "R",
            "F",
            "K",
            "P",
            "S",
            "B",
            "T",
            "D",
            "A",
            "U",
            "G",
        ]
        vegkategori_pri = {v: i for i, v in enumerate(pri_list_vegkategori)}
        max_vegkategori_pri = len(pri_list_vegkategori)
        LARGE = 10**9

        if len(single_loops) > 0:
            # Mapping:
            # key: cycle-id
            # value: attribute info for all relevant road instances
            cluster_to_roads = defaultdict(list)
            cluster_to_roads_outside = defaultdict(list)

            with arcpy.da.SearchCursor(
                "input_line_layer",
                [
                    "OID@",
                    "SHAPE@",
                    "vegkategori",
                    "vegklasse",
                    "Shape_Length",
                    "medium",
                ],
            ) as cursor:
                for oid, geom, vegkategori, vegklasse, shape_length, medium in cursor:
                    for cluster_oid, cluster_geom in single_loops.items():
                        if cluster_geom.contains(geom):
                            cluster_to_roads[cluster_oid].append(
                                [
                                    oid,
                                    geom,
                                    vegkategori,
                                    vegklasse,
                                    shape_length,
                                    medium,
                                ]
                            )
                        elif cluster_geom.intersect(geom, 1):
                            cluster_to_roads_outside[cluster_oid].append([oid, geom])

            # For each road cycle...
            for cluster_oid, roads in tqdm(
                cluster_to_roads.items(),
                desc="Selecting segments to remove",
                colour="yellow",
                leave=False,
            ):
                # Sort the list of segments based on:
                # vegkategori, vegklasse amd length of the road instance
                roads.sort(
                    key=lambda x: (
                        vegkategori_pri.get(x[2], max_vegkategori_pri),
                        (x[3] if x[3] is not None else LARGE),
                        (x[4] if x[4] is not None else LARGE),
                    )
                )

                # The last road in the sorted list is chosen, least prioritized
                # This is the road instance from the original input data
                road_to_remove = roads[-1][1]
                # ... because of that do we need to find the processed instance
                # used during the entire process that can be removed from the network
                geom_to_insert = self.find_geom_to_insert(oid_to_geom, road_to_remove)

                if geom_to_insert is not None:
                    s, e = get_endpoints(geom_to_insert)
                    p1, p2 = s.firstPoint, e.firstPoint
                    p1 = (p1.X, p1.Y)
                    p2 = (p2.X, p2.Y)
                    endpoints = [p1, p2]

                    touching_points = set()
                    for oid, geom in cluster_to_roads_outside[cluster_oid]:
                        start, end = get_endpoints(geom)
                        pnt1 = (start.firstPoint.X, start.firstPoint.Y)
                        pnt2 = (end.firstPoint.X, end.firstPoint.Y)
                        for i, pnt in enumerate([pnt1, pnt2]):
                            if pnt not in endpoints:
                                point_geom = [start, end][i]
                                if point_geom.distanceTo(geom_to_insert) == 0:
                                    touching_points.add(pnt)

                    geom_to_keep = None

                    if len(touching_points) > 0:
                        relevant_roads = []
                        for (
                            oid,
                            geom,
                            vegkategori,
                            vegklasse,
                            shape_length,
                            medium,
                        ) in roads:
                            if geom_to_insert.contains(geom):
                                relevant_roads.append(
                                    [
                                        oid,
                                        geom,
                                        vegkategori,
                                        vegklasse,
                                        shape_length,
                                        medium,
                                    ]
                                )
                        relevant_roads.sort(
                            key=lambda x: (
                                vegkategori_pri.get(x[2], max_vegkategori_pri),
                                (x[3] if x[3] is not None else LARGE),
                                (x[4] if x[4] is not None else LARGE),
                            )
                        )
                        geom_to_keep = [relevant_roads[0][1], relevant_roads[0][-1]]
                        geom_to_insert = relevant_roads[1][1]

                    # If a road segment is found, it is inserted into the hierarchy layer
                    with arcpy.da.InsertCursor(
                        self.remove_layer, ["SHAPE@"]
                    ) as insert_cursor:
                        insert_cursor.insertRow([geom_to_insert])
                    if geom_to_keep is not None:
                        with arcpy.da.InsertCursor(
                            self.add_layer, ["SHAPE@", "medium"]
                        ) as insert_cursor:
                            insert_cursor.insertRow([geom_to_keep[0], geom_to_keep[1]])

        if len(road_systems) > 0:
            inside_roads, outside_roads = [], []

            with arcpy.da.SearchCursor(
                "input_line_layer",
                ["OID@", "SHAPE@", "vegkategori", "vegklasse", "Shape_Length"],
            ) as cursor:
                for oid, geom, vegkategori, vegklasse, shape_length in cursor:
                    added = False
                    for cluster_geom in road_systems.values():
                        if geom.within(cluster_geom):
                            inside_roads.append(
                                [oid, geom, vegkategori, vegklasse, shape_length]
                            )
                            added = True
                            break
                    if not added:
                        outside_roads.append(
                            [oid, geom, vegkategori, vegklasse, shape_length]
                        )

            roads = set()
            for _, geom_dissolved in road_systems.items():
                for oid, (geom, _) in oid_to_geom.items():
                    if geom_dissolved.contains(geom):
                        roads.add(oid)

            endpoints = {}
            for oid in roads:
                s, e = get_endpoints(oid_to_geom[oid][0])
                s, e = s.firstPoint, e.firstPoint
                p1 = (s.X, s.Y)
                p2 = (e.X, e.Y)
                endpoints[oid] = (p1, p2)

            cycles = []
            for key, (s, e) in tqdm(
                endpoints.items(),
                desc="Finding connections",
                colour="yellow",
                leave=False,
            ):
                if len(cycles) == 0:
                    cycles.append([[key, s, e]])
                    continue

                match = set()

                for i, cycle in enumerate(cycles):
                    for element in cycle:
                        _, pt_s, pt_e = element
                        if s == pt_s or s == pt_e or e == pt_s or e == pt_e:
                            match.add(i)
                match = sorted(list(match))
                if len(match) == 0:
                    cycles.append([[key, s, e]])
                elif len(match) == 1:
                    cycles[match[0]].append([key, s, e])
                else:
                    first = match[0]
                    for idx in match[1:]:
                        cycles[first].extend(cycles[idx])
                        cycles.pop(idx)
                    cycles[first].append([key, s, e])

            for cycle in cycles:
                cycle_geoms = defaultdict(list)
                for oid, s, e in cycle:
                    geom, length = oid_to_geom[oid]
                    cycle_geoms[oid] = [geom, length, s, e]
                for oid, data in cycle_geoms.items():
                    geom, length, s_pnt, e_pnt = data
                    sr = geom.spatialReference
                    pt1 = arcpy.Point(s_pnt[0], s_pnt[1])
                    pt2 = arcpy.Point(e_pnt[0], e_pnt[1])
                    s_geom = arcpy.PointGeometry(pt1, sr)
                    e_geom = arcpy.PointGeometry(pt2, sr)
                    start_bool = self.point_on_any_line(s_geom, outside_roads)
                    end_bool = self.point_on_any_line(e_geom, outside_roads)
                    if start_bool and end_bool:
                        cycle_geoms[oid].extend([0, start_bool, end_bool])
                    elif start_bool or end_bool:
                        cycle_geoms[oid].extend([1, start_bool, end_bool])
                    else:
                        cycle_geoms[oid].extend([2, start_bool, end_bool])

                seen, remove, connected = set(), set(), set()

                for oid, data in cycle_geoms.items():
                    _, _, s, e, pri, _, _ = data
                    if pri == 0:
                        seen.add(oid)
                        connected.add(s)
                        connected.add(e)
                    elif pri == 2:
                        seen.add(oid)
                        remove.add(oid)

                shortest = []

                for oid1, oid2 in combinations(cycle_geoms.keys(), 2):
                    data1, data2 = cycle_geoms[oid1], cycle_geoms[oid2]
                    _, len1, s1, e1, pri1, sb1, eb1 = data1
                    _, len2, s2, e2, pri2, sb2, eb2 = data2

                    if pri1 != 1 or pri2 != 1:
                        continue

                    connect = [s1 == s2, s1 == e2, e1 == s2, e1 == e2]
                    if not any(statement for statement in connect):
                        continue

                    connecting_points = [
                        [e1, e2, sb1, sb2],
                        [e1, s2, sb1, eb2],
                        [s1, e2, eb1, sb2],
                        [s1, s2, eb1, eb2],
                    ]
                    try:
                        idx = next(i for i, v in enumerate(connect) if v)
                    except StopIteration:
                        continue
                    if all(pnt in connected for pnt in connecting_points[idx][:2]):
                        continue
                    if (
                        connecting_points[idx][2]
                        and connecting_points[idx][2] == connecting_points[idx][3]
                    ):
                        continue

                    if len(shortest) == 0:
                        shortest.append([oid1, oid2, len1 + len2])
                    elif len1 + len2 < shortest[0][-1]:
                        if shortest[0][-1] > (len1 + len2) * 2:
                            shortest.append(shortest[0])
                        shortest[0] = [oid1, oid2, len1 + len2]
                    elif len1 + len2 < shortest[0][-1] * 2:
                        shortest.append([oid1, oid2, len1 + len2])

                short_oids = set()

                if len(shortest) > 0:
                    the_shortest = shortest[0][2]
                    for i, elem in enumerate(shortest):
                        if i == 0:
                            for oid in elem[:2]:
                                short_oids.add(oid)
                        if elem[2] > the_shortest * 2:
                            for oid in elem[:2]:
                                short_oids.add(oid)

                for oid in cycle_geoms.keys():
                    if oid in seen or oid in short_oids:
                        continue
                    remove.add(oid)

                with arcpy.da.InsertCursor(
                    self.remove_layer, ["SHAPE@"]
                ) as insert_cursor:
                    for oid in remove:
                        insert_cursor.insertRow([oid_to_geom[oid][0]])

        # Remove the used intermediate layer
        if arcpy.Exists(dissolved_fc):
            arcpy.management.Delete(dissolved_fc)

    ###################
    # Main functions
    ###################

    @timing_decorator
    def remove_1_cycle_roads(self):
        """
        Detects and removes 1-cycle roads from the road network.
        """
        self.simplify_road_network(
            input_feature=self.copy_of_input_feature,
            dissolve_feature=self.dissolved_feature,
            output_feature=self.line_nodes,
        )

        detect_1_cycle_roads = GISGraph(
            input_path=self.line_nodes,
            object_id="OBJECTID",
            original_id="ORIG_FID",
            geometry_field="SHAPE",
        )

        road_1_cycle_sql = detect_1_cycle_roads.select_1_cycle()

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            expression=road_1_cycle_sql,
            output_name=self.line_1_cycle,
        )

        self.filter_short_roads(
            input_feature=self.line_1_cycle,
            output_feature=self.filtered_1_cycle_roads,
            mode=1,
        )

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            overlap_type=custom_arcpy.OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
            select_features=self.filtered_1_cycle_roads,
            output_name=self.removed_1_cycle_roads,
            inverted=True,
        )
        print()

    @timing_decorator
    def remove_2_cycle_roads(self):
        """
        Detects and removes 2-cycle roads from the road network
        based on the network with removed 1-cycle roads.
        """
        print()
        self.simplify_road_network(
            input_feature=self.removed_1_cycle_roads,
            dissolve_feature=self.dissolved_feature,
            output_feature=self.line_nodes,
        )

        detect_2_cycle_roads = GISGraph(
            input_path=self.line_nodes,
            object_id="OBJECTID",
            original_id="ORIG_FID",
            geometry_field="SHAPE",
        )

        road_2_cycle_sql = detect_2_cycle_roads.select_2_cycle()

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            expression=road_2_cycle_sql,
            output_name=self.line_2_cycle,
        )

        self.filter_short_roads(
            input_feature=self.line_2_cycle,
            output_feature=self.filtered_2_cycle_roads,
            mode=2,
        )

        print()
        self.select_segments_to_remove(self.filtered_2_cycle_roads)
        print()

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            overlap_type=custom_arcpy.OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
            select_features=self.remove_layer,
            output_name=self.removed_2_cycle_roads,
            inverted=True,
        )

        if arcpy.Exists(self.add_layer):
            add_geoms = [
                [geom, medium]
                for geom, medium in arcpy.da.SearchCursor(
                    self.add_layer, ["SHAPE@", "medium"]
                )
            ]

            with arcpy.da.InsertCursor(
                self.removed_2_cycle_roads, ["SHAPE@", "medium"]
            ) as insert:
                for add_geom in add_geoms:
                    insert.insertRow(add_geom)

        print()

    @timing_decorator
    def remove_3_cycle_roads(self):
        """
        Detects and removes 3-cycle roads from the road network
        based on the network with removed 1- and 2-cycle roads.
        """
        print()
        self.simplify_road_network(
            input_feature=self.removed_2_cycle_roads,
            dissolve_feature=self.dissolved_feature,
            output_feature=self.line_nodes,
        )

        detect_3_cycle_roads = GISGraph(
            input_path=self.line_nodes,
            object_id="OBJECTID",
            original_id="ORIG_FID",
            geometry_field="SHAPE",
        )

        road_3_cycle_sql = detect_3_cycle_roads.select_3_cycle()

        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            expression=road_3_cycle_sql,
            output_name=self.line_3_cycle,
        )

        self.filter_short_roads(
            input_feature=self.line_3_cycle,
            output_feature=self.filtered_3_cycle_roads,
            mode=3,
        )

        print()
        self.select_segments_to_remove(self.filtered_3_cycle_roads)
        print()

        custom_arcpy.select_location_and_make_permanent_feature(
            input_layer=self.dissolved_feature,
            overlap_type=custom_arcpy.OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
            select_features=self.remove_layer,
            output_name=self.removed_3_cycle_roads,
            inverted=True,
        )

        if arcpy.Exists(self.add_layer):
            add_geoms = [
                [geom, medium]
                for geom, medium in arcpy.da.SearchCursor(
                    self.add_layer, ["SHAPE@", "medium"]
                )
            ]

            with arcpy.da.InsertCursor(
                self.removed_3_cycle_roads, ["SHAPE@", "medium"]
            ) as insert:
                for add_geom in add_geoms:
                    insert.insertRow(add_geom)

        print()

    @timing_decorator
    def run(self):
        """
        Runs the complete process to remove road triangles.
        1-cycle, 2-cycle and 3-cycle road triangles are removed based on a minimum length.
        1-cycle roads are removed completely first, then 2-cycle roads and finally
        3-cycle roads partly to keep a complete road network.
        """
        arcpy.management.CopyFeatures(
            in_features=self.input_line_feature,
            out_feature_class=self.copy_of_input_feature,
        )

        self.remove_1_cycle_roads()
        self.remove_2_cycle_roads()
        self.remove_3_cycle_roads()


# Main function to be imported in other .py-files
def generalize_road_triangles():
    """
    Runs the RemoveRoadTriangles process with predefined parameters.
    """
    environment_setup.main()
    remove_road_triangles = RemoveRoadTriangles(
        input_line_feature=Road_N100.data_preparation___smooth_road___n100_road.value,
        maximum_length=500,
        root_file=Road_N100.testing_file___remove_triangles_root___n100_road.value,
        output_processed_feature=Road_N100.testing_file___removed_triangles___n100_road.value,
    )
    remove_road_triangles.run()


if __name__ == "__main__":
    generalize_road_triangles()
