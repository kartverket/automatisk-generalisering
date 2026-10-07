# Libraries

from dataclasses import dataclass

from data_orchestrator_2.pipelines import PipelineDefinition

######################
# Classes
######################


@dataclass(frozen=True)
class ValidationResult:
    dataset_name: str

    exists: bool
    has_rows: bool

    missing_fields: list[str]
    wrong_datatypes: list[str]

    success: bool


class DatasetValidator:
    def validate_pipeline(self, pipeline: PipelineDefinition) -> ValidationResult:
        pass
