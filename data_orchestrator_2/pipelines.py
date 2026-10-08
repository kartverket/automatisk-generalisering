# Libraries

from dataclasses import dataclass

from data_orchestrator_2.datasets import DatasetDefinition, Datasets
from data_orchestrator_2.names_paths import ObjectType, Scale

######################
# Classes
######################


@dataclass(frozen=True)
class PipelineDefinition:
    object_type: ObjectType
    scale: Scale
    datasets: tuple[DatasetDefinition, ...]

    def __str__(self) -> str:
        dataset_names = ", ".join(ds.name for ds in self.datasets)

        return (
            "\nPipelineDefinition("
            f"\n\tobject_type={self.object_type},"
            f"\n\tscale={self.scale},"
            f"\n\tdatasets=([{dataset_names}], {len(self.datasets)})"
            "\n)\n"
        )

    def getObjectType(self) -> ObjectType:
        return self.object_type

    def getScale(self) -> Scale:
        return self.scale

    def getDatasets(self) -> tuple[DatasetDefinition, ...]:
        return self.datasets


######################
# Pipelines
######################


PIPELINES: dict[tuple[ObjectType, Scale], PipelineDefinition] = {
    (ObjectType.ROAD, Scale.N100): PipelineDefinition(
        object_type=ObjectType.ROAD,
        scale=Scale.N100,
        datasets=(Datasets.ELVEG_AND_STI,),
    ),
}


######################
# Functionality
######################


def get_pipeline(object_type: ObjectType, scale: Scale) -> PipelineDefinition:
    return PIPELINES[(object_type, scale)]
