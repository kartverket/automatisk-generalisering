"""
In new road input from nvdb ramps dont always extend all the way to main roads,
This causes the ramps generalisation to leave behind dangles.
This function handles those dangles.
Make it in such a way that we can reuse the logic to handle other similar cases of dangles.
Sitations where the dangle is one of the roads part of the crossroad then we convert the crossroad to a T cross in the same medium.
"""

import logging
import math
import os
from collections import defaultdict
from collections.abc import Iterator, Set
from typing import Any, TypeAlias

import arcpy

logger = logging.getLogger(__name__)

Point: TypeAlias = tuple[float, float]
Segment: TypeAlias = tuple[float, float, float, float]
Cell: TypeAlias = tuple[int, int]

_SNAP_TOLERANCE_M = 1.0
_RAMP_MATCH_TOLERANCE_M = 5.0
_INDEX_CELL_SIZE_M = 25.0
_OID_CHUNK_SIZE = 500
_LINES_LAYER = "dangling_lines_layer"
_RAMP_WHERE_CLAUSE = "typeveg = 'rampe'"
_REMOVABLE_WHERE_CLAUSE = "objtype = 'VegSenterlinje'"


def _cell(point: Point, size: float) -> Cell:
    return math.floor(point[0] / size), math.floor(point[1] / size)


def _point_segment_distance(point: Point, segment: Segment) -> float:
    x, y = point
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length_sq))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


class _SegmentIndex:
    """Grid index answering whether a point is within `tolerance` of any indexed segment."""

    def __init__(self, tolerance: float) -> None:
        self._tolerance = tolerance
        self._cells: dict[Cell, list[tuple[int, Segment]]] = defaultdict(list)

    def add(self, oid: int, segment: Segment) -> None:
        x1, y1, x2, y2 = segment
        size, pad = _INDEX_CELL_SIZE_M, self._tolerance
        min_cx = math.floor((min(x1, x2) - pad) / size)
        max_cx = math.floor((max(x1, x2) + pad) / size)
        min_cy = math.floor((min(y1, y2) - pad) / size)
        max_cy = math.floor((max(y1, y2) + pad) / size)
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                self._cells[(cx, cy)].append((oid, segment))

    def has_within(self, point: Point, ignore: Set[int]) -> bool:
        for oid, segment in self._cells.get(_cell(point, _INDEX_CELL_SIZE_M), ()):
            if oid not in ignore and (
                _point_segment_distance(point, segment) <= self._tolerance
            ):
                return True
        return False


class _NodeIndex:
    """Merges endpoints closer than the snap tolerance into one node."""

    def __init__(self, tolerance: float) -> None:
        self._tolerance = tolerance
        self._cells: dict[Cell, list[int]] = defaultdict(list)
        self.xy: list[Point] = []

    def find_or_add(self, point: Point) -> int:
        cx, cy = _cell(point, self._tolerance)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for node in self._cells.get((cx + dx, cy + dy), ()):
                    nx, ny = self.xy[node]
                    if math.hypot(point[0] - nx, point[1] - ny) <= self._tolerance:
                        return node
        node = len(self.xy)
        self.xy.append(point)
        self._cells[(cx, cy)].append(node)
        return node


class _EndpointGraph:
    """Line endpoints as nodes; a dangle is a node with exactly one line attached."""

    def __init__(self) -> None:
        self.nodes = _NodeIndex(_SNAP_TOLERANCE_M)
        self.line_nodes: dict[int, tuple[int, int]] = {}
        self.node_lines: dict[int, set[int]] = defaultdict(set)
        self._segments = _SegmentIndex(_SNAP_TOLERANCE_M)

    def add_line(self, oid: int, segments: list[Segment]) -> None:
        first, last = segments[0], segments[-1]
        start = self.nodes.find_or_add((first[0], first[1]))
        end = self.nodes.find_or_add((last[2], last[3]))
        self.line_nodes[oid] = (start, end)
        self.node_lines[start].add(oid)
        self.node_lines[end].add(oid)
        for segment in segments:
            self._segments.add(oid, segment)

    def remove_line(self, oid: int) -> None:
        for node in self.line_nodes.pop(oid):
            self.node_lines[node].discard(oid)

    def _degree(self, node: int) -> int:
        # A closed line has both ends on the node.
        return sum(
            2 if self.line_nodes[oid][0] == self.line_nodes[oid][1] else 1
            for oid in self.node_lines[node]
        )

    def is_dangle(self, node: int, removed: Set[int]) -> bool:
        """True if one line ends at the node and no other line passes through it."""
        if self._degree(node) != 1:
            return False
        ignore = removed | self.node_lines[node]
        return not self._segments.has_within(self.nodes.xy[node], ignore)


def _read_segments(fc: str, where_clause: str) -> Iterator[tuple[int, list[Segment]]]:
    with arcpy.da.SearchCursor(
        fc, ["OID@", "SHAPE@"], where_clause=where_clause
    ) as cursor:
        for oid, shape in cursor:
            if shape is None:
                continue
            segments: list[Segment] = []
            for part in shape:
                points = [p for p in part if p is not None]
                segments.extend(
                    (a.X, a.Y, b.X, b.Y) for a, b in zip(points, points[1:])
                )
            if segments:
                yield oid, segments


def _build_graph(lines_fc: str) -> _EndpointGraph:
    graph = _EndpointGraph()
    for oid, segments in _read_segments(lines_fc, _REMOVABLE_WHERE_CLAUSE):
        graph.add_line(oid, segments)
    return graph


def _build_ramp_index(ramp_reference_fc: str) -> _SegmentIndex:
    index = _SegmentIndex(_RAMP_MATCH_TOLERANCE_M)
    for oid, segments in _read_segments(ramp_reference_fc, _RAMP_WHERE_CLAUSE):
        for segment in segments:
            index.add(oid, segment)
    return index


def _remove_in_waves(
    graph: _EndpointGraph, ramp_index: _SegmentIndex, max_iterations: int
) -> tuple[list[int], list[list[int]]]:
    """Remove dangling lines wave by wave; return removed OIDs and the dangle nodes per wave."""
    removed: set[int] = set()
    removed_oids: list[int] = []
    waves: list[list[int]] = []
    no_ignore: frozenset[int] = frozenset()

    wave = [
        node
        for node, xy in enumerate(graph.nodes.xy)
        if graph.is_dangle(node, removed) and ramp_index.has_within(xy, no_ignore)
    ]
    for iteration in range(1, max_iterations + 1):
        if not wave:
            break
        acted: list[int] = []
        exposed: list[int] = []
        for node in wave:
            if not graph.is_dangle(node, removed):
                continue
            (oid,) = graph.node_lines[node]
            start, end = graph.line_nodes[oid]
            graph.remove_line(oid)
            removed.add(oid)
            removed_oids.append(oid)
            acted.append(node)
            other = end if start == node else start
            if other not in exposed and graph.is_dangle(other, removed):
                exposed.append(other)
        waves.append(acted)
        logger.info(
            "Dangle removal iteration %d: %d dangles, %d lines removed",
            iteration,
            len(wave),
            len(acted),
        )
        wave = exposed
    else:
        logger.warning("Dangle removal stopped at max_iterations=%d", max_iterations)

    return removed_oids, waves


def _write_points(points: list[Point], out_fc: str, spatial_reference: Any) -> None:
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(out_fc),
        out_name=os.path.basename(out_fc),
        geometry_type="POINT",
        spatial_reference=spatial_reference,
    )
    with arcpy.da.InsertCursor(out_fc, ["SHAPE@XY"]) as cursor:
        for point in points:
            cursor.insertRow([point])


def _create_removed_fc(template_fc: str, removed_fc: str) -> None:
    if arcpy.Exists(removed_fc):
        arcpy.management.Delete(removed_fc)

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(removed_fc),
        out_name=os.path.basename(removed_fc),
        geometry_type="POLYLINE",
        template=template_fc,
        spatial_reference=arcpy.Describe(template_fc).spatialReference,
    )


def _move_lines_to_removed(lines_fc: str, removed_fc: str, oids: list[int]) -> None:
    """Copy the lines with `oids` to `removed_fc` and delete them from `lines_fc`."""
    if not oids:
        return

    oid_field = arcpy.Describe(lines_fc).OIDFieldName
    arcpy.management.MakeFeatureLayer(lines_fc, _LINES_LAYER)
    selection_type = "NEW_SELECTION"
    for start in range(0, len(oids), _OID_CHUNK_SIZE):
        chunk = ",".join(str(oid) for oid in oids[start : start + _OID_CHUNK_SIZE])
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=_LINES_LAYER,
            selection_type=selection_type,
            where_clause=f"{oid_field} IN ({chunk})",
        )
        selection_type = "ADD_TO_SELECTION"
    arcpy.management.Append(
        inputs=_LINES_LAYER, target=removed_fc, schema_type="NO_TEST"
    )
    arcpy.management.DeleteFeatures(_LINES_LAYER)
    arcpy.management.Delete(_LINES_LAYER)


def remove_new_dangles(
    lines_fc: str,
    ramp_reference_fc: str,
    removed_fc: str,
    max_iterations: int = 20,
    dangle_iterations_prefix: str | None = None,
) -> int:
    """Remove ramp dangles from `lines_fc`, then the dangles each removal exposes.

    Dangles come from an endpoint graph of the `VegSenterlinje` lines: a dangle is an
    endpoint with one line attached that no other line passes through. The starting
    dangles are those on `typeveg = 'rampe'` lines in `ramp_reference_fc`. Removing a
    line can expose a new dangle at its other end, so removal repeats in waves until
    no dangle is left.

    Args:
        lines_fc: Line feature class edited in place.
        ramp_reference_fc: Lines with `typeveg`; dangles on its ramps are the starting dangles.
        removed_fc: Permanent output; receives a copy of every removed line.
        max_iterations: Safety limit for the number of waves.
        dangle_iterations_prefix: If set, the dangles removed in each wave are
            saved permanently as `<prefix>_ite1`, `<prefix>_ite2`, ...

    Returns:
        Total number of removed lines.
    """
    _create_removed_fc(template_fc=lines_fc, removed_fc=removed_fc)

    graph = _build_graph(lines_fc)
    ramp_index = _build_ramp_index(ramp_reference_fc)
    removed_oids, waves = _remove_in_waves(graph, ramp_index, max_iterations)

    if dangle_iterations_prefix:
        spatial_reference = arcpy.Describe(lines_fc).spatialReference
        for iteration, nodes in enumerate(waves, start=1):
            _write_points(
                points=[graph.nodes.xy[node] for node in nodes],
                out_fc=f"{dangle_iterations_prefix}_ite{iteration}",
                spatial_reference=spatial_reference,
            )

    _move_lines_to_removed(lines_fc, removed_fc, removed_oids)
    return len(removed_oids)


if __name__ == "__main__":
    import arcpy
    from env_setup import environment_setup
    from file_manager.n100.file_manager_roads import Road_N100

    environment_setup.main()

    src = Road_N100.ramps__generalized_ramps__n100_road.value
    test_lines = (
        f"{src}_dangle_test"  # scratch copy, the permanent file stays untouched
    )
    test_removed = f"{src}_dangle_test_removed"

    arcpy.management.CopyFeatures(src, test_lines)
    removed = remove_new_dangles(
        lines_fc=test_lines,
        ramp_reference_fc=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        removed_fc=test_removed,
        dangle_iterations_prefix=f"{src}_dangle_test",
    )
    print(f"Removed {removed} lines")
