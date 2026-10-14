# Libraries

from dataclasses import dataclass

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from data_orchestrator_2.schemas.datasets import DatasetCatalog, DatasetDefinition

######################
# Classes
######################


@dataclass(frozen=True)
class PipelineDefinition:
    """Target scale and datasets required for one object-type pipeline."""

    object_type: ObjectType
    scale: Scale
    datasets: dict[FeatureClassName, DatasetDefinition]

    def __str__(self) -> str:
        dataset_names = ", ".join(ds.name.value for ds in self.datasets.values())

        return (
            "\nPipelineDefinition("
            f"\n\tobject_type={self.object_type},"
            f"\n\tscale={self.scale},"
            f"\n\tdatasets=([{dataset_names}], {len(self.datasets)})"
            "\n)\n"
        )

    def getDatasetNames(self) -> tuple[FeatureClassName, ...]:
        return tuple(self.datasets.keys())

    def getAllDatasets(self) -> tuple[DatasetDefinition, ...]:
        return tuple(self.datasets.values())

    def getDataset(self, name: FeatureClassName) -> DatasetDefinition:
        return self.datasets[name]


######################
# Pipelines
######################


PIPELINES: dict[tuple[ObjectType, Scale], PipelineDefinition] = {
    (ObjectType.ROAD, Scale.N100): PipelineDefinition(
        object_type=ObjectType.ROAD,
        scale=Scale.N100,
        datasets={FeatureClassName.ELVEG_AND_STI: DatasetCatalog.ELVEG_AND_STI},
    ),
}


######################
# Functionality
######################


def get_pipeline(object_type: ObjectType, scale: Scale) -> PipelineDefinition:
    """Look up a pipeline by object type and target scale; raise KeyError if absent."""
    return PIPELINES[(object_type, scale)]
