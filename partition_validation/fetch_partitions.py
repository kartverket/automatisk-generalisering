# Libraries

from typing import defaultdict

import arcpy

from custom_tools.general_tools.partition_iterator import PartitionIterator

##########################
# Functionality
##########################


def FetchPartitionBorders(
    partition_iterator: PartitionIterator, output_file: str
) -> None:
    if arcpy.Exists(partition_iterator.partition_features_all):
        arcpy.management.CopyFeatures(
            in_features=partition_iterator.partition_features_all,
            out_feature_class=output_file,
        )
        partition_count = int(arcpy.management.GetCount(output_file)[0])
        print(
            f"[ramp_partition] Exported {partition_count} partition borders to {output_file}"
        )


def BufferPartitionLines(
    partition_lines: str,
    output_line: str,
    output_buffer: str,
    buffer_distance: int = 500,
) -> None:
    CreatePartitionLines(partition_lines, output_line)

    if arcpy.Exists(output_buffer):
        arcpy.management.Delete(output_buffer)

    arcpy.analysis.Buffer(
        in_features=output_line,
        out_feature_class=output_buffer,
        buffer_distance_or_field=buffer_distance,
        line_end_type="FLAT",
        dissolve_option="ALL",  # Old: Drop it
    )


def AnalysePartitionBuffer(
    partition_buffer: str, input_fc: str, output_fc: str
) -> None:
    tmp_lyr = "temp_layer"

    results = {"input": dict(), "output": dict()}

    for key, fc in zip(["input", "output"], [input_fc, output_fc]):
        _delete_layer(tmp_lyr)

        arcpy.management.MakeFeatureLayer(in_features=fc, out_layer=tmp_lyr)
        arcpy.management.SelectLayerByLocation(
            in_layer=tmp_lyr,
            overlap_type="INTERSECT",
            select_features=partition_buffer,
            selection_type="NEW_SELECTION",
        )

        end_points = GetRelevantEndPoints(tmp_lyr, partition_buffer)

        results[key] = {"dangle_count": len(end_points)}

    print("Partition result:")
    for key, value in results.items():
        print(f"{key}:\n{value}")

    _delete_layer(tmp_lyr)


##########################
# Helpers
##########################


def CreatePartitionLines(partition_layer: str, output_file: str) -> None:
    if arcpy.Exists(output_file):
        arcpy.management.Delete(output_file)

    arcpy.management.PolygonToLine(
        in_features=partition_layer,
        out_feature_class=output_file,
        neighbor_option="IDENTIFY_NEIGHBORS",
    )

    tmp_lyr = "line_layer"

    arcpy.management.MakeFeatureLayer(in_features=output_file, out_layer=tmp_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=tmp_lyr,
        selection_type="NEW_SELECTION",
        where_clause="LEFT_FID = -1 OR RIGHT_FID = -1",
    )
    arcpy.management.DeleteFeatures(tmp_lyr)

    _delete_layer(tmp_lyr)


def GetRelevantEndPoints(line_layer: str, buffer_fc: str) -> defaultdict:
    end_points = defaultdict(list)

    buffer_geom = None
    with arcpy.da.SearchCursor(buffer_fc, ["SHAPE@"]) as buffer_cursor:
        buffer_geom = next(buffer_cursor)[0]

    if buffer_geom is None:
        raise ValueError("Buffer geometry could not be retrieved.")
    with arcpy.da.SearchCursor(line_layer, ["OID@", "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            start_point = geom.firstPoint
            end_point = geom.lastPoint

            start_geom = arcpy.PointGeometry(start_point, geom.spatialReference)
            end_geom = arcpy.PointGeometry(end_point, geom.spatialReference)

            if buffer_geom.contains(start_geom):
                end_points[(start_point.X, start_point.Y)].append(oid)
            if buffer_geom.contains(end_geom):
                end_points[(end_point.X, end_point.Y)].append(oid)

    return end_points


def _delete_layer(layer: str) -> None:
    if arcpy.Exists(layer):
        arcpy.management.Delete(layer)


##########################

INPUT = r""
OUTPUT = r""
PARTITIONS = r""
PARTITION_LINES = r""
PARTITION_BUFFER = r""


def test():
    BufferPartitionLines(
        partition_lines=PARTITIONS,
        output_line=PARTITION_LINES,
        output_buffer=PARTITION_BUFFER,
        buffer_distance=1000,
    )
    AnalysePartitionBuffer(
        partition_buffer=PARTITION_BUFFER, input_fc=INPUT, output_fc=OUTPUT
    )


if __name__ == "__main__":
    test()
