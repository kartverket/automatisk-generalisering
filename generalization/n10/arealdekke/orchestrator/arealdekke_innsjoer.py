import arcpy
from enum import Enum
from custom_tools.decorators.timing_decorator import timing_decorator
from arealdekke_configurations import a_configs

from composition_configs import core_config
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landuse import Landuse_N10
from input_data import input_arealdekke

from generalization.n10.arealdekke.category_tools.buff_small_polygon_segments import buff_small_polygon_segments

arcpy.env.overwriteOutput = True


"""
Hent data 👍
- Trekker ut innsjøer og regulerte innsjøer fra arealdekket og gjør dem om til egen fc.

Data bearbeiding 👍
- Fikse kommunegrenser som kutter innsjøer i biter: Dissolve -> multi-to-singlepart -> spatial join

Finne innsjoer under minstemål 👍
- Velge ut innsjøer under minimumsmål ved å opprette en minimumsbøffer rundt innsjø kanten (polygon to line) og deretter erase. 
- Samme minstemål som elvene på minimum 6 meter bredde
- Buffre områdene igjen fra den negative minimumsbøfferen for at den skal få ca. opprinnelig størrelse. 
- Erase store innsjø segmenter fra opprinnelig elvelag og gjør dette om til ny fc.

Buffe innsjø segmenter under minstemål (denne burde deles opp!) 👍
- Kjør en multi to single part på innsjø segmentene under minstekrav.
- Opprett en "overkill buffer" på ca. 10 Meter rundt innsjø segmentene.
- Clip innsjøene etter det som passer inni overkill bøfferne.
- Kjør en collapse hydro polygon for å finne midtlinje til bitene.
- Erase områdene over minimum fra midtlinjen.
- Buff midtlinjene med 3 meter for at de skal akkurat fylle minimumskravet.
- Opprett en ny fc som er en merge mellom de originale innsjøene og de nye forstørrede bitene.

Aggregering
- Aggreger små innsjøer som er veldig nærme hverandre. 7 meter aggregation distance virker greit hittil.
    - Kan være en løsning å sette opp en sjekk etter aggregeringen på områdene som ble selektert. Hvis arealet lagt til er en viss prosent av det originale
        arealet (hvertfall 50% ikke innafor), bør endringen sløyfes. Kan velges ut ved å legge til id-en i en liste eller å ha et ekstra attributt felt i
        den aggregerte polygon tabellen.

        - En mulighet kan være å lage en buffer rundt innsjøene som er innenfor største og minstemål. Deretter, kan man clippe arealdekket til bufferne, og
            kjøre en erase for å fjerne vann fra polygonet. Deretter, regner man ut hvilket areal som er størst i nærheten av innsjøen, og legger dette inn i
            innsjøen. En tanke kan å være å kjøre en dissolve for å gjøre alt område om til det som er størst. Her inngår selvsagt prioriteringene. Dette 
            kan feks. komme frem ved at selv om myr er størst, kan bebyggelse prioriteres.

    - Kan legge inn hierarkiet når sjekken skjer. Feks. hvis innsjøen ligger på myr, trenger den ikke å sjekkes.
    - Trenger minstemål og maksmål på innsjøer som skal bli kjørt gjennom aggregeringsfunksjonen. Maks kan f.eks. være 1500m^2, mens minstemål 40m^2

Forenkle innsjø kantene med smoothing og simplify algoritme

Hierarkiet

1. Laveste nivå: minstemål på øyene. Disse fjernes fullstendig
2. Middels nivå: hvis øyer har flere lag, f.eks. skog og snaumark, spiser det største arealet opp det/de andre arealet.
"""


def main():

    environment_setup.main()

    # Sets up work file manager and creates temporarily files
    working_fc = Landuse_N10.arealdekket_lake__n10_landuse.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    fetch_data(files=files)

    # remove_county_borders(files=files)
    combine_small_lakes(files=files)
    # target_selection(files=files)

    # buff_small_polygon_segments(
    #    in_feature_class=files[fc.lakes_processed_selection],
    #    out_feature_class=files[fc.lakes_segments_fixed],
    #    min_width=3)


# ========================
# Dictionary creation and
# Data fetching
# ========================


class fc(Enum):
    lakes_fc = "lakes_fc"
    lakes_segments_fixed = "lakes_segments_fixed"
    lakes_dissolved = "lakes_dissolved"
    lakes_singlepart = "lakes_singlepart"
    lakes_processed = "lakes_processed"
    lakes_simplified_buffed = "lakes_simplified_buffed"
    lakes_aggregated = "lakes_aggregated"
    lakes_processed_selection = "lakes_processed_selection"


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of placing the lake heights.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """

    # Fetch data
    lakes_fc = wfm.build_file_path(file_name="lakes_fc", file_type="gdb")
    lakes_segments_fixed = wfm.build_file_path(
        file_name="lakes_segments_fixed", file_type="gdb"
    )

    lakes_dissolved = wfm.build_file_path(file_name="lakes_dissolved", file_type="gdb")
    lakes_singlepart = wfm.build_file_path(
        file_name="lakes_singlepart", file_type="gdb"
    )
    lakes_processed = wfm.build_file_path(file_name="lakes_processed", file_type="gdb")
    lakes_simplified_buffed = wfm.build_file_path(
        file_name="lakes_simplified_buffed", file_type="gdb"
    )
    lakes_aggregated = wfm.build_file_path(
        file_name="lakes_aggregated", file_type="gdb"
    )

    lakes_processed_selection = wfm.build_file_path(
        file_name="lakes_processed_selection", file_type="gdb"
    )

    return {
        # Fetch data
        fc.lakes_fc: lakes_fc,
        fc.lakes_segments_fixed: lakes_segments_fixed,
        fc.lakes_dissolved: lakes_dissolved,
        fc.lakes_singlepart: lakes_singlepart,
        fc.lakes_processed: lakes_processed,
        fc.lakes_simplified_buffed: lakes_simplified_buffed,
        fc.lakes_aggregated: lakes_aggregated,
        fc.lakes_processed_selection: lakes_processed_selection,
    }


@timing_decorator
def fetch_data(files: dict) -> None:
    # Get data from gdb
    arealdekke_lyr = "arealdekke_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_arealdekke.arealdekke,
        out_layer=arealdekke_lyr,
        where_clause="arealdekke='Ferskvann_innsjo_tjern' OR arealdekke='Ferskvann_innsjo_tjern_regulert'",
    )

    # Repair data to remove self intersections
    arcpy.management.RepairGeometry(
        in_features=arealdekke_lyr, delete_null="DELETE_NULL"
    )
    arcpy.management.EliminatePolygonPart(
        in_features=arealdekke_lyr, out_feature_class=files[fc.lakes_fc]
    )


@timing_decorator
def remove_county_borders(
    files: dict,
) -> None:  # Denne kan kanskje sløyfes hvis vi aggregerer alt uansett
    # Fikse kommunegrenser som kutter innsjøer i biter: Dissolve -> multi-to-singlepart -> spatial join
    lakes_lyr = "lakes_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_fc], out_layer=lakes_lyr
    )

    arcpy.management.Dissolve(
        in_features=lakes_lyr, out_feature_class=files[fc.lakes_dissolved]
    )

    lakes_dissolved_lyr = "lakes_dissolved_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_dissolved], out_layer=lakes_dissolved_lyr
    )

    arcpy.management.MultipartToSinglepart(
        in_features=lakes_dissolved_lyr, out_feature_class=files[fc.lakes_singlepart]
    )

    lakes_singlepart_lyr = "lakes_singlepart_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_singlepart], out_layer=lakes_singlepart_lyr
    )

    arcpy.analysis.SpatialJoin(
        target_features=lakes_singlepart_lyr,
        join_features=lakes_lyr,
        out_feature_class=files[fc.lakes_processed],
        join_operation="JOIN_ONE_TO_ONE",
        match_option="INTERSECT",
    )


@timing_decorator
def combine_small_lakes(files: dict) -> None:

    lakes_lyr = "lakes_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_fc], out_layer=lakes_lyr
    )

    arcpy.management.RepairGeometry(in_features=lakes_lyr, delete_null="DELETE_NULL")

    # Må kjøre simplify først for at aggregate ikke tar for lang tid.
    arcpy.cartography.SimplifyPolygon(
        in_features=lakes_lyr,
        out_feature_class=files[fc.lakes_processed],
        algorithm="BEND_SIMPLIFY",
        tolerance="4 Meters",
        error_option="RESOLVE_ERRORS",
    )

    # Opprett en buffer for å finne innsjøer som er innenfor aggregation distance-en. Innsjøer som ikke er i nærheten av andre innsjøer skal ikke aggregeres.
    lakes_simplified_lyr = "lakes_simplified_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_processed], out_layer=lakes_simplified_lyr
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=lakes_simplified_lyr,
        out_feature_class=files[fc.lakes_simplified_buffed],
        buffer_distance_or_field=a_configs.lake_aggregation_distance,
        dissolve_option="ALL",
    )

    id_field = "buffer_id"
    arcpy.management.AddField(in_table=lakes_simplified_lyr, field_name=id_field)

    lakes_processed_lyr = "lakes_processed_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_processed], out_layer=lakes_processed_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=lakes_simplified_lyr,
        overlap_type="INTERSECT",
        select_features=lakes_processed_lyr,
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.UpdateCursor(
        lakes_simplified_lyr, ["OID@", "SHAPE@", id_field]
    ) as ucur:
        for oid, geom, _ in ucur:
            if (oid, geom) in candidates:
                if (
                    main_geom.overlaps(geom)
                    or main_geom.contains(geom)
                    or main_geom.within(geom)
                ):
                    ucur.updateRow([oid, geom, main_oid])

    arcpy.cartography.AggregatePolygons(
        in_features=lakes_processed_lyr,
        out_feature_class=files[fc.lakes_aggregated],
        aggregation_distance=a_configs.lake_aggregation_distance,
    )

    # Sjekk om det som ble aggregert IKKE er større enn et av polygonene den koblet seg til. Hvis for stor, legg innsjø objektidene til en liste over objekter
    # som selekteres bort. Kan f.eks. være en løsning å opprette en loop som


@timing_decorator
def target_selection(files: dict) -> None:  # Må endres!
    lakes_processed_lyr = "lakes_processed_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files[fc.lakes_processed], out_layer=lakes_processed_lyr
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lakes_processed_lyr,
        selection_type="NEW_SELECTION",
        where_clause="SHAPE_Area>=1000",
    )
    arcpy.management.CopyFeatures(
        in_features=lakes_processed_lyr,
        out_feature_class=files[fc.lakes_processed_selection],
    )


if __name__ == "__main__":
    main()
