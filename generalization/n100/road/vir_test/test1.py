# har tester ViR
import arcpy

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy

# from custom_tools.generalization_tools.road import DissolveWithIntersections
# from custom_tools.generalization_tools.road.dissolve_with_intersections import (
#     DissolveWithIntersections,
# )

# from input_data import input_elveg
# from input_data import input_veg
from input_data import input_roads

from custom_tools.decorators.timing_decorator import timing_decorator


@timing_decorator
def main():
    environment_setup.main()
    kommune()
    kommune_buffer()
    elveg_and_sti_kommune()
    elveg_and_sti_kommune_singlepart()
    adding_fields_to_elveg_and_sti_kommune_singlepart()
    removesmalllines()
    crd1()
    simplify()
    # lista()
    diss1()
    medium_ul1()
    medium_t1()
    kryss1()
    # veglenke()
    thin_vegklasse1()
    diss2()
    medium_ul2()
    medium_t2()
    kryss2()
    thin_vegklasse2()
    diss3()
    medium_ul3()
    medium_t3()
    kryss3()
    thin_vegklasse3()
    diss4()
    medium_ul4()
    medium_t4()
    kryss4()
    thin_vegklasse4()
    # run_dissolve_with_intersections()
    # box5()
    diss5()
    medium_ul5()
    medium_t5()
    kryss5()
    thin5_sti1()
    diss6()
    medium_ul6()
    medium_t6()
    kryss6()
    thin6_sti2()
    diss7()
    medium_ul7()
    medium_t7()
    kryss7()
    thin7_sti3()
    veg100_oslosentrum1()


# dette er sånn midlertidig, siden jeg ikke kan gjøre noe bedre må jeg skrive kommunenavn 4 steder linjer 35, 42, 388 og 418
def kommune():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.AdminFlate,
        expression="NAVN='oslosentrum1'",
        output_name=Road_N100.test1___kommune___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def kommune_buffer():
    arcpy.analysis.PairwiseBuffer(
        in_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___kommune_buffer___n100_road.value,
        buffer_distance_or_field="3000 meters",
    )


# lager en buffer så klipper til admingrense etterpå til slutt av modellen så veger treffer riktig
@timing_decorator
def elveg_and_sti_kommune():
    arcpy.analysis.Clip(
        in_features=input_roads.vegsenterlinje,
        clip_features=Road_N100.test1___kommune_buffer___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
    )


# singlepart er krav til flere verktøy
@timing_decorator
def elveg_and_sti_kommune_singlepart():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
    )


# field names burde endres til f eks hie_vegkat eller hie_klasse så de viser hvilke attributt hierarchy baseres på i Thin
@timing_decorator
def adding_fields_to_elveg_and_sti_kommune_singlepart() -> object:
    arcpy.management.AddFields(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
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
    assign_hiesti_to_elveg_and_sti_kommune_singlepart = """def Reclass(vegkategori):
        if vegkategori == 'T':
            return 1
        elif vegkategori == 'D':
            return 2
        elif vegkategori == 'A':
            return 2
        elif vegkategori == 'U':
            return 4
        elif vegkategori == 'G':
            return 3
        elif vegkategori == 'B':
            return 1
        elif vegkategori  in ('E', 'R', 'F', 'K', 'P', 'S'):
            return 0
        elif vegkategori is None:
            return 2
        """

    # Calculate field for hiesti som skal brukes i Thin av stiene og andre ikke-kjørbare veger
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="hiesti",
        expression="Reclass(!vegkategori!)",
        expression_type="PYTHON3",
        code_block=assign_hiesti_to_elveg_and_sti_kommune_singlepart,
    )

    # Code_block - egentlig blir dette ikke brukt - Thin går på vegklasse, dvs hie_2

    assign_hie_1_to_elveg_and_sti_kommune_singlepart = """def Reclass(vegklasse):
    if vegklasse in (None, ''):  # Handle NULL or empty values first
        return 5  
    elif vegklasse in ('0', '1', '2', '3', '4'):
        return 1
    elif vegklasse == '5':
        return 2
    elif vegklasse == '6':
        return 3
    elif vegklasse == '7':
        return 4
    elif vegklasse in ('8', '9'):
        return 5
    return 5  # Default return to prevent errors
"""

    # Calculate field for hie_1 som skal brukes i Thin av kjørbare veger basert på vegkategori
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="hie_1",
        expression="Reclass(!vegklasse!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_elveg_and_sti_kommune_singlepart,
    )

    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="merge",
        expression="0 if !vegnummer! is None else !vegnummer!",
        expression_type="PYTHON3",
    )

    assign_merge2_to_elveg_and_sti_kommune_singlepart = """def Reclass(medium):
        if medium == 'T':
            return 1
        elif medium == 'L':
            return 2
        elif medium == 'U':
            return 3
        elif medium == 'B':
            return 4
    """

    # Calculate field for merge2
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="merge2",
        expression="Reclass(!medium!)",
        expression_type="PYTHON3",
        code_block=assign_merge2_to_elveg_and_sti_kommune_singlepart,
    )

    # Code_block
    assign_character = """def Reclass(typeveg):
        if typeveg == 'rundkjøring':
            return 0
        elif typeveg == 'rampe':
            return 2
        else:
            return 1
        """

    # Calculate field for hiesti som skal brukes i Thin av stiene og andre ikke-kjørbare veger
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="character",
        expression="Reclass(!typeveg!)",
        expression_type="PYTHON3",
        code_block=assign_character,
    )

    # Code_block
    assign_hie_2_to_elveg_and_sti_kommune_singlepart = """def Reclass(vegklasse, typeveg):
        if typeveg == 'rampe':
            return 10
        elif vegklasse == 0:
            return 1
        elif vegklasse == 1:
            return 1
        elif vegklasse == 2:
            return 2
        elif vegklasse == 3:
            return 2
        elif vegklasse == 4:
            return 3
        elif vegklasse == 5:
            return 3
        elif vegklasse == 6:
            return 4
        elif vegklasse == 7:
            return 5
        elif vegklasse == 8:
            return 5
        elif vegklasse == 9:
            return 5
        elif vegklasse is None:
            return 10
        """

    # Calculate field for hie_2 som skal brukes i Thin basert på funksjonellvegklasse
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        field="hie_2",
        expression="Reclass(!vegklasse!, !typeveg!)",
        expression_type="PYTHON3",
        code_block=assign_hie_2_to_elveg_and_sti_kommune_singlepart,
    )


# remove small line fjerner mange små veger og gjør at datasett blir "lettere"
@timing_decorator
def removesmalllines():
    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        minimum_length="100 meters",
    )
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_rsl___n100_road.value,
    )


@timing_decorator
def crd1():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_rsl___n100_road.value,
        collapse_distance="60 meters",
        output_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_rsl_crd60___n100_road.value,
    )


@timing_decorator
def simplify():
    arcpy.cartography.SimplifyLine(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_rsl_crd60___n100_road.value,
        out_feature_class=Road_N100.test1___simplified___n100_road.value,
        algorithm="POINT_REMOVE",
        tolerance="2 meters",
        error_option="RESOLVE_ERRORS",
    )
    arcpy.management.DeleteField(
        in_table=Road_N100.test1___simplified___n100_road.value,
        drop_field=["InLine_FID", "SimLnFlag", "MaxSimpTol", "MinSimpTol"],
    )


# @timing_decorator
# def lista():
#     # Get a list of fields
#     fields = arcpy.ListFields(
#         Road_N100.test1___elveg_and_sti_kommune_singlepart_rsl_crd60___n100_road.value
#     )
#
#     # Print field names
#     for field in fields:
#         print(field.name)
#


@timing_decorator
def diss1():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___simplified___n100_road.value,
        out_feature_class=Road_N100.test1___diss1___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul1():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss1___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul1___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t1():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss1___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t1___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss1():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t1___n100_road.value,
        out_feature_class=Road_N100.test1___kryss1___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss1___n100_road.value,
        drop_field="FID_test1___medium_t1___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul1___n100_road.value,
        target=Road_N100.test1___kryss1___n100_road.value,
    )


@timing_decorator
def thin_vegklasse1():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss1___n100_road.value,
        minimum_length="500 meters",
        invisibility_field="inv_1",
        hierarchy_field="hie_1",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss1___n100_road.value,
        expression="inv_1 = 0",
        output_name=Road_N100.test1___thin1___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def diss2():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin1___n100_road.value,
        out_feature_class=Road_N100.test1___diss2___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul2():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss2___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t2():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss2___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss2():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t2___n100_road.value,
        out_feature_class=Road_N100.test1___kryss2___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss2___n100_road.value,
        drop_field="FID_test1___medium_t2___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul2___n100_road.value,
        target=Road_N100.test1___kryss2___n100_road.value,
    )


@timing_decorator
def thin_vegklasse2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss2___n100_road.value,
        minimum_length="1000 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss2___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___thin2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def diss3():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin2___n100_road.value,
        out_feature_class=Road_N100.test1___diss3___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul3():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss3___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul3___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t3():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss3___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t3___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss3():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t3___n100_road.value,
        out_feature_class=Road_N100.test1___kryss3___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss3___n100_road.value,
        drop_field="FID_test1___medium_t3___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul3___n100_road.value,
        target=Road_N100.test1___kryss3___n100_road.value,
    )


@timing_decorator
def thin_vegklasse3():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss3___n100_road.value,
        minimum_length="1500 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss3___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___thin3___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def diss4():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin3___n100_road.value,
        out_feature_class=Road_N100.test1___diss4___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul4():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss4___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul4___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t4():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss4___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t4___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss4():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t4___n100_road.value,
        out_feature_class=Road_N100.test1___kryss4___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss4___n100_road.value,
        drop_field="FID_test1___medium_t4___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul4___n100_road.value,
        target=Road_N100.test1___kryss4___n100_road.value,
    )


@timing_decorator
def thin_vegklasse4():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss4___n100_road.value,
        minimum_length="1500 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss4___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___thin4___n100_road.value,
        selection_type="NEW_SELECTION",
    )


#
# # Helper Functions
# def run_dissolve_with_intersections(
#     input_line_feature,
#     output_processed_feature,
#     dissolve_field_list,
# ):
#     dissolve_obj = DissolveWithIntersections(
#         input_line_feature=input_line_feature,
#         root_file=Road_N100.data_preparation___intersections_root___n100_road.value,
#         output_processed_feature=output_processed_feature,
#         dissolve_field_list=dissolve_field_list,
#         list_of_sql_expressions=[
#             f" MEDIUM = '{MediumAlias.tunnel}'",
#             f" MEDIUM = '{MediumAlias.bridge}'",
#             f" MEDIUM = '{MediumAlias.on_surface}'",
#         ],
#     )
#     dissolve_obj.run()
#
#
# def box5():
#     run_dissolve_with_intersections(
#         input_line_feature=Road_N100.test1___thin4___n100_road.value,
#         output_processed_feature=Road_N100.test1___diss5___n100_road.value,
#         dissolve_field_list=[
#             "objtype",
#             "subtypekode",
#             "vegstatus",
#             "typeveg",
#             "vegkategori",
#             "vegnummer",
#             "motorvegtype",
#             "vegklasse",
#             "rutemerking",
#             "medium",
#             "uttegning",
#             "inv_sti",
#             "hiesti",
#             "inv_1",
#             "hie_1",
#             "merge",
#             "character",
#             "inv_2",
#             "hie_2",
#             "merge2",
#             "character2",
#         ],
#     )


@timing_decorator
def diss5():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin4___n100_road.value,
        out_feature_class=Road_N100.test1___diss5___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul5():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss5___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul5___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t5():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss5___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t5___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss5():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t5___n100_road.value,
        out_feature_class=Road_N100.test1___kryss5___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss5___n100_road.value,
        drop_field="FID_test1___medium_t5___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul5___n100_road.value,
        target=Road_N100.test1___kryss5___n100_road.value,
    )


@timing_decorator
def thin5_sti1():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss5___n100_road.value,
        minimum_length="1500 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss5___n100_road.value,
        expression="inv_sti = 0",
        output_name=Road_N100.test1___thin5___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def diss6():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin5___n100_road.value,
        out_feature_class=Road_N100.test1___diss6___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul6():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss6___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul6___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t6():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss6___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t6___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss6():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t6___n100_road.value,
        out_feature_class=Road_N100.test1___kryss6___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss6___n100_road.value,
        drop_field="FID_test1___medium_t6___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul6___n100_road.value,
        target=Road_N100.test1___kryss6___n100_road.value,
    )


@timing_decorator
def thin6_sti2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss6___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss6___n100_road.value,
        expression="inv_sti = 0",
        output_name=Road_N100.test1___thin6___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def diss7():  # Perform the dissolve operation
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___thin6___n100_road.value,
        out_feature_class=Road_N100.test1___diss7___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
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


# brukes ikke foreløpig
def medium_ul7():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss7___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___medium_ul7___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t7():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___diss7___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___medium_t7___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss7():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___medium_t7___n100_road.value,
        out_feature_class=Road_N100.test1___kryss7___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___kryss7___n100_road.value,
        drop_field="FID_test1___medium_t7___n100_road",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___medium_ul7___n100_road.value,
        target=Road_N100.test1___kryss7___n100_road.value,
    )


def thin7_sti3():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___kryss7___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kryss7___n100_road.value,
        expression="inv_sti = 0",
        output_name=Road_N100.test1___thin7___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager en datasett med resultatet fra Thin etter vegklasse og 2000m
@timing_decorator
def veg100_oslosentrum1():
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___thin7___n100_road.value,
        merge_field="merge",
        merge_distance="60 meters",
        out_features=Road_N100.test1___mdr___n100_road.value,
        character_field="character",
    )
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___mdr___n100_road.value,
        merge_field="merge",
        merge_distance="60 meters",
        out_features=Road_N100.test1___mdr2___n100_road.value,
        character_field="character",
    )
    # trenger ikke en tredje runde, ingen forskjell
    # arcpy.cartography.MergeDividedRoads(
    #     in_features=Road_N100.test1___mdr2___n100_road.value,
    #     merge_field="merge",
    #     merge_distance="60 meters",
    #     out_features=Road_N100.test1___mdr3___n100_road.value,
    #     character_field="character",
    # )
    arcpy.cartography.SmoothLine(
        in_features=Road_N100.test1___mdr2___n100_road.value,
        out_feature_class=Road_N100.test1___sm300___n100_road.value,
        algorithm="PAEK",
        tolerance="300 meters",
        error_option="RESOLVE_ERRORS",
    )

    arcpy.management.Dissolve(
        in_features=Road_N100.test1___sm300___n100_road.value,
        out_feature_class=Road_N100.test1___dissx___n100_road.value,
        dissolve_field=[
            "objtype",
            "subtypekode",
            "vegstatus",
            "typeveg",
            "vegkategori",
            "vegnummer",
            "motorvegtype",
            "vegklasse",
            "rutemerking",
            "medium",
            "uttegning",
        ],
        multi_part="SINGLE_PART",
    )
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___dissx___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_oslosentrum1_modell3___n100_road.value,
    )


if __name__ == "__main__":
    main()
