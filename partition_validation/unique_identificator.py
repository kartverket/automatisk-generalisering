# Libraries

import uuid

import arcpy

##########################
# Functionality
##########################


def add_persistent_id(input_fc: str, field_name: str = "GLOBAL_ID") -> None:
    """
    Adds a persistent UUID field if it does not already exist, and fills it with unique values for each feature.

    Args:
        input_fc (str): The input feature class to add the persistent ID to
        field_name (str, optional): The name of the field to store the UUIDs (default: "GLOBAL_ID")
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
