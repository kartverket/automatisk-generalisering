import arcpy
import math

from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.isolated_line_remover import IsolatedLineRemover

from composition_configs import core_config
from file_manager import WorkFileManager
from file_manager.n10.file_manager_railway import Railway_N10
from input_data import input_n10
from env_setup import environment_setup


def compute_line_azimuth(geom: arcpy.Polyline):
    """Return azimuth in degrees in range [0,180). Uses first and last point of the polyline."""
    if geom is None:
        return None
    # get first and last point
    first = geom.firstPoint
    last = geom.lastPoint
    dx = last.X - first.X
    dy = last.Y - first.Y
    if dx == 0 and dy == 0:
        return None
    angle_rad = math.atan2(dy, dx)  # -pi..pi
    angle_deg = math.degrees(angle_rad)  # -180..180
    # normalize to 0..180 because direction reversed lines are still parallel
    angle_deg = angle_deg % 180.0
    if angle_deg < 0:
        angle_deg += 180.0
    return angle_deg


def azimuth_diff(a: int, b: int):
    """Return smallest absolute difference between two azimuths in degrees (0..90)."""
    diff = abs(a - b) % 180.0
    if diff > 90.0:
        diff = 180.0 - diff
    return diff


def compute_and_store_azimuth(layer: str, az_field: str = "azimuth_deg"):
    """Add azimuth field and compute azimuth for each feature using compute_line_azimuth."""
    arcpy.management.AddField(layer, az_field, "DOUBLE")
    with arcpy.da.UpdateCursor(layer, ["SHAPE@", az_field]) as ucur:
        for row in ucur:
            geom = row[0]
            az = compute_line_azimuth(geom)
            row[1] = az
            ucur.updateRow(row)
    return az_field


def analyze_neighbor_pairs(
    join_fc: str,
    az_field: str = "azimuth_deg",
    length_field: str = "Length_m",
    az_tol: int = 10,
    min_count: int = 20,
    min_length_sum: int = 10,
):
    """
    Analyze spatial join results and return set of selected TARGET_FID OIDs.
    Logic mirrors original: count neighbors with similar azimuth and accumulate length ratios.
    """
    counts = {}
    length_sum = {}
    fields = [
        "TARGET_FID",
        "src_oid",
        az_field,
        f"{az_field}_1",
        length_field,
        f"{length_field}_1",
    ]
    with arcpy.da.SearchCursor(join_fc, fields) as cur:
        for tgt, src_oid, az_tgt, az_j, length, length_1 in cur:
            if az_tgt is None or az_j is None:
                continue
            if tgt == src_oid:
                continue
            if azimuth_diff(az_tgt, az_j) <= az_tol:
                counts[tgt] = counts.get(tgt, 0) + 1
                length_ratio = (length_1 / length) if length and length != 0 else 0
                length_sum[tgt] = length_sum.get(tgt, 0) + length_ratio

    selected = {
        oid
        for oid, c in counts.items()
        if c >= min_count and length_sum.get(oid, 0) >= min_length_sum
    }
    return selected


def dissolve_original_lines(
    lines_layer: str,
    out_dissolved: str = "in_memory\\orig_lines_dissolved",
    orig_layer_name: str = "orig_lines",
):
    """Dissolve original lines layer and create a feature layer for selection."""
    arcpy.management.Dissolve(
        in_features=lines_layer,
        out_feature_class=out_dissolved,
        multi_part="SINGLE_PART",
    )
    arcpy.management.MakeFeatureLayer(out_dissolved, orig_layer_name)

    return orig_layer_name


def clip_and_erase(
    lines: str,
    buffers: str,
    clipped_fc: str = "in_memory\\clipped_lines_fc",
    erased_fc: str = "in_memory\\erased_lines_fc",
):
    """
    clip and erase, but with an additional UNIQ_ID to connect them later, already existing id like lokalid dissapears earlier in a dissolve
    """
    arcpy.AddField_management(lines, "UNIQ_ID", "LONG")
    with arcpy.da.UpdateCursor(lines, ["UNIQ_ID"]) as cur:
        for i, row in enumerate(cur, start=1):
            row[0] = i
            cur.updateRow(row)

    arcpy.analysis.Clip(
        in_features=lines, clip_features=buffers, out_feature_class=clipped_fc
    )
    arcpy.analysis.Erase(
        in_features=lines, erase_features=buffers, out_feature_class=erased_fc
    )

    return clipped_fc, erased_fc


def restore_lines_that_cross_buffer(files: dict, clipped: str, erased: str):
    """
    If a line crosses the buffer we restore it by inserting the clipped parts of the line into the erased feature class/ its own only_restored
    """

    erased_sp = erased + "_sp"
    clipped_sp = clipped + "_sp"
    arcpy.management.MultipartToSinglepart(clipped, clipped_sp)
    arcpy.management.MultipartToSinglepart(erased, erased_sp)
    id_count = {}
    with arcpy.da.SearchCursor(erased_sp, ["UNIQ_ID"]) as cur:
        for row in cur:
            uniq_id = row[0]
            if uniq_id not in id_count:
                id_count[uniq_id] = 1
                continue
            id_count[uniq_id] = id_count.get(uniq_id, 0) + 1

    with arcpy.da.SearchCursor(clipped_sp, ["UNIQ_ID"]) as cur:
        for row in cur:
            uniq_id = row[0]
            if uniq_id not in id_count:
                id_count[uniq_id] = 1
                continue
            id_count[uniq_id] = id_count.get(uniq_id, 0) + 1

    id_list = []
    for v in id_count.items():
        if v[1] > 2:
            id_list.append(v[0])

    with arcpy.da.UpdateCursor(
        clipped_sp, ["UNIQ_ID", "SHAPE@"]
    ) as u_cur, arcpy.da.InsertCursor(erased_sp, ["UNIQ_ID", "SHAPE@"]) as i_cur:
        for row in u_cur:
            if row[0] in id_list:
                i_cur.insertRow(row)
                u_cur.deleteRow()

    arcpy.CopyFeatures_management(clipped_sp, files["clipped"])
    arcpy.CopyFeatures_management(erased_sp, files["erased"])

    only_restored_layer = "only_restored_layer"
    where = "UNIQ_ID IN ({})".format(",".join(map(str, id_list)))
    arcpy.management.MakeFeatureLayer(
        erased_sp, only_restored_layer, where_clause=where
    )
    arcpy.management.CopyFeatures(only_restored_layer, files["only_restored"])

    return clipped_sp, erased_sp


def connect_lines_to_buffer(lines_fc: str, buffer_fc: str):
    bid_field = "bufferID"
    buf_bid_field = f"{bid_field}_buf"
    arcpy.management.AddField(lines_fc, bid_field, "LONG")
    arcpy.management.AddField(buffer_fc, buf_bid_field, "LONG")

    with arcpy.da.UpdateCursor(buffer_fc, ["OID@", buf_bid_field]) as ucur:
        for row in ucur:
            row[1] = int(row[0])
            ucur.updateRow(row)

    out_sj = "in_memory\\lines_buf_sj"

    arcpy.analysis.SpatialJoin(
        target_features=lines_fc,
        join_features=buffer_fc,
        out_feature_class=out_sj,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    # Build mapping from TARGET_FID (original lines OID) to bufferID from the join
    mapping = {}
    # SpatialJoin output uses TARGET_FID to reference the target feature OID
    with arcpy.da.SearchCursor(out_sj, ["TARGET_FID", buf_bid_field]) as scur:
        for row in scur:
            tgt_oid = row[0]
            buf_id = row[1]
            # convert to int or None
            mapping[int(tgt_oid)] = int(buf_id) if buf_id is not None else None

    with arcpy.da.UpdateCursor(lines_fc, ["OID@", bid_field]) as ucur:
        for row in ucur:
            oid = int(row[0])
            row[1] = mapping.get(oid, None)
            ucur.updateRow(row)


def endpoint_key(pt: arcpy.Point, tol: int = 1e-6):
    return (round(pt.X / tol) * tol, round(pt.Y / tol) * tol)


def get_endpoints_for_oid(oid: int, geom_by_oid: dict):
    g = geom_by_oid[oid]
    return endpoint_key(g.firstPoint), endpoint_key(g.lastPoint)


def intersects_buffer_edge(geom: arcpy.Polyline, buffer_outlines_geoms: list):
    for eg in buffer_outlines_geoms:
        if not geom.disjoint(eg):
            return True
    return False


def explore_paths(
    start_oid: int,
    start_endpoint: tuple,
    geom_by_oid: dict,
    adjacency: dict,
    buffer_outlines_geoms: list,
    global_visited: set,
):
    """
    Explore all paths starting from start_oid at start_endpoint going in one direction, looking for paths that intersect buffer edges.
    """
    # iterative DFS that explores all branches; stack holds (oid, cur_ep, path_list)
    stack = [(start_oid, start_endpoint, [])]
    longest_path = []
    longest_length = 0.0

    # geometry of the start line used for direction checks
    start_geom = geom_by_oid[start_oid]
    # use centroid of the start geometry as the reference point
    start_centroid = start_geom.centroid
    # small tolerance to avoid floating point noise
    tol = 1e-9

    def vec_from(a, b):
        """Return vector (bx-ax, by-ay) from point a to point b."""
        return (b[0] - a[0], b[1] - a[1])

    def dot(u, v):
        return u[0] * v[0] + u[1] * v[1]

    def norm2(u):
        return u[0] * u[0] + u[1] * u[1]

    first_iter = True
    first_iter_intersect = False
    while stack:
        oid, cur_ep, path = stack.pop()

        # avoid cycles in the current path
        if oid in path:
            continue

        # new path including this oid
        new_path = path + [oid]

        # check intersection BEFORE accepting this line

        geom = geom_by_oid[oid]
        if intersects_buffer_edge(geom, buffer_outlines_geoms):
            if first_iter:
                first_iter_intersect = True
            else:
                return True, new_path

        first_iter = False

        # update longest path candidate
        path_len = sum(geom_by_oid[p].length for p in new_path)
        if path_len > longest_length:
            longest_length = path_len
            longest_path = list(new_path)

        # find the other endpoint and push neighbors
        ep1, ep2 = get_endpoints_for_oid(oid, geom_by_oid)
        other_ep = ep2 if ep1 == cur_ep else ep1
        neighbors = adjacency.get(oid, set())

        # compute vector from the shared endpoint toward the start centroid (reference)
        other_ep_x, other_ep_y = other_ep
        # use tuple coordinates for vector math
        start_centroid_xy = (start_centroid.X, start_centroid.Y)
        v_to_start = vec_from(other_ep, start_centroid_xy)
        v_to_start_len2 = norm2(v_to_start)

        for nbr in neighbors:
            # skip if neighbor already in current path (prevents cycles)
            if nbr in new_path:
                continue
            # robust check: ensure neighbor actually shares the other_ep
            nbr_ep1, nbr_ep2 = get_endpoints_for_oid(nbr, geom_by_oid)
            if other_ep in (nbr_ep1, nbr_ep2):
                # determine the neighbor's endpoint that is opposite the shared other_ep
                nbr_other_ep = nbr_ep2 if nbr_ep1 == other_ep else nbr_ep1

                # vector from shared node to neighbor's other endpoint
                nbr_other_ep_x, nbr_other_ep_y = nbr_other_ep
                v_next = vec_from(other_ep, (nbr_other_ep_x, nbr_other_ep_y))
                v_next_len2 = norm2(v_next)

                # if either vector is degenerate, allow neighbor (can't decide direction)
                if v_to_start_len2 <= tol or v_next_len2 <= tol:
                    stack.append((nbr, other_ep, new_path))
                    first_iter_intersect = False
                    continue

                # dot product: if negative, v_next points roughly opposite v_to_start (i.e., away from start)
                dp = dot(v_next, v_to_start)
                if dp < -tol:
                    stack.append((nbr, other_ep, new_path))
                    first_iter_intersect = False
                else:
                    # skip neighbor because it does not move away from the start centroid
                    continue

        if first_iter_intersect:
            return True, new_path

    # if we exit loop without finding buffer-edge path, return longest path found
    return False, longest_path


def iterative_side_lines(
    orig_layer: str,
    outside_layer: str,
    buffers_fc: str,
    output_fc: str,
    max_iterations: int = 20,
    step: int = 10.0,
    tol: int = 1.0,
):
    """
    Iteratively expand outward from middle line:
      - Find side lines ~step m away
      - Shift them to exactly step m
      - Treat them as new middle lines for next iteration
    """

    endpoints_fc = r"in_memory\line_endpoints"
    arcpy.management.FeatureVerticesToPoints(outside_layer, endpoints_fc, "BOTH_ENDS")
    endpoint_buf = "in_memory\\endpoint_buf"
    # 1. Buffer the endpoints
    arcpy.analysis.Buffer(
        endpoints_fc,
        endpoint_buf,
        "10 Meters",
        dissolve_option="NONE",  # IMPORTANT: keep individual buffers separate
    )

    # 2. Make a layer from the endpoint buffers
    arcpy.management.MakeFeatureLayer(endpoint_buf, "endpoint_buf_lyr")

    # 3. Select only endpoint buffers that intersect the main buffers
    arcpy.management.SelectLayerByLocation(
        "endpoint_buf_lyr",
        overlap_type="INTERSECT",
        select_features=buffers_fc,
        selection_type="NEW_SELECTION",
    )

    # 4. Export only the selected endpoint buffers
    filtered_endpoint_buf = r"in_memory\endpoint_buf_filtered"
    arcpy.management.CopyFeatures("endpoint_buf_lyr", filtered_endpoint_buf)

    dissolved_endpoint_buf = "in_memory\\uncovered_buffers_merged"
    arcpy.management.Dissolve(
        in_features=filtered_endpoint_buf,
        out_feature_class=dissolved_endpoint_buf,
        dissolve_field=None,
        multi_part="SINGLE_PART",
        unsplit_lines="UNSPLIT_LINES",
    )

    all_side_lines = []

    with arcpy.da.SearchCursor(buffers_fc, ["OID@", "SHAPE@"]) as buf_cur:
        for buf_oid, buf_geom in buf_cur:
            center = buf_geom.centroid
            closest = None
            closest_oid = None
            closest_dist = float("inf")

            # Select candidate side lines inside this buffer
            arcpy.management.MakeFeatureLayer(orig_layer, "lines_lyr", "prio IN (1,2)")

            arcpy.management.SelectLayerByLocation("lines_lyr", "INTERSECT", buf_geom)

            with arcpy.da.SearchCursor(
                "lines_lyr", ["OID@", "SHAPE@", "prio"]
            ) as mid_cur:
                for oid, geom, prio in mid_cur:
                    dist = geom.distanceTo(center)
                    if dist < closest_dist:
                        closest = geom
                        closest_oid = oid
                        closest_dist = dist

            mid_line = closest
            mid_oid = closest_oid

            if not mid_line:
                continue

            # store selected geometries and their OIDs to avoid duplicates
            selected_geoms = []
            selected_oids = set()

            # start with mid_line and its OID if available
            # get mid_line OID by searching lines_lyr for geometry equal to mid_line

            if mid_oid is not None:
                selected_geoms.append(mid_line)
                selected_oids.add(mid_oid)

            for i in range(max_iterations):
                with arcpy.da.SearchCursor(
                    "lines_lyr", ["OID@", "SHAPE@", "prio"]
                ) as line_cur:
                    # mid_segment = mid_line_side.segmentAlongLine(0.25, 0.75, use_percentage=True)

                    # collect candidates that are at least one step away
                    candidates_1 = []
                    candidates_2 = []
                    for oid, geom, prio in line_cur:
                        # skip if already selected
                        if oid in selected_oids:
                            continue

                        _, _, dist, _ = mid_line.queryPointAndDistance(geom.centroid)

                        # require at least one step away (allow small tolerance)
                        too_close = False
                        if dist >= (step - tol):
                            for selected_geom in selected_geoms:
                                # mid_segment_selected_geom = selected_geom.segmentAlongLine(0.25, 0.75, use_percentage=True)
                                _, _, dist2, _ = selected_geom.queryPointAndDistance(
                                    geom.centroid
                                )
                                if dist2 < (step - tol):
                                    too_close = True
                                    break

                            if not too_close:
                                if geom.length > 100:
                                    if prio == 1:
                                        candidates_1.append((oid, geom, dist))
                                    else:
                                        candidates_2.append((oid, geom, dist))

                if candidates_1:
                    candidates = candidates_1
                else:
                    candidates = candidates_2

                if candidates:
                    # choose the candidate with the smallest distance (closest among those >= step)
                    chosen_oid, chosen_geom, chosen_dist = min(
                        candidates, key=lambda t: t[2]
                    )
                    # if chosen_geom.length > 1.0 and chosen_oid not in selected_oids:
                    selected_geoms.append(chosen_geom)
                    selected_oids.add(chosen_oid)
                    mid_line = chosen_geom
                    # reset or keep target as desired; here we reset to step
                    continue

            arcpy.management.Delete("lines_lyr")
            if not selected_geoms:
                continue

            out_fc = f"in_memory\\side_lines_oid{buf_oid}"
            arcpy.CopyFeatures_management(selected_geoms, out_fc)
            all_side_lines.append(out_fc)

    # Merge final output
    if all_side_lines:
        if arcpy.Exists(output_fc):
            arcpy.management.Delete(output_fc)
        arcpy.management.Merge(all_side_lines, output_fc)

        ##########
        # Ensure each cluster of lines going into the buffer has atleast one line that continues
        ##########

        dissolved_endpoint_buf_lyr = "dissolved_endpoint_buf_lyr"
        arcpy.management.MakeFeatureLayer(
            dissolved_endpoint_buf, dissolved_endpoint_buf_lyr
        )
        arcpy.management.SelectLayerByLocation(
            dissolved_endpoint_buf_lyr,
            "INTERSECT",
            output_fc,
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT",
        )
        connect_lines_to_buffer(orig_layer, dissolved_endpoint_buf_lyr)
        buf_id = "bufferID"

        # Spatial join to get cluster IDs
        joined = "in_memory\\side_lines_with_cluster"
        arcpy.analysis.SpatialJoin(
            target_features=orig_layer,
            join_features=dissolved_endpoint_buf_lyr,
            out_feature_class=joined,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            match_option="INTERSECT",
        )

        # For each cluster, find the longest line
        stats = "in_memory\\cluster_stats"
        arcpy.analysis.Statistics(
            in_table=joined,
            out_table=stats,
            statistics_fields=[["Shape_Length", "MAX"]],
            case_field=buf_id,
        )

        arcpy.management.MakeFeatureLayer(joined, "joined_lyr")
        arcpy.management.AddJoin("joined_lyr", buf_id, stats, buf_id)
        arcpy.management.SelectLayerByAttribute(
            "joined_lyr", "NEW_SELECTION", '"Shape_Length" = "MAX_Shape_Length"'
        )

        extra_lines = "in_memory\\extra_side_lines"
        arcpy.management.CopyFeatures("joined_lyr", extra_lines)

        with arcpy.da.SearchCursor(
            extra_lines, ["SHAPE@"]
        ) as s_cur, arcpy.da.InsertCursor(output_fc, ["SHAPE@"]) as i_cur:
            for row in s_cur:
                i_cur.insertRow(row)

        attach_extra_lines_endpoints(orig_layer, output_fc, 15)

        return output_fc
    else:
        return None


@timing_decorator
def attach_extra_lines_endpoints(orig_layer: str, output_fc: str, meters: int):
    """
    attach extra lines when endpoints are uncovered
    """
    # --- Start: ensure endpoints of orig_layer have at least one side line within 20 m ---
    # create endpoints for orig_layer
    orig_endpoints = r"in_memory\orig_line_endpoints"
    arcpy.management.FeatureVerticesToPoints(orig_layer, orig_endpoints, "BOTH_ENDS")

    output_endpoints = r"in_memory\output_line_endpoints"
    arcpy.management.FeatureVerticesToPoints(output_fc, output_endpoints, "BOTH_ENDS")

    # make a layer for the merged side lines
    arcpy.management.MakeFeatureLayer(output_fc, "side_lines_lyr")

    out_ep_buffer_geoms = []
    # iterate endpoints and check for nearby side lines
    with arcpy.da.SearchCursor(
        orig_endpoints, ["OID@", "SHAPE@"]
    ) as ep_cur, arcpy.da.InsertCursor(output_fc, ["SHAPE@"]) as out_ins:

        for ep_oid, ep_geom in ep_cur:
            # buffer the endpoint 20 m
            ep_buf = f"in_memory\\ep_buf_{ep_oid}"
            arcpy.analysis.Buffer(
                ep_geom, ep_buf, f"{meters} Meters", dissolve_option="NONE"
            )

            # check if any side line intersects this buffer
            arcpy.management.SelectLayerByLocation(
                "side_lines_lyr", "INTERSECT", ep_buf, selection_type="NEW_SELECTION"
            )
            count = int(arcpy.management.GetCount("side_lines_lyr").getOutput(0))

            if count == 0:
                # no side line within 20 m -> find candidate lines from orig_layer inside buffer
                arcpy.management.MakeFeatureLayer(orig_layer, "orig_lines_lyr")
                arcpy.management.SelectLayerByLocation(
                    "orig_lines_lyr",
                    "INTERSECT",
                    ep_buf,
                    selection_type="NEW_SELECTION",
                )

                # choose best candidate: prefer prio==1 and longest length
                best_geom = None
                best_score = -1.0
                with arcpy.da.SearchCursor(
                    "orig_lines_lyr", ["OID@", "SHAPE@", "prio", "Shape_Length"]
                ) as cand_cur:
                    for oid, geom, prio, length in cand_cur:
                        # score: prefer prio==1, then longer length
                        score = (1000 if prio == 1 else 0) + (length or 0)
                        if score > best_score:
                            best_score = score
                            best_geom = geom

                # if we found a candidate, append it to output_fc
                if best_geom is not None:
                    for geom in out_ep_buffer_geoms:
                        if not best_geom.disjoint(geom):
                            best_geom = None
                            break

                if best_geom is not None:
                    out_ins.insertRow([best_geom])
                    ep_geom_buffer = ep_geom.buffer(meters)
                    out_ep_buffer_geoms.append(ep_geom_buffer)

                # cleanup orig_lines_lyr
                arcpy.management.Delete("orig_lines_lyr")

            # cleanup buffer for this endpoint
            arcpy.management.Delete(ep_buf)

    # cleanup layers
    arcpy.management.Delete("side_lines_lyr")
    arcpy.management.Delete(orig_endpoints)
    # --- End fallback block ---


def prepare_lines(
    files: dict,
    default_source: str,
    lines_layer: str,
    max_length: float = 1000.0,
    length_field: str = "Length_m",
) -> str:
    """
    Copy source to in-memory senterlinje, export non-rail features, create lines_fc,
    calculate geodesic length and return the filtered length layer name.
    Returns the name of the length-layer (in-memory) to be used downstream.
    """
    senterlinje = r"in_memory\senterlinje"
    arcpy.management.CopyFeatures(
        in_features=default_source, out_feature_class=senterlinje
    )

    # Export non-jernbane features
    arcpy.management.MakeFeatureLayer(
        in_features=senterlinje,
        out_layer="not_jernbane",
        where_clause="jernbanetype <> 'J'",
    )
    arcpy.CopyFeatures_management("not_jernbane", files["not_jernbane"])
    # Make feature layer for jernbane = 'J'
    arcpy.management.MakeFeatureLayer(
        in_features=senterlinje,
        out_layer=lines_layer,
        where_clause="jernbanetype = 'J'",
    )

    arcpy.management.CopyFeatures(lines_layer, r"in_memory\jernbane_original")

    # Snap endpoints to each other within 3 meters
    arcpy.edit.Snap(lines_layer, [[lines_layer, "END", "3 Meters"]])

    # delete rows of lines that collapsed in snap
    with arcpy.da.UpdateCursor(lines_layer, ["SHAPE@"]) as cursor:
        for row in cursor:
            geom = row[0]
            if not geom or getattr(geom, "isEmpty", False):
                cursor.deleteRow()

    # Copy to in-memory fc and calculate length
    lines_fc = r"in_memory\lines_fc"
    arcpy.management.CopyFeatures(in_features=lines_layer, out_feature_class=lines_fc)
    arcpy.management.AddField(lines_fc, length_field, "DOUBLE")
    arcpy.management.CalculateGeometryAttributes(
        lines_fc, [[length_field, "LENGTH_GEODESIC"]], length_unit="METERS"
    )
    # Create a layer filtered by max_length
    length_layer = "length_lyr"
    arcpy.management.MakeFeatureLayer(in_features=lines_fc, out_layer=length_layer)

    return length_layer, lines_layer


def add_azimuth(length_layer: str, az_field: str = "azimuth_deg") -> None:
    """
    Add azimuth field to the provided length_layer and compute azimuth for each feature.
    """
    # Ensure field exists on the layer (AddField works on feature classes and layers)
    arcpy.management.AddField(length_layer, az_field, "DOUBLE")

    # Update cursor expects a feature class or layer; using SHAPE@ token to get geometry
    with arcpy.da.UpdateCursor(length_layer, ["SHAPE@", az_field]) as ucur:
        for row in ucur:
            geom = row[0]
            az = compute_line_azimuth(geom)
            row[1] = az
            ucur.updateRow(row)


def select_and_buffer(
    files: dict,
    length_layer: str,
    selection_lyr: str,
    buffer_dissolved_mem: str,
    buffer_distance: str = "40 Meters",
    src_oid_field: str = "src_oid",
) -> None:
    """
    Create selection layer, build buffers, spatially join buffers to lines,
    analyze neighbor pairs, select final lines, and produce dissolved buffer.
    """
    # Make selection layer from the filtered length_layer
    arcpy.management.MakeFeatureLayer(length_layer, selection_lyr)

    # Create buffer around the length features (for neighbor detection)
    buffer_fc = r"in_memory\buffer_lyr"
    arcpy.analysis.Buffer(
        in_features=length_layer,
        out_feature_class=buffer_fc,
        buffer_distance_or_field=buffer_distance,
        line_side="FULL",
        line_end_type="FLAT",
        dissolve_option="NONE",
        method="PLANAR",
    )

    # Ensure src_oid exists and populate it with the OID
    existing = [f.name for f in arcpy.ListFields(buffer_fc)]
    if src_oid_field not in existing:
        arcpy.management.AddField(buffer_fc, src_oid_field, "LONG")
        oid_name = arcpy.Describe(buffer_fc).OIDFieldName
        arcpy.management.CalculateField(
            buffer_fc, src_oid_field, f"!{oid_name}!", "PYTHON3"
        )

    # Spatial join: target = lines, join = buffers (one-to-many)
    join_fc = r"in_memory\neighbor_pairs"
    arcpy.analysis.SpatialJoin(
        target_features=length_layer,
        join_features=buffer_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # Analyze neighbor pairs  to get selected OIDs
    selected_oids = analyze_neighbor_pairs(join_fc)

    # Build SQL to select those OIDs on the selection layer
    oid_field = arcpy.Describe(selection_lyr).OIDFieldName
    oid_field_delimited = arcpy.AddFieldDelimiters(length_layer, oid_field)
    if not selected_oids:
        # If nothing selected, create an empty output and return
        arcpy.CopyFeatures_management(selection_lyr, files["selected_lines"])
        # Still create an empty dissolved buffer to keep behavior consistent
        empty_buffer = r"in_memory\buffer_selected"
        arcpy.analysis.Buffer(
            in_features=selection_lyr,
            out_feature_class=empty_buffer,
            buffer_distance_or_field=buffer_distance,
        )
        arcpy.management.Dissolve(
            in_features=empty_buffer,
            out_feature_class=buffer_dissolved_mem,
            multi_part="SINGLE_PART",
        )
        return

    sql = "{} IN ({})".format(oid_field_delimited, ",".join(map(str, selected_oids)))
    arcpy.management.SelectLayerByAttribute(selection_lyr, "NEW_SELECTION", sql)

    # Export selected lines
    arcpy.CopyFeatures_management(selection_lyr, files["selected_lines"])

    # Buffer selected lines and dissolve
    buffer_mem = r"in_memory\buffer_selected"
    arcpy.analysis.Buffer(
        in_features=selection_lyr,
        out_feature_class=buffer_mem,
        buffer_distance_or_field=buffer_distance,
    )
    arcpy.management.Dissolve(
        in_features=buffer_mem,
        out_feature_class=buffer_dissolved_mem,
        multi_part="SINGLE_PART",
    )


def connect_lines_to_buffer_and_buffer_centroids(clipped_fc: str, buffer_fc: str):
    """
    For each line in clipped_fc, find first buffer it intersects and set bufferID.
    Also create buffer centroids with bufferID assigned.
    """

    bid_field = "bufferID"
    arcpy.management.AddField(clipped_fc, bid_field, "LONG")

    buffers = []
    with arcpy.da.SearchCursor(buffer_fc, ["OID@", "SHAPE@"]) as scur:
        for row in scur:
            bid = row[0]
            geom = row[1]
            buffers.append((bid, geom))

    # 3) For each line in clipped_fc, find first buffer it intersects and set bufferID
    update_fields = [bid_field, "SHAPE@"]
    with arcpy.da.UpdateCursor(clipped_fc, update_fields) as ucur:
        for urow in ucur:
            line_geom = urow[1]
            assigned = None
            for bid, buf_geom in buffers:
                if line_geom.within(buf_geom):
                    assigned = bid
                    break
            urow[0] = assigned
            ucur.updateRow(urow)

    buffer_centroids = "in_memory\\buffer_centroids"
    arcpy.management.FeatureToPoint(buffer_fc, buffer_centroids, "CENTROID")

    arcpy.management.AddField(buffer_centroids, bid_field, "LONG")
    with arcpy.da.UpdateCursor(buffer_centroids, update_fields) as ucur:
        for urow in ucur:
            point_geom = urow[1]
            assigned = None
            for bid, buf_geom in buffers:
                if point_geom.within(buf_geom):
                    assigned = bid
                    break
            urow[0] = assigned
            ucur.updateRow(urow)

    return buffer_centroids


def create_whole_lines(
    clipped_fc: str, erased_fc: str, centroid_fc: str, buffer_fc: str
):
    """
    For each buffer group, connect lines into continuous paths starting from the line closest to the centroid.

    """
    arcpy.CreateFeatureclass_management(
        out_path="in_memory",
        out_name="complete_lines",
        geometry_type="POLYLINE",
        spatial_reference=arcpy.Describe(clipped_fc).spatialReference,
    )

    group_ids = set()
    with arcpy.da.SearchCursor(centroid_fc, ["bufferID"]) as scur:
        for row in scur:
            bid = row[0]
            group_ids.add(bid)

    keep_line_set = set()
    clipped_layer = "clipped_layer"
    arcpy.management.MakeFeatureLayer(clipped_fc, clipped_layer)
    centroid_layer = "centroid_layer"
    arcpy.management.MakeFeatureLayer(centroid_fc, centroid_layer)

    buffer_outlines = "in_memory\\buffer_outlines"
    arcpy.management.PolygonToLine(buffer_fc, buffer_outlines)

    buffer_outlines_geoms = []
    with arcpy.da.SearchCursor(buffer_outlines, ["SHAPE@"]) as ecur:
        for row in ecur:
            buffer_outlines_geoms.append(row[0])

    for bid in group_ids:

        sql = f"bufferID = {bid}"
        arcpy.management.SelectLayerByAttribute(clipped_layer, "NEW_SELECTION", sql)
        arcpy.management.SelectLayerByAttribute(centroid_layer, "NEW_SELECTION", sql)

        with arcpy.da.SearchCursor(centroid_layer, ["SHAPE@"]) as cur:
            centroid_geom = next(cur)[0]

        dist_list = []
        with arcpy.da.SearchCursor(clipped_layer, ["OID@", "SHAPE@"]) as cur:
            for oid, geom in cur:
                # geometry.distanceTo returns the planar distance between geometries
                d = geom.distanceTo(centroid_geom)
                dist_list.append((oid, d))

        # sort by distance (closest first)
        dist_list.sort(key=lambda x: x[1])

        # Read geometries and build endpoint map
        geom_by_oid = {}
        endpoints_map = {}

        # key -> set of oids
        with arcpy.da.SearchCursor(clipped_layer, ["OID@", "SHAPE@"]) as cur:
            for oid, geom in cur:
                geom_by_oid[oid] = geom
                # get first and last points
                first = geom.firstPoint
                last = geom.lastPoint
                for pt in (first, last):
                    key = endpoint_key(pt)
                    endpoints_map.setdefault(key, set()).add(oid)

        # build adjacency: oid -> set(neighbor_oids)
        adjacency = {oid: set() for oid in geom_by_oid}
        for key, oids in endpoints_map.items():
            if len(oids) > 1:
                for a in oids:
                    adjacency[a].update(oids - {a})

        # traversal: start from the closest line to centroid
        possible_path = []
        added = False
        visited = set()
        keep_line_list_list_prio1 = []
        keep_line_list_list_prio2 = []
        keep_line_list_list_prio3 = []
        for start_oid, _ in dist_list:
            if start_oid in visited:
                continue
            # choose a start endpoint: the endpoint closest to centroid
            start_geom = geom_by_oid[start_oid]
            fpt = start_geom.firstPoint
            lpt = start_geom.lastPoint

            fpt_geom = arcpy.PointGeometry(fpt, centroid_geom.spatialReference)
            lpt_geom = arcpy.PointGeometry(lpt, centroid_geom.spatialReference)

            # pick endpoint closer to centroid
            if fpt_geom.distanceTo(centroid_geom) <= lpt_geom.distanceTo(centroid_geom):
                first_endpoint = endpoint_key(fpt)
                second_endpoint = endpoint_key(lpt)
            else:
                first_endpoint = endpoint_key(lpt)
                second_endpoint = endpoint_key(fpt)

            # Explore from the first endpoint
            found1, path1 = explore_paths(
                start_oid,
                first_endpoint,
                geom_by_oid,
                adjacency,
                buffer_outlines_geoms,
                visited,
            )
            # Explore from the opposite endpoint
            found2, path2 = explore_paths(
                start_oid,
                second_endpoint,
                geom_by_oid,
                adjacency,
                buffer_outlines_geoms,
                visited,
            )

            # Merge paths and add to keep line lists based on priority
            # 1: both ends reach buffer edge
            # 2: one end reaches buffer edge
            # 3: neither end reaches buffer edge

            combined_path = []
            combined_path = list(path1)
            combined_path.extend(path2[1:])
            if found1 and found2:

                keep_line_list_list_prio1.append(combined_path)

            elif found1 or found2:

                keep_line_list_list_prio2.append(combined_path)

            else:
                keep_line_list_list_prio3.append(combined_path)

        arcpy.management.AddField(
            in_table="in_memory\\complete_lines", field_name="prio", field_type="LONG"
        )

        # Insert combined geometries
        with arcpy.da.InsertCursor(
            "in_memory\\complete_lines", ["SHAPE@", "prio"]
        ) as icur:
            for oid_list in keep_line_list_list_prio1:
                combined = None
                for oid in oid_list:
                    geom = geom_by_oid.get(oid)
                    if geom is None:
                        continue
                    if combined is None:
                        combined = geom
                    else:
                        combined = combined.union(geom)

                if combined:
                    icur.insertRow([combined, 1])

            for oid_list in keep_line_list_list_prio2:
                combined = None
                for oid in oid_list:
                    geom = geom_by_oid.get(oid)
                    if geom is None:
                        continue
                    if combined is None:
                        combined = geom
                    else:
                        combined = combined.union(geom)

                if combined:
                    icur.insertRow([combined, 2])

            for oid_list in keep_line_list_list_prio3:
                combined = None
                for oid in oid_list:
                    geom = geom_by_oid.get(oid)
                    if geom is None:
                        continue
                    if combined is None:
                        combined = geom
                    else:
                        combined = combined.union(geom)

                if combined:
                    icur.insertRow([combined, 3])

        arcpy.management.SelectLayerByAttribute(clipped_layer, "CLEAR_SELECTION")
        arcpy.management.SelectLayerByAttribute(centroid_layer, "CLEAR_SELECTION")


def keep_lines(files: dict, lines_layer: str, buffer_dissolved_mem: str):
    """
    orchestrates the steps to keep whole lines that are within the buffer and restore lines that cross the buffer edges.
    """
    orig_layer = dissolve_original_lines(lines_layer)

    clipped_fc, erased_fc = clip_and_erase(orig_layer, buffer_dissolved_mem)
    clipped_sp, erased_sp = restore_lines_that_cross_buffer(
        files, clipped_fc, erased_fc
    )

    buffer_centroids = connect_lines_to_buffer_and_buffer_centroids(
        clipped_sp, buffer_dissolved_mem
    )

    create_whole_lines(clipped_sp, erased_sp, buffer_centroids, buffer_dissolved_mem)

    arcpy.management.CopyFeatures(erased_sp, files["erased_restored"])

    arcpy.management.DeleteIdentical(
        in_dataset="in_memory\\complete_lines", fields=["SHAPE"]
    )

    arcpy.management.CopyFeatures("in_memory\\complete_lines", files["complete_lines"])

    iterative_side_lines(
        orig_layer=files["complete_lines"],
        outside_layer=files["erased_restored"],
        buffers_fc=buffer_dissolved_mem,
        output_fc=files["final_selection"],
        max_iterations=30,
        step=10.0,
        tol=1.0,
    )


def remove_small_lines(input: str, output: str, buffer_dissolved_mem: str):
    """
    Runs IsolatedLineRemover twice to remove small isolated lines.
    1st pass: removes small isolated lines in general
    2nd pass: removes small lines that get cutoff from the nettwork after generalizing the big clusters
    """
    removed_small_lines = "in_memory\\removed_small_lines"

    isolated_line_remover = IsolatedLineRemover(
        input_fc=input,
        output_fc=removed_small_lines,
        max_lines_per_group=6,
    )
    isolated_line_remover.run()

    buffer_expanded_mem = "in_memory\\buffer_expanded"
    arcpy.analysis.Buffer(
        buffer_dissolved_mem,
        out_feature_class=buffer_expanded_mem,
        buffer_distance_or_field="500 Meters",
    )

    removed_small_lines_lyr = "removed_small_lines_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=removed_small_lines, out_layer=removed_small_lines_lyr
    )

    arcpy.management.SelectLayerByLocation(
        removed_small_lines_lyr,
        overlap_type="INTERSECT",
        select_features=buffer_expanded_mem,
    )

    isolated_line_remover2 = IsolatedLineRemover(
        input_fc=removed_small_lines_lyr,
        output_fc=r"in_memory\removed_small_lines_around_buffer",
        max_lines_per_group=6,
        length_threshold_add_per_segment=150,
        search_radius_m=2,
    )
    isolated_line_remover2.run()

    removed_small_lines_lyr2 = "removed_small_lines_lyr2"
    arcpy.management.MakeFeatureLayer(
        in_features=removed_small_lines, out_layer=removed_small_lines_lyr2
    )

    arcpy.management.SelectLayerByLocation(
        removed_small_lines_lyr2,
        overlap_type="INTERSECT",
        select_features=buffer_expanded_mem,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.CopyFeatures(
        removed_small_lines_lyr2, r"in_memory\otherlines_not_removed"
    )

    arcpy.management.Merge(
        [
            r"in_memory\removed_small_lines_around_buffer",
            r"in_memory\otherlines_not_removed",
        ],
        output,
    )


def get_data_of_original_innside(innside_lines: str, orig_lines: str, output: str):
    """
    restores attributes from orig_lines to innside_lines after splitting innside_lines at orig_lines endpoints
    1. Split innside_lines at orig_lines endpoints
    2. For each segment point, find nearest orig_line
    3. Map segment to orig_line
    4. Copy attributes from orig_lines to split_lines
    5. Dissolve split_lines based on orig_lines attributes (to merge back segments that belonged to same orig_line)
    """
    points = r"in_memory\orig_lines_points"
    arcpy.management.FeatureVerticesToPoints(orig_lines, points, "BOTH_ENDS")

    split_lines = r"in_memory\lines_split_at_points"
    arcpy.management.SplitLineAtPoint(
        innside_lines, points, split_lines, search_radius="5 Meters"
    )

    # orig_lines_centerpoints = r"in_memory\orig_lines_centerpoints"
    split_lines_centerpoints = r"in_memory\split_lines_centerpoints"
    # arcpy.management.FeatureToPoint(orig_lines, orig_lines_centerpoints, "CENTROID")
    arcpy.management.FeatureToPoint(split_lines, split_lines_centerpoints, "INSIDE")

    near_table = r"in_memory\near_table_of_lines"
    arcpy.analysis.GenerateNearTable(
        split_lines_centerpoints,
        orig_lines,
        near_table,
        closest="CLOSEST",
        method="PLANAR",
    )

    seg_points_to_orig_lines = {}
    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cur:
        for in_fid, near_fid in cur:
            if in_fid not in seg_points_to_orig_lines:
                seg_points_to_orig_lines[in_fid] = near_fid

    split_points_to_split = {}
    with arcpy.da.SearchCursor(split_lines_centerpoints, ["OID@", "ORIG_FID"]) as s_cur:
        for row in s_cur:
            split_points_to_split[row[0]] = row[1]

    seg_to_orig = {}
    for seg_p, orig_l in seg_points_to_orig_lines.items():
        seg = split_points_to_split[seg_p]
        seg_to_orig[seg] = orig_l

    orig_fields = [
        f.name
        for f in arcpy.ListFields(orig_lines)
        if not f.required and f.type != "Geometry"
    ]
    orig_alias = [
        f.aliasName
        for f in arcpy.ListFields(orig_lines)
        if not f.required and f.type != "Geometry"
    ]

    target_fields = [
        f.name
        for f in arcpy.ListFields(split_lines)
        if not f.required and f.type != "Geometry"
    ]
    for fld, alias in zip(orig_fields, orig_alias):
        if fld not in target_fields:
            arcpy.management.AddField(
                split_lines,
                fld,
                arcpy.ListFields(orig_lines, fld)[0].type,
                field_alias=alias,
            )

    orig_oid_field = arcpy.Describe(orig_lines).OIDFieldName
    orig_attr = {}
    fields = [orig_oid_field] + orig_fields
    with arcpy.da.SearchCursor(orig_lines, fields) as cur:
        for row in cur:
            orig_attr[row[0]] = row[1:]

    split_oid_field = arcpy.Describe(split_lines).OIDFieldName
    update_fields = [split_oid_field] + orig_fields
    with arcpy.da.UpdateCursor(split_lines, update_fields) as ucur:
        for urow in ucur:
            seg_oid = urow[0]
            orig_oid = seg_to_orig.get(seg_oid)
            if orig_oid and orig_oid in orig_attr:
                for i, val in enumerate(orig_attr[orig_oid], start=1):
                    urow[i] = val
                ucur.updateRow(urow)

    for field in target_fields:
        if field not in orig_fields:
            arcpy.management.DeleteField(split_lines, field)

    orig_fields_dissolve = [
        f.name
        for f in arcpy.ListFields(orig_lines)
        if not f.required and f.type != "Geometry" and f.name != "SHAPE_Length"
    ]
    out_fc = r"in_memory\dissolved_split_lines_"
    arcpy.management.Dissolve(
        split_lines,
        out_fc,
        dissolve_field=orig_fields_dissolve,
        multi_part="SINGLE_PART",
    )

    arcpy.management.CopyFeatures(out_fc, output)


def restore_medium_b_lines(
    outside_lines: str, inside_lines: str, buffer: str, whole_lines: str
):
    """
    Finds medium b lines that have been cut and adds whole line connected to it, to uncut it
    """
    b_outside_layer = "b_outside_layer_123456"
    whole_intersect_b_outside_layer = "whole_intersect_b_outside_layer"
    buffer_layer = "buffer_layer_1230928721762"
    inside_lines_layer = "inside_lines_layer_127463"

    arcpy.management.MakeFeatureLayer(outside_lines, b_outside_layer, "medium = 'B'")
    arcpy.management.MakeFeatureLayer(buffer, buffer_layer)
    arcpy.management.MakeFeatureLayer(inside_lines, inside_lines_layer)

    arcpy.management.SelectLayerByLocation(b_outside_layer, "INTERSECT", buffer_layer)

    arcpy.management.SelectLayerByLocation(
        b_outside_layer,
        "INTERSECT",
        inside_lines_layer,
        selection_type="SUBSET_SELECTION",
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.MakeFeatureLayer(whole_lines, whole_intersect_b_outside_layer)
    arcpy.management.SelectLayerByLocation(
        whole_intersect_b_outside_layer, "INTERSECT", b_outside_layer
    )

    w_rows = [
        row
        for row in arcpy.da.SearchCursor(
            whole_intersect_b_outside_layer, ["OID@", "SHAPE@", "prio"]
        )
    ]

    with arcpy.da.SearchCursor(
        b_outside_layer, ["SHAPE@"]
    ) as b_cur, arcpy.da.InsertCursor(inside_lines, ["SHAPE@"]) as i_cur:

        for b_row in b_cur:
            possible_lines = {}
            b_geom = b_row[0]

            for w_row in w_rows:
                w_oid, w_geom, w_prio = w_row

                if not w_geom.disjoint(b_geom):
                    # skip if we've already stored a priority-2 line for this OID
                    if w_oid in possible_lines and possible_lines[w_oid][1] == 2:
                        continue

                    # if no entry yet, or this geometry is longer, store/replace it
                    if (
                        w_oid not in possible_lines
                        or possible_lines[w_oid][0].length < w_geom.length
                    ):
                        possible_lines[w_oid] = [w_geom, w_prio]

            # insert the selected geometries for this b_geom
            for geom, prio in possible_lines.values():
                i_cur.insertRow([geom])


@timing_decorator
def merge_lines(files: dict):
    """
    merge the seperated part together first, then remove small lines, then
    merge divided roads on lines outside of stations, seperated by jernbanetype and medium
    Dont merge lines in areas where its busy (based on analyze_neighbor_pairs), since merge dvivide roads doesnt handle the connector lines well
    """

    merge_field = "merge_field"
    arcpy.management.AddField(
        files["lines_with_attributes_innside"], merge_field, "SHORT"
    )
    arcpy.management.CalculateField(
        files["lines_with_attributes_innside"], merge_field, "0", "PYTHON3"
    )

    arcpy.management.Merge(
        [
            files["lines_with_attributes_innside"],
            files["lines_with_attributes_outside"],
            files["not_jernbane"],
        ],
        files["final_all_lines"],
    )

    remove_small_lines(
        files["final_all_lines"],
        files["small_lines_removed"],
        files["selected_lines_buffer"],
    )

    lines_singlepart = r"in_memory\lines_singlepart_89535"
    arcpy.management.MultipartToSinglepart(
        files["small_lines_removed"], lines_singlepart
    )

    busy_oids = get_busy_oids(files, lines_singlepart)

    jernbanetype_map = {"F": 10, "J": 20, "K": 30, "S": 40, "T": 50}
    medium_map = {"B": 1, "L": 2, "T": 3, "U": 4}

    with arcpy.da.UpdateCursor(
        lines_singlepart, ["jernbanetype", "medium", merge_field, "OID@"]
    ) as cursor:
        for row in cursor:
            if row[2] == 0:
                continue
            if row[3] in busy_oids:
                row[2] = 0
                cursor.updateRow(row)
                continue

            jtype = row[0]
            med = row[1]

            base = jernbanetype_map.get(jtype, 0)
            add = medium_map.get(med, 0)
            row[2] = base + add
            cursor.updateRow(row)

    outside_lines_dissolved = r"in_memory\outside_lines_dissolved_1264"
    # arcpy.management.Dissolve(outside_lines_singlepart, outside_lines_dissolved, merge_field, multi_part="SINGLE_PART")
    arcpy.cartography.MergeDividedRoads(
        in_features=lines_singlepart,
        merge_field=merge_field,
        merge_distance="7 Meters",
        out_features=Railway_N10.output_railway_n10.value,
    )


def get_busy_oids(files: dict, input: str):
    """
    use analyze_neighbor_pairs to find busy lines based on azimuth tolerance
    """
    length_field = "Length_m"
    arcpy.management.AddField(input, length_field, "DOUBLE")
    arcpy.management.CalculateGeometryAttributes(
        input, [[length_field, "LENGTH_GEODESIC"]], length_unit="METERS"
    )
    add_azimuth(input)

    # Create buffer around the length features (for neighbor detection)
    buffer_fc = files["buffer_busy_lines"]
    arcpy.analysis.Buffer(
        in_features=input,
        out_feature_class=buffer_fc,
        buffer_distance_or_field="7 Meters",
        line_side="FULL",
        line_end_type="FLAT",
        dissolve_option="NONE",
        method="PLANAR",
    )

    src_oid_field = "src_oid"
    # Ensure src_oid exists and populate it with the OID
    existing = [f.name for f in arcpy.ListFields(buffer_fc)]
    if src_oid_field not in existing:
        arcpy.management.AddField(buffer_fc, src_oid_field, "LONG")
        oid_name = arcpy.Describe(buffer_fc).OIDFieldName
        arcpy.management.CalculateField(
            buffer_fc, src_oid_field, f"!{oid_name}!", "PYTHON3"
        )

    # Spatial join: target = lines, join = buffers (one-to-many)
    join_fc = r"in_memory\neighbor_pairs_12345678"
    arcpy.analysis.SpatialJoin(
        target_features=input,
        join_features=buffer_fc,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # Analyze neighbor pairs  to get selected OIDs
    selected_oids = analyze_neighbor_pairs(
        join_fc, length_field=length_field, az_tol=15, min_count=6, min_length_sum=5
    )

    return selected_oids


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of creating contour annotations.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    railways = wfm.build_file_path(file_name="railways", file_type="gdb")
    erased = wfm.build_file_path(file_name="erased", file_type="gdb")
    erased_restored = wfm.build_file_path(file_name="erased_restored", file_type="gdb")
    clipped = wfm.build_file_path(file_name="clipped", file_type="gdb")
    complete_lines = wfm.build_file_path(file_name="complete_lines", file_type="gdb")
    not_jernbane = wfm.build_file_path(file_name="not_jernbane", file_type="gdb")
    selected_lines = wfm.build_file_path(file_name="selected_lines", file_type="gdb")
    selected_lines_buffer = wfm.build_file_path(
        file_name="selected_lines_buffer", file_type="gdb"
    )
    final_selection = wfm.build_file_path(file_name="final_selection", file_type="gdb")
    lines_with_attributes_outside = wfm.build_file_path(
        file_name="lines_with_attributes_outside", file_type="gdb"
    )
    lines_with_attributes_innside = wfm.build_file_path(
        file_name="lines_with_attributes_innside", file_type="gdb"
    )
    final_all_lines = wfm.build_file_path(file_name="final_all_lines", file_type="gdb")
    only_restored = wfm.build_file_path(file_name="only_restored", file_type="gdb")
    final_selection_restored = wfm.build_file_path(
        file_name="final_selection_restored", file_type="gdb"
    )
    cluster = wfm.build_file_path(file_name="cluster", file_type="gdb")
    small_lines_removed = wfm.build_file_path(
        file_name="small_lines_removed", file_type="gdb"
    )
    lines_outside_merged = wfm.build_file_path(
        file_name="lines_outside_merged", file_type="gdb"
    )
    buffer_busy_lines = wfm.build_file_path(
        file_name="buffer_busy_lines", file_type="gdb"
    )

    return {
        "railways": railways,
        "erased": erased,
        "erased_restored": erased_restored,
        "clipped": clipped,
        "complete_lines": complete_lines,
        "not_jernbane": not_jernbane,
        "selected_lines": selected_lines,
        "selected_lines_buffer": selected_lines_buffer,
        "final_selection": final_selection,
        "final_selection_restored": final_selection_restored,
        "lines_with_attributes_outside": lines_with_attributes_outside,
        "lines_with_attributes_innside": lines_with_attributes_innside,
        "final_all_lines": final_all_lines,
        "only_restored": only_restored,
        "cluster": cluster,
        "lines_outside_merged": lines_outside_merged,
        "small_lines_removed": small_lines_removed,
        "buffer_busy_lines": buffer_busy_lines,
    }


@timing_decorator
def main():
    #
    # For some reason these settings cause the output to worsen so we clear them then restore them
    # arcpy.env.XYTolerance, arcpy.env.XYResolution, arcpy.env.parallelProcessingFactor
    environment_setup.main()

    tol = arcpy.env.XYTolerance
    res = arcpy.env.XYResolution
    ppf = arcpy.env.parallelProcessingFactor

    arcpy.ClearEnvironment("XYTolerance")
    arcpy.ClearEnvironment("XYResolution")
    arcpy.ClearEnvironment("parallelProcessingFactor")

    source_file, files, wfm = setup_workflow()
    lines_lyr, buffer_dissolved_mem = prepare_and_select(source_file, files)
    generate_generalized_selection(files, lines_lyr, buffer_dissolved_mem)
    finalize_and_export(files, buffer_dissolved_mem)

    wfm.delete_created_files()
    arcpy.env.XYTolerance = tol
    arcpy.env.XYResolution = res
    arcpy.env.parallelProcessingFactor = ppf


def setup_workflow():
    source_file = input_n10.Railways
    working_fc = Railway_N10.input_railway_n10.value
    work_config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=work_config)
    files = create_wfm_gdbs(wfm=wfm)
    return source_file, files, wfm


@timing_decorator
def prepare_and_select(source_file: str, files: dict):
    lines_layer = "lines_layer"
    buffer_dissolved_mem = files["selected_lines_buffer"]

    length_lyr, lines_lyr = prepare_lines(files, source_file, lines_layer)
    add_azimuth(length_lyr)
    select_and_buffer(files, length_lyr, "selection_lyr", buffer_dissolved_mem)

    return lines_lyr, buffer_dissolved_mem


@timing_decorator
def generate_generalized_selection(
    files: dict, lines_lyr: str, buffer_dissolved_mem: str
):
    keep_lines(files, lines_lyr, buffer_dissolved_mem)

    arcpy.management.Merge(
        [files["final_selection"], files["only_restored"]],
        files["final_selection_restored"],
    )


@timing_decorator
def finalize_and_export(files: dict, buffer_dissolved_mem: str):
    copy_of_original_jernbane = r"in_memory\jernbane_original"

    # get outside lines with attributes
    arcpy.analysis.Erase(
        copy_of_original_jernbane,
        buffer_dissolved_mem,
        files["lines_with_attributes_outside"],
    )

    # ensure no medium b lines are cut
    restore_medium_b_lines(
        files["lines_with_attributes_outside"],
        files["final_selection_restored"],
        buffer_dissolved_mem,
        files["complete_lines"],
    )

    get_data_of_original_innside(
        files["final_selection_restored"],
        copy_of_original_jernbane,
        files["lines_with_attributes_innside"],
    )

    merge_lines(files)

    oid_field = arcpy.Describe(Railway_N10.output_railway_n10.value).OIDFieldName
    fields = [
        f.name
        for f in arcpy.ListFields(Railway_N10.output_railway_n10.value)
        if f.name != oid_field
    ]
    arcpy.management.DeleteIdentical(Railway_N10.output_railway_n10.value, fields)


if __name__ == "__main__":
    main()
