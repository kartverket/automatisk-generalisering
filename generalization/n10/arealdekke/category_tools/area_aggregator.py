# Libraries

import arcpy

arcpy.env.overwriteOutput = True
arcpy.env.referenceScale = "10000"

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

input_fc = r"C:\GIS_Files\ag_outputs\n10\land_use.gdb\B_dissolve___arealdekke___n10_land_use"

# ========================
# Main function
# ========================

@timing_decorator
def aggregate_category():
    working_fc = Arealdekke_N10.category_aggregator__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    land_use_lyr = "land_use_lyr"
    arcpy.MakeFeatureLayer_management(
        in_features=input_fc, out_layer=land_use_lyr
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="arealdekke = 'Høyblokkbebyggelse'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["target"]
    )

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="arealdekke = 'Bebygd'",
    )
    arcpy.management.CopyFeatures(
        in_features=land_use_lyr, out_feature_class=files["near"]
    )

    arcpy.cartography.DelineateBuiltUpAreas(
        in_buildings=files["target"],
        edge_features=files["near"],
        grouping_distance=20,
        minimum_detail_size=10,
        out_feature_class=files["aggregated"],
        minimum_building_count=1,
    )

# ========================
# Helper function
# ========================

def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    return {
        "target": wfm.build_file_path(file_name="target", file_type="gdb"),
        "near": wfm.build_file_path(file_name="near", file_type="gdb"),
        "aggregated": wfm.build_file_path(file_name="aggregated", file_type="gdb"),
    }

# ========================

if __name__ == "__main__":
    aggregate_category()