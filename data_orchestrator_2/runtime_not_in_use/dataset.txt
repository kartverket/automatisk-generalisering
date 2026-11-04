# Libraries

from dataclasses import dataclass, field

from data_orchestrator_2.organizers.path_factory import get_feature_class_full_path
from data_orchestrator_2.schemas.datasets import DatasetDefinition

######################
# Classes
######################


@dataclass(slots=True)
class Dataset:
    definition: DatasetDefinition
    path: str = field(init=False)
    validated: bool = False
    error: bool = False
    warning: bool = False
    error_message: str = ""
    warning_message: str = ""

    def __post_init__(self) -> None:
        self.path = get_feature_class_full_path(
            scale=self.definition.source_scale,
            object_type=self.definition.object_type,
            feature_class_name=self.definition.name,
        )

    def __str__(self) -> str:
        return f"Dataset:\n{self.definition.__str__()}\nPath: {self.path}\n\nStatus:\n\t- Validated: {self.validated}\n\t- Error: {self.error}\n\t- Warning: {self.warning}"

    def set_path(self, path: str) -> None:
        self.path = path
        self.set_validated(validated=False)

    def set_validated(self, validated: bool) -> None:
        self.validated = validated
        if not validated:
            self.error = False
            self.warning = False
