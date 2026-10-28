# Libraries

from dataclasses import dataclass

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, GDBName
from data_orchestrator_2.schemas.datasets import DatasetCatalog, DatasetDefinition

######################
# Classes
######################


@dataclass(frozen=True)
class PipelineDefinition:
    """Target scale and datasets required for one object-type pipeline."""

    gdb_name: GDBName
    scale: Scale
    datasets: dict[FeatureClassName, DatasetDefinition]

    def __str__(self) -> str:
        dataset_names = ", ".join(ds.name.value for ds in self.datasets.values())

        return (
            "\nPipelineDefinition("
            f"\n\tgdb_name={self.gdb_name},"
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


PIPELINES: dict[tuple[GDBName, Scale], PipelineDefinition] = {
    (GDBName.ROAD, Scale.N100): PipelineDefinition(
        gdb_name=GDBName.ROAD,
        scale=Scale.N100,
        datasets={FeatureClassName.ELVEG_AND_STI: DatasetCatalog.ELVEG_AND_STI},
    ),
}


######################
# Functionality
######################


def get_pipeline(gdb_name: GDBName, scale: Scale) -> PipelineDefinition:
    """Look up a pipeline by object type and target scale; raise KeyError if absent."""
    return PIPELINES[(gdb_name, scale)]
