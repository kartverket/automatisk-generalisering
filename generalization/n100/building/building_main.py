# Importing environment and directory structure modules
from env_setup import environment_setup
from env_setup import setup_directory_structure


# Importing sub models
from generalization.n100.building import building_data_preparation
from generalization.n100.building import calculating_values
from generalization.n100.building import create_simplified_building_polygons
from generalization.n100.building import create_points_from_polygon
from generalization.n100.building import points_to_polygon
from generalization.n100.building import resolve_building_conflicts
from generalization.n100.building import clean_up_building

# Importing environment
environment_setup.general_setup()
setup_directory_structure.main()


def main():
    building_data_preparation.main()
    create_simplified_building_polygons.main()
    create_points_from_polygon.main()
    calculating_values.main()
    points_to_polygon.main()
    resolve_building_conflicts.main()
    # clean_up_building.main()


if __name__ == "__main__":
    main()
