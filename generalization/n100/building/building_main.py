# Importing modules
from collections.abc import Callable
from pathlib import Path

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n100.file_manager_buildings import Building_N100

from data_orchestrator.orchestrator import InputDataOrchestrator

# Importing building scripts
from generalization.n100.building import (
    calculate_point_values,
    calculate_polygon_values,
    data_clean_up,
    data_preparation,
    finalizing_buildings,
    hospital_church_clusters,
    point_displacement_with_buffer,
    point_propogate_displacement,
    point_resolve_building_conflicts,
    polygon_propogate_displacement,
    polygon_resolve_building_conflicts,
    polygon_to_point,
    removing_overlapping_polygons_and_points,
    removing_points_and_erasing_polygons_in_water_features,
    simplify_polygons,
)

from generalization.n100.road.pipeline_checkpoint import PipelineCheckpoint


# Main function that runs all the building scripts
@timing_decorator
def main(checkpoint: PipelineCheckpoint | None = None) -> None:
    """
    Building N100 Generalization version 1.0

    What:
        MORE DOCSTRING NEEDED: Runs the building generalization logic.
    How:
        data_preparation:
            Prepares the input data for future building generalization processes, does spatial selections and coverts.

        simplify_polygons:
            Simplify building polygons to make them easier to read and fit around other features at a N100 map scale.

        calculate_polygon_values:
            Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.

        polygon_propogate_displacement:
            Propagates displacement for building polygons to ensure their alignment with roads is adjusted
            after the road generalization process.

        polygon_resolve_building_conflicts:
            PLACEHOLDER DOCSTRING NEEDS TO BE UPDATED.

        polygon_to_point:
            Merges all points originating from building polygons to a single point feature.

        calculate_point_values:
            Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.

        point_propogate_displacement:
            Propagates displacement for building points to ensure their alignment with roads is adjusted
            after the road generalization process.

        hospital_church_clusters:
            PLACEHOLDER DOCSTRING NEEDS TO BE UPDATED.

        point_displacement_with_buffer:
            Displaces building points relative to road buffers based on specified buffer increments.
            It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
            displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

        point_resolve_building_conflicts:
            PLACEHOLDER DOCSTRING NEEDS TO BE UPDATED.

        removing_points_and_erasing_polygons_in_water_features:
            Fixes geometric conflicts between building polygon/point objects and water-features. Allows for
            tourist cabins to intersect water-features.

        removing_overlapping_polygons_and_points:
            Resolves graphic conflicts and overlaps between building features which persist after RBC,
            prioritizing buildings with higher hierarchy values.

        finalizing_buildings:
            Separates building points and polygons into their respective features they are going to be delivered as.

        data_clean_up:
            Deletes all fields for each feature expect the fields which should be kept in the delivered product.
            Then adds last edited date and finally checks and potentially repairs the geometry of each feature.
    Why:
        MORE DOCSTRING NEEDED: Because we need to processing building information so it is cartographic usable for N100 scale.
    """
    environment_setup.main()

    last_completed = checkpoint.load() if checkpoint else None
    if last_completed is None:
        data_orc = data_preparation.main()
        if checkpoint:
            checkpoint.save("data_preparation")
    else:
        data_orc = InputDataOrchestrator(map_scale="n100", pipeline="building")

    steps: list[tuple[str, Callable[[], object]]] = [
        ("simplify_polygons", simplify_polygons.main),
        ("calculate_polygon_values", calculate_polygon_values.main),
        ("polygon_propogate_displacement", polygon_propogate_displacement.main),
        (
            "polygon_resolve_building_conflicts",
            lambda: polygon_resolve_building_conflicts.main(data_orc=data_orc),
        ),
        ("polygon_to_point", polygon_to_point.main),
        ("calculate_point_values", calculate_point_values.main),
        ("point_propogate_displacement", point_propogate_displacement.main),
        ("hospital_church_clusters", hospital_church_clusters.main),
        ("point_displacement_with_buffer", point_displacement_with_buffer.main),
        (
            "point_resolve_building_conflicts",
            lambda: point_resolve_building_conflicts.main(data_orc=data_orc),
        ),
        (
            "removing_points_and_erasing_polygons_in_water_features",
            removing_points_and_erasing_polygons_in_water_features.main,
        ),
        (
            "removing_overlapping_polygons_and_points",
            lambda: removing_overlapping_polygons_and_points.main(
                data_orc=data_orc
            ),
        ),
        ("finalizing_buildings", finalizing_buildings.main),
        ("data_clean_up", data_clean_up.main),
        (
            "write_workfile_count",
            lambda: Path(
                Building_N100.total_workfile_manager_files__n100.value
            ).write_text(
                "Total amount of work files created: "
                f"{WorkFileManager._build_file_counter}",
                encoding="utf-8",
            ),
        ),
    ]
    step_names = [name for name, _ in steps]
    if last_completed and last_completed not in ["data_preparation", *step_names]:
        raise ValueError(f"Unknown building pipeline checkpoint: {last_completed}")

    start_index = 0
    if last_completed and last_completed != "data_preparation":
        start_index = step_names.index(last_completed) + 1

    for name, step in steps[start_index:]:
        step()
        if checkpoint:
            checkpoint.save(name)

    if checkpoint:
        checkpoint.delete()


if __name__ == "__main__":
    main()
