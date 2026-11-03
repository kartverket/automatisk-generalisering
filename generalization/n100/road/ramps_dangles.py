"""
In new road input from nvdb ramps dont always extend all the way to main roads,
This causes the ramps generalisation to leave behind dangles.
This function handles those dangles.
Make it in such a way that we can reuse the logic to handle other similar cases of dangles.
Sitations where the dangle is one of the roads part of the crossroad then we convert the crossroad to a T cross in the same medium.
"""

import logging
import os

import arcpy

logger = logging.getLogger(__name__)

_MATCH_TOLERANCE = "5 Meters"
_NEW_DANGLES_LAYER = "new_dangles_layer"
_DANGLING_LINES_LAYER = "dangling_lines_layer"


def create_dangle_points(lines_fc: str, dangle_points_fc: str) -> None:
    """Write the dangle end points of `lines_fc` to `dangle_points_fc`."""
    if arcpy.Exists(dangle_points_fc):
        arcpy.management.Delete(dangle_points_fc)

    arcpy.management.FeatureVerticesToPoints(
        in_features=lines_fc,
        out_feature_class=dangle_points_fc,
        point_location="DANGLE",
    )


def _select_new_dangles(dangle_points_fc: str, baseline_dangles_fc: str) -> int:
    """Make a layer of the dangles not in the baseline and return how many there are."""
    arcpy.management.MakeFeatureLayer(dangle_points_fc, _NEW_DANGLES_LAYER)
    arcpy.management.SelectLayerByLocation(
        in_layer=_NEW_DANGLES_LAYER,
        overlap_type="WITHIN_A_DISTANCE",
        select_features=baseline_dangles_fc,
        search_distance=_MATCH_TOLERANCE,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )
    return int(arcpy.management.GetCount(_NEW_DANGLES_LAYER).getOutput(0))


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


def _move_dangling_lines(lines_fc: str, removed_fc: str) -> int:
    """Move short lines touching the selected new dangles from `lines_fc` to `removed_fc`."""
    arcpy.management.MakeFeatureLayer(lines_fc, _DANGLING_LINES_LAYER)
    arcpy.management.SelectLayerByLocation(
        in_layer=_DANGLING_LINES_LAYER,
        overlap_type="INTERSECT",
        select_features=_NEW_DANGLES_LAYER,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=_DANGLING_LINES_LAYER,
        selection_type="SUBSET_SELECTION",
    )
    count = int(arcpy.management.GetCount(_DANGLING_LINES_LAYER).getOutput(0))
    if count:
        arcpy.management.Append(
            inputs=_DANGLING_LINES_LAYER, target=removed_fc, schema_type="NO_TEST"
        )
        arcpy.management.DeleteFeatures(_DANGLING_LINES_LAYER)
    arcpy.management.Delete(_DANGLING_LINES_LAYER)
    return count


def remove_new_dangles(
    lines_fc: str,
    baseline_dangles_fc: str,
    dangle_points_fc: str,
    removed_fc: str,
    max_iterations: int = 20,
) -> int:
    """Repeatedly remove dangling lines that were not dangles in the baseline.

    Removing a dangling line can expose a new dangle on the line it was attached
    to, so the search repeats until no new dangle (or no removable line) is left.

    Args:
        lines_fc: Line feature class edited in place.
        baseline_dangles_fc: Dangle points that existed before the step that caused
            the dangles (from `create_dangle_points`); these are never touched.
        dangle_points_fc: Scratch output path for dangle points.
        removed_fc: Permanent output; receives a copy of every removed line.
        max_length_m: Longest line that may be removed.
        max_iterations: Safety limit for the loop.

    Returns:
        Total number of removed lines.
    """
    _create_removed_fc(template_fc=lines_fc, removed_fc=removed_fc)

    total_removed = 0
    for iteration in range(1, max_iterations + 1):
        create_dangle_points(lines_fc, dangle_points_fc)
        new_dangle_count = _select_new_dangles(dangle_points_fc, baseline_dangles_fc)
        if new_dangle_count == 0:
            arcpy.management.Delete(_NEW_DANGLES_LAYER)
            break

        removed = _move_dangling_lines(lines_fc, removed_fc)
        arcpy.management.Delete(_NEW_DANGLES_LAYER)
        logger.info(
            "Dangle removal iteration %d: %d new dangles, %d lines removed",
            iteration,
            new_dangle_count,
            removed,
        )
        if removed == 0:
            break
        total_removed += removed
    else:
        logger.warning("Dangle removal stopped at max_iterations=%d", max_iterations)

    return total_removed


if __name__ == "__main__":
    import arcpy
    from env_setup import environment_setup
    from file_manager.n100.file_manager_roads import Road_N100

    environment_setup.main()

    src = Road_N100.ramps__generalized_ramps__n100_road.value
    test_lines = (
        f"{src}_dangle_test"  # scratch copy, the permanent file stays untouched
    )
    test_removed = f"{src}_dangle_test_removed"
    test_points = f"{src}_dangle_test_points"

    arcpy.management.CopyFeatures(src, test_lines)
    test_baseline = f"{src}_dangle_test_baseline"
    create_dangle_points(
        Road_N100.data_preparation___road_single_part_2___n100_road.value,
        test_baseline,
    )
    removed = remove_new_dangles(
        lines_fc=test_lines,
        baseline_dangles_fc=test_baseline,
        dangle_points_fc=test_points,
        removed_fc=test_removed,
    )
    print(f"Removed {removed} lines")
