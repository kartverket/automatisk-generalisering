# Importing packages
import arcpy

# Importing custom input files modules
from input_data import input_n100
from input_data import input_roads

from composition_configs import core_config, logic_config, type_defs

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
from custom_tools.generalization_tools.road.remove_road_triangles import (
    generalize_road_triangles,
)
from custom_tools.generalization_tools.road.resolve_road_conflicts import (
    ResolveRoadConflicts,
)
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import (
    FieldNames,
    NvdbAlias,
)
from generalization.n100.road.dam import generalize_dam
from generalization.n100.road.major_road_crossings import (
    categories_major_road_crossings,
)
from generalization.n100.road.roundabouts import generalize_roundabouts
from generalization.n100.road.vegsperring import remove_roadblock
from generalization.n100.road.ramps_point import ramp_points
from generalization.n100.road.ramps_point import MovePointsToCrossings
from generalization.n100.road.resolve_road_conflict_preparation import (
    split_polyline_featureclass,
    remove_road_points_in_water,
    run_dissolve_with_intersections,
)
from file_manager import WorkFileManager
from file_manager.n100.file_manager_buildings import Building_N100

MERGE_DIVIDED_ROADS_ALTERATIVE = False

AREA_SELECTOR = "navn IN ('Ringerike')"
SCALE = "n100"


@timing_decorator
def main():
    environment_setup.main()
    arcpy.env.referenceScale = 100000
    data_selection_and_validation(AREA_SELECTOR)
    categories_major_road_crossings()
    generalize_roundabouts()
    remove_roadblock()
    trim_road_details()
    ramp_points()
    admin_boarder()
    adding_fields()
    collapse_road_detail()
    simplify_road()
    """
    generalize_road_triangles(scale="n100")
    return
    # """
    thin_roads()
    thin_sti_and_forest_roads()
    merge_divided_roads()
    smooth_line()
    generalize_road_triangles(SCALE)
    pre_resolve_road_conflicts(AREA_SELECTOR)
    resolve_road_conflicts()
    generalize_dam()
    final_output()
    final_ramp_points()
    with open(Building_N100.total_workfile_manager_files__n100.value, "w") as f:
        f.write(
            f"Total amount of work files created: "
            f"{WorkFileManager._build_file_counter}"
        )


SEARCH_DISTANCE = 5000
OBJECT_LIMIT = 100_000


@timing_decorator
def data_selection_and_validation(area_selection: str):
    """
    plot_area = "navn IN ('Asker', 'Bærum', 'Drammen', 'Frogn', 'Hole', 'Holmestrand', 'Horten', 'Jevnaker', 'Kongsberg', 'Larvik', 'Lier', 'Lunner', 'Modum', 'Nesodden', 'Oslo', 'Ringerike', 'Tønsberg', 'Øvre Eiker')"
    ferry_admin_test = "navn IN ('Hole')"
    small_plot_area = "navn IN ('Oslo', 'Ringerike')"
    smallest_plot_area = "navn IN ('Ringerike')"
    presentation_area = "navn IN ('Asker', 'Bærum', 'Oslo', 'Enebakk', 'Nittedal', 'Nordre Follo', 'Hole', 'Nesodden', 'Lørenskog', 'Sandnes', 'Stavanger', 'Gjesdal', 'Sola', 'Klepp', 'Strand', 'Time', 'Randaberg')"
    """

    selector = StudyAreaSelector(
        input_output_file_dict={
            input_roads.road_output_1: Road_N100.data_selection___nvdb_roads___n100_road.value,
            input_roads.vegsperring: Road_N100.data_selection___vegsperring___n100_road.value,
            input_n100.Bane: Road_N100.data_selection___railroad___n100_road.value,
            input_n100.BegrensningsKurve: Road_N100.data_selection___begrensningskurve___n100_road.value,
            input_n100.AdminGrense: Road_N100.data_selection___admin_boundary___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression=area_selection,
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


def run_thin_roads(
    input_feature: str,
    partition_root_file: str,
    output_feature: str,
    docu_path: type_defs.SubdirectoryPath,
    min_length_m: int,
    feature_count,
    special_selection_sql=None,
):
    road = "road"
    processed_road = "processed_road"

    thin_road_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=road,
                path=input_feature,
            )
        ]
    )

    thin_road_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=road,
                tag=processed_road,
                path=output_feature,
            )
        ]
    )

    thin_road_io_config = core_config.PartitionIOConfig(
        input_config=thin_road_input_config,
        output_config=thin_road_output_config,
        documentation_directory=docu_path,
    )

    thin_roads_init_config = logic_config.ThinRoadNetworkKwargs(
        input_road_line=core_config.InjectIO(
            object=road,
            tag="input",
        ),
        output_road_line=core_config.InjectIO(
            object=road,
            tag=processed_road,
        ),
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=partition_root_file
        ),
        minimum_length=min_length_m,
        invisibility_field_name="invisibility",
        hierarchy_field_name="hierarchy",
        special_selection_sql=special_selection_sql,
    )

    thin_road_class_config = core_config.ClassMethodEntryConfig(
        class_=ThinRoadNetwork,
        method=ThinRoadNetwork.run,
        init_params=thin_roads_init_config,
    )

    thin_road_method_config = core_config.MethodEntriesConfig(
        entries=[thin_road_class_config]
    )

    partition_thin_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=feature_count,
        context_radius_meters=SEARCH_DISTANCE,
    )

    partition_thin_roads = PartitionIterator(
        partition_io_config=thin_road_io_config,
        partition_method_inject_config=thin_road_method_config,
        partition_iterator_run_config=partition_thin_run_config,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=partition_root_file
        ),
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
        in_features=Road_N100.vegsperring__veg_uten_bom__n100_road.value,
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
        expression="OBJTYPE IN ('Riksgrense', 'AvtaltAvgrensningslinje')",
        output_name=Road_N100.data_preparation___country_boarder___n100_road.value,
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.ramps__generalized_ramps__n100_road.value,
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
    road = "road"
    processed_road = "processed_road"

    collapse_road_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=road,
                path=Road_N100.ramps__generalized_ramps__n100_road.value,
            )
        ]
    )

    collapse_road_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=road,
                tag=processed_road,
                path=Road_N100.data_preparation___collapse_road_detail___n100_road.value,
            )
        ]
    )

    collapse_partition_io_config = core_config.PartitionIOConfig(
        input_config=collapse_road_input_config,
        output_config=collapse_road_output_config,
        documentation_directory=Road_N100.collapse_road_docu___n100_road.value,
    )

    collapse_road_func_config = core_config.FuncMethodEntryConfig(
        func=collapse_road,
        params=logic_config.CollapseRoadDetailsKwargs(
            input_road_line=core_config.InjectIO(object=road, tag="input"),
            output_road_line=core_config.InjectIO(object=road, tag=processed_road),
            merge_distnace_m=60,
        ),
    )

    collapse_road_method_config = core_config.MethodEntriesConfig(
        entries=[collapse_road_func_config]
    )

    collapse_partition_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=OBJECT_LIMIT,
        context_radius_meters=SEARCH_DISTANCE,
    )

    partition_collapse_road_detail = PartitionIterator(
        partition_io_config=collapse_partition_io_config,
        partition_method_inject_config=collapse_road_method_config,
        partition_iterator_run_config=collapse_partition_run_config,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Road_N100.data_preparation___collapse_root___n100_road.value
        ),
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

    road_hierarchy = """def Reclass(typeveg, vegkategori, vegklasse, er_kryssningspunkt):
        if typeveg == 'bilferje':
            return 0
        
        if vegklasse in (0, 1, 2, 3, 4):
            klasse = 1
        elif vegklasse == 5:
            klasse = 2
        elif vegklasse == 6:
            klasse = 3
        elif vegklasse == 7:
            klasse = 4
        else:
            klasse = 5
        
        if er_kryssningspunkt == 1:
            if vegkategori in ('E', 'R', 'F'):
                kryss = -3
            elif vegkategori in ('K'):
                kryss = -2
            else:
                kryss = -1
        else:
            kryss = 0
        
        hierarki = klasse + kryss
        
        if hierarki < 0:
            return 0
        elif hierarki > 5:
            return 5
        return hierarki
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_preparation___dissolved_intersections_3___n100_road.value,
        field="hierarchy",
        expression="Reclass(!typeveg!, !vegkategori!, !vegklasse!, !er_kryssningspunkt!)",
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
        docu_path=Road_N100.thin_road_docu___n100_road.value,
        min_length_m=1400,
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
        docu_path=Road_N100.thin_sti_docu___n100_road.value,
        min_length_m=1800,
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


@timing_decorator
def pre_resolve_road_conflicts(area_selection: str):
    remove_road_points_in_water(
        road_fc=Road_N100.road_triangles_output.value,
        output_fc=Road_N100.road_cleaning_output__n100_road.value,
        area_selection=area_selection,
    )
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___railroad___n100_road.value,
        out_feature_class=Road_N100.data_preparation___railroad_single_part___n100_road.value,
    )

    # Takes care of long geometries for water features
    split_polyline_featureclass(
        input_fc=Road_N100.data_preparation___water_feature_outline___n100_road.value,
        dissolve_fc=Road_N100.data_preparation__water_feature_outline_dissolved__n100_road.value,
        split_fc=Road_N100.data_preparation__water_feature_outline_split_xm__n100_road.value,
        output_fc=Road_N100.data_preparation___water_feature_outline_single_part___n100_road.value,
    )

    road_data_validation = GeometryValidator(
        input_features={
            "roads": Road_N100.road_cleaning_output__n100_road.value,
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
        in_table=Road_N100.road_cleaning_output__n100_road.value,
        field="hierarchy",
        expression="Reclass(!vegklasse!, !typeveg!)",
        expression_type="PYTHON3",
        code_block=road_hierarchy,
    )

    calculate_boarder_road_hierarchy(
        input_road=Road_N100.road_cleaning_output__n100_road.value,
        root_file=Road_N100.data_preparation___root_calculate_boarder_hierarchy_2___n100_road.value,
        input_boarder_dagnle=Road_N100.data_preparation___boarder_road_dangle___n100_road.value,
        output_road=Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value,
    )

    # --- Aliases ---------------------------------------------------------------
    road = "road"
    railroad = "railroad"
    begrensningskurve = "begrensningskurve"
    displacement = "displacement"

    # --- Partition IO (inputs/outputs) ----------------------------------------
    rrc_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(
                object=road,
                path=Road_N100.data_preparation___calculated_boarder_hierarchy_2___n100_road.value,
            ),
            core_config.InputEntry.context_input(
                object=railroad,
                path=Road_N100.data_preparation___railroad_single_part___n100_road.value,
            ),
            core_config.InputEntry.context_input(
                object=begrensningskurve,
                path=Road_N100.data_preparation___water_feature_outline_single_part___n100_road.value,
            ),
        ]
    )

    rrc_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=road,
                tag="resolve_road_conflicts",
                path=Road_N100.data_preparation___resolve_road_conflicts___n100_road.value,
            ),
            core_config.OutputEntry.vector_output(
                object=displacement,
                tag="displacement_feature",
                path=Road_N100.data_preparation___resolve_road_conflicts_displacement_feature___n100_road.value,
            ),
        ]
    )

    rrc_io_config = core_config.PartitionIOConfig(
        input_config=rrc_input_config,
        output_config=rrc_output_config,
        documentation_directory=Road_N100.resolve_road_docu___n100_road.value,
    )

    # --- Symbology specs -------------------------------------------------------
    rrc_specs = [
        logic_config.SymbologyLayerSpec(
            unique_name=road,
            input_feature=core_config.InjectIO(object=road, tag="input"),
            input_lyrx=SymbologyN100.samferdsel.value,
            grouped_lyrx=True,
            target_layer_name="N100_Samferdsel_senterlinje_veg_bru_L2",
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=railroad,
            input_feature=core_config.InjectIO(object=railroad, tag="input"),
            input_lyrx=SymbologyN100.samferdsel.value,
            grouped_lyrx=True,
            target_layer_name="N100_Samferdsel_senterlinje_jernbane_terreng_sort_maske",
        ),
        logic_config.SymbologyLayerSpec(
            unique_name=begrensningskurve,
            input_feature=core_config.InjectIO(object=begrensningskurve, tag="input"),
            input_lyrx=SymbologyN100.begrensnings_kurve_line.value,
            grouped_lyrx=False,
        ),
    ]

    # --- Class init config (new RRC init kwargs) -------------------------------
    rrc_init = logic_config.RrcInitKwargs(
        input_data_structure=rrc_specs,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Road_N100.data_preparation___resolve_road_root___n100_road.value
        ),
        primary_road_unique_name=road,
        output_road_feature=core_config.InjectIO(
            object=road, tag="resolve_road_conflicts"
        ),
        output_displacement_feature=core_config.InjectIO(
            object=displacement, tag="displacement_feature"
        ),
        map_scale="100000",
        hierarchy_field="hierarchy",
    )

    # --- Method wiring ---------------------------------------------------------
    rrc_method = core_config.ClassMethodEntryConfig(
        class_=ResolveRoadConflicts,
        method=ResolveRoadConflicts.run,
        init_params=rrc_init,
    )

    rrc_methods = core_config.MethodEntriesConfig(entries=[rrc_method])

    # --- Partition run + WFM for iterator -------------------------------------
    rrc_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=100_000,
        context_radius_meters=500,
        partition_method=core_config.PartitionMethod.VERTICES,
    )

    rrc_partition_wfm = core_config.WorkFileConfig(
        root_file=Road_N100.data_preparation___resolve_road_partition_root___n100_road.value,
        keep_files=True,
    )

    # --- Execute ---------------------------------------------------------------
    partition_resolve_road_conflicts = PartitionIterator(
        partition_io_config=rrc_io_config,
        partition_method_inject_config=rrc_methods,
        partition_iterator_run_config=rrc_run_config,
        work_file_manager_config=rrc_partition_wfm,
    )

    partition_resolve_road_conflicts.run()


def final_output():

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.dam__cleaned_roads__n100_road.value,
        expression="typeveg IN ('bilferje', 'passasjerferje')",
        output_name=Road_N100.data_preparation___road_final_output___n100_road.value,
        inverted=True,
    )


def final_ramp_points():
    f = MovePointsToCrossings(
        Road_N100.data_preparation___road_final_output___n100_road.value,
        Road_N100.ramps__ramp_points_moved__n100_road.value,
        Road_N100.ramps__ramp_points_moved_2__n100_road.value,
        delete_points_not_on_crossings=True,
        with_ramps=False,
    )
    f.run()


if __name__ == "__main__":
    main()
