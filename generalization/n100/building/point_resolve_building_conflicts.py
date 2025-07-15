# Importing modules
from xml.sax.handler import feature_validation

import arcpy

# Importing custom files
import config
from custom_tools.general_tools import custom_arcpy
from input_data import input_n100
from input_data.input_symbology import SymbologyN100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_Values

from env_setup import environment_setup
from input_data import input_symbology
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.building.resolve_building_conflicts import (
    ResolveBuildingConflictsPoints,
)
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.geometry_tools import GeometryValidator


# Importing environment settings
import env_setup.global_config

# Importing timing decorator
from custom_tools.decorators.timing_decorator import timing_decorator


iteration_fc = config.resolve_building_conflicts_iteration_feature


@timing_decorator
def main():
    """
    This script resolves building conflicts, both building polygons and points
    """
    environment_setup.main()
    transforming_points_squares()
    fixing_potential_geometry_errors()

    resolve_building_conflicts()


def transforming_points_squares():
    polygon_processor = PolygonProcessor(
        input_building_points=Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
        output_polygon_feature_class=Building_N100.point_resolve_building_conflicts___building_points_squares___n100_building.value,
        building_symbol_dimensions=N100_Symbology.building_symbol_dimensions.value,
        symbol_field_name="symbol_val",
        index_field_name="OBJECTID",
    )
    polygon_processor.run()


def fixing_potential_geometry_errors():
    input_features_validation = {
        "building_pints": Building_N100.point_resolve_building_conflicts___building_points_squares___n100_building.value,
        "building_polygons": Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
        "road": Building_N100.data_preparation___unsplit_roads___n100_building.value,
        "railroad_tracks": Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        "railroad_stations": Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        "begrensningskurver": Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        "power_grid_lines": Building_N100.data_preparation___power_grid_lines___n100_building.value,
    }

    data_validation = GeometryValidator(
        input_features=input_features_validation,
        output_table_path=Building_N100.point_resolve_building_conflicts___geometry_validation___n100_building.value,
    )
    data_validation.check_repair_sequence()


def resolve_building_conflicts():
    """
    Resolves conflicts between building features and other spatial elements such as roads, railways, and water features.

    This function performs the following tasks:
    1. Defines aliases for various input and reference layers, including building points and polygons, roads, railways, and symbology files.
    2. Sets up input and output mappings for the building features and context layers.
    3. Configures the `ResolveBuildingConflicts` class to process these layers, handling barriers and building gaps.
    4. Uses `PartitionIterator` to manage large datasets efficiently by processing them in smaller chunks.
    5. Executes the conflict resolution process and generates the final outputs.

    The function utilizes the following components:
    - `ResolveBuildingConflicts` class: A custom class for handling building conflicts with spatial barriers.
    - `PartitionIterator`: A utility for processing large datasets by partitioning them into manageable chunks.
    - `N100_Values` and `N100_Symbology`: Configuration objects that provide buffer clearance distances and symbology settings.

    Inputs:
        - Building points and polygons
        - Contextual layers for roads, railways, railway stations, and boundary curves
        - Symbology files for various spatial features

    Outputs:
        - Processed building points
        - Processed building polygons

    Configuration:
        - `building_gap_distance`: Clearance distance between buildings and barriers.
        - `barrier_gap_distances`: Clearance distances for specific barriers (roads, railways, etc.).
        - `lyrx_files`: Symbology files used for visual representation of features.

    Execution:
        - `PartitionIterator` is used to iterate over partitions of data for processing.
    """
    building_points = "building_points"
    building_polygons = "building_polygons"

    road = "road"
    railway = "railway"
    railway_station = "raiilway_station"
    begrensningskurve = "begrensningskurve"
    building_squares_lyrx = "building_squares_lyrx"
    building_polygons_lyrx = "building_polygons_lyrx"
    begrensningskurve_lyrx = "begrensningskurve_lyrx"
    road_lyrx = "road_lyrx"
    railway_station_lyrx = "railway_station_lyrx"
    railway_lyrx = "railway_lyrx"
    power_grid_lines = "power_grid_lines"

    inputs = {
        building_points: [
            "input",
            Building_N100.point_resolve_building_conflicts___building_points_squares___n100_building.value,
        ],
        building_polygons: [
            "input",
            Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
        ],
        road: [
            "context",
            Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
        ],
        railway: [
            "context",
            Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
        ],
        railway_station: [
            "context",
            Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        ],
        begrensningskurve: [
            "context",
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        ],
        power_grid_lines: [
            "context",
            Building_N100.data_preparation___power_grid_lines___n100_building.value,
        ],
        building_squares_lyrx: [
            "reference",
            input_symbology.SymbologyN100.squares.value,
        ],
        building_polygons_lyrx: [
            "reference",
            input_symbology.SymbologyN100.building_polygon.value,
        ],
        begrensningskurve_lyrx: [
            "reference",
            input_symbology.SymbologyN100.begrensningskurve_polygon.value,
        ],
        road_lyrx: [
            "reference",
            input_symbology.SymbologyN100.road_buffer.value,
        ],
        railway_station_lyrx: [
            "reference",
            input_symbology.SymbologyN100.railway_station_squares.value,
        ],
        railway_lyrx: [
            "reference",
            input_symbology.SymbologyN100.railway.value,
        ],
    }

    outputs = {
        building_points: [
            "building_points_after_rbc",
            Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
        ],
        building_polygons: [
            "building_polygons_after_rbc",
            Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
        ],
    }

    input_data_structure = [
        {
            "unique_alias": "building_points",
            "input_feature": (building_points, "input"),
            "lyrx_file": input_symbology.SymbologyN100.squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "building_polygons",
            "input_feature": (building_polygons, "input"),
            "lyrx_file": input_symbology.SymbologyN100.building_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "road",
            "input_feature": (road, "context"),
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_bru_L2",
        },
        {
            "unique_alias": "railroad",
            "input_feature": (railway, "context"),
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        },
        {
            "unique_alias": "railroad_station",
            "input_feature": (railway_station, "context"),
            "lyrx_file": input_symbology.SymbologyN100.railway_station_squares.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "begrensningskurve",
            "input_feature": (begrensningskurve, "context"),
            "lyrx_file": input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            "grouped_lyrx": False,
            "target_layer_name": "",
        },
        {
            "unique_alias": "power_grid_lines",
            "input_feature": (power_grid_lines, "context"),
            "lyrx_file": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "AnleggsLinje_maske_sort",
        },
    ]
    resolve_building_conflicts_config = {
        "class": ResolveBuildingConflictsPoints,
        "method": "run",
        "params": {
            "input_list_of_dicts_data_structure": input_data_structure,
            "building_inputs": {
                "building_points": (building_points, "input"),
                "building_polygons": (building_polygons, "input"),
            },
            "building_gap_distance": N100_Values.buffer_clearance_distance_m.value,
            "barrier_inputs": {
                "begrensningskurve": (begrensningskurve, "context"),
                "road": (road, "context"),
                "railway_station": (railway_station, "context"),
                "railway": (railway, "context"),
                "power_grid_lines": (power_grid_lines, "context"),
            },
            "barrier_gap_distances": {
                "begrensningskurve": N100_Values.rbc_barrier_clearance_distance_m.value,
                "road": N100_Values.rbc_barrier_clearance_distance_m.value,
                "railway_station": N100_Values.rbc_barrier_clearance_distance_m.value,
                "railway": N100_Values.rbc_barrier_clearance_distance_m.value,
                "power_grid_lines": N100_Values.rbc_barrier_clearance_distance_m.value,
            },
            "building_symbol_dimension": N100_Symbology.building_symbol_dimensions.value,
            "lyrx_files": {
                "building_squares": (building_squares_lyrx, "reference"),
                "building_polygons": (building_polygons_lyrx, "reference"),
                "begrensningskurve": (begrensningskurve_lyrx, "reference"),
                "road": (road_lyrx, "reference"),
                "railway_station": (railway_station_lyrx, "reference"),
                "railway": (railway_lyrx, "reference"),
                "power_grid_lines": (begrensningskurve_lyrx, "reference"),
            },
            "base_path_for_lyrx": Building_N100.point_resolve_building_conflicts___lyrx_root___n100_building.value,
            "root_path": Building_N100.point_resolve_building_conflicts___base_path_for_features___n100_building.value,
            "output_files": {
                "building_points": (
                    building_points,
                    "building_points_after_rbc",
                ),
                "building_polygons": (
                    building_polygons,
                    "building_polygons_after_rbc",
                ),
            },
            "map_scale": "100000",
        },
    }
    resolve_building_conflicts_partition_iteration = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[resolve_building_conflicts_config],
        root_file_partition_iterator=Building_N100.point_resolve_building_conflicts___root_file___n100_building.value,
        dictionary_documentation_path=Building_N100.point_resolve_building_conflicts___documentation___building_n100.value,
        feature_count=500000,
    )

    resolve_building_conflicts_partition_iteration.run()


if __name__ == "__main__":
    main()
