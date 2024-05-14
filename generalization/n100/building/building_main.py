# Importing modules
from env_setup import environment_setup
from custom_tools.timing_decorator import timing_decorator


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
from generalization.n100.building import removing_points_in_water_features
from generalization.n100.building import data_clean_up
from generalization.n100.building import polygon_resolve_building_conflicts
from generalization.n100.building import removing_overlapping_points
from generalization.n100.building import finalizing_buildings


# Main function that runs all the building scripts
@timing_decorator
def main():
    """
    This is the main function that runs all the building scripts.

    Summary:
    1. building_data_preparation:
        Aims to prepare the data for future building generalization processing.

    2. create_simplified_building_polygons:
        Aggregates and simplifies building polygons, minimizing detailed parts of the building.

    3. building_polygon_displacement_rbc:
        Aligns building polygons with roads at a 1:100,000 scale, resolves conflicts among all building polygons,
         considering various barriers, and outputs both polygon and point layers.

    4. create_points_from_polygon
        Creates points from small grunnriss lost during aggregation, and merges
        them together with collapsed points from the tools simplify building and simplify polygon.

    5. calculating_values
        Adds required fields for building point for symbology and resolves building conflicts: angle, hierarchy, and invisibility.

    6. propagate_displacement:

    7. building_point_buffer_displacement
    8. hospital_church_clusters
    9. points_to_polygon
    10. resolve_building_conflicts
    11. clean_up_building

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
    removing_points_in_water_features.main()
    removing_overlapping_points.main()
    finalizing_buildings.main()
    data_clean_up.main()


if __name__ == "__main__":
    main()
