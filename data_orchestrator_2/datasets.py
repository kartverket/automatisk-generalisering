# Libraries

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from data_orchestrator_2.fields import FieldDefinition, Fields, FieldUsage
from data_orchestrator_2.names_paths import (
    ColumnName,
    FeatureClassName,
    GeometryType,
    ObjectType,
    Scale,
    get_feature_class_full_path,
)

######################
# Classes
######################


@dataclass(frozen=True)
class DatasetDefinition:
    """Dataset schema and path derived from its source scale and object type."""

    name: FeatureClassName
    source_scale: Scale
    object_type: ObjectType
    geometry_type: GeometryType
    fields: tuple[FieldDefinition, ...]
    path: Path = field(init=False)
    _field_lookup: Mapping[str, FieldDefinition] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        normalized_fields = tuple(self.fields)
        field_lookup = {field.name: field for field in normalized_fields}
        if len(field_lookup) != len(normalized_fields):
            raise ValueError(f"Dataset {self.name} contains duplicate field names")

        object.__setattr__(self, "fields", normalized_fields)
        object.__setattr__(
            self,
            "path",
            get_feature_class_full_path(
                scale=self.source_scale,
                object_type=self.object_type,
                feature_class_name=self.name,
            ),
        )
        object.__setattr__(self, "_field_lookup", MappingProxyType(field_lookup))

    @property
    def field_lookup(self) -> Mapping[str, FieldDefinition]:
        """Read-only lookup of field definitions by their catalog names."""
        return self._field_lookup

    def __str__(self) -> str:
        fields = "".join(f"\n\t\t- {f.name}" for f in self.fields)
        return (
            "\nDatasetDefinition("
            f"\n\tname={self.name},"
            f"\n\tgeometry_type={self.geometry_type},"
            f"\n\tpath={self.path},"
            f"\n\tfields ({len(self.fields)}):{fields}"
            "\n)\n"
        )

    def getName(self) -> FeatureClassName:
        return self.name

    def getGeometryType(self) -> GeometryType:
        return self.geometry_type

    def getFields(self) -> tuple[ColumnName, ...]:
        """Return the names of all registered fields."""
        return tuple(f.name for f in self.fields)

    def getField(self, field_name: str) -> FieldDefinition:
        """Return a registered field or raise KeyError if it is unknown."""
        return self.field_lookup[field_name]

    def getFieldsFor(self, usage: FieldUsage) -> tuple[FieldDefinition, ...]:
        """Return fields carrying any of the requested usage flags."""
        return tuple(field for field in self.fields if field.isUsedFor(usage))

    def getPath(self) -> Path:
        return self.path


######################
# Datasets
######################


class Datasets:
    """Named dataset definitions available to pipelines."""

    ELVEG_AND_STI = DatasetDefinition(
        name=FeatureClassName.ELVEG_AND_STI,
        source_scale=Scale.RAW_DATA,
        object_type=ObjectType.ROAD,
        geometry_type=GeometryType.POLYLINE,
        fields=(
            Fields.ADSKILTELOP,
            Fields.ADSKILTELOPNUMMER,
            Fields.ADRESSENAVN,
            Fields.FELTOVERSIKT,
            Fields.KONNEKTERINGSLENKE,
            Fields.KRYSSDEL,
            Fields.MEDIUM,
            Fields.MOTORVEGTYPE,
            Fields.OBJECTID,
            Fields.OBJTYPE,
            Fields.RUTEMERKING,
            Fields.SHAPE,
            Fields.SIDEANLEGGSDEL,
            Fields.SUBTYPEKODE,
            Fields.TYPEVEG,
            Fields.UTTEGNING,
            Fields.VEDLIKEH,
            Fields.VEGKATEGORI,
            Fields.VEGKLASSE,
            Fields.VEGNUMMER,
            Fields.VEGSTATUS,
        ),
    )
