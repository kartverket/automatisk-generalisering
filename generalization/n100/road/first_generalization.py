# Importing packages
import arcpy

from custom_tools.general_tools.study_area_selector import StudyAreaSelector

# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import env_setup.global_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import N100_Symbology, N100_SQLResources, N100_Values


def main():
    environment_setup.main()
    selecting_paths_and_nvdb_roads_in_studyarea()
    merge_n50_and_nvdb()
    multipart_to_singlepart()
    merge_divided_roads()
    thin_road_network()
    collapse_road_detail()
    adding_second_invisibility_and_hierarchy_field()


def selecting_paths_and_nvdb_roads_in_studyarea():
    selector = StudyAreaSelector(
        input_output_file_dict={
            Road_N100.data_preperation___paths_n50___n100_road.value: Road_N100.first_generalization___paths_in_study_area___n100_road.value,
            Road_N100.data_preperation___selecting_everything_but_rampe_with_calculated_fields_nvdb___n100_road.value: Road_N100.first_generalization____nvdb_roads_in_study_area___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Asker')",
        select_local=config.select_study_area,
    )

    selector.run()


def merge_n50_and_nvdb():
    # Merging paths and nvdb roads
    arcpy.management.Merge(
        inputs=[
            Road_N100.first_generalization___paths_in_study_area___n100_road.value,
            Road_N100.first_generalization____nvdb_roads_in_study_area___n100_road.value,
        ],
        output=Road_N100.first_generalization____merged_roads_and_paths___n100_road.value,
    )


def multipart_to_singlepart():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.first_generalization____merged_roads_and_paths___n100_road.value,
        out_feature_class=Road_N100.first_generalization____multipart_to_singlepart___n100_road.value,
    )


def merge_divided_roads():
    # Execute Merge Divided Roads
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.first_generalization____multipart_to_singlepart___n100_road.value,
        merge_field="VEGNUMMER",
        merge_distance="50 Meters",
        out_features=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        out_displacement_features=Road_N100.first_generalization____merge_divided_roads_displacement_feature___n100_road.value,
        character_field="characters",
    )


def thin_road_network():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        minimum_length="750 Meters",
        invisibility_field="invisibility",
        hierarchy_field="hierarchy",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        expression="invisibility = 0",
        output_name=Road_N100.first_generalization____visible_features_after_thin_road_network___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


def collapse_road_detail():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.first_generalization____visible_features_after_thin_road_network___n100_road.value,
        collapse_distance="80 Meters",
        output_feature_class=Road_N100.first_generalization____collapse_road_detail___n100_road.value,
    )  # Should we have "locking field" here?


def adding_second_invisibility_and_hierarchy_field():
    arcpy.management.AddFields(
        in_table=Road_N100.first_generalization____collapse_road_detail___n100_road.value,
        field_description=[
            ["invisibility_2", "SHORT"],
            ["hierarchy_2", "SHORT"],
        ],
    )


if __name__ == "__main__":
    main()
