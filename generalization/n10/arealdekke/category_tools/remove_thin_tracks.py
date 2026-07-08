# Libraries

import arcpy

from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Main function
# ========================


def remove_thin_tracks(
    target: str,
    input_fc: str,
    output_fc: str,
    locked_fc: str,
    complete_fc: str,
    map_scale: str,
):
    """
    For areas of type target, remove all thin tracks of type "Samferdsel"
    that goes through the area. This area should be replaced with the target
    area.

    Args:
        ...
    """
    return


# ========================
# Helper functions
# ========================


# ...


# ========================

if __name__ == "__main__":
    relevant_features = ["Bergverk", "GravUrnelund", "Industri", "Jordbruk"]

    target = relevant_features[0]
    input_fc = Arealdekke_N10.dissolve_gangsykkel.value

    lyr = f"{target}_lyr"
    arcpy.MakeFeatureLayer_management(input_fc, lyr)
    arcpy.SelectLayerByAttribute_management(
        lyr, "NEW_SELECTION", f"arealdekke = '{target}'"
    )
