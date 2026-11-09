import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, TypeAlias

import arcpy

from composition_configs import core_config
from custom_tools.general_tools.create_partition_features import (
    PARTITION_INDEX_FIELD,
)
from data_orchestrator.data_names import DataNames as dn
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100
from paths import GIS_FILES_ROOT

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

SRC_INDEX_FIELD = "src_index"
_STATE_FIELD = "fan_in_state"
_CLAIMED = "claimed"
_UNCLAIMED = "unclaimed"
_UNMATCHED = "unmatched"

# Fields that are dropped from the indexed outputs before merging, by lowercase
# prefix. FID_ fields from overlay tools carry the work file session id in their
# name and differ per pod. ORIG_FID would clash with the ORIG_FID written to the
# midpoints, which links each midpoint to its line.
DROPPED_FIELD_PREFIXES = ("fid_", "orig_fid")

ORIG_FID_FIELD = "ORIG_FID"

XY = tuple[float, float]
FanInMode: TypeAlias = Literal["strict", "partial"]


@dataclass
class _LineSignature:
    oid: int
    src_index: int
    start: XY
    end: XY
    length: float


def fan_in_partitions(
    indexed_outputs_gdb: str,
    fan_out_feature: str,
    fan_in_feature: str,
    output_feature: str,
    unclaimed_output: str,
    unmatched_output: str,
    work_file_config: core_config.WorkFileConfig,
    output_name_prefix: str = "p",
    mode: FanInMode = "strict",
    match_tolerance_m: float = 1.0,
    border_step_m: float = 0.02,
    max_border_distance_m: float = 1.0,
) -> None:
    """
    What:
        Merges the per-partition outputs {output_name_prefix}0 to {N-1} into one
        feature where every line is claimed by exactly one partition, and writes the
        lines that no partition claimed for troubleshooting.

    How:
        - N is read from the fan-out partition_index values. The indexed outputs gdb
          must hold only these outputs, and their schemas must match. In strict mode
          all N must be present; in partial mode missing outputs are left out and
          their cells are treated as dropped.
        - The outputs are merged with a src_index field, and every line gets its
          midpoint along its length, whose ORIG_FID is the line.
        - Border: midpoints near the boundaries of the present fan-out cells are
          selected with a search distance growing by border_step_m until no new
          points are added. Each border line is grouped with its copies from other
          partitions among all lines; the lowest src_index of each group is kept,
          and every line in a group is taken out of the main selection.
        - Main: for each present partition N, the lines of output N whose midpoint
          is within fan-out cell N.
        - Lines that are not claimed and have no claimed copy from another
          partition are written out: as unclaimed when their midpoint is within a
          fan-in cell that fan-out dropped or whose output is missing, otherwise as
          unmatched.

        Two lines are copies when both endpoints lie within match_tolerance_m of
        each other, in either direction, and their lengths differ by at most
        match_tolerance_m.

    Why:
        Each partition output holds its halo as well, so the same road appears in
        several outputs. The outputs also differ by an XY resolution offset, so
        copies of a road are matched by tolerance rather than by identical geometry.
        A border copy just outside the search distance is caught by growing the
        distance until a gap with no new points is found, and by looking for the
        copies of border lines among all lines. The midpoint along the length moves
        only by the offset between copies, unlike a FeatureToPoint INSIDE point.

    Args:
        indexed_outputs_gdb (str): The gdb holding only the per-partition outputs.
        fan_out_feature (str): The fan-out partition feature the outputs came from.
        fan_in_feature (str): The fan-in partition feature, all cells.
        output_feature (str): The merged output, with src_index.
        unclaimed_output (str): Lines with no claimed copy whose midpoint lies in a
            dropped cell or the cell of a missing output.
        unmatched_output (str): Other lines with no claimed copy.
        work_file_config (core_config.WorkFileConfig): Work file configuration.
        output_name_prefix (str): Name of the outputs before the index.
        mode (FanInMode): "strict" requires every output; "partial" runs with the
            outputs that are present.
        match_tolerance_m (float): Distance within which the endpoints, and
            difference within which the lengths, of two lines must lie for them to
            be copies of one road.
        border_step_m (float): Step the border search distance grows by.
        max_border_distance_m (float): Border search distance at which the run
            fails instead of growing further.
    """
    partition_count = _partition_count(fan_out_feature=fan_out_feature)
    indexed_outputs = _indexed_outputs(
        gdb=indexed_outputs_gdb,
        prefix=output_name_prefix,
        partition_count=partition_count,
        mode=mode,
    )
    _check_schemas(indexed_outputs=list(indexed_outputs.values()))
    logger.info(
        f"Fanning in {len(indexed_outputs)} of {partition_count} partitions from "
        f"{indexed_outputs_gdb}"
    )

    wfm = WorkFileManager(config=work_file_config)
    all_lines = wfm.build_file_path("all_lines")
    midpoints = wfm.build_file_path("midpoints")
    border_lines = wfm.build_file_path("border_lines")
    layers = _Layers()

    try:
        _merge_with_src_index(
            indexed_outputs=indexed_outputs, all_lines=all_lines, wfm=wfm
        )
        present_indices = ", ".join(str(index) for index in indexed_outputs)
        present_cells = layers.make(
            in_features=fan_out_feature,
            where_clause=f"{PARTITION_INDEX_FIELD} IN ({present_indices})",
        )
        arcpy.management.PolygonToLine(
            in_features=present_cells,
            out_feature_class=border_lines,
            neighbor_option="IGNORE_NEIGHBORS",
        )
        signatures = _write_midpoints(all_lines=all_lines, midpoints=midpoints)
        copies = _CopyIndex(tolerance_m=match_tolerance_m)
        for signature in signatures.values():
            copies.add(signature=signature)

        border_oids = _select_border_line_oids(
            midpoints=midpoints,
            border_lines=border_lines,
            step_m=border_step_m,
            max_distance_m=max_border_distance_m,
            layers=layers,
        )
        kept_border_oids, border_group_oids = _resolve_border_groups(
            border_oids=border_oids, signatures=signatures, copies=copies
        )
        main_oids = (
            _select_main_line_oids(
                midpoints=midpoints,
                fan_out_feature=fan_out_feature,
                partition_indices=list(indexed_outputs),
                layers=layers,
            )
            - border_group_oids
        )
        claimed_oids = main_oids | kept_border_oids

        unmatched_oids = _unmatched_line_oids(
            signatures=signatures,
            claimed_oids=claimed_oids,
            tolerance_m=match_tolerance_m,
        )
        unclaimed_oids = unmatched_oids & _select_dropped_cell_line_oids(
            midpoints=midpoints,
            present_cells=present_cells,
            fan_in_feature=fan_in_feature,
            layers=layers,
        )
        unmatched_oids -= unclaimed_oids

        _write_state(
            all_lines=all_lines,
            states={
                **{oid: _CLAIMED for oid in claimed_oids},
                **{oid: _UNCLAIMED for oid in unclaimed_oids},
                **{oid: _UNMATCHED for oid in unmatched_oids},
            },
        )
        for state, output in (
            (_CLAIMED, output_feature),
            (_UNCLAIMED, unclaimed_output),
            (_UNMATCHED, unmatched_output),
        ):
            _write_output(all_lines=all_lines, state=state, output=output)

        _log_summary(
            total=len(signatures),
            border=len(border_group_oids),
            kept_border=len(kept_border_oids),
            claimed=len(claimed_oids),
            unclaimed=len(unclaimed_oids),
            unmatched=len(unmatched_oids),
        )
    finally:
        layers.delete()

    # Only after success, so the work files of a failed run can be inspected.
    wfm.delete_created_files()


class _Layers:
    """
    Creates uniquely named feature layers and deletes them when done.
    """

    def __init__(self) -> None:
        self._names: list[str] = []

    def make(self, in_features: str, where_clause: str | None = None) -> str:
        name = f"fan_in_layer_{len(self._names)}"
        arcpy.management.MakeFeatureLayer(
            in_features=in_features, out_layer=name, where_clause=where_clause
        )
        self._names.append(name)
        return name

    def delete(self) -> None:
        for name in self._names:
            if arcpy.Exists(name):
                arcpy.management.Delete(name)


def _partition_count(fan_out_feature: str) -> int:
    """
    Returns N from the fan-out partition_index values, which must be exactly 0..N-1.
    """
    with arcpy.da.SearchCursor(fan_out_feature, [PARTITION_INDEX_FIELD]) as cursor:
        indices = sorted(index for (index,) in cursor)
    if not indices or indices != list(range(indices[-1] + 1)):
        raise ValueError(
            f"{PARTITION_INDEX_FIELD} in {fan_out_feature} must be 0 to N-1 with no "
            f"gaps or duplicates, got {indices}"
        )
    return len(indices)


def _indexed_outputs(
    gdb: str, prefix: str, partition_count: int, mode: FanInMode
) -> dict[int, str]:
    """
    What:
        Returns the paths of the outputs {prefix}0 to {prefix}{N-1} in gdb, keyed by
        partition index.

    How:
        Every feature class in gdb must be one of these outputs. In strict mode all
        N must be present. In partial mode the missing ones are logged and left out,
        but at least one must be present.
    """
    if not arcpy.Exists(gdb):
        raise FileNotFoundError(f"Indexed outputs gdb not found: {gdb}")

    found = {
        name
        for _, _, names in arcpy.da.Walk(gdb, datatype="FeatureClass")
        for name in names
    }
    expected = {f"{prefix}{index}": index for index in range(partition_count)}
    extra = sorted(found - expected.keys())
    missing = [index for name, index in expected.items() if name not in found]
    if extra or len(missing) == partition_count or (missing and mode == "strict"):
        required = "all of" if mode == "strict" else "at least one of"
        raise RuntimeError(
            f"{gdb} must hold only, and {required}, {prefix}0 to "
            f"{prefix}{partition_count - 1}.\nMissing: {missing}\nExtra: {extra}"
        )
    if missing:
        logger.warning(
            f"Partial fan-in: {len(missing)} of {partition_count} outputs missing, "
            f"partitions {missing}"
        )
    return {
        index: os.path.join(gdb, name)
        for name, index in expected.items()
        if name in found
    }


def _check_schemas(indexed_outputs: list[str]) -> None:
    """
    What:
        Raises if any indexed output differs from the first in geometry type, Z, M,
        spatial reference, or field names, types and lengths. Fields that are
        dropped before merging are not compared.

    Why:
        Append with schema_type TEST only reports that schemas differ. This names
        the output and the differences.
    """
    base_output = indexed_outputs[0]
    base_geometry, base_fields = _schema(feature=base_output)
    differences = []
    for output in indexed_outputs[1:]:
        geometry, fields = _schema(feature=output)
        name = os.path.basename(output)
        if geometry != base_geometry:
            differences.append(f"{name}: geometry {geometry} vs {base_geometry}")
        for field in sorted(base_fields.keys() - fields.keys()):
            differences.append(f"{name}: missing field {field}")
        for field in sorted(fields.keys() - base_fields.keys()):
            differences.append(f"{name}: extra field {field}")
        for field in sorted(base_fields.keys() & fields.keys()):
            if fields[field] != base_fields[field]:
                differences.append(
                    f"{name}: field {field} (type, length) {fields[field]} vs "
                    f"{base_fields[field]}"
                )
    if differences:
        raise RuntimeError(
            f"Indexed outputs do not match the schema of "
            f"{os.path.basename(base_output)}:\n" + "\n".join(differences)
        )


def _schema(
    feature: str,
) -> tuple[tuple[str, bool, bool, str], dict[str, tuple[str, int]]]:
    """
    Returns the geometry description and the fields of feature that are merged.
    Fields the geodatabase maintains itself, such as OID, Shape and Shape_Length,
    and the dropped fields are left out.
    """
    description = arcpy.Describe(feature)
    geometry = (
        description.shapeType,
        description.hasZ,
        description.hasM,
        description.spatialReference.name,
    )
    fields = {
        field.name.lower(): (field.type, field.length)
        for field in _merged_fields(feature=feature)
    }
    return geometry, fields


def _merged_fields(feature: str) -> list:
    return [
        field
        for field in arcpy.ListFields(feature)
        if not field.required and not _is_dropped(field_name=field.name)
    ]


def _is_dropped(field_name: str) -> bool:
    return field_name.lower().startswith(DROPPED_FIELD_PREFIXES)


def _merge_with_src_index(
    indexed_outputs: dict[int, str], all_lines: str, wfm: WorkFileManager
) -> None:
    """
    Merges the indexed outputs into all_lines with their partition index in
    src_index, after removing the dropped fields. The append fails on any schema
    mismatch between the outputs.
    """
    copies = []
    for index, indexed_output in indexed_outputs.items():
        copy = wfm.build_file_path("indexed_output", index=index)
        arcpy.management.CopyFeatures(
            in_features=indexed_output, out_feature_class=copy
        )
        dropped_fields = [
            field.name
            for field in arcpy.ListFields(copy)
            if not field.required and _is_dropped(field_name=field.name)
        ]
        if dropped_fields:
            arcpy.management.DeleteField(in_table=copy, drop_field=dropped_fields)
        arcpy.management.AddField(
            in_table=copy, field_name=SRC_INDEX_FIELD, field_type="LONG"
        )
        with arcpy.da.UpdateCursor(copy, [SRC_INDEX_FIELD]) as cursor:
            for row in cursor:
                cursor.updateRow([index])
        copies.append(copy)

    arcpy.management.CopyFeatures(in_features=copies[0], out_feature_class=all_lines)
    if len(copies) > 1:
        arcpy.management.Append(inputs=copies[1:], target=all_lines, schema_type="TEST")
    arcpy.management.AddField(
        in_table=all_lines, field_name=_STATE_FIELD, field_type="TEXT", field_length=16
    )


def _write_midpoints(all_lines: str, midpoints: str) -> dict[int, _LineSignature]:
    """
    Writes the midpoint along the length of every line to midpoints, with the line
    OID in ORIG_FID and its src_index, and returns the endpoints and length of
    every line keyed by its OID. Lines without geometry are left out.
    """
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(midpoints),
        out_name=os.path.basename(midpoints),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(all_lines).spatialReference,
    )
    for field in (ORIG_FID_FIELD, SRC_INDEX_FIELD):
        arcpy.management.AddField(
            in_table=midpoints, field_name=field, field_type="LONG"
        )

    signatures = {}
    with (
        arcpy.da.SearchCursor(all_lines, ["OID@", SRC_INDEX_FIELD, "SHAPE@"]) as lines,
        arcpy.da.InsertCursor(
            midpoints, ["SHAPE@", ORIG_FID_FIELD, SRC_INDEX_FIELD]
        ) as points,
    ):
        for oid, src_index, shape in lines:
            if shape is None or shape.length == 0:
                logger.warning(f"Line {oid} from output {src_index} has no geometry")
                continue
            points.insertRow([shape.positionAlongLine(0.5, True), oid, src_index])
            signatures[oid] = _LineSignature(
                oid=oid,
                src_index=src_index,
                start=(shape.firstPoint.X, shape.firstPoint.Y),
                end=(shape.lastPoint.X, shape.lastPoint.Y),
                length=shape.length,
            )
    return signatures


def _select_border_line_oids(
    midpoints: str,
    border_lines: str,
    step_m: float,
    max_distance_m: float,
    layers: _Layers,
) -> set[int]:
    """
    What:
        Returns the lines whose midpoint is near a fan-out cell boundary.

    How:
        The search distance starts at step_m and grows by step_m until a step
        selects no new points. If the first step selects nothing, there are no
        border lines.
    """
    points_layer = layers.make(in_features=midpoints)
    step = 1
    previous_count = None
    while True:
        distance_m = step * step_m
        if distance_m > max_distance_m:
            raise RuntimeError(
                f"Border selection kept growing past {max_distance_m} m without "
                f"reaching a gap of {step_m} m with no new points"
            )
        count = _select_by_location(
            in_layer=points_layer,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=border_lines,
            search_distance=f"{distance_m} Meters",
        )
        logger.info(f"Border search at {distance_m:.2f} m selected {count} points")
        if count == previous_count or (previous_count is None and count == 0):
            break
        previous_count = count
        step += 1

    return _selected_line_oids(points_layer=points_layer, count=count)


def _resolve_border_groups(
    border_oids: set[int],
    signatures: dict[int, _LineSignature],
    copies: "_CopyIndex",
) -> tuple[set[int], set[int]]:
    """
    What:
        Groups every border line with its copies from other partitions, and returns
        the line kept from each group and all lines in the groups.

    How:
        Border lines are taken in order of src_index, then OID. A line already in a
        group is skipped. Its copies are looked up among all lines, so a copy whose
        midpoint is not near the border still joins the group. The lowest
        (src_index, OID) of each group is kept.
    """
    kept = set()
    grouped = set()
    ordered = sorted(
        (signatures[oid] for oid in border_oids if oid in signatures),
        key=lambda signature: (signature.src_index, signature.oid),
    )
    for signature in ordered:
        if signature.oid in grouped:
            continue
        group = [signature] + [
            copy
            for copy in copies.copies_of(signature=signature)
            if copy.oid not in grouped
        ]
        kept.add(min(group, key=lambda member: (member.src_index, member.oid)).oid)
        grouped.update(member.oid for member in group)
    return kept, grouped


def _select_main_line_oids(
    midpoints: str,
    fan_out_feature: str,
    partition_indices: list[int],
    layers: _Layers,
) -> set[int]:
    """
    Returns, for every partition N in partition_indices, the lines of output N whose
    midpoint is within fan-out cell N.
    """
    oids = set()
    for index in partition_indices:
        cell_layer = layers.make(
            in_features=fan_out_feature,
            where_clause=f"{PARTITION_INDEX_FIELD} = {index}",
        )
        points_layer = layers.make(
            in_features=midpoints, where_clause=f"{SRC_INDEX_FIELD} = {index}"
        )
        count = _select_by_location(
            in_layer=points_layer, overlap_type="WITHIN", select_features=cell_layer
        )
        if count == 0:
            logger.warning(f"No midpoints of output {index} within cell {index}")
        oids |= _selected_line_oids(points_layer=points_layer, count=count)
    return oids


def _select_dropped_cell_line_oids(
    midpoints: str, present_cells: str, fan_in_feature: str, layers: _Layers
) -> set[int]:
    """
    Returns the lines whose midpoint is within a fan-in cell that has no identical
    present fan-out cell: one that fan-out dropped for having no counted features,
    or one whose output is missing.
    """
    dropped_cells_layer = layers.make(in_features=fan_in_feature)
    dropped_count = _select_by_location(
        in_layer=dropped_cells_layer,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=present_cells,
        invert=True,
    )
    if dropped_count == 0:
        return set()

    points_layer = layers.make(in_features=midpoints)
    count = _select_by_location(
        in_layer=points_layer,
        overlap_type="WITHIN",
        select_features=dropped_cells_layer,
    )
    return _selected_line_oids(points_layer=points_layer, count=count)


def _select_by_location(
    in_layer: str,
    overlap_type: str,
    select_features: str,
    search_distance: str | None = None,
    invert: bool = False,
) -> int:
    """
    What:
        Makes a new selection on in_layer and returns how many features it selected.

    Why:
        A selection that selects nothing leaves the layer without a selection, and
        GetCount and cursors then see every feature. The count is read from the
        tool result instead, and callers must not read the layer when it is 0.
    """
    result = arcpy.management.SelectLayerByLocation(
        in_layer=in_layer,
        overlap_type=overlap_type,
        select_features=select_features,
        search_distance=search_distance,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT" if invert else "NOT_INVERT",
    )
    return int(result.getOutput(2))


def _selected_line_oids(points_layer: str, count: int) -> set[int]:
    """
    Returns the ORIG_FID of the selected midpoints, or none when count is 0.
    """
    if count == 0:
        return set()
    with arcpy.da.SearchCursor(points_layer, [ORIG_FID_FIELD]) as cursor:
        oids = {oid for (oid,) in cursor}
    if len(oids) != count:
        raise RuntimeError(
            f"Read {len(oids)} midpoints from {points_layer}, but the selection "
            f"reported {count}"
        )
    return oids


def _unmatched_line_oids(
    signatures: dict[int, _LineSignature], claimed_oids: set[int], tolerance_m: float
) -> set[int]:
    """
    Returns the lines that are not claimed and have no claimed copy from another
    partition.
    """
    claimed = _CopyIndex(tolerance_m=tolerance_m)
    for oid in claimed_oids:
        claimed.add(signature=signatures[oid])

    return {
        oid
        for oid, signature in signatures.items()
        if oid not in claimed_oids and not claimed.copies_of(signature=signature)
    }


class _CopyIndex:
    """
    What:
        Finds the copies of a line from other partitions: lines whose endpoints lie
        within tolerance_m of its endpoints, in either direction, and whose length
        differs by at most tolerance_m.

    How:
        Lines are bucketed by both endpoints on a grid of tolerance_m, so a lookup
        only compares lines with an endpoint in the 3 x 3 buckets around the start
        point of the line looked up.
    """

    def __init__(self, tolerance_m: float) -> None:
        self.tolerance_m = tolerance_m
        self._buckets: dict[tuple[int, int], list[_LineSignature]] = defaultdict(list)

    def add(self, signature: _LineSignature) -> None:
        start_bucket = self._bucket(xy=signature.start)
        end_bucket = self._bucket(xy=signature.end)
        self._buckets[start_bucket].append(signature)
        if end_bucket != start_bucket:
            self._buckets[end_bucket].append(signature)

    def copies_of(self, signature: _LineSignature) -> list[_LineSignature]:
        bx, by = self._bucket(xy=signature.start)
        found: dict[int, _LineSignature] = {}
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in self._buckets.get((bx + dx, by + dy), ()):
                    if (
                        other.src_index != signature.src_index
                        and other.oid not in found
                        and self._is_copy(a=signature, b=other)
                    ):
                        found[other.oid] = other
        return list(found.values())

    def _is_copy(self, a: _LineSignature, b: _LineSignature) -> bool:
        tolerance_m = self.tolerance_m
        if abs(a.length - b.length) > tolerance_m:
            return False
        same_direction = (
            math.dist(a.start, b.start) <= tolerance_m
            and math.dist(a.end, b.end) <= tolerance_m
        )
        reversed_direction = (
            math.dist(a.start, b.end) <= tolerance_m
            and math.dist(a.end, b.start) <= tolerance_m
        )
        return same_direction or reversed_direction

    def _bucket(self, xy: XY) -> tuple[int, int]:
        return (
            math.floor(xy[0] / self.tolerance_m),
            math.floor(xy[1] / self.tolerance_m),
        )


def _write_state(all_lines: str, states: dict[int, str]) -> None:
    with arcpy.da.UpdateCursor(all_lines, ["OID@", _STATE_FIELD]) as cursor:
        for oid, _ in cursor:
            if oid in states:
                cursor.updateRow([oid, states[oid]])


def _write_output(all_lines: str, state: str, output: str) -> None:
    arcpy.analysis.Select(
        in_features=all_lines,
        out_feature_class=output,
        where_clause=f"{_STATE_FIELD} = '{state}'",
    )
    arcpy.management.DeleteField(in_table=output, drop_field=[_STATE_FIELD])


def _log_summary(
    total: int,
    border: int,
    kept_border: int,
    claimed: int,
    unclaimed: int,
    unmatched: int,
) -> None:
    logger.info(
        f"Fan-in: {total} lines in all outputs, {border} border lines of which "
        f"{kept_border} kept, {claimed} claimed"
    )
    for name, count in (("unclaimed", unclaimed), ("unmatched", unmatched)):
        if count:
            logger.warning(f"{count} {name} lines, see the {name} output")
        else:
            logger.info(f"No {name} lines")


if __name__ == "__main__":
    environment_setup.main()

    INDEXED_OUTPUTS_GDB = r"C:\GIS_Files\imported\091126only_outputs.gdb"
    partitioning_gdb = GIS_FILES_ROOT / dn.raw_data / f"{dn.partitioning.lower()}.gdb"

    fan_in_partitions(
        indexed_outputs_gdb=INDEXED_OUTPUTS_GDB,
        fan_out_feature=str(partitioning_gdb / dn.road_partitions_fan_out),
        fan_in_feature=str(partitioning_gdb / dn.road_partitions_fan_in),
        output_feature=Road_N100.fan_in___road_output___n100_road.value,
        unclaimed_output=Road_N100.fan_in___unclaimed___n100_road.value,
        unmatched_output=Road_N100.fan_in___unmatched___n100_road.value,
        work_file_config=core_config.WorkFileConfig(
            root_file=Road_N100.fan_in___root___n100_road.value
        ),
        mode="partial",
    )
