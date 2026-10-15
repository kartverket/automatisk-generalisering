# Libraries

from pathlib import Path

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from paths import GIS_FILES_ROOT

######################
# Path Factory
######################


def get_gdb_path(scale: Scale, object_type: ObjectType) -> Path:
    """Build a geodatabase path under the configured GIS files root."""
    return Path.joinpath(Path(GIS_FILES_ROOT), scale, f"{object_type}.gdb")


def get_feature_class_path(
    gdb_path: Path, feature_class_name: FeatureClassName
) -> Path:
    """Append a feature class name to a geodatabase path."""
    return Path.joinpath(gdb_path, feature_class_name)


def get_feature_class_full_path(
    scale: Scale,
    object_type: ObjectType,
    feature_class_name: FeatureClassName,
) -> str:
    """Build a feature class path from its source scale and object type."""
    gdb_path = get_gdb_path(scale, object_type)
    full_path = get_feature_class_path(gdb_path, feature_class_name)
    return str(full_path)
