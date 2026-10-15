from __future__ import annotations

# Libraries
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from custom_tools.general_tools.validation import (
    feature_class_exists,
    fetch_existing_fields,
    has_data,
)
from data_orchestrator_2.constants.featureClasses import FeatureClassName
from data_orchestrator_2.schemas.fields import FieldUsage

if TYPE_CHECKING:
    from data_orchestrator_2.runtime.pipeline import Pipeline

######################
# Classes
######################


@dataclass
class ValidationResult:
    """Schema and row checks for one dataset at a requested usage stage."""

    dataset_name: FeatureClassName
    path: str
    warning_message: str = ""
    error_message: str = ""
    exists: bool = False
    has_rows: bool = False
    missing_fields: list[str] = field(default_factory=list)
    extra_fields: list[str] = field(default_factory=list)
    wrong_datatypes: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the dataset exists, has rows, and passes required schema checks."""
        return (
            self.exists
            and self.has_rows
            and not self.missing_fields
            and not self.wrong_datatypes
        )

    @property
    def warning(self) -> bool:
        """Whether fields outside the requested usage are present."""
        return bool(self.extra_fields)

    def __str__(self) -> str:
        return (
            "\nValidationResult("
            f"\n\tdataset_name={self.dataset_name},"
            f"\n\tsuccess={self.success},"
            f"\n\twarning={self.warning},"
            f"\n\texists={self.exists},"
            f"\n\thas_rows={self.has_rows},"
            f"\n\tmissing_fields={self.missing_fields},"
            f"\n\textra_fields={self.extra_fields},"
            f"\n\twrong_datatypes={self.wrong_datatypes}"
            "\n)\n"
        )

    def __bool__(self) -> bool:
        return self.success

    def createWarningMessage(self) -> None:
        if self.warning:
            self.warning_message = f"Dataset {self.dataset_name} has extra fields: {', '.join(self.extra_fields)}"

    def createErrorMessage(self) -> None:
        if not self.success:
            message_parts = []
            if not self.exists:
                message_parts.append("Dataset does not exist.")
            if not self.has_rows:
                message_parts.append("Dataset has no rows.")
            if self.missing_fields:
                message_parts.append(
                    f"Missing fields: {', '.join(self.missing_fields)}."
                )
            if self.wrong_datatypes:
                message_parts.append(
                    f"Wrong datatypes: {', '.join(self.wrong_datatypes)}."
                )

            message = "\n".join(message_parts)

            self.error_message = (
                f"Dataset {self.dataset_name} failed validation.\n{message}"
            )


######################
# Functionality
######################


def validate_pipeline(pipeline: Pipeline, usage: FieldUsage) -> list[ValidationResult]:
    """Inspect every dataset for rows and fields expected at a usage stage.

    Missing optional fields are allowed; inspection does not alter the dataset.
    ArcPy inspection errors are handled by the shared validation helpers.
    """
    results: list[ValidationResult] = []

    for dataset in pipeline.datasets.values():
        definition = dataset.definition
        validation = ValidationResult(dataset_name=definition.name, path=dataset.path)

        validation.exists = feature_class_exists(validation.path)

        if validation.exists:
            validation.has_rows = has_data(validation.path)

            current_fields = fetch_existing_fields(validation.path)

            expected = {
                field.name.casefold(): field for field in definition.getFieldsFor(usage)
            }
            actual = {field.name.casefold(): field for field in current_fields}

            validation.missing_fields = sorted(
                field.name
                for name, field in expected.items()
                if field.required and name not in actual
            )
            validation.extra_fields = sorted(
                field.name for name, field in actual.items() if name not in expected
            )

            for field_name in expected.keys() & actual.keys():
                if (
                    expected[field_name].datatype.casefold()
                    != actual[field_name].type.casefold()
                ):
                    validation.wrong_datatypes.append(
                        f"{expected[field_name].name}: "
                        f"expected={expected[field_name].datatype}, "
                        f"actual={actual[field_name].type}"
                    )

        validation.createWarningMessage()
        validation.createErrorMessage()

        results.append(validation)

    return results
