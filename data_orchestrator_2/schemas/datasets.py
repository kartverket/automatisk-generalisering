# Libraries

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from data_orchestrator_2.constants.common import GeometryType, Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from data_orchestrator_2.constants.values import ColumnName
from data_orchestrator_2.schemas.fields import FieldCatalog, FieldDefinition, FieldUsage

######################
# Classes
######################


@dataclass(frozen=True, slots=True)
class DatasetDefinition:
    """Dataset schema and path derived from its source scale and object type."""

    name: FeatureClassName
    source_scale: Scale
    object_type: ObjectType
    geometry_type: GeometryType
    fields: tuple[FieldDefinition, ...]
    _field_lookup: Mapping[ColumnName, FieldDefinition] = field(
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

    def getField(self, field_name: ColumnName) -> FieldDefinition:
        """Return a registered field or raise KeyError if it is unknown."""
        return self._field_lookup[field_name]

    def getFieldsFor(self, usage: FieldUsage) -> tuple[FieldDefinition, ...]:
        """Return fields carrying any of the requested usage flags."""
        return tuple(field for field in self.fields if field.isUsedFor(usage))

    def hasField(self, field_name: ColumnName) -> bool:
        """Return True if the dataset contains the specified field."""
        return field_name in self._field_lookup


######################
# Datasets
######################


class DatasetCatalog:
    """Named dataset definitions available to pipelines."""

    ELVEG_AND_STI = DatasetDefinition(
        name=FeatureClassName.ELVEG_AND_STI,
        source_scale=Scale.RAW_DATA,
        object_type=ObjectType.ROAD,
        geometry_type=GeometryType.POLYLINE,
        fields=(
            FieldCatalog.ADSKILTELOP,
            FieldCatalog.ADSKILTELOPNUMMER,
            FieldCatalog.ADRESSENAVN,
            FieldCatalog.FELTOVERSIKT,
            FieldCatalog.KONNEKTERINGSLENKE,
            FieldCatalog.KRYSSDEL,
            FieldCatalog.MEDIUM,
            FieldCatalog.MOTORVEGTYPE,
            FieldCatalog.OBJECTID,
            FieldCatalog.OBJTYPE,
            FieldCatalog.RUTEMERKING,
            FieldCatalog.SHAPE,
            FieldCatalog.SHAPE_LENGTH,
            FieldCatalog.SIDEANLEGGSDEL,
            FieldCatalog.SUBTYPEKODE,
            FieldCatalog.TYPEVEG,
            FieldCatalog.UTTEGNING,
            FieldCatalog.VEDLIKEH,
            FieldCatalog.VEGKATEGORI,
            FieldCatalog.VEGKLASSE,
            FieldCatalog.VEGNUMMER,
            FieldCatalog.VEGSTATUS,
        ),
    )
