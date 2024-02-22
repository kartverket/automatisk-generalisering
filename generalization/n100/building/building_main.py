# Importing environment and directory structure
from env_setup import environment_setup
from env_setup import setup_directory_structure

# Environment and directory structure setup
environment_setup.general_setup()
setup_directory_structure.main()


# Importing building scripts
from generalization.n100.building import building_data_preparation
from generalization.n100.building import calculating_values
from generalization.n100.building import create_simplified_building_polygons
from generalization.n100.building import building_polygon_displacement_rbc
from generalization.n100.building import create_points_from_polygon
from generalization.n100.building import reducing_hospital_church_clusters
from generalization.n100.building import building_points_propagate_displacement
from generalization.n100.building import building_point_buffer_displacement
from generalization.n100.building import building_points_to_polygon
from generalization.n100.building import resolve_building_conflicts
from generalization.n100.building import building_clean_up


# Main function that runs all the building scripts
def main():
    """
    This is the main function that runs all the building scripts.

    Summary:
    1. building_data_preparation: Aims to prepare the data for future building generalization processing.
    2. create_simplified_building_polygons: Aggregates and simplifies building polygons, minimizing detailed parts of the building.
    3. building_polygon_displacement:
    4. create_points_from_polygon
    5. calculating_values
    6. propagate_displacement
    7. building_point_buffer_displacement
    8. hospital_church_clusters
    9. points_to_polygon
    10. resolve_building_conflicts
    11. clean_up_building

    """

    building_data_preparation.main()
    create_simplified_building_polygons.main()
    building_polygon_displacement_rbc.main()
    create_points_from_polygon.main()
    calculating_values.main()
    building_points_propagate_displacement.main()
    reducing_hospital_church_clusters.main()
    building_point_buffer_displacement.main()
    building_points_to_polygon.main()
    resolve_building_conflicts.main()
    building_clean_up.main()


if __name__ == "__main__":
    main()
