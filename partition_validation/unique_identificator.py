# TODO: Scheduled for deletion; migrate to lineage-based persistent ID for features

# Libraries

import uuid

import arcpy

##########################
# Functionality
##########################


def add_persistent_id(input_fc: str, field_name: str = "GLOBAL_ID") -> None:
    """
    Add a persistent UUID field to a feature class if it does not exist.

    Adds a persistent UUID field if not already present, then populates
    all features with unique UUIDs (only filling empty values).

    Args:
        input_fc: Input feature class to add the persistent ID field to
        field_name: Name of the field to store the UUIDs (default: "GLOBAL_ID")
    """
    existing_fields = [f.name.upper() for f in arcpy.ListFields(input_fc)]

    if field_name.upper() not in existing_fields:
        arcpy.management.AddField(
            in_table=input_fc, field_name=field_name, field_type="TEXT", field_length=36
        )

    with arcpy.da.UpdateCursor(input_fc, [field_name]) as cursor:
        for row in cursor:
            if not row[0]:
                row[0] = str(uuid.uuid4())
                cursor.updateRow(row)
