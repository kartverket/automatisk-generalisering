import arcpy

# Importing custom files
import config
from custom_tools.general_tools import custom_arcpy, line_topology
from file_manager.n100.file_manager_rivers import River_N100
from env_setup import environment_setup

from composition_configs import core_config, logic_config

from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.geometry_tools import LineAngleTool, LineEndpointTool


@timing_decorator
def main():
    environment_setup.main()
    fill_line_topology_gaps()
    # find_angles()
    # find_xy_endpoints()


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
        angle_block_threshold_degrees=90,
        angle_extra_dangle_threshold_degrees=70,
        line_alignment_weight=0.75,
        best_fit_weights=(
            logic_config.BestFitWeightsConfig(
                distance=0.5,
                angle=0.5,
                z=0.0,
            )
        ),
        angle_local_half_window_m=20,
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


if __name__ == "__main__":
    main()
