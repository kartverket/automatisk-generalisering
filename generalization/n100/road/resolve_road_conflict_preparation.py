# Libraries

import arcpy
import numpy as np
import os

from tqdm import tqdm

arcpy.env.overwriteOutput = True

from composition_configs import core_config, logic_config
from constants.n100_constants import FieldNames, MediumAlias
from custom_tools.general_tools import custom_arcpy
from custom_tools.generalization_tools.road.dissolve_with_intersections import (
    DissolveWithIntersections,
)
from file_manager import WorkFileManager
from file_manager.n100.file_manager_roads import Road_N100
from generalization.n100.road.dam import get_endpoints
from input_data import input_n50, input_n100

# Variables

EPS = 1e-9  # [m]
BUFFER_DIST = 60  # [m]
LENGTH_TOLERANCE = 10  # [m]

# Functions


def split_polyline_featureclass(
    input_fc: str,
    dissolve_fc: str,
    split_fc: str,
    output_fc: str,
    interval: float = 500.0,
) -> None:
    """
    Divides all the polylines in input_fc into pieces of x meters equal intervall,
    and stores the new geometries in an own output folder.

    Args:
        input_fc (str): The input polylines
        dissolve_fc (str): Layer for dissolved features
        split_fc (str): Layer for the divided geometries
        output_fc (str): Where to store the final single part output geometries
        intervall (float, optional): The split intervall, default: 500 m
    """
    # Fetch fields
    oid_fields = arcpy.Describe(input_fc).OIDFieldName
    join_fields = [
        f.name for f in arcpy.ListFields(input_fc) if f.type not in ("OID", "Geometry")
    ]

    attr_dict = {}
    read_fields = [oid_fields] + join_fields
    with arcpy.da.SearchCursor(input_fc, read_fields) as cursor:
        for row in cursor:
            oid = row[0]
            values = row[1:]
            attr_dict[oid] = dict(zip(join_fields, values))

    # Dissolve input features
    arcpy.management.Dissolve(
        in_features=input_fc,
        out_feature_class=dissolve_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    # Ensure singlepart layers only
    single_in = r"in_memory/input_singlepart"
    if arcpy.Exists(single_in):
        arcpy.management.Delete(single_in)
    arcpy.management.MultipartToSinglepart(
        in_features=dissolve_fc, out_feature_class=single_in
    )

    # Create the divide layer
    split_gdb = os.path.dirname(split_fc)
    split_name = os.path.basename(split_fc)
    if arcpy.Exists(split_fc):
        arcpy.management.Delete(split_fc)
    desc = arcpy.Describe(single_in)
    spatial_ref = desc.spatialReference
    has_z = "ENABLED" if desc.hasZ else "DISABLED"
    has_m = "ENABLED" if desc.hasM else "DISABLED"
    arcpy.management.CreateFeatureclass(
        out_path=split_gdb,
        out_name=split_name,
        geometry_type="POLYLINE",
        template="",
        has_m=has_m,
        has_z=has_z,
        spatial_reference=spatial_ref,
    )

    # Divide the geometries
    with arcpy.da.SearchCursor(
        single_in, ["SHAPE@"]
    ) as s_cursor, arcpy.da.InsertCursor(split_fc, ["SHAPE@"]) as i_cursor:
        for s_row in s_cursor:
            geom = s_row[0]
            if geom is None:
                # Needs a valid geometry
                continue
            total_len = geom.length
            if total_len <= interval:
                # If the geometry is shorter than the limit, just keep it
                i_cursor.insertRow([geom])
            else:
                # Otherwise -> Split it
                n_full = int(total_len // interval)
                pos = 0.0
                for _ in range(n_full):
                    seg = geom.segmentAlongLine(pos, pos + interval, False)
                    i_cursor.insertRow([seg])
                    pos += interval
                # The rest of the geometry
                if pos < total_len:
                    seg = geom.segmentAlongLine(pos, total_len, False)
                    i_cursor.insertRow([seg])

    # Clean up
    if arcpy.Exists(single_in):
        arcpy.management.Delete(single_in)

    # Spatial join to keep attributes
    fm = arcpy.FieldMappings()
    fm.addTable(split_fc)

    # Fill mapping with attributes
    for fld in join_fields:
        fmap = arcpy.FieldMap()
        fmap.addInputField(input_fc, fld)

        out_field = fmap.outputField
        out_field.name = fld
        out_field.aliasName = fld
        fmap.outputField = out_field
        fm.addFieldMap(fmap)

    # Performe spatial join
    joined_temp = r"in_memory/split_joined"
    if arcpy.Exists(joined_temp):
        arcpy.management.Delete(joined_temp)

    arcpy.analysis.SpatialJoin(
        target_features=split_fc,
        join_features=input_fc,
        out_feature_class=joined_temp,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
        field_mapping=fm,
    )

    # Perform multipart to singlepart for final layer
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)
    arcpy.management.MultipartToSinglepart(
        in_features=joined_temp,
        out_feature_class=output_fc,
    )


def creafte_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used during
    the process of snapping road points in water to the buffer edge.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    dissolved_fc = wfm.build_file_path(file_name="dissolved_roads", file_type="gdb")
    singlepart_fc = wfm.build_file_path(file_name="singlepart_roads", file_type="gdb")
    simplified_fc = wfm.build_file_path(file_name="simplified_fc", file_type="gdb")
    water_fc = wfm.build_file_path(file_name="water_fc", file_type="gdb")
    other_area_fc = wfm.build_file_path(file_name="other_area_fc", file_type="gdb")
    area_fc = wfm.build_file_path(file_name="area_fc", file_type="gdb")
    water_buffer_fc = wfm.build_file_path(file_name="water_buffer_fc", file_type="gdb")
    other_area_dissolved_fc = wfm.build_file_path(
        file_name="other_area_dissolved_fc", file_type="gdb"
    )
    point_fc = wfm.build_file_path(file_name="road_points", file_type="gdb")
    area_line_fc = wfm.build_file_path(file_name="area_line_fc", file_type="gdb")
    point_water_fc = wfm.build_file_path(
        file_name="road_points_in_water", file_type="gdb"
    )
    water_outline_fc = wfm.build_file_path(
        file_name="water_outline_fc", file_type="gdb"
    )
    smooth_fc = wfm.build_file_path(file_name="smooth_roads", file_type="gdb")

    return {
        "dissolved_fc": dissolved_fc,
        "singlepart_fc": singlepart_fc,
        "simplified_fc": simplified_fc,
        "water_fc": water_fc,
        "other_area_fc": other_area_fc,
        "area_fc": area_fc,
        "water_buffer_fc": water_buffer_fc,
        "other_area_dissolved_fc": other_area_dissolved_fc,
        "point_fc": point_fc,
        "area_line_fc": area_line_fc,
        "point_water_fc": point_water_fc,
        "water_outline_fc": water_outline_fc,
        "smooth_fc": smooth_fc,
    }


def run_dissolve_with_intersections(
    input_line_feature,
    output_processed_feature,
    dissolve_field_list,
):
    cfg = logic_config.DissolveInitKwargs(
        input_line_feature=input_line_feature,
        output_processed_feature=output_processed_feature,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Road_N100.data_preparation___intersections_root___n100_road.value
        ),
        dissolve_fields=dissolve_field_list,
        sql_expressions=[
            f" MEDIUM = '{MediumAlias.tunnel}'",
            f" MEDIUM = '{MediumAlias.bridge}'",
            f" MEDIUM = '{MediumAlias.on_surface}'",
        ],
    )
    DissolveWithIntersections(cfg).run()


def pre_processing(road_fc: str, files: dict) -> None:
    """
    Pre-processes the input data.

    Args:
        road_fc (str): input data as featureclass
        files (dict): Dictionary with the featureclasses to be created
    """
    run_dissolve_with_intersections(
        input_line_feature=road_fc,
        output_processed_feature=files["dissolved_fc"],
        dissolve_field_list=FieldNames.road_all_fields(),
    )
    arcpy.management.MultipartToSinglepart(
        in_features=files["dissolved_fc"],
        out_feature_class=files["singlepart_fc"],
    )

    arcpy.cartography.SimplifyLine(
        in_features=files["singlepart_fc"],
        out_feature_class=files["simplified_fc"],
        algorithm="POINT_REMOVE",
        tolerance="10 meters",
        error_option="RESOLVE_ERRORS",
    )


def data_selection(files: dict, area_selection: str) -> None:
    """
    Selects the relevant data and stores it in feature classes.

    Args:
        files (dict): Dictionary with the featureclasses to be created
        area_selection (str): An SQL-query for choice of area
    """
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=f"OBJTYPE IN ('Havflate', 'Innsjø', 'InnsjøRegulert')",
        output_name=files["water_fc"],
        selection_type="NEW_SELECTION",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.ArealdekkeFlate,
        expression=f"OBJTYPE NOT IN ('Havflate', 'Innsjø', 'InnsjøRegulert')",
        output_name=files["other_area_fc"],
        selection_type="NEW_SELECTION",
    )
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n100.AdminFlate,
        expression=area_selection,
        output_name=files["area_fc"],
        selection_type="NEW_SELECTION",
    )


def create_analysis_layers(files: dict) -> None:
    """
    Select data i prefered area, creates buffers, dissolves the data, and creates line features.

    Args:
        files (dict): Dictionary with the featureclasses to be created
    """
    water_lyr = "water_lyr"
    other_area_lyr = "other_area_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["water_fc"], out_layer=water_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=water_lyr,
        overlap_type="INTERSECT",
        select_features=files["area_fc"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.MakeFeatureLayer(
        in_features=files["other_area_fc"], out_layer=other_area_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=other_area_lyr,
        overlap_type="INTERSECT",
        select_features=files["area_fc"],
        selection_type="NEW_SELECTION",
    )
    arcpy.analysis.Buffer(
        in_features=water_lyr,
        out_feature_class=files["water_buffer_fc"],
        buffer_distance_or_field=BUFFER_DIST,
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="ALL",
    )
    arcpy.management.Dissolve(
        in_features=other_area_lyr,
        out_feature_class=files["other_area_dissolved_fc"],
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )
    arcpy.management.FeatureToLine(
        in_features=files["other_area_dissolved_fc"],
        out_feature_class=files["area_line_fc"],
    )
    delete_feature_layers([water_lyr, other_area_lyr])


def endpoints_of(geom: arcpy.Geometry, num: int = 3) -> tuple:
    """
    Returns rounded coordinates for the endpoints of the geom.

    Args:
        geom (arcpy.Geometry): The geometry to fetch endpoints
        num (int, optional): Number of wanted decimals, default: 3

    Returns:
        tuple: The X- and Y-coordinate of the endpoints to the geometry
    """
    s, e = get_endpoints(geom)
    s, e = s.firstPoint, e.firstPoint
    if num is None:
        # If num is None we want the original data without the round(...) operation
        return (s.X, s.Y), (e.X, e.Y)
    # Otherwise round to the desired number of decimals, default = 3
    return (round(s.X, num), round(s.Y, num)), (round(e.X, num), round(e.Y, num))


def collect_important_points(files: dict) -> set:
    """
    Collects all points in junctions or important passages or connections that mus be kept.

    Args:
        files (dict): Dictionary with the featureclasses to be created

    Returns:
        set: A set of point coordinates with points that should not be moved
    """
    road_keep_lyr = "road_keep_lyr"
    points_to_keep = set()
    arcpy.management.MakeFeatureLayer(
        in_features=files["simplified_fc"],
        out_layer=road_keep_lyr,
        where_clause="medium = 'L' OR medium = 'U' OR typeveg = 'bilferje'",
    )
    with arcpy.da.SearchCursor(road_keep_lyr, ["SHAPE@"]) as search_cursor:
        for row in search_cursor:
            geom = row[0]
            s, e = endpoints_of(geom, num=6)
            points_to_keep.add(s)
            points_to_keep.add(e)
    delete_feature_layers([road_keep_lyr])
    return points_to_keep


def points_roads_near_water(files: dict) -> None:
    """
    Collects every points for roads close to water bodies.

    Args:
        files (dict): Dictionary with the featureclasses to be created
    """
    road_lyr = "road_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["simplified_fc"],
        out_layer=road_lyr,
        where_clause="medium = 'T' AND typeveg <> 'bilferje'",
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=road_lyr,
        overlap_type="INTERSECT",
        select_features=files["water_buffer_fc"],
        selection_type="SUBSET_SELECTION",
    )

    # Collect road points from these instances that are close to waterbodies
    arcpy.management.FeatureVerticesToPoints(
        in_features=road_lyr, out_feature_class=files["point_fc"], point_location="ALL"
    )
    delete_feature_layers([road_lyr])


def prepare_attributes(files: dict) -> tuple[str]:
    """
    Creates new attributes and sets default values.

    Args:
        files (dict): Dictionary with the featureclasses to be created

    Returns:
        tuple[str]: The field names used for later queries
    """
    in_water_field = "IN_WATER"
    narrow_field = "IN_NARROW"
    field_names = [f.name for f in arcpy.ListFields(files["point_fc"])]
    if in_water_field not in field_names:
        arcpy.management.AddField(
            in_table=files["point_fc"], field_name=in_water_field, field_type="SHORT"
        )
        field_names.append(in_water_field)
    if narrow_field not in field_names:
        arcpy.management.AddField(
            in_table=files["point_fc"], field_name=narrow_field, field_type="SHORT"
        )
        field_names.append(narrow_field)

    arcpy.management.CalculateField(
        in_table=files["point_fc"],
        field=in_water_field,
        expression=0,
        expression_type="PYTHON3",
    )  # 1 = in water, 0 = not in water
    arcpy.management.CalculateField(
        in_table=files["point_fc"],
        field=narrow_field,
        expression=0,
        expression_type="PYTHON3",
    )  # 1 = narrow area, 0 = not narrow area
    return in_water_field, narrow_field


def is_narrow(pnt_fc: str, area_fc: str, narrow_field: str) -> None:
    """
    Calculates whether or not a point is located on a narrow part of the ground and
    updates the attribute from 0 (not) to 1 if it is located in a narrow area.

    Args:
        pnt_fc (str): Path to the featureclass with all the point data
        area_fc (str): Path to the featureclass with the bounding lines for ground area
        narrow_field (str): The field name of the attribute describing narrow areas or not
    """
    area_items = []
    with arcpy.da.SearchCursor(area_fc, ["SHAPE@"]) as sc:
        for row in sc:
            g = row[0]
            env = g.extent
            area_items.append((g, env.XMin, env.YMin, env.XMax, env.YMax))

    arcpy.analysis.Near(
        in_features=pnt_fc,
        near_features=area_fc,
        search_radius=50,
        location="LOCATION",
        distance_unit="Meters",
    )

    total = int(arcpy.management.GetCount(pnt_fc).getOutput(0))

    with arcpy.da.UpdateCursor(
        pnt_fc, ["SHAPE@", "NEAR_DIST", "NEAR_X", "NEAR_Y", narrow_field]
    ) as update_cursor:
        for geom, dist, x, y, _ in tqdm(
            update_cursor,
            total=total,
            desc="Updating narrow attribute",
            colour="yellow",
            leave=False,
        ):
            if dist == -1:
                continue
            if dist > BUFFER_DIST * 1.5:
                continue
            if x == None or y == None:
                continue

            cx, cy = geom.centroid.X, geom.centroid.Y
            near_pt = arcpy.PointGeometry(arcpy.Point(x, y), geom.spatialReference)

            vx = near_pt.centroid.X - cx
            vy = near_pt.centroid.Y - cy
            norm = np.hypot(vx, vy)

            if norm < EPS:
                continue

            ux, uy = -vx / norm, -vy / norm

            line_len = max(BUFFER_DIST * 1.5, norm * 2.0, 50.0)

            p0 = arcpy.Point(cx - ux * line_len, cy - uy * line_len)
            p1 = arcpy.Point(cx + ux * line_len, cy + uy * line_len)
            line = arcpy.Polyline(arcpy.Array([p0, p1]), geom.spatialReference)

            l_env = line.extent
            margin = 0.000001
            l_xmin, l_ymin, l_xmax, l_ymax = (
                l_env.XMin - margin,
                l_env.YMin - margin,
                l_env.XMax + margin,
                l_env.YMax + margin,
            )

            best_distance = np.inf
            for area_geom, axmin, aymin, axmax, aymax in area_items:
                if (
                    (axmax < l_xmin)
                    or (axmin > l_xmax)
                    or (aymax < l_ymin)
                    or (aymin > l_ymax)
                ):
                    continue

                inter = line.intersect(area_geom, 1)  # 1 = point

                if inter == None:
                    continue

                category = inter.type

                if category.lower() == "multipoint":
                    parts = list(inter)
                elif category.lower() == "point":
                    parts = [inter]
                else:
                    continue

                for point in parts:
                    if point == None:
                        continue
                    dx = point.X - cx
                    dy = point.Y - cy
                    dot = dx * vx + dy * vy

                    if dot < -EPS:
                        dist_ex = np.hypot(dx, dy)
                        if dist_ex <= BUFFER_DIST + EPS:
                            if dist + dist_ex < best_distance:
                                best_distance = dist + dist_ex

            if best_distance < LENGTH_TOLERANCE:
                update_cursor.updateRow([geom, dist, x, y, 1])


def estimate_attribute_values(
    files: dict, in_water_field: str, narrow_field: str
) -> None:
    """
    Calculates whether or not the different road points are located in water and
    or narrow areas before storing the points in a new point featureclass.

    Args:
        files (dict): Dictionary with the featureclasses to be created
        in_water_field (str): Field name for the water attribute
        narrow_field (str): Field name for the narrow attribute
    """
    point_lyr = "road_points_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["point_fc"], out_layer=point_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=point_lyr,
        overlap_type="INTERSECT",
        select_features=files["water_buffer_fc"],
        selection_type="NEW_SELECTION",
    )
    arcpy.management.CalculateField(
        in_table=point_lyr,
        field=in_water_field,
        expression=1,
        expression_type="PYTHON3",
    )

    area_lyr = "area_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["area_line_fc"], out_layer=area_lyr
    )

    is_narrow(point_lyr, area_lyr, narrow_field)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=point_lyr, selection_type="CLEAR_SELECTION"
    )
    arcpy.management.CopyFeatures(
        in_features=point_lyr, out_feature_class=files["point_water_fc"]
    )

    delete_feature_layers([point_lyr, area_lyr])


def create_movement_mapping(
    files: dict, in_water_field: str, narrow_field: str, points_to_keep: set
) -> tuple[set, dict]:
    """
    Locates points that should be moved and creates a mapping between current and new coordinates.

    Args:
        files (dict): Dictionary with the featureclasses to be created
        in_water_field (str): Field name for the water attribute
        narrow_field (str): Field name for the narrow attribute
        points_to_keep (set): A set containing critical points that should not be moved

    Returns:
        set: A set containing the OID for every road having a point that should be moved
        dict: A dictionary with the mapping between current and new coordinates
    """
    water_point_lyr = r"water_point_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["point_water_fc"], out_layer=water_point_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=water_point_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"{in_water_field} = 1 AND {narrow_field} = 0",
    )

    arcpy.management.FeatureToLine(
        in_features=files["water_buffer_fc"],
        out_feature_class=files["water_outline_fc"],
    )

    arcpy.analysis.Near(
        in_features=water_point_lyr,
        near_features=files["water_outline_fc"],
        search_radius=BUFFER_DIST * 1.2,
        location="LOCATION",
        angle="NO_ANGLE",
    )

    road_oids = set()
    mapping = {}

    with arcpy.da.SearchCursor(
        water_point_lyr, ["SHAPE@XY", "ORIG_FID", "NEAR_X", "NEAR_Y"]
    ) as search_cursor:
        for xy, orig_oid, nx, ny in search_cursor:
            if nx == None or ny == None:
                continue
            if nx == -1 or ny == -1:
                continue
            road_oids.add(orig_oid)

            key = (round(xy[0], 6), round(xy[1], 6))
            if key in points_to_keep:
                continue
            value = (round(nx, 6), round(ny, 6))

            mapping[key] = value

    delete_feature_layers([water_point_lyr])

    return road_oids, mapping


def update_road_geometries(files: dict, road_oids: set, mapping: dict) -> None:
    """
    Updates the road geometries with new point coordinates moved away from water bodies.

    Args:
        files (dict): Dictionary with the featureclasses to be created
        road_oids (set): Set containing the OID for every road having a point that should be moved
        mapping (dict): Dictionary with the mapping between current and new coordinates
    """
    roads_to_edit = r"roads_to_edit_lyr"
    oids = ",".join(str(OID) for OID in road_oids)
    sql = f"OBJECTID IN ({oids})"
    arcpy.management.MakeFeatureLayer(
        in_features=files["simplified_fc"], out_layer=roads_to_edit, where_clause=sql
    )

    total = int(arcpy.management.GetCount(roads_to_edit).getOutput(0))

    with arcpy.da.UpdateCursor(roads_to_edit, ["OID@", "SHAPE@"]) as update_cursor:
        for oid, geom in tqdm(
            update_cursor,
            total=total,
            desc="Edit road geometries in water",
            colour="yellow",
            leave=False,
        ):
            parts = []
            for part in tqdm(
                geom, desc="Editing geometries", colour="yellow", leave=False
            ):
                points = []
                prev_x, prev_y = None, None
                for pt in part:
                    if pt is None:
                        continue
                    px, py = pt.X, pt.Y
                    mapped = mapping.get((round(px, 6), round(py, 6)))
                    if mapped:
                        nx, ny = mapped
                        new_pt = arcpy.Point(nx, ny)
                    else:
                        new_pt = arcpy.Point(px, py)
                    if prev_x is None or (
                        abs(new_pt.X - prev_x) > EPS or abs(new_pt.Y - prev_y) > EPS
                    ):
                        points.append(new_pt)
                        prev_x, prev_y = new_pt.X, new_pt.Y
                if len(points) >= 2:
                    parts.append(arcpy.Array(points))
            if parts:
                new_geom = arcpy.Polyline(
                    arcpy.Array(parts), spatial_reference=geom.spatialReference
                )
                update_cursor.updateRow([oid, new_geom])


def delete_feature_layers(layers: list) -> None:
    for lyr in layers:
        if arcpy.Exists(lyr):
            arcpy.management.Delete(lyr)


def remove_road_points_in_water(
    road_fc: str, output_fc: str, area_selection: str
) -> None:
    """
    Moves vertices from road_fc that are located within a specific value from water, and prepares the
    data for Resolve Road Conflict by dissolving, creating singlepart objects and smoothening the road
    data. Road points located on bridges, tunnels, ferry lines or narrow ground areas are not moved.

    Args:
        road_fc (str): The road input feature class
        output_fc (str): Path to the new feature class that should contain the modified output data
        area_selection (str): A SQL-query selecting the prefered area
    """
    working_fc = Road_N100.road_cleaning__n100_road.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = creafte_wfm_gdbs(wfm=wfm)

    pre_processing(road_fc=road_fc, files=files)
    data_selection(files=files, area_selection=area_selection)
    create_analysis_layers(files=files)

    points_to_keep = collect_important_points(files=files)

    points_roads_near_water(files=files)

    in_water_field, narrow_field = prepare_attributes(files=files)

    estimate_attribute_values(
        files=files, in_water_field=in_water_field, narrow_field=narrow_field
    )

    road_oids, mapping = create_movement_mapping(
        files=files,
        in_water_field=in_water_field,
        narrow_field=narrow_field,
        points_to_keep=points_to_keep,
    )

    update_road_geometries(files=files, road_oids=road_oids, mapping=mapping)

    arcpy.cartography.SmoothLine(
        in_features=files["simplified_fc"],
        out_feature_class=files["smooth_fc"],
        algorithm="PAEK",
        tolerance="300 meters",
        error_option="RESOLVE_ERRORS",
        in_barriers=[
            Road_N100.data_preparation___water_feature_outline___n100_road.value,
            Road_N100.data_selection___railroad___n100_road.value,
            Road_N100.data_preparation___country_boarder___n100_road.value,
        ],
    )

    arcpy.management.CopyFeatures(
        in_features=files["smooth_fc"], out_feature_class=output_fc
    )

    wfm.delete_created_files()
