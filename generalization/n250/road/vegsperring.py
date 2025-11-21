# Importing packages
import arcpy

arcpy.env.overwriteOutput = True

# Importing custom modules
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager.n250.file_manager_roads import Road_N250
from input_data import input_n100

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input_road": Road_N250.roundabout__cleaned_road__n250_road.value,
    "input_vegsperring": Road_N250.data_selection___vegsperring___n250_road.value,
    "veg_uten_bom": Road_N250.vegsperring__veg_uten_bom__n250_road.value,
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

    # Fetch the relevant roads
    arcpy.management.MakeFeatureLayer(
        in_features=road_fc, out_layer="road_lyr", where_clause="medium = 'T'"
    )

    # Create near table with connections to roadblocks
    near_table = r"in_memory/near_table"
    arcpy.analysis.GenerateNearTable(
        in_features=roadblock_fc,
        near_features="road_lyr",
        out_table=near_table,
        search_radius="2 Meters",
        closest="ALL",
        location="NO_LOCATION",
        angle="NO_ANGLE",
    )

    # Fetch all the road oids with roadblocks
    road_oids_with_roadblock = set()
    if arcpy.Exists(near_table):
        with arcpy.da.SearchCursor(near_table, ["NEAR_FID"]) as search:
            for row in search:
                if row[0] is not None and row[0] != -1:
                    road_oids_with_roadblock.add(row[0])

    # If no roadblocks detected, just return input
    if not road_oids_with_roadblock:
        arcpy.management.CopyFeatures(road_fc, output)
        arcpy.management.Delete(near_table)
        return

    # Select roads with bom
    oid_field = arcpy.Describe(road_fc).OIDFieldName
    oid_list_str = ",".join(map(str, road_oids_with_roadblock))
    where_clause = f"{oid_field} IN ({oid_list_str})"
    arcpy.management.MakeFeatureLayer(
        in_features=road_fc,
        out_layer="roads_with_roadblock_lyr",
        where_clause=where_clause,
    )

    # Create layer with urban areas
    arcpy.management.MakeFeatureLayer(
        in_features=input_n100.ArealdekkeFlate,
        out_layer="urban_areas_lyr",
        where_clause="OBJTYPE IN ('Tettbebyggelse', 'BymessigBebyggelse')",
    )

    # Spatial join to collect roadblocks in urban areas
    joined = r"in_memory/roads_with_bom_joined"
    arcpy.analysis.SpatialJoin(
        target_features="roads_with_roadblock_lyr",
        join_features="urban_areas_lyr",
        out_feature_class=joined,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        match_option="WITHIN",
    )

    # Find oids in urban areas
    important_oids = set()
    if arcpy.Exists(joined):
        join_oid_field = "TARGET_FID"
        join_count_field = "Join_Count"
        fields = [f.name for f in arcpy.ListFields(joined)]
        if join_oid_field in fields and join_count_field in fields:
            with arcpy.da.SearchCursor(
                joined, [join_oid_field, join_count_field]
            ) as search:
                for target_fid, join_count in search:
                    if join_count is not None and int(join_count) > 0:
                        important_oids.add(int(target_fid))

    # Fetch the oids to delete
    to_delete = road_oids_with_roadblock.intersection(important_oids)

    if to_delete:
        arcpy.management.MakeFeatureLayer(road_fc, "to_delete_lyr")
        where_clause = f"{oid_field} IN ({','.join(map(str, to_delete))})"
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view="to_delete_lyr",
            selection_type="NEW_SELECTION",
            where_clause=where_clause,
        )
        arcpy.management.DeleteFeatures("to_delete_lyr")

    # Copy the result
    arcpy.management.CopyFeatures(road_fc, output)

    # Clean up
    for tmp in (joined, near_table):
        if arcpy.Exists(tmp):
            arcpy.management.Delete(tmp)
