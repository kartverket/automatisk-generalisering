# Libraries

import arcpy
import config
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

    # Sets up work file manager and creates temporary files
    working_fc = Landform_N10.hoyde__n10_landforms.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    fetch_data(files=files, municipality=municipality)
    get_annotation_contours(files=files)
    process_tiles(files=files)
    
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
    annotation_contours = wfm.build_file_path(file_name="contour_annotations", file_type="gdb")

    return {
        "contours": contours,
        "buildings": buildings,
        "annotation_contours": annotation_contours,
    }

@timing_decorator
def fetch_data(files: dict, municipality: str=None) -> None:
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
def process_tiles(files: dict, label_field: str="HØYDE"):
    """
    Creates annotations for all contours using a sliding
    window over dynamically generated tiles.

    Args:
        files (dict): Dictionary with all the working files
        label_field (str, optional): Field used as text in the annotation (default: 'HØYDE')
    """
    xmin, ymin, xmax, ymax = get_bbox(files["annotation_contours"])

    for i, (x1, y1, x2, y2) in tqdm(enumerate(generate_km_tiles(xmin, ymin, xmax, ymax)), desc="Processing tiles", colour="yellow", leave=False):
        # Create a polygon for this tile
        tile_poly = arcpy.Polygon(arcpy.Array([
            arcpy.Point(x1, y1),
            arcpy.Point(x2, y1),
            arcpy.Point(x2, y2),
            arcpy.Point(x1, y2)
        ]))

        tile_fc = f"in_memory/tile_{i}"
        clipped_fc = f"in_memory/clipped_{i}"

        # Create temporary polygon
        arcpy.management.CopyFeatures(in_features=tile_poly, out_feature_class=tile_fc)

        # Clip contours to the tile
        arcpy.analysis.Clip(in_features=files["annotation_contours"], clip_features=tile_fc, out_feature_class=clipped_fc)

        # Check for geometries
        if int(arcpy.management.GetCount(clipped_fc)[0]) == 0:
            continue

        # Create annotations
        out_gdb = f"{config.output_folder}/{main_directory_name}/{scale_n10}/{object_hoyde}_{i}.gdb"

        if not arcpy.Exists(out_gdb):
            arcpy.management.CreateFileGDB(out_folder_path=os.path.dirname(out_gdb), out_name=os.path.basename(out_gdb))

        arcpy.cartography.ContourAnnotation(
            in_features=clipped_fc,
            out_geodatabase=out_gdb,
            contour_label_field=label_field,
            reference_scale_value=10000,
            out_layer=f"contour_ann_{i}",
            contour_color="BLACK",
            contour_alignment="PAGE",
            enable_laddering="ENABLE_LADDERING"
        )

def merge_landform_annotations(folder_path, output_gdb, output_fc_name="merged_annotations"):
    """
    Finner alle GDB-er i folder_path som matcher 'landforms_{#}.gdb',
    henter ut annotation-feature-classes og slår dem sammen til én felles FC.
    """

    # Regex for å finne riktige GDB-er
    gdb_pattern = re.compile(r"landforms_(\d+)\.gdb$", re.IGNORECASE)

    # Samle annotation-FCs her
    annotation_sources = []

    # Iterer gjennom filer i mappen
    for item in os.listdir(folder_path):
        if gdb_pattern.match(item):
            gdb_path = os.path.join(folder_path, item)
            print(f"Fant GDB: {gdb_path}")

            # Sett workspace til denne GDB-en
            arcpy.env.workspace = gdb_path

            # Finn annotation feature classes
            fcs = arcpy.ListFeatureClasses(feature_type="Annotation")

            if not fcs:
                print("  → Ingen annotation-FCs funnet.")
                continue

            for fc in fcs:
                full_path = os.path.join(gdb_path, fc)
                annotation_sources.append(full_path)
                print(f"  → Lagt til annotation: {full_path}")

    if not annotation_sources:
        print("Ingen annotasjonslag funnet i noen GDB-er.")
        return

    # Lag output-GDB hvis den ikke finnes
    if not arcpy.Exists(output_gdb):
        out_folder, out_name = os.path.split(output_gdb)
        arcpy.CreateFileGDB_management(out_folder, out_name)

    # Full sti til output-FC
    output_fc = os.path.join(output_gdb, output_fc_name)

    # Hvis output-FC finnes fra før, slett den
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)

    print("\nSlår sammen annotasjonslag...")

    # Første FC kopieres, resten appendes
    first = annotation_sources[0]
    arcpy.CopyFeatures_management(first, output_fc)

    for src in annotation_sources[1:]:
        print(f"  → Appender {src}")
        arcpy.Append_management(src, output_fc, "NO_TEST")

    print(f"\nFerdig! Slått sammen {len(annotation_sources)} annotation-FCs til:")
    print(f"  {output_fc}")







@timing_decorator
def generate_points_along_contours(files: dict, dist: int=1000) -> None:
    """
    Generate points along contours for labeling.

    Args:
        files (dict): Dictionary with all the working files
        dist (int, optional): Distance interval for point generation (defaults to 25)
    """
    # Collect contours at specified height intervals
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

    # Generate points
    arcpy.management.GeneratePointsAlongLines(
        Input_Features=files["annotation_contours"],
        Output_Feature_Class=files["contour_points"],
        Point_Placement="DISTANCE",
        Distance=f"{dist} Meters",
    )

    # Spatial join between contours and points to transfer height values
    arcpy.analysis.SpatialJoin(
        target_features=files["contour_points"],
        join_features=files["annotation_contours"],
        out_feature_class=files["joined_contours"],
        match_option="CLOSEST",
    )

@timing_decorator
def generate_contour_annotations(files: dict) -> None:
    """
    Generate contour annotations for landforms at N10 scale.
    """
    out_gdb = f"{config.output_folder}/{main_directory_name}/{scale_n10}/{object_hoyde}.gdb"

    # Generate contour annotations
    arcpy.cartography.ContourAnnotation(
        in_features=files["annotation_contours"],
        out_geodatabase=out_gdb,
        contour_label_field="HØYDE",
        reference_scale_value=10000,
        out_layer="contour_annotations",
        contour_color="BLACK",
        contour_alignment="PAGE",
        enable_laddering="ENABLE_LADDERING",
    )

# ========================
# Helper functions
# ========================

def get_bbox(fc):
    desc = arcpy.Describe(fc)
    extent = desc.extent
    return extent.XMin, extent.YMin, extent.XMax, extent.YMax

def generate_km_tiles(xmin, ymin, xmax, ymax, size=1000):
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