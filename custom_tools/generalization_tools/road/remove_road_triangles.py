import arcpy
import os

from collections import defaultdict
from itertools import combinations
from tqdm import tqdm

from composition_configs import core_config, logic_config
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
        remove_road_triangles_config: logic_config.RemoveRoadTrianglesKwargs,
    ):
        """
        Creates an instance of RemoveRoadTriangles.

        Args:
            remove_road_triangles_config (RemoveRoadTrianglesKwargs):
            A config instance setting up the structure of files and tolerances for the
            remove road triangle instance
        """
        self.input_line_feature = remove_road_triangles_config.input_line_feature
        self.maximum_length = remove_road_triangles_config.maximum_length
        self.root_file = remove_road_triangles_config.root_file
        self.output_processed_feature = (
            remove_road_triangles_config.output_processed_feature
        )
        self.hierarchy_field = remove_road_triangles_config.hierarchy_field

        self.work_file_manager = WorkFileManager(
            config=remove_road_triangles_config.work_file_manager_config
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
    ) -> None:
        """
        Dissolves the road network and creates a feature class
        with start and end points of each dissolved line.

        Args:
            input_feature (str): The polyline layer to simplify
            dissolve_feature (str): Polyline layer to store the dissolved roads
            output_feature (str): Point layer to store the endpoints for all the dissolved features
        """
        config = logic_config.DissolveInitKwargs(
            input_line_feature=input_feature,
            output_processed_feature=dissolve_feature,
            work_file_manager_config=core_config.WorkFileConfig(self.internal_root),
            dissolve_fields=["MEDIUM"],
            sql_expressions=[
                f" MEDIUM = '{MediumAlias.tunnel}'",
                f" MEDIUM = '{MediumAlias.bridge}'",
                f" MEDIUM = '{MediumAlias.on_surface}'",
            ],
        )

        dissolve_obj = DissolveWithIntersections(dissolve_intersections_config=config)

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
    ) -> None:
        """
        Selects roads or cycles with road(s) shorter than minimum length.
        If 2- or 3-cycle mode, selects cycles where at least one of the roads
        is shorter than minimum length. If no one are found, creates an empty feature class.

        Args:
            input_feature (str): Input feature class with roads
            output_feature (str): Output feature class with filtered roads
            mode (int): Mode for cycle type (1, 2 or 3)
        """
        # If working with 1-cycle roads: return a simple query
        if mode == 1:
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=input_feature,
                expression=f"Shape_Length <= {self.maximum_length}",
                output_name=output_feature,
            )
            return
        # Otherwise:
        # Find the geometries
        oid_to_geom = {
            oid: geom
            for oid, geom in arcpy.da.SearchCursor(input_feature, ["OID@", "SHAPE@"])
        }
        # Match all combinations of two roads...
        oid_geom_connections = set()
        for oid1, oid2 in combinations(oid_to_geom.keys(), 2):
            geom1 = oid_to_geom[oid1]
            geom2 = oid_to_geom[oid2]
            # ... if they intersect ...
            if geom1.intersect(geom2, 1):
                # ... and at least one of them is short enough
                if (
                    geom1.length < self.maximum_length
                    or geom2.length < self.maximum_length
                ):
                    oid_geom_connections.add((oid1, oid2))
        # Sort and delete duplicates of matched oids that is a valid cycle
        oids = sorted({oid for pair in oid_geom_connections for oid in pair})
        if not oids:
            # If no valid cycle detected -> return an empty featureclass
            arcpy.management.CreateFeatureclass(
                out_path=os.path.dirname(output_feature),
                out_name=os.path.basename(output_feature),
                geometry_type="POLYLINE",
                spatial_reference=arcpy.Describe(input_feature).spatialReference,
            )
            return
        # Otherwise:
        # Return a query with those that are valid
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=input_feature,
            expression=f"OBJECTID IN ({','.join(map(str, oids))})",
            output_name=output_feature,
        )

    ######################################################
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

    ######################################################

    def sort_prioritized_hierarchy(self, roads: list) -> list:
        """
        Sort the list of road features according to the wanted hierarchy components.

        IMPORTANT:
        The list must be ordered in such a way that the first instance of the internal lists
        is "vegkategori", the second must be "vegklasse" and the third "ShapeLength". The
        internal lists can be arbitrary long as long as these first three are represented.

        Args:
            roads (list): List of road elements

        Returns:
            list: The same list as input, but sorted according to the hierarchy fields
        """
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

        roads.sort(
            key=lambda x: (
                vegkategori_pri.get(x[0], max_vegkategori_pri),
                (x[1] if x[1] is not None else LARGE),
                (x[2] if x[2] is not None else LARGE),
            )
        )
        return roads

    @timing_decorator
    def select_segments_to_remove_2_cycle_roads(
        self, road_cycles: str, working_fc: str
    ) -> None:
        """
        Selects which segments to remove based on hierarchy rules.

        Args:
            road_cycles (str): Feature class with road cycles
            working_fc (str): Feature class containing the remaining segments in the whole network
        """

        def endpoints_of(geom):
            s, e = get_endpoints(geom)
            s, e = s.firstPoint, e.firstPoint
            return (round(s.X, 3), round(s.Y, 3)), (round(e.X, 3), round(e.Y, 3))

        # Fetch the cycle-data
        oid_to_geom = {
            oid: geom
            for oid, geom in arcpy.da.SearchCursor(road_cycles, ["OID@", "SHAPE@"])
        }
        # ... and creates a dictionary keeping the
        # most relevant hierarchy for that section
        oid_to_data = defaultdict(list)

        arcpy.management.MakeFeatureLayer(
            in_features=self.input_line_feature, out_layer="original_data_layer"
        )

        for oid, geom in oid_to_geom.items():
            geom_fc = f"in_memory/tmp_geom_fc_{oid}"
            arcpy.management.CreateFeatureclass(
                os.path.dirname(geom_fc),
                os.path.basename(geom_fc),
                "POLYLINE",
                spatial_reference=geom.spatialReference,
            )
            with arcpy.da.InsertCursor(geom_fc, ["SHAPE@"]) as insert:
                insert.insertRow([geom])

            arcpy.management.SelectLayerByLocation(
                in_layer="original_data_layer",
                overlap_type="SHARE_A_LINE_SEGMENT_WITH",
                select_features=geom_fc,
                selection_type="NEW_SELECTION",
            )
            with arcpy.da.SearchCursor(
                "original_data_layer", ["vegkategori", "vegklasse", "Shape_Length"]
            ) as search:
                for row in search:
                    oid_to_data[oid].append([row[0], row[1], row[2]])

            if arcpy.Exists(geom_fc):
                arcpy.management.Delete(geom_fc)

        for oid, data in oid_to_data.items():
            oid_to_data[oid] = self.sort_prioritized_hierarchy(data)[-1]

        # Dissolves the cycle-instances
        dissolved_fc = r"in_memory/dissolved_fc"
        arcpy.management.Dissolve(
            in_features=road_cycles,
            out_feature_class=dissolved_fc,
            dissolve_field=[],
            multi_part="SINGLE_PART",
        )

        remove_geoms = []
        add_geoms = []

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

        with arcpy.da.SearchCursor(dissolved_fc, ["SHAPE@"]) as search:
            for row in search:
                geom = row[0]
                overlap = []

                for o_oid, o_geom in oid_to_geom.items():
                    if geom.contains(o_geom):
                        overlap.append([o_oid, o_geom])
                for i, (oid, o_geom) in enumerate(overlap):
                    base = list(oid_to_data.get(oid, []))
                    base.extend([oid, o_geom])
                    if len(base) == 5:
                        overlap[i] = base
                chosen = self.sort_prioritized_hierarchy(overlap)[-1]
                chosen_geom = chosen[-1]

                geom_fc = r"in_memory/tmp_geom_fc"
                arcpy.management.CreateFeatureclass(
                    os.path.dirname(geom_fc),
                    os.path.basename(geom_fc),
                    "POLYLINE",
                    spatial_reference=chosen_geom.spatialReference,
                )
                with arcpy.da.InsertCursor(geom_fc, ["SHAPE@"]) as insert:
                    insert.insertRow([chosen_geom])

                arcpy.management.SelectLayerByLocation(
                    in_layer="original_data_layer",
                    overlap_type="SHARE_A_LINE_SEGMENT_WITH",
                    select_features=working_fc,
                    selection_type="NEW_SELECTION",
                )
                arcpy.management.SelectLayerByLocation(
                    in_layer="original_data_layer",
                    overlap_type="INTERSECT",
                    select_features=geom_fc,
                    selection_type="SUBSET_SELECTION",
                )

                orig_s, orig_e = endpoints_of(chosen_geom)
                start_endpoints = {orig_s, orig_e}
                inside_geoms = []
                outside_geoms = set()

                with arcpy.da.SearchCursor(
                    "original_data_layer",
                    ["SHAPE@", "vegkategori", "vegklasse", "Shape_Length", "medium"],
                ) as sc:
                    for g, kategori, klasse, lengde, medium in sc:
                        if chosen_geom.contains(g):
                            inside_geoms.append([kategori, klasse, lengde, medium, g])
                        else:
                            other_s, other_e = endpoints_of(g)
                            s, e = get_endpoints(g)
                            s, e = s.firstPoint, e.firstPoint
                            if chosen_geom.distanceTo(s) == 0:
                                if other_s not in start_endpoints:
                                    outside_geoms.add(other_s)
                            elif chosen_geom.distanceTo(e) == 0:
                                if other_e not in start_endpoints:
                                    outside_geoms.add(other_e)

                remove_geoms.append(chosen_geom)

                if len(outside_geoms) > 0:
                    inside_geoms = self.sort_prioritized_hierarchy(inside_geoms)
                    pri_geom = inside_geoms[0][-1]
                    add_geoms.append([pri_geom, inside_geoms[0][-2]])
                    start_s, start_e = endpoints_of(pri_geom)
                    endpoints = {start_s, start_e}

                    changed = True
                    used = set()
                    used.add(0)

                    while changed:
                        changed = False

                        for idx, inside in enumerate(inside_geoms):
                            if idx in used:
                                continue
                            s_tuple, e_tuple = endpoints_of(inside[-1])
                            if s_tuple in endpoints or e_tuple in endpoints:
                                if s_tuple in endpoints:
                                    shared = s_tuple
                                    other = e_tuple
                                else:
                                    shared = e_tuple
                                    other = s_tuple
                                if shared in outside_geoms:
                                    continue
                                used.add(idx)
                                add_geoms.append([inside[-1], inside[-2]])
                                endpoints.add(other)
                                changed = True

                if arcpy.Exists(geom_fc):
                    arcpy.management.Delete(geom_fc)

        with arcpy.da.InsertCursor(self.remove_layer, ["SHAPE@"]) as insert_cursor:
            for geom in remove_geoms:
                insert_cursor.insertRow([geom])

        if len(add_geoms) > 0:
            with arcpy.da.InsertCursor(
                self.add_layer, ["SHAPE@", "medium"]
            ) as insert_cursor:
                for geom, medium in add_geoms:
                    insert_cursor.insertRow([geom, medium])

        if arcpy.Exists(dissolved_fc):
            arcpy.management.Delete(dissolved_fc)

    ###################
    # Main functions
    ###################

    @timing_decorator
    def remove_islands_and_small_dead_ends(self, edit_fc: str) -> None:
        """
        Detects and removes islands and dead ends from the road network.

        Args:
            edit_fc (str): Featureclass with the data that should be edited
        """
        count = None
        first, first_count = True, None
        k = 0

        # As long as new dead ends are detected -> search again
        while count != 0:
            k += 1

            # Simplifies the road with dissolve, and collect
            # both endpoints for all road instances
            self.simplify_road_network(
                input_feature=edit_fc,
                dissolve_feature=self.dissolved_feature,
                output_feature=self.line_nodes,
            )

            # Count the number of connected roads for all endpoints
            endpoints = {}
            with arcpy.da.SearchCursor(self.line_nodes, ["SHAPE@"]) as search:
                for row in search:
                    pnt = row[0].firstPoint
                    endpoints[(pnt.X, pnt.Y)] = endpoints.get((pnt.X, pnt.Y), 0) + 1

            intermediate_count, count = 0, 0

            # For each road instance in the input -> check for islands or dead ends
            with arcpy.da.UpdateCursor(self.dissolved_feature, ["SHAPE@"]) as update:
                for row in update:
                    intermediate_count += 1
                    geom = row[0]
                    start, end = get_endpoints(geom)
                    start, end = start.firstPoint, end.firstPoint
                    sx, sy, ex, ey = start.X, start.Y, end.X, end.Y
                    # If both end points are lonely: island
                    if (
                        endpoints.get((sx, sy), 0) == 1
                        and endpoints.get((ex, ey), 0) == 1
                    ):
                        update.deleteRow()
                        count += 1
                    # If one of the ends is lonely...
                    elif (
                        endpoints.get((sx, sy), 0) == 1
                        or endpoints.get((ex, ey), 0) == 1
                    ):
                        # ... and the instance is short enough: dead end
                        if geom.length < self.maximum_length:
                            update.deleteRow()
                            count += 1

            # Update the working file, and repeat if changes
            edit_fc = self.dissolved_feature

            if first:
                first = False
                first_count = intermediate_count

            if count == 1:
                print(f"Removed {count} island / dead end.")
            else:
                print(f"Removed {count} islands and dead ends.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        intermediate_count = intermediate_count if intermediate_count else first_count
        print(f"Number of roads in the end: {intermediate_count}\n")

    @timing_decorator
    def remove_1_cycle_roads(self) -> None:
        """
        Detects and removes 1-cycle roads from the road network.
        """
        count = None
        edit_fc = self.dissolved_feature
        first, first_count = True, None
        k = 0

        # As long as new 1-cycle roads are detected -> search again
        while count != 0:
            k += 1

            # Simplifies the road with dissolve, and collect
            # both endpoints for all road instances
            self.simplify_road_network(
                input_feature=edit_fc,
                dissolve_feature=self.dissolved_feature,
                output_feature=self.line_nodes,
            )

            if first:
                first = False
                first_count = int(arcpy.management.GetCount(self.dissolved_feature)[0])

            # Create the GISGraph instance
            detect_1_cycle_roads = GISGraph(
                input_path=self.line_nodes,
                object_id="OBJECTID",
                original_id="ORIG_FID",
                geometry_field="SHAPE",
            )

            # Detect the 1-cycle roads
            road_1_cycle_sql = detect_1_cycle_roads.select_1_cycle()

            # Create a specific layer with these instances
            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.dissolved_feature,
                expression=road_1_cycle_sql,
                output_name=self.line_1_cycle,
            )

            # Filter the roads so that only the valid once
            # (those that are short enough) are kept
            self.filter_short_roads(
                input_feature=self.line_1_cycle,
                output_feature=self.filtered_1_cycle_roads,
                mode=1,
            )

            count = int(arcpy.management.GetCount(self.filtered_1_cycle_roads)[0])

            # Select the instances to work further with
            custom_arcpy.select_location_and_make_permanent_feature(
                input_layer=self.dissolved_feature,
                overlap_type=custom_arcpy.OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                select_features=self.filtered_1_cycle_roads,
                output_name=self.removed_1_cycle_roads,
                inverted=True,
            )

            # Update the working file, and repeat if changes
            edit_fc = self.removed_1_cycle_roads

            if count == 1:
                print(f"Removed {count} 1-cycle road.")
            else:
                print(f"Removed {count} 1-cycle roads.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        end_count = int(arcpy.management.GetCount(self.removed_1_cycle_roads)[0])
        print(f"Number of roads in the end: {end_count}\n")

    """
    @timing_decorator
    def remove_1_cycle_roads(self):
        
        Detects and removes 1-cycle roads from the road network.
        
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
    """

    @timing_decorator
    def remove_2_cycle_roads(self) -> None:
        """
        Detects and removes 2-cycle roads from the road network
        based on the network with removed 1-cycle roads.
        """
        count = None
        edit_fc = self.dissolved_feature
        first, first_count = True, None
        k = 0

        # As long as new 2-cycle roads are detected -> search again
        while count != 0:
            k += 1

            # Simplifies the road with dissolve, and collect
            # both endpoints for all road instances
            self.simplify_road_network(
                input_feature=edit_fc,
                dissolve_feature=self.dissolved_feature,
                output_feature=self.line_nodes,
            )

            if first:
                first = False
                first_count = int(arcpy.management.GetCount(self.dissolved_feature)[0])

            # Create the GISGraph instance
            detect_2_cycle_roads = GISGraph(
                input_path=self.line_nodes,
                object_id="OBJECTID",
                original_id="ORIG_FID",
                geometry_field="SHAPE",
            )

            # Detect the 2-cycle roads
            road_2_cycle_sql = detect_2_cycle_roads.select_2_cycle()

            if road_2_cycle_sql:
                # Create a specific layer with these instances
                custom_arcpy.select_attribute_and_make_permanent_feature(
                    input_layer=self.dissolved_feature,
                    expression=road_2_cycle_sql,
                    output_name=self.line_2_cycle,
                )

                # Filter the roads so that only the valid once
                # (those that are short enough) are kept
                self.filter_short_roads(
                    input_feature=self.line_2_cycle,
                    output_feature=self.filtered_2_cycle_roads,
                    mode=2,
                )

                print()
                self.select_segments_to_remove_2_cycle_roads(
                    self.filtered_2_cycle_roads, edit_fc
                )
                print()

                count = int(arcpy.management.GetCount(self.remove_layer)[0])

                # Select the instances to work further with
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

                # Update the working file, and repeat if changes
                edit_fc = self.removed_2_cycle_roads
            else:
                count = 0
                arcpy.management.CopyFeatures(
                    in_features=self.dissolved_feature,
                    out_feature_class=self.removed_2_cycle_roads,
                )

            if count == 1:
                print(f"Removed {count} 2-cycle road.")
            else:
                print(f"Removed {count} 2-cycle roads.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        end_count = int(arcpy.management.GetCount(self.removed_2_cycle_roads)[0])
        print(f"Number of roads in the end: {end_count}\n")

    """
    @timing_decorator
    def remove_2_cycle_roads(self):
        
        Detects and removes 2-cycle roads from the road network
        based on the network with removed 1-cycle roads.
        
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
    """

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
    def fetch_original_data(self):
        """
        Capture the original data that should be included in the network
        and creates a copy of this data in a new featureclass.
        """
        output_fc = Road_N100.road_triangles_output.value
        intermediate_fc = r"in_memory/intermediate_fc"

        arcpy.management.MakeFeatureLayer(
            in_features=self.copy_of_input_feature, out_layer="original_roads_lyr"
        )
        arcpy.management.MakeFeatureLayer(
            in_features=self.removed_3_cycle_roads, out_layer="processed_roads_lyr"
        )

        arcpy.analysis.Erase(
            in_features="original_roads_lyr",
            erase_features="processed_roads_lyr",
            out_feature_class=intermediate_fc,
        )
        arcpy.analysis.Erase(
            in_features="original_roads_lyr",
            erase_features=intermediate_fc,
            out_feature_class=output_fc,
        )

    @timing_decorator
    def run(self) -> None:
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

        print("\nRemoves road cycles\n")
        self.remove_islands_and_small_dead_ends(edit_fc=self.input_line_feature)
        self.remove_1_cycle_roads()
        self.remove_islands_and_small_dead_ends(edit_fc=self.removed_1_cycle_roads)
        self.remove_2_cycle_roads()
        self.remove_islands_and_small_dead_ends(edit_fc=self.removed_2_cycle_roads)
        self.remove_3_cycle_roads()
        return

        self.remove_1_cycle_roads()
        self.remove_2_cycle_roads()
        self.remove_3_cycle_roads()
        self.fetch_original_data()


# Main function to be imported in other .py-files
@timing_decorator
def generalize_road_triangles() -> None:
    """
    Runs the RemoveRoadTriangles process with predefined parameters.
    """
    environment_setup.main()
    config = logic_config.RemoveRoadTrianglesKwargs(
        input_line_feature=Road_N100.data_preparation___simplified_road___n100_road.value,
        work_file_manager_config=core_config.WorkFileConfig(
            Road_N100.testing_file___remove_triangles_root___n100_road.value
        ),
        maximum_length=500,
        root_file=Road_N100.testing_file___remove_triangles_root___n100_road.value,
        output_processed_feature=Road_N100.testing_file___removed_triangles___n100_road.value,
    )
    remove_road_triangles = RemoveRoadTriangles(config)
    remove_road_triangles.run()


if __name__ == "__main__":
    generalize_road_triangles()
