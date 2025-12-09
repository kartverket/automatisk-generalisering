# Importing packages
import arcpy

from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.building.buffer_displacement import (
    BufferDisplacement,
)
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from composition_configs import logic_config, core_config


@timing_decorator
def main():
    """
    What:
        Displaces building points relative to road buffers based on specified buffer increments.
        It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
        displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

    How:
        Selects hospitals, churches and tourist huts so that they are not potentially lost in the buffer displacement process.
        Then runs the buffer displacement logic on the remaining points (see `BufferDisplacement` documentation for more details.
        Finally merges the output of the BufferDisplacement with the previous hospital, church and tourist hut selection.

    Why:
        To make sure there are no graphic conflicts with buildings and roads prior to RBC improving the result of RBC,
        but also the processing speed.
    """
    environment_setup.main()

    extracting_churches_hospitals()
    run_buffer_displacement()
    merge_church_hospitals_buffer_displaced_points()


@timing_decorator
def extracting_churches_hospitals():
    """
    Selects and saves features identified as churches or hospitals based on `symbol_val`.
    Separates out features that are not churches or hospitals.
    """
    church_hospital_tourist_hut_sql_expression = (
        "symbol_val IN (1, 2, 3) Or byggtyp_nbr = 956"
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_tourist_hut_sql_expression,
        output_name=Building_N100.point_displacement_with_buffer___church_hospital_selection___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_tourist_hut_sql_expression,
        output_name=Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
        inverted=True,
    )


@timing_decorator
def run_buffer_displacement():
    """
    What:
        Displaces building points relative to road buffers based on specified buffer increments.
        It processes multiple features, mainly focusing on roads taking into account varied symbology width for roads,
        displacing building points away from roads and other barriers, while iteratively calculating buffer increments.

    How:
        Runs the BufferDisplacement using the PartitionIterator. See `BufferDisplacement` documentation for more details.
    """
    building_points = "building_points"
    bane = "bane"
    river = "river"
    train_stations = "train_stations"
    urban_area = "urban_area"
    roads = "roads"
    power_grid_lines = "power_grid_lines"

    processed_buildings = "processed_buildings"

    buffer_displacement_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=building_points,
                path=Building_N100.point_displacement_with_buffer___building_points_selection___n100_building.value,
            ),
            core_config.InputEntry.processing_input(
                object=roads,
                path=Building_N100.data_preparation___unsplit_roads___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=river,
                path=Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=urban_area,
                path=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=train_stations,
                path=Building_N100.data_selection___railroad_stations_n100_input_data___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=bane,
                path=Building_N100.data_selection___railroad_tracks_n100_input_data___n100_building.value,
            ),
            core_config.InputEntry.context_input(
                object=power_grid_lines,
                path=Building_N100.data_preparation___power_grid_lines___n100_building.value,
            ),
        ]
    )

    buffer_displacement_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=building_points,
                tag=processed_buildings,
                path=Building_N100.point_displacement_with_buffer___displaced_building_points___n100_building.value,
            ),
        ]
    )

    buffer_displacement_io_config = core_config.PartitionIOConfig(
        input_config=buffer_displacement_input_config,
        output_config=buffer_displacement_output_config,
        documentation_directory=Building_N100.buffer_displacement_documentation_n100_building.value,
    )

    input_line_barriers_data = {
        "begrensningskurve": [
            core_config.InjectIO(object=river, tag="input"),
            0,
        ],
        "urban_areas": [
            core_config.InjectIO(object=urban_area, tag="input"),
            1,
        ],
        "bane_station": [
            core_config.InjectIO(object=train_stations, tag="input"),
            1,
        ],
        "bane_lines": [
            core_config.InjectIO(object=bane, tag="input"),
            1,
        ],
        "power_grid_lines": [
            core_config.InjectIO(object=power_grid_lines, tag="input"),
            1,
        ],
    }

    buffer_displacement_init_config = logic_config.BufferDisplacementKwargs(
        input_road_line=core_config.InjectIO(object=roads, tag="input"),
        input_building_points=core_config.InjectIO(object=building_points, tag="input"),
        input_line_barriers=input_line_barriers_data,
        output_building_points=core_config.InjectIO(
            object=building_points, tag=processed_buildings
        ),
        sql_selection_query=N100_SQLResources.new_road_symbology_size_sql_selection.value,
        building_symbol_dimension=N100_Symbology.building_symbol_dimensions.value,
        displacement_distance_m=N100_Values.buffer_clearance_distance_m.value,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Building_N100.point_displacement_with_buffer___root_file___n100_building.value,
        ),
    )

    buffer_displacement_output_config = core_config.MethodEntriesConfig(
        entries=[
            core_config.ClassMethodEntryConfig(
                class_=BufferDisplacement,
                method=BufferDisplacement.run,
                init_params=buffer_displacement_init_config,
            )
        ]
    )

    partition_buffer_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=1_400_000,
        context_radius_meters=500,
        run_partition_optimization=True,
    )

    buffer_displacement_partition = PartitionIterator(
        partition_io_config=buffer_displacement_io_config,
        partition_method_inject_config=buffer_displacement_output_config,
        partition_iterator_run_config=partition_buffer_run_config,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Building_N100.point_displacement_with_buffer___partition_root_file___n100_building.value
        ),
    )
    buffer_displacement_partition.run()


@timing_decorator
def merge_church_hospitals_buffer_displaced_points():
    arcpy.management.Merge(
        inputs=[
            Building_N100.point_displacement_with_buffer___church_hospital_selection___n100_building.value,
            Building_N100.point_displacement_with_buffer___displaced_building_points___n100_building.value,
        ],
        output=Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
    )


if __name__ == "__main__":
    main()
