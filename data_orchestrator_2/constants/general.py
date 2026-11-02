# Libraries

from enum import StrEnum

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
