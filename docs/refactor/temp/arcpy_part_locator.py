"""ArcPy `PartLocator`s and the adapter's two geometry guards for a dissolve. STAGING.

What:
    The engine-specific half of `dissolve_parents`. Two locators answer "which output
    part of a key does each input touch?" with `(output_index, input_index)` pairs:

    - `ArcpyPartLocator` — one representative point per input part (label point for a
      polygon, half-length point for a line, the point itself otherwise), one
      `SpatialJoin` of those points against the dissolve output within the XY
      tolerance. With `point_source="feature_to_point"` the points come from
      `FeatureToPoint(INSIDE)` over the whole input instead of a Python loop; that is one
      point per *feature*, so a multipart input gets one point, not one per part.
    - `ArcpySegmentLocator` — lines only. One `SpatialJoin` of the input lines against
      the output with `SHARE_A_LINE_SEGMENT_WITH`, so an input that the dissolve split
      at junctions is paired with every part it became, which a single point cannot do.

    Both keep only hits whose output part belongs to the same request as the input,
    which is the key filter; `dissolve_parents` rejects any pair that slips through.
    Both record `last_timings` per stage so the gate can report the split.

    Two guards belong to the adapter's dissolve method rather than to a locator:
    `find_empty_geometries` before the tool runs (an empty shape in the input emptied a
    whole PairwiseDissolve output silently on Pro 3.7.2), and `degenerate_inputs` after
    it, to classify unmatched inputs for `require_matched`.

How:
    The joins run over the whole input or the whole point set and are filtered in
    Python afterwards, because a where-clause over 10^5 ObjectIDs is slower than the
    join it would save. Reads that must be limited to requested inputs go by ObjectID in
    chunks of `OID_CHUNK`.

Why:
    A per-key Python loop over geometries is O(inputs x parts) and unbounded on a key
    such as a whole road category; a single spatial join is what the engine is good at,
    and its cost is measured by the gate rather than assumed.

Depends on `arcpy`; runs on Windows Pro or in the image, never in CI. Reads its feature
classes and writes only to the scratch workspace, which it cleans up.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable, Iterator, Sequence
from typing import Literal

import arcpy

from dissolve_parents import LocateRequest, ParentPair

INPUT_INDEX_FIELD = "AG_IN_IDX"
REQUEST_FIELD = "AG_REQ"
OID_CHUNK = 900
"""ObjectIDs per IN (...) clause; file geodatabases accept far more, this stays readable."""

PointSource = Literal["per_part", "feature_to_point"]


class EmptyGeometryError(ValueError):
    """An input row has a null or empty shape; the tool must not be called on it."""


def _scratch_name(workspace: str, stem: str) -> str:
    return f"{workspace}\\{stem}_{uuid.uuid4().hex[:8]}"


def _delete(*paths: str) -> None:
    for path in paths:
        if arcpy.Exists(path):
            arcpy.management.Delete(path)


def _request_maps(
    requests: Sequence[LocateRequest],
) -> tuple[dict[int, int], dict[int, int]]:
    request_of_input: dict[int, int] = {}
    request_of_output: dict[int, int] = {}
    for ordinal, request in enumerate(requests):
        for input_index in request.input_indices:
            request_of_input[input_index] = ordinal
        for output_index in request.output_indices:
            request_of_output[output_index] = ordinal
    return request_of_input, request_of_output


def _search_radius(
    spatial_reference: arcpy.SpatialReference, tolerance_m: float | None
) -> str:
    if tolerance_m is not None:
        return f"{tolerance_m} Meters"
    unit = spatial_reference.linearUnitName or "Meters"
    if unit.lower().startswith("meter"):
        unit = "Meters"
    return f"{spatial_reference.XYTolerance} {unit}"


def _read_by_oid(
    path: str, indices: Sequence[int], fields: Sequence[str]
) -> Iterator[tuple]:
    oid_field = arcpy.Describe(path).OIDFieldName
    for start in range(0, len(indices), OID_CHUNK):
        chunk = indices[start : start + OID_CHUNK]
        where = f"{oid_field} IN ({', '.join(str(i) for i in chunk)})"
        with arcpy.da.SearchCursor(path, list(fields), where_clause=where) as cursor:
            yield from cursor


def _filtered_pairs(
    joined_path: str,
    input_field: str,
    request_of_input: dict[int, int],
    request_of_output: dict[int, int],
) -> list[ParentPair]:
    pairs: set[ParentPair] = set()
    with arcpy.da.SearchCursor(joined_path, [input_field, "JOIN_FID"]) as cursor:
        for input_index, output_index in cursor:
            ordinal = request_of_input.get(input_index)
            if ordinal is not None and request_of_output.get(output_index) == ordinal:
                pairs.add(
                    ParentPair(output_index=output_index, input_index=input_index)
                )
    return sorted(pairs)


class ArcpyPartLocator:
    def __init__(
        self,
        *,
        input_path: str,
        output_path: str,
        tolerance_m: float | None = None,
        scratch_workspace: str = "memory",
        point_source: PointSource = "per_part",
    ) -> None:
        """Bind the locator to one dissolve's input and output feature classes.

        What: remembers the two paths, the tolerance and where the points come from.
        How: a tolerance of None means the output's own XY tolerance, read at call time.
        Why: the precondition is stated in the output's tolerance, not in metres.
        """
        self._input_path = input_path
        self._output_path = output_path
        self._tolerance_m = tolerance_m
        self._scratch_workspace = scratch_workspace
        self._point_source: PointSource = point_source
        self.last_timings: dict[str, float] = {}

    def locate(self, *, requests: Sequence[LocateRequest]) -> list[ParentPair]:
        self.last_timings = {}
        request_of_input, request_of_output = _request_maps(requests)
        if not request_of_input:
            return []
        spatial_reference = arcpy.Describe(self._output_path).spatialReference
        joined_path = _scratch_name(self._scratch_workspace, "ag_part_hits")
        points_path = ""
        try:
            started = time.perf_counter()
            if self._point_source == "feature_to_point":
                points_path, input_field = self._feature_to_point()
                self.last_timings["representative points (FeatureToPoint) s"] = (
                    time.perf_counter() - started
                )
            else:
                points = list(self._representative_points(request_of_input))
                self.last_timings["representative points (Python) s"] = (
                    time.perf_counter() - started
                )
                started = time.perf_counter()
                points_path = self._write_points(points, spatial_reference)
                input_field = INPUT_INDEX_FIELD
                self.last_timings["write points s"] = time.perf_counter() - started

            started = time.perf_counter()
            arcpy.analysis.SpatialJoin(
                target_features=points_path,
                join_features=self._output_path,
                out_feature_class=joined_path,
                join_operation="JOIN_ONE_TO_MANY",
                join_type="KEEP_COMMON",
                match_option="INTERSECT",
                search_radius=_search_radius(spatial_reference, self._tolerance_m),
            )
            self.last_timings["spatial join s"] = time.perf_counter() - started

            started = time.perf_counter()
            pairs = _filtered_pairs(
                joined_path, input_field, request_of_input, request_of_output
            )
            self.last_timings["read and filter s"] = time.perf_counter() - started
            return pairs
        finally:
            _delete(points_path, joined_path)

    def _feature_to_point(self) -> tuple[str, str]:
        """One point per input feature, inside it; the input OID rides in ORIG_FID."""
        path = _scratch_name(self._scratch_workspace, "ag_inside_points")
        arcpy.management.FeatureToPoint(self._input_path, path, "INSIDE")
        return path, "ORIG_FID"

    def _representative_points(
        self, request_of_input: dict[int, int]
    ) -> Iterator[tuple[float, float, int, int]]:
        rows = _read_by_oid(
            self._input_path, sorted(request_of_input), ["OID@", "SHAPE@"]
        )
        for input_index, geometry in rows:
            for x, y in _part_points(geometry=geometry):
                yield x, y, input_index, request_of_input[input_index]

    def _write_points(
        self,
        points: Iterable[tuple[float, float, int, int]],
        spatial_reference: arcpy.SpatialReference,
    ) -> str:
        path = _scratch_name(self._scratch_workspace, "ag_rep_points")
        workspace, _, name = path.rpartition("\\")
        arcpy.management.CreateFeatureclass(
            workspace, name, "POINT", spatial_reference=spatial_reference
        )
        arcpy.management.AddField(path, INPUT_INDEX_FIELD, "LONG")
        arcpy.management.AddField(path, REQUEST_FIELD, "LONG")
        fields = ["SHAPE@XY", INPUT_INDEX_FIELD, REQUEST_FIELD]
        with arcpy.da.InsertCursor(path, fields) as cursor:
            for x, y, input_index, ordinal in points:
                cursor.insertRow([(x, y), input_index, ordinal])
        return path


class ArcpySegmentLocator:
    def __init__(
        self, *, input_path: str, output_path: str, scratch_workspace: str = "memory"
    ) -> None:
        """Bind the line locator to one dissolve's input and output feature classes.

        What: pairs an input line with every output part that shares a segment with it.
        How: one `SpatialJoin` of the whole input against the output, filtered by request.
        Why: a dissolve splits lines at junctions, so one input can become many parts; a
        point finds one of them, a shared segment finds all of them.
        """
        self._input_path = input_path
        self._output_path = output_path
        self._scratch_workspace = scratch_workspace
        self.last_timings: dict[str, float] = {}

    def locate(self, *, requests: Sequence[LocateRequest]) -> list[ParentPair]:
        self.last_timings = {}
        request_of_input, request_of_output = _request_maps(requests)
        if not request_of_input:
            return []
        joined_path = _scratch_name(self._scratch_workspace, "ag_segment_hits")
        try:
            started = time.perf_counter()
            arcpy.analysis.SpatialJoin(
                target_features=self._input_path,
                join_features=self._output_path,
                out_feature_class=joined_path,
                join_operation="JOIN_ONE_TO_MANY",
                join_type="KEEP_COMMON",
                match_option="SHARE_A_LINE_SEGMENT_WITH",
            )
            self.last_timings["spatial join s"] = time.perf_counter() - started
            started = time.perf_counter()
            pairs = _filtered_pairs(
                joined_path, "TARGET_FID", request_of_input, request_of_output
            )
            self.last_timings["read and filter s"] = time.perf_counter() - started
            return pairs
        finally:
            _delete(joined_path)


def _part_points(*, geometry: arcpy.Geometry | None) -> list[tuple[float, float]]:
    """One point per part: label point, half-length point, or the point itself."""
    if geometry is None:
        return []
    kind = geometry.type
    spatial_reference = geometry.spatialReference
    if kind == "point":
        point = geometry.firstPoint
        return [(point.X, point.Y)]
    points: list[tuple[float, float]] = []
    for index in range(geometry.partCount):
        part = geometry.getPart(index)
        # A multipart can carry an empty part; every geometry call on it raises
        # "The operation was attempted on an empty geometry" (seen on real roads).
        if part is None or (kind != "multipoint" and part.count == 0):
            continue
        try:
            if kind == "polygon":
                point = arcpy.Polygon(part, spatial_reference).labelPoint
            elif kind == "polyline":
                point = (
                    arcpy.Polyline(part, spatial_reference)
                    .positionAlongLine(0.5, True)
                    .firstPoint
                )
            else:
                point = part
        except RuntimeError:
            # A degenerate part (zero length, all points identical): use its first point.
            point = part[0] if kind != "multipoint" else part
        points.append((point.X, point.Y))
    return points


def _measure_field(path: str) -> str | None:
    """The cheap per-row size token for this shape type, or None for points."""
    shape = arcpy.Describe(path).shapeType
    if shape == "Polyline":
        return "SHAPE@LENGTH"
    if shape == "Polygon":
        return "SHAPE@AREA"
    return None


def find_empty_geometries(path: str) -> list[int]:
    """ObjectIDs of rows whose shape is null or empty. Run before the tool.

    What: one pass over the feature class reading only a size token, never the
    geometry object, so it is cheap at 10^6 rows.
    How: length for lines, area for polygons, the point itself for points; a null
    token is an empty shape.
    Why: PairwiseDissolve on Pro 3.7.2 emitted no output rows at all, with no error,
    when two empty polylines sat in a five-row input. Raising here names the rows.
    """
    token = _measure_field(path) or "SHAPE@"
    empty: list[int] = []
    with arcpy.da.SearchCursor(path, ["OID@", token]) as cursor:
        for oid, value in cursor:
            if value is None:
                empty.append(oid)
    return empty


def assert_no_empty_geometries(path: str) -> None:
    empty = find_empty_geometries(path)
    if empty:
        raise EmptyGeometryError(
            f"{len(empty)} row(s) with a null or empty shape in {path}; first: "
            f"{empty[:10]}. The dissolve is not called on them."
        )


def degenerate_inputs(
    path: str, indices: Sequence[int], tolerance: float | None = None
) -> list[int]:
    """Which of these inputs are degenerate: empty, or sized at or below the tolerance.

    What: the classification `require_matched` needs for unmatched inputs.
    How: reads the size token of the named rows by ObjectID; a null token is empty,
    a value at or below the XY tolerance (the feature class's own unless given) is
    degenerate. Points are never degenerate.
    Why: only the adapter can read geometry; the resolver reports unmatched inputs and
    this decides which of them a dissolve could legitimately have discarded.
    """
    if not indices:
        return []
    token = _measure_field(path)
    if token is None:
        return []
    if tolerance is None:
        tolerance = arcpy.Describe(path).spatialReference.XYTolerance
    degenerate: list[int] = []
    for oid, value in _read_by_oid(path, sorted(indices), ["OID@", token]):
        if value is None or value <= tolerance:
            degenerate.append(oid)
    return degenerate
