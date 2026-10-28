# Libraries

from dataclasses import dataclass

from data_orchestrator_2.constants.common import FieldType
from data_orchestrator_2.constants.values import ColumnName

######################
# Classes
######################


@dataclass(frozen=True)
class FieldDefinition:
    """Catalog metadata for a field; requiredness is separate from usage."""

    name: ColumnName
    datatype: FieldType

    system_field: bool = False


######################
# Fields
######################


# Field registry, where all defined fields can be stored for easy access.
class FieldCatalog:
    """Reusable field definitions for dataset catalogs."""

    ADRESSENAVN = FieldDefinition(
        name=ColumnName.ADRESSENAVN,
        datatype=FieldType.STRING,
    )
    ADSKILTELOP = FieldDefinition(
        name=ColumnName.ADSKILTELOP,
        datatype=FieldType.STRING,
    )
    ADSKILTELOPNUMMER = FieldDefinition(
        name=ColumnName.ADSKILTELOPNUMMER,
        datatype=FieldType.STRING,
    )
    EIER = FieldDefinition(
        name=ColumnName.EIER,
        datatype=FieldType.STRING,
    )
    ER_KRYSSNINGSPUNKT = FieldDefinition(
        name=ColumnName.ER_KRYSSNINGSPUNKT,
        datatype=FieldType.BOOLEAN,
    )
    FELTOVERSIKT = FieldDefinition(
        name=ColumnName.FELTOVERSIKT,
        datatype=FieldType.STRING,
    )
    FUNKSJON = FieldDefinition(
        name=ColumnName.FUNKSJON,
        datatype=FieldType.STRING,
    )
    HIERARKI = FieldDefinition(
        name=ColumnName.HIERARKI,
        datatype=FieldType.SHORT,
    )
    KONNEKTERINGSLENKE = FieldDefinition(
        name=ColumnName.KONNEKTERINGSLENKE,
        datatype=FieldType.STRING,
    )
    KRYSSDEL = FieldDefinition(
        name=ColumnName.KRYSSDEL,
        datatype=FieldType.DOUBLE,
    )
    MEDIUM = FieldDefinition(
        name=ColumnName.MEDIUM,
        datatype=FieldType.STRING,
    )
    MOTORVEGTYPE = FieldDefinition(
        name=ColumnName.MOTORVEGTYPE,
        datatype=FieldType.STRING,
    )
    OBJECTID = FieldDefinition(
        name=ColumnName.OBJECTID,
        datatype=FieldType.OID,
        system_field=True,
    )
    OBJTYPE = FieldDefinition(
        name=ColumnName.OBJTYPE,
        datatype=FieldType.STRING,
    )
    RUTEMERKING = FieldDefinition(
        name=ColumnName.RUTEMERKING,
        datatype=FieldType.STRING,
    )
    SHAPE = FieldDefinition(
        name=ColumnName.SHAPE,
        datatype=FieldType.GEOMETRY,
        system_field=True,
    )
    SHAPE_LENGTH = FieldDefinition(
        name=ColumnName.SHAPE_LENGTH,
        datatype=FieldType.DOUBLE,
        system_field=True,
    )
    SIDEANLEGGSDEL = FieldDefinition(
        name=ColumnName.SIDEANLEGGSDEL,
        datatype=FieldType.DOUBLE,
    )
    SUBTYPEKODE = FieldDefinition(
        name=ColumnName.SUBTYPEKODE,
        datatype=FieldType.STRING,
    )
    TYPE = FieldDefinition(
        name=ColumnName.TYPE,
        datatype=FieldType.STRING,
    )
    TYPEVEG = FieldDefinition(
        name=ColumnName.TYPEVEG,
        datatype=FieldType.STRING,
    )
    UTTEGNING = FieldDefinition(
        name=ColumnName.UTTEGNING,
        datatype=FieldType.STRING,
    )
    VEDLIKEH = FieldDefinition(
        name=ColumnName.VEDLIKEH,
        datatype=FieldType.STRING,
    )
    VEGKATEGORI = FieldDefinition(
        name=ColumnName.VEGKATEGORI,
        datatype=FieldType.STRING,
    )
    VEGKLASSE = FieldDefinition(
        name=ColumnName.VEGKLASSE,
        datatype=FieldType.DOUBLE,
    )
    VEGNUMMER = FieldDefinition(
        name=ColumnName.VEGNUMMER,
        datatype=FieldType.DOUBLE,
    )
    VEGSTATUS = FieldDefinition(
        name=ColumnName.VEGSTATUS,
        datatype=FieldType.STRING,
    )
