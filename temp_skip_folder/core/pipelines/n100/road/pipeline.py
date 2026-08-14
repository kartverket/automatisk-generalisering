from n100.road.stages import thin_road_stage, ramps_stage
from pipeline_definitions import PipelineDefinition


n100_roads_pipeline = PipelineDefinition(
    name="n100_roads",
    stages={
        "thin_road": thin_road_stage,
        "ramps": ramps_stage,                                             
    }
)