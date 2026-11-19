# Libraries

import json
import time

import arcpy

from custom_tools.general_tools.partition_iterator import PartitionIterator
from partition_validation.feature_checker_factory import FeatureCheckerFactory

##########################
# Program
##########################


def analyse_partition_edges(
    partition_iterator: PartitionIterator,
    input_fc: str,
    output_fc: str,
    partition_areas: str,
    partition_lines: str,
    partition_buffer: str,
    buffer_distance: int = 500,
) -> None:
    fetch_partition_borders(partition_iterator, partition_areas)
    buffer_partition_lines(
        partition_areas, partition_lines, partition_buffer, buffer_distance
    )
    results = analyse_partition_buffer(partition_buffer, input_fc, output_fc)
    write_partition_analysis_to_file(results)


##########################
# Functionality
##########################


def fetch_partition_borders(
    partition_iterator: PartitionIterator, output_file: str
) -> None:
    if arcpy.Exists(partition_iterator.partition_features_all):
        arcpy.management.CopyFeatures(
            in_features=partition_iterator.partition_features_all,
            out_feature_class=output_file,
        )
        partition_count = int(arcpy.management.GetCount(output_file)[0])
        print(f"Exported {partition_count} partition borders to {output_file}")


def buffer_partition_lines(
    partition_lines: str,
    output_line: str,
    output_buffer: str,
    buffer_distance: int,
) -> None:
    _create_partition_lines(partition_lines, output_line)

    if arcpy.Exists(output_buffer):
        arcpy.management.Delete(output_buffer)

    arcpy.analysis.Buffer(
        in_features=output_line,
        out_feature_class=output_buffer,
        buffer_distance_or_field=buffer_distance,
        line_end_type="FLAT",
        dissolve_option="ALL",
    )


def analyse_partition_buffer(
    partition_buffer: str, input_fc: str, output_fc: str
) -> dict:
    tmp_lyr = "temp_layer"

    results = {"input": dict(), "output": dict()}

    for key, fc in zip(["input", "output"], [input_fc, output_fc]):
        print(f"Processing {key}")
        _delete_layer(tmp_lyr)

        arcpy.management.MakeFeatureLayer(in_features=fc, out_layer=tmp_lyr)
        arcpy.management.SelectLayerByLocation(
            in_layer=tmp_lyr,
            overlap_type="INTERSECT",
            select_features=partition_buffer,
            selection_type="NEW_SELECTION",
        )

        # Use factory to create appropriate checker based on feature type
        checker = FeatureCheckerFactory.create(
            feature_layer=tmp_lyr,
            buffer_fc=partition_buffer,
        )
        results[key] = checker.analyze()

    _delete_layer(tmp_lyr)

    results["difference"] = _estimate_difference(results)

    print("Partition analysis completed")

    return results


def write_partition_analysis_to_file(results: dict) -> None:
    """Writes the partition analysis results to a json file."""
    output_file = f"partition_analysis_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Partition analysis results written to {output_file}")


##########################
# Helpers
##########################


def _create_partition_lines(partition_layer: str, output_file: str) -> None:
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


def _estimate_difference(tmp_res: dict) -> dict:
    difference = {}

    for key in tmp_res["input"].keys():
        difference[key] = tmp_res["output"].get(key, 0) - tmp_res["input"].get(key, 0)

    return difference


def _delete_layer(layer: str) -> None:
    if arcpy.Exists(layer):
        arcpy.management.Delete(layer)
