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
from input_data import input_n10, input_n100

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
    get_annotation_contours(files=files)
    process_tiles(files=files, folder=f"{folder}/{object_hoyde}")
    gdbs = merge_landform_annotations(
        folder_path=folder, out_anno=files["annotations"], out_mask=files["masks"]
    )
    delete_gdbs(gdbs=gdbs)
    remove_annotations_short_contours(files=files)
    ladders, ids = build_annotation_ladders(files=files)
    remove_dense_annotations(files=files, locked_ids=ids)

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
    buildings = wfm.build_file_path(file_name="buildings", file_type="gdb")
    annotation_contours = wfm.build_file_path(
        file_name="contour_annotations", file_type="gdb"
    )
    annotations = wfm.build_file_path(file_name="annotations", file_type="gdb")
    masks = wfm.build_file_path(file_name="masks", file_type="gdb")
    join = wfm.build_file_path(file_name="join", file_type="gdb")

    return {
        "contours": contours,
        "buildings": buildings,
        "annotation_contours": annotation_contours,
        "annotations": annotations,
        "masks": masks,
        "join": join
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
    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Contours, out_layer=contour_lyr
    )
    arcpy.management.MakeFeatureLayer(
        in_features=input_n10.Buildings, out_layer=building_lyr
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

        # Clip data to municipality boundary
        for lyr, out_fc in zip(
            [contour_lyr, building_lyr],
            [files["contours"], files["buildings"]],
        ):
            arcpy.management.SelectLayerByLocation(
                in_layer=lyr,
                overlap_type="INTERSECT",
                select_features=municipality_lyr,
                selection_type="NEW_SELECTION",
            )
            arcpy.analysis.Clip(
                in_features=lyr,
                clip_features=municipality_lyr,
                out_feature_class=out_fc,
            )
    else:
        # Save all data to working geodatabases
        for lyr, out_fc in zip(
            [contour_lyr, building_lyr],
            [files["contours"], files["buildings"]],
        ):
            arcpy.management.CopyFeatures(
                in_features=lyr,
                out_feature_class=out_fc,
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
    tolerance_1 = 3_000 # [m]
    tolerance_2 = 10_000 # [m]

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
        match_option="INTERSECT"
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
    
    print(f"\nFjernet {len(anno_delete)} annotasjoner totalt.\n")

@timing_decorator
def build_annotation_ladders(files: dict, max_dist: float=2000.0) -> tuple[list[list], set]:
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
    
    # 2) Group by height
    by_height = {}
    for oid, (height, pt) in tqdm(anno_info.items(), desc="Group by height", colour="yellow", leave=False):
        by_height.setdefault(height, []).append((oid, pt))

    # 3) Sort height levels
    heights = sorted(by_height.keys())

    # 4) Build ladders
    ladders = []
    locked_ids = set()

    for i, h in tqdm(enumerate(heights), desc="Building ladders", colour="yellow", leave=False):
        current_level = by_height[h]

        # For the lowest level, each annotation starts a new ladder
        if i == 0:
            for oid, pt in current_level:
                ladders.append([oid])
                locked_ids.add(oid)
            continue

        # For higher levels, try to attach to existing ladders
        prev_level = by_height[heights[i-1]]
        prev_points = [(oid, pt) for oid, pt in prev_level]
        
        for oid, pt in tqdm(current_level, desc="Finds match", colour="green", leave=False):
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
                        ladder.append(oid)
                        locked_ids.add(oid)
                        break
    
    # Filter internal list of len == 1
    singletons = [lst[0] for lst in ladders if len(lst) == 1]
    ladders = [lst for lst in ladders if len(lst) > 1]
    locked_ids -= set(singletons)

    return ladders, locked_ids

@timing_decorator
def remove_dense_annotations(files: dict, locked_ids: set, min_spacing: float=1000.0) -> None:
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
        match_option="INTERSECT"
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
    for cont_oid, anno_list in tqdm(mapping.items(), desc="Finds annotations to delete", colour="yellow", leave=False):
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

    print(f"\nFjernet {len(anno_delete)} overflødige annotasjoner.\n")

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


# ========================

if __name__ == "__main__":
    main()
