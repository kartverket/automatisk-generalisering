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
    mergedividedroads()
    crd()
    medium_ul()
    medium_t()
    kryss()
    thin_sti()
    veglenke()
    thinveg2()
    thin3vegklasse()
    thin4vegklasse()
    veg100_ringerike0()
    veg100_ringerike1()
    veg100_ringerike2()


# dette er sånn midlertidig, siden jeg ikke kan gjøre noe bedre må jeg skrive kommunenavn 4 steder linjer 35, 42, 375 og 379
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


# lager en buffer så clipper til admingrense etterpå og veger treffer riktig
def elveg_and_sti_kommune():
    arcpy.analysis.Clip(
        in_features=input_roads.elveg,
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
            "VEGKLASSE",
            "MOTORVEGTYPE",
            "SUBTYPEKODE",
            "UTTEGNING",
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

    # Calculate field for hiesti som skal brukes i Thin av stiene og andre ikke-kjørbare veger
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

    # Calculate field for hie_1 som skal brukes i Thin av kjørbare veger basert på vegkategori
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

    # Code_block
    assign_hie_2_to_elveg_and_sti_kommune_singlepart_dissolve = """def Reclass(VEGKLASSE):
        if VEGKLASSE == 0:
            return 1
        elif VEGKLASSE == 1:
            return 1
        elif VEGKLASSE == 2:
            return 2
        elif VEGKLASSE == 3:
            return 2
        elif VEGKLASSE == 4:
            return 3
        elif VEGKLASSE == 5:
            return 3
        elif VEGKLASSE == 6:
            return 4
        elif VEGKLASSE == 7:
            return 5
        elif VEGKLASSE == 8:
            return 5
        elif VEGKLASSE == 9:
            return 5
        elif VEGKLASSE is None:
            return 10
        """

    # Calculate field for hie_2 som skal brukes i Thin basert på funksjonellvegklasse
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        field="hie_2",
        expression="Reclass(!VEGKLASSE!)",
        expression_type="PYTHON3",
        code_block=assign_hie_2_to_elveg_and_sti_kommune_singlepart_dissolve,
    )


# remove small line fjerner mange små veger og gjør at datasett blir "lettere"
def removesmalllines():
    arcpy.topographic.RemoveSmallLines(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        minimum_length="100 meters",
    )


# MDR skal kjøres før CRD, her er det potensiall for bedre prossessering hvis man ser på MDR ved vegnummer, medium og ansre attributter
def mergedividedroads():
    arcpy.cartography.MergeDividedRoads(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve___n100_road.value,
        merge_field="merge",
        merge_distance="150 meters",
        out_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads___n100_road.value,
    )


# ikke alle rundkjøringer som blir fjernet; noen rndkjøringer i i forskjellige plan enn veger som kjrysser under eller over;
# noen rundkjøringer har deler i luft og deler på bakken
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
        expression="MEDIUM IN ('U', 'L')",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_medium_ul___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# brukes for å lage kryss etter dissolve
def medium_t():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd___n100_road.value,
        expression=" MEDIUM = 'T'",
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


# første thin kjøres på ikke-kjørbare veger
# lages egen datasett med alle som fikk invisibility 0 og
# for disse kodes hie_1 til 5 slik at de skal være med, men med lav viktighet i neste THin
def thin_sti():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
        minimum_length="3000 meters",
        invisibility_field="inv_sti",
        hierarchy_field="hiesti",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
        expression="OBJTYPE IN ('Sti', 'Traktorveg', 'GangSykkelveg') AND inv_sti = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti___n100_road.value,
        selection_type="NEW_SELECTION",
    )
    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti___n100_road.value,
        field="hie_1",
        expression="5",
        expression_type="PYTHON3",
    )
    # Calculate field for hie_2
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti___n100_road.value,
        field="hie_2",
        expression="11",
        expression_type="PYTHON3",
    )


# lager datasett med kjørbare veger og blir sett sammen med stiene som er igkjen etter Thin
def veglenke():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss___n100_road.value,
        expression="OBJTYPE = 'Veglenke'",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        selection_type="NEW_SELECTION",
    )

    arcpy.management.Append(
        inputs=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_thin_sti___n100_road.value,
        target=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
    )


# andre runde på Thin kjøres på kjørbareveger og stiene som fikk bli igjen med har hierarchy 5
def thinveg2():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_1",
        hierarchy_field="hie_1",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        expression="inv_1 = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thinveg2___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager enda en datasett hvor kjørbareveger Thin med hierarchy etter vegklasse med 2000m
def thin3vegklasse():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        minimum_length="2000 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin3vegklasse___n100_road.value,
        selection_type="NEW_SELECTION",
    )


# lager enda en datasett hvor kjørbareveger Thin med hierarchy etter vegklasse og større min lengde
def thin4vegklasse():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        minimum_length="3000 meters",
        invisibility_field="inv_2",
        hierarchy_field="hie_2",
    )

    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke___n100_road.value,
        expression="inv_2 = 0",
        output_name=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin4vegklasse___n100_road.value,
        selection_type="NEW_SELECTION",
    )

# lager en datasett med resultatet fra Thin etter evgkatgori
def veg100_ringerike0():
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thinveg2___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_ringerike0___n100_road.value,
    )


# lager en datasett med resultatet fra Thin etter vegklasse og 2000m
def veg100_ringerike1():
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin3vegklasse___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_ringerike1___n100_road.value,
    )

# lager en datasett med resultatet fra Thin etter vegklasse og 3000m
def veg100_ringerike2():
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___elveg_and_sti_kommune_singlepart_dissolve_mergedividedroads_crd_kryss_veglenke_thin4vegklasse___n100_road.value,
        clip_features=Road_N100.test1___kommune___n100_road.value,
        out_feature_class=Road_N100.test1___veg100_ringerike2___n100_road.value,
    )


if __name__ == "__main__":
    main()
