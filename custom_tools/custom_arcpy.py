import arcpy
from enum import Enum


def attribute_select_and_make_feature_layer(
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

    class SelectionType(Enum):
        NEW_SELECTION = "NEW_SELECTION"
        ADD_TO_SELECTION = "ADD_TO_SELECTION"
        REMOVE_FROM_SELECTION = "REMOVE_FROM_SELECTION"
        SUBSET_SELECTION = "SUBSET_SELECTION"
        SWITCH_SELECTION = "SWITCH_SELECTION"
        CLEAR_SELECTION = "CLEAR_SELECTION"

    selected_type = (
        SelectionType[selection_type].value
        if selection_type in SelectionType.__members__
        else "NEW_SELECTION"
    )

    arcpy.management.MakeFeatureLayer(input_layer, output_name)
    arcpy.management.SelectLayerByAttribute(
        output_name, selected_type, expression, invert_where_clause=inverted
    )
    print(f"{output_name} created temporarily.")


def attribute_select_and_make_permanent_feature(
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

    class SelectionType(Enum):
        NEW_SELECTION = "NEW_SELECTION"
        ADD_TO_SELECTION = "ADD_TO_SELECTION"
        REMOVE_FROM_SELECTION = "REMOVE_FROM_SELECTION"
        SUBSET_SELECTION = "SUBSET_SELECTION"
        SWITCH_SELECTION = "SWITCH_SELECTION"
        CLEAR_SELECTION = "CLEAR_SELECTION"

    # Create a temporary feature layer from the input layer
    arcpy.management.MakeFeatureLayer(input_layer, "temp_layer")

    # Perform the attribute selection on the temporary layer
    arcpy.management.SelectLayerByAttribute(
        "temp_layer", selection_type, expression, invert_where_clause=inverted
    )

    # Copy only the selected features from the temporary layer into a new feature class
    arcpy.management.CopyFeatures("temp_layer", output_name)

    # Delete the temporary layer to clean up
    arcpy.management.Delete("temp_layer")

    print(f"{output_name} created permanently.")
