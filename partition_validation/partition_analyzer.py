# Libraries

import inspect
import json
import time
from typing import Any

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
    partition_areas_dissolved: str,
    partition_lines: str,
    partition_buffer: str,
    buffer_distance: int = 500,
    id_field: str = "GLOBAL_ID",
) -> None:
    """
    Receives the input and output files (feature classes) to a partition iterator and calculates
    statistical differences between the two datasets to detect potential issues during the process.
    The differences is written to a json file created dynamically.

    Args:
        partition_iterator (PartitionIterator): The partition iterator object containing partition features
        input_fc (str): Path to the input feature class containing the original data
        output_fc (str): Path to the output feature class containing the processed data
        partition_areas (str): Path where the partition areas should be stored
        partition_areas_dissolved (str): Path where the dissolved partition areas should be stored
        partition_lines (str): Path where the partition lines should be stored
        partition_buffer (str): Path where the partition buffer should be stored
        buffer_distance (int, optional): Distance for buffering partition lines (default: 500)
        id_field (str, optional): The name of the ID field to use for analysis (default: "GLOBAL_ID")
    """
    fetch_partition_areas(partition_iterator, partition_areas)
    preprocess_partition_lines(
        partition_areas,
        partition_areas_dissolved,
        partition_lines,
        partition_buffer,
        buffer_distance,
    )
    results = analyse_partition_differences(
        partition_areas_dissolved, partition_buffer, input_fc, output_fc, id_field
    )
    results.update(
        {
            "caller": inspect.stack()[1].function,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "buffer_distance": buffer_distance,
        }
    )
    write_partition_analysis_to_file(results)


##########################
# Functionality
##########################


def fetch_partition_areas(
    partition_iterator: PartitionIterator, output_file: str
) -> None:
    """Copies the partition features from the partition iterator to the specified feature class."""
    if arcpy.Exists(partition_iterator.partition_features_all):
        arcpy.management.CopyFeatures(
            in_features=partition_iterator.partition_features_all,
            out_feature_class=output_file,
        )
        partition_count = int(arcpy.management.GetCount(output_file)[0])
        print(f"Exported {partition_count} partition areas to {output_file}")


def preprocess_partition_lines(
    partition_areas: str,
    partition_areas_dissolved: str,
    output_line: str,
    output_buffer: str,
    buffer_distance: int,
) -> None:
    """Creates polylines of the partition features, selects only the relevant ones, and creates one dissolved buffer around them."""
    _create_partition_lines(partition_areas, output_line)

    arcpy.management.Dissolve(
        in_features=partition_areas,
        out_feature_class=partition_areas_dissolved,
        multi_part="SINGLE_PART",
    )

    if arcpy.Exists(output_buffer):
        arcpy.management.Delete(output_buffer)

    arcpy.analysis.Buffer(
        in_features=output_line,
        out_feature_class=output_buffer,
        buffer_distance_or_field=buffer_distance,
        line_end_type="FLAT",
        dissolve_option="ALL",
    )


def analyse_partition_differences(
    partition_areas: str,
    partition_buffer: str,
    input_fc: str,
    output_fc: str,
    id_field: str,
) -> dict[str, Any]:
    """
    Analyzes the partition buffer against the input and output feature classes and returns the results as a dictionary.

    Args:
        partition_areas (str): The partition areas feature class
        partition_buffer (str): The partition buffer feature class
        input_fc (str): The input feature class to analyze against the buffer
        output_fc (str): The output feature class to analyze against the buffer
        id_field (str): The field used to identify features in the input and output feature classes

    Returns:
        dict[str, dict[str, int | float]]: A dictionary containing the analysis results.
    """
    tmp_lyr = "temp_layer"

    results = {"input": dict(), "output": dict()}

    for key, fc in zip(["input", "output"], [input_fc, output_fc]):
        print(f"Processing {key}")

        layer_stats = {}

        for name, area in [("total", partition_areas), ("buffer", partition_buffer)]:
            _delete_layer(tmp_lyr)

            arcpy.management.MakeFeatureLayer(in_features=fc, out_layer=tmp_lyr)
            arcpy.management.SelectLayerByLocation(
                in_layer=tmp_lyr,
                overlap_type="INTERSECT",
                select_features=area,
                selection_type="NEW_SELECTION",
            )

            # Use factory to create appropriate checker based on feature type
            checker = FeatureCheckerFactory.create(
                feature_layer=tmp_lyr,
                fc=area,
                id_field=id_field,
            )
            layer_stats[name] = checker.analyze()

        clean_layer_stats = {}
        for k1, v1 in layer_stats.items():
            for k2, v2 in v1.items():
                clean_layer_stats[f"{k2}_{k1}"] = v2

        results[key] = clean_layer_stats

    _delete_layer(tmp_lyr)

    results["difference"] = _estimate_difference(results)

    print("Partition analysis completed")

    return results


def write_partition_analysis_to_file(results: dict) -> None:
    """Writes the partition analysis results to a json file."""
    output_file = f"partition_analysis_{results['caller']}_{results['timestamp'].replace(' ', '_').replace(':', '_')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"Partition analysis results written to {output_file}")


##########################
# Helpers
##########################


def _create_partition_lines(partition_layer: str, output_file: str) -> None:
    """
    Creates partition lines from the given partition layer, keeps only those having partition features
    on both sides of the partition border, and stores them in the output file.
    """
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
        try:
            difference[key] = tmp_res["output"].get(key, 0) - tmp_res["input"].get(
                key, 0
            )
        except:
            difference[key] = None

    return difference


def _delete_layer(layer: str) -> None:
    if arcpy.Exists(layer):
        arcpy.management.Delete(layer)
