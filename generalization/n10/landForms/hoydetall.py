# Libraries

import arcpy
import config
import numpy as np
import os
import re

arcpy.env.overwriteOutput = True

from tqdm import tqdm

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from env_setup.global_config import main_directory_name, object_hoyde, scale_n10
from file_manager import WorkFileManager
from file_manager.n10.file_manager_landforms import Landform_N10
from input_data import input_n10, input_n50, input_n100, input_roads

# ========================
# Program
# ========================


@timing_decorator
def main():
    """
    Main function to process landforms in order to generate contour annotations at N10 scale.
    """
    environment_setup.main()

    print("\nCreates contour annotations for landforms at N10 scale...\n")

    municipality = "Hole"
    folder = f"{config.output_folder}/{main_directory_name}/{scale_n10}"

    # Sets up work file manager and creates temporary files
    working_fc = Landform_N10.hoyde__n10_landforms.value
    work_config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=work_config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files, municipality=municipality)
    collect_out_of_bounds_areas(files=files)
    get_annotation_contours(files=files)
    process_tiles(files=files, folder=f"{folder}/{object_hoyde}")
    gdbs = merge_landform_annotations(
        folder_path=folder, out_anno=files["annotations"], out_mask=files["masks"]
    )
    delete_gdbs(gdbs=gdbs)
    remove_annotations_short_contours(files=files)
    ladders, ids = build_annotation_ladders(files=files)
    move_ladders_optimally(files=files, ladders=ladders)
    #delete_standalone_annotations_out_of_bounds(files=files, locked_ids=ids)
    #remove_dense_annotations(files=files, locked_ids=ids)

    print("\nContour annotations for landforms at N10 scale created successfully!\n")


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of creating contour annotations.

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
    out_of_bounds_buffers = wfm.build_file_path(file_name="out_of_bounds_buffers", file_type="gdb")
    out_of_bounds_dissolved = wfm.build_file_path(file_name="out_of_bounds_dissolved", file_type="gdb")
    temporary_file = wfm.build_file_path(file_name="temporary_file", file_type="gdb")
    annotation_contours = wfm.build_file_path(
        file_name="contour_annotations", file_type="gdb"
    )
    annotations = wfm.build_file_path(file_name="annotations", file_type="gdb")
    masks = wfm.build_file_path(file_name="masks", file_type="gdb")
    join = wfm.build_file_path(file_name="join", file_type="gdb")

    return {
        "contours": contours,
        "out_of_bounds_polygons": out_of_bounds_polygons,
        "out_of_bounds_polylines": out_of_bounds_polylines,
        "out_of_bounds_buffers": out_of_bounds_buffers,
        "out_of_bounds_dissolved": out_of_bounds_dissolved,
        "temporary_file": temporary_file,
        "annotation_contours": annotation_contours,
        "annotations": annotations,
        "masks": masks,
        "join": join,
    }


@timing_decorator
def fetch_data(files: dict, municipality: str = None) -> None:
    """
    Collects relevant data and clips it to desired area if required.

    Args:
        files (dict): Dictionary with all the working files
        municipality (str, optional): Municipality name to clip data to (defaults to None)
    """
    # Fetch relevant data
    contour_lyr = "contour_lyr"
    building_lyr = "building_lyr"
    land_use_lyr = "land_use_lyr"
    train_lyr = "train_lyr"
    road_lyr = "road_lyr"

    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Contours, out_layer=contour_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Buildings, out_layer=building_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_n50.ArealdekkeFlate,
        out_layer=land_use_lyr,
        where_clause="OBJTYPE IN ('BymessigBebyggelse', 'ElvBekk', 'FerskvannTørrfall', 'Havflate', 'Industriområde', 'Innsjø', 'InnsjøRegulert', 'Tettbebyggelse')",
    )
    arcpy.management.MakeFeatureLayer(in_features=input_n50.Bane, out_layer=train_lyr)
    arcpy.management.MakeFeatureLayer(
        in_features=input_roads.road_output_1, out_layer=road_lyr
    )

    def process_layer(
        in_lyr: str,
        out_fc: str,
        clip_boundary: str = None,
        temp_fc: str = None,
        append: bool = False,
    ) -> None:
        """
        Clip and appends, or copies the input layer to the output layer.
        """
        if clip_boundary:
            # Clip til kommune
            arcpy.analysis.Clip(
                in_features=in_lyr,
                clip_features=clip_boundary,
                out_feature_class=temp_fc if append else out_fc,
            )
            if append:
                arcpy.management.Append(
                    inputs=temp_fc, target=out_fc, schema_type="NO_TEST"
                )
        else:
            # Ingen kommune: bare kopier eller append
            if append:
                arcpy.management.Append(
                    inputs=in_lyr, target=out_fc, schema_type="NO_TEST"
                )
            else:
                arcpy.management.CopyFeatures(
                    in_features=in_lyr, out_feature_class=out_fc
                )

    if municipality:
        # Fetch municipality boundary
        municipality_lyr = "municipality_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=input_n100.AdminFlate, out_layer=municipality_lyr
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=municipality_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"NAVN = '{municipality}'",
        )

        # 1) Contours
        process_layer(
            in_lyr=contour_lyr, out_fc=files["contours"], clip_boundary=municipality_lyr
        )

        # 2) Building + Train
        for lyr, out_fc in zip(
            [building_lyr, train_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc, clip_boundary=municipality_lyr)
        for lyr, out_fc in zip(
            [land_use_lyr, road_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(
                in_lyr=lyr,
                out_fc=out_fc,
                clip_boundary=municipality_lyr,
                temp_fc=files["temporary_file"],
                append=True,
            )
    else:
        # Save all data to working geodatabases
        process_layer(in_lyr=contour_lyr, out_fc=files["contours"])
        for lyr, out_fc in zip(
            [building_lyr, train_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc)
        for lyr, out_fc in zip(
            [land_use_lyr, road_lyr],
            [files["out_of_bounds_polygons"], files["out_of_bounds_polylines"]],
        ):
            process_layer(in_lyr=lyr, out_fc=out_fc, append=True)


@timing_decorator
def collect_out_of_bounds_areas(files: dict) -> None:
    """
    Creates buffer around lines and dissolves all polygons without creating multiparts.

    Args:
        files (dict): Dictionary with all the working files
    """
    arcpy.analysis.Buffer(
        in_features=files["out_of_bounds_polylines"],
        out_feature_class=files["out_of_bounds_buffers"],
        buffer_distance_or_field="20 Meters",
        line_side="FULL",
        line_end_type="ROUND"
    )
    arcpy.management.Append(
        inputs=files["out_of_bounds_buffers"],
        target=files["out_of_bounds_polygons"],
        schema_type="NO_TEST"
    )
    arcpy.management.Dissolve(
        in_features=files["out_of_bounds_polygons"],
        out_feature_class=files["out_of_bounds_dissolved"],
        dissolve_field=[],
        multi_part="MULTI_PART"
    )


@timing_decorator
def get_annotation_contours(files: dict) -> None:
    """
    Collect index contours with the specific heigth intervall.

    Args:
        files (dict): Dictionary with all the working files
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

    arcpy.management.CopyFeatures(
        in_features=contours_lyr,
        out_feature_class=files["annotation_contours"],
    )


@timing_decorator
def process_tiles(files: dict, folder: str, label_field: str = "HØYDE") -> None:
    """
    Creates annotations for all contours using a sliding
    window over dynamically generated tiles.

    Args:
        files (dict): Dictionary with all the working files
        folder (str): String with a path to the main folder to store gdbs
        label_field (str, optional): Field used as text in the annotation (default: 'HØYDE')
    """
    xmin, ymin, xmax, ymax = get_bbox(files["annotation_contours"])

    size = 5000
    nx = np.ceil((xmax - xmin) / size)
    ny = np.ceil((ymax - ymin) / size)
    total = int(nx * ny)

    for i, (x1, y1, x2, y2) in tqdm(
        enumerate(generate_tiles(xmin, ymin, xmax, ymax, size)),
        total=total,
        desc="Processing tiles",
        colour="yellow",
        leave=False,
    ):
        # Create a polygon for this tile
        tile_poly = arcpy.Polygon(
            arcpy.Array(
                [
                    arcpy.Point(x1, y1),
                    arcpy.Point(x2, y1),
                    arcpy.Point(x2, y2),
                    arcpy.Point(x1, y2),
                ]
            )
        )

        tile_fc = f"in_memory/tile_{i}"
        clipped_fc = f"in_memory/clipped_{i}"

        # Create temporary polygon
        arcpy.management.CopyFeatures(in_features=tile_poly, out_feature_class=tile_fc)

        # Clip contours to the tile
        arcpy.analysis.Clip(
            in_features=files["annotation_contours"],
            clip_features=tile_fc,
            out_feature_class=clipped_fc,
        )

        # Check for geometries
        if int(arcpy.management.GetCount(clipped_fc)[0]) == 0:
            continue

        # Create annotations
        out_gdb = f"{folder}_{i}.gdb"

        if not arcpy.Exists(out_gdb):
            arcpy.management.CreateFileGDB(
                out_folder_path=os.path.dirname(out_gdb),
                out_name=os.path.basename(out_gdb),
            )

        arcpy.cartography.ContourAnnotation(
            in_features=clipped_fc,
            out_geodatabase=out_gdb,
            contour_label_field=label_field,
            reference_scale_value=10000,
            out_layer=f"contour_ann_{i}",
            contour_color="BLACK",
            contour_alignment="PAGE",
            enable_laddering="ENABLE_LADDERING",
        )

        # Delete temporary files
        for fc in [tile_fc, clipped_fc]:
            if arcpy.Exists(fc):
                arcpy.management.Delete(fc)


@timing_decorator
def merge_landform_annotations(folder_path: str, out_anno: str, out_mask: str) -> list:
    """
    Finds all gdb files in the folder_path that matches 'landforms_{#}.gdb',
    collects the annotation-feature-classes and merges them together into one common fc.

    Args:
        folder_path (str): The path to the folder containing the gdb files
        out_anno (str): The feature class that should store the final annotations
        out_mask (str): The feature class that should store the final masks

    Returns:
        list: A list of the gdb files that can be deleted from the project
    """

    # Regex to find correct gdbs
    gdb_pattern = re.compile(r"landforms_(\d+)\.gdb$", re.IGNORECASE)
    annotation_sources = []
    mask_sources = []
    gdb_paths = []

    # Find all the gdb files
    for item in tqdm(
        os.listdir(folder_path),
        desc="Finds landform gdbs",
        colour="yellow",
        leave=False,
    ):
        if gdb_pattern.match(item):
            gdb_path = os.path.join(folder_path, item)
            gdb_paths.append(gdb_path)

            # Set workspace to this gdb
            arcpy.env.workspace = gdb_path

            # Find annotation feature classes
            fcs = arcpy.ListFeatureClasses()
            if not fcs:
                continue

            for fc in fcs:
                full_path = os.path.join(gdb_path, fc)
                if fc.lower().endswith("annomask"):
                    mask_sources.append(full_path)
                elif fc.lower().endswith("anno"):
                    annotation_sources.append(full_path)

    if not annotation_sources:
        print("Fant ingen Contour_FeaturesAnno.")
        return
    if not mask_sources:
        print("Fant ingen Contour_FeaturesAnnoMask.")
        return

    # If the outpiut fcs exist, delete them
    for out in (out_anno, out_mask):
        if arcpy.Exists(out):
            arcpy.management.Delete(out)

    # Merge ANNOTATION
    arcpy.management.CopyFeatures(
        in_features=annotation_sources[0], out_feature_class=out_anno
    )

    for src in tqdm(
        annotation_sources[1:], desc="Merges annotations", colour="yellow", leave=False
    ):
        arcpy.management.Append(inputs=src, target=out_anno, schema_type="NO_TEST")

    # Merge MASKS
    arcpy.management.CopyFeatures(
        in_features=mask_sources[0], out_feature_class=out_mask
    )

    for src in tqdm(
        mask_sources[1:], desc="Merges masks", colour="yellow", leave=False
    ):
        arcpy.management.Append(inputs=src, target=out_mask, schema_type="NO_TEST")

    print(
        f"\nFinished! Merged a total of {len(annotation_sources)} annotation-fcs to:\n  {out_anno}\n  {out_mask}\n"
    )

    return gdb_paths


@timing_decorator
def delete_gdbs(gdbs: list) -> None:
    """
    Deletes the input gdbs.

    Args:
        gdbs (list): List of gdb files that should be deleted
    """
    arcpy.env.workspace = None
    for gdb in gdbs:
        try:
            if arcpy.Exists(gdb):
                arcpy.management.Delete(gdb)
        except:
            continue


@timing_decorator
def remove_annotations_short_contours(files: dict) -> None:
    """
    Removes annotations for short contours.

    Args:
        files (dict): Dictionary with all the working files
    """
    tolerance_1 = 3_000  # [m]
    tolerance_2 = 10_000  # [m]

    contours = files["annotation_contours"]
    annos = files["annotations"]
    masks = files["masks"]
    join = files["join"]

    # 1) Spatial join: annotation -> contour
    arcpy.analysis.SpatialJoin(
        target_features=annos,
        join_features=contours,
        out_feature_class=join,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # 2) Create mapping: contour_oid -> annotation_oids
    mapping = {}
    with arcpy.da.SearchCursor(join, ["TARGET_FID", "JOIN_FID"]) as cur:
        for anno_id, cont_oid in cur:
            mapping.setdefault(cont_oid, []).append(anno_id)

    # 3) Find contours by length
    short = set()
    medium = set()

    with arcpy.da.SearchCursor(contours, ["OID@", "SHAPE@LENGTH"]) as cur:
        for oid, length in cur:
            if length < tolerance_1:
                short.add(oid)
            elif length < tolerance_2:
                medium.add(oid)

    # 4) Delete the annotations for short contours
    anno_delete = []
    for cont_oid in short:
        anno_delete.extend(mapping.get(cont_oid, []))

    # 5) Keep only one for medium contours
    for cont_oid in medium:
        annos_for_contour = mapping.get(cont_oid, [])
        if len(annos_for_contour) > 1:
            anno_delete.extend(annos_for_contour[1:])

    # 6) Delete the annotations and masks
    if anno_delete:
        where = f"OBJECTID IN ({','.join(map(str, anno_delete))})"
        arcpy.management.MakeFeatureLayer(annos, "anno_lyr")
        arcpy.management.SelectLayerByAttribute("anno_lyr", "NEW_SELECTION", where)
        arcpy.management.DeleteFeatures("anno_lyr")

        arcpy.management.MakeFeatureLayer(masks, "mask_lyr")
        arcpy.management.SelectLayerByAttribute("mask_lyr", "NEW_SELECTION", where)
        arcpy.management.DeleteFeatures("mask_lyr")

    print(f"\nDeleted {len(anno_delete)} annotations.\n")


@timing_decorator
def build_annotation_ladders(
    files: dict, max_dist: float = 1000.0
) -> tuple[list[list], set]:
    """
    Groups contour annotations into 'ladders' where each ladder
    represents a sequence of increasing elevation labels that lie within
    'max_dist' meters of each other.

    Args:
        files (dict): Dictionary with all the working files
        max_dist (float, optional): Maximum distance to be connected to a ladder (default: 2000)

    Returns:
        ladders (list[list[int]]): Each inner list contains annotation OIDs
        locked_ids (set[int]): All OIDs that appear in at least one ladder
    """
    annos = files["annotations"]

    # 1) Load annotation info
    anno_info = {}
    with arcpy.da.SearchCursor(annos, ["OID@", "TextString", "SHAPE@"]) as cur:
        for oid, text, geom in cur:
            try:
                height = int(text.replace(" ", ""))
            except:
                continue
            anno_info[oid] = (height, geom.centroid)

    # 2) Clustering
    clusters = cluster_points(points=[(oid, pt) for oid, (_, pt) in anno_info.items()], eps=max_dist)

    # 3) Build ladders per cluster
    all_ladders = []
    all_locked = set()

    for cluster in tqdm(clusters, desc="Building ladders", colour="yellow", leave=False):
        sub_info = {oid: anno_info[oid] for oid in cluster}

        # Group by height
        by_height = {}
        for oid, (height, pt) in sub_info.items():
            by_height.setdefault(height, []).append((oid, pt))
        
        heights = sorted(by_height.keys())

        ladders = []
        locked_ids = set()

        for i, h in enumerate(heights):
            current_level = by_height[h]

            # For the lowest level, each annotation starts a new ladder
            if i == 0:
                for oid, pt in current_level:
                    ladders.append([oid])
                    locked_ids.add(oid)
                continue

            # For higher levels, try to attach to existing ladders
            prev_level = by_height[heights[i - 1]]
            prev_points = [(oid, pt) for oid, pt in prev_level]

            for oid, pt in tqdm(
                current_level, desc="Finds match", colour="green", leave=False
            ):
                pt_geom = arcpy.PointGeometry(pt)

                best = None
                best_dist = None

                for oid_prev, pt_prev in prev_points:
                    d = pt_geom.distanceTo(arcpy.PointGeometry(pt_prev))
                    if d <= max_dist and (best is None or d < best_dist):
                        best = oid_prev
                        best_dist = d

                if best is None:
                    # New ladder
                    ladders.append([oid])
                    locked_ids.add(oid)
                else:
                    # Attach to the best ladder
                    for ladder in ladders:
                        if ladder[-1] == best:
                            ladder_heights = {sub_info[x][0] for x in ladder}
                            if h in ladder_heights:
                                continue
                            ladder.append(oid)
                            locked_ids.add(oid)
                            break

        # Filter internal list of len == 1
        singletons = [lst[0] for lst in ladders if len(lst) < 5]
        ladders = [lst for lst in ladders if len(lst) >= 5]
        locked_ids -= set(singletons)

        all_ladders.extend(ladders)
        all_locked |= locked_ids

    return all_ladders, all_locked


@timing_decorator
def delete_standalone_annotations_out_of_bounds(files: dict, locked_ids: set) -> None:
    """
    Deletes annotations in out of bounds areas that
    are not connected in an annotation ladder.

    Args:
        files (dict): Dictionary with all the working files
        locked_ids (set): IDs that are part of a ladder and cannot be deleted
    """
    annos = files["annotations"]
    masks = files["masks"]
    ob = files["out_of_bounds_dissolved"]

    annos_lyr = "annos_lyr"
    mask_lyr = "mask_lyr"
    arcpy.management.MakeFeatureLayer(in_features=annos, out_layer=annos_lyr)
    arcpy.management.MakeFeatureLayer(in_features=masks, out_layer=mask_lyr)

    arcpy.management.SelectLayerByLocation(
        in_layer=annos_lyr,
        overlap_type="INTERSECT",
        select_features=ob,
        selection_type="NEW_SELECTION"
    )

    oids = [
        row[0]
        for row in arcpy.da.SearchCursor(annos_lyr, ["OID@"])
        if row[0] not in locked_ids
    ]

    if not oids:
        return

    where = f"OBJECTID IN ({','.join(map(str, oids))})"

    for lyr in [annos_lyr, mask_lyr]:
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=lyr,
            selection_type="NEW_SELECTION",
            where_clause=where
        )
        arcpy.management.DeleteRows(in_rows=lyr)
    
    print(f"\nDeleted {len(oids)} annotations.\n")

@timing_decorator
def move_ladders_optimally(files: dict, ladders: list) -> None:
    """
    Moves ladders of contour annotations to the
    optimal position to avoid out of bounds areas.

    Args:
        files (dict): Dictionary with all the working files
        ladders (list): A list of lists, where each internal list
                        contains the OIDs of annotations in the same ladder
    """
    contours = files["annotation_contours"]
    annos = files["annotations"]
    masks = files["masks"]
    ob = files["out_of_bounds_dissolved"]

    # Create ONE geometry object of the ob area
    geoms = []
    with arcpy.da.SearchCursor(ob, ["SHAPE@"]) as cur:
        for (g,) in cur:
            geoms.append(g)
    ob_geom = geoms[0].union(geoms[1:]) if len(geoms) > 1 else geoms[0]

    # The maximum distance that the ladder can be moved:
    max_movement = 1000 # [m]

    contours_lyr = "contours_lyr"
    annos_lyr = "annos_lyr"
    masks_lyr = "masks_lyr"

    for fc, lyr in zip(
        [contours, annos, masks],
        [contours_lyr, annos_lyr, masks_lyr]
    ):
        arcpy.management.MakeFeatureLayer(in_features=fc, out_layer=lyr)
    
    # Keep IDs to be deleted
    ids_to_delete = set()

    for ladder in tqdm(ladders, desc="Adjusting ladders", colour="yellow", leave=False):
        sql = f"OBJECTID IN ({','.join(map(str, ladder))})"
        arcpy.management.SelectLayerByAttribute(in_layer_or_view=annos_lyr, selection_type="NEW_SELECTION", where_clause=sql)

        # Fetch annotation geometries
        annos_data = []
        with arcpy.da.SearchCursor(annos_lyr, ["OID@", "SHAPE@", "TextString"]) as cur:
            for oid, geom, text in cur:
                annos_data.append([oid, geom, int(text)])
        
        if not annos_data:
            continue
        annos_data.sort(key=lambda x: x[2])
        
        """
        Find the anchor annotation:
        Start in the bottom and the first one having a
        position in a valid area is considered the anchor
        """
        anchor_oid, anchor_geom = None, None
        idx = 0
        while not anchor_oid:
            oid, geom, _ = annos_data[idx]
            
            pt = geom.getPart()[0][0]
            x, y = pt.X, pt.Y
            geom = arcpy.PointGeometry(arcpy.Point(x, y), geom.spatialReference)


            contour = get_contour_for_annotation(geom=geom, contours_lyr=contours_lyr)
            if not contour:
                idx += 1
                continue
            valid_geom = find_valid_position_along_contour(point_geom=geom, contour_geom=contour, ob_geom=ob_geom, max_dist=max_movement)
            if valid_geom:
                anchor_oid, anchor_geom = oid, valid_geom
            else:
                idx += 1
                ids_to_delete.add(oid)
                if idx == len(annos_data):
                    break
        # Adjusts all remaining points according to the anchor
        # 1) Finds the new positions
        for i in tqdm(range(len(annos_data)), desc="Adjusting annotations", colour="green", leave=False):
            oid, geom, _ = annos_data[i]
            if oid == anchor_oid or oid in ids_to_delete:
                continue

            pt = geom.getPart()[0][0]
            x, y = pt.X, pt.Y
            geom = arcpy.PointGeometry(arcpy.Point(x, y), geom.spatialReference)

            contour = get_contour_for_annotation(geom = geom, contours_lyr=contours_lyr)

            new_pos = move_towards_anchor(
                point_geom=geom,
                contour_geom=contour,
                anchor_geom=anchor_geom,
                ob_geom=ob_geom,
                max_dist=max_movement
            )

            if new_pos is None:
                ids_to_delete.add(oid)
            else:
                # Store for update
                annos_data[i][1] = new_pos
        
        # 2) Update the positions in the featureclass
        # ANNOTATIONS
        with arcpy.da.UpdateCursor(annos_lyr, ["OID@", "SHAPE@ANCHORPOINT"]) as a_cur:
            for oid, _ in a_cur:
                if oid in ids_to_delete:
                    a_cur.deleteRow()
                else:
                    new_geom = next((g for id, g, _ in annos_data if id == oid), None)
                    if new_geom:
                        x = new_geom.centroid.X
                        y = new_geom.centroid.Y
                        a_cur.updateRow([oid, (x, y)])

        # MASKS
        with arcpy.da.UpdateCursor(masks_lyr, ["OID@", "SHAPE@"]) as m_cur:
            for oid, geom in m_cur:
                if oid in ids_to_delete:
                    m_cur.deleteRow()
                else:
                    new_geom = next((g for id, g, _ in annos_data if id == oid), None)
                    if new_geom:
                        old_x, old_y = geom.centroid.X, geom.centroid.Y
                        new_x, new_y = new_geom.centroid.X, new_geom.centroid.Y
                        dx = new_x - old_x
                        dy = new_y - old_y
                        moved_geom = geom.move(dx, dy)
                        m_cur.updateRow([oid, moved_geom])


@timing_decorator
def remove_dense_annotations(
    files: dict, locked_ids: set, min_spacing: float = 1000.0
) -> None:
    """
    Removes redundant annotations on long contours.

    Args:
        files (dict): Dictionary with all the working files
        locked_ids (set): IDs that are part of a ladder and cannot be deleted
        min_spacing (float, optional): Minimum spacing between two annotations on the same contour (default: 2000)
    """
    contours = files["annotation_contours"]
    annos = files["annotations"]
    masks = files["masks"]
    join = files["join"]

    # 1) Spatial join: annotation -> contour
    arcpy.analysis.SpatialJoin(
        target_features=annos,
        join_features=contours,
        out_feature_class=join,
        join_operation="JOIN_ONE_TO_MANY",
        match_option="INTERSECT",
    )

    # 2) Build mapping: contour_oid -> list of (anno_id, position_on_line)
    mapping = {}
    # Pre-loaded geometries for fast lookup
    contour_geoms = {}
    with arcpy.da.SearchCursor(contours, ["OID@", "SHAPE@"]) as cur:
        for oid, geom in cur:
            contour_geoms[oid] = geom

    seen = set()

    with arcpy.da.SearchCursor(join, ["TARGET_FID", "JOIN_FID", "SHAPE@"]) as cur:
        for anno_oid, cont_oid, anno_geom in cur:
            if (anno_oid, cont_oid) in seen:
                continue
            seen.add((anno_oid, cont_oid))
            if cont_oid not in contour_geoms:
                continue
            pos = contour_geoms[cont_oid].measureOnLine(anno_geom.centroid)
            mapping.setdefault(cont_oid, []).append((anno_oid, pos))

    # 3) Determine the annotations to delete
    anno_delete = []
    for cont_oid, anno_list in tqdm(
        mapping.items(),
        desc="Finds annotations to delete",
        colour="yellow",
        leave=False,
    ):
        anno_list.sort(key=lambda x: x[1])
        last_pos = None
        for anno_oid, pos in anno_list:
            if last_pos is None:
                last_pos = pos
            elif pos - last_pos < min_spacing:
                if anno_oid not in locked_ids:
                    anno_delete.append(anno_oid)
                else:
                    last_pos = pos
            else:
                last_pos = pos

    # 4) Delete annotations and masks
    if anno_delete:
        where = f"OBJECTID IN ({','.join(map(str, anno_delete))})"

        # Delete annotations
        arcpy.management.MakeFeatureLayer(annos, "anno_lyr")
        arcpy.management.SelectLayerByAttribute("anno_lyr", "NEW_SELECTION", where)
        arcpy.management.DeleteFeatures("anno_lyr")

        # Delete masks
        arcpy.management.MakeFeatureLayer(masks, "mask_lyr")
        arcpy.management.SelectLayerByAttribute("mask_lyr", "NEW_SELECTION", where)
        arcpy.management.DeleteFeatures("mask_lyr")

    print(f"\nDeleted {len(anno_delete)} annotations.\n")


# ========================
# Helper functions
# ========================


def get_bbox(fc: str) -> tuple[float]:
    """
    Creates the bounding box of a FeatureClass.

    Args:
        fc (str): The feature class to process

    Returns:
        tuple[float]: float values describing the bbox of the fc
    """
    desc = arcpy.Describe(fc)
    extent = desc.extent
    return extent.XMin, extent.YMin, extent.XMax, extent.YMax


def generate_tiles(xmin: float, ymin: float, xmax: float, ymax: float, size: int):
    """
    Generate square tiles covering a bounding box.

    This generator yields axis‑aligned tiles of fixed size that together
    cover the rectangular area defined by the input coordinates. Tiles are
    produced in row‑major order, starting at (xmin, ymin) and stepping by
    `size` in both x‑ and y‑direction until the maximum bounds are reached.

    Args:
        xmin (float): Minimum x‑coordinate of the bounding box
        ymin (float): Minimum y‑coordinate of the bounding box
        xmax (float): Maximum x‑coordinate of the bounding box
        ymax (float): Maximum y‑coordinate of the bounding box
        size (int): Width and height of each tile

    Yields:
        tuple[float, float, float, float]: A tile represented as
        (x_min, y_min, x_max, y_max)
    """

    x = xmin
    while x < xmax:
        y = ymin
        while y < ymax:
            yield (x, y, x + size, y + size)
            y += size
        x += size


def cluster_points(points: list, eps: int) -> list:
    """
    Simple DBSCAN-like clustering for points on same height level.

    Args:
        points (list): List of points with format [(oid, pt), ...]
        eps (int): Length tolerance for being connected to a cluster

    Returns:
        list: List of OIDs connected in clusters
    """
    clusters = []
    used = set()

    for oid, pt in tqdm(points, desc="Cluster points", colour="yellow", leave=False):
        if oid in used:
            continue

        cluster = [oid]
        used.add(oid)

        for oid2, pt2 in points:
            if oid2 in used:
                continue
            pt_geom = arcpy.PointGeometry(pt)
            if pt_geom.distanceTo(arcpy.PointGeometry(pt2)) <= eps:
                cluster.append(oid2)
                used.add(oid2)
        clusters.append(cluster)
    
    return clusters


def get_contour_for_annotation(geom: arcpy.Geometry, contours_lyr: str) -> arcpy.Geometry | None:
    """
    Find nearest contour line to annotation.

    Args:
        geom (arcpy.Geometry): The arcpy-geometry to analys
        contours_lyr (str): THe feature layer with contours

    Returns:
        arcpy.Geometry: The geometry of the closest contour, if some
    """
    arcpy.management.SelectLayerByLocation(
        in_layer=contours_lyr,
        overlap_type="WITHIN_A_DISTANCE",
        select_features=geom,
        search_distance="5 Meters",
        selection_type="NEW_SELECTION"
    )

    # If none found, expand search
    count = int(arcpy.management.GetCount(contours_lyr)[0])
    if count == 0:
        arcpy.management.SelectLayerByLocation(
            in_layer=contours_lyr,
            overlap_type="WITHIN_A_DISTANCE",
            select_features=geom,
            search_distance="50 Meters",
            selection_type="NEW_SELECTION"
        )

    with arcpy.da.SearchCursor(contours_lyr, ["SHAPE@"]) as cur:
        for row in cur:
            return row[0]

    return None

def is_valid(point_geom: arcpy.Geometry, ob_geom: arcpy.Geometry) -> bool:
    """
    Identifies if a point is in the area.

    Args:
        point_geom (arcpy.Geometry): The geometry to investigate
        ob_geom (arcpy.Geometry): The area to search for relationship

    Returns:
        bool: True if geom is inside ob_lyr, else False
    """
    return point_geom.disjoint(ob_geom)

def find_valid_position_along_contour(point_geom: arcpy.Point, contour_geom: arcpy.Polyline, ob_geom: arcpy.Geometry, max_dist: int, step: int=5):
    """
    Moves a point along a contour polyline until it finds a valid (non-OB) position.

    Args:
        point_geom (Geometry): The annotation point geometry
        contour_geom (Geometry): The contour polyline geometry
        ob_geom (arcpy.Geometry): Out of bounds geometry
        max_dist (int): Maximum distance to move along the contour
        step (int, optional): Step size in meters for searching (default: 5)

    Returns:
        Geometry or None: A valid point geometry, or None if no valid position exists
    """
    # 1) Find start position
    try:
        m0 = contour_geom.measureOnLine(point_geom)
    except:
        return None
    
    # 2) Validate starting position
    if is_valid(point_geom, ob_geom):
        return point_geom
    
    # 3) Search in both directions
    max_m = contour_geom.length
    search_range = int(max_dist // step)
    for i in range(1, search_range + 1):
        for direction in (+1, -1):
            m_new = m0 + direction * i * step
            # Limit to polyline
            if m_new < 0 or m_new > max_m:
                continue
            new_point = contour_geom.positionAlongLine(m_new)
            if is_valid(new_point, ob_geom):
                return new_point
    
    # 4) No valid position found
    return None

def move_towards_anchor(point_geom: arcpy.Point, contour_geom: arcpy. Polyline, anchor_geom: arcpy.Point, ob_geom: arcpy.Geometry, max_dist: int, step: int=5) -> arcpy.Point | arcpy.PointGeometry | None:
    """
    Moves a point along its contour towards the anchor point,
    stopping at the closest valid (non-OB) position.

    Args:
        point_geom (arcpy.Point): The point to move
        contour_geom (arcpy.Polyline): The contour to move along
        anchor_geom (arcpy.Point): The anchor point
        ob_geom (arcpy.Geometry): Out-of-bounds geometry
        max_dist (int): Maximum distance to move along the contour
        step (int, optional): Step size in meters for searching (default: 5)

    Returns:
        Geometry or None: A valid point geometry, or None if no valid position exists
    """
    # 1) Find start position
    try:
        m_point = contour_geom.measureOnLine(point_geom)
        m_anchor = contour_geom.measureOnLine(anchor_geom)
    except:
        return None

    # 2) Start searching after valid position
    direction = 1 if m_anchor > m_point else -1
    max_m = contour_geom.length

    if is_valid(point_geom, ob_geom):
        return point_geom
    
    steps = int(max_dist // step)
    for i in range(1, steps + 1):
        m_new = m_point + direction * i * step
        if m_new < 0 or m_new > max_m:
            continue
        new_pos = contour_geom.positionAlongLine(m_new)
        if is_valid(new_pos, ob_geom):
            return new_pos
    return None


# ========================

if __name__ == "__main__":
    main()
