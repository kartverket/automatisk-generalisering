# Libraries

from dataclasses import dataclass, field

from data_orchestrator_2.constants.featureClasses import FeatureClassName
from data_orchestrator_2.runtime.dataset import Dataset
from data_orchestrator_2.schemas.pipelines import PipelineDefinition

######################
# Classes
######################


@dataclass(slots=True)
class Pipeline:
    definition: PipelineDefinition
    datasets: dict[FeatureClassName, Dataset] = field(init=False)

    def __post_init__(self) -> None:
        self.datasets = {
            name: Dataset(dataset_definition)
            for name, dataset_definition in self.definition.datasets.items()
        }
