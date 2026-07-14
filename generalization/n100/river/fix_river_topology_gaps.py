import arcpy

# Importing custom files
from data_orchestrator import input_raster
from custom_tools.general_tools import custom_arcpy, line_topology
from file_manager.n100.file_manager_rivers import River_N100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup

from composition_configs import core_config, logic_config
from composition_configs import type_defs

from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.geometry_tools import (
    find_rasters_for_vector_extent,
    LineZOrientTool,
)
from custom_tools.general_tools.line_segmenter import segment_line


@timing_decorator
def main():
    environment_setup.main()
    raster = compute_raster_extent()
    fix_river_orientation(raster_list=raster)
    prepare_segmented_inputs()
    fill_line_topology_gaps(raster_list=raster)
    # fill_raod_gaps()


def compute_raster_extent() -> tuple[type_defs.RasterFilePath, ...]:

    rasters = find_rasters_for_vector_extent(
        raster_dir=str(input_raster.dom_10m),
        input_features=River_N100.data_preparation___river_lines___n100_river.value,
    )
    return tuple(rasters)


def fix_river_orientation(raster_list: tuple[type_defs.RasterFilePath, ...]):
    arcpy.management.CopyFeatures(
        in_features=River_N100.data_preparation___river_lines___n100_river.value,
        out_feature_class=River_N100.river_topology___fixed_river_orientation___n100_river.value,
    )

    flip_config = logic_config.LineZOrientConfig(
        input_lines=River_N100.river_topology___fixed_river_orientation___n100_river.value,
        raster_paths=raster_list,
        orientation_mode=logic_config.LineZOrientMode.NETWORK,
        min_anchor_z_drop_meters=2,
        min_confident_flip_meters=1.5,
        connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
    )
    LineZOrientTool(config=flip_config).run()


@timing_decorator
def prepare_segmented_inputs():
    # FillLineGaps now converts polygon connect_to_features to their
    # boundary polyline internally; no upstream PolygonToLine needed.

    # segment_line(
    #     input_fc=River_N100.river_topology___fixed_river_orientation___n100_river.value,
    #     output_fc=River_N100.river_topology___segmented_river_lines___n100_river.value,
    #     segment_interval=20,
    #     even_segments=True,
    # )
    #
    # segment_line(
    #     input_fc=River_N100.river_topology___river_polygons_as_lines___n100_river.value,
    #     output_fc=River_N100.river_topology___segmented_river_polygon_lines___n100_river.value,
    #     segment_interval=20,
    #     even_segments=True,
    # )
    pass


@timing_decorator
def fill_line_topology_gaps(raster_list: tuple[type_defs.RasterFilePath, ...]):

    work_file_manager_config = core_config.WorkFileConfig(
        root_file=River_N100.river_topology___root___n100_river.value,
    )

    river_polygons = River_N100.data_preparation___river_polygons___n100_river.value

    line_fix_config = logic_config.FillLineGapsConfig(
        input_lines=River_N100.river_topology___fixed_river_orientation___n100_river.value,
        output_lines=River_N100.river_topology___fixed_river_gaps___n100_river.value,
        work_file_manager_config=work_file_manager_config,
        gap_tolerance_meters=300,
        connect_to_features=[river_polygons],
        best_fit_weights=logic_config.BestFitWeightsConfig(
            distance=0.5,
            angle=0.25,
            z=0.25,
        ),
        output_config=logic_config.FillLineGapsOutputConfig(
            line_changes_output=River_N100.river_topology___river_gaps_changes___n100_river.value,
            write_output_metadata=True,
            candidate_connections_output=River_N100.river_topology___river_gaps_diagnostic___n100_river.value,
        ),
        angle_config=logic_config.FillLineGapsAngleConfig(
            angle_block_threshold_degrees=85,
            angle_extra_dangle_threshold_degrees=95,
            angle_local_half_window_m=20,
            lines_are_directed=True,
            connector_angle_diff_required_above_meters=5,
            connect_to_features_angle_mode={
                river_polygons: logic_config.AngleTargetMode.FORCE_NON_LINE,
            },
        ),
        z_config=logic_config.FillLineGapsZConfig(
            raster_paths=raster_list,
            z_drop_threshold=2,
        ),
        crossing_config=logic_config.FillLineGapsCrossingConfig(
            reject_crossing_connectors=True,
            crossing_check_spatial_reference=environment_setup.project_spatial_reference,
        ),
        connectivity_config=logic_config.FillLineGapsConnectivityConfig(
            connectivity_scope=logic_config.ConnectivityScope.TRANSITIVE,
            connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
        ),
        advanced_config=logic_config.FillLineGapsAdvancedConfig(
            edit_method=logic_config.EditMethod.NEW_LINE,
            increased_tolerance_edge_case_distance_meters=15,
        ),
        segmentation=logic_config.SegmentationConfig(
            interval_meters=20,
            mode=logic_config.SegmentationMode.EVEN,
        ),
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
        fill_gaps_on_self=False,
        output_config=logic_config.FillLineGapsOutputConfig(
            line_changes_output=Road_N100.data_preparation___road_gap_changes___n100_road.value,
            write_output_metadata=True,
            candidate_connections_output=Road_N100.data_preparation___road_gap_diagnostics___n100_road.value,
        ),
        crossing_config=logic_config.FillLineGapsCrossingConfig(
            reject_crossing_connectors=True,
            crossing_check_spatial_reference=environment_setup.project_spatial_reference,
        ),
        connectivity_config=logic_config.FillLineGapsConnectivityConfig(
            connectivity_tolerance_meters=environment_setup.ArcGisEnvironmentSetup.XY_TOLERANCE,
        ),
        advanced_config=logic_config.FillLineGapsAdvancedConfig(
            increased_tolerance_edge_case_distance_meters=10,
        ),
    )

    line_topology.FillLineGaps(line_gap_config=line_fix_config).run()

    arcpy.management.Merge(
        inputs=(
            Road_N100.data_preparation___nvdb_selection___n100_road.value,
            Road_N100.data_preparation___fixed_road_gaps___n100_road.value,
        ),
        output=Road_N100.data_preparation___integrated_nvdb_traktor_sti___n100_road.value,
    )


if __name__ == "__main__":
    main()
