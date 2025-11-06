# Import packages
import os
import arcpy
from collections import defaultdict
from tqdm import tqdm

arcpy.env.overwriteOutput = True

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from custom_tools.decorators.timing_decorator import timing_decorator


from dam import get_endpoints, calculate_angle

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input": Road_N100.data_preparation___road_single_part_2___n100_road.value,
    "ramps": Road_N100.ramps__ramps__n100_road.value,
    "roundabouts_1": Road_N100.ramps__collapsed_roundabouts__n100_road.value,
    "roundabouts_2": Road_N100.ramps__small_roundabouts__n100_road.value,
    "cleaned_roads": Road_N100.ramps__roads_with_cleaned_roundabouts__n100_road.value,
    "buffered_ramps": Road_N100.ramps__buffered_ramps__n100_road.value,
    "roads_near_ramps": Road_N100.ramps__roads_near_ramp__n100_road.value,
    "endpoints": Road_N100.ramps__endpoints__n100_road.value,
    "dissolved_ramps": Road_N100.ramps__dissolved_ramps__n100_road.value,
    "intermediate_ramps": Road_N100.ramps__intermediate_ramps__n100_road.value,
    "merged_ramps": Road_N100.ramps__merged_ramps__n100_road.value,
    "dissolved_group": Road_N100.ramps__dissolved_group__n100_road.value,
    "splitted_group": Road_N100.ramps__splitted_group__n100_road.value,
    "ramp_points": Road_N100.ramps__ramp_points__n100_road.value,
    "ramp_points_moved": Road_N100.ramps__ramp_points_moved__n100_road.value,
    "generalized_ramps": Road_N100.ramps__generalized_ramps__n100_road.value,
}

files_to_delete = [
    # Stores all the keys from 'data_files' that should be deleted in the end
    "roundabouts_1",
    "roundabouts_2",
    "cleaned_roads",
    "buffered_ramps",
    "roads_near_ramps",
    "endpoints",
    "dissolved_ramps",
    "intermediate_ramps",
    "merged_ramps",
    "dissolved_group",
    "splitted_group",
    "ramp_points",
]


@timing_decorator
def ramp_points():
    merge_ramps()
    make_ramp_points()
    connect_roads_to_points()

    delete_intermediate_files()


##################
# Help functions
##################


def create_buffer(
    input: arcpy.Geometry | str,
    buffer_distance: str,
    buffer_type: str,
    output: arcpy.Geometry | str,
) -> None:
    """
    Createas a buffer around the features in the input,
    and dissolves those that overlaps each other.

    Args:
        input (arcpy.Geometry | str): The input layer with features
        buffer_distance (str): String describing the size of the buffer, format: "X Meters"
        buffer_type (str): String describing if it should be FLAT or ROUND ends
        output (arcpy.Geometry | str): The output layer to save the results
    """
    intermediate_fc = r"in_memory\intermediate"
    arcpy.analysis.Buffer(
        in_features=input,
        out_feature_class=intermediate_fc,
        buffer_distance_or_field=buffer_distance,
        line_end_type=buffer_type,
        dissolve_option="NONE",
        method="PLANAR",
    )
    arcpy.management.Dissolve(
        in_features=intermediate_fc,
        out_feature_class=output,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )


def split_polyline_at_index(
    polyline: arcpy.Polyline, angle_tolerance: int = 40
) -> arcpy.Polyline | None:
    """
    Splits the input polyline into two if there are an angle sharper than 40 degrees.

    Args:
        polyline (arcpy.Polyline): Polyline object to be analysed
        angle_tolerance (int, optional): Tolerance of what is categorized as a sharp angle, default 40 degrees

    Returns:
        arcpy.Polyline: Two new polylines, one starting in the point with a sharp angle,
        and one that ends in the same point
        If no sharp angle: returns None
    """
    points = polyline.getPart(0)
    sharp_index = None
    for i in tqdm(
        range(1, len(points) - 1), desc="Analysing points", colour="yellow", leave=False
    ):
        a, b, c = points[i - 1 : i + 2]
        angle = calculate_angle(a, b, c)
        if angle < angle_tolerance or angle > 360 - angle_tolerance:
            sharp_index = i
            break
    if sharp_index:
        first = arcpy.Polyline(
            arcpy.Array(points[: sharp_index + 1]), polyline.spatialReference
        )
        second = arcpy.Polyline(
            arcpy.Array(points[sharp_index:]), polyline.spatialReference
        )
        return first, second
    return None, None


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


def combine_intersecting_buffers(buffer_fc, out_fc, max_per_cluster=4):
    """
    Combine intersecting buffer polygons into single features.
    buffer_fc     Path to input buffer feature class (must be polygons).
    out_fc        Path to output feature class to create.
    temp_sr       Optional spatial reference object or WKID. If None uses buffer_fc's SR.
    """
    # determine spatial reference

    desc = arcpy.Describe(buffer_fc)
    sr = desc.spatialReference

    # load OID field name and geometries
    oid_field = arcpy.Describe(buffer_fc).OIDFieldName
    geoms = []
    oids = []
    with arcpy.da.SearchCursor(buffer_fc, [oid_field, "SHAPE@"]) as cursor:
        for oid, geom in cursor:
            if geom is None:
                continue
            oids.append(oid)
            geoms.append(geom)

    n = len(oids)

    # build adjacency list by geometry intersection
    adj = {i: set() for i in range(n)}
    for i in range(n):
        gi = geoms[i]
        for j in range(i + 1, n):
            gj = geoms[j]
            if not gi.disjoint(gj):
                adj[i].add(j)
                adj[j].add(i)

    # find connected components (DFS)
    visited = [False] * n
    components = []
    for start in range(n):
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        comp = []
        while stack:
            cur = stack.pop()
            if len(comp) == max_per_cluster:
                # limit component size to avoid very large unions
                components.append(comp)
                comp = []
            if len(comp) == 0:
                comp.append(cur)
            else:
                if not prev.disjoint(geoms[cur]):
                    comp.append(cur)
                else:
                    # store previous component
                    components.append(comp)
                    # start new component
                    comp = [cur]
            # push neighbors onto stack
            for nb in adj[cur]:
                if not visited[nb]:
                    visited[nb] = True
                    stack.append(nb)

            prev = geoms[cur]
        # append final partial component from this connected traversal
        if comp:
            components.append(comp)

    # create output feature class
    arcpy.management.CreateFeatureclass(
        "in_memory", out_fc, "POLYGON", spatial_reference=sr
    )

    # if CreateFeatureclass returned a full path different from out_fc, use that path for insert
    out_fc_final = "in_memory\\" + out_fc

    # add component ID field
    arcpy.management.AddField(out_fc_final, "ClusterID", "LONG")
    arcpy.management.AddField(out_fc_final, "NumberOfBuffer", "SHORT")

    # union geometries per component and insert
    with arcpy.da.InsertCursor(
        out_fc_final, ["SHAPE@", "ClusterID", "NumberOfBuffer"]
    ) as icur:
        for comp_id, comp in enumerate(components, start=1):
            geom_list = [geoms[idx] for idx in comp]
            number = len(geom_list)
            # union progressively to avoid very large single union call
            merged = geom_list[0]
            for g in geom_list[1:]:
                merged = merged.union(g)
            icur.insertRow([merged, comp_id, number])

    arcpy.AddMessage(
        "Created {} clusters from {} input buffers.".format(len(components), n)
    )


def remove_endpoints_points(endpoints_layer, fc):
    """
    Removes points in fc that intersect with endpoints in endpoints_layer
    """
    endpoints_fc = "in_memory\\collected_endpoints"

    sr = arcpy.Describe(endpoints_layer).spatialReference
    arcpy.CreateFeatureclass_management(
        "in_memory", "collected_endpoints", "POINT", spatial_reference=sr
    )

    with arcpy.da.SearchCursor(
        endpoints_layer, ["OID@", "SHAPE@"]
    ) as road_cur, arcpy.da.InsertCursor(endpoints_fc, ["SHAPE@"]) as ins_cur:
        for oid, geom in road_cur:
            # if oid in intersecting_oids:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg])
            ins_cur.insertRow([end_pg])

    points_lyr = arcpy.management.MakeFeatureLayer(fc, "points_lyr").getOutput(0)
    arcpy.management.SelectLayerByLocation(
        points_lyr, "INTERSECT", endpoints_fc, selection_type="NEW_SELECTION"
    )

    selected_count = int(arcpy.GetCount_management(points_lyr).getOutput(0))
    if selected_count > 0:
        arcpy.DeleteRows_management(points_lyr)

    arcpy.management.Delete(endpoints_fc)
    arcpy.management.Delete(points_lyr)


def create_near_map(
    distance_str,
    in_fc,
    near_fc,
):
    """
    Creates a near table and returns it in a map with only near rank 1 entries and the key is oid of in fc
    """
    near_table = "in_memory\\near_table"
    arcpy.GenerateNearTable_analysis(
        in_features=in_fc,
        near_features=near_fc,
        out_table=near_table,
        search_radius=distance_str,
        location="LOCATION",
        angle="NO_ANGLE",
        closest="ALL",
        method="PLANAR",
    )

    near_map = {}
    with arcpy.da.SearchCursor(
        near_table, ["IN_FID", "NEAR_X", "NEAR_Y", "NEAR_DIST", "NEAR_RANK", "NEAR_FID"]
    ) as s:
        for in_fid, nx, ny, nd, nr, nf in s:
            if nr != 1:
                continue
            if nx is None or ny is None:
                continue
            near_map[int(in_fid)] = (float(nx), float(ny), float(nd), int(nf))

    arcpy.management.Delete(near_table)

    return near_map


##################
# Main functions
##################


@timing_decorator
def merge_ramps() -> None:
    """
    Tries to merge ramps so that each ramp is one geometric object,
    then makes buffers around those and combines intersecting ones up to 4 per group.
    This is so that later when we make the points there is roughly 1 point per group of ramps,
    but bigger groups of ramps like those in Oslo get multiple points
    """
    roads_fc = data_files["input"]
    dissolved_fc = data_files["dissolved_ramps"]
    intermediate_fc = data_files["intermediate_ramps"]
    merged_fc = data_files["merged_ramps"]
    point_fc = data_files["endpoints"]
    relevant_roads_fc = data_files["roads_near_ramps"]
    buffer_fc = data_files["buffered_ramps"]

    arcpy.management.MakeFeatureLayer(
        roads_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    arcpy.management.MakeFeatureLayer(roads_fc, "roads_lyr")

    create_buffer("ramps_lyr", "20 Meters", "ROUND", buffer_fc)

    arcpy.management.SelectLayerByLocation(
        in_layer="roads_lyr", overlap_type="INTERSECT", select_features=buffer_fc
    )

    arcpy.management.CopyFeatures("roads_lyr", relevant_roads_fc)

    end_points = {}
    with arcpy.da.SearchCursor("ramps_lyr", ["SHAPE@"]) as cursor:
        for row in cursor:
            s, e = get_endpoints(row[0])

            key_s = (s.firstPoint.X, s.firstPoint.Y)
            key_e = (e.firstPoint.X, e.firstPoint.Y)

            end_points[key_s] = end_points.get(key_s, 0) + 1
            end_points[key_e] = end_points.get(key_e, 0) + 1

    with arcpy.da.SearchCursor(relevant_roads_fc, ["SHAPE@", "typeveg"]) as cursor:
        for geom, t in cursor:
            if t == "rampe":
                continue
            s, e = get_endpoints(geom)

            key_s = (s.firstPoint.X, s.firstPoint.Y)
            key_e = (e.firstPoint.X, e.firstPoint.Y)

            if end_points.get(key_s, 0) > 0:
                end_points[key_s] += 1
            if end_points.get(key_e, 0) > 0:
                end_points[key_e] += 1

    valid_end_points = set()
    for pnt in tqdm(
        end_points, desc="Fetching valid endpoints", colour="yellow", leave=False
    ):
        if end_points[pnt] > 2:
            valid_end_points.add(pnt)

    spatial_ref = arcpy.Describe(roads_fc).spatialReference
    path, name = os.path.split(point_fc)
    arcpy.management.CreateFeatureclass(
        path, name, geometry_type="POINT", spatial_reference=spatial_ref
    )

    with arcpy.da.InsertCursor(point_fc, ["SHAPE@"]) as cursor:
        for x, y in tqdm(
            valid_end_points, desc="Adding points", colour="yellow", leave=False
        ):
            point = arcpy.Point(x, y)
            point_geom = arcpy.PointGeometry(point, spatial_ref)
            cursor.insertRow([point_geom])

    arcpy.management.Dissolve(
        in_features="ramps_lyr",
        out_feature_class=dissolved_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    arcpy.management.SplitLineAtPoint(
        in_features=dissolved_fc,
        point_features=point_fc,
        out_feature_class=intermediate_fc,
        search_radius="5 Meters",
    )

    splitted_geometries = []

    with arcpy.da.UpdateCursor(intermediate_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            polyline = row[0]
            first, second = split_polyline_at_index(polyline)
            if first and second:
                cursor.deleteRow()
                splitted_geometries.extend([first, second])

    with arcpy.da.InsertCursor(intermediate_fc, ["SHAPE@"]) as insert_cursor:
        for line in splitted_geometries:
            insert_cursor.insertRow([line])

    arcpy.analysis.Buffer(intermediate_fc, "in_memory\\buffer_ramps_50m", "50 Meters")
    combine_intersecting_buffers(
        "in_memory\\buffer_ramps_50m", "buffer_ramps_50m_dissolved"
    )

    joined_output = "in_memory\\lines_with_group_id"
    arcpy.analysis.SpatialJoin(
        target_features=intermediate_fc,
        join_features="in_memory\\buffer_ramps_50m_dissolved",
        out_feature_class=joined_output,
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    arcpy.management.Dissolve(
        joined_output, intermediate_fc, dissolve_field="ClusterID"
    )

    arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause="typeveg <> 'rampe'",
    )

    arcpy.management.CopyFeatures("roads_lyr", merged_fc)

    existing_fields = [f.name for f in arcpy.ListFields(intermediate_fc)]
    attr_fields = [
        (f.name, f.type)
        for f in arcpy.ListFields(merged_fc)
        if f.type not in ("Geometry", "OID") and f.name not in existing_fields
    ]

    variants = {
        "String": "TEXT",
        "Integer": "LONG",
        "SmallInteger": "LONG",
        "Double": "DOUBLE",
        "Date": "DATE",
    }
    for field_name, field_type in tqdm(
        attr_fields, desc="Updating attributes", colour="yellow", leave=False
    ):
        string = variants[field_type]
        if string == "TEXT":
            arcpy.management.AddField(
                intermediate_fc, field_name, string, field_length=255
            )
        else:
            arcpy.management.AddField(intermediate_fc, field_name, string)

    arcpy.management.SelectLayerByAttribute("roads_lyr", "CLEAR_SELECTION")
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="roads_lyr",
        selection_type="NEW_SELECTION",
        where_clause="typeveg = 'rampe'",
    )
    road_attrs = []
    with arcpy.da.SearchCursor(
        "roads_lyr", ["SHAPE@"] + [f[0] for f in attr_fields] + ["typeveg"]
    ) as cursor:
        for row in cursor:
            road_attrs.append(row)

    with arcpy.da.UpdateCursor(
        intermediate_fc, ["SHAPE@"] + [f[0] for f in attr_fields]
    ) as cursor:
        for row_orig in tqdm(cursor, desc="Updating attributes", leave=False):
            ramp_geom = row_orig[0]
            update = defaultdict(set)
            for road_row in road_attrs:
                road_geom = road_row[0]
                road_type = road_row[-1]
                if road_type != "rampe" and ramp_geom.intersect(road_geom, 2):
                    for i, el in enumerate(road_row[1:-1]):  # skip SHAPE@ and typeveg
                        update[attr_fields[i]].add(el)

            row_orig = list(row_orig)

            final_values = {}
            for field, values in update.items():
                field = field[0]
                values = list(values)
                if field.lower() == "medium":
                    values = [v for v in values if v is not None]
                    if values:
                        final_values[field] = values[0]
                    else:
                        final_values[field] = "T"
                else:
                    final_values[field] = values[0]
            if "medium" not in final_values:
                final_values["medium"] = "T"
            for i, field in enumerate(attr_fields, start=1):
                row_orig[i] = final_values.get(field, row[i])
            cursor.updateRow(row_orig)

    arcpy.management.Append(
        inputs=intermediate_fc, target=merged_fc, schema_type="NO_TEST"
    )


@timing_decorator
def make_ramp_points() -> None:
    """
    Create center points for the ramps and move them using MovePointsToCrossings
    """

    roads_fc = data_files["merged_ramps"]
    ramp_points_fc = data_files["ramp_points"]
    output_fc = data_files["generalized_ramps"]

    out_fc = data_files["ramp_points_moved"]

    arcpy.management.CopyFeatures(roads_fc, output_fc)
    arcpy.management.MakeFeatureLayer(
        output_fc,
        "roads_lyr",
        where_clause="typeveg <> 'rampe' and objtype = 'VegSenterlinje'",
    )
    arcpy.management.MakeFeatureLayer(
        output_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    arcpy.management.FeatureToPoint("ramps_lyr", ramp_points_fc, "CENTROID")

    run = MovePointsToCrossings(
        input_road_feature=roads_fc,
        input_point_feature=ramp_points_fc,
        output_point_feature=out_fc,
    )

    run.run()


@timing_decorator
def connect_roads_to_points():
    """
    connect roads to ramp points priority 3, 3.5 and 4.
    This takes the endpoints of the roads that intersect with ramps finds the closest ramp point and ads the cords of that point to the roads start or end.
    """
    roads_fc = data_files["generalized_ramps"]
    ramp_points_fc = data_files["ramp_points_moved"]

    arcpy.management.MakeFeatureLayer(
        roads_fc, "roads_lyr", where_clause="typeveg <> 'rampe'"
    )
    arcpy.management.MakeFeatureLayer(
        roads_fc, "ramps_lyr", where_clause="typeveg = 'rampe'"
    )

    arcpy.management.MakeFeatureLayer(
        ramp_points_fc,
        "ramp_points_34_lyr",
        where_clause="priority = 3 or priority = 3.5 or priority = 4",
    )

    arcpy.management.SelectLayerByLocation(
        "roads_lyr", "INTERSECT", "ramps_lyr", selection_type="NEW_SELECTION"
    )

    sr = arcpy.Describe(ramp_points_fc).spatialReference
    endpoints_fc = "in_memory\\collected_endpoints"
    arcpy.CreateFeatureclass_management(
        "in_memory", "collected_endpoints", "POINT", spatial_reference=sr
    )
    arcpy.management.AddField(endpoints_fc, "from_road", "LONG")
    arcpy.management.AddField(endpoints_fc, "start_end", "LONG")

    with arcpy.da.SearchCursor(
        "roads_lyr", ["OID@", "SHAPE@"]
    ) as road_cur, arcpy.da.InsertCursor(
        endpoints_fc, ["SHAPE@", "from_road", "start_end"]
    ) as ins_cur:
        for oid, geom in road_cur:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg, oid, 1])
            ins_cur.insertRow([end_pg, oid, 2])

    arcpy.management.MakeFeatureLayer(endpoints_fc, "endpoints_lyr")

    arcpy.management.SelectLayerByLocation(
        "endpoints_lyr", "INTERSECT", "ramps_lyr", selection_type="NEW_SELECTION"
    )

    point_priority = {}
    roadID = {}
    with arcpy.da.SearchCursor(ramp_points_fc, ["OID@", "priority", "roadID"]) as pc:
        for pid, pr, rid in pc:
            point_priority[int(pid)] = pr
            roadID[int(pid)] = rid

    near_table = "in_memory\\near_table"
    arcpy.GenerateNearTable_analysis(
        in_features="endpoints_lyr",
        near_features=ramp_points_fc,
        out_table=near_table,
        search_radius="300 Meters",
        location="LOCATION",
        angle="NO_ANGLE",
        closest="ALL",
        method="PLANAR",
    )

    near_map = {}
    with arcpy.da.SearchCursor(
        near_table, ["IN_FID", "NEAR_FID", "NEAR_X", "NEAR_Y", "NEAR_DIST", "NEAR_RANK"]
    ) as s:
        for in_fid, near_fid, nx, ny, nd, nr in s:
            if nr != 1:
                continue
            if nx is None or ny is None:
                continue
            pr = point_priority.get(int(near_fid))
            rid = roadID.get(int(near_fid))
            # store priority as fourth element (nx, ny, dist, priority)
            near_map[int(in_fid)] = (float(nx), float(ny), float(nd), pr, rid)

    arcpy.management.Delete(near_table)

    with arcpy.da.SearchCursor(
        "endpoints_lyr", ["OID@", "from_road", "start_end"]
    ) as end_cur:
        end_dict = {}
        for oid, from_road, start_end in end_cur:
            key = (from_road, start_end)
            end_dict[key] = oid

    point_endpoint_seen = {}

    with arcpy.da.UpdateCursor("roads_lyr", ["OID@", "SHAPE@"]) as road_cur:
        for oid, geom in road_cur:
            modified = False
            # Check start point
            start_key = (oid, 1)
            end_key = (oid, 2)
            if end_key in end_dict:
                endpoint_oid = end_dict[end_key]
                if endpoint_oid in near_map:
                    nx, ny, nd, pr, rid = near_map[endpoint_oid]
                    if pr != 3 and pr != 3.5 and pr != 4:
                        continue
                    if rid == oid:
                        continue
                    new_end = arcpy.Point(nx, ny)
                    arr = arcpy.Array()
                    for part in geom:
                        for p in part:
                            arr.add(p)
                    arr.add(new_end)
                    geom = arcpy.Polyline(arr, geom.spatialReference)
                    modified = True
            else:
                if start_key in end_dict:
                    endpoint_oid = end_dict[start_key]
                    if endpoint_oid in near_map:
                        nx, ny, nd, pr, rid = near_map[endpoint_oid]
                        if pr != 3 and pr != 3.5 and pr != 4:
                            continue
                        if rid == oid:
                            continue
                        new_start = arcpy.Point(nx, ny)
                        arr = arcpy.Array()
                        arr.add(new_start)
                        for part in geom:
                            for p in part:
                                arr.add(p)
                        geom = arcpy.Polyline(arr, geom.spatialReference)
                        modified = True

            if modified:
                point_endpoint_combo = (nx, ny, nd)
                if point_endpoint_combo in point_endpoint_seen:
                    continue
                else:
                    road_cur.updateRow([oid, geom])
                    point_endpoint_seen[nx, ny, nd] = 0

    arcpy.management.DeleteFeatures("ramps_lyr")


@timing_decorator
def delete_intermediate_files() -> None:
    """
    Deletes the intermediate files used during the process.
    """
    for file in files_to_delete:
        arcpy.management.Delete(data_files[file])


class MovePointsToCrossings:
    def __init__(
        self,
        input_road_feature: str,
        input_point_feature: str,
        output_point_feature: str,
        delete_points_not_on_crossings: bool = False,
        with_ramps: bool = True,
    ):
        self.input_road_feature = input_road_feature
        self.input_point_feature = input_point_feature
        self.output_point_feature = output_point_feature

        self.delete_points_not_on_crossings = delete_points_not_on_crossings
        self.with_ramps = with_ramps

    def run(self):
        self.make_priority_points()
        self.make_priority_maps()
        self.place_points()
        for item in self.delete_list:
            arcpy.management.Delete(item)

    def make_priority_points(self):
        # in memory
        buffer_500m = "in_memory\\buffer_500m"
        buffer_100m = "in_memory\\buffer_ramps_100m"
        buffer_100m_dissolved = "in_memory\\buffer_ramps_100m_dissolved"
        self.priority1 = "in_memory\\priority1"
        self.priority1_5 = "in_memory\\priority1_5"
        self.priority2 = "in_memory\\priority2"
        self.piority2_5 = "in_memory\\priority2_5"

        # Feature layers
        roads_lyr = "roads_lyr"
        ramps_lyr = "ramps_lyr"
        motorveg_t_lyr = "motorveg_t_lyr"
        motorveg_l_lyr = "motorveg_l_lyr"
        motorveg_u_lyr = "motorveg_u_lyr"
        ikke_motorveg_t_lyr = "ikke_motorveg_t_lyr"
        ikke_motorveg_l_lyr = "ikke_motorveg_l_lyr"
        ikke_motorveg_u_lyr = "ikke_motorveg_u_lyr"
        roads_t_lyr = "roads_t_lyr"
        roads_l_lyr = "roads_l_lyr"
        roads_u_lyr = "roads_u_lyr"
        roads_ul_lyr = "roads_ul_lyr"
        priority1_lyr = "priority1_lyr"
        priority1_5_lyr = "priority1_5_lyr"
        priority2_lyr = "priority2_lyr"

        self.delete_list = [
            buffer_500m,
            buffer_100m,
            buffer_100m_dissolved,
            roads_lyr,
            motorveg_t_lyr,
            motorveg_l_lyr,
            motorveg_u_lyr,
            ikke_motorveg_t_lyr,
            ikke_motorveg_l_lyr,
            ikke_motorveg_u_lyr,
            roads_t_lyr,
            roads_l_lyr,
            roads_u_lyr,
            roads_ul_lyr,
            priority1_lyr,
            priority1_5_lyr,
            priority2_lyr,
        ]

        arcpy.management.MakeFeatureLayer(
            self.input_road_feature,
            roads_lyr,
            where_clause="typeveg <> 'rampe' and objtype = 'VegSenterlinje'",
        )
        # Select roads within 500 meters to iterate over fewer objects
        arcpy.analysis.Buffer(
            self.input_point_feature, buffer_500m, "500 Meters", dissolve_option="ALL"
        )
        arcpy.management.SelectLayerByLocation(
            roads_lyr, "INTERSECT", buffer_500m, selection_type="NEW_SELECTION"
        )

        # Create layers for different road types
        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            motorveg_t_lyr,
            where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'T'",
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            motorveg_l_lyr,
            where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'L'",
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            motorveg_u_lyr,
            where_clause="(motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg') and medium = 'U'",
        )

        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            ikke_motorveg_t_lyr,
            where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'T'",
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            ikke_motorveg_l_lyr,
            where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'L'",
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            ikke_motorveg_u_lyr,
            where_clause="(motorvegtype <> 'Motortrafikkveg' and motorvegtype <> 'Motorveg') and medium = 'U'",
        )

        arcpy.management.MakeFeatureLayer(
            roads_lyr, roads_t_lyr, where_clause="medium = 'T'"
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr, roads_l_lyr, where_clause="medium = 'L'"
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr, roads_u_lyr, where_clause="medium = 'U'"
        )
        arcpy.management.MakeFeatureLayer(
            roads_lyr, roads_ul_lyr, where_clause="medium <> 'T'"
        )

        self.make_priority1_points(
            motorveg_t_lyr, motorveg_l_lyr, motorveg_u_lyr, roads_ul_lyr, self.priority1
        )
        self.make_priority1_5_points(
            motorveg_t_lyr,
            motorveg_l_lyr,
            motorveg_u_lyr,
            ikke_motorveg_t_lyr,
            ikke_motorveg_l_lyr,
            ikke_motorveg_u_lyr,
            roads_ul_lyr,
            self.priority1_5,
        )
        self.make_priority2_points(
            roads_t_lyr, roads_l_lyr, roads_u_lyr, roads_ul_lyr, self.priority2
        )
        if not self.with_ramps:
            self.make_priority2_5_points(roads_lyr, self.piority2_5)

            # keep only priority points within 100 meters of ramps
        if self.with_ramps:
            arcpy.management.MakeFeatureLayer(
                self.input_road_feature, ramps_lyr, where_clause="typeveg = 'rampe'"
            )
            arcpy.analysis.Buffer(ramps_lyr, buffer_100m, "100 Meters")
            combine_intersecting_buffers(
                buffer_100m, "buffer_ramps_100m_dissolved", max_per_cluster=1000
            )

            arcpy.management.MakeFeatureLayer(self.priority1, priority1_lyr)
            arcpy.management.SelectLayerByLocation(
                priority1_lyr,
                "INTERSECT",
                buffer_100m_dissolved,
                selection_type="NEW_SELECTION",
            )
            arcpy.management.SelectLayerByAttribute(
                priority1_lyr, "SWITCH_SELECTION", "1=1"
            )
            count = int(arcpy.management.GetCount(priority1_lyr).getOutput(0))
            if count > 0:
                arcpy.management.DeleteFeatures(priority1_lyr)

            arcpy.management.MakeFeatureLayer(self.priority1_5, priority1_5_lyr)
            arcpy.management.SelectLayerByLocation(
                priority1_5_lyr,
                "INTERSECT",
                buffer_100m_dissolved,
                selection_type="NEW_SELECTION",
            )
            arcpy.management.SelectLayerByAttribute(
                priority1_5_lyr, "SWITCH_SELECTION", "1=1"
            )
            count = int(arcpy.management.GetCount(priority1_5_lyr).getOutput(0))
            if count > 0:
                arcpy.management.DeleteFeatures(priority1_5_lyr)

            arcpy.management.MakeFeatureLayer(self.priority2, priority2_lyr)
            arcpy.management.SelectLayerByLocation(
                priority2_lyr,
                "INTERSECT",
                buffer_100m_dissolved,
                selection_type="NEW_SELECTION",
            )
            arcpy.management.SelectLayerByAttribute(
                priority2_lyr, "SWITCH_SELECTION", "1=1"
            )
            count = int(arcpy.management.GetCount(priority2_lyr).getOutput(0))
            if count > 0:
                arcpy.management.DeleteFeatures(priority2_lyr)

    def make_priority_maps(self):
        # oids
        all_oids = []
        oid_field = arcpy.Describe(self.input_point_feature).oidFieldName
        with arcpy.da.SearchCursor(self.input_point_feature, [oid_field]) as sc:
            for row in sc:
                all_oids.append(int(row[0]))

        if self.with_ramps:
            self.near1_map = self.create_near_map_unmatched_buffer(
                "500 Meters",
                self.input_point_feature,
                self.priority1,
                all_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near1_map = self.create_near_map_unmatched(
                "200 Meters", self.input_point_feature, self.priority1, all_oids
            )
        self.unmatched_oids = [oid for oid in all_oids if oid not in self.near1_map]

        if self.with_ramps:
            self.near1_5_map = self.create_near_map_unmatched_buffer(
                "500 Meters",
                self.input_point_feature,
                self.priority1_5,
                self.unmatched_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near1_5_map = self.create_near_map_unmatched(
                "200 Meters",
                self.input_point_feature,
                self.priority1_5,
                self.unmatched_oids,
            )
        self.unmatched_oids = [
            oid for oid in self.unmatched_oids if oid not in self.near1_5_map
        ]

        if self.with_ramps:
            self.near2_map = self.create_near_map_unmatched_buffer(
                "500 Meters",
                self.input_point_feature,
                self.priority2,
                self.unmatched_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near2_map = self.create_near_map_unmatched(
                "200 Meters",
                self.input_point_feature,
                self.priority2,
                self.unmatched_oids,
            )
        self.unmatched_oids = [
            oid for oid in self.unmatched_oids if oid not in self.near2_map
        ]

        if not self.with_ramps:
            self.near2_5_map = self.create_near_map_unmatched(
                "200 Meters",
                self.input_point_feature,
                self.piority2_5,
                self.unmatched_oids,
            )
            self.unmatched_oids = [
                oid for oid in self.unmatched_oids if oid not in self.near2_5_map
            ]

        roads_lyr = "roads_lyr"

        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            "motorveg_lyr",
            where_clause="motorvegtype = 'Motortrafikkveg' or motorvegtype = 'Motorveg'",
        )
        if self.with_ramps:
            self.near3_map = self.create_near_map_unmatched_buffer(
                "100 Meters",
                self.input_point_feature,
                "motorveg_lyr",
                self.unmatched_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near3_map = self.create_near_map_unmatched(
                "100 Meters",
                self.input_point_feature,
                "motorveg_lyr",
                self.unmatched_oids,
            )
        self.unmatched_oids = [
            oid for oid in self.unmatched_oids if oid not in self.near3_map
        ]

        arcpy.management.MakeFeatureLayer(
            roads_lyr,
            "ikke_motorveg_lyr",
            where_clause="motorvegtype = 'Ikke motorveg'",
        )
        if self.with_ramps:
            self.near3_5_map = self.create_near_map_unmatched_buffer(
                "100 Meters",
                self.input_point_feature,
                "ikke_motorveg_lyr",
                self.unmatched_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near3_5_map = self.create_near_map_unmatched(
                "100 Meters",
                self.input_point_feature,
                "ikke_motorveg_lyr",
                self.unmatched_oids,
            )
        self.unmatched_oids = [
            oid for oid in self.unmatched_oids if oid not in self.near3_5_map
        ]

        if self.with_ramps:
            self.near4_map = self.create_near_map_unmatched_buffer(
                "100 Meters",
                self.input_point_feature,
                "roads_lyr",
                self.unmatched_oids,
                "in_memory\\buffer_ramps_100m_dissolved",
            )
        else:
            self.near4_map = self.create_near_map_unmatched(
                "100 Meters", self.input_point_feature, "roads_lyr", self.unmatched_oids
            )

    def place_points(self):
        """
        moves the points using the cords stored in the near maps and inserts what priority the point is and what road the point is on.
        """
        sr = arcpy.Describe(self.input_point_feature).spatialReference

        arcpy.management.CreateFeatureclass(
            os.path.dirname(self.output_point_feature),
            os.path.basename(self.output_point_feature),
            "POINT",
            spatial_reference=arcpy.Describe(self.input_point_feature).spatialReference,
        )

        existing_out_fields = [
            f.name
            for f in arcpy.ListFields(self.output_point_feature)
            if f.type not in ("OID", "Geometry")
        ]
        out_fields = ["SHAPE@", "priority", "roadID"] + existing_out_fields
        in_fields = [
            arcpy.Describe(self.input_point_feature).oidFieldName,
            "SHAPE@",
        ] + existing_out_fields

        arcpy.management.AddField(self.output_point_feature, "priority", "DOUBLE")
        arcpy.management.AddField(self.output_point_feature, "roadID", "DOUBLE")

        with arcpy.da.SearchCursor(
            self.input_point_feature, in_fields
        ) as scur, arcpy.da.InsertCursor(self.output_point_feature, out_fields) as icur:
            for row in scur:
                oid = int(row[0])
                orig_geom = row[1]
                changed = False

                # Priority 1
                if oid in self.near1_map:
                    nx, ny, nd, nf = self.near1_map[oid]
                    new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                    priority = [1]
                    roadid = [nf]
                    changed = True

                # Priority 1.5
                elif oid in self.near1_5_map:
                    nx, ny, nd, nf = self.near1_5_map[oid]
                    new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                    priority = [1.5]
                    roadid = [nf]
                    changed = True

                # Priority 2
                elif oid in self.near2_map:
                    nx, ny, nd, nf = self.near2_map[oid]
                    new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                    priority = [2]
                    roadid = [nf]
                    changed = True

                # Priority 2.5 (only if ramps are not allowed)
                elif not self.with_ramps and oid in self.near2_5_map:
                    nx, ny, nd, nf = self.near2_5_map[oid]
                    new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                    priority = [2.5]
                    roadid = [nf]
                    changed = True

                # Priority 3 and above (only if deletion is not enforced)
                elif not self.delete_points_not_on_crossings:
                    if oid in self.near3_map:
                        nx, ny, nd, nf = self.near3_map[oid]
                        new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                        priority = [3]
                        roadid = [nf]
                        changed = True
                    elif oid in self.near3_5_map:
                        nx, ny, nd, nf = self.near3_5_map[oid]
                        new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                        priority = [3.5]
                        roadid = [nf]
                        changed = True
                    elif oid in self.near4_map:
                        nx, ny, nd, nf = self.near4_map[oid]
                        new_geom = arcpy.PointGeometry(arcpy.Point(nx, ny), sr)
                        priority = [4]
                        roadid = [nf]
                        changed = True
                    else:
                        new_geom = orig_geom
                        priority = [0]
                        roadid = [None]
                        changed = True

                if changed:
                    insert_row = [new_geom] + priority + roadid
                    icur.insertRow(insert_row)

        # Remove duplicates
        arcpy.DeleteIdentical_management(
            in_dataset=self.output_point_feature,
            fields="Shape",
            xy_tolerance="100 Meters",
        )

    @staticmethod
    def make_priority1_points(
        motorveg_t_lyr, motorveg_l_lyr, motorveg_u_lyr, roads_ul_lyr, priority1
    ):
        """
        priority 1 is where intersects crosses motorveg
        """
        intersect = "in_memory\\intersect8"
        intersect2 = "in_memory\\intersect9"

        arcpy.Intersect_analysis(
            [motorveg_t_lyr, motorveg_l_lyr],
            intersect,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_t_lyr, motorveg_u_lyr],
            intersect2,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_u_lyr, motorveg_l_lyr],
            priority1,
            join_attributes="ALL",
            output_type="POINT",
        )

        arcpy.management.Append([intersect, intersect2], priority1)
        remove_endpoints_points(roads_ul_lyr, priority1)

        arcpy.management.Delete(intersect)
        arcpy.management.Delete(intersect2)

    @staticmethod
    def make_priority1_5_points(
        motorveg_t_lyr,
        motorveg_l_lyr,
        motorveg_u_lyr,
        ikke_motorveg_t_lyr,
        ikke_motorveg_l_lyr,
        ikke_motorveg_u_lyr,
        roads_ul_lyr,
        priority1_5,
    ):
        """
        priority 1_5 is where motorveg intersects non motorveg with different medium
        """
        intersect1 = "in_memory\\intersect1"
        intersect2 = "in_memory\\intersect2"
        intersect3 = "in_memory\\intersect3"
        intersect4 = "in_memory\\intersect4"
        intersect5 = "in_memory\\intersect5"

        arcpy.Intersect_analysis(
            [motorveg_t_lyr, ikke_motorveg_l_lyr],
            intersect1,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_t_lyr, ikke_motorveg_u_lyr],
            intersect2,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_l_lyr, ikke_motorveg_u_lyr],
            intersect3,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_l_lyr, ikke_motorveg_t_lyr],
            intersect4,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_u_lyr, ikke_motorveg_t_lyr],
            intersect5,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [motorveg_u_lyr, ikke_motorveg_l_lyr],
            priority1_5,
            join_attributes="ALL",
            output_type="POINT",
        )

        arcpy.management.Append(
            [intersect1, intersect2, intersect3, intersect4, intersect5], priority1_5
        )
        remove_endpoints_points(roads_ul_lyr, priority1_5)

        arcpy.management.Delete(intersect1)
        arcpy.management.Delete(intersect2)
        arcpy.management.Delete(intersect3)
        arcpy.management.Delete(intersect4)
        arcpy.management.Delete(intersect5)

    @staticmethod
    def make_priority2_points(
        roads_t_lyr, roads_l_lyr, roads_u_lyr, roads_ul_lyr, priority2
    ):
        """
        Priority 2 is where any road intersects another road with different mediums
        """
        intersect1 = "in_memory\\intersect1"
        intersect2 = "in_memory\\intersect2"

        arcpy.Intersect_analysis(
            [roads_t_lyr, roads_l_lyr],
            intersect1,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [roads_t_lyr, roads_u_lyr],
            intersect2,
            join_attributes="ALL",
            output_type="POINT",
        )
        arcpy.Intersect_analysis(
            [roads_u_lyr, roads_l_lyr],
            priority2,
            join_attributes="ALL",
            output_type="POINT",
        )

        arcpy.management.Append([intersect1, intersect2], priority2)
        remove_endpoints_points(roads_ul_lyr, priority2)

        arcpy.management.Delete(intersect1)
        arcpy.management.Delete(intersect2)

    @staticmethod
    def make_priority2_5_points(roads_lyr, priority2_5):
        """
        priority 2_5 is where the endpoints of 3 different roads or more intersect
        """

        endpoints_fc = "in_memory\\collected_endpoints"

        sr = arcpy.Describe(roads_lyr).spatialReference
        arcpy.CreateFeatureclass_management(
            "in_memory", "collected_endpoints", "POINT", spatial_reference=sr
        )
        arcpy.CreateFeatureclass_management(
            os.path.dirname(priority2_5),
            os.path.basename(priority2_5),
            "POINT",
            spatial_reference=sr,
        )

        with arcpy.da.SearchCursor(
            roads_lyr, ["OID@", "SHAPE@"]
        ) as road_cur, arcpy.da.InsertCursor(endpoints_fc, ["SHAPE@"]) as ins_cur:
            for oid, geom in road_cur:
                # if oid in intersecting_oids:
                start_pg, end_pg = get_line_endpoints(geom)
                ins_cur.insertRow([start_pg])
                ins_cur.insertRow([end_pg])

        # build dictionary: key = (x,y) or rounded coords, value = count
        round_decimals = None
        counts = {}
        coords_example = {}  # store one example point geometry per key

        with arcpy.da.SearchCursor(endpoints_fc, ["SHAPE@XY"]) as cur:
            for row in cur:
                x, y = row[0]
                if round_decimals is None:
                    key = (x, y)
                else:
                    key = (round(x, round_decimals), round(y, round_decimals))
                counts[key] = counts.get(key, 0) + 1
                if key not in coords_example:
                    coords_example[key] = (x, y)

        # insert keys with count >= 3
        with arcpy.da.InsertCursor(priority2_5, ["SHAPE@XY", "count"]) as ins:
            # add count field if it doesn't exist
            if "count" not in [f.name for f in arcpy.ListFields(priority2_5)]:
                arcpy.management.AddField(priority2_5, "count", "LONG")
            for key, cnt in counts.items():
                if cnt >= 3:
                    x, y = coords_example[key]
                    ins.insertRow([(x, y), cnt])

        arcpy.management.Delete(endpoints_fc)

    @staticmethod
    def create_near_map_unmatched_buffer(
        distance_str, in_fc, near_fc, unmatched_oids, buffer_fc
    ):
        """
        For the subset of points in 'in_fc' (unmatched_oids) find the nearest feature in 'near_fc'
        but only if that near_fc feature intersects the closest buffer polygon to the point.
        Returns a dict: {in_fid: (near_x, near_y, near_dist, near_fid)}
        """
        if unmatched_oids:
            points_lyr = "points_lyr_unmatched"
            arcpy.MakeFeatureLayer_management(in_fc, points_lyr)

            oid_field = arcpy.Describe(in_fc).oidFieldName

            in_list = ",".join(map(str, unmatched_oids))
            where = f"{arcpy.AddFieldDelimiters(in_fc, oid_field)} IN ({in_list})"

            arcpy.SelectLayerByAttribute_management(points_lyr, "NEW_SELECTION", where)

            near_table = "in_memory\\near_table"
            arcpy.GenerateNearTable_analysis(
                in_features=points_lyr,
                near_features=buffer_fc,
                out_table=near_table,
                search_radius=distance_str,
                location="LOCATION",
                angle="NO_ANGLE",
                closest="ALL",
                method="PLANAR",
            )

            in_buffer_map = {}
            with arcpy.da.SearchCursor(
                near_table, ["IN_FID", "NEAR_FID", "NEAR_RANK"]
            ) as s:
                for in_fid, nf, nr in s:
                    if nr != 1:
                        continue
                    if nf is None:
                        continue
                    in_buffer_map[int(in_fid)] = float(nf)

            arcpy.management.Delete(near_table)

            near_table = "in_memory\\near_table"
            arcpy.GenerateNearTable_analysis(
                in_features=near_fc,
                near_features=buffer_fc,
                out_table=near_table,
                search_radius=distance_str,
                location="LOCATION",
                angle="NO_ANGLE",
                closest="ALL",
                method="PLANAR",
            )

            near_buffer_map = {}
            with arcpy.da.SearchCursor(
                near_table, ["IN_FID", "NEAR_FID", "NEAR_RANK"]
            ) as s:
                for in_fid, nf, nr in s:
                    if nr != 1:
                        continue
                    if nf is None:
                        continue
                    near_buffer_map[int(in_fid)] = float(nf)

            arcpy.management.Delete(near_table)

            near_table = "in_memory\\near_table"
            arcpy.GenerateNearTable_analysis(
                in_features=points_lyr,
                near_features=near_fc,
                out_table=near_table,
                search_radius=distance_str,
                location="LOCATION",
                angle="NO_ANGLE",
                closest="ALL",
                method="PLANAR",
            )

            near_map = {}
            with arcpy.da.SearchCursor(
                near_table, ["IN_FID", "NEAR_X", "NEAR_Y", "NEAR_FID", "NEAR_RANK"]
            ) as s:
                for in_fid, nx, ny, nf, nr in s:
                    if nx is None or ny is None:
                        continue
                    if in_buffer_map[int(in_fid)] == near_buffer_map[int(nf)]:
                        if int(in_fid) in near_map:
                            if near_map[int(in_fid)][2] > nr:
                                near_map[int(in_fid)] = (
                                    float(nx),
                                    float(ny),
                                    float(nr),
                                    int(nf),
                                )
                            else:
                                continue
                        else:
                            near_map[int(in_fid)] = (
                                float(nx),
                                float(ny),
                                float(nr),
                                int(nf),
                            )
                    else:
                        continue

            arcpy.management.Delete(near_table)

        else:
            near_map = {}

        return near_map

    @staticmethod
    def create_near_map_unmatched(distance_str, in_fc, near_fc, unmatched_oids):
        if unmatched_oids:
            points_lyr = "points_lyr_unmatched"
            arcpy.MakeFeatureLayer_management(in_fc, points_lyr)

            oid_field = arcpy.Describe(in_fc).oidFieldName

            in_list = ",".join(map(str, unmatched_oids))
            where = f"{arcpy.AddFieldDelimiters(in_fc, oid_field)} IN ({in_list})"

            arcpy.SelectLayerByAttribute_management(points_lyr, "NEW_SELECTION", where)

            near_map = create_near_map(distance_str, points_lyr, near_fc)

            arcpy.Delete_management(points_lyr)

        else:
            near_map = {}

        return near_map


if __name__ == "__main__":
    ramp_points()
