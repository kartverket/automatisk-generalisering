# Libraries

from dataclasses import InitVar, dataclass, field

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from data_orchestrator_2.organizers.validator import validate_pipeline
from data_orchestrator_2.runtime.dataset import Dataset
from data_orchestrator_2.schemas.fields import FieldUsage
from data_orchestrator_2.schemas.pipelines import PipelineDefinition, get_pipeline

######################
# Classes
######################


@dataclass(slots=True)
class Pipeline:
    object_type: InitVar[ObjectType]
    scale: InitVar[Scale]
    definition: PipelineDefinition = field(init=False)
    datasets: dict[FeatureClassName, Dataset] = field(init=False)
    error: bool = False
    warning: bool = False

    def __post_init__(self, object_type: ObjectType, scale: Scale) -> None:
        self.definition = get_pipeline(object_type, scale)
        self.datasets = {
            name: Dataset(dataset_definition)
            for name, dataset_definition in self.definition.datasets.items()
        }

    def __str__(self) -> str:
        return f"Pipeline:\n{self.definition.__str__()}\nStatus:\n\t- Error: {self.error}\n\t- Warning: {self.warning}"

    def getDataset(self, name: FeatureClassName) -> Dataset:
        return self.datasets[name]

    def validInput(self) -> None:
        self._validate(FieldUsage.INPUT)

    def validProcessing(self) -> None:
        self._validate(FieldUsage.PROCESSING)

    def validOutput(self) -> None:
        self._validate(FieldUsage.OUTPUT)

    def errorReport(self) -> None:
        for dataset_name, dataset in self.datasets.items():
            if dataset.error:
                print(f"Error in dataset {dataset_name}: {dataset.error_message}")

    def warningReport(self) -> None:
        for dataset_name, dataset in self.datasets.items():
            if dataset.warning:
                print(f"Warning in dataset {dataset_name}: {dataset.warning_message}")

    def _validate(self, usage: FieldUsage) -> None:
        for result in validate_pipeline(self, usage):
            dataset = self.datasets[result.dataset_name]
            dataset.validated = True
            dataset.error = not result.success
            dataset.warning = result.warning
            dataset.error_message = result.error_message if dataset.error else ""
            dataset.warning_message = result.warning_message if dataset.warning else ""

        self.error = any(dataset.error for dataset in self.datasets.values())
        self.warning = any(dataset.warning for dataset in self.datasets.values())
