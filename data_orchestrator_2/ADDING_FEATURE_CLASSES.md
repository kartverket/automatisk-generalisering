# Adding New Feature Classes - Step-by-Step Guide

A guide to extending `data_orchestrator_2` with new feature classes through the **fields → datasets → pipelines** workflow.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Define Fields](#step-1-define-fields)
4. [Step 2: Create Dataset Definition](#step-2-create-dataset-definition)
5. [Step 3: Register Pipeline](#step-3-register-pipeline)
6. [Complete Example](#complete-example)
7. [Validation & Testing](#validation--testing)

---

## Overview

Adding a new feature class follows a **three-layer progression** through the schema system:

```mermaid
graph LR
    Step1["<b>Step 1</b><br/>Define Fields<br/>in fields.py"]
    Step2["<b>Step 2</b><br/>Create Dataset<br/>in datasets.py"]
    Step3["<b>Step 3</b><br/>Register Pipeline<br/>in pipelines.py"]
    Deploy["<b>Deploy</b><br/>Ready for use"]
    
    Step1 -->|FieldDefinitions| Step2
    Step2 -->|DatasetDefinition| Step3
    Step3 -->|PipelineDefinition| Deploy
    
    classDef step1 fill:#2196F3,stroke:#0D47A1,stroke-width:3px,color:#fff,font-weight:bold
    classDef step2 fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff,font-weight:bold
    classDef step3 fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff,font-weight:bold
    classDef deploy fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff,font-weight:bold
    
    class Step1 step1
    class Step2 step2
    class Step3 step3
    class Deploy deploy
```

Each layer **builds on the previous one**, ensuring that:
- Fields are reusable across datasets
- Datasets are frozen and immutable
- Pipelines are the entry point for runtime operations

---

## Prerequisites

Before adding a new feature class, ensure:

1. **Constants are defined** in `data_orchestrator_2/constants/`:
   - Add `FeatureClassName` to `fileStructures.py` (if new object type)
   - Add `GDBName` to `fileStructures.py` (if new geodatabase)
   - Add `GeometryType` to `general.py` (if geometry type not already present)
   - Add `ColumnName` values to `columns.py` (for each field)

2. **Example Prerequisites**:
   ```python
   # constants/fileStructures.py
   class FeatureClassName(StrEnum):
       BUILDING = "building"          # New feature class name
       BUILDINGS_PROCESSED = "buildings_processed"
   
   class GDBName(StrEnum):
       BUILDING = "building"           # New GDB name
   
   # constants/columns.py
   class ColumnName(StrEnum):
       BUILDING_ID = "building_id"     # New field name
       BUILDING_HEIGHT = "building_height"
       ROOF_MATERIAL = "roof_material"
   
   # constants/general.py
   class FieldType(StrEnum):
       STRING = "string"
       DOUBLE = "double"
       GEOMETRY = "geometry"
       # (FieldType already has common types)
   ```

---

## Step 1: Define Fields

**File**: `data_orchestrator_2/schemas/fields.py`  
**Class**: `FieldCatalog`

All fields used in your datasets must be registered in the `FieldCatalog`.

### Add Field Definitions

```python
# In FieldCatalog class, add your new fields:

class FieldCatalog:
    """Reusable field definitions for dataset catalogs."""
    
    # Existing fields...
    OBJECTID = FieldDefinition(
        name=ColumnName.OBJECTID,
        datatype=FieldType.OID,
        system_field=True,
    )
    
    # NEW FIELDS ↓
    BUILDING_ID = FieldDefinition(
        name=ColumnName.BUILDING_ID,
        datatype=FieldType.LONG,
    )
    
    BUILDING_HEIGHT = FieldDefinition(
        name=ColumnName.BUILDING_HEIGHT,
        datatype=FieldType.DOUBLE,
    )
    
    ROOF_MATERIAL = FieldDefinition(
        name=ColumnName.ROOF_MATERIAL,
        datatype=FieldType.STRING,
    )
    
    SHAPE = FieldDefinition(
        name=ColumnName.SHAPE,
        datatype=FieldType.GEOMETRY,
        system_field=True,
    )
```

### Field Definition Structure

```mermaid
graph TB
    subgraph FieldDefinitionClass["FieldDefinition (Frozen Dataclass)"]
        name["<b>name</b><br/>ColumnName enum value<br/>Must be unique in catalog"]
        datatype["<b>datatype</b><br/>FieldType enum<br/>STRING, LONG, DOUBLE,<br/>GEOMETRY, etc."]
        system_field["<b>system_field</b> = False<br/>Mark if ArcPy managed<br/>(OBJECTID, SHAPE, etc.)"]
    end
    
    result["✓ Reusable field<br/>ready for datasets"]
    
    name --> result
    datatype --> result
    system_field --> result
    
    classDef field fill:#2196F3,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    classDef result fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff,font-weight:bold
    
    class FieldDefinitionClass field
    class result result
```

### Key Points

- **Every field must exist in `FieldCatalog`** before it can be used in a dataset
- Fields are **frozen dataclasses** (immutable)
- Mark ArcPy-managed fields with `system_field=True` (e.g., OBJECTID, SHAPE)
- Field names must correspond to actual geodatabase column names

---

## Step 2: Create Dataset Definition

**File**: `data_orchestrator_2/schemas/datasets.py`  
**Class**: `DatasetCatalog`

A dataset combines fields with their usage patterns and source metadata.

### Add Dataset Definition

```python
# In DatasetCatalog class, add your new dataset:

class DatasetCatalog:
    """Named dataset definitions available to pipelines."""
    
    # Existing datasets...
    
    # NEW DATASET ↓
    BUILDINGS_RAW = DatasetDefinition(
        name=FeatureClassName.BUILDING,
        source_scale=Scale.RAW_DATA,
        gdb_name=GDBName.BUILDING,
        geometry_type=GeometryType.POLYGON,
        fields=(
            used_for(FieldCatalog.OBJECTID, FieldUsage.INPUT),
            used_for(FieldCatalog.SHAPE, FieldUsage.INPUT),
            used_for(
                FieldCatalog.BUILDING_ID,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
                required=True,
            ),
            used_for(
                FieldCatalog.BUILDING_HEIGHT,
                FieldUsage.INPUT | FieldUsage.PROCESSING,
                required=False,
            ),
            used_for(
                FieldCatalog.ROOF_MATERIAL,
                FieldUsage.INPUT | FieldUsage.PROCESSING,
                required=False,
            ),
        ),
    )
    
    BUILDINGS_PROCESSED = DatasetDefinition(
        name=FeatureClassName.BUILDINGS_PROCESSED,
        source_scale=Scale.N100,
        gdb_name=GDBName.BUILDING,
        geometry_type=GeometryType.POLYGON,
        fields=(
            used_for(FieldCatalog.OBJECTID, FieldUsage.OUTPUT),
            used_for(FieldCatalog.SHAPE, FieldUsage.OUTPUT),
            used_for(FieldCatalog.BUILDING_ID, FieldUsage.OUTPUT, required=True),
            used_for(FieldCatalog.BUILDING_HEIGHT, FieldUsage.OUTPUT, required=False),
        ),
    )
```

### Dataset Definition Structure

```mermaid
graph TB
    subgraph DatasetDefinitionClass["DatasetDefinition (Frozen Dataclass)"]
        name["<b>name</b><br/>FeatureClassName<br/>e.g., BUILDING"]
        source_scale["<b>source_scale</b><br/>Scale enum<br/>RAW_DATA, N100, N250, etc."]
        gdb_name["<b>gdb_name</b><br/>GDBName<br/>e.g., GDBName.BUILDING"]
        geometry_type["<b>geometry_type</b><br/>GeometryType<br/>POLYGON, POLYLINE, POINT"]
        fields["<b>fields</b><br/>tuple of DatasetField<br/>with usage & required"]
    end
    
    datasetfield["DatasetField<br/>@dataclass frozen<br/><br/>field: FieldDefinition<br/>usage: FieldUsage<br/>required: bool"]
    
    usage["FieldUsage (Flag enum)<br/><br/>INPUT<br/>PROCESSING<br/>OUTPUT<br/><br/>Can combine with |"]
    
    fields --> datasetfield
    datasetfield --> usage
    
    classDef dsdef fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff,font-weight:bold
    classDef dsfield fill:#E91E63,stroke:#880E4F,stroke-width:2px,color:#fff,font-weight:bold
    classDef enum fill:#FF6B6B,stroke:#D32F2F,stroke-width:2px,color:#fff,font-weight:bold
    
    class DatasetDefinitionClass dsdef
    class datasetfield dsfield
    class usage enum
```

### Field Usage Patterns

```mermaid
graph TB
    subgraph InputPhase["INPUT Stage"]
        Read["Fields needed to<br/>READ raw data<br/>from geodatabase"]
    end
    
    subgraph ProcessingPhase["PROCESSING Stage"]
        Clean["Fields used during<br/>GENERALIZATION<br/>and transformation"]
    end
    
    subgraph OutputPhase["OUTPUT Stage"]
        Write["Fields written to<br/>target geodatabase<br/>for publication"]
    end
    
    Example["<b>Example: BUILDING_ID</b><br/>FieldUsage.INPUT |<br/>FieldUsage.PROCESSING |<br/>FieldUsage.OUTPUT"]
    
    InputPhase --> ProcessingPhase
    ProcessingPhase --> OutputPhase
    Example -.-> ProcessingPhase
    
    classDef input fill:#2196F3,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    classDef processing fill:#FF9800,stroke:#E65100,stroke-width:2px,color:#fff,font-weight:bold
    classDef output fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff,font-weight:bold
    classDef example fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff,font-weight:bold
    
    class InputPhase input
    class ProcessingPhase processing
    class OutputPhase output
    class Example example
```

### Key Points

- Each dataset maps to **one feature class** at **one source scale**
- The `used_for()` helper function combines `FieldDefinition`, `FieldUsage`, and `required` status
- Fields marked `required=True` must always be present
- System fields (OBJECTID, SHAPE) are typically INPUT-only
- Datasets are **frozen** and changes require careful review

---

## Step 3: Register Pipeline

**File**: `data_orchestrator_2/schemas/pipelines.py`  
**Dictionary**: `PIPELINES`

Pipelines connect datasets to a target scale and geodatabase.

### Add Pipeline Entry

```python
# In the PIPELINES dictionary, add your new pipeline:

PIPELINES: dict[tuple[GDBName, Scale], PipelineDefinition] = {
    # Existing pipelines...
    (GDBName.ROAD, Scale.N100): PipelineDefinition(
        gdb_name=GDBName.ROAD,
        scale=Scale.N100,
        datasets={FeatureClassName.ELVEG_AND_STI: DatasetCatalog.ELVEG_AND_STI},
    ),
    
    # NEW PIPELINE ↓
    (GDBName.BUILDING, Scale.N100): PipelineDefinition(
        gdb_name=GDBName.BUILDING,
        scale=Scale.N100,
        datasets={
            FeatureClassName.BUILDING: DatasetCatalog.BUILDINGS_RAW,
            FeatureClassName.BUILDINGS_PROCESSED: DatasetCatalog.BUILDINGS_PROCESSED,
        },
    ),
}
```

### Pipeline Registration Pattern

```mermaid
graph TB
    subgraph Input["Pipeline Key"]
        gdbname["<b>GDBName</b><br/>e.g., GDBName.BUILDING"]
        scale["<b>Scale</b><br/>e.g., Scale.N100"]
        key["Unique key:<br/>GDBName, Scale tuple"]
    end
    
    subgraph Definition["PipelineDefinition"]
        pgdb["<b>gdb_name</b><br/>Geodatabase identifier"]
        pscale["<b>scale</b><br/>Target generalization scale"]
        datasets["<b>datasets</b><br/>dict mapping<br/>FeatureClassName →<br/>DatasetDefinition"]
    end
    
    subgraph Result["Pipeline Ready"]
        lookup["Accessible via<br/>get_pipeline<br/>GDBName, Scale"]
        runtime["Runtime can now:<br/>- Validate datasets<br/>- Access field schemas<br/>- Manage field usage"]
    end
    
    gdbname --> key
    scale --> key
    key -->|creates| pgdb
    key -->|creates| pscale
    pgdb --> datasets
    pscale --> datasets
    datasets --> lookup
    lookup --> runtime
    
    classDef input fill:#2196F3,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    classDef defn fill:#9C27B0,stroke:#6A1B9A,stroke-width:2px,color:#fff,font-weight:bold
    classDef result fill:#4CAF50,stroke:#2E7D32,stroke-width:2px,color:#fff,font-weight:bold
    
    class Input input
    class Definition defn
    class Result result
```

### Key Points

- Pipeline key is **(GDBName, Scale)** — this uniquely identifies a generalization pipeline
- One pipeline can contain **multiple datasets** (e.g., raw input + processed output)
- The `get_pipeline()` function looks up pipelines by this key
- Adding a pipeline makes the dataset schemas **discoverable at runtime**

---

## Complete Example

Adding a **Building feature class** with raw and processed datasets:

### 1. Update Constants

```python
# constants/fileStructures.py
class FeatureClassName(StrEnum):
    BUILDING = "building"
    BUILDINGS_PROCESSED = "buildings_processed"

class GDBName(StrEnum):
    BUILDING = "building"

# constants/columns.py
class ColumnName(StrEnum):
    BUILDING_ID = "building_id"
    BUILDING_HEIGHT = "building_height"
    ROOF_MATERIAL = "roof_material"
```

### 2. Add Fields to FieldCatalog

```python
# schemas/fields.py
class FieldCatalog:
    BUILDING_ID = FieldDefinition(
        name=ColumnName.BUILDING_ID,
        datatype=FieldType.LONG,
    )
    
    BUILDING_HEIGHT = FieldDefinition(
        name=ColumnName.BUILDING_HEIGHT,
        datatype=FieldType.DOUBLE,
    )
    
    ROOF_MATERIAL = FieldDefinition(
        name=ColumnName.ROOF_MATERIAL,
        datatype=FieldType.STRING,
    )
```

### 3. Create Dataset Definitions

```python
# schemas/datasets.py
class DatasetCatalog:
    BUILDINGS_RAW = DatasetDefinition(
        name=FeatureClassName.BUILDING,
        source_scale=Scale.RAW_DATA,
        gdb_name=GDBName.BUILDING,
        geometry_type=GeometryType.POLYGON,
        fields=(
            used_for(FieldCatalog.OBJECTID, FieldUsage.INPUT),
            used_for(FieldCatalog.SHAPE, FieldUsage.INPUT),
            used_for(
                FieldCatalog.BUILDING_ID,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
                required=True,
            ),
            used_for(
                FieldCatalog.BUILDING_HEIGHT,
                FieldUsage.INPUT | FieldUsage.PROCESSING | FieldUsage.OUTPUT,
            ),
            used_for(
                FieldCatalog.ROOF_MATERIAL,
                FieldUsage.INPUT | FieldUsage.PROCESSING,
            ),
        ),
    )
    
    BUILDINGS_PROCESSED = DatasetDefinition(
        name=FeatureClassName.BUILDINGS_PROCESSED,
        source_scale=Scale.N100,
        gdb_name=GDBName.BUILDING,
        geometry_type=GeometryType.POLYGON,
        fields=(
            used_for(FieldCatalog.OBJECTID, FieldUsage.OUTPUT),
            used_for(FieldCatalog.SHAPE, FieldUsage.OUTPUT),
            used_for(
                FieldCatalog.BUILDING_ID,
                FieldUsage.OUTPUT,
                required=True,
            ),
            used_for(
                FieldCatalog.BUILDING_HEIGHT,
                FieldUsage.OUTPUT,
            ),
        ),
    )
```

### 4. Register Pipeline

```python
# schemas/pipelines.py
PIPELINES: dict[tuple[GDBName, Scale], PipelineDefinition] = {
    (GDBName.ROAD, Scale.N100): PipelineDefinition(...),
    
    # NEW
    (GDBName.BUILDING, Scale.N100): PipelineDefinition(
        gdb_name=GDBName.BUILDING,
        scale=Scale.N100,
        datasets={
            FeatureClassName.BUILDING: DatasetCatalog.BUILDINGS_RAW,
            FeatureClassName.BUILDINGS_PROCESSED: DatasetCatalog.BUILDINGS_PROCESSED,
        },
    ),
}
```

### 5. Use in Runtime Code

```python
# Any module importing pipelines can now use:
from data_orchestrator_2.schemas.pipelines import get_pipeline
from data_orchestrator_2.constants.fileStructures import GDBName
from data_orchestrator_2.constants.general import Scale

# Get the pipeline
pipeline = get_pipeline(GDBName.BUILDING, Scale.N100)

# Access datasets
buildings_raw = pipeline.getDataset(FeatureClassName.BUILDING)
buildings_processed = pipeline.getDataset(FeatureClassName.BUILDINGS_PROCESSED)

# Query field schemas
input_fields = buildings_raw.getFieldsFor(FieldUsage.INPUT)
output_fields = buildings_processed.getFieldsFor(FieldUsage.OUTPUT)
```

---

## Workflow Visualization

The complete flow from definition to runtime usage:

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Fields as fields.py<br/>FieldCatalog
    participant Datasets as datasets.py<br/>DatasetCatalog
    participant Pipelines as pipelines.py<br/>PIPELINES dict
    participant Runtime as Runtime Code<br/>get_pipeline()
    
    Dev->>Fields: 1. Add BUILDING_ID,<br/>BUILDING_HEIGHT, etc.
    Fields-->>Dev: ✓ Fields registered
    
    Dev->>Datasets: 2. Create BUILDINGS_RAW<br/>& BUILDINGS_PROCESSED<br/>datasets
    Datasets->>Fields: Reference FieldCatalog
    Fields-->>Datasets: Provide FieldDefinitions
    Datasets-->>Dev: ✓ Datasets defined
    
    Dev->>Pipelines: 3. Add (GDBName.BUILDING,<br/>Scale.N100) → Pipeline
    Pipelines->>Datasets: Reference DatasetCatalog
    Datasets-->>Pipelines: Provide DatasetDefinitions
    Pipelines-->>Dev: ✓ Pipeline registered
    
    Runtime->>Pipelines: get_pipeline(GDBName.BUILDING,<br/>Scale.N100)
    Pipelines-->>Runtime: PipelineDefinition
    
    Runtime->>Runtime: Access fields,<br/>validate schemas,<br/>manage data
```
