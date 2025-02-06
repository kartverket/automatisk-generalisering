# har tester ViR
import arcpy

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy

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
    elveg_and_sti_kommune_singlepart_dissolve()
    adding_fields_to_elveg_and_sti_kommune_singlepart_dissolve()
    removesmalllines()
    mergedividedroads()
    crd()
    medium_ul()
    medium_t()
    kryss()
    simplify()
    thin_sti2()
    veglenke2()
    thin_vegklasse2()
    veg100_finnmarkc()


# dette er sånn midlertidig, siden jeg ikke kan gjøre noe bedre må jeg skrive kommunenavn 4 steder linjer 35, 42, 375 og 379
def kommune():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.AdminFlate,
        expression="NAVN='finnmarkc'",
        output_name=Road_N100.test1___kommune___n100_road.value,
        selection_type="NEW_SELECTION",
    )


@timing_decorator
def kommune_buffer():
    arcpy.analysis.PairwiseBuffer(
        in_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___kommune_buffer___n100_road.value,
        buffer_distance_or_field="1000 meters",
    )


# lager en buffer så clipper til admingrense etterpå og veger treffer riktig
def elveg_and_sti_kommune():
    arcpy.analysis.Clip(
        in_features=input_roads.vegsenterlinje,
        clip_features=Road_N100.test1___kommune_buffer___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
    )


# singlepart er krav til flere verktøy
def elveg_and_sti_kommune_singlepart():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___elveg_and_sti_kommune___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
    )


# dissolve slik at RemoveSmallLines fungerer bedre, mange små stubber hvor veglenker som vi ikke trenger splitter
@timing_decorator
def elveg_and_sti_kommune_singlepart_dissolve():
    arcpy.management.Dissolve(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
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


# field names burde endres til f eks hie_vegkat eller hie_klasse så de viser hvilke attributt hierarchy baseres på i Thin
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
    assign_hiesti_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(vegkategori):
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hiesti",
        expression="Reclass(!vegkategori!)",
        expression_type="PYTHON3",
        code_block=assign_hiesti_to_elveg_and_sti_kommune_singlepart_dissolve,
    )

    # Code_block
    assign_hie_1_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(vegkategori):
        if vegkategori == 'E':
            return 1
        elif vegkategori == 'R':
            return 1
        elif vegkategori == 'F':
            return 2
        elif vegkategori == 'K':
            return 3
        elif vegkategori == 'P':
            return 4
        elif vegkategori == 'S':
            return 5
        elif vegkategori  in ('T', 'D', 'A', 'U', 'G', 'B'):
            return 0
        elif vegkategori is None:
            return 4
        """

    # Calculate field for hie_1 som skal brukes i Thin av kjørbare veger basert på vegkategori
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hie_1",
        expression="Reclass(!vegkategori!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_elveg_and_sti_kommune_singlepart_dissolve,
    )

    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="merge",
        expression="0 if !vegnummer! is None else !vegnummer!",
        expression_type="PYTHON3",
    )

    assign_merge2_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(medium):
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="merge2",
        expression="Reclass(!medium!)",
        expression_type="PYTHON3",
        code_block=assign_merge2_to_elveg_and_sti_kommune_singlepart_dissolve,
    )

    # Code_block
    assign_hie_2_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(vegklasse):
        if vegklasse == 0:
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
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hie_2",
        expression="Reclass(!vegklasse!)",
        expression_type="PYTHON3",
        code_block=assign_hie_2_to_elveg_and_sti_kommune_singlepart_dissolve,
    )


# remove small line fjerner mange små veger og gjør at datasett blir "lettere"
@timing_decorator
def removesmalllines():
    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        minimum_length="100 meters",
    )


# MDR skal kjøres før CRD, her er det potensiall for bedre prossessering hvis man ser på MDR ved vegnummer, medium og ansre attributter
@timing_decorator
def mergedividedroads():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads___n100_road.value,
    )
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads___n100_road.value,
        merge_field="merge",
        merge_distance="150 meters",
        out_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads2___n100_road.value,
    )


# ikke alle rundkjøringer som blir fjernet; noen rndkjøringer i i forskjellige plan enn veger som kjrysser under eller over;
# noen rundkjøringer har deler i luft og deler på bakken


@timing_decorator
def crd():
    arcpy.cartography.CollapseRoadDetail(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads___n100_road.value,
        collapse_distance="60 meters",
        output_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd___n100_road.value,
    )


# brukes ikke foreløpig
def medium_ul():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd___n100_road.value,
        expression="medium IN ('U', 'L')",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_ul___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd___n100_road.value,
        expression=" medium = 'T'",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_t___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager kryss for alle veger som er på bakken, den prossess skaper en ny field som må slettes så append etterpå fungerer
def kryss():
    arcpy.management.FeatureToLine(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_t___n100_road.value,
        out_feature_class=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
    )

    arcpy.management.DeleteField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
        drop_field="FID_test1___elveg_and_sti_kommune_singlepart_dissolve_mergedivid",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_ul___n100_road.value,
        target=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
    )


def simplify():
    arcpy.cartography.SimplifyLine(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
        out_feature_class=Road_N100.test1___simplified___n100_road.value,
        algorithm="POINT_REMOVE",
        tolerance="2 meters",
        error_option="RESOLVE_ERRORS",
    )


@timing_decorator
def thin_sti2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___simplified___n100_road.value,
        minimum_length="1500 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___simplified___n100_road.value,
        expression="objtype IN ('Barmarksløype', 'Sti', 'Traktorveg', 'GangSykkelveg') AND inv_sti = 0",
        output_name=Road_N100.test1___simplified_thin_sti___n100_road.value,
        selection_type="NEW_SELECTION",
    )
    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___simplified_thin_sti___n100_road.value,
        field="hie_1",
        expression="5",
        expression_type="PYTHON3",
    )
    # Calculate field for hie_2
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___simplified_thin_sti___n100_road.value,
        field="hie_2",
        expression="11",
        expression_type="PYTHON3",
    )


# lager datasett med kjørbare veger og blir sett sammen med stiene som er igkjen etter Thin
def veglenke2():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___simplified___n100_road.value,
        expression="objtype = 'VegSenterlinje'",
        output_name=Road_N100.test1___veglenke2___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___simplified_thin_sti___n100_road.value,
        target=Road_N100.test1___veglenke2___n100_road.value,
    )


# lager enda en datasett hvor kjørbareveger Thin med hierarchy etter vegklasse og større min lengde
@timing_decorator
def thin_vegklasse2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___veglenke2___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___veglenke2___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___thin_vegklasse2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager en datasett med resultatet fra Thin etter vegklasse og 2000m
@timing_decorator
def veg100_finnmarkc():
    arcpy.cartography.SmoothLine(
        in_features=Road_N100.test1___thin_vegklasse2___n100_road.value,
        out_feature_class=Road_N100.test1___sm300___n100_road.value,
        algorithm="PAEK",
        tolerance="300 meters",
        error_option="RESOLVE_ERRORS",
    )

    arcpy.management.Dissolve(
        in_features=Road_N100.test1___sm300___n100_road.value,
        out_feature_class=Road_N100.test1___diss___n100_road.value,
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
        in_features=Road_N100.test1___diss___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_finnmarkc_modell3___n100_road.value,
    )


if __name__ == "__main__":
    main()
