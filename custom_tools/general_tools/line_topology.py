from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math
import os

from typing import Optional, Callable, Iterable, Any, TypeAlias

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
    dangle_oid: int
    src_parent_id: int
    src_node: "EntityKey"
    tgt_node: "EntityKey"
    pair_key: "tuple[EntityKey, EntityKey]"
    target_parent_id: Optional[int]
    target_dangle_oid: Optional[int]
    near_fc_key: str
    near_fid: int
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
    assess: Optional["AngleAssessment"]


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
    """Stage-A candidate; Z normalized within its pair_key group."""

    ctx: "_CandidateContext"
    dangle_norm_z: Optional[float]  # carried from _DangleProposal.score.norm_z
    score: "_ProposalScore"  # score.norm_z = connection_norm_z

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

    @classmethod
    def from_network(
        cls, n: "_ConnectionProposal", score: "_ProposalScore"
    ) -> "_GlobalProposal":
        return cls(
            ctx=n.ctx,
            dangle_norm_z=n.dangle_norm_z,
            connection_norm_z=n.score.norm_z,
            score=score,
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
class _ResnappedCapture:
    """
    Metadata for an accepted connection whose near-point may land on a segment
    that moves when another accepted SNAP connection applies.

    Identified after Stage B; geometry is re-resolved in _resnap_connections
    using post-apply lines_copy geometry.
    """

    parent_id: int
    dangle_oid: int
    forced_target_parent: int  # target_parent_id of the accepted connection
    proposal: "_GlobalProposal"
    gap_source: str


@dataclass(frozen=True)
class AngleAssessment:
    # Primary decisions
    available: bool
    blocks: bool
    allow_extra_dangle: bool  # expanded dangle tol + edge-case bonus
    angle_metric_deg: Optional[float]
    # Normalisation range for angle_metric_deg used in best-fit scoring.
    # 90.0 for undirected targets; 180.0 for directional dangle-pair targets.
    angle_max_deg: float = 90.0

    # Diagnostics (optional)
    src_connector_diff: Optional[float] = None
    connector_target_diff: Optional[float] = None
    src_target_diff: Optional[float] = None
    connector_transition_diff: Optional[float] = None


@dataclass
class CandidateDiagnostic:
    """
    Diagnostic record for one candidate connection evaluated during the main planning phase.

    One record exists per (dangle, target) pair, excluding the self parent line target.
    The dataclass is mutable so that resnap outcomes can be patched by run()
    after _resnap_connections resolves.

    candidate_status values:
        "illegal"             — failed legality or angle blocking; could not be selected
        "legal_not_selected"  — passed legality but lost to a better scored candidate
                               within the same dangle
        "selected_for_dangle" — was the local best candidate for its dangle but did not
                               survive later pipeline stages to become applied output
        "applied_to_output"   — truly survived the full pipeline and was applied to geometry

    status_reason values per status:
        illegal:              beyond_distance_tolerance | same_network | illegal_target |
                              blocked_by_angle | expanded_dangle_angle_disallowed |
                              blocked_by_z_drop
        legal_not_selected:   outscored_within_dangle
        selected_for_dangle:  lost_connection_selection | lost_kruskal_selection
        applied_to_output:    applied_main | applied_resnapped
    """

    parent_id: int
    dangle_oid: int
    dangle_x: float
    dangle_y: float
    near_fc_key: str
    near_fid: int
    near_x: float
    near_y: float
    raw_distance: float
    candidate_status: str  # see class docstring
    status_reason: Optional[str]  # see class docstring; None only for rare edge cases
    best_fit_score: Optional[float]
    best_fit_rank: Optional[int]  # 1 = local dangle winner; higher = lower-ranked legal
    bonus_applied: Optional[bool]
    assess: Optional[AngleAssessment]
    target_parent_id: Optional[int]
    final_gap_source: Optional[
        str
    ]  # gap_source value for applied_to_output rows; None otherwise
    start_z: Optional[float] = (
        None  # Z at the dangle point (candidate start); None when no rasters
    )
    end_z: Optional[float] = (
        None  # Z at the near point (candidate end); None when no rasters
    )
    dangle_norm_z: Optional[float] = (
        None  # Z normalized within dangle candidate set; None for illegals
    )
    connection_norm_z: Optional[float] = (
        None  # Z normalized within pair_key group; None for illegals/deferred
    )
    global_norm_z: Optional[float] = (
        None  # Z normalized across all Stage-A winners; None unless Stage-B reached
    )


# ---------------------------------------------------------------------------
# Pipeline type aliases
# ---------------------------------------------------------------------------
_DangleXYsByParent: TypeAlias = dict[int, list[tuple[float, float]]]
_IllegalTargets: TypeAlias = dict[int, dict[str, set[int]]]
_CandRow: TypeAlias = dict[str, Any]
_Grouped: TypeAlias = dict[int, list[_CandRow]]
_NormZByDangle: TypeAlias = dict[int, Optional[float]]
_ConnectionWithSource: TypeAlias = tuple[_ConnectionProposal, str]
_GlobalWithSource: TypeAlias = tuple[_GlobalProposal, str]
# (dangle_oid, dangle_x, dangle_y, near_x, near_y)
_AcceptedConnectorRaw: TypeAlias = tuple[int, float, float, float, float]
# Diagnostic collection tuples (produced in _select_dangle_proposals, consumed in _assemble_diagnostics)
_Step1AIllegalEntry: TypeAlias = tuple[int, int, _CandRow, str]
_Step1BIllegalEntry: TypeAlias = tuple[
    int, int, _CandRow, AngleAssessment, str, Optional[float], Optional[float]
]
_Step1BScoredEntry: TypeAlias = tuple[
    int,
    int,
    _CandRow,
    AngleAssessment,
    float,
    float,
    bool,
    bool,
    tuple[float, int, float],
    Optional[float],
    Optional[float],
    Optional[float],
]


class FillLineGaps:
    ORIGINAL_ID = "line_gap_original_id"

    # Change output fields
    FIELD_GAP_DIST_M = "gap_dist_m"
    FIELD_GAP_SOURCE = "gap_source"

    GAP_SOURCE_DEFAULT = "default"
    GAP_SOURCE_PAIR_DANGLE = "pair_dangle"
    GAP_SOURCE_PAIR_LINE = "pair_line"

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
        out = line_gap_config.output_config
        ang = line_gap_config.angle_config
        z = line_gap_config.z_config
        cross = line_gap_config.crossing_config
        conn = line_gap_config.connectivity_config

        self.fill_gaps_on_self = bool(line_gap_config.fill_gaps_on_self)
        self.best_fit_weights = line_gap_config.best_fit_weights

        self.line_changes_output = out.line_changes_output
        self.write_output_metadata = bool(out.write_output_metadata)
        self.candidate_connections_output = out.candidate_connections_output

        self.increased_tolerance_edge_case_distance_meters = int(
            adv.increased_tolerance_edge_case_distance_meters
        )
        self.require_mutual_dangle_preference_for_bonus = bool(
            adv.require_mutual_dangle_preference_for_bonus
        )
        self.edit_method = logic_config.EditMethod(adv.edit_method)

        self.connectivity_scope = logic_config.ConnectivityScope(conn.connectivity_scope)
        self.connectivity_tolerance_meters = float(conn.connectivity_tolerance_meters)
        self.line_connectivity_mode = logic_config.LineConnectivityMode(
            conn.line_connectivity_mode
        )

        if self.connect_to_features is None and self.fill_gaps_on_self is False:
            raise ValueError(
                "Invalid config: fill_gaps_on_self cannot be False when connect_to_features is None."
            )

        self.lines_are_directed: bool = bool(ang.lines_are_directed)
        self.dangle_pair_apply_connector_diff: bool = bool(
            ang.dangle_pair_apply_connector_diff
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

    def _mutual_dangle_preference(
        self,
        *,
        dangle_oid: int,
        other_dangle_oid: int,
        dangle_parent: dict[int, int],
        best_line_parent_by_dangle: dict[int, int],
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
        dangle_oid: int,
        cand: dict,
        dangles_fc_key: str,
        dangle_parent: dict[int, int],
        best_line_parent_by_dangle: dict[int, int],
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

        if str(cand["near_fc_key"]) != str(dangles_fc_key):
            return False

        if not self.require_mutual_dangle_preference_for_bonus:
            return True

        return self._mutual_dangle_preference(
            dangle_oid=dangle_oid,
            other_dangle_oid=int(cand["near_fid"]),
            dangle_parent=dangle_parent,
            best_line_parent_by_dangle=best_line_parent_by_dangle,
        )

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

    def _directed_start_dangle_oids(
        self,
        *,
        dangle_xy: dict[int, tuple[float, float]],
        dangle_parent: dict[int, int],
        polyline_by_parent: dict[int, Any],
    ) -> set[int]:
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
        legal_rows_by_dangle: "_Grouped",
        dangle_xy: dict[int, tuple[float, float]],
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
                near_fc_key = str(cand["near_fc_key"])
                near_fid = int(cand["near_fid"])
                key = (dangle_oid, near_fc_key, near_fid)

                trimmed = self._build_trimmed_connector(
                    from_x=from_x,
                    from_y=from_y,
                    to_x=float(cand["near_x"]),
                    to_y=float(cand["near_y"]),
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
        legal_rows_by_dangle: "_Grouped",
        dangle_xy: dict[int, tuple[float, float]],
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
                key = (dangle_oid, str(cand["near_fc_key"]), int(cand["near_fid"]))
                trimmed = self._build_trimmed_connector(
                    from_x=from_x,
                    from_y=from_y,
                    to_x=float(cand["near_x"]),
                    to_y=float(cand["near_y"]),
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
        line_like_ds_keys: set[str],
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
        illegal: dict[int, dict[str, set[int]]],
        dangle_parent: dict[int, int],
        dangles_fc_key: str,
        lines_fc_key: str,
        line_like_ds_keys: set[str],
        parent_id: int,
        cand: dict,
        base_tol: float,
        dangle_candidate_tol: float,
        topology: "TopologyModel | None",
    ) -> str:
        """Return the legality-failure reason for a candidate, mirroring _candidate_is_legal."""
        ds_key = cand["near_fc_key"]
        oid = int(cand["near_fid"])
        dist = float(cand["near_dist"])

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
        cand: dict,
        dangle_parent: dict[int, int],
        dangles_fc_key: str,
        lines_fc_key: str,
    ) -> Optional[int]:
        """Return the target parent original ID for a candidate, or None for external targets."""
        ds_key = str(cand["near_fc_key"])
        near_fid = int(cand["near_fid"])
        if ds_key == dangles_fc_key:
            return dangle_parent.get(near_fid)
        if ds_key == lines_fc_key:
            return near_fid  # already in ORIGINAL_ID space
        return None

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
        dangle_xys_by_parent: Optional[_DangleXYsByParent] = None,
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
            self.lines_are_directed
            or _is_dangle_pair
            or _is_dangle_parent_line
        )

        if _use_directional:
            _diff = self._directional_diff
            angle_max_deg = 180.0

            src_poly_for_norm = polyline_by_parent.get(int(src_parent_id))
            _endpoint_snap = _is_dangle_pair or _is_dangle_parent_line
            # In directed mode: always use raw forward direction (no flip).
            # The topology check handles endpoint snaps; for mid-line snaps, raw angles
            # give consistent directionality across all target types.
            # In undirected mode: flip if at start so src points "exit toward gap"
            # for symmetric dangle-pair scoring.
            if src_poly_for_norm is not None and src_angle_deg is not None:
                if not self.lines_are_directed:
                    if self._xy_is_at_line_start(src_poly_for_norm, dangle_x, dangle_y):
                        src_angle_deg = (float(src_angle_deg) + 180.0) % 360.0

            # In undirected mode (_use_directional triggered by dangle-pair / dangle-parent-line):
            # normalise target_angle to "entry direction into target interior" so that both
            # dangles in a pair score symmetrically (0° for a good collinear fill).
            # In directed mode: leave target_angle as the raw flow direction of the target
            # line at the snap point. The source exits toward the gap; the target should flow
            # in the same direction for a good match — flipping would collapse the score to
            # 0° for both dangles regardless of their relative orientation.
            if not self.lines_are_directed:
                _tgt_snap_x = float(tx) if _is_dangle_pair else float(near_x)
                _tgt_snap_y = float(ty) if _is_dangle_pair else float(near_y)
                if not self._xy_is_at_line_start(tgt_poly, _tgt_snap_x, _tgt_snap_y):
                    target_angle = (float(target_angle) + 180.0) % 360.0
            # In directed mode, override src_connector_diff to use directional diff
            # so that anti-parallel src/connector (e.g. west vs east) reports 180° (BAD)
            # rather than collapsing to 0° under orientation_diff.
            # Undirected mode keeps the orientation-based value computed earlier.
            if self.lines_are_directed:
                src_connector_diff = self._directional_diff(
                    float(src_angle_deg), float(connector_angle)
                )
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

        if _use_directional:
            if self.lines_are_directed and _endpoint_snap:
                # Topology-aware metric: only end→start is a valid directional connection.
                # "Opposite attracts": src_is_end AND target_is_start → use direction diff.
                # All other combinations (end→end, start→start, start→end) → 180° (BAD).
                _snap_x = float(tx) if _is_dangle_pair else float(near_x)
                _snap_y = float(ty) if _is_dangle_pair else float(near_y)
                _src_is_end = (
                    src_poly_for_norm is not None
                    and not self._xy_is_at_line_start(
                        src_poly_for_norm, dangle_x, dangle_y
                    )
                )
                _tgt_is_start = self._xy_is_at_line_start(tgt_poly, _snap_x, _snap_y)
                if _src_is_end and _tgt_is_start:
                    metric = (
                        max(float(src_target_diff), float(src_connector_diff))
                        if self.dangle_pair_apply_connector_diff and _is_dangle_pair
                        else float(src_target_diff)
                    )
                else:
                    metric = 180.0
            elif self.lines_are_directed:
                # Non-endpoint line-like target: worst of angular alignment vs connector
                # direction — a bad score on either component makes the candidate bad.
                metric = max(float(src_target_diff), float(src_connector_diff))
            else:
                # Undirected dangle-pair / dangle-parent-line after both normalizations.
                metric = float(src_target_diff)
        else:
            metric = float(src_connector_diff)

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
            angle_max_deg=float(angle_max_deg),
            src_connector_diff=float(src_connector_diff),
            connector_target_diff=float(connector_target_diff),
            src_target_diff=float(src_target_diff),
            connector_transition_diff=float(connector_transition_diff),
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

    def _build_plan(self, *, dangles_fc: str, target_layers: list[str]) -> tuple[
        dict[int, list[dict]],
        list["_ResnappedCapture"],
        list["CandidateDiagnostic"],
        list[
            _AcceptedConnectorRaw
        ],  # accepted_connector_raw (for resnap crossing re-check)
        dict[int, int],  # kruskal_rank_by_dangle_oid (for resnap crossing re-check)
    ]:
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
            return {}, [], [], [], {}

        collect_diags = self.candidate_connections_output is not None

        # ----------------------------
        # Angle caches
        # ----------------------------
        polyline_by_parent = self._build_polyline_by_parent_id()

        # External polyline caches and line-type map, keyed by dataset_key(layer).
        # Built before candidate filtering so line_like_ds_keys is available.
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

        # ds_keys for line-like targets that receive the expanded tolerance.
        # Self-lines are included only when fill_gaps_on_self is active (otherwise no
        # candidates with lines_key appear in the near table anyway).
        line_like_external_ds_keys: set[str] = {
            ds_key for ds_key, is_line in is_external_line_like.items() if is_line
        }
        line_like_ds_keys: set[str] = line_like_external_ds_keys.copy()
        if self.fill_gaps_on_self:
            line_like_ds_keys.add(lines_key)

        # In directed mode, source dangles at a line's start node are invalid sources.
        # polyline_by_parent is already built above; dangle_xy was built at the top.
        directed_start_dangles = self._directed_start_dangle_oids(
            dangle_xy=dangle_xy,
            dangle_parent=dangle_parent,
            polyline_by_parent=polyline_by_parent,
        )

        # ----------------------------
        # Dangle filtering: collect legal candidates per dangle
        # ----------------------------
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

        # ----------------------------
        # Crossing conflict pre-filter (last legality check)
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

        if self.barrier_layers and legal_rows_by_dangle and _crossing_sr is not None:
            _barrier_keys = self._find_barrier_crossing_keys(
                legal_rows_by_dangle=legal_rows_by_dangle,
                dangle_xy=dangle_xy,
                barrier_layers=self.barrier_layers,
                trim_distance=_crossing_trim,
                spatial_reference=_crossing_sr,
            )
            if _barrier_keys:
                for _dangle_oid in list(legal_rows_by_dangle.keys()):
                    _parent_id = parent_id_by_dangle[_dangle_oid]
                    _remaining: list[dict] = []
                    for _cand in legal_rows_by_dangle[_dangle_oid]:
                        _cand_key = (
                            _dangle_oid,
                            str(_cand["near_fc_key"]),
                            int(_cand["near_fid"]),
                        )
                        if _cand_key in _barrier_keys:
                            if collect_diags:
                                _step1a_illegal.append(
                                    (
                                        _dangle_oid,
                                        _parent_id,
                                        _cand,
                                        "crosses_barrier_layer",
                                    )
                                )
                        else:
                            _remaining.append(_cand)
                    if _remaining:
                        legal_rows_by_dangle[_dangle_oid] = _remaining
                    else:
                        del legal_rows_by_dangle[_dangle_oid]
                        parent_id_by_dangle.pop(_dangle_oid, None)

        trimmed_connector_cache: dict[tuple[int, str, int], Any] = {}
        if self.reject_crossing_connectors and legal_rows_by_dangle and _crossing_sr is not None:
            # lines_copy provides self-line geometries; external polyline layers
            # whose ds_key is in polyline_by_external were loaded as angle caches.
            _check_layers: list[str] = [self.lines_copy]
            for _lyr in target_layers:
                if self._dataset_key(_lyr) in polyline_by_external:
                    _check_layers.append(_lyr)
            crossing_conflict_keys, trimmed_connector_cache = (
                self._find_crossing_conflict_keys(
                    legal_rows_by_dangle=legal_rows_by_dangle,
                    dangle_xy=dangle_xy,
                    check_feature_layers=_check_layers,
                    trim_distance=_crossing_trim,
                    spatial_reference=_crossing_sr,
                )
            )
            if crossing_conflict_keys:
                for _dangle_oid in list(legal_rows_by_dangle.keys()):
                    _parent_id = parent_id_by_dangle[_dangle_oid]
                    _remaining: list[dict] = []
                    for _cand in legal_rows_by_dangle[_dangle_oid]:
                        _cand_key = (
                            _dangle_oid,
                            str(_cand["near_fc_key"]),
                            int(_cand["near_fid"]),
                        )
                        if _cand_key in crossing_conflict_keys:
                            if collect_diags:
                                _step1a_illegal.append(
                                    (
                                        _dangle_oid,
                                        _parent_id,
                                        _cand,
                                        "crosses_existing_feature",
                                    )
                                )
                        else:
                            _remaining.append(_cand)
                    if _remaining:
                        legal_rows_by_dangle[_dangle_oid] = _remaining
                    else:
                        del legal_rows_by_dangle[_dangle_oid]
                        parent_id_by_dangle.pop(_dangle_oid, None)

        if not legal_rows_by_dangle:
            return (
                {},
                [],
                self._assemble_diagnostics(
                    collect_diags=collect_diags,
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=[],
                    step1b_scored=[],
                    connection_loser_oids=set(),
                    kruskal_rejected_oids=set(),
                    kruskal_crossing_rejected_oids=set(),
                    accepted_dangle_oids=set(),
                    gap_source_by_dangle={},
                    dangle_norm_z_by_dangle={},
                    connection_norm_z_by_dangle={},
                    global_norm_z_by_dangle={},
                    dangle_xy=dangle_xy,
                    dangle_parent=dangle_parent,
                    dangles_key=dangles_key,
                    lines_key=lines_key,
                ),
                [],
                {},
            )

        # ----------------------------
        # Best line parent per dangle (angle-aware)
        # Used by edge-case bonus detection.
        # ----------------------------
        best_line_parent_by_dangle: dict[int, int] = {}

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

                raw_dist = float(cand["near_dist"])
                _tol = float(self.gap_tolerance_meters) or 1.0
                eff = self._compute_best_fit_score(
                    norm_dist=raw_dist / _tol, assess=assess
                )

                # Deterministic tie-break:
                score = (float(eff), float(raw_dist), self._candidate_sort_key(cand))
                if best_score is None or score < best_score:
                    best_score = score
                    best = int(cand["near_fid"])

            if best is not None:
                best_line_parent_by_dangle[int(dangle_oid)] = int(best)
        # ----------------------------
        # Dangle selection: choose one proposal per dangle using angle-aware scoring
        # ----------------------------
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
                is_external_line_like=is_external_line_like,
                best_line_parent_by_dangle=best_line_parent_by_dangle,
                dangle_parent=dangle_parent,
                topology=topology,
                collect_diags=collect_diags,
            )
        )

        if not _dangle_proposals:
            return (
                {},
                [],
                self._assemble_diagnostics(
                    collect_diags=collect_diags,
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    connection_loser_oids=set(),
                    kruskal_rejected_oids=set(),
                    kruskal_crossing_rejected_oids=set(),
                    accepted_dangle_oids=set(),
                    gap_source_by_dangle={},
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                    connection_norm_z_by_dangle={},
                    global_norm_z_by_dangle={},
                    dangle_xy=dangle_xy,
                    dangle_parent=dangle_parent,
                    dangles_key=dangles_key,
                    lines_key=lines_key,
                ),
                [],
                {},
            )

        # ----------------------------
        # Mutual detection (for labeling)
        # - dangle mutual pairs: D1 targets D2 AND D2 targets D1 (both dangle targets)
        # - network mutual: any proposal exists in both directions between the two network nodes
        # ----------------------------
        active: list[_DangleProposal] = list(_dangle_proposals.values())
        if not active:
            return (
                {},
                [],
                self._assemble_diagnostics(
                    collect_diags=collect_diags,
                    step1a_illegal=_step1a_illegal,
                    step1b_illegal=_step1b_illegal,
                    step1b_scored=_step1b_scored,
                    connection_loser_oids=set(),
                    kruskal_rejected_oids=set(),
                    kruskal_crossing_rejected_oids=set(),
                    accepted_dangle_oids=set(),
                    gap_source_by_dangle={},
                    dangle_norm_z_by_dangle=dangle_norm_z_by_dangle,
                    connection_norm_z_by_dangle={},
                    global_norm_z_by_dangle={},
                    dangle_xy=dangle_xy,
                    dangle_parent=dangle_parent,
                    dangles_key=dangles_key,
                    lines_key=lines_key,
                ),
                [],
                {},
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
        # Connection normalization: re-normalize Z within each undirected A↔B connection group
        # ----------------------------
        connection_proposals_by_dangle, connection_norm_z_by_dangle = (
            self._run_connection_normalization(_dangle_proposals)
        )

        # ----------------------------
        # Connection selection: one winner per undirected connection
        # ----------------------------
        _connection_proposals, connection_loser_oids = self._run_connection_selection(
            connection_proposals_by_dangle=connection_proposals_by_dangle,
            directed_edges=directed_network_edges,
            dangle_mutual_oids=dangle_mutual_oids,
            collect_diags=collect_diags,
        )

        # ----------------------------
        # Global normalization: re-normalize Z across all connection winners
        # ----------------------------
        _global_winners, global_norm_z_by_dangle = self._run_global_normalization(
            _connection_proposals
        )

        # ----------------------------
        # Global selection: Kruskal cycle prevention across accepted connections
        # ----------------------------
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

        if not _global_proposals:
            return (
                {},
                [],
                self._assemble_diagnostics(
                    collect_diags=collect_diags,
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
                    dangle_xy=dangle_xy,
                    dangle_parent=dangle_parent,
                    dangles_key=dangles_key,
                    lines_key=lines_key,
                ),
                [],
                {},
            )

        # ----------------------------
        # Resnap candidate identification
        # ----------------------------
        resnap_captures = self._identify_resnap_captures(_global_proposals)

        # ----------------------------
        # Build plan_by_parent: parent_id -> list[plan_entry]
        # ----------------------------
        plan_by_parent = self._assemble_plan_entries(_global_proposals)

        return (
            plan_by_parent,
            resnap_captures,
            self._assemble_diagnostics(
                collect_diags=collect_diags,
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
                dangle_xy=dangle_xy,
                dangle_parent=dangle_parent,
                dangles_key=dangles_key,
                lines_key=lines_key,
            ),
            accepted_connector_raw,
            kruskal_rank_by_dangle_oid,
        )

    def _filter_legal_candidates(
        self,
        *,
        grouped: _Grouped,
        dangle_parent: dict[int, int],
        illegal: _IllegalTargets,
        dangles_key: str,
        lines_key: str,
        line_like_ds_keys: set[str],
        base_tol: float,
        dangle_tol: float,
        topology: TopologyModel,
        collect_diags: bool,
        directed_source_illegal_oids: set[int],
    ) -> tuple[_Grouped, dict[int, int], list[_Step1AIllegalEntry]]:
        """Dangle filtering: collect legal candidates per dangle.

        Returns (legal_rows_by_dangle, parent_id_by_dangle, step1a_illegal).
        """
        legal_rows_by_dangle: dict[int, list[dict]] = {}
        parent_id_by_dangle: dict[int, int] = {}
        _step1a_illegal: list[_Step1AIllegalEntry] = []

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
                        if str(cand["near_fc_key"]) == str(lines_key) and int(
                            cand["near_fid"]
                        ) == int(parent_id):
                            continue
                        _step1a_illegal.append(
                            (dangle_oid, parent_id, cand, "directed_start_node")
                        )
                continue

            rows = sorted(candidates, key=self._candidate_sort_key)

            legal_rows: list[dict] = []
            for cand in rows:
                # Self-parent candidates are excluded from the plan and from diagnostics.
                if str(cand["near_fc_key"]) == str(lines_key) and int(
                    cand["near_fid"]
                ) == int(parent_id):
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
                    _step1a_illegal.append((dangle_oid, parent_id, cand, reason))

            if not legal_rows:
                continue

            legal_rows_by_dangle[dangle_oid] = legal_rows
            parent_id_by_dangle[dangle_oid] = parent_id

        return legal_rows_by_dangle, parent_id_by_dangle, _step1a_illegal

    def _select_dangle_proposals(
        self,
        *,
        legal_rows_by_dangle: _Grouped,
        parent_id_by_dangle: dict[int, int],
        dangle_xy: dict[int, tuple[float, float]],
        dangles_key: str,
        lines_key: str,
        line_like_ds_keys: set[str],
        line_like_external_ds_keys: set[str],
        base_tol: float,
        polyline_by_parent: dict[int, Any],
        polyline_by_external: dict[str, dict[int, Any]],
        is_external_line_like: dict[str, bool],
        best_line_parent_by_dangle: dict[int, int],
        dangle_parent: dict[int, int],
        topology: TopologyModel,
        collect_diags: bool,
    ) -> tuple[
        dict[int, _DangleProposal],
        _NormZByDangle,
        list[_Step1BIllegalEntry],
        list[_Step1BScoredEntry],
    ]:
        """Dangle selection: choose one proposal per dangle using angle-aware scoring.

        Returns (_dangle_proposals, dangle_norm_z_by_dangle, step1b_illegal, step1b_scored).
        """
        _dangle_proposals: dict[int, _DangleProposal] = {}
        dangle_norm_z_by_dangle: dict[int, Optional[float]] = {}
        _step1b_illegal: list[_Step1BIllegalEntry] = []
        _step1b_scored: list[_Step1BScoredEntry] = []

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
                        float(_c["near_x"]),
                        float(_c["near_y"]),
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

            # (_ProposalScore, cand, raw_dist, best_fit, bonus, assess, norm_z, end_z)
            scored_candidates: list[tuple[Any, ...]] = []

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
                    is_external_line_like=is_external_line_like,
                    dangle_xys_by_parent=_dangle_xys_by_parent,
                )

                _cand_end_z: Optional[float] = end_z_by_cand_index.get(_cand_idx)

                # 1) Candidate blocking (angle_block_threshold_degrees)
                if assess.blocks:
                    if collect_diags:
                        _step1b_illegal.append(
                            (
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
                is_dangle_target = str(cand["near_fc_key"]) == str(dangles_key)
                is_line_like_target = str(cand["near_fc_key"]) in line_like_ds_keys
                dist = float(cand["near_dist"])

                if (
                    (is_dangle_target or is_line_like_target)
                    and dist > float(base_tol)
                    and not bool(assess.allow_extra_dangle)
                ):
                    # Candidate is only legal due to expanded tolerance; angle disallows it
                    if collect_diags:
                        _step1b_illegal.append(
                            (
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
                            float(cand["near_x"]),
                            float(cand["near_y"]),
                        )
                    )
                    if (
                        _end_z_gate is not None
                        and (_end_z_gate - start_z) > self.z_drop_threshold
                    ):
                        if collect_diags:
                            _step1b_illegal.append(
                                (
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

                raw_distance, effective_distance, bonus_applied, _score_unused = (
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
                    (
                        dangle_score,
                        cand,
                        float(raw_distance),
                        float(effective_for_scoring),
                        bool(bonus_applied),
                        assess,
                        _norm_z,
                        end_z_by_cand_index.get(_cand_idx),  # per-candidate end_z
                    )
                )

            if not scored_candidates:
                continue

            winner_item = min(
                scored_candidates,
                key=lambda item: (item[0].composite, item[0].bonus_rank, item[2]),
            )
            (
                winner_dangle_score,
                chosen,
                raw_distance,
                effective_distance_for_scoring,
                bonus_applied,
                chosen_assess,
                winner_norm_z,
                winner_end_z,
            ) = winner_item

            if collect_diags:
                for sc_tuple in scored_candidates:
                    (
                        sc_score,
                        sc_cand,
                        sc_raw,
                        sc_best_fit,
                        sc_bonus,
                        sc_assess,
                        sc_norm_z,
                        sc_end_z,
                    ) = sc_tuple
                    _step1b_scored.append(
                        (
                            dangle_oid,
                            parent_id,
                            sc_cand,
                            sc_assess,
                            float(sc_raw),
                            float(sc_best_fit),
                            bool(sc_bonus),
                            sc_tuple is winner_item,
                            (
                                sc_score.composite,
                                sc_score.bonus_rank,
                                sc_raw,
                            ),  # for per-dangle rank
                            sc_norm_z,  # dangle_norm_z for this candidate
                            start_z,  # fixed per dangle
                            sc_end_z,  # per-candidate end_z
                        )
                    )

            # ----------------------------
            # _DangleProposal construction
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
                near_x=float(chosen["near_x"]),
                near_y=float(chosen["near_y"]),
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
        dangle_proposals: dict[int, _DangleProposal],
    ) -> tuple[dict[int, _ConnectionProposal], _NormZByDangle]:
        """Connection normalization: re-normalize Z within each undirected A↔B connection group.

        Returns (connection_proposals_by_dangle, connection_norm_z_by_dangle).
        """
        active = list(dangle_proposals.values())
        _by_connection_for_normalization: dict[tuple, list[_DangleProposal]] = {}
        for p in active:
            _by_connection_for_normalization.setdefault(p.ctx.pair_key, []).append(p)

        connection_proposals_by_dangle: dict[int, _ConnectionProposal] = {}
        connection_norm_z_by_dangle: dict[int, Optional[float]] = {}
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
        connection_proposals_by_dangle: dict[int, _ConnectionProposal],
        directed_edges: set[tuple[EntityKey, EntityKey]],
        dangle_mutual_oids: set[int],
        collect_diags: bool,
    ) -> tuple[list[_ConnectionWithSource], set[int]]:
        """Connection selection: one winner per undirected connection.

        Returns (_connection_proposals, connection_loser_oids).
        """
        by_connection: dict[tuple, list[_ConnectionProposal]] = {}
        for p in connection_proposals_by_dangle.values():
            by_connection.setdefault(p.ctx.pair_key, []).append(p)

        _connection_proposals: list[_ConnectionWithSource] = []
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
                gap_source = self.GAP_SOURCE_PAIR_DANGLE
            elif mutual_network:
                gap_source = self.GAP_SOURCE_PAIR_LINE
            else:
                gap_source = self.GAP_SOURCE_DEFAULT

            _connection_proposals.append((winner, str(gap_source)))

        connection_loser_oids: set[int] = set()
        if collect_diags:
            _stage_a_winner_oids = {
                int(prop.ctx.dangle_oid) for prop, _ in _connection_proposals
            }
            connection_loser_oids.update(
                int(p.ctx.dangle_oid)
                for p in connection_proposals_by_dangle.values()
                if int(p.ctx.dangle_oid) not in _stage_a_winner_oids
            )

        return _connection_proposals, connection_loser_oids

    def _run_global_normalization(
        self,
        connection_proposals: list[_ConnectionWithSource],
    ) -> tuple[list[_GlobalWithSource], _NormZByDangle]:
        """Global normalization: re-normalize Z across all connection winners.

        Returns (_global_winners, global_norm_z_by_dangle).
        """
        _all_end_z_global = [p.ctx.end_z for p, _ in connection_proposals]
        _global_winners: list[_GlobalWithSource] = []
        global_norm_z_by_dangle: dict[int, Optional[float]] = {}
        for n_prop, gap_source in connection_proposals:
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
            _global_winners.append((g_prop, gap_source))
            global_norm_z_by_dangle[int(n_prop.ctx.dangle_oid)] = glob_norm_z

        return _global_winners, global_norm_z_by_dangle

    def _run_kruskal(
        self,
        *,
        global_winners: list[_GlobalWithSource],
        topology: TopologyModel,
        collect_diags: bool,
        trimmed_connector_cache: dict[tuple[int, str, int], Any],
        crossing_spatial_reference: Any,  # arcpy.SpatialReference | None
    ) -> tuple[
        list[_GlobalWithSource],
        set[int],  # accepted_dangle_oids
        set[int],  # kruskal_rejected_oids (cycle-based)
        set[int],  # kruskal_crossing_rejected_oids
        dict[int, str],  # gap_source_by_dangle
        list[
            _AcceptedConnectorRaw
        ],  # accepted_connector_raw (for resnap crossing re-check)
        dict[int, int],  # kruskal_rank_by_dangle_oid
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
        _global_proposals: list[_GlobalWithSource] = []
        kruskal_crossing_rejected_oids: set[int] = set()
        accepted_keys: set[tuple[int, str, int]] = set()
        accepted_connector_raw: list[_AcceptedConnectorRaw] = []
        kruskal_rank_by_dangle_oid: dict[int, int] = {}
        rank_counter = 0

        # --- Pre-loop: build candidate-vs-candidate conflict lookup ---
        conflict_lookup: dict[tuple[int, str, int], set[tuple[int, str, int]]] = {}
        if reject_crossing:
            _kruskal_cands: list[tuple[tuple[int, str, int], Any]] = []
            for prop, _ in global_winners:
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

        def _accept(prop: Any, gap_source: Any) -> None:
            nonlocal rank_counter
            _global_proposals.append((prop, gap_source))
            if reject_crossing:
                rank_counter += 1
                d_oid = int(prop.ctx.dangle_oid)
                kruskal_rank_by_dangle_oid[d_oid] = rank_counter
                _key = (d_oid, str(prop.ctx.near_fc_key), int(prop.ctx.near_fid))
                accepted_keys.add(_key)
                accepted_connector_raw.append(
                    (
                        d_oid,
                        float(prop.ctx.dangle_x),
                        float(prop.ctx.dangle_y),
                        float(prop.ctx.near_x),
                        float(prop.ctx.near_y),
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
            for prop, gap_source in sorted(
                global_winners, key=lambda t: t[0].sort_key()
            ):
                if uf.find(prop.ctx.src_node) == uf.find(prop.ctx.tgt_node):
                    continue
                if _crossing_blocked(prop):
                    kruskal_crossing_rejected_oids.add(int(prop.ctx.dangle_oid))
                    continue
                uf.union(prop.ctx.src_node, prop.ctx.tgt_node)
                _accept(prop, gap_source)
        else:
            # NONE / DIRECT_CONNECTION: no cycle check, crossing check only.
            for prop, gap_source in sorted(
                global_winners, key=lambda t: t[0].sort_key()
            ):
                if _crossing_blocked(prop):
                    kruskal_crossing_rejected_oids.add(int(prop.ctx.dangle_oid))
                    continue
                _accept(prop, gap_source)

        accepted_dangle_oids: set[int] = set()
        kruskal_rejected_oids: set[int] = set()
        gap_source_by_dangle: dict[int, str] = {}
        if collect_diags and _global_proposals:
            _accepted_oids = {int(prop.ctx.dangle_oid) for prop, _ in _global_proposals}
            accepted_dangle_oids.update(_accepted_oids)
            kruskal_rejected_oids.update(
                int(prop.ctx.dangle_oid)
                for prop, _ in global_winners
                if int(prop.ctx.dangle_oid) not in _accepted_oids
                and int(prop.ctx.dangle_oid) not in kruskal_crossing_rejected_oids
            )
            gap_source_by_dangle.update(
                {int(prop.ctx.dangle_oid): str(gs) for prop, gs in _global_proposals}
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
        global_proposals: list[_GlobalWithSource],
    ) -> list[_ResnappedCapture]:
        """Identify connections whose near-point may need re-resolving after snap.

        A connection A→B needs resnap if:
          1. B is the target_parent_id of A's accepted connection
          2. Another accepted connection B→T exists with GAP_SOURCE_PAIR_DANGLE
             (i.e. B's dangle endpoint will move when B snaps to T)
          3. A's near-point lies on B's last segment — checked in _resnap_connections
             using post-apply geometry (this block is a cheap pre-filter only).
        """
        snap_source_parents: set[int] = {
            int(prop.ctx.src_parent_id)
            for prop, gap_source in global_proposals
            if str(gap_source) == self.GAP_SOURCE_PAIR_DANGLE
        }
        resnap_captures: list[_ResnappedCapture] = []
        for prop, gap_source in global_proposals:
            tp = prop.ctx.target_parent_id
            if tp is None or int(tp) not in snap_source_parents:
                continue
            resnap_captures.append(
                _ResnappedCapture(
                    parent_id=int(prop.ctx.src_parent_id),
                    dangle_oid=int(prop.ctx.dangle_oid),
                    forced_target_parent=int(tp),
                    proposal=prop,
                    gap_source=str(gap_source),
                )
            )
        return resnap_captures

    def _recheck_resnap_crossings(
        self,
        *,
        resnap_plan: dict[int, dict],
        accepted_connector_raw: list[_AcceptedConnectorRaw],
        kruskal_rank_by_dangle_oid: dict[int, int],
        trim_distance: float,
        spatial_reference: Any,
    ) -> tuple[dict[int, dict], set[int], set[int]]:
        """Re-check resnap captures against accepted connector geometries.

        Called after _resnap_connections resolves final geometry for deferred
        connectors.  Uses a spatial CROSSES relationship check (trimmed resnap
        connectors vs trimmed accepted connectors) as the source of truth for
        crossing conflicts, then
        applies rank-based conflict resolution:

          - If the resnap capture has a worse (higher) rank than the best-ranked
            conflicting accepted connector → the resnap capture loses; its plan
            entry is marked skip=True so the corrected geometry is not applied.
          - If the resnap capture has a better (lower) rank → it wins; the
            conflicting connector(s) are flagged as displaced.  Their geometry
            is already applied to the feature class and is not reverted, so the
            displacement is recorded in diagnostics only.

        Returns (resnap_plan, resnap_crossing_rejected_oids,
                 resnap_crossing_displaced_oids).
        """
        if not accepted_connector_raw:
            return resnap_plan, set(), set()

        # Build trimmed resnap connectors: key = parent_id (unique per resnap entry).
        resnap_cands: list[tuple[Any, Any]] = []
        for parent_id, entry in resnap_plan.items():
            if entry.get("skip", False):
                continue
            trimmed = self._build_trimmed_connector(
                from_x=float(entry["dangle_x"]),
                from_y=float(entry["dangle_y"]),
                to_x=float(entry["near_x"]),
                to_y=float(entry["near_y"]),
                trim_distance=trim_distance,
                spatial_reference=spatial_reference,
            )
            if trimmed is not None:
                resnap_cands.append((parent_id, trimmed))

        if not resnap_cands:
            return resnap_plan, set(), set()

        # Build trimmed accepted connectors: key = dangle_oid.
        accepted_cands: list[tuple[Any, Any]] = []
        for acc_doid, ax, ay, bx, by in accepted_connector_raw:
            trimmed = self._build_trimmed_connector(
                from_x=ax,
                from_y=ay,
                to_x=bx,
                to_y=by,
                trim_distance=trim_distance,
                spatial_reference=spatial_reference,
            )
            if trimmed is not None:
                accepted_cands.append((acc_doid, trimmed))

        if not accepted_cands:
            return resnap_plan, set(), set()

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
        conflicts_by_parent: dict[int, set[int]] = {}
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

        resnap_crossing_rejected_oids: set[int] = set()
        resnap_crossing_displaced_oids: set[int] = set()

        for parent_id, entry in resnap_plan.items():
            if entry.get("skip", False):
                continue

            conflicting_doids = conflicts_by_parent.get(parent_id)
            if not conflicting_doids:
                continue

            dangle_oid = int(entry["dangle_oid"])
            resnap_rank = kruskal_rank_by_dangle_oid.get(dangle_oid, float("inf"))
            best_conflict_rank = min(
                kruskal_rank_by_dangle_oid.get(aoid, float("inf"))
                for aoid in conflicting_doids
            )

            if resnap_rank <= best_conflict_rank:
                # Resnap capture wins: displace the conflicting accepted connectors.
                resnap_crossing_displaced_oids.update(conflicting_doids)
            else:
                # Resnap capture loses: skip the corrected-geometry application.
                entry["skip"] = True
                resnap_crossing_rejected_oids.add(dangle_oid)

        return (
            resnap_plan,
            resnap_crossing_rejected_oids,
            resnap_crossing_displaced_oids,
        )

    def _assemble_plan_entries(
        self,
        global_proposals: list[_GlobalWithSource],
    ) -> dict[int, list[dict[str, Any]]]:
        """Assemble plan_by_parent from accepted global proposals."""
        tmp: dict[int, list[tuple[tuple[Any, ...], dict[str, Any]]]] = {}

        for prop, gap_source in sorted(global_proposals, key=lambda t: t[0].sort_key()):
            entry = self._make_plan_entry(
                parent_id=int(prop.ctx.src_parent_id),
                dangle_oid=int(prop.ctx.dangle_oid),
                dangle_x=float(prop.ctx.dangle_x),
                dangle_y=float(prop.ctx.dangle_y),
                chosen={
                    "near_x": float(prop.ctx.near_x),
                    "near_y": float(prop.ctx.near_y),
                    "near_fc_key": str(prop.ctx.near_fc_key),
                    "near_fid": int(prop.ctx.near_fid),
                },
                gap_source=str(gap_source),
                bonus_applied=prop.ctx.bonus_applied,
                assess=prop.ctx.assess,
                best_fit_score=prop.score.composite,
            )

            tmp.setdefault(int(prop.ctx.src_parent_id), []).append(
                (prop.sort_key(), entry)
            )

        plan_by_parent: dict[int, list[dict]] = {}
        for pid, items in tmp.items():
            # Deterministic per-parent order
            ordered = sorted(
                items, key=lambda t: (t[0], int(t[1].get("dangle_oid", 0)))
            )
            plan_by_parent[int(pid)] = [entry for _, entry in ordered]

        return plan_by_parent

    def _assemble_diagnostics(
        self,
        *,
        collect_diags: bool,
        step1a_illegal: list[_Step1AIllegalEntry],
        step1b_illegal: list[_Step1BIllegalEntry],
        step1b_scored: list[_Step1BScoredEntry],
        connection_loser_oids: set[int],
        kruskal_rejected_oids: set[int],
        kruskal_crossing_rejected_oids: set[int],
        accepted_dangle_oids: set[int],
        gap_source_by_dangle: dict[int, str],
        dangle_norm_z_by_dangle: _NormZByDangle,
        connection_norm_z_by_dangle: _NormZByDangle,
        global_norm_z_by_dangle: _NormZByDangle,
        dangle_xy: dict[int, tuple[float, float]],
        dangle_parent: dict[int, int],
        dangles_key: str,
        lines_key: str,
    ) -> list[CandidateDiagnostic]:
        """Assemble CandidateDiagnostic records from all pipeline state collected during _build_plan."""
        if not collect_diags:
            return []
        result: list[CandidateDiagnostic] = []

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

        # Step-1A illegals: angle never computed; z values looked up here
        for d_oid, p_id, cand, reason in step1a_illegal:
            xy = dangle_xy.get(int(d_oid))
            if xy is None:
                continue
            _sz, _ez = _z_pair(xy, cand["near_x"], cand["near_y"])
            result.append(
                CandidateDiagnostic(
                    parent_id=p_id,
                    dangle_oid=d_oid,
                    dangle_x=float(xy[0]),
                    dangle_y=float(xy[1]),
                    near_fc_key=str(cand["near_fc_key"]),
                    near_fid=int(cand["near_fid"]),
                    near_x=float(cand["near_x"]),
                    near_y=float(cand["near_y"]),
                    raw_distance=float(cand["near_dist"]),
                    candidate_status="illegal",
                    status_reason=reason,
                    best_fit_score=None,
                    best_fit_rank=None,
                    bonus_applied=None,
                    assess=None,
                    target_parent_id=self._resolve_target_parent_id(
                        cand, dangle_parent, dangles_key, lines_key
                    ),
                    final_gap_source=None,
                    start_z=_sz,
                    end_z=_ez,
                    dangle_norm_z=None,
                    connection_norm_z=None,
                    global_norm_z=None,
                )
            )

        # Step-1B angle-blocked illegals: z values carried in tuple
        for d_oid, p_id, cand, assess, reason, _sz, _ez in step1b_illegal:
            xy = dangle_xy.get(int(d_oid))
            if xy is None:
                continue
            result.append(
                CandidateDiagnostic(
                    parent_id=p_id,
                    dangle_oid=d_oid,
                    dangle_x=float(xy[0]),
                    dangle_y=float(xy[1]),
                    near_fc_key=str(cand["near_fc_key"]),
                    near_fid=int(cand["near_fid"]),
                    near_x=float(cand["near_x"]),
                    near_y=float(cand["near_y"]),
                    raw_distance=float(cand["near_dist"]),
                    candidate_status="illegal",
                    status_reason=reason,
                    best_fit_score=None,
                    best_fit_rank=None,
                    bonus_applied=None,
                    assess=assess,
                    target_parent_id=self._resolve_target_parent_id(
                        cand, dangle_parent, dangles_key, lines_key
                    ),
                    final_gap_source=None,
                    start_z=_sz,
                    end_z=_ez,
                    dangle_norm_z=None,
                    connection_norm_z=None,
                    global_norm_z=None,
                )
            )

        # Compute per-dangle rank for scored candidates (1 = local winner)
        scored_by_dangle: dict[int, list[_Step1BScoredEntry]] = {}
        for entry in step1b_scored:
            scored_by_dangle.setdefault(int(entry[0]), []).append(entry)
        rank_map: dict[tuple[int, str, int], int] = {}
        for d_oid, entries in scored_by_dangle.items():
            for rank, entry in enumerate(sorted(entries, key=lambda e: e[8]), start=1):
                cand = entry[2]
                rank_map[(d_oid, str(cand["near_fc_key"]), int(cand["near_fid"]))] = (
                    rank
                )

        # Step-1B scored candidates; z values carried in tuple
        for (
            d_oid,
            p_id,
            cand,
            assess,
            raw_dist,
            best_fit,
            bonus,
            is_local_winner,
            _score,
            sc_norm_z,
            sc_start_z,
            sc_end_z,
        ) in step1b_scored:
            xy = dangle_xy.get(int(d_oid))
            if xy is None:
                continue
            rank = rank_map.get(
                (d_oid, str(cand["near_fc_key"]), int(cand["near_fid"]))
            )

            if not is_local_winner:
                status = "legal_not_selected"
                reason = "outscored_within_dangle"
                final_gs: Optional[str] = None
                conn_nz: Optional[float] = None
                glob_nz: Optional[float] = None
            elif int(d_oid) in connection_loser_oids:
                status = "selected_for_dangle"
                reason = "lost_connection_selection"
                final_gs = None
                conn_nz = connection_norm_z_by_dangle.get(int(d_oid))
                glob_nz = None
            elif int(d_oid) in kruskal_rejected_oids:
                status = "selected_for_dangle"
                reason = "lost_kruskal_selection"
                final_gs = None
                conn_nz = connection_norm_z_by_dangle.get(int(d_oid))
                glob_nz = global_norm_z_by_dangle.get(int(d_oid))
            elif int(d_oid) in kruskal_crossing_rejected_oids:
                status = "selected_for_dangle"
                reason = "crosses_accepted_connector"
                final_gs = None
                conn_nz = connection_norm_z_by_dangle.get(int(d_oid))
                glob_nz = global_norm_z_by_dangle.get(int(d_oid))
            elif int(d_oid) in accepted_dangle_oids:
                status = "applied_to_output"
                reason = "applied_main"
                final_gs = gap_source_by_dangle.get(int(d_oid))
                conn_nz = connection_norm_z_by_dangle.get(int(d_oid))
                glob_nz = global_norm_z_by_dangle.get(int(d_oid))
            else:
                # Local winner that didn't reach proposal construction
                # (e.g. target dangle had no resolvable parent)
                status = "selected_for_dangle"
                reason = None
                final_gs = None
                conn_nz = None
                glob_nz = None

            result.append(
                CandidateDiagnostic(
                    parent_id=p_id,
                    dangle_oid=d_oid,
                    dangle_x=float(xy[0]),
                    dangle_y=float(xy[1]),
                    near_fc_key=str(cand["near_fc_key"]),
                    near_fid=int(cand["near_fid"]),
                    near_x=float(cand["near_x"]),
                    near_y=float(cand["near_y"]),
                    raw_distance=float(raw_dist),
                    candidate_status=status,
                    status_reason=reason,
                    best_fit_score=float(best_fit),
                    best_fit_rank=rank,
                    bonus_applied=bool(bonus),
                    assess=assess,
                    target_parent_id=self._resolve_target_parent_id(
                        cand, dangle_parent, dangles_key, lines_key
                    ),
                    final_gap_source=final_gs,
                    start_z=sc_start_z,
                    end_z=sc_end_z,
                    dangle_norm_z=sc_norm_z,
                    connection_norm_z=conn_nz,
                    global_norm_z=glob_nz,
                )
            )
        return result

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
                entry["meta_connector_transition_diff"] = (
                    assess.connector_transition_diff
                )
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
    # Resnap pass
    # ----------------------------

    def _resnap_connections(
        self,
        *,
        captures: "list[_ResnappedCapture]",
        dangles_fc: str,
        snap_source_dangle_xy: "dict[int, tuple[float, float]]",
    ) -> dict[int, dict]:
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
        v_prev_by_parent: dict[int, tuple[float, float]] = {}
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
        near_oid_to_parent: dict[int, int] = {}
        with arcpy.da.SearchCursor(
            resnap_lines_lyr, [lines_oid_field, self.ORIGINAL_ID]
        ) as cur:
            for oid, pid in cur:
                near_oid_to_parent[int(oid)] = int(pid)

        search_radius = (
            2 * self.connectivity_tolerance_meters + self.gap_tolerance_meters
        )
        resnap_table = self.wfm.build_file_path(file_name="resnap_near_table")
        arcpy.analysis.GenerateNearTable(
            in_features=resnap_dangles_lyr,
            near_features=[resnap_lines_lyr],
            out_table=resnap_table,
            search_radius=f"{search_radius} Meters",
            location="LOCATION",
            angle="NO_ANGLE",
            closest="ALL",
            closest_count=100,
            method="PLANAR",
        )

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
        out: dict[int, dict] = {}

        for cap in filtered:
            hit = best_xy.get((cap.dangle_oid, cap.forced_target_parent))
            if hit is None:
                continue
            dangle_coords = dangle_xy.get(cap.dangle_oid)
            if dangle_coords is None:
                continue
            out[cap.parent_id] = self._make_plan_entry(
                parent_id=cap.parent_id,
                dangle_oid=cap.dangle_oid,
                dangle_x=float(dangle_coords[0]),
                dangle_y=float(dangle_coords[1]),
                chosen={
                    "near_x": float(hit[0]),
                    "near_y": float(hit[1]),
                    "near_fc_key": lines_key,
                    "near_fid": cap.forced_target_parent,
                },
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
            row.extend(
                [
                    meta.get("meta_src_connector_diff"),
                    meta.get("meta_connector_target_diff"),
                    meta.get("meta_src_target_diff"),
                    meta.get("meta_connector_transition_diff"),
                    meta.get("meta_angle_metric_deg"),
                    meta.get("meta_best_fit_score"),
                    meta.get("meta_bonus_applied"),
                ]
            )
        return tuple(row)

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
        arcpy.management.AddField(fc_path, "src_line_id", "LONG")
        arcpy.management.AddField(fc_path, "src_dangle_oid", "LONG")
        arcpy.management.AddField(fc_path, "target_ds_key", "TEXT", field_length=100)
        arcpy.management.AddField(fc_path, "target_fid", "LONG")
        arcpy.management.AddField(fc_path, "target_parent_id", "LONG")
        arcpy.management.AddField(fc_path, "raw_distance", "DOUBLE")
        arcpy.management.AddField(fc_path, "best_fit_score", "DOUBLE")
        arcpy.management.AddField(fc_path, "best_fit_rank", "SHORT")
        arcpy.management.AddField(fc_path, "bonus_applied", "SHORT")
        for fname in (
            "angle_metric_deg",
            "src_connector_diff",
            "connector_target_diff",
            "src_target_diff",
            "connector_transition_diff",
        ):
            arcpy.management.AddField(fc_path, fname, "DOUBLE")
        arcpy.management.AddField(fc_path, "final_gap_source", "TEXT", field_length=20)
        arcpy.management.AddField(fc_path, "candidate_status", "TEXT", field_length=25)
        arcpy.management.AddField(fc_path, "status_reason", "TEXT", field_length=50)
        arcpy.management.AddField(fc_path, "start_z", "DOUBLE")
        arcpy.management.AddField(fc_path, "end_z", "DOUBLE")
        arcpy.management.AddField(fc_path, "dangle_norm_z", "DOUBLE")
        arcpy.management.AddField(fc_path, "connection_norm_z", "DOUBLE")
        arcpy.management.AddField(fc_path, "global_norm_z", "DOUBLE")

    def _write_candidate_connections_output(
        self,
        fc_path: str,
        diagnostics: list[CandidateDiagnostic],
        spatial_reference,
    ) -> None:
        """Write one row per CandidateDiagnostic to the candidate-connections feature class."""
        if not diagnostics:
            return
        fields = [
            "SHAPE@",
            "src_line_id",
            "src_dangle_oid",
            "target_ds_key",
            "target_fid",
            "target_parent_id",
            "raw_distance",
            "best_fit_score",
            "best_fit_rank",
            "bonus_applied",
            "angle_metric_deg",
            "src_connector_diff",
            "connector_target_diff",
            "src_target_diff",
            "connector_transition_diff",
            "final_gap_source",
            "candidate_status",
            "status_reason",
            "start_z",
            "end_z",
            "dangle_norm_z",
            "connection_norm_z",
            "global_norm_z",
        ]
        with arcpy.da.InsertCursor(fc_path, fields) as cur:
            for d in diagnostics:
                arr = arcpy.Array(
                    [
                        arcpy.Point(d.dangle_x, d.dangle_y),
                        arcpy.Point(d.near_x, d.near_y),
                    ]
                )
                geom = arcpy.Polyline(arr, spatial_reference)
                a = d.assess
                cur.insertRow(
                    (
                        geom,
                        d.parent_id,
                        d.dangle_oid,
                        d.near_fc_key,
                        d.near_fid,
                        d.target_parent_id,
                        d.raw_distance,
                        d.best_fit_score,
                        d.best_fit_rank,
                        int(bool(d.bonus_applied)),
                        a.angle_metric_deg if a is not None else None,
                        a.src_connector_diff if a is not None else None,
                        a.connector_target_diff if a is not None else None,
                        a.src_target_diff if a is not None else None,
                        a.connector_transition_diff if a is not None else None,
                        d.final_gap_source,
                        d.candidate_status,
                        d.status_reason,
                        d.start_z,
                        d.end_z,
                        d.dangle_norm_z,
                        d.connection_norm_z,
                        d.global_norm_z,
                    )
                )

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

                    if (
                        self.line_changes_output is not None
                        and self.write_output_metadata
                    ):
                        meta = (
                            {
                                k: info.get(k)
                                for k in (
                                    "meta_src_connector_diff",
                                    "meta_connector_target_diff",
                                    "meta_src_target_diff",
                                    "meta_connector_transition_diff",
                                    "meta_angle_metric_deg",
                                    "meta_best_fit_score",
                                    "meta_bonus_applied",
                                )
                            }
                            if any(
                                k in info
                                for k in (
                                    "meta_src_connector_diff",
                                    "meta_angle_metric_deg",
                                    "meta_bonus_applied",
                                )
                            )
                            else None
                        )
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
        self._build_raster_handles()
        self._add_original_id_field()
        self._create_dangles()
        self._build_external_target_layers_once()
        targets = self._select_targets_within_tolerance_of_dangles()

        # Keep only dangles that have any candidate within base tolerance
        self._filter_true_dangles()
        dangles_for_plan = self.filtered_dangles

        if self.line_changes_output is not None and self.write_output_metadata:
            file_utilities.delete_feature(input_feature=self.line_changes_output)
            self._setup_line_changes_output()

        if self.candidate_connections_output is not None:
            self._setup_candidate_connections_output(self.candidate_connections_output)

        (
            plan,
            resnap_captures,
            diagnostics,
            accepted_connector_raw,
            kruskal_rank_by_dangle_oid,
        ) = self._build_plan(dangles_fc=dangles_for_plan, target_layers=targets)

        # Capture snap-source dangle endpoints before _apply_plan moves them.
        snap_source_dangle_xy: dict[int, tuple[float, float]] = {
            parent_id: (float(info["dangle_x"]), float(info["dangle_y"]))
            for parent_id, entries in plan.items()
            for info in entries
            if str(info.get("edit_op")) == EditOp.SNAP.value
        }

        self._apply_plan(plan)

        if resnap_captures:
            resnap_plan = self._resnap_connections(
                captures=resnap_captures,
                dangles_fc=dangles_for_plan,
                snap_source_dangle_xy=snap_source_dangle_xy,
            )

            if (
                self.reject_crossing_connectors
                and resnap_plan
                and accepted_connector_raw
            ):
                (
                    resnap_plan,
                    resnap_crossing_rejected_oids,
                    resnap_crossing_displaced_oids,
                ) = self._recheck_resnap_crossings(
                    resnap_plan=resnap_plan,
                    accepted_connector_raw=accepted_connector_raw,
                    kruskal_rank_by_dangle_oid=kruskal_rank_by_dangle_oid,
                    trim_distance=2.0 * float(self.connectivity_tolerance_meters),
                    spatial_reference=arcpy.SpatialReference(
                        self.crossing_check_spatial_reference
                    ),
                )
            else:
                resnap_crossing_rejected_oids: set[int] = set()
                resnap_crossing_displaced_oids: set[int] = set()

            self._apply_plan(resnap_plan)

            if self.candidate_connections_output is not None and diagnostics:
                resnapped_dangle_oids = {
                    int(v["dangle_oid"])
                    for v in resnap_plan.values()
                    if isinstance(v, dict)
                    and "dangle_oid" in v
                    and not v.get("skip", False)
                }
                for diag in diagnostics:
                    d_oid = int(diag.dangle_oid)
                    if diag.candidate_status == "applied_to_output":
                        if d_oid in resnap_crossing_displaced_oids:
                            diag.status_reason = "resnap_crossing_displaced"
                        elif d_oid in resnapped_dangle_oids:
                            diag.status_reason = "applied_resnapped"
                    elif diag.candidate_status == "selected_for_dangle":
                        if d_oid in resnap_crossing_rejected_oids:
                            diag.status_reason = "resnap_crossing_rejected"

        if self.candidate_connections_output is not None and diagnostics:
            spatial_reference = arcpy.Describe(self.lines_copy).spatialReference
            self._write_candidate_connections_output(
                fc_path=self.candidate_connections_output,
                diagnostics=diagnostics,
                spatial_reference=spatial_reference,
            )

        self._write_output()

        self.wfm.delete_created_files()
