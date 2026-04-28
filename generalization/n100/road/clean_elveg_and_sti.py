##################################
### RYDDE KARTDATA MOT VEGNETT ###
##################################
"""
Steg 0: overfør Motorveg som Ida hentet fra N50
Steg 1: Buffer+intersect per medium → erase
Steg 2: Snap berørte endepunkter
Steg 3: Snap alene-endepunkter
Steg 4: Splitt vegnett ved snap
Steg 5: Merge og lag (CLEAN!) elveg_and_sti
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


# ===== Hjelpefunksjon =====
def legg_til_felt(fc, feltnavn, felttype):
    if feltnavn not in [f.name for f in arcpy.ListFields(fc)]:
        arcpy.management.AddField(fc, feltnavn, felttype)


# ===== STEG 0: Oppdater motorvegtype i vegnett =====
def steg0_motorvegtype():
    print("\n[STEG 0] Oppdaterer motorvegtype i vegnett...")
    motorveg_fc = r"C:\AG_inputs\Roads_raw4.gdb\motorveg_Ida"
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

    # FIX 4: håndter tom berørte_fids
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

    stier_berørt_snappet = "stier_berørt_snappet"
    snap_kun_endepunkter("berørt_lyr", stier_berørt_snappet)
    arcpy.management.Delete("berørt_lyr")
    print(f"  Snap ferdig → lagret som: {stier_berørt_snappet}")

    return stier_uberørt, stier_berørt_snappet


# ===== Mellomtrinn: Merge =====
def mellomtrinn_merge(stier_uberørt, stier_berørt_snappet):
    print("\n[MELLOMTRINN] Merger uberørte + snappede berørte ...")
    output_fc = "kartdata_etter_snap1"

    # FIX 4 følge-opp: håndter at stier_berørt_snappet kan være None
    if stier_berørt_snappet is None:
        arcpy.management.CopyFeatures(stier_uberørt, output_fc)
    else:
        arcpy.management.Merge([stier_uberørt, stier_berørt_snappet], output_fc)

    n = int(arcpy.management.GetCount(output_fc)[0])
    print(f"  Lagret: {output_fc}  ({n} linjer)")
    return output_fc


# ===== STEG 3: Snap alene-endepunkter til vegnett =====
def snap_alene_ender(kartdata_etter_snap1):
    print("\n[STEG 3] Snap alene-endepunkter til vegnett...")

    alle_ender = "s3_alle_ender_tmp"
    arcpy.management.FeatureVerticesToPoints(
        kartdata_etter_snap1, alle_ender, "BOTH_ENDS"
    )

    overlap = "s3_overlap_tmp"
    arcpy.analysis.CountOverlappingFeatures(alle_ender, overlap)

    arcpy.management.MakeFeatureLayer(overlap, "alene_lyr", "COUNT_ = 1")
    alene_ender = "s3_alene_ender"
    arcpy.management.CopyFeatures("alene_lyr", alene_ender)
    arcpy.management.Delete("alene_lyr")

    print(f"  Alene endepunkter: {int(arcpy.management.GetCount(alene_ender)[0])}")

    arcpy.management.MakeFeatureLayer(alene_ender, "nær_veg_lyr")
    arcpy.management.SelectLayerByLocation(
        "nær_veg_lyr", "WITHIN_A_DISTANCE", VEGNETT, "25 Meters"
    )
    ender_nær_veg = "s3_ender_nar_veg"
    arcpy.management.CopyFeatures("nær_veg_lyr", ender_nær_veg)
    arcpy.management.Delete("nær_veg_lyr")
    n_nær_veg = int(arcpy.management.GetCount(ender_nær_veg)[0])
    print(f"  Innen 25 m fra vegnett: {n_nær_veg}")

    arcpy.management.MakeFeatureLayer(ender_nær_veg, "snap_ok_lyr")
    arcpy.management.SelectLayerByLocation(
        "snap_ok_lyr", "WITHIN_A_DISTANCE", "n50_snapfasit", "25 Meters"
    )
    snap_ender_ok = "s3_snap_ender_ok"
    arcpy.management.CopyFeatures("snap_ok_lyr", snap_ender_ok)
    arcpy.management.Delete("snap_ok_lyr")
    n_ok = int(arcpy.management.GetCount(snap_ender_ok)[0])
    print(f"  Endepunkter som kan snappes: {n_ok}")

    if n_ok == 0:
        print("  Ingen ender å snappe.")
        out = "kartdata_ferdig"
        arcpy.management.CopyFeatures(kartdata_etter_snap1, out)
        # FIX 2/3: rydd opp også ved tidlig retur
        for tmp in [alle_ender, overlap, alene_ender, ender_nær_veg, snap_ender_ok]:
            if arcpy.Exists(tmp):
                arcpy.management.Delete(tmp)
        return out

    print("  Lager lokalt vegnett-utvalg...")
    arcpy.management.MakeFeatureLayer(VEGNETT, "veg_lyr")
    arcpy.management.SelectLayerByLocation(
        "veg_lyr", "WITHIN_A_DISTANCE", snap_ender_ok, "30 Meters"
    )
    veg_local = "s3_veg_local"
    arcpy.management.CopyFeatures("veg_lyr", veg_local)
    arcpy.management.Delete("veg_lyr")
    print(f"  Veglinjer brukt: {int(arcpy.management.GetCount(veg_local)[0])}")

    veg_end = "s3_veg_end_tmp"
    veg_vertex = "s3_veg_vertex_tmp"
    arcpy.management.FeatureVerticesToPoints(veg_local, veg_end, "BOTH_ENDS")
    arcpy.management.FeatureVerticesToPoints(veg_local, veg_vertex, "ALL")

    print("  Kjører Near analyser...")

    arcpy.analysis.Near(
        snap_ender_ok, veg_end, "25 Meters", location="LOCATION", method="PLANAR"
    )
    near_end = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(snap_ender_ok, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        snap_ender_ok, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    arcpy.analysis.Near(
        snap_ender_ok, veg_vertex, "25 Meters", location="LOCATION", method="PLANAR"
    )
    near_vertex = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(snap_ender_ok, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        snap_ender_ok, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    arcpy.analysis.Near(
        snap_ender_ok, VEGNETT, "25 Meters", location="LOCATION", method="PLANAR"
    )
    near_edge = {
        row[0]: (row[1], row[2])
        for row in arcpy.da.SearchCursor(snap_ender_ok, ["OID@", "NEAR_X", "NEAR_Y"])
        if row[1] is not None and row[1] != -1
    }
    arcpy.management.DeleteField(
        snap_ender_ok, ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]
    )

    ny_pos = {}
    for oid in set(list(near_end) + list(near_vertex) + list(near_edge)):
        if oid in near_end:
            ny_pos[oid] = near_end[oid]
        elif oid in near_vertex:
            ny_pos[oid] = near_vertex[oid]
        elif oid in near_edge:
            ny_pos[oid] = near_edge[oid]
    print(f"  Snap-punkter funnet: {len(ny_pos)}")

    snap_xy = set()
    with arcpy.da.SearchCursor(snap_ender_ok, ["OID@", "SHAPE@XY"]) as cur:
        for oid, xy in cur:
            if oid in ny_pos:
                snap_xy.add((round(xy[0], 3), round(xy[1], 3)))

    out_fc = "kartdata_ferdig"
    arcpy.management.CopyFeatures(kartdata_etter_snap1, out_fc)
    sr = arcpy.Describe(out_fc).spatialReference

    snappet_linjer = 0
    with arcpy.da.UpdateCursor(out_fc, ["SHAPE@"]) as cur:
        for row in cur:
            geom = row[0]
            if not geom:
                continue

            part = geom.getPart(0)
            pts = [part.getObject(i) for i in range(part.count)]
            endret = False

            first_xy = (round(pts[0].X, 3), round(pts[0].Y, 3))
            last_xy = (round(pts[-1].X, 3), round(pts[-1].Y, 3))

            if first_xy in snap_xy:
                for oid, xy in ny_pos.items():
                    if abs(xy[0] - pts[0].X) < 0.01 and abs(xy[1] - pts[0].Y) < 0.01:
                        pts[0] = arcpy.Point(xy[0], xy[1])
                        endret = True
                        break

            if last_xy in snap_xy:
                for oid, xy in ny_pos.items():
                    if abs(xy[0] - pts[-1].X) < 0.01 and abs(xy[1] - pts[-1].Y) < 0.01:
                        pts[-1] = arcpy.Point(xy[0], xy[1])
                        endret = True
                        break

            if endret:
                row[0] = arcpy.Polyline(arcpy.Array(pts), sr)
                cur.updateRow(row)
                snappet_linjer += 1

    print(f"  Snappet linjer: {snappet_linjer}")

    # FIX 2/3: cleanup flyttet før return, inkl. snap_ender_ok og veg_local
    for tmp in [
        alle_ender,
        overlap,
        alene_ender,
        ender_nær_veg,
        snap_ender_ok,
        veg_local,
        veg_end,
        veg_vertex,
    ]:
        if arcpy.Exists(tmp):
            arcpy.management.Delete(tmp)

    return out_fc


# ===== STEG 4: Split vegnett =====
def split_vegnett():
    print("\n[STEG 4] Split vegnett i nye sti-endepunkter ...")
    kartdata_ferdig = "kartdata_ferdig"
    sti_ferdig = "sti_ferdig"

    # FIX 6: lag layer før SelectLayerByAttribute
    arcpy.management.MakeFeatureLayer(kartdata_ferdig, "kartdata_lyr")
    arcpy.management.SelectLayerByAttribute(
        "kartdata_lyr", "NEW_SELECTION", "OBJTYPE='Sti'"
    )
    arcpy.management.CopyFeatures("kartdata_lyr", sti_ferdig)
    arcpy.management.Delete("kartdata_lyr")

    alle_ender = "s4_alle_ender"
    arcpy.management.FeatureVerticesToPoints(sti_ferdig, alle_ender, "BOTH_ENDS")
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
    output_gdb = r"C:\AG_inputs\Roads_test.gdb"
    output_fc = os.path.join(output_gdb, "elveg_and_sti")

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    arcpy.management.Merge(["vegnett_splittet", "kartdata_ferdig"], output_fc)
    n = int(arcpy.management.GetCount(output_fc)[0])
    print(f"  Lagret: {output_fc} ({n} linjer)")


# ===== MAIN =====
def main():
    print("\n===== STARTER PROSESS =====")

    steg0_motorvegtype()

    stier_clean, overlap_big = overlapp_og_erase()
    if stier_clean is None:
        print("Ingen overlapp funnet – stopper.")
        return

    stier_uberørt, stier_berørt_snappet = snap_berørte(stier_clean, overlap_big)

    kartdata_etter_snap1 = mellomtrinn_merge(stier_uberørt, stier_berørt_snappet)

    kartdata_ferdig = snap_alene_ender(kartdata_etter_snap1)
    print(f"\nFerdig → {kartdata_ferdig}")

    split_vegnett()
    merge_til_slutt()  # FIX 5: kall som manglet


if __name__ == "__main__":
    main()
