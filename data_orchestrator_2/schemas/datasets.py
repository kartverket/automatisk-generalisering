# Libraries

from dataclasses import dataclass, field
from enum import Flag, auto
from types import MappingProxyType
from typing import Mapping

from data_orchestrator_2.constants.common import FieldType, GeometryType, Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, GDBName
from data_orchestrator_2.constants.values import ColumnName
from data_orchestrator_2.schemas.fields import FieldCatalog, FieldDefinition

######################
# Classes
######################


class FieldUsage(Flag):
    """Stages at which a field is expected or retained; values may be combined."""

    INPUT = auto()
    PROCESSING = auto()
    OUTPUT = auto()


@dataclass(frozen=True)
class DatasetField:
    field: FieldDefinition
    usage: FieldUsage
    required: bool

    @property
    def name(self) -> ColumnName:
        return self.field.name

    @property
    def datatype(self) -> FieldType:
        return self.field.datatype

    @property
    def system_field(self) -> bool:
        return self.field.system_field

    def isUsedFor(self, usage: FieldUsage) -> bool:
        """Return whether any requested usage flag belongs to this field."""
        return bool(self.usage & usage)


@dataclass(frozen=True, slots=True)
class DatasetDefinition:
    """Dataset schema and path derived from its source scale and object type."""

    name: FeatureClassName
    source_scale: Scale
    gdb_name: GDBName
    geometry_type: GeometryType
    fields: tuple[DatasetField, ...]
    _field_lookup: Mapping[ColumnName, DatasetField] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        normalized_fields = tuple(self.fields)
        field_lookup = {field.name: field for field in normalized_fields}
        if len(field_lookup) != len(normalized_fields):
            raise ValueError(f"Dataset {self.name} contains duplicate field names")

        object.__setattr__(self, "fields", normalized_fields)
        object.__setattr__(self, "_field_lookup", MappingProxyType(field_lookup))

    def __str__(self) -> str:
        fields = "".join(f"\n\t\t- {f.name}" for f in self.fields)
        return (
            "\nDatasetDefinition("
            f"\n\tname={self.name},"
            f"\n\tgeometry_type={self.geometry_type},"
            f"\n\tfields ({len(self.fields)}):{fields}"
            "\n)\n"
        )

    def getFieldNames(self) -> tuple[ColumnName, ...]:
        """Return the names of all registered fields."""
        return tuple(field.name for field in self.fields)

    def getField(self, field_name: ColumnName) -> DatasetField:
        """Return a registered field or raise KeyError if it is unknown."""
        return self._field_lookup[field_name]

    def getFieldsFor(self, usage: FieldUsage) -> tuple[DatasetField, ...]:
        """Return fields carrying any of the requested usage flags."""
        return tuple(field for field in self.fields if field.isUsedFor(usage))

    def hasField(self, field_name: ColumnName) -> bool:
        """Return True if the dataset contains the specified field."""
        return field_name in self._field_lookup


######################
# Toolbox
######################


def used_for(
    field: FieldDefinition, usage: FieldUsage, required: bool = True
) -> DatasetField:
    return DatasetField(field=field, usage=usage, required=required)


######################
# Datasets
######################


class DatasetCatalog:
    """Named dataset definitions available to pipelines."""

    ELVEG_AND_STI = DatasetDefinition(
        name=FeatureClassName.ELVEG_AND_STI,
        source_scale=Scale.RAW_DATA,
        gdb_name=GDBName.ROAD,
        geometry_type=GeometryType.POLYLINE,
        fields=(
            used_for(
                FieldCatalog.ADRESSENAVN, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.ADSKILTELOP, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.ADSKILTELOPNUMMER, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.FELTOVERSIKT, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.KONNEKTERINGSLENKE,
                FieldUsage.INPUT | FieldUsage.PROCESSING,
            ),
            used_for(FieldCatalog.KRYSSDEL, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(FieldCatalog.MEDIUM, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(
                FieldCatalog.MOTORVEGTYPE, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.OBJECTID,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
            ),
            used_for(FieldCatalog.OBJTYPE, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(
                FieldCatalog.RUTEMERKING, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.SHAPE,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
            ),
            used_for(
                FieldCatalog.SHAPE_LENGTH, FieldUsage.PROCESSING | FieldUsage.OUTPUT
            ),
            used_for(
                FieldCatalog.SIDEANLEGGSDEL, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(
                FieldCatalog.SUBTYPEKODE, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(FieldCatalog.TYPEVEG, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(FieldCatalog.UTTEGNING, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(FieldCatalog.VEDLIKEH, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(
                FieldCatalog.VEGKATEGORI, FieldUsage.INPUT | FieldUsage.PROCESSING
            ),
            used_for(FieldCatalog.VEGKLASSE, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(FieldCatalog.VEGNUMMER, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(FieldCatalog.VEGSTATUS, FieldUsage.INPUT | FieldUsage.PROCESSING),
        ),
    )

    VEGSPERRING = DatasetDefinition(
        name=FeatureClassName.VEGSPERRING,
        source_scale=Scale.RAW_DATA,
        gdb_name=GDBName.ROAD,
        geometry_type=GeometryType.POINT,
        fields=(
            used_for(FieldCatalog.EIER, FieldUsage.INPUT),
            used_for(FieldCatalog.FUNKSJON, FieldUsage.INPUT),
            used_for(
                FieldCatalog.OBJECTID,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
            ),
            used_for(FieldCatalog.OBJTYPE, FieldUsage.INPUT | FieldUsage.PROCESSING),
            used_for(
                FieldCatalog.SHAPE,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
            ),
            used_for(FieldCatalog.TYPE, FieldUsage.INPUT),
        ),
    )
