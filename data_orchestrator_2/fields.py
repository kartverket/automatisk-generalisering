# Libraries

from dataclasses import dataclass
from enum import Flag, auto

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
    name: str
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
        name="objtype", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    SUBTYPEKODE = FieldDefinition(
        name="subtypekode", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    TYPEVEG = FieldDefinition(
        name="typeveg", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGKATEGORI = FieldDefinition(
        name="vegkategori", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGNUMMER = FieldDefinition(
        name="vegnummer", datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    VEGSTATUS = FieldDefinition(
        name="vegstatus", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    MEDIUM = FieldDefinition(
        name="medium", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    MOTORVEGTYPE = FieldDefinition(
        name="motorvegtype", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    RUTEMERKING = FieldDefinition(
        name="rutemerking", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEDLIKEH = FieldDefinition(
        name="vedlikeh", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    UTTEGNING = FieldDefinition(
        name="uttegning", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    VEGKLASSE = FieldDefinition(
        name="vegklasse", datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    FELTOVERSIKT = FieldDefinition(
        name="feltoversikt", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    KONNEKTERINGSLENKE = FieldDefinition(
        name="konnekteringslenke", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    SIDEANLEGGSDEL = FieldDefinition(
        name="sideanleggsdel", datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    KRYSSDEL = FieldDefinition(
        name="kryssdel", datatype=FieldType.DOUBLE, usage=(FieldUsage.INPUT)
    )
    ADSKILTELOP = FieldDefinition(
        name="adskiltelop", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    ADSKILTELOPNUMMER = FieldDefinition(
        name="adskiltelopnummer", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    ADRESSENAVN = FieldDefinition(
        name="adressenavn", datatype=FieldType.TEXT, usage=(FieldUsage.INPUT)
    )
    OBJECTID = FieldDefinition(
        name="objectid",
        datatype=FieldType.OID,
        usage=(FieldUsage.INPUT),
        system_field=True,
    )
    SHAPE = FieldDefinition(
        name="shape",
        datatype=FieldType.GEOMETRY,
        usage=(FieldUsage.INPUT),
        system_field=True,
    )
