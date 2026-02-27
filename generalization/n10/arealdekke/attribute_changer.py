# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from tqdm import tqdm

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_land_use import Land_use_N10
from input_data import input_n10, input_n100

# ========================
# Program
# ========================


@timing_decorator
def main():
    """
    Main program generalizing farmland for N10.
    """
    environment_setup.main()
    print("\nChanges attributes for land use...\n")

    # Sets up work file manager and creates temporarily files
    working_fc = Land_use_N10.attribute_changer__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)
    files["area"] = Land_use_N10.attribute_changer_area__n10_land_use.value

    MUNICIPALITY = "Drammen"
    fetch_data(files=files, area=MUNICIPALITY)

    ########################################################
    # Print all unique combinations of 'arealdekke' and
    # 'arealbruk_hovedklasse' along with their counts

    # print_unique_combinations_and_count(files=files)
    ########################################################

    change_attributes(files=files)

    arcpy.management.CopyFeatures(
        in_features=files["attribute_file"],
        out_feature_class=Land_use_N10.attribute_changer_output__n10_land_use.value
    )

    wfm.delete_created_files()

    print("\nAttributes for land use have been changed successfully!\n")


# ========================
# Main functions
# ========================


@timing_decorator
def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of generalizing farmland.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    attribute_file = wfm.build_file_path(file_name="attribute_file", file_type="gdb")
    
    return {"attribute_file": attribute_file}


@timing_decorator
def fetch_data(files: dict, area: str = None) -> None:
    """
    Collects relevant data and clips it to desired area if required.

    Args:
        files (dict): Dictionary with all the working files
        area (str, optional): Municipality name to clip data to (defaults to None)
    """
    if not arcpy.Exists(files["area"]):
        if area:
            clip_lyr = "clip_lyr"
            arcpy.management.MakeFeatureLayer(
                input_n100.AdminFlate, clip_lyr, f"NAVN = '{area}'"
            )
            arcpy.analysis.Clip(
                in_features=input_n10.arealdekkeflate,
                clip_features=clip_lyr,
                out_feature_class=files["area"],
            )
        else:
            arcpy.Copy_management(input_n10.arealdekkeflate, files["area"])
    arcpy.management.CopyFeatures(files["area"], files["attribute_file"])


@timing_decorator
def change_attributes(files: dict) -> None:
    """
    Sets attribute 'arealdekke' equal to attribute 'arealbruk_hovedklasse'
    for all features, except for those where 'arealdekke' is in the "keep" set.

    Args:
        files (dict): Dictionary with all the working files
    """
    fc = files["attribute_file"]
    attribute_1 = "arealdekke"
    attribute_2 = "arealbruk_hovedklasse"

    keep = set([
        "samferdsel", "skog", # arealdekke
        "landbrukfiske" # arealbruk_hovedklasse
    ])

    keep_farmland = set([
        "naeringtjeneste", "tekninfrastr", "landbrukfiske", "fritidsbebyggelse", "boligbebyggelse"
    ])

    adjust_built_up_area = set([
        "idrettsomr", "groenneomr", "uklassifisertbeb"
    ])

    unique_vals_1 = set()
    unique_vals_2 = set()
    with arcpy.da.SearchCursor(fc, [attribute_1, attribute_2]) as cursor:
        for row in cursor:
            unique_vals_1.add(row[0])
            unique_vals_2.add(row[1])

    lyr = "temp_layer"
    arcpy.management.MakeFeatureLayer(fc, lyr)

    for v1 in tqdm(
        unique_vals_1, desc="Rewrites attributes", colour="yellow", leave=False
    ):
        if v1.lower() in keep:
            continue
        for v2 in unique_vals_2:
            if v2 is None:
                continue
            elif "jordbruk" in v1.lower() and v2.lower() in keep_farmland:
                continue
            elif v1.lower() == "bebygd" and v2.lower() not in adjust_built_up_area:
                continue
            elif v2.lower() in keep:
                continue
            try:
                where = f"{attribute_1} = '{v1}' AND {attribute_2} = '{v2}'"
                arcpy.management.SelectLayerByAttribute(lyr, "NEW_SELECTION", where)
                count = int(arcpy.management.GetCount(lyr)[0])
                if count > 0:
                    with arcpy.da.UpdateCursor(
                        lyr, [attribute_1, attribute_2]
                    ) as cursor:
                        for _, a2 in cursor:
                            cursor.updateRow([a2, a2])
            except:
                continue


# ========================
# Helper functions
# ========================


def print_unique_combinations_and_count(files: dict) -> None:
    """
    Prints the unique combinations of specific attributes
    along with their counts.

    Args:
        files (dict): Dictionary with all the working files
    """
    fc = files["attribute_file"]
    attribute_1 = "arealdekke"
    attribute_2 = "arealbruk_hovedklasse"

    unique_vals_1 = set()
    unique_vals_2 = set()
    with arcpy.da.SearchCursor(fc, [attribute_1, attribute_2]) as cursor:
        for row in cursor:
            unique_vals_1.add(row[0])
            unique_vals_2.add(row[1])

    lyr = "temp_layer"
    arcpy.management.MakeFeatureLayer(fc, lyr)

    for v1 in unique_vals_1:
        for v2 in unique_vals_2:
            try:
                where = f"{attribute_1} = '{v1}' AND {attribute_2} = '{v2}'"
                arcpy.management.SelectLayerByAttribute(lyr, "NEW_SELECTION", where)
                count = int(arcpy.management.GetCount(lyr)[0])
                if count > 0:
                    print(f"Combination: {v1}, {v2} => Count: {count}")
            except:
                continue


# ========================

if __name__ == "__main__":
    main()
