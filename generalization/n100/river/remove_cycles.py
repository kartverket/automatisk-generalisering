import arcpy
from collections import defaultdict
import networkx as nx
import os

from composition_configs import core_config, logic_config
from constants.n100_constants import FieldNames_str, RiverObjecttypes_str
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.custom_arcpy import OverlapType, SelectionType
from custom_tools.general_tools.partition_iterator import PartitionIterator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_rivers import River_N100
from generalization.n100.river.elevated_river_lines import RiverElevator


class RemoveCycles:
    """
    Class for removing cycles from river network by removing the node with the highest
    z-value from the line segment with the highest meanZ in each cycle.
    """

    def __init__(self, remove_cycles_config: logic_config.RemoveCyclesKwargs):
        """
        Creates an instance of RemoveCycles.
        """
        self.graph = None
        self.input_line_feature = remove_cycles_config.input_line_feature
        self.output_processed_feature = remove_cycles_config.output_processed_feature
        self.work_file_manager = WorkFileManager(
            config=remove_cycles_config.work_file_manager_config
        )

        self.copy_of_input_feature = "copy_of_input_feature"
        self.result_feature = "result_feature"
        self.split_feature = "split_feature"
        self.split_cleaned_feature = "split_cleaned_feature"
        self.dissolved_objtype_feature = "dissolved_objtype_feature"
        self.dissolved_feature = "dissolved_feature"
        self.cycle_feature = "cycle_feature"
        self.elevated_feature = "elevated_feature"
        self.intermediate_feature = "intermediate_feature"
        self.remove_feature = "remove_feature"
        self.selection_layer = "selection_layer"

        self.gdb_files_list = [
            self.copy_of_input_feature,
            self.result_feature,
            self.split_feature,
            self.split_cleaned_feature,
            self.dissolved_objtype_feature,
            self.dissolved_feature,
            self.cycle_feature,
            self.elevated_feature,
            self.intermediate_feature,
            self.remove_feature,
            self.selection_layer,
        ]
        self.gdb_files_list = self.work_file_manager.setup_work_file_paths(
            instance=self,
            file_structure=self.gdb_files_list,
        )

    @timing_decorator
    def detect_cycles(self, edit_fc: str) -> str:
        """
        Uses Networkx's methods to detect cycles in the feature class.
        """
        self.graph = nx.Graph()

        with arcpy.da.SearchCursor(edit_fc, ["OID@", "SHAPE@"]) as cur:
            for oid, geom in cur:
                if geom is None:
                    continue

                start = (round(geom.firstPoint.X, 3), round(geom.firstPoint.Y, 3))
                end = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))

                self.graph.add_edge(start, end, oid=oid)

        cycle_oids = set()

        # Detect 2-segment cycles
        endpoint_pairs = {}
        cycles_2 = 0
        with arcpy.da.SearchCursor(edit_fc, ["OID@", "SHAPE@"]) as cur:
            for oid, geom in cur:
                if geom is None:
                    continue

                start = (round(geom.firstPoint.X, 3), round(geom.firstPoint.Y, 3))
                end = (round(geom.lastPoint.X, 3), round(geom.lastPoint.Y, 3))

                key = tuple(sorted([start, end]))
                endpoint_pairs.setdefault(key, []).append(oid)

        for oids in endpoint_pairs.values():
            if len(oids) == 2:
                cycles_2 += 1
                cycle_oids.update(oids)

        # Detect 3-segment cycles
        cycles_3 = nx.cycle_basis(self.graph)
        for cycle in cycles_3:
            edge_oids = []
            for u, v in zip(cycle, cycle[1:] + cycle[:1]):
                data = self.graph.get_edge_data(u, v)
                if data:
                    edge_oids.append(data["oid"])
            cycle_oids.update(edge_oids)

        if not cycle_oids:
            return {}

        print()
        print(f"Cycles left in partition: {cycles_2 + len(cycles_3)}")
        print()

        where = f"OBJECTID IN ({','.join(map(str, cycle_oids))})"

        return where

    def fetch_original_data(self, input: str, output: str) -> None:
        """
        Capture the original data that should be included in the network
        and creates a copy of this data in a new featureclass.
        """
        # Creates feature layers for the original data and the current data
        arcpy.management.MakeFeatureLayer(
            in_features=self.copy_of_input_feature, out_layer="original_rivers_lyr"
        )
        arcpy.management.MakeFeatureLayer(
            in_features=input, out_layer="processed_rivers_lyr"
        )

        # Deletes the geometries that we want to keep from the
        # original data and store these in the intermediate layer
        arcpy.analysis.Erase(
            in_features="original_rivers_lyr",
            erase_features="processed_rivers_lyr",
            out_feature_class=self.intermediate_feature,
        )

        # Erase the created intermediate layer from the original
        # data so that the result is the wanted data only
        arcpy.analysis.Erase(
            in_features="original_rivers_lyr",
            erase_features=self.intermediate_feature,
            out_feature_class=output,
        )

    def sort_prioritized_hierarchy(self, rivers: list) -> list:
        """
        Sort the list of river features according to the wanted hierarchy components.
        """
        LARGE = 10**9

        pri_list_river_objtype = [
            RiverObjecttypes_str.generated_centerline,
            RiverObjecttypes_str.elv_bekk,
        ]

        river_objects_pri = {
            v: i for i, v in enumerate(pri_list_river_objtype)
        }  # Mapping dictionary from text to integers
        max_river_objtype_pri = len(
            pri_list_river_objtype
        )  # If no specified, default value to lowest priority

        # Sort the incoming list against the hierarchy values
        rivers.sort(
            key=lambda x: (
                river_objects_pri.get(x[0], max_river_objtype_pri),  # objtype
                (x[1] if x[1] is not None else LARGE),  # mean_z
                (x[2] if x[2] is not None else LARGE),  # length
            )
        )
        return rivers

    def delete_highest_z_endpoint(self, oid, geom, geom_lookup, objtype_lookup) -> None:
        """
        Remove the highest-Z endpoint from the segment, unless that endpoint coincides
        with a node belonging to a generated centerline segment. In that case, remove
        the other endpoint.
        """
        first = geom.firstPoint
        last = geom.lastPoint

        # Default: remove the highest-Z endpoint
        remove_first = first.Z >= last.Z
        candidate_pt = first if remove_first else last

        # Check if candidate_pt coincides with a generated centerline node
        for other_oid, data in objtype_lookup.items():
            if other_oid == oid:
                continue

            objtype = data[0]
            if objtype == RiverObjecttypes_str.generated_centerline:
                other_geom = geom_lookup[other_oid][0]

                ofirst = other_geom.firstPoint
                olast = other_geom.lastPoint

                if (
                    round(candidate_pt.X, 3) == round(ofirst.X, 3)
                    and round(candidate_pt.Y, 3) == round(ofirst.Y, 3)
                ) or (
                    round(candidate_pt.X, 3) == round(olast.X, 3)
                    and round(candidate_pt.Y, 3) == round(olast.Y, 3)
                ):
                    # Flip the removal decision
                    remove_first = not remove_first
                    break

        # Build new point list
        new_points = []
        for part in geom:
            pts = [pt for pt in part if pt]
            if remove_first:
                pts = pts[1:]
            else:
                pts = pts[:-1]
            new_points.extend(pts)

        new_geom = arcpy.Polyline(
            arcpy.Array(new_points), geom.spatialReference, has_z=True
        )

        with arcpy.da.UpdateCursor(self.elevated_feature, ["OID@", "SHAPE@"]) as ucur:
            for row_oid, _ in ucur:
                if row_oid == oid:
                    ucur.updateRow([row_oid, new_geom])
                    break

    def get_endpoints(
        self,
        polyline: arcpy.Geometry,
    ) -> tuple[arcpy.PointGeometry, arcpy.PointGeometry]:
        """
        Returns the start and end points of a polyline.
        """
        return (
            arcpy.PointGeometry(polyline.firstPoint, polyline.spatialReference),
            arcpy.PointGeometry(polyline.lastPoint, polyline.spatialReference),
        )

    def endpoints_of(self, geom: arcpy.Geometry, num: int = 3) -> tuple:
        """
        Returns rounded coordinates for the endpoints of the geom.
        """
        s, e = self.get_endpoints(geom)
        s, e = s.firstPoint, e.firstPoint
        if num is None:
            # If num is None we want the original data without the round(...) operation
            return (s.X, s.Y), (e.X, e.Y)
        # Otherwise round to the desired number of decimals, default = 3
        return (round(s.X, num), round(s.Y, num)), (round(e.X, num), round(e.Y, num))

    def get_geoms(self, feature_class: str) -> dict:
        """
        Returns a dictionary with all the geometries in the featureclass.
        """
        return {
            oid: [geom, length]
            for oid, geom, length in arcpy.da.SearchCursor(
                feature_class, ["OID@", "SHAPE@", "Shape_Length"]
            )
        }

    def get_geom_data(self, oid_to_geom: dict) -> defaultdict:
        """
        Fetches relevant data for the hierarchy and returns it as a dictionary.
        """
        oid_to_data = defaultdict(list)

        arcpy.management.MakeFeatureLayer(
            in_features=self.elevated_feature, out_layer="original_data_layer"
        )

        if arcpy.Exists(self.selection_layer):
            arcpy.management.Delete(self.selection_layer)

        first_geom = next(iter(oid_to_geom.values()))[0]
        arcpy.management.CreateFeatureclass(
            out_path=os.path.dirname(self.selection_layer),
            out_name=os.path.basename(self.selection_layer),
            geometry_type="POLYLINE",
            spatial_reference=first_geom.spatialReference,
        )

        for oid, (geom, length) in oid_to_geom.items():
            # Delete existing rows in the layer
            with arcpy.da.UpdateCursor(self.selection_layer, ["SHAPE@"]) as update:
                for _ in update:
                    update.deleteRow()
            # Insert the geometry (the dissolved pieces in each cycle) in the new layer
            with arcpy.da.InsertCursor(self.selection_layer, ["SHAPE@"]) as insert:
                insert.insertRow([geom])

            # Select the original features that is dissolved into 'geom'
            arcpy.management.SelectLayerByLocation(
                in_layer="original_data_layer",
                overlap_type=OverlapType.SHARE_A_LINE_SEGMENT_WITH.value,
                select_features=self.selection_layer,
                selection_type=SelectionType.NEW_SELECTION.value,
            )
            with arcpy.da.SearchCursor(
                "original_data_layer",
                [FieldNames_str.objtype, "meanZ"],
            ) as search:
                for objtype, mean_z in search:
                    oid_to_data[oid].append([objtype, mean_z, length])

        # Sort each list of hierarchy values and keep the the least prioritized segment
        result = {}
        for oid, entries in oid_to_data.items():
            if entries:
                result[oid] = self.sort_prioritized_hierarchy(entries)[-1]
        return result

    def feature_selection(
        self,
        geom: arcpy.Polyline | list[arcpy.Polyline],
        oid_to_geom: dict,
        oid_to_data: dict,
    ) -> None:
        """
        Detects the exactly instance of a cycle to be removed. Finds the instance with
        worst hierarchy from the dissolved cycles. If there are instances with other
        mediums connected to the chosen instance, this is further split and the highest
        prioritized part is added back again.
        """
        geoms = geom if isinstance(geom, list) else [geom]  # Geoms must be an iterable
        overlap = []

        # For each geom, find all the geoms in the working file, kept
        # in oid_to_geom, that overlap with this / these geometries
        for geom in geoms:
            for o_oid, (o_geom, _) in oid_to_geom.items():
                if geom is None or o_geom is None:
                    continue
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

        # Fetch the geometry
        chosen_geom = chosen[-1]
        chosen_oid = chosen[-2]

        # Remove the endpoint with the highest z-value from the chosen geometry
        self.delete_highest_z_endpoint(
            oid=chosen_oid,
            geom=chosen_geom,
            geom_lookup=oid_to_geom,
            objtype_lookup=oid_to_data,
        )

    @timing_decorator
    def select_segments_to_remove(self, river_cycles: str) -> None:
        """
        Selects which segments to remove based on hierarchy rules.
        """
        # Fetch the cycle-data
        oid_to_geom = self.get_geoms(river_cycles)
        # ... and creates a dictionary keeping the
        # most relevant hierarchy for that section
        oid_to_data = self.get_geom_data(oid_to_geom)

        arcpy.management.Dissolve(
            in_features=river_cycles,
            out_feature_class=self.dissolved_feature,
            dissolve_field=[],
            multi_part="SINGLE_PART",
        )

        # Divide the cycles that are single loops or nested cycles going into each other
        single_cycluses = []
        systems_of_cycluses = []
        cycles = []

        with arcpy.da.SearchCursor(self.dissolved_feature, ["SHAPE@"]) as search:
            # For each geometry
            for row in search:
                geom = row[0]
                # -> Get the endpoints
                s, e = self.endpoints_of(geom)
                cycles.append(geom)
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

        #########################
        # Removes single cycles #
        #########################
        for geom in single_cycluses:
            self.feature_selection(geom, oid_to_geom, oid_to_data)

        #############################
        # Removes systems of cycles #
        #############################
        for system in systems_of_cycluses:
            geoms, endpoints = system
            self.feature_selection(geoms, oid_to_geom, oid_to_data)

    @timing_decorator
    def run(self) -> None:
        """
        Run the cycle removal process.
        """
        arcpy.management.CopyFeatures(
            in_features=self.input_line_feature,
            out_feature_class=self.copy_of_input_feature,
        )

        count = 0
        while True:
            count += 1

            arcpy.management.CopyFeatures(
                in_features=self.copy_of_input_feature,
                out_feature_class=self.result_feature,
            )

            arcpy.management.SplitLine(self.copy_of_input_feature, self.split_feature)

            arcpy.management.DeleteIdentical(
                in_dataset=self.split_feature,
                fields=["SHAPE"],
                xy_tolerance="0 Meters",
            )

            custom_arcpy.select_attribute_and_make_permanent_feature(
                input_layer=self.split_feature,
                expression="Shape_Length > 0",
                output_name=self.split_cleaned_feature,
                selection_type=SelectionType.NEW_SELECTION,
            )

            arcpy.management.Dissolve(
                in_features=self.split_cleaned_feature,
                out_feature_class=self.dissolved_objtype_feature,
                dissolve_field=[FieldNames_str.objtype],
                multi_part="SINGLE_PART",
            )

            cycle_sql = self.detect_cycles(edit_fc=self.dissolved_objtype_feature)

            if cycle_sql:
                custom_arcpy.select_attribute_and_make_permanent_feature(
                    input_layer=self.dissolved_objtype_feature,
                    expression=cycle_sql,
                    output_name=self.cycle_feature,
                )

                RiverElevator(
                    input_lines_fc=self.cycle_feature,
                    output_fc=self.elevated_feature,
                ).run()

                self.select_segments_to_remove(self.elevated_feature)

                arcpy.analysis.Erase(
                    in_features=self.cycle_feature,
                    erase_features=self.elevated_feature,
                    out_feature_class=self.remove_feature,
                )

                arcpy.analysis.Erase(
                    in_features=self.result_feature,
                    erase_features=self.remove_feature,
                    out_feature_class=self.copy_of_input_feature,
                )
            else:
                break  # If there is no sql, it means that there are no cycles left

        self.fetch_original_data(
            input=self.copy_of_input_feature, output=self.output_processed_feature
        )
        self.work_file_manager.delete_created_files()


def generalize_rivers() -> None:
    """
    Main function for cycle removal.
    """
    environment_setup.main()

    input_file = River_N100.river_connected___connected_river_lines___n100.value
    root = River_N100.river_cycles___remove_cycles_root___n100.value
    partition_root = River_N100.river_cycles___partition_root___n100.value
    removed = River_N100.river_cycles___removed_cycles___n100.value
    documentation_directory = River_N100.river_cycles_docu___n100.value

    river_object = "river"
    removed_tag = "removed_cycles"

    remove_cycles_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=river_object,
                path=input_file,
            )
        ]
    )

    remove_cycles_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=river_object,
                tag=removed_tag,
                path=removed,
            )
        ]
    )

    remove_cycles_io_config = core_config.PartitionIOConfig(
        input_config=remove_cycles_input_config,
        output_config=remove_cycles_output_config,
        documentation_directory=documentation_directory,
    )

    remove_cycles_init_config = logic_config.RemoveCyclesKwargs(
        input_line_feature=core_config.InjectIO(
            object=river_object,
            tag="input",
        ),
        output_processed_feature=core_config.InjectIO(
            object=river_object,
            tag=removed_tag,
        ),
        work_file_manager_config=core_config.WorkFileConfig(root_file=root),
    )

    remove_cycles_class_config = core_config.ClassMethodEntryConfig(
        class_=RemoveCycles,
        method=RemoveCycles.run,
        init_params=remove_cycles_init_config,
        method_params=[],
    )

    remove_cycles_method_config = core_config.MethodEntriesConfig(
        entries=[remove_cycles_class_config]
    )

    partition_remove_cycles_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=10_000,
        context_radius_meters=1,
        run_partition_optimization=False,
    )

    partition_remove_cycles = PartitionIterator(
        partition_io_config=remove_cycles_io_config,
        partition_method_inject_config=remove_cycles_method_config,
        partition_iterator_run_config=partition_remove_cycles_run_config,
        work_file_manager_config=core_config.WorkFileConfig(root_file=partition_root),
    )

    partition_remove_cycles.run()


if __name__ == "__main__":
    generalize_rivers()
