# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n100.file_manager_land_use import Land_Use_N100
from input_data import input_fkb, input_n50

# Variables

# ...

# ========================
# Program
# ========================

@timing_decorator
def main():
    """
    The main program that is generalizing runways from FKB and N50 to N100.
    """
    print("\nGeneralizes runways!\n")

    # Sets up the work file manager and creates temporarily files
    working_fc = Land_Use_N100.rullebane__n100_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    find_runways(files=files)
    create_buffers(files=files)
    match_runways(files=files)

    print()

# ========================
# Main functions
# ========================

@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of generalizing runways.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    runway_line = wfm.build_file_path(file_name="runway_line", file_type="gdb")
    runway_poly = wfm.build_file_path(file_name="runway_poly", file_type="gdb")
    runway_n50 = wfm.build_file_path(file_name="runway_n50", file_type="gdb")
    line_buffer = wfm.build_file_path(file_name="line_buffer", file_type="gdb")
    poly_buffer = wfm.build_file_path(file_name="poly_buffer", file_type="gdb")
    line_dissolved = wfm.build_file_path(file_name="line_dissolved", file_type="gdb")
    poly_dissolved = wfm.build_file_path(file_name="poly_dissolved", file_type="gdb")

    return {
        "runway_line": runway_line,
        "runway_poly": runway_poly,
        "runway_n50": runway_n50,
        "line_buffer": line_buffer,
        "poly_buffer": poly_buffer,
        "line_dissolved": line_dissolved,
        "poly_dissolved": poly_dissolved
    }

@timing_decorator
def find_runways(files: dict) -> None:
    """
    Fetches all the data for runways, both lines and polygons, FKB and N50.

    Args:
        files (dict): Dictionary with all the working files
    """
    airport_line_lyr = "airport_line_lyr"
    airport_poly_lyr = "airport_poly_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fkb.fkb_lufthavn_grense, out_layer=airport_line_lyr)
    arcpy.management.MakeFeatureLayer(in_features=input_fkb.fkb_lufthavn_omrade, out_layer=airport_poly_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_line_lyr,
        selection_type="NEW_SELECTION",
        where_clause="informasjon = 'FKB50: Kodet om fra Rullebanegrense'"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_poly_lyr,
        selection_type="NEW_SELECTION",
        where_clause="objtype = 'Rullebane'"
    )

    arcpy.management.CopyFeatures(in_features=airport_line_lyr, out_feature_class=files["runway_line"])
    arcpy.management.CopyFeatures(in_features=airport_poly_lyr, out_feature_class=files["runway_poly"])

    airport_n50_lyr = "airport_n50_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_n50.ArealdekkeFlate, out_layer=airport_n50_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=airport_n50_lyr,
        selection_type="NEW_SELECTION",
        where_clause="OBJTYPE = 'Rullebane'"
    )

    arcpy.management.CopyFeatures(in_features=airport_n50_lyr, out_feature_class=files["runway_n50"])

@timing_decorator
def create_buffers(files: dict) -> None:
    """
    Creates dissolved buffers around all the FKB data for runways.

    Args:
        files (dict): Dictionary with all the working files
    """
    combinations = [
        [files["runway_line"], files["line_buffer"], files["line_dissolved"]],
        [files["runway_poly"], files["poly_buffer"], files["poly_dissolved"]]
    ]
    for comb in combinations:
        create_dissolved_buffer(
            in_layer=comb[0],
            buffer_layer=comb[1],
            dissolved_layer=comb[2]
        )

@timing_decorator
def match_runways(files: dict) -> None:
    """
    Matches runway polygons from N50 with the FKB data and labels it depending on
    overlap with either polygons or lines, where polygons have the highest priority.

    Args:
        files (dict): Dictionary with all the working files
    """
    runway_fc = files["runway_n50"]
    line_buffer_fc = files["line_dissolved"]
    poly_buffer_fc = files["poly_dissolved"]

    # Adds the new field
    fields = [f.name for f in arcpy.ListFields(runway_fc)]
    if "connection" not in fields:
        arcpy.management.AddField(runway_fc, "connection", "TEXT")

    with arcpy.da.UpdateCursor(runway_fc, ["connection"]) as cursor:
        for row in cursor:
            row[0] = "None"
            cursor.updateRow(row)
    
    # Finds overlap with polygons
    runway_lyr = "runway_lyr"
    arcpy.management.MakeFeatureLayer(runway_fc, runway_lyr)
    arcpy.management.SelectLayerByLocation(
        in_layer=runway_lyr,
        overlap_type="INTERSECT",
        select_features=poly_buffer_fc,
        selection_type="NEW_SELECTION"
    )
    with arcpy.da.UpdateCursor(runway_lyr, ["connection"]) as cursor:
        for row in cursor:
            row[0] = "FKB_poly"
            cursor.updateRow(row)
    
    # Finds overlap with lines
    arcpy.management.SelectLayerByLocation(
        in_layer=runway_lyr,
        overlap_type="INTERSECT",
        select_features=line_buffer_fc,
        selection_type="NEW_SELECTION"
    )
    with arcpy.da.UpdateCursor(runway_lyr, ["connection"]) as cursor:
        for row in cursor:
            if row[0] != "FKB_poly":
                row[0] = "FKB_line"
                cursor.updateRow(row)

# ========================
# Helper functions
# ========================

def create_dissolved_buffer(in_layer: str, buffer_layer: str, dissolved_layer: str, buffer_dist: int=20) -> None:
    """
    Create dissolved buffers.

    Args:
        in_layer (str): The layer with features to make buffers around
        buffer_layer (str): The layer to store buffers
        dissolved_layer (str): The layr to store dissolved buffers
        buffer_dist (optional, int): Distance for the buffer, default = 20 m
    """
    arcpy.analysis.Buffer(
        in_features=in_layer,
        out_feature_class=buffer_layer,
        buffer_distance_or_field=buffer_dist,
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_field=[]
    )
    
    arcpy.management.Dissolve(
        in_features=buffer_layer,
        out_feature_class=dissolved_layer,
        dissolve_field=[],
        multi_part="SINGLE_PART"
    )

# ========================

if __name__ == "__main__":
    main()
