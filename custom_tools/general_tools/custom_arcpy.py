from enum import Enum

import arcpy


# Selection Type definition used for select by attribute functions
# Define your enums at the module level
class SelectionType(Enum):
    """
    Summary:
        Enum class that holds the strings for the selection types.
    """

    NEW_SELECTION = "NEW_SELECTION"
    ADD_TO_SELECTION = "ADD_TO_SELECTION"
    REMOVE_FROM_SELECTION = "REMOVE_FROM_SELECTION"
    SUBSET_SELECTION = "SUBSET_SELECTION"
    SWITCH_SELECTION = "SWITCH_SELECTION"
    CLEAR_SELECTION = "CLEAR_SELECTION"


class OverlapType(Enum):
    """
    Summary:
        Enum class that holds the strings for overlap types for select by location.
    """

    INTERSECT = "INTERSECT"
    INTERSECT_3D = "INTERSECT_3D"
    INTERSECT_DBMS = "INTERSECT_DBMS"
    WITHIN_A_DISTANCE = "WITHIN_A_DISTANCE"
    WITHIN_A_DISTANCE_3D = "WITHIN_A_DISTANCE_3D"
    WITHIN_A_DISTANCE_GEODESIC = "WITHIN_A_DISTANCE_GEODESIC"
    CONTAINS = "CONTAINS"
    COMPLETELY_CONTAINS = "COMPLETELY_CONTAINS"
    CONTAINS_CLEMENTINI = "CONTAINS_CLEMENTINI"
    WITHIN = "WITHIN"
    COMPLETELY_WITHIN = "COMPLETELY_WITHIN"
    WITHIN_CLEMENTINI = "WITHIN_CLEMENTINI"
    ARE_IDENTICAL_TO = "ARE_IDENTICAL_TO"
    BOUNDARY_TOUCHES = "BOUNDARY_TOUCHES"
    SHARE_A_LINE_SEGMENT_WITH = "SHARE_A_LINE_SEGMENT_WITH"
    CROSSED_BY_THE_OUTLINE_OF = "CROSSED_BY_THE_OUTLINE_OF"
    HAVE_THEIR_CENTER_IN = "HAVE_THEIR_CENTER_IN"


def resolve_enum(enum_class, value):
    """
    Resolves various types of inputs to their corresponding enum member within a specified enumeration class.

    This function is designed to enhance flexibility in function arguments, allowing the use of enum members,
    their string names, or their values interchangeably. This is particularly useful in scenarios where function parameters might be specified in different formats,
    ensuring compatibility and ease of use.

    Parameters:
        enum_class (Enum): The enumeration class to which the value is supposed to belong.
        value (str, Enum, or any): The input value to resolve. This can be the enum member itself, its string name,
        or its associated value. The function is designed to handle these various formats gracefully.

    """
    if isinstance(value, enum_class):
        return value
    elif isinstance(value, str):
        if value in enum_class.__members__:
            return enum_class[value]
        for member in enum_class:
            if member.value == value:
                return member
    return None


# Define your function using the above enum
def select_attribute_and_make_feature_layer(
    input_layer, expression, output_name, selection_type="NEW_SELECTION", inverted=False
):
    """
    Summary:
        Selects features based on an attribute query and creates a new feature layer with the selected features.

    Details:
        - A temporary feature layer is created from the `input_layer`.
        - The selection type, defined by `selection_type`, is applied to this layer.
        - The selected features are stored in a new temporary feature layer

    Parameters:
        input_layer (str): The path or name of the input feature layer.
        expression (str): The SQL expression for selecting features.
        output_name (str): The name of the output feature layer.
        selection_type (str, optional): Type of selection (e.g., "NEW_SELECTION"). Defaults to "NEW_SELECTION".
        inverted (bool, optional): If True, inverts the selection. Defaults to False.

    Example:
        >>> custom_arcpy.select_attribute_and_make_feature_layer(
        ...     input_layer=input_n100.ArealdekkeFlate,
        ...     expression=urban_areas_sql_expr,
        ...     output_name=Building_N100.data_preparation___urban_area_selection_n100___n100_building.value,
        ... )
        'Building_N100.adding_matrikkel_as_points__urban_area_selection_n100__n100' created temporarily.
    """

    # Resolve selection_type
    selection_type = (
        resolve_enum(SelectionType, selection_type) or SelectionType.NEW_SELECTION
    )

    # Create a temporary feature layer from the input layer
    arcpy.management.MakeFeatureLayer(input_layer, output_name)

    # Perform the attribute selection on the temporary layer
    arcpy.management.SelectLayerByAttribute(
        output_name, selection_type.value, expression, invert_where_clause=inverted
    )

    print(f"{output_name} created temporarily.")


def select_attribute_and_make_permanent_feature(
    input_layer, expression, output_name, selection_type="NEW_SELECTION", inverted=False
):
    """
    Summary:
        Selects features based on an attribute query and creates a new feature layer,
        then stores the selected features permanently in the specified output feature class.

    Details:
        - A temporary feature layer is created from the `input_layer`.
        - The `selection_type` determines how the selection is applied to this layer. If `inverted` is True, the selection is inverted.
        - The selection is done on the feature layer using the `expression`.
        - The selected features are stored permanently in a new feature class specified by `output_name` using copy features.

    Parameters:
        input_layer (str): The path or name of the input feature layer for selection.
        expression (str): The SQL expression used for selecting features.
        output_name (str): The name for the new, permanent output feature class.
        selection_type (str, optional): Specifies the type of selection. Defaults to "NEW_SELECTION".
        inverted (bool, optional): If set to True, inverts the selection. Defaults to False.

    Example:
        >>> custom_arcpy.select_attribute_and_make_permanent_feature(
        ...     input_layer=input_n100.ArealdekkeFlate,
        ...     expression=urban_areas_sql_expr,
        ...     output_name=Building_N100.adding_matrikkel_as_points__urban_area_selection_n100__permanent,
        ... )
        'Building_N100.adding_matrikkel_as_points__urban_area_selection_n100__permanent' created permanently.
    """

    # Resolve selection_type
    selection_type = (
        resolve_enum(SelectionType, selection_type) or SelectionType.NEW_SELECTION
    )

    # Create a temporary feature layer from the input layer
    arcpy.management.MakeFeatureLayer(input_layer, "temp_layer")

    # Perform the attribute selection on the temporary layer
    arcpy.management.SelectLayerByAttribute(
        "temp_layer", selection_type.value, expression, invert_where_clause=inverted
    )

    # Copy only the selected features from the temporary layer into a new feature class
    arcpy.management.CopyFeatures("temp_layer", output_name)

    # Delete the temporary layer to clean up
    arcpy.management.Delete("temp_layer")
    print(f"{output_name} created permanently.")


# Temporary Feature Layer with Location-based Selection
def select_location_and_make_feature_layer(
    input_layer,
    overlap_type,
    select_features,
    output_name,
    selection_type=SelectionType.NEW_SELECTION,
    inverted=False,
    search_distance=None,
):
    """
    Summary:
        Selects features based from the input layer based on their spatial relationship to the selection features
        and creates a new, temporary feature layer as an output.

    Details:
        - Creates a feature layer from the `input_layer`.
        - Depending on the `overlap_type`, features in `input_layer` that spatially relate to `select_features` are selected.
        - If `overlap_type` requires a `search_distance` and it is provided, the distance is used in the selection.
        - The selection can be inverted if `inverted` is set to True.
        - The selected features are stored in a new temporary feature layer named `output_name`.

    Parameters:
        input_layer (str): The path or name of the input feature layer.
        overlap_type (str or OverlapType): The spatial relationship type to use for selecting features.
        select_features (str): The path or name of the feature layer used to select features from the `input_layer`.
        output_name (str): The name of the output feature layer.
        selection_type (SelectionType, optional): Specifies the type of selection. Defaults to SelectionType.NEW_SELECTION.
        inverted (bool, optional): If True, inverts the selection. Defaults to False.
        search_distance (str, optional): A distance value that defines the proximity for selecting features. Required for certain `overlap_type` values.

    Example:
        >>> custom_arcpy.select_location_and_make_feature_layer(
        ...     input_layer=Building_N100.data_preparation___polygons_that_are_large_enough___n100_building.value,
        ...     overlap_type=custom_arcpy.OverlapType.INTERSECT.value,
        ...     select_features=Building_N100.grunnriss_to_point__aggregated_polygon__n100.value,
        ...      output_name=Building_N100.simplify_polygons___not_intersect_aggregated_and_original_polygon___n100_building.value,
        ...     inverted=True,
        ... )
        'grunnriss_to_point__intersect_aggregated_and_original__n100' created temporarily.
    """
    # Resolve overlap_type and selection_type
    overlap_type = resolve_enum(OverlapType, overlap_type) or OverlapType.INTERSECT
    selection_type = (
        resolve_enum(SelectionType, selection_type) or SelectionType.NEW_SELECTION
    )

    arcpy.management.MakeFeatureLayer(input_layer, output_name)

    try:
        # If the overlap type requires a search distance and it's provided
        if overlap_type in [OverlapType.WITHIN_A_DISTANCE] and search_distance:
            arcpy.management.SelectLayerByLocation(
                output_name,
                overlap_type.value,
                select_features,
                search_distance,
                selection_type.value,
                "INVERT" if inverted else "NOT_INVERT",
            )
        else:
            arcpy.management.SelectLayerByLocation(
                output_name,
                overlap_type.value,
                select_features,
                "",
                selection_type.value,
                "INVERT" if inverted else "NOT_INVERT",
            )
        print(f"{output_name} created temporarily.")
    except Exception as e:
        print(f"Error occurred: {e}")


def select_location_and_make_permanent_feature(
    input_layer,
    overlap_type,
    select_features,
    output_name,
    selection_type=SelectionType.NEW_SELECTION,
    inverted=False,
    search_distance=None,
):
    """
    Summary:
        Selects features based from the input layer based on their spatial relationship to the selection features
        and creates a new, permanent feature class as an output.

    Details:
        - Initiates by creating a temporary feature layer from `input_layer`.
        - Applies a spatial selection based on `overlap_type` between the `input_layer` and `select_features`.
        - Utilizes `search_distance` if required by the `overlap_type` and provided, to define the proximity for selection.
        - The selection can be inverted if `inverted` is set to True, meaning it will select all features not meeting the spatial relationship criteria.
        - The selected features are stored permanently in a new feature class specified by `output_name`.
        - Cleans up by deleting the temporary feature layer to maintain a tidy workspace.

    Parameters:
        input_layer (str): The path or name of the input feature layer.
        overlap_type (str or OverlapType): The type of spatial relationship to use for feature selection.
        select_features (str): The feature layer used as a reference for spatial selection.
        output_name (str): The name for the new, permanent feature class to store selected features.
        selection_type (SelectionType, optional): The method of selection to apply. Defaults to SelectionType.NEW_SELECTION.
        inverted (bool, optional): If set to True, the selection will be inverted. Defaults to False.
        search_distance (str, optional): The distance within which to select features, necessary for certain types of spatial selections like WITHIN_A_DISTANCE.

    Example:
        >>> custom_arcpy.select_location_and_make_permanent_feature(
        ...     input_layer=Building_N100.data_selection___begrensningskurve_n100_input_data___n100_building.value,
        ...     overlap_type=OverlapType.WITHIN_A_DISTANCE.value,
        ...     select_features=Building_N100.polygon_propogate_displacement___building_polygons_after_displacement___n100_building.value,
        ...     output_name=Building_N100.polygon_resolve_building_conflicts___begrensningskurve_500m_from_displaced_polygon___n100_building.value,
        ...     search_distance="500 Meters",
        ... )
        'polygon_propogate_displacement___begrensningskurve_500_m_from_displaced_polygon___n100_building' created permanently.
    """
    # Resolve overlap_type and selection_type
    overlap_type = resolve_enum(OverlapType, overlap_type) or OverlapType.INTERSECT
    selection_type = (
        resolve_enum(SelectionType, selection_type) or SelectionType.NEW_SELECTION
    )

    arcpy.management.MakeFeatureLayer(input_layer, "temp_layer")

    try:
        # If the overlap type requires a search distance and it's provided
        if overlap_type in [OverlapType.WITHIN_A_DISTANCE] and search_distance:
            arcpy.management.SelectLayerByLocation(
                "temp_layer",
                overlap_type.value,
                select_features,
                search_distance,
                selection_type.value,
                "INVERT" if inverted else "NOT_INVERT",
            )
        else:
            arcpy.management.SelectLayerByLocation(
                "temp_layer",
                overlap_type.value,
                select_features,
                "",
                selection_type.value,
                "INVERT" if inverted else "NOT_INVERT",
            )

        arcpy.management.CopyFeatures("temp_layer", output_name)

    except Exception as e:
        print(f"Error occurred: {e}")

    finally:
        arcpy.management.Delete("temp_layer")
        print(f"{output_name} created permanently.")


def apply_symbology(
    input_layer,
    in_symbology_layer,
    output_name,
    grouped_lyrx=False,
    target_layer_name=None,
):
    """
    Summary:
        Applies symbology from a specified lyrx file to an input feature layer and saves the result as a new lyrx file.

    Details:
        - Creates a temporary feature layer from the `input_layer`.
        - Applies symbology to the temporary layer using the symbology defined in `in_symbology_layer`.
        - The symbology settings are maintained as they are in the symbology layer file.
        - Saves the temporary layer with the applied symbology to a new layer file specified by `output_name`.
        - Deletes the temporary layer to clean up the workspace.
        - A confirmation message is printed indicating the successful creation of the output layer file.

    Parameters:
        input_layer (str): The path or name of the input feature layer to which symbology will be applied.
        in_symbology_layer (str): The path to the layer file (.lyrx) containing the desired symbology settings.
        output_name (str): The name (including path) for the output layer file (.lyrx) with the applied symbology.
        grouped_lyrx (bool, optional): If True, the symbology is applied to the entire layer group. Defaults to False.
        target_layer_name (str, optional): The name of the target layer within the layer group to which symbology is applied. Defaults to None.

    Example:
        >>> custom_arcpy.apply_symbology_to_the_layers(
        ...     input_layer=Building_N100.point_displacement_with_buffer___merged_buffer_displaced_points___n100_building.value,
        ...     in_symbology_layer=config.symbology_n100_grunnriss,
        ...     output_name=Building_N100.polygon_resolve_building_conflicts___building_polygon___n100_building_lyrx.value,
        ... )
        'apply_symbology_to_layers__building_polygon__n100__lyrx.lyrx file created.'
    """

    def apply_symbology_to_single_layer(
        target_layer,
        apply_symbology_layer,
        created_lrx_file_name,
    ):
        arcpy.management.MakeFeatureLayer(
            in_features=target_layer,
            out_layer=f"{input_layer}_tmp",
        )

        arcpy.management.ApplySymbologyFromLayer(
            in_layer=f"{target_layer}_tmp",
            in_symbology_layer=apply_symbology_layer,
            update_symbology="MAINTAIN",
        )

        arcpy.management.SaveToLayerFile(
            in_layer=f"{target_layer}_tmp",
            out_layer=output_name,
            is_relative_path="ABSOLUTE",
        )

        arcpy.management.Delete(
            f"{target_layer}_tmp",
        )

        print(f"{created_lrx_file_name} lyrx file created.")

    if not grouped_lyrx:
        apply_symbology_to_single_layer(
            target_layer=input_layer,
            apply_symbology_layer=in_symbology_layer,
            created_lrx_file_name=output_name,
        )

    elif grouped_lyrx and target_layer_name is None:
        raise Exception("This feature has not been implemented please do not use yet")

    elif grouped_lyrx and target_layer_name is not None:
        group_lyrx_layer_file = arcpy.mp.LayerFile(in_symbology_layer)
        listed_layers = group_lyrx_layer_file.listLayers()
        symbology_layer = None

        for layer in listed_layers:
            if layer.name == target_layer_name:
                symbology_layer = layer
                print(f"Layer {target_layer_name} found in {in_symbology_layer}.")
                break

        if symbology_layer is None:
            print(f"Layer {target_layer_name} not found in {in_symbology_layer}.")
            return None

        apply_symbology_to_single_layer(
            target_layer=input_layer,
            apply_symbology_layer=symbology_layer,
            created_lrx_file_name=output_name,
        )



def join_field(in_feature_class: str, join_feature_class: str, in_field: str, join_field: str, fields: list[str] = None):
    """
    Replaces arcpy.management.JoinField with a custom implementation because JoinField crashes in arcpy image

    args:
        in_feature_class: The feature class to which the join table will be joined.
        join_feature_class: The feature class that will be joined to the input table.
        in_field: The field in the input table on which the join will be based.
        join_field: The field in the join table that contains the values on which the join will be based
        fields: The fields from the join table that will be transferred to the input table based on a join between the input table and the join table.
            if None all fields except required fields and fields already in in_feature_class will be joined.
    """
    output_field_names = {
        field.name for field in arcpy.ListFields(in_feature_class)
    }
    fields_to_join = [
        field
        for field in arcpy.ListFields(join_feature_class)
        if not field.required and field.name not in output_field_names
    ]
    if fields is not None:
        fields_to_join = [field for field in fields_to_join if field.name in fields]

    for field in fields_to_join:
        arcpy.management.AddField(
            in_feature_class,
            field.name,
            field.type,
            field.precision,
            field.scale,
            field.length,
        )

    joined_field_names = [field.name for field in fields_to_join]
    source_fields = [in_field] + joined_field_names
    source_values = {
        row[0]: row[1:]
        for row in arcpy.da.SearchCursor(
            join_feature_class, source_fields
        )
    }

    with arcpy.da.UpdateCursor(
        in_feature_class,
        [join_field] + joined_field_names,
    ) as cursor:
        for row in cursor:
            row[1:] = source_values[row[0]]
            cursor.updateRow(row)



def find_point_clusters(input_points: str, output_feature_class: str, search_distance: str):
    """
    arcpy.gapro.FindPointClusters does not exist on arcgis server,
    this function replaces it with a custom implementation using available ArcGIS Server tools.

    This custom implementation doesnt use a dbscan clustering method like FindPointClusters does.
    Looking at the input data / results for pipeline building n100 
    we only need to group hospitals and churches that are closer than 250 meters 
    to get the same results as the original FindPointClusters tool.
    If in the future we wish to do something similar on a different dataset or with different distance thresholds, 
    the implementation may need to be adjusted accordingly.

    There is a second implementation of this in remove_overlapping overlapping polygons and points,
    this second implementation i have only seen on Data in Oslo, in oslo it this function is enough to replace the original FindPointClusters tool.
    However i dont know if thats the case for the whole of norway.
    Therefore, we test run for whole of norway and have to check if this implementation is sufficient for all regions.

    adds same fields as the original FindPointClusters tool would have added to avoid having to change downstream processes.
    """
    #creating output fc
    if not arcpy.Exists(output_feature_class):
        path_split = output_feature_class.split(".gdb/")
        out_path = path_split[0] + ".gdb"
        out_name = path_split[1]
        arcpy.management.CreateFeatureclass(
            out_path=out_path,
            out_name=out_name,
            geometry_type="POINT",
            spatial_reference=arcpy.Describe(input_points).spatialReference,
        )
    arcpy.management.CopyFeatures(
        in_features=input_points,
        out_feature_class=output_feature_class,
    )
    
    arcpy.management.AddField(
        in_table=output_feature_class,
        field_name="CLUSTER_ID",
        field_type="LONG",
    )
    arcpy.management.AddField(
        in_table=output_feature_class,
        field_name="COLOR_ID",
        field_type="LONG",
    )

    arcpy.analysis.GenerateNearTable(
        in_features=output_feature_class,
        near_features=output_feature_class,
        out_table=f"{output_feature_class}_near_table",
        search_radius=search_distance,
        closest="ALL",
    )

    clusters = []
    with arcpy.da.SearchCursor(
        f"{output_feature_class}_near_table",
        ["IN_FID", "NEAR_FID"],
    ) as cursor:
        for in_fid, near_fid in cursor:
            matching_clusters = [
                cluster
                for cluster in clusters
                if in_fid in cluster or near_fid in cluster
            ]

            if not matching_clusters:
                clusters.append({in_fid, near_fid})
            else:
                # Combine all matching clusters.
                combined_cluster = {in_fid, near_fid}

                for cluster in matching_clusters:
                    combined_cluster.update(cluster)
                    clusters.remove(cluster)

                clusters.append(combined_cluster)

    # adding cluster IDs to the output feature class
    cluster_ids = {
        feature_id: cluster_id
        for cluster_id, cluster in enumerate(clusters, start=1)
        for feature_id in cluster
    }

    with arcpy.da.UpdateCursor(
        output_feature_class,
        ["OBJECTID", "CLUSTER_ID", "COLOR_ID"],
    ) as cursor:
        for object_id, _, _ in cursor:
            cluster_id = cluster_ids.get(object_id, -1)
            cursor.updateRow([object_id, cluster_id, cluster_id])
