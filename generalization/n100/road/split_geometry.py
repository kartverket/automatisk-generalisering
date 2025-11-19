# Importing packages
import arcpy
import os

arcpy.env.overwriteOutput = True


def split_polyline_featureclass(
    input_fc: str, dissolve_fc: str, split_fc: str, output_fc: str, interval: float = 500.0
) -> None:
    """
    Divides all the polylines in input_fc into pieces of x meters equal intervall,
    and stores the new geometries in an own output folder.

    Args:
        input_fc (str): The input polylines
        dissolve_fc (str): Layer for dissolved features
        split_fc (str): Layer for the divided geometries
        output_fc (str): Where to store the final single part output geometries
        intervall (float, optional): The split intervall, default: 500 m
    """
    # Fetch fields
    oid_fields = arcpy.Describe(input_fc).OIDFieldName
    join_fields = [f.name for f in arcpy.ListFields(input_fc) if f.type not in ("OID", "Geometry")]

    attr_dict = {}
    read_fields = [oid_fields] + join_fields
    with arcpy.da.SearchCursor(input_fc, read_fields) as cursor:
        for row in cursor:
            oid = row[0]
            values = row[1:]
            attr_dict[oid] = dict(zip(join_fields, values))

    # Dissolve input features
    arcpy.management.Dissolve(
        in_features=input_fc,
        out_feature_class=dissolve_fc,
        dissolve_field=[],
        multi_part="SINGLE_PART",
    )

    # Ensure singlepart layers only
    single_in = r"in_memory/input_singlepart"
    if arcpy.Exists(single_in):
        arcpy.management.Delete(single_in)
    arcpy.management.MultipartToSinglepart(
        in_features=dissolve_fc, out_feature_class=single_in
    )

    # Create the divide layer
    split_gdb = os.path.dirname(split_fc)
    split_name = os.path.basename(split_fc)
    if arcpy.Exists(split_fc):
        arcpy.management.Delete(split_fc)
    desc = arcpy.Describe(single_in)
    spatial_ref = desc.spatialReference
    has_z = "ENABLED" if desc.hasZ else "DISABLED"
    has_m = "ENABLED" if desc.hasM else "DISABLED"
    arcpy.management.CreateFeatureclass(
        out_path=split_gdb,
        out_name=split_name,
        geometry_type="POLYLINE",
        template="",
        has_m=has_m,
        has_z=has_z,
        spatial_reference=spatial_ref,
    )

    # Divide the geometries
    with arcpy.da.SearchCursor(
        single_in, ["SHAPE@"]
    ) as s_cursor, arcpy.da.InsertCursor(split_fc, ["SHAPE@"]) as i_cursor:
        for s_row in s_cursor:
            geom = s_row[0]
            if geom is None:
                # Needs a valid geometry
                continue
            total_len = geom.length
            if total_len <= interval:
                # If the geometry is shorter than the limit, just keep it
                i_cursor.insertRow([geom])
            else:
                # Otherwise -> Split it
                n_full = int(total_len // interval)
                pos = 0.0
                for _ in range(n_full):
                    seg = geom.segmentAlongLine(pos, pos + interval, False)
                    i_cursor.insertRow([seg])
                    pos += interval
                # The rest of the geometry
                if pos < total_len:
                    seg = geom.segmentAlongLine(pos, total_len, False)
                    i_cursor.insertRow([seg])

    # Clean up
    if arcpy.Exists(single_in):
        arcpy.management.Delete(single_in)
    
    # Spatial join to keep attributes
    fm = arcpy.FieldMappings()
    fm.addTable(split_fc)

    # Fill mapping with attributes
    for fld in join_fields:
        fmap = arcpy.FieldMap()
        fmap.addInputField(input_fc, fld)
        
        out_field = fmap.outputField
        out_field.name = fld
        out_field.aliasName = fld
        fmap.outputField = out_field
        fm.addFieldMap(fmap)
    
    # Performe spatial join
    joined_temp = r"in_memory/split_joined"
    if arcpy.Exists(joined_temp):
        arcpy.management.Delete(joined_temp)
    
    arcpy.analysis.SpatialJoin(
        target_features=split_fc,
        join_features=input_fc,
        out_feature_class=joined_temp,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
        field_mapping=fm,
    )

    # Perform multipart to singlepart for final layer
    arcpy.management.MultipartToSinglepart(
        in_features=joined_temp,
        out_feature_class=output_fc,
    )
