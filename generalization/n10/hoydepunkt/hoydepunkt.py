import arcpy
import arcpy.cim
import arcpy.cim.CIMEnum as cimenum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from env_setup import environment_setup
from file_manager import WorkFileManager
from file_manager.n10.file_manager_hoydepunkt import Hoydepunkt_N10
from input_data import input_n10

import re
from typing import Dict
import os
import copy

arcpy.env.overwriteOutput = True


@timing_decorator
def main():
    """
    Main function that runs the entire process of generalizing the height points for N10 and creating labels and annpotations for those points.

    To create annotations you need:
    - we need an arcgis project to create labels
    - the arcgis project needs to include the layers you want the annotations to avoid. (we set all feature weights to 1000 to make sure the labels avoid all features)
    - If db connection is used in the project you need to create a connection file using arcpy.management.CreateDatabaseConnection


    """
    ######### PROJECT AND DBCONNECTION SETUP ############
    db_con="PATH TO DBCONNECTION FILE"
    project="PATH TO ARCGIS PROJECT"
    ###################################################

    environment_setup.main()
    
    working_fc = Hoydepunkt_N10.hoydepunkt_n10.value
    config = core_config.WorkFileConfig(root_file=working_fc)
    wfm = WorkFileManager(config=config)
    
  

    files = create_wfm_gdbs(wfm=wfm)

    distance = "250 Meters"
    fetch_data(files=files)
    select_forsenkningspunkt(files=files, distance=distance)
    select_terrengpunkt(files=files, distance=distance)
    remove_points_in_bebygd(files=files, distance="30 Meters")
    merge_and_add_medium(files=files)
    populate_hoyde_int(files=files)
    objtype(files=files)
    add_nato_codes(files=files)
    output_hoydepunkt(files=files)
    label_hoyde_int(files=files, annotations=True, db_con=db_con, project=project)

    wfm.delete_created_files()
    

@timing_decorator
def objtype(files: dict) -> None:
    """
    moves objtype to new column and writes "høydepunkt" in the objtype column
    """
    arcpy.management.AddField(
        in_table=files["hoydepunkt_n10"], field_name="hoydepunkt_type", field_type="TEXT",)
    
    with arcpy.da.UpdateCursor(files["hoydepunkt_n10"], ["objtype", "hoydepunkt_type"]) as u_cur:
        for row in u_cur:
            row[1] = row[0]
            row[0] = "høydepunkt"
            u_cur.updateRow(row)

@timing_decorator
def label_hoyde_int(files: dict = None, annotations: bool = False,  db_con: str = None, project: str = None) -> None:
    """
    Labels the hoyde_int field in the final hoydepunkt_n10 feature class. If annotations is set to True, it also creates annotations for the labels.
    Label gets saved only in the project, annotations get saved in the same place as the høydepunkt fc
    """
    if db_con is not None:
        orig_workspace = arcpy.env.workspace
        arcpy.env.workspace = db_con


    layer_name = os.path.basename(Hoydepunkt_N10.hoydepunkt_n10.value)
    
    p = arcpy.mp.ArcGISProject(project)
    m = p.listMaps('Map')[0]
    
    layer_list = m.listLayers()
    # Set feature weight to 1000 for all layers to make sure labels avoid all features
    for lyr in layer_list:
        print(lyr)
        if lyr.name == layer_name:
            print("remove: layer")
            m.removeLayer(lyr)
            continue
        
        if getattr(lyr, "isGroupLayer", False):
            group_layer_list = lyr.listLayers()
            for l in group_layer_list:
                lyr_cim = l.getDefinition('V3')
                for i in range(len(lyr_cim.labelClasses)):
                    labelclass = lyr_cim.labelClasses[i]
                    labelclass.maplexLabelPlacementProperties.featureWeight = 1000
                l.setDefinition(lyr_cim)
        else:
        
            lyr_cim = lyr.getDefinition('V3')
            for i in range(len(lyr_cim.labelClasses)):
                labelclass = lyr_cim.labelClasses[i]
                labelclass.maplexLabelPlacementProperties.featureWeight = 1000
            lyr.setDefinition(lyr_cim)
    
    

        
    m.addDataFromPath(Hoydepunkt_N10.hoydepunkt_n10.value)
    l = m.listLayers(layer_name)[0]
    
    
    # edit the label class
    l.showLabels = True
    if l.showLabels == True:
        print("Labels are enabled")
    lyr_cim = l.getDefinition('V3')
    lyrlclass = lyr_cim.labelClasses[0]
    lyrlclass.name = "medium T"
    lyrlclass.expressionEngine = cimenum.LabelExpressionEngine.Arcade 
    lyrlclass.expression = "$feature.hoyde_int"
    lyrlclass.expressionTitle = "hoyde_int"    
    lyrlclass.visibility = True
    lyrlclass.maplexLabelPlacementProperties.featureWeight = 10
    lyrlclass.whereClause = "medium <> 'I'"
        
    lyrlclass.textSymbol.symbol.fontFamilyName = "Arial"
    lyrlclass.textSymbol.symbol.fontStyleName = "regular"
    lyrlclass.textSymbol.symbol.height = 8
    lyrlclass.textSymbol.symbol.symbol.symbolLayers[0].color = {'type': 'CIMCMYKColor', 'colorSpace': "DeviceCMYK", 'values': [0, 0, 0, 100, 100]}
    

    second_lc = copy.deepcopy(lyrlclass) 
    second_lc.name = "medium I"
    second_lc.whereClause = "medium = 'I'"
    second_lc.textSymbol.symbol.symbol.symbolLayers[0].color = {'type': 'CIMCMYKColor', 'colorSpace': "DeviceCMYK", 'values': [100, 0, 0, 0, 100]}
    lyr_cim.labelClasses.append(second_lc)

    l.setDefinition(lyr_cim)
    l.setDefinition(l.getDefinition("V3"))

    m.referenceScale = 10000

    p.save()
    

    if annotations:
        if arcpy.Exists(f"{Hoydepunkt_N10.hoydepunkt_n10.value}Anno10000"):
            arcpy.management.Delete(f"{Hoydepunkt_N10.hoydepunkt_n10.value}Anno10000")

        arcpy.cartography.TiledLabelsToAnnotation(
            input_map=m,
            polygon_index_layer=input_n10.AdminFlate,
            out_geodatabase=os.path.dirname(Hoydepunkt_N10.hoydepunkt_n10.value),
            out_layer="hoydepunkt_n10_anno",
            generate_unplaced_annotation="GENERATE_UNPLACED_ANNOTATION",
            which_layers="SINGLE_LAYER",
            single_layer=layer_name,
        )

        arcpy.management.CopyFeatures(
            in_features=f"{Hoydepunkt_N10.hoydepunkt_n10.value}Anno10000", 
            out_feature_class=f"{Hoydepunkt_N10.hoydepunkt_n10.value}Anno10000_DI"
        )
        
        arcpy.management.DeleteIdentical(
        in_dataset=f"{Hoydepunkt_N10.hoydepunkt_n10.value}Anno10000_DI", 
        fields=["FeatureID"]
        )

    if db_con is not None:
        # reset workspace
        arcpy.env.workspace = orig_workspace




def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to
    be used during the process of generalizing power lines.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """

    hoydepunkt_n50 = wfm.build_file_path(file_name="hoydepunkt_n50", file_type="gdb")
    forsenkningspunkt_fkb = wfm.build_file_path(file_name="forsenkningspunkt_fkb", file_type="gdb")
    terrengpunkt_fkb = wfm.build_file_path(file_name="terrengpunkt_fkb", file_type="gdb")
    n50_hoydepunkt_buffers = wfm.build_file_path(file_name="n50_hoydepunkt_buffers", file_type="gdb")
    selected_forsenkningspunkt = wfm.build_file_path(file_name="selected_forsenkningspunkt", file_type="gdb")
    selected_forsenkningspunkt_buffers = wfm.build_file_path(file_name="selected_forsenkningspunkt_buffers", file_type="gdb")
    selected_terrengpunkt = wfm.build_file_path(file_name="selected_terrengpunkt", file_type="gdb")
    hoydepunkt_n10 = wfm.build_file_path(file_name="hoydepunkt_n10", file_type="gdb")
    isbreFlate = wfm.build_file_path(file_name="isbreFlate", file_type="gdb")
    ArealdekkeFlate_bebygd = wfm.build_file_path(file_name="ArealdekkeFlate_bebygd", file_type="gdb")
    
    

    return {
       "hoydepunkt_n50": hoydepunkt_n50,
       "forsenkningspunkt_fkb": forsenkningspunkt_fkb,
       "terrengpunkt_fkb": terrengpunkt_fkb,
       "n50_hoydepunkt_buffers": n50_hoydepunkt_buffers,
       "selected_forsenkningspunkt": selected_forsenkningspunkt,
       "selected_forsenkningspunkt_buffers": selected_forsenkningspunkt_buffers,
       "selected_terrengpunkt": selected_terrengpunkt,
       "hoydepunkt_n10": hoydepunkt_n10,
       "isbreFlate": isbreFlate,
       "ArealdekkeFlate_bebygd": ArealdekkeFlate_bebygd,
    }

@timing_decorator
def fetch_data(files: dict) -> None:
    """
    Fetches relevant data.
    """
    arcpy.management.CopyFeatures(
        in_features=input_n10.N50HoydePunkt, out_feature_class=files["hoydepunkt_n50"]
    )
    arcpy.management.CopyFeatures(
        in_features=input_n10.FKBforsenkningspunkt, out_feature_class=files["forsenkningspunkt_fkb"]
    )
    arcpy.management.CopyFeatures(
        in_features=input_n10.FKBterrengpunkt, out_feature_class=files["terrengpunkt_fkb"]
    )
    arcpy.management.CopyFeatures(
        in_features=input_n10.ArealdekkeFlate_bebygd, out_feature_class=files["ArealdekkeFlate_bebygd"]
    )

    arcpy.management.CopyFeatures(
        in_features=input_n10.ArealdekkeFlate, out_feature_class="in_memory\\arealdekkeFlate"
    )
    arcpy.management.MakeFeatureLayer(
        in_features="in_memory\\arealdekkeFlate", out_layer="arealdekkeFlate_lyr"
    )
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view="arealdekkeFlate_lyr", selection_type="NEW_SELECTION", where_clause="objtype = 'SnøIsbre'"
    )
    arcpy.management.CopyFeatures(
        in_features="arealdekkeFlate_lyr", out_feature_class=files["isbreFlate"]
    )

@timing_decorator
def output_hoydepunkt(files: dict):
    arcpy.management.CopyFeatures(
        in_features=files["hoydepunkt_n10"], out_feature_class=Hoydepunkt_N10.hoydepunkt_n10.value
    )

@timing_decorator
def add_nato_codes(files: dict):
    """
    Adds the relevant nato codes for the height points
    """
    fc = files["hoydepunkt_n10"]
    arcpy.management.AddField(
        in_table=fc, field_name="dgfcd_feature_alpha", field_type="TEXT", 
    )
    arcpy.management.AddField(
        in_table=fc, field_name="dgfcd_feature_531", field_type="TEXT", 
    )
    arcpy.management.AddField(
        in_table=fc, field_name="msl", field_type="TEXT", 
    )
    arcpy.management.AddField(
        in_table=fc, field_name="esc", field_type="TEXT", 
    )
    arcpy.management.AddField(
        in_table=fc, field_name="suy", field_type="TEXT", 
    )

    arcpy.management.AddField(
        in_table=fc, field_name="dgif_ccode", field_type="TEXT", 
    )

    fields = ["objtype", "hoyde", "medium", "dgfcd_feature_alpha", "dgfcd_feature_531", "msl", "esc", "suy", "dgif_ccode"]
    with arcpy.da.UpdateCursor(fc, fields) as u_cur:
        for row in u_cur:
            objtype = row[0]
            hoyde = row[1]
            medium = row[2]

            row[5] = hoyde

            if medium == "I":
                row[6] = "2"
            else: 
                row[6] = "1"


            if objtype == "TrigonometriskPunkt":
                row[3] = "surveyPointType"
                row[4] = "ZB050"
                row[7] = "5"

            else:
                row[3] = "SpotElevation"
                row[4] = "CA030"
            

            row[8] = f"{row[4]}_MSL_{row[5]}"
            u_cur.updateRow(row)

                


@timing_decorator
def remove_points_in_bebygd(files : dict, distance: str) -> None:
    """
    Removes points that are in bebygde areas from the forsenkningspunkt and terrengpunkt layers
    """

    near_table = "in_memory\\near_table"
    for fc_name in ["selected_terrengpunkt", "selected_forsenkningspunkt"]:
        print(fc_name)
        
        arcpy.analysis.GenerateNearTable(
            in_features=files[fc_name],
            near_features=files["ArealdekkeFlate_bebygd"],
            out_table=near_table,
            search_radius=distance,
            closest="CLOSEST"
        )
        print("near table done")

        oid_delete = set()
        with arcpy.da.SearchCursor(near_table, ["IN_FID"]) as cur:
            for row in cur:
                oid_delete.add(row[0])
        
        with arcpy.da.UpdateCursor(files[fc_name], ["OID@"]) as u_cur:
            for row in u_cur:
                if row[0] in oid_delete:
                    u_cur.deleteRow()


            

@timing_decorator
def select_forsenkningspunkt(files: dict, distance: str) -> None:
    """
    Selects forsenkningspunkt that are distance from n50_hoydepunkt and other forsenkningspunkt
    """
    arcpy.analysis.Buffer(
        in_features=files["hoydepunkt_n50"], out_feature_class=files["n50_hoydepunkt_buffers"], buffer_distance_or_field=distance
    )

    fkb_forsenkningspunkt_lyr = "fkb_forsenkningspunkt_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["forsenkningspunkt_fkb"], out_layer=fkb_forsenkningspunkt_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_forsenkningspunkt_lyr, overlap_type="INTERSECT", select_features=files["n50_hoydepunkt_buffers"], selection_type="NEW_SELECTION", invert_spatial_relationship="INVERT"
    )

    near_table = "in_memory\\near_table"
    arcpy.analysis.GenerateNearTable(
        in_features=fkb_forsenkningspunkt_lyr, near_features=fkb_forsenkningspunkt_lyr, out_table=near_table, search_radius=distance, closest="ALL"
    )

    keep_oids = select_points_from_neartable(near_table=near_table, layer=fkb_forsenkningspunkt_lyr)


    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=fkb_forsenkningspunkt_lyr, selection_type="REMOVE_FROM_SELECTION", where_clause=f"OBJECTID NOT IN ({', '.join(map(str, keep_oids))})"
    )


    arcpy.management.CopyFeatures(
        in_features=fkb_forsenkningspunkt_lyr, out_feature_class=files["selected_forsenkningspunkt"]
    )






@timing_decorator
def select_terrengpunkt(files: dict, distance: str) -> None:
    """
    Selects terrengpunkt that are distance from n50_hoydepunkt, forsenkningspunkt and other terrengpunkt
    """
    arcpy.analysis.Buffer(
        in_features=files["selected_forsenkningspunkt"], out_feature_class=files["selected_forsenkningspunkt_buffers"], buffer_distance_or_field=distance
    )

    fkb_terrengpunkt_lyr = "fkb_terrengpunkt_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["terrengpunkt_fkb"], out_layer=fkb_terrengpunkt_lyr
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_terrengpunkt_lyr, overlap_type="INTERSECT", select_features=files["n50_hoydepunkt_buffers"], selection_type="NEW_SELECTION", invert_spatial_relationship="INVERT"
    )
    arcpy.management.SelectLayerByLocation(
        in_layer=fkb_terrengpunkt_lyr, overlap_type="INTERSECT", select_features=files["selected_forsenkningspunkt_buffers"], selection_type="REMOVE_FROM_SELECTION",
    )

    near_table = "in_memory\\near_table"
    arcpy.analysis.GenerateNearTable(
        in_features=fkb_terrengpunkt_lyr, near_features=fkb_terrengpunkt_lyr, out_table=near_table, search_radius=distance, closest="ALL"
    )

    keep_oids = select_points_from_neartable(near_table=near_table, layer=fkb_terrengpunkt_lyr)


    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=fkb_terrengpunkt_lyr, selection_type="REMOVE_FROM_SELECTION", where_clause=f"OBJECTID NOT IN ({', '.join(map(str, keep_oids))})"
    )

    
    arcpy.management.CopyFeatures(
        in_features=fkb_terrengpunkt_lyr, out_feature_class=files["selected_terrengpunkt"]
    )

@timing_decorator
def merge_and_add_medium(files: dict) -> None:
    """
    Merges the selected forsenkningspunkt and terrengpunkt into the final hoydepunkt_n10 feature class
    """
    arcpy.management.Merge(
        inputs=[files["selected_forsenkningspunkt"], files["selected_terrengpunkt"], files["hoydepunkt_n50"]],
        output=files["hoydepunkt_n10"]
    )

    hoydepunkt_n10_lyr = "høydepunkt_n10_lyr"
    arcpy.management.MakeFeatureLayer(
        in_features=files["hoydepunkt_n10"], out_layer=hoydepunkt_n10_lyr
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=hoydepunkt_n10_lyr, overlap_type="INTERSECT", select_features=files["isbreFlate"], selection_type="NEW_SELECTION"
    )

    with arcpy.da.UpdateCursor(hoydepunkt_n10_lyr, ["medium"]) as u_cur:
        for row in u_cur:
            row[0] = "I"
            u_cur.updateRow(row)
    
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=hoydepunkt_n10_lyr, selection_type="CLEAR_SELECTION"
    )

    arcpy.management.SelectLayerByLocation(
        in_layer=hoydepunkt_n10_lyr, overlap_type="INTERSECT", select_features=files["isbreFlate"], selection_type="NEW_SELECTION", invert_spatial_relationship="INVERT"
    )

    with arcpy.da.UpdateCursor(hoydepunkt_n10_lyr, ["medium"]) as u_cur:
        for row in u_cur:
            if row[0] == "I" or row[0] == None:
                row[0] = "T"
                u_cur.updateRow(row)


def _parse_hoyde_text(value: str):
    """
    Normalize a text representation of a number that may use '.' or ',' as decimal
    separators and may include thousands separators. Returns float or None.
    Examples handled:
      "1.234,56" -> 1234.56
      "1234.56"  -> 1234.56
      "1 234,56" -> 1234.56
      "1234,56"  -> 1234.56
      "1000"     -> 1000.0
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None

    # Remove spaces and non-breaking spaces
    s = s.replace("\u00A0", "").replace(" ", "")

    # If both '.' and ',' present, assume '.' is thousands sep and ',' is decimal
    if "." in s and "," in s:
        s = s.replace(".", "")      # remove thousands separator
        s = s.replace(",", ".")     # convert decimal comma to dot
    else:
        # If only comma present, treat it as decimal separator
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        # If only dot present, assume it's decimal separator already
        # If neither present, it's an integer-like string

    # Remove any characters that are not digits, minus sign, or dot
    s = re.sub(r"[^0-9\.\-]", "", s)

    # Final sanity check
    if s in ("", ".", "-", "-.", ".-"):
        return None

    try:
        return float(s)
    except ValueError:
        return None

def populate_hoyde_int(files: Dict[str, str]) -> None:
    """
    Populates the hoyde_int field in the final hoydepunkt_n10 feature class
    using the text field 'hoyde'. Non-numeric or empty values are left as None.
    """
    fc = files["hoydepunkt_n10"]
    text_field = "hoyde"
    int_field = "hoyde_int"

    # Ensure the integer field exists (AddField already called elsewhere, but safe to check)
    existing_fields = [f.name for f in arcpy.ListFields(fc)]
    if int_field not in existing_fields:
        arcpy.management.AddField(fc, int_field, "SHORT")

    # Use an update cursor to populate the integer field
    count_updated = 0
    count_skipped = 0
    with arcpy.da.UpdateCursor(fc, [text_field, int_field]) as cursor:
        for row in cursor:
            raw = row[0]
            parsed = _parse_hoyde_text(raw)
            if parsed is None:
                # set to None / NULL in geodatabase
                row[1] = None
                count_skipped += 1
            else:
                # round to nearest integer 
                int_val = int(round(parsed))
                row[1] = int_val
                count_updated += 1
            cursor.updateRow(row)

    arcpy.AddMessage(f"populate_hoyde_int: updated {count_updated} rows, skipped {count_skipped} rows.")





def select_points_from_neartable(near_table: str, layer: str) -> list:
    """
    Selects points to keep based on a near table using a greedy algorithm to maximize the number of points kept
    """
    adj = {}
    oids = set()
    with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cur:
        for in_fid, near_fid in cur:
            if in_fid == near_fid:
                continue

            adj.setdefault(in_fid, set()).add(near_fid)
            adj.setdefault(near_fid, set()).add(in_fid)

    with arcpy.da.SearchCursor(layer, ["OID@"]) as cur:
        for row in cur:
            oid = row[0]
            if oid not in adj:
                adj.setdefault(oid, set())
            oids.add(oid)
    

    keep_oids = []

    remaining = set(adj.keys())  


    while remaining:
        # Compute degree restricted to remaining nodes
        degrees = {n: len(adj[n] & remaining) for n in remaining}

        # Pick node with smallest degree; tie-breaker: smallest id for determinism
        node = min(degrees, key=lambda x: (degrees[x], x))

        # Add chosen node to keep list
        keep_oids.append(node)

        # Determine neighbours to remove (only those still remaining)
        neighbours = set(adj[node]) & remaining

        # Remove the chosen node and its neighbours from remaining
        to_remove = neighbours 
        for r in to_remove:
            remaining.discard(r)
        remaining.discard(node)

        # Remove neighbours (and the chosen node) from adjacency dict
        for r in to_remove:
            adj.pop(r, None)
        adj.pop(node, None)

        # Also remove any references to removed nodes from remaining adjacency entries
        for n in list(adj.keys()):
            if adj[n] & to_remove:
                adj[n] -= to_remove

    return keep_oids


if __name__ == "__main__":
    main()



