# Libraries

from dataclasses import dataclass
from enum import Flag, auto

from data_orchestrator_2.names_paths import ColumnName as C
from data_orchestrator_2.names_paths import FieldType

######################
# Classes
######################


# What should the field be used for?
class FieldUsage(Flag):
    INPUT = auto()
    PROCESSING = auto()
    OUTPUT = auto()


# Definition of a field, including its name, datatype, and usage.
@dataclass(frozen=True)
class FieldDefinition:
    name: C
    datatype: FieldType
    usage: FieldUsage
    required: bool = True
    system_field: bool = False


######################
# Fields
######################


# Field registry, where all defined fields can be stored for easy access.
class Fields:
    OBJTYPE = FieldDefinition(
        name=C.OBJTYPE, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    SUBTYPEKODE = FieldDefinition(
        name=C.SUBTYPEKODE, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    TYPEVEG = FieldDefinition(
        name=C.TYPEVEG, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGKATEGORI = FieldDefinition(
        name=C.VEGKATEGORI, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGNUMMER = FieldDefinition(
        name=C.VEGNUMMER, datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    VEGSTATUS = FieldDefinition(
        name=C.VEGSTATUS, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    MEDIUM = FieldDefinition(
        name=C.MEDIUM, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    MOTORVEGTYPE = FieldDefinition(
        name=C.MOTORVEGTYPE, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    RUTEMERKING = FieldDefinition(
        name=C.RUTEMERKING, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEDLIKEH = FieldDefinition(
        name=C.VEDLIKEH, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    UTTEGNING = FieldDefinition(
        name=C.UTTEGNING, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGKLASSE = FieldDefinition(
        name=C.VEGKLASSE, datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    FELTOVERSIKT = FieldDefinition(
        name=C.FELTOVERSIKT, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    KONNEKTERINGSLENKE = FieldDefinition(
        name=C.KONNEKTERINGSLENKE, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    SIDEANLEGGSDEL = FieldDefinition(
        name=C.SIDEANLEGGSDEL, datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    KRYSSDEL = FieldDefinition(
        name=C.KRYSSDEL, datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    ADSKILTELOP = FieldDefinition(
        name=C.ADSKILTELOP, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    ADSKILTELOPNUMMER = FieldDefinition(
        name=C.ADSKILTELOPNUMMER, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    ADRESSENAVN = FieldDefinition(
        name=C.ADRESSENAVN, datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    OBJECTID = FieldDefinition(
        name=C.OBJECTID,
        datatype=FieldType.OID,
        usage=(FieldUsage.INPUT),
        system_field=True,
    )
    SHAPE = FieldDefinition(
        name=C.SHAPE,
        datatype=FieldType.GEOMETRY,
        usage=(FieldUsage.INPUT),
        system_field=True,
    )
