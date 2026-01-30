# Libraries

import arcpy

from collections import defaultdict, deque
from tqdm import tqdm

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_facilities import Facility_N10
from input_data import input_n10

# ========================
# Program
# ========================


@timing_decorator
def main():
    """
    The main program for updating the railroad attributes in FKB.
    """
    environment_setup.main()
    print("\nUpdates railroad attributes in FKB...\n")

    # Sets up work file manager and creates temporarily files
    working_fc = Facility_N10.railroad__n10_facility.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files)
    create_buffers(files=files)
    intersect_fkb_n50(files=files)
    small_buffer = build_railroad_network_fkb_safe(files=files)
    collect_unusable_railroads(files=files, small_buffer=small_buffer)
    update_railroad_attributes(files=files)

    # wfm.delete_created_files()

    print("\nRailroad attributes updated!\n")


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of fixing attribute data for railroad.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    railroad_N50_N = wfm.build_file_path(file_name="railroad_N50_N", file_type="gdb")
    railroad_N50_P = wfm.build_file_path(file_name="railroad_N50_P", file_type="gdb")
    railroad_FKB = wfm.build_file_path(file_name="railroad_FKB", file_type="gdb")
    railroad_FKB_dissolved = wfm.build_file_path(
        file_name="railroad_FKB_dissolved", file_type="gdb"
    )
    railroad_N50_N_buffer_small = wfm.build_file_path(
        file_name="railroad_N50_N_buffer_small", file_type="gdb"
    )
    railroad_N50_N_buffer_large = wfm.build_file_path(
        file_name="railroad_N50_N_buffer_large", file_type="gdb"
    )
    railroad_FKB_intersect_N50 = wfm.build_file_path(
        file_name="railroad_FKB_intersect_N50", file_type="gdb"
    )
    railroad_FKB_working_area_N50 = wfm.build_file_path(
        file_name="railroad_FKB_working_area_N50", file_type="gdb"
    )
    valid_railroad_FKB = wfm.build_file_path(
        file_name="valid_railroad_FKB", file_type="gdb"
    )
    new_FKB = wfm.build_file_path(file_name="new_FKB", file_type="gdb")
    
    return {
        "railroad_N50_N": railroad_N50_N,
        "railroad_N50_P": railroad_N50_P,
        "railroad_FKB": railroad_FKB,
        "railroad_FKB_dissolved": railroad_FKB_dissolved,
        "railroad_N50_N_buffer_small": railroad_N50_N_buffer_small,
        "railroad_N50_N_buffer_large": railroad_N50_N_buffer_large,
        "railroad_FKB_intersect_N50": railroad_FKB_intersect_N50,
        "railroad_FKB_working_area_N50": railroad_FKB_working_area_N50,
        "valid_railroad_FKB": valid_railroad_FKB,
        "new_FKB": new_FKB,
    }


@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.

    Args:
        files (dict): Dictionary with all the working files
    """
    railroad_lyr = "railroad_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Railroad, out_layer=railroad_lyr
    )

    # Fetch N50 railroad
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=railroad_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Bane' and jernbanestatus = 'N'",
    )
    arcpy.management.CopyFeatures(
        in_features=railroad_lyr, out_feature_class=files["railroad_N50_N"]
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=railroad_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Bane' and jernbanestatus = 'P'",
    )
    arcpy.management.CopyFeatures(
        in_features=railroad_lyr, out_feature_class=files["railroad_N50_P"]
    )

    # Fetch FKB railroad
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=railroad_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Spormidt'",
    )
    arcpy.management.CopyFeatures(
        in_features=railroad_lyr, out_feature_class=files["railroad_FKB"]
    )
    arcpy.management.Dissolve(
        in_features=files["railroad_FKB"],
        out_feature_class=files["railroad_FKB_dissolved"],
        dissolve_field=["objtype"],
        multi_part="SINGLE_PART",
    )


@timing_decorator
def create_buffers(files: dict) -> None:
    """
    Creates buffers around railroad features that are not in normally use anymore.

    Args:
        files (dict): Dictionary with all the working files
    """
    N50_lyr = "N50_railroad_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["railroad_N50_N"], out_layer=N50_lyr
    )

    arcpy.analysis.Buffer(
        in_features=N50_lyr,
        out_feature_class=files["railroad_N50_N_buffer_small"],
        buffer_distance_or_field="10 Meters",
        line_side="FULL",
        line_end_type="FLAT",
        dissolve_option="NONE",
    )

    arcpy.analysis.Buffer(
        in_features=N50_lyr,
        out_feature_class=files["railroad_N50_N_buffer_large"],
        buffer_distance_or_field="200 Meters",
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="NONE",
    )


@timing_decorator
def intersect_fkb_n50(files: dict) -> None:
    """
    Finds FKB railroad features that are within the buffer of N50
    railroad features that are not in normally use anymore.

    Args:
        files (dict): Dictionary with all the working files
    """
    FKB_lyr = "FKB_railroad_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["railroad_FKB_dissolved"], out_layer=FKB_lyr
    )
    intersect_output = files["railroad_FKB_intersect_N50"]
    arcpy.management.SelectLayerByLocation(
        in_layer=FKB_lyr,
        overlap_type="INTERSECT",
        select_features=files["railroad_N50_N_buffer_small"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=FKB_lyr, out_feature_class=intersect_output
    )
    working_output = files["railroad_FKB_working_area_N50"]
    arcpy.management.SelectLayerByLocation(
        in_layer=FKB_lyr,
        overlap_type="INTERSECT",
        select_features=files["railroad_N50_N_buffer_large"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(in_features=FKB_lyr, out_feature_class=working_output)


@timing_decorator
def build_railroad_network_fkb_safe(files: dict) -> arcpy.Geometry:
    """
    Collects the railroad elements that absolutely should
    be categorized as railroad not usable anymore.

    Args:
        files (dict): Dictionary with all the working files

    Returns:
        arcpy.Geometry: One geometry representing the small buffer around
                        the N50 railroad not in use anymore
    """
    intersect = files["railroad_FKB_intersect_N50"]
    intersect_geoms = {
        oid: geom for oid, geom in arcpy.da.SearchCursor(intersect, ["OID@", "SHAPE@"])
    }

    buffer_small = files["railroad_N50_N_buffer_small"]
    buf_small_lyr = "buf_small_lyr"
    arcpy.MakeFeatureLayer_management(buffer_small, buf_small_lyr)

    buf_union_fc = "in_memory/buffer_geom"
    arcpy.management.Dissolve(buf_small_lyr, buf_union_fc)
    with arcpy.da.SearchCursor(buf_union_fc, ["SHAPE@"]) as cur:
        buffer_geom = next(cur)[0]

    valid_oids = set()

    for oid, geom in tqdm(intersect_geoms.items()):
        if oid in valid_oids:
            continue

        total_length = geom.length
        if total_length < 20:
            continue

        clipped = geom.intersect(buffer_geom, 2)

        inside_length = clipped.length

        if inside_length / total_length >= 0.75:
            valid_oids.add(oid)

    intersect_lyr = "intersect_lyr"
    arcpy.MakeFeatureLayer_management(intersect, intersect_lyr)
    oid_list = ",".join(map(str, valid_oids))
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=intersect_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"OBJECTID IN ({oid_list})",
    )

    valid_railroad_FKB = files["valid_railroad_FKB"]
    arcpy.management.CopyFeatures(
        in_features=intersect_lyr, out_feature_class=valid_railroad_FKB
    )

    return buffer_geom


@timing_decorator
def collect_unusable_railroads_1(files: dict, small_buffer: arcpy.Geometry) -> None:
    """ """
    intersect = files["railroad_FKB_working_area_N50"]
    valid_railroad_FKB = files["valid_railroad_FKB"]

    fkb_n50_lyr = "fkb_n50_lyr"
    arcpy.management.MakeFeatureLayer(in_features=intersect, out_layer=fkb_n50_lyr)

    def find_oids(pt):
        matching_oids = set()
        for oid, (start, end) in oid_to_endpoints_intersect.items():
            if pt == start or pt == end:
                matching_oids.add(oid)
        return matching_oids

    def all_oids_in_valid(oids):
        return all(oid in valid_oids for oid in oids)

    valid_oids = set()

    endpoint_count_valid = defaultdict(int)
    endpoint_count_intersect = defaultdict(int)

    oid_to_endpoints_intersect = {}

    oids_to_add = set()

    with arcpy.da.SearchCursor(valid_railroad_FKB, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            valid_oids.add(oid)
            start_point = geom.firstPoint
            end_point = geom.lastPoint
            endpoint_count_valid[(start_point.X, start_point.Y)] += 1
            endpoint_count_valid[(end_point.X, end_point.Y)] += 1

    with arcpy.da.SearchCursor(intersect, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            start_point = geom.firstPoint
            end_point = geom.lastPoint
            endpoint_count_intersect[(start_point.X, start_point.Y)] += 1
            endpoint_count_intersect[(end_point.X, end_point.Y)] += 1
            oid_to_endpoints_intersect[oid] = [
                (start_point.X, start_point.Y),
                (end_point.X, end_point.Y),
            ]

    for oid, endpoints in oid_to_endpoints_intersect.items():
        start, end = endpoints
        if start in endpoint_count_valid and end in endpoint_count_valid:
            oids_to_add.add(oid)
        elif start in endpoint_count_valid:
            if endpoint_count_intersect[end] == 1:
                if all_oids_in_valid(find_oids(start)):
                    oids_to_add.add(oid)
        elif end in endpoint_count_valid:
            if endpoint_count_intersect[start] == 1:
                if all_oids_in_valid(find_oids(end)):
                    oids_to_add.add(oid)

    if len(oids_to_add) != 0:
        sql = f"OBJECTID IN ({', '.join(map(str, oids_to_add))})"
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=fkb_n50_lyr,
            selection_type="NEW_SELECTION",
            where_clause=sql,
        )
        arcpy.management.Append(
            inputs=fkb_n50_lyr,
            target=valid_railroad_FKB,
            schema_type="NO_TEST",
        )


@timing_decorator
def collect_unusable_railroads(files: dict, small_buffer: arcpy.Geometry) -> None:
    """
    Utvider valid_railroad_FKB ved å hente alle FKB-linjer som:
    - henger sammen med valid_railroad_FKB
    - ligger innenfor small_buffer
    - ikke er koblet til større nettverk via noder som også har linjer som går ut av small_buffer.
    """

    # --- 0. Datasett ---
    fkb_all = prepare_fkb_for_network(files)
    valid_fc = files["valid_railroad_FKB"]          # det du allerede har funnet via N50_N
    large_buffer_fc = files["railroad_N50_N_buffer_large"]

    # --- 1. Lag et arbeidsutvalg av FKB innenfor storbufferen ---
    fkb_work = "in_memory/fkb_work"
    arcpy.analysis.Select(
        in_features=fkb_all,
        out_feature_class=fkb_work,
        where_clause=None
    )
    fkb_work_lyr = "fkb_work_lyr"
    arcpy.management.MakeFeatureLayer(fkb_work, fkb_work_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_work_lyr,
        overlap_type="INTERSECT",
        select_features=large_buffer_fc,
        selection_type="NEW_SELECTION"
    )

    # Kopier kun de som faktisk ligger i storbufferen
    fkb_work_sel = "in_memory/fkb_work_sel"
    arcpy.management.CopyFeatures(fkb_work_lyr, fkb_work_sel)

    # --- 2. Bygg nettverk på endepunkter med toleranse ---
    TOL = 0.5  # meter

    def snap_point(pt):
        return (round(pt.X / TOL) * TOL, round(pt.Y / TOL) * TOL)

    # node -> sett av OID
    node_to_oids = defaultdict(set)
    # OID -> geometri
    oid_to_geom = {}
    # OID -> True/False om linjen ligger helt innenfor small_buffer
    oid_inside_small = {}

    with arcpy.da.SearchCursor(fkb_work_sel, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            oid_to_geom[oid] = geom
            start = snap_point(geom.firstPoint)
            end = snap_point(geom.lastPoint)
            node_to_oids[start].add(oid)
            node_to_oids[end].add(oid)
            # sjekk om linjen er helt innenfor small_buffer
            oid_inside_small[oid] = not geom.disjoint(small_buffer)

    # --- 3. Finn "farlige" noder: noder som har minst én linje utenfor small_buffer ---
    dangerous_nodes = set()
    for node, oids in node_to_oids.items():
        for oid in oids:
            if not oid_inside_small[oid]:
                dangerous_nodes.add(node)
                break  # holder å vite at én linje går ut

    # --- 4. Finn start-OIDer: FKB-linjer som overlapper valid_fc ---
    start_oids = set()
    valid_lyr = "valid_lyr"
    arcpy.management.MakeFeatureLayer(valid_fc, valid_lyr)

    fkb_work_sel_lyr = "fkb_work_sel_lyr"
    arcpy.management.MakeFeatureLayer(fkb_work_sel, fkb_work_sel_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_work_sel_lyr,
        overlap_type="INTERSECT",
        select_features=valid_lyr,
        selection_type="NEW_SELECTION"
    )

    with arcpy.da.SearchCursor(fkb_work_sel_lyr, ["OID@"]) as cur:
        for (oid,) in cur:
            start_oids.add(oid)

    if not start_oids:
        print("Fant ingen FKB-linjer som overlapper valid_railroad_FKB.")
        return

    # --- 5. BFS på "trygge" noder og linjer innenfor small_buffer ---
    visited = set()
    queue = list(start_oids)

    while queue:
        oid = queue.pop(0)
        if oid in visited:
            continue
        if not oid_inside_small.get(oid, False):
            continue  # ikke ta med linjer som går ut av small_buffer

        geom = oid_to_geom[oid]
        start = snap_point(geom.firstPoint)
        end = snap_point(geom.lastPoint)

        # Hvis en av endepunktene er "farlig", betyr det at denne linjen
        # er koblet til større nettverk via en node som også har linjer
        # som går ut av small_buffer. Da skal vi ikke ta med denne linjen.
        if start in dangerous_nodes or end in dangerous_nodes:
            continue

        visited.add(oid)

        # legg til nabo-linjer via trygge noder
        for node in (start, end):
            if node in dangerous_nodes:
                continue
            for neigh_oid in node_to_oids[node]:
                if neigh_oid not in visited:
                    queue.append(neigh_oid)

    # --- 6. Append resultatet til valid_fc ---
    if visited:
        oid_list = ",".join(map(str, visited))
        arcpy.management.MakeFeatureLayer(fkb_work_sel, fkb_work_sel_lyr)
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=fkb_work_sel_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({oid_list})",
        )
        arcpy.management.Append(
            inputs=fkb_work_sel_lyr,
            target=valid_fc,
            schema_type="NO_TEST",
        )
        print(f"La til {len(visited)} linjer som er koblet til valid_fc, uten å gå inn i større nettverk.")
    else:
        print("Fant ingen ekstra linjer som oppfylte kriteriene.")


@timing_decorator
def update_railroad_attributes(files: dict) -> None:
    """
    Oppdaterer FKB basert på nærmeste N50-linje.
    - Hvis N50 har jernbanetype = 'M' → FKB får jernbanestatus='N' og jernbanetype='M'
    - Hvis N50 har jernbanestatus = 'N' → FKB får jernbanestatus='N'
    """

    # --- Datasett ---
    fkb = files["railroad_FKB"]
    valid_fc = files["valid_railroad_FKB"]
    n50 = files["railroad_N50_N"]   # inneholder både 'N' og 'M'
    out_fc = files["new_FKB"]

    # --- 1. Kopier FKB til output ---
    arcpy.management.CopyFeatures(fkb, out_fc)

    # --- 2. Velg kun FKB-linjer som skal oppdateres ---
    out_lyr = "out_lyr"
    arcpy.management.MakeFeatureLayer(out_fc, out_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=out_lyr,
        overlap_type="INTERSECT",
        select_features=valid_fc,
        selection_type="NEW_SELECTION"
    )

    # --- 3. Kjør Near for å finne nærmeste N50-linje ---
    arcpy.analysis.Near(
        in_features=out_lyr,
        near_features=n50,
        search_radius="50 Meters",
        location="NO_LOCATION",
        angle="NO_ANGLE",
        method="PLANAR"
    )

    # --- 4. Lag oppslagsverk: N50_OID -> (status, type) ---
    n50_lookup = {}
    with arcpy.da.SearchCursor(n50, ["OID@", "jernbanestatus", "jernbanetype"]) as cur:
        for oid, status, jtype in cur:
            n50_lookup[oid] = (status, jtype)

    # --- 5. Oppdater FKB basert på NEAR_FID ---
    with arcpy.da.UpdateCursor(out_fc, ["OID@", "NEAR_FID", "jernbanestatus", "jernbanetype"]) as cur:
        for oid, near_oid, fkb_status, fkb_type in cur:
            if near_oid in n50_lookup:
                n50_status, n50_type = n50_lookup[near_oid]

                # Regel 1: Museumsbane
                if n50_type == "M":
                    cur.updateRow([oid, near_oid, "N", "M"])
                
                # Regel 2: Nedlagt bane
                elif n50_status == "N":
                    cur.updateRow([oid, near_oid, "N", fkb_type])

    print("✔ Oppdaterte FKB-linjer basert på N50-status og -type.")


# ========================
# Helper functions
# ========================


def prepare_fkb_for_network(files: dict) -> str:
    """
    Lager et topologisk renset FKB-lag for nettverksanalyse.
    Returnerer feature class-navnet som kan brukes i collect_unusable_railroads.
    """
    fkb_src = files["railroad_FKB"]  # original Spormidt
    fkb_clean = "in_memory/fkb_clean"

    # Kopier først
    arcpy.management.CopyFeatures(fkb_src, fkb_clean)

    # Integrate "snurper sammen" små gap og nesten-snappede noder
    # Juster toleransen ved behov (0.3–1.0 m typisk)
    arcpy.management.Integrate(in_features=[fkb_clean], cluster_tolerance="0.5 Meters")

    return fkb_clean


# ========================

if __name__ == "__main__":
    main()
