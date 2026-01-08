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

    return {
        "contours": contours,
        "buildings": buildings,
        "annotation_contours": annotation_contours,
        "annotations": annotations,
        "masks": masks,
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
        f"\nFinished! Merged a total of {len(annotation_sources)} annotation-fcs to:\n  {out_anno}\n  {out_mask}"
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
        if arcpy.Exists(gdb):
            arcpy.management.Delete(gdb)

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
