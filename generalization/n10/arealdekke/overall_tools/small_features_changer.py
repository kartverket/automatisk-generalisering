# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Program
# ========================


@timing_decorator
def change_attribute_value_main(working_fc: str) -> None:
    return


# ========================
# Main functions
# ========================


@timing_decorator
def change_attribute_value_category(
    working_fc: str,
    field: str,
    category: str,
    new_value: str,
    size_limit: int = None,
    exception_value: str = None,
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
        new_value (str): The new value to assign to the category
        size_limit (int, optional): The size limit for changing the category (defaults to None)
        exception_value (str, optional): The exception value for surrounded features (defaults to None)
    """
    # Relevant fields to copy for different categories
    relevant_fields = {
        "Snaumark": ["arealdekke", "dgfcd_feature_alpha"],
        "Skog": ["arealdekke", "treslag"],
    }

    # TODO: Legg til felt for å bevare original objekt-ID

    # Initialize the work file manager
    work_fc = Arealdekke_N10.small_features_changer__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=work_fc)
    wfm = WorkFileManager(config=config)

    files = create_wfm_gdbs(wfm=wfm)

    # Select relevant features
    sql = f"{field} = '{category}' AND SHAPE_Area < {size_limit}" if size_limit else f"{field} = '{category}'"
    
    work_lyr = "work_lyr"
    arcpy.management.MakeFeatureLayer(in_features=working_fc, out_layer=work_lyr)

    arcpy.management.SelectLayerByAttribute(in_layer_or_view=work_lyr, selection_type="NEW_SELECTION", where_clause=sql)
    arcpy.management.CopyFeatures(in_features=work_lyr, out_feature_class=files["selected_features"])

    # TODO: Hvis unntaksverdi er spesifisert
    # TODO: Ny seleksjon for å finne intersect med de nettopp kopierte geometriene (som er av typen unntaksverdi)
    # TODO: Finn indre hull
    # TODO: Selekter treffene for å skille første seleksjon og de som er omringet av unntaksverdi
    # TODO: Oppdater verdier for begge seleksjonene i originalt datasett

    # TODO: Omskriv alt hvis unntaksverdi ikke er spesifisert


# ========================
# Helper functions
# ========================


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
        "selected_features": wfm.build_file_path(filename="selected_features", file_type="gdb"),
        "surrounding_features": wfm.build_file_path(filename="surrounding_features", file_type="gdb"),
    }
