# Importing custom files relative to the root path
from custom_tools import custom_arcpy
import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from generalization.n100.building import building_data_preparation
from file_manager.n100.file_manager_buildings import TemporaryFiles

# Importing general packages
import arcpy

# Importing sub models
from generalization.n100.building import building_data_preparation
from generalization.n100.building import calculating_values
from generalization.n100.building import create_simplified_building_polygons
from generalization.n100.building import create_points_from_polygon
from generalization.n100.building import resolve_building_conflicts

# Importing environment
environment_setup.general_setup()


def main():
    building_data_preparation.main()
    create_simplified_building_polygons.main()
    create_points_from_polygon.main()
    calculating_values.main()
    resolve_building_conflicts.main()


main()
