# Importing modules
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator


# Importing building scripts
from generalization.n100.building import data_preparation
from generalization.n100.building import calculate_polygon_values
from generalization.n100.building import calculate_point_values
from generalization.n100.building import simplify_polygons
from generalization.n100.building import polygon_propogate_displacement
from generalization.n100.building import polygon_to_point
from generalization.n100.building import hospital_church_clusters
from generalization.n100.building import point_propogate_displacement
from generalization.n100.building import point_displacement_with_buffer
from generalization.n100.building import point_resolve_building_conflicts
from generalization.n100.building import (
    removing_points_and_erasing_polygons_in_water_features,
)
from generalization.n100.building import data_clean_up
from generalization.n100.building import polygon_resolve_building_conflicts
from generalization.n100.building import removing_overlapping_polygons_and_points
from generalization.n100.building import finalizing_buildings


# Main function that runs all the building scripts
@timing_decorator
def main():
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
    data_preparation.main()
    simplify_polygons.main()
    calculate_polygon_values.main()
    polygon_propogate_displacement.main()
    polygon_resolve_building_conflicts.main()
    polygon_to_point.main()
    calculate_point_values.main()
    point_propogate_displacement.main()
    hospital_church_clusters.main()
    point_displacement_with_buffer.main()
    point_resolve_building_conflicts.main()
    removing_points_and_erasing_polygons_in_water_features.main()
    removing_overlapping_polygons_and_points.main()
    finalizing_buildings.main()
    data_clean_up.main()


if __name__ == "__main__":
    main()
