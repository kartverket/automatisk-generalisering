"""
In new road input from nvdb ramps dont always extend all the way to main roads,
This causes the ramps generalisation to leave behind dangles.
This function handles those dangles.
Make it in such a way that we can reuse the logic to handle other similar cases of dangles.
Sitations where the dangle is one of the roads part of the crossroad then we convert the crossroad to a T cross in the same medium.
"""

import heapq
import logging
import math
import os
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence, Set
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
_MAX_FALSE_LOOP_PERIMETER_M = 500
_MEDIUM_FIELD = "medium"
_RAMP_ID_FIELD = "ramp_id"
_RAMP_WHERE_CLAUSE = "typeveg = 'rampe'"
_REMOVABLE_WHERE_CLAUSE = None


def _cell(point: Point, size: float) -> Cell:
    return math.floor(point[0] / size), math.floor(point[1] / size)


def _project(point: Point, segment: Segment) -> tuple[float, Point]:
    """Return the fraction along `segment` and the point on it closest to `point`."""
    x, y = point
    x1, y1, x2, y2 = segment
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return 0.0, (x1, y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length_sq))
    return t, (x1 + t * dx, y1 + t * dy)


def _point_segment_distance(point: Point, segment: Segment) -> float:
    return math.dist(point, _project(point, segment)[1])


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


def _drop_empty(segments: list[Segment]) -> list[Segment]:
    return [s for s in segments if (s[0], s[1]) != (s[2], s[3])]


def _segment_length(segment: Segment) -> float:
    return math.dist((segment[0], segment[1]), (segment[2], segment[3]))


def _length(segments: Sequence[Segment]) -> float:
    return sum(_segment_length(segment) for segment in segments)


def _distance_along(segments: Sequence[Segment], point: Point) -> float:
    """Length along `segments` to where `point` projects onto the closest segment."""
    best_gap = math.inf
    best_along = 0.0
    walked = 0.0
    for segment in segments:
        fraction, projected = _project(point, segment)
        gap = math.dist(point, projected)
        segment_length = _segment_length(segment)
        if gap < best_gap:
            best_gap, best_along = gap, walked + fraction * segment_length
        walked += segment_length
    return best_along


@dataclass
class _Line:
    segments: list[Segment]
    medium: str | None = None
    ramp_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class _Cut:
    """Where to cut a dangling line; `shared_ramp_ids` is empty for a plain junction."""

    other_oid: int
    segment_index: int
    point: Point
    shared_ramp_ids: frozenset[str]
    oriented_segments: tuple[Segment, ...]


@dataclass(frozen=True)
class _Split:
    oid: int
    point: Point
    dangle_point: Point


@dataclass
class _WaveResult:
    removed_oids: list[int]
    splits: list[_Split]
    ramp_changed: set[int]
    waves: list[list[int]]


def _is_ramp_crossing(line: _Line, other: _Line) -> bool:
    """True if `other` is a road of another medium sharing a ramp id with `line`."""
    return bool(
        line.medium
        and other.medium
        and other.medium != line.medium
        and line.ramp_ids & other.ramp_ids
    )


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
        return next(self._within(point, ignore), None) is not None

    def oids_within(self, point: Point, ignore: Set[int]) -> set[int]:
        return set(self._within(point, ignore))

    def _within(self, point: Point, ignore: Set[int]) -> Iterator[int]:
        for entry in self._cells.get(_cell(point, _INDEX_CELL_SIZE_M), ()):
            oid, segment = entry
            if (
                oid not in ignore
                and entry not in self._dead
                and _point_segment_distance(point, segment) <= self._tolerance
            ):
                yield oid


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

    def connected_end_nodes(
        self, oid: int, segments: list[Segment], end_nodes: list[int]
    ) -> list[int]:
        """End nodes of every other line connected to `segments` or `end_nodes` of `oid`.

        A line is connected if it shares an end node, ends on `segments`, or has
        one of `end_nodes` on its interior.
        """
        ignore = {oid}
        connected: set[int] = set()
        for node in end_nodes:
            connected |= self.node_lines[node]
            connected |= self._segments.oids_within(self.nodes.xy[node], ignore)
        for segment in segments:
            for other_oid, _ in self._segments.candidates(segment):
                if other_oid == oid or other_oid in connected:
                    continue
                if any(
                    _point_segment_distance(self.nodes.xy[node], segment)
                    <= _SNAP_TOLERANCE_M
                    for node in self.line_nodes[other_oid]
                ):
                    connected.add(other_oid)
        connected.discard(oid)
        return sorted({node for other in connected for node in self.line_nodes[other]})

    def remove_line(self, oid: int) -> list[int]:
        """Remove the line and return the end nodes of the lines connected to it."""
        line = self.lines[oid]
        affected = self.connected_end_nodes(
            oid, line.segments, list(self.line_nodes[oid])
        )
        self._segments.kill(oid, line.segments)
        for node in self.line_nodes.pop(oid):
            self.node_lines[node].discard(oid)
        return affected

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

    def _far_node(self, oid: int, node: int) -> int:
        start, end = self.line_nodes[oid]
        return end if start == node else start

    def _shortest_path(
        self,
        starts: Iterable[int],
        start_cost: float,
        blocked: Set[int],
        max_cost: float,
        closing_cost: Callable[[int], float | None],
    ) -> list[int] | None:
        """Lines in order on the shortest path from `starts` to a node that closes a loop within `max_cost`.

        `closing_cost` gives the cost left to close the loop at a node, or None if the
        node does not close it. The walk never continues past a closing node.
        """
        best: dict[int, float] = {}
        heap: list[tuple[float, int]] = []
        for node in starts:
            best[node] = start_cost
            heapq.heappush(heap, (start_cost, node))
        previous: dict[int, tuple[int, int]] = {}
        while heap:
            cost, node = heapq.heappop(heap)
            if cost > max_cost:
                return None
            if cost > best[node]:
                continue
            extra = closing_cost(node)
            if extra is not None:
                if cost + extra <= max_cost:
                    path: list[int] = []
                    while node in previous:
                        node, via = previous[node]
                        path.append(via)
                    return path[::-1]
                continue
            for next_oid in self.node_lines[node]:
                if next_oid in blocked:
                    continue
                far = self._far_node(next_oid, node)
                next_cost = cost + _length(self.lines[next_oid].segments)
                if next_cost < best.get(far, math.inf):
                    best[far] = next_cost
                    previous[far] = (node, next_oid)
                    heapq.heappush(heap, (next_cost, far))
        return None

    def _attachment_nodes(self, loop: Set[int], hub: int) -> set[int]:
        """Nodes other than `hub` where lines outside `loop` touch it."""
        loop_nodes = {node for oid in loop for node in self.line_nodes[oid]}
        attached: set[int] = set()
        for node in loop_nodes - {hub}:
            if self.node_lines[node] - loop or self._segments.has_within(
                self.nodes.xy[node], loop | self.node_lines[node]
            ):
                attached.add(node)
        for oid in loop:
            for segment in self.lines[oid].segments:
                for other_oid, _ in self._segments.candidates(segment):
                    if other_oid in loop:
                        continue
                    for node in self.line_nodes[other_oid]:
                        if (
                            node not in loop_nodes
                            and _point_segment_distance(self.nodes.xy[node], segment)
                            <= _SNAP_TOLERANCE_M
                        ):
                            attached.add(node)
        return attached

    def pendant_loop(self, node: int, max_perimeter: float) -> list[int] | None:
        """Lines in order around the loop through `node`, if it is a small loop hanging off the network.

        `node` must have two line ends and no line through it, the shortest loop
        through it must have a perimeter within `max_perimeter`, and other lines may
        touch the loop at one node at most.
        """
        lines = self.node_lines[node]
        if self._degree(node) != 2 or self._segments.has_within(
            self.nodes.xy[node], lines
        ):
            return None
        if len(lines) == 1:
            (ring,) = lines
            if _length(self.lines[ring].segments) > max_perimeter:
                return None
            cycle = [ring]
        else:
            first, second = sorted(lines)
            second_far = self._far_node(second, node)
            second_length = _length(self.lines[second].segments)
            path = self._shortest_path(
                starts=[self._far_node(first, node)],
                start_cost=_length(self.lines[first].segments),
                blocked=lines,
                max_cost=max_perimeter,
                closing_cost=lambda n: second_length if n == second_far else None,
            )
            if path is None:
                return None
            cycle = [first, *path, second]
        if len(self._attachment_nodes(set(cycle), node)) > 1:
            return None
        return cycle

    def has_ramp_crossing(self, oid: int) -> bool:
        line = self.lines[oid]
        for segment in line.segments:
            for other_oid, other_segment in self._segments.candidates(segment):
                if (
                    other_oid != oid
                    and _is_ramp_crossing(line, self.lines[other_oid])
                    and _segment_intersection(segment, other_segment) is not None
                ):
                    return True
        return False

    def loop_lines_to_remove(self, hub: int, cycle: list[int]) -> list[int]:
        """Lines of the pendant loop `cycle` at `hub` to remove.

        If the loop has ramp crossings, the side holding the first one, from `hub` to
        where the loop meets the network, is kept so that crossing is handled as a
        ramp crossing once `hub` dangles; the other side is removed with its crossings.
        """
        crossing = next(
            (i for i, oid in enumerate(cycle) if self.has_ramp_crossing(oid)), None
        )
        if crossing is None or len(cycle) == 1:
            return cycle
        attachments = self._attachment_nodes(set(cycle), hub)
        nodes = [hub]
        for oid in cycle:
            nodes.append(self._far_node(oid, nodes[-1]))
        # An isolated loop, or one attached on a line interior, is split in the middle.
        split = next(
            (i for i in range(1, len(cycle)) if nodes[i] in attachments),
            len(cycle) // 2,
        )
        return cycle[split:] if crossing < split else cycle[:split]

    def false_loop_oids(
        self,
        oid: int,
        oriented: Sequence[Segment],
        hit_point: Point,
        other_oid: int,
        max_perimeter: float,
    ) -> set[int] | None:
        """Lines of the shortest loop from `other_oid` back onto `oid`, if its perimeter is within `max_perimeter`.

        The perimeter is the length of the loop lines plus the stretch of `oid`
        between the two contact points.
        """
        other_length = _length(self.lines[other_oid].segments)
        start, end = self.line_nodes[other_oid]
        if start == end:
            return {other_oid} if other_length <= max_perimeter else None

        hit_along = _distance_along(oriented, hit_point)

        def closing_cost(node: int) -> float | None:
            xy = self.nodes.xy[node]
            if any(
                _point_segment_distance(xy, segment) <= _SNAP_TOLERANCE_M
                for segment in oriented
            ):
                return abs(_distance_along(oriented, xy) - hit_along)
            return None

        # A crossing hit starts from both ends at full length, which only overstates the loop.
        path = self._shortest_path(
            starts=[
                node
                for node in (start, end)
                if math.dist(self.nodes.xy[node], hit_point) > _SNAP_TOLERANCE_M
            ],
            start_cost=other_length,
            blocked={oid, other_oid},
            max_cost=max_perimeter,
            closing_cost=closing_cost,
        )
        return None if path is None else {*path, other_oid}

    def find_cut(
        self, oid: int, dangle_node: int, max_loop_perimeter: float
    ) -> _Cut | None:
        """First junction or ramp crossing along the line, walking from the dangle.

        A junction is another line's endpoint on the line, or a crossing with a road of
        the same medium. A ramp crossing is a crossing with a road of another medium
        that shares a ramp id; it wins a tie with a junction. A junction on a loop back
        onto the line with perimeter within `max_loop_perimeter` is a false junction and
        is skipped.
        """
        line = self.lines[oid]
        oriented = (
            line.segments
            if self.line_nodes[oid][0] == dangle_node
            else _reverse_segments(line.segments)
        )
        ends = [(oriented[0][0], oriented[0][1]), (oriented[-1][2], oriented[-1][3])]
        no_ramp_ids: frozenset[str] = frozenset()
        false_loops: dict[int, bool] = {}
        for index, segment in enumerate(oriented):
            # (fraction, priority, point, other oid, shared ramp ids)
            hits: list[tuple[float, int, Point, int, frozenset[str]]] = []
            seen_oids: set[int] = set()
            for other_oid, other_segment in self._segments.candidates(segment):
                if other_oid == oid:
                    continue
                other = self.lines[other_oid]
                is_ramp_crossing = _is_ramp_crossing(line, other)
                if is_ramp_crossing or other.medium == line.medium:
                    hit = _segment_intersection(segment, other_segment)
                    if hit is not None:
                        fraction, point = hit
                        if is_ramp_crossing:
                            shared = frozenset(line.ramp_ids & other.ramp_ids)
                            hits.append((fraction, 0, point, other_oid, shared))
                        else:
                            hits.append((fraction, 1, point, other_oid, no_ramp_ids))
                if other_oid in seen_oids:
                    continue
                seen_oids.add(other_oid)
                for node in self.line_nodes[other_oid]:
                    xy = self.nodes.xy[node]
                    fraction, point = _project(xy, segment)
                    if math.dist(xy, point) <= _SNAP_TOLERANCE_M:
                        hits.append((fraction, 1, point, other_oid, no_ramp_ids))
            hits = [
                hit
                for hit in hits
                if all(math.dist(hit[2], end) >= _SNAP_TOLERANCE_M for end in ends)
            ]
            for _, priority, point, other_oid, shared in sorted(
                hits, key=lambda hit: (hit[0], hit[1])
            ):
                if priority == 1:
                    if other_oid not in false_loops:
                        false_loops[other_oid] = (
                            self.false_loop_oids(
                                oid, oriented, point, other_oid, max_loop_perimeter
                            )
                            is not None
                        )
                    if false_loops[other_oid]:
                        continue
                return _Cut(
                    other_oid=other_oid,
                    segment_index=index,
                    point=point,
                    shared_ramp_ids=shared,
                    oriented_segments=tuple(oriented),
                )
        return None

    def split_line(
        self, oid: int, dangle_node: int, cut: _Cut
    ) -> tuple[_Split, list[int]]:
        """Cut off the dangle side at `cut`; at a ramp crossing the kept part takes the crossed road's medium.

        Returns the split and the end nodes of the lines connected to the cut-off side.
        """
        line = self.lines[oid]
        start, end = self.line_nodes[oid]
        px, py = cut.point
        oriented = cut.oriented_segments
        x1, y1, x2, y2 = oriented[cut.segment_index]
        kept = _drop_empty([(px, py, x2, y2), *oriented[cut.segment_index + 1 :]])
        cut_off = _drop_empty([*oriented[: cut.segment_index], (x1, y1, px, py)])
        affected = self.connected_end_nodes(oid, cut_off, [dangle_node])

        self._segments.kill(oid, line.segments)
        line.segments = kept
        for segment in kept:
            self._segments.add(oid, segment)

        far = end if start == dangle_node else start
        cut_node = self.nodes.find_or_add(cut.point)
        self.node_lines[dangle_node].discard(oid)
        self.line_nodes[oid] = (cut_node, far)
        self.node_lines[cut_node].add(oid)

        if cut.shared_ramp_ids:
            other = self.lines[cut.other_oid]
            line.medium = other.medium
            line.ramp_ids -= cut.shared_ramp_ids
            other.ramp_ids -= cut.shared_ramp_ids
        split = _Split(
            oid=oid, point=cut.point, dangle_point=self.nodes.xy[dangle_node]
        )
        return split, affected


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
    graph: _EndpointGraph,
    ramp_index: _SegmentIndex,
    max_iterations: int,
    max_loop_perimeter: float,
) -> _WaveResult:
    """Remove or split dangling lines wave by wave, recording the dangle nodes per wave."""
    result = _WaveResult(removed_oids=[], splits=[], ramp_changed=set(), waves=[])
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
        exposed: dict[int, None] = {}

        def expose(nodes: list[int]) -> None:
            for candidate in nodes:
                if candidate not in exposed and (
                    graph.is_dangle(candidate)
                    or graph.pendant_loop(candidate, max_loop_perimeter) is not None
                ):
                    exposed[candidate] = None

        for node in wave:
            if graph.is_dangle(node):
                (oid,) = graph.node_lines[node]
                acted.append(node)
                cut = graph.find_cut(oid, node, max_loop_perimeter)
                if cut is not None:
                    split, affected = graph.split_line(oid, node, cut)
                    result.splits.append(split)
                    if cut.shared_ramp_ids:
                        result.ramp_changed.add(cut.other_oid)
                else:
                    affected = graph.remove_line(oid)
                    result.removed_oids.append(oid)
                expose(affected)
                continue
            cycle = graph.pendant_loop(node, max_loop_perimeter)
            if cycle is None:
                continue
            acted.append(node)
            for loop_oid in graph.loop_lines_to_remove(node, cycle):
                expose(graph.remove_line(loop_oid))
                result.removed_oids.append(loop_oid)
        result.waves.append(acted)
        logger.info(
            "Dangle removal iteration %d: %d dangles handled", iteration, len(acted)
        )
        wave = list(exposed)
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
    first, last = shape.firstPoint, shape.lastPoint
    start_gap = math.dist(split.dangle_point, (first.X, first.Y))
    end_gap = math.dist(split.dangle_point, (last.X, last.Y))
    return (before, after) if start_gap <= end_gap else (after, before)


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
    splits: dict[int, list[_Split]] = defaultdict(list)
    for split in result.splits:
        splits[split.oid].append(split)
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
                shape = row[1]
                for split in splits[oid]:
                    dangle_piece, shape = _cut_shape(shape, split)
                    removed_rows.append([dangle_piece, *row[2:]])
                row[1] = shape
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
    max_false_loop_perimeter: float = _MAX_FALSE_LOOP_PERIMETER_M,
) -> int:
    """Remove ramp dangles from `lines_fc`, then dangles on the lines connected to each removal.

    Dangles come from an endpoint graph of the `VegSenterlinje` lines: a dangle is an
    endpoint with one line attached that no other line passes through. The starting
    dangles are those on `typeveg = 'rampe'` lines in `ramp_reference_fc`. After a
    line or a cut-off piece is removed, both ends of every line connected to it are
    checked, and any dangle there is handled in the next wave, even one that existed
    before the run. A line is connected if it shares an end node with the removed
    geometry, ends on it, or has the removed geometry end on its interior. Removal
    repeats in waves until no dangle is left.

    A dangling line is not removed whole if, walking from the dangle, it reaches a
    junction (another line's endpoint, or a crossing with a road of the same medium)
    or a ramp crossing (a road of another medium sharing a `ramp_id`). It is cut at
    the first one and the dangle side goes to `removed_fc`. At a ramp crossing the
    kept part takes the crossed road's medium, and the shared ids are removed from
    `ramp_id` on both the kept part and the crossed road. A line can be cut again
    if its kept part later dangles. A junction where a loop of lines leaves and
    rejoins the dangling line (a P shape) is skipped if the loop perimeter is at most
    `max_false_loop_perimeter`. A loop of at most that perimeter left hanging at a
    node after a removal, touched by other lines at one node at most, is removed
    like a dangle. If that loop has ramp crossings, the side with the first one is
    kept and then handled from the dangle, so only that crossing becomes a T cross.

    Args:
        lines_fc: Line feature class edited in place.
        ramp_reference_fc: Lines with `typeveg`; dangles on its ramps are the starting dangles.
        removed_fc: Permanent output; receives a copy of every removed line.
        max_iterations: Safety limit for the number of waves.
        dangle_iterations_prefix: If set, the dangles removed in each wave are
            saved permanently as `<prefix>_ite1`, `<prefix>_ite2`, ...
        max_false_loop_perimeter: Largest loop perimeter in metres treated as a
            false junction; 0 disables the check.

    Returns:
        Total number of removed lines.
    """
    _create_removed_fc(template_fc=lines_fc, removed_fc=removed_fc)

    graph = _build_graph(lines_fc)
    ramp_index = _build_ramp_index(ramp_reference_fc)
    result = _remove_in_waves(
        graph, ramp_index, max_iterations, max_false_loop_perimeter
    )

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
