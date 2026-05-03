"""
generaliser_anleggspunkt.py
"""

import arcpy
import os
import math

# =============================================================================
# STIER
# =============================================================================
N100_GDB = r"D:\Data\N100K\N100k.gdb"
N50_GDB = r"D:\Data\N50K\N50K.gdb"
working_gdb = r"D:\Data\Arbeidsfiler\AnleggsPunkt\AP.gdb"

# =============================================================================
# ARCPY MILJØ
# =============================================================================
arcpy.env.workspace = working_gdb
arcpy.env.overwriteOutput = True

# =============================================================================
# PARAMETERE
# =============================================================================
AGG_AVSTAND: dict[str, int] = {
    "Campingplass": 150,
    "Golfbane": 200,
    "Gruve": 150,
    "Hoppbake": 140,
    "MastTele": 150,
    "Navigasjonsinstallasjon": 150,
    "Parkeringsområde": 170,
    "SpesiellDetalj": 80,
    "Tank": 60,
    "Tårn": 140,
    "Vindkraft": 180,
}

MIN_VEGAVSTAND: dict[str, int] = {
    "Campingplass": 75,
    "Golfbane": 100,
    "Gruve": 75,
    "Hoppbake": 70,
    "MastTele": 75,
    "Navigasjonsinstallasjon": 75,
    "Parkeringsområde": 85,
    "SpesiellDetalj": 40,
    "Tank": 30,
    "Tårn": 70,
    "Vindkraft": 90,
}
DEFAULT_VEGAVSTAND = 50


# =============================================================================
# HJELPEFUNKSJONER
# =============================================================================


def _felt_finnes(fc: str, feltnavn: str) -> bool:
    return feltnavn in [f.name for f in arcpy.ListFields(fc)]


def legg_til_felt(fc: str, feltnavn: str, felttype: str) -> None:
    if not _felt_finnes(fc, feltnavn):
        arcpy.management.AddField(fc, feltnavn, felttype)


def _euklidsk_avstand(p1: tuple, p2: tuple) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


# =============================================================================
# STEG 1 – KOPIERING
# =============================================================================


def kopiere() -> None:
    arcpy.management.CopyFeatures(os.path.join(N100_GDB, "VegSti"), "VegSti")
    arcpy.management.CopyFeatures(os.path.join(N50_GDB, "AnleggsPunkt"), "AnleggsPunkt")
    print("Steg 1 ferdig: Data kopiert til working.gdb")


# =============================================================================
# STEG 2 – FINN ISOLERTE VS. TETTE PUNKTER
# =============================================================================


def finn_isolerte(buffer_dist: int = 600) -> None:
    analyse_fc = "AnleggsPunkt_for_analysis"
    near_table_fc = os.path.join(working_gdb, "NearTable")

    arcpy.management.CopyFeatures("AnleggsPunkt", analyse_fc)

    if arcpy.Exists(near_table_fc):
        arcpy.management.Delete(near_table_fc)

    arcpy.analysis.GenerateNearTable(
        in_features=analyse_fc,
        near_features=analyse_fc,
        out_table=near_table_fc,
        search_radius=f"{buffer_dist} Meters",
        closest="ALL",
        method="PLANAR",
    )

    oid_felt = arcpy.Describe(analyse_fc).oidFieldName
    oids_med_nabo = {
        row[0]
        for row in arcpy.da.SearchCursor(near_table_fc, ["IN_FID", "NEAR_FID"])
        if row[0] != row[1]
    }

    if oids_med_nabo:
        oids_str = ",".join(map(str, oids_med_nabo))
        isolert_query = f"{oid_felt} NOT IN ({oids_str})"
        dense_query = f"{oid_felt} IN ({oids_str})"
    else:
        isolert_query = "1=1"
        dense_query = "1=0"

    arcpy.MakeFeatureLayer_management(analyse_fc, "isolert_lyr", isolert_query)
    arcpy.CopyFeatures_management("isolert_lyr", "AnleggsPunkt_Isolert")

    arcpy.MakeFeatureLayer_management(analyse_fc, "dense_lyr", dense_query)
    arcpy.CopyFeatures_management("dense_lyr", "AnleggsPunkt_Dense")

    print(f"Steg 2 ferdig: {len(oids_med_nabo)} tette punkter, resten isolerte.")


# =============================================================================
# STEG 3 – AGGREGER TETTE PUNKTER
# =============================================================================


def aggreger_dense() -> None:
    input_fc = "AnleggsPunkt_Dense"
    output_fc = "AnleggsPunkt_Dense_Aggregert"

    arcpy.management.CopyFeatures(input_fc, output_fc)
    legg_til_felt(output_fc, "COUNT", "SHORT")

    felter = ["OID@", "SHAPE@XY", "objtype", "subtypekode", "COUNT"]
    punkter_per_type: dict[tuple, list[dict]] = {}

    with arcpy.da.SearchCursor(output_fc, felter) as cursor:
        for row in cursor:
            key = (row[2], row[3])
            punkter_per_type.setdefault(key, []).append(
                {"oid": row[0], "xy": row[1], "count": 1, "merged": False}
            )

    for (objtype, _), punkter in punkter_per_type.items():
        terskel = AGG_AVSTAND.get(objtype, 100)
        endring = True
        while endring:
            endring = False
            aktive = [p for p in punkter if not p["merged"]]
            for i, p1 in enumerate(aktive):
                for p2 in aktive[i + 1 :]:
                    if _euklidsk_avstand(p1["xy"], p2["xy"]) <= terskel:
                        total = p1["count"] + p2["count"]
                        p1["xy"] = (
                            (p1["xy"][0] * p1["count"] + p2["xy"][0] * p2["count"])
                            / total,
                            (p1["xy"][1] * p1["count"] + p2["xy"][1] * p2["count"])
                            / total,
                        )
                        p1["count"] = total
                        p2["merged"] = True
                        endring = True
                        break
                if endring:
                    break

    alle_gjenværende = {
        p["oid"]: p for pts in punkter_per_type.values() for p in pts if not p["merged"]
    }
    alle_merged_oids = [
        p["oid"] for pts in punkter_per_type.values() for p in pts if p["merged"]
    ]

    with arcpy.da.UpdateCursor(output_fc, felter) as cursor:
        for row in cursor:
            oid = row[0]
            if oid in alle_gjenværende:
                p = alle_gjenværende[oid]
                row[1] = p["xy"]
                row[4] = p["count"]
                cursor.updateRow(row)

    if alle_merged_oids:
        oid_felt = arcpy.Describe(output_fc).oidFieldName
        oids_str = ",".join(map(str, alle_merged_oids))
        arcpy.MakeFeatureLayer_management(
            output_fc, "slett_lyr", f"{oid_felt} IN ({oids_str})"
        )
        arcpy.management.DeleteFeatures("slett_lyr")
        arcpy.management.Delete("slett_lyr")

    print(
        f"Steg 3 ferdig: {len(alle_gjenværende)} aggregerte punkter lagret som {output_fc}"
    )


# =============================================================================
# STEG 4 – IDENTIFISER VEGKONFLIKT
# =============================================================================


def identifiser_vegkonflikt(input_fc: str, veg_fc: str, output_fc: str) -> list[int]:
    arcpy.management.CopyFeatures(input_fc, output_fc)
    legg_til_felt(output_fc, "MIN_VEGAVSTAND", "SHORT")
    legg_til_felt(output_fc, "AVSTAND_TIL_VEG", "DOUBLE")
    legg_til_felt(output_fc, "MANGLER_M", "DOUBLE")

    arcpy.analysis.Near(output_fc, veg_fc, method="PLANAR")

    konflikt_oids = []
    felter = [
        "OID@",
        "objtype",
        "MIN_VEGAVSTAND",
        "AVSTAND_TIL_VEG",
        "MANGLER_M",
        "NEAR_DIST",
    ]

    with arcpy.da.UpdateCursor(output_fc, felter) as cursor:
        for row in cursor:
            objtype = row[1]
            krav = MIN_VEGAVSTAND.get(objtype, DEFAULT_VEGAVSTAND)
            faktisk = row[5] if row[5] >= 0 else 9999
            mangler = round(krav - faktisk, 1)
            row[2] = krav
            row[3] = round(faktisk, 1)
            row[4] = mangler if mangler > 0 else 0
            cursor.updateRow(row)
            if faktisk < krav:
                konflikt_oids.append(row[0])

    for felt in ["NEAR_FID", "NEAR_DIST"]:
        if _felt_finnes(output_fc, felt):
            arcpy.management.DeleteField(output_fc, felt)

    if konflikt_oids:
        oid_felt = arcpy.Describe(output_fc).oidFieldName
        oids_str = ",".join(map(str, konflikt_oids))
        konflikt_fc = output_fc + "_Konflikt"
        arcpy.management.MakeFeatureLayer(
            output_fc, "konflikt_lyr", f"{oid_felt} IN ({oids_str})"
        )
        arcpy.management.CopyFeatures("konflikt_lyr", konflikt_fc)
        arcpy.management.Delete("konflikt_lyr")
        print(f"  Konfliktpunkter lagret som: {konflikt_fc}")

    total = int(arcpy.management.GetCount(output_fc)[0])
    n_konflikt = len(konflikt_oids)
    pst = round(n_konflikt / total * 100, 1) if total else 0
    print(f"  {input_fc}: {total} punkter totalt, {n_konflikt} for nær veg ({pst} %)")

    return konflikt_oids


# =============================================================================
# STEG 5 – FLYTT PUNKTER BORT FRA VEG
# =============================================================================


def flytt_fra_veg(input_fc: str, veg_fc: str) -> None:
    konflikt_oids = [
        row[0]
        for row in arcpy.da.SearchCursor(input_fc, ["OID@", "MANGLER_M"])
        if row[1] > 0
    ]

    if not konflikt_oids:
        print("  Ingen konfliktpunkter å flytte.")
        return

    oid_felt = arcpy.Describe(input_fc).oidFieldName
    oids_str = ",".join(map(str, konflikt_oids))
    arcpy.management.MakeFeatureLayer(
        input_fc, "flytt_lyr", f"{oid_felt} IN ({oids_str})"
    )

    maks_krav = max(MIN_VEGAVSTAND.values())
    extent = arcpy.Describe("flytt_lyr").extent
    klipp_rect = arcpy.Extent(
        extent.XMin - maks_krav,
        extent.YMin - maks_krav,
        extent.XMax + maks_krav,
        extent.YMax + maks_krav,
    )

    veg_lokal = "VegSti_lokal_tmp"
    arcpy.management.MakeFeatureLayer(veg_fc, "veg_lyr")
    arcpy.management.SelectLayerByLocation("veg_lyr", "INTERSECT", klipp_rect.polygon)
    arcpy.management.CopyFeatures("veg_lyr", veg_lokal)
    arcpy.management.Delete("veg_lyr")

    n_veg = int(arcpy.management.GetCount(veg_lokal)[0])
    n_tot = int(arcpy.management.GetCount(veg_fc)[0])
    print(f"  Bruker {n_veg} lokale vegsegmenter (av totalt {n_tot}).")

    arcpy.analysis.Near("flytt_lyr", veg_lokal, location=True, method="PLANAR")

    flyttet = 0
    felter = [
        "OID@",
        "SHAPE@XY",
        "objtype",
        "NEAR_X",
        "NEAR_Y",
        "AVSTAND_TIL_VEG",
        "MANGLER_M",
    ]

    with arcpy.da.UpdateCursor("flytt_lyr", felter) as cursor:
        for row in cursor:
            objtype = row[2]
            krav = MIN_VEGAVSTAND.get(objtype, DEFAULT_VEGAVSTAND)
            px, py = row[1]
            nx, ny = row[3], row[4]
            dx = px - nx
            dy = py - ny
            d = math.hypot(dx, dy)
            if d < 0.001:
                dx, dy = krav, 0.0
            else:
                dx = dx / d * krav
                dy = dy / d * krav
            row[1] = (nx + dx, ny + dy)
            row[5] = krav
            row[6] = 0.0
            cursor.updateRow(row)
            flyttet += 1

    arcpy.management.Delete("flytt_lyr")
    arcpy.management.Delete(veg_lokal)

    for felt in ["NEAR_FID", "NEAR_DIST", "NEAR_X", "NEAR_Y"]:
        if _felt_finnes(input_fc, felt):
            arcpy.management.DeleteField(input_fc, felt)

    print(f"  Steg 5: Flyttet {flyttet} punkter bort fra veg.")


# =============================================================================
# STEG 6 – DOKUMENTASJONSLAG ETTER FLYTTING
# =============================================================================


def lag_etter_konflikt(output_fc: str) -> None:
    etter_fc = output_fc + "_Etter_Flytting"
    arcpy.management.CopyFeatures(output_fc, etter_fc)
    legg_til_felt(etter_fc, "FLYTTET", "SHORT")

    n_flyttet = 0
    felter = ["AVSTAND_TIL_VEG", "MIN_VEGAVSTAND", "MANGLER_M", "FLYTTET"]

    with arcpy.da.UpdateCursor(etter_fc, felter) as cursor:
        for row in cursor:
            ble_flyttet = row[0] == row[1] and row[2] == 0.0
            row[3] = 1 if ble_flyttet else 0
            cursor.updateRow(row)
            if ble_flyttet:
                n_flyttet += 1

    print(
        f"  Steg 6: Dokumentasjonslag lagret som {etter_fc} ({n_flyttet} punkter merket som flyttet)"
    )


# =============================================================================
# STEG 7 – SLÅING AV DATASETT
# =============================================================================


def slaa_sammen() -> None:
    output_fc = "AnleggsPunkt_n100"

    for fc, kilde in [
        ("AnleggsPunkt_Isolert_Veg", "isolert"),
        ("AnleggsPunkt_Aggregert_Veg", "aggregert"),
    ]:
        legg_til_felt(fc, "KILDE", "TEXT")
        arcpy.management.CalculateField(fc, "KILDE", f'"{kilde}"', "PYTHON3")

    arcpy.management.Merge(
        ["AnleggsPunkt_Isolert_Veg", "AnleggsPunkt_Aggregert_Veg"],
        output_fc,
    )

    total = int(arcpy.management.GetCount(output_fc)[0])
    n_isolert = sum(
        1 for r in arcpy.da.SearchCursor(output_fc, ["KILDE"]) if r[0] == "isolert"
    )
    n_aggregert = total - n_isolert
    print(
        f"\nSteg 7 ferdig: {total} punkter lagret som {output_fc} ({n_isolert} isolerte, {n_aggregert} aggregerte)"
    )


# =============================================================================
# STEG 8 – LØSNING AV TÅRN/MASTTELE-KONFLIKTER
# =============================================================================


def fiks_tårn_masttele_konflikt(
    veg_fc: str, min_avstand: int = 145, maks_iter: int = 3
) -> None:
    fc = "AnleggsPunkt_n100"
    krav = {"Tårn": 70, "MastTele": 75}
    sr = arcpy.Describe(fc).spatialReference

    extent = arcpy.Describe(fc).extent
    margin = max(krav.values()) * 2
    arcpy.management.MakeFeatureLayer(veg_fc, "veg_lyr_t")
    arcpy.management.SelectLayerByLocation(
        "veg_lyr_t",
        "INTERSECT",
        arcpy.Extent(
            extent.XMin - margin,
            extent.YMin - margin,
            extent.XMax + margin,
            extent.YMax + margin,
        ).polygon,
    )
    veg_lokal = "VegSti_tårn_tmp"
    arcpy.management.CopyFeatures("veg_lyr_t", veg_lokal)
    arcpy.management.Delete("veg_lyr_t")

    def nærmeste_vegpunkt(pt_geom):
        min_d, nx, ny = float("inf"), None, None
        with arcpy.da.SearchCursor(veg_lokal, ["SHAPE@"]) as vc:
            for (veg,) in vc:
                snap = veg.queryPointAndDistance(pt_geom)[0]
                d = pt_geom.distanceTo(snap)
                if d < min_d:
                    min_d = d
                    nx, ny = snap.firstPoint.X, snap.firstPoint.Y
        return nx, ny, min_d

    def juster_for_veg(px, py, objtype):
        pt_geom = arcpy.PointGeometry(arcpy.Point(px, py), sr)
        nx, ny, d = nærmeste_vegpunkt(pt_geom)
        vegkrav = krav.get(objtype, DEFAULT_VEGAVSTAND)
        if d >= vegkrav or nx is None:
            return px, py
        if d < 0.001:
            return px + vegkrav, py
        fak = vegkrav / d
        return nx + (px - nx) * fak, ny + (py - ny) * fak

    for iterasjon in range(1, maks_iter + 1):
        pts: dict[int, dict] = {}
        with arcpy.da.SearchCursor(
            fc,
            ["OID@", "SHAPE@XY", "objtype"],
            where_clause="objtype IN ('Tårn', 'MastTele')",
        ) as cursor:
            for oid, xy, ot in cursor:
                pts[oid] = {"xy": xy, "objtype": ot}

        konflikter = []
        for oid_t, pt in pts.items():
            if pt["objtype"] != "Tårn":
                continue
            for oid_m, pm in pts.items():
                if pm["objtype"] != "MastTele":
                    continue
                dx = pt["xy"][0] - pm["xy"][0]
                dy = pt["xy"][1] - pm["xy"][1]
                d = math.hypot(dx, dy)
                if d < min_avstand:
                    konflikter.append((oid_t, oid_m, dx, dy, d))

        if not konflikter:
            print(f"  Iterasjon {iterasjon}: ingen konflikter gjenstår.")
            break

        print(f"  Iterasjon {iterasjon}: {len(konflikter)} Tårn/MastTele-konflikter.")

        oppdater: dict[int, tuple[float, float]] = {}
        for oid_t, oid_m, dx, dy, d in konflikter:
            mangler = min_avstand - d
            if d < 0.001:
                dx, dy, d = 1.0, 0.0, 1.0
            steg = mangler / 2.0
            tx, ty = pts[oid_t]["xy"]
            mx, my = pts[oid_m]["xy"]
            ny_tx = tx + (dx / d) * steg
            ny_ty = ty + (dy / d) * steg
            ny_mx = mx - (dx / d) * steg
            ny_my = my - (dy / d) * steg
            ny_tx, ny_ty = juster_for_veg(ny_tx, ny_ty, "Tårn")
            ny_mx, ny_my = juster_for_veg(ny_mx, ny_my, "MastTele")
            oppdater[oid_t] = (ny_tx, ny_ty)
            oppdater[oid_m] = (ny_mx, ny_my)

        oid_felt = arcpy.Describe(fc).oidFieldName
        oids_str = ",".join(map(str, oppdater))
        arcpy.management.MakeFeatureLayer(
            fc, "oppdater_lyr", f"{oid_felt} IN ({oids_str})"
        )
        with arcpy.da.UpdateCursor("oppdater_lyr", ["OID@", "SHAPE@XY"]) as cursor:
            for row in cursor:
                if row[0] in oppdater:
                    row[1] = oppdater[row[0]]
                    cursor.updateRow(row)
        arcpy.management.Delete("oppdater_lyr")
    else:
        print(
            f"  OBS: Nådde maks {maks_iter} iterasjoner – noen konflikter kan gjenstå."
        )

    arcpy.management.Delete(veg_lokal)
    print("  Steg 8 ferdig: Tårn/MastTele-konfliktsjekk fullført.")


# =============================================================================
# STEG 9 – LAGRE ENDELIG RESULTAT
# =============================================================================


def lagre_endelig() -> None:
    output_fc = os.path.join(N100_GDB, "AnleggsPunkt")
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)
    arcpy.management.CopyFeatures("AnleggsPunkt_n100", output_fc)
    n = int(arcpy.management.GetCount(output_fc)[0])
    print(f"\nSteg 9 ferdig: {n} punkter lagret som {output_fc}")


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    print("=" * 60)
    print("Starter generalisering av AnleggsPunkt (N50 → N100)")
    print("=" * 60)

    kopiere()
    finn_isolerte(buffer_dist=600)
    aggreger_dense()

    veg_fc = "VegSti"

    for input_fc, output_fc in [
        ("AnleggsPunkt_Isolert", "AnleggsPunkt_Isolert_Veg"),
        ("AnleggsPunkt_Dense_Aggregert", "AnleggsPunkt_Aggregert_Veg"),
    ]:
        print(f"\n--- Vegsjekk: {input_fc} ---")
        konflikt_oids = identifiser_vegkonflikt(input_fc, veg_fc, output_fc)
        if konflikt_oids:
            flytt_fra_veg(output_fc, veg_fc)
            lag_etter_konflikt(output_fc)
        else:
            print("  Ingen punkter å flytte.")

    slaa_sammen()
    fiks_tårn_masttele_konflikt(veg_fc, maks_iter=3)
    lagre_endelig()

    print("\n" + "=" * 60)
    print("Generalisering ferdig.")
    print("=" * 60)



if __name__ == "__main__":
    main()
