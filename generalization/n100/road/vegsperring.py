# Importing packages
import arcpy

arcpy.env.overwriteOutput = True

# Importing custom modules
from file_manager.n100.file_manager_roads import Road_N100
from custom_tools.decorators.timing_decorator import timing_decorator

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input_road": Road_N100.roundabout__cleaned_road__n100_road.value,
    "input_vegsperring": Road_N100.data_selection___vegsperring___n100_road.value,
    "veg_uten_bom": Road_N100.vegsperring__veg_uten_bom__n100_road.value,
}


@timing_decorator
def remove_roadblock():
    """
    Identifies every road having some kind of roadblock 2 m from the
    centre line and marks them with either "ja" (yes) or "nei" (no).
    """
    road_fc = data_files["input_road"]
    roadblock_fc = data_files["input_vegsperring"]
    output = data_files["veg_uten_bom"]

    arcpy.management.MakeFeatureLayer(
        in_features=road_fc, out_layer="road_lyr", where_clause="medium = 'T'"
    )
    arcpy.management.MakeFeatureLayer(
        in_features=roadblock_fc, out_layer="roadblock_lyr"
    )
    arcpy.analysis.Near(
        in_features="roadblock_lyr",
        near_features="road_lyr",
        search_radius="5 Meters",
        location="NO_LOCATION",
        angle="NO_ANGLE",
    )

    near_ids = {
        row[0]
        for row in arcpy.da.SearchCursor("roadblock_lyr", ["NEAR_FID"])
        if row[0] != -1
    }

    arcpy.management.AddField(
        in_table=road_fc, field_name="har_bom", field_type="TEXT", field_length=10
    )
    with arcpy.da.UpdateCursor(road_fc, ["OID@", "har_bom"]) as cursor:
        for oid, bom in cursor:
            if oid in near_ids:
                bom = "ja"
            else:
                bom = "nei"
            cursor.updateRow([oid, bom])
    arcpy.management.CopyFeatures(road_fc, output)
