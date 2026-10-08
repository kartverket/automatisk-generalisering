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
    name: FeatureClassName
    source_scale: Scale  # TODO: Slette?
    object_type: ObjectType  # TODO: Slette?
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
        return tuple(f.name for f in self.fields)

    def getField(self, field_name: str) -> FieldDefinition:
        return self.field_lookup[field_name]

    def getInputFields(self) -> tuple[FieldDefinition, ...]:
        return tuple(field for field in self.fields if field.usage & FieldUsage.INPUT)

    def getProcessingFields(self) -> tuple[FieldDefinition, ...]:
        return tuple(
            field for field in self.fields if field.usage & FieldUsage.PROCESSING
        )

    def getOutputFields(self) -> tuple[FieldDefinition, ...]:
        return tuple(field for field in self.fields if field.usage & FieldUsage.OUTPUT)

    def getPath(self) -> Path:
        return self.path


######################
# Datasets
######################


class Datasets:
    ELVEG_AND_STI = DatasetDefinition(
        name=FeatureClassName.ELVEG_AND_STI,
        source_scale=Scale.RAW_DATA,
        object_type=ObjectType.ROAD,
        geometry_type=GeometryType.POLYLINE,
        fields=(
            Fields.OBJTYPE,
            Fields.SUBTYPEKODE,
            Fields.TYPEVEG,
            Fields.VEGKATEGORI,
            Fields.VEGNUMMER,
            Fields.VEGSTATUS,
            Fields.MEDIUM,
            Fields.MOTORVEGTYPE,
            Fields.RUTEMERKING,
            Fields.VEDLIKEH,
            Fields.UTTEGNING,
            Fields.VEGKLASSE,
            Fields.FELTOVERSIKT,
            Fields.KONNEKTERINGSLENKE,
            Fields.SIDEANLEGGSDEL,
            Fields.KRYSSDEL,
            Fields.ADSKILTELOP,
            Fields.ADSKILTELOPNUMMER,
            Fields.ADRESSENAVN,
            Fields.OBJECTID,
            Fields.SHAPE,
        ),
    )
