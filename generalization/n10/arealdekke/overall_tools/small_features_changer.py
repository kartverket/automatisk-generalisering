# Libraries

import arcpy
import os

from pathlib import Path

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.param_utils import initialize_params
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.parameters.parameter_dataclasses import (
    SmallFeatures,
)

# ========================
# Program
# ========================


@timing_decorator
def change_attribute_value_main(working_fc: str) -> None:
    params = fetch_parameters(map_scale="N10")

    change_attribute_value_category(
        working_fc=working_fc,
        field="arealdekke",
        category="Bebygd",
        new_category="Snaumark",
        size_limit=params.Bebygd,
        exception_category="Skog",
    )


# ========================
# Main functions
# ========================


@timing_decorator
def change_attribute_value_category(
    working_fc: str,
    field: str,
    category: str,
    new_category: str,
    size_limit: int = None,
    exception_category: str = None,
) -> None:
    """
    Changes the attribute value of the field with the specified category to the new value for features
    smaller than the size limit (or all if not specified). If an exception value is specified, features
    of the category under size limit, completely surrounded by features of the exception value, is
    changed to the exception value.

    Args:
        working_fc (str): The feature class with complete, non-overlapping geometries
        field (str): The field to check for the category
        category (str): The category to change
        new_category (str): The new category to assign to the field
        size_limit (int, optional): The size limit for changing the category (defaults to None)
        exception_category (str, optional): The exception category for surrounded features (defaults to None)
    """
    # Relevant fields to copy for different categories
    relevant_fields = {
        "Snaumark": [field, "dgfcd_feature_alpha"],
        "Skog": [field, "treslag"],
    }

    updated_fields = {"Bebygd": [new_category, "BuiltUpArea"]}

    # Adds a field to collect original OID
    new_field = "orig_OID"
    arcpy.management.AddField(
        in_table=working_fc, field_name=new_field, field_type="TEXT"
    )
    arcpy.management.CalculateField(
        in_table=working_fc,
        field=new_field,
        expression="!OBJECTID!",
        expression_type="PYTHON3",
    )

    # Initialize the work file manager
    work_fc = Arealdekke_N10.small_features_changer__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=work_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    # Select relevant features
    sql = (
        f"{field} = '{category}' AND SHAPE_Area < {size_limit}"
        if size_limit
        else f"{field} = '{category}'"
    )

    work_lyr = "work_lyr"
    arcpy.management.MakeFeatureLayer(in_features=working_fc, out_layer=work_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=work_lyr, selection_type="NEW_SELECTION", where_clause=sql
    )

    if exception_category:
        # Extract the relevant selection
        arcpy.management.CopyFeatures(
            in_features=work_lyr, out_feature_class=files["selected_features"]
        )

        # Find intersecting features to 'selected_features' that are of category 'exception_category'
        arcpy.management.SelectLayerByLocation(
            in_layer=work_lyr,
            overlap_type="INTERSECT",
            select_features=files["selected_features"],
            selection_type="NEW_SELECTION",
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=work_lyr,
            overlap_type="WITHIN",
            select_features=files["selected_features"],
            selection_type="SUBSET_SELECTION",
            invert_spatial_relationship="INVERT",
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=work_lyr,
            selection_type="SUBSET_SELECTION",
            where_clause=f"{field} = '{exception_category}'",
        )
        arcpy.management.CopyFeatures(
            in_features=work_lyr, out_feature_class=files["surrounding_features"]
        )

        # Extract inner holes
        find_holes(
            input_fc=files["surrounding_features"],
            singlepart_fc=files["singlepart"],
            line_fc=files["surrounding_features_lines"],
            output_fc=files["holes"],
        )

        # Select geometries of 'exception_category'
        sel_lyr = "sel_lyr"
        arcpy.management.MakeFeatureLayer(
            in_features=files["selected_features"], out_layer=sel_lyr
        )
        arcpy.management.SelectLayerByLocation(
            in_layer=sel_lyr,
            overlap_type="INTERSECT",
            select_features=files["holes"],
            selection_type="NEW_SELECTION",
        )
        arcpy.management.CopyFeatures(
            in_features=sel_lyr, out_feature_class=files["selected_exception"]
        )

        # Extract the remaining to seperate feature class
        arcpy.management.SelectLayerByLocation(
            in_layer=sel_lyr,
            overlap_type="INTERSECT",
            select_features=files["selected_exception"],
            selection_type="NEW_SELECTION",
            invert_spatial_relationship="INVERT",
        )
        arcpy.management.CopyFeatures(
            in_features=sel_lyr, out_feature_class=files["selected_normal"]
        )

        # Updates attribute for 'new_category'
        OIDS = ", ".join(
            [
                row[0]
                for row in arcpy.da.SearchCursor(files["selected_normal"], [new_field])
            ]
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=work_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({OIDS})",
        )
        with arcpy.da.UpdateCursor(work_lyr, relevant_fields[new_category]) as update:
            for _ in update:
                update.updateRow(updated_fields[category])

        # Updates attribute for 'exception_category'
        arcpy.analysis.Near(
            in_features=files["selected_exception"],
            near_features=files["surrounding_features"],
        )

        OIDS = ", ".join(
            [
                row[0]
                for row in arcpy.da.SearchCursor(
                    files["selected_exception"], [new_field]
                )
            ]
        )
        arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=work_lyr,
            selection_type="NEW_SELECTION",
            where_clause=f"OBJECTID IN ({OIDS})",
        )
        match_fields = {
            oid: val
            for oid, val in arcpy.da.SearchCursor(
                files["surrounding_features"],
                ["OID@", relevant_fields[exception_category][-1]],
            )
        }
        sel_oids = {
            orig_OID: near_OID
            for orig_OID, near_OID in arcpy.da.SearchCursor(
                files["selected_exception"], [new_field, "NEAR_FID"]
            )
        }
        with arcpy.da.UpdateCursor(
            work_lyr, ["OID@"] + relevant_fields[exception_category]
        ) as update:
            for oid, _, _ in update:  # (category, dissolve_field, object ID)
                update.updateRow(
                    [oid, exception_category, match_fields[sel_oids[str(oid)]]]
                )
    else:
        # If no exception value, rewrite all selected features
        with arcpy.da.UpdateCursor(
            in_table=work_lyr, field_names=relevant_fields[new_category]
        ) as update:
            for _ in update:
                update.updateRow(updated_fields[category])

    arcpy.management.DeleteField(in_table=working_fc, drop_field=new_field)

    wfm.delete_created_files()


# ========================
# Helper functions
# ========================


def fetch_parameters(map_scale: str) -> dict:
    """
    Fetches minimum area parameters for small features from the parameters.yml file for the given map scale.

    Args:
        map_scale (str): The map scale to fetch parameters for

    Returns:
        dict: A dictionary of minimum area parameters for small features for the given map scale
    """
    params_path = Path(__file__).parent.parent / "parameters" / "parameters.yml"
    scale_parameters = initialize_params(
        params_path=params_path,
        class_name="SmallFeatures",
        map_scale=map_scale,
        dataclass=SmallFeatures,
    )
    return scale_parameters


def create_wfm_gdbs(wfm: WorkFileManager) -> dict:
    """
    Creates all the temporarily files that are going to be used
    during the process of combining land use on islands.

    Args:
        wfm (WorkFileManager): The WorkFileManager instance that are keeping the files

    Returns:
        dict: A dictionary with all the files as variables
    """
    return {
        "selected_features": wfm.build_file_path(
            file_name="selected_features", file_type="gdb"
        ),
        "surrounding_features": wfm.build_file_path(
            file_name="surrounding_features", file_type="gdb"
        ),
        "singlepart": wfm.build_file_path(file_name="singlepart", file_type="gdb"),
        "surrounding_features_lines": wfm.build_file_path(
            file_name="surrounding_features_lines", file_type="gdb"
        ),
        "holes": wfm.build_file_path(file_name="holes", file_type="gdb"),
        "selected_exception": wfm.build_file_path(
            file_name="selected_exception", file_type="gdb"
        ),
        "selected_normal": wfm.build_file_path(
            file_name="selected_normal", file_type="gdb"
        ),
    }


def find_holes(input_fc: str, singlepart_fc: str, line_fc: str, output_fc: str) -> None:
    """
    Detects inner holes in the input and copies these to the output.

    Args:
        input_fc (str): Input feature class with potential holes
        singlepart_fc (str): Feature class to store temporary singlepart features
        line_fc (str): Feature class to store temporary line segments
        output_fc (str): Output feature class to store the identified holes
    """
    arcpy.management.MultipartToSinglepart(
        in_features=input_fc, out_feature_class=singlepart_fc
    )

    arcpy.management.PolygonToLine(
        in_features=singlepart_fc,
        out_feature_class=line_fc,
        neighbor_option="IGNORE_NEIGHBORS",
    )

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    sr = arcpy.Describe(input_fc).spatialReference
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(output_fc),
        out_name=os.path.basename(output_fc),
        geometry_type="POLYGON",
        spatial_reference=sr,
    )

    with arcpy.da.SearchCursor(line_fc, ["SHAPE@"]) as cursor_in, arcpy.da.InsertCursor(
        output_fc, ["SHAPE@"]
    ) as cursor_out:
        for row in cursor_in:
            geom = row[0]
            for i in range(1, geom.partCount):
                part = geom.getPart(i)
                hole_polygon = arcpy.Polygon(arcpy.Array([p for p in part]), sr)
                cursor_out.insertRow([hole_polygon])
