##################################
### RYDDE KARTDATA MOT VEGNETT ###
##################################
"""
Steg 1: Buffer+intersect per medium → erase
Steg 2: Snap berørte endepunkter
Steg 3: Snap alene-endepunkter innen 2 m
Steg 4: Split vegnett i endepunkter på edge
"""
import arcpy
import os
import paths

# ===== ArcPy miljø =====
working_gdb = os.path.join(paths.DATA_WORKING, "working.gdb")
arcpy.env.workspace = working_gdb
arcpy.env.overwriteOutput = True


# ===== STEG 0: SPLITT INPUT =====

INPUT_FC = r"C:\overlaps\data\input\Roads.gdb\elveg_and_sti"

VEGNETT_KODER = ["1", "2", "3", "4", "5"]
KARTDATA_KODER = [
    "Barmarksløype",
    "Gang- og Sykkelveg",
    "Traktorveg",
    "Sti",
]

VEGNETT = "vegnett"
STIER = "kartdata"


def steg0_split():
    print("\n[STEG 0] Splitt elveg_and_sti → vegnett + kartdata")

    # ===== VEGNETT =====
    vegnett_sql = "objtype = 'VegSenterlinje'"

    arcpy.conversion.ExportFeatures(INPUT_FC, VEGNETT, vegnett_sql)
    print(f"  vegnett: {int(arcpy.management.GetCount(VEGNETT)[0])} linjer")

    # ===== KARTDATA =====
    kartdata_sql = "objtype <> 'VegSenterlinje'"

    arcpy.conversion.ExportFeatures(INPUT_FC, STIER, kartdata_sql)
    print(f"  kartdata: {int(arcpy.management.GetCount(STIER)[0])} linjer")


# ===== Konfigurasjon =====
VEGNETT = "vegnett"
STIER = "kartdata"

BUFFER_DIST = "10 Meters"
AREA_LIMIT = 1200
MEDIUM_KODER = ["T", "U", "B", "L"]

SNAP_END = 15  # m
SNAP_VERTEX = 20  # m
SNAP_EDGE = 25  # m
DANGLE_DIST = 2  # m

SNAP_TOLERANSE = "0.01 Meters"


# ===== Hjelpefunksjon =====


def legg_til_felt(fc, feltnavn, felttype):
    if feltnavn not in [f.name for f in arcpy.ListFields(fc)]:
        arcpy.management.AddField(fc, feltnavn, felttype)


# ===== STEG 1: Overlapp og erase =====


def overlapp_og_erase():
    print("\n[STEG 1] Buffer og intersect per medium-verdi ...")
    overlap_per_medium = []

    for medium in MEDIUM_KODER:
        print(f"\n  Medium = '{medium}' ...")
        arcpy.management.MakeFeatureLayer(VEGNETT, "veg_lyr", f"medium = '{medium}'")
        arcpy.management.MakeFeatureLayer(STIER, "sti_lyr", f"medium = '{medium}'")

        n_veg = int(arcpy.management.GetCount("veg_lyr")[0])
        n_sti = int(arcpy.management.GetCount("sti_lyr")[0])
        print(f"    vegnett: {n_veg} linjer, kartdata: {n_sti} linjer")

        if n_veg == 0 or n_sti == 0:
            print(f"    Hopper over – ingen linjer i begge lag")
            arcpy.management.Delete("veg_lyr")
            arcpy.management.Delete("sti_lyr")
            continue

        veg_buf = f"veg_buf_{medium}_tmp"
        sti_buf = f"sti_buf_{medium}_tmp"
        arcpy.analysis.Buffer(
            "veg_lyr",
            veg_buf,
            BUFFER_DIST,
            line_end_type="FLAT",
            dissolve_option="NONE",
        )
        arcpy.analysis.Buffer(
            "sti_lyr",
            sti_buf,
            BUFFER_DIST,
            line_end_type="FLAT",
            dissolve_option="NONE",
        )
        arcpy.management.Delete("veg_lyr")
        arcpy.management.Delete("sti_lyr")

        overlap_m = f"overlap_{medium}_tmp"
        arcpy.analysis.PairwiseIntersect([veg_buf, sti_buf], overlap_m)
        n = int(arcpy.management.GetCount(overlap_m)[0])
        print(f"    Intersect: {n} polygoner")

        arcpy.management.Delete(veg_buf)
        arcpy.management.Delete(sti_buf)

        if n > 0:
            overlap_per_medium.append(overlap_m)
        else:
            arcpy.management.Delete(overlap_m)

    if not overlap_per_medium:
        print("\nIngen overlapp funnet – avslutter.")
        return None, None

    print("\n  Merger overlapp fra alle medium-verdier ...")
    overlap_raw = "overlap_raw"
    if len(overlap_per_medium) == 1:
        arcpy.management.CopyFeatures(overlap_per_medium[0], overlap_raw)
    else:
        arcpy.management.Merge(overlap_per_medium, overlap_raw)
    for tmp in overlap_per_medium:
        arcpy.management.Delete(tmp)

    overlap_diss = "overlap_diss"
    arcpy.management.Dissolve(overlap_raw, overlap_diss)

    overlap_single = "overlap_single"
    arcpy.management.MultipartToSinglepart(overlap_diss, overlap_single)

    legg_til_felt(overlap_single, "AREA_M2", "DOUBLE")
    arcpy.management.CalculateGeometryAttributes(
        overlap_single, [["AREA_M2", "AREA"]], area_unit="SQUARE_METERS"
    )
    arealer = sorted(
        [row[0] for row in arcpy.da.SearchCursor(overlap_single, ["AREA_M2"])]
    )
    print(
        f"  Totalt {len(arealer)} polygoner | "
        f"> {AREA_LIMIT} m²: {sum(1 for a in arealer if a > AREA_LIMIT)} | "
        f"min: {round(min(arealer), 1)} | maks: {round(max(arealer), 1)}"
    )

    overlap_big = "overlap_big"
    arcpy.management.MakeFeatureLayer(
        overlap_single, "overlap_lyr", f"AREA_M2 > {AREA_LIMIT}"
    )
    arcpy.management.CopyFeatures("overlap_lyr", overlap_big)
    arcpy.management.Delete("overlap_lyr")
    print(f"  overlap_big: {int(arcpy.management.GetCount(overlap_big)[0])} polygoner")

    stier_clean = "stier_clean"
    arcpy.analysis.Erase(STIER, overlap_big, stier_clean)
    arcpy.management.CopyFeatures(stier_clean, "stier_clean_backup")
    n_før = int(arcpy.management.GetCount(STIER)[0])
    n_etter = int(arcpy.management.GetCount(stier_clean)[0])
    print(f"  Kartdata før: {n_før} | etter erase: {n_etter}")

    return stier_clean, overlap_big


# ===== STEG 2: Snap berørte endepunkter =====


def snap_kun_endepunkter(linjer_fc, output_fc):
    """Snapper KUN første og siste punkt på hver linje. Ingen midtpunkter røres."""
    arcpy.management.CopyFeatures(linjer_fc, output_fc)
    sr = arcpy.Describe(output_fc).spatialReference

    ender_fc = "snap_ender_tmp"
    veg_end = "snap_veg_end_tmp"
    veg_vertex = "snap_veg_vertex_tmp"
    arcpy.management.FeatureVerticesToPoints(output_fc, ender_fc, "BOTH_ENDS")
    arcpy.management.FeatureVerticesToPoints(VEGNETT, veg_end, "BOTH_ENDS")
    arcpy.management.FeatureVerticesToPoints(VEGNETT, veg_vertex, "ALL")

    oid_felt = arcpy.Describe(output_fc).oidFieldName

    # Finn dangle-endepunkter (Join_Count = 1)
    join_tmp = "snap_join_tmp"
    arcpy.analysis.SpatialJoin(
        ender_fc,
        output_fc,
        join_tmp,
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        match_option="INTERSECT",
    )
    dangle_ender_oids = set()
    with arcpy.da.SearchCursor(join_tmp, ["OID@", "Join_Count"]) as cursor:
        for oid, count in cursor:
            if count == 1:
                dangle_ender_oids.add(oid)
    arcpy.management.Delete(join_tmp)

    n_totalt = int(arcpy.management.GetCount(ender_fc)[0])
    print(
        f"    Endepunkter totalt: {n_totalt}, dangles: {len(dangle_ender_oids)}, "
        f"hoppes over: {n_totalt - len(dangle_ender_oids)}"
    )

    # Near mot veg_end, veg_vertex, vegnett – ett kall per lag
    arcpy.analysis.Near(
        ender_fc, veg_end, f"{SNAP_END} Meters", location="LOCATION", method="PLANAR"
    )
    near_end = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(ender_fc, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        ender_fc, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    arcpy.analysis.Near(
        ender_fc,
        veg_vertex,
        f"{SNAP_VERTEX} Meters",
        location="LOCATION",
        method="PLANAR",
    )
    near_vertex = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(ender_fc, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        ender_fc, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    arcpy.analysis.Near(
        ender_fc, VEGNETT, f"{SNAP_EDGE} Meters", location="LOCATION", method="PLANAR"
    )
    near_edge = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(ender_fc, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        ender_fc, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    # Bygg ny_pos – kun for dangle-endepunkter, prioritet END > VERTEX > EDGE
    ny_pos = {}
    for ender_oid in set(
        list(near_end.keys()) + list(near_vertex.keys()) + list(near_edge.keys())
    ):
        if ender_oid not in dangle_ender_oids:
            continue
        if ender_oid in near_end and near_end[ender_oid][0] != -1:
            ny_pos[ender_oid] = near_end[ender_oid]
        elif ender_oid in near_vertex and near_vertex[ender_oid][0] != -1:
            ny_pos[ender_oid] = near_vertex[ender_oid]
        elif ender_oid in near_edge and near_edge[ender_oid][0] != -1:
            ny_pos[ender_oid] = near_edge[ender_oid]

    # Bygg dict: orig_fid → liste av (ender_oid, xy)
    fid_til_ender_oid = {}
    with arcpy.da.SearchCursor(ender_fc, ["OID@", "ORIG_FID", "SHAPE@XY"]) as cursor:
        for ender_oid, orig_fid, xy in cursor:
            fid_til_ender_oid.setdefault(orig_fid, []).append((ender_oid, xy))

    # Oppdater geometri – kun første og siste punkt
    oppdatert = 0
    with arcpy.da.UpdateCursor(output_fc, [oid_felt, "SHAPE@"]) as cursor:
        for row in cursor:
            orig_fid = row[0]
            geom = row[1]
            if orig_fid not in fid_til_ender_oid:
                continue

            ender_for_linje = fid_til_ender_oid[orig_fid]
            endret = False
            nye_deler = []

            for part in geom:
                pts = list(part)
                if not pts:
                    continue
                for idx in [0, len(pts) - 1]:
                    pt = pts[idx]
                    for ender_oid, exy in ender_for_linje:
                        if abs(pt.X - exy[0]) < 0.01 and abs(pt.Y - exy[1]) < 0.01:
                            if ender_oid in ny_pos:
                                nx, ny = ny_pos[ender_oid]
                                pts[idx] = arcpy.Point(nx, ny)
                                endret = True
                            break
                nye_deler.append(arcpy.Array(pts))

            if endret:
                row[1] = arcpy.Polyline(arcpy.Array(nye_deler), sr)
                cursor.updateRow(row)
                oppdatert += 1

    for tmp in [ender_fc, veg_end, veg_vertex]:
        if arcpy.Exists(tmp):
            arcpy.management.Delete(tmp)

    print(f"    Snappet endepunkter på {oppdatert} linjer")


def snap_berørte(stier_clean, overlap_big):
    print("\n[STEG 2] Snap berørte stier ...")

    alle_ender = "alle_ender_tmp"
    arcpy.management.FeatureVerticesToPoints(stier_clean, alle_ender, "BOTH_ENDS")

    arcpy.management.MakeFeatureLayer(alle_ender, "ender_lyr")
    arcpy.management.SelectLayerByLocation(
        "ender_lyr", "WITHIN_A_DISTANCE", overlap_big, "0.1 Meters"
    )
    berørte_ender = "sti_endepunkter_berørt"
    arcpy.management.CopyFeatures("ender_lyr", berørte_ender)
    arcpy.management.Delete("ender_lyr")
    arcpy.management.Delete(alle_ender)

    n = int(arcpy.management.GetCount(berørte_ender)[0])
    print(f"  Berørte endepunkter: {n}  → lagret som: {berørte_ender}")

    berørte_fids = set()
    with arcpy.da.SearchCursor(berørte_ender, ["ORIG_FID"]) as cursor:
        for (fid,) in cursor:
            berørte_fids.add(fid)

    oid_felt = arcpy.Describe(stier_clean).oidFieldName
    fids_str = ",".join(map(str, berørte_fids))

    arcpy.management.MakeFeatureLayer(
        stier_clean, "berørt_lyr", f"{oid_felt} IN ({fids_str})"
    )
    arcpy.management.MakeFeatureLayer(
        stier_clean, "uberørt_lyr", f"{oid_felt} NOT IN ({fids_str})"
    )

    stier_uberørt = "stier_uberørt"
    arcpy.management.CopyFeatures("uberørt_lyr", stier_uberørt)
    arcpy.management.Delete("uberørt_lyr")
    print(
        f"  Berørte: {len(berørte_fids)} | Uberørte: "
        f"{int(arcpy.management.GetCount(stier_uberørt)[0])}"
    )

    stier_berørt_snappet = "stier_berørt_snappet"
    snap_kun_endepunkter("berørt_lyr", stier_berørt_snappet)
    arcpy.management.Delete("berørt_lyr")
    print(f"  Snap ferdig → lagret som: {stier_berørt_snappet}")

    return stier_uberørt, stier_berørt_snappet


# ===== Mellomtrinn: Merge =====


def mellomtrinn_merge(stier_uberørt, stier_berørt_snappet):
    print("\n[MELLOMTRINN] Merger uberørte + snappede berørte ...")
    output_fc = "kartdata_etter_snap1"
    arcpy.management.Merge([stier_uberørt, stier_berørt_snappet], output_fc)
    n = int(arcpy.management.GetCount(output_fc)[0])
    print(f"  Lagret: {output_fc}  ({n} linjer)")
    return output_fc


# ===== STEG 3: Snap alene-endepunkter innen 2 m =====


def snap_alene_2m(kartdata_etter_snap1):
    print(f"\n[STEG 3] Finn alene-endepunkter innen {DANGLE_DIST} m og snap ...")

    alle_ender = "alle_ender2_tmp"
    arcpy.management.FeatureVerticesToPoints(
        kartdata_etter_snap1, alle_ender, "BOTH_ENDS"
    )

    join_fc = "ender_join_tmp"
    arcpy.analysis.SpatialJoin(
        alle_ender,
        kartdata_etter_snap1,
        join_fc,
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        match_option="INTERSECT",
    )
    arcpy.management.MakeFeatureLayer(join_fc, "alene_lyr", "Join_Count = 1")
    alene_ender = "alene_ender_tmp"
    arcpy.management.CopyFeatures("alene_lyr", alene_ender)
    arcpy.management.Delete("alene_lyr")
    print(
        f"  Alene endepunkter totalt: "
        f"{int(arcpy.management.GetCount(alene_ender)[0])}"
    )

    arcpy.analysis.Near(alene_ender, VEGNETT, method="PLANAR")
    legg_til_felt(alene_ender, "AVSTAND_VEGNETT", "DOUBLE")
    arcpy.management.CalculateField(
        alene_ender, "AVSTAND_VEGNETT", "!NEAR_DIST!", "PYTHON3"
    )
    arcpy.management.DeleteField(alene_ender, ["NEAR_FID", "NEAR_DIST"])

    arcpy.management.MakeFeatureLayer(
        alene_ender,
        "nær_lyr",
        f"AVSTAND_VEGNETT > 0 AND AVSTAND_VEGNETT <= {DANGLE_DIST}",
    )
    dangles_2m = "sti_dangles_2m"
    arcpy.management.CopyFeatures("nær_lyr", dangles_2m)
    arcpy.management.Delete("nær_lyr")
    n_nær = int(arcpy.management.GetCount(dangles_2m)[0])
    print(f"  Innen {DANGLE_DIST} m fra vegnett: {n_nær}  → lagret som: {dangles_2m}")

    snap2_fids = set()
    with arcpy.da.SearchCursor(dangles_2m, ["ORIG_FID"]) as cursor:
        for (fid,) in cursor:
            snap2_fids.add(fid)

    kartdata_ferdig = "kartdata_ferdig"
    if not snap2_fids:
        print("  Ingen linjer å snappe i steg 3.")
        arcpy.management.CopyFeatures(kartdata_etter_snap1, kartdata_ferdig)
    else:
        oid_felt = arcpy.Describe(kartdata_etter_snap1).oidFieldName
        fids_str = ",".join(map(str, snap2_fids))

        arcpy.management.MakeFeatureLayer(
            kartdata_etter_snap1, "snap2_lyr", f"{oid_felt} IN ({fids_str})"
        )
        arcpy.management.MakeFeatureLayer(
            kartdata_etter_snap1, "rest2_lyr", f"{oid_felt} NOT IN ({fids_str})"
        )

        snap2_snappet = "snap2_snappet_tmp"
        snap_kun_endepunkter("snap2_lyr", snap2_snappet)
        arcpy.management.Delete("snap2_lyr")

        rest2 = "rest2_tmp"
        arcpy.management.CopyFeatures("rest2_lyr", rest2)
        arcpy.management.Delete("rest2_lyr")

        arcpy.management.Merge([rest2, snap2_snappet], kartdata_ferdig)
        for tmp in [snap2_snappet, rest2]:
            arcpy.management.Delete(tmp)
        print(f"  Snap ferdig for {len(snap2_fids)} linjer")

    n_ferdig = int(arcpy.management.GetCount(kartdata_ferdig)[0])
    print(f"  Lagret: {kartdata_ferdig}  ({n_ferdig} linjer)")

    for tmp in [alle_ender, join_fc, alene_ender]:
        if arcpy.Exists(tmp):
            arcpy.management.Delete(tmp)

    return kartdata_ferdig


# ===== STEG 4: Split vegnett =====


def split_vegnett(kartdata_ferdig):
    """
    Finner endepunkter fra kartdata_ferdig som intersect med vegnett
    og splitter vegnett i disse punktene.
    Alle mellomresultater beholdes for inspeksjon.
    """
    print("\n[STEG 4] Split vegnett i nye sti-endepunkter ...")

    # Alle endepunkter av kartdata_ferdig – beholdes
    alle_ender = "s4_alle_ender"
    arcpy.management.FeatureVerticesToPoints(kartdata_ferdig, alle_ender, "BOTH_ENDS")
    n_alle = int(arcpy.management.GetCount(alle_ender)[0])
    print(f"  Totalt endepunkter i kartdata_ferdig: {n_alle}")
    print(f"  Lagret som: {alle_ender}")

    # Velg endepunkter som intersect med vegnett – beholdes
    arcpy.management.MakeFeatureLayer(alle_ender, "intersect_lyr")
    arcpy.management.SelectLayerByLocation("intersect_lyr", "INTERSECT", VEGNETT)
    snap_punkter = "s4_snap_punkter"
    arcpy.management.CopyFeatures("intersect_lyr", snap_punkter)
    arcpy.management.Delete("intersect_lyr")

    n_snap = int(arcpy.management.GetCount(snap_punkter)[0])
    print(f"  Endepunkter som intersect vegnett: {n_snap}")
    print(f"  Lagret som: {snap_punkter}")

    # Split
    n_før = int(arcpy.management.GetCount(VEGNETT)[0])
    vegnett_splittet = "vegnett_splittet"
    arcpy.management.SplitLineAtPoint(
        VEGNETT, snap_punkter, vegnett_splittet, SNAP_TOLERANSE
    )
    n_etter = int(arcpy.management.GetCount(vegnett_splittet)[0])
    print(f"  Vegnett før:   {n_før} linjer")
    print(f"  Vegnett etter: {n_etter} linjer  ({n_etter - n_før} nye segmenter)")
    print(f"  Lagret som: {vegnett_splittet}")


# ===== Main =====


def main():
    steg0_split()  # ← NYTT STEG
    stier_clean, overlap_big = overlapp_og_erase()
    if stier_clean is None:
        return

    stier_uberørt, stier_berørt_snappet = snap_berørte(stier_clean, overlap_big)
    kartdata_etter_snap1 = mellomtrinn_merge(stier_uberørt, stier_berørt_snappet)
    kartdata_ferdig = snap_alene_2m(kartdata_etter_snap1)
    split_vegnett(kartdata_ferdig)

    print("\n✓ Ferdig! Datasett i working.gdb:")
    print(f"  overlap_big              – overlapp-polygoner")
    print(f"  stier_clean              – kartdata etter erase")
    print(f"  stier_clean_backup       – backup av stier_clean")
    print(f"  sti_endepunkter_berørt   – endepunkter berørt av erase")
    print(f"  stier_uberørt            – linjer ikke berørt av erase")
    print(f"  stier_berørt_snappet     – berørte linjer etter snap")
    print(f"  kartdata_etter_snap1     – mellomtrinn: uberørt + snap1")
    print(f"  sti_dangles_2m           – alene-endepunkter innen 2 m fra vegnett")
    print(f"  kartdata_ferdig          – sluttresultat kartdata")
    print(f"  s4_alle_ender            – alle endepunkter fra kartdata_ferdig")
    print(f"  s4_snap_punkter          – endepunkter som intersect vegnett")
    print(f"  vegnett_splittet         – vegnett med nye noder")


# ===== Kjør main =====
if __name__ == "__main__":
    main()
