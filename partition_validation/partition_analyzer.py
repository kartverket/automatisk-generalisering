# Libraries

import inspect
import json
import time
from typing import Any

import arcpy

from custom_tools.general_tools.partition_iterator import PartitionIterator
from partition_validation.feature_checker_factory import FeatureCheckerFactory

# TODO: Skal bli lineage-basert analyse
##########################
# Constants
##########################


GLOBAL_ID = "GLOBAL_ID"  # TODO: Skal bort


##########################
# Program
##########################


def analyze_partition_edges(
    partition_iterator: PartitionIterator,
    input_fc: str,
    output_fc: str,
    partition_areas: str,
    partition_areas_dissolved: str,
    partition_lines: str,
    partition_buffer: str,
    buffer_distance: int = 500,
    id_field: str = GLOBAL_ID,
) -> None:
    """
    Analyze partition edges by comparing input and output feature classes.

    Processes partition geometry and calculates statistical differences between
    input and output datasets to detect potential data quality issues.
    Results are written to a JSON file.

    Args:
        partition_iterator: Partition iterator object containing partition features
        input_fc: Path to input feature class containing original data
        output_fc: Path to output feature class containing processed data
        partition_areas: Output path for partition areas feature class
        partition_areas_dissolved: Output path for dissolved partition areas feature class
        partition_lines: Output path for partition lines feature class
        partition_buffer: Output path for partition buffer feature class
        buffer_distance: Distance for buffering partition lines (default: 500)
        id_field: Name of ID field for feature identification (default: "GLOBAL_ID")
    """
    print(
        f"\nAnalyzing partition edges for:\n\t- Input: {input_fc}\n\t- Output: {output_fc}"
    )

    fetch_partition_areas(partition_iterator, partition_areas)
    preprocess_partition_lines(
        partition_areas,
        partition_areas_dissolved,
        partition_lines,
        partition_buffer,
        buffer_distance,
    )
    results = analyze_partition_differences(
        partition_areas_dissolved, partition_buffer, input_fc, output_fc, id_field
    )
    results.update(
        {
            "caller": inspect.stack()[1].function,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "buffer_distance": buffer_distance,
            "unique_id_field": id_field,
        }
    )
    write_partition_analysis_to_file(results)


##########################
# Functionality
##########################


def fetch_partition_areas(
    partition_iterator: PartitionIterator, output_file: str
) -> None:
    """
    Copy partition features from iterator to feature class.

    Exports partition features from the partition iterator to the specified
    output feature class and prints export statistics.

    Args:
        partition_iterator: Partition iterator containing partition features
        output_file: Output path for the partition areas feature class
    """
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
    """
    Preprocess partition lines by converting polygons to lines and creating buffer.

    Converts polygon boundaries to lines, filters to keep only internal boundaries,
    dissolves the polygons, and creates a buffer zone around the lines.

    Args:
        partition_areas: Input partition areas feature class
        partition_areas_dissolved: Output path for dissolved partition areas
        output_line: Output path for partition lines feature class
        output_buffer: Output path for partition buffer feature class
        buffer_distance: Distance for buffering partition lines
    """
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


def analyze_partition_differences(
    partition_areas: str,
    partition_buffer: str,
    input_fc: str,
    output_fc: str,
    id_field: str,
) -> dict[str, Any]:
    """
    Analyze partition areas and buffers against input and output feature classes.

    Compares input and output feature classes against partition areas and buffers
    to identify features affected by partition boundaries. Returns type-specific
    metrics for each feature class and area type.

    Args:
        partition_areas: Partition areas feature class
        partition_buffer: Partition buffer feature class
        input_fc: Input feature class to analyze
        output_fc: Output feature class to analyze
        id_field: Field name for feature identification

    Returns:
        Dictionary with nested metrics: {"input": {...}, "output": {...}, "difference": {...}}
    """
    tmp_lyr = "temp_layer"

    results: dict[str, Any] = {"input": {}, "output": {}}

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
                area_fc=area,
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


def write_partition_analysis_to_file(results: dict[str, Any]) -> None:
    """
    Write partition analysis results to a JSON file.

    Creates a timestamped JSON file containing analysis results with metadata
    (caller function name, timestamp, buffer distance, ID field).

    Args:
        results: Dictionary containing analysis results and metadata
    """
    output_file = f"partition_analysis_{results['caller']}_{results['timestamp'].replace(' ', '_').replace(':', '_')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nPartition analysis results written to:\n\t- {output_file}\n")


##########################
# Helpers
##########################


def _create_partition_lines(partition_layer: str, output_file: str) -> None:
    """
    Create partition lines from polygon boundaries.

    Converts polygon boundaries to lines and removes those without neighbors
    (i.e., keeps only internal partition boundaries with features on both sides).

    Args:
        partition_layer: Input partition polygon feature class
        output_file: Output path for partition lines feature class
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


def _estimate_difference(tmp_res: dict[str, Any]) -> dict[str, Any]:
    """
    Estimate differences between input and output analysis results.

    Computes metric differences between input and output datasets. For list-type
    metrics (e.g., feature IDs), returns items in output not in input. For numeric
    metrics, returns the difference. Handles errors gracefully by setting difference
    to None for problematic values.

    Args:
        tmp_res: Dictionary with "input" and "output" keys containing analysis results

    Returns:
        Dictionary with computed differences for each metric
    """
    difference: dict[str, Any] = {}
    drop_keys = []

    for key in tmp_res["input"].keys():
        try:
            if isinstance(tmp_res["input"].get(key, None), list):
                difference[key] = [
                    geom_id
                    for geom_id in tmp_res["output"][key]
                    if geom_id not in set(tmp_res["input"][key])
                ]
                drop_keys.append(key)
            elif isinstance(tmp_res["input"].get(key, None), dict):
                continue
            else:
                difference[key] = tmp_res["output"].get(key) - tmp_res["input"].get(key)
        except (KeyError, TypeError, ValueError):
            difference[key] = None

    for key in drop_keys:
        for layer in ["input", "output"]:
            if key in tmp_res[layer]:
                del tmp_res[layer][key]

    return difference


def _delete_layer(layer: str) -> None:
    """
    Delete a temporary feature layer if it exists.

    Args:
        layer: Name of the layer to delete
    """
    if arcpy.Exists(layer):
        arcpy.management.Delete(layer)
