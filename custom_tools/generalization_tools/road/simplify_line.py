import arcpy

from composition_configs import logic_config


def simplify_line(simplify_line_config: logic_config.SimplifyLineKwargs) -> None:
    """
    Simplifies lines with point removal, resolving topological errors it creates.
    """
    arcpy.cartography.SimplifyLine(
        in_features=simplify_line_config.input_line,
        out_feature_class=simplify_line_config.output_line,
        algorithm="POINT_REMOVE",
        tolerance=f"{simplify_line_config.tolerance_m} Meters",
        error_option="RESOLVE_ERRORS",
    )
