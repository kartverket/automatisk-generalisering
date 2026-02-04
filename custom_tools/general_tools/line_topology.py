from __future__ import annotations

from typing import Optional

import arcpy

from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
from file_manager import WorkFileManager
from composition_configs import logic_config


class FillLineGaps:
    ORIGINAL_ID = "line_gap_original_id"

    # Change output fields
    FIELD_GAP_DIST_M = "gap_dist_m"
    FIELD_GAP_SOURCE = "gap_source"

    GAP_SOURCE_DEFAULT = "default"
    GAP_SOURCE_PAIR_DANGLE = "pair_dangle"
    GAP_SOURCE_PAIR_LINE = "pair_line"
    GAP_SOURCE_DEFERRED = "deferred"

    # Near table fields
    F_IN_FID = "IN_FID"
    F_NEAR_FID = "NEAR_FID"
    F_NEAR_FC = "NEAR_FC"
    F_NEAR_DIST = "NEAR_DIST"
    F_NEAR_X = "NEAR_X"
    F_NEAR_Y = "NEAR_Y"

    def __init__(self, line_gap_config: logic_config.FillLineGapsConfig):
        self.input_lines = line_gap_config.input_lines
        self.output_lines = line_gap_config.output_lines
        self.connect_to_features = line_gap_config.connect_to_features
        self.gap_tolerance_meters = int(line_gap_config.gap_tolerance_meters)

        adv = line_gap_config.advanced_config
        self.fill_gaps_on_self = bool(adv.fill_gaps_on_self)
        self.line_changes_output = adv.line_changes_output
        self.increased_tolerance_edge_case_distance_meters = int(
            adv.increased_tolerance_edge_case_distance_meters
        )
        self.edit_method = logic_config.EditMethod(adv.edit_method)
        self.propagate_illigal_targets = adv.propagating_illigal_targets

        if self.connect_to_features is None and self.fill_gaps_on_self is False:
            raise ValueError(
                "Invalid config: fill_gaps_on_self cannot be False when connect_to_features is None."
            )

        self.write_work_files_to_memory = (
            line_gap_config.work_file_manager_config.write_to_memory
        )
        self.keep_work_files = line_gap_config.work_file_manager_config.keep_files
        self.root_file = line_gap_config.work_file_manager_config.root_file

        self.wfm = WorkFileManager(config=line_gap_config.work_file_manager_config)

        # Work files (WFM will expand to full unique paths in run())
        self.lines_copy = "lines_copy"
        self.dangles = "dangles"
        self.filtered_dangles = "filtered_dangles"

        self.target_self = "target_self"

        self.near_table = "near_table_all"
        self.conn_endpoints = "line_endpoints"
        self.conn_table = "connected_table"

        self.external_target_layers: list[str] = []

        self.work_file_list = [
            self.lines_copy,
            self.dangles,
            self.filtered_dangles,
            self.target_self,
            self.near_table,
            self.conn_endpoints,
            self.conn_table,
        ]

    # ----------------------------
    # Units & dataset key
    # ----------------------------

    def _tolerance_linear_unit(self) -> str:
        return f"{int(self.gap_tolerance_meters)} Meters"

    def _expanded_dangle_tolerance_meters(self) -> int:
        extra = max(0, int(self.increased_tolerance_edge_case_distance_meters))
        return int(self.gap_tolerance_meters) + extra

    def _expanded_dangle_tolerance_linear_unit(self) -> str:
        return f"{int(self._expanded_dangle_tolerance_meters())} Meters"

    def _dataset_key(self, value: str) -> str:
        text = str(value).replace("\\", "/")
        return text.split("/")[-1]

    def _line_dataset_keys(self) -> set[str]:
        return {
            self._dataset_key(self.lines_copy),
            self._dataset_key(self.target_self),
        }

    def _normalize_target_key(
        self, *, near_fc_key: str, lines_key: str, line_keys: set[str]
    ) -> str:
        if near_fc_key in line_keys:
            return lines_key
        return near_fc_key

    def _oid_to_original_id_lookup(self, fc: str) -> dict[int, int]:
        oid_field = arcpy.Describe(fc).OIDFieldName
        out: dict[int, int] = {}
        with arcpy.da.SearchCursor(fc, [oid_field, self.ORIGINAL_ID]) as cur:
            for oid, original_id in cur:
                out[int(oid)] = int(original_id)
        return out

    def _resolve_edit_op(self, *, gap_source: str) -> logic_config.EditOp:
        method = self.edit_method

        if method == logic_config.EditMethod.FORCED_SNAP:
            return logic_config.EditOp.SNAP
        if method == logic_config.EditMethod.FORCED_EXTEND:
            return logic_config.EditOp.EXTEND

        # AUTO
        if str(gap_source) == self.GAP_SOURCE_PAIR_DANGLE:
            return logic_config.EditOp.SNAP
        return logic_config.EditOp.EXTEND

    def _choose_endpoint_index(
        self, *, points: list, dangle_x: float, dangle_y: float, tol: float = 0.001
    ) -> int:
        first = points[0]
        last = points[-1]

        def matches(point, x: float, y: float) -> bool:
            return abs(point.X - x) <= tol and abs(point.Y - y) <= tol

        if matches(first, dangle_x, dangle_y):
            return 0
        if matches(last, dangle_x, dangle_y):
            return -1

        # Fallback: closest end
        d_first = (first.X - dangle_x) ** 2 + (first.Y - dangle_y) ** 2
        d_last = (last.X - dangle_x) ** 2 + (last.Y - dangle_y) ** 2
        return 0 if d_first <= d_last else -1

    def _snap_endpoint(
        self, *, shape, dangle_x: float, dangle_y: float, near_x: float, near_y: float
    ):
        if shape is None:
            return shape

        part = shape.getPart(0)
        points = [pt for pt in part]
        if len(points) < 2:
            return shape

        idx = self._choose_endpoint_index(
            points=points, dangle_x=dangle_x, dangle_y=dangle_y
        )

        points[idx] = arcpy.Point(near_x, near_y)
        return arcpy.Polyline(arcpy.Array(points), shape.spatialReference)

    def _extend_endpoint(
        self, *, shape, dangle_x: float, dangle_y: float, near_x: float, near_y: float
    ):
        if shape is None:
            return shape

        part = shape.getPart(0)
        points = [pt for pt in part]
        if len(points) < 2:
            return shape

        idx = self._choose_endpoint_index(
            points=points, dangle_x=dangle_x, dangle_y=dangle_y
        )

        # If extending at the start, insert new point before first.
        # If extending at the end, append new point after last.
        if idx == 0:
            points.insert(0, arcpy.Point(near_x, near_y))
        else:
            points.append(arcpy.Point(near_x, near_y))

        return arcpy.Polyline(arcpy.Array(points), shape.spatialReference)

    # ----------------------------
    # Preprocessing
    # ----------------------------

    def _copy_input_lines(self) -> None:
        arcpy.management.CopyFeatures(self.input_lines, self.lines_copy)

    def _add_original_id_field(self) -> None:
        existing = {f.name for f in arcpy.ListFields(self.lines_copy)}
        if self.ORIGINAL_ID not in existing:
            arcpy.management.AddField(self.lines_copy, self.ORIGINAL_ID, "LONG")

        oid_field = arcpy.Describe(self.lines_copy).OIDFieldName
        arcpy.management.CalculateField(
            self.lines_copy,
            self.ORIGINAL_ID,
            expression=f"!{oid_field}!",
            expression_type="PYTHON3",
        )

    def _create_dangles(self) -> None:
        arcpy.management.FeatureVerticesToPoints(
            self.lines_copy, self.dangles, "DANGLE"
        )

    # ----------------------------
    # Target staging
    # ----------------------------

    def _build_external_target_layers_once(self) -> None:
        if self.external_target_layers:
            return
        if self.connect_to_features is None:
            return

        for index, feature_path in enumerate(self.connect_to_features):
            output_name = self.wfm.build_file_path(file_name=f"target_feature_{index}")

            if self.write_work_files_to_memory:
                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=feature_path,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=output_name,
                    search_distance=self._tolerance_linear_unit(),
                )
            else:
                custom_arcpy.select_location_and_make_permanent_feature(
                    input_layer=feature_path,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=output_name,
                    search_distance=self._tolerance_linear_unit(),
                )

            self.external_target_layers.append(output_name)

    def _select_targets_within_tolerance_of_dangles(self) -> list[str]:
        targets: list[str] = []
        if self.fill_gaps_on_self:
            if self.write_work_files_to_memory:
                custom_arcpy.select_location_and_make_feature_layer(
                    input_layer=self.lines_copy,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=self.target_self,
                    search_distance=self._tolerance_linear_unit(),
                )
            else:
                custom_arcpy.select_location_and_make_permanent_feature(
                    input_layer=self.lines_copy,
                    overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                    select_features=self.dangles,
                    output_name=self.target_self,
                    search_distance=self._tolerance_linear_unit(),
                )
            targets.append(self.target_self)

        targets.extend(self.external_target_layers)
        return targets

    def _filter_true_dangles(self) -> None:
        """
        Keeps only true dangles:
        - dangles that do NOT intersect any external target features
        Note:
        - We do NOT consider self lines here, only non-input layers.
        - If connect_to_features is None -> all dangles are treated as true.
        """
        if not self.external_target_layers:
            # Nothing to filter against; keep all dangles as "true"
            arcpy.management.CopyFeatures(self.dangles, self.filtered_dangles)
            return

        dangles_lyr = "dangles_true_filter_lyr"
        arcpy.management.MakeFeatureLayer(self.dangles, dangles_lyr)

        arcpy.management.SelectLayerByAttribute(dangles_lyr, "CLEAR_SELECTION")

        # Select dangles that intersect ANY external features
        for target in self.external_target_layers:
            arcpy.management.SelectLayerByLocation(
                in_layer=dangles_lyr,
                overlap_type="INTERSECT",
                select_features=target,
                selection_type="ADD_TO_SELECTION",
            )

        # Invert -> keep only dangles that do NOT intersect external features
        arcpy.management.SelectLayerByAttribute(
            dangles_lyr,
            selection_type="SWITCH_SELECTION",
        )

        arcpy.management.CopyFeatures(dangles_lyr, self.filtered_dangles)

    # ----------------------------
    # Dangle lookups
    # ----------------------------

    def _build_dangle_parent_lookup(self, dangles_fc: str) -> dict[int, int]:
        oid_field = arcpy.Describe(dangles_fc).OIDFieldName
        out: dict[int, int] = {}
        with arcpy.da.SearchCursor(dangles_fc, [oid_field, self.ORIGINAL_ID]) as cur:
            for dangle_oid, parent_id in cur:
                out[int(dangle_oid)] = int(parent_id)
        return out

    def _build_dangle_xy_lookup(
        self, dangles_fc: str
    ) -> dict[int, tuple[float, float]]:
        oid_field = arcpy.Describe(dangles_fc).OIDFieldName
        out: dict[int, tuple[float, float]] = {}
        with arcpy.da.SearchCursor(dangles_fc, [oid_field, "SHAPE@XY"]) as cur:
            for dangle_oid, (x, y) in cur:
                out[int(dangle_oid)] = (float(x), float(y))
        return out

    # ----------------------------
    # Illegal targets detection
    # ----------------------------

    def detect_illegal_targets(
        self,
        *,
        dangle_parent: dict[int, int],
        target_layers: list[str],
    ) -> tuple[dict[int, dict[str, set[int]]], dict[int, set[int]]]:
        """
        illegal[parent_id][dataset_key] -> set(objectid)

        Clauses:
          - self line
          - objects connected to parent line endpoints
        """
        illegal: dict[int, dict[str, set[int]]] = {}

        self._illegal_self_line(
            illegal=illegal,
            parent_ids=set(dangle_parent.values()),
        )
        adjacency = self._illegal_connected_features(
            illegal=illegal,
            target_layers=target_layers,
        )
        if self.propagate_illigal_targets:
            self._propagate_external_illegal_within_components(
                illegal=illegal,
                adjacency=adjacency,
            )
        return illegal, adjacency

    def _illegal_self_line(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        parent_ids: set[int],
    ) -> None:
        lines_key = self._dataset_key(self.lines_copy)
        for pid in parent_ids:
            illegal.setdefault(int(pid), {}).setdefault(lines_key, set()).add(int(pid))

    def _illegal_connected_features(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        target_layers: list[str],
    ) -> dict[int, set[int]]:
        adjacency: dict[int, set[int]] = {}

        arcpy.management.FeatureVerticesToPoints(
            self.lines_copy, self.conn_endpoints, "BOTH_ENDS"
        )

        endpoint_oid = arcpy.Describe(self.conn_endpoints).OIDFieldName
        endpoint_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            self.conn_endpoints, [endpoint_oid, self.ORIGINAL_ID]
        ) as cur:
            for eo, pid in cur:
                endpoint_parent[int(eo)] = int(pid)

        # IMPORTANT: include full lines_copy for building adjacency/components
        near_features = list(target_layers)
        if self.lines_copy not in near_features:
            near_features.append(self.lines_copy)

        connect_tol_m = 0.02
        connect_tol = f"{connect_tol_m} Meters"

        arcpy.analysis.GenerateNearTable(
            in_features=self.conn_endpoints,
            near_features=near_features,
            out_table=self.conn_table,
            search_radius=connect_tol,
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

        lines_key = self._dataset_key(self.lines_copy)
        line_keys = self._line_dataset_keys()

        lines_copy_key = self._dataset_key(self.lines_copy)
        target_self_key = self._dataset_key(self.target_self)

        lines_copy_oid_to_orig = self._oid_to_original_id_lookup(self.lines_copy)
        target_self_oid_to_orig = (
            self._oid_to_original_id_lookup(self.target_self)
            if self.fill_gaps_on_self
            else {}
        )

        fields = [self.F_IN_FID, self.F_NEAR_FID, self.F_NEAR_FC, self.F_NEAR_DIST]
        with arcpy.da.SearchCursor(self.conn_table, fields) as cur:
            for in_fid, near_fid, near_fc, near_dist in cur:
                if near_fid is None or near_dist is None:
                    continue

                if float(near_dist) >= float(connect_tol_m):
                    continue

                a_parent = endpoint_parent.get(int(in_fid))
                if a_parent is None:
                    continue
                a_parent = int(a_parent)

                raw_key = self._dataset_key(near_fc)
                nf_id = int(near_fid)

                # Convert line-like near_fid into ORIGINAL_ID space
                if raw_key == lines_copy_key:
                    nf_id = int(lines_copy_oid_to_orig.get(nf_id, nf_id))
                elif raw_key == target_self_key:
                    nf_id = int(target_self_oid_to_orig.get(nf_id, nf_id))

                ds_key = self._normalize_target_key(
                    near_fc_key=raw_key,
                    lines_key=lines_key,
                    line_keys=line_keys,
                )

                illegal.setdefault(a_parent, {}).setdefault(ds_key, set()).add(
                    int(nf_id)
                )

                # Build adjacency only for line network connections
                if ds_key == lines_key:
                    b_parent = int(nf_id)
                    if b_parent != a_parent:
                        adjacency.setdefault(a_parent, set()).add(b_parent)
                        adjacency.setdefault(b_parent, set()).add(a_parent)

        return adjacency

    def _propagate_external_illegal_within_components(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        adjacency: dict[int, set[int]],
    ) -> None:
        """
        For each connected component of the line network, union external illegal targets
        and apply to every member.

        External illegal targets = everything except the canonical lines_key (self-line rule).
        """
        lines_key = self._dataset_key(self.lines_copy)

        visited: set[int] = set()

        # Ensure we include isolated nodes too
        all_nodes = set(illegal.keys()) | set(adjacency.keys())
        for pid in list(all_nodes):
            pid = int(pid)
            if pid in visited:
                continue

            # BFS to get component
            stack = [pid]
            component: set[int] = set()

            while stack:
                cur = int(stack.pop())
                if cur in visited:
                    continue
                visited.add(cur)
                component.add(cur)

                for nb in adjacency.get(cur, set()):
                    nb = int(nb)
                    if nb not in visited:
                        stack.append(nb)

            # Union external illegal across component
            union_external: dict[str, set[int]] = {}
            for member in component:
                ds_map = illegal.get(int(member), {})
                for ds_key, ids in ds_map.items():
                    if ds_key == lines_key:
                        continue  # keep self-line constraint per member
                    union_external.setdefault(ds_key, set()).update(ids)

            # Apply union to each member
            for member in component:
                illegal.setdefault(int(member), {})
                for ds_key, ids in union_external.items():
                    illegal[int(member)].setdefault(ds_key, set()).update(ids)

    def _is_illegal(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        parent_id: int,
        target_fc_key: str,
        target_oid: int,
    ) -> bool:
        ds = illegal.get(int(parent_id))
        if not ds:
            return False
        return int(target_oid) in ds.get(str(target_fc_key), set())

    def _parents_share_illegal_target(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        a_parent: int,
        b_parent: int,
    ) -> bool:
        """
        Your constraint: dangle-pairs must not share an illegal target object.

        Interpreted as:
          there exists any (dataset_key, oid) that is illegal for both parents.
        """
        a = illegal.get(int(a_parent), {})
        b = illegal.get(int(b_parent), {})
        if not a or not b:
            return False

        for ds_key, a_set in a.items():
            b_set = b.get(ds_key)
            if not b_set:
                continue
            if a_set.intersection(b_set):
                return True
        return False

    def _find_specific_line_candidate(
        self,
        *,
        candidates_sorted: list[dict],
        lines_fc_keys: set[str],
        other_parent_id: int,
        base_tol: float,
    ) -> Optional[dict]:
        """
        Find the row that explicitly targets the other *parent line* (lines_copy),
        within base_tol.
        """
        for cand in candidates_sorted:
            if cand["near_fc_key"] not in lines_fc_keys:
                continue
            if int(cand["near_fid"]) != int(other_parent_id):
                continue
            if float(cand["near_dist"]) <= float(base_tol):
                return cand
        return None

    # ----------------------------
    # Near table reading
    # ----------------------------

    def _generate_near_table(
        self,
        *,
        in_dangles: str,
        near_features: list[str],
        search_radius: str,
        out_table: str,
    ) -> None:
        arcpy.analysis.GenerateNearTable(
            in_features=in_dangles,
            near_features=near_features,
            out_table=out_table,
            search_radius=search_radius,
            location="LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

    def _read_near_table_grouped(
        self,
        *,
        near_table: str,
        dangles_fc_key: str,
        lines_copy_key: str,
        target_self_key: str,
        lines_copy_oid_to_orig: dict[int, int],
        target_self_oid_to_orig: dict[int, int],
    ) -> dict[int, list[dict]]:

        grouped: dict[int, list[dict]] = {}

        # Canonical key for “input lines”
        lines_key = self._dataset_key(self.lines_copy)
        line_keys = self._line_dataset_keys()

        fields = [
            self.F_IN_FID,
            self.F_NEAR_FID,
            self.F_NEAR_FC,
            self.F_NEAR_DIST,
            self.F_NEAR_X,
            self.F_NEAR_Y,
        ]

        with arcpy.da.SearchCursor(near_table, fields) as cur:
            for in_fid, near_fid, near_fc, near_dist, near_x, near_y in cur:
                if near_fid is None or near_dist is None:
                    continue

                in_id = int(in_fid)
                nf_id = int(near_fid)
                dist = float(near_dist)

                raw_key = self._dataset_key(near_fc)
                nf_id = int(near_fid)

                # Convert line-like near_fid into ORIGINAL_ID space
                if raw_key == lines_copy_key:
                    nf_id = lines_copy_oid_to_orig.get(nf_id, nf_id)
                elif raw_key == target_self_key:
                    nf_id = target_self_oid_to_orig.get(nf_id, nf_id)

                near_fc_key = self._normalize_target_key(
                    near_fc_key=raw_key,
                    lines_key=lines_key,
                    line_keys=line_keys,
                )

                # Defensive guard against self-dangle returning as candidate
                if near_fc_key == dangles_fc_key and nf_id == in_id:
                    continue

                grouped.setdefault(in_id, []).append(
                    {
                        "near_fc_key_raw": raw_key,  # optional: keep for debugging
                        "near_fc_key": near_fc_key,  # normalized key
                        "near_fid": nf_id,
                        "near_dist": dist,
                        "near_x": float(near_x),
                        "near_y": float(near_y),
                    }
                )

        return grouped

    # ----------------------------
    # Planning: choose closest legal + detect pairs
    # ----------------------------

    def _candidate_is_legal(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        dangle_parent: dict[int, int],
        dangles_fc_key: str,
        lines_fc_key: str,
        parent_id: int,
        cand: dict,
        base_tol: float,
        dangle_tol: float,
        component_id: dict[int, int] | None = None,
    ) -> bool:
        ds_key = cand["near_fc_key"]
        oid = int(cand["near_fid"])
        dist = float(cand["near_dist"])

        a_comp = component_id.get(int(parent_id)) if component_id is not None else None

        if ds_key == dangles_fc_key:
            if dist > dangle_tol:
                return False

            other_parent = dangle_parent.get(int(oid))
            if other_parent is None:
                return False

            # NEW: disallow snapping to a dangle whose parent is in the same connected component
            if a_comp is not None and component_id is not None:
                if component_id.get(int(other_parent)) == a_comp:
                    return False

            # existing illegal check (treat as snapping to that parent line)
            if self._is_illegal(
                illegal=illegal,
                parent_id=parent_id,
                target_fc_key=lines_fc_key,
                target_oid=int(other_parent),
            ):
                return False

            return True

        # non-dangle
        if dist > base_tol:
            return False

        if ds_key == lines_fc_key and int(oid) == int(parent_id):
            return False

        # NEW: disallow snapping to a line in the same connected component
        if ds_key == lines_fc_key and a_comp is not None and component_id is not None:
            if component_id.get(int(oid)) == a_comp:
                return False

        if self._is_illegal(
            illegal=illegal,
            parent_id=parent_id,
            target_fc_key=ds_key,
            target_oid=oid,
        ):
            return False

        return True

    def _pair_token_from_candidate(
        self,
        *,
        dangle_parent: dict[int, int],
        dangles_fc_key: str,
        lines_fc_keys: set[str],
        cand: dict,
    ) -> Optional[int]:
        """
        Returns the *other parent line id* if this candidate represents “the other side”
        of a potential dangle pair (either via dangle feature or via line feature).
        """
        ds_key = cand["near_fc_key"]
        oid = int(cand["near_fid"])

        if ds_key == dangles_fc_key:
            other_parent = dangle_parent.get(oid)
            return int(other_parent) if other_parent is not None else None

        if ds_key in lines_fc_keys:
            return int(oid)

        return None

    def _select_first_legal_candidate(
        self,
        *,
        candidates_sorted: list[dict],
        illegal: dict[int, dict[str, set[int]]],
        dangle_parent: dict[int, int],
        dangles_fc_key: str,
        lines_fc_key: str,
        parent_id: int,
        base_tol: float,
        dangle_tol: float,
        component_id: dict[int, int] | None = None,
    ) -> Optional[dict]:
        for cand in candidates_sorted:
            if self._candidate_is_legal(
                illegal=illegal,
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_fc_key,
                lines_fc_key=lines_fc_key,
                parent_id=parent_id,
                cand=cand,
                base_tol=base_tol,
                dangle_tol=dangle_tol,
                component_id=component_id,
            ):
                return cand
        return None

    def _find_specific_dangle_candidate(
        self,
        *,
        candidates_sorted: list[dict],
        dangles_fc_key: str,
        other_dangle_oid: int,
        dangle_tol: float,
    ) -> Optional[dict]:
        """
        Find the row that explicitly targets the other *dangle* (not its line),
        within dangle_tol (custom dangle tolerance).
        """
        for cand in candidates_sorted:
            if cand["near_fc_key"] != dangles_fc_key:
                continue
            if int(cand["near_fid"]) != int(other_dangle_oid):
                continue
            if float(cand["near_dist"]) <= float(dangle_tol):
                return cand
        return None

    def _build_component_ids(
        self, *, adjacency: dict[int, set[int]], nodes: set[int]
    ) -> dict[int, int]:
        comp_id: dict[int, int] = {}
        visited: set[int] = set()
        cid = 0

        for start in nodes | set(adjacency.keys()):
            start = int(start)
            if start in visited:
                continue
            cid += 1
            stack = [start]
            while stack:
                cur = int(stack.pop())
                if cur in visited:
                    continue
                visited.add(cur)
                comp_id[cur] = cid
                for nb in adjacency.get(cur, set()):
                    if nb not in visited:
                        stack.append(int(nb))
        return comp_id

    # ----------------------------
    # Build plan (two-phase: detect pairs first, then decide moves)
    # ----------------------------

    def _build_plan(
        self, *, dangles_fc: str, target_layers: list[str]
    ) -> dict[int, dict]:
        dangle_parent = self._build_dangle_parent_lookup(dangles_fc=dangles_fc)
        dangle_xy = self._build_dangle_xy_lookup(dangles_fc=dangles_fc)

        illegal, adjacency = self.detect_illegal_targets(
            dangle_parent=dangle_parent,
            target_layers=target_layers,
        )
        nodes = set(dangle_parent.values())
        component_id = (
            self._build_component_ids(adjacency=adjacency, nodes=nodes)
            if self.propagate_illigal_targets
            else None
        )
        dangles_key = self._dataset_key(dangles_fc)

        lines_key = self._dataset_key(self.lines_copy)
        lines_fc_keys = self._line_dataset_keys()
        near_features = list(target_layers) + [dangles_fc]

        base_tol = float(self.gap_tolerance_meters)
        dangle_tol = float(self._expanded_dangle_tolerance_meters())

        lines_copy_key = self._dataset_key(self.lines_copy)
        target_self_key = self._dataset_key(self.target_self)

        lines_copy_oid_to_orig = self._oid_to_original_id_lookup(self.lines_copy)
        target_self_oid_to_orig = (
            self._oid_to_original_id_lookup(self.target_self)
            if self.fill_gaps_on_self
            else {}
        )
        # One near-table for everything (expanded radius so we can see dangle pairs)
        self._generate_near_table(
            in_dangles=dangles_fc,
            near_features=near_features,
            search_radius=self._expanded_dangle_tolerance_linear_unit(),
            out_table=self.near_table,
        )
        grouped = self._read_near_table_grouped(
            near_table=self.near_table,
            dangles_fc_key=dangles_key,
            lines_copy_key=lines_copy_key,
            target_self_key=target_self_key,
            lines_copy_oid_to_orig=lines_copy_oid_to_orig,
            target_self_oid_to_orig=target_self_oid_to_orig,
        )

        # DEBUG: inspect first candidates
        lines_key = self._dataset_key(self.lines_copy)
        zero = 0
        line = 0
        total = 0

        for in_id, rows in list(grouped.items())[:2000]:  # sample
            if not rows:
                continue
            r0 = min(rows, key=lambda r: r["near_dist"])
            total += 1
            if float(r0["near_dist"]) == 0.0:
                zero += 1
            if r0["near_fc_key"] == lines_key:
                line += 1

        arcpy.AddMessage(f"DEBUG sample={total} zero_dist={zero} line_key={line}")

        if not grouped:
            return {}

        # ----------------------------
        # Phase 1: per dangle -> first legal + pair token
        # ----------------------------
        total_dangles = 0
        no_parent = 0
        no_legal = 0
        per_dangle: dict[int, dict] = {}
        for dangle_oid, candidates in grouped.items():
            total_dangles += 1
            parent_id = dangle_parent.get(int(dangle_oid))
            if parent_id is None:
                no_parent += 1
                continue

            rows = sorted(candidates, key=lambda r: r["near_dist"])
            first_legal = self._select_first_legal_candidate(
                candidates_sorted=rows,
                illegal=illegal,
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_key,
                lines_fc_key=lines_key,
                parent_id=int(parent_id),
                base_tol=base_tol,
                dangle_tol=dangle_tol,
                component_id=component_id,
            )
            if first_legal is None:
                no_legal += 1
                continue
            token = self._pair_token_from_candidate(
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_key,
                lines_fc_keys=lines_fc_keys,
                cand=first_legal,
            )

            per_dangle[int(dangle_oid)] = {
                "parent_id": int(parent_id),
                "rows": rows,
                "first_legal": first_legal,
                "pair_token_parent": token,  # other parent id if pair-like
            }
            if len(per_dangle) < 20:
                arcpy.AddMessage(
                    f"DEBUG example: dangle_oid={dangle_oid} parent={parent_id} "
                    f"first_legal key={first_legal['near_fc_key']} raw={first_legal.get('near_fc_key_raw')} "
                    f"near_fid={first_legal['near_fid']} dist={first_legal['near_dist']}"
                )

        arcpy.AddMessage(
            f"DEBUG grouped={len(grouped)} total={total_dangles} "
            f"no_parent={no_parent} no_legal={no_legal}"
        )
        if not per_dangle:
            return {}

        # Helper: parent -> dangle oid (assumes one dangle per line; if not, last wins)
        parent_to_dangle: dict[int, int] = {}
        for d_oid, info in per_dangle.items():
            parent_to_dangle[int(info["parent_id"])] = int(d_oid)

        # ----------------------------
        # Phase 2: decide moves with pair logic + defer logic
        # ----------------------------
        decided_by_parent: dict[int, dict] = {}
        deferred_by_parent: dict[int, dict] = {}
        visited_pairs: set[tuple[int, int]] = set()

        for d_oid, info in per_dangle.items():
            a_parent = int(info["parent_id"])
            if a_parent in decided_by_parent or a_parent in deferred_by_parent:
                continue

            token_parent = info["pair_token_parent"]
            if token_parent is None:
                chosen = info["first_legal"]
                dx, dy = dangle_xy[int(d_oid)]
                decided_by_parent[a_parent] = self._make_plan_entry(
                    parent_id=a_parent,
                    dangle_oid=int(d_oid),
                    dangle_x=dx,
                    dangle_y=dy,
                    chosen=chosen,
                    gap_source=self.GAP_SOURCE_DEFAULT,
                )
                continue

            b_parent = int(token_parent)
            if b_parent == a_parent:
                chosen = info["first_legal"]
                dx, dy = dangle_xy[int(d_oid)]
                decided_by_parent[a_parent] = self._make_plan_entry(
                    parent_id=a_parent,
                    dangle_oid=int(d_oid),
                    dangle_x=dx,
                    dangle_y=dy,
                    chosen=chosen,
                    gap_source=self.GAP_SOURCE_DEFAULT,
                )
                continue

            # If the other parent doesn't have a dangle in this run, treat as normal
            b_dangle = parent_to_dangle.get(b_parent)
            if b_dangle is None:
                chosen = info["first_legal"]
                dx, dy = dangle_xy[int(d_oid)]
                decided_by_parent[a_parent] = self._make_plan_entry(
                    parent_id=a_parent,
                    dangle_oid=int(d_oid),
                    dangle_x=dx,
                    dangle_y=dy,
                    chosen=chosen,
                    gap_source=self.GAP_SOURCE_DEFAULT,
                )
                continue

            # Determine if mutual pair: B's closest legal token points back to A
            b_info = per_dangle.get(int(b_dangle))
            if not b_info or int(b_info.get("pair_token_parent") or -1) != int(
                a_parent
            ):
                deferred_by_parent[a_parent] = {
                    "parent_id": a_parent,
                    "dangle_oid": int(d_oid),
                    "forced_target_parent": int(b_parent),
                }
                continue

            # Mutual pair
            pair_key = tuple(sorted((a_parent, b_parent)))
            if pair_key in visited_pairs:
                continue
            visited_pairs.add(pair_key)

            # Pair constraint: they must not share an illegal target object
            if self._parents_share_illegal_target(
                illegal=illegal,
                a_parent=a_parent,
                b_parent=b_parent,
            ):
                # Fall back to normal for each (still mark as pair for symmetric skip)
                for parent, dangle in [
                    (a_parent, int(d_oid)),
                    (b_parent, int(b_dangle)),
                ]:
                    ii = per_dangle[dangle]
                    chosen = ii["first_legal"]
                    dx, dy = dangle_xy[int(dangle)]
                    decided_by_parent[parent] = self._make_plan_entry(
                        parent_id=parent,
                        dangle_oid=int(dangle),
                        dangle_x=dx,
                        dangle_y=dy,
                        chosen=chosen,
                        gap_source=self.GAP_SOURCE_DEFAULT,
                    )
                decided_by_parent[a_parent]["pair_parent"] = b_parent
                decided_by_parent[b_parent]["pair_parent"] = a_parent
                continue

            # ----------------------------
            # Pair preference:
            # - We can snap to each other's DANGLE within dangle_tol
            # - BUT the parent lines must be within base_tol (and legal)
            # ----------------------------

            # (1) Explicit dangle->dangle rows (within custom dangle tolerance)
            a_to_b_dangle = self._find_specific_dangle_candidate(
                candidates_sorted=info["rows"],
                dangles_fc_key=dangles_key,
                other_dangle_oid=int(b_dangle),
                dangle_tol=float(dangle_tol),
            )
            b_to_a_dangle = self._find_specific_dangle_candidate(
                candidates_sorted=b_info["rows"],
                dangles_fc_key=dangles_key,
                other_dangle_oid=int(d_oid),
                dangle_tol=float(dangle_tol),
            )

            # (2) Explicit parent-line proximity rows (must be within base tolerance)
            a_to_b_line = self._find_specific_line_candidate(
                candidates_sorted=info["rows"],
                lines_fc_keys=lines_fc_keys,
                other_parent_id=int(b_parent),
                base_tol=float(base_tol),
            )
            b_to_a_line = self._find_specific_line_candidate(
                candidates_sorted=b_info["rows"],
                lines_fc_keys=lines_fc_keys,
                other_parent_id=int(a_parent),
                base_tol=float(base_tol),
            )

            # (3) Enforce legality for those line candidates too (connected/illegal rules)
            if a_to_b_line is not None and not self._candidate_is_legal(
                illegal=illegal,
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_key,
                lines_fc_key=lines_key,
                parent_id=int(a_parent),
                cand=a_to_b_line,
                base_tol=float(base_tol),
                dangle_tol=float(dangle_tol),
                component_id=component_id,
            ):
                a_to_b_line = None

            if b_to_a_line is not None and not self._candidate_is_legal(
                illegal=illegal,
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_key,
                lines_fc_key=lines_key,
                parent_id=int(b_parent),
                cand=b_to_a_line,
                base_tol=float(base_tol),
                dangle_tol=float(dangle_tol),
                component_id=component_id,
            ):
                b_to_a_line = None

            # Decide chosen targets for each parent
            if (
                a_to_b_dangle is not None
                and b_to_a_dangle is not None
                and a_to_b_line is not None
                and b_to_a_line is not None
            ):
                # Both can snap to each other’s dangle within custom tolerance,
                # AND their parent lines are within base tolerance (and legal)
                a_chosen = a_to_b_dangle
                b_chosen = b_to_a_dangle
                a_source = self.GAP_SOURCE_PAIR_DANGLE
                b_source = self.GAP_SOURCE_PAIR_DANGLE
            else:
                # Pair exists but dangle snap not allowed by constraints
                a_chosen = info["first_legal"]
                b_chosen = b_info["first_legal"]
                a_source = self.GAP_SOURCE_PAIR_LINE
                b_source = self.GAP_SOURCE_PAIR_LINE

            # Write entries (still need symmetric skip: only one moves)
            for parent, dangle, chosen, source in [
                (a_parent, int(d_oid), a_chosen, a_source),
                (b_parent, int(b_dangle), b_chosen, b_source),
            ]:
                dx, dy = dangle_xy[int(dangle)]
                decided_by_parent[int(parent)] = self._make_plan_entry(
                    parent_id=int(parent),
                    dangle_oid=int(dangle),
                    dangle_x=dx,
                    dangle_y=dy,
                    chosen=chosen,
                    gap_source=str(source),
                )

            decided_by_parent[a_parent]["pair_parent"] = b_parent
            decided_by_parent[b_parent]["pair_parent"] = a_parent

        # Apply symmetric skip on mutual pairs (only one moves)
        self._apply_pair_symmetric_skip(decided_by_parent)

        plan = {
            pid: entry
            for pid, entry in decided_by_parent.items()
            if not entry.get("skip", False)
        }

        # Defer phase (one-sided “closest to a dangle-pair object”)
        if deferred_by_parent:
            self._resolve_deferred_moves(
                plan=plan,
                deferred=deferred_by_parent,
            )

        return plan

    def _make_plan_entry(
        self,
        *,
        parent_id: int,
        dangle_oid: int,
        dangle_x: float,
        dangle_y: float,
        chosen: dict,
        gap_source: str,
    ) -> dict:
        edit_op = self._resolve_edit_op(gap_source=str(gap_source))
        return {
            "processed": False,
            "skip": False,
            "gap_source": str(gap_source),
            "edit_op": str(edit_op.value),
            "dangle_oid": int(dangle_oid),
            "dangle_x": float(dangle_x),
            "dangle_y": float(dangle_y),
            "near_x": float(chosen["near_x"]),
            "near_y": float(chosen["near_y"]),
            "chosen_near_fc_key": str(chosen["near_fc_key"]),
            "chosen_near_fid": int(chosen["near_fid"]),
        }

    def _apply_pair_symmetric_skip(self, decided_by_parent: dict[int, dict]) -> None:
        """
        If A and B are marked as pair parents, move only one of them.
        Keep the smaller parent id by default.
        """
        for a_parent, entry in list(decided_by_parent.items()):
            b_parent = entry.get("pair_parent")
            if b_parent is None:
                continue
            b_parent = int(b_parent)

            other = decided_by_parent.get(b_parent)
            if not other:
                continue
            if int(other.get("pair_parent") or -1) != int(a_parent):
                continue

            keep = min(int(a_parent), int(b_parent))
            drop = max(int(a_parent), int(b_parent))

            decided_by_parent[drop]["skip"] = True
            decided_by_parent[keep]["skip"] = False

    # ----------------------------
    # Deferred handling
    # ----------------------------

    def _resolve_deferred_moves(
        self,
        *,
        plan: dict[int, dict],
        deferred: dict[int, dict],
    ) -> None:
        """
        Your requirement (simplified, but aligned):
          - If A “wanted” B as closest but B didn’t want A, A waits.
          - After other edits, run another near table that finds snap point on B’s line,
            accepting a much larger tolerance.
          - Then add A to the plan pointing to the forced target line geometry.

        Implementation:
          - We force near_features = [lines_copy]
          - We run GenerateNearTable from the deferred dangles to lines_copy with large radius
          - For each deferred parent A, we select the row with NEAR_FID == forced_target_parent (B)
        """
        # Build a feature layer of deferred dangles (by OBJECTID)
        dangles_oid = arcpy.Describe(self.filtered_dangles).OIDFieldName
        ids = [str(int(v["dangle_oid"])) for v in deferred.values()]
        if not ids:
            return

        where = f"{arcpy.AddFieldDelimiters(self.filtered_dangles, dangles_oid)} IN ({','.join(ids)})"
        deferred_lyr = "deferred_dangles_lyr"
        arcpy.management.MakeFeatureLayer(self.filtered_dangles, deferred_lyr, where)

        # Large tolerance: choose something intentionally generous but bounded.
        # If you want this configurable later, put it in AdvancedConfig.
        large_m = max(50, int(self.gap_tolerance_meters) * 10)
        large_tol = f"{int(large_m)} Meters"

        forced_table = self.wfm.build_file_path(file_name="deferred_forced_table")
        arcpy.analysis.GenerateNearTable(
            in_features=deferred_lyr,
            near_features=[self.lines_copy],
            out_table=forced_table,
            search_radius=large_tol,
            location="LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

        lines_key = self._dataset_key(self.lines_copy)

        # Map in_dangle_oid -> list of (near_fid, near_x, near_y, dist)
        grouped: dict[int, list[tuple[int, float, float, float]]] = {}
        fields = [
            self.F_IN_FID,
            self.F_NEAR_FID,
            self.F_NEAR_DIST,
            self.F_NEAR_X,
            self.F_NEAR_Y,
        ]
        with arcpy.da.SearchCursor(forced_table, fields) as cur:
            for in_fid, near_fid, near_dist, near_x, near_y in cur:
                if near_fid is None or near_dist is None:
                    continue
                grouped.setdefault(int(in_fid), []).append(
                    (int(near_fid), float(near_x), float(near_y), float(near_dist))
                )

        if not grouped:
            return

        # For each deferred parent, locate the row for its forced target parent line id
        for a_parent, info in deferred.items():
            a_parent = int(a_parent)
            if a_parent in plan:
                continue  # already moved via other logic

            dangle_oid_val = int(info["dangle_oid"])
            forced_parent = int(info["forced_target_parent"])

            rows = grouped.get(dangle_oid_val, [])
            chosen_row = None
            for near_fid, near_x, near_y, dist in rows:
                if int(near_fid) == int(forced_parent):
                    chosen_row = (near_x, near_y)
                    break

            if chosen_row is None:
                continue

            # Need dangle XY from current dangle feature (it might be unchanged, but safer)
            xy_lookup = self._build_dangle_xy_lookup(self.filtered_dangles)
            dangle_x, dangle_y = xy_lookup.get(dangle_oid_val, (None, None))
            if dangle_x is None:
                continue

            plan[a_parent] = {
                "processed": False,
                "skip": False,
                "gap_source": self.GAP_SOURCE_DEFERRED,
                "edit_op": str(
                    self._resolve_edit_op(gap_source=self.GAP_SOURCE_DEFERRED).value
                ),
                "dangle_oid": dangle_oid_val,
                "dangle_x": float(dangle_x),
                "dangle_y": float(dangle_y),
                "near_x": float(chosen_row[0]),
                "near_y": float(chosen_row[1]),
                "chosen_near_fc_key": lines_key,
                "chosen_near_fid": forced_parent,
            }

    # ----------------------------
    # Change output + edits (unchanged from your current version except gap_source field)
    # ----------------------------

    def _setup_line_changes_output(self) -> None:
        if self.line_changes_output is None:
            return

        file_utilities.create_feature_class(
            template_feature=self.lines_copy,
            new_feature=self.line_changes_output,
        )

        existing = {f.name for f in arcpy.ListFields(self.line_changes_output)}

        if self.ORIGINAL_ID not in existing:
            arcpy.management.AddField(
                self.line_changes_output, self.ORIGINAL_ID, "LONG"
            )
        if self.FIELD_GAP_DIST_M not in existing:
            arcpy.management.AddField(
                self.line_changes_output, self.FIELD_GAP_DIST_M, "DOUBLE"
            )
        if self.FIELD_GAP_SOURCE not in existing:
            arcpy.management.AddField(
                self.line_changes_output, self.FIELD_GAP_SOURCE, "TEXT", field_length=20
            )

    def _build_change_row(
        self,
        original_id: int,
        dangle_x: float,
        dangle_y: float,
        near_x: float,
        near_y: float,
        spatial_reference,
        gap_source: str,
    ):
        dist = ((dangle_x - near_x) ** 2 + (dangle_y - near_y) ** 2) ** 0.5
        if dist == 0.0:
            return None

        arr = arcpy.Array(
            [arcpy.Point(dangle_x, dangle_y), arcpy.Point(near_x, near_y)]
        )
        geom = arcpy.Polyline(arr, spatial_reference)
        return (geom, int(original_id), float(dist), str(gap_source))

    def _apply_edits(self, plan: dict[int, dict]) -> None:
        if not plan:
            arcpy.management.CopyFeatures(self.lines_copy, self.output_lines)
            return

        if self.line_changes_output is not None:
            self._setup_line_changes_output()

        spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
        change_rows: list[tuple] = []

        with arcpy.da.UpdateCursor(
            self.lines_copy, [self.ORIGINAL_ID, "SHAPE@"]
        ) as cur:
            for original_id, shape in cur:
                pid = int(original_id)
                info = plan.get(pid)
                if not info:
                    continue
                if (
                    info.get("skip", False) is True
                    or info.get("processed", False) is True
                ):
                    continue

                edit_op = str(info.get("edit_op", logic_config.EditOp.EXTEND.value))

                if edit_op == logic_config.EditOp.SNAP.value:
                    new_shape = self._snap_endpoint(
                        shape=shape,
                        dangle_x=float(info["dangle_x"]),
                        dangle_y=float(info["dangle_y"]),
                        near_x=float(info["near_x"]),
                        near_y=float(info["near_y"]),
                    )
                else:
                    new_shape = self._extend_endpoint(
                        shape=shape,
                        dangle_x=float(info["dangle_x"]),
                        dangle_y=float(info["dangle_y"]),
                        near_x=float(info["near_x"]),
                        near_y=float(info["near_y"]),
                    )
                cur.updateRow((original_id, new_shape))

                if self.line_changes_output is not None:
                    row = self._build_change_row(
                        original_id=pid,
                        dangle_x=float(info["dangle_x"]),
                        dangle_y=float(info["dangle_y"]),
                        near_x=float(info["near_x"]),
                        near_y=float(info["near_y"]),
                        spatial_reference=spatial_reference,
                        gap_source=str(info.get("gap_source", self.GAP_SOURCE_DEFAULT)),
                    )
                    if row is not None:
                        change_rows.append(row)

        if self.line_changes_output is not None and change_rows:
            with arcpy.da.InsertCursor(
                self.line_changes_output,
                [
                    "SHAPE@",
                    self.ORIGINAL_ID,
                    self.FIELD_GAP_DIST_M,
                    self.FIELD_GAP_SOURCE,
                ],
            ) as icur:
                for row in change_rows:
                    icur.insertRow(row)

        arcpy.management.CopyFeatures(self.lines_copy, self.output_lines)

    # ----------------------------
    # Run
    # ----------------------------

    def run(self) -> None:
        environment_setup.main()

        self.work_file_list = self.wfm.setup_work_file_paths(
            instance=self,
            file_structure=self.work_file_list,
        )

        self._copy_input_lines()
        self._add_original_id_field()
        self._create_dangles()

        self._build_external_target_layers_once()
        targets = self._select_targets_within_tolerance_of_dangles()

        # Keep only dangles that have any candidate within base tolerance
        self._filter_true_dangles()
        dangles_for_plan = self.filtered_dangles

        plan = self._build_plan(dangles_fc=dangles_for_plan, target_layers=targets)
        self._apply_edits(plan)

        self.wfm.delete_created_files()
