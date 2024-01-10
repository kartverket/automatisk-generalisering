import arcpy
from enum import Enum


# Selection Type definition used for select by attribute functions
# Define your enums at the module level
class SelectionType(Enum):
    NEW_SELECTION = "NEW_SELECTION"
    ADD_TO_SELECTION = "ADD_TO_SELECTION"
    REMOVE_FROM_SELECTION = "REMOVE_FROM_SELECTION"
    SUBSET_SELECTION = "SUBSET_SELECTION"
    SWITCH_SELECTION = "SWITCH_SELECTION"
    CLEAR_SELECTION = "CLEAR_SELECTION"


class OverlapType(Enum):
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


# Define your function using the above enum
def select_attribute_and_make_feature_layer(
    input_layer, expression, output_name, selection_type="NEW_SELECTION", inverted=False
):
    """Selects features based on attribute and creates a new feature layer.
    then it uses the selection in the feature layer to store it permanently using copy features.

    Parameters:
    - input_layer: The input feature layer for selection.
    - expression: The SQL expression to use for selection.
    - output_name: The name of the output feature layer.
    - selection_type: The type of selection to perform. Defaults to "NEW_SELECTION".
    - inverted: A boolean flag to indicate if the selection should be inverted.
    """
    selected_type = (
        SelectionType[selection_type].value
        if selection_type in SelectionType.__members__
        else "NEW_SELECTION"
    )
    # Create a temporary feature layer from the input layer
    arcpy.management.MakeFeatureLayer(input_layer, output_name)
    # Perform the attribute selection on the temporary layer
    arcpy.management.SelectLayerByAttribute(
        output_name, selected_type, expression, invert_where_clause=inverted
    )
    print(f"{output_name} created temporarily.")


def select_attribute_and_make_permanent_feature(
    input_layer, expression, output_name, selection_type="NEW_SELECTION", inverted=False
):
    """Selects features based on attribute and creates a new feature layer.
    then it uses the selection in the feature layer to store it permanently using copy features.

    Parameters:
    - input_layer: The input feature layer for selection.
    - expression: The SQL expression to use for selection.
    - output_name: The name of the output feature layer.
    - selection_type: The type of selection to perform. Defaults to "NEW_SELECTION".
    - inverted: A boolean flag to indicate if the selection should be inverted.
    """
    selected_type = (
        SelectionType[selection_type].value
        if selection_type in SelectionType.__members__
        else "NEW_SELECTION"
    )
    # Create a temporary feature layer from the input layer
    arcpy.management.MakeFeatureLayer(input_layer, "temp_layer")
    # Perform the attribute selection on the temporary layer
    arcpy.management.SelectLayerByAttribute(
        "temp_layer", selected_type, expression, invert_where_clause=inverted
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
    # Convert string to Enum value or set default
    if not isinstance(overlap_type, OverlapType):
        overlap_type = OverlapType.INTERSECT

    if not isinstance(selection_type, SelectionType):
        selection_type = SelectionType.NEW_SELECTION

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
    if not isinstance(overlap_type, OverlapType):
        overlap_type = OverlapType.INTERSECT

    if not isinstance(selection_type, SelectionType):
        selection_type = SelectionType.NEW_SELECTION

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
        print(f"Error occurred: {e}")  # Here's the added logic for the exception block

    finally:
        arcpy.management.Delete("temp_layer")
        print(f"{output_name} created permanently.")


def apply_symbology(input_layer, in_symbology_layer, output_name):
    arcpy.management.MakeFeatureLayer(
        in_features=input_layer,
        out_layer=f"{input_layer}_tmp",
    )

    arcpy.management.ApplySymbologyFromLayer(
        in_layer=f"{input_layer}_tmp",
        in_symbology_layer=in_symbology_layer,
        update_symbology="MAINTAIN",
    )

    arcpy.management.SaveToLayerFile(
        in_layer=f"{input_layer}_tmp",
        out_layer=output_name,
        is_relative_path="ABSOLUTE",
    )

    arcpy.management.Delete(
        f"{input_layer}_tmp",
    )

    print(f"{output_name} lyrx file created.")
