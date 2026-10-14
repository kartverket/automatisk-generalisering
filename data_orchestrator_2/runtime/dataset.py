# Libraries

from dataclasses import dataclass, field

from data_orchestrator_2.path_factory import get_feature_class_full_path
from data_orchestrator_2.schemas.datasets import DatasetDefinition

######################
# Classes
######################


@dataclass(slots=True)
class Dataset:
    definition: DatasetDefinition
    path: str = field(init=False)
    validated: bool = False

    def __post_init__(self) -> None:
        self.path = str(
            get_feature_class_full_path(
                scale=self.definition.source_scale,
                object_type=self.definition.object_type,
                feature_class_name=self.definition.name,
                path_type=str,
            )
        )

    def set_path(self, path: str) -> None:
        self.path = path
