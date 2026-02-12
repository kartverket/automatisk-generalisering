import arcpy
import os
import time

from collections import defaultdict
from itertools import combinations

from composition_configs import core_config, logic_config
from custom_tools.general_tools.partition_iterator import PartitionIterator
from constants.n100_constants import FieldNames_str, MediumAlias, NvdbAlias
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.custom_arcpy import OverlapType, SelectionType
from custom_tools.general_tools.graph import GISGraph
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100
from file_manager.n250.file_manager_roads import Road_N250

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
        self.intermediate_original = "intermediate_original"
        self.line_1_cycle = "line_1_cycle"
        self.filtered_1_cycle_roads = "filtered_1_cycle_roads"
        self.removed_1_cycle_roads = "removed_1_cycle_roads"
        self.line_2_cycle = "line_2_cycle"
        self.filtered_2_cycle_roads = "filtered_2_cycle_roads"
        self.removed_2_cycle_roads = "removed_2_cycle_roads"
        self.line_3_cycle = "line_3_cycle"
        self.filtered_3_cycle_roads = "filtered_3_cycle_roads"
        self.removed_3_cycle_roads = "removed_3_cycle_roads"
        self.line_4_cycle = "line_4_cycle"
        self.filtered_4_cycle_roads = "filtered_4_cycle_roads"
        self.removed_4_cycle_roads = "removed_4_cycle_roads"
        self.remove_layer = "remove_layer"
        self.add_layer = "add_layer"
        self.short_roads = "short_roads"

        self.gdb_files_list = [
            self.copy_of_input_feature,
            self.dissolved_feature,
            self.internal_root,
            self.line_nodes,
            self.intermediate_original,
            self.line_1_cycle,
            self.filtered_1_cycle_roads,
            self.removed_1_cycle_roads,
            self.line_2_cycle,
            self.filtered_2_cycle_roads,
            self.removed_2_cycle_roads,
            self.line_3_cycle,
            self.filtered_3_cycle_roads,
            self.removed_3_cycle_roads,
            self.line_4_cycle,
            self.filtered_4_cycle_roads,
            self.removed_4_cycle_roads,
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

    def fetch_original_data(self, input: str, output: str):
        """
        Capture the original data that should be included in the network
        and creates a copy of this data in a new featureclass.

        Args:
            input (str): The feature class with segments to keep
            output (str): The feature class where the output should be saved
        """
        intermediate_fc = r"in_memory/intermediate_fc"

        # Creates feature layers for the original data and the current data
        arcpy.management.MakeFeatureLayer(
            in_features=self.copy_of_input_feature, out_layer="original_roads_lyr"
        )
        arcpy.management.MakeFeatureLayer(
            in_features=input, out_layer="processed_roads_lyr"
        )

        # Deletes the geometries that we want to keep from the
        # original data and store these in the intermediate layer
        arcpy.analysis.Erase(
            in_features="original_roads_lyr",
            erase_features="processed_roads_lyr",
            out_feature_class=intermediate_fc,
        )

        time.sleep(0.5)  # Short wait to be sure to not crash

        # Erase the created intermediate layer from the original
        # data so that the result is the wanted data only
        arcpy.analysis.Erase(
            in_features="original_roads_lyr",
            erase_features=intermediate_fc,
            out_feature_class=output,
        )

    def simplify_road_network(
        self,
        input_feature: str = None,
        dissolve_feature: str = None,
        output_feature: str = None,
        dead_ends: bool = False,
    ) -> None:
        """
        Dissolves the road network and creates a feature class
        with start and end points of each dissolved line.

        Args:
            input_feature (str): The polyline layer to simplify
            dissolve_feature (str): Polyline layer to store the dissolved roads
            output_feature (str): Point layer to store the endpoints for all the dissolved features
            dead_ends (bool): Boolean telling if it works with the dead ends function
        """
        # Dissolves the input data with medium as the deciding attribute
        config = logic_config.DissolveInitKwargs(
            input_line_feature=input_feature,
            output_processed_feature=dissolve_feature,
            work_file_manager_config=core_config.WorkFileConfig(self.internal_root),
            dissolve_fields=[FieldNames_str.medium.upper()],
            sql_expressions=[
                f" {FieldNames_str.medium.upper()} = '{MediumAlias.tunnel}'",
                f" {FieldNames_str.medium.upper()} = '{MediumAlias.bridge}'",
                f" {FieldNames_str.medium.upper()} = '{MediumAlias.on_surface}'",
            ],
        )

        dissolve_obj = DissolveWithIntersections(dissolve_intersections_config=config)

        dissolve_obj.run()

        # If we are working with the dead ends:
        if dead_ends:
            # Fetches the original data that matches with the data that are left
            self.fetch_original_data(
                input=dissolve_feature, output=self.intermediate_original
            )

            # ... and fetches the endpoints of this data
            arcpy.management.FeatureVerticesToPoints(
                in_features=self.intermediate_original,
                out_feature_class=output_feature,
                point_location="BOTH_ENDS",
            )
        else:
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

    def endpoints_of(self, geom: arcpy.Geometry, num: int = 3) -> tuple:
        """
        Returns rounded coordinates for the endpoints of the geom.

        Args:
            geom (arcpy.Geometry): The geometry to fetch endpoints
            num (int, optional): Number of wanted decimals, default: 3

        Returns:
            tuple: The X- and Y-coordinate of the endpoints to the geometry
        """
        s, e = get_endpoints(geom)
        s, e = s.firstPoint, e.firstPoint
        if num is None:
            # If num is None we want the original data without the round(...) operation
            return (s.X, s.Y), (e.X, e.Y)
        # Otherwise round to the desired number of decimals, default = 3
        return (round(s.X, num), round(s.Y, num)), (round(e.X, num), round(e.Y, num))

    def get_geoms(self, FeatureClass: str) -> dict:
        """
        Returns a dictionary with all the geometries in the featureclass.

        Args:
            FeatureClass (str): FeatureClass with objects

        Returns:
            dict: key = oid, val = [geom, length] -> for all the geometries in FeatureClass
        """
        return {
            oid: [geom, length]
            for oid, geom, length in arcpy.da.SearchCursor(
                FeatureClass, ["OID@", "SHAPE@", "Shape_Length"]
            )
        }

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
            NvdbAlias.europaveg,
            NvdbAlias.riksveg,
            NvdbAlias.fylkesveg,
            NvdbAlias.kommunalveg,
            NvdbAlias.privatveg,
            NvdbAlias.skogsveg,
            NvdbAlias.barmarksløype,
            NvdbAlias.traktorveg,
            NvdbAlias.sti_dnt,
            NvdbAlias.sti_andre,
            NvdbAlias.sti_umerket,
            NvdbAlias.gang_og_sykkelveg,
        ]
        vegkategori_pri = {
            v: i for i, v in enumerate(pri_list_vegkategori)
        }  # Mapping dictionary from text to integers
        max_vegkategori_pri = len(
            pri_list_vegkategori
        )  # If no specified, default value to lowest priority
        LARGE = 10**9

        # Sort the incomming list against the hierarchy values
        roads.sort(
            key=lambda x: (
                vegkategori_pri.get(x[0], max_vegkategori_pri),
                (x[1] if x[1] is not None else LARGE),
                (x[2] if x[2] is not None else LARGE),
            )
        )
        return roads

    def get_geom_data(self, oid_to_geom: dict) -> defaultdict:
        """
        Fetches relevant data for the hierarchy and returns it as a dictionary.

        Args:
            oid_to_geom (dict): Dictionary containing all the relevant geometries

        Returns:
            defaultdict(list): Dictionary with 'vegkategori', 'vegklasse' and 'length' for all geometries
        """
        oid_to_data = defaultdict(list)

        arcpy.management.MakeFeatureLayer(  # Fetch original data
            in_features=self.copy_of_input_feature, out_layer="original_data_layer"
        )

        # Create temporarly layer for selection
        temp_fc = r"in_memory/tmp_geom_fc"
        if arcpy.Exists(temp_fc):
            arcpy.management.Delete(temp_fc)

        first_geom = next(iter(oid_to_geom.values()))[0]
        arcpy.management.CreateFeatureclass(
            "in_memory",
            "tmp_geom_fc",
            "POLYLINE",
            spatial_reference=first_geom.spatialReference,
        )

        try:
            for oid, (geom, length) in oid_to_geom.items():
                # Delete existing rows in the layer
                with arcpy.da.UpdateCursor(temp_fc, ["SHAPE@"]) as update:
                    for _ in update:
                        update.deleteRow()
                # Insert the geometry (the dissolved pieces in each cycle) in the new layer
                with arcpy.da.InsertCursor(temp_fc, ["SHAPE@"]) as insert:
                    insert.insertRow([geom])

                # Select the original features that is dissolved into 'geom'
                arcpy.management.SelectLayerByLocation(
                    in_layer="original_data_layer",
                    overlap_type=OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                    select_features=temp_fc,
                    selection_type=SelectionType.NEW_SELECTION.value,
                )
                # Add the hierarchy values for these features
                with arcpy.da.SearchCursor(
                    "original_data_layer",
                    [FieldNames_str.vegkategori, FieldNames_str.vegklasse],
                ) as search:
                    for vegkategori, vegklasse in search:
                        oid_to_data[oid].append([vegkategori, vegklasse, length])
            # Sort each list of hierarchy values and keep the values describing the least prioritized segment
            result = {}
            for oid, entries in oid_to_data.items():
                if entries:
                    result[oid] = self.sort_prioritized_hierarchy(entries)[-1]
            return result
        except:
            return {}
        finally:
            # Delete the intermediate feature layer
            if arcpy.Exists(temp_fc):
                arcpy.management.Delete(temp_fc)

    def setup_feature_selection(self, FeatureClass: str) -> str:
        """
        Dissolves the input road instances and creates an intermediate layer.
        Generates new layers for features that should be removed and added
        from / to the original input dataset.

        Args:
            FeatureClass (str): The path to the FeatureClass to be dissolved

        Returns:
            str: The path to the intermediate layer
        """
        # Dissolves the input data
        dissolved_fc = r"in_memory/dissolved_fc"
        arcpy.management.Dissolve(
            in_features=FeatureClass,
            out_feature_class=dissolved_fc,
            dissolve_field=[],
            multi_part="SINGLE_PART",
        )

        # Create the new remove
        if arcpy.Exists(self.remove_layer):
            arcpy.management.Delete(self.remove_layer)
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.remove_layer),
            out_name=os.path.basename(self.remove_layer),
            geometry_type="POLYLINE",
            spatial_reference=arcpy.Describe(
                self.copy_of_input_feature
            ).spatialReference,
        )
        # ... and add layer
        if arcpy.Exists(self.add_layer):
            arcpy.management.Delete(self.add_layer)
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.add_layer),
            out_name=os.path.basename(self.add_layer),
            geometry_type="POLYLINE",
            spatial_reference=arcpy.Describe(
                self.copy_of_input_feature
            ).spatialReference,
        )
        # The add layer also need the medium field because that is used in the dissolve functions
        arcpy.management.AddField(self.add_layer, FieldNames_str.medium, "TEXT")

        return dissolved_fc

    def feature_selection(
        self,
        geom: arcpy.Polyline | list[arcpy.Polyline],
        oid_to_geom: dict,
        oid_to_data: dict,
        working_fc: str,
        remove_geoms: list,
        add_geoms: list,
    ) -> None:
        """
        Detects the exactly instance of a cycle to be removed.
        Finds the instance with worst hierarchy from the dissolved cycles.
        If there are instances with other mediums connected to the chosen
        instance, this is further split and the highest prioritized part
        is added back again.

        Args:
            geom (arcpy.Polyline | list[arcpy.Polyline]): The dissolved geometry / geometries of a cycle
            oid_to_geom (dict): Dictionary with input geometries
            oid_to_data (dict): Dictionary with hierarchy data for the input geometries
            working_fc (str): The feature class containing the remaining input geometries
            remove_geoms (list): List of geometries that should be removed
            add_geoms (list): List of geometries that should be added
        """
        length_tolerance = (
            1000  # Length tolerance: segments must be shorter to be removed
        )
        geoms = geom if isinstance(geom, list) else [geom]  # Geoms must be an iterable
        overlap = []

        # For each geom, find all the geoms in the working file, kept
        # in oid_to_geom, that overlap with this / these geometries
        for geom in geoms:
            for o_oid, (o_geom, _) in oid_to_geom.items():
                if geom.contains(o_geom):
                    overlap.append((o_oid, o_geom))

        # Fetch the hierarchy data for prioritizing
        enriched = []
        for oid, geom in overlap:
            data = oid_to_data.get(oid)
            if data:
                enriched.append(tuple(data) + (oid, geom))

        if not enriched:
            return

        # Fetch the least prioritized segment - the one to be removed
        chosen = self.sort_prioritized_hierarchy(enriched)[-1]

        if chosen[2] > length_tolerance:
            # The segment must be shorter than the tolerance to be removed
            return

        # Fetch the geometry
        chosen_geom = chosen[-1]

        # Create a new temporarly layer for use in spatial search
        temp_fc = r"in_memory/tmp_geom_fc"
        if arcpy.Exists(temp_fc):
            arcpy.management.Delete(temp_fc)

        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(temp_fc),
            out_name=os.path.basename(temp_fc),
            geometry_type="POLYLINE",
            spatial_reference=chosen_geom.spatialReference,
        )

        try:
            # Insert the current geometry
            with arcpy.da.InsertCursor(temp_fc, ["SHAPE@"]) as insert:
                insert.insertRow([chosen_geom])

            # Performe spatial search to find the original segments that intersects with
            # this geom, and only looking at the remaining features in the entire process
            arcpy.management.SelectLayerByLocation(
                in_layer="original_data_layer",
                overlap_type=OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                select_features=working_fc,
                selection_type=SelectionType.NEW_SELECTION.value,
            )
            arcpy.management.SelectLayerByLocation(
                in_layer="original_data_layer",
                overlap_type=OverlapType.INTERSECT.value,
                select_features=temp_fc,
                selection_type=SelectionType.SUBSET_SELECTION.value,
            )

            """
            We do now have our geometry to remove, but other segments with
            another medium can be connected to this segment. This means f.ex.
            that 3-cycles can be registered as 2-cycles.

            If so, we need to find the segment with highest priority, collect
            all the segments connected to this segment to preserve topology
            consistency to the segment with different medium, and add these
            features back into the working file.
            """
            # Create list of endpoints
            orig_s, orig_e = self.endpoints_of(chosen_geom)
            start_endpoints = {orig_s, orig_e}

            inside_geoms = []  # Smaller geometries inside the dissolved one
            outside_endpoints = (
                set()  # Set of endpoints to count if there are any extra junctions
            )

            # Search through the original dataset and fetch the original geometries
            with arcpy.da.SearchCursor(
                "original_data_layer",
                [
                    "SHAPE@",
                    FieldNames_str.vegkategori,
                    FieldNames_str.vegklasse,
                    "Shape_Length",
                    FieldNames_str.medium,
                ],
            ) as search:
                for g, kategori, klasse, lengde, medium in search:
                    # If the chosen geometry contains this original geometry
                    # -> Store it as an internal geometry
                    if chosen_geom.contains(g):
                        inside_geoms.append((kategori, klasse, lengde, medium, g))
                    # Otherwise -> Store the endpoints in the set if they
                    # are close enough to the chosen geometry
                    else:
                        other_s, other_e = self.endpoints_of(g)
                        s, e = get_endpoints(g)
                        s, e = s.firstPoint, e.firstPoint
                        if (
                            chosen_geom.distanceTo(s) == 0
                            and other_s not in start_endpoints
                        ):
                            outside_endpoints.add(other_s)
                        if (
                            chosen_geom.distanceTo(e) == 0
                            and other_e not in start_endpoints
                        ):
                            outside_endpoints.add(other_e)

            # Add the chosen geometry to the list of geometries to remove
            remove_geoms.append(chosen_geom)

            # If there are any segments with different medium connected to the chosen geometry
            if outside_endpoints and inside_geoms:
                # -> Find the highest prioritized geometry
                inside_geoms = self.sort_prioritized_hierarchy(inside_geoms)
                if not inside_geoms:
                    return
                _, _, _, pri_med, pri_geom = inside_geoms[0]
                add_geoms.append((pri_geom, pri_med))

                # Create a set of endpoints and add the index of this geometry to it
                endpoints = set(self.endpoints_of(pri_geom))
                used = {0}

                changed = True
                # Continue as long as new segments are added
                # This is because the section we need to fill for consistent topology
                # can consist of more geometries than the one already added
                while changed:
                    changed = False
                    for idx, inside in enumerate(inside_geoms):
                        # Do not add already added segments
                        if idx in used:
                            continue
                        # Fetch the endpoints
                        s_tuple, e_tuple = self.endpoints_of(inside[-1])
                        # The geometry most be connected to the added geometries
                        if s_tuple in endpoints or e_tuple in endpoints:
                            # Find out witch end that is the connecting point
                            shared = s_tuple if s_tuple in endpoints else e_tuple
                            other = e_tuple if shared is s_tuple else s_tuple
                            if shared in outside_endpoints:
                                # If the connected point is a road junction point it is not valid
                                # We do not want to cross junctions when adding features
                                continue
                            # Add the segment
                            used.add(idx)
                            add_geoms.append((inside[-1], inside[-2]))
                            endpoints.add(other)
                            changed = True
        finally:
            # Delete the temporary feature layer
            if arcpy.Exists(temp_fc):
                arcpy.management.Delete(temp_fc)

    def clean_feature_selection(
        self, remove_geoms: list, add_geoms: list, dissolved_fc: str
    ) -> None:
        """
        Finish the selection process.

        Args:
            remove_geoms (list): List of geometries to remove from the working data
            add_geoms (list): List of geometries to add to the working data
            dissolved_fc (str): The intermediate feature layer to be deleted
        """
        # Add the geometries to remove to the feature class
        with arcpy.da.InsertCursor(self.remove_layer, ["SHAPE@"]) as insert_cursor:
            for geom in remove_geoms:
                insert_cursor.insertRow([geom])

        # If there are any segments that need to be added back again -> add these
        if len(add_geoms) > 0:
            with arcpy.da.InsertCursor(
                self.add_layer, ["SHAPE@", FieldNames_str.medium]
            ) as insert_cursor:
                for geom, medium in add_geoms:
                    insert_cursor.insertRow([geom, medium])

        # Delete the dissolved layer
        if arcpy.Exists(dissolved_fc):
            arcpy.management.Delete(dissolved_fc)

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
        # Fetch the cycle-data
        oid_to_geom = self.get_geoms(road_cycles)
        # ... and creates a dictionary keeping the
        # most relevant hierarchy for that section
        oid_to_data = self.get_geom_data(oid_to_geom)

        # Dissolves the cycle-instances into single loops
        dissolved_fc = self.setup_feature_selection(road_cycles)

        remove_geoms, add_geoms = [], []

        # For each dissolved cycle, select the segment to be removed, and potential added back again
        with arcpy.da.SearchCursor(dissolved_fc, ["SHAPE@"]) as search:
            for row in search:
                geom = row[0]
                self.feature_selection(
                    geom, oid_to_geom, oid_to_data, working_fc, remove_geoms, add_geoms
                )

        # Add the data to the remove and add layers, and delete dissolved_fc
        self.clean_feature_selection(remove_geoms, add_geoms, dissolved_fc)

    @timing_decorator
    def select_segments_to_remove_3_4_cycle_roads(
        self, road_cycles: str, working_fc: str
    ) -> None:
        """
        Selects which segments to remove based on hierarchy rules.

        Args:
            road_cycles (str): Feature class with road cycles
            working_fc (str): Feature class containing the remaining segments in the whole network
        """
        # Fetch the cycle-data
        oid_to_geom = self.get_geoms(road_cycles)
        # ... and creates a dictionary keeping the
        # most relevant hierarchy for that section
        oid_to_data = self.get_geom_data(oid_to_geom)

        # Dissolves the cycle-instances
        dissolved_fc = self.setup_feature_selection(road_cycles)

        remove_geoms, add_geoms = [], []

        # Divide the cycles that are single loops or nested cycles going into each other
        single_cycluses = []
        systems_of_cycluses = []

        with arcpy.da.SearchCursor(dissolved_fc, ["SHAPE@"]) as search:
            # For each geometry
            for row in search:
                geom = row[0]
                # -> Get the endpoints
                s, e = self.endpoints_of(geom)
                if s == e:
                    # If the endpoints are the same point -> It is a single loop
                    single_cycluses.append(geom)
                else:
                    # Otherwise -> It is a part of a system of cycles
                    # and we need to find out which
                    if len(systems_of_cycluses) == 0:
                        systems_of_cycluses.append([[geom], {s, e}])
                    else:
                        added = False
                        # If the endpoints of the dissolved geometry is
                        # located in a system already, it is added to this
                        for system in systems_of_cycluses:
                            geoms, endpoints = system
                            if any(pnt in endpoints for pnt in [s, e]):
                                geoms.append(geom)
                                endpoints.add(s)
                                endpoints.add(e)
                                added = True
                        # Otherwise -> A new system is created
                        if not added:
                            systems_of_cycluses.append([[geom], {s, e}])

        ###########################
        # Removes single 3-cycles #
        ###########################

        for geom in single_cycluses:
            self.feature_selection(
                geom, oid_to_geom, oid_to_data, working_fc, remove_geoms, add_geoms
            )

        ###############################
        # Removes systems of 3-cycles #
        ###############################

        for system in systems_of_cycluses:
            geoms, endpoints = system
            self.feature_selection(
                geoms, oid_to_geom, oid_to_data, working_fc, remove_geoms, add_geoms
            )

        ##################
        # Final clean up #
        ##################

        self.clean_feature_selection(remove_geoms, add_geoms, dissolved_fc)

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
                dead_ends=True,
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
                    start, end = self.endpoints_of(geom, num=None)
                    # If both end points are lonely: island
                    if endpoints.get(start, 0) == 1 and endpoints.get(end, 0) == 1:
                        update.deleteRow()
                        count += 1
                    # If one of the ends is lonely...
                    elif endpoints.get(start, 0) == 1 or endpoints.get(end, 0) == 1:
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
    def remove_1_cycle_roads(self, edit_fc: str) -> None:
        """
        Detects and removes 1-cycle roads from the road network.

        Args:
            edit_fc (str): Featureclass with the data that should be edited
        """
        count = None
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

            if road_1_cycle_sql:
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

                if (
                    arcpy.management.GetCount(self.filtered_1_cycle_roads)[0] == "0"
                    or type(arcpy.management.GetCount(self.filtered_1_cycle_roads)[0])
                    is None
                ):
                    # If no valid 1-cycles are found, break the loop
                    if not arcpy.Exists(self.removed_1_cycle_roads):
                        arcpy.management.CopyFeatures(
                            in_features=self.dissolved_feature,
                            out_feature_class=self.removed_1_cycle_roads,
                        )
                    count = 0
                    break

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
            else:
                # If some data already have been removed in previous iterations,
                # keep these changes and continue
                if arcpy.Exists(self.removed_1_cycle_roads):
                    count = 0
                else:
                    # If the sql-query return an error or no match (None):
                    # Stop the iteration and copy the features for further processing, if first run
                    count = 0
                    arcpy.management.CopyFeatures(
                        in_features=self.dissolved_feature,
                        out_feature_class=self.removed_1_cycle_roads,
                    )

            if count == 1:
                print(f"Removed {count} 1-cycle road.")
            else:
                print(f"Removed {count} 1-cycle roads.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        end_count = int(arcpy.management.GetCount(self.removed_1_cycle_roads)[0])
        print(f"Number of roads in the end: {end_count}\n")

    @timing_decorator
    def remove_2_cycle_roads(self, edit_fc: str) -> None:
        """
        Detects and removes 2-cycle roads from the road network
        based on the network with removed 1-cycle roads.

        Args:
            edit_fc (str): Featureclass with the data that should be edited
        """
        count = None
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

                if (
                    arcpy.management.GetCount(self.filtered_2_cycle_roads)[0] == "0"
                    or type(arcpy.management.GetCount(self.filtered_2_cycle_roads)[0])
                    is None
                ):
                    # If no valid 2-cycles are found, break the loop
                    if not arcpy.Exists(self.removed_2_cycle_roads):
                        arcpy.management.CopyFeatures(
                            in_features=self.dissolved_feature,
                            out_feature_class=self.removed_2_cycle_roads,
                        )
                    count = 0
                    break

                print()
                # Select the specific features to remove and to add
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

                # If it was 3-cycles that were detected as 2-cycles because of different
                # medium, some features must be added back again to preserve topology
                if arcpy.Exists(self.add_layer):
                    add_geoms = [
                        [geom, medium]
                        for geom, medium in arcpy.da.SearchCursor(
                            self.add_layer, ["SHAPE@", FieldNames_str.medium]
                        )
                    ]

                    with arcpy.da.InsertCursor(
                        self.removed_2_cycle_roads, ["SHAPE@", FieldNames_str.medium]
                    ) as insert:
                        for add_geom in add_geoms:
                            insert.insertRow(add_geom)

                # Update the working file, and repeat if changes
                edit_fc = self.removed_2_cycle_roads
            else:
                # If some data already have been removed in previous iterations,
                # keep these changes and continue
                if arcpy.Exists(self.removed_2_cycle_roads):
                    count = 0
                else:
                    # If the sql-query return an error or no match (None):
                    # Stop the iteration and copy the features for further processing, if first run
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

    @timing_decorator
    def remove_3_cycle_roads(self) -> None:
        """
        Detects and removes 3-cycle roads from the road network
        based on the network with removed 1- and 2-cycle roads.
        """
        count = None
        edit_fc = self.removed_2_cycle_roads
        first, first_count = True, None
        k = 0

        # As long as new 3-cycle roads are detected -> search again
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
            detect_3_cycle_roads = GISGraph(
                input_path=self.line_nodes,
                object_id="OBJECTID",
                original_id="ORIG_FID",
                geometry_field="SHAPE",
            )

            # Detect the 2-cycle roads
            road_3_cycle_sql = detect_3_cycle_roads.select_3_cycle()

            if road_3_cycle_sql:
                # Create a specific layer with these instances
                custom_arcpy.select_attribute_and_make_permanent_feature(
                    input_layer=self.dissolved_feature,
                    expression=road_3_cycle_sql,
                    output_name=self.line_3_cycle,
                )

                # Filter the roads so that only the valid once
                # (those that are short enough) are kept
                self.filter_short_roads(
                    input_feature=self.line_3_cycle,
                    output_feature=self.filtered_3_cycle_roads,
                    mode=3,
                )

                if (
                    arcpy.management.GetCount(self.filtered_3_cycle_roads)[0] == "0"
                    or type(arcpy.management.GetCount(self.filtered_3_cycle_roads)[0])
                    is None
                ):
                    # If no valid 3-cycles are found, break the loop
                    if not arcpy.Exists(self.removed_3_cycle_roads):
                        arcpy.management.CopyFeatures(
                            in_features=self.dissolved_feature,
                            out_feature_class=self.removed_3_cycle_roads,
                        )
                    count = 0
                    break

                print()
                # Select the specific features to remove and to add
                self.select_segments_to_remove_3_4_cycle_roads(
                    self.filtered_3_cycle_roads, edit_fc
                )
                print()

                count = int(arcpy.management.GetCount(self.remove_layer)[0])

                # Select the instances to work further with
                custom_arcpy.select_location_and_make_permanent_feature(
                    input_layer=self.dissolved_feature,
                    overlap_type=OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                    select_features=self.remove_layer,
                    output_name=self.removed_3_cycle_roads,
                    inverted=True,
                )

                # If it was 4-cycles that were detected as 3-cycles because of different
                # medium, some features must be added back again to preserve topology
                if arcpy.Exists(self.add_layer):
                    add_geoms = [
                        [geom, medium]
                        for geom, medium in arcpy.da.SearchCursor(
                            self.add_layer, ["SHAPE@", FieldNames_str.medium]
                        )
                    ]

                    with arcpy.da.InsertCursor(
                        self.removed_3_cycle_roads, ["SHAPE@", FieldNames_str.medium]
                    ) as insert:
                        for add_geom in add_geoms:
                            insert.insertRow(add_geom)

                # Update the working file, and repeat if changes
                edit_fc = self.removed_3_cycle_roads
            else:
                # If some data already have been removed in previous iterations,
                # keep these changes and continue
                if arcpy.Exists(self.removed_3_cycle_roads):
                    count = 0
                else:
                    # If the sql-query return an error or no match (None):
                    # Stop the iteration and copy the features for further processing, if first run
                    count = 0
                    arcpy.management.CopyFeatures(
                        in_features=self.dissolved_feature,
                        out_feature_class=self.removed_3_cycle_roads,
                    )

            if count == 1:
                print(f"Removed {count} 3-cycle road.")
            else:
                print(f"Removed {count} 3-cycle roads.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        end_count = int(arcpy.management.GetCount(self.removed_3_cycle_roads)[0])
        print(f"Number of roads in the end: {end_count}\n")

    @timing_decorator
    def remove_4_cycle_roads(self) -> None:
        """
        Detects and removes 4-cycle roads from the road network
        based on the network with removed 1-, 2- and 3-cycle roads.
        """
        count = None
        edit_fc = self.removed_3_cycle_roads
        first, first_count = True, None
        k = 0

        # As long as new 3-cycle roads are detected -> search again
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
            detect_4_cycle_roads = GISGraph(
                input_path=self.line_nodes,
                object_id="OBJECTID",
                original_id="ORIG_FID",
                geometry_field="SHAPE",
            )

            # Detect the 2-cycle roads
            road_4_cycle_sql = detect_4_cycle_roads.select_4_cycle()

            if road_4_cycle_sql:
                # Create a specific layer with these instances
                custom_arcpy.select_attribute_and_make_permanent_feature(
                    input_layer=self.dissolved_feature,
                    expression=road_4_cycle_sql,
                    output_name=self.line_4_cycle,
                )

                # Filter the roads so that only the valid once
                # (those that are short enough) are kept
                self.filter_short_roads(
                    input_feature=self.line_4_cycle,
                    output_feature=self.filtered_4_cycle_roads,
                    mode=3,
                )

                if (
                    arcpy.management.GetCount(self.filtered_4_cycle_roads)[0] == "0"
                    or type(arcpy.management.GetCount(self.filtered_4_cycle_roads)[0])
                    is None
                ):
                    # If no valid 4-cycles are found, break the loop
                    if not arcpy.Exists(self.removed_4_cycle_roads):
                        arcpy.management.CopyFeatures(
                            in_features=self.dissolved_feature,
                            out_feature_class=self.removed_4_cycle_roads,
                        )
                    count = 0
                    break

                print()
                # Select the specific features to remove and to add
                self.select_segments_to_remove_3_4_cycle_roads(
                    self.filtered_4_cycle_roads, edit_fc
                )
                print()

                count = int(arcpy.management.GetCount(self.remove_layer)[0])

                # Select the instances to work further with
                custom_arcpy.select_location_and_make_permanent_feature(
                    input_layer=self.dissolved_feature,
                    overlap_type=OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                    select_features=self.remove_layer,
                    output_name=self.removed_4_cycle_roads,
                    inverted=True,
                )

                # If it was 4-cycles that were detected as 3-cycles because of different
                # medium, some features must be added back again to preserve topology
                if arcpy.Exists(self.add_layer):
                    add_geoms = [
                        [geom, medium]
                        for geom, medium in arcpy.da.SearchCursor(
                            self.add_layer, ["SHAPE@", FieldNames_str.medium]
                        )
                    ]

                    with arcpy.da.InsertCursor(
                        self.removed_4_cycle_roads, ["SHAPE@", FieldNames_str.medium]
                    ) as insert:
                        for add_geom in add_geoms:
                            insert.insertRow(add_geom)

                # Update the working file, and repeat if changes
                edit_fc = self.removed_4_cycle_roads
            else:
                # If some data already have been removed in previous iterations,
                # keep these changes and continue
                if arcpy.Exists(self.removed_4_cycle_roads):
                    count = 0
                else:
                    # If the sql-query return an error or no match (None):
                    # Stop the iteration and copy the features for further processing, if first run
                    count = 0
                    arcpy.management.CopyFeatures(
                        in_features=self.dissolved_feature,
                        out_feature_class=self.removed_4_cycle_roads,
                    )

            if count == 1:
                print(f"Removed {count} 4-cycle road.")
            else:
                print(f"Removed {count} 4-cycle roads.")

        print(f"\nNumber of iterations: {k}")
        print(f"Number of roads in the start: {first_count}")
        end_count = int(arcpy.management.GetCount(self.removed_4_cycle_roads)[0])
        print(f"Number of roads in the end: {end_count}\n")

    @timing_decorator
    def fetch_original_data_final(self, scale: str, edit_fc: str):
        """
        Fetches the original data that should be kept for further processing.

        Args:
            edit_fc (str): Featureclass with the data that should be kept
        """
        if scale.lower() == "n100":
            output = Road_N100.road_triangles_output.value
        elif scale.lower() == "n250":
            output = Road_N250.road_triangles_output.value

        self.fetch_original_data(
            input=edit_fc,
            output=output,
        )

    @timing_decorator
    def run(self, scale: str) -> None:
        """
        Runs the complete process to remove road triangles.
        1-cycle, 2-cycle, 3-cycle and 4-cycle road triangles are removed based on a minimum length.
        1-cycle roads are removed completely first, then 2-cycle roads and finally
        3-cycle roads partly to keep a complete road network.

        Args:
            scale (str): String describing which scale to use (N100, N250)
        """
        arcpy.management.CopyFeatures(
            in_features=self.input_line_feature,
            out_feature_class=self.copy_of_input_feature,
        )

        """
        Parameter to decide if the functionality should run as either:
            - True: ... before thin roads
            - False: ... after thin roads
        """
        before = False

        print("\nRemoves road cycles\n")
        if before:
            self.remove_islands_and_small_dead_ends(edit_fc=self.copy_of_input_feature)
            self.remove_1_cycle_roads(edit_fc=self.dissolved_feature)
            self.remove_islands_and_small_dead_ends(edit_fc=self.removed_1_cycle_roads)
            self.remove_2_cycle_roads(edit_fc=self.dissolved_feature)
            self.remove_3_cycle_roads()
            # self.remove_4_cycle_roads()
            self.fetch_original_data_final(
                scale=scale, edit_fc=self.removed_3_cycle_roads
            )
        else:
            self.remove_1_cycle_roads(edit_fc=self.copy_of_input_feature)
            self.remove_2_cycle_roads(edit_fc=self.removed_1_cycle_roads)
            self.remove_3_cycle_roads()
            # self.remove_4_cycle_roads()
            self.fetch_original_data_final(
                scale=scale, edit_fc=self.removed_4_cycle_roads
            )

        self.work_file_manager.delete_created_files()


# Main function to be imported in other .py-files
@timing_decorator
def generalize_road_triangles_no_partition_call(scale: str) -> None:
    """
    Runs the RemoveRoadTriangles process with predefined parameters.

    Args:
        scale (str): String describing which scale to use (N100, N250)
    """
    environment_setup.main()

    before = False
    if scale.lower() == "n100":
        file = (
            Road_N100.data_preparation___simplified_road___n100_road.value
            if before
            else Road_N100.data_preparation___smooth_road___n100_road.value
        )
        root = Road_N100.road_triangles___remove_triangles_root___n100_road.value
        removed = Road_N100.road_triangles___removed_triangles___n100_road.value
    elif scale.lower() == "n250":
        file = (
            Road_N250.data_preparation___simplified_road___n250_road.value
            if before
            else Road_N250.data_preparation___merge_divided_roads___n250_road.value
        )
        root = Road_N250.road_triangles___remove_triangles_root___n250_road.value
        removed = Road_N250.road_triangles___removed_triangles___n250_road.value

    config = logic_config.RemoveRoadTrianglesKwargs(
        input_line_feature=file,
        work_file_manager_config=core_config.WorkFileConfig(root),
        maximum_length=500,
        root_file=root,
        output_processed_feature=removed,
    )
    remove_road_triangles = RemoveRoadTriangles(config)
    remove_road_triangles.run(scale=scale)


def generalize_road_triangles(scale: str) -> None:
    before = False

    if scale.lower() == "n100":
        file = (
            Road_N100.data_preparation___simplified_road___n100_road.value
            if before
            else Road_N100.data_preparation___smooth_road___n100_road.value
        )
        root = Road_N100.road_triangles___remove_triangles_root___n100_road.value
        partition_root = Road_N100.road_triangles___partition_root___n100_road.value
        maximum_cycle_length: int = 500
        documentation_directory = Road_N100.road_cycles_docu___n100_road.value
        removed = Road_N100.road_triangles___removed_triangles___n100_road.value

    elif scale.lower() == "n250":
        file = (
            Road_N250.data_preparation___simplified_road___n250_road.value
            if before
            else Road_N250.data_preparation___merge_divided_roads___n250_road.value
        )
        root = Road_N250.road_triangles___remove_triangles_root___n250_road.value
        partition_root = Road_N250.road_triangles___partition_root___n250_road.value
        maximum_cycle_length: int = 500
        documentation_directory = Road_N250.road_cycles_docu___n250_road.value
        removed = Road_N250.road_triangles___removed_triangles___n250_road.value

    else:
        raise ValueError(f"Unsupported scale: {scale}")

    road_object = "road"
    removed_tag = "removed_triangles"

    remove_triangles_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=road_object,
                path=file,
            )
        ]
    )

    remove_triangles_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=road_object,
                tag=removed_tag,
                path=removed,
            )
        ]
    )

    remove_triangles_io_config = core_config.PartitionIOConfig(
        input_config=remove_triangles_input_config,
        output_config=remove_triangles_output_config,
        documentation_directory=documentation_directory,
    )

    remove_triangles_init_config = logic_config.RemoveRoadTrianglesKwargs(
        input_line_feature=core_config.InjectIO(
            object=road_object,
            tag="input",
        ),
        output_processed_feature=core_config.InjectIO(
            object=road_object,
            tag=removed_tag,
        ),
        work_file_manager_config=core_config.WorkFileConfig(root_file=root),
        maximum_length=maximum_cycle_length,
        root_file=root,
        hierarchy_field=None,
        write_to_memory=False,
        keep_work_files=False,
    )

    remove_triangels_run_config = logic_config.RemoveRoadTrianglesRunParams(scale=scale)

    remove_triangles_class_config = core_config.ClassMethodEntryConfig(
        class_=RemoveRoadTriangles,
        method=RemoveRoadTriangles.run,
        init_params=remove_triangles_init_config,
        method_params=[remove_triangels_run_config],
    )

    remove_triangles_method_config = core_config.MethodEntriesConfig(
        entries=[remove_triangles_class_config]
    )

    partition_remove_triangles_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=50_000,
        context_radius_meters=maximum_cycle_length + 10,
        run_partition_optimization=False,
    )

    partition_remove_triangles = PartitionIterator(
        partition_io_config=remove_triangles_io_config,
        partition_method_inject_config=remove_triangles_method_config,
        partition_iterator_run_config=partition_remove_triangles_run_config,
        work_file_manager_config=core_config.WorkFileConfig(root_file=partition_root),
    )

    partition_remove_triangles.run()


if __name__ == "__main__":
    generalize_road_triangles(scale="n100")
