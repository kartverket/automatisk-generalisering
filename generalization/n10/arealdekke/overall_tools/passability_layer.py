# Libraries

import arcpy

arcpy.env.overwriteOutput = True

from enum import StrEnum

from composition_configs import core_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.validation import check_valid_feature_class
from file_manager import WorkFileManager
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10

# ========================
# Class
# ========================


class Names(StrEnum):
    erased = "erased"
    aggregated = "aggregated"


# ========================
# Main functions
# ========================


@timing_decorator
def create_passability_layer(input_fc: str, output_fc: str) -> None:
    """
    Creates a separate feature class with the geometries not having 'None' as passability.

    Args:
        input_fc (str): Feature class with original land use data having a column named 'fremkommelighet'
        output_fc (str) Feature class to be created with the geometries having 'fremkommelighet' != 'None'
    """
    land_use_lyr = "land_use_lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_fc, out_layer=land_use_lyr)

    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=land_use_lyr,
        selection_type="NEW_SELECTION",
        where_clause="fremkommelighet <> 'None'",
    )

    arcpy.management.Dissolve(
        in_features=land_use_lyr,
        out_feature_class=output_fc,
        dissolve_field=["arealdekke", "fremkommelighet"],
        multi_part="SINGLE_PART",
    )


@timing_decorator
def postprocess_passability_layer(final_fc: str, passability_fc: str) -> None:
    """
    Post-processes the passability layer by checking for match with geometries in the final feature class.

    Args:
        final_fc (str): Feature class to be created with the post-processed passability layer
        passability_fc (str): Feature class with the passability layer to be post-processed
    """
    if not check_valid_feature_class(passability_fc, level=2):
        print("Passability feature class does not contain any data.")
        return

    fremkommelighet = "fremkommelighet"
    arealdekke = "arealdekke"

    # Sets up work file manager to take care of temporary files
    fc = Arealdekke_N10.passability_work_file__n10_land_use.value
    config = core_config.WorkFileConfig(root_file=fc)
    wfm = WorkFileManager(config=config)

    files = {
        name: wfm.build_file_path(file_name=name, file_type="gdb") for name in Names
    }

    final_lyr = "final_lyr"
    features_to_keep = [
        "Samferdsel",
        "ElvFlate",
        "Innsjo",
        "InnsjoRegulert",
        "Kanal",
        "Hav",
    ]
    values_to_keep = "', '".join(features_to_keep)
    sql = f"{arealdekke} IN ('{values_to_keep}')"
    arcpy.management.MakeFeatureLayer(in_features=final_fc, out_layer=final_lyr)
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=final_lyr, selection_type="NEW_SELECTION", where_clause=sql
    )

    arcpy.analysis.PairwiseErase(
        in_features=passability_fc,
        erase_features=final_lyr,
        out_feature_class=files[Names.erased],
    )

    arcpy.cartography.AggregatePolygons(
        in_features=files[Names.erased],
        out_feature_class=files[Names.aggregated],
        aggregation_distance="5 Meters",
        orthogonality_option="ORTHOGONAL",
        barrier_features=final_lyr,
        aggregate_field=fremkommelighet,
    )

    arcpy.management.Dissolve(
        in_features=files[Names.aggregated],
        out_feature_class=passability_fc,
        dissolve_field=fremkommelighet,
        multi_part="SINGLE_PART",
    )

    wfm.delete_created_files()
