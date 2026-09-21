# Libraries

from enum import StrEnum
from pathlib import Path

from paths import GIS_FILES_ROOT

######################
# Classes
######################


class FieldType(StrEnum):
    TEXT = "TEXT"
    DOUBLE = "DOUBLE"
    OID = "OID"
    GEOMETRY = "Geometry"


class GeometryType(StrEnum):
    POINT = "point"
    POLYLINE = "polyline"
    POLYGON = "polygon"


class Scale(StrEnum):
    RAW_DATA = "raw_data"
    N10 = "n10"
    N25 = "n25"
    N50 = "n50"
    N100 = "n100"
    N250 = "n250"
    N500 = "n500"


class ObjectType(StrEnum):
    ROAD = "road"


class FeatureClassName(StrEnum):
    ELVEG_AND_STI = "elveg_and_sti"


######################
# Path Factory
######################


def get_gdb_path(scale: Scale, object_type: ObjectType) -> Path:
    return Path.joinpath(Path(GIS_FILES_ROOT), scale, f"{object_type}.gdb")


def get_feature_class_path(
    gdb_path: Path, feature_class_name: FeatureClassName
) -> Path:
    return Path.joinpath(gdb_path, feature_class_name)


def get_feature_class_full_path(
    scale: Scale, object_type: ObjectType, feature_class_name: FeatureClassName
) -> Path:
    gdb_path = get_gdb_path(scale, object_type)
    return get_feature_class_path(gdb_path, feature_class_name)
