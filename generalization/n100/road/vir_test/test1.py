# har tester ViR
import arcpy

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy

# from input_data import input_elveg
# from input_data import input_veg
from input_data import input_roads

# from custom_tools.decorators import timing_decorator


def main():
    environment_setup.main()
    komm()
    komm_buff()
    roads_komm()
    roads_komm_single()
    adding_fields_to_roads_komm_single()
    roads_komm_diss()
    remove()
    merge1()
    thin_sti()
    komm_sti_thin1()
    komm_bilveg()
    komm_copy()
    komm_thin2()
    thin_bilveger()
    komm_thin3()
    komm_crd1()
    veg100_oslo()


def komm():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.AdminFlate,
        expression="NAVN='Oslo'",
        output_name=Road_N100.test1___komm___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def komm_buff():
    arcpy.analysis.PairwiseBuffer(
        in_features=Road_N100.test1___komm___n100_road.value,
        out_feature_class=Road_N100.test1___komm_buff___n100_road.value,
        buffer_distance_or_field="1000 meters",
    )


def roads_komm():
    arcpy.analysis.Clip(
        in_features=input_roads.elveg_and_sti_oslo,
        clip_features=Road_N100.test1___komm_buff___n100_road.value,
        out_feature_class=Road_N100.test1___roads_komm___n100_road.value,
    )


def roads_komm_single():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___roads_komm___n100_road.value,
        out_feature_class=Road_N100.test1___roads_komm_single___n100_road.value,
    )


def adding_fields_to_roads_komm_single() -> object:
    arcpy.management.AddFields(
        in_table=Road_N100.test1___roads_komm_single___n100_road.value,
        field_description=[
            ["inv_sti", "SHORT"],
            ["hiesti", "SHORT"],
            ["inv_1", "SHORT"],
            ["hie_1", "SHORT"],
            ["merge", "LONG"],
            ["character", "SHORT"],
            ["inv_2", "SHORT"],
            ["hie_2", "SHORT"],
            ["merge2", "LONG"],
            ["character2", "SHORT"],
        ],
    )

    # Code_block
    assign_hiesti_to_roads_komm_single = """def Reclass(VEGKATEGORI):
        if VEGKATEGORI == 'T':
            return 1
        elif VEGKATEGORI == 'D':
            return 2
        elif VEGKATEGORI == 'A':
            return 2
        elif VEGKATEGORI == 'U':
            return 4
        elif VEGKATEGORI == 'G':
            return 3
        elif VEGKATEGORI  in ('E', 'R', 'F', 'K', 'P', 'S'):
            return 0
        """

    # Calculate field for hiesti
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___roads_komm_single___n100_road.value,
        field="hiesti",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hiesti_to_roads_komm_single,
    )

    # Code_block
    assign_hie_1_to_roads_komm_single = """def Reclass(VEGKATEGORI):
        if VEGKATEGORI == 'E':
            return 1
        elif VEGKATEGORI == 'R':
            return 1
        elif VEGKATEGORI == 'F':
            return 2
        elif VEGKATEGORI == 'K':
            return 3
        elif VEGKATEGORI == 'P':
            return 4
        elif VEGKATEGORI == 'S':
            return 5
        elif VEGKATEGORI  in ('T', 'D', 'A', 'U', 'G'):
            return 0
        """

    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___roads_komm_single___n100_road.value,
        field="hie_1",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_roads_komm_single,
    )

    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___roads_komm_single___n100_road.value,
        field="merge",
        expression="0 if !VEGNUMMER! is None else !VEGNUMMER!",
        expression_type="PYTHON3",
    )

    assign_merge2_to_roads_komm_single = """def Reclass(MEDIUM):
        if MEDIUM == 'T':
            return 1
        elif MEDIUM == 'L':
            return 2
        elif MEDIUM == 'U':
            return 3
        elif MEDIUM == 'B':
            return 4
    """

    # Calculate field for merge2
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___roads_komm_single___n100_road.value,
        field="merge2",
        expression="Reclass(!MEDIUM!)",
        expression_type="PYTHON3",
        code_block=assign_merge2_to_roads_komm_single,
    )


def roads_komm_diss():
    arcpy.analysis.PairwiseDissolve(
        in_features=Road_N100.test1___roads_komm_single___n100_road.value,
        out_feature_class=Road_N100.test1___roads_komm_diss___n100_road.value,
        dissolve_field=[
            "OBJTYPE",
            "TYPEVEG",
            "MEDIUM",
            "VEGFASE",
            "VEGKATEGORI",
            "VEGNUMMER",
            "inv_sti",
            "hiesti",
            "inv_1",
            "hie_1",
            "merge",
            "character",
            "inv_2",
            "hie_2",
            "merge2",
            "character2",
        ],
        multi_part="SINGLE_PART",
    )


def remove():
    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.test1___roads_komm_diss___n100_road.value,
        minimum_length="100 meters",
    )


def merge1():
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___roads_komm_diss___n100_road.value,
        merge_field="merge",
        merge_distance="150 meters",
        out_features=Road_N100.test1___roads_komm_merge1___n100_road.value,
    )


def thin_sti():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___roads_komm_merge1___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )


def komm_sti_thin1():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___roads_komm_merge1___n100_road.value,
        expression="OBJTYPE IN ('Sti', 'Traktorveg', 'GangSykkelveg') AND inv_sti = 0",
        output_name=Road_N100.test1___komm_sti_thin1___n100_road.value,
        selection_type="NEW_SELECTION",
    )
    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___komm_sti_thin1___n100_road.value,
        field="hie_1",
        expression="5",
        expression_type="PYTHON3",
    )


def komm_bilveg():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___roads_komm_merge1___n100_road.value,
        expression="OBJTYPE = 'Veglenke'",
        output_name=Road_N100.test1___komm_bilveg___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def komm_copy():
    arcpy.management.CopyFeatures(
        in_features=Road_N100.test1___komm_bilveg___n100_road.value,
        out_feature_class=Road_N100.test1___komm_thin2___n100_road.value,
    )


def komm_thin2():
    arcpy.management.Append(
        inputs=Road_N100.test1___komm_sti_thin1___n100_road.value,
        target=Road_N100.test1___komm_thin2___n100_road.value,
    )


def thin_bilveger():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___komm_thin2___n100_road.value,
        minimum_length="1000 meters",
        invisibility_field="inv_1",
        hierarchy_field="hie_1",
    )


def komm_thin3():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___komm_thin2___n100_road.value,
        expression="inv_1 = 0",
        output_name=Road_N100.test1___komm_thin3___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def komm_crd1():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.test1___komm_thin3___n100_road.value,
        collapse_distance="60 meters",
        output_feature_class=Road_N100.test1___komm_crd1___n100_road.value,
    )


def veg100_oslo():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___komm_crd1___n100_road.value,
        expression="inv_1 = 0",
        output_name=Road_N100.test1___veg100_oslo___n100_road.value,
        selection_type="NEW_SELECTION",
    )


if __name__ == "__main__":
    main()


# def field_names():
#     feature_class = Road_N100.test1___sti2___n100_road.value
#     field_names = arcpy.ListFields(feature_class)
#
#     for field in field_names:
#         print(f"{field.name}")
#
#     arcpy.management.DeleteField(
#         in_table=Road_N100.test1___sti2___n100_road.value,
#         drop_field=[
#             "FELTOVERSIKT",
#             "KONNEKTERINGSLENKE",
#             "SIDEVEG",
#             "ADSKILTELOP",
#             "SIDEANLEGGSDEL",
#             "_CLIPPED",
#             "ORIG_FID",
#         ],
#     )
#
#
#
# def MDR1_bilnum():
#     arcpy.cartography.MergeDividedRoads(
#         in_features=Road_N100.test1___veg4___n100_road.value,
#         merge_field="merge",
#         merge_distance="40 meters",
#         out_features=Road_N100.test1___MDR1_bilnum___n100_road.value,
#         character_field="character",
#     )
#
#
# def adding_locks_to_veg4():
#     arcpy.management.AddFields(
#         in_table=Road_N100.test1___veg4___n100_road.value,
#         field_description=[
#             ["LOCK_TL", "SHORT"],
#             ["LOCK_TU", "SHORT"],
#             ["LOCK_UL", "SHORT"],
#         ],
#     )
#     assign_LOCK_TL_to_veg4 = """def Reclass(MEDIUM):
#          if MEDIUM == 'T':
#              return 1
#          elif MEDIUM == 'L':
#              return 1
#          elif MEDIUM == 'U':
#              return 0
#          """
#
#
# def CDR1():
#     arcpy.cartography.CollapseRoadDetail(
#         in_features=Road_N100.test1___MDR1_bilnum___n100_road.value,
#         collapse_distance="60 meters",
#         output_feature_class=Road_N100.test1___CDR1___n100_road.value,
#         # locking_field="LOCK_UL",
#     )
#
# def CDR0():
#     arcpy.cartography.CollapseRoadDetail(
#         in_features=Road_N100.test1___veg4___n100_road.value,
#         collapse_distance="60 meters",
#         output_feature_class=Road_N100.test1___CDR0___n100_road.value,
#     )
