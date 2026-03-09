from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math

from typing import Optional, Callable, Iterable, Any

import arcpy

from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy, file_utilities
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
    connectivity_id_by_parent: Optional[dict[int, int]]
    connectivity_id_by_optional: Optional[dict[OptionalKey, int]]
    entities_by_connectivity_id: Optional[dict[int, set[EntityKey]]]

    # DIRECT_CONNECTION only (required); allowed to be None otherwise
    direct_neighbors_by_parent: Optional[dict[int, set[int]]]
    direct_optionals_by_parent: Optional[dict[int, set[OptionalKey]]]


class EditOp(str, Enum):
    SNAP = "snap"
    EXTEND = "extend"


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
    ) -> None:
        self.lines_fc = lines_fc
        self.original_id_field = original_id_field
        self.connect_to_features = connect_to_features or []
        self.dataset_key_fn = dataset_key_fn
        self.wfm = wfm
        self.write_work_files_to_memory = bool(write_work_files_to_memory)
        self.tol_m = float(connectivity_tolerance_meters)
        self.line_mode = line_connectivity_mode

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
        endpoints_fc = self.wfm.build_file_path(file_name="topo_line_endpoints")
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

        near_table = self.wfm.build_file_path(file_name="topo_endpoints_near_lines")
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

        near_table = self.wfm.build_file_path(file_name="topo_lines_near_lines")
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
                    file_name=f"topo_lines_to_opt_{ds_key}"
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
                file_name=f"topo_lines_to_opt_attach_{ds_key}"
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
        table = self.wfm.build_file_path(file_name=f"topo_optopt_{ds_in}_to_{ds_near}")
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
class Proposal:
    """
    One best-fit legal candidate per dangle (no fallback).
    """

    dangle_oid: int
    src_parent_id: int
    src_node: EntityKey
    tgt_node: EntityKey
    chosen: dict  # the chosen candidate row dict

    raw_distance: float
    best_fit_score: float
    bonus_applied: bool

    # (effective_dist, bonus_rank, raw_dist, src_parent, dangle_oid, near_fc_key, near_fid)
    # bonus_rank: 0 when edge-case bonus applied, else 1
    score: tuple[float, int, float, int, int, str, int]

    pair_key: tuple[EntityKey, EntityKey]  # unordered network pair
    target_parent_id: Optional[int]  # only for line/dangle targets (ORIGINAL_ID space)
    target_dangle_oid: Optional[int]  # only if chosen is a dangle target


@dataclass(frozen=True)
class AngleAssessment:
    # Primary decisions
    available: bool
    blocks: bool
    allow_extra_dangle: bool  # expanded dangle tol + edge-case bonus
    angle_metric_deg: Optional[float]

    # Diagnostics (optional)
    src_connector_diff: Optional[float] = None
    connector_target_diff: Optional[float] = None
    src_target_diff: Optional[float] = None
    connector_transition_diff: Optional[float] = None
    line_match_diff: Optional[float] = None


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
        self.write_output_metadata = bool(adv.write_output_metadata)
        self.increased_tolerance_edge_case_distance_meters = int(
            adv.increased_tolerance_edge_case_distance_meters
        )
        self.edit_method = logic_config.EditMethod(adv.edit_method)

        self.connectivity_scope = logic_config.ConnectivityScope(adv.connectivity_scope)
        self.connectivity_tolerance_meters = float(adv.connectivity_tolerance_meters)
        self.line_connectivity_mode = logic_config.LineConnectivityMode(
            adv.line_connectivity_mode
        )

        if self.connect_to_features is None and self.fill_gaps_on_self is False:
            raise ValueError(
                "Invalid config: fill_gaps_on_self cannot be False when connect_to_features is None."
            )

        # ----------------------------
        # Angle config
        # ----------------------------
        self.angle_block_threshold_degrees = (
            None
            if adv.angle_block_threshold_degrees is None
            else float(adv.angle_block_threshold_degrees)
        )
        self.angle_extra_dangle_threshold_degrees = (
            None
            if adv.angle_extra_dangle_threshold_degrees is None
            else float(adv.angle_extra_dangle_threshold_degrees)
        )
        self.best_fit_weights = adv.best_fit_weights

        w = float(getattr(adv, "line_alignment_weight", 0.6))
        self.line_alignment_weight = max(0.0, min(1.0, w))

        self.angle_local_half_window_m = float(
            getattr(adv, "angle_local_half_window_m", 2.0)
        )

        # Raw config map (may be keyed by path or dataset_key(path))
        self._connect_to_features_angle_mode_raw = (
            adv.connect_to_features_angle_mode or {}
        )

        # Filled during _build_external_target_layers_once:
        # dataset_key(output_layer) -> AngleTargetMode
        self._angle_mode_by_external_ds_key: dict[str, logic_config.AngleTargetMode] = (
            {}
        )

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

    def _connectivity_tolerance_linear_unit(self) -> str:
        meters = max(0.0, float(self.connectivity_tolerance_meters))
        return f"{meters} Meters"

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

    def _resolve_edit_op(self, *, gap_source: str) -> EditOp:
        method = self.edit_method

        if method == logic_config.EditMethod.FORCED_SNAP:
            return EditOp.SNAP
        if method == logic_config.EditMethod.FORCED_EXTEND:
            return EditOp.EXTEND

        # AUTO
        if str(gap_source) == self.GAP_SOURCE_PAIR_DANGLE:
            return EditOp.SNAP
        return EditOp.EXTEND

    def _same_network(
        self,
        *,
        a_parent: int,
        b_parent: int,
        topology: TopologyModel,
    ) -> bool:
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

    def _candidate_sort_key(self, cand: dict) -> tuple:
        # Deterministic ordering for candidate rows within a dangle
        return (
            float(cand.get("near_dist", float("inf"))),
            str(cand.get("near_fc_key", "")),
            int(cand.get("near_fid", -1)),
            float(cand.get("near_x", 0.0)),
            float(cand.get("near_y", 0.0)),
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
        legal_rows: list[dict],
        lines_fc_key: str,
    ) -> Optional[int]:
        """
        Return the parent line id of the closest legal line target for this dangle.

        `legal_rows` must already be sorted by raw candidate order.
        """
        for cand in legal_rows:
            if str(cand["near_fc_key"]) == str(lines_fc_key):
                return int(cand["near_fid"])
        return None

    def _edge_case_bonus_applies(
        self,
        *,
        dangle_oid: int,
        cand: dict,
        dangles_fc_key: str,
        dangle_parent: dict[int, int],
        best_line_parent_by_dangle: dict[int, int],
    ) -> bool:
        """
        Edge-case bonus applies only for dangle targets when:

        - source dangle's best legal line target is the target dangle's parent line
        - target dangle's best legal line target is the source dangle's parent line

        This is the explicit implementation of:
        "if both dangles want each other's parent line, prioritize the dangle".
        """
        extra = max(0, int(self.increased_tolerance_edge_case_distance_meters))
        if extra <= 0:
            return False

        if str(cand["near_fc_key"]) != str(dangles_fc_key):
            return False

        src_parent = dangle_parent.get(int(dangle_oid))
        if src_parent is None:
            return False

        other_dangle_oid = int(cand["near_fid"])
        other_parent = dangle_parent.get(int(other_dangle_oid))
        if other_parent is None:
            return False

        src_best_line_parent = best_line_parent_by_dangle.get(int(dangle_oid))
        other_best_line_parent = best_line_parent_by_dangle.get(int(other_dangle_oid))

        if src_best_line_parent is None or other_best_line_parent is None:
            return False

        return int(src_best_line_parent) == int(other_parent) and int(
            other_best_line_parent
        ) == int(src_parent)

    def _candidate_score_details(
        self,
        *,
        dangle_oid: int,
        parent_id: int,
        cand: dict,
        dangles_fc_key: str,
        dangle_parent: dict[int, int],
        best_line_parent_by_dangle: dict[int, int],
        bonus_allowed: bool = True,
    ) -> tuple[float, float, bool, tuple[float, int, float, int, int, str, int]]:
        raw_distance = float(cand["near_dist"])

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

        bonus_rank = 0 if bonus_applied else 1

        score = (
            float(effective_distance),
            int(bonus_rank),
            float(raw_distance),
            int(parent_id),
            int(dangle_oid),
            str(cand["near_fc_key"]),
            int(cand["near_fid"]),
        )

        return raw_distance, effective_distance, bool(bonus_applied), score

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

    def _build_polyline_by_parent_id(self) -> dict[int, Any]:
        out: dict[int, Any] = {}
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

    def _orientation(self, angle_deg: float) -> float:
        return float(angle_deg) % 180.0

    def _orientation_diff(self, a_deg: float, b_deg: float) -> float:
        a = self._orientation(float(a_deg))
        b = self._orientation(float(b_deg))
        raw = abs(a - b)
        return min(raw, 180.0 - raw)  # 0..90

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
        topology: TopologyModel,
    ) -> dict[int, dict[str, set[int]]]:
        """
        illegal[parent_id][dataset_key] -> set(objectid)

        Clauses:
        - self line
        - objects connected to parent line endpoints

        Propagation:
        - Scope-dependent, using topology connectivity ids (not local BFS adjacency).
        """
        illegal: dict[int, dict[str, set[int]]] = {}

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
        illegal: dict[int, dict[str, set[int]]],
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

        connect_tol_m = float(self.connectivity_tolerance_meters)
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
        dangle_candidate_tol: float,
        topology: TopologyModel | None = None,
    ) -> bool:
        ds_key = cand["near_fc_key"]
        oid = int(cand["near_fid"])
        dist = float(cand["near_dist"])

        if ds_key == dangles_fc_key:
            # IMPORTANT: use dangle_candidate_tol, not expanded tolerance by default
            if dist > float(dangle_candidate_tol):
                return False

            other_parent = dangle_parent.get(int(oid))
            if other_parent is None:
                return False

            # Same-network restriction (value-neutral topology)
            if topology is not None and self._same_network(
                a_parent=int(parent_id),
                b_parent=int(other_parent),
                topology=topology,
            ):
                return False

            # Dangle->dangle still illegal-checks against the other parent line id
            if self._is_illegal(
                illegal=illegal,
                parent_id=parent_id,
                target_fc_key=lines_fc_key,
                target_oid=int(other_parent),
            ):
                return False

            return True

        # non-dangle always uses base_tol
        if dist > float(base_tol):
            return False

        if ds_key == lines_fc_key and int(oid) == int(parent_id):
            return False

        # Same-network restriction for line targets (oid is in ORIGINAL_ID space in your grouped rows)
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

    def _assess_angle(
        self,
        *,
        src_parent_id: int,
        dangle_x: float,
        dangle_y: float,
        src_angle_deg: Optional[float],
        cand: dict,
        dangles_fc_key: str,
        lines_fc_key: str,
        dangle_parent: dict[int, int],
        dangle_xy: dict[int, tuple[float, float]],
        polyline_by_parent: dict[int, Any],
        polyline_by_external: dict[str, dict[int, Any]],
        is_external_line_like: dict[str, bool],
    ) -> AngleAssessment:
        ds_key = str(cand["near_fc_key"])
        near_fid = int(cand["near_fid"])
        near_x = float(cand["near_x"])
        near_y = float(cand["near_y"])

        connector_angle = self._connector_angle_deg(
            from_x=dangle_x, from_y=dangle_y, to_x=near_x, to_y=near_y
        )

        # Determine line-like vs non-line
        if ds_key == lines_fc_key or ds_key == dangles_fc_key:
            treat_as_line_like = True
        else:
            mode = self._angle_mode_by_external_ds_key.get(
                ds_key, logic_config.AngleTargetMode.AUTO
            )
            if mode == logic_config.AngleTargetMode.FORCE_NON_LINE:
                treat_as_line_like = False
            else:
                treat_as_line_like = bool(is_external_line_like.get(ds_key, False))

        # Base requirements
        if src_angle_deg is None or connector_angle is None:
            # Angle unavailable => no block, no penalty; conservative extra-dangle policy handled below
            allow_extra = ds_key != dangles_fc_key  # only relevant for dangle targets
            return AngleAssessment(
                available=False,
                blocks=False,
                allow_extra_dangle=bool(allow_extra),
                angle_metric_deg=None,
            )

        src_connector_diff = self._orientation_diff(
            float(src_angle_deg), float(connector_angle)
        )

        # Non-line targets use src_connector_diff directly
        if not treat_as_line_like:
            metric = float(src_connector_diff)

            blocks = self.angle_block_threshold_degrees is not None and metric > float(
                self.angle_block_threshold_degrees
            )

            # extra-dangle threshold only affects dangle targets
            allow_extra = True
            if ds_key == dangles_fc_key:
                if self.angle_extra_dangle_threshold_degrees is None:
                    allow_extra = True
                else:
                    allow_extra = metric <= float(
                        self.angle_extra_dangle_threshold_degrees
                    )

            return AngleAssessment(
                available=True,
                blocks=bool(blocks),
                allow_extra_dangle=bool(allow_extra),
                angle_metric_deg=float(metric),
                src_connector_diff=float(src_connector_diff),
            )

        # Line-like targets: need target angle too
        target_angle: Optional[float] = None
        connector_target_diff: Optional[float] = None
        src_target_diff: Optional[float] = None
        connector_transition_diff: Optional[float] = None
        line_match_diff: Optional[float] = None

        if ds_key == lines_fc_key:
            tgt_parent = int(near_fid)
            tgt_poly = polyline_by_parent.get(tgt_parent)
            if tgt_poly is not None:
                target_angle = self._local_line_angle_cached(
                    dataset_key=lines_fc_key,
                    oid=tgt_parent,
                    polyline=tgt_poly,
                    x=near_x,
                    y=near_y,
                )

        elif ds_key == dangles_fc_key:
            other_dangle_oid = int(near_fid)
            other_parent = dangle_parent.get(other_dangle_oid)
            if other_parent is not None:
                tgt_poly = polyline_by_parent.get(int(other_parent))
                if tgt_poly is not None:
                    # Prefer true dangle XY lookup; fall back to near_x/near_y
                    xy = dangle_xy.get(other_dangle_oid)
                    tx, ty = xy if xy is not None else (near_x, near_y)
                    target_angle = self._local_line_angle_cached(
                        dataset_key=lines_fc_key,
                        oid=int(other_parent),
                        polyline=tgt_poly,
                        x=float(tx),
                        y=float(ty),
                    )

        else:
            ext = polyline_by_external.get(ds_key, {})
            tgt_poly = ext.get(int(near_fid))
            if tgt_poly is not None:
                target_angle = self._local_line_angle_cached(
                    dataset_key=ds_key,
                    oid=int(near_fid),
                    polyline=tgt_poly,
                    x=near_x,
                    y=near_y,
                )

        if target_angle is None:
            # Unavailable => no block/penalty; conservative extra-dangle policy for dangle targets
            allow_extra = ds_key != dangles_fc_key
            return AngleAssessment(
                available=False,
                blocks=False,
                allow_extra_dangle=bool(allow_extra),
                angle_metric_deg=None,
                src_connector_diff=float(src_connector_diff),
            )

        connector_target_diff = self._orientation_diff(
            float(connector_angle), float(target_angle)
        )
        src_target_diff = self._orientation_diff(
            float(src_angle_deg), float(target_angle)
        )
        connector_transition_diff = 0.5 * (
            float(src_connector_diff) + float(connector_target_diff)
        )

        w = float(self.line_alignment_weight)
        connector_w = 1.0 - w
        line_match_diff = connector_w * float(connector_transition_diff) + w * float(
            src_target_diff
        )

        metric = float(line_match_diff)

        blocks = self.angle_block_threshold_degrees is not None and metric > float(
            self.angle_block_threshold_degrees
        )

        allow_extra = True
        if ds_key == dangles_fc_key:
            if self.angle_extra_dangle_threshold_degrees is None:
                allow_extra = True
            else:
                allow_extra = metric <= float(self.angle_extra_dangle_threshold_degrees)

        return AngleAssessment(
            available=True,
            blocks=bool(blocks),
            allow_extra_dangle=bool(allow_extra),
            angle_metric_deg=float(metric),
            src_connector_diff=float(src_connector_diff),
            connector_target_diff=float(connector_target_diff),
            src_target_diff=float(src_target_diff),
            connector_transition_diff=float(connector_transition_diff),
            line_match_diff=float(line_match_diff),
        )

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
        topology: TopologyModel | None = None,
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
                dangle_candidate_tol=base_tol,
                topology=topology,
            ):
                return cand
        return None

    def _find_best_dangle_candidate_to_parent(
        self,
        *,
        candidates_sorted: list[dict],
        dangles_fc_key: str,
        dangle_parent: dict[int, int],
        target_parent_id: int,
        dangle_tol: float,
    ) -> Optional[dict]:
        """
        From A's candidate rows, find the closest dangle feature that belongs to target_parent_id.
        This handles "target parent has 2 dangles" correctly by selecting the closest.
        """
        best = None
        best_dist = float("inf")

        for cand in candidates_sorted:
            if cand["near_fc_key"] != dangles_fc_key:
                continue

            other_dangle_oid = int(cand["near_fid"])
            other_parent = dangle_parent.get(other_dangle_oid)
            if other_parent is None:
                continue
            if int(other_parent) != int(target_parent_id):
                continue

            dist = float(cand["near_dist"])
            if dist <= float(dangle_tol) and dist < best_dist:
                best = cand
                best_dist = dist

        return best

    def _best_dangle_for_parent_towards_target_parent(
        self,
        *,
        parent_id: int,
        target_parent_id: int,
        parent_to_dangles: dict[int, list[int]],
        per_dangle: dict[int, dict],
    ) -> int | None:
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
        candidates_sorted: list[dict],
        dangles_fc_key: str,
        other_dangle_oid: int,
        dangle_tol: float,
    ) -> Optional[dict]:
        """
        Find candidate row that targets a specific dangle OID (within dangle_tol).
        """
        for cand in candidates_sorted:
            if cand["near_fc_key"] != dangles_fc_key:
                continue
            if int(cand["near_fid"]) != int(other_dangle_oid):
                continue

            dist = float(cand["near_dist"])
            if dist <= float(dangle_tol):
                return cand
        return None

    def _best_dangle_for_parent(
        self,
        *,
        parent_id: int,
        parent_to_dangles: dict[int, list[int]],
        per_dangle: dict[int, dict],
    ) -> int | None:
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

    # ----------------------------
    # Build plan (two-phase: detect pairs first, then decide moves)
    # ----------------------------

    def _build_plan(
        self, *, dangles_fc: str, target_layers: list[str]
    ) -> tuple[dict[int, list[dict]], dict[int, dict]]:
        dangle_parent = self._build_dangle_parent_lookup(dangles_fc=dangles_fc)
        dangle_xy = self._build_dangle_xy_lookup(dangles_fc=dangles_fc)

        relevant_parent_ids = set(dangle_parent.values())

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

        illegal = self.detect_illegal_targets(
            dangle_parent=dangle_parent,
            target_layers=target_layers,
            topology=topology,
        )

        dangles_key = self._dataset_key(dangles_fc)
        lines_key = self._dataset_key(self.lines_copy)

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

        # Expanded radius so we can see dangle→dangle candidates, but legality will enforce tol rules.
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

        if not grouped:
            return {}, {}

        # ----------------------------
        # Step 1A: collect legal candidates per dangle
        # ----------------------------
        legal_rows_by_dangle: dict[int, list[dict]] = {}
        parent_id_by_dangle: dict[int, int] = {}

        for dangle_oid in sorted(grouped.keys()):
            candidates = grouped[dangle_oid]
            dangle_oid = int(dangle_oid)

            parent_id = dangle_parent.get(dangle_oid)
            if parent_id is None:
                continue
            parent_id = int(parent_id)

            rows = sorted(candidates, key=self._candidate_sort_key)

            legal_rows: list[dict] = []
            for cand in rows:
                if self._candidate_is_legal(
                    illegal=illegal,
                    dangle_parent=dangle_parent,
                    dangles_fc_key=dangles_key,
                    lines_fc_key=lines_key,
                    parent_id=parent_id,
                    cand=cand,
                    base_tol=base_tol,
                    dangle_candidate_tol=dangle_tol,
                    topology=topology,
                ):
                    legal_rows.append(cand)

            if not legal_rows:
                continue

            legal_rows_by_dangle[dangle_oid] = legal_rows
            parent_id_by_dangle[dangle_oid] = parent_id

        if not legal_rows_by_dangle:
            return {}, {}
        # ----------------------------
        # Angle caches (new)
        # ----------------------------
        polyline_by_parent = self._build_polyline_by_parent_id()

        # External polyline caches keyed by dataset_key(layer)
        polyline_by_external: dict[str, dict[int, Any]] = {}
        is_external_line_like: dict[str, bool] = {}

        line_keys = (
            self._line_dataset_keys()
        )  # {dataset_key(lines_copy), dataset_key(target_self)}

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

        # ----------------------------
        # Best line parent per dangle (angle-aware)
        # Used by edge-case bonus detection.
        # ----------------------------
        best_line_parent_by_dangle = {}

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
                if str(cand["near_fc_key"]) != str(lines_key):
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
                    is_external_line_like=is_external_line_like,
                )
                if assess.blocks:
                    continue

                # Line targets do not use edge-case bonus.
                raw_dist = float(cand["near_dist"])
                _tol = float(self.gap_tolerance_meters) or 1.0
                _norm_d = raw_dist / _tol
                _norm_a = (float(assess.angle_metric_deg) / 90.0
                           if assess.angle_metric_deg is not None else 0.0)
                eff = (float(self.best_fit_weights.distance) * _norm_d
                       + float(self.best_fit_weights.angle) * _norm_a)

                # Deterministic tie-break:
                score = (float(eff), float(raw_dist), self._candidate_sort_key(cand))
                if best_score is None or score < best_score:
                    best_score = score
                    best = int(cand["near_fid"])

            if best is not None:
                best_line_parent_by_dangle[int(dangle_oid)] = int(best)
        # ----------------------------
        # Step 1B: choose exactly ONE proposal per dangle using angle-aware scoring
        # ----------------------------
        proposals_by_dangle: dict[int, Proposal] = {}
        assess_by_dangle: dict[int, AngleAssessment] = {}

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

            scored_candidates: list[
                tuple[
                    tuple[float, int, float, int, int, str, int],  # score tuple
                    dict,  # candidate
                    float,  # raw_distance
                    float,  # effective_distance_for_scoring
                    bool,  # bonus_applied
                    "AngleAssessment",  # assess for winning candidate metadata
                ]
            ] = []

            for cand in legal_rows:
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
                    is_external_line_like=is_external_line_like,
                )

                # 1) Candidate blocking (angle_block_threshold_degrees)
                if assess.blocks:
                    continue

                # 2) Expanded dangle tolerance gating (angle_extra_dangle_threshold_degrees)
                is_dangle_target = str(cand["near_fc_key"]) == str(dangles_key)
                dist = float(cand["near_dist"])

                if (
                    is_dangle_target
                    and dist > float(base_tol)
                    and not bool(assess.allow_extra_dangle)
                ):
                    # Candidate is only legal due to expanded tolerance; angle disallows it
                    continue

                # 3) Edge-case bonus eligibility is angle-controlled (and conservative when angle missing)
                bonus_allowed = True
                if is_dangle_target:
                    # conservative policy: if angle is unavailable => no expanded behavior, no bonus
                    bonus_allowed = bool(assess.available) and bool(
                        assess.allow_extra_dangle
                    )

                raw_distance, effective_distance, bonus_applied, score = (
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

                # 4) Normalized weighted composite score
                _tol = float(self.gap_tolerance_meters) or 1.0
                _norm_d = float(effective_distance) / _tol
                _norm_a = (float(assess.angle_metric_deg) / 90.0
                           if assess.angle_metric_deg is not None else 0.0)
                effective_for_scoring = (
                    float(self.best_fit_weights.distance) * _norm_d
                    + float(self.best_fit_weights.angle) * _norm_a
                )

                # Keep score tuple shape stable; only replace the first element
                score_with_angle = (
                    float(effective_for_scoring),
                    int(score[1]),
                    float(score[2]),
                    int(score[3]),
                    int(score[4]),
                    str(score[5]),
                    int(score[6]),
                )

                scored_candidates.append(
                    (
                        score_with_angle,
                        cand,
                        float(raw_distance),
                        float(effective_for_scoring),
                        bool(bonus_applied),
                        assess,
                    )
                )

            if not scored_candidates:
                continue

            (
                score,
                chosen,
                raw_distance,
                effective_distance_for_scoring,
                bonus_applied,
                chosen_assess,
            ) = min(
                scored_candidates,
                key=lambda item: item[0],
            )

            # ----------------------------
            # Proposal construction (unchanged semantics)
            # ----------------------------
            src_node = self._node_for_parent(parent_id=parent_id, topology=topology)

            target_parent_id: Optional[int] = None
            target_dangle_oid: Optional[int] = None

            ds_key = str(chosen["near_fc_key"])
            near_fid = int(chosen["near_fid"])

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

            proposals_by_dangle[dangle_oid] = Proposal(
                dangle_oid=dangle_oid,
                src_parent_id=parent_id,
                src_node=src_node,
                tgt_node=tgt_node,
                chosen=chosen,
                raw_distance=float(raw_distance),
                best_fit_score=float(effective_distance_for_scoring),
                bonus_applied=bool(bonus_applied),
                score=score,
                pair_key=pair_key,
                target_parent_id=target_parent_id,
                target_dangle_oid=target_dangle_oid,
            )
            assess_by_dangle[dangle_oid] = chosen_assess

        if not proposals_by_dangle:
            return {}, {}

        # ----------------------------
        # Mutual detection (for labeling)
        # - dangle mutual pairs: D1 targets D2 AND D2 targets D1 (both dangle targets)
        # - network mutual: any proposal exists in both directions between the two network nodes
        # ----------------------------
        parents_with_dangles = sorted(set(dangle_parent.values()))
        parents_with_dangles_set = {int(v) for v in parents_with_dangles}

        outgoing_parent_targets: dict[int, set[int]] = {}
        for p in proposals_by_dangle.values():
            if p.target_parent_id is None:
                continue
            outgoing_parent_targets.setdefault(int(p.src_parent_id), set()).add(
                int(p.target_parent_id)
            )

        deferred_by_parent: dict[int, dict] = {}
        deferred_score_by_parent: dict[int, tuple] = {}
        deferred_dangles: set[int] = set()

        for p in proposals_by_dangle.values():
            b_parent = p.target_parent_id
            if b_parent is None:
                continue
            b_parent = int(b_parent)

            # Only defer when the target parent has dangles in this run
            if b_parent not in parents_with_dangles_set:
                continue

            # No reciprocal proposal from B -> A (parent-id space)
            b_out = outgoing_parent_targets.get(b_parent, set())
            if int(p.src_parent_id) in b_out:
                continue

            # Keep only one deferred per parent (deterministic: best score)
            cur_best = deferred_score_by_parent.get(int(p.src_parent_id))
            if cur_best is None or p.score < cur_best:
                deferred_by_parent[int(p.src_parent_id)] = {
                    "parent_id": int(p.src_parent_id),
                    "dangle_oid": int(p.dangle_oid),
                    "forced_target_parent": int(b_parent),
                }
                deferred_score_by_parent[int(p.src_parent_id)] = p.score
                deferred_dangles.add(int(p.dangle_oid))

        # Active proposals exclude deferred dangles (no fallback)
        active: list[Proposal] = [
            p
            for d_oid, p in proposals_by_dangle.items()
            if int(d_oid) not in deferred_dangles
        ]
        if not active:
            return {}, deferred_by_parent
        active_by_dangle = {int(p.dangle_oid): p for p in active}

        dangle_mutual_oids: set[int] = set()
        for p in active:
            if p.target_dangle_oid is None:
                continue
            q = active_by_dangle.get(int(p.target_dangle_oid))
            if q is None or q.target_dangle_oid is None:
                continue
            if int(q.target_dangle_oid) == int(p.dangle_oid):
                dangle_mutual_oids.add(int(p.dangle_oid))
                dangle_mutual_oids.add(int(q.dangle_oid))

        directed_network_edges: set[tuple[EntityKey, EntityKey]] = {
            (p.src_node, p.tgt_node) for p in active
        }

        # ----------------------------
        # Stage A: one winner per unordered network pair
        # ----------------------------
        by_pair: dict[tuple[EntityKey, EntityKey], list[Proposal]] = {}
        for p in active:
            by_pair.setdefault(p.pair_key, []).append(p)

        stage_a_winners: list[tuple[Proposal, str]] = []
        for pair_key in sorted(by_pair.keys()):
            group = by_pair[pair_key]
            winner = min(group, key=lambda pr: pr.score)

            a_node, b_node = pair_key
            mutual_network = (a_node, b_node) in directed_network_edges and (
                b_node,
                a_node,
            ) in directed_network_edges

            if (
                winner.target_dangle_oid is not None
                and int(winner.dangle_oid) in dangle_mutual_oids
            ):
                gap_source = self.GAP_SOURCE_PAIR_DANGLE
            elif mutual_network:
                gap_source = self.GAP_SOURCE_PAIR_LINE
            else:
                gap_source = self.GAP_SOURCE_DEFAULT

            stage_a_winners.append((winner, str(gap_source)))

        # ----------------------------
        # Stage B: Kruskal-style cycle prevention (component scopes only)
        # ----------------------------
        scope = topology.scope
        accepted: list[tuple[Proposal, str]] = []

        if scope in (
            logic_config.ConnectivityScope.INPUT_LINES,
            logic_config.ConnectivityScope.ONE_DEGREE,
            logic_config.ConnectivityScope.TRANSITIVE,
        ):
            uf = _UnionFind()
            for prop, gap_source in sorted(stage_a_winners, key=lambda t: t[0].score):
                if uf.find(prop.src_node) == uf.find(prop.tgt_node):
                    continue
                uf.union(prop.src_node, prop.tgt_node)
                accepted.append((prop, gap_source))
        else:
            # NONE / DIRECT_CONNECTION: only Stage A
            accepted = list(stage_a_winners)

        if not accepted:
            return {}, deferred_by_parent

        # ----------------------------
        # Build plan_by_parent: parent_id -> list[plan_entry]
        # ----------------------------
        tmp: dict[int, list[tuple[tuple, dict]]] = {}

        for prop, gap_source in sorted(accepted, key=lambda t: t[0].score):
            xy = dangle_xy.get(int(prop.dangle_oid))
            if xy is None:
                continue
            d_x, d_y = xy

            entry = self._make_plan_entry(
                parent_id=int(prop.src_parent_id),
                dangle_oid=int(prop.dangle_oid),
                dangle_x=float(d_x),
                dangle_y=float(d_y),
                chosen=prop.chosen,
                gap_source=str(gap_source),
                bonus_applied=prop.bonus_applied,
                assess=assess_by_dangle.get(int(prop.dangle_oid)),
                best_fit_score=prop.best_fit_score,
            )

            tmp.setdefault(int(prop.src_parent_id), []).append((prop.score, entry))

        plan_by_parent: dict[int, list[dict]] = {}
        for pid, items in tmp.items():
            # Deterministic per-parent order
            ordered = sorted(
                items, key=lambda t: (t[0], int(t[1].get("dangle_oid", 0)))
            )
            plan_by_parent[int(pid)] = [entry for _, entry in ordered]

        return plan_by_parent, deferred_by_parent

    def _make_plan_entry(
        self,
        *,
        parent_id: int,
        dangle_oid: int,
        dangle_x: float,
        dangle_y: float,
        chosen: dict,
        gap_source: str,
        bonus_applied: bool = False,
        assess: "Optional[AngleAssessment]" = None,
        best_fit_score: Optional[float] = None,
    ) -> dict:
        edit_op = self._resolve_edit_op(gap_source=str(gap_source))
        entry: dict = {
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
        if self.write_output_metadata:
            entry["meta_bonus_applied"] = int(bonus_applied)
            if assess is not None:
                entry["meta_src_connector_diff"] = assess.src_connector_diff
                entry["meta_connector_target_diff"] = assess.connector_target_diff
                entry["meta_src_target_diff"] = assess.src_target_diff
                entry["meta_connector_transition_diff"] = assess.connector_transition_diff
                entry["meta_line_match_diff"] = assess.line_match_diff
                entry["meta_angle_metric_deg"] = assess.angle_metric_deg
                entry["meta_best_fit_score"] = best_fit_score
        return entry

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

    def _build_deferred_plan(
        self,
        *,
        deferred: dict[int, dict],
        dangles_fc: str,
    ) -> dict[int, dict]:
        # Deferred dangles layer
        dangles_oid = arcpy.Describe(dangles_fc).OIDFieldName
        dangle_oids = sorted({int(v["dangle_oid"]) for v in deferred.values()})
        if not dangle_oids:
            return {}

        where_d = f"{arcpy.AddFieldDelimiters(dangles_fc, dangles_oid)} IN ({','.join(map(str, dangle_oids))})"
        deferred_lyr = "deferred_dangles_lyr"
        arcpy.management.MakeFeatureLayer(dangles_fc, deferred_lyr, where_d)

        # Locked forced-target lines layer (UPDATED geometry because pass 1 already ran)
        forced_parents = sorted(
            {int(v["forced_target_parent"]) for v in deferred.values()}
        )
        where_l = f"{arcpy.AddFieldDelimiters(self.lines_copy, self.ORIGINAL_ID)} IN ({','.join(map(str, forced_parents))})"
        forced_lines_lyr = "forced_lines_lyr"
        arcpy.management.MakeFeatureLayer(self.lines_copy, forced_lines_lyr, where_l)

        # Map near OID -> parent id (do NOT assume OID == ORIGINAL_ID)
        lines_oid = arcpy.Describe(forced_lines_lyr).OIDFieldName
        near_oid_to_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            forced_lines_lyr, [lines_oid, self.ORIGINAL_ID]
        ) as cur:
            for oid, pid in cur:
                near_oid_to_parent[int(oid)] = int(pid)

        # Large tolerance (keep your current heuristic)
        large_m = max(50, int(self.gap_tolerance_meters) * 10)
        large_tol = f"{int(large_m)} Meters"

        forced_table = self.wfm.build_file_path(file_name="deferred_forced_table")
        arcpy.analysis.GenerateNearTable(
            in_features=deferred_lyr,
            near_features=[forced_lines_lyr],
            out_table=forced_table,
            search_radius=large_tol,
            location="LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

        # Best near point per (dangle_oid, forced_parent)
        best_xy: dict[tuple[int, int], tuple[float, float, float]] = {}  # -> (x,y,dist)
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
                d_oid = int(in_fid)
                near_parent = near_oid_to_parent.get(int(near_fid))
                if near_parent is None:
                    continue

                dist = float(near_dist)
                key = (d_oid, int(near_parent))
                prev = best_xy.get(key)
                if prev is None or dist < prev[2]:
                    best_xy[key] = (float(near_x), float(near_y), dist)

        if not best_xy:
            return {}

        # Dangle XY (only build once)
        dangle_xy = self._build_dangle_xy_lookup(dangles_fc)

        lines_key = self._dataset_key(self.lines_copy)
        out: dict[int, dict] = {}

        for a_parent, info in deferred.items():
            a_parent = int(a_parent)
            d_oid = int(info["dangle_oid"])
            forced_parent = int(info["forced_target_parent"])

            hit = best_xy.get((d_oid, forced_parent))
            if hit is None:
                continue

            dxy = dangle_xy.get(d_oid)
            if dxy is None:
                continue
            dangle_x, dangle_y = dxy

            near_x, near_y, _ = hit

            out[a_parent] = {
                "processed": False,
                "skip": False,
                "gap_source": self.GAP_SOURCE_DEFERRED,
                "edit_op": str(
                    self._resolve_edit_op(gap_source=self.GAP_SOURCE_DEFERRED).value
                ),
                "dangle_oid": d_oid,
                "dangle_x": float(dangle_x),
                "dangle_y": float(dangle_y),
                "near_x": float(near_x),
                "near_y": float(near_y),
                "chosen_near_fc_key": lines_key,
                "chosen_near_fid": forced_parent,  # parent-id space, consistent with your plan
            }

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
            "line_match_diff",
            "angle_metric_deg",
            "best_fit_score",
        ]
        for fname in meta_double_fields:
            if fname not in existing:
                arcpy.management.AddField(self.line_changes_output, fname, "DOUBLE")

        if "bonus_applied" not in existing:
            arcpy.management.AddField(self.line_changes_output, "bonus_applied", "SHORT")

    def _build_change_row(
        self,
        original_id: int,
        dangle_x: float,
        dangle_y: float,
        near_x: float,
        near_y: float,
        spatial_reference,
        gap_source: str,
        meta: Optional[dict] = None,
    ):
        dist = ((dangle_x - near_x) ** 2 + (dangle_y - near_y) ** 2) ** 0.5
        if dist == 0.0:
            return None

        arr = arcpy.Array(
            [arcpy.Point(dangle_x, dangle_y), arcpy.Point(near_x, near_y)]
        )
        geom = arcpy.Polyline(arr, spatial_reference)
        row = [geom, int(original_id), float(dist), str(gap_source)]
        if meta is not None:
            row.extend([
                meta.get("meta_src_connector_diff"),
                meta.get("meta_connector_target_diff"),
                meta.get("meta_src_target_diff"),
                meta.get("meta_connector_transition_diff"),
                meta.get("meta_line_match_diff"),
                meta.get("meta_angle_metric_deg"),
                meta.get("meta_best_fit_score"),
                meta.get("meta_bonus_applied"),
            ])
        return tuple(row)

    def _apply_plan(self, plan) -> None:
        if not plan:
            return

        spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
        change_rows: list[tuple] = []

        def _as_entries(value) -> list[dict]:
            # Backwards compatible: allow dict (single) or list[dict] (multi)
            if value is None:
                return []
            if isinstance(value, list):
                return [v for v in value if isinstance(v, dict)]
            if isinstance(value, dict):
                return [value]
            return []

        with arcpy.da.UpdateCursor(
            self.lines_copy, [self.ORIGINAL_ID, "SHAPE@"]
        ) as cur:
            for original_id, shape in cur:
                pid = int(original_id)
                entries = _as_entries(plan.get(pid))
                if not entries:
                    continue

                pending = [
                    e
                    for e in entries
                    if not e.get("skip", False) and not e.get("processed", False)
                ]
                if not pending:
                    continue

                current_shape = shape

                for info in pending:
                    edit_op = str(info.get("edit_op", EditOp.EXTEND.value))

                    if edit_op == EditOp.SNAP.value:
                        current_shape = self._snap_endpoint(
                            shape=current_shape,
                            dangle_x=float(info["dangle_x"]),
                            dangle_y=float(info["dangle_y"]),
                            near_x=float(info["near_x"]),
                            near_y=float(info["near_y"]),
                        )
                    else:
                        current_shape = self._extend_endpoint(
                            shape=current_shape,
                            dangle_x=float(info["dangle_x"]),
                            dangle_y=float(info["dangle_y"]),
                            near_x=float(info["near_x"]),
                            near_y=float(info["near_y"]),
                        )

                    info["processed"] = True

                    if self.line_changes_output is not None and self.write_output_metadata:
                        meta = {k: info.get(k) for k in (
                            "meta_src_connector_diff",
                            "meta_connector_target_diff",
                            "meta_src_target_diff",
                            "meta_connector_transition_diff",
                            "meta_line_match_diff",
                            "meta_angle_metric_deg",
                            "meta_best_fit_score",
                            "meta_bonus_applied",
                        )} if any(k in info for k in (
                            "meta_src_connector_diff",
                            "meta_angle_metric_deg",
                            "meta_bonus_applied",
                        )) else None
                        row = self._build_change_row(
                            original_id=pid,
                            dangle_x=float(info["dangle_x"]),
                            dangle_y=float(info["dangle_y"]),
                            near_x=float(info["near_x"]),
                            near_y=float(info["near_y"]),
                            spatial_reference=spatial_reference,
                            gap_source=str(
                                info.get("gap_source", self.GAP_SOURCE_DEFAULT)
                            ),
                            meta=meta,
                        )
                        if row is not None:
                            change_rows.append(row)

                cur.updateRow((original_id, current_shape))

        if self.line_changes_output is not None and self.write_output_metadata and change_rows:
            meta_fields = [
                "src_connector_diff",
                "connector_target_diff",
                "src_target_diff",
                "connector_transition_diff",
                "line_match_diff",
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
                ] + meta_fields,
            ) as icur:
                for row in change_rows:
                    if len(row) == 4:
                        # Deferred / polygon rows — no metadata; pad with None
                        row = row + (None,) * len(meta_fields)
                    icur.insertRow(row)

    def _write_output(self) -> None:
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

        if self.line_changes_output is not None and self.write_output_metadata:
            if arcpy.Exists(self.line_changes_output):
                arcpy.management.Delete(self.line_changes_output)
            self._setup_line_changes_output()

        plan, deferred = self._build_plan(
            dangles_fc=dangles_for_plan, target_layers=targets
        )

        self._apply_plan(plan)

        if deferred:
            deferred_plan = self._build_deferred_plan(
                deferred=deferred, dangles_fc=dangles_for_plan
            )
            self._apply_plan(deferred_plan)

        self._write_output()

        self.wfm.delete_created_files()
