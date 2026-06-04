import arcpy
from env_setup import environment_setup
from file_manager import WorkFileManager
from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
import os
from file_manager.n100.file_manager_roads import Road_N100
from collections import deque, defaultdict
from typing import Dict, Set, List, Any, Iterable, Optional



def main(input_fc: str, output_roads_fc: str, output_points_fc: str):
    config = core_config.WorkFileConfig(root_file=input_fc)
    wfm = WorkFileManager(config=config)
    files = create_wfm_gdbs(wfm=wfm)
    arcpy.management.CopyFeatures(input_fc, files["copy_of_input"])

    relevant_roads_layer = select_relevant_roads(files=files, buffer_size=400) #1000 and above gets an error about falling outside of geometry domain?
    dissolve_relevant_roads(relevant_roads=relevant_roads_layer, output_fc=files["relevant_roads_dissolved"])
    make_potential_points(files=files)
    remove_points_without_ramp_connection(files=files)
    give_points_score(files=files)
    give_points_ramp_id(files=files)
    give_roads_ramp_id_2(files=files)

    delete_ramps(files=files)
    arcpy.management.CopyFeatures(
        in_features=files["copy_of_input"],
        out_feature_class=output_roads_fc,
    )
    arcpy.management.CopyFeatures(
        in_features=files["potential_points"],
        out_feature_class=output_points_fc,
    )
    #wfm.delete_created_files()

    


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of combining land use on islands.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    copy_of_input = wfm.build_file_path(file_name="copy_of_input", file_type="gdb")
    rampe_buffer = wfm.build_file_path(file_name="rampe_buffer", file_type="gdb")
    relevant_roads_dissolved = wfm.build_file_path(file_name="relevant_roads_dissolved", file_type="gdb")
    potential_points_multipart = wfm.build_file_path(file_name="potential_points_multipart", file_type="gdb")
    potential_points = wfm.build_file_path(file_name="potential_points", file_type="gdb")
    endpoints = wfm.build_file_path(file_name="endpoints", file_type="gdb")
    near_table = wfm.build_file_path(file_name="near_table", file_type="gdb")
    
    return {
        "copy_of_input": copy_of_input,
        "rampe_buffer": rampe_buffer,
        "relevant_roads_dissolved": relevant_roads_dissolved,
        "potential_points_multipart": potential_points_multipart,
        "potential_points": potential_points,
        "endpoints": endpoints,
        "near_table": near_table,
        
    }

@timing_decorator
def select_relevant_roads(files: dict, buffer_size: int):
    """
    Select relevent roads and ramps using buffer
    returns featurelayer
    """
    rampe_layer = "rampe_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=rampe_layer,
        where_clause="typeveg = 'rampe'"
    )
    arcpy.analysis.Buffer(
        in_features=rampe_layer,
        out_feature_class=files["rampe_buffer"],
        buffer_distance_or_field=f"{buffer_size} Meters",
        #dissolve_option="ALL",
    )    
    relevant_roads_layer = "relevant_roads_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=relevant_roads_layer,
        where_clause="objtype = 'VegSenterlinje'"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=relevant_roads_layer,
        overlap_type="INTERSECT",
        select_features=files["rampe_buffer"],
        selection_type="NEW_SELECTION",
    )

    return relevant_roads_layer


@timing_decorator
def dissolve_relevant_roads(relevant_roads: str, output_fc: str):
    """
    Dissolves roads and ramps
    using these fields: ["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"]
    before dissolving we add a field with objid so we can keep track of which roads were dissolved together
    """
    field_name = "obj_id_txt"
    arcpy.management.AddField(
        in_table=relevant_roads,
        field_name=field_name,
        field_type="TEXT",
    )
    arcpy.management.CalculateField(
        in_table=relevant_roads,
        field=field_name,
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )
    arcpy.management.Dissolve(
        in_features=relevant_roads, 
        out_feature_class=output_fc, 
        dissolve_field=["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"], 
        multi_part="SINGLE_PART",
        statistics_fields=[[field_name, "CONCATENATE"]],
        concatenation_separator=",",
    )

    concat_field = f"CONCATENATE_{field_name}"
    orig_lines_id = "orig_lines_id"
    arcpy.management.AddField(
        in_table=output_fc,
        field_name=orig_lines_id,
        field_type="TEXT",
    )
    orig_layer = "orig_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=relevant_roads,
        out_layer=orig_layer,
    )
    with arcpy.da.UpdateCursor(output_fc, ["OID@", "SHAPE@", concat_field, orig_lines_id]) as ucur:
        for row in ucur:
            oid = row[0]
            geom = row[1]
            concat_val = row[2]

            # Build set of allowed IDs from the CONCATENATE field
            allowed = set()
            if concat_val:
                # split on comma, strip whitespace, ignore empty tokens
                tokens = [t.strip() for t in str(concat_val).split(",") if t.strip() != ""]
                allowed = set(tokens)

            # If no allowed IDs, write empty and continue
            if not allowed:
                row[3] = ""
                ucur.updateRow(row)
                continue

            # Select original lines that intersect this dissolved geometry
            arcpy.SelectLayerByLocation_management(orig_layer, "INTERSECT", geom, selection_type="NEW_SELECTION")

            matched_ids = []
            # Iterate selected original lines and keep only those whose ID is in allowed
            with arcpy.da.SearchCursor(orig_layer, [field_name]) as scur:
                for srow in scur:
                    orig_id = srow[0]
                    if orig_id is None:
                        continue
                    # If orig_id is numeric in the orig table but concat contains strings, ensure matching by string
                    if orig_id in allowed:
                        matched_ids.append(orig_id)

            # Remove duplicates and preserve order (optional)
            # Here we keep the order of first occurrence
            seen = set()
            ordered = []
            for v in matched_ids:
                if v not in seen:
                    seen.add(v)
                    ordered.append(v)

            # Join into comma-separated string and write to out_field
            row[3] = ",".join(ordered)
            ucur.updateRow(row)

@timing_decorator
def make_potential_points(files: dict):
    layer_T = "layer_T"
    layer_U = "layer_U"
    layer_L = "layer_L"

    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_T,
        where_clause=f"medium = 'T' AND typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_U,
        where_clause=f"medium = 'U' AND typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_L,
        where_clause=f"medium = 'L' AND typeveg <> 'rampe'"
    )
        
    intersect_1 = f"{files['potential_points']}_intersect_1"   
    intersect_2 = f"{files['potential_points']}_intersect_2"   
    intersect_3 = f"{files['potential_points']}_intersect_3"    
    arcpy.analysis.Intersect(
        [layer_T, layer_U], 
        out_feature_class=intersect_1,
        join_attributes="ONLY_FID",
        output_type="POINT",
    )
    arcpy.analysis.Intersect(
        [layer_T, layer_L], 
        out_feature_class=intersect_2,
        join_attributes="ONLY_FID",
        output_type="POINT",
    )
    arcpy.analysis.Intersect(
        [layer_L, layer_U], 
        out_feature_class=intersect_3,
        join_attributes="ONLY_FID",
        output_type="POINT",
    )
    arcpy.management.Merge(
        inputs=[intersect_1, intersect_2, intersect_3],
        output=files["potential_points_multipart"],
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files["potential_points_multipart"],
        out_feature_class=files["potential_points"],
    )
    arcpy.management.DeleteField(
        in_table=files["potential_points"],
        drop_field="ORIG_FID",
    )

    remove_endpoints(files=files, lines_fc=files["relevant_roads_dissolved"], points_fc=files["potential_points"])

def remove_endpoints(files: dict, lines_fc: str, points_fc: str):
    """
    Removes points in points_fc that intersect with endpoints in lines_fc
    """

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files["endpoints"]),
        out_name=os.path.basename(files["endpoints"]),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(lines_fc).spatialReference,
    )

    with arcpy.da.SearchCursor(
        lines_fc, ["OID@", "SHAPE@"]
    ) as road_cur, arcpy.da.InsertCursor(files["endpoints"], ["SHAPE@"]) as ins_cur:
        for oid, geom in road_cur:
            # if oid in intersecting_oids:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg])
            ins_cur.insertRow([end_pg])

    points_lyr = arcpy.management.MakeFeatureLayer(points_fc, "points_lyr").getOutput(0)
    arcpy.management.SelectLayerByLocation(
        points_lyr, "INTERSECT", files["endpoints"], selection_type="NEW_SELECTION"
    )

    selected_count = int(arcpy.GetCount_management(points_lyr).getOutput(0))
    if selected_count > 0:
        arcpy.DeleteRows_management(points_lyr)

    arcpy.management.Delete(files["endpoints"])
    arcpy.management.Delete(points_lyr)

def get_line_endpoints(line_geom):
    """
    Accepts an arcpy Polyline geometry and returns two arcpy PointGeometry objects:
    (start_point_geom, end_point_geom).
    """
    # Get first and last coordinate from first part (works for simple and multipart;
    # for multipart this uses the first and last vertex of the entire geometry).
    first_part = line_geom.getPart(0)
    start_pt = first_part[0]
    # find last non-None vertex in geometry
    last_pt = None
    for part in line_geom:
        for v in part:
            if v is not None:
                last_pt = v
    if last_pt is None:
        raise ValueError("Line geometry has no vertices")
    sr = line_geom.spatialReference
    start_pg = arcpy.PointGeometry(arcpy.Point(start_pt.X, start_pt.Y), sr)
    end_pg = arcpy.PointGeometry(arcpy.Point(last_pt.X, last_pt.Y), sr)
    return start_pg, end_pg

def remove_points_without_ramp_connection(files: dict):
    """
    Removes potential points that arent on top of 2 roads connected by ramps
    """
    adjacency = build_adjacency_with_medium(files, files["relevant_roads_dissolved"])
    ramp_oids = set()
    ramps_lyr = "ramps_lyr_436"
    arcpy.management.MakeFeatureLayer(files["relevant_roads_dissolved"], ramps_lyr, "typeveg = 'rampe'")
    with arcpy.da.SearchCursor(ramps_lyr, ["OID@"]) as s_cur:
        for row in s_cur:
            ramp_oids.add(row[0])

    remove_points = set()
    
    valid_oids = defaultdict(set)
    arcpy.analysis.GenerateNearTable(files["potential_points"], files["relevant_roads_dissolved"], files["near_table"], search_radius="500 Meter", closest="ALL")
    with arcpy.da.SearchCursor(files["near_table"], ["IN_FID", "NEAR_FID"]) as s_cur:
        for row in s_cur:
            in_fid = row[0]
            near_fid = row[1]
            valid_oids[in_fid].add(near_fid)
    
    fid_fields = [
            f.name
            for f in arcpy.ListFields(files["potential_points"])
            if f.type not in ("OID", "Geometry")
        ]
    cursor_fields = ["OID@"] + fid_fields
    with arcpy.da.SearchCursor(files["potential_points"], cursor_fields) as s_cur:
        for row in s_cur:
            point_oid = row[0]
            # expect two FID fields (order depends on how Intersect was run)
            if len(row) < 3 or row[1] is None or row[2] is None:
                print(f"More or less than 2 roads for this point: {point_oid}")
                continue
            road_a = int(row[1])
            road_b = int(row[2])
            near_set = valid_oids.get(point_oid, set())
            all_paths = bfs_all_paths_with_prevous_neighbour_rule(adjacency=adjacency, start=road_a, target=road_b, max_steps=10, valid_oids=near_set)
            has_ramp = any(node in ramp_oids for path in all_paths for node in path)
            if not has_ramp:
                remove_points.add(point_oid)

    with arcpy.da.UpdateCursor(files["potential_points"], ["OID@"]) as u_cur:
        for row in u_cur:
            if row[0] in remove_points:
                u_cur.deleteRow()

def _endpoints(poly):
    pts = set()
    for part in poly:
        part = list(part)
        if not part:
            continue
        pts.add((part[0].X, part[0].Y))
        pts.add((part[-1].X, part[-1].Y))
    return pts

def build_adjacency_with_medium(files: dict, lines, medium_field="medium"):
    """
    Creates adjecency graph of roads that intersect using near table 1 meter, but with a check for medium attribute to avoid false connections where roads arent actually connected but just intersect in the geometry due to overpasses etc.
    if different mediums only keep as adjecent if they intersect at endpoints
    """
    adjacency = defaultdict(set)
    near_table = files["near_table"]
    arcpy.analysis.GenerateNearTable(
        in_features=lines,
        near_features=lines,
        out_table=near_table,
        search_radius="1 Meters",
        closest="ALL",
    )

    # Cache shapes and medium values to avoid repeated cursors
    shapes = {}
    mediums = {}
    with arcpy.da.SearchCursor(lines, ["OID@", "SHAPE@", medium_field]) as cur:
        for oid, shape, med in cur:
            shapes[oid] = shape
            mediums[oid] = med

    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
        for in_fid, near_fid in cursor:
            if in_fid == near_fid:
                continue
            # fast path: same medium -> neighbour
            if mediums.get(in_fid) == mediums.get(near_fid):
                adjacency[in_fid].add(near_fid)
                continue

            g1 = shapes.get(in_fid)
            g2 = shapes.get(near_fid)
            if g1 is None or g2 is None:
                continue

            # compute intersection geometry (dimension 1 = point)
            inter = g1.intersect(g2, 1)  # 1 for point output
            if inter is None:
                continue

            # collect intersection points as coordinate tuples
            inter_pts = set()
            for p in inter:
                inter_pts.add((p.X, p.Y))

            if not inter_pts:
                continue

            # endpoints of each polyline
            ep1 = _endpoints(g1)
            ep2 = _endpoints(g2)

            # require every intersection point to be an endpoint of both features
            if inter_pts.issubset(ep1) and inter_pts.issubset(ep2):
                adjacency[in_fid].add(near_fid)

    arcpy.management.Delete(near_table)
    return adjacency

def bfs_all_paths(
    adjacency: Dict[Any, Iterable[Any]],
    start: Any,
    target: Any,
    max_steps: int = 20,
    max_paths: Optional[int] = None,
    valid_oids: Optional[set] = None
) -> List[List[Any]]:
    """
    Find all simple paths from start to target using a BFS expansion up to max_steps edges.

    Parameters
    - adjacency: mapping node -> iterable of neighbor nodes
    - start: starting node OID
    - target: target node OID
    - max_steps: maximum number of edges to traverse (default 20)
    - max_paths: optional cap on number of returned paths (None = no cap)
    - valid_oids: optional set of all valid oids

    Returns
    - list of paths, where each path is a list of node OIDs starting with start and ending with target
    """
    if start == target:
        return [[start]]

    results: List[List[Any]] = []
    queue = deque()
    queue.append([start])

    while queue:
        path = queue.popleft()
        if len(path) - 1 > max_steps:
            # path already exceeds allowed edges; skip
            continue

        last = path[-1]
        neighbors = adjacency.get(last, ())

        for nbr in neighbors:
            if valid_oids:
                if nbr not in valid_oids:
                    continue
            if nbr in path:
                # avoid cycles; require simple paths
                continue

            new_path = path + [nbr]

            if nbr == target:
                # found a path; only accept if within max_steps
                if len(new_path) - 1 <= max_steps:
                    results.append(new_path)
                    if max_paths is not None and len(results) >= max_paths:
                        return results
                # do not expand this path further
                continue

            # only enqueue if we can still add edges without exceeding max_steps
            if len(new_path) - 1 < max_steps:
                queue.append(new_path)

    return results

def bfs_all_paths_with_prevous_neighbour_rule(
    adjacency: Dict[Any, Iterable[Any]],
    start: Any,
    target: Any,
    max_steps: int = 20,
    max_paths: Optional[int] = None,
    valid_oids: Optional[set] = None
) -> List[List[Any]]:
    """
    Find all simple paths from start to target using a BFS expansion up to max_steps edges.

    Parameters
    - adjacency: mapping node -> iterable of neighbor nodes
    - start: starting node OID
    - target: target node OID
    - max_steps: maximum number of edges to traverse (default 20)
    - max_paths: optional cap on number of returned paths (None = no cap)
    - valid_oids: optional set of all valid oids

    Returns
    - list of paths, where each path is a list of node OIDs starting with start and ending with target

    
    Additional rule:
    - If the previous node and the current node both share a neighbor, that shared
      neighbor is NOT allowed as the next step.
    This may help enforce that we actually traverse a ramp instead of just going to a neighboring road that intersects with the same ramp endpoint.
    I thought maybe this would be issue when 3 roads make a triangle,
    however if its a ramp connecting to two roads with different mediums then the roads should not be neighbours 
    and if they have the same medium then they are already connected in the adjecency and the third roads is obsolete for the path,
    and a ramp connecting two roads with same medium doesnt matter since that shouldnt be a potential point in the first place
    """
    if start == target:
        return [[start]]

    results: List[List[Any]] = []
    queue = deque()
    queue.append([start])

    while queue:
        path = queue.popleft()
        if len(path) - 1 > max_steps:
            # path already exceeds allowed edges; skip
            continue

        last = path[-1]
        neighbors = adjacency.get(last, ())
        
        # If we have a previous node, get its neighbors too
        previous_neighbors = set()
        if len(path) >= 2:
            previous = path[-2]
            previous_neighbors = set(adjacency.get(previous, ()))


        for nbr in neighbors:
            if valid_oids:
                if nbr not in valid_oids:
                    continue
            if nbr in path:
                # avoid cycles; require simple paths
                continue

            # New rule:
            # If previous node also connects to this candidate neighbor,
            # then do not allow current -> nbr
            if nbr in previous_neighbors:
                continue


            new_path = path + [nbr]

            if nbr == target:
                # found a path; only accept if within max_steps
                if len(new_path) - 1 <= max_steps:
                    results.append(new_path)
                    if max_paths is not None and len(results) >= max_paths:
                        return results
                # do not expand this path further
                continue

            # only enqueue if we can still add edges without exceeding max_steps
            if len(new_path) - 1 < max_steps:
                queue.append(new_path)

    return results

def give_points_score(files: dict):
    """
    Gives score to potential points
    """
    roads_lyr = "roads_lyr"
    arcpy.management.MakeFeatureLayer(files["relevant_roads_dissolved"], roads_lyr, "typeveg <> 'rampe'")
    road_m_v_t = {}
    with arcpy.da.SearchCursor(roads_lyr, ["OID@", "motorvegtype", "vegkategori", "typeveg"]) as s_cur:
        for row in s_cur:
            oid = row[0]
            motorvegtype = row[1]
            vegkategori = row[2]
            typeveg = row[3]
            road_m_v_t[oid] = [motorvegtype, vegkategori, typeveg]

    
    fields = [
        f.name
        for f in arcpy.ListFields(files["potential_points"])
        if f.type not in ("OID", "Geometry")
    ]
    fields = ["OID@"] + fields

    motorvegtype_score = "motorvegtype_score"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=motorvegtype_score,
        field_type="SHORT"
    )
    fields = fields + [motorvegtype_score]

    vegkategori_score = "vegkategori_score"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=vegkategori_score,
        field_type="SHORT"
    )
    fields = fields + [vegkategori_score]

    typeveg_score = "typeveg_score"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=typeveg_score,
        field_type="SHORT"
    )
    fields = fields + [typeveg_score]

    total_score = "total_score"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=total_score,
        field_type="SHORT"
    )
    fields = fields + [total_score]

    with arcpy.da.UpdateCursor(files["potential_points"], fields) as u_cur:
        for row in u_cur:
            point_oid = row[0]
            road_a = row[1]
            road_b = row[2]

            road_a_m, road_a_v, road_a_t = road_m_v_t[road_a]
            road_b_m, road_b_v, road_b_t = road_m_v_t[road_b]

            motorvegtype_score_map = {"Motorveg":1, "Motortrafikkveg":2, "Ikke motorveg":3, "Udefinert":4}
            m_a = motorvegtype_score_map.get(road_a_m)
            m_b = motorvegtype_score_map.get(road_b_m)
            m_sum = m_a+m_b
            
            vegkategori_score_map = {'E':1, 'R':2, 'F':3, 'K':4, 'P':5, 'S':6}
            v_a = vegkategori_score_map.get(road_a_v)
            v_b = vegkategori_score_map.get(road_b_v)
            v_sum = v_a+v_b

            typeveg_score_map = {"kanalisertVeg":1, "enkelBilveg":2}
            t_a = typeveg_score_map.get(road_a_t)
            t_b = typeveg_score_map.get(road_b_t)
            t_sum = t_a+t_b

            row[3] = m_sum
            row[4] = v_sum
            row[5] = t_sum
            row[6] = m_sum+v_sum+t_sum
            u_cur.updateRow(row)

@timing_decorator
def give_points_ramp_id(files: dict):
    """
    Give points a field with objid that doesnt change
    """
    field_name = "ramp_id"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=field_name,
        field_type="TEXT",
    )

    arcpy.management.CalculateField(
        in_table=files["potential_points"],
        field=field_name,
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )

def give_roads_ramp_id_2(files: dict):
    """
    Add a nullable text field 'ramp_id' to the copy_of_input feature class
    and populate it with comma-separated OIDs from potential points that intersect each line.
    Loop through dissolved_relevant roads and build map of map[oid] = orig_lines_id from the field CONCATENATE_obj_id_txt which is comma seperated list of oids
    Then loop through potential points and for each point get the two roads it intersects with the fields road_a and road_b and build a map of map[road_oid] = ramp_id(from potential points)
    Then loop through copy of input and use the map of road_oid to ramp_id and the map of road_oid to orig lines_id to write the ramp_id to thje original lines  
    """
    field_name = "ramp_id"
    arcpy.management.AddField(
            in_table=files["copy_of_input"],
            field_name=field_name,
            field_type="TEXT",
            field_is_nullable="NULLABLE",
        )
    
    orig_field = "orig_lines_id"
    orig_to_dissolved = defaultdict(set)
    with arcpy.da.SearchCursor(files["relevant_roads_dissolved"], ["OID@", orig_field]) as s_cur:
        for row in s_cur:
            oid = row[0]
            orig_ids_str = row[1]
            if orig_ids_str is None:
                continue
            orig_ids = [oid.strip() for oid in str(orig_ids_str).split(",") if oid.strip() != ""]
            for orig_id in orig_ids:
                orig_to_dissolved[orig_id].add(oid)
    
    dissolved_to_ramp = defaultdict(set)
    base = os.path.splitext(os.path.basename(files["relevant_roads_dissolved"]))[0]
    road_id_field1 = f"FID_{base}"
    road_id_field2 = f"FID_{base}_1"
    with arcpy.da.SearchCursor(files["potential_points"], ["ramp_id", road_id_field1, road_id_field2]) as s_cur:
        for row in s_cur:
            ramp_id = row[0]
            road_a = row[1]
            road_b = row[2]
            dissolved_to_ramp[road_a].add(ramp_id)
            dissolved_to_ramp[road_b].add(ramp_id)
    
    with arcpy.da.UpdateCursor(files["copy_of_input"], ["OID@", field_name]) as u_cur:
        for row in u_cur:
            oid = row[0]
            dissolved_oids = orig_to_dissolved.get(str(oid), set())
            ramp_ids = set()
            for dissolved_oid in dissolved_oids:
                ramp_id = dissolved_to_ramp.get(dissolved_oid, set())
                ramp_ids.update(ramp_id)

            if ramp_ids:
                row[1] = ",".join(sorted(ramp_ids))
                u_cur.updateRow(row)

@timing_decorator
def give_roads_ramp_id(files: dict):
    """
    Add a nullable text field 'ramp_id' to the copy_of_input feature class
    and populate it with comma-separated OIDs from potential points that intersect each line.
    If no points intersect a line the field is left NULL.
    """
    in_fc = files["copy_of_input"]
    points_fc = files["potential_points"]
    field_name = "ramp_id"
    field_length = 1000

    # ensure field exists (create if missing)
    existing = {f.name for f in arcpy.ListFields(in_fc)}
    if field_name not in existing:
        arcpy.management.AddField(
            in_table=in_fc,
            field_name=field_name,
            field_type="TEXT",
            field_length=field_length,
            field_is_nullable="NULLABLE",
        )

    # create feature layers for spatial selection
    lines_lyr = "copy_of_input_lyr_rampid"
    points_lyr = "potential_points_lyr_rampid"
    arcpy.management.MakeFeatureLayer(in_fc, lines_lyr)
    arcpy.management.MakeFeatureLayer(points_fc, points_lyr)

    # OID field names and delimiters
    lines_oid_field = arcpy.Describe(in_fc).OIDFieldName
    points_oid_field = arcpy.Describe(points_fc).OIDFieldName
    lines_oid_delim = arcpy.AddFieldDelimiters(in_fc, lines_oid_field)
    points_oid_delim = arcpy.AddFieldDelimiters(points_fc, points_oid_field)

    # Build mapping: line_oid -> list of point_oids
    line_to_points = defaultdict(list)

    # Iterate points and find intersecting lines (select features to limit work)
    with arcpy.da.SearchCursor(points_fc, ["OID@"]) as pcur:
        for prow in pcur:
            point_oid = int(prow[0])
            # select the single point in the points layer
            where_pt = f"{points_oid_delim} = {point_oid}"
            arcpy.management.SelectLayerByAttribute(points_lyr, "NEW_SELECTION", where_pt)

            # select lines that intersect the currently selected point
            arcpy.management.SelectLayerByLocation(lines_lyr, "INTERSECT", points_lyr, selection_type="NEW_SELECTION")

            # gather selected line OIDs
            with arcpy.da.SearchCursor(lines_lyr, ["OID@"]) as lcur:
                for lrow in lcur:
                    line_oid = int(lrow[0])
                    line_to_points[line_oid].append(point_oid)

            # clear selections for next iteration
            arcpy.management.SelectLayerByAttribute(points_lyr, "CLEAR_SELECTION")
            arcpy.management.SelectLayerByAttribute(lines_lyr, "CLEAR_SELECTION")

    # Write comma-separated lists into the field; set None when no points
    with arcpy.da.UpdateCursor(in_fc, ["OID@", field_name]) as ucur:
        for urow in ucur:
            line_oid = int(urow[0])
            pts = line_to_points.get(line_oid)
            if pts:
                # keep deterministic order
                pts_sorted = sorted(set(pts))
                urow[1] = ",".join(str(p) for p in pts_sorted)
            else:
                urow[1] = None
            ucur.updateRow(urow)

    # cleanup
    try:
        arcpy.management.Delete(lines_lyr)
    except Exception:
        pass
    try:
        arcpy.management.Delete(points_lyr)
    except Exception:
        pass
    

def delete_ramps(files: dict):
    layer = "layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=layer,
        where_clause="typeveg = 'rampe'",
    )
    arcpy.management.DeleteFeatures(
        in_features=layer
    )



###################################################################################
#                                       PART 2                                    #
###################################################################################
@timing_decorator
def main_part_2(input_roads_fc: str, input_points_fc: str, output_points_fc: str):
    """
    Places points on the crosses that survived the whole generalization process
    Removes points that are to close to eachother
    """
    config = core_config.WorkFileConfig(root_file=input_points_fc)
    wfm = WorkFileManager(config=config)
    files = create_wfm_gdbs_2(wfm=wfm)
    arcpy.management.CopyFeatures(input_roads_fc, files["copy_of_roads"])
    arcpy.management.CopyFeatures(input_points_fc, files["copy_of_points"])

    explode_roads(files=files)
    dissolve_exploded_roads(
        exploded_roads=files["exploded_roads"],
        output_fc=files["exploded_roads_dissolved"]
    )
    keep_relevant_roads(files=files)
    find_surviving_potential_points(files=files, input_points=input_points_fc)
    pruning(files=files)
    

    arcpy.management.CopyFeatures(
        in_features=files["potential_points_part2"],
        out_feature_class=output_points_fc,
    )

def create_wfm_gdbs_2(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of combining land use on islands.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    copy_of_roads = wfm.build_file_path(file_name="copy_of_roads", file_type="gdb")
    copy_of_points = wfm.build_file_path(file_name="copy_of_points", file_type="gdb")
    exploded_roads = wfm.build_file_path(file_name="exploded_roads", file_type="gdb")
    exploded_roads_dissolved = wfm.build_file_path(file_name="exploded_roads_dissolved", file_type="gdb")
    part2_points_lt = wfm.build_file_path(file_name="part2_points_lt", file_type="gdb")
    part2_points_lu = wfm.build_file_path(file_name="part2_points_lu", file_type="gdb")
    part2_points_ut = wfm.build_file_path(file_name="part2_points_ut", file_type="gdb")
    potential_points_part2 = wfm.build_file_path(file_name="potential_points_part2", file_type="gdb")
    
    
    return {
        "copy_of_roads": copy_of_roads, 
        "copy_of_points": copy_of_points,     
        "exploded_roads": exploded_roads,
        "exploded_roads_dissolved": exploded_roads_dissolved,
        "part2_points_lt": part2_points_lt,
        "part2_points_lu": part2_points_lu,
        "part2_points_ut": part2_points_ut,
        "potential_points_part2": potential_points_part2,
        
    }

@timing_decorator
def explode_roads(files: dict):
    """
    Roads have the column ramp_id with the obj id of potential ramp points they intersect with
    If 2 roads with different mediums cross and have the same values in ramp_id we want to move that point to the intersection of those 2 road (excluding endpoints)
    A road can intersect more than one potential point, 
    so to make sure this road can dissolve and intersect with multiple other roads that only have one of the values in ramp_id we explode the road table on the column ramp_id 
    exploding: 
        if we have one row with 3 different ramp_id values 
        we turn it into 3 seperate rows each with one of the values 
    """
    ramp_id = "ramp_id"

    # Remove existing output if present
    if arcpy.Exists(files["exploded_roads"]):
        arcpy.management.Delete(files["exploded_roads"])

    desc = arcpy.Describe(files["copy_of_roads"])
    shape_type = desc.shapeType.upper()  # e.g. "POLYLINE", "POINT"
    out_path = os.path.dirname(files["exploded_roads"])
    out_name = os.path.basename(files["exploded_roads"])

    # Create empty featureclass using input as template so fields + spatial ref are preserved
    arcpy.management.CreateFeatureclass(
        out_path,
        out_name,
        geometry_type=shape_type,
        template=files["copy_of_roads"],
        spatial_reference=desc.spatialReference,
    )

    # Determine attribute fields to copy (exclude OID / Geometry)
    all_fields = arcpy.ListFields(files["copy_of_roads"])
    attr_fields = [f.name for f in all_fields if f.type not in ("OID", "Geometry")]
    search_fields = ["SHAPE@"] + attr_fields
    insert_fields = ["SHAPE@"] + attr_fields
    ramp_idx = search_fields.index(ramp_id)

    with arcpy.da.SearchCursor(files["copy_of_roads"], search_fields) as s_cur, \
     arcpy.da.InsertCursor(files["exploded_roads"], insert_fields) as i_cur:

        ramp_field = search_fields[ramp_idx]

        for s_row in s_cur:
            # Map field name -> value for easy reuse
            row_map = dict(zip(search_fields, s_row))

            ramp_val = row_map.get(ramp_field)

            # Helper to build insert tuple in the order of insert_fields
            def build_insert_tuple(map_with_updated_ramp):
                return tuple(map_with_updated_ramp.get(f) for f in insert_fields)

            # Null or empty: insert original row once
            if ramp_val is None or str(ramp_val).strip() == "":
                i_cur.insertRow(build_insert_tuple(row_map))
                continue

            # Normalize to string and split on commas
            ramp_str = str(ramp_val)
            parts = [p.strip() for p in ramp_str.split(",") if p.strip()]


            # If only one part, insert once (keeps original behavior)
            if len(parts) == 1:
                # ensure the ramp field is the cleaned single value
                row_map[ramp_field] = parts[0]
                i_cur.insertRow(build_insert_tuple(row_map))
                continue

            # Multiple parts: insert one row per ramp id
            for part in parts:
                row_map[ramp_field] = part
                i_cur.insertRow(build_insert_tuple(row_map))

def dissolve_exploded_roads(exploded_roads: str, output_fc: str):
    """
    Dissolves roads and ramps
    using these fields: ["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"]
    """
    arcpy.management.Dissolve(
        in_features=exploded_roads, 
        out_feature_class=output_fc, 
        dissolve_field=["objtype", "medium", "motorvegtype", "vegkategori", "typeveg", "ramp_id"], 
        multi_part="SINGLE_PART",
    )


@timing_decorator
def keep_relevant_roads(files: dict):
    """
        remove roads that dont have potential to be a ramp crossing
    """
    ramp_id_count = defaultdict(int)
    with arcpy.da.SearchCursor(files["exploded_roads_dissolved"], ["OID@", "ramp_id"]) as s_cur:
        for row in s_cur:
            if row[1] is None:
                continue
            ramp_id_count[row[1]] += 1
    
    with arcpy.da.UpdateCursor(files["exploded_roads_dissolved"], ["OID@", "ramp_id"]) as u_cur:
        for row in u_cur:
            rid = row[1]
            if rid is None:
                u_cur.deleteRow()
            if ramp_id_count[rid] < 2:
                u_cur.deleteRow()

@timing_decorator   
def find_surviving_potential_points(files: dict, input_points: str):
    """
    Find intersection points between features in `exploded_roads_dissolved` that
    share the same `ramp_id` but have different `medium` values.

    
    """
    rid_points = defaultdict(list)

    # Read roads into memory grouped by OID
    road_m = {}
    road_rid = {}
    road_geom = {}
    in_fc = files["exploded_roads_dissolved"]
    fields = ["OID@", "medium", "ramp_id", "SHAPE@"]
    with arcpy.da.SearchCursor(in_fc, fields) as s_cur:
        for oid, med, rid, geom in s_cur:
            # skip null ramp_id
            if rid is None:
                continue
            road_m[oid] = med
            road_rid[oid] = str(rid)
            road_geom[oid] = geom

    # invert to ramp_id -> list of oids
    rid_to_oids = defaultdict(list)
    for oid, rid in road_rid.items():
        rid_to_oids[rid].append(oid)

    # helper to round coords for deduplication
    def _coord_key(x, y, ndigits=6):
        return (round(float(x), ndigits), round(float(y), ndigits))

    # compute intersections per ramp_id
    for rid, oids in rid_to_oids.items():
        if len(oids) < 2:
            continue
        seen = set()
        for i in range(len(oids)):
            oid_i = oids[i]
            gi = road_geom.get(oid_i)
            mi = road_m.get(oid_i)
            if gi is None or mi is None:
                continue
            # compare with later oids to avoid duplicate pairs
            for j in range(i + 1, len(oids)):
                oid_j = oids[j]
                mj = road_m.get(oid_j)
                gj = road_geom.get(oid_j)
                if gj is None or mj is None:
                    continue
                # require different medium
                if mi == mj:
                    continue

                inter = None
                try:
                    inter = gi.intersect(gj, 1)
                except Exception:
                    inter = None


                if not inter:
                    continue

                # get endpoints to exclude
                ep_i = _endpoints(gi)
                ep_j = _endpoints(gj)

                # iterate resulting points
                
                for p in inter:
                    if p is None:
                        continue
                    key = _coord_key(p.X, p.Y)
                    # skip if intersection equals an endpoint of either geometry
                    if key in ep_i or key in ep_j:
                        continue
                    if key in seen:
                        continue
                    seen.add(key)
                    # create PointGeometry with spatial reference of gi
                    sr = gi.spatialReference if hasattr(gi, "spatialReference") else None
                    pg = arcpy.PointGeometry(arcpy.Point(p.X, p.Y), sr) if sr is not None else arcpy.PointGeometry(arcpy.Point(p.X, p.Y))
                    rid_points[rid].append(pg)
    

    
    # delete existing
    out_fc = files["potential_points_part2"]
    arcpy.management.CopyFeatures(input_points, out_fc)
    arcpy.management.DeleteRows(out_fc)

    attr_fields = [f.name for f in arcpy.ListFields(input_points)
               if f.type not in ("OID", "Geometry")]
    attr_fields.remove("ramp_id")
    fields = ["ramp_id"] + attr_fields + ["SHAPE@"]
    
    
    with arcpy.da.SearchCursor(input_points, fields) as s_cur, \
        arcpy.da.InsertCursor(out_fc, fields) as ins:
        for srow in s_cur:
            oid = srow[0]
            rid_key = str(oid)                        
            pts = rid_points.get(rid_key)
            if not pts:
                continue
            # choose the first intersection (or loop pts to create multiple rows)
            new_shape = pts[0]
            new_row = list(srow)
            new_row[-1] = new_shape             # replace shape
            ins.insertRow(new_row)

def pruning(files: dict):
    """
    en func per disse punkter:
    Her kommer pruning av potensielle punkter:
    regler i rekkefølge av fjerning:
    Hvis et punkt er på 2 veier som har kobling uten rampe så fjerner vi det punktet. (USIKKER PÅ DENNE HØR MED TEAMET) (nesten garantert at denne blir med bare usikker på grense på lengde for kobling, 500m?)
    Så fjerner vi punkter som er oppå hverandre ?50m? og beholder det med høyest score (usikker på hva som blir tiebreaker)
    Hvis 2 punkter har en kort kobling som starter på en vei og er innom alle veier med punkt på, så fjerner vi punktet med lavest score (igjen tiebreaker?) (her kan vi starte med at punktene må være innen x meter fra hverandre)

    Hvis du kjører dissolve with intersections så kan du kanskje lettere ta i bruk shape_length under bfs søk?
    dissolve with intersections tenker kanskje ikke på medium så da måtte du kjørt dissolve with intersections en gang per medium og så slått sammen resultat
    """
    
    pass

def remove_points_where_roads_are_connected(files: dict):
    """
    If a point is on 2 roads that have a connection within a limit we remove it (limit yet to be decided)
    first build adjacency with medium
    loop through points and use bfs all path with start and end
    if we find a path remove within the limit remove the point
    """
    points = ""
    roads = ""

    adjacency = build_adjacency_with_medium(
        files=files,
        lines=roads,
    )

    base = os.path.splitext(os.path.basename(files["the feature class the points is built from"]))[0]
    road_id_field1 = f"FID_{base}"
    road_id_field2 = f"FID_{base}_1"
    with arcpy.da.UpdateCursor(points, [road_id_field1, road_id_field2]) as u_cur:
        for row in u_cur:
            road_id_1 = row[0]
            road_id_2 = row[1]
            path = bfs_all_paths_with_prevous_neighbour_rule(
                adjacency=adjacency,
                start=road_id_1,
                target=road_id_2,
                max_steps=10, ############################ Undecided, we might have to rebuild this so that we can do length instead of steps 
                max_paths=1,
            )
            if path:
                u_cur.deleteRow()
    


def correct_ramp_id_after_merge_divided_roads(merge_input: str, merge_output: str, merge_out_table: str):
    """
    In the roads pipeline merge divided roads will just pick a value in ramp id when merging two roads, 
    we need values from both roads in ramp_id to accuratly determine wether or not to place a point on a potential crossing,
    To correct it we use the out_table from merge divided roads to update the values in merge_output with all the values in ramp_id from the merge_input roads that were merged together,  
    ramp ids are stored as comma seperated strings 
    """
    out_table_map = defaultdict(set)
    with arcpy.da.SearchCursor(merge_out_table, ["OUTPUT_FID", "INPUT_FID"]) as s_cur:
        for row in s_cur:
            output_fid = row[0]
            input_fid = row[1]
            out_table_map[output_fid].add(input_fid)
    
    input_ramp_id_map = defaultdict(set)
    with arcpy.da.SearchCursor(merge_input, ["OID@", "ramp_id"]) as s_cur:
        for row in s_cur:
            oid = row[0]
            ramp_id = row[1]
            if ramp_id is not None:
                values = [int(x.strip()) for x in ramp_id.split(",") if x.strip()]
                for val in values:
                    input_ramp_id_map[oid].add(val)

    with arcpy.da.UpdateCursor(merge_output, ["OID@", "ramp_id"]) as u_cur:
        for row in u_cur:
            oid = row[0]
            input_fids = out_table_map.get(oid, set())
            if not input_fids:
                continue

            ramp_ids = set()
            for input_fid in input_fids:
                ramp_ids.update(input_ramp_id_map.get(input_fid, set()))

            if ramp_ids:
                row[1] = ",".join(str(r) for r in ramp_ids)
                u_cur.updateRow(row)

   
if __name__ == "__main__":
    environment_setup.main()
    main(
        input_fc=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        output_roads_fc=Road_N100.ramps__generalized_ramps__n100_road.value,
        output_points_fc=Road_N100.ramps__potential_points__n100_road.value,
    )
    
    #main_part_2(
        #input_roads_fc=Road_N100.data_preparation___road_final_output___n100_road.value,
        #input_points_fc=r"C:\GIS_Files\ag_outputs\n100\road.gdb\ramps___potential_points___n100_road",
        #output_points_fc=Road_N100.ramps__final_points__n100_road.value,
    #)
