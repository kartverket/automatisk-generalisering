# Importing packages
import arcpy

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
from custom_tools.general_tools import custom_arcpy
from custom_tools.general_tools.polygon_processor import PolygonProcessor
from custom_tools.general_tools.line_to_buffer_symbology import LineToBufferSymbology
from input_data.input_symbology import SymbologyN100
from constants.n100_constants import (
    N100_Symbology,
    N100_SQLResources,
    N100_Values,
    NvdbAlias,
)


@timing_decorator
def main():
    environment_setup.main()
    arcpy.env.referenceScale = 100000
    data_selection()
    table_management()
    dissolve_and_merge_divided_roads()
    # run_dissolve_partition()
    # thin_roadnetwork()


@timing_decorator
def data_selection():
    selector = StudyAreaSelector(
        input_output_file_dict={
            input_roads.elveg_and_sti: Road_N100.data_selection___nvdb_roads___n100_road.value,
        },
        selecting_file=input_n100.AdminFlate,
        selecting_sql_expression="navn IN ('Oslo', 'Ringerike')",
        select_local=config.select_study_area,
    )

    selector.run()


@timing_decorator
def table_management():
    reclassify_missing_vegnummer = """def Reclass(value):
        if value is None:
            return -99
        else:
            return value
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="VEGNUMMER",
        expression="Reclass(!VEGNUMMER!)",
        expression_type="PYTHON3",
        code_block=reclassify_missing_vegnummer,
    )

    arcpy.management.AddFields(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field_description=[
            ["invisibility", "SHORT"],
            ["hierarchy", "SHORT"],
            ["character", "SHORT"],
        ],
    )

    assign_hierarchy_to_nvdb_roads = f"""def Reclass(VEGKATEGORI):
        if VEGKATEGORI == '{NvdbAlias.europaveg}':
            return 1
        elif VEGKATEGORI in ['{NvdbAlias.riksveg}', '{NvdbAlias.fylkesveg}']:
            return 2
        elif VEGKATEGORI == '{NvdbAlias.kommunalveg}':
            return 3
        elif VEGKATEGORI == '{NvdbAlias.privatveg}':
            return 4
        elif VEGKATEGORI == '{NvdbAlias.skogsveg}':
            return 5
        
        else:
            return 5
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hierarchy_to_nvdb_roads,
    )

    reclassify_null_values = f"""def Reclass(VEGKATEGORI):
        if VEGKATEGORI is None:
            return 5
        else:
            return VEGKATEGORI
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="hierarchy",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=reclassify_null_values,
    )

    define_character_field = f"""def Reclass(TYPEVEG):
        if TYPEVEG == 'rundkjøring':
            return 0
        elif TYPEVEG in 'kanalisertVeg':
            return 1
        elif TYPEVEG == 'rampe':
            return 2
        else: 
            return 999
    """

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="character",
        expression="Reclass(!TYPEVEG!)",
        expression_type="PYTHON3",
        code_block=define_character_field,
    )

    arcpy.management.CalculateField(
        in_table=Road_N100.data_selection___nvdb_roads___n100_road.value,
        field="invisibility",
        expression=0,
    )


@timing_decorator
def dissolve_and_merge_divided_roads():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.data_selection___nvdb_roads___n100_road.value,
        out_feature_class=Road_N100.data_preparation___road_single_part___n100_road.value,
    )

    arcpy.analysis.PairwiseDissolve(
        in_features=Road_N100.data_preparation___road_single_part___n100_road.value,
        out_feature_class=Road_N100.data_preperation___dissolved_road_feature___n100_road.value,
        dissolve_field=[
            "OBJTYPE",
            "TYPEVEG",
            "MEDIUM",
            "VEGFASE",
            "VEGKATEGORI",
            "VEGNUMMER",
            "SUBTYPEKODE",
            "character",
        ],
        multi_part="SINGLE_PART",
    )

    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.data_preperation___dissolved_road_feature___n100_road.value,
        merge_field="VEGNUMMER",
        merge_distance="100 Meters",
        out_features=Road_N100.data_preperation___merge_divided_roads___n100_road.value,
        out_displacement_features=Road_N100.data_preperation___merge_divided_roads_displacement_feature___n100_road.value,
        character_field="character",
    )


@partition_io_decorator(
    input_param_names=["input_road"], output_param_names=["output_road"]
)
def dissolve_partition(input_road: str = None, output_road: str = None) -> None:
    work_output_file = f"{output_road}_work_out"
    work_displacement_file = f"{output_road}_work_displacement"
    arcpy.cartography.MergeDividedRoads(
        in_features=input_road,
        merge_field="VEGNUMMER",
        merge_distance="100 Meters",
        out_features=work_output_file,
        out_displacement_features=work_displacement_file,
        character_field="character",
    )

    arcpy.analysis.PairwiseDissolve(
        in_features=work_output_file,
        out_feature_class=output_road,
        dissolve_field=[
            "OBJTYPE",
            "TYPEVEG",
            "MEDIUM",
            "VEGFASE",
            "VEGKATEGORI",
            "VEGNUMMER",
            "partition_select",
            "SUBTYPEKODE",
            "MOTORVEGTYPE",
            "UTTEGNING",
        ],
        multi_part="SINGLE_PART",
    )


def run_dissolve_partition():
    road_lines = "road_lines"
    inputs = {
        road_lines: [
            "input",
            Road_N100.data_selection___nvdb_roads___n100_road.value,
        ],
    }

    outputs = {
        road_lines: [
            "dissolve_output",
            Road_N100.data_preperation___partition_dissolve_output___n100_road.value,
        ],
    }

    dissolve_partition_config = {
        "func": dissolve_partition,
        "params": {
            "input_road": (f"{road_lines}", "input"),
            "output_road": (f"{road_lines}", "dissolve_output"),
        },
    }

    dissolve_partition_partition_iteration = PartitionIterator(
        alias_path_data=inputs,
        alias_path_outputs=outputs,
        custom_functions=[dissolve_partition_config],
        root_file_partition_iterator=Road_N100.data_preperation___partition_dissolve_root___n100_road.value,
        dictionary_documentation_path=Road_N100.data_preparation___json_documentation___n100_road.value,
        feature_count="4000",
    )

    dissolve_partition_partition_iteration.run()


@timing_decorator
def thin_roadnetwork():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.data_preperation___merge_divided_roads___n100_road.value,
        minimum_length="2000 Meters",
        invisibility_field="invisibility",
        hierarchy_field="hierarchy",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.first_generalization____merge_divided_roads_features___n100_road.value,
        expression="invisibility = 0",
        output_name=Road_N100.data_selection___thin_road_network_selection___n100_road.value,
        selection_type=custom_arcpy.SelectionType.NEW_SELECTION,
    )


if __name__ == "__main__":
    main()
