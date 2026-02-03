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

    # Program
    fetch_data(files=files)
    create_buffers(files=files)
    intersect_fkb_n50(files=files)
    small_buffer = build_railroad_network_fkb_safe(files=files)
    collect_unusable_railroads(files=files, small_buffer=small_buffer)
    update_railroad_attributes(files=files)
    fetch_remaining_railroads(files=files)
    classify_within_n50_buffer(files=files)
    fetch_edge_case_ends(files=files)
    add_railroad_under_construction(files=files)

    # Clean up of files
    output = Facility_N10.railroad_output__n10_facility.value
    arcpy.management.CopyFeatures(
        in_features=files["new_FKB"], out_feature_class=output
    )

    wfm.delete_created_files()

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
    railroad_N50_N_dissolved_small = wfm.build_file_path(
        file_name="railroad_N50_N_dissolved_small", file_type="gdb"
    )
    railroad_N50_N_buffer_large = wfm.build_file_path(
        file_name="railroad_N50_N_buffer_large", file_type="gdb"
    )
    railroad_N50_N_dissolved_large = wfm.build_file_path(
        file_name="railroad_N50_N_dissolved_large", file_type="gdb"
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
    railroad_I_5m = wfm.build_file_path(file_name="railroad_I_5m", file_type="gdb")
    railroad_I_5m_dissolve = wfm.build_file_path(
        file_name="railroad_I_5m_dissolve", file_type="gdb"
    )

    return {
        "railroad_N50_N": railroad_N50_N,
        "railroad_N50_P": railroad_N50_P,
        "railroad_FKB": railroad_FKB,
        "railroad_FKB_dissolved": railroad_FKB_dissolved,
        "railroad_N50_N_buffer_small": railroad_N50_N_buffer_small,
        "railroad_N50_N_dissolved_small": railroad_N50_N_dissolved_small,
        "railroad_N50_N_buffer_large": railroad_N50_N_buffer_large,
        "railroad_N50_N_dissolved_large": railroad_N50_N_dissolved_large,
        "railroad_FKB_intersect_N50": railroad_FKB_intersect_N50,
        "railroad_FKB_working_area_N50": railroad_FKB_working_area_N50,
        "valid_railroad_FKB": valid_railroad_FKB,
        "new_FKB": new_FKB,
        "railroad_I_5m": railroad_I_5m,
        "railroad_I_5m_dissolve": railroad_I_5m_dissolve,
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
    Creates buffers around railroad features that are not in normal use anymore.

    Args:
        files (dict): Dictionary with all the working files
    """
    N50_lyr = "N50_railroad_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["railroad_N50_N"], out_layer=N50_lyr
    )

    small = 10
    large = 300

    arcpy.analysis.Buffer(
        in_features=N50_lyr,
        out_feature_class=files["railroad_N50_N_buffer_small"],
        buffer_distance_or_field=f"{small} Meters",
        line_side="FULL",
        line_end_type="FLAT",
        dissolve_option="NONE",
    )
    arcpy.management.Dissolve(
        in_features=files["railroad_N50_N_buffer_small"],
        out_feature_class=files["railroad_N50_N_dissolved_small"],
    )

    arcpy.analysis.Buffer(
        in_features=N50_lyr,
        out_feature_class=files["railroad_N50_N_buffer_large"],
        buffer_distance_or_field=f"{large} Meters",
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="None",
    )
    arcpy.management.Dissolve(
        in_features=files["railroad_N50_N_buffer_large"],
        out_feature_class=files["railroad_N50_N_dissolved_large"],
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )


@timing_decorator
def intersect_fkb_n50(files: dict) -> None:
    """
    Finds FKB railroad features that are within the buffer of N50
    railroad features that are not in normally use anymore.

    Args:
        files (dict): Dictionary with all the working files
    """
    # Datasets
    intersect_output = files["railroad_FKB_intersect_N50"]
    working_output = files["railroad_FKB_working_area_N50"]

    # Create feature layer of dissolved fkb railroads
    FKB_lyr = "FKB_railroad_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["railroad_FKB_dissolved"], out_layer=FKB_lyr
    )

    # Select features in the small buffer
    arcpy.management.SelectLayerByLocation(
        in_layer=FKB_lyr,
        overlap_type="INTERSECT",
        select_features=files["railroad_N50_N_dissolved_small"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=FKB_lyr, out_feature_class=intersect_output
    )

    # Select features in the large buffer
    arcpy.management.SelectLayerByLocation(
        in_layer=FKB_lyr,
        overlap_type="INTERSECT",
        select_features=files["railroad_N50_N_dissolved_large"],
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
    # Fetch railroad instances inside small buffer
    intersect = files["railroad_FKB_intersect_N50"]
    intersect_geoms = {
        oid: geom for oid, geom in arcpy.da.SearchCursor(intersect, ["OID@", "SHAPE@"])
    }

    # Fetch the small buffer as one single instance (geometry)
    buffer_small = files["railroad_N50_N_dissolved_small"]
    with arcpy.da.SearchCursor(buffer_small, ["SHAPE@"]) as cur:
        buffer_geom = next(cur)[0]

    # Collect oids for geometries that has 75% of
    # their geometry length inside the small geometry
    valid_oids = set()
    for oid, geom in tqdm(
        intersect_geoms.items(),
        desc="Collect valid geometries",
        colour="yellow",
        leave=False,
    ):
        if oid in valid_oids:
            continue

        total_length = geom.length
        if total_length < 20:
            continue

        clipped = geom.intersect(buffer_geom, 2)

        inside_length = clipped.length

        if inside_length / total_length >= 0.75:
            valid_oids.add(oid)

    # Select the features with valid oid and create new feature class
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
def collect_unusable_railroads(files: dict, small_buffer: arcpy.Geometry) -> None:
    """
    Suplements the railroad network not in use anymore by fetching railroad that:
    - Connects to valid_railroad_fkb
    - Is inside small_buffer
    - Is not connected to a larger network where the nodes are connected to lines outside small_buffer

    Args:
        files (dict): Dictionary with all the working files
        arcpy.Geometry: One geometry representing the small buffer around
                        the N50 railroad not in use anymore
    """

    # Data sets
    fkb_all = prepare_fkb_for_network(files)
    valid_fc = files["valid_railroad_FKB"]
    large_buffer_fc = files["railroad_N50_N_dissolved_large"]

    # 1) Create a selection with the lines to adjust inside the large buffer
    fkb_all_lyr = "fkb_all_lyr"
    arcpy.management.MakeFeatureLayer(in_features=fkb_all, out_layer=fkb_all_lyr)

    fkb_work_sel = r"in_memory/fkb_work_sel"
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_all_lyr,
        overlap_type="INTERSECT",
        select_features=large_buffer_fc,
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(fkb_all_lyr, fkb_work_sel)

    # 2) Build a network of end points with tolerance

    # Node -> Set of OIDs
    node_to_oids = defaultdict(set)
    # OID -> Geometry
    oid_to_geom = {}
    # OID -> True/False if the line is completely inside small_buffer
    oid_inside_small = {}

    with arcpy.da.SearchCursor(fkb_work_sel, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            oid_to_geom[oid] = geom
            start = snap_point(geom.firstPoint)
            end = snap_point(geom.lastPoint)
            node_to_oids[start].add(oid)
            node_to_oids[end].add(oid)
            # Check if the line is completely inside small_buffer
            oid_inside_small[oid] = not geom.disjoint(small_buffer)

    # 3) Find "dangerous" nodes: Nodes that have at least one line outside small_buffer
    dangerous_nodes = set()
    for node, oids in node_to_oids.items():
        for oid in oids:
            if not oid_inside_small[oid]:
                dangerous_nodes.add(node)
                break  # If one is inside -> continue

    # 4) Find start OIDs: FKB lines that have overlap with valid_fc
    start_oids = set()
    valid_lyr = "valid_lyr"
    arcpy.management.MakeFeatureLayer(valid_fc, valid_lyr)

    fkb_work_sel_lyr = "fkb_work_sel_lyr"
    arcpy.management.MakeFeatureLayer(fkb_work_sel, fkb_work_sel_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_work_sel_lyr,
        overlap_type="INTERSECT",
        select_features=valid_lyr,
        selection_type="NEW_SELECTION",
    )

    with arcpy.da.SearchCursor(fkb_work_sel_lyr, ["OID@"]) as cur:
        for (oid,) in cur:
            start_oids.add(oid)

    if not start_oids:
        return

    # 5) BFS on "safe" nodes and lines inside small_buffer
    visited = set()
    queue = list(start_oids)

    while queue:
        oid = queue.pop(0)
        if oid in visited:
            continue
        if not oid_inside_small.get(oid, False):
            continue  # Do not include lines going out of small_buffer

        geom = oid_to_geom[oid]
        start = snap_point(geom.firstPoint)
        end = snap_point(geom.lastPoint)

        """
        If one of the end points is "dangerous", it means that this line
        is connected to a larger network through a node that also has lines
        that go outside small_buffer. Then we should not include this line.
        """
        if start in dangerous_nodes or end in dangerous_nodes:
            continue

        visited.add(oid)

        # Add the neighbour line through safe nodes
        for node in (start, end):
            if node in dangerous_nodes:
                continue
            for neigh_oid in node_to_oids[node]:
                if neigh_oid not in visited:
                    queue.append(neigh_oid)

    # 6) Append the result to valid_fc
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


@timing_decorator
def update_railroad_attributes(files: dict) -> None:
    """
    Updates the FKB attribute data based on closest N50 line.
    - If the N50 line has 'jernbanetype' = 'M' -> FKB gets 'jernbanestatus' = 'N' and 'jernbanetype' = 'M'
    - If the N50 line har 'jernbanestatus' = 'N' -> FKB gets 'jernbanestatus' = 'N'

    Args:
        files (dict): Dictionary with all the working files
    """

    # Data sets
    fkb = files["railroad_FKB"]
    valid_fc = files["valid_railroad_FKB"]
    n50 = files["railroad_N50_N"]
    out_fc = files["new_FKB"]

    # 1) Copy the FKB data to the output
    arcpy.management.CopyFeatures(fkb, out_fc)

    # 2) Choose only the FKB lines that should be updated
    out_lyr = "out_lyr"
    arcpy.management.MakeFeatureLayer(out_fc, out_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=out_lyr,
        overlap_type="INTERSECT",
        select_features=valid_fc,
        selection_type="NEW_SELECTION",
    )

    # 3) Run Near to fetch closest N50 line
    arcpy.analysis.Near(
        in_features=out_lyr,
        near_features=n50,
        search_radius="50 Meters",
        location="NO_LOCATION",
        angle="NO_ANGLE",
        method="PLANAR",
    )

    # 4) Create a look-up dict: N50_OID -> (status, type)
    n50_lookup = {}
    with arcpy.da.SearchCursor(n50, ["OID@", "jernbanestatus", "jernbanetype"]) as cur:
        for oid, status, jtype in cur:
            n50_lookup[oid] = (status, jtype)

    # 5) Update FKB based on NEAR_FID
    with arcpy.da.UpdateCursor(
        out_fc, ["OID@", "NEAR_FID", "jernbanestatus", "jernbanetype"]
    ) as cur:
        for oid, near_oid, _, fkb_type in cur:
            if near_oid in n50_lookup:
                n50_status, n50_type = n50_lookup[near_oid]

                # Rule 1: Museumsbane
                if n50_type == "M":
                    cur.updateRow([oid, near_oid, "N", "M"])

                # Rule 2: Disused railroad
                elif n50_status == "N":
                    cur.updateRow([oid, near_oid, "N", fkb_type])


@timing_decorator
def fetch_remaining_railroads(files: dict) -> None:
    """
    Performes BFS to add disused railroad instances inside the search area.

    Args:
        files (dict): Dictionary with all the working files
    """
    fkb_fc = files["new_FKB"]
    dissolved_fc = files["railroad_FKB_dissolved"]
    buffer_fc = files["railroad_N50_N_dissolved_large"]

    # 1) Dissolve the FKB data
    arcpy.management.Dissolve(
        in_features=fkb_fc,
        out_feature_class=dissolved_fc,
        dissolve_field=["medium", "jernbanestatus"],
        multi_part="SINGLE_PART",
    )

    # 2) Create feature layers
    dissolved_lyr = "dissolved_lyr"
    fkb_lyr = "fkb_lyr"
    arcpy.management.MakeFeatureLayer(dissolved_fc, dissolved_lyr)
    arcpy.management.MakeFeatureLayer(fkb_fc, fkb_lyr)

    # 3. Select dissolved segments that lie fully within buffer
    arcpy.management.SelectLayerByLocation(
        in_layer=dissolved_lyr,
        overlap_type="WITHIN",
        select_features=buffer_fc,
        selection_type="NEW_SELECTION",
    )

    # 4) Build an overview of segments for the chosen dissolved segments only
    segments = {}
    with arcpy.da.SearchCursor(
        dissolved_lyr, ["OID@", "SHAPE@", "jernbanestatus"]
    ) as cursor:
        for oid, geom, status in cursor:
            start = geom.firstPoint
            end = geom.lastPoint
            segments[oid] = {
                "status": status,
                "start": (start.X, start.Y),
                "end": (end.X, end.Y),
            }

    # 5) Build graph
    node_index = defaultdict(list)
    for oid, seg in segments.items():
        node_index[seg["start"]].append(oid)
        node_index[seg["end"]].append(oid)

    graph = defaultdict(list)
    for oids in node_index.values():
        if len(oids) > 1:
            for oid in oids:
                graph[oid].extend([o for o in oids if o != oid])

    # 6) BFS from all N segments
    queue = deque([oid for oid, d in segments.items() if d["status"] == "N"])
    visited = set(queue)
    dissolved_to_update = set()

    while queue:
        current = queue.popleft()
        for neighbor in graph[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                if segments[neighbor]["status"] == "I":
                    dissolved_to_update.add(neighbor)
                queue.append(neighbor)

    # 7) Find original FKB segments that match the dissolved segments
    original_to_update = set()

    for dissolved_oid in dissolved_to_update:
        # For each dissolved object
        arcpy.management.SelectLayerByAttribute(
            dissolved_lyr, "NEW_SELECTION", f"OBJECTID = {dissolved_oid}"
        )

        # Collect original FKB lines that have 100% overlap
        arcpy.management.SelectLayerByLocation(
            in_layer=fkb_lyr,
            overlap_type="WITHIN",
            select_features=dissolved_lyr,
            selection_type="NEW_SELECTION",
        )

        # Fetch OID for original FKB
        with arcpy.da.SearchCursor(fkb_lyr, ["OID@"]) as cursor:
            for (oid,) in cursor:
                original_to_update.add(oid)

    # 8) Update original FKB
    with arcpy.da.UpdateCursor(fkb_fc, ["OID@", "jernbanestatus"]) as cursor:
        for oid, status in cursor:
            if oid in original_to_update and status == "I":
                cursor.updateRow([oid, "N"])


@timing_decorator
def classify_within_n50_buffer(files: dict) -> None:
    """
    Creates a 5 m buffer around FKB data in use, and collect the instances having a buffer
    completely inside the N50 buffer. These instances should be set to disused.

    Args:
        files (dict): Dictionary with all the working files
    """
    fkb_fc = files["new_FKB"]
    n50_buffer_fc = files["railroad_N50_N_dissolved_large"]
    i_buffer_fc = files["railroad_I_5m"]
    i_dissolved_fc = files["railroad_I_5m_dissolve"]

    # 1) Create feature layer of FKB
    fkb_lyr = "fkb_lyr"
    arcpy.management.MakeFeatureLayer(fkb_fc, fkb_lyr)

    # 2) Collect all railroads with 'jernbanestatus' = 'I'
    arcpy.management.SelectLayerByAttribute(
        fkb_lyr, "NEW_SELECTION", "jernbanestatus = 'I'"
    )

    # 3) Create a tiny buffer of 5 m around all the chosen railroads
    tol = 5
    arcpy.analysis.Buffer(
        in_features=fkb_lyr,
        out_feature_class=i_buffer_fc,
        buffer_distance_or_field=f"{tol} Meters",
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="None",
    )
    arcpy.management.Dissolve(
        in_features=i_buffer_fc,
        out_feature_class=i_dissolved_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    # 4) Create feature layer of the I-buffers
    i_dissolved_lyr = "i_dissolved_lyr"
    arcpy.management.MakeFeatureLayer(i_dissolved_fc, i_dissolved_lyr)

    # 5) Choose the I-buffers that are completely inside the N50-buffers
    arcpy.management.SelectLayerByLocation(
        in_layer=i_dissolved_lyr,
        overlap_type="WITHIN",
        select_features=n50_buffer_fc,
        selection_type="NEW_SELECTION",
    )

    # 6) Use the chosen I-buffers to choose all FKB railroads that should be categorised as disused
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_lyr,
        overlap_type="INTERSECT",
        select_features=i_dissolved_lyr,
        selection_type="SUBSET_SELECTION",
    )

    # 7) Adjust the chosen railroads to jernbanestatus = 'N'
    with arcpy.da.UpdateCursor(fkb_lyr, ["jernbanestatus"]) as cursor:
        for _ in cursor:
            cursor.updateRow(["N"])


@timing_decorator
def fetch_edge_case_ends(files: dict) -> None:
    """
    Identifies FKB railroad segments inside the search area whose endpoints form
    small, isolated branches connected to disused railroad (status = 'N').
    These segments represent edge cases where short stubs or small branches
    should also be marked as disused.

    A segment qualifies for update if:
        - Both endpoints occur at most twice in the dataset (endpoint_count <= 2),
          meaning the segment is part of a simple chain, not a junction
        - At least one endpoint connects to a segment already marked as disused
        - Neither endpoint lies outside the search area
        - The logic accounts for cascading updates: newly added disused segments
          may cause additional segments to qualify in the same iteration

    Args:
        files (dict): Dictionary with all the working files
    """
    # Data sets
    fkb_fc = files["new_FKB"]
    search_area_fc = files["railroad_N50_N_dissolved_large"]

    # 1) Select railroad inside the buffers
    fkb_lyr = "fkb_lyr"
    arcpy.management.MakeFeatureLayer(fkb_fc, fkb_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_lyr,
        overlap_type="INTERSECT",
        select_features=search_area_fc,
        selection_type="NEW_SELECTION",
    )

    # 2) Create one single geometry for the buffers
    search_area_geom = None
    with arcpy.da.SearchCursor(search_area_fc, ["SHAPE@"]) as cur:
        for (g,) in cur:
            search_area_geom = (
                g if search_area_geom is None else search_area_geom.union(g)
            )

    # 3) Create a mapping of fkb elements
    fkb_railroad = {}
    endpoint_count = {}
    with arcpy.da.SearchCursor(fkb_lyr, ["OID@", "SHAPE@", "jernbanestatus"]) as cur:
        for oid, geom, status in cur:
            start = geom.firstPoint
            end = geom.lastPoint

            endpoint_count[start] = endpoint_count.get(start, 0) + 1
            endpoint_count[end] = endpoint_count.get(end, 0) + 1

            if not start.disjoint(search_area_geom) and not end.disjoint(
                search_area_geom
            ):
                fkb_railroad[oid] = [start, end, status]

    # 4) Find the elements to change attribute
    to_edit = set()

    node_to_oids = defaultdict(set)
    for oid, (start, end, status) in fkb_railroad.items():
        node_to_oids[start].add(oid)
        node_to_oids[end].add(oid)

    changed = True

    while changed:
        changed = False

        for oid, (start, end, status) in tqdm(
            fkb_railroad.items(),
            desc="Adds disused railroad",
            colour="yellow",
            leave=False,
        ):
            # Skip those already added
            if oid in to_edit:
                continue
            # Each endpoint must be part of a simple chain, no junction
            if endpoint_count[start] > 2 or endpoint_count[end] > 2:
                continue
            # At least one point must be connected to disused railroad
            connected_oids_start = node_to_oids[start]
            connected_oids_end = node_to_oids[end]

            connected_statuses = set()

            for neigh_oid in connected_oids_start | connected_oids_end:
                neigh_status = fkb_railroad[neigh_oid][2]
                if neigh_oid in to_edit:
                    neigh_status = "N"  # Becomes disused in this iteration

                connected_statuses.add(neigh_status)

            if "N" in connected_statuses:
                to_edit.add(oid)
                changed = True

    # 5) Update the attributes
    sql = f"OBJECTID IN ({','.join(map(str, to_edit))})"
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=fkb_lyr, selection_type="NEW_SELECTION", where_clause=sql
    )

    with arcpy.da.UpdateCursor(fkb_lyr, ["jernbanestatus"]) as cur:
        for _ in cur:
            cur.updateRow(["N"])


@timing_decorator
def add_railroad_under_construction(files: dict) -> None:
    """
    Add the N50 data under construction to the FKB data.

    Args:
        files (dict): Dictionary with all the working files
    """
    fkb = files["new_FKB"]
    n50_construction = files["railroad_N50_P"]

    arcpy.management.Append(inputs=n50_construction, target=fkb, schema_type="NO_TEST")


# ========================
# Helper functions
# ========================


def snap_point(pt: arcpy.PointGeometry, TOL: float = 0.5) -> tuple[float]:
    """
    Snaps a point's coordinates to a tolerance grid to reduce floating‑point
    variation when comparing endpoints in a network.

    Args:
        pt (arcpy.PointGeometry): The point to snap.
        TOL (float): Grid size used for snapping. Defaults to 0.5.

    Returns:
        tuple[float]: The snapped (x, y) coordinate pair.
    """
    return (round(pt.X / TOL) * TOL, round(pt.Y / TOL) * TOL)


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
