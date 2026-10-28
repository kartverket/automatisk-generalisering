# Libraries

from pathlib import Path

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, GDBName
from paths import GIS_FILES_ROOT

######################
# Path Factory
######################


def get_gdb_path(scale: Scale, gdb_name: GDBName) -> Path:
    """Build a geodatabase path under the configured GIS files root."""
    return Path.joinpath(Path(GIS_FILES_ROOT), scale, f"{gdb_name}.gdb")


def get_feature_class_path(
    gdb_path: Path, feature_class_name: FeatureClassName
) -> Path:
    """Append a feature class name to a geodatabase path."""
    return Path.joinpath(gdb_path, feature_class_name)


def get_feature_class_full_path(
    scale: Scale,
    gdb_name: GDBName,
    feature_class_name: FeatureClassName,
) -> str:
    """Build a feature class path from its source scale and object type."""
    return str(
        get_feature_class_path(
            gdb_path=get_gdb_path(scale=scale, gdb_name=gdb_name),
            feature_class_name=feature_class_name,
        )
    )
