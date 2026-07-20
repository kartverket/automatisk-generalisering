import arcpy
from env_setup import environment_setup
from file_manager import WorkFileManager
from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
import os
from file_manager.n100.file_manager_roads import Road_N100
from collections import deque, defaultdict
from typing import Dict, Set, List, Any, Iterable, Optional


@timing_decorator
def main(input_fc: str, output_roads_fc: str, output_points_fc: str):
    """
    creates points that symbolize a connection between two roads,
    give id of point to the roads that it symbolizes a connection between,
    this is how we track the movement of the cross through further generalization of the roads,
    removes all ramps from the roads,
    Not implemented yet but will restore connections between roads that get lost because of ramp removal when the connection isnt symbolized through a point
    """
    config = core_config.WorkFileConfig(root_file=input_fc)
    wfm = WorkFileManager(config=config)
    files = create_wfm_gdbs(wfm=wfm)
    arcpy.management.CopyFeatures(input_fc, files["copy_of_input"])

    relevant_roads_layer = select_relevant_roads(files=files, buffer_size=400)

    dissolve_and_return_connection(
        lines_fc=relevant_roads_layer,
        output_fc=files["relevant_roads_dissolved"],
        dissolve_fields=["objtype", "medium", "motorvegtype", "vegkategori", "typeveg"],
    )
    add_ramps_to_relevant_roads(files=files)

    make_potential_points(files=files)
    give_points_score(files=files)
    give_points_ramp_id(files=files)
    all_ramp_oids_per_rampid, all_ramp_oids_per_rampid_extended_length_threshold = (
        remove_points_without_ramp_connection(files=files, max_path_length=1000)
    )
    add_subsets_values(files=files, all_ramp_oids_per_rampid=all_ramp_oids_per_rampid)

    give_roads_ramp_id(files=files)
    restoring_lost_connections(
        files=files,
        all_ramp_oids_per_rampid=all_ramp_oids_per_rampid_extended_length_threshold,
    )

    delete_ramps(files=files)
    arcpy.management.CopyFeatures(
        in_features=files["copy_of_input"],
        out_feature_class=output_roads_fc,
    )
    arcpy.management.Append([files["new_lines"]], output_roads_fc)
    arcpy.management.CopyFeatures(
        in_features=files["potential_points"],
        out_feature_class=output_points_fc,
    )
    wfm.delete_created_files()


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
    relevant_roads_dissolved = wfm.build_file_path(
        file_name="relevant_roads_dissolved", file_type="gdb"
    )
    potential_points_multipart = wfm.build_file_path(
        file_name="potential_points_multipart", file_type="gdb"
    )
    potential_points = wfm.build_file_path(
        file_name="potential_points", file_type="gdb"
    )
    endpoints = wfm.build_file_path(file_name="endpoints", file_type="gdb")
    near_table = wfm.build_file_path(file_name="near_table", file_type="gdb")
    copy_of_input_dissolved_medium = wfm.build_file_path(
        file_name="copy_of_input_dissolved_medium", file_type="gdb"
    )
    endpoints_for_connections = wfm.build_file_path(
        file_name="endpoints_for_connections", file_type="gdb"
    )
    intersection_points = wfm.build_file_path(
        file_name="intersection_points", file_type="gdb"
    )
    potential_connection = wfm.build_file_path(
        file_name="potential_connection", file_type="gdb"
    )
    new_lines = wfm.build_file_path(file_name="new_lines", file_type="gdb")
    ramp_group = wfm.build_file_path(file_name="ramp_group", file_type="gdb")
    endpoint_group = wfm.build_file_path(file_name="endpoint_group", file_type="gdb")

    return {
        "copy_of_input": copy_of_input,
        "rampe_buffer": rampe_buffer,
        "relevant_roads_dissolved": relevant_roads_dissolved,
        "potential_points_multipart": potential_points_multipart,
        "potential_points": potential_points,
        "endpoints": endpoints,
        "near_table": near_table,
        "copy_of_input_dissolved_medium": copy_of_input_dissolved_medium,
        "endpoints_for_connections": endpoints_for_connections,
        "intersection_points": intersection_points,
        "potential_connection": potential_connection,
        "new_lines": new_lines,
        "ramp_group": ramp_group,
        "endpoint_group": endpoint_group,
    }


@timing_decorator
def select_relevant_roads(files: dict, buffer_size: int):
    """
    Select relevent roads using buffer
    we add the ramps later to avoid dissolving them
    returns featurelayer
    """
    rampe_layer = "rampe_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=rampe_layer,
        where_clause="typeveg = 'rampe'",
    )
    arcpy.analysis.Buffer(
        in_features=rampe_layer,
        out_feature_class=files["rampe_buffer"],
        buffer_distance_or_field=f"{buffer_size} Meters",
        # dissolve_option="ALL",
    )
    relevant_roads_layer = "relevant_roads_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=relevant_roads_layer,
        where_clause="objtype = 'VegSenterlinje' and typeveg <> 'rampe'",
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
    with arcpy.da.UpdateCursor(
        output_fc, ["OID@", "SHAPE@", concat_field, orig_lines_id]
    ) as ucur:
        for row in ucur:
            oid = row[0]
            geom = row[1]
            concat_val = row[2]

            # Build set of allowed IDs from the CONCATENATE field
            allowed = set()
            if concat_val:
                # split on comma, strip whitespace, ignore empty tokens
                tokens = [
                    t.strip() for t in str(concat_val).split(",") if t.strip() != ""
                ]
                allowed = set(tokens)

            # If no allowed IDs, write empty and continue
            if not allowed:
                row[3] = ""
                ucur.updateRow(row)
                continue

            # Select original lines that intersect this dissolved geometry
            arcpy.SelectLayerByLocation_management(
                orig_layer, "INTERSECT", geom, selection_type="NEW_SELECTION"
            )

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


def dissolve_and_return_connection(
    lines_fc: str, output_fc: str, dissolve_fields: list
):
    """
    dissolves lines_fc on dissolve_fields and returns a map like this map[orig_oid] = dissolved oid
    adds field "obj_id_txt" to lines_fc
    """
    field_name = "obj_id_txt"
    arcpy.management.AddField(
        in_table=lines_fc,
        field_name=field_name,
        field_type="TEXT",
    )
    arcpy.management.CalculateField(
        in_table=lines_fc,
        field=field_name,
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )
    arcpy.management.Dissolve(
        in_features=lines_fc,
        out_feature_class=output_fc,
        dissolve_field=dissolve_fields,
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
        in_features=lines_fc,
        out_layer=orig_layer,
    )
    orig_oid_dissolved_oid = {}
    with arcpy.da.UpdateCursor(
        output_fc, ["OID@", "SHAPE@", concat_field, orig_lines_id]
    ) as ucur:
        for row in ucur:
            oid = row[0]
            geom = row[1]
            concat_val = row[2]

            # Build set of allowed IDs from the CONCATENATE field
            allowed = set()
            if concat_val:
                # split on comma, strip whitespace, ignore empty tokens
                tokens = [
                    t.strip() for t in str(concat_val).split(",") if t.strip() != ""
                ]
                allowed = set(tokens)

            # If no allowed IDs, write empty and continue
            if not allowed:
                row[3] = ""
                ucur.updateRow(row)
                continue

            # Select original lines that intersect this dissolved geometry
            arcpy.SelectLayerByLocation_management(
                orig_layer, "INTERSECT", geom, selection_type="NEW_SELECTION"
            )

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
                        orig_oid_dissolved_oid[orig_id] = oid

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

    return orig_oid_dissolved_oid


def add_ramps_to_relevant_roads(files: dict):
    """
    When we traverse the paths later we want to be able to seperate the different parts of the ramps
    so that if one point is using one part of the ramp and another point is using another part they dont count as the same ramp
    This is important for the subset analysis later
    """
    ramps_layer = "ramps_layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=ramps_layer,
        where_clause="objtype = 'VegSenterlinje' and typeveg = 'rampe'",
    )
    with arcpy.da.SearchCursor(
        ramps_layer,
        [
            "OID@",
            "SHAPE@",
            "objtype",
            "medium",
            "motorvegtype",
            "vegkategori",
            "typeveg",
        ],
    ) as s_cur, arcpy.da.InsertCursor(
        files["relevant_roads_dissolved"],
        ["SHAPE@", "objtype", "medium", "motorvegtype", "vegkategori", "typeveg"],
    ) as i_cur:
        for row in s_cur:
            geom = row[1]
            objtype = row[2]
            medium = row[3]
            motorvegtype = row[4]
            vegkategori = row[5]
            typeveg = row[6]
            i_cur.insertRow([geom, objtype, medium, motorvegtype, vegkategori, typeveg])


@timing_decorator
def make_potential_points(files: dict):
    """
    create points where two roads cross with different mediums,
    Testing without vegkategori p
    """
    layer_T = "layer_T"
    layer_U = "layer_U"
    layer_L = "layer_L"

    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_T,
        where_clause=f"medium = 'T' AND typeveg <> 'rampe' AND vegkategori <> 'P'",
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_U,
        where_clause=f"medium = 'U' AND typeveg <> 'rampe' AND vegkategori <> 'P'",
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files["relevant_roads_dissolved"],
        out_layer=layer_L,
        where_clause=f"medium = 'L' AND typeveg <> 'rampe' AND vegkategori <> 'P'",
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

    remove_endpoints(
        files=files,
        lines_fc=files["relevant_roads_dissolved"],
        points_fc=files["potential_points"],
    )


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


@timing_decorator
def remove_points_without_ramp_connection(files: dict, max_path_length: int):
    """
    Removes potential points that arent on top of 2 roads connected by ramps

    max_path_length: maximum legnth of path in meters, paths longer than this dont count as a connection

    returns a map that groups ramp id and ramp oids
    """
    adjacency = build_adjacency_with_medium(files, files["relevant_roads_dissolved"])
    ramp_oids = set()
    ramps_lyr = "ramps_lyr_436"
    arcpy.management.MakeFeatureLayer(
        files["relevant_roads_dissolved"], ramps_lyr, "typeveg = 'rampe'"
    )
    with arcpy.da.SearchCursor(ramps_lyr, ["OID@"]) as s_cur:
        for row in s_cur:
            ramp_oids.add(row[0])

    line_geom_dict = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"]
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom = row[1]
            line_geom_dict[oid] = geom

    remove_points = set()

    valid_oids = defaultdict(set)
    arcpy.analysis.GenerateNearTable(
        files["potential_points"],
        files["relevant_roads_dissolved"],
        files["near_table"],
        search_radius="500 Meter",
        closest="ALL",
    )
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
    fid_fields.remove("ramp_id")
    cursor_fields = ["ramp_id"] + fid_fields
    all_ramp_oids_per_rampid = defaultdict(set)
    all_ramp_oids_per_rampid_extended_length_threshold = defaultdict(set)
    with arcpy.da.SearchCursor(files["potential_points"], cursor_fields) as s_cur:
        for row in s_cur:
            point_oid = row[0]
            # expect two FID fields
            if len(row) < 3 or row[1] is None or row[2] is None:
                continue
            road_a = int(row[1])
            road_b = int(row[2])
            near_set = valid_oids.get(point_oid, set())
            all_paths = bfs_all_paths_with_prevous_neighbour_rule(
                adjacency=adjacency,
                start=road_a,
                target=road_b,
                max_steps=10,
                valid_oids=near_set,
            )

            paths_with_ramps = [
                path for path in all_paths if any(node in ramp_oids for node in path)
            ]

            #######
            test_without_previous_neighbour_rule = bfs_all_paths(
                adjacency=adjacency,
                start=road_a,
                target=road_b,
                max_steps=10,
                valid_oids=near_set,
            )
            paths_with_ramps_test_no_neighbour = [
                path
                for path in test_without_previous_neighbour_rule
                if any(node in ramp_oids for node in path)
            ]
            paths_with_ramps_extended_length_threshold = [
                path
                for path in paths_with_ramps_test_no_neighbour
                if path_lenght(path, line_geom_dict) <= max_path_length + 900
            ]

            ######

            paths_with_ramps = [
                path
                for path in paths_with_ramps
                if path_lenght(path, line_geom_dict) <= max_path_length
            ]

            has_ramp = bool(paths_with_ramps)

            if not has_ramp:
                remove_points.add(point_oid)
            else:
                for path in paths_with_ramps:
                    for node in path:
                        if node in ramp_oids:
                            all_ramp_oids_per_rampid[point_oid].add(node)
                ####
                for path in paths_with_ramps_extended_length_threshold:
                    for node in path:
                        if node in ramp_oids:
                            all_ramp_oids_per_rampid_extended_length_threshold[
                                point_oid
                            ].add(node)
                ###

    with arcpy.da.UpdateCursor(files["potential_points"], ["ramp_id"]) as u_cur:
        for row in u_cur:
            if row[0] in remove_points:
                u_cur.deleteRow()

    return all_ramp_oids_per_rampid, all_ramp_oids_per_rampid_extended_length_threshold


@timing_decorator
def add_subsets_values(files: dict, all_ramp_oids_per_rampid: dict):
    """
    If a points ramp oids in paths are a subset of another points ramp oids we add it in the is_subset column,
    if two points have the exact same ramp oids we say the one with a hicher score is a subset of the other,
    and if the score is equal the one further away from the ramps is subset of the one thats closer to the ramps,
    """
    road_geoms = defaultdict()
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"]
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom = row[1]
            road_geoms[oid] = geom

    ramp_id_score = defaultdict(int)
    ramp_id_geom = defaultdict()
    with arcpy.da.SearchCursor(
        files["potential_points"], ["ramp_id", "total_score", "SHAPE@"]
    ) as s_cur:
        for row in s_cur:
            ramp_id = row[0]
            score = row[1]
            geom = row[2]
            ramp_id_score[ramp_id] = score
            ramp_id_geom[ramp_id] = geom

    subset_dict = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["potential_points"], ["ramp_id", "total_score", "SHAPE@"]
    ) as s_cur:
        for row in s_cur:
            ramp_id = row[0]
            score = row[1]
            ramp_point_geom = row[2]
            ramp_oids = all_ramp_oids_per_rampid.get(ramp_id, set())
            for other_ramp_id, other_ramp_oids in all_ramp_oids_per_rampid.items():
                if other_ramp_id == ramp_id:
                    continue
                if ramp_oids.issubset(other_ramp_oids):
                    if ramp_oids == other_ramp_oids:
                        other_score = ramp_id_score.get(other_ramp_id, 0)
                        if score < other_score:
                            subset_dict.setdefault(ramp_id, set()).add(other_ramp_id)
                        elif score == other_score:
                            other_ramp_geom = ramp_id_geom[other_ramp_id]
                            total_distance_ramp = 0
                            total_distance_other_ramp = 0
                            for ramp_oid in ramp_oids:
                                total_distance_ramp += ramp_point_geom.distanceTo(
                                    road_geoms[ramp_oid]
                                )
                                total_distance_other_ramp += other_ramp_geom.distanceTo(
                                    road_geoms[ramp_oid]
                                )

                            if total_distance_ramp > total_distance_other_ramp:
                                subset_dict.setdefault(ramp_id, set()).add(
                                    other_ramp_id
                                )

                        else:
                            subset_dict.setdefault(other_ramp_id, set()).add(ramp_id)
                    else:
                        subset_dict.setdefault(ramp_id, set()).add(other_ramp_id)

    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name="is_subset",
        field_type="TEXT",
    )
    with arcpy.da.UpdateCursor(
        files["potential_points"],
        [
            "ramp_id",
            "is_subset",
            "total_score",
            "typeveg_score",
            "vegkategori_score",
            "motorvegtype_score",
        ],
    ) as u_cur:
        for row in u_cur:
            if row[0] in subset_dict:
                row[1] = ",".join(subset_dict[row[0]])
                u_cur.updateRow(row)


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
    Creates adjecency graph of roads that intersect using near table 0 meter, but with a check for medium attribute to avoid false connections where roads arent actually connected but just intersect in the geometry due to overpasses etc.
    If different mediums only keep as adjecent if they intersect at endpoints.
    Inputs need to be dissolved on medium and nothing else
    """
    adjacency = defaultdict(set)
    near_table = files["near_table"]
    arcpy.analysis.GenerateNearTable(
        in_features=lines,
        near_features=lines,
        out_table=near_table,
        search_radius="0 Meters",
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

            # require any intersection point to be an endpoint of both features
            # NÅ tester vi med endpoint av en feature og ser om detskaper trøbbel eller ikke,
            #  hvis det skaper trøbbel må du se på å bygge adjecency på veier som bare er dissolvet på medium,
            # det at andre ting er burdert i dissolven kan føre til at en bru er delt i 2 akkuratt hvor veien under krysser
            # da hadde det jo blitt en path som egentlig ikke eksisterer
            if any(pt in ep1 or pt in ep2 for pt in inter_pts):
                adjacency[in_fid].add(near_fid)

    arcpy.management.Delete(near_table)
    return adjacency


def bfs_all_paths(
    adjacency: Dict[Any, Iterable[Any]],
    start: Any,
    target: Any,
    max_steps: int = 20,
    max_paths: Optional[int] = None,
    valid_oids: Optional[set] = None,
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
    valid_oids: Optional[set] = None,
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


def bfs_all_ramps(
    adjacency: Dict[Any, Iterable[Any]],
    start: int,
    valid_oids: set,
    max_steps: int = 20,
) -> Set:
    """
    Find all oids in valid oids that are connected to start oid using a BFS expansion up to max_steps edges.

    Parameters
    - adjacency: mapping node -> iterable of neighbor nodes
    - start: starting node OID
    - max_steps: maximum number of edges to traverse (default 20)
    - valid_oids: set of all valid oids

    Returns
    - list of oids, where each oid is connected to start oid through valid oids
    """

    results = set()
    queue = deque()
    queue.append([start])
    results.add(start)

    while queue:
        path = queue.popleft()
        if len(path) - 1 > max_steps:
            # path already exceeds allowed edges; skip
            continue

        last = path[-1]
        neighbors = adjacency.get(last, ())

        for nbr in neighbors:
            if nbr not in valid_oids:
                continue
            if nbr in path:
                # avoid cycles; require simple paths
                continue

            results.add(nbr)
            new_path = path + [nbr]

            # only enqueue if we can still add edges without exceeding max_steps
            if len(new_path) - 1 < max_steps:
                queue.append(new_path)

    return results


def path_lenght(path: List[int], geom_dict: dict) -> int:
    """
    The lines making up the path have parts that are not part of the path,
    so to find the actual length of the path we measure the distance between the intersections
    like this: path = [1,2,3,4,5]
    we start at the intersection of 1 and 5
    then we go to the intersection between 1 and 2
    then 2 and 3
    etc and we end at the intersection between 5 and 1

    """

    start_inter = None
    total_length = 0
    prev_inter = None
    for n in range(len(path)):
        current_geom = geom_dict[path[n]]
        previous_geom = geom_dict[path[n - 1]]
        inter = current_geom.intersect(previous_geom, 1)

        inter_pts = []
        for p in inter:
            inter_pts.append(p)

        if len(inter_pts) == 0:
            continue

        inter = inter_pts[0]
        inter = arcpy.PointGeometry(inter, previous_geom.spatialReference)

        if prev_inter is None:
            start_inter = inter
            prev_inter = inter
            continue

        # measure distance from prev_inter to inter along current_geom

        m1 = previous_geom.measureOnLine(prev_inter)
        m2 = previous_geom.measureOnLine(inter)
        total_length += abs(m2 - m1)

        prev_inter = inter

    # Close the loop:
    # from last intersection (path[-1], path[-2]) to start intersection (path[-1], path[0])
    last_geom = geom_dict[path[-1]]
    m1 = last_geom.measureOnLine(prev_inter)
    m2 = last_geom.measureOnLine(start_inter)
    total_length += abs(m2 - m1)

    return total_length


def give_points_score(files: dict):
    """
    Gives score to potential points
    the score is based on the motorvegtype, vegkategori and typeveg of the two roads the point is on,
    the score is the sum of the two roads,
    a lower score means more important roads
    """
    roads_lyr = "roads_lyr"
    arcpy.management.MakeFeatureLayer(
        files["relevant_roads_dissolved"], roads_lyr, "typeveg <> 'rampe'"
    )
    road_m_v_t = {}
    with arcpy.da.SearchCursor(
        roads_lyr, ["OID@", "motorvegtype", "vegkategori", "typeveg"]
    ) as s_cur:
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
        field_type="SHORT",
    )
    fields = fields + [motorvegtype_score]

    vegkategori_score = "vegkategori_score"
    arcpy.management.AddField(
        in_table=files["potential_points"],
        field_name=vegkategori_score,
        field_type="SHORT",
    )
    fields = fields + [vegkategori_score]

    typeveg_score = "typeveg_score"
    arcpy.management.AddField(
        in_table=files["potential_points"], field_name=typeveg_score, field_type="SHORT"
    )
    fields = fields + [typeveg_score]

    total_score = "total_score"
    arcpy.management.AddField(
        in_table=files["potential_points"], field_name=total_score, field_type="SHORT"
    )
    fields = fields + [total_score]

    with arcpy.da.UpdateCursor(files["potential_points"], fields) as u_cur:
        for row in u_cur:
            point_oid = row[0]
            road_a = row[1]
            road_b = row[2]

            road_a_m, road_a_v, road_a_t = road_m_v_t[road_a]
            road_b_m, road_b_v, road_b_t = road_m_v_t[road_b]

            motorvegtype_score_map = {
                "Motorveg": 1,
                "Motortrafikkveg": 2,
                "Ikke motorveg": 3,
                "Udefinert": 4,
            }
            m_a = motorvegtype_score_map.get(road_a_m)
            m_b = motorvegtype_score_map.get(road_b_m)
            m_sum = m_a + m_b

            vegkategori_score_map = {"E": 1, "R": 2, "F": 3, "K": 4, "P": 5, "S": 6}
            v_a = vegkategori_score_map.get(road_a_v)
            v_b = vegkategori_score_map.get(road_b_v)
            v_sum = v_a + v_b

            typeveg_score_map = {"kanalisertVeg": 1, "enkelBilveg": 2}
            t_a = typeveg_score_map.get(road_a_t)
            t_b = typeveg_score_map.get(road_b_t)
            t_sum = t_a + t_b

            row[3] = m_sum
            row[4] = v_sum
            row[5] = t_sum
            row[6] = m_sum + v_sum + t_sum
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


def give_roads_ramp_id(files: dict):
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
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", orig_field]
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            orig_ids_str = row[1]
            if orig_ids_str is None:
                continue
            orig_ids = [
                oid.strip() for oid in str(orig_ids_str).split(",") if oid.strip() != ""
            ]
            for orig_id in orig_ids:
                orig_to_dissolved[orig_id].add(oid)

    dissolved_to_ramp = defaultdict(set)
    base = os.path.splitext(os.path.basename(files["relevant_roads_dissolved"]))[0]
    road_id_field1 = f"FID_{base}"
    road_id_field2 = f"FID_{base}_1"
    with arcpy.da.SearchCursor(
        files["potential_points"], ["ramp_id", road_id_field1, road_id_field2]
    ) as s_cur:
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


def delete_ramps(files: dict):
    layer = "layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_input"],
        out_layer=layer,
        where_clause="typeveg = 'rampe'",
    )
    arcpy.management.DeleteFeatures(in_features=layer)


###################################################################################
#                             Restoring lost connections                          #
###################################################################################
@timing_decorator
def restoring_lost_connections(files: dict, all_ramp_oids_per_rampid: dict):
    """
    What:
        This function orchestrates the process of restoring lost connections in a road network after ramp removal.
        It identifies endpoints that lost connectivity, groups them, and creates potential connection points to restore the network.

    How:
        The groups of endpoints are split into two categories: those that belong to a ramp points and those that do not.

        For groups that belong to a ramp point,
        the first potential connection point is created based on the ramp point's location.
        Then the endpoints that are connected to the first potential connection point are removed from the group and turned into a potential connection point if they arent connected to any other road.

        For groups that do not belong to a ramp point,
        we subgroup the endpoints based on their adjacency to each other,
        then rank them based on their vegkategori and motorvegtype and choose the less important endpoints,
        then create a potential connection point based on the shortest connection to the roads in the other subgroups.

        Then we create lines between endpoints and potential connection points,
        update and check the adjacency graph after each new line and turn endpoints that are connected to the potential connection points into potential connection points.
    """

    endpoint_data_map = create_endpoints(files=files)
    all_ramp_oids_per_rampid = remove_subsets_as_potential_connections(
        files=files, all_ramp_oids_per_rampid=all_ramp_oids_per_rampid
    )
    remove_small_roads_from_endpoints(files=files, min_length=600)
    endpoints_per_rampid = group_endpoints(
        files=files, all_ramp_oids_per_rampid=all_ramp_oids_per_rampid
    )
    endpoint_groups, ramp_groups = group_endpoints_not_belonging_to_a_ramp_id(
        files=files, endpoints_per_rampid=endpoints_per_rampid
    )
    endpoints_per_rampid = make_potential_connection_points(
        files=files, endpoints_per_rampid=endpoints_per_rampid
    )
    endpoints_per_rampid = make_potential_connection_points_for_groups_without_rampid(
        files=files,
        endpoint_groups=endpoint_groups,
        ramp_groups=ramp_groups,
        endpoints_per_rampid=endpoints_per_rampid,
        endpoint_data_map=endpoint_data_map,
    )
    extending_roads(
        files=files,
        endpoints_per_rampid=endpoints_per_rampid,
        endpoint_data_map=endpoint_data_map,
    )


@timing_decorator
def create_endpoints(files: dict):
    """
    Creates endpoints for all roads that intersect with ramps and removes endpoints that dont intersect ramps.
    Creates a unique identifier for each endpoint and returns a mapping of endpoint UIDs to their attributes.
    """
    roads_lyr = "roads_lyr"
    ramps_lyr = "ramps_lyr"

    arcpy.management.MakeFeatureLayer(
        files["copy_of_input"],
        roads_lyr,
        where_clause="typeveg <> 'rampe' and objtype = 'VegSenterlinje'",
    )
    arcpy.management.MakeFeatureLayer(
        files["copy_of_input"],
        ramps_lyr,
        where_clause="typeveg = 'rampe' and objtype = 'VegSenterlinje'",
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=roads_lyr,
        overlap_type="INTERSECT",
        select_features=ramps_lyr,
        selection_type="NEW_SELECTION",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=roads_lyr,
        out_feature_class=files["endpoints_for_connections"],
        point_location="BOTH_ENDS",
    )

    endpoints_lyr = "endpoints_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["endpoints_for_connections"],
        out_layer=endpoints_lyr,
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=endpoints_lyr,
        overlap_type="INTERSECT",
        select_features=ramps_lyr,
        invert_spatial_relationship="INVERT",
    )

    arcpy.management.DeleteFeatures(in_features=endpoints_lyr)

    # Add a unique identifier field to the endpoints feature class and create a mapping of endpoint OIDs to their attributes
    arcpy.management.AddField(
        in_table=files["endpoints_for_connections"],
        field_name="uid",
        field_type="SHORT",
    )
    arcpy.management.CalculateField(
        in_table=files["endpoints_for_connections"],
        field="uid",
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )
    fields = [
        f.name
        for f in arcpy.ListFields(files["endpoints_for_connections"])
        if f.type not in ("OID", "Geometry")
    ]
    fields.remove("uid")
    fields = ["uid"] + fields
    endpoint_data_map = {}
    with arcpy.da.SearchCursor(files["endpoints_for_connections"], fields) as s_cur:
        for row in s_cur:
            endpoint_oid = row[0]
            data = {field: value for field, value in zip(fields[1:], row[1:])}
            endpoint_data_map[endpoint_oid] = data

    return endpoint_data_map


def remove_subsets_as_potential_connections(
    files: dict, all_ramp_oids_per_rampid: dict
):
    """
    Removes all ramp points that are subsets to avoid one endpoint connectting to multiple places unnecessarily
    """
    with arcpy.da.SearchCursor(
        files["potential_points"], ["ramp_id"], where_clause="is_subset IS NOT NULL"
    ) as s_cur:
        for row in s_cur:
            all_ramp_oids_per_rampid.pop(row[0])

    return all_ramp_oids_per_rampid


@timing_decorator
def remove_small_roads_from_endpoints(files: dict, min_length: int = 500):
    """
    Removes endpoints that are on small road segments that are less than min_length meters long,
    as they are likely not significant enough for connections.
    Also removes the corresponding road segments from the relevant_roads_dissolved feature class.
    """
    adjacency = build_adjacency_with_medium(
        files=files, lines=files["relevant_roads_dissolved"]
    )

    valid_oids = set()
    line_length_dict = defaultdict(int)
    line_geom_dict = defaultdict()
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"],
        ["OID@", "SHAPE@LENGTH", "SHAPE@"],
        where_clause="typeveg <> 'rampe'",
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            valid_oids.add(oid)
            length = row[1]
            line_length_dict[oid] = length
            geom = row[2]
            line_geom_dict[oid] = geom

    delete_oids = set()
    with arcpy.da.UpdateCursor(
        files["endpoints_for_connections"], ["uid", "SHAPE@"]
    ) as u_cur:
        for row in u_cur:
            point_oid = row[0]
            point_geom = row[1]

            road_oid = None
            for road_id, road_geom in line_geom_dict.items():
                if not point_geom.disjoint(road_geom):
                    road_oid = road_id
                    break

            oids = bfs_all_ramps(
                adjacency=adjacency, start=road_oid, valid_oids=valid_oids, max_steps=10
            )
            length = sum(line_length_dict[oid] for oid in oids)
            if length < min_length:
                u_cur.deleteRow()
                delete_oids.add(road_oid)

    with arcpy.da.UpdateCursor(files["relevant_roads_dissolved"], ["OID@"]) as u_cur:
        for row in u_cur:
            oid = row[0]
            if oid in delete_oids:
                u_cur.deleteRow()


@timing_decorator
def group_endpoints(files: dict, all_ramp_oids_per_rampid: dict):
    """
    Groups endpoints based on their intersection with ramp geometries and associates them with ramp points.

     Returns:
        dict: A dictionary mapping endpoints to their corresponding ramp points, where each key is a ramp point ID and the value is a list of endpoint dictionaries containing 'endpoint_oid' and 'endpoint_geom'.
    """

    ramp_oid_geom = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"], "typeveg = 'rampe'"
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom = row[1]
            ramp_oid_geom.setdefault(oid, geom)

    ramp_ids_per_oid = defaultdict(set)
    for ramp_id, ramp_oids in all_ramp_oids_per_rampid.items():
        for ramp_oid in ramp_oids:
            ramp_ids_per_oid[ramp_oid].add(ramp_id)

    endpoints_per_rampid = defaultdict(list)

    with arcpy.da.SearchCursor(
        files["endpoints_for_connections"], ["uid", "SHAPE@"]
    ) as s_cur:
        for endpoint_oid, endpoint_geom in s_cur:
            intersecting_ramp_oids = []

            for ramp_oid, ramp_geom in ramp_oid_geom.items():
                if not endpoint_geom.disjoint(ramp_geom):
                    intersecting_ramp_oids.append(ramp_oid)

            matching_ramp_ids = set()

            for ramp_oid in intersecting_ramp_oids:
                matching_ramp_ids.update(ramp_ids_per_oid.get(ramp_oid, set()))

            for ramp_id in matching_ramp_ids:
                endpoints_per_rampid[ramp_id].append(
                    {
                        "endpoint_oid": endpoint_oid,
                        "endpoint_geom": endpoint_geom,
                    }
                )

    return endpoints_per_rampid


def group_endpoints_not_belonging_to_a_ramp_id(files: dict, endpoints_per_rampid: dict):
    """
    Groups endpoints that do not belong to any ramp point based on their adjacency and proximity to each other.
    Removes groups where all endpoints are already connected through non-ramp road adjacency.

    Args:
        endpoints_per_rampid (dict): A dictionary mapping ramp point IDs to lists of endpoint dictionaries containing 'endpoint_oid' and 'endpoint_geom'.

    Returns:
        tuple: A tuple containing two dictionaries:
            - endpoint_groups: The modified endpoints_per_rampid dictionary with groups of endpoints that do not belong to any ramp point.
            - ramp_groups: A dictionary mapping group keys to sets of ramp OIDs that are connected to the endpoints in the corresponding endpoint group.
    """
    ramp_oid_geom = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"], "typeveg = 'rampe'"
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom = row[1]
            ramp_oid_geom.setdefault(oid, geom)

    adjacency = build_adjacency_with_medium(
        files=files, lines=files["relevant_roads_dissolved"]
    )
    ramp_groups = {}
    endpoint_groups = {}
    key = "ramp_group_key_"
    counter = 0
    valid_oids = ramp_oid_geom.keys()

    endpoint_oids_in_groups = set()
    for endpoints in endpoints_per_rampid.values():
        for endpoint in endpoints:
            endpoint_oids_in_groups.add(endpoint["endpoint_oid"])

    with arcpy.da.SearchCursor(
        files["endpoints_for_connections"], ["uid", "SHAPE@"]
    ) as s_cur:
        for endpoint_oid, endpoint_geom in s_cur:

            if endpoint_oid not in endpoint_oids_in_groups:
                intersecting_ramp_oids = []

                for ramp_oid, ramp_geom in ramp_oid_geom.items():
                    if not endpoint_geom.disjoint(ramp_geom):
                        intersecting_ramp_oids.append(ramp_oid)

                ramp_oid = intersecting_ramp_oids[0]

                existing_key = None

                for group_key, ramp_oids in ramp_groups.items():
                    if ramp_oid in ramp_oids:
                        existing_key = group_key
                        break

                if existing_key is None:
                    counter += 1

                    all_ramp_oids_to_add_group = bfs_all_ramps(
                        adjacency=adjacency,
                        start=ramp_oid,
                        max_steps=10,
                        valid_oids=valid_oids,
                    )

                    key_string = f"{key}{counter}"

                    ramp_groups[key_string] = all_ramp_oids_to_add_group
                    endpoint_groups.setdefault(key_string, []).append(
                        {"oid": endpoint_oid, "geom": endpoint_geom}
                    )

                else:
                    endpoint_groups.setdefault(existing_key, []).append(
                        {"oid": endpoint_oid, "geom": endpoint_geom}
                    )

    # Remove groups where all endpoints are already connected through non-ramp road adjacency
    road_oid_geom = {}
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"], "typeveg <> 'rampe'"
    ) as s_cur:
        for oid, geom in s_cur:
            road_oid_geom[oid] = geom
    valid_road_oids = set(road_oid_geom.keys())

    adjacency_with_points = _add_potential_points_to_adjacency(
        files=files,
        adjacency=adjacency,
        adjacency_file=files["relevant_roads_dissolved"],
    )

    max_path_length = 500

    keys_to_remove = []
    for group_key, endpoint_rows in endpoint_groups.items():
        if len(endpoint_rows) < 2:
            continue

        endpoint_road_oids = []
        for endpoint in endpoint_rows:
            road_oid = _find_endpoint_road_oid(endpoint["geom"], road_oid_geom)
            if road_oid is not None:
                endpoint_road_oids.append(road_oid)

        if len(endpoint_road_oids) < 2:
            continue

        all_connected = True
        for i in range(len(endpoint_road_oids)):
            if not all_connected:
                break
            for j in range(i + 1, len(endpoint_road_oids)):
                paths = bfs_all_paths(
                    adjacency=adjacency_with_points,
                    start=endpoint_road_oids[i],
                    target=endpoint_road_oids[j],
                    max_steps=4,
                    valid_oids=valid_road_oids,
                )
                has_short_path = any(
                    _path_length_linear(path, road_oid_geom) <= max_path_length
                    for path in paths
                )
                if not has_short_path:
                    all_connected = False
                    break

        if all_connected:
            keys_to_remove.append(group_key)

    for key_to_remove in keys_to_remove:
        del endpoint_groups[key_to_remove]
        del ramp_groups[key_to_remove]

    return endpoint_groups, ramp_groups


##########
# make potential connection points for groups without rampid
#########


def _load_ramp_and_road_geometries(files: dict):
    ramp_oid_geom = {}
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"], "typeveg = 'rampe'"
    ) as s_cur:
        for oid, geom in s_cur:
            ramp_oid_geom[oid] = geom

    road_oid_geom = {}
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@"], "typeveg <> 'rampe'"
    ) as s_cur:
        for oid, geom in s_cur:
            road_oid_geom[oid] = geom

    return ramp_oid_geom, road_oid_geom


def _collect_adjacent_roads_for_ramp_group(
    adjacency: dict,
    ramp_oids: set,
    ramp_oid_geom: dict,
    valid_road_oids: set,
    max_steps: int = 4,
) -> set:
    adjacent_roads = set()

    for ramp_oid in ramp_oids:
        neighbors = adjacency.get(ramp_oid, ())
        for neighbor in neighbors:
            if neighbor in ramp_oid_geom:
                continue
            adjacent_roads.add(neighbor)

            expanded = bfs_all_ramps(
                adjacency=adjacency,
                start=neighbor,
                valid_oids=valid_road_oids,
                max_steps=max_steps,
            )
            adjacent_roads.update(expanded)

    return adjacent_roads


def _exclude_roads_touching_endpoint(
    endpoint_geom,
    candidate_roads: set,
    road_oid_geom: dict,
    adjacency: dict,
    valid_road_oids: set,
    max_steps: int = 4,
):
    filtered_roads = set(candidate_roads)
    endpoint_adjacent_roads = set()

    for road_oid in list(filtered_roads):
        road_geom = road_oid_geom[road_oid]
        if endpoint_geom.disjoint(road_geom):
            continue

        filtered_roads.discard(road_oid)
        endpoint_adjacent_roads.add(road_oid)

        expanded = bfs_all_ramps(
            adjacency=adjacency,
            start=road_oid,
            valid_oids=valid_road_oids,
            max_steps=max_steps,
        )
        for step in expanded:
            filtered_roads.discard(step)
            endpoint_adjacent_roads.add(step)

    return filtered_roads, endpoint_adjacent_roads


def _find_best_endpoint_to_road_connection(
    endpoint_rows: list,
    adjacent_roads: set,
    road_oid_geom: dict,
    adjacency: dict,
    valid_road_oids: set,
    max_steps: int = 4,
):
    best_distance = float("inf")
    best_road_oid = None
    best_connection_point = None
    endpoint_adjacent_roads = defaultdict(set)

    for endpoint in endpoint_rows:
        endpoint_oid = endpoint["oid"]
        endpoint_geom = endpoint["geom"]

        candidate_roads, excluded_for_endpoint = _exclude_roads_touching_endpoint(
            endpoint_geom=endpoint_geom,
            candidate_roads=adjacent_roads,
            road_oid_geom=road_oid_geom,
            adjacency=adjacency,
            valid_road_oids=valid_road_oids,
            max_steps=max_steps,
        )
        endpoint_adjacent_roads[endpoint_oid].update(excluded_for_endpoint)

        candidate_roads = sorted(
            candidate_roads,
            key=lambda road_oid: road_oid_geom[road_oid].distanceTo(endpoint_geom),
        )
        for road_oid in candidate_roads:
            road_geom = road_oid_geom[road_oid]
            valid_connection_point = _find_valid_connection_point(
                closest_road_geom=road_geom,
                closest_endpoint_geom=endpoint_geom,
                road_oid_geom=road_oid_geom,
            )
            if valid_connection_point is None:
                continue
            distance = valid_connection_point.distanceTo(endpoint_geom)
            if distance < best_distance:
                best_distance = distance
                best_road_oid = road_oid
                best_connection_point = valid_connection_point

    return best_road_oid, endpoint_adjacent_roads, best_distance, best_connection_point


def _append_remaining_group_endpoints(
    endpoints_per_rampid: dict,
    group_key: str,
    endpoint_rows: list,
    closest_road_oid,
    endpoint_adjacent_roads: dict,
):
    for endpoint in endpoint_rows:
        endpoint_oid = endpoint["oid"]
        if closest_road_oid in endpoint_adjacent_roads.get(endpoint_oid, set()):
            continue

        endpoints_per_rampid[group_key].append(
            {
                "endpoint_oid": endpoint_oid,
                "endpoint_geom": endpoint["geom"],
            }
        )


def _uf_find(parent: dict, node):
    root = node
    while parent[root] != root:
        root = parent[root]

    # Path compression
    while node != root:
        parent_node = parent[node]
        parent[node] = root
        node = parent_node

    return root


def _uf_union(parent: dict, rank: dict, a, b):
    root_a = _uf_find(parent, a)
    root_b = _uf_find(parent, b)
    if root_a == root_b:
        return

    if rank[root_a] < rank[root_b]:
        parent[root_a] = root_b
    elif rank[root_a] > rank[root_b]:
        parent[root_b] = root_a
    else:
        parent[root_b] = root_a
        rank[root_a] += 1


def _find_endpoint_road_oid(endpoint_geom, road_oid_geom: dict):
    for road_oid, road_geom in road_oid_geom.items():
        if not endpoint_geom.disjoint(road_geom):
            return road_oid
    return None


def _group_endpoints_with_union_find_by_bfs(
    endpoint_rows: list,
    road_oid_geom: dict,
    adjacency: dict,
    valid_oids: set,
    max_steps: int = 12,
) -> list:
    """
    Group endpoint rows by connectivity of their intersecting roads.
    Two endpoints belong to the same component if BFS finds a path between
    their road oids in adjacency.
    """
    endpoint_oid_to_row = {}
    endpoint_oid_to_road_oid = {}

    for endpoint in endpoint_rows:
        endpoint_oid = endpoint["oid"]
        endpoint_geom = endpoint["geom"]
        road_oid = _find_endpoint_road_oid(endpoint_geom, road_oid_geom)
        if road_oid is None:
            continue

        endpoint_oid_to_row[endpoint_oid] = endpoint
        endpoint_oid_to_road_oid[endpoint_oid] = road_oid

    endpoint_oids = sorted(endpoint_oid_to_road_oid.keys())
    if not endpoint_oids:
        return []

    parent = {oid: oid for oid in endpoint_oids}
    rank = {oid: 0 for oid in endpoint_oids}

    for i in range(len(endpoint_oids)):
        oid_a = endpoint_oids[i]
        road_a = endpoint_oid_to_road_oid[oid_a]

        for j in range(i + 1, len(endpoint_oids)):
            oid_b = endpoint_oids[j]
            road_b = endpoint_oid_to_road_oid[oid_b]

            if road_a == road_b:
                _uf_union(parent, rank, oid_a, oid_b)
                continue

            paths = bfs_all_paths(
                adjacency=adjacency,
                start=road_a,
                target=road_b,
                max_steps=max_steps,
                max_paths=1,
                valid_oids=valid_oids,
            )
            if paths:
                _uf_union(parent, rank, oid_a, oid_b)

    components = defaultdict(list)
    for endpoint_oid in endpoint_oids:
        root = _uf_find(parent, endpoint_oid)
        components[root].append(endpoint_oid)

    grouped_rows = []
    for root in sorted(components.keys()):
        rows = [endpoint_oid_to_row[oid] for oid in sorted(components[root])]
        grouped_rows.append(rows)

    return grouped_rows


def _find_valid_connection_point(
    closest_road_geom,
    closest_endpoint_geom,
    road_oid_geom: dict,
):
    closest_point_geom = closest_road_geom.queryPointAndDistance(
        closest_endpoint_geom, True
    )[0]
    invalid_point = False
    for road_oid, road_geom in road_oid_geom.items():
        if not closest_point_geom.disjoint(road_geom) and not road_geom.equals(
            closest_road_geom
        ):
            invalid_point = True
            break

    if invalid_point:
        valid_points = []
        for i in range(1, 100, 10):
            invalid = False
            fraction = i / 100
            new_point = closest_road_geom.positionAlongLine(fraction, True)
            if new_point is None:
                continue
            for road_oid, road_geom in road_oid_geom.items():
                if not new_point.disjoint(road_geom) and not road_geom.equals(
                    closest_road_geom
                ):
                    invalid = True
                    break
            if not invalid:
                valid_points.append(new_point)

        if valid_points:
            closest_point_geom = min(
                valid_points, key=lambda p: p.distanceTo(closest_endpoint_geom)
            )
        else:
            return None

    return closest_point_geom


@timing_decorator
def make_potential_connection_points_for_groups_without_rampid(
    files: dict,
    endpoint_groups: dict,
    ramp_groups: dict,
    endpoints_per_rampid: dict,
    endpoint_data_map: dict,
):
    """
    What:
        This function creates potential connection points for groups of endpoints that do not belong to any ramp point.

    How:
        The function first builds an adjacency graph of the road network and loads the geometries of ramps and roads.
        It then iterates through each group of endpoints, removing duplicates based on geometry.
        For each group, it collects adjacent roads and subgroups the endpoints based on their connectivity using a union-find algorithm.
        Each subgroup is scored based on the 'motorvegtype' and 'vegkategori' attributes of its endpoints, and the subgroup with the least important endpoints is selected.
        The function then finds the best connection point for the selected subgroup to connect to the adjacent roads, and inserts this point into the potential connection feature class.
        Finally, it appends any remaining endpoints in the group that are not connected to the road with the connection point to the endpoints_per_rampid dictionary.

    Why:
        The reason we choose the subgroup with the least important endpoints is to make the less importan roads extend to the more important roads

    Returns:
        dict: The modified endpoints_per_rampid dictionary with the newly created potential connection points for groups without ramp IDs.
    """
    adjacency = build_adjacency_with_medium(
        files=files, lines=files["relevant_roads_dissolved"]
    )
    adjacency = _add_potential_points_to_adjacency(
        files=files,
        adjacency=adjacency,
        adjacency_file=files["relevant_roads_dissolved"],
    )
    ramp_oid_geom, road_oid_geom = _load_ramp_and_road_geometries(files)
    valid_road_oids = set(road_oid_geom.keys())

    for group_key, endpoint_rows in endpoint_groups.items():
        seen_geoms = set()
        unique_rows = []

        for endpoint in endpoint_rows:
            endpoint_geom = endpoint["geom"].WKT  # Use WKT for hashable representation

            if endpoint_geom in seen_geoms:
                print("Duplicate endpoint geometry found, skipping")
                continue

            seen_geoms.add(endpoint_geom)
            unique_rows.append(endpoint)

        endpoint_groups[group_key] = unique_rows

    with arcpy.da.InsertCursor(
        files["potential_connection"], ["SHAPE@", "group_id"]
    ) as i_cur:
        for group_key, ramp_oids in ramp_groups.items():
            endpoint_rows = endpoint_groups.get(group_key, [])
            if not endpoint_rows:
                continue

            adjacent_roads = _collect_adjacent_roads_for_ramp_group(
                adjacency=adjacency,
                ramp_oids=ramp_oids,
                ramp_oid_geom=ramp_oid_geom,
                valid_road_oids=valid_road_oids,
                max_steps=4,
            )

            endpoint_subgroups = _group_endpoints_with_union_find_by_bfs(
                endpoint_rows=endpoint_rows,
                road_oid_geom=road_oid_geom,
                adjacency=adjacency,
                valid_oids=valid_road_oids,
                max_steps=4,
            )
            if not endpoint_subgroups:
                continue

            best_subgroups = []
            best_score = float("-inf")
            motorvegtype_score_map = {
                "Motorveg": 1,
                "Motortrafikkveg": 2,
                "Ikke motorveg": 3,
                "Udefinert": 4,
            }
            vegkategori_score_map = {"E": 1, "R": 2, "F": 3, "K": 4, "P": 5, "S": 6}
            for subgroup in endpoint_subgroups:
                score = 0
                endpoint_count = len(subgroup)
                for endpoint in subgroup:
                    endpoint_oid = endpoint["oid"]
                    data = endpoint_data_map.get(endpoint_oid, {})
                    vegkategori = data.get("vegkategori")
                    motorvegtype = data.get("motorvegtype")

                    score += motorvegtype_score_map.get(motorvegtype, 0)
                    score += vegkategori_score_map.get(vegkategori, 0)

                score = score / endpoint_count  # Average score for the subgroup

                if score > best_score:
                    best_score = score
                    best_subgroups = [subgroup]

                elif score == best_score:
                    best_subgroups.append(subgroup)

            best_distance = float("inf")
            best_road_oid_final = None
            endpoint_adjacent_roads_final = defaultdict(set)
            for subgroup in best_subgroups:
                (
                    best_road_oid,
                    endpoint_adjacent_roads,
                    distance,
                    best_connection_point,
                ) = _find_best_endpoint_to_road_connection(
                    endpoint_rows=subgroup,
                    adjacent_roads=adjacent_roads,
                    road_oid_geom=road_oid_geom,
                    adjacency=adjacency,
                    valid_road_oids=valid_road_oids,
                    max_steps=4,
                )

                if distance < best_distance:
                    best_distance = distance
                    best_road_oid_final = best_road_oid
                    endpoint_adjacent_roads_final = endpoint_adjacent_roads

            if best_connection_point is not None:
                i_cur.insertRow([best_connection_point, group_key])

            _append_remaining_group_endpoints(
                endpoints_per_rampid=endpoints_per_rampid,
                group_key=group_key,
                endpoint_rows=endpoint_rows,
                closest_road_oid=best_road_oid_final,
                endpoint_adjacent_roads=endpoint_adjacent_roads_final,
            )

    return endpoints_per_rampid


##################
# make potential connection points
##################


def _create_potential_connection_featureclass(files: dict):
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files["potential_connection"]),
        out_name=os.path.basename(files["potential_connection"]),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(
            files["relevant_roads_dissolved"]
        ).spatialReference,
    )
    arcpy.management.AddField(
        in_table=files["potential_connection"],
        field_name="group_id",
        field_type="TEXT",
    )


def _load_non_ramp_roads(files: dict):
    valid_adjacency_oid = set()
    road_oid_geom = {}

    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "SHAPE@", "typeveg"]
    ) as s_cur:
        for oid, geom, typeveg in s_cur:
            if typeveg != "rampe":
                road_oid_geom[oid] = geom
                valid_adjacency_oid.add(oid)

    return road_oid_geom, valid_adjacency_oid


def _get_point_road_fid_fields(points_fc: str):
    all_fields = arcpy.ListFields(points_fc)
    fid_fields = [f.name for f in all_fields if "FID" in f.name]

    if len(fid_fields) < 2:
        raise ValueError(
            f"Expected at least 2 FID fields in {points_fc}, found: {fid_fields}"
        )

    return fid_fields[0], fid_fields[1]


def _load_rampid_road_oids(files: dict):
    fid_a, fid_b = _get_point_road_fid_fields(files["potential_points"])
    rampid_road_oids = {}

    with arcpy.da.SearchCursor(
        files["potential_points"],
        ["ramp_id", fid_a, fid_b],
        where_clause="is_subset IS NULL",
    ) as s_cur:
        for ramp_id, road_oid_1, road_oid_2 in s_cur:
            rampid_road_oids[ramp_id] = [road_oid_1, road_oid_2]

    return rampid_road_oids


def _find_intersecting_road_oid(endpoint_geom, road_oid_geom: dict):
    for road_oid, road_geom in road_oid_geom.items():
        if not endpoint_geom.disjoint(road_geom):
            return road_oid
    return None


def _path_length_linear(
    path: List[int],
    geom_dict: dict,
    start_geom=None,
    end_geom=None,
) -> float:
    """
    Measures the traversed distance along a linear (non-cyclic) path.

    For path = [A, B, C, D]:
      - Finds intersection points between consecutive pairs: A∩B, B∩C, C∩D
      - If start_geom is given, measures from start_geom to A∩B along A
      - Measures along B from A∩B to B∩C, along C from B∩C to C∩D
      - If end_geom is given, measures from C∩D to end_geom along D
    Returns float('inf') if any consecutive pair has no geometric intersection.
    """
    if len(path) < 2:
        return 0.0

    intersection_points = []
    for i in range(len(path) - 1):
        geom_a = geom_dict[path[i]]
        geom_b = geom_dict[path[i + 1]]
        inter = geom_a.intersect(geom_b, 1)
        inter_pts = [p for p in inter if p is not None]
        if not inter_pts:
            return float("inf")
        intersection_points.append(
            arcpy.PointGeometry(inter_pts[0], geom_a.spatialReference)
        )

    total_length = 0.0
    first_geom = geom_dict[path[0]]
    first_inter = intersection_points[0]

    if start_geom is not None:
        m1 = first_geom.measureOnLine(start_geom)
        m2 = first_geom.measureOnLine(first_inter)
        total_length += abs(m2 - m1)

    for i in range(1, len(intersection_points)):
        seg_geom = geom_dict[path[i]]
        m1 = seg_geom.measureOnLine(intersection_points[i - 1])
        m2 = seg_geom.measureOnLine(intersection_points[i])
        total_length += abs(m2 - m1)

    last_geom = geom_dict[path[-1]]
    last_inter = intersection_points[-1]

    if end_geom is not None:
        m1 = last_geom.measureOnLine(last_inter)
        m2 = last_geom.measureOnLine(end_geom)
        total_length += abs(m2 - m1)

    return total_length


def _build_endpoint_to_potential_connection_map(
    endpoints_per_rampid: dict,
    rampid_road_oids: dict,
    road_oid_geom: dict,
    valid_adjacency_oid: set,
    adjacency: dict,
    rampid_geoms: dict,
):
    """
    Creates a mapping of endpoints to potential connections based on their proximity and connectivity to ramp points.
    to be considered connected the path needs a length of less than 1000 Meters
    """
    endpoint_to_potential_connection = {}

    for rampid, endpoints in endpoints_per_rampid.items():
        if rampid not in rampid_road_oids:
            continue

        rampid_geom = rampid_geoms[rampid]

        target_a, target_b = rampid_road_oids[rampid]

        for endpoint in endpoints:
            endpoint_oid = endpoint["endpoint_oid"]
            endpoint_geom = endpoint["endpoint_geom"]

            endpoint_road_oid = _find_intersecting_road_oid(
                endpoint_geom, road_oid_geom
            )
            if endpoint_road_oid is None:
                continue

            paths1 = bfs_all_paths(
                adjacency=adjacency,
                start=endpoint_road_oid,
                target=target_a,
                max_steps=12,
                valid_oids=valid_adjacency_oid,
            )
            paths2 = bfs_all_paths(
                adjacency=adjacency,
                start=endpoint_road_oid,
                target=target_b,
                max_steps=12,
                valid_oids=valid_adjacency_oid,
            )

            connected = False
            if paths1 or paths2:
                paths = paths1 + paths2
                for path in paths:
                    if (
                        _path_length_linear(
                            path, road_oid_geom, endpoint_geom, rampid_geom
                        )
                        < 1000
                    ):

                        connected = True
                        break

                if connected:
                    endpoint_to_potential_connection.setdefault(
                        endpoint_oid,
                        {"rampid": [], "geom": endpoint_geom},
                    )["rampid"].append(rampid)

    return endpoint_to_potential_connection


def _load_rampid_to_point_geom(files: dict):
    rampid_to_potential_connection = {}

    with arcpy.da.SearchCursor(
        files["potential_points"],
        ["ramp_id", "SHAPE@"],
        where_clause="is_subset IS NULL",
    ) as s_cur:
        for ramp_id, geom in s_cur:
            rampid_to_potential_connection[ramp_id] = geom

    return rampid_to_potential_connection


def _insert_potential_connections(
    files: dict,
    endpoint_to_potential_connection: dict,
    rampid_to_potential_connection: dict,
):
    with arcpy.da.InsertCursor(
        files["potential_connection"], ["SHAPE@", "group_id"]
    ) as i_cur:
        for _, data in endpoint_to_potential_connection.items():
            endpoint_geom = data["geom"]
            for rid in data["rampid"]:
                try:
                    i_cur.insertRow([endpoint_geom, str(rid)])
                except Exception as e:
                    print(
                        f"Error inserting endpoint for rampid {rid}: {e},  {endpoint_geom}"
                    )

        for rampid, ramp_geom in rampid_to_potential_connection.items():
            i_cur.insertRow([ramp_geom, str(rampid)])


def _remove_promoted_endpoints(
    files: dict, endpoints_per_rampid: dict, endpoint_to_potential_connection: dict
):
    """
    removes promoted endpoints from endpoints_per_rampid to avoid duplicates in potential_connection
    and removes endpoints to remove from endpoints_per_rampid to avoid endpoints that are not valid for connection and remove them from endpoints for connections
    """
    for rampid, endpoints in endpoints_per_rampid.items():
        endpoints_per_rampid[rampid] = [
            endpoint
            for endpoint in endpoints
            if not (
                endpoint["endpoint_oid"] in endpoint_to_potential_connection
                and rampid
                in endpoint_to_potential_connection[endpoint["endpoint_oid"]]["rampid"]
            )
        ]

    return endpoints_per_rampid


def _delete_double_points(files: dict, endpoint_to_potential_connection: dict):
    uids_to_xy = defaultdict()
    xy_counts = defaultdict(int)
    with arcpy.da.UpdateCursor(
        files["endpoints_for_connections"], ["SHAPE@XY", "uid"]
    ) as u_cur:
        for row in u_cur:
            xy = row[0]
            uid = row[1]
            uids_to_xy[uid] = xy
            xy_counts[xy] += 1

    endpoint_to_potential_connection_copy = endpoint_to_potential_connection.copy()

    for endpoint_oid, data in endpoint_to_potential_connection_copy.items():
        xy = uids_to_xy.get(endpoint_oid)
        if xy_counts[xy] > 1:
            endpoint_to_potential_connection.pop(endpoint_oid)

    return endpoint_to_potential_connection


@timing_decorator
def make_potential_connection_points(files: dict, endpoints_per_rampid: dict):
    """
    Creates potential connection points for groups with ramp point
    turns ramp point into potential connection point
    then removes endpoints that are already connected to ramp point from endpoints_per_rampid
    and turns them into potential connection points if they are dont intersect any other endpoint
    """
    _create_potential_connection_featureclass(files)

    road_oid_geom, valid_adjacency_oid = _load_non_ramp_roads(files)
    rampid_road_oids = _load_rampid_road_oids(files)
    adjacency = build_adjacency_with_medium(
        files=files, lines=files["relevant_roads_dissolved"]
    )
    adjacency = _add_potential_points_to_adjacency(
        files=files,
        adjacency=adjacency,
        adjacency_file=files["relevant_roads_dissolved"],
    )
    rampid_to_potential_connection = _load_rampid_to_point_geom(files)

    endpoint_to_potential_connection = _build_endpoint_to_potential_connection_map(
        endpoints_per_rampid=endpoints_per_rampid,
        rampid_road_oids=rampid_road_oids,
        road_oid_geom=road_oid_geom,
        valid_adjacency_oid=valid_adjacency_oid,
        adjacency=adjacency,
        rampid_geoms=rampid_to_potential_connection,
    )

    endpoints_per_rampid = _remove_promoted_endpoints(
        files, endpoints_per_rampid, endpoint_to_potential_connection
    )

    endpoint_to_potential_connection = _delete_double_points(
        files, endpoint_to_potential_connection
    )

    _insert_potential_connections(
        files=files,
        endpoint_to_potential_connection=endpoint_to_potential_connection,
        rampid_to_potential_connection=rampid_to_potential_connection,
    )

    return endpoints_per_rampid


#######################
# Extending roads to restore lost connections
#######################


def _load_potential_connections(files: dict) -> dict:
    potential_connections_per_rampid = {}
    with arcpy.da.SearchCursor(
        files["potential_connection"], ["group_id", "SHAPE@"]
    ) as s_cur:
        for group_id, geom in s_cur:
            potential_connections_per_rampid.setdefault(group_id, []).append(geom)
    return potential_connections_per_rampid


def _roads_intersecting_line_body(new_line: arcpy.Polyline, road_oid_geom: dict) -> set:
    """
    Returns roads crossed by the line body, excluding roads touching line endpoints.
    """
    intersect_roads = set()
    sr = new_line.spatialReference
    start_pg = arcpy.PointGeometry(new_line.firstPoint, sr)
    end_pg = arcpy.PointGeometry(new_line.lastPoint, sr)

    for road_oid, road_geom in road_oid_geom.items():
        if (
            not new_line.disjoint(road_geom)
            and start_pg.disjoint(road_geom)
            and end_pg.disjoint(road_geom)
        ):
            intersect_roads.add(road_oid)

    return intersect_roads


def _roads_touching_point(point_geom: arcpy.PointGeometry, road_oid_geom: dict) -> set:
    """
    Returns road ids that touch the point geometry.
    """
    roads = set()
    for road_oid, road_geom in road_oid_geom.items():
        if not point_geom.disjoint(road_geom):
            roads.add(road_oid)
    return roads


def _line_road_intersection_points(
    line_geom: arcpy.Polyline, road_geom
) -> List[arcpy.PointGeometry]:
    """
    Returns all point intersections between a line and one road geometry.
    """
    intersections = []
    inter = line_geom.intersect(road_geom, 1)
    if inter is None:
        return intersections

    sr = line_geom.spatialReference
    for p in inter:
        if p is None:
            continue
        intersections.append(arcpy.PointGeometry(arcpy.Point(p.X, p.Y), sr))

    return intersections


def _find_snap_point_for_same_medium_crossing(
    new_line: arcpy.Polyline,
    intersect_road_oid,
    road_oid_geom: dict,
    adjacency: dict,
    valid_adjacency_oid: set,
    max_steps: int = 12,
) -> Optional[arcpy.PointGeometry]:
    """
    Finds a snap point on the intersected road when that road is connected,
    through adjacency, to any road touching the new line's last point.
    """
    intersect_road_geom = road_oid_geom.get(intersect_road_oid)
    if intersect_road_geom is None:
        return None

    sr = new_line.spatialReference
    end_pg = arcpy.PointGeometry(new_line.lastPoint, sr)
    start_pg = arcpy.PointGeometry(new_line.firstPoint, sr)
    end_point_roads = _roads_touching_point(end_pg, road_oid_geom)
    start_point_roads = _roads_touching_point(start_pg, road_oid_geom)
    if not end_point_roads:
        return None

    connected_start = False
    for start_road_oid in start_point_roads:
        if start_road_oid == intersect_road_oid:
            connected_start = True
            break

        paths = bfs_all_paths(
            adjacency=adjacency,
            start=intersect_road_oid,
            target=start_road_oid,
            max_steps=max_steps,
            max_paths=1,
            valid_oids=valid_adjacency_oid,
        )
        if paths:
            connected_start = True
            break

    if connected_start:
        return None

    connected_end = False
    for end_road_oid in end_point_roads:
        if end_road_oid == intersect_road_oid:
            connected_end = True
            break

        paths = bfs_all_paths(
            adjacency=adjacency,
            start=intersect_road_oid,
            target=end_road_oid,
            max_steps=max_steps,
            max_paths=1,
            valid_oids=valid_adjacency_oid,
        )
        if paths:
            connected_end = True
            break

    if not connected_end:
        return None

    intersection_points = _line_road_intersection_points(new_line, intersect_road_geom)
    if not intersection_points:
        return None

    return min(intersection_points, key=lambda p: p.distanceTo(end_pg))


def _try_other_points_along_lines(
    road_oid_geom, endpoint_geom, candidate_geom, road_oid_medium, new_line_medium
):
    """ """
    intersecting_roads = _roads_touching_point(candidate_geom, road_oid_geom)
    possible_lines = []

    for road_oid in intersecting_roads:
        road_geom = road_oid_geom[road_oid]
        for i in range(1, 100, 2):
            fraction = i / 100
            new_point = road_geom.positionAlongLine(fraction, True)
            if new_point is None:
                continue

            line = arcpy.Polyline(
                arcpy.Array([endpoint_geom.firstPoint, new_point.firstPoint]),
                endpoint_geom.spatialReference,
            )
            roads_intersecting_line = _roads_intersecting_line_body(line, road_oid_geom)
            intersecting_wrong_medium = False
            for road_oid_2 in roads_intersecting_line:
                medium = road_oid_medium.get(road_oid_2)
                if medium == new_line_medium:
                    intersecting_wrong_medium = True
                    break
            if not intersecting_wrong_medium:
                possible_lines.append(line)

    shortest_line = None
    shortest_length = float("inf")
    for line in possible_lines:
        length = line.length
        if length < shortest_length:
            shortest_length = length
            shortest_line = line

    return shortest_line


def _validate_line_crossings(
    new_line: arcpy.Polyline,
    new_line_medium: str,
    road_oid_geom: dict,
    road_oid_medium: dict,
    adjacency: dict,
    valid_adjacency_oid: set,
    candidate_geom: arcpy.Point,
    endpoint_geom: arcpy.Point,
) -> tuple[bool, arcpy.Polyline]:
    """
    Validates line crossings and, only for same-medium conflicts, may snap
    line last point to a crossing point if BFS connectivity allows it.
    """
    current_line = new_line

    # Limit snaps to avoid pathological loops if geometry is degenerate.
    for _ in range(3):
        intersect_roads = _roads_intersecting_line_body(current_line, road_oid_geom)
        if not intersect_roads:
            return True, current_line

        snapped = False
        for road_oid in intersect_roads:
            road_medium = road_oid_medium.get(road_oid)
            if road_medium == new_line_medium:
                snap_point = _find_snap_point_for_same_medium_crossing(
                    new_line=current_line,
                    intersect_road_oid=road_oid,
                    road_oid_geom=road_oid_geom,
                    adjacency=adjacency,
                    valid_adjacency_oid=valid_adjacency_oid,
                    max_steps=12,
                )

                if snap_point is None:
                    shortest_line = _try_other_points_along_lines(
                        road_oid_geom,
                        endpoint_geom,
                        candidate_geom,
                        road_oid_medium,
                        new_line_medium,
                    )
                    if shortest_line:
                        return True, shortest_line
                    return False, current_line

                sr = current_line.spatialReference
                snapped_line = arcpy.Polyline(
                    arcpy.Array([current_line.firstPoint, snap_point.firstPoint]),
                    sr,
                )

                if (
                    snap_point.distanceTo(
                        arcpy.PointGeometry(current_line.lastPoint, sr)
                    )
                    <= 0.001
                ):
                    return False, current_line

                current_line = snapped_line
                snapped = True
                break

        if not snapped:
            return True, current_line

    return False, current_line


def _build_line_between_points(endpoint_geom, candidate_geom):
    if endpoint_geom is None or candidate_geom is None:
        return None, None
    sr = endpoint_geom.spatialReference
    try:
        line = arcpy.Polyline(
            arcpy.Array([endpoint_geom.firstPoint, candidate_geom.firstPoint]), sr
        )
    except Exception as e:
        print(f"Error creating line between points: {e}")
        return None, sr
    if line is None or line.length == 0:
        return None, sr
    return line, sr


def _find_very_short_connection(
    files: dict,
    endpoint_geom: arcpy.PointGeometry,
    candidate_geom: arcpy.PointGeometry,
    road_oid_geom: dict,
    adjacency: dict,
    valid_adjacency_oid: dict,
):
    adjacency = _add_potential_points_to_adjacency(
        files=files,
        adjacency=adjacency,
        adjacency_file=files["relevant_roads_dissolved"],
    )

    endpoint_roads = _roads_touching_point(endpoint_geom, road_oid_geom)

    endpoint_adjacent_oids = set()
    for endpoint_road in endpoint_roads:
        oids = bfs_all_ramps(
            adjacency=adjacency,
            start=endpoint_road,
            valid_oids=valid_adjacency_oid,
            max_steps=5,
        )
        endpoint_adjacent_oids.update(oids)

    candidate_lines_oids = set()
    for oid, road_geom in road_oid_geom.items():
        if not candidate_geom.disjoint(road_geom):
            candidate_lines_oids.add(oid)

    possible_lines = set()
    for candidate_line in candidate_lines_oids:
        oids = bfs_all_ramps(
            adjacency=adjacency,
            start=candidate_line,
            valid_oids=valid_adjacency_oid,
            max_steps=2,
        )
        for oid in oids:
            if oid not in endpoint_adjacent_oids:
                possible_lines.add(oid)

    possible_lines_geoms = []
    for possible_line in possible_lines:
        geom = road_oid_geom.get(possible_line)
        possible_lines_geoms.append(geom)

    shortes_distance = float("inf")
    best_point = None
    for possible_line_geom in possible_lines_geoms:
        if possible_line_geom is None:
            continue
        point_on_line = possible_line_geom.queryPointAndDistance(endpoint_geom, True)[0]
        distance = endpoint_geom.distanceTo(point_on_line)
        if distance < shortes_distance:
            shortes_distance = distance
            best_point = point_on_line

    if shortes_distance < 50:
        return best_point
    else:
        return candidate_geom


def _connect_group_endpoints_3(
    files: dict,
    rampid: str,
    endpoints: list,
    potential_connections_per_rampid: dict,
    road_oid_geom: dict,
    road_oid_medium: dict,
    endpoint_data_map: dict,
    adjacency: dict,
    valid_adjacency_oid: set,
):
    """
    Creates connecting lines between endpoints and potential connection points.

    Logic:
    - Rechecks adjacency before each new line is created.
    - Builds and validates all possible lines.
    - Chooses the shortest finished/validated line.
    - For each endpoint it checks if there is a short connection under 50m it can use instead of the candidate connection point.
    - Adds only one line per while iteration.
    - After adding one line, adjacency is updated and checked again.

    Maximum line length is 500 meters. Lines longer than this are discarded.

    Returns:
        dict: A dictionary mapping endpoint OIDs to lists of new connecting lines.
        spatial reference of the new lines.
    """
    new_lines_for_group = {}
    remaining_endpoints = endpoints.copy()
    potential_connections_per_rampid.setdefault(rampid, [])

    sr = None
    counter = 0

    while remaining_endpoints:
        best_found = False
        connected_endpoint_index = -1

        # Recheck whether some endpoints are already connected
        # before attempting to create a new line.
        remaining_endpoints, potential_connections_per_rampid = (
            _check_endpoints_connection(
                adjacency=adjacency,
                valid_adjacency_oid=valid_adjacency_oid,
                road_oid_geom=road_oid_geom,
                endpoints=remaining_endpoints,
                potential_connections_per_rampid=potential_connections_per_rampid,
                rampid=rampid,
            )
        )

        if not remaining_endpoints:
            break

        valid_connections = []

        # Build and validate all possible endpoint/candidate lines first.
        # We store only valid finished lines, then choose the shortest one.
        for endpoint_idx, endpoint in enumerate(remaining_endpoints):
            endpoint_oid = endpoint["endpoint_oid"]
            endpoint_geom = endpoint["endpoint_geom"]

            if endpoint_geom is None:
                continue

            for candidate_geom in potential_connections_per_rampid[rampid]:
                if candidate_geom is None:
                    continue

                candidate_geom = _find_very_short_connection(
                    files=files,
                    endpoint_geom=endpoint_geom,
                    candidate_geom=candidate_geom,
                    road_oid_geom=road_oid_geom,
                    adjacency=adjacency,
                    valid_adjacency_oid=valid_adjacency_oid,
                )

                new_line, sr = _build_line_between_points(endpoint_geom, candidate_geom)

                if new_line is None:
                    continue

                if new_line.length == 0 or new_line.length > 500:
                    continue

                new_line_medium = endpoint_data_map.get(endpoint_oid, {}).get("medium")

                is_valid, validated_line = _validate_line_crossings(
                    new_line,
                    new_line_medium,
                    road_oid_geom,
                    road_oid_medium,
                    adjacency,
                    valid_adjacency_oid,
                    candidate_geom,
                    endpoint_geom,
                )

                if not is_valid or validated_line is None:
                    continue

                if validated_line.length == 0 or validated_line.length > 500:
                    continue

                valid_connections.append(
                    {
                        "line_length": validated_line.length,
                        "endpoint_idx": endpoint_idx,
                        "endpoint_oid": endpoint_oid,
                        "endpoint_geom": endpoint_geom,
                        "candidate_geom": candidate_geom,
                        "validated_line": validated_line,
                        "sr": sr,
                    }
                )

        # If no valid lines exist for any remaining endpoint, stop.
        if not valid_connections:
            break

        # Choose the shortest finished/validated line.
        valid_connections.sort(key=lambda x: x["line_length"])
        best_connection = valid_connections[0]

        endpoint_idx = best_connection["endpoint_idx"]
        endpoint_oid = best_connection["endpoint_oid"]
        endpoint_geom = best_connection["endpoint_geom"]
        validated_line = best_connection["validated_line"]
        sr = best_connection["sr"]

        new_lines_for_group.setdefault(endpoint_oid, []).append(validated_line)

        # Add this endpoint as a new potential connection point.
        potential_connections_per_rampid[rampid].append(endpoint_geom)

        # Add only this one shortest valid line to adjacency.
        adjacency, valid_adjacency_oid, road_oid_geom = _add_new_line_to_adjacency(
            adjacency=adjacency,
            valid_adjacency_oid=valid_adjacency_oid,
            line=validated_line,
            road_oid_geom=road_oid_geom,
            new_line_oid=f"new_line_{endpoint_oid}_{counter}",
            sr=sr,
        )

        counter += 1
        connected_endpoint_index = endpoint_idx
        best_found = True

        # Remove only the endpoint directly connected by this new line.
        # Other endpoints that became connected indirectly will be removed
        # by _check_endpoints_connection at the start of the next iteration.
        if best_found:
            remaining_endpoints.pop(connected_endpoint_index)

    return new_lines_for_group, sr


def _write_new_lines_feature_class(
    files: dict, endpoint_data_map: dict, new_lines: dict, spatial_reference
):
    if spatial_reference is None:
        spatial_reference = arcpy.Describe(files["copy_of_input"]).spatialReference

    arcpy.management.CreateFeatureclass(
        os.path.dirname(files["new_lines"]),
        os.path.basename(files["new_lines"]),
        geometry_type="POLYLINE",
        template=files["copy_of_input"],
        spatial_reference=spatial_reference,
    )

    fields = [
        f.name
        for f in arcpy.ListFields(files["new_lines"])
        if f.type not in ("OID", "Geometry")
    ]
    fields = ["SHAPE@"] + fields

    with arcpy.da.InsertCursor(files["new_lines"], fields) as i_cur:
        for uid, lines in new_lines.items():
            data = endpoint_data_map.get(uid, {})
            for line in lines:
                row = [line] + [data.get(field, None) for field in fields[1:]]
                i_cur.insertRow(row)


def _finalize_new_lines(new_lines_fc: str):
    arcpy.management.DeleteIdentical(
        in_dataset=new_lines_fc,
        fields="Shape",
    )
    arcpy.management.RepairGeometry(
        in_features=new_lines_fc,
        delete_null="DELETE_NULL",
    )


def _add_new_line_to_adjacency(
    adjacency: dict,
    valid_adjacency_oid: set,
    line: arcpy.Polyline,
    road_oid_geom: dict,
    new_line_oid: int,
    sr,
):
    """
    adds new line to adjacency by checking which roads its endpoints intersect with and adding a ghost member to the adjacency list for those roads
    also adds the new line to the road_oid_geom and valid_adjacency_oid sets
    """
    start_point = line.firstPoint
    end_point = line.lastPoint
    start_pg = arcpy.PointGeometry(start_point, sr)
    end_pg = arcpy.PointGeometry(end_point, sr)

    for road_oid, road_geom in road_oid_geom.items():
        if not start_pg.disjoint(road_geom) or not end_pg.disjoint(road_geom):
            adjacency.setdefault(road_oid, set()).add(new_line_oid)
            adjacency.setdefault(new_line_oid, set()).add(road_oid)

    valid_adjacency_oid.add(new_line_oid)
    road_oid_geom[new_line_oid] = line

    return adjacency, valid_adjacency_oid, road_oid_geom


def _check_endpoints_connection(
    adjacency: dict,
    valid_adjacency_oid: set,
    road_oid_geom: dict,
    endpoints,
    rampid: str,
    potential_connections_per_rampid: dict,
):
    """
    Checks if the endpoints are connected to the potential connection points
    and removes the endpoints that are connected from the endpoints list.
    and adds the connected endpoints to the potential_connections_per_rampid dictionary
    """

    endpoints_copy = endpoints.copy()

    for endpoint in endpoints_copy:
        endpoint_oid = endpoint["endpoint_oid"]
        endpoint_geom = endpoint["endpoint_geom"]

        # Skip endpoints with None geometry
        if endpoint_geom is None:
            continue

        endpoint_road_oids = []
        for road_oid, road_geom in road_oid_geom.items():
            if not endpoint_geom.disjoint(road_geom):
                endpoint_road_oids.append(road_oid)

        connected = False
        for potential_geom in potential_connections_per_rampid.get(rampid, []):
            # Skip None geometries
            if potential_geom is None:
                continue

            if connected:
                break
            potential_road_oids = []
            for road_oid, road_geom in road_oid_geom.items():
                if not potential_geom.disjoint(road_geom):
                    potential_road_oids.append(road_oid)

            for endpoint_road_oid in endpoint_road_oids:

                if connected:
                    break
                for potential_road_oid in potential_road_oids:
                    paths = bfs_all_paths(
                        adjacency=adjacency,
                        start=endpoint_road_oid,
                        target=potential_road_oid,
                        max_steps=8,
                        valid_oids=valid_adjacency_oid,
                    )

                    if paths:

                        for path in paths:
                            if (
                                _path_length_linear(
                                    path, road_oid_geom, endpoint_geom, potential_geom
                                )
                                < 1000
                            ):
                                connected = True
                                break

        if connected:
            potential_connections_per_rampid.setdefault(rampid, []).append(
                endpoint_geom
            )
            endpoints.remove(endpoint)

    return endpoints, potential_connections_per_rampid


def _load_non_ramp_road_mediums(files: dict) -> dict:
    road_oid_medium = {}
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved"], ["OID@", "medium", "typeveg"]
    ) as s_cur:
        for oid, medium, typeveg in s_cur:
            if typeveg != "rampe":
                road_oid_medium[oid] = medium
    return road_oid_medium


def _add_potential_points_to_adjacency(
    files: dict, adjacency: dict, adjacency_file: str
):
    """
    connects roads in adjacency if they both intersect the same point
    """
    potential_points_oid_geom = {}
    with arcpy.da.SearchCursor(files["potential_points"], ["OID@", "SHAPE@"]) as s_cur:
        for oid, geom in s_cur:
            potential_points_oid_geom[oid] = geom

    lines_oid_geom = {}
    with arcpy.da.SearchCursor(adjacency_file, ["OID@", "SHAPE@"]) as s_cur:
        for oid, geom in s_cur:
            lines_oid_geom[oid] = geom

    # For each point, find all lines that touch it and connect all line-pairs
    for _, point_geom in potential_points_oid_geom.items():
        if point_geom is None:
            continue

        intersecting_line_oids = set()
        for line_oid, line_geom in lines_oid_geom.items():
            if line_geom is None:
                continue
            if not point_geom.disjoint(line_geom):
                intersecting_line_oids.add(line_oid)

        for line_oid_1 in intersecting_line_oids:
            for line_oid_2 in intersecting_line_oids:
                if line_oid_1 != line_oid_2:
                    adjacency.setdefault(line_oid_1, set()).add(line_oid_2)
                    adjacency.setdefault(line_oid_2, set()).add(line_oid_1)

    return adjacency


def _sort_rampids_by_avg_vegklasse(
    endpoints_per_rampid: dict, endpoint_data_map: dict
) -> dict:
    """
    Sort rampids by the average vegklasse of their endpoints (highest first).
    """

    def avg_vegklasse(endpoints):
        values = [
            endpoint_data_map.get(e["endpoint_oid"], {}).get("vegklasse", 0)
            for e in endpoints
        ]
        return sum(values) / len(values) if values else 0

    return dict(
        sorted(
            endpoints_per_rampid.items(),
            key=lambda item: avg_vegklasse(item[1]),
            reverse=True,
        )
    )


@timing_decorator
def extending_roads(files: dict, endpoints_per_rampid: dict, endpoint_data_map: dict):
    """
    What:
        This function orchestrates the process of extending roads to restore lost connections.
        It iterates through each group, checks for potential connections, and creates new lines
        to connect endpoints to potential connection points.

    How:
       Sorts the groups by average vegklasse of their endpoints (highest first).
       For each group, it checks if the endpoints are already connected to potential connection points.
       Then connects the endpoints to the potential connection points by creating new lines, validating them, and updating the adjacency structure.

    Why:
       We Sort the groups by average vegklasse to prioritize roads with higher vegklasse for creating new lines

    """
    potential_connections_per_rampid = _load_potential_connections(files)

    all_new_lines = {}
    last_sr = None

    adjacency = build_adjacency_with_medium(
        files=files, lines=files["relevant_roads_dissolved"]
    )
    road_oid_geom, valid_adjacency_oid = _load_non_ramp_roads(files)
    road_oid_medium = _load_non_ramp_road_mediums(files)
    counter = 0
    endpoints_per_rampid = _sort_rampids_by_avg_vegklasse(
        endpoints_per_rampid, endpoint_data_map
    )

    for rampid, endpoints in endpoints_per_rampid.items():
        counter += 1

        endpoints, potential_connections_per_rampid = _check_endpoints_connection(
            adjacency=adjacency,
            valid_adjacency_oid=valid_adjacency_oid,
            road_oid_geom=road_oid_geom,
            endpoints=endpoints,
            potential_connections_per_rampid=potential_connections_per_rampid,
            rampid=rampid,
        )

        group_lines, sr = _connect_group_endpoints_3(
            files,
            rampid,
            endpoints,
            potential_connections_per_rampid,
            road_oid_geom,
            road_oid_medium,
            endpoint_data_map,
            adjacency,
            valid_adjacency_oid,
        )
        if sr is not None:
            last_sr = sr
        for uid, lines in group_lines.items():
            all_new_lines.setdefault(uid, []).extend(lines)
            adjacency, valid_adjacency_oid, road_oid_geom = _add_new_line_to_adjacency(
                adjacency=adjacency,
                valid_adjacency_oid=valid_adjacency_oid,
                line=lines[0],
                road_oid_geom=road_oid_geom,
                new_line_oid=f"new_line_{uid}_{counter}",
                sr=sr,
            )

    _write_new_lines_feature_class(
        files=files,
        endpoint_data_map=endpoint_data_map,
        new_lines=all_new_lines,
        spatial_reference=last_sr,
    )
    _finalize_new_lines(files["new_lines"])


###################################################################################
#                                       PART 2                                    #
###################################################################################
@timing_decorator
def main_part_2(input_roads_fc: str, input_points_fc: str, output_points_fc: str):
    """
    Roads have the column ramp_id with the obj id of potential ramp points they intersect with
    If 2 roads with different mediums cross and have the same values in ramp_id we want to move that point to the intersection of those 2 roads (excluding endpoints)

    Removes points if they are subsets of another surviving point
    Removes points where there is a short connection between the roads the point is on
    """
    config = core_config.WorkFileConfig(root_file=input_points_fc)
    wfm = WorkFileManager(config=config)
    files = create_wfm_gdbs_2(wfm=wfm)
    arcpy.management.CopyFeatures(input_roads_fc, files["copy_of_roads"])
    arcpy.management.CopyFeatures(input_points_fc, files["copy_of_points"])

    explode_roads(files=files)
    dissolve_exploded_roads(
        exploded_roads=files["exploded_roads"],
        output_fc=files["exploded_roads_dissolved"],
    )
    keep_relevant_roads(files=files)
    find_surviving_potential_points(files=files, input_points=input_points_fc)
    remove_subsets(files=files)
    remove_points_with_short_connections(files=files, short_path_length=250)

    arcpy.DeleteIdentical_management(
        in_dataset=files["potential_points_part2"],
        fields="Shape",
        xy_tolerance="5 Meters",
    )
    arcpy.management.CopyFeatures(
        in_features=files["potential_points_part2"],
        out_feature_class=output_points_fc,
    )
    wfm.delete_created_files()


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
    exploded_roads_dissolved = wfm.build_file_path(
        file_name="exploded_roads_dissolved", file_type="gdb"
    )
    potential_points_part2 = wfm.build_file_path(
        file_name="potential_points_part2", file_type="gdb"
    )
    endpoints = wfm.build_file_path(file_name="endpoints", file_type="gdb")
    endpoints_without_ramp_id = wfm.build_file_path(
        file_name="endpoints_without_ramp_id", file_type="gdb"
    )
    endpoints_with_ramp_id = wfm.build_file_path(
        file_name="endpoints_with_ramp_id", file_type="gdb"
    )
    dissolved_without_ramp_id = wfm.build_file_path(
        file_name="dissolved_without_ramp_id", file_type="gdb"
    )
    near_table = wfm.build_file_path(file_name="near_table", file_type="gdb")
    relevant_roads = wfm.build_file_path(file_name="relevant_roads", file_type="gdb")
    relevant_roads_dissolved_medium = wfm.build_file_path(
        file_name="relevant_roads_dissolved_medium", file_type="gdb"
    )

    return {
        "copy_of_roads": copy_of_roads,
        "copy_of_points": copy_of_points,
        "exploded_roads": exploded_roads,
        "exploded_roads_dissolved": exploded_roads_dissolved,
        "potential_points_part2": potential_points_part2,
        "endpoints": endpoints,
        "endpoints_without_ramp_id": endpoints_without_ramp_id,
        "endpoints_with_ramp_id": endpoints_with_ramp_id,
        "dissolved_without_ramp_id": dissolved_without_ramp_id,
        "near_table": near_table,
        "relevant_roads": relevant_roads,
        "relevant_roads_dissolved_medium": relevant_roads_dissolved_medium,
    }


@timing_decorator
def explode_roads(files: dict):
    """
    When a road intersects more than one potential point the value in ramp_id looks like this: 51,52,43,
    so to make sure this road can dissolve and intersect with multiple other roads that share one of the values in ramp_id
    we explode the road table on the column ramp_id

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

    with arcpy.da.SearchCursor(
        files["copy_of_roads"], search_fields
    ) as s_cur, arcpy.da.InsertCursor(files["exploded_roads"], insert_fields) as i_cur:

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
    using these fields: ["objtype", "medium", "motorvegtype", "vegkategori", "typeveg", "ramp_id"]
    """
    arcpy.management.Dissolve(
        in_features=exploded_roads,
        out_feature_class=output_fc,
        dissolve_field=[
            "objtype",
            "medium",
            "motorvegtype",
            "vegkategori",
            "typeveg",
            "ramp_id",
        ],
        multi_part="SINGLE_PART",
    )


@timing_decorator
def keep_relevant_roads(files: dict):
    """
    remove roads that dont have potential to be a ramp crossing,
    keep roads that have a ramp_id that is shared with at least one other road,
    remove roads that have null ramp_id since they cant be part of a crossing
    and remove roads that have a ramp_id that is not shared with any other road since they cant be part of a crossing
    """
    ramp_id_count = defaultdict(int)
    with arcpy.da.SearchCursor(
        files["exploded_roads_dissolved"], ["OID@", "ramp_id"]
    ) as s_cur:
        for row in s_cur:
            if row[1] is None:
                continue
            ramp_id_count[row[1]] += 1

    with arcpy.da.UpdateCursor(
        files["exploded_roads_dissolved"], ["OID@", "ramp_id"]
    ) as u_cur:
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
    excluding endpoints

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
                # ep_i = _endpoints(gi)
                # ep_j = _endpoints(gj)

                # iterate resulting points

                for p in inter:
                    if p is None:
                        continue
                    key = _coord_key(p.X, p.Y)
                    # skip if intersection equals an endpoint of either geometry
                    # if p in ep_i or p in ep_j:
                    #    continue
                    if p in seen:
                        continue
                    seen.add(p)
                    # create PointGeometry with spatial reference of gi
                    sr = (
                        gi.spatialReference if hasattr(gi, "spatialReference") else None
                    )
                    pg = (
                        arcpy.PointGeometry(arcpy.Point(p.X, p.Y), sr)
                        if sr is not None
                        else arcpy.PointGeometry(arcpy.Point(p.X, p.Y))
                    )
                    rid_points[rid].append(pg)

    # delete existing
    out_fc = files["potential_points_part2"]
    arcpy.management.CopyFeatures(input_points, out_fc)
    arcpy.management.DeleteRows(out_fc)

    attr_fields = [
        f.name
        for f in arcpy.ListFields(input_points)
        if f.type not in ("OID", "Geometry")
    ]
    attr_fields.remove("ramp_id")
    fields = ["ramp_id"] + attr_fields + ["SHAPE@"]

    with arcpy.da.SearchCursor(input_points, fields) as s_cur, arcpy.da.InsertCursor(
        out_fc, fields
    ) as ins:
        for srow in s_cur:
            oid = srow[0]
            rid_key = str(oid)
            pts = rid_points.get(rid_key)
            if not pts:
                continue
            # if multiple pts choose the closest to the original point
            new_shape = min(pts, key=lambda p: p.distanceTo(srow[-1]))

            new_row = list(srow)
            new_row[-1] = new_shape  # replace shape
            ins.insertRow(new_row)

    # remove_endpoints_part_2_test(files=files, lines_fc=in_fc, points_fc=out_fc)
    layer = "layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_roads"],
        out_layer=layer,
        where_clause="ramp_id IS NOT NULL",
    )
    arcpy.edit.Snap(in_features=layer, snap_environment=[[layer, "END", "1 meter"]])
    arcpy.management.Dissolve(
        in_features=layer,
        out_feature_class=files["dissolved_without_ramp_id"],
        dissolve_field=["objtype", "medium"],
        multi_part="SINGLE_PART",
    )
    remove_endpoints_part_2(
        files=files, lines_fc=files["dissolved_without_ramp_id"], points_fc=out_fc
    )


def _parse_ramp_ids(value):
    """
    Convert a ramp_id text value like '54,67,89' into a set {'54', '67', '89'}.
    Null/empty values return an empty set.
    """
    if value is None:
        return set()

    text = str(value).strip()
    if not text:
        return set()

    return {part.strip() for part in text.split(",") if part.strip()}


def _shares_ramp_id(ramp_a, ramp_b):
    """
    Returns True if ramp_a and ramp_b share at least one ramp id.

    Examples:
        '54,66' and '66,55' -> True
        '54,66' and '77,55' -> False
        None and '66,55'     -> False
    """
    ids_a = _parse_ramp_ids(ramp_a)
    ids_b = _parse_ramp_ids(ramp_b)
    return bool(ids_a & ids_b)


def remove_endpoints_part_2(files: dict, lines_fc: str, points_fc: str):
    """
    Removes points in points_fc that intersect with endpoints in lines_fc
    In part 2 we have some exceptions where we dont wish to remove the points even if they are intersecting with endpoints
        - Two roads with the same ramp ID can cross, where one is split by the other and their endpoints are about 1 meter apart, preventing dissolving.
        - There can be different ramp_ids on each side of the cross, here we also wish to not remove the points
        - There can also be a different endpoint that just happens to intersect with a valid point

    To solve this:
        - If two endpoints with the same ramp_id and same medium are very close (2 meters) they get removed from endpoints
        - TEST if two endpoints with different ramp_id and same medium are very close (2 meters) they get removed from endpoints
        - Points and endpoints need same ramp_id to remove a point
    """

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files["endpoints_with_ramp_id"]),
        out_name=os.path.basename(files["endpoints_with_ramp_id"]),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(lines_fc).spatialReference,
    )
    endpoint_ramp_field = "ep_ramp_id"
    arcpy.management.AddField(
        files["endpoints_with_ramp_id"], endpoint_ramp_field, "TEXT", field_length=255
    )

    layer = "layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["exploded_roads_dissolved"],
        out_layer=layer,
        where_clause="ramp_id IS NOT NULL",
    )

    with arcpy.da.SearchCursor(
        files["exploded_roads_dissolved"], ["OID@", "SHAPE@", "ramp_id"]
    ) as road_cur, arcpy.da.InsertCursor(
        files["endpoints_with_ramp_id"], ["SHAPE@", endpoint_ramp_field]
    ) as ins_cur:
        for oid, geom, ramp_id in road_cur:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg, ramp_id])
            ins_cur.insertRow([end_pg, ramp_id])

    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(files["endpoints_without_ramp_id"]),
        out_name=os.path.basename(files["endpoints_without_ramp_id"]),
        geometry_type="POINT",
        spatial_reference=arcpy.Describe(lines_fc).spatialReference,
    )

    with arcpy.da.SearchCursor(
        lines_fc, ["OID@", "SHAPE@"]
    ) as road_cur, arcpy.da.InsertCursor(
        files["endpoints_without_ramp_id"], ["SHAPE@"]
    ) as ins_cur:
        for oid, geom in road_cur:
            # if oid in intersecting_oids:
            start_pg, end_pg = get_line_endpoints(geom)
            ins_cur.insertRow([start_pg])
            ins_cur.insertRow([end_pg])

    point_oids_to_delete = set()

    # build endpoint geometry lists
    endpoints_without_geoms = []
    with arcpy.da.SearchCursor(files["endpoints_without_ramp_id"], ["SHAPE@"]) as ecur:
        for (g,) in ecur:
            endpoints_without_geoms.append(g)

    endpoints_with = []
    with arcpy.da.SearchCursor(
        files["endpoints_with_ramp_id"], ["ep_ramp_id", "SHAPE@"]
    ) as ecur:
        for eramp, g in ecur:
            endpoints_with.append((eramp, g))

    # find points that intersect both kinds of endpoints and share ramp id
    with arcpy.da.SearchCursor(points_fc, ["OID@", "ramp_id", "SHAPE@"]) as pcur:
        for oid, p_ramp, p_geom in pcur:
            if p_geom is None:
                continue
            # must intersect at least one endpoint without ramp_id
            intersects_without = any(
                not p_geom.disjoint(egeom) for egeom in endpoints_without_geoms
            )
            if not intersects_without:
                continue
            # must intersect at least one endpoint with ramp_id that shares ramp id
            for ep_ramp, egeom in endpoints_with:
                if p_geom.disjoint(egeom):
                    continue
                if _shares_ramp_id(p_ramp, ep_ramp):
                    point_oids_to_delete.add(int(oid))
                    break

    if point_oids_to_delete:
        points_lyr = arcpy.management.MakeFeatureLayer(
            points_fc, "points_lyr"
        ).getOutput(0)

        oid_sql = ",".join(map(str, point_oids_to_delete))
        where = f"OBJECTID IN ({oid_sql})"

        arcpy.management.SelectLayerByAttribute(points_lyr, "NEW_SELECTION", where)
        if int(arcpy.management.GetCount(points_lyr).getOutput(0)) > 0:
            arcpy.management.DeleteRows(points_lyr)

        arcpy.management.Delete(points_lyr)


def remove_subsets(files: dict):
    """
    If a surviving point is a subset of another surviving point we remove the one that is the subset
    subset is defined in part 1 of the ramp generalization
    """
    ramp_ids = set()
    with arcpy.da.SearchCursor(files["potential_points_part2"], ["ramp_id"]) as s_cur:
        for row in s_cur:
            rid = row[0]
            ramp_ids.add(rid)

    with arcpy.da.UpdateCursor(
        files["potential_points_part2"], ["ramp_id", "is_subset"]
    ) as u_cur:
        for row in u_cur:
            rid = row[0]
            if row[1] is None:
                continue
            subset_ids = [x.strip() for x in str(row[1]).split(",") if x.strip()]
            if any(sid in ramp_ids for sid in subset_ids):
                u_cur.deleteRow()


@timing_decorator
def remove_points_with_short_connections(files: dict, short_path_length: int):
    """
    Removes points when the two roads it is on have a short connection
    """
    layer = "layer"
    arcpy.management.MakeFeatureLayer(
        in_features=files["copy_of_roads"], out_layer=layer
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=layer,
        overlap_type="WITHIN_A_DISTANCE",
        select_features=files["potential_points_part2"],
        search_distance="500 Meters",
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CopyFeatures(
        in_features=layer, out_feature_class=files["relevant_roads"]
    )
    orig_oid_dissolved_oid = dissolve_and_return_connection(
        files["relevant_roads"], files["relevant_roads_dissolved_medium"], ["medium"]
    )
    adjacency = build_adjacency_with_medium(
        files, files["relevant_roads_dissolved_medium"]
    )
    remove_points = set()

    valid_oids = defaultdict(set)
    arcpy.analysis.GenerateNearTable(
        files["potential_points_part2"],
        files["relevant_roads_dissolved_medium"],
        files["near_table"],
        search_radius="500 Meter",
        closest="ALL",
    )
    with arcpy.da.SearchCursor(files["near_table"], ["IN_FID", "NEAR_FID"]) as s_cur:
        for row in s_cur:
            in_fid = row[0]
            near_fid = row[1]
            valid_oids[in_fid].add(near_fid)

    road_geom_rampid_medium = defaultdict(list)
    with arcpy.da.SearchCursor(
        files["relevant_roads"], ["OID@", "SHAPE@", "ramp_id", "medium"]
    ) as s_cur:
        for oid, geom, rid, medium in s_cur:
            road_geom_rampid_medium.setdefault(oid, [geom, rid, medium])

    fid_fields = [
        f.name
        for f in arcpy.ListFields(files["potential_points_part2"])
        if f.type not in ("OID", "Geometry")
    ]
    fid_fields.remove("ramp_id")
    cursor_fields = ["ramp_id"] + fid_fields + ["SHAPE@"]
    all_ramp_oids_per_rampid = defaultdict(set)
    line_geom_dict = defaultdict(set)
    with arcpy.da.SearchCursor(
        files["relevant_roads_dissolved_medium"], ["OID@", "SHAPE@"]
    ) as s_cur:
        for row in s_cur:
            oid = row[0]
            geom = row[1]
            line_geom_dict[oid] = geom

    with arcpy.da.SearchCursor(files["potential_points_part2"], cursor_fields) as s_cur:
        for row in s_cur:
            point_oid = row[0]

            roads = []
            medium = set()
            for key, items in road_geom_rampid_medium.items():
                if _shares_ramp_id(items[1], point_oid):
                    if items[2] not in medium:
                        if not items[0].disjoint(row[-1]):
                            roads.append(key)
                            medium.add(items[2])
            if len(roads) != 2:
                continue
            road_a = roads[0]
            road_b = roads[1]
            road_a_dissolved = int(orig_oid_dissolved_oid[str(road_a)])
            road_b_dissolved = int(orig_oid_dissolved_oid[str(road_b)])
            near_set = valid_oids.get(point_oid, set())
            all_paths = bfs_all_paths_with_prevous_neighbour_rule(
                adjacency=adjacency,
                start=road_a_dissolved,
                target=road_b_dissolved,
                max_steps=10,
                valid_oids=near_set,
            )

            short_paths = [
                path
                for path in all_paths
                if path_lenght(path, line_geom_dict) <= short_path_length
            ]

            has_short_path = bool(short_paths)

            if has_short_path:
                remove_points.add(point_oid)

    with arcpy.da.UpdateCursor(files["potential_points_part2"], ["ramp_id"]) as u_cur:
        for row in u_cur:
            if row[0] in remove_points:
                u_cur.deleteRow()


def correct_ramp_id_after_merge_divided_roads(
    merge_input: str, merge_output: str, merge_out_table: str
):
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
    """
    main_part_2(
        input_roads_fc=Road_N100.data_preparation___road_final_output___n100_road.value,
        input_points_fc=Road_N100.ramps__potential_points__n100_road.value,
        output_points_fc=Road_N100.ramps__final_points__n100_road.value,
    )"""
