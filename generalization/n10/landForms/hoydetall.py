# Libraries

import arcpy
import numpy as np
import os
import requests

arcpy.env.overwriteOutput = True

from collections import defaultdict
from tqdm import tqdm

from composition_configs import core_config
from constants.county_numbers import county_numbers
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.append_features import Append_Features
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landforms import Landform_N10
from input_data import input_n10, input_n50, input_n100, input_roads
from lxml import etree

# ========================
# Program
# ========================

"""
DOCUMENTATION:

==========================================
How to use this functionality properly
==========================================

1) Run this code to get the modified point layer (feature class)
2) Open the point feature class in ArcGIS Pro
3) Select the layer, go to 'Labeling' and turn it on
4) In 'Label Class' choose 'Field' to be 'HØYDE'
5) Select font, size and colour in 'Text Symbol'
6) Open the side panel for 'Label Placement' and do the following:
    - In 'Symbol': turn the 'Halo' of
    - In 'Position':
        * Set placement to 'Centered on point' and center on symbol
        * 'Orientation' should be 'Curved'
        * 'Rotation' should be set to rotate according to the 'ROTATION' field, 0 deg, Arithmetic and Straight
        * Turn of 'Keep label upright (may flip)' ## IMPORTANT ##
7) Convert the labels to annotations:
    - Right click on the layer and choose 'Convert Labels' and '... To Annotation'
    - Zoom the map to fit the layer area
    - Set scale to 10.000
    - Extent must be the same as the map (the leftmost choice)
    -> Run
8) Choose the 'Feature Outline Mask (Cartography Tool)' function:
    - Choose input layer to be the annotation layer
    - Set 'Margin' to x m (5 m)
    - 'Mask Kind' must be 'Exact'
    - 'Preserve small-sized features' must be turned on
    -> Run

Then you have annotations with masks in ladders with correct orientation and spacing.
"""


@timing_decorator
def main():
    """
    Main function to process landforms in order to generate contour annotations at N10 scale.
    """
    environment_setup.main()

    print("\nCreates contour annotations for landforms at N10 scale...\n")

    # 1) Setting up work file managers to take care of temporary and final files
    global_fc = Landform_N10.hoydetall_global__n10_landforms.value
    work_fc = Landform_N10.hoydetall__n10_landforms.value
    output_fc = Landform_N10.hoydetall_output__n10_landforms.value

    global_config = core_config.WorkFileConfig(root_file=global_fc)
    work_config = core_config.WorkFileConfig(root_file=work_fc)
    output_config = core_config.WorkFileConfig(root_file=output_fc)

    global_wfm = WorkFileManager(config=global_config)
    work_wfm = WorkFileManager(config=work_config)
    output_wfm = WorkFileManager(config=output_config)

    out_of_bound_fc = Landform_N10.hoydetall_out_of_bounds_areas__n10_landforms.value
    annotation_contour_fc = (
        Landform_N10.hoydetall_annotation_contours__n10_landforms.value
    )
    valid_contour_fc = Landform_N10.hoydetall_valid_contours__n10_landforms.value
    point_1km_fc = Landform_N10.hoydetall_point_1km__n10_landforms.value

    # 2) Create temporary files
    global_files = create_global_wfm_gdbs(wfm=global_wfm)
    work_files = create_work_wfm_gdbs(wfm=work_wfm)

    # 3) Fetch data globally
    if not arcpy.Exists(out_of_bound_fc):
        if not arcpy.Exists(annotation_contour_fc):
            # 3.1) Contours, buildings, land use, railroad and roads
            fetch_data(files=global_files)
    else:
        print(
            "\nOut of bounds areas and annotation contours are already stored, skips to next.\n"
        )
    if not arcpy.Exists(out_of_bound_fc):
        # 3.2) Annotations
        fetch_annotations_to_avoid(files=global_files)
        # 3.3) Merge out of bounds buffers
        collect_out_of_bounds_areas(files=global_files, save_fc=out_of_bound_fc)
    else:
        print("\nOut of bounds areas are already stored, skips to next.\n")

    # 4) Fetch index countours
    if not arcpy.Exists(annotation_contour_fc):
        get_annotation_contours(files=global_files, save_fc=annotation_contour_fc)
    else:
        print("\nAnnotation contours are already stored, skips to next.\n")

    global_wfm.delete_created_files()

    # 5) Erase OB from contours
    if not arcpy.Exists(valid_contour_fc):
        find_valid_contours(
            contour_fc=annotation_contour_fc,
            erase_fc=out_of_bound_fc,
            out_fc=valid_contour_fc,
        )
    else:
        print("\nValid contours are already identified, skips to next.\n")

    # 6) Create points every 1000 m along the index contours
    if not arcpy.Exists(point_1km_fc):
        create_points_along_line(contour_fc=annotation_contour_fc, save_fc=point_1km_fc)
    else:
        print("\nPoints are already generated, skips to next.\n")

    # 7) Fetch search area(s)
    county = None  # If None = whole Norway, otherwise per county
    municipalities = get_municipality_names(county=county)
    print(f"\nNumber of municipalities to process: {len(municipalities)}\n")

    if county:
        print(
            "\nMunicipalities:\n\t- " + "\n\t- ".join(map(str, municipalities)) + "\n"
        )

    # "Backlog" to store processed municipalities
    path = "generalization/n10/landForms/processed_municipalities.txt"
    seen_municipalities = read_file(path=path)

    # 8) Iterate through each municipality and store points for each
    for i, municipality in enumerate(municipalities):
        space = "   " if i+1 < 10 else ("  " if i+1 < 100 else " ")
        if municipality in seen_municipalities:
            print(f"{i+1}{space}- {municipality} - SKIPS")
            continue

        print(f"{i+1}{space}- {municipality} - PROCESSING")

        # 8.1) Select municipality polygon for clip
        select_area(work_files["area"], municipality)

        # 8.2) Build ladders in unique layer
        ladders = create_ladders(
            points_fc=point_1km_fc,
            contours_fc=annotation_contour_fc,
            work_files=work_files,
        )
        ladders = remove_multiple_points_for_medium_contours(
            files=work_files, ladders=ladders
        )
        ladders = move_ladders_to_valid_area(
            files=work_files, valid_fc=valid_contour_fc, ladders=ladders
        )
        ladders = remove_dense_points(files=work_files, ladders=ladders)
        set_tangential_rotation(files=work_files)

        # 8.3) Store the final ladder points in unique feature class
        filename = municipality.replace(" ", "_").replace("-", "_")
        output = output_wfm.build_file_path(
            file_name=f"Kurvetall_{filename}", file_type="gdb"
        )

        arcpy.management.CopyFeatures(
            in_features=work_files["sel_points"],
            out_feature_class=output,
        )

        work_wfm.delete_created_files()

        write_to_file(path=path, name=municipality)
        seen_municipalities.add(municipality)
    
    delete_file(path=path)

    # 9) Combine all the created feature classes into one
    try:
        combine_feature_classes()
        #output_wfm.delete_created_files()
        print("Feature classes merged and output files representing each individual county are deleted.")
    except:
        print("Was not able to merge feature classes into one single.")

    print("\nContour annotations for landforms at N10 scale created successfully!\n")


# ========================
# Main functions
# ========================


@timing_decorator
def create_global_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates the temporarily files that are going to be used
    to create global files for further analysis with annotations.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    contours = wfm.build_file_path(file_name="contours", file_type="gdb")
    out_of_bounds_polygons = wfm.build_file_path(
        file_name="out_of_bounds_polygons", file_type="gdb"
    )
    out_of_bounds_polylines = wfm.build_file_path(
        file_name="out_of_bounds_polylines", file_type="gdb"
    )
    out_of_bounds_buffers = wfm.build_file_path(
        file_name="out_of_bounds_buffers", file_type="gdb"
    )
    out_of_bounds_annotations = wfm.build_file_path(
        file_name="out_of_bounds_annotations", file_type="gdb"
    )
    out_of_bounds_annotation_polygons = wfm.build_file_path(
        file_name="out_of_bounds_annotation_polygons", file_type="gdb"
    )
    out_of_bounds_points = wfm.build_file_path(
        file_name="out_of_bounds_points", file_type="gdb"
    )
    temporary_file = wfm.build_file_path(file_name="temporary_file", file_type="gdb")

    return {
        "contours": contours,
        "out_of_bounds_polygons": out_of_bounds_polygons,
        "out_of_bounds_polylines": out_of_bounds_polylines,
        "out_of_bounds_buffers": out_of_bounds_buffers,
        "out_of_bounds_annotations": out_of_bounds_annotations,
        "out_of_bounds_annotation_polygons": out_of_bounds_annotation_polygons,
        "out_of_bounds_points": out_of_bounds_points,
        "temporary_file": temporary_file,
    }


@timing_decorator
def create_work_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of creating contour annotations.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    area = wfm.build_file_path(file_name="area", file_type="gdb")
    sel_points = wfm.build_file_path(file_name="sel_points", file_type="gdb")
    sel_contours = wfm.build_file_path(file_name="sel_contours", file_type="gdb")
    joined_contours = wfm.build_file_path(file_name="joined_contours", file_type="gdb")
    valid_clip = wfm.build_file_path(file_name="valid_clip", file_type="gdb")
    valid_dissolved = wfm.build_file_path(file_name="valid_dissolved", file_type="gdb")
    temp_joined = wfm.build_file_path(file_name="temp_joined", file_type="gdb")

    return {
        "area": area,
        "sel_points": sel_points,
        "sel_contours": sel_contours,
        "joined_contours": joined_contours,
        "valid_clip": valid_clip,
        "valid_dissolved": valid_dissolved,
        "temp_joined": temp_joined,
    }


@timing_decorator
def get_municipality_names(county: str = None) -> list:
    """
    Fetches the names of the municipalities inside
    a county using the Norwegian WFS service.

    Args:
        county (str): The name of the county to search inside

    Returns:
        list: A list of strings where all the strings represents
            municipality names inside the county
    """
    if county:
        county_num = county_numbers[county]

    url = (
        "https://wfs.geonorge.no/skwms1/wfs.administrative_enheter?"
        "service=WFS&version=2.0.0&request=GetFeature&"
        "typeNames=app:Kommune"
    )

    response = requests.get(url)
    response.raise_for_status()

    root = etree.fromstring(response.content)

    ns = {
        "app": "https://skjema.geonorge.no/SOSI/produktspesifikasjon/AdmEnheter/20240101",
        "gml": "http://www.opengis.net/gml/3.2",
    }

    municipalities = []

    for feature in root.findall(".//app:Kommune", ns):
        if county:
            municipality_el = feature.find("app:kommunenummer", ns)
            if municipality_el is None:
                continue

            municipality_number = municipality_el.text
            county_number = municipality_number[:2]

            if county_number == county_num:
                name_el = feature.find("app:kommunenavn", ns)
                if name_el is not None:
                    municipality = name_el.text
                    municipalities.append(municipality.split(" - ")[0])
        else:
            name_el = feature.find("app:kommunenavn", ns)
            if name_el is not None:
                municipality = name_el.text
                municipalities.append(municipality.split(" - ")[0])

    return municipalities


@timing_decorator
def fetch_data(files: dict, area: list = None) -> None:
    """
    Collects relevant data and clips it to desired area if required.

    Args:
        files (dict): Dictionary with all the working files
        area (list, optional): List of municipality name(s) to clip data to (defaults to None)
    """
    # 1) Defining layers to use
    layers = [
        ("contour_lyr", input_n10.Contours, None, files["contours"], False),
        (
            "building_lyr",
            input_n10.Buildings,
            None,
            files["out_of_bounds_polygons"],
            False,
        ),
        (
            "land_use_lyr",
            input_n50.ArealdekkeFlate,
            "OBJTYPE IN ('BymessigBebyggelse','ElvBekk','FerskvannTørrfall','Havflate','Industriområde','Innsjø','InnsjøRegulert','Tettbebyggelse')",
            files["out_of_bounds_polygons"],
            True,
        ),
        ("railroad_lyr", input_n50.Bane, None, files["out_of_bounds_polylines"], False),
        (
            "road_lyr",
            input_roads.road_output_1,
            None,
            files["out_of_bounds_polylines"],
            True,
        ),
    ]

    # 2) Creating feature layers
    for name, src, sql, *_ in layers:
        arcpy.management.MakeFeatureLayer(src, name, sql)

    # 3) Defining clip area, if a chosen area exists
    clip_lyr = None
    if area:
        clip_lyr = "area_lyr"
        arcpy.management.MakeFeatureLayer(input_n100.AdminFlate, clip_lyr)
        vals = ",".join(f"'{v}'" for v in area)
        arcpy.management.SelectLayerByAttribute(
            clip_lyr, "NEW_SELECTION", f"NAVN IN ({vals})"
        )

    # 4) Process each layer
    for lyr_name, _, _, out_fc, append in tqdm(
        layers, desc="Fetching data", colour="yellow", leave=False
    ):
        process(files, lyr_name, out_fc, clip=clip_lyr, append=append)

    # 5) Prepare out-of-bounds points
    if clip_lyr:
        arcpy.analysis.Clip(
            in_features=input_n50.HoydePunkt,
            clip_features=clip_lyr,
            out_feature_class=files["temporary_file"],
        )
    else:
        arcpy.management.CopyFeatures(
            in_features=input_n50.HoydePunkt, out_feature_class=files["temporary_file"]
        )
    arcpy.analysis.Buffer(
        in_features=files["temporary_file"],
        out_feature_class=files["out_of_bounds_points"],
        buffer_distance_or_field="30 Meters",
    )


@timing_decorator
def fetch_annotations_to_avoid(files: dict, area: list = None) -> None:
    """
    Fetches annotations that should be avoided when placing new contour annotations.

    Args:
        files (dict): Dictionary with all the working files
        area (list, optional): List of municipality name(s) to clip data to (defaults to None)
    """
    # 1) Defining layers to use
    annotation_layers = input_n10.annotations  # list of all annotation paths

    layers = []

    for i, anno in enumerate(annotation_layers):
        layers.append(
            (
                f"annotation_lyr_{i}",
                anno,
                files["out_of_bounds_annotations"],
            )
        )

    # 2) Creating feature layers
    for name, src, _ in layers:
        arcpy.management.MakeFeatureLayer(src, name)

    # 3) Defining clip area, if a chosen area exists
    clip_lyr = None
    if area:
        clip_lyr = "area_lyr"
        arcpy.management.MakeFeatureLayer(input_n100.AdminFlate, clip_lyr)
        vals = ",".join(f"'{v}'" for v in area)
        arcpy.management.SelectLayerByAttribute(
            clip_lyr, "NEW_SELECTION", f"NAVN IN ({vals})"
        )

    # 4) Process each layer and add the data in one feature class
    for lyr_name, _, out_fc in tqdm(
        layers, desc="Fetching annotations to avoid", colour="yellow", leave=False
    ):
        tmp = files["temporary_file"]
        if arcpy.Exists(files["temporary_file"]):
            arcpy.management.Delete(files["temporary_file"])
        if clip_lyr:
            arcpy.analysis.PairwiseClip(
                in_features=lyr_name, clip_features=clip_lyr, out_feature_class=tmp
            )
        else:
            arcpy.management.CopyFeatures(in_features=lyr_name, out_feature_class=tmp)
        if arcpy.Exists(out_fc):
            arcpy.management.Append(inputs=tmp, target=out_fc, schema_type="NO_TEST")
        else:
            arcpy.management.CopyFeatures(in_features=tmp, out_feature_class=out_fc)

    # 5) Fetch the bounding polygons of the annotations and store them in a separate feature class as polygons
    insert_fc = files["out_of_bounds_annotation_polygons"]
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(insert_fc),
        out_name=os.path.basename(insert_fc),
        geometry_type="POLYGON",
    )
    with arcpy.da.InsertCursor(insert_fc, ["SHAPE@"]) as insert_cur:
        with arcpy.da.SearchCursor(
            files["out_of_bounds_annotations"], ["SHAPE@"]
        ) as search_cur:
            for row in search_cur:
                geom = row[0]
                if geom is None:
                    continue
                insert_cur.insertRow([geom])


@timing_decorator
def collect_out_of_bounds_areas(files: dict, save_fc: str) -> None:
    """
    Creates buffer around lines and dissolves all polygons without creating multiparts.

    Args:
        files (dict): Dictionary with all the working files
        save_fc (str): Path to the feature class to store the final output
    """
    arcpy.analysis.Buffer(
        in_features=files["out_of_bounds_polylines"],
        out_feature_class=files["out_of_bounds_buffers"],
        buffer_distance_or_field="20 Meters",
        line_side="FULL",
        line_end_type="ROUND",
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_buffers"],
        target=files["out_of_bounds_polygons"],
        schema_type="TEST_AND_SKIP",
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_points"],
        target=files["out_of_bounds_polygons"],
        schema_type="TEST_AND_SKIP",
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_annotation_polygons"],
        target=files["out_of_bounds_polygons"],
        schema_type="TEST_AND_SKIP",
    )
    arcpy.analysis.Buffer(
        in_features=files["out_of_bounds_polygons"],
        out_feature_class=save_fc,
        buffer_distance_or_field="20 Meters",
    )


@timing_decorator
def get_annotation_contours(files: dict, save_fc: str) -> None:
    """
    Collect index contours with the specific height intervall.

    Args:
        files (dict): Dictionary with all the working files
        save_fc (str): Path to the feature class to store the final output
    """
    contours_lyr = "contours_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["contours"],
        out_layer=contours_lyr,
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=contours_lyr,
        selection_type="NEW_SELECTION",
        where_clause="MOD(HØYDE, 25) = 0",
    )

    arcpy.management.MultipartToSinglepart(
        in_features=contours_lyr,
        out_feature_class=save_fc,
    )


@timing_decorator
def find_valid_contours(contour_fc: str, erase_fc: str, out_fc: str) -> None:
    """
    Erases out of bounds areas from the contours so
    that only the valid parts of the contours remain.

    Args:
        contour_fc (str): Path to the feature class containing the contours
        erase_fc (str): Path to the feature class containing the areas to avoid
        out_fc (str): Path to the feature class to store the final output
    """
    arcpy.analysis.Erase(
        in_features=contour_fc, erase_features=erase_fc, out_feature_class=out_fc
    )


@timing_decorator
def create_points_along_line(
    contour_fc: str, save_fc: str, threshold: int = 1000
) -> None:
    """
    Creates a point every x m defined by the threshold.

    Args:
        files (dict): Dictionary with all the working files
        save_fc (str): Path to the feature class to store the final output
        threshold (int, optionally): Distance (m) between each new point (default: 1000)
    """
    length_tol = 1000
    contours_lyr = "contours_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=contour_fc,
        out_layer=contours_lyr,
        where_clause=f"Shape_Length > {length_tol}",
    )

    arcpy.management.GeneratePointsAlongLines(
        Input_Features=contours_lyr,
        Output_Feature_Class=save_fc,
        Point_Placement="DISTANCE",
        Distance=f"{threshold} Meters",
        Include_End_Points="NO_END_POINTS",
        Distance_Method="GEODESIC",
    )


def create_ladders(points_fc: str, contours_fc: str, work_files: dict) -> dict:
    """
    Cluster the points using DBSCAN to sort the points into ladders.

    Args:
        points_fc (str): Path to the feature class containing the points
        contours_fc (str): Path to the feature class containing the contours
        work_files (dict): Dictionary with all the working files

    Returns:
        dict: A dictionary containing all the ladders, {cluster_id: [oid1, oid2, ...], ...}
    """
    join_fc = work_files["joined_contours"]

    work_points = work_files["sel_points"]
    work_contours = work_files["sel_contours"]

    # Setup
    setup = [(points_fc, work_points), (contours_fc, work_contours)]

    for fc, temp in setup:
        arcpy.analysis.PairwiseClip(
            in_features=fc, clip_features=work_files["area"], out_feature_class=temp
        )

    cluster_field = "CLUSTER_ID"
    height_field = "HØYDE"
    eps_distance = 250  # [m]

    # 1) Performe DBSCAN
    arcpy.management.AddField(
        in_table=work_points, field_name=cluster_field, field_type="LONG"
    )
    points = [
        (oid, pt, h)
        for oid, pt, h in arcpy.da.SearchCursor(
            work_points, ["OID@", "SHAPE@", "HØYDE"]
        )
    ]
    clusters = cluster_points(points=points, eps=eps_distance)

    # 2) Write cluster ID back to point
    cluster_id_map = {}
    for cid, cluster in enumerate(clusters):
        for oid in cluster:
            cluster_id_map[oid] = cid

    with arcpy.da.UpdateCursor(work_points, ["OID@", cluster_field]) as cur:
        for oid, _ in cur:
            cur.updateRow([oid, cluster_id_map[oid]])

    # 3) Find points of same height in same cluster and delete these
    cluster_groups = defaultdict(lambda: defaultdict(list))
    with arcpy.da.SearchCursor(
        work_points, ["OID@", cluster_field, height_field]
    ) as cur:
        for oid, cid, height in cur:
            cluster_groups[cid][height].append(oid)

    to_delete = set()
    for cid, height_dict in cluster_groups.items():
        for height, pts in height_dict.items():
            if len(pts) > 1:
                for p in pts[1:]:
                    to_delete.add(p)

    with arcpy.da.UpdateCursor(work_points, ["OID@"]) as cur:
        for row in cur:
            if row[0] in to_delete:
                cur.deleteRow()

    for cluster, height in cluster_groups.items():
        for oids in height.values():
            k = 0
            while k < len(oids):
                if oids[k] in to_delete:
                    oids.pop(k)
                else:
                    k += 1

    # 4) Performe spatial join to connect points with contours
    arcpy.analysis.SpatialJoin(
        target_features=work_contours,
        join_features=work_points,
        out_feature_class=join_fc,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # 5) Return the ladders
    result = defaultdict(list)
    for cid, height_dict in cluster_groups.items():
        for oids in height_dict.values():
            for oid in oids:
                result[cid].append(oid)

    return result


def remove_multiple_points_for_medium_contours(files: dict, ladders: dict) -> dict:
    """
    For contours shorter than 10 km, only the annotation
    in the longest ladder should be kept.

    Args:
        files (dict): Dictionary with all the working files
        ladders (dict): Dictionary with all the ladders, {ladder_id: [id1, id2, ...], ...}

    Returns:
        dict: Modified ladder overview
    """
    points_fc = files["sel_points"]
    contour_fc = files["joined_contours"]

    # 1) Find contours shorter than 10 km
    contour_to_points = defaultdict(list)

    with arcpy.da.SearchCursor(
        contour_fc,
        ["TARGET_FID", "JOIN_FID", "CLUSTER_ID"],
        where_clause="Shape_Length < 10000",
    ) as cur:
        for target, join, cluster in cur:
            contour_to_points[target].append((join, cluster))

    # 2) Find points to delete
    oids_to_delete = set()

    for info in contour_to_points.values():
        if len(info) == 1:
            continue
        longest = max(info, key=lambda x: len(ladders[x[1]]))
        keep_join = longest[0]
        for join_oid, cluster_id in info:
            if join_oid != keep_join:
                oids_to_delete.add(join_oid)
                ladders[cluster_id] = [
                    oid for oid in ladders[cluster_id] if oid != join_oid
                ]

    # 3) Delete points in the point layer
    if oids_to_delete:
        sql = f"OBJECTID IN ({','.join(map(str, oids_to_delete))})"
        with arcpy.da.UpdateCursor(points_fc, ["OID@"], sql) as cur:
            for _ in cur:
                cur.deleteRow()

    return ladders


def move_ladders_to_valid_area(files: dict, valid_fc: str, ladders: dict) -> dict:
    """
    Moves ladder points to valid positions along their associated contour lines.

    Workflow:
        1) Fetch the valid parts of the relevant contours to avoid out-of-bounds areas
        2) For each point, find the nearest valid location on its own contour,
           limited by a maximum allowed movement distance
        3) Keep points that can be moved; delete points that cannot
           (only one point per height per ladder)

    Args:
        files (dict): Paths to all working feature classes
        valid_fc (str): Path to the feature class containing the valid parts of the contours
        ladders (dict): Mapping of ladder IDs to lists of point OIDs,
                        e.g. {ladder_id: [oid1, oid2, ...]}

    Returns:
        dict: Updated ladder mapping with invalid points removed
    """

    max_movement = 1000  # [m]

    valid_clip_fc = files["valid_clip"]
    valid_dissolved_fc = files["valid_dissolved"]
    points_fc = files["sel_points"]

    # 1) Clip valid contours to specific area
    arcpy.analysis.PairwiseClip(
        in_features=valid_fc,
        clip_features=files["area"],
        out_feature_class=valid_clip_fc,
    )
    arcpy.management.Dissolve(
        in_features=valid_clip_fc,
        out_feature_class=valid_dissolved_fc,
        dissolve_field=["HØYDE"],
        multi_part="MULTI_PART",
    )
    arcpy.management.AddField(
        in_table=valid_dissolved_fc, field_name="contour_ID", field_type="LONG"
    )
    with arcpy.da.UpdateCursor(valid_dissolved_fc, ["contour_ID"]) as cur:
        for i, _ in enumerate(cur):
            cur.updateRow([i])

    # 2) Collect point and contour information
    heights = sorted({h for (h,) in arcpy.da.SearchCursor(points_fc, ["HØYDE"])})

    point_info = {
        oid: {"near_geom": None, "geom": geom, "height": h}
        for oid, geom, h in arcpy.da.SearchCursor(
            points_fc, ["OID@", "SHAPE@", "HØYDE"]
        )
    }

    contours_clipped = (
        {  # For valid contours: ID -> valid, dissolved, multipart geometry
            contour_id: geom
            for contour_id, geom in arcpy.da.SearchCursor(
                valid_dissolved_fc, ["contour_ID", "SHAPE@"]
            )
        }
    )

    clip_lyr = "clip_lyr"
    points_lyr = "points_lyr"
    temp_joined = files["temp_joined"]

    arcpy.management.MakeFeatureLayer(valid_dissolved_fc, clip_lyr)

    contours = {}  # Point ID -> valid, dissolved, multipart contour geometry

    for h in tqdm(
        heights,
        desc="Matching points with clipped contours",
        colour="yellow",
        leave=False,
    ):
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=clip_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"HØYDE = {h}",
        )

        arcpy.management.MakeFeatureLayer(
            in_features=points_fc, out_layer=points_lyr, where_clause=f"HØYDE = {h}"
        )

        arcpy.analysis.SpatialJoin(
            target_features=points_lyr,
            join_features=clip_lyr,
            out_feature_class=temp_joined,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_COMMON",
            match_option="CLOSEST",
        )

        for point_id, join_attr in arcpy.da.SearchCursor(
            temp_joined, ["Target_FID", "contour_ID"]
        ):
            contours[point_id] = contours_clipped[join_attr]

    # 3) Iterate through each ladder and fetch new geometries
    points_to_delete = set()

    for oids in tqdm(
        ladders.values(), desc="Moving ladders", colour="yellow", leave=False
    ):
        oids.sort(key=lambda oid: point_info[oid]["height"])
        accumulated = []
        for oid in oids:
            contour = contours.get(oid)
            if contour is None:
                points_to_delete.add(oid)
                continue

            pt_geom = point_info[oid]["geom"]

            prev_geom = (
                get_accumulated_movement(accumulated)
                if len(accumulated) > 0
                else pt_geom
            )

            nearest_point, *_ = contour.queryPointAndDistance(prev_geom)
            dist_to_orig = pt_geom.distanceTo(nearest_point)

            if dist_to_orig > max_movement:
                points_to_delete.add(oid)
                continue

            point_info[oid]["near_geom"] = nearest_point
            accumulated.append(nearest_point)

    # 4) Update point geometry or delete the point
    with arcpy.da.UpdateCursor(points_fc, ["OID@", "SHAPE@"]) as cur:
        for oid, _ in cur:
            if oid in points_to_delete:
                cur.deleteRow()
            else:
                if point_info[oid]["near_geom"] is None:
                    continue

                cur.updateRow([oid, point_info[oid]["near_geom"]])

    # 5) Update ladder list
    for ladder_id, oids in ladders.items():
        ladders[ladder_id] = [oid for oid in oids if oid not in points_to_delete]

    return ladders


def remove_dense_points(files: dict, ladders: dict) -> dict:
    """
    Remove points that are too close to each other along the same contour.

    Args:
        files (dict): Dictionary with all the working files
        ladders (dict): Dictionary with all the ladders, {ladder_id: [id1, id2, ...], ...}

    Returns:
        dict: Updated ladder list
    """
    points_fc = files["sel_points"]
    contour_fc = files["joined_contours"]

    points = {
        oid: geom for oid, geom in arcpy.da.SearchCursor(points_fc, ["OID@", "SHAPE@"])
    }

    # 1) Build contour mapping
    contour_to_points = defaultdict(list)
    contours = {}
    with arcpy.da.SearchCursor(
        contour_fc, ["SHAPE@", "TARGET_FID", "JOIN_FID", "CLUSTER_ID"]
    ) as cur:
        for geom, target, join, cluster in cur:
            if target not in contours:
                contours[target] = geom
                ladder_size = len(ladders[cluster])
            if join in points:
                contour_to_points[target].append(
                    {"oid": join, "geom": points[join], "ladder_size": ladder_size}
                )

    # 2) Detect the points that should be deleted
    tolerance = 1000  # [m]
    oids_to_delete = set()

    for contour_oid, pts in contour_to_points.items():
        contour_geom = contours[contour_oid]

        # Estimate distance along contour
        for p in pts:
            p["dist"] = contour_geom.measureOnLine(p["geom"])

        # Sort on distance
        pts.sort(key=lambda x: x["dist"])

        # Iterate through the points along the contour
        current = pts[0]
        for p in pts[1:]:
            dist_diff = p["dist"] - current["dist"]
            large_current = current["ladder_size"] >= 4
            large_new = p["ladder_size"] >= 4

            # Rules
            # 1: Both are large = keep both
            if large_current and large_new:
                current = p
            # 2: New is large, but old is short = delete old, keep new
            elif large_new and not large_current:
                oids_to_delete.add(current["oid"])
                current = p
            # 3: Both are small or new is small = use 2km rule
            elif dist_diff < tolerance:
                oids_to_delete.add(p["oid"])
            else:
                current = p

    # 3) Delete the points
    if oids_to_delete:
        sql = f"OBJECTID IN ({','.join(map(str, oids_to_delete))})"
        with arcpy.da.UpdateCursor(points_fc, ["OID@"], where_clause=sql) as cur:
            for _ in cur:
                cur.deleteRow()

    for ladder_id, oids in ladders.items():
        ladders[ladder_id] = [oid for oid in oids if oid not in oids_to_delete]

    return ladders


def set_tangential_rotation(files: dict) -> None:
    """
    Set ROTATION for each point so the label aligns with
    the contour line's tangent at that location.

    Approach:
        For each point:
            1) Find the contour line it belongs to (JOIN_FID)
            2) Measure the point's position along the line
            3) Extract a small segment around that position
            4) Compute tangent direction using atan2(dy, dx)
            5) Store the angle in ROTATION (ArcGIS format)

    Args:
        files (dict): Dictionary with all the working files.
    """

    points_fc = files["sel_points"]
    contour_fc = files["joined_contours"]

    # 1) Ensure ROTATION field exists
    if "ROTATION" not in [f.name for f in arcpy.ListFields(points_fc)]:
        arcpy.management.AddField(points_fc, "ROTATION", "DOUBLE")

    # 2) Build mapping: JOIN_FID -> contour geometry
    contour_by_join = {}
    with arcpy.da.SearchCursor(contour_fc, ["JOIN_FID", "SHAPE@"]) as cur:
        for join, geom in cur:
            contour_by_join[join] = geom

    # 3) Update tangent rotation for each point
    with arcpy.da.UpdateCursor(points_fc, ["OID@", "SHAPE@", "ROTATION"]) as cur:
        for oid, pt, _ in cur:

            if oid not in contour_by_join:
                continue

            line = contour_by_join[oid]

            # 3.1) Position along line
            m = line.measureOnLine(pt)
            if m is None:
                continue

            # 3.2) Small segment around the point (±10 m)
            m1 = max(0, m - 10)
            m2 = min(line.length, m + 10)
            seg = line.segmentAlongLine(m1, m2)

            # 3.3) Compute tangent direction
            start = seg.firstPoint
            end = seg.lastPoint
            dx = end.X - start.X
            dy = end.Y - start.Y

            tangent = np.degrees(np.arctan2(dy, dx)) % 360

            # 3.4) Store rotation
            cur.updateRow([oid, pt, tangent])


@timing_decorator
def combine_feature_classes() -> None:
    """
    Combines all the created feature classes into one.
    """
    file = Landform_N10.hoydetall_output__n10_landforms.value
    file = file.split("___")
    folder, name = file[0], file[1]

    folder_path = ""
    for part in folder.split("\\"):
        folder_path += f"{part}/"
        if ".gdb" in part:
            folder_path = folder_path[:-1]
            break

    file_structure = f"*{name}*"

    af = Append_Features(workspace=folder_path, output_fc=Landform_N10.hoydetall_landsdekkende__n10_landforms.value)

    af.append_features(file_name_structure=file_structure)


# ========================
# Helper functions
# ========================


def read_file(path: str) -> set:
    """
    Reads a file with processed municipalities and returns
    a set of strings with the municipality names.

    Args:
        path (str): The filepath

    Returns:
        set: A set of strings with the municipality names
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = set()
            for line in f.readlines():
                lines.add(line.replace("\n", ""))
            return lines
    except FileNotFoundError:
        print(f"File {path} not found.")
    except Exception as e:
        print(f"Something went wrong:\n{e}")
    return set()


def write_to_file(path: str, name: str) -> None:
    """
    Adds the name of a processed municipality to the file.

    Args:
        path (str): The filepath
        name (str): The name / string to add in the file
    """
    try:
        file_exists = os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if file_exists and os.path.getsize(path) > 0:
                f.write(f"\n{name}")
            else:
                f.write(name)
    except Exception as e:
        print(f"Something went wrong:\n{e}")


def delete_file(path: str) -> None:
    """
    Deletes a file at the given path if it exists.

    Args:
        path (str): The filepath to delete
    """
    try:
        os.remove(path)
        print(f"File {path} deleted.")
    except FileNotFoundError:
        print(f"File {path} not found.")
    except Exception as e:
        print(f"Something went wrong:\n{e}")


def process(
    files: dict, in_lyr: str, out_fc: str, clip: str = None, append: bool = False
) -> None:
    """
    Pre-processing function to clip or append data to a feature class.

    Args:
        files (dict): Dictionary with all the working files
        in_lyr (str): Input layer to process
        out_fc (str): Output feature class
        clip (str, optional): Feature class to use for clipping (defaults to None)
        append (bool, optional): Whether to append to existing feature class (defaults to False)
    """
    if clip:
        tmp = files["temporary_file"] if append else out_fc
        arcpy.analysis.PairwiseClip(in_lyr, clip, tmp)
        if append:
            arcpy.management.Append(tmp, out_fc, "NO_TEST")
    else:
        if append:
            arcpy.management.Append(in_lyr, out_fc, "NO_TEST")
        else:
            arcpy.management.CopyFeatures(in_lyr, out_fc)


def select_area(area_fc: str, area_name: str) -> None:
    """
    Select the polygon of a specific municipality
    and stores it in a feature class.

    Args:
        area_fc (str): Path to the feature class to store the polygon
        area_name (str): The name of the municipality
    """
    area_lyr = "area_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=input_n100.AdminFlate, out_layer=area_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=area_lyr,
        selection_type="NEW_SELECTION",
        where_clause=f"NAVN = '{area_name}'",
    )
    arcpy.management.CopyFeatures(in_features=area_lyr, out_feature_class=area_fc)


def cluster_points(points: list, eps: int) -> list:
    """
    Proper DBSCAN-like clustering.

    Args:
        points (list): [(oid, arcpy.Point, height), ...]
        eps (float): distance threshold

    Returns:
        list: list of clusters, each cluster is a list of OIDs
    """
    # Precompute coordinates
    coords = {oid: (pt.centroid.X, pt.centroid.Y) for oid, pt, _ in points}
    # oid -> height
    heights = {oid: h for oid, _, h in points}

    # Build grid index
    cell_size = eps
    grid = defaultdict(list)

    def cell_for(x, y):
        return (int(x // cell_size), int(y // cell_size))

    for oid, (x, y) in coords.items():
        cell = cell_for(x, y)
        grid[cell].append(oid)

    # Find neighbors using grid lookup
    neighbors = {oid: [] for oid, _, _ in points}

    for oid, (x, y) in coords.items():
        cx, cy = cell_for(x, y)

        # Check this + all 8-neighbors
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cell = (cx + dx, cy + dy)
                if cell not in grid:
                    continue
                for other in grid[cell]:
                    if other == oid:
                        continue
                    if heights[other] == heights[oid]:
                        continue
                    ox, oy = coords[other]
                    if (x - ox) ** 2 + (y - oy) ** 2 <= eps**2:
                        neighbors[oid].append(other)

    # Build clusters (BFS / DFS)
    visited = set()
    clusters = []

    for oid, _, _ in points:
        if oid in visited:
            continue

        cluster = []
        stack = [oid]

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            cluster.append(current)

            for n in neighbors[current]:
                if n not in visited:
                    stack.append(n)

        clusters.append(cluster)

    return clusters


def get_accumulated_movement(accumulated: list) -> arcpy.PointGeometry:
    """
    Returns the average point from a list of points.

    Args:
        accumulated (list): List of arcpy.PointGeometry

    Returns:
        arcpy.PointGeometry: The average point
    """
    xs = [p.centroid.X if hasattr(p, "centroid") else p.X for p in accumulated]
    ys = [p.centroid.Y if hasattr(p, "centroid") else p.Y for p in accumulated]

    avg_x = sum(xs) / len(xs)
    avg_y = sum(ys) / len(ys)

    return arcpy.PointGeometry(arcpy.Point(avg_x, avg_y))


# ========================

if __name__ == "__main__":
    #main()
    combine_feature_classes()
