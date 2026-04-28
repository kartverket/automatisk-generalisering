from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum
import math
import os
import time  # [DBG_LINEGAP]

from typing import Optional, Callable, Iterable, Any, TypeAlias, NamedTuple

import arcpy

from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
from custom_tools.general_tools.line_segmenter import segment_line
from file_manager import WorkFileManager
from composition_configs import logic_config
from composition_configs.logic_config import ConnectivityScope, LineConnectivityMode
from custom_tools.general_tools import geometry_tools


OptionalKey = tuple[str, int]  # (dataset_key, oid)  -- oid is SOURCE oid
ParentEntityKey = tuple[str, int]  # ("parent", parent_id)
OptionalEntityKey = tuple[str, str, int]  # ("optional", dataset_key, oid)
EntityKey = tuple  # union-ish (kept simple)


@dataclass(frozen=True)
class TopologyModel:
    scope: "ConnectivityScope"

    # Component modes only (INPUT_LINES / ONE_DEGREE / TRANSITIVE)
    # cid (connectivity_id) values stay as plain int — they live in topology space,
    # not the dangle/parent id space; see ParentId / DangleOid aliases below.
    connectivity_id_by_parent: Optional[dict[ParentId, int]]
    connectivity_id_by_optional: Optional[dict[OptionalKey, int]]
    entities_by_connectivity_id: Optional[dict[int, set[EntityKey]]]

    # DIRECT_CONNECTION only (required); allowed to be None otherwise
    direct_neighbors_by_parent: Optional[dict[ParentId, set[ParentId]]]
    direct_optionals_by_parent: Optional[dict[ParentId, set[OptionalKey]]]


class EditOp(str, Enum):
    SNAP = "snap"
    EXTEND = "extend"
    NEW_LINE = "new_line"


class GapSource(str, Enum):
    """How a connection was chosen.

    default: single-ended selection. The dangle picked a target on its own, nothing
        on the target side voted to pair back.
    pair_dangle: both endpoints are true dangles that prefer each other's parent
        line. A SNAP edit moves one endpoint onto the other, fusing the pair.
    pair_line: two network nodes each have a proposal pointing at the other. An
        EXTEND edit attaches the source onto the target line.
    """

    DEFAULT = "default"
    PAIR_DANGLE = "pair_dangle"
    PAIR_LINE = "pair_line"


@dataclass(frozen=True)
class NearCandidate:
    """One row from the GenerateNearTable output, already keyed against the canonical
    dataset keys (line-like targets collapsed onto a single ``lines_key``).

    near_fc_key_raw preserves the original dataset key before normalization;
    near_fid_raw preserves the original OID before parent-id mapping. Together
    they let the per-segment angle path reach the segmented twin's polyline
    geometry when segmentation is enabled. With segmentation off, near_fid_raw
    equals near_fid and near_fc_key_raw equals the source FC key.

    near_fid is polymorphic (DangleOid when near_fc_key == dangles_key, ParentId when
    near_fc_key == lines_key, external-dataset FID otherwise); stays as int.
    """

    near_fc_key: DatasetKey
    near_fid: int
    near_dist: float
    near_x: float
    near_y: float
    near_fc_key_raw: DatasetKey
    near_fid_raw: int


@dataclass(frozen=True)
class PlanEntryMeta:
    """Optional diagnostic metadata attached to a PlanEntry when
    ``write_output_metadata`` is enabled."""

    bonus_applied: bool
    src_connector_diff: Optional[float]
    connector_target_diff: Optional[float]
    src_target_diff: Optional[float]
    connector_transition_diff: Optional[float]
    angle_metric_deg: Optional[float]
    best_fit_score: Optional[float]


@dataclass
class PlanEntry:
    """One scheduled edit for a parent line. Mutable so _apply_plan can flip
    ``processed`` and _apply_pair_symmetric_skip / _recheck_resnap_crossings can
    flip ``skip``."""

    dangle_oid: DangleOid
    dangle_x: float
    dangle_y: float
    near_x: float
    near_y: float
    chosen_near_fc_key: DatasetKey
    chosen_near_fid: int
    gap_source: GapSource
    edit_op: EditOp
    pair_parent: Optional[ParentId] = None
    processed: bool = False
    skip: bool = False
    meta: Optional[PlanEntryMeta] = None


@dataclass(frozen=True)
class _GeneratedLineRecord:
    """One pending NEW_LINE materialisation collected during ``_apply_plan``
    and consumed by ``_insert_generated_lines`` after the UpdateCursor closes.
    """

    parent_original_id: ParentId
    dangle_x: float
    dangle_y: float
    near_x: float
    near_y: float


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[EntityKey, EntityKey] = {}
        self._rank: dict[EntityKey, int] = {}

    def add(self, x: EntityKey) -> None:
        if x in self._parent:
            return
        self._parent[x] = x
        self._rank[x] = 0

    def find(self, x: EntityKey) -> EntityKey:
        # Path compression
        p = self._parent.get(x)
        if p is None:
            self.add(x)
            return x
        if p != x:
            self._parent[x] = self.find(p)
        return self._parent[x]

    def union(self, a: EntityKey, b: EntityKey) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        rka = self._rank.get(ra, 0)
        rkb = self._rank.get(rb, 0)
        if rka < rkb:
            self._parent[ra] = rb
        elif rka > rkb:
            self._parent[rb] = ra
        else:
            self._parent[rb] = ra
            self._rank[ra] = rka + 1

    def components(self) -> dict[EntityKey, set[EntityKey]]:
        out: dict[EntityKey, set[EntityKey]] = {}
        for x in list(self._parent.keys()):
            r = self.find(x)
            out.setdefault(r, set()).add(x)
        return out


class TopologyBuilder:
    """
    Value-neutral connectivity inference.

    IMPORTANT:
    - Does NOT use dangle candidate layers.
    - Uses explicit connectivity_tolerance_meters (not arcpy.env.XYTolerance).
    - Optional objects are keyed by (dataset_key, SOURCE_OID).
    """

    def __init__(
        self,
        *,
        lines_fc: str,
        original_id_field: str,
        connect_to_features: Optional[list[str]],
        dataset_key_fn: Callable[[str], str],
        wfm,
        write_work_files_to_memory: bool,
        connectivity_tolerance_meters: float,
        line_connectivity_mode: "LineConnectivityMode",
        file_name_prefix: str = "",
    ) -> None:
        self.lines_fc = lines_fc
        self.original_id_field = original_id_field
        self.connect_to_features = connect_to_features or []
        self.dataset_key_fn = dataset_key_fn
        self.wfm = wfm
        self.write_work_files_to_memory = bool(write_work_files_to_memory)
        self.tol_m = float(connectivity_tolerance_meters)
        self.line_mode = line_connectivity_mode
        self.file_name_prefix = str(file_name_prefix)

    @staticmethod
    def _short_key(key: str, max_len: int = 24) -> str:
        """Truncate a dataset key to at most max_len chars for use in file paths.
        When truncation is needed, keeps the first 16 chars and appends 8 hex
        chars from an MD5 digest of the full key so the result stays unique."""
        if len(key) <= max_len:
            return key
        import hashlib

        return key[:16] + hashlib.md5(key.encode()).hexdigest()[:8]

    def build(
        self,
        *,
        scope: "ConnectivityScope",
        relevant_parent_ids: set[int],
    ) -> TopologyModel:
        scope = ConnectivityScope(scope)

        if scope == ConnectivityScope.NONE:
            return TopologyModel(
                scope=scope,
                connectivity_id_by_parent=None,
                connectivity_id_by_optional=None,
                entities_by_connectivity_id=None,
                direct_neighbors_by_parent=None,
                direct_optionals_by_parent=None,
            )

        if scope == ConnectivityScope.DIRECT_CONNECTION:
            direct_neighbors = self._build_parent_adjacency(
                restrict_to_parent_ids=set(relevant_parent_ids)
            )
            direct_optionals = self._build_parent_optionals(
                parent_ids=set(relevant_parent_ids),
                optional_paths=self.connect_to_features,
                use_connectivity_layers=False,
                transitive_expand=False,
            )
            # Ensure required keys exist for all relevant parents
            for pid in relevant_parent_ids:
                direct_neighbors.setdefault(int(pid), set())
                direct_optionals.setdefault(int(pid), set())

            return TopologyModel(
                scope=scope,
                connectivity_id_by_parent=None,
                connectivity_id_by_optional=None,
                entities_by_connectivity_id=None,
                direct_neighbors_by_parent=direct_neighbors,
                direct_optionals_by_parent=direct_optionals,
            )

        # Component modes:
        # - INPUT_LINES: line-only components
        # - ONE_DEGREE: merge via shared optionals (no optional↔optional traversal)
        # - TRANSITIVE: full closure incl optional↔optional edges
        parent_adjacency = self._build_parent_adjacency(restrict_to_parent_ids=None)

        if scope == ConnectivityScope.INPUT_LINES:
            cid_by_parent, entities_by_cid = self._components_from_line_only(
                parent_adjacency=parent_adjacency
            )

            # Attachments are allowed (optional); compute only for relevant parents
            direct_optionals = self._build_parent_optionals(
                parent_ids=set(relevant_parent_ids),
                optional_paths=self.connect_to_features,
                use_connectivity_layers=False,
                transitive_expand=False,
            )

            return TopologyModel(
                scope=scope,
                connectivity_id_by_parent=cid_by_parent,
                connectivity_id_by_optional=None,
                entities_by_connectivity_id=entities_by_cid,
                direct_neighbors_by_parent=None,
                direct_optionals_by_parent=direct_optionals,
            )

        # ONE_DEGREE / TRANSITIVE
        if not self.connect_to_features:
            # No optionals to participate; degrade to line-only components
            cid_by_parent, entities_by_cid = self._components_from_line_only(
                parent_adjacency=parent_adjacency
            )
            return TopologyModel(
                scope=scope,
                connectivity_id_by_parent=cid_by_parent,
                connectivity_id_by_optional=None,
                entities_by_connectivity_id=entities_by_cid,
                direct_neighbors_by_parent=None,
                direct_optionals_by_parent=None,
            )

        transitive_expand = scope == ConnectivityScope.TRANSITIVE

        # Build reduced connectivity layers for optionals (feature layers with selection),
        # seeded by lines_fc (NOT dangles), optionally expanded within dataset for TRANSITIVE.
        optional_layers = self._build_optional_connectivity_layers(
            optional_paths=self.connect_to_features,
            transitive_expand=transitive_expand,
        )

        parent_to_optional = self._build_parent_optionals(
            parent_ids=None,  # compute for all parents that touch selected optionals
            optional_paths=self.connect_to_features,
            use_connectivity_layers=True,
            transitive_expand=transitive_expand,
            optional_layers=optional_layers,
        )

        uf = _UnionFind()

        # Ensure all parent nodes exist (so isolated parents get deterministic ids too)
        for pid in self._iter_all_parent_ids():
            uf.add(("parent", int(pid)))

        # Add selected optional nodes
        for ds_key, opt_layer in optional_layers:
            oid_field = arcpy.Describe(opt_layer).OIDFieldName
            with arcpy.da.SearchCursor(opt_layer, [oid_field]) as cur:
                for (oid,) in cur:
                    uf.add(("optional", str(ds_key), int(oid)))

        # parent↔parent unions
        for a, nbs in parent_adjacency.items():
            a_ent: ParentEntityKey = ("parent", int(a))
            for b in nbs:
                uf.union(a_ent, ("parent", int(b)))

        # parent↔optional unions (ONE_DEGREE + TRANSITIVE)
        for pid, opt_keys in parent_to_optional.items():
            p_ent: ParentEntityKey = ("parent", int(pid))
            for ds_key, oid in opt_keys:
                uf.union(p_ent, ("optional", str(ds_key), int(oid)))

        # optional↔optional unions (TRANSITIVE only)
        if scope == ConnectivityScope.TRANSITIVE:
            for ds_a, layer_a in optional_layers:
                # within-dataset
                self._union_optional_optional_edges(
                    uf=uf,
                    in_layer=layer_a,
                    near_layer=layer_a,
                    ds_in=str(ds_a),
                    ds_near=str(ds_a),
                )
            # cross-dataset
            for i in range(len(optional_layers)):
                ds_i, lyr_i = optional_layers[i]
                for j in range(i + 1, len(optional_layers)):
                    ds_j, lyr_j = optional_layers[j]
                    self._union_optional_optional_edges(
                        uf=uf,
                        in_layer=lyr_i,
                        near_layer=lyr_j,
                        ds_in=str(ds_i),
                        ds_near=str(ds_j),
                    )

        cid_by_parent, cid_by_optional, entities_by_cid = self._assign_component_ids(uf)

        return TopologyModel(
            scope=scope,
            connectivity_id_by_parent=cid_by_parent,
            connectivity_id_by_optional=cid_by_optional,
            entities_by_connectivity_id=entities_by_cid,
            direct_neighbors_by_parent=None,
            direct_optionals_by_parent=parent_to_optional,  # useful primitive
        )

    # ----------------------------
    # Parent ids
    # ----------------------------

    def _iter_all_parent_ids(self) -> Iterable[int]:
        with arcpy.da.SearchCursor(self.lines_fc, [self.original_id_field]) as cur:
            for (pid,) in cur:
                yield int(pid)

    # ----------------------------
    # Parent↔parent adjacency
    # ----------------------------

    def _build_parent_adjacency(
        self, *, restrict_to_parent_ids: Optional[set[int]]
    ) -> dict[int, set[int]]:
        if self.line_mode == LineConnectivityMode.INTERSECT:
            return self._build_parent_adjacency_intersect(restrict_to_parent_ids)
        return self._build_parent_adjacency_endpoints(restrict_to_parent_ids)

    def _build_parent_adjacency_endpoints(
        self, restrict_to_parent_ids: Optional[set[int]]
    ) -> dict[int, set[int]]:
        endpoints_fc = self.wfm.build_file_path(
            file_name=f"{self.file_name_prefix}topo_line_endpoints"
        )
        arcpy.management.FeatureVerticesToPoints(
            self.lines_fc, endpoints_fc, "BOTH_ENDS"
        )

        endpoints_lyr = "topo_endpoints_lyr"
        arcpy.management.MakeFeatureLayer(endpoints_fc, endpoints_lyr)

        if restrict_to_parent_ids:
            where = self._where_in_ints(
                endpoints_fc, self.original_id_field, restrict_to_parent_ids
            )
            arcpy.management.SelectLayerByAttribute(
                endpoints_lyr, "NEW_SELECTION", where
            )

        near_table = self.wfm.build_file_path(
            file_name=f"{self.file_name_prefix}topo_endpoints_near_lines"
        )
        arcpy.analysis.GenerateNearTable(
            in_features=endpoints_lyr,
            near_features=[self.lines_fc],
            out_table=near_table,
            search_radius=self._meters(self.tol_m),
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

        # endpoint OID -> parent_id
        endpoint_oid = arcpy.Describe(endpoints_lyr).OIDFieldName
        endpoint_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            endpoints_lyr, [endpoint_oid, self.original_id_field]
        ) as cur:
            for eo, pid in cur:
                endpoint_parent[int(eo)] = int(pid)

        # line OID -> parent_id (ORIGINAL_ID space)
        lines_oid = arcpy.Describe(self.lines_fc).OIDFieldName
        line_oid_to_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            self.lines_fc, [lines_oid, self.original_id_field]
        ) as cur:
            for oid, pid in cur:
                line_oid_to_parent[int(oid)] = int(pid)

        out: dict[int, set[int]] = {}
        fields = ["IN_FID", "NEAR_FID", "NEAR_DIST"]
        with arcpy.da.SearchCursor(near_table, fields) as cur:
            for in_fid, near_fid, near_dist in cur:
                if near_fid is None or near_dist is None:
                    continue
                if float(near_dist) >= float(self.tol_m):
                    continue
                a_parent = endpoint_parent.get(int(in_fid))
                if a_parent is None:
                    continue
                b_parent = line_oid_to_parent.get(int(near_fid))
                if b_parent is None:
                    continue
                if int(a_parent) == int(b_parent):
                    continue
                out.setdefault(int(a_parent), set()).add(int(b_parent))
                out.setdefault(int(b_parent), set()).add(int(a_parent))
        return out

    def _build_parent_adjacency_intersect(
        self, restrict_to_parent_ids: Optional[set[int]]
    ) -> dict[int, set[int]]:
        lines_lyr = "topo_lines_lyr"
        arcpy.management.MakeFeatureLayer(self.lines_fc, lines_lyr)

        if restrict_to_parent_ids:
            where = self._where_in_ints(
                self.lines_fc, self.original_id_field, restrict_to_parent_ids
            )
            arcpy.management.SelectLayerByAttribute(lines_lyr, "NEW_SELECTION", where)

        near_table = self.wfm.build_file_path(
            file_name=f"{self.file_name_prefix}topo_lines_near_lines"
        )
        arcpy.analysis.GenerateNearTable(
            in_features=lines_lyr,
            near_features=[self.lines_fc],
            out_table=near_table,
            search_radius=self._meters(self.tol_m),
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

        lines_oid = arcpy.Describe(self.lines_fc).OIDFieldName
        line_oid_to_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            self.lines_fc, [lines_oid, self.original_id_field]
        ) as cur:
            for oid, pid in cur:
                line_oid_to_parent[int(oid)] = int(pid)

        out: dict[int, set[int]] = {}
        fields = ["IN_FID", "NEAR_FID", "NEAR_DIST"]
        with arcpy.da.SearchCursor(near_table, fields) as cur:
            for in_fid, near_fid, near_dist in cur:
                if near_fid is None or near_dist is None:
                    continue
                if float(near_dist) > float(self.tol_m):
                    continue
                a_parent = line_oid_to_parent.get(int(in_fid))
                b_parent = line_oid_to_parent.get(int(near_fid))
                if a_parent is None or b_parent is None:
                    continue
                if int(a_parent) == int(b_parent):
                    continue
                out.setdefault(int(a_parent), set()).add(int(b_parent))
                out.setdefault(int(b_parent), set()).add(int(a_parent))
        return out

    # ----------------------------
    # Parent↔optional links (whole-geometry; value-neutral)
    # ----------------------------

    def _build_optional_connectivity_layers(
        self, *, optional_paths: list[str], transitive_expand: bool
    ) -> list[tuple[str, str]]:
        """
        Returns [(dataset_key, selected_feature_layer_name), ...]
        Selection is seeded by lines_fc (NOT dangles). For TRANSITIVE, expands optional↔optional
        within the same dataset until stable.
        """
        out: list[tuple[str, str]] = []
        overlap_type, search_distance = self._overlap_for_tol()

        for index, path in enumerate(optional_paths):
            ds_key = self.dataset_key_fn(path)
            lyr = f"topo_opt_{index}_lyr"
            arcpy.management.MakeFeatureLayer(path, lyr)

            arcpy.management.SelectLayerByLocation(
                in_layer=lyr,
                overlap_type=overlap_type,
                select_features=self.lines_fc,
                search_distance=search_distance,
                selection_type="NEW_SELECTION",
            )

            if transitive_expand:
                # Expansion within dataset:
                # Repeatedly add optionals that intersect/touch the current selection until stable.
                # NOTE: passing a layer with a selection uses the selection set as the geometry source.
                prev = -1
                while True:
                    cur = int(arcpy.management.GetCount(lyr)[0])
                    if cur == prev:
                        break
                    prev = cur
                    arcpy.management.SelectLayerByLocation(
                        in_layer=lyr,
                        overlap_type=overlap_type,
                        select_features=lyr,
                        search_distance=search_distance,
                        selection_type="ADD_TO_SELECTION",
                    )

            out.append((str(ds_key), lyr))

        return out

    def _build_parent_optionals(
        self,
        *,
        parent_ids: Optional[set[int]],
        optional_paths: list[str],
        use_connectivity_layers: bool,
        transitive_expand: bool,
        optional_layers: Optional[list[tuple[str, str]]] = None,
    ) -> dict[int, set[OptionalKey]]:
        """
        Returns parent_id -> set[(dataset_key, source_oid)].

        - DIRECT_CONNECTION / INPUT_LINES attachments:
            use_connectivity_layers=False; builds links against original datasets.
            If parent_ids is provided, only computes for those parents.

        - ONE_DEGREE / TRANSITIVE component modes:
            use_connectivity_layers=True; links against selected optional layers.
            parent_ids is ignored (we compute for all parents that touch selected optionals).
        """
        out: dict[int, set[OptionalKey]] = {}

        if not optional_paths:
            return out

        # Lines layer, optionally restricted to specific parents
        lines_lyr = "topo_lines_for_opt_lyr"
        arcpy.management.MakeFeatureLayer(self.lines_fc, lines_lyr)
        if parent_ids is not None:
            where = self._where_in_ints(
                self.lines_fc, self.original_id_field, parent_ids
            )
            arcpy.management.SelectLayerByAttribute(lines_lyr, "NEW_SELECTION", where)

        overlap_type, search_distance = self._overlap_for_tol()

        if use_connectivity_layers:
            if optional_layers is None:
                optional_layers = self._build_optional_connectivity_layers(
                    optional_paths=optional_paths,
                    transitive_expand=transitive_expand,
                )

            # Restrict lines to those near selected optionals (correct + faster than scanning all lines)
            # Union all optionals by selecting against each optional layer
            arcpy.management.SelectLayerByAttribute(lines_lyr, "CLEAR_SELECTION")
            for _, opt_lyr in optional_layers:
                arcpy.management.SelectLayerByLocation(
                    in_layer=lines_lyr,
                    overlap_type=overlap_type,
                    select_features=opt_lyr,
                    search_distance=search_distance,
                    selection_type="ADD_TO_SELECTION",
                )

            # Now link per dataset-layer (so dataset_key is explicit and stable)
            for ds_key, opt_lyr in optional_layers:
                table = self.wfm.build_file_path(
                    file_name=f"{self.file_name_prefix}topo_lines_to_opt_{self._short_key(ds_key)}"
                )
                arcpy.analysis.GenerateNearTable(
                    in_features=lines_lyr,
                    near_features=[opt_lyr],
                    out_table=table,
                    search_radius=self._meters(self.tol_m),
                    location="NO_LOCATION",
                    angle="NO_ANGLE",
                    closest="ALL",
                    closest_count=200,
                    method="PLANAR",
                )

                # IN_FID is line OID, but we want parent_id from ORIGINAL_ID
                lines_oid = arcpy.Describe(self.lines_fc).OIDFieldName
                line_oid_to_parent: dict[int, int] = {}
                with arcpy.da.SearchCursor(
                    self.lines_fc, [lines_oid, self.original_id_field]
                ) as cur:
                    for oid, pid in cur:
                        line_oid_to_parent[int(oid)] = int(pid)

                fields = ["IN_FID", "NEAR_FID", "NEAR_DIST"]
                with arcpy.da.SearchCursor(table, fields) as cur:
                    for in_fid, near_fid, near_dist in cur:
                        if near_fid is None or near_dist is None:
                            continue
                        if float(near_dist) > float(self.tol_m):
                            continue
                        pid = line_oid_to_parent.get(int(in_fid))
                        if pid is None:
                            continue
                        out.setdefault(int(pid), set()).add(
                            (str(ds_key), int(near_fid))
                        )
            return out

        # Non-connectivity-layer mode: link per original dataset path (stable ds_key)
        for path in optional_paths:
            ds_key = self.dataset_key_fn(path)
            table = self.wfm.build_file_path(
                file_name=f"{self.file_name_prefix}topo_lines_to_opt_attach_{self._short_key(ds_key)}"
            )

            arcpy.analysis.GenerateNearTable(
                in_features=lines_lyr,
                near_features=[path],
                out_table=table,
                search_radius=self._meters(self.tol_m),
                location="NO_LOCATION",
                angle="NO_ANGLE",
                closest="ALL",
                closest_count=200,
                method="PLANAR",
            )

            lines_oid = arcpy.Describe(self.lines_fc).OIDFieldName
            line_oid_to_parent: dict[int, int] = {}
            with arcpy.da.SearchCursor(
                self.lines_fc, [lines_oid, self.original_id_field]
            ) as cur:
                for oid, pid in cur:
                    line_oid_to_parent[int(oid)] = int(pid)

            fields = ["IN_FID", "NEAR_FID", "NEAR_DIST"]
            with arcpy.da.SearchCursor(table, fields) as cur:
                for in_fid, near_fid, near_dist in cur:
                    if near_fid is None or near_dist is None:
                        continue
                    if float(near_dist) > float(self.tol_m):
                        continue
                    pid = line_oid_to_parent.get(int(in_fid))
                    if pid is None:
                        continue
                    out.setdefault(int(pid), set()).add((str(ds_key), int(near_fid)))

        return out

    def _union_optional_optional_edges(
        self,
        *,
        uf: _UnionFind,
        in_layer: str,
        near_layer: str,
        ds_in: str,
        ds_near: str,
    ) -> None:
        """
        Adds undirected optional↔optional edges to union-find for TRANSITIVE.
        """
        table = self.wfm.build_file_path(
            file_name=f"{self.file_name_prefix}topo_optopt_{self._short_key(ds_in)}_to_{self._short_key(ds_near)}"
        )
        arcpy.analysis.GenerateNearTable(
            in_features=in_layer,
            near_features=[near_layer],
            out_table=table,
            search_radius=self._meters(self.tol_m),
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=500,
            method="PLANAR",
        )

        fields = ["IN_FID", "NEAR_FID", "NEAR_DIST"]
        with arcpy.da.SearchCursor(table, fields) as cur:
            for in_fid, near_fid, near_dist in cur:
                if near_fid is None or near_dist is None:
                    continue
                if float(near_dist) > float(self.tol_m):
                    continue
                if int(in_fid) == int(near_fid) and ds_in == ds_near:
                    continue
                uf.union(
                    ("optional", str(ds_in), int(in_fid)),
                    ("optional", str(ds_near), int(near_fid)),
                )

    # ----------------------------
    # Components + determinism
    # ----------------------------

    def _components_from_line_only(
        self, *, parent_adjacency: dict[int, set[int]]
    ) -> tuple[dict[int, int], dict[int, set[EntityKey]]]:
        uf = _UnionFind()
        for pid in self._iter_all_parent_ids():
            uf.add(("parent", int(pid)))
        for a, nbs in parent_adjacency.items():
            for b in nbs:
                uf.union(("parent", int(a)), ("parent", int(b)))
        cid_by_parent, _, entities_by_cid = self._assign_component_ids(uf)
        return cid_by_parent, entities_by_cid

    def _assign_component_ids(
        self, uf: _UnionFind
    ) -> tuple[dict[int, int], dict[OptionalKey, int], dict[int, set[EntityKey]]]:
        comps = uf.components()  # root -> set[entity]
        # Deterministic ordering by smallest entity key (tuple ordering is deterministic)
        ordered = sorted((min(members), root) for root, members in comps.items())

        cid_by_parent: dict[int, int] = {}
        cid_by_optional: dict[OptionalKey, int] = {}
        entities_by_cid: dict[int, set[EntityKey]] = {}

        for idx, (_, root) in enumerate(ordered, start=1):
            members = comps[root]
            entities_by_cid[idx] = set(members)
            for ent in members:
                if not ent:
                    continue
                if ent[0] == "parent":
                    cid_by_parent[int(ent[1])] = int(idx)
                elif ent[0] == "optional":
                    cid_by_optional[(str(ent[1]), int(ent[2]))] = int(idx)

        return cid_by_parent, cid_by_optional, entities_by_cid

    # ----------------------------
    # Small helpers
    # ----------------------------

    def _meters(self, value_m: float) -> str:
        return f"{float(value_m)} Meters"

    def _overlap_for_tol(self) -> tuple[str, Optional[str]]:
        if float(self.tol_m) <= 0.0:
            return "INTERSECT", None
        return "WITHIN_A_DISTANCE", self._meters(self.tol_m)

    def _where_in_ints(self, fc: str, field_name: str, ids: set[int]) -> str:
        # Defensive for empty sets
        safe = sorted({int(v) for v in ids})
        if not safe:
            return "1=0"
        fld = arcpy.AddFieldDelimiters(fc, field_name)
        return f"{fld} IN ({','.join(str(v) for v in safe)})"


@dataclass(frozen=True)
class _CandidateContext:
    """Fixed metadata for a dangle winner; carried unchanged across scope promotions."""

    # Topology routing
    dangle_oid: DangleOid
    src_parent_id: ParentId
    src_node: "EntityKey"
    tgt_node: "EntityKey"
    pair_key: "tuple[EntityKey, EntityKey]"
    target_parent_id: Optional[ParentId]
    target_dangle_oid: Optional[DangleOid]
    near_fc_key: DatasetKey
    near_fid: int  # polymorphic: DangleOid / ParentId / external FID
    # Geometry
    dangle_x: float
    dangle_y: float
    near_x: float
    near_y: float
    raw_distance: float
    bonus_applied: bool
    # Scoring inputs (fixed; needed for diagnostics and score recomputation)
    start_z: Optional[float]  # Z at source dangle endpoint
    end_z: Optional[float]  # Z at target near-point
    norm_dist: float  # raw_distance / gap_tolerance_meters
    # assess is always populated on constructed contexts — code paths that
    # early-return before proposal construction never reach _CandidateContext.
    assess: "AngleAssessment"


@dataclass(frozen=True)
class _ProposalScore:
    """Readable replacement for the opaque score tuple."""

    composite: float  # weighted best-fit score (primary sort key)
    bonus_rank: int  # 0 = bonus applied, 1 = no bonus
    norm_dist: float  # effective distance component [0, 1]
    norm_angle: Optional[float]  # angle component [0, 1]; None if unavailable
    norm_z: Optional[float]  # Z component at current scope; None if unavailable


@dataclass(frozen=True)
class _DangleProposal:
    """Step-1B winner; Z normalized within its dangle's candidate set."""

    ctx: "_CandidateContext"
    score: "_ProposalScore"  # score.norm_z = dangle_norm_z

    def sort_key(self) -> tuple:
        c = self.ctx
        return (
            self.score.composite,
            self.score.bonus_rank,
            c.raw_distance,
            c.src_parent_id,
            c.dangle_oid,
            c.near_fc_key,
            c.near_fid,
        )


@dataclass(frozen=True)
class _ConnectionProposal:
    """Stage-A candidate; Z normalized within its pair_key group.

    gap_source is stamped in _run_connection_selection; instances observed
    downstream of selection have it non-None.
    """

    ctx: "_CandidateContext"
    dangle_norm_z: Optional[float]  # carried from _DangleProposal.score.norm_z
    score: "_ProposalScore"  # score.norm_z = connection_norm_z
    gap_source: Optional[GapSource] = None

    @classmethod
    def from_dangle(
        cls, d: "_DangleProposal", score: "_ProposalScore"
    ) -> "_ConnectionProposal":
        return cls(ctx=d.ctx, dangle_norm_z=d.score.norm_z, score=score)

    def sort_key(self) -> tuple:
        c = self.ctx
        return (
            self.score.composite,
            self.score.bonus_rank,
            c.raw_distance,
            c.src_parent_id,
            c.dangle_oid,
            c.near_fc_key,
            c.near_fid,
        )


@dataclass(frozen=True)
class _GlobalProposal:
    """Stage-B candidate; Z normalized across all Stage-A winners."""

    ctx: "_CandidateContext"
    dangle_norm_z: Optional[float]
    connection_norm_z: Optional[float]
    score: "_ProposalScore"  # score.norm_z = global_norm_z
    gap_source: GapSource

    @classmethod
    def from_network(
        cls, n: "_ConnectionProposal", score: "_ProposalScore"
    ) -> "_GlobalProposal":
        assert (
            n.gap_source is not None
        ), "_ConnectionProposal.gap_source must be stamped before promotion to Stage B"
        return cls(
            ctx=n.ctx,
            dangle_norm_z=n.dangle_norm_z,
            connection_norm_z=n.score.norm_z,
            score=score,
            gap_source=n.gap_source,
        )

    def sort_key(self) -> tuple:
        c = self.ctx
        return (
            self.score.composite,
            self.score.bonus_rank,
            c.raw_distance,
            c.src_parent_id,
            c.dangle_oid,
            c.near_fc_key,
            c.near_fid,
        )


@dataclass(frozen=True)
class AcceptedConnectorRaw:
    """Raw geometry of an accepted Kruskal connection; used by the resnap
    crossing re-check to re-trim connectors against post-apply geometry."""

    dangle_oid: DangleOid
    dangle_x: float
    dangle_y: float
    near_x: float
    near_y: float


@dataclass(frozen=True)
class _ResnappedCapture:
    """
    Metadata for an accepted connection whose near-point may land on a segment
    that moves when another accepted SNAP connection applies.

    Identified after Stage B; geometry is re-resolved in _resnap_connections
    using post-apply lines_copy geometry.
    """

    parent_id: ParentId
    dangle_oid: DangleOid
    forced_target_parent: ParentId  # target_parent_id of the accepted connection
    proposal: "_GlobalProposal"
    gap_source: GapSource


@dataclass(frozen=True)
class AngleAssessment:
    # Primary decisions
    available: bool
    blocks: bool
    allow_extra_dangle: bool  # expanded dangle tol + edge-case bonus
    angle_metric_deg: Optional[float]
    # Normalisation range for angle_metric_deg used in best-fit scoring.
    # 90.0 for undirected line-like targets and non-line targets in undirected mode;
    # 180.0 whenever directional comparison is in effect — i.e. lines_are_directed,
    # or a dangle endpoint snap (target is a dangle, or the parent line at one of
    # its dangle endpoints) regardless of mode.
    angle_max_deg: float = 90.0

    # Diagnostics (optional)
    src_connector_diff: Optional[float] = None
    connector_target_diff: Optional[float] = None
    src_target_diff: Optional[float] = None
    connector_transition_diff: Optional[float] = None


@dataclass(frozen=True, slots=True)
class ScopeRecord:
    """
    Status snapshot at one pipeline scope for a candidate connection.

    status: the outcome at this scope (scope-specific vocabulary; see CandidateDiagnostic).
    reason: optional detail string; None when status is self-explanatory (e.g. "scored",
        "accepted").
    norm_z: Z value normalized within this scope's candidate comparison set; None when Z
        is inactive or the scope was not reached.
    """

    status: str
    reason: Optional[str] = None
    norm_z: Optional[float] = None


@dataclass
class CandidateDiagnostic:
    """
    Diagnostic record for one candidate connection evaluated during the main planning phase.

    One record exists per (dangle, target) pair, excluding the self parent line target.
    The dataclass is mutable so that resnap outcomes can update deferred_scope and
    final_status after _resnap_connections resolves.

    Per-scope fields record the outcome at each pipeline stage independently. None means
    the candidate did not reach that scope. final_status repeats the last non-None scope.

    Candidate scope status values (candidate_scope.status):
        Illegal: beyond_distance_tolerance | same_network | illegal_target |
                 crosses_existing_feature | crosses_barrier_layer | directed_start_node |
                 blocked_by_angle | expanded_dangle_angle_disallowed | blocked_by_z_drop
        Passed:  scored

    Network scope status values (network_scope.status):
        outscored_within_dangle | lost_connection_selection | passed

    Kruskal scope status values (kruskal_scope.status):
        lost_kruskal_selection | crosses_accepted_connector | accepted

    Deferred scope status values (deferred_scope.status):
        applied_resnapped | resnap_crossing_rejected | resnap_crossing_displaced |
        referenced_as_winner

    final_status repeats the last non-None scope. For accepted non-resnapped candidates
    deferred_scope is None and final_status repeats kruskal_scope.
    """

    parent_id: ParentId
    dangle_oid: DangleOid
    dangle_x: float
    dangle_y: float
    near_fc_key: DatasetKey
    near_fid: int  # polymorphic; see NearCandidate
    near_x: float
    near_y: float
    raw_distance: float
    candidate_scope: ScopeRecord
    network_scope: Optional[ScopeRecord]
    kruskal_scope: Optional[ScopeRecord]
    deferred_scope: Optional[ScopeRecord]
    final_status: ScopeRecord
    best_fit_score: Optional[float]
    best_fit_rank: Optional[int]
    bonus_applied: Optional[bool]
    norm_dist: Optional[float]
    norm_angle: Optional[float]
    assess: Optional[AngleAssessment]
    target_parent_id: Optional[ParentId]
    final_gap_source: Optional[str]
    start_z: Optional[float] = None
    end_z: Optional[float] = None


# ---------------------------------------------------------------------------
# Pipeline type aliases
# ---------------------------------------------------------------------------
# Semantic id families. Runtime unchanged; these are readability annotations.
DangleOid: TypeAlias = int
ParentId: TypeAlias = int  # ORIGINAL_ID space for lines_copy
DatasetKey: TypeAlias = str

_DangleXYsByParent: TypeAlias = dict[ParentId, list[tuple[float, float]]]
_IllegalTargets: TypeAlias = dict[ParentId, dict[DatasetKey, set[int]]]
_NormZByDangle: TypeAlias = dict[DangleOid, Optional[float]]


class _CandidateIllegalA(NamedTuple):
    """Candidate rejected at Step 1A (distance/network/legality gate) before angle assessment."""

    dangle_oid: DangleOid
    parent_id: ParentId
    cand: NearCandidate
    reason: str


class _CandidateIllegalB(NamedTuple):
    """Candidate rejected at Step 1B (angle/Z gate) after angle assessment."""

    dangle_oid: DangleOid
    parent_id: ParentId
    cand: NearCandidate
    assess: AngleAssessment
    reason: str
    start_z: Optional[float]
    end_z: Optional[float]


class _CandidateScored(NamedTuple):
    """Candidate that survived all legality gates and received a composite score."""

    dangle_oid: DangleOid
    parent_id: ParentId
    cand: NearCandidate
    assess: AngleAssessment
    raw_distance: float
    best_fit: float
    bonus: bool
    is_local_winner: bool
    score_tuple: tuple[float, int, float]
    norm_dist: float
    norm_angle: Optional[float]
    dangle_norm_z: Optional[float]
    start_z: Optional[float]
    end_z: Optional[float]


class _DirectionalNormalization(NamedTuple):
    """Outcome of normalising angles for the directional metric.

    Undirected mode flips ``src_angle_deg`` and ``target_angle`` so a clean
    collinear pair scores 0°; directed mode replaces ``src_connector_diff``
    with the directional difference so anti-parallel src/connector reports
    180° instead of collapsing under orientation_diff. ``endpoint_snap`` is
    surfaced so the metric helper can apply the target-start topology rule
    without re-deriving it.
    """

    src_angle_deg: float
    target_angle: float
    src_connector_diff: float
    endpoint_snap: bool


class _TargetAngleResolution(NamedTuple):
    """Result of resolving a candidate's target polyline and snap point.

    target_angle is None when the polyline is missing (parent unknown, geometry
    not cached). tgt_poly mirrors that — None when the helper cannot resolve
    geometry. snap_x/snap_y are the coordinates used for both local angle
    sampling and downstream endpoint topology checks; for dangle-pair targets
    these prefer the precise dangle XY over the near-table snap.
    target_parent_id is set for line-like input candidates (line target →
    own parent; dangle target → the other dangle's parent line), None for
    external datasets.
    """

    target_angle: Optional[float]
    tgt_poly: Any
    snap_x: float
    snap_y: float
    target_parent_id: Optional[ParentId] = None


@dataclass(frozen=True)
class _ScoredCandidateItem:
    """One scored candidate row inside _select_dangle_proposals.

    Collected per dangle; the `min(...)` winner is promoted to a _DangleProposal.
    Replaces a positional 10-tuple.
    """

    score: "_ProposalScore"
    cand: NearCandidate
    raw_distance: float
    effective_for_scoring: float
    bonus_applied: bool
    assess: AngleAssessment
    norm_z: Optional[float]
    norm_dist: float
    norm_angle: Optional[float]
    end_z: Optional[float]


@dataclass(frozen=True)
class _AngleCaches:
    """Polyline and line-type caches consumed by the CANDIDATE scope.

    polyline_by_parent: self-line polylines keyed by parent_id. Used for the
        SOURCE side of every candidate (the source dangle sits at a parent
        endpoint) and for dangle-to-dangle target lookups (the other dangle is
        also at its parent's endpoint).
    polyline_by_external: polylines from external polyline targets, keyed by
        SOURCE dataset_key then SOURCE OID. Used for the target side when
        segmentation is None. Only populated for targets that survive the
        line-like classification below.
    polyline_by_segment: polylines from segmented twin FCs, keyed by raw
        segmented dataset_key then segmented OID. Empty when segmentation is
        None. Used for the target side when segmentation is set so each
        candidate is scored against its own segment's local geometry.
    is_external_line_like: per external dataset_key, whether it is treated as
        a line-like target for scoring. Respects
        connect_to_features_angle_mode overrides.
    line_like_external_ds_keys: subset of is_external_line_like where the
        value is True.
    line_like_ds_keys: line_like_external_ds_keys plus lines_key when
        fill_gaps_on_self is active.
    """

    polyline_by_parent: dict[ParentId, Any]
    polyline_by_external: dict[DatasetKey, dict[int, Any]]
    polyline_by_segment: dict[DatasetKey, dict[int, Any]]
    is_external_line_like: dict[DatasetKey, bool]
    line_like_external_ds_keys: set[DatasetKey]
    line_like_ds_keys: set[DatasetKey]


@dataclass
class _DiagnosticsState:
    """All pipeline state collected during _build_plan for diagnostic assembly.

    Every field defaults to empty so early bail-outs only need to pass the
    fields that have actually been populated up to that point.
    """

    step1a_illegal: list[_CandidateIllegalA] = field(default_factory=list)
    step1b_illegal: list[_CandidateIllegalB] = field(default_factory=list)
    step1b_scored: list[_CandidateScored] = field(default_factory=list)
    connection_loser_oids: set[DangleOid] = field(default_factory=set)
    kruskal_rejected_oids: set[DangleOid] = field(default_factory=set)
    kruskal_crossing_rejected_oids: set[DangleOid] = field(default_factory=set)
    accepted_dangle_oids: set[DangleOid] = field(default_factory=set)
    gap_source_by_dangle: dict[DangleOid, GapSource] = field(default_factory=dict)
    dangle_norm_z_by_dangle: _NormZByDangle = field(default_factory=dict)
    connection_norm_z_by_dangle: _NormZByDangle = field(default_factory=dict)
    global_norm_z_by_dangle: _NormZByDangle = field(default_factory=dict)


# Per-parent plan: each parent line carries a list of planned edits, applied in
# order by _apply_plan.
PlanByParent: TypeAlias = dict[ParentId, list[PlanEntry]]


@dataclass(frozen=True)
class BuildPlanResult:
    """Bundle of everything _build_plan hands back to run()."""

    plan_by_parent: PlanByParent
    resnap_captures: list["_ResnappedCapture"]
    diagnostics: list["CandidateDiagnostic"]
    accepted_connector_raw: list[AcceptedConnectorRaw]
    kruskal_rank_by_dangle_oid: dict[DangleOid, int]

    @classmethod
    def empty(cls, diagnostics: list["CandidateDiagnostic"]) -> "BuildPlanResult":
        return cls(
            plan_by_parent={},
            resnap_captures=[],
            diagnostics=diagnostics,
            accepted_connector_raw=[],
            kruskal_rank_by_dangle_oid={},
        )


class FillLineGaps:
    """Fill small end-of-line gaps by snapping or extending dangle endpoints.

    A dangle is an open polyline end.  For each dangle, this class picks the
    best legal target within ``gap_tolerance_meters`` and edits the source
    line so the gap closes.  Targets come from ``connect_to_features``, from
    the input itself (``fill_gaps_on_self``), or both; at least one mode must
    be enabled.

    How:
        ``run`` orchestrates the full workflow.  ``_build_plan`` drives the
        four-scope decision pipeline and ``_apply_plan`` commits the edits.
        The scopes are, in order:

          - CANDIDATE:  angle and polyline caches, legality gates (distance,
            network membership, illegal-target, barrier/crossing), and one
            angle-aware proposal per dangle.
          - NETWORK:    one winner per undirected A<->B connection, with Z
            re-normalized inside each connection group.
          - KRUSKAL:    cycle prevention and accepted-connector crossing
            checks across all connection winners.
          - DEFERRED:   post-apply resnap pass for connections whose target
            endpoint moved during ``_apply_plan``, with an optional crossing
            recheck.

    Why:
        Scope-based staging attributes every rejected candidate to the
        earliest scope that can prove it.  The optional diagnostic feature
        class ``candidate_connections_output`` relies on that separation so
        each row carries the scope that decided its fate.

    Outputs:
        output_lines:
            Required.  The edited polyline feature class.
        line_changes_output:
            Optional per-edit metadata feature class.
        candidate_connections_output:
            Optional diagnostic feature class.  One row per evaluated
            ``(dangle, candidate)`` pair.
    """

    ORIGINAL_ID = "line_gap_original_id"

    # Output flag: 1 on rows materialised by EditMethod.NEW_LINE, 0 otherwise.
    FIELD_GAP_GENERATED = "fill_line_gap_generated"

    # Sentinel ORIGINAL_ID for generated rows. Real ORIGINAL_IDs come from
    # OBJECTID (>= 1), so -1 cannot collide with any plan key — keeps the
    # second _apply_plan (resnap) pass from walking into generated rows.
    GENERATED_ORIGINAL_ID_SENTINEL = -1

    # Change output fields
    FIELD_GAP_DIST_M = "gap_dist_m"
    FIELD_GAP_SOURCE = "gap_source"

    # Near table fields
    F_IN_FID = "IN_FID"
    F_NEAR_FID = "NEAR_FID"
    F_NEAR_FC = "NEAR_FC"
    F_NEAR_DIST = "NEAR_DIST"
    F_NEAR_X = "NEAR_X"
    F_NEAR_Y = "NEAR_Y"

    def __init__(self, line_gap_config: logic_config.FillLineGapsConfig):
        """Transcribe the config bundle into flat instance attributes.

        The ``FillLineGapsConfig`` groups settings by concern (``advanced_config``,
        ``output_config``, ``angle_config``, ``z_config``, ``crossing_config``,
        ``connectivity_config``); ``__init__`` flattens those groups onto
        ``self`` so hot-path methods can read one attribute instead of walking
        the config tree.  It also resolves work-file names via
        ``WorkFileManager`` and preloads the local angle cache.

        Raises:
            ValueError: if ``connect_to_features`` is ``None`` while
                ``fill_gaps_on_self`` is ``False`` (no legal target source),
                or if ``lines_are_directed`` is enabled with an angle weight
                of zero (directed scoring would have no effect).
        """
        self.input_lines = line_gap_config.input_lines
        self.output_lines = line_gap_config.output_lines
        self.connect_to_features = line_gap_config.connect_to_features
        self.gap_tolerance_meters = int(line_gap_config.gap_tolerance_meters)

        adv = line_gap_config.advanced_config
        out = line_gap_config.output_config
        ang = line_gap_config.angle_config
        z = line_gap_config.z_config
        cross = line_gap_config.crossing_config
        conn = line_gap_config.connectivity_config

        self.fill_gaps_on_self = bool(line_gap_config.fill_gaps_on_self)
        self.best_fit_weights = line_gap_config.best_fit_weights
        self.segmentation = line_gap_config.segmentation

        self.line_changes_output = out.line_changes_output
        self.write_output_metadata = bool(out.write_output_metadata)
        self.candidate_connections_output = out.candidate_connections_output
        self.diagnostic_detail = logic_config.DiagnosticDetail(out.diagnostic_detail)
        self._collect_diags = (
            self.candidate_connections_output is not None
            and self.diagnostic_detail is not logic_config.DiagnosticDetail.OFF
        )

        self.increased_tolerance_edge_case_distance_meters = int(
            adv.increased_tolerance_edge_case_distance_meters
        )
        self.require_mutual_dangle_preference_for_bonus = bool(
            adv.require_mutual_dangle_preference_for_bonus
        )
        self.edit_method = logic_config.EditMethod(adv.edit_method)
        self.candidate_closest_count = int(adv.candidate_closest_count)
        self.connectivity_closest_count = int(adv.connectivity_closest_count)

        self.connectivity_scope = logic_config.ConnectivityScope(
            conn.connectivity_scope
        )
        self.connectivity_tolerance_meters = float(conn.connectivity_tolerance_meters)
        self.line_connectivity_mode = logic_config.LineConnectivityMode(
            conn.line_connectivity_mode
        )

        if self.connect_to_features is None and self.fill_gaps_on_self is False:
            raise ValueError(
                "Invalid config: fill_gaps_on_self cannot be False when connect_to_features is None."
            )

        self.lines_are_directed: bool = bool(ang.lines_are_directed)
        self.connector_angle_diff_required_above_meters: Optional[float] = (
            None
            if ang.connector_angle_diff_required_above_meters is None
            else float(ang.connector_angle_diff_required_above_meters)
        )

        self.angle_block_threshold_degrees = (
            None
            if ang.angle_block_threshold_degrees is None
            else float(ang.angle_block_threshold_degrees)
        )
        self.angle_extra_dangle_threshold_degrees = (
            None
            if ang.angle_extra_dangle_threshold_degrees is None
            else float(ang.angle_extra_dangle_threshold_degrees)
        )

        if self.lines_are_directed and self.best_fit_weights.angle == 0.0:
            raise ValueError(
                "lines_are_directed=True requires best_fit_weights.angle > 0.0 — "
                "directional scoring has no effect when angle weight is zero."
            )

        self.angle_local_half_window_m = float(ang.angle_local_half_window_m)

        self._connect_to_features_angle_mode_raw = (
            ang.connect_to_features_angle_mode or {}
        )

        self._angle_mode_by_external_ds_key: dict[str, logic_config.AngleTargetMode] = (
            {}
        )

        self.raster_paths: tuple[str, ...] = (
            tuple(z.raster_paths) if z.raster_paths else ()
        )
        self.z_drop_threshold: Optional[float] = (
            None if z.z_drop_threshold is None else float(z.z_drop_threshold)
        )
        self._raster_handles: list[geometry_tools.RasterHandle] = []

        self.reject_crossing_connectors: bool = bool(cross.reject_crossing_connectors)
        self.crossing_check_spatial_reference = cross.crossing_check_spatial_reference
        self.barrier_layers: list[str] | None = cross.barrier_layers or None

        # Local angle cache (dataset_key, oid, rx, ry) -> Optional[float]
        self._local_angle_cache: dict[tuple[str, int, int, int], Optional[float]] = {}
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

        # Segmented twins of lines_copy / target_self / each line-like external
        # target layer. Built by _setup_segmentation when self.segmentation is
        # set; used by the candidate near table only. Other phases continue to
        # read the unsegmented originals. Lookups map a segmented FC's OID
        # space back to parent ORIGINAL_ID.
        self.lines_copy_segmented = "lines_copy_segmented"
        self.target_self_segmented = "target_self_segmented"
        self.external_target_layers_segmented: list[str] = []
        self._segmented_oid_to_parent_id: dict[str, dict[int, ParentId]] = {}

        self.external_target_layers: list[str] = []
        # FCs to use as against_fcs in the connector-crossing pre-filter.
        # Polyline connect_to_features are reused as-is; polygon
        # connect_to_features contribute their boundary as a polyline FC
        # built once via PolygonToLine in
        # _build_external_target_layers_once.  Populated only when
        # reject_crossing_connectors is True; entries are pure paths so
        # the existing line-vs-line crossing path applies uniformly.
        self.external_target_crossing_layers: list[str] = []

        self.work_file_list = [
            self.lines_copy,
            self.dangles,
            self.filtered_dangles,
            self.target_self,
            self.near_table,
            self.conn_endpoints,
            self.conn_table,
        ]

        if self.segmentation is not None:
            self.work_file_list.extend(
                [self.lines_copy_segmented, self.target_self_segmented]
            )

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

    def _connectivity_tolerance_linear_unit(self) -> str:
        meters = max(0.0, float(self.connectivity_tolerance_meters))
        return f"{meters} Meters"

    def _dataset_key(self, value: str) -> str:
        text = str(value).replace("\\", "/")
        return text.split("/")[-1]

    def _line_dataset_keys(self) -> set[str]:
        keys = {
            self._dataset_key(self.lines_copy),
            self._dataset_key(self.target_self),
        }
        if self.segmentation is not None:
            keys.add(self._dataset_key(self.lines_copy_segmented))
            keys.add(self._dataset_key(self.target_self_segmented))
        return keys

    def _normalize_target_key(
        self, *, near_fc_key: str, lines_key: str, line_keys: set[str]
    ) -> str:
        if near_fc_key in line_keys:
            return lines_key
        return near_fc_key

    def _oid_to_original_id_lookup(self, fc: str) -> dict[int, ParentId]:
        # key is raw arcpy OID, value is ORIGINAL_ID (ParentId) space
        oid_field = arcpy.Describe(fc).OIDFieldName
        out: dict[int, ParentId] = {}
        with arcpy.da.SearchCursor(fc, [oid_field, self.ORIGINAL_ID]) as cur:
            for oid, original_id in cur:
                out[int(oid)] = int(original_id)
        return out

    def _resolve_edit_op(self, *, gap_source: GapSource) -> EditOp:
        """Map ``edit_method`` + ``gap_source`` onto the geometry edit to perform.

        ``FORCED_SNAP``, ``FORCED_EXTEND`` and ``NEW_LINE`` ignore
        ``gap_source``.  ``AUTO`` snaps dangle-to-dangle pairs
        (``GapSource.PAIR_DANGLE``) and extends everything else.
        """
        method = self.edit_method

        if method == logic_config.EditMethod.FORCED_SNAP:
            return EditOp.SNAP
        if method == logic_config.EditMethod.FORCED_EXTEND:
            return EditOp.EXTEND
        if method == logic_config.EditMethod.NEW_LINE:
            return EditOp.NEW_LINE

        # AUTO
        if gap_source is GapSource.PAIR_DANGLE:
            return EditOp.SNAP
        return EditOp.EXTEND

    def _same_network(
        self,
        *,
        a_parent: int,
        b_parent: int,
        topology: TopologyModel,
    ) -> bool:
        """Return ``True`` if two parent lines share a network under the topology scope.

        - NONE: always ``False``.
        - DIRECT_CONNECTION: ``True`` iff ``b`` is in ``a``'s direct
          neighbor set.
        - Component scopes: ``True`` iff both parents share a
          connectivity id.
        """
        scope = topology.scope

        if scope == logic_config.ConnectivityScope.NONE:
            return False

        if scope == logic_config.ConnectivityScope.DIRECT_CONNECTION:
            direct = topology.direct_neighbors_by_parent or {}
            return int(b_parent) in direct.get(int(a_parent), set())

        # Component modes:
        cid = topology.connectivity_id_by_parent
        if not cid:
            return False
        a = cid.get(int(a_parent))
        b = cid.get(int(b_parent))
        return a is not None and b is not None and int(a) == int(b)

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

    def _candidate_sort_key(self, cand: NearCandidate) -> tuple:
        # Deterministic ordering for candidate rows within a dangle
        return (
            cand.near_dist,
            cand.near_fc_key,
            cand.near_fid,
            cand.near_x,
            cand.near_y,
        )

    def _unordered_pair_key(
        self, a: EntityKey, b: EntityKey
    ) -> tuple[EntityKey, EntityKey]:
        # Deterministic unordered key using tuple ordering
        return (a, b) if a <= b else (b, a)

    def _node_for_parent(self, *, parent_id: int, topology: TopologyModel) -> EntityKey:
        """
        Network identity for a parent line.
        - Component scopes: prefer ("component", connectivity_id)
        - Otherwise: ("parent", parent_id)
        """
        scope = topology.scope
        if scope in (
            logic_config.ConnectivityScope.INPUT_LINES,
            logic_config.ConnectivityScope.ONE_DEGREE,
            logic_config.ConnectivityScope.TRANSITIVE,
        ):
            cid = (topology.connectivity_id_by_parent or {}).get(int(parent_id))
            if cid is not None:
                return ("component", int(cid))
        return ("parent", int(parent_id))

    def _node_for_optional_candidate(
        self, *, dataset_key: str, near_fid: int
    ) -> EntityKey:
        """
        Optional identity in candidate space.
        Isolated behind a function so it can be upgraded later if SOURCE_OID becomes available.
        """
        return ("optional_candidate", str(dataset_key), int(near_fid))

    def _best_legal_line_target_parent(
        self,
        *,
        legal_rows: list[NearCandidate],
        lines_fc_key: str,
    ) -> Optional[int]:
        """
        Return the parent line id of the closest legal line target for this dangle.

        `legal_rows` must already be sorted by raw candidate order.
        """
        for cand in legal_rows:
            if cand.near_fc_key == lines_fc_key:
                return cand.near_fid
        return None

    def _mutual_dangle_preference(
        self,
        *,
        dangle_oid: DangleOid,
        other_dangle_oid: DangleOid,
        dangle_parent: dict[DangleOid, ParentId],
        best_line_parent_by_dangle: dict[DangleOid, ParentId],
    ) -> bool:
        """
        True when source and target dangles mutually prefer each other's parent line:
        - source's best line target is the other dangle's parent
        - other dangle's best line target is the source's parent
        """
        src_parent = dangle_parent.get(int(dangle_oid))
        other_parent = dangle_parent.get(int(other_dangle_oid))
        if src_parent is None or other_parent is None:
            return False
        src_best = best_line_parent_by_dangle.get(int(dangle_oid))
        other_best = best_line_parent_by_dangle.get(int(other_dangle_oid))
        if src_best is None or other_best is None:
            return False
        return int(src_best) == int(other_parent) and int(other_best) == int(src_parent)

    def _edge_case_bonus_applies(
        self,
        *,
        dangle_oid: DangleOid,
        cand: NearCandidate,
        dangles_fc_key: DatasetKey,
        dangle_parent: dict[DangleOid, ParentId],
        best_line_parent_by_dangle: dict[DangleOid, ParentId],
    ) -> bool:
        """
        Determines whether the edge-case distance bonus applies for a candidate.

        The bonus is only possible when the TARGET is a true dangle — i.e. an unconnected
        endpoint of an input line. For all other target types (self-lines, external features)
        the bonus is never applied; those targets benefit only from the expanded search
        tolerance, not from the effective-distance reduction.

        For dangle targets the condition is mutual preference: both dangles must prefer
        each other's parent line (see _mutual_dangle_preference).

        Requires increased_tolerance_edge_case_distance_meters > 0.
        """
        extra = max(0, int(self.increased_tolerance_edge_case_distance_meters))
        if extra <= 0:
            return False

        if cand.near_fc_key != dangles_fc_key:
            return False

        if not self.require_mutual_dangle_preference_for_bonus:
            return True

        return self._mutual_dangle_preference(
            dangle_oid=dangle_oid,
            other_dangle_oid=cand.near_fid,
            dangle_parent=dangle_parent,
            best_line_parent_by_dangle=best_line_parent_by_dangle,
        )

    def _candidate_score_details(
        self,
        *,
        dangle_oid: DangleOid,
        parent_id: ParentId,
        cand: NearCandidate,
        dangles_fc_key: DatasetKey,
        dangle_parent: dict[DangleOid, ParentId],
        best_line_parent_by_dangle: dict[DangleOid, ParentId],
        bonus_allowed: bool = True,
    ) -> tuple[float, float, bool]:
        raw_distance = cand.near_dist

        bonus_applied = False
        if bonus_allowed:
            bonus_applied = self._edge_case_bonus_applies(
                dangle_oid=int(dangle_oid),
                cand=cand,
                dangles_fc_key=dangles_fc_key,
                dangle_parent=dangle_parent,
                best_line_parent_by_dangle=best_line_parent_by_dangle,
            )

        if bonus_applied:
            effective_distance = raw_distance - float(
                max(0, int(self.increased_tolerance_edge_case_distance_meters))
            )
        else:
            effective_distance = raw_distance

        return raw_distance, effective_distance, bool(bonus_applied)

    @staticmethod
    def _normalize_z_within(
        end_z_values: "list[Optional[float]]",
        target_end_z: Optional[float],
    ) -> Optional[float]:
        """
        Normalize target_end_z within the range of end_z_values.
        Returns None when fewer than 2 valid values exist, range is flat, or target is None.
        """
        if target_end_z is None:
            return None
        valid = [z for z in end_z_values if z is not None]
        if len(valid) < 2:
            return None
        lo = min(valid)
        hi = max(valid)
        if hi == lo:
            return None
        return (target_end_z - lo) / (hi - lo)

    def _compute_best_fit_score(
        self,
        *,
        norm_dist: float,
        assess: "AngleAssessment",
        norm_z: Optional[float] = None,
    ) -> float:
        """
        Normalized weighted composite best-fit score. Lower is better.

        Unavailable dimensions are excluded from the composite and the score
        is normalized by the sum of available weights only.  This ensures a
        missing dimension is neutral rather than treated as a perfect fit.

        norm_z: Z contribution normalized to [0, 1] within the current dangle's
            candidate set, where 0 = lowest end elevation (most downstream, best)
            and 1 = highest (most upstream, worst).  None excludes the Z weight.
        """
        w_d = float(self.best_fit_weights.distance)
        w_a = float(self.best_fit_weights.angle)
        w_z = float(self.best_fit_weights.z)

        total_w = w_d
        score = w_d * float(norm_dist)

        if assess.angle_metric_deg is not None:
            norm_a = float(assess.angle_metric_deg) / float(assess.angle_max_deg)
            score += w_a * norm_a
            total_w += w_a
        # angle unavailable: exclude w_a from total so the score is not biased

        if norm_z is not None and w_z > 0.0:
            score += w_z * float(norm_z)
            total_w += w_z
        # z unavailable: exclude w_z from total so the score is not biased

        return float(score) / float(total_w) if total_w > 0.0 else 0.0

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

    def _ensure_gap_generated_field(self) -> None:
        """Idempotently provision ``FIELD_GAP_GENERATED`` on ``lines_copy``.

        If the field is missing, add it as SHORT and bulk-set every
        existing row to 0.  If the field already exists (e.g. because the
        input is the output of a prior run), values are preserved
        verbatim — generated rows from the prior run keep their 1.
        """
        existing = {f.name for f in arcpy.ListFields(self.lines_copy)}
        if self.FIELD_GAP_GENERATED in existing:
            return

        arcpy.management.AddField(
            self.lines_copy, self.FIELD_GAP_GENERATED, "SHORT"
        )
        with arcpy.da.UpdateCursor(
            self.lines_copy, [self.FIELD_GAP_GENERATED]
        ) as cur:
            for _ in cur:
                cur.updateRow((0,))

    def _create_dangles(self) -> None:
        arcpy.management.FeatureVerticesToPoints(
            self.lines_copy, self.dangles, "DANGLE"
        )

    def _build_polyline_by_parent_id(self) -> dict[ParentId, Any]:
        out: dict[ParentId, Any] = {}
        with arcpy.da.SearchCursor(
            self.lines_copy, [self.ORIGINAL_ID, "SHAPE@"]
        ) as cur:
            for pid, shape in cur:
                if shape is None:
                    continue
                out[int(pid)] = shape
        return out

    def _build_polyline_by_oid(self, fc: str) -> dict[int, Any]:
        oid_field = arcpy.Describe(fc).OIDFieldName
        out: dict[int, Any] = {}
        with arcpy.da.SearchCursor(fc, [oid_field, "SHAPE@"]) as cur:
            for oid, shape in cur:
                if shape is None:
                    continue
                out[int(oid)] = shape
        return out

    def _is_polyline_fc(self, fc: str) -> bool:
        try:
            desc = arcpy.Describe(fc)
            # ArcGIS commonly uses "Polyline" here
            return str(getattr(desc, "shapeType", "")).lower() == "polyline"
        except Exception:
            return False

    def _is_polygon_fc(self, fc: str) -> bool:
        try:
            desc = arcpy.Describe(fc)
            return str(getattr(desc, "shapeType", "")).lower() == "polygon"
        except Exception:
            return False

    def _build_angle_caches(
        self,
        *,
        target_layers: list[str],
        lines_key: DatasetKey,
    ) -> _AngleCaches:
        """Build the polyline caches and line-like flags used by angle scoring.

        Populates one cache per parent id for the source lines and one
        OID-keyed cache per external dataset.  Line-like status is
        resolved by the configured ``AngleTargetMode`` (falling back to
        ``Describe.shapeType``).  When ``fill_gaps_on_self`` is enabled,
        the self-lines dataset key is added to the line-like set so
        self-targets participate in angle-aware scoring.
        """
        polyline_by_parent = self._build_polyline_by_parent_id()

        polyline_by_external: dict[DatasetKey, dict[int, Any]] = {}
        polyline_by_segment: dict[DatasetKey, dict[int, Any]] = {}
        is_external_line_like: dict[DatasetKey, bool] = {}

        line_keys = self._line_dataset_keys()

        for lyr in target_layers:
            ds_key = self._dataset_key(lyr)

            # Skip any internal line datasets
            if ds_key in line_keys:
                continue

            mode = self._angle_mode_by_external_ds_key.get(
                ds_key, logic_config.AngleTargetMode.AUTO
            )
            if mode == logic_config.AngleTargetMode.FORCE_NON_LINE:
                is_external_line_like[ds_key] = False
                continue

            if self._is_polyline_fc(lyr):
                is_external_line_like[ds_key] = True
                polyline_by_external[ds_key] = self._build_polyline_by_oid(lyr)
            else:
                is_external_line_like[ds_key] = False

        # Per-segment polyline cache (consumed by _resolve_target_angle_and_snap
        # when segmentation is enabled). Built only for the candidate-side
        # segmented twins — the tolerance filter that scopes target_self also
        # scopes target_self_segmented, so the cache size tracks candidate
        # volume, not total segment count.
        if self.segmentation is not None:
            if self.fill_gaps_on_self:
                seg_self_key = self._dataset_key(self.target_self_segmented)
                polyline_by_segment[seg_self_key] = self._build_polyline_by_oid(
                    self.target_self_segmented
                )
            # external_target_layers and external_target_layers_segmented are
            # appended in lock-step in _setup_segmentation (one entry per
            # source layer), so zip pairs each segmented twin with its source.
            for ext_src, ext_seg in zip(
                self.external_target_layers, self.external_target_layers_segmented
            ):
                if not self._is_polyline_fc(ext_seg):
                    continue
                src_mode = self._angle_mode_by_external_ds_key.get(
                    self._dataset_key(ext_src), logic_config.AngleTargetMode.AUTO
                )
                if src_mode == logic_config.AngleTargetMode.FORCE_NON_LINE:
                    continue
                polyline_by_segment[self._dataset_key(ext_seg)] = (
                    self._build_polyline_by_oid(ext_seg)
                )

        line_like_external_ds_keys: set[DatasetKey] = {
            ds_key for ds_key, is_line in is_external_line_like.items() if is_line
        }
        # Self-lines are included only when fill_gaps_on_self is active (otherwise
        # no candidates with lines_key appear in the near table anyway).
        line_like_ds_keys: set[DatasetKey] = line_like_external_ds_keys.copy()
        if self.fill_gaps_on_self:
            line_like_ds_keys.add(lines_key)

        return _AngleCaches(
            polyline_by_parent=polyline_by_parent,
            polyline_by_external=polyline_by_external,
            polyline_by_segment=polyline_by_segment,
            is_external_line_like=is_external_line_like,
            line_like_external_ds_keys=line_like_external_ds_keys,
            line_like_ds_keys=line_like_ds_keys,
        )

    def _orientation(self, angle_deg: float) -> float:
        return float(angle_deg) % 180.0

    def _orientation_diff(self, a_deg: float, b_deg: float) -> float:
        a = self._orientation(float(a_deg))
        b = self._orientation(float(b_deg))
        raw = abs(a - b)
        return min(raw, 180.0 - raw)  # 0..90

    def _directional_diff(self, a_deg: float, b_deg: float) -> float:
        """Signed-aware circular difference between two direction angles. Result in [0, 180]."""
        diff = abs(float(a_deg) - float(b_deg)) % 360.0
        return min(diff, 360.0 - diff)  # 0..180

    def _connector_angle_deg(
        self, *, from_x: float, from_y: float, to_x: float, to_y: float
    ) -> Optional[float]:
        dx = float(to_x) - float(from_x)
        dy = float(to_y) - float(from_y)
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return None
        ang = math.degrees(math.atan2(dy, dx))
        if ang < 0.0:
            ang += 360.0
        return float(ang)

    def _build_raster_handles(self) -> None:
        """
        Load each raster in self.raster_paths into a RasterHandle windowed to
        the extent of the input lines.  Called once at the start of run().
        Populates self._raster_handles; no-ops when raster_paths is empty.
        """
        if not self.raster_paths:
            return

        try:
            ext = arcpy.Describe(self.input_lines).extent
            clip_kwargs = dict(
                clip_xmin=ext.XMin,
                clip_ymin=ext.YMin,
                clip_xmax=ext.XMax,
                clip_ymax=ext.YMax,
            )
        except Exception:
            clip_kwargs = {}

        handles = []
        for path in self.raster_paths:
            try:
                handles.append(
                    geometry_tools.build_raster_handle(raster_path=path, **clip_kwargs)
                )
            except Exception as exc:
                arcpy.AddWarning(
                    f"Could not load raster {path}: {exc}. "
                    "Z values from this raster will be None."
                )

        self._raster_handles = handles

    # ----------------------------
    # Source direction orientation
    # ----------------------------

    def _local_angle_cache_key(
        self, *, dataset_key: str, oid: int, x: float, y: float
    ) -> tuple[str, int, int, int]:
        # integer mill-units in dataset units (deterministic hashing)
        scale = 1000.0
        return (
            str(dataset_key),
            int(oid),
            int(round(float(x) * scale)),
            int(round(float(y) * scale)),
        )

    def _local_line_angle_cached(
        self,
        *,
        dataset_key: str,
        oid: int,
        polyline,
        x: float,
        y: float,
    ) -> Optional[float]:
        key = self._local_angle_cache_key(dataset_key=dataset_key, oid=oid, x=x, y=y)
        if key in self._local_angle_cache:
            return self._local_angle_cache[key]

        angle = geometry_tools.local_line_angle_at_xy(
            polyline=polyline,
            x=float(x),
            y=float(y),
            desired_half_window_m=float(self.angle_local_half_window_m),
        )
        self._local_angle_cache[key] = angle
        return angle

    def _xy_is_at_line_start(self, polyline, x: float, y: float) -> bool:
        """
        Returns True if (x, y) is geometrically closer to the start of polyline than to
        its end, False otherwise (including on any geometry failure).

        Uses squared-distance comparison between (x, y) and polyline.firstPoint /
        polyline.lastPoint — no ArcPy queryPointAndDistance call, so this is immune
        to the map-unit vs percentage ambiguity in that API.

        Used for angle normalisation: flip the forward tangent to the exit direction
        when the dangle sits at the start of its parent line, leave it when at the end.
        """
        if polyline is None:
            return False
        try:
            first = polyline.firstPoint
            last = polyline.lastPoint
            if first is None or last is None:
                return False
            d_start = (x - first.X) ** 2 + (y - first.Y) ** 2
            d_end = (x - last.X) ** 2 + (y - last.Y) ** 2
            return d_start < d_end
        except Exception:
            return False

    # ----------------------------
    # Target staging
    # ----------------------------

    def _build_external_target_layers_once(self) -> None:
        """Pre-filter each ``connect_to_features`` layer to its tolerance window.

        Runs ``SELECT_LOCATION`` with ``WITHIN_A_DISTANCE`` at the
        configured gap tolerance so downstream near-table queries and
        angle caches only scan features that can possibly matter.  Each
        output layer's angle mode is resolved from
        ``connect_to_features_angle_mode`` (keyed by source path, source
        dataset key, or output dataset key) and recorded in
        ``_angle_mode_by_external_ds_key``.  Idempotent — skips work on
        re-entry.
        """
        if self.external_target_layers:
            return
        if self.connect_to_features is None:
            return

        for index, feature_path in enumerate(self.connect_to_features):
            output_name = self.wfm.build_file_path(file_name=f"target_feature_{index}")

            # Segmentation needs to stamp ORIGINAL_ID on the output FC so the
            # segmented twin can map back to a stable parent identifier;
            # that requires a permanent FC rather than a memory-backed layer
            # view (which would point at the user's source data).
            use_memory_layer = (
                self.write_work_files_to_memory and self.segmentation is None
            )
            if use_memory_layer:
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

            if self.segmentation is not None:
                # Stamp ORIGINAL_ID = OID on the staged target FC so the
                # segmented twin's segments can carry their parent's OID
                # via segment_line's field-preservation, giving a clean
                # segmented_oid -> parent_id mapping in the candidate near
                # table reader.
                existing = {f.name for f in arcpy.ListFields(output_name)}
                if self.ORIGINAL_ID not in existing:
                    arcpy.management.AddField(output_name, self.ORIGINAL_ID, "LONG")
                oid_field = arcpy.Describe(output_name).OIDFieldName
                arcpy.management.CalculateField(
                    output_name,
                    self.ORIGINAL_ID,
                    expression=f"!{oid_field}!",
                    expression_type="PYTHON3",
                )

            self.external_target_layers.append(output_name)

            # Companion entry for the connector-crossing pre-filter.
            # Polyline sources reuse output_name; polygon sources are
            # converted to their boundary polyline once via PolygonToLine
            # so the line-vs-line crossing path handles them uniformly.
            # Other shape types (points) are skipped — a connector cannot
            # cross a point.
            if self.reject_crossing_connectors:
                if self._is_polyline_fc(output_name):
                    self.external_target_crossing_layers.append(output_name)
                elif self._is_polygon_fc(output_name):
                    outline_name = self.wfm.build_file_path(
                        file_name=f"target_feature_{index}_polygon_outline"
                    )
                    arcpy.management.PolygonToLine(
                        in_features=output_name,
                        out_feature_class=outline_name,
                    )
                    self.external_target_crossing_layers.append(outline_name)

            out_key = self._dataset_key(output_name)

            raw_map = self._connect_to_features_angle_mode_raw
            raw_mode = (
                raw_map.get(feature_path)
                or raw_map.get(self._dataset_key(feature_path))
                or raw_map.get(out_key)
            )

            if raw_mode is None:
                mode = logic_config.AngleTargetMode.AUTO
            else:
                mode = logic_config.AngleTargetMode(raw_mode)

            self._angle_mode_by_external_ds_key[str(out_key)] = mode

    def _setup_segmentation(self) -> None:
        """Build internal segmented twins of ``lines_copy`` and line-like
        external target layers. Segmented twins are read only by the
        candidate near table; other phases continue to use the unsegmented
        originals.

        ``ORIGINAL_ID`` is stamped on ``lines_copy`` by
        ``_add_original_id_field`` and on each external target layer in
        ``_build_external_target_layers_once`` (when segmentation is
        enabled); ``segment_line`` preserves all non-required fields, so
        each segment carries its parent's ORIGINAL_ID and the OID lookup
        reduces to the existing ``_oid_to_original_id_lookup`` helper.

        Polygon ``connect_to_features`` are not supported with segmentation
        enabled — callers should convert polygons to polylines before
        passing them in. Geometry types other than polygon and polyline
        (e.g. points) pass through unsegmented; the candidate near table
        reads them directly.

        No-op when ``self.segmentation`` is None.
        """
        if self.segmentation is None:
            return

        seg_cfg = self.segmentation
        even = seg_cfg.mode is logic_config.SegmentationMode.EVEN

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _setup_segmentation lines_copy START")  # [DBG_LINEGAP]
        segment_line(
            input_fc=self.lines_copy,
            output_fc=self.lines_copy_segmented,
            segment_interval=float(seg_cfg.interval_meters),
            even_segments=even,
            tail_tolerance=float(seg_cfg.tail_tolerance_meters),
        )
        self._segmented_oid_to_parent_id[
            self._dataset_key(self.lines_copy_segmented)
        ] = self._oid_to_original_id_lookup(self.lines_copy_segmented)
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _setup_segmentation lines_copy END (rows={int(arcpy.management.GetCount(self.lines_copy_segmented)[0])})")  # [DBG_LINEGAP]

        for index, ext_path in enumerate(self.external_target_layers):
            if self._is_polygon_fc(ext_path):
                raise ValueError(
                    f"connect_to_features[{index}] is a polygon feature class. "
                    f"Segmentation only supports polyline connect_to_features. "
                    f"Convert polygons to polylines (e.g. via PolygonToLine) "
                    f"before passing them to FillLineGaps when segmentation "
                    f"is enabled."
                )
            if not self._is_polyline_fc(ext_path):
                # Non-line, non-polygon (e.g. point) — segmentation does
                # not apply. Pass the source path through so the segmented
                # list aligns with external_target_layers.
                self.external_target_layers_segmented.append(ext_path)
                continue

            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _setup_segmentation external[{index}] START")  # [DBG_LINEGAP]
            seg_path = self.wfm.build_file_path(
                file_name=f"target_feature_{index}_segmented"
            )
            segment_line(
                input_fc=ext_path,
                output_fc=seg_path,
                segment_interval=float(seg_cfg.interval_meters),
                even_segments=even,
                tail_tolerance=float(seg_cfg.tail_tolerance_meters),
            )
            self.external_target_layers_segmented.append(seg_path)
            self._segmented_oid_to_parent_id[
                self._dataset_key(seg_path)
            ] = self._oid_to_original_id_lookup(seg_path)
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _setup_segmentation external[{index}] END (rows={int(arcpy.management.GetCount(seg_path)[0])})")  # [DBG_LINEGAP]

    def _select_targets_within_tolerance_of_dangles(self) -> list[str]:
        """Return the global target layer list for connectivity-side queries.

        Includes the tolerance-filtered self-lines layer (``target_self``)
        when ``fill_gaps_on_self`` is enabled, followed by the external
        target layers built in ``_build_external_target_layers_once``. The
        candidate-side target list is produced separately by
        ``_candidate_target_layers`` (which routes to segmented twins when
        ``self.segmentation`` is set).

        When segmentation is enabled and ``fill_gaps_on_self`` is True, also
        builds ``target_self_segmented`` (a tolerance-filtered slice of
        ``lines_copy_segmented``) and registers its segmented OID lookup so
        the candidate near table reader can map back to parent ids.
        """
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

            if self.segmentation is not None:
                # target_self_segmented is built from lines_copy_segmented at
                # the same tolerance filter — candidates reach segments by
                # their segmented OID, the OID lookup maps back to parent_id.
                print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} target_self_segmented build START")  # [DBG_LINEGAP]
                if self.write_work_files_to_memory:
                    custom_arcpy.select_location_and_make_feature_layer(
                        input_layer=self.lines_copy_segmented,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                        select_features=self.dangles,
                        output_name=self.target_self_segmented,
                        search_distance=self._tolerance_linear_unit(),
                    )
                else:
                    custom_arcpy.select_location_and_make_permanent_feature(
                        input_layer=self.lines_copy_segmented,
                        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
                        select_features=self.dangles,
                        output_name=self.target_self_segmented,
                        search_distance=self._tolerance_linear_unit(),
                    )
                self._segmented_oid_to_parent_id[
                    self._dataset_key(self.target_self_segmented)
                ] = self._oid_to_original_id_lookup(self.target_self_segmented)
                print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} target_self_segmented build END (rows={int(arcpy.management.GetCount(self.target_self_segmented)[0])})")  # [DBG_LINEGAP]

        targets.extend(self.external_target_layers)
        return targets

    def _candidate_target_layers(self, global_target_layers: list[str]) -> list[str]:
        """Translate the global target list to its segmented twins for the
        candidate near table.

        Returns ``global_target_layers`` unchanged when
        ``self.segmentation`` is None. Otherwise returns
        ``[target_self_segmented]`` (when ``fill_gaps_on_self``) followed
        by ``external_target_layers_segmented`` — the same shape as
        ``_select_targets_within_tolerance_of_dangles``, but every line-like
        entry points at its segmented twin.
        """
        if self.segmentation is None:
            return global_target_layers
        out: list[str] = []
        if self.fill_gaps_on_self:
            out.append(self.target_self_segmented)
        out.extend(self.external_target_layers_segmented)
        return out

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

    def _build_dangle_parent_lookup(self, dangles_fc: str) -> dict[DangleOid, ParentId]:
        oid_field = arcpy.Describe(dangles_fc).OIDFieldName
        out: dict[DangleOid, ParentId] = {}
        with arcpy.da.SearchCursor(dangles_fc, [oid_field, self.ORIGINAL_ID]) as cur:
            for dangle_oid, parent_id in cur:
                out[int(dangle_oid)] = int(parent_id)
        return out

    def _build_dangle_xy_lookup(
        self, dangles_fc: str
    ) -> dict[DangleOid, tuple[float, float]]:
        oid_field = arcpy.Describe(dangles_fc).OIDFieldName
        out: dict[DangleOid, tuple[float, float]] = {}
        with arcpy.da.SearchCursor(dangles_fc, [oid_field, "SHAPE@XY"]) as cur:
            for dangle_oid, (x, y) in cur:
                out[int(dangle_oid)] = (float(x), float(y))
        return out

    def _directed_start_dangle_oids(
        self,
        *,
        dangle_xy: dict[DangleOid, tuple[float, float]],
        dangle_parent: dict[DangleOid, ParentId],
        polyline_by_parent: dict[ParentId, Any],
    ) -> set[DangleOid]:
        """
        Returns the set of dangle OIDs that sit at the start of their parent line.

        In directed mode a gap-fill connector extended from a start-node dangle would
        run antiparallel to the source line's digitization direction, breaking topology.
        Only end-node dangles are valid sources.

        Returns an empty set when lines_are_directed is False.
        """
        if not self.lines_are_directed:
            return set()

        start_oids: set[int] = set()
        for dangle_oid, (x, y) in dangle_xy.items():
            parent_id = dangle_parent.get(dangle_oid)
            if parent_id is None:
                continue
            poly = polyline_by_parent.get(int(parent_id))
            if poly is None:
                continue
            if self._xy_is_at_line_start(poly, x, y):
                start_oids.add(dangle_oid)
        return start_oids

    # ----------------------------
    # Connector crossing check helpers
    # ----------------------------

    def _build_trimmed_connector(
        self,
        *,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        trim_distance: float,
        spatial_reference: Any,
    ) -> Any:
        """
        Returns a connector polyline with trim_distance removed from each endpoint.

        Returns None if the connector is too short to survive trimming (i.e.
        2 * trim_distance >= full length).  The returned geometry is a temporary
        check artifact only; it is never written to output.
        """
        full = arcpy.Polyline(
            arcpy.Array([arcpy.Point(from_x, from_y), arcpy.Point(to_x, to_y)]),
            spatial_reference,
        )
        length = float(full.length)
        if length <= 2.0 * trim_distance:
            return None
        start_pt = full.positionAlongLine(trim_distance)
        end_pt = full.positionAlongLine(length - trim_distance)
        return arcpy.Polyline(
            arcpy.Array([start_pt.firstPoint, end_pt.firstPoint]),
            spatial_reference,
        )

    def _write_trimmed_cands_fc(
        self,
        *,
        cands_with_keys: list[tuple[Any, Any]],
        fc_path: str,
        spatial_reference: Any,
    ) -> dict[int, Any]:
        """Write trimmed connector geometries to a temp in-memory FC.

        Creates fc_path, inserts one polyline per (key, geom) pair, and returns
        a mapping from OID → key so near-table IN_FID results can be resolved
        back to the original candidate identifier.

        CAND_IDX stores the insertion index; a post-insert SearchCursor builds
        the OID→key mapping without relying on OID-assignment order.
        """
        if arcpy.Exists(fc_path):
            arcpy.management.Delete(fc_path)
        workspace, fc_name = fc_path.rsplit("/", 1)
        arcpy.management.CreateFeatureclass(
            workspace, fc_name, "POLYLINE", spatial_reference=spatial_reference
        )
        arcpy.management.AddField(fc_path, "CAND_IDX", "LONG")

        keys_by_idx: dict[int, Any] = {}
        with arcpy.da.InsertCursor(fc_path, ["SHAPE@", "CAND_IDX"]) as ins:
            for idx, (key, geom) in enumerate(cands_with_keys):
                ins.insertRow((geom, idx))
                keys_by_idx[idx] = key

        oid_field = arcpy.Describe(fc_path).OIDFieldName
        oid_to_key: dict[int, Any] = {}
        with arcpy.da.SearchCursor(fc_path, [oid_field, "CAND_IDX"]) as cur:
            for oid, idx in cur:
                oid_to_key[int(oid)] = keys_by_idx[int(idx)]

        return oid_to_key

    @staticmethod
    def _find_crossing_pairs(
        in_fc: str,
        against_fcs: list[str],
    ) -> dict[int, set[int]]:
        """Return {in_oid: {against_oid, ...}} for pairs where in_fc line crosses against_fcs line.

        Uses INTERSECT as a broad spatial pre-filter, then confirms each candidate
        with spatial_relationship="CROSSES" — exact, no false positives from
        XY-tolerance snapping.  Self-pairs are excluded when against_fcs contains in_fc.
        """
        pairs: dict[int, set[int]] = {}
        _in_lyr = arcpy.management.MakeFeatureLayer(in_fc, "__crossing_filter_lyr")[0]
        for i, _against_fc in enumerate(against_fcs):
            arcpy.management.SelectLayerByLocation(
                in_layer=_in_lyr,
                overlap_type="INTERSECT",
                select_features=_against_fc,
                selection_type="NEW_SELECTION" if i == 0 else "ADD_TO_SELECTION",
            )
        with arcpy.da.SearchCursor(_in_lyr, ["OID@", "SHAPE@"]) as _cur:
            for _in_oid, _in_geom in _cur:
                for _against_fc in against_fcs:
                    with arcpy.da.SearchCursor(
                        _against_fc,
                        ["OID@"],
                        spatial_filter=_in_geom,
                        spatial_relationship="CROSSES",
                    ) as _inner:
                        for (_against_oid,) in _inner:
                            if _against_fc == in_fc and _against_oid == _in_oid:
                                continue
                            pairs.setdefault(_in_oid, set()).add(_against_oid)
        arcpy.management.Delete(_in_lyr)
        return pairs

    def _find_crossing_conflict_keys(
        self,
        *,
        legal_rows_by_dangle: dict[DangleOid, list[NearCandidate]],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        check_feature_layers: list[str],
        trim_distance: float,
        spatial_reference: Any,
    ) -> tuple[set[tuple[int, str, int]], dict[tuple[int, str, int], Any]]:
        """
        Pre-filter: identify candidates whose trimmed connector crosses an existing feature.

        Writes trimmed candidate connectors to a temp in-memory FC and uses
        a spatial CROSSES relationship check against check_feature_layers as the
        source of truth for crossing conflicts.  Only legal candidates (already filtered by all other
        legality checks) are considered, so the temp FC is as small as possible.

        Returns:
          crossing_conflict_keys
            (dangle_oid, near_fc_key, near_fid) tuples whose trimmed connector is
            within connectivity_tolerance_meters of any check feature.
          trimmed_cache
            Trimmed connector polyline for every legal candidate key (None when the
            connector is too short to trim after 2x trimming).  Reused by the
            Kruskal candidate-vs-candidate crossing check.
        """
        trimmed_cache: dict[tuple[int, str, int], Any] = {}
        cands_with_keys: list[tuple[tuple[int, str, int], Any]] = []

        for dangle_oid, candidates in legal_rows_by_dangle.items():
            dangle_oid = int(dangle_oid)
            xy = dangle_xy.get(dangle_oid)
            if xy is None:
                continue
            from_x, from_y = xy

            for cand in candidates:
                key = (dangle_oid, cand.near_fc_key, cand.near_fid)

                trimmed = self._build_trimmed_connector(
                    from_x=from_x,
                    from_y=from_y,
                    to_x=cand.near_x,
                    to_y=cand.near_y,
                    trim_distance=trim_distance,
                    spatial_reference=spatial_reference,
                )
                trimmed_cache[key] = trimmed
                if trimmed is not None:
                    cands_with_keys.append((key, trimmed))

        if not cands_with_keys or not check_feature_layers:
            return set(), trimmed_cache

        _cands_fc = "memory/crossing_check_trimmed_cands"

        oid_to_key = self._write_trimmed_cands_fc(
            cands_with_keys=cands_with_keys,
            fc_path=_cands_fc,
            spatial_reference=spatial_reference,
        )

        crossing_pairs = self._find_crossing_pairs(_cands_fc, check_feature_layers)

        conflict_keys: set[tuple[int, str, int]] = set()
        for in_oid in crossing_pairs:
            key = oid_to_key.get(in_oid)
            if key is not None:
                conflict_keys.add(key)

        arcpy.management.Delete(_cands_fc)

        return conflict_keys, trimmed_cache

    def _find_barrier_crossing_keys(
        self,
        *,
        legal_rows_by_dangle: dict[DangleOid, list[NearCandidate]],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        barrier_layers: list[str] | None,
        trim_distance: float,
        spatial_reference: Any,
    ) -> set[tuple[int, str, int]]:
        """Return keys of candidates whose trimmed connector crosses a barrier layer.

        Returns an empty set immediately when barrier_layers is None or empty.
        barrier_layers are never used as snap targets; they only block candidates
        that cross them.
        """
        if not barrier_layers:
            return set()

        cands_with_keys: list[tuple[Any, Any]] = []
        for dangle_oid, candidates in legal_rows_by_dangle.items():
            dangle_oid = int(dangle_oid)
            xy = dangle_xy.get(dangle_oid)
            if xy is None:
                continue
            from_x, from_y = xy
            for cand in candidates:
                key = (dangle_oid, cand.near_fc_key, cand.near_fid)
                trimmed = self._build_trimmed_connector(
                    from_x=from_x,
                    from_y=from_y,
                    to_x=cand.near_x,
                    to_y=cand.near_y,
                    trim_distance=trim_distance,
                    spatial_reference=spatial_reference,
                )
                if trimmed is not None:
                    cands_with_keys.append((key, trimmed))

        if not cands_with_keys:
            return set()

        _fc = "memory/barrier_crossing_check"
        oid_to_key = self._write_trimmed_cands_fc(
            cands_with_keys=cands_with_keys,
            fc_path=_fc,
            spatial_reference=spatial_reference,
        )
        crossing_pairs = self._find_crossing_pairs(_fc, barrier_layers)
        arcpy.management.Delete(_fc)

        return {
            key
            for in_oid in crossing_pairs
            if (key := oid_to_key.get(in_oid)) is not None
        }

    # ----------------------------
    # Illegal targets detection
    # ----------------------------

    def detect_illegal_targets(
        self,
        *,
        dangle_parent: dict[DangleOid, ParentId],
        target_layers: list[str],
        topology: TopologyModel,
    ) -> _IllegalTargets:
        """
        illegal[parent_id][dataset_key] -> set(objectid)

        Clauses:
        - self line
        - objects connected to parent line endpoints

        Propagation:
        - Scope-dependent, using topology connectivity ids (not local BFS adjacency).
        """
        illegal: _IllegalTargets = {}

        self._illegal_self_line(
            illegal=illegal,
            parent_ids=set(dangle_parent.values()),
        )

        # Keep existing illegal detection semantics (connected endpoints rule).
        # We don't return adjacency anymore.
        _ = self._illegal_connected_features(
            illegal=illegal,
            target_layers=target_layers,
        )

        # Scope-driven propagation using topology output (no propagation for NONE/DIRECT).
        self._propagate_external_illegal_by_scope(
            illegal=illegal,
            topology=topology,
        )

        return illegal

    def _propagate_external_illegal_by_scope(
        self,
        *,
        illegal: _IllegalTargets,
        topology: TopologyModel,
    ) -> None:
        scope = topology.scope

        if scope in (
            logic_config.ConnectivityScope.NONE,
            logic_config.ConnectivityScope.DIRECT_CONNECTION,
        ):
            return

        cid = topology.connectivity_id_by_parent
        if not cid:
            return

        self._propagate_external_illegal_within_connectivity_ids(
            illegal=illegal,
            connectivity_id_by_parent=cid,
        )

    def _propagate_external_illegal_within_connectivity_ids(
        self,
        *,
        illegal: dict[int, dict[str, set[int]]],
        connectivity_id_by_parent: dict[int, int],
    ) -> None:
        """
        For each connectivity_id group (scope-defined component), union external illegal targets
        and apply to every parent in that group.

        External illegal targets = everything except the canonical lines_key (self-line rule).
        Self-line rule remains local and never propagates.
        """
        lines_key = self._dataset_key(self.lines_copy)

        groups: dict[int, list[int]] = {}
        for pid in illegal.keys():
            cid = connectivity_id_by_parent.get(int(pid))
            if cid is None:
                continue
            groups.setdefault(int(cid), []).append(int(pid))

        for _, members in groups.items():
            union_external: dict[str, set[int]] = {}

            for member in members:
                ds_map = illegal.get(int(member), {})
                for ds_key, ids in ds_map.items():
                    if ds_key == lines_key:
                        continue
                    union_external.setdefault(str(ds_key), set()).update(
                        {int(v) for v in ids}
                    )

            for member in members:
                illegal.setdefault(int(member), {})
                for ds_key, ids in union_external.items():
                    illegal[int(member)].setdefault(str(ds_key), set()).update(ids)

    def _illegal_self_line(
        self,
        *,
        illegal: _IllegalTargets,
        parent_ids: set[ParentId],
    ) -> None:
        lines_key = self._dataset_key(self.lines_copy)
        for pid in parent_ids:
            illegal.setdefault(int(pid), {}).setdefault(lines_key, set()).add(int(pid))

    def _illegal_connected_features(
        self,
        *,
        illegal: _IllegalTargets,
        target_layers: list[str],
    ) -> dict[ParentId, set[ParentId]]:
        adjacency: dict[ParentId, set[ParentId]] = {}

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

        connect_tol_m = float(self.connectivity_tolerance_meters)
        connect_tol = f"{connect_tol_m} Meters"

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(connectivity) START (in_endpoints={int(arcpy.management.GetCount(self.conn_endpoints)[0])}, near_features={len(near_features)}, radius={connect_tol})")  # [DBG_LINEGAP]
        arcpy.analysis.GenerateNearTable(
            in_features=self.conn_endpoints,
            near_features=near_features,
            out_table=self.conn_table,
            search_radius=connect_tol,
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=self.connectivity_closest_count,
            method="PLANAR",
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(connectivity) END (conn_table_rows={int(arcpy.management.GetCount(self.conn_table)[0])})")  # [DBG_LINEGAP]

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

    def _is_illegal(
        self,
        *,
        illegal: _IllegalTargets,
        parent_id: ParentId,
        target_fc_key: DatasetKey,
        target_oid: int,
    ) -> bool:
        ds = illegal.get(int(parent_id))
        if not ds:
            return False
        return int(target_oid) in ds.get(str(target_fc_key), set())

    def _parents_share_illegal_target(
        self,
        *,
        illegal: _IllegalTargets,
        a_parent: ParentId,
        b_parent: ParentId,
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
        candidates_sorted: list[NearCandidate],
        lines_fc_keys: set[DatasetKey],
        other_parent_id: ParentId,
        base_tol: float,
    ) -> Optional[NearCandidate]:
        """
        Find the row that explicitly targets the other *parent line* (lines_copy),
        within base_tol.
        """
        for cand in candidates_sorted:
            if cand.near_fc_key not in lines_fc_keys:
                continue
            if cand.near_fid != int(other_parent_id):
                continue
            if cand.near_dist <= float(base_tol):
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
            closest_count=self.candidate_closest_count,
            method="PLANAR",
        )

    def _read_near_table_grouped(
        self,
        *,
        near_table: str,
        dangles_fc_key: DatasetKey,
        lines_copy_key: DatasetKey,
        target_self_key: DatasetKey,
        lines_copy_oid_to_orig: dict[int, ParentId],
        target_self_oid_to_orig: dict[int, ParentId],
    ) -> dict[DangleOid, list[NearCandidate]]:

        grouped: dict[DangleOid, list[NearCandidate]] = {}

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
                raw_fid = int(near_fid)
                dist = float(near_dist)

                raw_key = self._dataset_key(near_fc)

                # Convert line-like near_fid into ORIGINAL_ID space. Segmented
                # twins (when self.segmentation is set) are checked first so
                # the candidate near table's segmented OID maps to its parent
                # ORIGINAL_ID; the lines_copy / target_self branches handle
                # the unsegmented path.
                seg_lookup = self._segmented_oid_to_parent_id.get(raw_key)
                if seg_lookup is not None:
                    nf_id = seg_lookup.get(raw_fid, raw_fid)
                elif raw_key == lines_copy_key:
                    nf_id = lines_copy_oid_to_orig.get(raw_fid, raw_fid)
                elif raw_key == target_self_key:
                    nf_id = target_self_oid_to_orig.get(raw_fid, raw_fid)
                else:
                    nf_id = raw_fid

                near_fc_key = self._normalize_target_key(
                    near_fc_key=raw_key,
                    lines_key=lines_key,
                    line_keys=line_keys,
                )

                # Defensive guard against self-dangle returning as candidate
                if near_fc_key == dangles_fc_key and nf_id == in_id:
                    continue

                grouped.setdefault(in_id, []).append(
                    NearCandidate(
                        near_fc_key=near_fc_key,
                        near_fid=nf_id,
                        near_dist=dist,
                        near_x=float(near_x),
                        near_y=float(near_y),
                        near_fc_key_raw=raw_key,
                        near_fid_raw=raw_fid,
                    )
                )

        return grouped

    def _build_dist_to_parent_line_by_dangle(
        self,
        *,
        grouped: dict[DangleOid, list[NearCandidate]],
        lines_key: DatasetKey,
        skip_dangles: set[DangleOid],
    ) -> dict[DangleOid, dict[ParentId, float]]:
        """Per source dangle, map every line-target parent_id to its near-table
        distance. Built once from the raw grouped near table so the dangle-pair
        connector-diff gate can do a flat lookup instead of a per-iteration
        dict-comp inside ``_select_dangle_proposals``. Distances reflect what
        arcpy reported regardless of legality (legal/illegal filtering decides
        snap targets, not distance measurements). ``skip_dangles`` excludes
        dangles whose candidates will never reach the gate (e.g. directed
        start-node sources rejected upstream by ``_filter_legal_candidates``).
        """
        return {
            d_oid: {
                int(c.near_fid): float(c.near_dist)
                for c in cands
                if c.near_fc_key == lines_key
            }
            for d_oid, cands in grouped.items()
            if d_oid not in skip_dangles
        }

    # ----------------------------
    # Planning: choose closest legal + detect pairs
    # ----------------------------

    def _candidate_is_legal(
        self,
        *,
        illegal: _IllegalTargets,
        dangle_parent: dict[DangleOid, ParentId],
        dangles_fc_key: DatasetKey,
        lines_fc_key: DatasetKey,
        line_like_ds_keys: set[DatasetKey],
        parent_id: ParentId,
        cand: NearCandidate,
        base_tol: float,
        dangle_candidate_tol: float,
        topology: TopologyModel | None = None,
    ) -> bool:
        ds_key = cand.near_fc_key
        oid = cand.near_fid
        dist = cand.near_dist

        if ds_key == dangles_fc_key:
            if dist > float(dangle_candidate_tol):
                return False

            other_parent = dangle_parent.get(int(oid))
            if other_parent is None:
                return False

            if topology is not None and self._same_network(
                a_parent=int(parent_id),
                b_parent=int(other_parent),
                topology=topology,
            ):
                return False

            # Dangle->dangle illegal-checks against the other parent line id
            if self._is_illegal(
                illegal=illegal,
                parent_id=parent_id,
                target_fc_key=lines_fc_key,
                target_oid=int(other_parent),
            ):
                return False

            return True

        # Line-like targets (self-lines and connect_to_features polylines) use the
        # expanded tolerance so true-dangle connections beyond base_tol are reachable.
        effective_tol = (
            dangle_candidate_tol if ds_key in line_like_ds_keys else base_tol
        )
        if dist > float(effective_tol):
            return False

        if ds_key == lines_fc_key and int(oid) == int(parent_id):
            return False

        if (
            ds_key == lines_fc_key
            and topology is not None
            and self._same_network(
                a_parent=int(parent_id),
                b_parent=int(oid),
                topology=topology,
            )
        ):
            return False

        if self._is_illegal(
            illegal=illegal,
            parent_id=parent_id,
            target_fc_key=ds_key,
            target_oid=oid,
        ):
            return False

        return True

    def _candidate_rejection_reason(
        self,
        *,
        illegal: _IllegalTargets,
        dangle_parent: dict[DangleOid, ParentId],
        dangles_fc_key: DatasetKey,
        lines_fc_key: DatasetKey,
        line_like_ds_keys: set[DatasetKey],
        parent_id: ParentId,
        cand: NearCandidate,
        base_tol: float,
        dangle_candidate_tol: float,
        topology: "TopologyModel | None",
    ) -> str:
        """Return the legality-failure reason for a candidate, mirroring _candidate_is_legal."""
        ds_key = cand.near_fc_key
        oid = cand.near_fid
        dist = cand.near_dist

        if ds_key == dangles_fc_key:
            if dist > float(dangle_candidate_tol):
                return "beyond_distance_tolerance"
            other_parent = dangle_parent.get(int(oid))
            if other_parent is None:
                return "illegal_target"
            if topology is not None and self._same_network(
                a_parent=int(parent_id), b_parent=int(other_parent), topology=topology
            ):
                return "same_network"
            if self._is_illegal(
                illegal=illegal,
                parent_id=parent_id,
                target_fc_key=lines_fc_key,
                target_oid=int(other_parent),
            ):
                return "illegal_target"
            return "illegal_target"

        effective_tol = (
            dangle_candidate_tol if ds_key in line_like_ds_keys else base_tol
        )
        if dist > float(effective_tol):
            return "beyond_distance_tolerance"
        if (
            topology is not None
            and ds_key == lines_fc_key
            and self._same_network(
                a_parent=int(parent_id), b_parent=int(oid), topology=topology
            )
        ):
            return "same_network"
        if self._is_illegal(
            illegal=illegal, parent_id=parent_id, target_fc_key=ds_key, target_oid=oid
        ):
            return "illegal_target"
        return "illegal_target"

    def _resolve_target_parent_id(
        self,
        cand: NearCandidate,
        dangle_parent: dict[DangleOid, ParentId],
        dangles_fc_key: DatasetKey,
        lines_fc_key: DatasetKey,
    ) -> Optional[ParentId]:
        """Return the target parent original ID for a candidate, or None for external targets."""
        ds_key = cand.near_fc_key
        near_fid = cand.near_fid
        if ds_key == dangles_fc_key:
            return dangle_parent.get(near_fid)
        if ds_key == lines_fc_key:
            return near_fid  # already in ORIGINAL_ID space
        return None

    def _normalize_directional_angles(
        self,
        *,
        src_parent_id: ParentId,
        src_angle_deg: float,
        target_angle: float,
        src_connector_diff: float,
        connector_angle: float,
        dangle_x: float,
        dangle_y: float,
        tgt_poly: Any,
        tgt_snap_x: float,
        tgt_snap_y: float,
        is_dangle_pair: bool,
        is_dangle_parent_line: bool,
        polyline_by_parent: dict[ParentId, Any],
    ) -> _DirectionalNormalization:
        """Apply the directional-mode flips and src_connector_diff override.

        Undirected mode: flip src_angle if the source line starts at the dangle
        (so it points outward toward the gap); flip target_angle when the snap
        is not at the target line's start (so both dangles in a pair receive
        a 0° score for a clean collinear fill).

        Directed mode: lines are pre-oriented, so skip flips and re-express
        src_connector_diff using directional_diff so anti-parallel src/connector
        reports 180° instead of collapsing under orientation_diff.
        """
        src_poly_for_norm = polyline_by_parent.get(int(src_parent_id))
        endpoint_snap = is_dangle_pair or is_dangle_parent_line

        if not self.lines_are_directed:
            if (
                src_poly_for_norm is not None
                and self._xy_is_at_line_start(src_poly_for_norm, dangle_x, dangle_y)
            ):
                src_angle_deg = (float(src_angle_deg) + 180.0) % 360.0
            if not self._xy_is_at_line_start(tgt_poly, tgt_snap_x, tgt_snap_y):
                target_angle = (float(target_angle) + 180.0) % 360.0
        else:
            src_connector_diff = self._directional_diff(
                float(src_angle_deg), float(connector_angle)
            )

        return _DirectionalNormalization(
            src_angle_deg=float(src_angle_deg),
            target_angle=float(target_angle),
            src_connector_diff=float(src_connector_diff),
            endpoint_snap=bool(endpoint_snap),
        )

    def _resolve_target_angle_and_snap(
        self,
        *,
        cand: NearCandidate,
        ds_key: DatasetKey,
        lines_fc_key: DatasetKey,
        dangles_fc_key: DatasetKey,
        dangle_parent: dict[DangleOid, ParentId],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        polyline_by_parent: dict[ParentId, Any],
        polyline_by_external: dict[DatasetKey, dict[int, Any]],
        polyline_by_segment: dict[DatasetKey, dict[int, Any]],
    ) -> _TargetAngleResolution:
        """Resolve the target polyline, its local angle, and the snap point.

        For dangle-pair targets the snap defaults to the precise dangle XY
        (more accurate than the near-table snap, which is rounded). Other
        targets use the near-table coordinates directly.

        When segmentation is enabled, line-target angle is evaluated against
        the candidate's segment polyline (looked up via near_fc_key_raw +
        near_fid_raw in polyline_by_segment) so each segment gets its own
        local angle. Source-side dangle and other-dangle target lookups stay
        on parent geometry — those endpoints sit at the parent's true ends.
        """
        near_fid = cand.near_fid
        snap_x = float(cand.near_x)
        snap_y = float(cand.near_y)
        use_segment = self.segmentation is not None

        if ds_key == lines_fc_key:
            tgt_parent = int(near_fid)
            if use_segment:
                seg_lookup = polyline_by_segment.get(cand.near_fc_key_raw)
                tgt_poly = (
                    seg_lookup.get(int(cand.near_fid_raw))
                    if seg_lookup is not None
                    else None
                )
                angle_ds_key = cand.near_fc_key_raw
                angle_oid = int(cand.near_fid_raw)
            else:
                tgt_poly = polyline_by_parent.get(tgt_parent)
                angle_ds_key = lines_fc_key
                angle_oid = tgt_parent
            if tgt_poly is None:
                return _TargetAngleResolution(
                    None, None, snap_x, snap_y, target_parent_id=tgt_parent
                )
            target_angle = self._local_line_angle_cached(
                dataset_key=angle_ds_key,
                oid=angle_oid,
                polyline=tgt_poly,
                x=snap_x,
                y=snap_y,
            )
            return _TargetAngleResolution(
                target_angle, tgt_poly, snap_x, snap_y, target_parent_id=tgt_parent
            )

        if ds_key == dangles_fc_key:
            other_dangle_oid = int(near_fid)
            other_parent = dangle_parent.get(other_dangle_oid)
            if other_parent is None:
                return _TargetAngleResolution(None, None, snap_x, snap_y)
            tgt_poly = polyline_by_parent.get(int(other_parent))
            if tgt_poly is None:
                return _TargetAngleResolution(
                    None, None, snap_x, snap_y, target_parent_id=int(other_parent)
                )
            xy = dangle_xy.get(other_dangle_oid)
            if xy is not None:
                snap_x, snap_y = float(xy[0]), float(xy[1])
            target_angle = self._local_line_angle_cached(
                dataset_key=lines_fc_key,
                oid=int(other_parent),
                polyline=tgt_poly,
                x=snap_x,
                y=snap_y,
            )
            return _TargetAngleResolution(
                target_angle,
                tgt_poly,
                snap_x,
                snap_y,
                target_parent_id=int(other_parent),
            )

        if use_segment:
            seg_lookup = polyline_by_segment.get(cand.near_fc_key_raw)
            tgt_poly = (
                seg_lookup.get(int(cand.near_fid_raw))
                if seg_lookup is not None
                else None
            )
            angle_ds_key = cand.near_fc_key_raw
            angle_oid = int(cand.near_fid_raw)
        else:
            ext = polyline_by_external.get(ds_key, {})
            tgt_poly = ext.get(int(near_fid))
            angle_ds_key = ds_key
            angle_oid = int(near_fid)
        if tgt_poly is None:
            return _TargetAngleResolution(None, None, snap_x, snap_y)
        target_angle = self._local_line_angle_cached(
            dataset_key=angle_ds_key,
            oid=angle_oid,
            polyline=tgt_poly,
            x=snap_x,
            y=snap_y,
        )
        return _TargetAngleResolution(target_angle, tgt_poly, snap_x, snap_y)

    def _resolve_treat_as_line_like(
        self,
        *,
        ds_key: DatasetKey,
        lines_fc_key: DatasetKey,
        dangles_fc_key: DatasetKey,
        is_external_line_like: dict[DatasetKey, bool],
    ) -> bool:
        """Decide whether a candidate's dataset should use line-aware angle scoring.

        Input lines and dangles are always line-like. External datasets honour
        the AngleTargetMode override; AUTO defers to the runtime detection
        cached in ``is_external_line_like``.
        """
        if ds_key == lines_fc_key or ds_key == dangles_fc_key:
            return True
        mode = self._angle_mode_by_external_ds_key.get(
            ds_key, logic_config.AngleTargetMode.AUTO
        )
        if mode == logic_config.AngleTargetMode.FORCE_NON_LINE:
            return False
        return bool(is_external_line_like.get(ds_key, False))

    def _unavailable_assessment(
        self,
        *,
        ds_key: DatasetKey,
        dangles_fc_key: DatasetKey,
        src_connector_diff: Optional[float] = None,
    ) -> AngleAssessment:
        """Assessment used when an angle input is missing.

        Conservative policy: never block, never penalise. The extra-dangle
        allowance only restricts dangle-layer candidates, so it stays True
        for every other ds_key.
        """
        return AngleAssessment(
            available=False,
            blocks=False,
            allow_extra_dangle=ds_key != dangles_fc_key,
            angle_metric_deg=None,
            src_connector_diff=src_connector_diff,
        )

    def _assess_angle(
        self,
        *,
        src_parent_id: ParentId,
        dangle_x: float,
        dangle_y: float,
        src_angle_deg: Optional[float],
        cand: NearCandidate,
        dangles_fc_key: DatasetKey,
        lines_fc_key: DatasetKey,
        dangle_parent: dict[DangleOid, ParentId],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        polyline_by_parent: dict[ParentId, Any],
        polyline_by_external: dict[DatasetKey, dict[int, Any]],
        polyline_by_segment: dict[DatasetKey, dict[int, Any]],
        is_external_line_like: dict[DatasetKey, bool],
        dangle_xys_by_parent: Optional[_DangleXYsByParent] = None,
        dist_to_parent_line_by_id: Optional[dict[ParentId, float]] = None,
    ) -> AngleAssessment:
        ds_key = cand.near_fc_key
        near_fid = cand.near_fid
        near_x = cand.near_x
        near_y = cand.near_y

        connector_angle = self._connector_angle_deg(
            from_x=dangle_x, from_y=dangle_y, to_x=near_x, to_y=near_y
        )

        treat_as_line_like = self._resolve_treat_as_line_like(
            ds_key=ds_key,
            lines_fc_key=lines_fc_key,
            dangles_fc_key=dangles_fc_key,
            is_external_line_like=is_external_line_like,
        )

        # Base requirements
        if src_angle_deg is None or connector_angle is None:
            return self._unavailable_assessment(
                ds_key=ds_key,
                dangles_fc_key=dangles_fc_key,
            )

        src_connector_diff = self._orientation_diff(
            float(src_angle_deg), float(connector_angle)
        )

        # Non-line targets use src_connector_diff directly. In directed mode,
        # promote to _directional_diff (0..180) so anti-parallel src/connector
        # reports its true large angle instead of folding back into 0..90.
        # Upstream filtering guarantees the src dangle is at its parent's end
        # vertex when lines_are_directed, so src_angle already points outward.
        if not treat_as_line_like:
            if self.lines_are_directed:
                src_connector_diff = self._directional_diff(
                    float(src_angle_deg), float(connector_angle)
                )
            metric = float(src_connector_diff)
            block_thr = self.angle_block_threshold_degrees
            blocks = block_thr is not None and metric > float(block_thr)
            extra_thr = self.angle_extra_dangle_threshold_degrees
            allow_extra = (
                ds_key != dangles_fc_key
                or extra_thr is None
                or metric <= float(extra_thr)
            )
            return AngleAssessment(
                available=True,
                blocks=bool(blocks),
                allow_extra_dangle=bool(allow_extra),
                angle_metric_deg=float(metric),
                src_connector_diff=float(src_connector_diff),
            )

        # Line-like targets: need target angle too
        connector_target_diff: Optional[float] = None
        src_target_diff: Optional[float] = None
        connector_transition_diff: Optional[float] = None

        resolved = self._resolve_target_angle_and_snap(
            cand=cand,
            ds_key=ds_key,
            lines_fc_key=lines_fc_key,
            dangles_fc_key=dangles_fc_key,
            dangle_parent=dangle_parent,
            dangle_xy=dangle_xy,
            polyline_by_parent=polyline_by_parent,
            polyline_by_external=polyline_by_external,
            polyline_by_segment=polyline_by_segment,
        )
        target_angle = resolved.target_angle
        tgt_poly = resolved.tgt_poly
        tgt_snap_x = resolved.snap_x
        tgt_snap_y = resolved.snap_y
        target_parent_id = resolved.target_parent_id

        if target_angle is None:
            return self._unavailable_assessment(
                ds_key=ds_key,
                dangles_fc_key=dangles_fc_key,
                src_connector_diff=float(src_connector_diff),
            )

        # Dangle-pair detection is retained for:
        # (1) edge-case distance bonus eligibility
        # (2) diagnostic labeling
        # (3) using the precise dangle XY as the target snap point for angle normalisation.
        # It no longer solely drives the switch to directional semantics.
        _is_dangle_pair = ds_key == dangles_fc_key
        _is_dangle_parent_line = False
        if ds_key == lines_fc_key and dangle_xys_by_parent is not None:
            _tol = self.connectivity_tolerance_meters
            _is_dangle_parent_line = any(
                abs(dx - near_x) < _tol and abs(dy - near_y) < _tol
                for dx, dy in dangle_xys_by_parent.get(int(near_fid), [])
            )

        # Use directional diff (0–180°, src_target_diff as metric) when:
        # - lines_are_directed, or
        # - comparing dangle-pair / dangle-parent-line targets in undirected mode, to avoid
        #   collapsing anti-parallel lines to zero diff.
        _use_directional = (
            self.lines_are_directed or _is_dangle_pair or _is_dangle_parent_line
        )

        endpoint_snap = False
        if _use_directional:
            _diff = self._directional_diff
            angle_max_deg = 180.0
            norm = self._normalize_directional_angles(
                src_parent_id=src_parent_id,
                src_angle_deg=float(src_angle_deg),
                target_angle=float(target_angle),
                src_connector_diff=float(src_connector_diff),
                connector_angle=float(connector_angle),
                dangle_x=dangle_x,
                dangle_y=dangle_y,
                tgt_poly=tgt_poly,
                tgt_snap_x=tgt_snap_x,
                tgt_snap_y=tgt_snap_y,
                is_dangle_pair=_is_dangle_pair,
                is_dangle_parent_line=_is_dangle_parent_line,
                polyline_by_parent=polyline_by_parent,
            )
            src_angle_deg = norm.src_angle_deg
            target_angle = norm.target_angle
            src_connector_diff = norm.src_connector_diff
            endpoint_snap = norm.endpoint_snap
        else:
            _diff = self._orientation_diff
            angle_max_deg = 90.0

        connector_target_diff = _diff(float(connector_angle), float(target_angle))
        src_target_diff = _diff(float(src_angle_deg), float(target_angle))
        # connector_transition_diff mixes src→connector and connector→target.
        # Use directional src→connector when in directional mode to stay consistent.
        _src_conn_for_transition = (
            self._directional_diff(float(src_angle_deg), float(connector_angle))
            if _use_directional
            else float(src_connector_diff)
        )
        connector_transition_diff = 0.5 * (
            _src_conn_for_transition + float(connector_target_diff)
        )

        # Pick the angle metric.
        #
        # Non-directional path (lines_are_directed=False, target is not a dangle
        # endpoint snap): src_connector_diff alone.
        #
        # Undirected dangle endpoint snap (lines_are_directed=False but target is a
        # dangle or the parent line at a dangle endpoint): src_target_diff after the
        # normalisation flips, so a clean collinear pair scores 0°.
        #
        # Directional path (lines_are_directed=True): default to
        # max(src_target_diff, src_connector_diff, connector_target_diff) for
        # line-like targets — a bad score on any of the three joints makes the
        # candidate bad. The third term catches the case where src→target looks
        # aligned overall but the connector enters the target broadside, which
        # the two-term max cannot see. At endpoint snaps two extra rules apply:
        #   - End-to-start enforcement: target must be at its line's start, else
        #     metric is forced to 180° (rejection). Src-end is guaranteed
        #     upstream by _filter_legal_candidates, so only target-start needs to
        #     be checked here.
        #   - Close-dangle exception: connector_angle_diff_required_above_meters
        #     decides whether to penalise bad connector direction. When the
        #     parent line of the target dangle is within the threshold the
        #     geometry already constrains src↔connector alignment, so use
        #     src_target_diff alone. None disables the penalty entirely (always
        #     src_target_diff at endpoint snaps); 0 always penalises (always
        #     three-term max). For dangle-pair targets a per-dangle parent-line
        #     lookup is consulted only when cand.near_dist > threshold (a closer
        #     dangle implies an at-least-as-close parent). For dangle-parent-line
        #     targets cand.near_dist *is* the parent-line distance, so the
        #     direct comparison decides without a lookup.
        connector_diff_threshold = self.connector_angle_diff_required_above_meters
        if not _use_directional:
            metric = float(src_connector_diff)
        elif not self.lines_are_directed:
            # Undirected dangle endpoint snap (dangle pair or dangle-parent-line).
            metric = float(src_target_diff)
        elif endpoint_snap:
            if not self._xy_is_at_line_start(tgt_poly, tgt_snap_x, tgt_snap_y):
                metric = 180.0
            elif connector_diff_threshold is None:
                metric = float(src_target_diff)
            elif float(connector_diff_threshold) == 0.0:
                metric = max(
                    float(src_target_diff),
                    float(src_connector_diff),
                    float(connector_target_diff),
                )
            elif float(cand.near_dist) <= float(connector_diff_threshold):
                # Close enough that the parent line is guaranteed within the
                # threshold (dangle-pair: parent passes through the dangle;
                # dangle-parent-line: target IS the parent). No lookup needed.
                metric = float(src_target_diff)
            elif _is_dangle_pair:
                # Dangle target outside the threshold — the parent line might
                # still be within (e.g. running parallel back toward the source).
                # Lookup required. Conservative on miss (treat as outside).
                _parent_dist = (
                    dist_to_parent_line_by_id.get(int(target_parent_id))
                    if (
                        dist_to_parent_line_by_id is not None
                        and target_parent_id is not None
                    )
                    else None
                )
                if (
                    _parent_dist is not None
                    and float(_parent_dist) <= float(connector_diff_threshold)
                ):
                    metric = float(src_target_diff)
                else:
                    metric = max(
                        float(src_target_diff),
                        float(src_connector_diff),
                        float(connector_target_diff),
                    )
            else:
                # Dangle-parent-line outside the threshold: parent_dist == near_dist
                # by construction, so the parent is also outside. No lookup.
                metric = max(
                    float(src_target_diff),
                    float(src_connector_diff),
                    float(connector_target_diff),
                )
        else:
            metric = max(
                float(src_target_diff),
                float(src_connector_diff),
                float(connector_target_diff),
            )

        block_thr = self.angle_block_threshold_degrees
        blocks = block_thr is not None and metric > float(block_thr)
        extra_thr = self.angle_extra_dangle_threshold_degrees
        allow_extra = (
            ds_key != dangles_fc_key
            or extra_thr is None
            or metric <= float(extra_thr)
        )

        return AngleAssessment(
            available=True,
            blocks=bool(blocks),
            allow_extra_dangle=bool(allow_extra),
            angle_metric_deg=float(metric),
            angle_max_deg=float(angle_max_deg),
            src_connector_diff=float(src_connector_diff),
            connector_target_diff=float(connector_target_diff),
            src_target_diff=float(src_target_diff),
            connector_transition_diff=float(connector_transition_diff),
        )

    def _pair_token_from_candidate(
        self,
        *,
        dangle_parent: dict[DangleOid, ParentId],
        dangles_fc_key: DatasetKey,
        lines_fc_keys: set[DatasetKey],
        cand: NearCandidate,
    ) -> Optional[ParentId]:
        """
        Returns the *other parent line id* if this candidate represents “the other side”
        of a potential dangle pair (either via dangle feature or via line feature).
        """
        ds_key = cand.near_fc_key
        oid = cand.near_fid

        if ds_key == dangles_fc_key:
            other_parent = dangle_parent.get(oid)
            return int(other_parent) if other_parent is not None else None

        if ds_key in lines_fc_keys:
            return int(oid)

        return None

    def _select_first_legal_candidate(
        self,
        *,
        candidates_sorted: list[NearCandidate],
        illegal: _IllegalTargets,
        dangle_parent: dict[DangleOid, ParentId],
        dangles_fc_key: DatasetKey,
        lines_fc_key: DatasetKey,
        parent_id: ParentId,
        base_tol: float,
        topology: TopologyModel | None = None,
    ) -> Optional[NearCandidate]:
        for cand in candidates_sorted:
            if self._candidate_is_legal(
                illegal=illegal,
                dangle_parent=dangle_parent,
                dangles_fc_key=dangles_fc_key,
                lines_fc_key=lines_fc_key,
                line_like_ds_keys=set(),  # no expanded tolerance in this context
                parent_id=parent_id,
                cand=cand,
                base_tol=base_tol,
                dangle_candidate_tol=base_tol,
                topology=topology,
            ):
                return cand
        return None

    def _find_best_dangle_candidate_to_parent(
        self,
        *,
        candidates_sorted: list[NearCandidate],
        dangles_fc_key: DatasetKey,
        dangle_parent: dict[DangleOid, ParentId],
        target_parent_id: ParentId,
        dangle_tol: float,
    ) -> Optional[NearCandidate]:
        """
        From A's candidate rows, find the closest dangle feature that belongs to target_parent_id.
        This handles "target parent has 2 dangles" correctly by selecting the closest.
        """
        best: Optional[NearCandidate] = None
        best_dist = float("inf")

        for cand in candidates_sorted:
            if cand.near_fc_key != dangles_fc_key:
                continue

            other_dangle_oid = cand.near_fid
            other_parent = dangle_parent.get(other_dangle_oid)
            if other_parent is None:
                continue
            if int(other_parent) != int(target_parent_id):
                continue

            dist = cand.near_dist
            if dist <= float(dangle_tol) and dist < best_dist:
                best = cand
                best_dist = dist

        return best

    def _best_dangle_for_parent_towards_target_parent(
        self,
        *,
        parent_id: ParentId,
        target_parent_id: ParentId,
        parent_to_dangles: dict[ParentId, list[DangleOid]],
        per_dangle: dict[DangleOid, dict],
    ) -> DangleOid | None:
        """
        Choose the dangle on `parent_id` that is most suitable for pairing with `target_parent_id`.

        Rule:
        - Only consider dangles whose pair_token_parent == target_parent_id
        - Pick the one with the smallest first_legal near_dist
        """
        dangles = parent_to_dangles.get(int(parent_id), [])
        if not dangles:
            return None

        best_dangle = None
        best_dist = float("inf")

        for d_oid in dangles:
            info = per_dangle.get(int(d_oid))
            if not info:
                continue

            if int(info.get("pair_token_parent") or -1) != int(target_parent_id):
                continue

            first_legal = info.get("first_legal")
            if not first_legal:
                continue

            dist = float(first_legal.get("near_dist", float("inf")))
            if dist < best_dist:
                best_dist = dist
                best_dangle = int(d_oid)

        return best_dangle

    def _find_specific_dangle_candidate(
        self,
        *,
        candidates_sorted: list[NearCandidate],
        dangles_fc_key: DatasetKey,
        other_dangle_oid: DangleOid,
        dangle_tol: float,
    ) -> Optional[NearCandidate]:
        """
        Find candidate row that targets a specific dangle OID (within dangle_tol).
        """
        for cand in candidates_sorted:
            if cand.near_fc_key != dangles_fc_key:
                continue
            if cand.near_fid != int(other_dangle_oid):
                continue

            dist = cand.near_dist
            if dist <= float(dangle_tol):
                return cand
        return None

    def _best_dangle_for_parent(
        self,
        *,
        parent_id: ParentId,
        parent_to_dangles: dict[ParentId, list[DangleOid]],
        per_dangle: dict[DangleOid, dict],
    ) -> DangleOid | None:
        """
        Choose which dangle (of possibly many on the same parent line) should represent
        this parent for default / non-pair behavior.

        Rule: choose the dangle whose first_legal candidate is closest (smallest near_dist).
        """
        dangles = parent_to_dangles.get(int(parent_id), [])
        if not dangles:
            return None

        best = None
        best_dist = float("inf")
        for d_oid in dangles:
            info = per_dangle.get(int(d_oid))
            if not info:
                continue
            cand = info.get("first_legal")
            if not cand:
                continue
            dist = float(cand.get("near_dist", float("inf")))
            if dist < best_dist:
                best_dist = dist
                best = int(d_oid)

        return best

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

    def _compute_best_line_parent_by_dangle(
        self,
        *,
        legal_rows_by_dangle: dict[DangleOid, list[NearCandidate]],
        parent_id_by_dangle: dict[DangleOid, ParentId],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        dangle_parent: dict[DangleOid, ParentId],
        dangles_key: DatasetKey,
        lines_key: DatasetKey,
        polyline_by_parent: dict[ParentId, Any],
        polyline_by_external: dict[DatasetKey, dict[int, Any]],
        polyline_by_segment: dict[DatasetKey, dict[int, Any]],
        is_external_line_like: dict[DatasetKey, bool],
    ) -> dict[DangleOid, ParentId]:
        """Per dangle, pick the line-target parent that wins the angle-aware
        best-fit score. Used downstream by the edge-case bonus detection in
        _select_dangle_proposals."""
        best_line_parent_by_dangle: dict[DangleOid, ParentId] = {}

        for dangle_oid in sorted(legal_rows_by_dangle.keys()):
            parent_id = int(parent_id_by_dangle[dangle_oid])

            xy = dangle_xy.get(int(dangle_oid))
            if xy is None:
                continue
            d_x, d_y = xy

            src_poly = polyline_by_parent.get(int(parent_id))
            src_angle = None
            if src_poly is not None:
                src_angle = self._local_line_angle_cached(
                    dataset_key=lines_key,
                    oid=int(parent_id),
                    polyline=src_poly,
                    x=float(d_x),
                    y=float(d_y),
                )

            best = None
            best_score = None

            for cand in legal_rows_by_dangle[dangle_oid]:
                if cand.near_fc_key != lines_key:
                    continue

                assess = self._assess_angle(
                    src_parent_id=int(parent_id),
                    dangle_x=float(d_x),
                    dangle_y=float(d_y),
                    src_angle_deg=src_angle,
                    cand=cand,
                    dangles_fc_key=dangles_key,
                    lines_fc_key=lines_key,
                    dangle_parent=dangle_parent,
                    dangle_xy=dangle_xy,
                    polyline_by_parent=polyline_by_parent,
                    polyline_by_external=polyline_by_external,
                    polyline_by_segment=polyline_by_segment,
                    is_external_line_like=is_external_line_like,
                )
                if assess.blocks:
                    continue

                raw_dist = cand.near_dist
                _tol = float(self.gap_tolerance_meters) or 1.0
                eff = self._compute_best_fit_score(
                    norm_dist=raw_dist / _tol, assess=assess
                )

                # Deterministic tie-break:
                score = (float(eff), float(raw_dist), self._candidate_sort_key(cand))
                if best_score is None or score < best_score:
                    best_score = score
                    best = cand.near_fid

            if best is not None:
                best_line_parent_by_dangle[int(dangle_oid)] = int(best)

        return best_line_parent_by_dangle

    # ----------------------------
    # Build plan (two-phase: detect pairs first, then decide moves)
    # ----------------------------

    def _build_plan(
        self, *, dangles_fc: str, target_layers: list[str]
    ) -> BuildPlanResult:
        """Decide which dangles to fill and how, in four staged scopes.

        Each scope narrows the set of surviving proposals.  Rejected
        candidates carry the scope label of the earliest stage that
        rejected them, which drives the diagnostic feature class.

        How:
            CANDIDATE scope
                Build the near table and angle caches, then run legality
                gates (``_filter_legal_candidates``) and crossing
                pre-filters (barrier + existing-feature CROSSES checks).
                For each surviving dangle, pick the best line-target parent
                (``_compute_best_line_parent_by_dangle``) and emit one
                angle-aware proposal per dangle
                (``_select_dangle_proposals``).

            NETWORK scope
                Detect mutual pairs, re-normalize Z inside each undirected
                A<->B connection group (``_run_connection_normalization``),
                and pick one winner per connection
                (``_run_connection_selection``).  The winner is stamped
                with its authoritative ``gap_source``.

            KRUSKAL scope
                Re-normalize Z globally (``_run_global_normalization``),
                then run Kruskal-style cycle prevention plus
                accepted-connector crossing checks (``_run_kruskal``).

            DEFERRED scope
                Identify proposals whose target endpoint will move during
                ``_apply_plan`` (``_identify_resnap_captures``) and
                assemble the per-parent plan entries
                (``_assemble_plan_entries``).  Their final status is not
                resolved here — it is filled in by
                ``_update_deferred_diagnostics`` after the resnap pass in
                ``run``.

            Each scope short-circuits to a diagnostics-only
            ``BuildPlanResult`` when no survivors remain, so the caller
            still receives a complete rejection record.

        Returns:
            ``BuildPlanResult`` — plan keyed by parent id, plus resnap
            captures, diagnostics, and the Kruskal bookkeeping needed for
            the post-apply passes in ``run``.
        """
        dangle_parent = self._build_dangle_parent_lookup(dangles_fc=dangles_fc)
        dangle_xy = self._build_dangle_xy_lookup(dangles_fc=dangles_fc)

        relevant_parent_ids = set(dangle_parent.values())

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} TopologyBuilder.build START (relevant_parents={len(relevant_parent_ids)})")  # [DBG_LINEGAP]
        topology = TopologyBuilder(
            lines_fc=self.lines_copy,
            original_id_field=self.ORIGINAL_ID,
            connect_to_features=self.connect_to_features,
            dataset_key_fn=self._dataset_key,
            wfm=self.wfm,
            write_work_files_to_memory=self.write_work_files_to_memory,
            connectivity_tolerance_meters=self.connectivity_tolerance_meters,
            line_connectivity_mode=self.line_connectivity_mode,
        ).build(
            scope=self.connectivity_scope,
            relevant_parent_ids=relevant_parent_ids,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} TopologyBuilder.build END")  # [DBG_LINEGAP]

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} detect_illegal_targets START")  # [DBG_LINEGAP]
        illegal = self.detect_illegal_targets(
            dangle_parent=dangle_parent,
            target_layers=target_layers,
            topology=topology,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} detect_illegal_targets END (illegal_dangles={len(illegal)})")  # [DBG_LINEGAP]

        dangles_key = self._dataset_key(dangles_fc)
        lines_key = self._dataset_key(self.lines_copy)

        # Candidate near table reads from segmented twins when
        # self.segmentation is set (per-segment closest-point + per-segment
        # angle); other engine phases continue to use the unsegmented globals.
        candidate_target_layers = self._candidate_target_layers(target_layers)
        near_features = list(candidate_target_layers) + [dangles_fc]

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

        # Expanded radius so we can see dangle→dangle candidates, but legality will enforce tol rules.
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(candidate) START (near_features={len(near_features)}, radius={self._expanded_dangle_tolerance_linear_unit()})")  # [DBG_LINEGAP]
        self._generate_near_table(
            in_dangles=dangles_fc,
            near_features=near_features,
            search_radius=self._expanded_dangle_tolerance_linear_unit(),
            out_table=self.near_table,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(candidate) END (near_table_rows={int(arcpy.management.GetCount(self.near_table)[0])})")  # [DBG_LINEGAP]

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _read_near_table_grouped START")  # [DBG_LINEGAP]
        grouped = self._read_near_table_grouped(
            near_table=self.near_table,
            dangles_fc_key=dangles_key,
            lines_copy_key=lines_copy_key,
            target_self_key=target_self_key,
            lines_copy_oid_to_orig=lines_copy_oid_to_orig,
            target_self_oid_to_orig=target_self_oid_to_orig,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _read_near_table_grouped END (dangles_with_candidates={len(grouped)})")  # [DBG_LINEGAP]

        if not grouped:
            return BuildPlanResult.empty(diagnostics=[])

        collect_diags = self._collect_diags

        def _build_diagnostics(
            state: _DiagnosticsState,
        ) -> list["CandidateDiagnostic"]:
            return self._assemble_diagnostics(
                collect_diags=collect_diags,
                state=state,
                dangle_xy=dangle_xy,
                dangle_parent=dangle_parent,
                dangles_key=dangles_key,
                lines_key=lines_key,
            )

        def _empty_result(state: _DiagnosticsState) -> BuildPlanResult:
            return BuildPlanResult.empty(diagnostics=_build_diagnostics(state))

        # ============================
        # CANDIDATE SCOPE
        # Decides which (dangle, target) pairs are legal, then picks one
        # winning proposal per dangle.
        # ============================

        # ----------------------------
        # Step 1 - Angle & polyline caches
        # Built before candidate filtering so line_like_ds_keys is available.
        # ----------------------------
        angle_caches = self._build_angle_caches(
            target_layers=target_layers,
            lines_key=lines_key,
        )
        polyline_by_parent = angle_caches.polyline_by_parent
        polyline_by_external = angle_caches.polyline_by_external
        polyline_by_segment = angle_caches.polyline_by_segment
        is_external_line_like = angle_caches.is_external_line_like
        line_like_external_ds_keys = angle_caches.line_like_external_ds_keys
        line_like_ds_keys = angle_caches.line_like_ds_keys

        # In directed mode, source dangles at a line's start node are invalid sources.
        directed_start_dangles = self._directed_start_dangle_oids(
            dangle_xy=dangle_xy,
            dangle_parent=dangle_parent,
            polyline_by_parent=polyline_by_parent,
        )

        # Built once when the dangle-pair distance gate is active; passed into
        # _select_dangle_proposals so the gate has a flat per-dangle lookup
        # instead of rebuilding it on every iteration. Skips start-node src
        # dangles since their candidates are dropped by _filter_legal_candidates
        # and the gate is a no-op outside directed mode.
        dist_to_parent_line_by_dangle: Optional[
            dict[DangleOid, dict[ParentId, float]]
        ] = None
        if (
            self.lines_are_directed
            and self.connector_angle_diff_required_above_meters is not None
        ):
            dist_to_parent_line_by_dangle = self._build_dist_to_parent_line_by_dangle(
                grouped=grouped,
                lines_key=lines_key,
                skip_dangles=directed_start_dangles,
            )

        # ----------------------------
        # Step 2 - Legality gates (distance / network / illegal-target)
        # Collects legal (dangle, target) candidate rows.
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _filter_legal_candidates START (grouped={len(grouped)})")  # [DBG_LINEGAP]
        legal_rows_by_dangle, parent_id_by_dangle, _step1a_illegal = (
            self._filter_legal_candidates(
                grouped=grouped,
                dangle_parent=dangle_parent,
                illegal=illegal,
                dangles_key=dangles_key,
                lines_key=lines_key,
                line_like_ds_keys=line_like_ds_keys,
                base_tol=base_tol,
                dangle_tol=dangle_tol,
                topology=topology,
                collect_diags=collect_diags,
                directed_source_illegal_oids=directed_start_dangles,
            )
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _filter_legal_candidates END (legal_dangles={len(legal_rows_by_dangle)}, illegal_rows={len(_step1a_illegal)})")  # [DBG_LINEGAP]

        # Eager release: the outer dict's surviving NearCandidate lists are
        # already referenced by legal_rows_by_dangle; the rest is dead weight.
        grouped.clear()

        # ----------------------------
        # Step 3 - Crossing pre-filters (last legality check)
        # Barrier check runs first so the subsequent check against existing
        # features only processes survivors.  The trimmed connector cache built
        # by _find_crossing_conflict_keys is reused in _run_kruskal.
        # ----------------------------
        _crossing_trim = 2.0 * float(self.connectivity_tolerance_meters)
        _crossing_sr = (
            arcpy.SpatialReference(self.crossing_check_spatial_reference)
            if self.crossing_check_spatial_reference is not None
            else None
        )

        def _apply_crossing_filter(
            reject_keys: set[tuple[int, str, int]], reason: str
        ) -> None:
            for _dangle_oid in list(legal_rows_by_dangle.keys()):
                _parent_id = parent_id_by_dangle[_dangle_oid]
                _remaining: list[NearCandidate] = []
                for _cand in legal_rows_by_dangle[_dangle_oid]:
                    _cand_key = (_dangle_oid, _cand.near_fc_key, _cand.near_fid)
                    if _cand_key in reject_keys:
                        if collect_diags:
                            _step1a_illegal.append(
                                _CandidateIllegalA(
                                    _dangle_oid, _parent_id, _cand, reason
                                )
                            )
                    else:
                        _remaining.append(_cand)
                if _remaining:
                    legal_rows_by_dangle[_dangle_oid] = _remaining
                else:
                    del legal_rows_by_dangle[_dangle_oid]
                    parent_id_by_dangle.pop(_dangle_oid, None)

        if self.barrier_layers and legal_rows_by_dangle and _crossing_sr is not None:
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _find_barrier_crossing_keys START (legal_dangles={len(legal_rows_by_dangle)})")  # [DBG_LINEGAP]
            _barrier_keys = self._find_barrier_crossing_keys(
                legal_rows_by_dangle=legal_rows_by_dangle,
                dangle_xy=dangle_xy,
                barrier_layers=self.barrier_layers,
                trim_distance=_crossing_trim,
                spatial_reference=_crossing_sr,
            )
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _find_barrier_crossing_keys END (rejected_keys={len(_barrier_keys)})")  # [DBG_LINEGAP]
            if _barrier_keys:
                _apply_crossing_filter(_barrier_keys, "crosses_barrier_layer")

        trimmed_connector_cache: dict[tuple[int, str, int], Any] = {}
        if (
            self.reject_crossing_connectors
            and legal_rows_by_dangle
            and _crossing_sr is not None
        ):
            # self-lines (lines_copy) plus every connect_to_features layer
            # eligible for the line-vs-line crossing pre-filter.  Polygon
            # sources have already been converted to their boundary polyline
            # in _build_external_target_layers_once so a single uniform path
            # applies here.
            _check_layers: list[str] = [
                self.lines_copy,
                *self.external_target_crossing_layers,
            ]
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _find_crossing_conflict_keys START (legal_dangles={len(legal_rows_by_dangle)}, check_layers={len(_check_layers)})")  # [DBG_LINEGAP]
            crossing_conflict_keys, trimmed_connector_cache = (
                self._find_crossing_conflict_keys(
                    legal_rows_by_dangle=legal_rows_by_dangle,
                    dangle_xy=dangle_xy,
                    check_feature_layers=_check_layers,
                    trim_distance=_crossing_trim,
                    spatial_reference=_crossing_sr,
                )
            )
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _find_crossing_conflict_keys END (rejected_keys={len(crossing_conflict_keys)}, trimmed_cache={len(trimmed_connector_cache)})")  # [DBG_LINEGAP]
            if crossing_conflict_keys:
                _apply_crossing_filter(
                    crossing_conflict_keys, "crosses_existing_feature"
                )

        if not legal_rows_by_dangle:
            return _empty_result(
                _DiagnosticsState(step1a_illegal=_step1a_illegal),
            )

        # ----------------------------
        # Step 4 - Best line parent per dangle (angle-aware)
        # Used by edge-case bonus detection in the scoring step.
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _compute_best_line_parent_by_dangle START (legal_dangles={len(legal_rows_by_dangle)})")  # [DBG_LINEGAP]
        best_line_parent_by_dangle = self._compute_best_line_parent_by_dangle(
            legal_rows_by_dangle=legal_rows_by_dangle,
            parent_id_by_dangle=parent_id_by_dangle,
            dangle_xy=dangle_xy,
            dangle_parent=dangle_parent,
            dangles_key=dangles_key,
            lines_key=lines_key,
            polyline_by_parent=polyline_by_parent,
            polyline_by_external=polyline_by_external,
            polyline_by_segment=polyline_by_segment,
            is_external_line_like=is_external_line_like,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _compute_best_line_parent_by_dangle END (best_line_parents={len(best_line_parent_by_dangle)})")  # [DBG_LINEGAP]

        # ----------------------------
        # Step 5 - Angle-aware selection: one proposal per dangle
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _select_dangle_proposals START (legal_dangles={len(legal_rows_by_dangle)})")  # [DBG_LINEGAP]
        _dangle_proposals, dangle_norm_z_by_dangle, _step1b_illegal, _step1b_scored = (
            self._select_dangle_proposals(
                legal_rows_by_dangle=legal_rows_by_dangle,
                parent_id_by_dangle=parent_id_by_dangle,
                dangle_xy=dangle_xy,
                dangles_key=dangles_key,
                lines_key=lines_key,
                line_like_ds_keys=line_like_ds_keys,
                line_like_external_ds_keys=line_like_external_ds_keys,
                base_tol=base_tol,
                polyline_by_parent=polyline_by_parent,
                polyline_by_external=polyline_by_external,
                polyline_by_segment=polyline_by_segment,
                is_external_line_like=is_external_line_like,
                best_line_parent_by_dangle=best_line_parent_by_dangle,
                dangle_parent=dangle_parent,
                topology=topology,
                collect_diags=collect_diags,
                dist_to_parent_line_by_dangle=dist_to_parent_line_by_dangle,
            )
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _select_dangle_proposals END (proposals={len(_dangle_proposals)}, illegal_b={len(_step1b_illegal)}, scored_b={len(_step1b_scored)})")  # [DBG_LINEGAP]

        if not _dangle_proposals:
            return _empty_result(
                _DiagnosticsState(
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                ),
            )

        # ============================
        # NETWORK SCOPE
        # Resolves one winner per undirected A<->B connection group.
        # ============================

        # ----------------------------
        # Step 1 - Mutual detection (for labeling)
        # - dangle mutual pairs: D1 targets D2 AND D2 targets D1 (both dangle targets)
        # - network mutual: any proposal exists in both directions between the two network nodes
        # ----------------------------
        active: list[_DangleProposal] = list(_dangle_proposals.values())
        if not active:
            return _empty_result(
                _DiagnosticsState(
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                ),
            )
        active_by_dangle = {int(p.ctx.dangle_oid): p for p in active}

        dangle_mutual_oids: set[int] = set()
        for p in active:
            if p.ctx.target_dangle_oid is None:
                continue
            q = active_by_dangle.get(int(p.ctx.target_dangle_oid))
            if q is None or q.ctx.target_dangle_oid is None:
                continue
            if int(q.ctx.target_dangle_oid) == int(p.ctx.dangle_oid):
                dangle_mutual_oids.add(int(p.ctx.dangle_oid))
                dangle_mutual_oids.add(int(q.ctx.dangle_oid))

        directed_network_edges: set[tuple[EntityKey, EntityKey]] = {
            (p.ctx.src_node, p.ctx.tgt_node) for p in active
        }

        # ----------------------------
        # Step 2 - Connection normalization: re-normalize Z within each undirected A<->B connection group
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_connection_normalization START (dangle_proposals={len(_dangle_proposals)})")  # [DBG_LINEGAP]
        connection_proposals_by_dangle, connection_norm_z_by_dangle = (
            self._run_connection_normalization(_dangle_proposals)
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_connection_normalization END (proposals={len(connection_proposals_by_dangle)})")  # [DBG_LINEGAP]

        # ----------------------------
        # Step 3 - Connection selection: one winner per undirected connection
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_connection_selection START")  # [DBG_LINEGAP]
        _connection_proposals, connection_loser_oids = self._run_connection_selection(
            connection_proposals_by_dangle=connection_proposals_by_dangle,
            directed_edges=directed_network_edges,
            dangle_mutual_oids=dangle_mutual_oids,
            collect_diags=collect_diags,
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_connection_selection END (winners={len(_connection_proposals)}, losers={len(connection_loser_oids)})")  # [DBG_LINEGAP]

        # ============================
        # KRUSKAL SCOPE
        # Cycle prevention + crossing recheck across all connection winners.
        # ============================

        # ----------------------------
        # Step 1 - Global normalization: re-normalize Z across all connection winners
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_global_normalization START (connection_proposals={len(_connection_proposals)})")  # [DBG_LINEGAP]
        _global_winners, global_norm_z_by_dangle = self._run_global_normalization(
            _connection_proposals
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_global_normalization END (global_winners={len(_global_winners)})")  # [DBG_LINEGAP]

        # ----------------------------
        # Step 2 - Kruskal cycle prevention across accepted connections
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_kruskal START")  # [DBG_LINEGAP]
        (
            _global_proposals,
            accepted_dangle_oids,
            kruskal_rejected_oids,
            kruskal_crossing_rejected_oids,
            gap_source_by_dangle,
            accepted_connector_raw,
            kruskal_rank_by_dangle_oid,
        ) = self._run_kruskal(
            global_winners=_global_winners,
            topology=topology,
            collect_diags=collect_diags,
            trimmed_connector_cache=trimmed_connector_cache,
            crossing_spatial_reference=(
                arcpy.SpatialReference(self.crossing_check_spatial_reference)
                if self.reject_crossing_connectors
                else None
            ),
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _run_kruskal END (accepted={len(accepted_dangle_oids)}, kruskal_rejected={len(kruskal_rejected_oids)}, crossing_rejected={len(kruskal_crossing_rejected_oids)})")  # [DBG_LINEGAP]

        # Eager release: trimmed_connector_cache is consumed by _run_kruskal
        # and not referenced by resnap or output phases; release the Polyline
        # handles before the deferred scope and the diagnostics assembly run.
        trimmed_connector_cache.clear()

        if not _global_proposals:
            return _empty_result(
                _DiagnosticsState(
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    connection_loser_oids=connection_loser_oids,
                    kruskal_rejected_oids=kruskal_rejected_oids,
                    kruskal_crossing_rejected_oids=kruskal_crossing_rejected_oids,
                    accepted_dangle_oids=accepted_dangle_oids,
                    gap_source_by_dangle=gap_source_by_dangle,
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                    connection_norm_z_by_dangle=connection_norm_z_by_dangle,
                    global_norm_z_by_dangle=global_norm_z_by_dangle,
                ),
            )

        # ============================
        # DEFERRED SCOPE
        # Resolved later in run() after _apply_plan + _resnap_connections.
        # ============================

        # ----------------------------
        # Step 1 - Resnap candidate identification
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _identify_resnap_captures START (global_proposals={len(_global_proposals)})")  # [DBG_LINEGAP]
        resnap_captures = self._identify_resnap_captures(_global_proposals)
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _identify_resnap_captures END (resnap_captures={len(resnap_captures)})")  # [DBG_LINEGAP]

        # ----------------------------
        # Step 2 - Plan entry assembly: parent_id -> list[plan_entry]
        # ----------------------------
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _assemble_plan_entries START")  # [DBG_LINEGAP]
        plan_by_parent = self._assemble_plan_entries(_global_proposals)
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _assemble_plan_entries END (plan_parents={len(plan_by_parent)})")  # [DBG_LINEGAP]

        return BuildPlanResult(
            plan_by_parent=plan_by_parent,
            resnap_captures=resnap_captures,
            diagnostics=_build_diagnostics(
                _DiagnosticsState(
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    connection_loser_oids=connection_loser_oids,
                    kruskal_rejected_oids=kruskal_rejected_oids,
                    kruskal_crossing_rejected_oids=kruskal_crossing_rejected_oids,
                    accepted_dangle_oids=accepted_dangle_oids,
                    gap_source_by_dangle=gap_source_by_dangle,
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                    connection_norm_z_by_dangle=connection_norm_z_by_dangle,
                    global_norm_z_by_dangle=global_norm_z_by_dangle,
                ),
            ),
            accepted_connector_raw=accepted_connector_raw,
            kruskal_rank_by_dangle_oid=kruskal_rank_by_dangle_oid,
        )

    def _filter_legal_candidates(
        self,
        *,
        grouped: dict[DangleOid, list[NearCandidate]],
        dangle_parent: dict[DangleOid, ParentId],
        illegal: _IllegalTargets,
        dangles_key: DatasetKey,
        lines_key: DatasetKey,
        line_like_ds_keys: set[DatasetKey],
        base_tol: float,
        dangle_tol: float,
        topology: TopologyModel,
        collect_diags: bool,
        directed_source_illegal_oids: set[DangleOid],
    ) -> tuple[
        dict[DangleOid, list[NearCandidate]],
        dict[DangleOid, ParentId],
        list[_CandidateIllegalA],
    ]:
        """Dangle filtering: collect legal candidates per dangle.

        Returns (legal_rows_by_dangle, parent_id_by_dangle, step1a_illegal).
        """
        legal_rows_by_dangle: dict[DangleOid, list[NearCandidate]] = {}
        parent_id_by_dangle: dict[DangleOid, ParentId] = {}
        _step1a_illegal: list[_CandidateIllegalA] = []

        for dangle_oid in sorted(grouped.keys()):
            candidates = grouped[dangle_oid]
            dangle_oid = int(dangle_oid)

            parent_id = dangle_parent.get(dangle_oid)
            if parent_id is None:
                continue
            parent_id = int(parent_id)

            # In directed mode, start-node dangles cannot be gap-fill sources.
            # A connector from a start node would run antiparallel to the source line.
            if dangle_oid in directed_source_illegal_oids:
                if collect_diags:
                    for cand in candidates:
                        if cand.near_fc_key == lines_key and cand.near_fid == parent_id:
                            continue
                        _step1a_illegal.append(
                            _CandidateIllegalA(
                                dangle_oid, parent_id, cand, "directed_start_node"
                            )
                        )
                continue

            rows = sorted(candidates, key=self._candidate_sort_key)

            legal_rows: list[NearCandidate] = []
            for cand in rows:
                # Self-parent candidates are excluded from the plan and from diagnostics.
                if cand.near_fc_key == lines_key and cand.near_fid == parent_id:
                    continue

                is_legal = self._candidate_is_legal(
                    illegal=illegal,
                    dangle_parent=dangle_parent,
                    dangles_fc_key=dangles_key,
                    lines_fc_key=lines_key,
                    line_like_ds_keys=line_like_ds_keys,
                    parent_id=parent_id,
                    cand=cand,
                    base_tol=base_tol,
                    dangle_candidate_tol=dangle_tol,
                    topology=topology,
                )
                if is_legal:
                    legal_rows.append(cand)
                elif collect_diags:
                    reason = self._candidate_rejection_reason(
                        illegal=illegal,
                        dangle_parent=dangle_parent,
                        dangles_fc_key=dangles_key,
                        lines_fc_key=lines_key,
                        line_like_ds_keys=line_like_ds_keys,
                        parent_id=parent_id,
                        cand=cand,
                        base_tol=base_tol,
                        dangle_candidate_tol=dangle_tol,
                        topology=topology,
                    )
                    _step1a_illegal.append(
                        _CandidateIllegalA(dangle_oid, parent_id, cand, reason)
                    )

            if not legal_rows:
                continue

            legal_rows_by_dangle[dangle_oid] = legal_rows
            parent_id_by_dangle[dangle_oid] = parent_id

        return legal_rows_by_dangle, parent_id_by_dangle, _step1a_illegal

    def _select_dangle_proposals(
        self,
        *,
        legal_rows_by_dangle: dict[DangleOid, list[NearCandidate]],
        parent_id_by_dangle: dict[DangleOid, ParentId],
        dangle_xy: dict[DangleOid, tuple[float, float]],
        dangles_key: DatasetKey,
        lines_key: DatasetKey,
        line_like_ds_keys: set[DatasetKey],
        line_like_external_ds_keys: set[DatasetKey],
        base_tol: float,
        polyline_by_parent: dict[ParentId, Any],
        polyline_by_external: dict[DatasetKey, dict[int, Any]],
        polyline_by_segment: dict[DatasetKey, dict[int, Any]],
        is_external_line_like: dict[DatasetKey, bool],
        best_line_parent_by_dangle: dict[DangleOid, ParentId],
        dangle_parent: dict[DangleOid, ParentId],
        topology: TopologyModel,
        collect_diags: bool,
        dist_to_parent_line_by_dangle: Optional[
            dict[DangleOid, dict[ParentId, float]]
        ] = None,
    ) -> tuple[
        dict[DangleOid, _DangleProposal],
        _NormZByDangle,
        list[_CandidateIllegalB],
        list[_CandidateScored],
    ]:
        """Dangle selection: choose one proposal per dangle using angle-aware scoring.

        Returns (_dangle_proposals, dangle_norm_z_by_dangle, step1b_illegal, step1b_scored).
        """
        _dangle_proposals: dict[DangleOid, _DangleProposal] = {}
        dangle_norm_z_by_dangle: _NormZByDangle = {}
        _step1b_illegal: list[_CandidateIllegalB] = []
        _step1b_scored: list[_CandidateScored] = []

        for dangle_oid in sorted(legal_rows_by_dangle.keys()):
            dangle_oid = int(dangle_oid)
            parent_id = int(parent_id_by_dangle[dangle_oid])
            legal_rows = legal_rows_by_dangle[dangle_oid]

            xy = dangle_xy.get(dangle_oid)
            if xy is None:
                continue
            d_x, d_y = xy

            # Source line angle (local at the dangle XY)
            src_poly = polyline_by_parent.get(int(parent_id))
            src_angle = None
            if src_poly is not None:
                src_angle = self._local_line_angle_cached(
                    dataset_key=lines_key,  # canonical lines key
                    oid=int(parent_id),  # ORIGINAL_ID space for parent lines
                    polyline=src_poly,
                    x=float(d_x),
                    y=float(d_y),
                )

            # ----------------------------
            # Z setup for this dangle
            # ----------------------------
            # start_z is fixed for all candidates of this dangle.
            start_z: Optional[float] = None
            if self._raster_handles:
                start_z = geometry_tools.local_z_at_xy(
                    self._raster_handles, float(d_x), float(d_y)
                )

            # Pre-scan end_z.  Run when Z scoring is active OR when diagnostic
            # output is requested so z values are available for all candidate rows.
            end_z_by_cand_index: dict[int, Optional[float]] = {}
            z_score_min: Optional[float] = None
            z_score_max: Optional[float] = None

            if self._raster_handles and (
                float(self.best_fit_weights.z) > 0.0 or collect_diags
            ):
                for _i, _c in enumerate(legal_rows):
                    _ez = geometry_tools.local_z_at_xy(
                        self._raster_handles,
                        _c.near_x,
                        _c.near_y,
                    )
                    end_z_by_cand_index[_i] = _ez

                if float(self.best_fit_weights.z) > 0.0:
                    _valid_z = [
                        z for z in end_z_by_cand_index.values() if z is not None
                    ]
                    if _valid_z:
                        z_score_min = min(_valid_z)
                        z_score_max = max(_valid_z)

            # Build a mapping from parent line ID -> list of dangle XY coords.
            # Used in _assess_angle to detect when a line candidate is hit at a
            # dangle endpoint, so it can be scored with directional semantics.
            _dangle_xys_by_parent: _DangleXYsByParent = {}
            for _d_oid, _d_parent in dangle_parent.items():
                _d_xy = dangle_xy.get(_d_oid)
                if _d_xy is not None:
                    _dangle_xys_by_parent.setdefault(int(_d_parent), []).append(_d_xy)

            # Per-dangle slice of the global parent-line distance lookup; the
            # caller already chose to materialise the global table only when
            # connector_angle_diff_required_above_meters is set.
            dist_to_parent_line_by_id = (
                dist_to_parent_line_by_dangle.get(dangle_oid)
                if dist_to_parent_line_by_dangle is not None
                else None
            )

            scored_candidates: list[_ScoredCandidateItem] = []

            for _cand_idx, cand in enumerate(legal_rows):
                assess = self._assess_angle(
                    src_parent_id=int(parent_id),
                    dangle_x=float(d_x),
                    dangle_y=float(d_y),
                    src_angle_deg=src_angle,
                    cand=cand,
                    dangles_fc_key=dangles_key,
                    lines_fc_key=lines_key,
                    dangle_parent=dangle_parent,
                    dangle_xy=dangle_xy,
                    polyline_by_parent=polyline_by_parent,
                    polyline_by_external=polyline_by_external,
                    polyline_by_segment=polyline_by_segment,
                    is_external_line_like=is_external_line_like,
                    dangle_xys_by_parent=_dangle_xys_by_parent,
                    dist_to_parent_line_by_id=dist_to_parent_line_by_id,
                )

                _cand_end_z: Optional[float] = end_z_by_cand_index.get(_cand_idx)

                # 1) Candidate blocking (angle_block_threshold_degrees)
                if assess.blocks:
                    if collect_diags:
                        _step1b_illegal.append(
                            _CandidateIllegalB(
                                dangle_oid,
                                parent_id,
                                cand,
                                assess,
                                "blocked_by_angle",
                                start_z,
                                _cand_end_z,
                            )
                        )
                    continue

                # 2) Expanded tolerance gating (angle_extra_dangle_threshold_degrees)
                # Applies to dangle targets and line-like targets that are only in range
                # because of the expanded tolerance — angle must permit extra-dangle behavior.
                is_dangle_target = cand.near_fc_key == dangles_key
                is_line_like_target = cand.near_fc_key in line_like_ds_keys
                dist = cand.near_dist

                if (
                    (is_dangle_target or is_line_like_target)
                    and dist > float(base_tol)
                    and not bool(assess.allow_extra_dangle)
                ):
                    if collect_diags:
                        _step1b_illegal.append(
                            _CandidateIllegalB(
                                dangle_oid,
                                parent_id,
                                cand,
                                assess,
                                "expanded_dangle_angle_disallowed",
                                start_z,
                                _cand_end_z,
                            )
                        )
                    continue

                # 3) Z drop gate (z_drop_threshold)
                if self.z_drop_threshold is not None and start_z is not None:
                    _end_z_gate = (
                        _cand_end_z
                        if _cand_end_z is not None
                        else geometry_tools.local_z_at_xy(
                            self._raster_handles,
                            cand.near_x,
                            cand.near_y,
                        )
                    )
                    if (
                        _end_z_gate is not None
                        and (_end_z_gate - start_z) > self.z_drop_threshold
                    ):
                        if collect_diags:
                            _step1b_illegal.append(
                                _CandidateIllegalB(
                                    dangle_oid,
                                    parent_id,
                                    cand,
                                    assess,
                                    "blocked_by_z_drop",
                                    start_z,
                                    _cand_end_z,
                                )
                            )
                        continue

                # 4) Edge-case bonus eligibility is angle-controlled (and conservative when
                # angle missing). Only dangle targets can receive the bonus.
                bonus_allowed = True
                if is_dangle_target:
                    # conservative policy: if angle is unavailable => no expanded behavior, no bonus
                    bonus_allowed = bool(assess.available) and bool(
                        assess.allow_extra_dangle
                    )

                raw_distance, effective_distance, bonus_applied = (
                    self._candidate_score_details(
                        dangle_oid=dangle_oid,
                        parent_id=parent_id,
                        cand=cand,
                        dangles_fc_key=dangles_key,
                        dangle_parent=dangle_parent,
                        best_line_parent_by_dangle=best_line_parent_by_dangle,
                        bonus_allowed=bool(bonus_allowed),
                    )
                )
                bonus_rank = 0 if bonus_applied else 1

                # 5) Normalized weighted composite score (dangle scope)
                _tol = float(self.gap_tolerance_meters) or 1.0
                _eff_norm_dist = float(effective_distance) / _tol

                _norm_z: Optional[float] = None
                if z_score_min is not None and z_score_max is not None:
                    _ez = end_z_by_cand_index.get(_cand_idx)
                    if _ez is not None:
                        if z_score_max > z_score_min:
                            _norm_z = (_ez - z_score_min) / (z_score_max - z_score_min)
                        else:
                            _norm_z = None  # flat range: Z cannot discriminate

                effective_for_scoring = self._compute_best_fit_score(
                    norm_dist=_eff_norm_dist,
                    assess=assess,
                    norm_z=_norm_z,
                )

                _norm_angle: Optional[float] = (
                    float(assess.angle_metric_deg) / float(assess.angle_max_deg)
                    if assess.angle_metric_deg is not None
                    else None
                )

                dangle_score = _ProposalScore(
                    composite=float(effective_for_scoring),
                    bonus_rank=int(bonus_rank),
                    norm_dist=_eff_norm_dist,
                    norm_angle=_norm_angle,
                    norm_z=_norm_z,
                )

                scored_candidates.append(
                    _ScoredCandidateItem(
                        score=dangle_score,
                        cand=cand,
                        raw_distance=float(raw_distance),
                        effective_for_scoring=float(effective_for_scoring),
                        bonus_applied=bool(bonus_applied),
                        assess=assess,
                        norm_z=_norm_z,
                        norm_dist=_eff_norm_dist,
                        norm_angle=_norm_angle,
                        end_z=end_z_by_cand_index.get(_cand_idx),
                    )
                )

            if not scored_candidates:
                continue

            winner_item = min(
                scored_candidates,
                key=lambda item: (
                    item.score.composite,
                    item.score.bonus_rank,
                    item.raw_distance,
                ),
            )
            winner_dangle_score = winner_item.score
            chosen = winner_item.cand
            raw_distance = winner_item.raw_distance
            bonus_applied = winner_item.bonus_applied
            chosen_assess = winner_item.assess
            winner_norm_z = winner_item.norm_z
            winner_end_z = winner_item.end_z

            if collect_diags:
                for sc_item in scored_candidates:
                    _step1b_scored.append(
                        _CandidateScored(
                            dangle_oid=dangle_oid,
                            parent_id=parent_id,
                            cand=sc_item.cand,
                            assess=sc_item.assess,
                            raw_distance=float(sc_item.raw_distance),
                            best_fit=float(sc_item.effective_for_scoring),
                            bonus=bool(sc_item.bonus_applied),
                            is_local_winner=sc_item is winner_item,
                            score_tuple=(
                                sc_item.score.composite,
                                sc_item.score.bonus_rank,
                                sc_item.raw_distance,
                            ),
                            norm_dist=float(sc_item.norm_dist),
                            norm_angle=sc_item.norm_angle,
                            dangle_norm_z=sc_item.norm_z,
                            start_z=start_z,
                            end_z=sc_item.end_z,
                        )
                    )

            # ----------------------------
            # _DangleProposal construction
            # ----------------------------
            src_node = self._node_for_parent(parent_id=parent_id, topology=topology)

            target_parent_id: Optional[int] = None
            target_dangle_oid: Optional[int] = None

            ds_key = str(chosen.near_fc_key)
            near_fid = int(chosen.near_fid)

            if ds_key == dangles_key:
                target_dangle_oid = near_fid
                other_parent = dangle_parent.get(int(target_dangle_oid))
                if other_parent is None:
                    continue
                target_parent_id = int(other_parent)
                tgt_node = self._node_for_parent(
                    parent_id=target_parent_id,
                    topology=topology,
                )

            elif ds_key == lines_key:
                target_parent_id = near_fid  # already in ORIGINAL_ID space
                tgt_node = self._node_for_parent(
                    parent_id=target_parent_id,
                    topology=topology,
                )

            else:
                tgt_node = self._node_for_optional_candidate(
                    dataset_key=ds_key,
                    near_fid=near_fid,
                )

            pair_key = self._unordered_pair_key(src_node, tgt_node)
            _tol_for_ctx = float(self.gap_tolerance_meters) or 1.0

            ctx = _CandidateContext(
                dangle_oid=dangle_oid,
                src_parent_id=parent_id,
                src_node=src_node,
                tgt_node=tgt_node,
                pair_key=pair_key,
                target_parent_id=target_parent_id,
                target_dangle_oid=target_dangle_oid,
                near_fc_key=ds_key,
                near_fid=near_fid,
                dangle_x=float(d_x),
                dangle_y=float(d_y),
                near_x=chosen.near_x,
                near_y=chosen.near_y,
                raw_distance=float(raw_distance),
                bonus_applied=bool(bonus_applied),
                start_z=start_z,
                end_z=winner_end_z,
                norm_dist=float(raw_distance) / _tol_for_ctx,
                assess=chosen_assess,
            )

            _dangle_proposals[dangle_oid] = _DangleProposal(
                ctx=ctx, score=winner_dangle_score
            )
            dangle_norm_z_by_dangle[dangle_oid] = winner_norm_z

        return (
            _dangle_proposals,
            dangle_norm_z_by_dangle,
            _step1b_illegal,
            _step1b_scored,
        )

    def _run_connection_normalization(
        self,
        dangle_proposals: dict[DangleOid, _DangleProposal],
    ) -> tuple[dict[DangleOid, _ConnectionProposal], _NormZByDangle]:
        """Connection normalization: re-normalize Z within each undirected A↔B connection group.

        Returns (connection_proposals_by_dangle, connection_norm_z_by_dangle).
        """
        active = list(dangle_proposals.values())
        _by_connection_for_normalization: dict[tuple, list[_DangleProposal]] = {}
        for p in active:
            _by_connection_for_normalization.setdefault(p.ctx.pair_key, []).append(p)

        connection_proposals_by_dangle: dict[DangleOid, _ConnectionProposal] = {}
        connection_norm_z_by_dangle: _NormZByDangle = {}
        for _pair_group in _by_connection_for_normalization.values():
            _group_end_z = [p.ctx.end_z for p in _pair_group]
            for p in _pair_group:
                net_norm_z = self._normalize_z_within(_group_end_z, p.ctx.end_z)
                net_score = _ProposalScore(
                    composite=self._compute_best_fit_score(
                        norm_dist=p.score.norm_dist,
                        assess=p.ctx.assess,
                        norm_z=net_norm_z,
                    ),
                    bonus_rank=p.score.bonus_rank,
                    norm_dist=p.score.norm_dist,
                    norm_angle=p.score.norm_angle,
                    norm_z=net_norm_z,
                )
                connection_proposals_by_dangle[int(p.ctx.dangle_oid)] = (
                    _ConnectionProposal.from_dangle(p, score=net_score)
                )
                connection_norm_z_by_dangle[int(p.ctx.dangle_oid)] = net_norm_z

        return connection_proposals_by_dangle, connection_norm_z_by_dangle

    def _run_connection_selection(
        self,
        *,
        connection_proposals_by_dangle: dict[DangleOid, _ConnectionProposal],
        directed_edges: set[tuple[EntityKey, EntityKey]],
        dangle_mutual_oids: set[DangleOid],
        collect_diags: bool,
    ) -> tuple[list[_ConnectionProposal], set[DangleOid]]:
        """Connection selection: one winner per undirected connection.

        Stamps the authoritative gap_source onto each winner via dataclasses.replace
        before returning; all returned proposals have gap_source non-None.

        Returns (_connection_proposals, connection_loser_oids).
        """
        by_connection: dict[tuple, list[_ConnectionProposal]] = {}
        for p in connection_proposals_by_dangle.values():
            by_connection.setdefault(p.ctx.pair_key, []).append(p)

        _connection_proposals: list[_ConnectionProposal] = []
        for pair_key in sorted(by_connection.keys()):
            group = by_connection[pair_key]
            winner = min(group, key=lambda pr: pr.sort_key())

            a_node, b_node = pair_key
            mutual_network = (a_node, b_node) in directed_edges and (
                b_node,
                a_node,
            ) in directed_edges

            if (
                winner.ctx.target_dangle_oid is not None
                and int(winner.ctx.dangle_oid) in dangle_mutual_oids
            ):
                gap_source = GapSource.PAIR_DANGLE
            elif mutual_network:
                gap_source = GapSource.PAIR_LINE
            else:
                gap_source = GapSource.DEFAULT

            _connection_proposals.append(replace(winner, gap_source=gap_source))

        connection_loser_oids: set[DangleOid] = set()
        if collect_diags:
            _stage_a_winner_oids = {
                int(prop.ctx.dangle_oid) for prop in _connection_proposals
            }
            connection_loser_oids.update(
                int(p.ctx.dangle_oid)
                for p in connection_proposals_by_dangle.values()
                if int(p.ctx.dangle_oid) not in _stage_a_winner_oids
            )

        return _connection_proposals, connection_loser_oids

    def _run_global_normalization(
        self,
        connection_proposals: list[_ConnectionProposal],
    ) -> tuple[list[_GlobalProposal], _NormZByDangle]:
        """Global normalization: re-normalize Z across all connection winners.

        Returns (_global_winners, global_norm_z_by_dangle).
        """
        _all_end_z_global = [p.ctx.end_z for p in connection_proposals]
        _global_winners: list[_GlobalProposal] = []
        global_norm_z_by_dangle: _NormZByDangle = {}
        for n_prop in connection_proposals:
            glob_norm_z = self._normalize_z_within(_all_end_z_global, n_prop.ctx.end_z)
            glob_score = _ProposalScore(
                composite=self._compute_best_fit_score(
                    norm_dist=n_prop.score.norm_dist,
                    assess=n_prop.ctx.assess,
                    norm_z=glob_norm_z,
                ),
                bonus_rank=n_prop.score.bonus_rank,
                norm_dist=n_prop.score.norm_dist,
                norm_angle=n_prop.score.norm_angle,
                norm_z=glob_norm_z,
            )
            g_prop = _GlobalProposal.from_network(n_prop, score=glob_score)
            _global_winners.append(g_prop)
            global_norm_z_by_dangle[int(n_prop.ctx.dangle_oid)] = glob_norm_z

        return _global_winners, global_norm_z_by_dangle

    def _run_kruskal(
        self,
        *,
        global_winners: list[_GlobalProposal],
        topology: TopologyModel,
        collect_diags: bool,
        trimmed_connector_cache: dict[tuple[int, str, int], Any],
        crossing_spatial_reference: Any,  # arcpy.SpatialReference | None
    ) -> tuple[
        list[_GlobalProposal],
        set[DangleOid],  # accepted_dangle_oids
        set[DangleOid],  # kruskal_rejected_oids (cycle-based)
        set[DangleOid],  # kruskal_crossing_rejected_oids
        dict[DangleOid, GapSource],  # gap_source_by_dangle
        list[
            AcceptedConnectorRaw
        ],  # accepted_connector_raw (for resnap crossing re-check)
        dict[DangleOid, int],  # kruskal_rank_by_dangle_oid
    ]:
        """Global selection: Kruskal cycle prevention across accepted connections.

        Candidates are processed in score order (best first).  Two rejection
        reasons exist:
          - Cycle rejection: UF finds src_node and tgt_node already in the same
            component (reason: lost_kruskal_selection).
          - Crossing rejection (when reject_crossing_connectors is True): the
            candidate's trimmed connector is within connectivity_tolerance_meters
            of an already-accepted candidate's trimmed connector
            (reason: crosses_accepted_connector).

        Crossing uses a single pre-loop CROSSES relationship check of all candidate
        trimmed connectors against themselves to build a conflict lookup.  During the
        loop, _crossing_blocked consults that lookup instead of running live geometry
        checks.

        Note on deferred displacement inaccuracy:
            When a deferred connector's (resnap capture's) final geometry causes
            a previously accepted connector to be displaced during the resnap
            re-check (see _recheck_resnap_crossings), the Union-Find state built
            here becomes stale.  Both are accepted inaccuracies — the scenario is
            rare enough that a full mock-Kruskal + mock-deferred pass is not
            justified.

        Returns (proposals, accepted_dangle_oids, kruskal_rejected_oids,
                 kruskal_crossing_rejected_oids, gap_source_by_dangle,
                 accepted_connector_raw, kruskal_rank_by_dangle_oid).
        """
        reject_crossing = crossing_spatial_reference is not None
        scope = topology.scope
        _global_proposals: list[_GlobalProposal] = []
        kruskal_crossing_rejected_oids: set[DangleOid] = set()
        accepted_keys: set[tuple[int, str, int]] = set()
        accepted_connector_raw: list[AcceptedConnectorRaw] = []
        kruskal_rank_by_dangle_oid: dict[DangleOid, int] = {}
        rank_counter = 0

        # --- Pre-loop: build candidate-vs-candidate conflict lookup ---
        conflict_lookup: dict[tuple[int, str, int], set[tuple[int, str, int]]] = {}
        if reject_crossing:
            _kruskal_cands: list[tuple[tuple[int, str, int], Any]] = []
            for prop in global_winners:
                _key = (
                    int(prop.ctx.dangle_oid),
                    str(prop.ctx.near_fc_key),
                    int(prop.ctx.near_fid),
                )
                _trimmed = trimmed_connector_cache.get(_key)
                if _trimmed is not None:
                    _kruskal_cands.append((_key, _trimmed))

            if _kruskal_cands:
                _kruskal_fc = "memory/crossing_check_kruskal_cands"
                _kruskal_oid_to_key = self._write_trimmed_cands_fc(
                    cands_with_keys=_kruskal_cands,
                    fc_path=_kruskal_fc,
                    spatial_reference=crossing_spatial_reference,
                )
                for _oid_in, _against_oids in self._find_crossing_pairs(
                    _kruskal_fc, [_kruskal_fc]
                ).items():
                    _key_in = _kruskal_oid_to_key.get(_oid_in)
                    if _key_in is None:
                        continue
                    for _oid_near in _against_oids:
                        _key_near = _kruskal_oid_to_key.get(_oid_near)
                        if _key_near is not None:
                            conflict_lookup.setdefault(_key_in, set()).add(_key_near)
                arcpy.management.Delete(_kruskal_fc)

        def _accept(prop: _GlobalProposal) -> None:
            nonlocal rank_counter
            _global_proposals.append(prop)
            if reject_crossing:
                rank_counter += 1
                d_oid = int(prop.ctx.dangle_oid)
                kruskal_rank_by_dangle_oid[d_oid] = rank_counter
                _key = (d_oid, str(prop.ctx.near_fc_key), int(prop.ctx.near_fid))
                accepted_keys.add(_key)
                accepted_connector_raw.append(
                    AcceptedConnectorRaw(
                        dangle_oid=d_oid,
                        dangle_x=float(prop.ctx.dangle_x),
                        dangle_y=float(prop.ctx.dangle_y),
                        near_x=float(prop.ctx.near_x),
                        near_y=float(prop.ctx.near_y),
                    )
                )

        def _crossing_blocked(prop: Any) -> bool:
            if not reject_crossing:
                return False
            key = (
                int(prop.ctx.dangle_oid),
                str(prop.ctx.near_fc_key),
                int(prop.ctx.near_fid),
            )
            if trimmed_connector_cache.get(key) is None:
                return False
            return bool(conflict_lookup.get(key, set()) & accepted_keys)

        if scope in (
            logic_config.ConnectivityScope.INPUT_LINES,
            logic_config.ConnectivityScope.ONE_DEGREE,
            logic_config.ConnectivityScope.TRANSITIVE,
        ):
            uf = _UnionFind()
            # Map topology ds_keys (from original connect_to_features paths) to the
            # candidate ds_keys (from work layer paths) so seeded nodes match tgt_node.
            topo_to_cand_ds_key: dict[str, str] = {
                self._dataset_key(orig): self._dataset_key(work)
                for orig, work in zip(
                    self.connect_to_features or [], self.external_target_layers
                )
            }
            for (ds_key, oid), cid in (
                topology.connectivity_id_by_optional or {}
            ).items():
                cand_ds_key = topo_to_cand_ds_key.get(ds_key, ds_key)
                uf.union(
                    ("component", int(cid)),
                    ("optional_candidate", str(cand_ds_key), int(oid)),
                )
            for prop in sorted(global_winners, key=lambda p: p.sort_key()):
                if uf.find(prop.ctx.src_node) == uf.find(prop.ctx.tgt_node):
                    continue
                if _crossing_blocked(prop):
                    kruskal_crossing_rejected_oids.add(int(prop.ctx.dangle_oid))
                    continue
                uf.union(prop.ctx.src_node, prop.ctx.tgt_node)
                _accept(prop)
        else:
            # NONE / DIRECT_CONNECTION: no cycle check, crossing check only.
            for prop in sorted(global_winners, key=lambda p: p.sort_key()):
                if _crossing_blocked(prop):
                    kruskal_crossing_rejected_oids.add(int(prop.ctx.dangle_oid))
                    continue
                _accept(prop)

        accepted_dangle_oids: set[DangleOid] = set()
        kruskal_rejected_oids: set[DangleOid] = set()
        gap_source_by_dangle: dict[DangleOid, GapSource] = {}
        if collect_diags and _global_proposals:
            _accepted_oids = {int(prop.ctx.dangle_oid) for prop in _global_proposals}
            accepted_dangle_oids.update(_accepted_oids)
            kruskal_rejected_oids.update(
                int(prop.ctx.dangle_oid)
                for prop in global_winners
                if int(prop.ctx.dangle_oid) not in _accepted_oids
                and int(prop.ctx.dangle_oid) not in kruskal_crossing_rejected_oids
            )
            gap_source_by_dangle.update(
                {
                    int(prop.ctx.dangle_oid): prop.gap_source
                    for prop in _global_proposals
                }
            )

        return (
            _global_proposals,
            accepted_dangle_oids,
            kruskal_rejected_oids,
            kruskal_crossing_rejected_oids,
            gap_source_by_dangle,
            accepted_connector_raw,
            kruskal_rank_by_dangle_oid,
        )

    def _identify_resnap_captures(
        self,
        global_proposals: list[_GlobalProposal],
    ) -> list[_ResnappedCapture]:
        """Identify connections whose near-point may need re-resolving after snap.

        A connection A→B needs resnap if:
          1. B is the target_parent_id of A's accepted connection
          2. Another accepted connection B→T exists with GapSource.PAIR_DANGLE
             (i.e. B's dangle endpoint will move when B snaps to T)
          3. A's near-point lies on B's last segment — checked in _resnap_connections
             using post-apply geometry (this block is a cheap pre-filter only).
        """
        snap_source_parents: set[ParentId] = {
            int(prop.ctx.src_parent_id)
            for prop in global_proposals
            if prop.gap_source is GapSource.PAIR_DANGLE
        }
        resnap_captures: list[_ResnappedCapture] = []
        for prop in global_proposals:
            tp = prop.ctx.target_parent_id
            if tp is None or int(tp) not in snap_source_parents:
                continue
            resnap_captures.append(
                _ResnappedCapture(
                    parent_id=int(prop.ctx.src_parent_id),
                    dangle_oid=int(prop.ctx.dangle_oid),
                    forced_target_parent=int(tp),
                    proposal=prop,
                    gap_source=prop.gap_source,
                )
            )
        return resnap_captures

    def _recheck_resnap_crossings(
        self,
        *,
        resnap_plan: dict[ParentId, PlanEntry],
        accepted_connector_raw: list[AcceptedConnectorRaw],
        kruskal_rank_by_dangle_oid: dict[DangleOid, int],
        trim_distance: float,
        spatial_reference: Any,
    ) -> tuple[
        dict[ParentId, PlanEntry], set[DangleOid], set[DangleOid], set[DangleOid]
    ]:
        """Re-check resnap captures against accepted connector geometries.

        Called after _resnap_connections resolves final geometry for deferred
        connectors.  Uses a spatial CROSSES relationship check (trimmed resnap
        connectors vs trimmed accepted connectors) as the source of truth for
        crossing conflicts, then applies rank-based conflict resolution:

          - If the resnap capture has a worse (higher) rank than the best-ranked
            conflicting accepted connector -> the resnap capture loses; its plan
            entry is marked skip=True so the corrected geometry is not applied.
          - If the resnap capture has a better (lower) rank -> it wins; the
            conflicting connector(s) are flagged as displaced. Their geometry is
            already applied to the feature class and is not reverted, so the
            displacement is recorded in diagnostics only.

        Returns (resnap_plan, resnap_crossing_rejected_oids,
                 resnap_crossing_displaced_oids, resnap_crossing_winner_oids).
        resnap_crossing_winner_oids contains dangle_oids of accepted connectors that
        won a conflict against a resnap capture (i.e. the resnap capture deferred to them).
        """
        if not accepted_connector_raw:
            return resnap_plan, set(), set(), set()

        # Build trimmed resnap connectors: key = parent_id (unique per resnap entry).
        resnap_cands: list[tuple[Any, Any]] = []
        for parent_id, entry in resnap_plan.items():
            if entry.skip:
                continue
            trimmed = self._build_trimmed_connector(
                from_x=entry.dangle_x,
                from_y=entry.dangle_y,
                to_x=entry.near_x,
                to_y=entry.near_y,
                trim_distance=trim_distance,
                spatial_reference=spatial_reference,
            )
            if trimmed is not None:
                resnap_cands.append((parent_id, trimmed))

        if not resnap_cands:
            return resnap_plan, set(), set(), set()

        # Build trimmed accepted connectors: key = dangle_oid.
        accepted_cands: list[tuple[Any, Any]] = []
        for acc in accepted_connector_raw:
            trimmed = self._build_trimmed_connector(
                from_x=acc.dangle_x,
                from_y=acc.dangle_y,
                to_x=acc.near_x,
                to_y=acc.near_y,
                trim_distance=trim_distance,
                spatial_reference=spatial_reference,
            )
            if trimmed is not None:
                accepted_cands.append((acc.dangle_oid, trimmed))

        if not accepted_cands:
            return resnap_plan, set(), set(), set()

        _resnap_fc = "memory/resnap_crossing_trimmed"
        _accepted_fc = "memory/resnap_crossing_accepted"

        oid_to_parent_id = self._write_trimmed_cands_fc(
            cands_with_keys=resnap_cands,
            fc_path=_resnap_fc,
            spatial_reference=spatial_reference,
        )
        oid_to_accepted_doid = self._write_trimmed_cands_fc(
            cands_with_keys=accepted_cands,
            fc_path=_accepted_fc,
            spatial_reference=spatial_reference,
        )

        # {parent_id: set of conflicting accepted dangle_oids}
        conflicts_by_parent: dict[ParentId, set[DangleOid]] = {}
        for rsnp_oid, acc_oids in self._find_crossing_pairs(
            _resnap_fc, [_accepted_fc]
        ).items():
            parent_id = oid_to_parent_id.get(rsnp_oid)
            if parent_id is None:
                continue
            for acc_oid in acc_oids:
                acc_doid = oid_to_accepted_doid.get(acc_oid)
                if acc_doid is not None:
                    conflicts_by_parent.setdefault(parent_id, set()).add(int(acc_doid))

        arcpy.management.Delete(_resnap_fc)
        arcpy.management.Delete(_accepted_fc)

        resnap_crossing_rejected_oids: set[DangleOid] = set()
        resnap_crossing_displaced_oids: set[DangleOid] = set()
        resnap_crossing_winner_oids: set[DangleOid] = set()

        for parent_id, entry in resnap_plan.items():
            if entry.skip:
                continue

            conflicting_doids = conflicts_by_parent.get(parent_id)
            if not conflicting_doids:
                continue

            dangle_oid = entry.dangle_oid
            resnap_rank = kruskal_rank_by_dangle_oid.get(dangle_oid, float("inf"))
            best_conflict_rank = min(
                kruskal_rank_by_dangle_oid.get(aoid, float("inf"))
                for aoid in conflicting_doids
            )

            if resnap_rank <= best_conflict_rank:
                # Resnap capture wins: displace the conflicting accepted connectors.
                resnap_crossing_displaced_oids.update(conflicting_doids)
                resnap_crossing_winner_oids.add(dangle_oid)
            else:
                # Resnap capture loses: skip the corrected-geometry application.
                entry.skip = True
                resnap_crossing_rejected_oids.add(dangle_oid)

        return (
            resnap_plan,
            resnap_crossing_rejected_oids,
            resnap_crossing_displaced_oids,
            resnap_crossing_winner_oids,
        )

    def _assemble_plan_entries(
        self,
        global_proposals: list[_GlobalProposal],
    ) -> PlanByParent:
        """Assemble plan_by_parent from accepted global proposals."""
        tmp: dict[ParentId, list[tuple[tuple[Any, ...], PlanEntry]]] = {}

        for prop in sorted(global_proposals, key=lambda p: p.sort_key()):
            # near_dist is filled from prop.ctx.raw_distance so the NearCandidate is
            # self-consistent; near_fc_key_raw is unused downstream so we reuse the
            # normalized key.
            chosen = NearCandidate(
                near_fc_key=str(prop.ctx.near_fc_key),
                near_fid=int(prop.ctx.near_fid),
                near_dist=float(prop.ctx.raw_distance),
                near_x=float(prop.ctx.near_x),
                near_y=float(prop.ctx.near_y),
                near_fc_key_raw=str(prop.ctx.near_fc_key),
                near_fid_raw=int(prop.ctx.near_fid),
            )
            entry = self._make_plan_entry(
                parent_id=int(prop.ctx.src_parent_id),
                dangle_oid=int(prop.ctx.dangle_oid),
                dangle_x=float(prop.ctx.dangle_x),
                dangle_y=float(prop.ctx.dangle_y),
                chosen=chosen,
                gap_source=prop.gap_source,
                bonus_applied=prop.ctx.bonus_applied,
                assess=prop.ctx.assess,
                best_fit_score=prop.score.composite,
            )

            tmp.setdefault(int(prop.ctx.src_parent_id), []).append(
                (prop.sort_key(), entry)
            )

        plan_by_parent: PlanByParent = {}
        for pid, items in tmp.items():
            # Deterministic per-parent order
            ordered = sorted(items, key=lambda t: (t[0], t[1].dangle_oid))
            plan_by_parent[int(pid)] = [entry for _, entry in ordered]

        return plan_by_parent

    def _make_base_diag_fields(
        self,
        cand: NearCandidate,
        dangle_oid: DangleOid,
        parent_id: ParentId,
        xy: tuple[float, float],
        dangle_parent: dict[DangleOid, ParentId],
        dangles_key: DatasetKey,
        lines_key: DatasetKey,
    ) -> dict:
        """Return the identity fields shared by all three diagnostic assembly branches."""
        return dict(
            parent_id=parent_id,
            dangle_oid=dangle_oid,
            dangle_x=float(xy[0]),
            dangle_y=float(xy[1]),
            near_fc_key=cand.near_fc_key,
            near_fid=cand.near_fid,
            near_x=cand.near_x,
            near_y=cand.near_y,
            raw_distance=cand.near_dist,
            target_parent_id=self._resolve_target_parent_id(
                cand, dangle_parent, dangles_key, lines_key
            ),
        )

    def _assemble_diagnostics(
        self,
        *,
        collect_diags: bool,
        state: _DiagnosticsState,
        dangle_xy: dict[DangleOid, tuple[float, float]],
        dangle_parent: dict[DangleOid, ParentId],
        dangles_key: DatasetKey,
        lines_key: DatasetKey,
    ) -> list[CandidateDiagnostic]:
        """Stream non-deferrable diagnostic records to the FC; return only the
        accepted-Kruskal subset that may receive late annotations from
        ``_update_deferred_diagnostics`` after the resnap pass.

        The returned list contains records with ``kruskal_scope.status ==
        "accepted"`` only. All other records (step-1A illegals, step-1B
        illegals, and step-1B scored entries that were outscored, lost the
        connection selection, or rejected by Kruskal) are written immediately
        and not retained, dropping the peak in-memory diagnostic footprint
        from O(rejected candidates) to O(accepted candidates).
        """
        if not collect_diags:
            return []

        assert self.candidate_connections_output is not None
        deferred: list[CandidateDiagnostic] = []
        spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
        cursor_fields = ("SHAPE@",) + self._diag_field_names()

        def _z_pair(
            d_xy: tuple[float, float], near_x: float, near_y: float
        ) -> tuple[Optional[float], Optional[float]]:
            if not self._raster_handles:
                return None, None
            sz = geometry_tools.local_z_at_xy(
                self._raster_handles, float(d_xy[0]), float(d_xy[1])
            )
            ez = geometry_tools.local_z_at_xy(
                self._raster_handles, float(near_x), float(near_y)
            )
            return sz, ez

        with arcpy.da.InsertCursor(
            self.candidate_connections_output, cursor_fields
        ) as cur:

            def _emit(d: CandidateDiagnostic) -> None:
                geom = arcpy.Polyline(
                    arcpy.Array(
                        [
                            arcpy.Point(d.dangle_x, d.dangle_y),
                            arcpy.Point(d.near_x, d.near_y),
                        ]
                    ),
                    spatial_reference,
                )
                cur.insertRow(self._diag_row(d, geom))

            # Step-1A illegals: angle never computed; z values looked up here.
            # Never accepted by Kruskal — stream directly.
            for entry in state.step1a_illegal:
                xy = dangle_xy.get(int(entry.dangle_oid))
                if xy is None:
                    continue
                _sz, _ez = _z_pair(xy, entry.cand.near_x, entry.cand.near_y)
                cand_scope = ScopeRecord(status=entry.reason)
                _emit(
                    CandidateDiagnostic(
                        **self._make_base_diag_fields(
                            entry.cand,
                            entry.dangle_oid,
                            entry.parent_id,
                            xy,
                            dangle_parent,
                            dangles_key,
                            lines_key,
                        ),
                        candidate_scope=cand_scope,
                        network_scope=None,
                        kruskal_scope=None,
                        deferred_scope=None,
                        final_status=cand_scope,
                        best_fit_score=None,
                        best_fit_rank=None,
                        bonus_applied=None,
                        norm_dist=None,
                        norm_angle=None,
                        assess=None,
                        final_gap_source=None,
                        start_z=_sz,
                        end_z=_ez,
                    )
                )

            # Eager release: source records are not referenced past this loop.
            state.step1a_illegal.clear()

            # Step-1B angle/Z-blocked illegals: z values carried in entry.
            # Never accepted by Kruskal — stream directly.
            for entry in state.step1b_illegal:
                xy = dangle_xy.get(int(entry.dangle_oid))
                if xy is None:
                    continue
                cand_scope = ScopeRecord(status=entry.reason)
                _emit(
                    CandidateDiagnostic(
                        **self._make_base_diag_fields(
                            entry.cand,
                            entry.dangle_oid,
                            entry.parent_id,
                            xy,
                            dangle_parent,
                            dangles_key,
                            lines_key,
                        ),
                        candidate_scope=cand_scope,
                        network_scope=None,
                        kruskal_scope=None,
                        deferred_scope=None,
                        final_status=cand_scope,
                        best_fit_score=None,
                        best_fit_rank=None,
                        bonus_applied=None,
                        norm_dist=None,
                        norm_angle=None,
                        assess=entry.assess,
                        final_gap_source=None,
                        start_z=entry.start_z,
                        end_z=entry.end_z,
                    )
                )

            # Eager release: source records are not referenced past this loop.
            state.step1b_illegal.clear()

            # Compute per-dangle rank for scored candidates (1 = local winner)
            scored_by_dangle: dict[int, list[_CandidateScored]] = {}
            for entry in state.step1b_scored:
                scored_by_dangle.setdefault(int(entry.dangle_oid), []).append(entry)
            rank_map: dict[tuple[int, str, int], int] = {}
            for d_oid, entries in scored_by_dangle.items():
                for rank, entry in enumerate(
                    sorted(entries, key=lambda e: e.score_tuple), start=1
                ):
                    rank_map[(d_oid, entry.cand.near_fc_key, entry.cand.near_fid)] = (
                        rank
                    )

            # Step-1B scored candidates: only the accepted-Kruskal branch
            # below produces records eligible for late deferred-scope
            # annotation; everything else streams.
            for entry in state.step1b_scored:
                xy = dangle_xy.get(int(entry.dangle_oid))
                if xy is None:
                    continue
                rank = rank_map.get(
                    (entry.dangle_oid, entry.cand.near_fc_key, entry.cand.near_fid)
                )
                d_oid = int(entry.dangle_oid)
                cand_scope = ScopeRecord(status="scored", norm_z=entry.dangle_norm_z)

                if not entry.is_local_winner:
                    net_scope = ScopeRecord(status="outscored_within_dangle")
                    kru_scope: Optional[ScopeRecord] = None
                    final_scope = net_scope
                    final_gs: Optional[str] = None
                elif d_oid in state.connection_loser_oids:
                    net_scope = ScopeRecord(
                        status="lost_connection_selection",
                        norm_z=state.connection_norm_z_by_dangle.get(d_oid),
                    )
                    kru_scope = None
                    final_scope = net_scope
                    final_gs = None
                elif d_oid in state.kruskal_rejected_oids:
                    net_scope = ScopeRecord(
                        status="passed",
                        norm_z=state.connection_norm_z_by_dangle.get(d_oid),
                    )
                    kru_scope = ScopeRecord(
                        status="lost_kruskal_selection",
                        norm_z=state.global_norm_z_by_dangle.get(d_oid),
                    )
                    final_scope = kru_scope
                    final_gs = None
                elif d_oid in state.kruskal_crossing_rejected_oids:
                    net_scope = ScopeRecord(
                        status="passed",
                        norm_z=state.connection_norm_z_by_dangle.get(d_oid),
                    )
                    kru_scope = ScopeRecord(
                        status="crosses_accepted_connector",
                        norm_z=state.global_norm_z_by_dangle.get(d_oid),
                    )
                    final_scope = kru_scope
                    final_gs = None
                elif d_oid in state.accepted_dangle_oids:
                    net_scope = ScopeRecord(
                        status="passed",
                        norm_z=state.connection_norm_z_by_dangle.get(d_oid),
                    )
                    kru_scope = ScopeRecord(
                        status="accepted",
                        norm_z=state.global_norm_z_by_dangle.get(d_oid),
                    )
                    final_scope = kru_scope
                    gs = state.gap_source_by_dangle.get(d_oid)
                    final_gs = gs.value if gs is not None else None
                else:
                    # Local winner that didn't reach proposal construction
                    # (e.g. target dangle had no resolvable parent)
                    net_scope = ScopeRecord(status="passed")
                    kru_scope = None
                    final_scope = net_scope
                    final_gs = None

                d = CandidateDiagnostic(
                    **self._make_base_diag_fields(
                        entry.cand,
                        entry.dangle_oid,
                        entry.parent_id,
                        xy,
                        dangle_parent,
                        dangles_key,
                        lines_key,
                    ),
                    candidate_scope=cand_scope,
                    network_scope=net_scope,
                    kruskal_scope=kru_scope,
                    deferred_scope=None,
                    final_status=final_scope,
                    best_fit_score=float(entry.best_fit),
                    best_fit_rank=rank,
                    bonus_applied=bool(entry.bonus),
                    norm_dist=float(entry.norm_dist),
                    norm_angle=entry.norm_angle,
                    assess=entry.assess,
                    final_gap_source=final_gs,
                    start_z=entry.start_z,
                    end_z=entry.end_z,
                )

                if kru_scope is not None and kru_scope.status == "accepted":
                    deferred.append(d)
                else:
                    _emit(d)

        return deferred

    def _make_plan_entry(
        self,
        *,
        parent_id: int,
        dangle_oid: int,
        dangle_x: float,
        dangle_y: float,
        chosen: NearCandidate,
        gap_source: GapSource,
        bonus_applied: bool = False,
        assess: "Optional[AngleAssessment]" = None,
        best_fit_score: Optional[float] = None,
    ) -> PlanEntry:
        edit_op = self._resolve_edit_op(gap_source=gap_source)

        meta: Optional[PlanEntryMeta] = None
        if self.write_output_metadata:
            meta = PlanEntryMeta(
                bonus_applied=bool(bonus_applied),
                src_connector_diff=assess.src_connector_diff if assess else None,
                connector_target_diff=assess.connector_target_diff if assess else None,
                src_target_diff=assess.src_target_diff if assess else None,
                connector_transition_diff=(
                    assess.connector_transition_diff if assess else None
                ),
                angle_metric_deg=assess.angle_metric_deg if assess else None,
                best_fit_score=best_fit_score,
            )

        return PlanEntry(
            dangle_oid=int(dangle_oid),
            dangle_x=float(dangle_x),
            dangle_y=float(dangle_y),
            near_x=chosen.near_x,
            near_y=chosen.near_y,
            chosen_near_fc_key=chosen.near_fc_key,
            chosen_near_fid=chosen.near_fid,
            gap_source=gap_source,
            edit_op=edit_op,
            meta=meta,
        )

    def _apply_pair_symmetric_skip(
        self, decided_by_parent: dict[int, PlanEntry]
    ) -> None:
        """
        If A and B are marked as pair parents, move only one of them.
        Keep the smaller parent id by default.
        """
        for a_parent, entry in list(decided_by_parent.items()):
            b_parent = entry.pair_parent
            if b_parent is None:
                continue
            b_parent = int(b_parent)

            other = decided_by_parent.get(b_parent)
            if other is None:
                continue
            if (other.pair_parent or -1) != a_parent:
                continue

            keep = min(int(a_parent), int(b_parent))
            drop = max(int(a_parent), int(b_parent))

            decided_by_parent[drop].skip = True
            decided_by_parent[keep].skip = False

    # ----------------------------
    # Resnap pass
    # ----------------------------

    def _resnap_connections(
        self,
        *,
        captures: "list[_ResnappedCapture]",
        dangles_fc: str,
        snap_source_dangle_xy: "dict[ParentId, tuple[float, float]]",
    ) -> dict[ParentId, PlanEntry]:
        """
        Re-resolve the near-point for connections whose target line endpoint moved
        during _apply_plan (SNAP operations).

        Steps:
        1. Read the last segment of each target line (B) from post-apply lines_copy.
           V_prev is the vertex adjacent to B's dangle end; V_end is the original
           dangle position from snap_source_dangle_xy (before the snap moved it).
        2. Project A's original near-point onto [V_prev, V_end]. Discard captures
           whose near-point is not on that segment (unaffected by the snap).
        3. Run GenerateNearTable on the surviving captures against the updated
           target lines to get the new near-point.
        4. Build and return plan entries keyed by parent_id.
        """
        # --- 1. Read V_prev for each forced-target line from updated geometry ---
        forced_target_parents = {int(cap.forced_target_parent) for cap in captures}
        where_l = (
            f"{arcpy.AddFieldDelimiters(self.lines_copy, self.ORIGINAL_ID)}"
            f" IN ({','.join(map(str, sorted(forced_target_parents)))})"
        )
        v_prev_by_parent: dict[ParentId, tuple[float, float]] = {}
        with arcpy.da.SearchCursor(
            self.lines_copy, [self.ORIGINAL_ID, "SHAPE@"], where_l
        ) as cur:
            for pid, shape in cur:
                part = shape.getPart(0)
                pts = [pt for pt in part if pt is not None]
                if len(pts) < 2:
                    continue
                orig_v_end = snap_source_dangle_xy.get(int(pid))
                if orig_v_end is None:
                    continue
                # Determine which end was the dangle by proximity to the original
                # dangle position (dangle end has moved; non-dangle end is unchanged).
                d_first = (pts[0].X - orig_v_end[0]) ** 2 + (
                    pts[0].Y - orig_v_end[1]
                ) ** 2
                d_last = (pts[-1].X - orig_v_end[0]) ** 2 + (
                    pts[-1].Y - orig_v_end[1]
                ) ** 2
                if d_first <= d_last:
                    v_prev_by_parent[int(pid)] = (pts[1].X, pts[1].Y)
                else:
                    v_prev_by_parent[int(pid)] = (pts[-2].X, pts[-2].Y)

        # --- 2. Segment projection: keep captures whose near-point is on [V_prev, V_end] ---
        filtered: list[_ResnappedCapture] = []
        for cap in captures:
            tp = int(cap.forced_target_parent)
            v_prev = v_prev_by_parent.get(tp)
            v_end = snap_source_dangle_xy.get(tp)
            if v_prev is None or v_end is None:
                continue
            nx = float(cap.proposal.ctx.near_x)
            ny = float(cap.proposal.ctx.near_y)
            dx = v_end[0] - v_prev[0]
            dy = v_end[1] - v_prev[1]
            seg_len_sq = dx * dx + dy * dy
            if seg_len_sq == 0.0:
                continue
            t = ((nx - v_prev[0]) * dx + (ny - v_prev[1]) * dy) / seg_len_sq
            if 0.0 <= t <= 1.0:
                filtered.append(cap)

        if not filtered:
            return {}

        # --- 3. GenerateNearTable against updated target-line geometry ---
        dangle_oids = sorted({int(cap.dangle_oid) for cap in filtered})
        forced_parents_filtered = sorted(
            {int(cap.forced_target_parent) for cap in filtered}
        )

        dangles_oid_field = arcpy.Describe(dangles_fc).OIDFieldName
        where_d = (
            f"{arcpy.AddFieldDelimiters(dangles_fc, dangles_oid_field)}"
            f" IN ({','.join(map(str, dangle_oids))})"
        )
        resnap_dangles_lyr = "resnap_dangles_lyr"
        arcpy.management.MakeFeatureLayer(dangles_fc, resnap_dangles_lyr, where_d)

        where_l2 = (
            f"{arcpy.AddFieldDelimiters(self.lines_copy, self.ORIGINAL_ID)}"
            f" IN ({','.join(map(str, forced_parents_filtered))})"
        )
        resnap_lines_lyr = "resnap_lines_lyr"
        arcpy.management.MakeFeatureLayer(self.lines_copy, resnap_lines_lyr, where_l2)

        lines_oid_field = arcpy.Describe(resnap_lines_lyr).OIDFieldName
        near_oid_to_parent: dict[int, ParentId] = {}  # key is raw arcpy OID
        with arcpy.da.SearchCursor(
            resnap_lines_lyr, [lines_oid_field, self.ORIGINAL_ID]
        ) as cur:
            for oid, pid in cur:
                near_oid_to_parent[int(oid)] = int(pid)

        search_radius = (
            2 * self.connectivity_tolerance_meters + self.gap_tolerance_meters
        )
        resnap_table = self.wfm.build_file_path(file_name="resnap_near_table")
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(resnap) START (dangles={len(dangle_oids)}, target_parents={len(forced_parents_filtered)}, radius={search_radius} Meters)")  # [DBG_LINEGAP]
        arcpy.analysis.GenerateNearTable(
            in_features=resnap_dangles_lyr,
            near_features=[resnap_lines_lyr],
            out_table=resnap_table,
            search_radius=f"{search_radius} Meters",
            location="LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=self.candidate_closest_count,
            method="PLANAR",
        )
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} GenerateNearTable(resnap) END (resnap_table_rows={int(arcpy.management.GetCount(resnap_table)[0])})")  # [DBG_LINEGAP]

        best_xy: dict[tuple[int, int], tuple[float, float, float]] = {}
        fields = [
            self.F_IN_FID,
            self.F_NEAR_FID,
            self.F_NEAR_DIST,
            self.F_NEAR_X,
            self.F_NEAR_Y,
        ]
        with arcpy.da.SearchCursor(resnap_table, fields) as cur:
            for in_fid, near_fid, near_dist, near_x, near_y in cur:
                if near_fid is None or near_dist is None:
                    continue
                near_parent = near_oid_to_parent.get(int(near_fid))
                if near_parent is None:
                    continue
                key = (int(in_fid), int(near_parent))
                prev = best_xy.get(key)
                if prev is None or float(near_dist) < prev[2]:
                    best_xy[key] = (float(near_x), float(near_y), float(near_dist))

        if not best_xy:
            return {}

        # --- 4. Build updated plan entries ---
        dangle_xy = self._build_dangle_xy_lookup(dangles_fc)
        lines_key = self._dataset_key(self.lines_copy)
        out: dict[ParentId, PlanEntry] = {}

        for cap in filtered:
            hit = best_xy.get((cap.dangle_oid, cap.forced_target_parent))
            if hit is None:
                continue
            dangle_coords = dangle_xy.get(cap.dangle_oid)
            if dangle_coords is None:
                continue
            resnap_cand = NearCandidate(
                near_fc_key=lines_key,
                near_fid=cap.forced_target_parent,
                near_dist=float(hit[2]),
                near_x=float(hit[0]),
                near_y=float(hit[1]),
                near_fc_key_raw=lines_key,
                near_fid_raw=cap.forced_target_parent,
            )
            out[cap.parent_id] = self._make_plan_entry(
                parent_id=cap.parent_id,
                dangle_oid=cap.dangle_oid,
                dangle_x=float(dangle_coords[0]),
                dangle_y=float(dangle_coords[1]),
                chosen=resnap_cand,
                gap_source=cap.gap_source,
                bonus_applied=cap.proposal.ctx.bonus_applied,
                assess=cap.proposal.ctx.assess,
                best_fit_score=cap.proposal.score.composite,
            )

        return out

    # ----------------------------
    # Change output + edits (unchanged from your current version except gap_source field)
    # ----------------------------

    def _setup_line_changes_output(self) -> None:
        if self.line_changes_output is None or not self.write_output_metadata:
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

        meta_double_fields = [
            "src_connector_diff",
            "connector_target_diff",
            "src_target_diff",
            "connector_transition_diff",
            "angle_metric_deg",
            "best_fit_score",
        ]
        for fname in meta_double_fields:
            if fname not in existing:
                arcpy.management.AddField(self.line_changes_output, fname, "DOUBLE")

        if "bonus_applied" not in existing:
            arcpy.management.AddField(
                self.line_changes_output, "bonus_applied", "SHORT"
            )

    def _build_change_row(
        self,
        original_id: int,
        dangle_x: float,
        dangle_y: float,
        near_x: float,
        near_y: float,
        spatial_reference,
        gap_source: GapSource,
        meta: Optional[PlanEntryMeta] = None,
    ):
        dist = ((dangle_x - near_x) ** 2 + (dangle_y - near_y) ** 2) ** 0.5
        if dist == 0.0:
            return None

        arr = arcpy.Array(
            [arcpy.Point(dangle_x, dangle_y), arcpy.Point(near_x, near_y)]
        )
        geom = arcpy.Polyline(arr, spatial_reference)
        row: list[Any] = [geom, int(original_id), float(dist), gap_source.value]
        if meta is not None:
            row.extend(
                [
                    meta.src_connector_diff,
                    meta.connector_target_diff,
                    meta.src_target_diff,
                    meta.connector_transition_diff,
                    meta.angle_metric_deg,
                    meta.best_fit_score,
                    int(meta.bonus_applied),
                ]
            )
        return tuple(row)

    @staticmethod
    def _diag_field_names() -> tuple[str, ...]:
        """Canonical ordered field list for the candidate-connections FC (excluding SHAPE@)."""
        return (
            "src_line_id",
            "src_dangle_oid",
            "target_ds_key",
            "target_fid",
            "target_parent_id",
            "raw_distance",
            "best_fit_score",
            "best_fit_rank",
            "bonus_applied",
            "norm_dist",
            "norm_angle",
            "angle_metric_deg",
            "src_connector_diff",
            "connector_target_diff",
            "src_target_diff",
            "connector_transition_diff",
            "candidate_scope_status",
            "candidate_scope_reason",
            "candidate_scope_norm_z",
            "network_scope_status",
            "network_scope_reason",
            "network_scope_norm_z",
            "kruskal_scope_status",
            "kruskal_scope_reason",
            "kruskal_scope_norm_z",
            "deferred_scope_status",
            "deferred_scope_reason",
            "final_status",
            "final_status_reason",
            "final_gap_source",
            "start_z",
            "end_z",
        )

    @staticmethod
    def _diag_row(d: "CandidateDiagnostic", geom: Any) -> tuple:
        """Build one InsertCursor row tuple from a CandidateDiagnostic."""
        a = d.assess
        net = d.network_scope
        kru = d.kruskal_scope
        def_ = d.deferred_scope
        return (
            geom,
            d.parent_id,
            d.dangle_oid,
            d.near_fc_key,
            d.near_fid,
            d.target_parent_id,
            d.raw_distance,
            d.best_fit_score,
            d.best_fit_rank,
            int(bool(d.bonus_applied)) if d.bonus_applied is not None else None,
            d.norm_dist,
            d.norm_angle,
            a.angle_metric_deg if a is not None else None,
            a.src_connector_diff if a is not None else None,
            a.connector_target_diff if a is not None else None,
            a.src_target_diff if a is not None else None,
            a.connector_transition_diff if a is not None else None,
            d.candidate_scope.status,
            d.candidate_scope.reason,
            d.candidate_scope.norm_z,
            net.status if net is not None else None,
            net.reason if net is not None else None,
            net.norm_z if net is not None else None,
            kru.status if kru is not None else None,
            kru.reason if kru is not None else None,
            kru.norm_z if kru is not None else None,
            def_.status if def_ is not None else None,
            def_.reason if def_ is not None else None,
            d.final_status.status,
            d.final_status.reason,
            d.final_gap_source,
            d.start_z,
            d.end_z,
        )

    def _setup_candidate_connections_output(self, fc_path: str) -> None:
        """Create and schema the candidate-connections diagnostic feature class."""
        sr = arcpy.Describe(self.lines_copy).spatialReference
        out_path, out_name = os.path.split(fc_path)
        if arcpy.Exists(fc_path):
            arcpy.management.Delete(fc_path)
        arcpy.management.CreateFeatureclass(
            out_path=out_path,
            out_name=out_name,
            geometry_type="POLYLINE",
            spatial_reference=sr,
        )
        _text50 = {"field_type": "TEXT", "field_length": 50}
        _dbl = {"field_type": "DOUBLE"}
        _long = {"field_type": "LONG"}
        _short = {"field_type": "SHORT"}
        field_specs: list[tuple[str, dict]] = [
            ("src_line_id", _long),
            ("src_dangle_oid", _long),
            ("target_ds_key", {"field_type": "TEXT", "field_length": 100}),
            ("target_fid", _long),
            ("target_parent_id", _long),
            ("raw_distance", _dbl),
            ("best_fit_score", _dbl),
            ("best_fit_rank", _short),
            ("bonus_applied", _short),
            ("norm_dist", _dbl),
            ("norm_angle", _dbl),
            ("angle_metric_deg", _dbl),
            ("src_connector_diff", _dbl),
            ("connector_target_diff", _dbl),
            ("src_target_diff", _dbl),
            ("connector_transition_diff", _dbl),
            ("candidate_scope_status", _text50),
            ("candidate_scope_reason", _text50),
            ("candidate_scope_norm_z", _dbl),
            ("network_scope_status", _text50),
            ("network_scope_reason", _text50),
            ("network_scope_norm_z", _dbl),
            ("kruskal_scope_status", _text50),
            ("kruskal_scope_reason", _text50),
            ("kruskal_scope_norm_z", _dbl),
            ("deferred_scope_status", _text50),
            ("deferred_scope_reason", _text50),
            ("final_status", _text50),
            ("final_status_reason", _text50),
            ("final_gap_source", {"field_type": "TEXT", "field_length": 20}),
            ("start_z", _dbl),
            ("end_z", _dbl),
        ]
        for fname, kwargs in field_specs:
            arcpy.management.AddField(fc_path, fname, **kwargs)

    def _write_candidate_connections_output(
        self,
        fc_path: str,
        diagnostics: list[CandidateDiagnostic],
        spatial_reference,
    ) -> None:
        """Write one row per CandidateDiagnostic to the candidate-connections feature class."""
        if not diagnostics:
            return
        fields = ("SHAPE@",) + self._diag_field_names()
        with arcpy.da.InsertCursor(fc_path, fields) as cur:
            for d in diagnostics:
                arr = arcpy.Array(
                    [
                        arcpy.Point(d.dangle_x, d.dangle_y),
                        arcpy.Point(d.near_x, d.near_y),
                    ]
                )
                geom = arcpy.Polyline(arr, spatial_reference)
                cur.insertRow(self._diag_row(d, geom))

    def _apply_plan(self, plan: PlanByParent) -> None:
        """Commit plan entries to ``lines_copy`` and optionally record changes.

        Iterates ``lines_copy`` via ``UpdateCursor``.  For each parent line
        with pending plan entries, applies each entry in order — SNAP moves
        the dangle endpoint exactly to the target point; EXTEND inserts the
        target point as the new endpoint while preserving the existing
        vertices; NEW_LINE leaves the parent untouched and is materialised
        as a new feature in a post-pass insert (see
        ``_insert_generated_lines``).  When ``line_changes_output`` is set
        and metadata writing is enabled, a per-edit row is collected and
        inserted after all geometry updates are complete.

        How:
            Each ``PlanEntry`` carries ``skip`` and ``processed`` flags.
            Entries with ``skip=True`` (e.g. a losing side of a mutual pair
            or a resnap capture displaced by a crossing recheck) are never
            applied.  ``processed`` is set as soon as an entry is applied,
            so calling ``_apply_plan`` a second time with the same plan is
            a no-op for already-applied entries — this is what lets
            ``run`` invoke ``_apply_plan`` twice (once for the initial
            plan, once for the resnap plan) without double-editing any
            line.
        """
        if not plan:
            return

        spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
        change_rows: list[tuple] = []
        generated_records: list[_GeneratedLineRecord] = []

        with arcpy.da.UpdateCursor(
            self.lines_copy, [self.ORIGINAL_ID, "SHAPE@"]
        ) as cur:
            for original_id, shape in cur:
                pid = int(original_id)
                entries = plan.get(pid, [])
                if not entries:
                    continue

                pending = [e for e in entries if not e.skip and not e.processed]
                if not pending:
                    continue

                current_shape = shape
                shape_modified = False

                for info in pending:
                    if info.edit_op is EditOp.SNAP:
                        current_shape = self._snap_endpoint(
                            shape=current_shape,
                            dangle_x=info.dangle_x,
                            dangle_y=info.dangle_y,
                            near_x=info.near_x,
                            near_y=info.near_y,
                        )
                        shape_modified = True
                    elif info.edit_op is EditOp.EXTEND:
                        current_shape = self._extend_endpoint(
                            shape=current_shape,
                            dangle_x=info.dangle_x,
                            dangle_y=info.dangle_y,
                            near_x=info.near_x,
                            near_y=info.near_y,
                        )
                        shape_modified = True
                    else:
                        # NEW_LINE — defer to post-pass insert; parent untouched.
                        generated_records.append(
                            _GeneratedLineRecord(
                                parent_original_id=pid,
                                dangle_x=info.dangle_x,
                                dangle_y=info.dangle_y,
                                near_x=info.near_x,
                                near_y=info.near_y,
                            )
                        )

                    info.processed = True

                    if (
                        self.line_changes_output is not None
                        and self.write_output_metadata
                    ):
                        row = self._build_change_row(
                            original_id=pid,
                            dangle_x=info.dangle_x,
                            dangle_y=info.dangle_y,
                            near_x=info.near_x,
                            near_y=info.near_y,
                            spatial_reference=spatial_reference,
                            gap_source=info.gap_source,
                            meta=info.meta,
                        )
                        if row is not None:
                            change_rows.append(row)

                if shape_modified:
                    cur.updateRow((original_id, current_shape))

        if generated_records:
            self._insert_generated_lines(
                records=generated_records,
                spatial_reference=spatial_reference,
            )

        if (
            self.line_changes_output is not None
            and self.write_output_metadata
            and change_rows
        ):
            meta_fields = [
                "src_connector_diff",
                "connector_target_diff",
                "src_target_diff",
                "connector_transition_diff",
                "angle_metric_deg",
                "best_fit_score",
                "bonus_applied",
            ]
            with arcpy.da.InsertCursor(
                self.line_changes_output,
                [
                    "SHAPE@",
                    self.ORIGINAL_ID,
                    self.FIELD_GAP_DIST_M,
                    self.FIELD_GAP_SOURCE,
                ]
                + meta_fields,
            ) as icur:
                for row in change_rows:
                    if len(row) == 4:
                        # Polygon (non-line) rows have no angle metadata; pad with None.
                        row = row + (None,) * len(meta_fields)
                    icur.insertRow(row)

    def _insert_generated_lines(
        self,
        *,
        records: list[_GeneratedLineRecord],
        spatial_reference,
    ) -> None:
        """Materialise NEW_LINE plan entries as new features in ``lines_copy``.

        Each record is written as a 2-vertex polyline (dangle -> near) that
        carries a copy of the parent line's attributes — every field except
        the OID, the geometry, ``Shape_Length``/``Shape_Area``,
        ``ORIGINAL_ID``, and ``FIELD_GAP_GENERATED``.  ``ORIGINAL_ID`` is
        forced to ``GENERATED_ORIGINAL_ID_SENTINEL`` so the second
        ``_apply_plan`` (resnap) pass cannot mistake a generated row for a
        real parent; ``FIELD_GAP_GENERATED`` is forced to 1.

        Records whose dangle and near coordinates coincide are skipped — a
        zero-length connector should not have been considered a gap, but
        the guard keeps the insert pass safe.
        """
        if not records:
            return

        oid_field = arcpy.Describe(self.lines_copy).OIDFieldName
        excluded = {
            oid_field,
            self.FIELD_GAP_GENERATED,
            self.ORIGINAL_ID,
        }
        copyable_fields: list[str] = []
        for f in arcpy.ListFields(self.lines_copy):
            if f.type in ("Geometry", "OID", "GlobalID"):
                continue
            if f.name in excluded:
                continue
            if f.name in ("Shape_Length", "Shape_Area"):
                continue
            copyable_fields.append(f.name)

        needed_parent_ids = {r.parent_original_id for r in records}
        parent_attrs: dict[ParentId, tuple] = {}
        if copyable_fields:
            with arcpy.da.SearchCursor(
                self.lines_copy, [self.ORIGINAL_ID] + copyable_fields
            ) as scur:
                for row in scur:
                    pid = int(row[0])
                    if pid in needed_parent_ids and pid not in parent_attrs:
                        parent_attrs[pid] = tuple(row[1:])

        insert_fields = (
            copyable_fields
            + [self.ORIGINAL_ID, self.FIELD_GAP_GENERATED, "SHAPE@"]
        )

        epsilon_sq = 1e-10
        with arcpy.da.InsertCursor(self.lines_copy, insert_fields) as icur:
            for rec in records:
                dx = rec.near_x - rec.dangle_x
                dy = rec.near_y - rec.dangle_y
                if dx * dx + dy * dy <= epsilon_sq:
                    continue

                if copyable_fields:
                    attrs = parent_attrs.get(rec.parent_original_id)
                    if attrs is None:
                        # Parent vanished from lines_copy between cursor
                        # passes — should not happen, but skip rather
                        # than write None for every field.
                        continue
                else:
                    attrs = ()

                geom = arcpy.Polyline(
                    arcpy.Array(
                        [
                            arcpy.Point(rec.dangle_x, rec.dangle_y),
                            arcpy.Point(rec.near_x, rec.near_y),
                        ]
                    ),
                    spatial_reference,
                )
                icur.insertRow(
                    tuple(attrs)
                    + (
                        self.GENERATED_ORIGINAL_ID_SENTINEL,
                        1,
                        geom,
                    )
                )

    def _update_deferred_diagnostics(
        self,
        *,
        diagnostics: list[CandidateDiagnostic],
        resnap_plan: dict[ParentId, PlanEntry],
        rejected_oids: set[DangleOid],
        displaced_oids: set[DangleOid],
        winner_oids: set[DangleOid],
    ) -> None:
        """Record each accepted candidate's resnap outcome on its diagnostic.
        Precedence: displaced > winner > applied_resnapped > rejected."""
        if not self._collect_diags or not diagnostics:
            return

        applied_oids = {v.dangle_oid for v in resnap_plan.values() if not v.skip}
        for diag in diagnostics:
            if diag.kruskal_scope is None or diag.kruskal_scope.status != "accepted":
                continue
            d_oid = int(diag.dangle_oid)
            if d_oid in displaced_oids:
                deferred = ScopeRecord(status="resnap_crossing_displaced")
                diag.deferred_scope = deferred
                diag.final_status = deferred
            elif d_oid in winner_oids:
                diag.deferred_scope = ScopeRecord(status="referenced_as_winner")
            elif d_oid in applied_oids:
                deferred = ScopeRecord(status="applied_resnapped")
                diag.deferred_scope = deferred
                diag.final_status = deferred
            elif d_oid in rejected_oids:
                deferred = ScopeRecord(status="resnap_crossing_rejected")
                diag.deferred_scope = deferred
                diag.final_status = deferred

    def _write_output(self) -> None:
        arcpy.management.CopyFeatures(self.lines_copy, self.output_lines)

    # ----------------------------
    # Run
    # ----------------------------

    def run(self) -> None:
        """Execute the full gap-fill workflow.

        How:
            1. Set up the arcpy environment and resolve work-file paths via
               ``WorkFileManager``.
            2. Copy inputs, stamp ``ORIGINAL_ID``, extract dangle endpoints
               and (optionally) load raster handles for Z scoring.
            3. Build the target universe: self-lines filtered by tolerance
               (``fill_gaps_on_self``) plus external ``connect_to_features``
               layers (``_build_external_target_layers_once``).
            4. Keep only true dangles — those not already touching an
               external target (``_filter_true_dangles``).
            5. Initialize optional diagnostic feature classes
               (``line_changes_output``, ``candidate_connections_output``).
            6. Run the four-scope decision pipeline in ``_build_plan`` and
               apply the resulting edits with ``_apply_plan``.
            7. If any proposals deferred into the resnap scope, resolve
               their final geometry with ``_resnap_connections``; when
               ``reject_crossing_connectors`` is enabled, re-check the
               resnapped geometry against accepted connectors via
               ``_recheck_resnap_crossings`` before applying the second
               pass and annotating diagnostics.
            8. Write the diagnostic feature class (if requested), copy
               ``lines_copy`` to ``output_lines``, and delete work files.

        Why:
            The resnap pass runs after the first ``_apply_plan`` because a
            snap moves the target line's endpoint, which can invalidate any
            connector previously anchored on that endpoint's last segment.
            Resolving that re-projection pre-apply would require predicting
            the snapped geometry; doing it post-apply reads the real
            geometry and is exact.
        """
        environment_setup.main()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} run START")  # [DBG_LINEGAP]

        self.work_file_list = self.wfm.setup_work_file_paths(
            instance=self,
            file_structure=self.work_file_list,
        )

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _copy_input_lines START")  # [DBG_LINEGAP]
        self._copy_input_lines()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _copy_input_lines END (lines_copy_rows={int(arcpy.management.GetCount(self.lines_copy)[0])})")  # [DBG_LINEGAP]
        self._build_raster_handles()
        self._add_original_id_field()
        self._ensure_gap_generated_field()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _create_dangles START")  # [DBG_LINEGAP]
        self._create_dangles()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _create_dangles END (dangles_rows={int(arcpy.management.GetCount(self.dangles)[0])})")  # [DBG_LINEGAP]
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _build_external_target_layers_once START")  # [DBG_LINEGAP]
        self._build_external_target_layers_once()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _build_external_target_layers_once END")  # [DBG_LINEGAP]
        self._setup_segmentation()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _select_targets_within_tolerance_of_dangles START")  # [DBG_LINEGAP]
        targets = self._select_targets_within_tolerance_of_dangles()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _select_targets_within_tolerance_of_dangles END (target_layers={len(targets)})")  # [DBG_LINEGAP]

        # Keep only dangles that have any candidate within base tolerance
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _filter_true_dangles START")  # [DBG_LINEGAP]
        self._filter_true_dangles()
        dangles_for_plan = self.filtered_dangles
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _filter_true_dangles END (filtered_dangles_rows={int(arcpy.management.GetCount(dangles_for_plan)[0])})")  # [DBG_LINEGAP]

        if self.line_changes_output is not None and self.write_output_metadata:
            file_utilities.delete_feature(input_feature=self.line_changes_output)
            self._setup_line_changes_output()

        if self._collect_diags:
            assert self.candidate_connections_output is not None
            self._setup_candidate_connections_output(self.candidate_connections_output)

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _build_plan START")  # [DBG_LINEGAP]
        result = self._build_plan(dangles_fc=dangles_for_plan, target_layers=targets)
        plan = result.plan_by_parent
        resnap_captures = result.resnap_captures
        diagnostics = result.diagnostics
        accepted_connector_raw = result.accepted_connector_raw
        kruskal_rank_by_dangle_oid = result.kruskal_rank_by_dangle_oid
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _build_plan END (plan_parents={len(plan)}, resnap_captures={len(resnap_captures)}, diagnostics={len(diagnostics)})")  # [DBG_LINEGAP]

        # Capture snap-source dangle endpoints before _apply_plan moves them.
        snap_source_dangle_xy: dict[ParentId, tuple[float, float]] = {
            parent_id: (info.dangle_x, info.dangle_y)
            for parent_id, entries in plan.items()
            for info in entries
            if info.edit_op is EditOp.SNAP
        }

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _apply_plan START (plan_parents={len(plan)})")  # [DBG_LINEGAP]
        self._apply_plan(plan)
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _apply_plan END")  # [DBG_LINEGAP]

        if resnap_captures:
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _resnap_connections START (captures={len(resnap_captures)})")  # [DBG_LINEGAP]
            resnap_plan = self._resnap_connections(
                captures=resnap_captures,
                dangles_fc=dangles_for_plan,
                snap_source_dangle_xy=snap_source_dangle_xy,
            )
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _resnap_connections END (resnap_plan={len(resnap_plan)})")  # [DBG_LINEGAP]

            if (
                self.reject_crossing_connectors
                and resnap_plan
                and accepted_connector_raw
            ):
                print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _recheck_resnap_crossings START (resnap_plan={len(resnap_plan)})")  # [DBG_LINEGAP]
                (
                    resnap_plan,
                    resnap_crossing_rejected_oids,
                    resnap_crossing_displaced_oids,
                    resnap_crossing_winner_oids,
                ) = self._recheck_resnap_crossings(
                    resnap_plan=resnap_plan,
                    accepted_connector_raw=accepted_connector_raw,
                    kruskal_rank_by_dangle_oid=kruskal_rank_by_dangle_oid,
                    trim_distance=2.0 * float(self.connectivity_tolerance_meters),
                    spatial_reference=arcpy.SpatialReference(
                        self.crossing_check_spatial_reference
                    ),
                )
                print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _recheck_resnap_crossings END (resnap_plan={len(resnap_plan)}, rejected={len(resnap_crossing_rejected_oids)})")  # [DBG_LINEGAP]
            else:
                resnap_crossing_rejected_oids: set[DangleOid] = set()
                resnap_crossing_displaced_oids: set[DangleOid] = set()
                resnap_crossing_winner_oids: set[DangleOid] = set()

            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _apply_plan(resnap) START (entries={len(resnap_plan)})")  # [DBG_LINEGAP]
            self._apply_plan({pid: [entry] for pid, entry in resnap_plan.items()})
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _apply_plan(resnap) END")  # [DBG_LINEGAP]

            self._update_deferred_diagnostics(
                diagnostics=diagnostics,
                resnap_plan=resnap_plan,
                rejected_oids=resnap_crossing_rejected_oids,
                displaced_oids=resnap_crossing_displaced_oids,
                winner_oids=resnap_crossing_winner_oids,
            )

        if self._collect_diags and diagnostics:
            assert self.candidate_connections_output is not None
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _write_candidate_connections_output START (diagnostics={len(diagnostics)})")  # [DBG_LINEGAP]
            spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
            self._write_candidate_connections_output(
                fc_path=self.candidate_connections_output,
                diagnostics=diagnostics,
                spatial_reference=spatial_reference,
            )
            print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _write_candidate_connections_output END")  # [DBG_LINEGAP]

        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} _write_output START")  # [DBG_LINEGAP]
        self._write_output()
        print(f"[DBG_LINEGAP] {time.strftime('%H:%M:%S')} run END")  # [DBG_LINEGAP]

        self.wfm.delete_created_files()
