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
    kommune()
    kommune_buffer()
    elveg_and_sti_kommune()
    elveg_and_sti_kommune_singlepart()
    elveg_and_sti_kommune_singlepart_dissolve()
    adding_fields_to_elveg_and_sti_kommune_singlepart_dissolve()
    removesmalllines()
    medium_ul()
    medium_t()
    kryss()
    mergedividedroads()
    thin_sti()
    veglenke()
    thin2()
    crd()
    veg100_ringerike()


def kommune():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.AdminFlate,
        expression="NAVN='Ringerike'",
        output_name=Road_N100.test1___kommune___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def kommune_buffer():
    arcpy.analysis.PairwiseBuffer(
        in_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___kommune_buffer___n100_road.value,
        buffer_distance_or_field="1000 meters",
    )


def elveg_and_sti_kommune():
    arcpy.analysis.Clip(
        in_features=input_roads.elveg_and_sti,
        clip_features=Road_N100.test1___kommune_buffer___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
    )


def elveg_and_sti_kommune_singlepart():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
    )


def elveg_and_sti_kommune_singlepart_dissolve():
    arcpy.analysis.PairwiseDissolve(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        dissolve_field=[
            "OBJTYPE",
            "TYPEVEG",
            "MEDIUM",
            "VEGFASE",
            "VEGKATEGORI",
            "VEGNUMMER",
            "SUBTYPEKODE",
            "MOTORVEGTYPE",
            "UTTEGNING",
        ],
        multi_part="SINGLE_PART",
    )


def adding_fields_to_elveg_and_sti_kommune_singlepart_dissolve() -> object:
    arcpy.management.AddFields(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
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
    assign_hiesti_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(VEGKATEGORI):
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hiesti",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hiesti_to_elveg_and_sti_kommune_singlepart_dissolve,
    )

    # Code_block
    assign_hie_1_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(VEGKATEGORI):
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hie_1",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_elveg_and_sti_kommune_singlepart_dissolve,
    )

    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="merge",
        expression="0 if !VEGNUMMER! is None else !VEGNUMMER!",
        expression_type="PYTHON3",
    )

    assign_merge2_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(MEDIUM):
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="merge2",
        expression="Reclass(!MEDIUM!)",
        expression_type="PYTHON3",
        code_block=assign_merge2_to_elveg_and_sti_kommune_singlepart_dissolve,
    )


def removesmalllines():
    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        minimum_length="100 meters",
    )


def medium_ul():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        expression="MEDIUM IN ('U', 'L')",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_ul___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def medium_t():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        expression=" MEDIUM = 'T'",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def kryss():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
        drop_field="FID_test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t__",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_ul___n100_road.value,
        target=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
    )


def mergedividedroads():
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss___n100_road.value,
        merge_field="merge",
        merge_distance="150 meters",
        out_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads___n100_road.value,
    )


def thin_sti():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads___n100_road.value,
        minimum_length="3000 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads___n100_road.value,
        expression="OBJTYPE IN ('Sti', 'Traktorveg', 'GangSykkelveg') AND inv_sti = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_thin_sti___n100_road.value,
        selection_type="NEW_SELECTION",
    )
    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_thin_sti___n100_road.value,
        field="hie_1",
        expression="5",
        expression_type="PYTHON3",
    )


def veglenke():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads___n100_road.value,
        expression="OBJTYPE = 'Veglenke'",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_thin_sti___n100_road.value,
        target=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke___n100_road.value,
    )


def thin2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_1",
        hierarchy_field="hie_1",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke___n100_road.value,
        expression="inv_1 = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke_thin2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def crd():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke_thin2___n100_road.value,
        collapse_distance="60 meters",
        output_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke_thin2_crd___n100_road.value,
    )


def veg100_ringerike():
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_medium_t_kryss_mergedividedroads_veglenke_thin2_crd___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_ringerike___n100_road.value,
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
