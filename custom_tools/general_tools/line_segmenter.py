import math
import os

import arcpy


def segment_line(
    input_fc: str,
    output_fc: str,
    segment_interval: float,
    even_segments: bool = False,
    tail_tolerance: float = 0.0,
) -> None:
    """Split each polyline in input_fc so no segment exceeds segment_interval.

    Lines with length <= segment_interval pass through unchanged. Longer
    lines are cut along their natural direction, and the source row's
    non-functional fields (everything except OID, Shape, and required
    auto-managed fields) are copied onto every emitted segment.

    Singlepart polyline input only. Multipart input is not supported
    because segmentAlongLine measures along cumulative length and the
    resulting cuts may straddle parts in unexpected ways.

    Args:
        input_fc: Singlepart polyline feature class.
        output_fc: Path of the feature class to create. Overwritten if it
            already exists.
        segment_interval: Maximum segment length in the input's linear
            units. Must be > 0.
        even_segments: When True, divide each long line into
            ceil(L / segment_interval) equal-length pieces. When False,
            cut at fixed segment_interval and emit the remainder as a
            final segment (subject to tail_tolerance).
        tail_tolerance: Fixed-mode only. When the remainder of a fixed
            split is <= tail_tolerance, it is absorbed into the preceding
            segment instead of emitted on its own. Default 0.0 disables
            absorption. Sensible values are well below segment_interval.
    """
    if segment_interval <= 0:
        raise ValueError("segment_interval must be > 0")
    if tail_tolerance < 0:
        raise ValueError("tail_tolerance must be >= 0")

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(output_fc),
        out_name=os.path.basename(output_fc),
        geometry_type="POLYLINE",
        template=input_fc,
        spatial_reference=input_fc,
    )

    carried_fields = [
        f.name for f in arcpy.ListFields(input_fc) if not f.required
    ]
    cursor_fields = ["SHAPE@"] + carried_fields

    with arcpy.da.SearchCursor(input_fc, cursor_fields) as src, \
            arcpy.da.InsertCursor(output_fc, cursor_fields) as dst:
        for row in src:
            geom = row[0]
            if geom is None:
                continue
            attrs = list(row)
            for start, end in _segment_positions(
                geom.length, segment_interval, even_segments, tail_tolerance
            ):
                if start == 0.0 and end >= geom.length:
                    attrs[0] = geom
                else:
                    attrs[0] = geom.segmentAlongLine(start, end, False)
                dst.insertRow(attrs)


def _segment_positions(
    length: float,
    interval: float,
    even: bool,
    tail_tolerance: float,
):
    """Yield (start, end) cut positions along a line of the given length."""
    if length <= interval:
        yield (0.0, length)
        return
    if even:
        n = math.ceil(length / interval)
        step = length / n
        for i in range(n):
            end = length if i == n - 1 else (i + 1) * step
            yield (i * step, end)
        return
    n_full = int(length // interval)
    remainder = length - n_full * interval
    if 0 < remainder <= tail_tolerance:
        for i in range(n_full - 1):
            yield (i * interval, (i + 1) * interval)
        yield ((n_full - 1) * interval, length)
    else:
        for i in range(n_full):
            yield (i * interval, (i + 1) * interval)
        if remainder > 0:
            yield (n_full * interval, length)
