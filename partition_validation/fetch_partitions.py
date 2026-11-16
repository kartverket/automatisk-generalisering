# Libraries

import arcpy

from custom_tools.general_tools.partition_iterator import PartitionIterator

##########################
# Functionality
##########################


def FetchPartitionBorders(partition_iterator: PartitionIterator, output_file: str):
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
):
    CreatePartitionLines(partition_lines, output_line)

    if arcpy.Exists(output_buffer):
        arcpy.management.Delete(output_buffer)

    arcpy.analysis.Buffer(
        in_features=output_line,
        out_feature_class=output_buffer,
        buffer_distance_or_field=buffer_distance,
        line_end_type="FLAT",
    )


def AnalysePartitionBuffer(partition_buffer: str, input_fc: str, output_fc: str):
    tmp_lyr = "temp_layer"

    # results = {"input": [], "output": []}

    for fc in [input_fc, output_fc]:
        arcpy.management.MakeFeatureLayer(in_features=fc, out_layer=tmp_lyr)
        arcpy.management.SelectLayerByLocation(
            in_layer=tmp_lyr,
            overlap_type="INTERSECT",
            select_features=partition_buffer,
            selection_type="NEW_SELECTION",
        )


##########################
# Helpers
##########################


def CreatePartitionLines(partition_layer: str, output_file: str):
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

    if arcpy.Exists(tmp_lyr):
        arcpy.management.Delete(tmp_lyr)


def CountEndPoints(line_layer: str, buffer_layer: str):
    return


def PointWithinBuffer(point: arcpy.PointGeometry, buffer_fc: str):
    return arcpy.management.SelectLayerByLocation(
        in_layer=buffer_fc,
        overlap_type="INTERSECT",
        select_features=point,
        selection_type="NEW_SELECTION",
    )


##########################

INPUT = r"..."
OUTPUT = r"..."
PARTITIONS = r"..."
PARTITION_LINES = r"..."
PARTITION_BUFFER = r"..."


def test():
    BufferPartitionLines(
        PARTITIONS, PARTITION_LINES, PARTITION_BUFFER, buffer_distance=1000
    )


if __name__ == "__main__":
    test()
