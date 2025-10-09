# Importing packages
from types import SimpleNamespace

import arcpy
import os
import textwrap


# Importing custom input files modules
from input_data import input_n50
from input_data import input_n100
from input_data import input_other
from input_data import input_elveg
from input_data import input_roads

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
import config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from custom_tools.general_tools.study_area_selector import StudyAreaSelector
from custom_tools.general_tools.geometry_tools import GeometryValidator
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools import file_utilities
from custom_tools.generalization_tools.road.thin_road_network import ThinRoadNetwork
from custom_tools.generalization_tools.road.collapse_road import collapse_road
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from custom_tools.generalization_tools.road.resolve_road_conflicts import (
    ResolveRoadConflicts,
)
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import (
    FieldNames,
    NvdbAlias,
    MediumAlias,
)
from generalization.n100.road.dam import main as dam

MERGE_DIVIDED_ROADS_ALTERATIVE = False


@timing_decorator
def main():
    environment_setup.main()
    arcpy.env.referenceScale = 100000
    data_selection_and_validation()
    trim_road_details()
    admin_boarder()
    adding_fields()
    collapse_road_detail()
    simplify_road()
    thin_roads()
    thin_sti_and_forest_roads()
    merge_divided_roads()
    smooth_line()
    pre_resolve_road_conflicts()
    resolve_road_conflicts()
    dam()
    final_output()


SEARCH_DISTANCE = "5000 Meters"
OBJECT_LIMIT = 100_000


@timing_decorator
def data_selection_and_validation():
    plot_area = "navn IN ('Asker', 'Bærum', 'Drammen', 'Frogn', 'Hole', 'Holmestrand', 'Horten', 'Jevnaker', 'Kongsberg', 'Larvik', 'Lier', 'Lunner', 'Modum', 'Nesodden', 'Oslo', 'Ringerike', 'Tønsberg', 'Øvre Eiker')"
    ferry_admin_test = "navn IN ('Ringerike', 'Tønsberg')"
    small_plot_area = "navn IN ('Oslo', 'Ringerike')"
    presentation_area = "navn IN ('Asker', 'Bærum', 'Oslo', 'Enebakk', 'Nittedal', 'Nordre Follo', 'Hole', 'Nesodden', 'Lørenskog', 'Sandnes', 'Stavanger', 'Gjesdal', 'Sola', 'Klepp', 'Strand', 'Time', 'Randaberg')"

    selector = StudyAreaSelector(
        input_output_file_dict={
            input_roads.road_output_1: Road_N100.data_selection___nvdb_roads___n100_road.value,
            input_n100.Bane: Road_N100.data_selection___railroad___n100_road.value,
            input_n100.BegrensningsKurve: Road_N100.data_selection___begrensningskurve___n100_road.value,
            input_n100.AdminGrense: Road_N100.data_selection___admin_boundary___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression=ferry_admin_test,
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


# Helper Functions
def run_dissolve_with_intersections(
    input_line_feature,
    output_processed_feature,
    dissolve_field_list,
):
    dissolve_obj = DissolveWithIntersections(
        input_line_feature=input_line_feature,
        root_file=Road_N100.data_preparation___intersections_root___n100_road.value,
        output_processed_feature=output_processed_feature,
        dissolve_field_list=dissolve_field_list,
        list_of_sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    dissolve_obj.run()


def run_thin_roads(
    input_feature,
    partition_root_file,
    output_feature,
    docu_path,
    min_length,
    feature_count,
    special_selection_sql=None,
):
    alias = "road"
    input_dict = {alias: ["input", input_feature]}
    output_dict = {alias: ["thin_road", output_feature]}
    thin_road_network_config = {
        "class": ThinRoadNetwork,
        "method": "run",
        "params": {
            "road_network_input": (alias, "input"),
            "road_network_output": (alias, "thin_road"),
            "root_file": Road_N100.data_preparation___thin_road_root___n100_road.value,
            "minimum_length": min_length,
            "invisibility_field_name": "invisibility",
            "partition_field_name": "",
            "hierarchy_field_name": "hierarchy",
            "special_selection_sql": special_selection_sql,
        },
    }
    partition_thin_roads = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[thin_road_network_config],
        root_file_partition_iterator=partition_root_file,
        dictionary_documentation_path=docu_path,
        feature_count=feature_count,
        search_distance=SEARCH_DISTANCE,
    )
    partition_thin_roads.run()


def calculate_boarder_road_hierarchy(
    input_road: str,
    root_file: str,
    input_boarder_dagnle: str,
    output_road: str,
):
    boarder_intersecting_roads = f"{root_file}_1"
    boarder_intersecting_roads_inverted = f"{root_file}_2"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_road,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=input_boarder_dagnle,
        output_name=boarder_intersecting_roads,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=input_road,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=input_boarder_dagnle,
        output_name=boarder_intersecting_roads_inverted,
        inverted=True,
    )

    arcpy.management.CalculateField(
        in_table=boarder_intersecting_roads,
        field="hierarchy",
        expression="0",
        expression_type="PYTHON3",
    )

    arcpy.management.Merge(
        inputs=[
            boarder_intersecting_roads,
            boarder_intersecting_roads_inverted,
        ],
        output=output_road,
    )


@timing_decorator
def trim_road_details():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___nvdb_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part___n100_road.value,
    )

    run_dissolve_with_intersections(
        input_line_feature=Road_N100.data_preparation___road_single_part___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections___n100_road.value,
        dissolve_field_list=FieldNames.road_input_fields.value,
    )

    run_dissolve_with_intersections(
        input_line_feature=Road_N100.data_preparation___dissolved_intersections___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_2___n100_road.value,
        dissolve_field_list=FieldNames.road_input_fields.value,
    )

    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_preparation___dissolved_intersections_2___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part_2___n100_road.value,
    )


@timing_decorator
def admin_boarder():

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.data_selection___admin_boundary___n100_road.value,
        expression="OBJTYPE = 'Riksgrense'",
        output_name=Road_N100.data_preparation___country_boarder___n100_road.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.ramps__generalized_ramps__n100_road.value,  # Road_N100.data_preparation___road_single_part_2___n100_road.value,
        expression=f"vegkategori  in ('{NvdbAlias.europaveg}', '{NvdbAlias.riksveg}', '{NvdbAlias.fylkesveg}', '{NvdbAlias.kommunalveg}', '{NvdbAlias.privatveg}', '{NvdbAlias.skogsveg}')",
        output_name=Road_N100.data_preparation___car_raod___n100_road.value,
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=Road_N100.data_preparation___car_raod___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_dangle___n100_road.value,
        point_location="DANGLE",
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=Road_N100.data_preparation___road_dangle___n100_road.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
        search_distance="1 Meters",
        select_features=Road_N100.data_preparation___country_boarder___n100_road.value,
        output_name=Road_N100.data_preparation___boarder_road_dangle___n100_road.value,
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
        input_table=Road_N100.ramps__generalized_ramps__n100_road.value,
        target_field="VEGNUMMER",
        target_value="None",
        replace_value="-99",
        reference_field="VEGNUMMER",
    )

    arcpy.management.AddFields(
        in_table=Road_N100.ramps__generalized_ramps__n100_road.value,
        field_description=FieldNames.road_added_fields.value,
    )


@timing_decorator
def collapse_road_detail():
    input_dict = {
        "roads": (
            "input",
            Road_N100.ramps__generalized_ramps__n100_road.value,
        )
    }

    output_dict = {
        "roads": (
            "road_detail",
            Road_N100.data_preparation___collapse_road_detail___n100_road.value,
        )
    }

    collapse_road_detail_config = {
        "func": collapse_road,
        "params": {
            "road_network_input": ("roads", "input"),
            "road_network_output": ("roads", "road_detail"),
            "merge_distance": "60 Meters",
        },
    }

    partition_collapse_road_detail = PartitionIterator(
        alias_path_data=input_dict,
        alias_path_outputs=output_dict,
        custom_functions=[collapse_road_detail_config],
        root_file_partition_iterator=Road_N100.data_preparation___thin_road_partition_root___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___thin_road_docu___n100_road.value,
        feature_count=OBJECT_LIMIT,
        run_partition_optimization=True,
        search_distance=SEARCH_DISTANCE,
    )
    partition_collapse_road_detail.run()


@timing_decorator
def simplify_road():
    arcpy.cartography.SimplifyLine(
        in_features=Road_N100.data_preparation___collapse_road_detail___n100_road.value,
        out_feature_class=Road_N100.data_preparation___simplified_road___n100_road.value,
        algorithm="POINT_REMOVE",
        tolerance="2 meters",
        error_option="RESOLVE_ERRORS",
    )


@timing_decorator
def thin_roads():
    run_dissolve_with_intersections(
        input_line_feature=Road_N100.data_preparation___simplified_road___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
    )

    road_data_validation = GeometryValidator(
        input_features={
            "roads": Road_N100.data_preparation___dissolved_intersections_3___n100_road.value
        },
        output_table_path=f"{Road_N100.data_preparation___geometry_validation___n100_road.value}_3",
    )
    road_data_validation.check_repair_sequence()

    road_hierarchy = """def Reclass(vegklasse, typeveg, motorvegtype):
        if motorvegtype is not None and motorvegtype != 'Udefinert':
            return 0
        elif typeveg in ('bilferje', 'rampe'):
            return 0
        elif vegklasse in (0, 1, 2, 3, 4):
            return 1
        elif vegklasse == 5:
            return 2
        elif vegklasse == 6:
            return 3
        elif vegklasse == 7:
            return 4
        else:
            return 5
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegklasse!, !typeveg!, !motorvegtype!)",
        expression_type="PYTHON3",
        code_block=road_hierarchy,
    )

    calculate_boarder_road_hierarchy(
        input_road=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        root_file=Road_N100.data_preparation___root_calculate_boarder_hierarchy___n100_road.value,
        input_boarder_dagnle=Road_N100.data_preparation___boarder_road_dangle___n100_road.value,
        output_road=Road_N100.data_preparation___calculated_boarder_hierarchy___n100_road.value,
    )

    run_thin_roads(
        input_feature=Road_N100.data_preparation___calculated_boarder_hierarchy___n100_road.value,
        partition_root_file=Road_N100.data_preparation___thin_road_partition_root___n100_road.value,
        output_feature=Road_N100.data_preparation___thin_road_output___n100_road.value,
        docu_path=Road_N100.data_preparation___thin_road_docu___n100_road.value,
        min_length="1400 meters",
        feature_count=OBJECT_LIMIT,
    )


@timing_decorator
def thin_sti_and_forest_roads():
    run_dissolve_with_intersections(
        input_line_feature=Road_N100.data_preparation___thin_road_output___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_4___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
    )
    road_data_validation = GeometryValidator(
        input_features={
            "roads": Road_N100.data_preparation___dissolved_intersections_4___n100_road.value
        },
        output_table_path=f"{Road_N100.data_preparation___geometry_validation___n100_road.value}_2",
    )
    road_data_validation.check_repair_sequence()

    # It seems from source code that having 2 as an else return is intended function if not revert to `otpional_sti_and_forest_hierarchy`
    sti_and_forest_hierarchy = f"""def Reclass(vegkategori, typeveg):
        if vegkategori  in ('{NvdbAlias.europaveg}', '{NvdbAlias.riksveg}', '{NvdbAlias.fylkesveg}', '{NvdbAlias.kommunalveg}', '{NvdbAlias.privatveg}', '{NvdbAlias.skogsveg}'):
            return 0
        elif typeveg == 'bilferje':
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
            return 4
        """
    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___dissolved_intersections_4___n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegkategori!, !typeveg!)",
        expression_type="PYTHON3",
        code_block=sti_and_forest_hierarchy,
    )

    run_thin_roads(
        input_feature=Road_N100.data_preparation___dissolved_intersections_4___n100_road.value,
        partition_root_file=Road_N100.data_preparation___thin_sti_partition_root___n100_road.value,
        output_feature=Road_N100.data_preparation___thin_road_sti_output___n100_road.value,
        docu_path=Road_N100.data_preparation___thin_sti_docu___n100_road.value,
        min_length="1800 meters",
        feature_count=OBJECT_LIMIT,
    )


@timing_decorator
def merge_divided_roads():
    file_utilities.reclassify_value(
        input_table=Road_N100.data_preparation___thin_road_sti_output___n100_road.value,
        target_field="merge_divided_id",
        target_value="-99",
        replace_value="0",
        reference_field="VEGNUMMER",
    )

    if MERGE_DIVIDED_ROADS_ALTERATIVE:
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
            in_table=Road_N100.ramps__generalized_ramps__n100_road.value,
            field="character",
            expression="Reclass(!TYPEVEG!)",
            expression_type="PYTHON3",
            code_block=define_character_field,
        )

    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.data_preparation___thin_road_sti_output___n100_road.value,
        merge_field="merge_divided_id",
        merge_distance="150 Meters",
        out_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        out_displacement_features=Road_N100.data_preparation___merge_divided_roads_displacement_feature___n100_road.value,
        character_field="character",
    )


@timing_decorator
def smooth_line():

    # custom_arcpy.select_attribute_and_make_permanent_feature(
    #     input_layer=Road_N100.data_selection___admin_boundary___n100_road.value,
    #     expression="OBJTYPE = 'Riksgrense'",
    #     output_name=Road_N100.data_preparation___country_boarder___n100_road.value,
    # )
    arcpy.cartography.SmoothLine(
        in_features=Road_N100.data_preparation___merge_divided_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___smooth_road___n100_road.value,
        algorithm="PAEK",
        tolerance="300 meters",
        error_option="RESOLVE_ERRORS",
        in_barriers=[
            Road_N100.data_preparation___water_feature_outline___n100_road.value,
            Road_N100.data_selection___railroad___n100_road.value,
            Road_N100.data_preparation___country_boarder___n100_road.value,
        ],
    )


def pre_resolve_road_conflicts():
    run_dissolve_with_intersections(
        input_line_feature=Road_N100.data_preparation___smooth_road___n100_road.value,
        output_processed_feature=Road_N100.data_preparation___dissolved_intersections_5___n100_road.value,
        dissolve_field_list=FieldNames.road_all_fields(),
    )
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_preparation___dissolved_intersections_5___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part_3___n100_road.value,
    )
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___railroad___n100_road.value,
        out_feature_class=Road_N100.data_preparation___railroad_single_part___n100_road.value,
    )
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_preparation___water_feature_outline___n100_road.value,
        out_feature_class=Road_N100.data_preparation___water_feature_outline_single_part___n100_road.value,
    )

    road_data_validation = GeometryValidator(
        input_features={
            "roads": Road_N100.data_preparation___road_single_part_3___n100_road.value,
            "railroad": Road_N100.data_preparation___railroad_single_part___n100_road.value,
            "begrensningskurve": Road_N100.data_preparation___water_feature_outline_single_part___n100_road.value,
        },
        output_table_path=f"{Road_N100.data_preparation___geometry_validation___n100_road.value}_6",
    )
    road_data_validation.check_repair_sequence()


def resolve_road_conflicts():

    road_hierarchy = """def Reclass(vegklasse, typeveg):
        if typeveg in ('bilferje', 'ramps'):
            return 0
        elif vegklasse in (0, 1, 2, 3, 4):
            return 1
        elif vegklasse == 5:
            return 2
        elif vegklasse == 6:
            return 3
        elif vegklasse == 7:
            return 4
        else:
            return 5
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___road_single_part_3___n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegklasse!, !typeveg!)",
        expression_type="PYTHON3",
        code_block=road_hierarchy,
    )

    calculate_boarder_road_hierarchy(
        input_road=Road_N100.data_preparation___road_single_part_3___n100_road.value,
        root_file=Road_N100.data_preparation___root_calculate_boarder_hierarchy_2___n100_road.value,
        input_boarder_dagnle=Road_N100.data_preparation___boarder_road_dangle___n100_road.value,
        output_road=Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value,
    )

    road = "road"
    railroad = "railroad"
    begrensningskurve = "begrensningskurve"
    displacement = "displacement"

    inputs = {
        road: [
            "input",
            Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value,
        ],
        railroad: [
            "context",
            Road_N100.data_preparation___railroad_single_part___n100_road.value,
        ],
        begrensningskurve: [
            "context",
            Road_N100.data_preparation___water_feature_outline_single_part___n100_road.value,
        ],
    }

    outputs = {
        road: [
            "resolve_road_conflicts",
            Road_N100.data_preparation___resolve_road_conflicts___n100_road.value,
        ],
        displacement: [
            "displacement_feature",
            Road_N100.data_preparation___resolve_road_conflicts_displacement_feature___n100_road.value,
        ],
    }

    input_data_structure = [
        {
            "unique_alias": road,
            "input_line_feature": (road, "input"),
            "input_lyrx_feature": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_veg_bru_L2",
        },
        {
            "unique_alias": railroad,
            "input_line_feature": (railroad, "context"),
            "input_lyrx_feature": config.symbology_samferdsel,
            "grouped_lyrx": True,
            "target_layer_name": "N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        },
        {
            "unique_alias": begrensningskurve,
            "input_line_feature": (begrensningskurve, "context"),
            "input_lyrx_feature": SymbologyN100.begrensnings_kurve_line.value,
            "grouped_lyrx": False,
            "target_layer_name": None,
        },
    ]

    resolve_road_conflicts_config = {
        "class": ResolveRoadConflicts,
        "method": "run",
        "params": {
            "input_list_of_dicts_data_structure": input_data_structure,
            "root_file": Road_N100.data_preparation___resolve_road_root___n100_road.value,
            "output_road_feature": (road, "resolve_road_conflicts"),
            "output_displacement_feature": (
                displacement,
                "displacement_feature",
            ),
            "map_scale": "100000",
        },
    }

    partition_resolve_road_conflicts = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[resolve_road_conflicts_config],
        root_file_partition_iterator=Road_N100.data_preparation___resolve_road_partition_root___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___resolve_road_docu___n100_road.value,
        feature_count=25_000,
        run_partition_optimization=True,
        search_distance="500 Meters",
    )
    partition_resolve_road_conflicts.run()


def final_output():

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.dam__cleaned_roads__n100_road.value,
        expression="typeveg IN ('bilferje', 'passasjerferje')",
        output_name=Road_N100.data_preparation___road_final_output___n100_road.value,
        inverted=True,
    )


if __name__ == "__main__":
    main()
