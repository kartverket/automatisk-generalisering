# Libraries

from dataclasses import dataclass

from data_orchestrator_2.constants.columns import ColumnName
from data_orchestrator_2.constants.general import FieldType

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
    AREAL_M2 = FieldDefinition(
        name=ColumnName.AREAL_M2,
        datatype=FieldType.DOUBLE,
    )
    AREALBRUK_HOVEDKLASSE = FieldDefinition(
        name=ColumnName.AREALBRUK_HOVEDKLASSE,
        datatype=FieldType.STRING,
    )
    AREALBRUK_UNDERKLASSE = FieldDefinition(
        name=ColumnName.AREALBRUK_UNDERKLASSE,
        datatype=FieldType.STRING,
    )
    AREALDEKKE = FieldDefinition(
        name=ColumnName.AREALDEKKE,
        datatype=FieldType.STRING,
    )
    BRUKTFLAGG = FieldDefinition(
        name=ColumnName.BRUKTFLAGG,
        datatype=FieldType.LONG,
    )
    DGFCD_FEATURE_531 = FieldDefinition(
        name=ColumnName.DGFCD_FEATURE_531,
        datatype=FieldType.STRING,
    )
    DGFCD_FEATURE_ALPHA = FieldDefinition(
        name=ColumnName.DGFCD_FEATURE_ALPHA,
        datatype=FieldType.STRING,
    )
    DGIF_CCODE = FieldDefinition(
        name=ColumnName.DGIF_CCODE,
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
    GRUNNFORHOLD = FieldDefinition(
        name=ColumnName.GRUNNFORHOLD,
        datatype=FieldType.STRING,
    )
    GRUNNKART_KILDE = FieldDefinition(
        name=ColumnName.GRUNNKART_KILDE,
        datatype=FieldType.STRING,
    )
    HAVAREALBRUKSTEDSBUNDET = FieldDefinition(
        name=ColumnName.HAVAREALBRUKSTEDSBUNDET,
        datatype=FieldType.STRING,
    )
    HAVFISKERIBRUK = FieldDefinition(
        name=ColumnName.HAVFISKERIBRUK,
        datatype=FieldType.STRING,
    )
    HIERARKI = FieldDefinition(
        name=ColumnName.HIERARKI,
        datatype=FieldType.SHORT,
    )
    HOYDE = FieldDefinition(
        name=ColumnName.HOYDE,
        datatype=FieldType.STRING,
    )
    ID = FieldDefinition(
        name=ColumnName.ID,
        datatype=FieldType.LONG,
    )
    KOMID = FieldDefinition(
        name=ColumnName.KOMID,
        datatype=FieldType.LONG,
    )
    KONNEKTERINGSLENKE = FieldDefinition(
        name=ColumnName.KONNEKTERINGSLENKE,
        datatype=FieldType.STRING,
    )
    KRYSSDEL = FieldDefinition(
        name=ColumnName.KRYSSDEL,
        datatype=FieldType.DOUBLE,
    )
    LRV = FieldDefinition(
        name=ColumnName.LRV,
        datatype=FieldType.LONG,
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
    OKOSYSTEMTYPE_1 = FieldDefinition(
        name=ColumnName.OKOSYSTEMTYPE_1,
        datatype=FieldType.STRING,
    )
    OKOSYSTEMTYPE_2 = FieldDefinition(
        name=ColumnName.OKOSYSTEMTYPE_2,
        datatype=FieldType.STRING,
    )
    OKOSYSTEMTYPE_3 = FieldDefinition(
        name=ColumnName.OKOSYSTEMTYPE_3,
        datatype=FieldType.STRING,
    )
    OKOSYSTEMTYPE_KODE = FieldDefinition(
        name=ColumnName.OKOSYSTEMTYPE_KODE,
        datatype=FieldType.STRING,
    )
    OMKRETS = FieldDefinition(
        name=ColumnName.OMKRETS,
        datatype=FieldType.DOUBLE,
    )
    PARTITION_SELECTION_FIELD = FieldDefinition(
        name=ColumnName.PARTITION_SELECTION_FIELD,
        datatype=FieldType.LONG,
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
    SHAPE_AREA = FieldDefinition(
        name=ColumnName.SHAPE_AREA,
        datatype=FieldType.DOUBLE,
        system_field=True,
    )
    SHAPE_LENGTH = FieldDefinition(
        name=ColumnName.SHAPE_LENGTH,
        datatype=FieldType.DOUBLE,
        system_field=True,
    )
    SKOGBONITET = FieldDefinition(
        name=ColumnName.SKOGBONITET,
        datatype=FieldType.STRING,
    )
    SIDEANLEGGSDEL = FieldDefinition(
        name=ColumnName.SIDEANLEGGSDEL,
        datatype=FieldType.DOUBLE,
    )
    SSBAREALBRUK_KILDE = FieldDefinition(
        name=ColumnName.SSBAREALBRUK_KILDE,
        datatype=FieldType.STRING,
    )
    SUBTYPEKODE = FieldDefinition(
        name=ColumnName.SUBTYPEKODE,
        datatype=FieldType.STRING,
    )
    TRESLAG = FieldDefinition(
        name=ColumnName.TRESLAG,
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
