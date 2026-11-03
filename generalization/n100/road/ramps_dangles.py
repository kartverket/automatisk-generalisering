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
from dataclasses import dataclass, field
from typing import Any, TypeAlias

import arcpy

logger = logging.getLogger(__name__)


Point: TypeAlias = tuple[float, float]
Segment: TypeAlias = tuple[float, float, float, float]
Cell: TypeAlias = tuple[int, int]

_SNAP_TOLERANCE_M = 1.0
_RAMP_MATCH_TOLERANCE_M = 1.0
_INDEX_CELL_SIZE_M = 25.0
_MEDIUM_FIELD = "medium"
_RAMP_ID_FIELD = "ramp_id"
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


def _segment_intersection(a: Segment, b: Segment) -> tuple[float, Point] | None:
    """Return the fraction along `a` and the point where `a` and `b` cross, if they do."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    rx, ry = ax2 - ax1, ay2 - ay1
    sx, sy = bx2 - bx1, by2 - by1
    denom = rx * sy - ry * sx
    if denom == 0.0:
        return None
    qx, qy = bx1 - ax1, by1 - ay1
    t = (qx * sy - qy * sx) / denom
    u = (qx * ry - qy * rx) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t, (ax1 + t * rx, ay1 + t * ry)
    return None


def _reverse_segments(segments: list[Segment]) -> list[Segment]:
    return [(x2, y2, x1, y1) for x1, y1, x2, y2 in reversed(segments)]


@dataclass
class _Line:
    segments: list[Segment]
    medium: str | None = None
    ramp_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class _Crossing:
    other_oid: int
    segment_index: int
    point: Point
    shared_ramp_ids: frozenset[str]
    oriented_segments: tuple[Segment, ...]


@dataclass(frozen=True)
class _Split:
    oid: int
    point: Point
    dangle_at_start: bool


@dataclass
class _WaveResult:
    removed_oids: list[int]
    splits: list[_Split]
    ramp_changed: set[int]
    waves: list[list[int]]


class _SegmentIndex:
    """Grid index answering whether a point is within `tolerance` of any indexed segment."""

    def __init__(self, tolerance: float) -> None:
        self._tolerance = tolerance
        self._cells: dict[Cell, list[tuple[int, Segment]]] = defaultdict(list)
        self._dead: set[tuple[int, Segment]] = set()

    def add(self, oid: int, segment: Segment) -> None:
        self._dead.discard((oid, segment))
        x1, y1, x2, y2 = segment
        size, pad = _INDEX_CELL_SIZE_M, self._tolerance
        min_cx = math.floor((min(x1, x2) - pad) / size)
        max_cx = math.floor((max(x1, x2) + pad) / size)
        min_cy = math.floor((min(y1, y2) - pad) / size)
        max_cy = math.floor((max(y1, y2) + pad) / size)
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                self._cells[(cx, cy)].append((oid, segment))

    def kill(self, oid: int, segments: list[Segment]) -> None:
        """Stop reporting these segments; they stay in the cells."""
        self._dead.update((oid, segment) for segment in segments)

    def candidates(self, segment: Segment) -> Iterator[tuple[int, Segment]]:
        """Yield indexed segments whose cells overlap the bounding box of `segment`."""
        x1, y1, x2, y2 = segment
        size = _INDEX_CELL_SIZE_M
        seen: set[tuple[int, Segment]] = set()
        for cx in range(
            math.floor(min(x1, x2) / size), math.floor(max(x1, x2) / size) + 1
        ):
            for cy in range(
                math.floor(min(y1, y2) / size), math.floor(max(y1, y2) / size) + 1
            ):
                for entry in self._cells.get((cx, cy), ()):
                    if entry not in seen and entry not in self._dead:
                        seen.add(entry)
                        yield entry

    def has_within(self, point: Point, ignore: Set[int]) -> bool:
        for entry in self._cells.get(_cell(point, _INDEX_CELL_SIZE_M), ()):
            oid, segment = entry
            if (
                oid not in ignore
                and entry not in self._dead
                and _point_segment_distance(point, segment) <= self._tolerance
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
        self.lines: dict[int, _Line] = {}
        self.line_nodes: dict[int, tuple[int, int]] = {}
        self.node_lines: dict[int, set[int]] = defaultdict(set)
        self._segments = _SegmentIndex(_SNAP_TOLERANCE_M)

    def add_line(self, oid: int, line: _Line) -> None:
        first, last = line.segments[0], line.segments[-1]
        start = self.nodes.find_or_add((first[0], first[1]))
        end = self.nodes.find_or_add((last[2], last[3]))
        self.lines[oid] = line
        self.line_nodes[oid] = (start, end)
        self.node_lines[start].add(oid)
        self.node_lines[end].add(oid)
        for segment in line.segments:
            self._segments.add(oid, segment)

    def remove_line(self, oid: int) -> None:
        self._segments.kill(oid, self.lines[oid].segments)
        for node in self.line_nodes.pop(oid):
            self.node_lines[node].discard(oid)

    def _degree(self, node: int) -> int:
        # A closed line has both ends on the node.
        return sum(
            2 if self.line_nodes[oid][0] == self.line_nodes[oid][1] else 1
            for oid in self.node_lines[node]
        )

    def is_dangle(self, node: int) -> bool:
        """True if one line ends at the node and no other line passes through it."""
        if self._degree(node) != 1:
            return False
        return not self._segments.has_within(self.nodes.xy[node], self.node_lines[node])

    def find_crossing(self, oid: int, dangle_node: int) -> _Crossing | None:
        """First crossing, from the dangle, with a road of another medium and a shared ramp id."""
        line = self.lines[oid]
        if not line.medium or not line.ramp_ids:
            return None
        oriented = (
            line.segments
            if self.line_nodes[oid][0] == dangle_node
            else _reverse_segments(line.segments)
        )
        ends = [(oriented[0][0], oriented[0][1]), (oriented[-1][2], oriented[-1][3])]
        for index, segment in enumerate(oriented):
            best: tuple[float, _Crossing] | None = None
            for other_oid, other_segment in self._segments.candidates(segment):
                other = self.lines.get(other_oid)
                if other_oid == oid or other is None:
                    continue
                shared = line.ramp_ids & other.ramp_ids
                if not other.medium or other.medium == line.medium or not shared:
                    continue
                hit = _segment_intersection(segment, other_segment)
                if hit is None:
                    continue
                fraction, point = hit
                if any(math.dist(point, end) < _SNAP_TOLERANCE_M for end in ends):
                    continue
                if best is None or fraction < best[0]:
                    best = (
                        fraction,
                        _Crossing(
                            other_oid=other_oid,
                            segment_index=index,
                            point=point,
                            shared_ramp_ids=frozenset(shared),
                            oriented_segments=tuple(oriented),
                        ),
                    )
            if best is not None:
                return best[1]
        return None

    def split_line(self, oid: int, dangle_node: int, crossing: _Crossing) -> _Split:
        """Cut off the dangle side at `crossing`; the kept part takes the crossed road's medium."""
        line, other = self.lines[oid], self.lines[crossing.other_oid]
        start, end = self.line_nodes[oid]
        px, py = crossing.point
        oriented = crossing.oriented_segments
        _, _, x2, y2 = oriented[crossing.segment_index]
        kept = [(px, py, x2, y2), *oriented[crossing.segment_index + 1 :]]

        self._segments.kill(oid, line.segments)
        line.segments = kept
        for segment in kept:
            self._segments.add(oid, segment)

        far = end if start == dangle_node else start
        cut_node = self.nodes.find_or_add(crossing.point)
        self.node_lines[dangle_node].discard(oid)
        self.line_nodes[oid] = (far, cut_node)
        self.node_lines[cut_node].add(oid)

        line.medium = other.medium
        line.ramp_ids -= crossing.shared_ramp_ids
        other.ramp_ids -= crossing.shared_ramp_ids
        return _Split(
            oid=oid, point=crossing.point, dangle_at_start=start == dangle_node
        )


def _parse_ramp_ids(value: object) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def _read_lines(fc: str, where_clause: str) -> Iterator[tuple[int, _Line]]:
    names = {f.name for f in arcpy.ListFields(fc)}
    extra = [name for name in (_MEDIUM_FIELD, _RAMP_ID_FIELD) if name in names]
    with arcpy.da.SearchCursor(
        fc, ["OID@", "SHAPE@", *extra], where_clause=where_clause
    ) as cursor:
        for row in cursor:
            oid, shape = row[0], row[1]
            if shape is None:
                continue
            attributes = dict(zip(extra, row[2:]))
            segments: list[Segment] = []
            for part in shape:
                points = [p for p in part if p is not None]
                segments.extend(
                    (a.X, a.Y, b.X, b.Y) for a, b in zip(points, points[1:])
                )
            if segments:
                yield (
                    oid,
                    _Line(
                        segments=segments,
                        medium=attributes.get(_MEDIUM_FIELD),
                        ramp_ids=_parse_ramp_ids(attributes.get(_RAMP_ID_FIELD)),
                    ),
                )


def _build_graph(lines_fc: str) -> _EndpointGraph:
    graph = _EndpointGraph()
    for oid, line in _read_lines(lines_fc, _REMOVABLE_WHERE_CLAUSE):
        graph.add_line(oid, line)
    return graph


def _build_ramp_index(ramp_reference_fc: str) -> _SegmentIndex:
    index = _SegmentIndex(_RAMP_MATCH_TOLERANCE_M)
    for oid, line in _read_lines(ramp_reference_fc, _RAMP_WHERE_CLAUSE):
        for segment in line.segments:
            index.add(oid, segment)
    return index


def _remove_in_waves(
    graph: _EndpointGraph, ramp_index: _SegmentIndex, max_iterations: int
) -> _WaveResult:
    """Remove or split dangling lines wave by wave, recording the dangle nodes per wave."""
    result = _WaveResult(removed_oids=[], splits=[], ramp_changed=set(), waves=[])
    split_oids: set[int] = set()
    no_ignore: frozenset[int] = frozenset()

    wave = [
        node
        for node, xy in enumerate(graph.nodes.xy)
        if graph.is_dangle(node) and ramp_index.has_within(xy, no_ignore)
    ]
    for iteration in range(1, max_iterations + 1):
        if not wave:
            break
        acted: list[int] = []
        exposed: list[int] = []
        for node in wave:
            if not graph.is_dangle(node):
                continue
            (oid,) = graph.node_lines[node]
            # A split line keeps its original geometry in the edits, so it is not cut again.
            if oid in split_oids:
                continue
            acted.append(node)
            crossing = graph.find_crossing(oid, node)
            if crossing is not None:
                result.splits.append(graph.split_line(oid, node, crossing))
                result.ramp_changed.add(crossing.other_oid)
                split_oids.add(oid)
                continue
            start, end = graph.line_nodes[oid]
            graph.remove_line(oid)
            result.removed_oids.append(oid)
            other = end if start == node else start
            if other not in exposed and graph.is_dangle(other):
                exposed.append(other)
        result.waves.append(acted)
        logger.info(
            "Dangle removal iteration %d: %d dangles handled", iteration, len(acted)
        )
        wave = exposed
    else:
        logger.warning("Dangle removal stopped at max_iterations=%d", max_iterations)

    return result


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


def _cut_shape(shape: Any, split: _Split) -> tuple[Any, Any]:
    """Return the (dangle side, kept side) pieces of `shape` cut at the split point."""
    cut_point = arcpy.PointGeometry(arcpy.Point(*split.point), shape.spatialReference)
    along = shape.queryPointAndDistance(cut_point)[1]
    before = shape.segmentAlongLine(0, along)
    after = shape.segmentAlongLine(along, shape.length)
    return (before, after) if split.dangle_at_start else (after, before)


def _write_attributes(
    row: list[Any], index: dict[str, int], line: _Line, set_medium: bool
) -> None:
    if set_medium and _MEDIUM_FIELD in index:
        row[index[_MEDIUM_FIELD]] = line.medium
    if _RAMP_ID_FIELD in index:
        row[index[_RAMP_ID_FIELD]] = ",".join(sorted(line.ramp_ids)) or None


def _apply_edits(
    lines_fc: str, removed_fc: str, graph: _EndpointGraph, result: _WaveResult
) -> None:
    """Delete removed lines, cut split lines and update ramp ids; removed parts go to `removed_fc`."""
    removed = set(result.removed_oids)
    splits = {split.oid: split for split in result.splits}
    if not (removed or splits or result.ramp_changed):
        return

    field_names = [
        f.name
        for f in arcpy.ListFields(lines_fc)
        if f.editable and f.type not in ("OID", "Geometry")
    ]
    index = {name: position for position, name in enumerate(field_names, start=2)}
    removed_rows: list[list[Any]] = []
    with arcpy.da.UpdateCursor(lines_fc, ["OID@", "SHAPE@", *field_names]) as cursor:
        for row in cursor:
            oid = row[0]
            if oid in removed:
                removed_rows.append(row[1:])
                cursor.deleteRow()
            elif oid in splits:
                dangle_piece, kept_piece = _cut_shape(row[1], splits[oid])
                removed_rows.append([dangle_piece, *row[2:]])
                row[1] = kept_piece
                _write_attributes(row, index, graph.lines[oid], set_medium=True)
                cursor.updateRow(row)
            elif oid in result.ramp_changed:
                _write_attributes(row, index, graph.lines[oid], set_medium=False)
                cursor.updateRow(row)

    with arcpy.da.InsertCursor(removed_fc, ["SHAPE@", *field_names]) as cursor:
        for removed_row in removed_rows:
            cursor.insertRow(removed_row)


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

    A dangling line that crosses another road with a different medium and a shared
    `ramp_id` is not removed whole: it is cut at the first such crossing, the dangle
    side goes to `removed_fc`, and the kept part takes the crossed road's medium. The
    shared ids are removed from `ramp_id` on both the kept part and the crossed road.
    A line that has been cut is not processed again.

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
    result = _remove_in_waves(graph, ramp_index, max_iterations)

    if dangle_iterations_prefix:
        spatial_reference = arcpy.Describe(lines_fc).spatialReference
        for iteration, nodes in enumerate(result.waves, start=1):
            _write_points(
                points=[graph.nodes.xy[node] for node in nodes],
                out_fc=f"{dangle_iterations_prefix}_ite{iteration}",
                spatial_reference=spatial_reference,
            )

    _apply_edits(lines_fc, removed_fc, graph, result)
    logger.info(
        "Removed %d lines and split %d lines",
        len(result.removed_oids),
        len(result.splits),
    )
    return len(result.removed_oids)


if __name__ == "__main__":
    import arcpy
    from env_setup import environment_setup
    from file_manager.n100.file_manager_roads import Road_N100

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    environment_setup.main()

    src = r"C:\temp\291026\road.gdb\ramps___generalized_ramps___n100_road"
    test_lines = (
        f"{src}_dangle_test"  # scratch copy, the permanent file stays untouched
    )
    test_removed = f"{src}_dangle_test_removed"

    arcpy.management.CopyFeatures(src, test_lines)
    removed = remove_new_dangles(
        lines_fc=test_lines,
        ramp_reference_fc=r"C:\temp\291026\road.gdb\data_preparation___road_single_part_2___n100_road",
        removed_fc=test_removed,
        dangle_iterations_prefix=f"{src}_dangle_test",
    )
    print(f"Removed {removed} lines")
