import arcpy

# Importing custom files
import config
from custom_tools.general_tools import custom_arcpy
from generalization.n100 import building
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

from composition_configs import core_config, logic_config

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
    building_points = "building_points"
    building_polygons = "building_polygons"

    road = "road"
    railway = "railway"
    railway_station = "raiilway_station"
    begrensningskurve = "begrensningskurve"
    power_grid_lines = "power_grid_lines"

    building_points_after_rbc = "building_points_after_rbc"
    building_polygons_after_rbc = "building_polygons_after_rbc"

    rbc_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=building_points,
                path=Building_N100.point_resolve_building_conflicts___building_points_squares___n100_building.value,
            ),
            core_config.InputEntry.processing_input(
                object=building_polygons,
                path=Building_N100.polygon_resolve_building_conflicts___building_polygons_final___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=road,
                path=Building_N100.data_preparation___road_symbology_buffers___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=railway,
                path=Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=railway_station,
                path=Building_N100.data_preparation___railway_stations_to_polygons___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=begrensningskurve,
                path=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=power_grid_lines,
                path=Building_N100.data_preparation___power_grid_lines___n100_building.value,
            ),
        ]
    )

    rbc_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=building_points,
                tag=building_points_after_rbc,
                path=Building_N100.point_resolve_building_conflicts___POINT_OUTPUT___n100_building.value,
            ),
            core_config.OutputEntry.vector_output(
                object=building_polygons,
                tag=building_polygons_after_rbc,
                path=Building_N100.point_resolve_building_conflicts___POLYGON_OUTPUT___n100_building.value,
            ),
        ]
    )

    rbc_io_config = core_config.PartitionIOConfig(
        input_config=rbc_input_config,
        output_config=rbc_output_config,
        documentation_directory=Building_N100.rbc_point_documentation_n100_building.value,
    )

    rbc_input_data_structure = [
        logic_config.SymbologyLayerSpec(
            unique_name=building_points,
            input_feature=core_config.InjectIO(object=building_points, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.squares.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=building_polygons,
            input_feature=core_config.InjectIO(object=building_polygons, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.building_polygon.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=road,
            input_feature=core_config.InjectIO(object=road, tag="input"),
            input_lyrx=config.symbology_samferdsel,
            grouped_lyrx=True,
            target_layer_name="N100_Samferdsel_senterlinje_veg_bru_L2",
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=railway,
            input_feature=core_config.InjectIO(object=railway, tag="input"),
            input_lyrx=config.symbology_samferdsel,
            grouped_lyrx=True,
            target_layer_name="N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=railway_station,
            input_feature=core_config.InjectIO(object=railway_station, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.railway_station_squares.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=begrensningskurve,
            input_feature=core_config.InjectIO(object=begrensningskurve, tag="input"),
            input_lyrx=input_symbology.SymbologyN100.begrensningskurve_polygon.value,
            grouped_lyrx=False,
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=power_grid_lines,
            input_feature=core_config.InjectIO(object=power_grid_lines, tag="input"),
            input_lyrx=config.anleggslinje,
            grouped_lyrx=False,
        ),
    ]

    rbc_barrier_default_rule = logic_config.BarrierDefault(
        gap_meters=30,
        use_turn_orientation=False,
    )

    rbc_init_config = logic_config.RbcPointsInitKwargs(
        input_data_structure=rbc_input_data_structure,
        building_points_unique_name=building_points,
        building_polygons_unique_name=building_polygons,
        building_gap_distance_m=N100_Values.buffer_clearance_distance_m.value,
        output_points_after_rbc=core_config.InjectIO(
            object=building_points,
            tag=building_points_after_rbc,
        ),
        output_polygons_after_rbc=core_config.InjectIO(
            object=building_polygons,
            tag=building_polygons_after_rbc,
        ),
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Building_N100.point_resolve_building_conflicts___root_path___n100_building.value
        ),
        building_symbol_dimension=N100_Symbology.building_symbol_dimensions.value,
        barrier_default=rbc_barrier_default_rule,
        map_scale="100000",
    )

    point_rbc_method = core_config.ClassMethodEntryConfig(
        class_=ResolveBuildingConflictsPoints,
        method=ResolveBuildingConflictsPoints.run,
        init_params=rbc_init_config,
    )
    rbc_method_injects_config = core_config.MethodEntriesConfig(
        entries=[point_rbc_method]
    )

    rbc_partition_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=500_000,
        context_radius_meters=500,
        run_partition_optimization=False,
    )

    rbc_parition_work_file_manager_config = core_config.WorkFileConfig(
        root_file=Building_N100.point_resolve_building_conflicts___partition_root_path___n100_building.value,
        keep_files=True,
    )

    partition_point_rbc = PartitionIterator(
        partition_io_config=rbc_io_config,
        partition_method_inject_config=rbc_method_injects_config,
        partition_iterator_run_config=rbc_partition_run_config,
        work_file_manager_config=rbc_parition_work_file_manager_config,
    )

    partition_point_rbc.run()


if __name__ == "__main__":
    main()
