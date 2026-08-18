"""
Stage Implementation Template and Guide

Use this template when creating new stages.

## Single-Input, Single-Output Stage Template

If your stage runs a single processing function with one input and one output:

```python
from composition_configs.logic_config import DataRef
from stage_factory import make_stage
from n100.road.function_calls import your_processing_function

def process_your_stage(input_root: DataRef, output_root: DataRef) -> None:
    input_fc = DataRef(
        path=f"{input_root.path}/input",
        tag=input_root.tag,
    )
    output_fc = DataRef(
        path=f"{output_root.path}/output",
        tag=output_root.tag,
    )
    
    your_processing_function(
        input=input_fc,
        output=output_fc,
    )

your_stage_name = make_stage(process_your_stage)
```

## Multi-Output Stage Template

If your stage produces multiple outputs (e.g., lines and points):

```python
from composition_configs.logic_config import DataRef
from stage_factory import make_stage
from n100.road.function_calls import your_processing_function

def process_your_stage(input_root: DataRef, output_root: DataRef) -> None:
    input_fc = DataRef(
        path=f"{input_root.path}/input",
        tag=input_root.tag,
    )
    output_fc = DataRef(
        path=f"{output_root.path}/output",
        tag=output_root.tag,
    )
    output_secondary_fc = DataRef(
        path=f"{output_root.path}/output_secondary",
        tag=output_root.tag,
    )
    
    your_processing_function(
        input=input_fc,
        output_main=output_fc,
        output_secondary=output_secondary_fc,
    )

your_stage_name = make_stage(process_your_stage)
```

## Multi-Input Stage Template

If your stage needs multiple input datasets (e.g., roads and buildings):

```python
from composition_configs.logic_config import DataRef
from stage_factory import make_stage
from n100.road.function_calls import your_processing_function

def process_your_stage(input_root: DataRef, output_root: DataRef) -> None:
    # Construct multiple inputs from input_root
    input_roads = DataRef(
        path=f"{input_root.path}/roads",
        tag=input_root.tag,
    )
    input_buildings = DataRef(
        path=f"{input_root.path}/buildings",
        tag=input_root.tag,
    )
    output_fc = DataRef(
        path=f"{output_root.path}/output",
        tag=output_root.tag,
    )
    
    your_processing_function(
        input_roads=input_roads,
        input_buildings=input_buildings,
        output=output_fc,
    )

your_stage_name = make_stage(process_your_stage)
```

## Important Notes

1. **Input/Output root paths**: The factory provides input_root and output_root which point to the downloaded/uploaded directories
2. **Construct paths from roots**: Always construct input_fc and output_fc by using `f"{input_root.path}/{featureclass}"` or `f"{output_root.path}/{featureclass}"`
3. **Logging**: Import logging if you need to add log messages
4. **Error handling**: Handle errors in the process_fn; the factory will propagate them

## Adding to Pipeline Registry

After creating your stage file, add it to stages/__init__.py:

```python
from .your_stage_name import your_stage_name

__all__ = [
    'thin_road_stage',
    'ramps_stage',
    'your_stage_name',  # Add here
]
```

Then register in pipeline.py:

```python
n100_roads_pipeline = PipelineDefinition(
    name="n100_roads",
    stages={
        "thin_road": thin_road_stage,
        "ramps": ramps_stage,
        "your_stage": your_stage_name,  # Add here
    }
)
```
"""
