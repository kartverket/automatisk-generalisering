# Importing modules
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
    ResolveBuildingConflicts,
)


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
    resolve_building_conflicts()


def resolve_building_conflicts():
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

    inputs = {
        building_points: [
            "input",
            Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
        ],
        building_polygons: [
            "input",
            Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
        ],
        road: [
            "context",
            Building_N100.data_preparation___unsplit_roads___n100_building.value,
        ],
        railway: [
            "context",
            input_n100.Bane,
        ],
        railway_station: [
            "context",
            Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
        ],
        begrensningskurve: [
            "context",
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
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
            input_symbology.SymbologyN100.road.value,
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

    resolve_building_conflicts_config = {
        "class": ResolveBuildingConflicts,
        "method": "run",
        "params": {
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
            },
            "barrier_gap_distances": {
                "begrensningskurve": N100_Values.rbc_barrier_clearance_distance_m.value,
                "road": N100_Values.rbc_barrier_clearance_distance_m.value,
                "railway_station": N100_Values.rbc_barrier_clearance_distance_m.value,
                "railway": N100_Values.rbc_barrier_clearance_distance_m.value,
            },
            "building_symbol_dimension": N100_Symbology.building_symbol_dimensions.value,
            "lyrx_files": {
                "building_squares": (building_squares_lyrx, "reference"),
                "building_polygons": (building_polygons_lyrx, "reference"),
                "begrensningskurve": (begrensningskurve_lyrx, "reference"),
                "road": (road_lyrx, "reference"),
                "railway_station": (railway_station_lyrx, "reference"),
                "railway": (railway_lyrx, "reference"),
            },
            "base_path_for_lyrx": Building_N100.point_resolve_building_conflicts___lyrx_root___n100_building.value,
            "base_path_for_features": Building_N100.point_resolve_building_conflicts___base_path_for_features___n100_building.value,
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
        },
    }
    resolve_building_conflicts_partition_iteration = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[resolve_building_conflicts_config],
        root_file_partition_iterator=Building_N100.point_resolve_building_conflicts___root_file___n100_building.value,
        scale=env_setup.global_config.scale_n100,
        dictionary_documentation_path=Building_N100.point_resolve_building_conflicts___documentation___building_n100.value,
        feature_count="8000",
    )

    resolve_building_conflicts_partition_iteration.run()


if __name__ == "__main__":
    main()
