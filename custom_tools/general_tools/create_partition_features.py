import logging
import math
import os
from dataclasses import dataclass

import arcpy

from data_orchestrator.data_names import DataNames as dn
from env_setup import environment_setup
from paths import GIS_FILES_ROOT

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
)

logger = logging.getLogger(__name__)

PARTITION_INDEX_FIELD = "partition_index"
VECTOR_COUNT_FIELD = "vector_count"
HALO_FIELD = "halo_m"

_CELLS = "memory/partition_cells"
_CENTER_POINTS = "memory/partition_center_points"
_CELL_LAYER = "partition_cell_layer"


@dataclass
class _CellStats:
    oid: int
    shape: arcpy.Geometry
    with_centerpoint_within: int
    intersecting: int
    vector_count: int


def create_partition_features(
    counted_feature: str,
    context_features: list[str],
    target_partition_count: int,
    output_gdb: str,
    name_prefix: str,
    halo_m: int = 5000,
) -> None:
    """
    What:
        Creates the fan-out and fan-in partition features for running one pipeline
        partition per Kubernetes Indexed Job pod.

    How:
        Cartographic partitions are made from the counted feature and the context
        features. Each cell gets the number of counted features whose inside point
        lies within it, the number intersecting it, and the number of features of all
        inputs within halo_m of it (vector_count).

        - {name_prefix}_partitions_fan_in: every cell, for clip-only fan-in.
        - {name_prefix}_partitions_fan_out: only cells with at least one counted
          feature, numbered by partition_index from 0, sorted by vector_count
          descending, ties broken by the cell's inside point (Y descending, then X
          ascending).

    Why:
        CreateCartographicPartitions takes a feature count per partition, not a
        partition count, so feature_count is derived from the total input count. The
        resulting number of partitions is approximately target_partition_count.
        Intermediates go to memory, so output_gdb only holds the final features.

    Args:
        counted_feature (str): The feature class whose features the partitions are
            balanced around and counted for, for example the roads.
        context_features (list[str]): The other inputs the pipeline selects within
            the halo of a partition.
        target_partition_count (int): The approximate number of partitions wanted.
        output_gdb (str): The gdb the two partition features are written to.
        name_prefix (str): Prefix for the feature class and count field names,
            for example "road".
        halo_m (int): The distance in meters around a cell a pod selects data within.
    """
    all_features = [counted_feature, *context_features]
    total_count = sum(_count(feature) for feature in all_features)
    feature_count = math.ceil(total_count / target_partition_count)
    logger.info(
        f"Creating partitions for {total_count} features, "
        f"{feature_count} features per partition"
    )

    arcpy.cartography.CreateCartographicPartitions(
        in_features=all_features,
        out_features=_CELLS,
        feature_count=feature_count,
        partition_method="FEATURES",
    )
    arcpy.management.FeatureToPoint(
        in_features=counted_feature,
        out_feature_class=_CENTER_POINTS,
        point_location="INSIDE",
    )

    try:
        cell_stats = _compute_cell_stats(
            counted_feature=counted_feature,
            all_features=all_features,
            halo_m=halo_m,
        )
        _write_partition_features(
            cell_stats=cell_stats,
            output_gdb=output_gdb,
            name_prefix=name_prefix,
            halo_m=halo_m,
        )
    finally:
        for intermediate in (_CELL_LAYER, _CENTER_POINTS, _CELLS):
            if arcpy.Exists(intermediate):
                arcpy.management.Delete(intermediate)


def _compute_cell_stats(
    counted_feature: str, all_features: list[str], halo_m: int
) -> list[_CellStats]:
    """
    Counts, per partition cell, the counted features with their inside point within
    the cell, those intersecting it, and the features of all inputs within the halo.
    """
    oid_field = arcpy.Describe(_CELLS).OIDFieldName
    center_points_layer = arcpy.management.MakeFeatureLayer(
        in_features=_CENTER_POINTS, out_layer="partition_center_points_layer"
    )[0]
    input_layers = {
        feature: arcpy.management.MakeFeatureLayer(
            in_features=feature, out_layer=f"partition_input_layer_{i}"
        )[0]
        for i, feature in enumerate(all_features)
    }

    with arcpy.da.SearchCursor(_CELLS, ["OID@", "SHAPE@"]) as cursor:
        cells = list(cursor)

    cell_stats = []
    try:
        for oid, shape in cells:
            arcpy.management.MakeFeatureLayer(
                in_features=_CELLS,
                out_layer=_CELL_LAYER,
                where_clause=f"{oid_field} = {oid}",
            )
            cell_stats.append(
                _CellStats(
                    oid=oid,
                    shape=shape,
                    with_centerpoint_within=_count_selected(
                        layer=center_points_layer, overlap_type="WITHIN"
                    ),
                    intersecting=_count_selected(
                        layer=input_layers[counted_feature],
                        overlap_type="INTERSECT",
                    ),
                    vector_count=sum(
                        _count_selected(
                            layer=layer,
                            overlap_type="WITHIN_A_DISTANCE",
                            search_distance=f"{halo_m} Meters",
                        )
                        for layer in input_layers.values()
                    ),
                )
            )
            arcpy.management.Delete(_CELL_LAYER)
    finally:
        for layer in (center_points_layer, *input_layers.values()):
            arcpy.management.Delete(layer)

    return cell_stats


def _count_selected(
    layer, overlap_type: str, search_distance: str | None = None
) -> int:
    """
    Selects the features in layer that relate to the current cell and returns how
    many were selected.
    """
    arcpy.management.SelectLayerByLocation(
        in_layer=layer,
        overlap_type=overlap_type,
        select_features=_CELL_LAYER,
        search_distance=search_distance,
        selection_type="NEW_SELECTION",
    )
    return _count(layer)


def _count(feature) -> int:
    return int(arcpy.management.GetCount(feature)[0])


def _write_partition_features(
    cell_stats: list[_CellStats], output_gdb: str, name_prefix: str, halo_m: int
) -> None:
    """
    Writes the fan-in feature with every cell and the fan-out feature with the
    cells that contain counted features, numbered by partition_index.
    """
    within_field = f"{name_prefix}s_with_centerpoint_within"
    intersecting_field = f"{name_prefix}s_intersecting"
    fan_in = os.path.join(output_gdb, f"{name_prefix}_partitions_fan_in")
    fan_out = os.path.join(output_gdb, f"{name_prefix}_partitions_fan_out")

    if not arcpy.Exists(output_gdb):
        arcpy.management.CreateFileGDB(
            out_folder_path=os.path.dirname(output_gdb),
            out_name=os.path.basename(output_gdb),
        )
    for output in (fan_in, fan_out):
        if arcpy.Exists(output):
            arcpy.management.Delete(output)

    spatial_reference = arcpy.Describe(_CELLS).spatialReference
    count_fields = [within_field, intersecting_field, VECTOR_COUNT_FIELD, HALO_FIELD]
    _create_polygon_feature(
        path=fan_in, fields=count_fields, spatial_reference=spatial_reference
    )
    _create_polygon_feature(
        path=fan_out,
        fields=[PARTITION_INDEX_FIELD, *count_fields],
        spatial_reference=spatial_reference,
    )

    with arcpy.da.InsertCursor(fan_in, ["SHAPE@", *count_fields]) as cursor:
        for stats in cell_stats:
            cursor.insertRow(
                [
                    stats.shape,
                    stats.with_centerpoint_within,
                    stats.intersecting,
                    stats.vector_count,
                    halo_m,
                ]
            )

    kept = [
        stats
        for stats in cell_stats
        if stats.with_centerpoint_within > 0 or stats.intersecting > 0
    ]
    kept.sort(
        key=lambda stats: (
            -stats.vector_count,
            -stats.shape.labelPoint.Y,
            stats.shape.labelPoint.X,
        )
    )

    with arcpy.da.InsertCursor(
        fan_out, ["SHAPE@", PARTITION_INDEX_FIELD, *count_fields]
    ) as cursor:
        for partition_index, stats in enumerate(kept):
            if stats.with_centerpoint_within == 0:
                logger.warning(
                    f"Partition {partition_index} (cell {stats.oid}) has "
                    f"{stats.intersecting} intersecting {name_prefix} features but "
                    f"no centre points within it"
                )
            cursor.insertRow(
                [
                    stats.shape,
                    partition_index,
                    stats.with_centerpoint_within,
                    stats.intersecting,
                    stats.vector_count,
                    halo_m,
                ]
            )

    logger.info(
        f"Wrote {len(cell_stats)} cells to {fan_in} and {len(kept)} partitions "
        f"to {fan_out}. N = {len(kept)}"
    )


def _create_polygon_feature(
    path: str, fields: list[str], spatial_reference: arcpy.SpatialReference
) -> None:
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(path),
        out_name=os.path.basename(path),
        geometry_type="POLYGON",
        spatial_reference=spatial_reference,
    )
    for field in fields:
        arcpy.management.AddField(in_table=path, field_name=field, field_type="LONG")


if __name__ == "__main__":
    environment_setup.main()

    # InputDataOrchestrator for the road pipeline validates that the partition
    # features exist, so the inputs are resolved with the same layout DataReader uses.
    raw_data = GIS_FILES_ROOT / dn.raw_data

    def _raw_feature(gdb: str, feature_class: str) -> str:
        return str(raw_data / f"{gdb.lower()}.gdb" / feature_class)

    create_partition_features(
        counted_feature=_raw_feature(dn.road, dn.elveg_and_sti),
        context_features=[
            _raw_feature(dn.road, dn.vegsperring),
            _raw_feature(dn.railway, dn.Bane_N50),
            _raw_feature(dn.area, dn.Begrensningskurve_N50),
            _raw_feature(dn.area, dn.AdminGrense_N50),
        ],
        target_partition_count=16,
        output_gdb=str(raw_data / f"{dn.partitioning.lower()}.gdb"),
        name_prefix="road",
        halo_m=5000,
    )
