# Libraries

from dataclasses import dataclass, field

from custom_tools.general_tools.validation import (
    feature_class_exists,
    fetch_existing_fields,
    has_data,
)
from data_orchestrator_2.pipelines import PipelineDefinition

######################
# Classes
######################


@dataclass
class ValidationResult:
    dataset_name: str
    path: str
    exists: bool = False
    has_rows: bool = False
    missing_fields: list[str] = field(default_factory=list)
    wrong_datatypes: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return (
            self.exists
            and self.has_rows
            and not self.missing_fields
            and not self.wrong_datatypes
        )

    def __str__(self) -> str:
        return (
            "\nValidationResult("
            f"\n\tdataset_name={self.dataset_name},"
            f"\n\tsuccess={self.success},"
            f"\n\texists={self.exists},"
            f"\n\thas_rows={self.has_rows},"
            f"\n\tmissing_fields={self.missing_fields},"
            f"\n\twrong_datatypes={self.wrong_datatypes}"
            "\n)\n"
        )

    def __bool__(self) -> bool:
        return self.success


######################
# Functionality
######################


def validate_pipeline(pipeline: PipelineDefinition) -> list[ValidationResult]:
    results: list[ValidationResult] = []

    for ds in pipeline.getDatasets():
        validation = ValidationResult(dataset_name=ds.getName(), path=str(ds.getPath()))

        validation.exists = feature_class_exists(validation.path)

        if validation.exists:
            validation.has_rows = has_data(validation.path)

            current_fields = fetch_existing_fields(validation.path)

            required = {f.name: f for f in ds.getInputFields()}
            actual = {f.name: f for f in current_fields}

            validation.missing_fields = list(required.keys() - actual.keys())

            for field_name in required.keys() & actual.keys():
                if required[field_name].datatype != actual[field_name].type:
                    validation.wrong_datatypes.append(
                        f"{field_name}: "
                        f"expected={required[field_name].datatype}, "
                        f"actual={actual[field_name].type}"
                    )

        results.append(validation)

    return results
