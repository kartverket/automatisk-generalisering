# Libraries

from enum import StrEnum
from pathlib import Path

from paths import GIS_FILES_ROOT

######################
# Classes
######################


class FieldType(StrEnum):
    BOOLEAN = "Boolean"
    DOUBLE = "Double"
    GEOMETRY = "Geometry"
    OID = "OID"
    SHORT = "Short"
    STRING = "String"


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


class ColumnName(StrEnum):
    ADRESSENAVN = "adressenavn"
    ADSKILTELOP = "adskiltelop"
    ADSKILTELOPNUMMER = "adskiltelopnummer"
    ER_KRYSSNINGSPUNKT = "er_kryssningspunkt"
    FELTOVERSIKT = "feltoversikt"
    HIERARKI = "hierarki"
    KONNEKTERINGSLENKE = "konnekteringslenke"
    KRYSSDEL = "kryssdel"
    MEDIUM = "medium"
    MOTORVEGTYPE = "motorvegtype"
    OBJECTID = "objectid"
    OBJTYPE = "objtype"
    RUTEMERKING = "rutemerking"
    SHAPE = "SHAPE"
    SIDEANLEGGSDEL = "sideanleggsdel"
    SUBTYPEKODE = "subtypekode"
    TYPEVEG = "typeveg"
    UTTEGNING = "uttegning"
    VEDLIKEH = "vedlikeh"
    VEGKATEGORI = "vegkategori"
    VEGKLASSE = "vegklasse"
    VEGNUMMER = "vegnummer"
    VEGSTATUS = "vegstatus"


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
    scale: Scale, object_type: ObjectType, feature_class_name: FeatureClassName
) -> Path:
    """Build a feature class path from its source scale and object type."""
    gdb_path = get_gdb_path(scale, object_type)
    return get_feature_class_path(gdb_path, feature_class_name)
