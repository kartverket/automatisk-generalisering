# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager.n10.file_manager_land_use import Land_use_N10
from input_data import input_test_data


# ========================
# Program
# ========================


@timing_decorator
def adjusting_surrounding_geometries(input: str, changed_area: str) -> None:
    """
    Adjust land use that intersects with 'changed_area'
    that have been enlarged to preserve topology.

    Args:
        input (str): Input feature class with overlapping land use
        changed_area (str): The field name value of the land
                            use 'arealdekke' that is enlarged
                            and overlaps other areas
    
    Concept:
        0) Input feature class contains a complete land use, where one specific value of 'arealdekke' overlaps other areas
        1) Select all features with 'arealdekke' equal to 'changed_area' and keep these as locked features
        2) Select all features that overlaps with the locked features
        3) Create a dictionary with: key: locked area ID, value: the geometry of the bounding line
        4) For each of the overlapping features:
            a) Use PolygonToLine to get the bounding line geometry
            b) Identify the points on the edge of locked area and those within
            c) Remove the points within
            d) Fetch the line of the locked featyre between the intersecting points
            e) Add these points to the original line geometry
    """


# ========================
# Main functions
# ========================


# ========================
# Helper functions
# ========================


# ========================


if __name__ == "__main__":
    working_fc = Land_use_N10.area_line_merger_start__n10_land_use.value

    attribute = "Ferskvann_elv_bekk"

    if not arcpy.Exists(working_fc):
        input_fc = input_test_data.arealdekke
        elv_fc = input_test_data.elv

        arealdekke_lyr = "arealdekke_lyr"
        arcpy.management.MakeFeatureLayer(input_fc, arealdekke_lyr, where_clause=f"arealdekke = '{attribute}'")

        temp_merge_fc = r"in_memory/temp_merge_fc"
        temp_dissolve_fc = r"in_memory/temp_dissolved_fc"

        arcpy.management.Merge(
            inputs=[elv_fc, arealdekke_lyr],
            output=temp_merge_fc
        )

        arcpy.management.Dissolve(
            in_features=temp_merge_fc,
            out_feature_class=temp_dissolve_fc,
            dissolve_field="arealdekke"
        )

        arcpy.management.SelectLayerByAttribute(arealdekke_lyr, selection_type="SWITCH_SELECTION")

        arcpy.management.Merge(
            inputs=[temp_dissolve_fc, arealdekke_lyr],
            output=working_fc
        )
