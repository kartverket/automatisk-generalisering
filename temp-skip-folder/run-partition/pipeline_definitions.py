from collections.abc import Callable
from dataclasses import dataclass


StageFunction = Callable[..., None]


@dataclass(frozen=True)
class PipelineDefinition:
    name: str
    stages: dict[str, StageFunction]

    def get_stage(self, stage_name: str) -> StageFunction:
        try:
            return self.stages[stage_name]
        except KeyError:
            valid_stages = ", ".join(sorted(self.stages))
            raise ValueError(
                f"Invalid stage '{stage_name}' for pipeline '{self.name}'. "
                f"Valid stages: {valid_stages}"
            ) from None


