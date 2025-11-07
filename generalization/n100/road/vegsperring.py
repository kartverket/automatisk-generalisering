# Importing packages
import arcpy

arcpy.env.overwriteOutput = True

# Importing custom modules
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager.n100.file_manager_roads import Road_N100
from input_data import input_n100

data_files = {
    # Stores all the relevant file paths to the geodata used in this Python file
    "input_road": Road_N100.roundabout__cleaned_road__n100_road.value,
    "input_vegsperring": Road_N100.data_selection___vegsperring___n100_road.value,
    "veg_uten_bom": Road_N100.vegsperring__veg_uten_bom__n100_road.value,
}

"""
Documentation of the development process:

During the development of this code, some different approaches were tested. The code was tested for the municipalities Ringerike and Hole.

1) The first attempt created a new attribute "har_bom" (has roadblock) describing the occurrence of roadblock(s) on the road instance. This attribute was
used to increase the hierarchy level to a less prioritized instance in the thin-road function. The result produced a road network without the roadblocks in
urban areas, but most of the roadblock roads were kept since they are mostly represented in wilderness areas as the only option.
Here, all roadblocks were treated as equally important and the hierarchy was changed equally for all instances. In most cases the results were satisfying,
but some special occurrences made 'islands' of roads that are not desirable.

2) Secondly, we tried to differentiate between the types of roadblocks. The different roadblock types were placed into three categories depending on the degree
to which it is possible to get through the roadblock. The "har_bom" attribute was modified so that it could hold a number depending on category and increase the
hierarchy level in thin-roads accordingly.
On the other hand, some of the roadblock types were highly overrepresented in the dataset and represented in both urban and wilderness areas.
As we use thin-roads twice - first for both roads and paths, then only for paths - we tried to change the hierarchy levels so that all paths received a worse
hierarchy level than the roads in the first loops. We use 6 hierarchy levels (0 to 5). The municipalities tested this approach both with divided hierarchy (roads: 0-4,
paths: 5) and with shared hierarchy (everything: 0-5).
None of the results were perfect. Some of the missing roads were also roads not affected by "har_bom", so thin-roads did more...

3) The final approach, which became the final solution (code below), captured all roadblocks inside urban areas and cities and removed these road instances
completely from the dataset before thin-roads. The "har_bom" attribute was removed completely and no longer effecting the hierarchy levels in thin-roads.
The result now does not contain any roads going near roadblocks in these areas, but critical roads in wilderness areas are still present. There are no 'islands'
in the road network anymore, but in some places road segments can be removed seemingly at random. The result is that only paths or tractor roads are connected to
these roads, but if we look further out from the municipality, they are connected to roads from the other side. It is then a longer road segment going through,
for example, a forest having a small gap in the middle. The road has a roadblock, but the removed segment does not.
"""

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

    near_data = {
        near: [geom, bom]
        for geom, bom, near in arcpy.da.SearchCursor(
            "roadblock_lyr", ["SHAPE@", "TYPE", "NEAR_FID"]
        )
        if near != -1
    }

    arcpy.management.MakeFeatureLayer(
        in_features=input_n100.ArealdekkeFlate,
        out_layer="Tettbebyggelse_lyr",
        where_clause="OBJTYPE IN ('Tettbebyggelse', 'BymessigBebyggelse')",
    )

    to_delete = []

    with arcpy.da.UpdateCursor(road_fc, ["OID@"]) as cursor:
        for row in cursor:
            oid = row[0]
            if oid in near_data:
                important = False
                arcpy.management.SelectLayerByAttribute(
                    "road_lyr", "NEW_SELECTION", where_clause=f"OBJECTID = {oid}"
                )
                arcpy.management.SelectLayerByLocation(
                    in_layer="Tettbebyggelse_lyr",
                    overlap_type="CONTAINS",
                    select_features="road_lyr",
                    search_distance="0 Meters",
                    selection_type="NEW_SELECTION",
                )
                count = int(
                    arcpy.management.GetCount("Tettbebyggelse_lyr").getOutput(0)
                )
                if count > 0:
                    important = True

                if important:
                    to_delete.append(oid)

    if to_delete:
        oid_field = arcpy.Describe(road_fc).OIDFieldName
        oid_list_str = ",".join(str(i) for i in to_delete)
        where = f"{oid_field} IN ({oid_list_str})"
        arcpy.management.MakeFeatureLayer(
            in_features=road_fc, out_layer="to_delete_lyr"
        )
        arcpy.management.SelectLayerByAttribute(
            "to_delete_lyr", "NEW_SELECTION", where_clause=where
        )
        arcpy.management.DeleteFeatures("to_delete_lyr")

    arcpy.management.CopyFeatures(road_fc, output)
