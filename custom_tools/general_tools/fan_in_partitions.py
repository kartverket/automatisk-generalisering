import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass

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
# name and differ per pod. ORIG_FID would clash with the ORIG_FID that
# FeatureToPoint adds, which links each centre point to its line.
DROPPED_FIELD_PREFIXES = ("fid_", "orig_fid")

XY = tuple[float, float]


@dataclass
class _LineSignature:
    oid: int
    src_index: int
    start: XY
    centre: XY
    end: XY


def fan_in_partitions(
    indexed_outputs_gdb: str,
    fan_out_feature: str,
    fan_in_feature: str,
    output_feature: str,
    unclaimed_output: str,
    unmatched_output: str,
    work_file_config: core_config.WorkFileConfig,
    output_name_prefix: str = "final_output",
    match_tolerance_m: float = 1.0,
    border_step_m: float = 0.02,
    max_border_distance_m: float = 1.0,
) -> None:
    """
    What:
        Merges the per-partition outputs {output_name_prefix}_0 to _{N-1} into one
        feature where every line is claimed by exactly one partition, and writes the
        lines that no partition claimed for troubleshooting.

    How:
        - N is read from the fan-out partition_index values. The indexed outputs gdb
          must hold exactly the N outputs, and their schemas must match.
        - The outputs are merged with a src_index field, and every line gets a
          centre point (FeatureToPoint INSIDE) whose ORIG_FID is the line.
        - Border: centre points near the fan-out cell boundaries are selected with
          a search distance growing by border_step_m until no new points are added.
          Their lines are deduplicated across partitions, keeping the lowest
          src_index, and taken out of the main selection.
        - Main: for each partition N, the lines of output N whose centre point is
          within fan-out cell N.
        - Lines that are not claimed and have no claimed line from another
          partition sharing start, centre and end within match_tolerance_m are
          written out: as unclaimed when their centre point is within a fan-in cell
          that fan-out dropped, otherwise as unmatched.

    Why:
        Each partition output holds its halo as well, so the same road appears in
        several outputs. The outputs also differ by an XY resolution offset, so
        copies of a road are matched by tolerance rather than by identical geometry.
        A border copy just outside the search distance is caught by growing the
        distance until a gap with no new points is found.

    Args:
        indexed_outputs_gdb (str): The gdb holding only the per-partition outputs.
        fan_out_feature (str): The fan-out partition feature the outputs came from.
        fan_in_feature (str): The fan-in partition feature, all cells.
        output_feature (str): The merged output, with src_index.
        unclaimed_output (str): Lines with no claimed copy whose centre lies in a
            dropped cell.
        unmatched_output (str): Other lines with no claimed copy.
        work_file_config (core_config.WorkFileConfig): Work file configuration.
        output_name_prefix (str): Name of the outputs before the _N index.
        match_tolerance_m (float): Distance within which start, centre and end
            points of two lines must lie for them to be copies of one road.
        border_step_m (float): Step the border search distance grows by.
        max_border_distance_m (float): Border search distance at which the run
            fails instead of growing further.
    """
    partition_count = _partition_count(fan_out_feature=fan_out_feature)
    indexed_outputs = _indexed_outputs(
        gdb=indexed_outputs_gdb,
        prefix=output_name_prefix,
        partition_count=partition_count,
    )
    _check_schemas(indexed_outputs=indexed_outputs)
    logger.info(f"Fanning in {partition_count} partitions from {indexed_outputs_gdb}")

    wfm = WorkFileManager(config=work_file_config)
    all_lines = wfm.build_file_path("all_lines")
    centre_points = wfm.build_file_path("centre_points")
    border_lines = wfm.build_file_path("border_lines")
    layers = _Layers()

    try:
        _merge_with_src_index(
            indexed_outputs=indexed_outputs, all_lines=all_lines, wfm=wfm
        )
        arcpy.management.FeatureToPoint(
            in_features=all_lines,
            out_feature_class=centre_points,
            point_location="INSIDE",
        )
        arcpy.management.PolygonToLine(
            in_features=fan_out_feature,
            out_feature_class=border_lines,
            neighbor_option="IGNORE_NEIGHBORS",
        )
        signatures = _line_signatures(all_lines=all_lines, centre_points=centre_points)

        border_oids = _select_border_line_oids(
            centre_points=centre_points,
            border_lines=border_lines,
            step_m=border_step_m,
            max_distance_m=max_border_distance_m,
            layers=layers,
        )
        kept_border_oids = _deduplicate(
            candidates=[signatures[oid] for oid in border_oids if oid in signatures],
            tolerance_m=match_tolerance_m,
        )
        main_oids = (
            _select_main_line_oids(
                centre_points=centre_points,
                fan_out_feature=fan_out_feature,
                partition_count=partition_count,
                layers=layers,
            )
            - border_oids
        )
        claimed_oids = main_oids | kept_border_oids

        unmatched_oids = _unmatched_line_oids(
            signatures=signatures,
            claimed_oids=claimed_oids,
            tolerance_m=match_tolerance_m,
        )
        unclaimed_oids = unmatched_oids & _select_dropped_cell_line_oids(
            centre_points=centre_points,
            fan_out_feature=fan_out_feature,
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
            border=len(border_oids),
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


def _indexed_outputs(gdb: str, prefix: str, partition_count: int) -> list[str]:
    """
    Returns the paths of {prefix}_0 to {prefix}_{N-1}, which must be the only
    feature classes in gdb.
    """
    if not arcpy.Exists(gdb):
        raise FileNotFoundError(f"Indexed outputs gdb not found: {gdb}")

    found = {
        name
        for _, _, names in arcpy.da.Walk(gdb, datatype="FeatureClass")
        for name in names
    }
    expected = [f"{prefix}_{index}" for index in range(partition_count)]
    missing = set(expected) - found
    extra = found - set(expected)
    if missing or extra:
        raise RuntimeError(
            f"{gdb} must hold exactly {prefix}_0 to {prefix}_{partition_count - 1}."
            f"\nMissing: {sorted(missing)}\nExtra: {sorted(extra)}"
        )
    return [os.path.join(gdb, name) for name in expected]


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
    indexed_outputs: list[str], all_lines: str, wfm: WorkFileManager
) -> None:
    """
    Merges the indexed outputs into all_lines with their index in src_index, after
    removing the dropped fields. The append fails on any schema mismatch between
    the outputs.
    """
    copies = []
    for index, indexed_output in enumerate(indexed_outputs):
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


def _line_signatures(all_lines: str, centre_points: str) -> dict[int, _LineSignature]:
    """
    Returns the start, centre and end point of every line, keyed by its OID.
    Lines without geometry have no centre point and are left out.
    """
    with arcpy.da.SearchCursor(centre_points, ["ORIG_FID", "SHAPE@XY"]) as cursor:
        centres = {oid: xy for oid, xy in cursor}

    signatures = {}
    with arcpy.da.SearchCursor(
        all_lines, ["OID@", SRC_INDEX_FIELD, "SHAPE@"]
    ) as cursor:
        for oid, src_index, shape in cursor:
            if shape is None or oid not in centres:
                logger.warning(f"Line {oid} from output {src_index} has no geometry")
                continue
            signatures[oid] = _LineSignature(
                oid=oid,
                src_index=src_index,
                start=(shape.firstPoint.X, shape.firstPoint.Y),
                centre=centres[oid],
                end=(shape.lastPoint.X, shape.lastPoint.Y),
            )
    return signatures


def _select_border_line_oids(
    centre_points: str,
    border_lines: str,
    step_m: float,
    max_distance_m: float,
    layers: _Layers,
) -> set[int]:
    """
    What:
        Returns the lines whose centre point is near a fan-out cell boundary.

    How:
        The search distance starts at step_m and grows by step_m until a step
        selects no new points. If the first step selects nothing, there are no
        border lines.
    """
    points_layer = layers.make(in_features=centre_points)
    step = 1
    previous_count = None
    while True:
        distance_m = step * step_m
        if distance_m > max_distance_m:
            raise RuntimeError(
                f"Border selection kept growing past {max_distance_m} m without "
                f"reaching a gap of {step_m} m with no new points"
            )
        arcpy.management.SelectLayerByLocation(
            in_layer=points_layer,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=border_lines,
            search_distance=f"{distance_m} Meters",
            selection_type="NEW_SELECTION",
        )
        count = _count(points_layer)
        logger.info(f"Border search at {distance_m:.2f} m selected {count} points")
        if count == previous_count or (previous_count is None and count == 0):
            break
        previous_count = count
        step += 1

    if count == 0:
        return set()
    with arcpy.da.SearchCursor(points_layer, ["ORIG_FID"]) as cursor:
        return {oid for (oid,) in cursor}


def _deduplicate(candidates: list[_LineSignature], tolerance_m: float) -> set[int]:
    """
    Returns the border lines to keep: one line per set of copies across
    partitions, the one with the lowest src_index. Lines from the same partition
    are never treated as copies of each other.
    """
    kept: dict[tuple[int, int], list[_LineSignature]] = defaultdict(list)
    kept_oids = set()
    for candidate in sorted(candidates, key=lambda s: (s.src_index, s.oid)):
        if not _has_copy(signature=candidate, index=kept, tolerance_m=tolerance_m):
            kept[_bucket(xy=candidate.centre, size=tolerance_m)].append(candidate)
            kept_oids.add(candidate.oid)
    return kept_oids


def _select_main_line_oids(
    centre_points: str, fan_out_feature: str, partition_count: int, layers: _Layers
) -> set[int]:
    """
    Returns, for every partition N, the lines of output N whose centre point is
    within fan-out cell N.
    """
    oids = set()
    for index in range(partition_count):
        cell_layer = layers.make(
            in_features=fan_out_feature,
            where_clause=f"{PARTITION_INDEX_FIELD} = {index}",
        )
        points_layer = layers.make(
            in_features=centre_points, where_clause=f"{SRC_INDEX_FIELD} = {index}"
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=points_layer,
            overlap_type="WITHIN",
            select_features=cell_layer,
            selection_type="NEW_SELECTION",
        )
        with arcpy.da.SearchCursor(points_layer, ["ORIG_FID"]) as cursor:
            oids.update(oid for (oid,) in cursor)
    return oids


def _select_dropped_cell_line_oids(
    centre_points: str, fan_out_feature: str, fan_in_feature: str, layers: _Layers
) -> set[int]:
    """
    Returns the lines whose centre point is within a fan-in cell that fan-out
    dropped for having no counted features.
    """
    dropped_cells_layer = layers.make(in_features=fan_in_feature)
    arcpy.management.SelectLayerByLocation(
        in_layer=dropped_cells_layer,
        overlap_type="ARE_IDENTICAL_TO",
        select_features=fan_out_feature,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )
    if _count(dropped_cells_layer) == 0:
        return set()

    points_layer = layers.make(in_features=centre_points)
    arcpy.management.SelectLayerByLocation(
        in_layer=points_layer,
        overlap_type="WITHIN",
        select_features=dropped_cells_layer,
        selection_type="NEW_SELECTION",
    )
    if _count(points_layer) == 0:
        return set()
    with arcpy.da.SearchCursor(points_layer, ["ORIG_FID"]) as cursor:
        return {oid for (oid,) in cursor}


def _unmatched_line_oids(
    signatures: dict[int, _LineSignature], claimed_oids: set[int], tolerance_m: float
) -> set[int]:
    """
    Returns the lines that are not claimed and have no claimed copy from another
    partition.
    """
    claimed: dict[tuple[int, int], list[_LineSignature]] = defaultdict(list)
    for oid in claimed_oids:
        signature = signatures[oid]
        claimed[_bucket(xy=signature.centre, size=tolerance_m)].append(signature)

    return {
        oid
        for oid, signature in signatures.items()
        if oid not in claimed_oids
        and not _has_copy(signature=signature, index=claimed, tolerance_m=tolerance_m)
    }


def _has_copy(
    signature: _LineSignature,
    index: dict[tuple[int, int], list[_LineSignature]],
    tolerance_m: float,
) -> bool:
    """
    Returns whether index holds a line from another partition whose start, centre
    and end lie within tolerance_m of signature's, in either direction.
    """
    bx, by = _bucket(xy=signature.centre, size=tolerance_m)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for other in index.get((bx + dx, by + dy), ()):
                if other.src_index != signature.src_index and _is_copy(
                    a=signature, b=other, tolerance_m=tolerance_m
                ):
                    return True
    return False


def _is_copy(a: _LineSignature, b: _LineSignature, tolerance_m: float) -> bool:
    if math.dist(a.centre, b.centre) > tolerance_m:
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


def _bucket(xy: XY, size: float) -> tuple[int, int]:
    return math.floor(xy[0] / size), math.floor(xy[1] / size)


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


def _count(feature: str) -> int:
    return int(arcpy.management.GetCount(feature)[0])


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

    INDEXED_OUTPUTS_GDB = (
        r"C:\GIS_Files\ag_outputs\n100\indexed_only_outputs\only_outputs.gdb"
    )
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
    )
