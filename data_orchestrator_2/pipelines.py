# Libraries

from dataclasses import dataclass

from data_orchestrator_2.datasets import DatasetDefinition, Datasets

######################
# Classes
######################


@dataclass(frozen=True)
class PipelineDefinition:
    object_type: str
    scale: str
    datasets: tuple[DatasetDefinition, ...]


######################
# Pipelines
######################


N100_VEG = PipelineDefinition(
    object_type="veg",
    scale="n100",
    datasets=(Datasets.ELVEG_AND_STI,),
)


PIPELINES = {
    ("vei", "n100"): N100_VEG,
}
