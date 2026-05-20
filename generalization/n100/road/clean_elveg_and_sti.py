##################################
### RYDDE KARTDATA MOT VEGNETT (9b) ###
##################################
"""
Steg 0: overfør Motorveg som Ida hentet fra N50
Steg 1: Buffer+intersect per medium → erase
Steg 2: Snap berørte endepunkter
Steg 3: Snap alene-endepunkter veiledet av snap_fasit (fra VegSti)
Steg 4: Split vegnett i endepunkter på edge
Steg 5: Slå sammen til elveg_and_sti
Steg 6: Unsplit
"""

import arcpy
import os

# ===== ArcPy miljø =====
gdb = r"C:\AG_inputs\Roads_raw.gdb"
arcpy.env.workspace = gdb
arcpy.env.overwriteOutput = True

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

# Steg 3
VEGSTI_FC = r"C:\AG_inputs\n50.gdb\VegSti"
EKTE_DANGLE_DIST = 50.0  # m
FASIT_RADIUS = 25.0  # m


# ===== Hjelpefunksjoner =====


def legg_til_felt(fc, feltnavn, felttype):
    if feltnavn not in [f.name for f in arcpy.ListFields(fc)]:
        arcpy.management.AddField(fc, feltnavn, felttype)


def snap_kun_endepunkter(linjer_fc, output_fc, godkjente_xy=None):
    """
    Snapper KUN første og siste punkt på hver linje. Ingen midtpunkter røres.

    godkjente_xy: set av (round(x,3), round(y,3)) som ER lov å snappe.
                  Bare ender som matcher disse XY-ene vil bli snappet.
                  Hvis None snappes alle dangle-ender (gammel oppførsel).
    """
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

    # FIX: Begrens til kun godkjente XY-er hvis oppgitt
    if godkjente_xy is not None:
        godkjente_ender_oids = set()
        with arcpy.da.SearchCursor(ender_fc, ["OID@", "SHAPE@XY"]) as cursor:
            for oid, xy in cursor:
                if (round(xy[0], 3), round(xy[1], 3)) in godkjente_xy:
                    godkjente_ender_oids.add(oid)
        print(
            f"    Godkjente ender å snappe: {len(godkjente_ender_oids)} (av {len(dangle_ender_oids)} dangles)"
        )
    else:
        godkjente_ender_oids = dangle_ender_oids

    # Near mot veg_end, veg_vertex, vegnett
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

    # Bygg ny_pos – kun godkjente dangle-ender, prioritet END > VERTEX > EDGE
    ny_pos = {}
    for ender_oid in set(
        list(near_end.keys()) + list(near_vertex.keys()) + list(near_edge.keys())
    ):
        if ender_oid not in dangle_ender_oids:
            continue
        if ender_oid not in godkjente_ender_oids:  # FIX
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


# ===== STEG 0: Oppdater motorvegtype i vegnett =====


def steg0_motorvegtype():
    print("\n[STEG 0] Oppdaterer motorvegtype i vegnett...")
    motorveg_fc = "motorveg_Ida"
    arcpy.management.MakeFeatureLayer(VEGNETT, "veg_lyr")
    arcpy.management.SelectLayerByLocation(
        "veg_lyr", "SHARE_A_LINE_SEGMENT_WITH", motorveg_fc
    )
    arcpy.management.CalculateField("veg_lyr", "motorvegtype", "'Motorveg'", "PYTHON3")
    n = int(arcpy.management.GetCount("veg_lyr")[0])
    print(f"  Oppdatert {n} veglinjer til motorvegtype = 'Motorveg'")
    arcpy.management.Delete("veg_lyr")


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
    overlap_single = "overlap_single"
    arcpy.management.Dissolve(overlap_raw, overlap_diss)
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
    n_før = int(arcpy.management.GetCount(STIER)[0])
    n_etter = int(arcpy.management.GetCount(stier_clean)[0])
    print(f"  Kartdata før: {n_før} | etter erase: {n_etter}")

    return stier_clean, overlap_big


# ===== STEG 2: Snap berørte endepunkter =====


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

    if not berørte_fids:
        print("  Ingen berørte endepunkter – hopper over snap.")
        stier_uberørt = "stier_uberørt"
        arcpy.management.CopyFeatures(stier_clean, stier_uberørt)
        return stier_uberørt, None

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

    # FIX: bygg godkjente_xy fra berørte_ender (kun disse endene skal snappes)
    godkjente_xy = set()
    with arcpy.da.SearchCursor(berørte_ender, ["SHAPE@XY"]) as cursor:
        for (xy,) in cursor:
            godkjente_xy.add((round(xy[0], 3), round(xy[1], 3)))

    stier_berørt_snappet = "stier_berørt_snappet"
    snap_kun_endepunkter("berørt_lyr", stier_berørt_snappet, godkjente_xy=godkjente_xy)
    arcpy.management.Delete("berørt_lyr")
    print(f"  Snap ferdig → lagret som: {stier_berørt_snappet}")

    return stier_uberørt, stier_berørt_snappet


# ===== Mellomtrinn: Merge =====


def mellomtrinn_merge(stier_uberørt, stier_berørt_snappet):
    print("\n[MELLOMTRINN] Merger uberørte + snappede berørte ...")
    output_fc = "kartdata_etter_snap1"
    if stier_berørt_snappet is None:
        arcpy.management.CopyFeatures(stier_uberørt, output_fc)
    else:
        arcpy.management.Merge([stier_uberørt, stier_berørt_snappet], output_fc)
    n = int(arcpy.management.GetCount(output_fc)[0])
    print(f"  Lagret: {output_fc}  ({n} linjer)")
    return output_fc


# ===== STEG 3: Snap alene-endepunkter veiledet av snap_fasit =====


def snap_alene_2m(kartdata_etter_snap1):
    print(f"\n[STEG 3] Snap alene-endepunkter veiledet av snap_fasit ...")

    # ── A) Bygg snap_fasit ────────────────────────────────────────────────────
    print("  [A] Bygger snap_fasit fra VegSti ...")

    n50_veger = "n50_veger"
    n50_veger_ender = "n50_veger_ender"
    arcpy.analysis.Select(VEGSTI_FC, n50_veger, "objtype = 'VegSenterlinje'")
    arcpy.management.FeatureVerticesToPoints(n50_veger, n50_veger_ender, "BOTH_ENDS")
    print(f"    n50_veger: {int(arcpy.management.GetCount(n50_veger)[0])} linjer")

    n50_trails = "n50_trails"
    n50_trails_ender = "n50_trails_ender"
    arcpy.analysis.Select(VEGSTI_FC, n50_trails, "objtype <> 'VegSenterlinje'")
    n_trails_før = int(arcpy.management.GetCount(n50_trails)[0])
    arcpy.management.DeleteIdentical(n50_trails, ["Shape"])
    n_trails_etter = int(arcpy.management.GetCount(n50_trails)[0])
    print(f"    n50_trails: {n_trails_før} → {n_trails_etter} etter Delete Identical")
    arcpy.management.FeatureVerticesToPoints(n50_trails, n50_trails_ender, "BOTH_ENDS")

    n50_trails_ender_count = "n50_trails_ender_count"
    arcpy.analysis.CountOverlappingFeatures(
        n50_trails_ender, n50_trails_ender_count, min_overlap_count=1
    )
    n50_trails_ender_alene = "n50_trails_ender_alene"
    arcpy.management.MakeFeatureLayer(n50_trails_ender_count, "count_lyr", "COUNT_ = 1")
    arcpy.management.CopyFeatures("count_lyr", n50_trails_ender_alene)
    arcpy.management.Delete("count_lyr")
    print(
        f"    n50_trails_ender_alene: {int(arcpy.management.GetCount(n50_trails_ender_alene)[0])}"
    )

    snap_fasit = "n50_trails_ender_alene_snapfasit"
    arcpy.management.MakeFeatureLayer(n50_trails_ender_alene, "alene_lyr")
    arcpy.management.SelectLayerByLocation(
        "alene_lyr",
        "WITHIN_A_DISTANCE",
        n50_veger_ender,
        search_distance="25 Meters",
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures("alene_lyr", snap_fasit)
    arcpy.management.Delete("alene_lyr")
    print(f"    snap_fasit: {int(arcpy.management.GetCount(snap_fasit)[0])} punkter")

    # ── B) Finn alene-ender av kartdata og snap ───────────────────────────────
    print("  [B] Finn alene-ender av kartdata_etter_snap1 ...")

    s3_alle_ender = "s3_alle_ender"
    arcpy.management.FeatureVerticesToPoints(
        kartdata_etter_snap1, s3_alle_ender, "BOTH_ENDS"
    )

    s3_join = "s3_ender_join"
    arcpy.analysis.SpatialJoin(
        s3_alle_ender,
        kartdata_etter_snap1,
        s3_join,
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        match_option="INTERSECT",
    )
    s3_alene_ender = "s3_alene_ender"
    arcpy.management.MakeFeatureLayer(s3_join, "alene_lyr", "Join_Count = 1")
    arcpy.management.CopyFeatures("alene_lyr", s3_alene_ender)
    arcpy.management.Delete("alene_lyr")
    print(
        f"    Alene-ender i kartdata: {int(arcpy.management.GetCount(s3_alene_ender)[0])}"
    )

    s3_snap_ender = "s3_snap_ender"
    arcpy.management.MakeFeatureLayer(s3_alene_ender, "fasit_lyr")
    arcpy.management.SelectLayerByLocation(
        "fasit_lyr",
        "WITHIN_A_DISTANCE",
        snap_fasit,
        search_distance=f"{FASIT_RADIUS} Meters",
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures("fasit_lyr", s3_snap_ender)
    arcpy.management.Delete("fasit_lyr")
    n_snap_ender = int(arcpy.management.GetCount(s3_snap_ender)[0])
    print(f"    Alene-ender innen {FASIT_RADIUS} m av snap_fasit: {n_snap_ender}")

    snap_fids = set()
    with arcpy.da.SearchCursor(s3_snap_ender, ["ORIG_FID"]) as cursor:
        for (fid,) in cursor:
            snap_fids.add(fid)
    print(f"    Kartdata-linjer som skal snappes: {len(snap_fids)}")

    kartdata_ferdig = "kartdata_ferdig"

    if not snap_fids:
        print("    Ingen linjer å snappe i steg 3.")
        arcpy.management.CopyFeatures(kartdata_etter_snap1, kartdata_ferdig)
    else:
        oid_felt = arcpy.Describe(kartdata_etter_snap1).oidFieldName
        fids_str = ",".join(map(str, snap_fids))

        arcpy.management.MakeFeatureLayer(
            kartdata_etter_snap1, "snap3_lyr", f"{oid_felt} IN ({fids_str})"
        )
        arcpy.management.MakeFeatureLayer(
            kartdata_etter_snap1, "rest3_lyr", f"{oid_felt} NOT IN ({fids_str})"
        )

        # FIX: bygg godkjente_xy fra s3_snap_ender – kun disse endene snappes
        godkjente_xy = set()
        with arcpy.da.SearchCursor(s3_snap_ender, ["SHAPE@XY"]) as cursor:
            for (xy,) in cursor:
                godkjente_xy.add((round(xy[0], 3), round(xy[1], 3)))

        s3_snappet = "s3_snappet"
        snap_kun_endepunkter("snap3_lyr", s3_snappet, godkjente_xy=godkjente_xy)
        arcpy.management.Delete("snap3_lyr")

        s3_rest = "s3_rest"
        arcpy.management.CopyFeatures("rest3_lyr", s3_rest)
        arcpy.management.Delete("rest3_lyr")

        arcpy.management.Merge([s3_rest, s3_snappet], kartdata_ferdig)
        print(f"    Snap ferdig for {len(snap_fids)} linjer")

    n_ferdig = int(arcpy.management.GetCount(kartdata_ferdig)[0])
    print(f"  Lagret: {kartdata_ferdig}  ({n_ferdig} linjer)")

    return kartdata_ferdig


# ===== STEG 4: Split vegnett =====


def split_vegnett(kartdata_ferdig):
    print("\n[STEG 4] Split vegnett i nye sti-endepunkter ...")

    alle_ender = "s4_alle_ender"
    arcpy.management.FeatureVerticesToPoints(kartdata_ferdig, alle_ender, "BOTH_ENDS")
    n_alle = int(arcpy.management.GetCount(alle_ender)[0])
    print(f"  Totalt endepunkter i kartdata_ferdig: {n_alle}")

    arcpy.management.MakeFeatureLayer(alle_ender, "intersect_lyr")
    arcpy.management.SelectLayerByLocation("intersect_lyr", "INTERSECT", VEGNETT)
    snap_punkter = "s4_snap_punkter"
    arcpy.management.CopyFeatures("intersect_lyr", snap_punkter)
    arcpy.management.Delete("intersect_lyr")

    n_snap = int(arcpy.management.GetCount(snap_punkter)[0])
    print(f"  Endepunkter som intersect vegnett: {n_snap}")

    n_før = int(arcpy.management.GetCount(VEGNETT)[0])
    vegnett_splittet = "vegnett_splittet"
    arcpy.management.SplitLineAtPoint(
        VEGNETT, snap_punkter, vegnett_splittet, SNAP_TOLERANSE
    )
    n_etter = int(arcpy.management.GetCount(vegnett_splittet)[0])
    print(
        f"  Vegnett før: {n_før} | etter: {n_etter} ({n_etter - n_før} nye segmenter)"
    )


# ===== STEG 5: Slå sammen til elveg_and_sti =====


def merge_til_slutt():
    print("\n[STEG 5] Slår sammen vegnett og kartdata ...")
    merge_fc = "clean_elveg_and_sti_merged"
    if arcpy.Exists(merge_fc):
        arcpy.management.Delete(merge_fc)
    arcpy.management.Merge(["vegnett_splittet", "kartdata_ferdig"], merge_fc)
    n = int(arcpy.management.GetCount(merge_fc)[0])
    print(f"  Lagret: {merge_fc} ({n} linjer)")


# ===== STEG 6: Unsplit =====


def steg6_unsplit():
    print("\n[STEG 6] Generaliserer med Unsplit per medium ...")

    INPUT = "clean_elveg_and_sti_merged"
    OUTPUT = "vegnett_generalisert"

    UNSPLIT_FIELDS = [
        "objtype",
        "subtypekode",
        "vegstatus",
        "vegkategori",
        "vegnummer",
        "typeveg",
        "vegklasse",
        "medium",
        "motorvegtype",
        "rutemerking",
        "vedlikeh",
        "uttegning",
    ]

    n_før = int(arcpy.management.GetCount(INPUT)[0])
    print(f"  Antall objekter før: {n_før}")

    outputs = []
    for m in ["T", "U", "L", "B"]:
        print(f"\n  --- Medium {m} ---")
        lyr = f"lyr_{m}"
        unsplit_fc = f"unsplit_{m}"
        f2l_fc = f"f2l_{m}"

        arcpy.management.MakeFeatureLayer(INPUT, lyr, f"medium = '{m}'")
        n_sel = int(arcpy.management.GetCount(lyr)[0])
        print(f"    Valgt: {n_sel}")

        if n_sel == 0:
            arcpy.management.Delete(lyr)
            continue

        arcpy.management.UnsplitLine(lyr, unsplit_fc, UNSPLIT_FIELDS)
        arcpy.management.FeatureToLine(unsplit_fc, f2l_fc, attributes="ATTRIBUTES")

        outputs.append(f2l_fc)
        arcpy.management.Delete(lyr)
        arcpy.management.Delete(unsplit_fc)

    print("\n  Merger alle medier...")
    arcpy.management.Merge(outputs, OUTPUT)

    n_etter = int(arcpy.management.GetCount(OUTPUT)[0])
    print(f"  Etter unsplit: {n_etter} (reduksjon: {n_før - n_etter})")

    for fc in outputs:
        arcpy.management.Delete(fc)

    return OUTPUT


# ===== Main =====


def main():
    steg0_motorvegtype()

    stier_clean, overlap_big = overlapp_og_erase()
    if stier_clean is None:
        return

    stier_uberørt, stier_berørt_snappet = snap_berørte(stier_clean, overlap_big)
    kartdata_etter_snap1 = mellomtrinn_merge(stier_uberørt, stier_berørt_snappet)
    kartdata_ferdig = snap_alene_2m(kartdata_etter_snap1)
    split_vegnett(kartdata_ferdig)
    merge_til_slutt()
    generalisert = steg6_unsplit()

    slutt_gdb = r"C:\AG_inputs\Roads_clean.gdb"
    slutt_fc = os.path.join(slutt_gdb, "elveg_and_sti")

    if arcpy.Exists(slutt_fc):
        arcpy.management.Delete(slutt_fc)

    arcpy.management.CopyFeatures(generalisert, slutt_fc)
    print(f"\n  Sluttresultat: {slutt_fc}")
    print("\n✓ Ferdig!")


if __name__ == "__main__":
    main()
