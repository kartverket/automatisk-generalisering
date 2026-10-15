# Libraries

from dataclasses import dataclass
from enum import Flag, StrEnum, auto

from data_orchestrator_2.constants.common import FieldType
from data_orchestrator_2.constants.values import ColumnName

######################
# Classes
######################


# TODO: Usage skal bli i hvert datasett
class FieldUsage(Flag):
    """Stages at which a field is expected or retained; values may be combined."""

    INPUT = auto()
    PROCESSING = auto()
    OUTPUT = auto()


@dataclass(frozen=True)
class FieldDefinition:
    """Catalog metadata for a field; requiredness is separate from usage."""

    name: ColumnName
    datatype: FieldType
    usage: FieldUsage

    required: bool = True
    system_field: bool = False

    domain: type[StrEnum] | None = None

    def isUsedFor(self, usage: FieldUsage) -> bool:
        """Return whether any requested usage flag belongs to this field."""
        return bool(self.usage & usage)


######################
# Fields
######################


# Field registry, where all defined fields can be stored for easy access.
class FieldCatalog:
    """Reusable field definitions for dataset catalogs."""

    ADRESSENAVN = FieldDefinition(
        name=ColumnName.ADRESSENAVN,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    ADSKILTELOP = FieldDefinition(
        name=ColumnName.ADSKILTELOP,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    ADSKILTELOPNUMMER = FieldDefinition(
        name=ColumnName.ADSKILTELOPNUMMER,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    ER_KRYSSNINGSPUNKT = FieldDefinition(
        name=ColumnName.ER_KRYSSNINGSPUNKT,
        datatype=FieldType.BOOLEAN,
        usage=FieldUsage.PROCESSING,
    )
    FELTOVERSIKT = FieldDefinition(
        name=ColumnName.FELTOVERSIKT,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    HIERARKI = FieldDefinition(
        name=ColumnName.HIERARKI, datatype=FieldType.SHORT, usage=FieldUsage.PROCESSING
    )
    KONNEKTERINGSLENKE = FieldDefinition(
        name=ColumnName.KONNEKTERINGSLENKE,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    KRYSSDEL = FieldDefinition(
        name=ColumnName.KRYSSDEL,
        datatype=FieldType.DOUBLE,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    MEDIUM = FieldDefinition(
        name=ColumnName.MEDIUM,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    MOTORVEGTYPE = FieldDefinition(
        name=ColumnName.MOTORVEGTYPE,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    OBJECTID = FieldDefinition(
        name=ColumnName.OBJECTID,
        datatype=FieldType.OID,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
        system_field=True,
    )
    OBJTYPE = FieldDefinition(
        name=ColumnName.OBJTYPE,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    RUTEMERKING = FieldDefinition(
        name=ColumnName.RUTEMERKING,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    SHAPE = FieldDefinition(
        name=ColumnName.SHAPE,
        datatype=FieldType.GEOMETRY,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
        system_field=True,
    )
    SHAPE_LENGTH = FieldDefinition(
        name=ColumnName.SHAPE_LENGTH,
        datatype=FieldType.DOUBLE,
        usage=FieldUsage.PROCESSING | FieldUsage.OUTPUT,
        system_field=True,
    )
    SIDEANLEGGSDEL = FieldDefinition(
        name=ColumnName.SIDEANLEGGSDEL,
        datatype=FieldType.DOUBLE,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    SUBTYPEKODE = FieldDefinition(
        name=ColumnName.SUBTYPEKODE,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    TYPEVEG = FieldDefinition(
        name=ColumnName.TYPEVEG,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    UTTEGNING = FieldDefinition(
        name=ColumnName.UTTEGNING,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    VEDLIKEH = FieldDefinition(
        name=ColumnName.VEDLIKEH,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    VEGKATEGORI = FieldDefinition(
        name=ColumnName.VEGKATEGORI,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    VEGKLASSE = FieldDefinition(
        name=ColumnName.VEGKLASSE,
        datatype=FieldType.DOUBLE,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    VEGNUMMER = FieldDefinition(
        name=ColumnName.VEGNUMMER,
        datatype=FieldType.DOUBLE,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
    VEGSTATUS = FieldDefinition(
        name=ColumnName.VEGSTATUS,
        datatype=FieldType.STRING,
        usage=FieldUsage.INPUT | FieldUsage.PROCESSING,
    )
