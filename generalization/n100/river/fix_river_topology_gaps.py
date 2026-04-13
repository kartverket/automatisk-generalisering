import arcpy

# Importing custom files
import config
from custom_tools.general_tools import custom_arcpy, line_topology
from file_manager.n100.file_manager_rivers import River_N100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup

from composition_configs import core_config, logic_config

from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.geometry_tools import (
    LineAngleTool,
    LineEndpointTool,
    find_rasters_for_vector_extent,
    LineZValueTool,
    LineZOrientTool,
)


@timing_decorator
def main():
    environment_setup.main()
    fill_line_topology_gaps()
    # fill_raod_gaps()
    # fix_river_orientation()
    # find_angles()
    # find_xy_endpoints()
    # find_relevant_rasters()


def fix_river_orientation():
    arcpy.management.CopyFeatures(
        in_features=River_N100.data_preparation___river_lines___n100_river.value,
        out_feature_class=River_N100.river_topology___fixed_river_orientation___n100_river.value,
    )

    rasters = find_rasters_for_vector_extent(
        raster_dir=config.raster_directory,
        input_features=River_N100.data_preparation___river_lines___n100_river.value,
    )

    flip_config = logic_config.LineZOrientConfig(
        input_lines=River_N100.river_topology___fixed_river_orientation___n100_river.value,
        raster_paths=rasters,
        orientation_mode=logic_config.LineZOrientMode.NETWORK,
        min_z_drop_meters=1.5,
        connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
    )
    LineZOrientTool(config=flip_config).run()


def find_angles():
    line_angle_config = logic_config.AngleToolConfig(
        input_lines=River_N100.data_preparation___river_lines___n100_river.value,
        angle_modes=(logic_config.LineAngleMode.ALL_ANGLES,),
        output_lines=River_N100.river_topology___river_angles___n100_river.value,
        return_results=True,
        write_fields=True,
    )
    returned_angles = LineAngleTool(config=line_angle_config).run()
    print(f"{returned_angles}")

    line_angle_config2 = logic_config.AngleToolConfig(
        input_lines=River_N100.river_topology___river_gaps_changes___n100_river.value,
        angle_modes=(logic_config.LineAngleMode.ALL_ANGLES,),
        output_lines=River_N100.river_topology___river_angles_2___n100_river.value,
        return_results=True,
        write_fields=True,
    )
    returned_angles2 = LineAngleTool(config=line_angle_config2).run()


@timing_decorator
def fill_line_topology_gaps():

    rasters = find_rasters_for_vector_extent(
        raster_dir=config.raster_directory,
        input_features=River_N100.data_preparation___river_lines___n100_river.value,
    )
    line_fix_advanced_config = logic_config.FillLineGapsAdvancedConfig(
        fill_gaps_on_self=True,
        line_changes_output=River_N100.river_topology___river_gaps_changes___n100_river.value,
        write_output_metadata=True,
        candidate_connections_output=River_N100.river_topology___river_gaps_diagnostic___n100_river.value,
        increased_tolerance_edge_case_distance_meters=10,
        edit_method=logic_config.EditMethod.AUTO,
        connectivity_scope=logic_config.ConnectivityScope.TRANSITIVE,
        connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
        line_connectivity_mode=logic_config.LineConnectivityMode.ENDPOINTS,
        angle_block_threshold_degrees=85,
        angle_extra_dangle_threshold_degrees=95,
        best_fit_weights=(
            logic_config.BestFitWeightsConfig(
                distance=0.5,
                angle=0.25,
                z=0.25,
            )
        ),
        angle_local_half_window_m=20,
        source_direction_mode=logic_config.SourceDirectionMode.RASTER_DERIVED,
        min_z_drop_meters=1,
        raster_paths=rasters,
    )
    work_file_manager_config = core_config.WorkFileConfig(
        root_file=River_N100.river_topology___root___n100_river.value,
        write_to_memory=False,
        keep_files=True,
    )

    line_fix_config = logic_config.FillLineGapsConfig(
        input_lines=River_N100.data_preparation___river_lines___n100_river.value,
        output_lines=River_N100.river_topology___fixed_river_gaps___n100_river.value,
        work_file_manager_config=work_file_manager_config,
        gap_tolerance_meters=25,
        connect_to_features=[
            River_N100.data_preparation___river_polygons___n100_river.value
        ],
        advanced_config=line_fix_advanced_config,
    )

    line_topology.FillLineGaps(line_gap_config=line_fix_config).run()


@timing_decorator
def fill_raod_gaps():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_selection___nvdb_roads___n100_road.value,
        expression="objtype IN ('VegSenterlinje')",
        output_name=Road_N100.data_preparation___nvdb_selection___n100_road.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_selection___nvdb_roads___n100_road.value,
        expression="objtype IN ('VegSenterlinje')",
        output_name=Road_N100.data_preparation___tractor_selection___n100_road.value,
        inverted=True,
    )

    line_fix_advanced_config = logic_config.FillLineGapsAdvancedConfig(
        fill_gaps_on_self=False,
        line_changes_output=Road_N100.data_preparation___road_gap_changes___n100_road.value,
        write_output_metadata=True,
        candidate_connections_output=Road_N100.data_preparation___road_gap_diagnostics___n100_road.value,
        increased_tolerance_edge_case_distance_meters=10,
        edit_method=logic_config.EditMethod.AUTO,
        connectivity_scope=logic_config.ConnectivityScope.DIRECT_CONNECTION,
        connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
        line_connectivity_mode=logic_config.LineConnectivityMode.ENDPOINTS,
    )
    work_file_manager_config = core_config.WorkFileConfig(
        root_file=Road_N100.data_preparation___road_gap_root___n100_road.value,
        write_to_memory=False,
        keep_files=True,
    )

    line_fix_config = logic_config.FillLineGapsConfig(
        input_lines=Road_N100.data_preparation___tractor_selection___n100_road.value,
        output_lines=Road_N100.data_preparation___fixed_road_gaps___n100_road.value,
        work_file_manager_config=work_file_manager_config,
        gap_tolerance_meters=25,
        connect_to_features=[
            Road_N100.data_preparation___nvdb_selection___n100_road.value
        ],
        advanced_config=line_fix_advanced_config,
    )

    line_topology.FillLineGaps(line_gap_config=line_fix_config).run()

    arcpy.management.Merge(
        inputs=(
            Road_N100.data_preparation___nvdb_selection___n100_road.value,
            Road_N100.data_preparation___fixed_road_gaps___n100_road.value,
        ),
        output=Road_N100.data_preparation___integrated_nvdb_traktor_sti___n100_road.value,
    )


@timing_decorator
def find_xy_endpoints():
    xy_endpoint_config = logic_config.LineEndpointToolConfig(
        input_lines=River_N100.river_topology___river_angles___n100_river.value,
        output_lines=River_N100.river_topology___river_xy_endpoints___n100_river.value,
        endpoint_modes=(logic_config.LineEndpointMode.BOTH_ENDPOINTS,),
        write_fields=True,
        return_results=True,
    )

    results = LineEndpointTool(config=xy_endpoint_config).run()
    # print(f"{results}")


@timing_decorator
def find_relevant_rasters():
    rasters = find_rasters_for_vector_extent(
        raster_dir=config.raster_directory,
        input_features=River_N100.data_preparation___river_lines___n100_river.value,
    )
    print(rasters)

    line_z_config = logic_config.LineZValueToolConfig(
        input_lines=River_N100.data_preparation___river_lines___n100_river.value,
        input_rasters=rasters,
        endpoint_modes=(logic_config.LineZValueMode.BOTH_ENDPOINTS,),
        output_lines=River_N100.river_topology___river_angles___n100_river.value,
        write_fields=True,
    )
    LineZValueTool(config=line_z_config).run()


if __name__ == "__main__":
    main()
