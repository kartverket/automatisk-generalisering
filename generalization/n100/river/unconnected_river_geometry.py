import arcpy
import multiprocessing
from multiprocessing import Pool, Manager
from math import radians, cos, sin, sqrt, atan2
from tqdm import tqdm

import config
from env_setup import environment_setup
from input_data import input_n50
from input_data import input_n100
from custom_tools import custom_arcpy
from file_manager.n100.file_manager_rivers import River_N100


def main():
    geomotry_search_tolerance = 15
    id_field = "orig_ob_id"
    dangle_id_field = "dang_id"
    cpu_usage_percentage = 0.9
    num_cores = int(multiprocessing.cpu_count() * cpu_usage_percentage)
    setup_arcpy_environment()
    copy_input_features(geomotry_search_tolerance)

    # Feature classes
    buffer_fc = River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value
    line_fc = River_N100.unconnected_river_geometry__unsplit_river_features__n100.value
    polygon_fc = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )
    point_fc = River_N100.unconnected_river_geometry__river_dangles__n100.value

    # Determine total number of buffers
    total_buffers = int(arcpy.GetCount_management(buffer_fc)[0])

    # Define the percentage of the dataset to process in each batch (e.g., 25%)
    batch_percentage = 0.05
    batch_size = int(total_buffers * batch_percentage)

    # Prepare arguments for each batch
    batch_args = [
        (
            start,
            min(start + batch_size, total_buffers),
            line_fc,
            polygon_fc,
            buffer_fc,
            id_field,
            dangle_id_field,
        )
        for start in range(0, total_buffers, batch_size)
    ]

    print("starting processing unconnected river geometry loop...")
    with Manager() as manager:
        shared_results = manager.list()  # Shared list for results
        queue = manager.Queue()  # Manager Queue for progress tracking

        # Include both shared_results and queue in the tuples
        args_with_shared_results = [(*arg, shared_results, queue) for arg in batch_args]

        with Pool(processes=num_cores) as pool:
            pool.starmap(process_batch, args_with_shared_results)

        all_problematic_ids = list(shared_results)
        print("All problematic IDs:", all_problematic_ids)

    try:
        resolve_geometry(id_field, dangle_id_field, all_problematic_ids)
    except Exception as e:
        print("Error in resolve_geometry:", e)

    problematic_dangles, all_rivers, water_polygon = connect_unconnected_features()

    # Ensure all_rivers and water_polygon are accessible for find_closest_feature function
    search_features = [
        all_rivers,
        water_polygon,
    ]  # This may need adjustment based on actual implementation

    # Iterate through problematic dangles
    with arcpy.da.SearchCursor(problematic_dangles, ["SHAPE@"]) as dangle_cursor:
        for dangle_row in dangle_cursor:
            dangle_point = dangle_row[0]
            oid, matching_vertex = get_matching_vertex(all_rivers, dangle_point)
            if oid and matching_vertex:
                # Note: find_closest_feature function may need to be adjusted to accept a point geometry directly
                closest_feature_point, _ = find_closest_feature(
                    oid, search_features, dangle_point
                )
                if closest_feature_point:
                    # Calculate extension distance and direction
                    angle, distance = calculate_extension_direction_and_distance(
                        matching_vertex, closest_feature_point
                    )
                    extend_line_vertex(
                        all_rivers,
                        oid,
                        distance,
                        matching_vertex,
                        closest_feature_point,
                    )


def setup_arcpy_environment():
    """
    Summary:
        Sets up the ArcPy environment based on predefined settings defined in `general_setup`.
        This function ensures that the ArcPy environment is properly configured for the specific project by utilizing
        the `general_setup` function from the `environment_setup` module.

    Details:
        - It calls the `general_setup` function from the `environment_setup` module to set up the ArcPy environment based on predefined settings.
    """
    environment_setup.general_setup()


def copy_input_features(geomotry_search_tolerance):
    arcpy.UnsplitLine_management(
        in_features=config.river_sprint_feature,
        out_feature_class=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
    )

    print(
        f"Created {River_N100.unconnected_river_geometry__unsplit_river_features__n100.value}"
    )

    id_field = "orig_ob_id"
    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(
        in_table=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        field_name=id_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        field=id_field,
        expression="!OBJECTID!",
    )
    print(f"Added field orig_ob_id")

    sql_expression_water_features = f"OBJTYPE = 'FerskvannTørrfall' Or OBJTYPE = 'Innsjø' Or OBJTYPE = 'InnsjøRegulert' Or OBJTYPE = 'Havflate' Or OBJTYPE = 'ElvBekk'"
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=sql_expression_water_features,
        output_name=River_N100.unconnected_river_geometry__water_area_features__n100.value,
    )

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__water_area_features__n100.value,
        overlap_type=custom_arcpy.OverlapType.WITHIN_A_DISTANCE.value,
        select_features=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        output_name=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        search_distance=f"{geomotry_search_tolerance} Meters",
    )

    arcpy.management.FeatureVerticesToPoints(
        in_features=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        out_feature_class=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        point_location="DANGLE",
    )
    print(f"Created {River_N100.unconnected_river_geometry__river_dangles__n100.value}")

    dangle_id_field = "dang_id"
    # Adding transferring the NBR value to the matrikkel_bygningspunkt
    arcpy.AddField_management(
        in_table=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        field_name=dangle_id_field,
        field_type="LONG",
    )
    arcpy.CalculateField_management(
        in_table=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        field=dangle_id_field,
        expression="!OBJECTID!",
    )
    print(f"Added field dang_id")

    custom_arcpy.select_location_and_make_permanent_feature(
        input_layer=River_N100.unconnected_river_geometry__river_dangles__n100.value,
        overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        select_features=River_N100.unconnected_river_geometry__water_area_features_selected__n100.value,
        output_name=River_N100.unconnected_river_selected_river_dangles__n100.value,
        inverted=True,
    )

    arcpy.analysis.PairwiseBuffer(
        in_features=River_N100.unconnected_river_selected_river_dangles__n100.value,
        out_feature_class=River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value,
        buffer_distance_or_field=f"{geomotry_search_tolerance} Meters",
    )
    print(
        f"Created {River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value}"
    )

    # Feature classes
    buffer_fc = River_N100.unconnected_river_geometry__river_dangles_buffer__n100.value
    line_fc = River_N100.unconnected_river_geometry__unsplit_river_features__n100.value
    polygon_fc = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )
    point_fc = River_N100.unconnected_river_selected_river_dangles__n100.value


def process_batch(
    start,
    end,
    line_fc,
    polygon_fc,
    buffer_fc,
    id_field,
    dangle_id_field,
    shared_results,
    queue,
):
    lines = [
        (row[0], row[1]) for row in arcpy.da.SearchCursor(line_fc, [id_field, "SHAPE@"])
    ]
    polygons = [row[0] for row in arcpy.da.SearchCursor(polygon_fc, ["SHAPE@"])]

    query = f"OBJECTID >= {start} AND OBJECTID < {end}"
    with arcpy.da.SearchCursor(
        buffer_fc, [id_field, dangle_id_field, "SHAPE@"], where_clause=query
    ) as buffer_cursor:
        for buffer_row in buffer_cursor:
            buffer_id, dangle_id, buffer_geom = buffer_row

            line_intersect = any(
                line_id != buffer_id
                and (
                    not buffer_geom.disjoint(line_geom)
                    or buffer_geom.touches(line_geom)
                )
                for line_id, line_geom in lines
            )

            polygon_intersect = any(
                not buffer_geom.disjoint(poly_geom) or buffer_geom.touches(poly_geom)
                for poly_geom in polygons
            )

            if line_intersect or polygon_intersect:
                buffer_id, dangle_id, buffer_geom = buffer_row
                shared_results.append((buffer_id, dangle_id))

    queue.put(1)


def resolve_geometry(
    id_field,
    dangle_id_field,
    all_problematic_ids,
):
    # Check if the list is empty
    if not all_problematic_ids:
        print("No problematic IDs found.")
        return

    # Separate id_field and dangle_id_field values
    line_ids = {item[0] for item in all_problematic_ids}  # Extract unique line IDs
    dangle_ids = {item[1] for item in all_problematic_ids}  # Extract unique dangle IDs

    # Convert list of line IDs to a comma-separated string
    line_ids_string = ", ".join(map(str, line_ids))
    print("Line IDs SQL Query String:", line_ids_string)

    # Construct the SQL query for line IDs
    sql_line_problematic_ids = f"{id_field} IN ({line_ids_string})"
    print("Line IDs SQL Query:", sql_line_problematic_ids)

    # Convert list of dangle IDs to a comma-separated string
    dangle_ids_string = ", ".join(map(str, dangle_ids))
    print("Dangle IDs SQL Query String:", dangle_ids_string)

    # Construct the SQL query for dangle IDs
    sql_dangle_problematic_ids = f"{dangle_id_field} IN ({dangle_ids_string})"
    print("Dangle IDs SQL Query:", sql_dangle_problematic_ids)

    # Proceed with the selection and creation of features for lines
    if line_ids:
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
            expression=sql_line_problematic_ids,
            output_name=River_N100.unconnected_river_geometry__problematic_river_lines__n100.value,
        )

    # Proceed with the selection and creation of features for dangles
    if dangle_ids:
        custom_arcpy.select_attribute_and_make_permanent_feature(
            input_layer=River_N100.unconnected_river_geometry__river_dangles__n100.value,
            expression=sql_dangle_problematic_ids,
            output_name=River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value,
        )


def connect_unconnected_features():
    arcpy.management.CopyFeatures(
        in_features=River_N100.unconnected_river_geometry__unsplit_river_features__n100.value,
        out_feature_class=f"{River_N100.unconnected_river_geometry__unsplit_river_features__n100.value}_copy",
    )

    problematic_dangles = (
        River_N100.unconnected_river_geometry__problematic_river_dangles__n100.value
    )
    all_rivers = f"{River_N100.unconnected_river_geometry__unsplit_river_features__n100.value}_copy"
    water_polygon = (
        River_N100.unconnected_river_geometry__water_area_features_selected__n100.value
    )
    return problematic_dangles, all_rivers, water_polygon


def get_matching_vertex(line_feature_class, dangle_point):
    """
    Find the line and vertex in line_feature_class that matches the dangle_point location.
    Returns the line OID and the matching vertex as an arcpy.Point object.
    """
    with arcpy.da.SearchCursor(line_feature_class, ["OID@", "SHAPE@"]) as cursor:
        for oid, shape in cursor:
            for part in shape:
                for vertex in part:
                    if vertex.equals(dangle_point):
                        return oid, vertex
    return None, None


import arcpy


def find_closest_feature(exclude_oid, search_features, search_point):
    """
    Find the closest feature to search_point in search_features, excluding the feature with exclude_oid.
    :param exclude_oid: OID of the feature to exclude from the search.
    :param search_features: List of feature classes to search within.
    :param search_point: The point geometry from which to find the nearest feature.
    :return: Tuple containing the geometry of the closest point and its OID.
    """
    # Create an in-memory feature layer excluding the feature with exclude_oid
    temp_layer = "tempLayer"
    arcpy.MakeFeatureLayer_management(search_features, temp_layer)
    arcpy.SelectLayerByAttribute_management(
        temp_layer, "NEW_SELECTION", f"OBJECTID <> {exclude_oid}"
    )

    # Use Generate Near Table to find the closest feature
    near_table = arcpy.GenerateNearTable_analysis(
        search_point,
        temp_layer,
        "in_memory\\near_table",
        closest="ONLY",
        location="LOCATION",
        method="PLANAR",
    )

    # Fetch the results from the near table
    with arcpy.da.SearchCursor(near_table, ["NEAR_X", "NEAR_Y", "NEAR_FID"]) as cursor:
        for row in cursor:
            closest_point = arcpy.Point(row[0], row[1])
            closest_fid = row[2]
            return closest_point, closest_fid
    return None, None


def calculate_extension_direction_and_distance(vertex, target_point):
    """
    Calculate the direction and distance from the vertex to the target_point.
    """
    dx = target_point.X - vertex.X
    dy = target_point.Y - vertex.Y
    distance = sqrt(dx**2 + dy**2)
    angle = atan2(dy, dx)
    return angle, distance


def extend_line_to_point(line, point, extension_distance):
    """
    Extends a line geometry towards a point by a specified distance.
    """
    # Calculate bearing from line's end to point
    line_end = line.lastPoint
    dy = point.Y - line_end.Y
    dx = point.X - line_end.X
    angle = atan2(dy, dx)

    # Calculate new end point based on bearing and distance
    new_x = line_end.X + (extension_distance * cos(angle))
    new_y = line_end.Y + (extension_distance * sin(angle))
    new_point = arcpy.Point(new_x, new_y)

    # Create new line by appending new point to existing line
    new_line_points = arcpy.Array([line.firstPoint, line.lastPoint, new_point])
    extended_line = arcpy.Polyline(new_line_points, line.spatialReference)

    return extended_line


def extend_line_vertex(
    line_feature_class, line_oid, distance, vertex_to_extend, extend_to_point
):
    """
    Extend the specified vertex of the line with line_oid in line_feature_class towards extend_to_point.
    """
    # Fetch the line geometry
    with arcpy.da.UpdateCursor(
        line_feature_class, ["SHAPE@"], f"OBJECTID = {line_oid}"
    ) as cursor:
        for row in cursor:
            line_geom = row[0]
            # Assuming extend_to_point is the target geometry to extend towards
            # You may calculate the extension distance based on specific logic
            extended_line = extend_line_to_point(line_geom, extend_to_point, distance)
            row[0] = extended_line
            cursor.updateRow(row)


if __name__ == "__main__":
    main()
