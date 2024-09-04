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
    """ """
    environment_setup.main()
    # data_preparation.main()
    # simplify_polygons.main()
    # calculate_polygon_values.main()
    # polygon_propogate_displacement.main()
    # polygon_resolve_building_conflicts.main()
    # polygon_to_point.main()
    # calculate_point_values.main()
    # point_propogate_displacement.main()
    # hospital_church_clusters.main()
    # point_displacement_with_buffer.main()
    # point_resolve_building_conflicts.main()
    # removing_points_and_erasing_polygons_in_water_features.main()
    removing_overlapping_polygons_and_points.main()
    finalizing_buildings.main()
    data_clean_up.main()


if __name__ == "__main__":
    main()
