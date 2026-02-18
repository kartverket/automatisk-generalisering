import arcpy

# Importing custom files
import config
from custom_tools.general_tools import custom_arcpy, line_topology
from file_manager import work_file_manager
from file_manager.n100.file_manager_rivers import River_N100

from env_setup import environment_setup
from input_data import input_symbology
from custom_tools.general_tools.partition_iterator import PartitionIterator

from composition_configs import core_config, logic_config

from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()
    fill_line_topology_gaps()


@timing_decorator
def fill_line_topology_gaps():
    line_fix_advanced_config = logic_config.FillLineGapsAdvancedConfig(
        fill_gaps_on_self=True,
        line_changes_output=River_N100.river_topology___river_gaps_changes___n100_river.value,
        increased_tolerance_edge_case_distance_meters=3,
        edit_method=logic_config.EditMethod.AUTO,
        connectivity_scope=logic_config.ConnectivityScope.TRANSITIVE,
        connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
        line_connectivity_mode=logic_config.LineConnectivityMode.ENDPOINTS,
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
        gap_tolerance_meters=3,
        connect_to_features=[
            River_N100.data_preparation___river_polygons___n100_river.value
        ],
        advanced_config=line_fix_advanced_config,
    )

    line_topology.FillLineGaps(line_gap_config=line_fix_config).run()


if __name__ == "__main__":
    main()
