import arcpy
from env_setup import environment_setup
from file_manager import WorkFileManager
from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
import os
from file_manager.n100.file_manager_roads import Road_N100
from collections import deque, defaultdict
from typing import Dict, Set, List, Any, Iterable, Optional



def main(input_fc: str, output_fc: str):
    config = core_config.WorkFileConfig(root_file=input_fc)
    wfm = WorkFileManager(config=config)
    files = create_wfm_gdbs(wfm=wfm)
    arcpy.management.CopyFeatures(input_fc, files["copy_of_input"])

    relevant_roads_layer = select_relevant_roads(files=files, buffer_size=900) #1000 and above gets an error about falling outside of geometry domain?
    dissolve_relevant_roads(files=files, relevant_roads_layer=relevant_roads_layer)
    make_potential_points(files=files)
    remove_points_without_ramp_connection(files=files)
    give_points_priority_and_score(files=files)

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
    potential_points = wfm.build_file_path(file_name="potential_points", file_type="gdb")
    endpoints = wfm.build_file_path(file_name="endpoints", file_type="gdb")
    near_table = wfm.build_file_path(file_name="near_table", file_type="gdb")
    
    return {
        "copy_of_input": copy_of_input,
        "rampe_buffer": rampe_buffer,
        "relevant_roads_dissolved": relevant_roads_dissolved,
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
        dissolve_option="ALL",
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
def dissolve_relevant_roads(files: dict, relevant_roads_layer: str):
    """
    Dissolves roads and ramps
    using these fields: ["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"]
    """
    arcpy.management.Dissolve(
        in_features=relevant_roads_layer, 
        out_feature_class=files["relevant_roads_dissolved"], 
        dissolve_field=["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"], 
        multi_part="SINGLE_PART",
    )

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
        output=files["potential_points"],
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
            all_paths = bfs_all_paths(adjacency=adjacency, start=road_a, target=road_b, max_steps=10, valid_oids=near_set)
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

def give_points_priority_and_score(files: dict):
    """
    Gives priority and vegkategori_score to potential points
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

    priority = "priority"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=priority,
        field_type="SHORT"
    )
    fields = fields + [priority]

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






if __name__ == "__main__":
    environment_setup.main()
    main(
        input_fc=Road_N100.data_preparation___road_single_part_2___n100_road.value,
        output_fc=Road_N100.ramps__ramp_points__n100_road.value,
    )
