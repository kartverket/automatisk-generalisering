# Libraries

import time

import arcpy

from data_orchestrator_2.constants.values import ColumnName
from data_orchestrator_2.runtime.dataset import Dataset
from data_orchestrator_2.schemas.fields import FieldDefinition, FieldUsage

######################
# Functionality
######################


def remove_none_geometry(dataset: Dataset) -> None:
    """Delete null-geometry rows and report the number removed."""
    layer = arcpy.management.MakeFeatureLayer(dataset.path, "del_lyr")
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

    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Removed {removed} rows with None geometry."
    )


def clean_columns(dataset: Dataset, usage: FieldUsage) -> None:
    """Delete unregistered or unused fields, preserving required and system fields.

    Combined usage flags retain fields marked for any requested stage.
    """
    path = dataset.path
    definitions = {field.name.casefold(): field for field in dataset.definition.fields}
    actual_fields = arcpy.ListFields(path)
    removed = 0

    for actual in actual_fields:
        definition: FieldDefinition | None = definitions.get(actual.name.casefold())
        if actual.required or (definition is not None and definition.system_field):
            continue
        if definition is None or not definition.isUsedFor(usage):
            arcpy.management.DeleteField(path, actual.name)
            removed += 1

    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Removed {removed} columns not flagged for {usage}."
    )


def prepare_final_dataset(dataset: Dataset) -> None:
    """Perform final cleanup and preparation of the dataset before use."""
    remove_none_geometry(dataset)
    clean_columns(dataset, FieldUsage.OUTPUT)
