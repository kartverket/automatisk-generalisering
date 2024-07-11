# Importing packages
import arcpy
import os

from input_data import input_n100
from file_manager.n100.file_manager_buildings import Building_N100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values

import env_setup.global_config
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.generalization_tools.building.buffer_displacement import (
    BufferDisplacement,
)
from env_setup import environment_setup
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy


@timing_decorator
def main():
    """
    Summary:
        Needs summary

    Details:
        1. `setup_arcpy_environment`:
            Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
            This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
            the `general_setup` function from the `environment_setup` module.

        2. `selection`:
            Makes the selection of the relevant input features using a sub selection since the operation is too processing heavy to be done for the global dataset. Small scale test logic untill this logic is made OOP.

        3. `creating_raod_buffer`:
            This function creates a buffered feature with a size corresponding to the road width in its symbology.
            Then it iterates through the road features first creating a smaller buffer and gradually increasing the size.
            For each iteration uses the erase tool to erase the polgon created from building points to gradually move it away from road features to prevent overlapp with road features.

        4. `copy_output_feature`:
            Copies the last output of the `creating_raod_buffer` iteration to be able to integrate it into our `file_manager` system.
    """
    environment_setup.main()

    extracting_churches_hospitals()
    buffer_displacement()
    merge_church_hospitals_buffer_displaced_points()


@timing_decorator
def extracting_churches_hospitals():
    church_hospital_sql_expression = "symbol_val IN (1, 2, 3)"

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_sql_expression,
        output_name=Building_N100.building_point_buffer_displacement___church_hospital_selection___n100_building.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Building_N100.hospital_church_clusters___final___n100_building.value,
        expression=church_hospital_sql_expression,
        output_name=Building_N100.building_point_buffer_displacement___building_points_selection___n100_building.value,
        inverted=True,
    )


@timing_decorator
def buffer_displacement():
    building_points = "building_points"
    bane = "bane"
    river = "river"
    train_stations = "train_stations"
    urban_area = "urban_area"
    roads = "roads"

    inputs = {
        building_points: [
            "input",
            Building_N100.building_point_buffer_displacement___building_points_selection___n100_building.value,
        ],
        roads: [
            "input",
            Building_N100.data_preparation___unsplit_roads___n100_building.value,
        ],
        river: [
            "context",
            Building_N100.data_preparation___processed_begrensningskurve___n100_building.value,
        ],
        urban_area: [
            "context",
            Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        ],
        train_stations: [
            "context",
            input_n100.JernbaneStasjon,
        ],
        bane: [
            "context",
            input_n100.Bane,
        ],
    }

    outputs = {
        building_points: [
            "buffer_displacement",
            Building_N100.building_point_buffer_displacement___displaced_building_points___n100_building.value,
        ],
    }
    misc_objects = {
        "begrensningskurve": [
            ("river", "context"),
            0,
        ],
        "urban_areas": [
            ("urban_area", "context"),
            1,
        ],
        "bane_station": [
            ("train_stations", "context"),
            1,
        ],
        "bane_lines": [
            ("bane", "context"),
            1,
        ],
    }

    buffer_displacement_config = {
        "class": BufferDisplacement,
        "method": "run",
        "params": {
            "input_road_lines": ("roads", "input"),
            "input_building_points": ("building_points", "input"),
            "input_misc_objects": misc_objects,
            "output_building_points": ("building_points", "buffer_displacement"),
            "sql_selection_query": N100_SQLResources.road_symbology_size_sql_selection.value,
            "root_file": Building_N100.building_point_buffer_displacement___root_file___n100_building.value,
            "building_symbol_dimensions": N100_Symbology.building_symbol_dimensions.value,
            "buffer_displacement_meter": N100_Values.buffer_clearance_distance_m.value,
            "write_work_files_to_memory": False,
            "keep_work_files": False,
        },
    }

    buffer_displacement_partition_iteration = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[buffer_displacement_config],
        root_file_partition_iterator=Building_N100.building_point_buffer_displacement___root_file___n100_building.value,
        scale=env_setup.global_config.scale_n100,
        dictionary_documentation_path=Building_N100.point_displacement_with_buffer___documentation___building_n100.value,
        feature_count="1400000",
    )

    buffer_displacement_partition_iteration.run()


@timing_decorator
def merge_church_hospitals_buffer_displaced_points():
    arcpy.management.Merge(
        inputs=[
            Building_N100.building_point_buffer_displacement___church_hospital_selection___n100_building.value,
            Building_N100.building_point_buffer_displacement___displaced_building_points___n100_building.value,
        ],
        output=Building_N100.building_point_buffer_displacement___merged_buffer_displaced_points___n100_building.value,
    )


if __name__ == "__main__":
    main()
