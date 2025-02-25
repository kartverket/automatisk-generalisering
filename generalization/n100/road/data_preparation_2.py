# Importing packages
import arcpy
import os


# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from input_data import input_elveg
from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import env_setup.global_config
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.decorators.partition_io_decorator import partition_io_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.general_tools.study_area_selector import StudyAreaSelector
from custom_tools.general_tools.geometry_tools import GeometryValidator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools import file_utilities
from custom_tools.generalization_tools.road.thin_road_network import ThinRoadNetwork
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import (
    FieldNames,
    NvdbAlias,
    MediumAlias,
)

CHANGES_BOOLEAN = False


@timing_decorator
def main():
    environment_setup.main()
    arcpy.env.referenceScale = 100000
    data_selection_and_validation()
    trim_road_details()
    adding_fields()
    merge_divided_roads()
    collapse_road_detail()
    separate_bridge_and_tunnel_from_surface_roads()
    create_intersections_for_on_surface_roads()
    simplify_road()
    thin_sti_and_forest_roads()
    thin_roads()
    thin_road_2()
    thin_road_3()
    smooth_line()


@timing_decorator
def data_selection_and_validation():
    selector = StudyAreaSelector(
        input_output_file_dict={
            input_roads.road_output_1: Road_N100.data_selection___nvdb_roads___n100_road.value,
            input_n100.Bane: Road_N100.data_selection___railroad___n100_road.value,
            input_n100.BegrensningsKurve: Road_N100.data_selection___begrensningskurve___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Oslo', 'Ringerike')",
        select_local=config.select_study_area,
    )

    selector.run()

    input_features_validation = {
        "nvdb_roads": Road_N100.data_selection___nvdb_roads___n100_road.value,
        "railroad": Road_N100.data_selection___railroad___n100_road.value,
        "begrensningskurve": Road_N100.data_selection___begrensningskurve___n100_road.value,
    }
    road_data_validation = GeometryValidator(
        input_features=input_features_validation,
        output_table_path=Road_N100.data_preparation___geometry_validation___n100_road.value,
    )
    road_data_validation.check_repair_sequence()


@timing_decorator
def trim_road_details():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___nvdb_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part___n100_road.value,
    )

    create_intersections = DissolveWithIntersections(
        input_line_feature=Road_N100.data_preparation___road_single_part___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections___n100_road.value,
        dissolve_field_list=FieldNames.road_input_fields.value,
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections.run()

    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.data_preparation___dissolved_intersections___n100_road.value,
        minimum_length="100 meters",
        recursive="RECURSIVE",
    )

    create_intersections_2 = DissolveWithIntersections(
        input_line_feature=Road_N100.data_preparation___dissolved_intersections___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root_2___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_2___n100_road.value,
        dissolve_field_list=FieldNames.road_input_fields.value,
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections_2.run()

    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_preparation___dissolved_intersections_2___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part_2___n100_road.value,
    )


@timing_decorator
def adding_fields():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_selection___begrensningskurve___n100_road.value,
        expression="""objtype IN ('Innsjøkant', 'InnsjøkantRegulert', 'Kystkontur', 'ElvBekkKant')""",
        output_name=Road_N100.data_preparation___water_feature_outline___n100_road.value,
    )

    tables_to_update = [
        Road_N100.data_preparation___water_feature_outline___n100_road.value,
        Road_N100.data_selection___railroad___n100_road.value,
    ]

    for table in tables_to_update:
        arcpy.management.AddField(
            in_table=table,
            field_name="hierarchy",
            field_type="SHORT",
        )
        arcpy.management.CalculateField(
            in_table=table,
            field="hierarchy",
            expression="0",
            expression_type="PYTHON3",
        )

    file_utilities.reclassify_value(
        input_table=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        target_field="VEGNUMMER",
        target_value="None",
        replace_value="-99",
        reference_field="VEGNUMMER",
    )

    arcpy.management.AddFields(
        in_table=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        field_description=FieldNames.road_added_fields.value,
    )


@timing_decorator
def merge_divided_roads():
    file_utilities.reclassify_value(
        input_table=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        target_field="merge_divided_id",
        target_value="-99",
        replace_value="0",
        reference_field="VEGNUMMER",
    )

    if CHANGES_BOOLEAN:
        define_character_field = f"""def Reclass(TYPEVEG):
            if TYPEVEG == 'rundkjøring':
                return 0
            elif TYPEVEG in 'kanalisertVeg':
                return 1
            elif TYPEVEG == 'enkelBilveg':
                return 1
            elif TYPEVEG == 'rampe':
                return 2
            else: 
                return 1
        """

        arcpy.management.CalculateField(
            in_table=Road_N100.data_preparation___road_single_part_2___n100_road.value,
            field="character",
            expression="Reclass(!TYPEVEG!)",
            expression_type="PYTHON3",
            code_block=define_character_field,
        )

    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        merge_field="merge_divided_id",
        merge_distance="150 Meters",
        out_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        out_displacement_features=Road_N100.data_preparation___merge_divided_roads_displacement_feature___n100_road.value,
        character_field="character",
    )


@timing_decorator
def collapse_road_detail():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        collapse_distance="60 Meters",
        output_feature_class=Road_N100.data_preparation___collapse_road_detail___n100_road.value,
    )


@timing_decorator
def separate_bridge_and_tunnel_from_surface_roads():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___collapse_road_detail___n100_road.value,
        expression=f"medium IN ('{MediumAlias.tunnel}', '{MediumAlias.bridge}')",
        output_name=Road_N100.data_preparation___road_bridge_and_tunnel_selection___n100_road.value,
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___collapse_road_detail___n100_road.value,
        expression=f"medium = '{MediumAlias.on_surface}'",
        output_name=Road_N100.data_preparation___road_on_surface_selection___n100_road.value,
    )


@timing_decorator
def create_intersections_for_on_surface_roads():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.data_preparation___road_on_surface_selection___n100_road.value,
        out_feature_class=Road_N100.data_preparation___on_surface_feature_to_line___n100_road.value,
    )

    file_utilities.deleting_added_field_from_feature_to_x(
        input_file_feature=Road_N100.data_preparation___on_surface_feature_to_line___n100_road.value,
        field_name_feature=Road_N100.data_preparation___road_on_surface_selection___n100_road.value,
    )

    arcpy.management.Append(
        inputs=Road_N100.data_preparation___road_bridge_and_tunnel_selection___n100_road.value,
        target=Road_N100.data_preparation___on_surface_feature_to_line___n100_road.value,
    )


@timing_decorator
def simplify_road():
    arcpy.cartography.SimplifyLine(
        in_features=Road_N100.data_preparation___on_surface_feature_to_line___n100_road.value,
        out_feature_class=Road_N100.data_preparation___simplified_road___n100_road.value,
        algorithm="POINT_REMOVE",
        tolerance="2 meters",
        error_option="RESOLVE_ERRORS",
    )


@timing_decorator
def thin_sti_and_forest_roads():
    # It seems from source code that having 2 as an else return is intended function if not revert to `otpional_sti_and_forest_hierarchy`
    sti_and_forest_hierarchy = f"""def Reclass(vegkategori):
        if vegkategori  in ('{NvdbAlias.europaveg}', '{NvdbAlias.riksveg}', '{NvdbAlias.fylkesveg}', '{NvdbAlias.kommunalveg}', '{NvdbAlias.privatveg}', '{NvdbAlias.skogsveg}'):
            return 0
        elif vegkategori in ('{NvdbAlias.traktorveg}', '{NvdbAlias.barmarksløype}'):
            return 1
        elif vegkategori in ('{NvdbAlias.sti_dnt}', '{NvdbAlias.sti_andre}'):
            return 2
        elif vegkategori == '{NvdbAlias.gang_og_sykkelveg}':
            return 3
        elif vegkategori == '{NvdbAlias.sti_umerket}':
            return 4
        else:
            return 2
        """
    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___simplified_road___n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegkategori!)",
        expression_type="PYTHON3",
        code_block=sti_and_forest_hierarchy,
    )
    road = "road"
    input_dict = {
        road: [
            "input",
            Road_N100.data_preparation___simplified_road___n100_road.value,
        ]
    }

    output_dict = {
        road: [
            "thin_road",
            Road_N100.data_preparation___thin_road_sti_output___n100_road.value,
        ]
    }
    thin_road_network_config = {
        "class": ThinRoadNetwork,
        "method": "run",
        "params": {
            "road_network_input": ("road", "input"),
            "road_network_output": ("road", "thin_road"),
            "root_file": Road_N100.data_preparation___thin_road_sti_root___n100_road.value,
            "minimum_length": "1500 meters",
            "invisibility_field_name": "invisibility",
            "hierarchy_field_name": "hierarchy",
            "special_selection_sql": "objtype IN ('Barmarksløype', 'Sti', 'Traktorveg', 'GangSykkelveg')",
        },
    }
    partition_thin_roads = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[thin_road_network_config],
        root_file_partition_iterator=Road_N100.data_preparation___thin_sti_partition_root___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___thin_sti_docu___n100_road.value,
        feature_count="6000",
    )
    partition_thin_roads.run()


@timing_decorator
def thin_roads():
    create_intersections = DissolveWithIntersections(
        input_line_feature=Road_N100.data_preparation___thin_road_sti_output___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root_3___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections.run()

    road_hierarchy = f"""def Reclass(vegklasse, vegkategori):
        if vegklasse in (0, 1, 2, 3):
            return 1
        elif vegklasse == 4:
            return 2
        elif vegklasse == 5:
            return 3
        elif vegklasse == 6:
            return 4
        elif vegklasse == 7 or vegkategori in ('{NvdbAlias.traktorveg}', '{NvdbAlias.barmarksløype}'):
            return 5
        elif vegklasse in (8 , 9):
            return 6
        elif vegklasse is None:
            return 6
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegklasse!, !vegkategori!)",
        expression_type="PYTHON3",
        code_block=road_hierarchy,
    )
    road = "road"
    input_dict = {
        road: [
            "input",
            Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        ]
    }

    output_dict = {
        road: [
            "thin_road",
            Road_N100.data_preparation___thin_road_output___n100_road.value,
        ]
    }
    thin_road_network_config = {
        "class": ThinRoadNetwork,
        "method": "run",
        "params": {
            "road_network_input": ("road", "input"),
            "road_network_output": ("road", "thin_road"),
            "root_file": Road_N100.data_preparation___thin_road_root___n100_road.value,
            "minimum_length": "2000 meters",
            "invisibility_field_name": "invisibility",
            "hierarchy_field_name": "hierarchy",
        },
    }
    partition_thin_roads = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[thin_road_network_config],
        root_file_partition_iterator=Road_N100.data_preparation___thin_road_partition_root___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___thin_road_docu___n100_road.value,
        feature_count="6000",
    )
    partition_thin_roads.run()


def thin_road_2():
    create_intersections = DissolveWithIntersections(
        input_line_feature=Road_N100.data_preparation___thin_road_output___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root_4___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_4___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections.run()

    road = "road"
    input_dict = {
        road: [
            "input",
            Road_N100.data_preparation___dissolved_intersections_4___n100_road.value,
        ]
    }

    output_dict = {
        road: [
            "thin_road",
            Road_N100.data_preparation___thin_road_output_2___n100_road.value,
        ]
    }
    thin_road_network_config = {
        "class": ThinRoadNetwork,
        "method": "run",
        "params": {
            "road_network_input": ("road", "input"),
            "road_network_output": ("road", "thin_road"),
            "root_file": Road_N100.data_preparation___thin_road_root_2___n100_road.value,
            "minimum_length": "2000 meters",
            "invisibility_field_name": "invisibility",
            "hierarchy_field_name": "hierarchy",
        },
    }
    partition_thin_roads = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[thin_road_network_config],
        root_file_partition_iterator=Road_N100.data_preparation___thin_road_partition_root_2___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___thin_road_docu_2___n100_road.value,
        feature_count="6000",
    )
    partition_thin_roads.run()


def thin_road_3():
    create_intersections = DissolveWithIntersections(
        input_line_feature=Road_N100.data_preparation___thin_road_output_2___n100_road.value,
        root_file=Road_N100.data_preparation___intersections_root_5___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_5___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    create_intersections.run()

    road = "road"
    input_dict = {
        road: [
            "input",
            Road_N100.data_preparation___dissolved_intersections_5___n100_road.value,
        ]
    }

    output_dict = {
        road: [
            "thin_road",
            Road_N100.data_preparation___thin_road_output_3___n100_road.value,
        ]
    }
    thin_road_network_config = {
        "class": ThinRoadNetwork,
        "method": "run",
        "params": {
            "road_network_input": ("road", "input"),
            "road_network_output": ("road", "thin_road"),
            "root_file": Road_N100.data_preparation___thin_road_root_3___n100_road.value,
            "minimum_length": "2000 meters",
            "invisibility_field_name": "invisibility",
            "hierarchy_field_name": "hierarchy",
        },
    }
    partition_thin_roads = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[thin_road_network_config],
        root_file_partition_iterator=Road_N100.data_preparation___thin_road_partition_root_3___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___thin_road_docu_3___n100_road.value,
        feature_count="6000",
    )
    partition_thin_roads.run()


@timing_decorator
def smooth_line():
    arcpy.cartography.SmoothLine(
        in_features=Road_N100.data_preparation___thin_road_output___n100_road.value,
        out_feature_class=Road_N100.data_preparation___smooth_road___n100_road.value,
        algorithm="PAEK",
        tolerance="300 meters",
        error_option="RESOLVE_ERRORS",
    )

    def resolve_road_conflict(
        input_line_layers: list[str], output_displacement_feature: str
    ):
        arcpy.env.referenceScale = "100000"

        arcpy.cartography.ResolveRoadConflicts(
            in_layers=[
                Road_N100.testing_file___roads_area_lyrx___n100_road.value,
                Road_N100.testing_file___railway_area_lyrx___n100_road.value,
                Road_N100.testing_file___begrensningskurve_water_area_lyrx___n100_road.value,
            ],
            hierarchy_field="hierarchy",
            out_displacement_features=Road_N100.testing_file___displacement_feature_after_resolve_road_conflict___n100_road.value,
        )


if __name__ == "__main__":
    main()
