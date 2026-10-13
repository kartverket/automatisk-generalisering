# Libraries

import time

import arcpy

from data_orchestrator_2.datasets import DatasetDefinition
from data_orchestrator_2.fields import FieldDefinition, FieldUsage
from data_orchestrator_2.names_paths import ColumnName

######################
# Functionality
######################


def remove_none_geometry(dataset: DatasetDefinition) -> str:
    """Delete null-geometry rows and report the number removed."""
    layer = arcpy.management.MakeFeatureLayer(str(dataset.getPath()), "del_lyr")
    try:
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=layer,
            selection_type="NEW_SELECTION",
            where_clause=f"{ColumnName.SHAPE} IS NULL",
        )
        removed = int(arcpy.management.GetCount(layer)[0])
        arcpy.management.DeleteRows(layer)
    finally:
        arcpy.management.Delete(layer)

    return f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Removed {removed} rows with None geometry."


def clean_columns(dataset: DatasetDefinition, usage: FieldUsage) -> str:
    """Delete unregistered or unused fields, preserving required and system fields.

    Combined usage flags retain fields marked for any requested stage.
    """
    path = str(dataset.getPath())
    definitions = {str(field.name).casefold(): field for field in dataset.fields}
    actual_fields = arcpy.ListFields(path)
    removed = 0

    for actual in actual_fields:
        definition: FieldDefinition | None = definitions.get(actual.name.casefold())
        if actual.required or (definition is not None and definition.system_field):
            continue
        if definition is None or not definition.isUsedFor(usage):
            arcpy.management.DeleteField(path, actual.name)
            removed += 1

    return f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Removed {removed} columns not flagged for {usage}."
