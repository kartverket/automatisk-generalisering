# Libraries

from dataclasses import dataclass
from pathlib import Path

from data_orchestrator_2.fields import ALL_FIELDS, FieldDefinition, Fields, FieldUsage
from data_orchestrator_2.names_paths import get_feature_class_full_path
from data_orchestrator_2.names_paths import FeatureClassName, GeometryType, ObjectType, Scale

######################
# Classes
######################


@dataclass(frozen=True)
class DatasetDefinition:
    name: str
    source: Scale
    geometry_type: GeometryType
    fields: tuple[FieldDefinition, ...]

    @property
    def field_lookup(self) -> dict[str, FieldDefinition]:
        return {field.name: field for field in self.fields}

    def get_input_fields(self) -> tuple[FieldDefinition, ...]:
        return tuple(field for field in self.fields if field.usage & FieldUsage.INPUT)

    def get_processing_fields(self) -> tuple[FieldDefinition, ...]:
        return tuple(
            field for field in self.fields if field.usage & FieldUsage.PROCESSING
        )

    def get_output_fields(self) -> tuple[FieldDefinition, ...]:
        return tuple(field for field in self.fields if field.usage & FieldUsage.OUTPUT)

    def get_field(self, field_name: str) -> FieldDefinition:
        return self.field_lookup[field_name]


@dataclass(frozen=True)
class FeatureClass:
    definition: DatasetDefinition
    path: Path


######################
# Datasets
######################


ELVEG_AND_STI = DatasetDefinition(
    name=FeatureClassName.ELVEG_AND_STI,
    source=Scale.RAW_DATA,
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


class Datasets:
    ELVEG_AND_STI = ELVEG_AND_STI


######################
# Feature Classes
######################

elveg_and_sti = FeatureClass(
    definition=ELVEG_AND_STI,
    path=get_feature_class_full_path(
        scale=ELVEG_AND_STI.source,
        object_type=ObjectType.ROAD,
        feature_class_name=ELVEG_AND_STI.name,
    ),
)


class Registry:
    ELVEG_AND_STI = elveg_and_sti
