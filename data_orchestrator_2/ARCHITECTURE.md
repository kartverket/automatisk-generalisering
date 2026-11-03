# Data Orchestrator 2 - Architecture & Module Dependencies

A comprehensive guide to the `data_orchestrator_2` module structure, class hierarchies, and component dependencies.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Layers](#architecture-layers)
3. [Module Dependencies](#module-dependencies)
4. [Class Hierarchy & Relationships](#class-hierarchy--relationships)
5. [Data Flow](#data-flow)
6. [Key Components](#key-components)
7. [Usage Examples](#usage-examples)

---

## Overview

`data_orchestrator_2` separates **catalog definitions** (pipeline and dataset schemas) from **runtime operations** (dataset paths and ArcPy interactions). The module is organized into four main layers:

- **Constants Layer**: Type enums and static definitions
- **Schemas Layer**: Frozen catalog definitions and lookups
- **Organizers Layer**: Runtime operations (path resolution, validation, field management)
- **Core Entry Point**: The `test.py` manual example

A pipeline is uniquely selected by `(GDBName, Scale)`. Each dataset definition records its source scale, geometry type, and field catalog.

---

## Architecture Layers

```mermaid
graph TB
    subgraph Constants["📦 Constants Layer"]
        columns["columns.py<br/>ColumnName enum"]
        general["general.py<br/>Scale, FieldType, GeometryType"]
        fileStructures["fileStructures.py<br/>FeatureClassName, GDBName"]
        domains["domains.py<br/>DomainObject, DomainScale<br/>Domain value lookups"]
    end

    subgraph Schemas["📋 Schemas Layer"]
        fields["fields.py<br/>FieldDefinition, FieldCatalog"]
        datasets["datasets.py<br/>DatasetField, FieldUsage<br/>DatasetDefinition, DatasetCatalog"]
        pipelines["pipelines.py<br/>PipelineDefinition<br/>PIPELINES registry<br/>get_pipeline()"]
    end

    subgraph Organizers["🔧 Organizers Layer"]
        pathFactory["path_factory.py<br/>get_gdb_path()<br/>get_feature_class_path()"]
        validator["validator.py<br/>ValidationResult<br/>validate_dataset()"]
        fieldManager["fieldManager.py<br/>remove_none_geometry()<br/>clean_columns()<br/>prepare_final_dataset()"]
    end

    subgraph Test["🧪 Testing"]
        test["test.py<br/>Manual ArcPy example"]
    end

    Constants -->|provides enums| Schemas
    Schemas -->|provides definitions| Organizers
    Organizers -->|uses ArcPy| Test
```

---

## Module Dependencies

### Complete Dependency Graph

```mermaid
graph LR
    subgraph Constants["📦 CONSTANTS"]
        columns["<b>columns</b>"]
        general["<b>general</b>"]
        fileStructures["<b>fileStructures</b>"]
        domains["<b>domains</b>"]
    end

    subgraph Schemas["📋 SCHEMAS"]
        fields["<b>fields</b>"]
        datasets["<b>datasets</b>"]
        pipelines["<b>pipelines</b>"]
    end

    subgraph Organizers["🔧 ORGANIZERS"]
        pathFactory["<b>path_factory</b>"]
        validator["<b>validator</b>"]
        fieldManager["<b>fieldManager</b>"]
    end

    subgraph External["🔌 EXTERNAL"]
        paths["<b>paths</b>"]
        arcpy["<b>ArcPy</b>"]
    end

    test["<b>test.py</b>"]

    columns -->|ColumnName| fields
    columns -->|ColumnName| validator
    
    general -->|Scale<br/>FieldType| fields
    general -->|Scale| datasets
    general -->|Scale| pathFactory
    
    fileStructures -->|FeatureClassName<br/>GDBName| datasets
    fileStructures -->|GDBName| pipelines
    fileStructures -->|GDBName| pathFactory
    
    domains -->|DomainObject| datasets
    domains -->|lookups| validator
    
    fields -->|FieldDefinition| datasets
    
    datasets -->|DatasetDefinition| pipelines
    datasets -->|FieldUsage| validator
    datasets -->|FieldUsage| fieldManager
    
    pipelines -->|PipelineDefinition| test
    
    paths -->|GIS_FILES_ROOT| pathFactory
    
    pathFactory -->|paths| validator
    
    validator -->|ValidationResult| test
    
    arcpy -->|Feature ops| validator
    arcpy -->|Field ops| fieldManager
    
    test -->|uses all| fieldManager
    
    classDef constants fill:#2196F3,stroke:#0D47A1,stroke-width:3px,color:#fff,font-weight:bold
    classDef schemas fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff,font-weight:bold
    classDef organizers fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff,font-weight:bold
    classDef external fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff,font-weight:bold
    classDef test fill:#E91E63,stroke:#880E4F,stroke-width:3px,color:#fff,font-weight:bold
    
    class columns,general,fileStructures,domains constants
    class fields,datasets,pipelines schemas
    class pathFactory,validator,fieldManager organizers
    class paths,arcpy external
    class test test
```

---

## Class Hierarchy & Relationships

### Constants Layer

```mermaid
graph TB
    subgraph Enums["Enumerations (Constants)"]
        ColumnName["<b>ColumnName</b> (StrEnum)<br/>OBJECTID, SHAPE, ADRESSENAVN,<br/>ADSKILTELOP, AREALBRUK_*, etc."]
        Scale["<b>Scale</b> (StrEnum)<br/>RAW_DATA, N100, N250, N1000"]
        FieldType["<b>FieldType</b> (StrEnum)<br/>STRING, LONG, DOUBLE, GEOMETRY"]
        GeometryType["<b>GeometryType</b> (StrEnum)<br/>POLYLINE, POLYGON, POINT"]
        FeatureClassName["<b>FeatureClassName</b> (StrEnum)<br/>ELVEG_AND_STI, ..."]
        GDBName["<b>GDBName</b> (StrEnum)<br/>ROAD, ..."]
        DomainObject["<b>DomainObject</b> (StrEnum)<br/>HIERARKI, MEDIUM_VALUE, etc."]
        DomainScale["<b>DomainScale</b> (StrEnum)<br/>N100, N250, N1000"]
    end
```

### Schemas Layer

```mermaid
graph TB
    subgraph SchemaClasses["Schema Classes"]
        FieldDef["<b>FieldDefinition</b><br/>@dataclass frozen<br/><br/>name: ColumnName<br/>datatype: FieldType<br/>system_field: bool"]
        FieldCatalog["<b>FieldCatalog</b><br/><br/>ADRESSENAVN<br/>AREAL_M2<br/>...<br/><br/>All 22+ field<br/>definitions"]
        FieldUsage["<b>DatasetField</b><br/>@dataclass frozen<br/><br/>field: FieldDefinition<br/>usage: FieldUsage<br/>required: bool<br/><br/>isUsedFor method"]
        FieldUsageEnum["<b>FieldUsage</b><br/>Flag enum<br/><br/>INPUT<br/>PROCESSING<br/>OUTPUT"]
        DatasetDef["<b>DatasetDefinition</b><br/>@dataclass frozen<br/><br/>name: FeatureClassName<br/>source_scale: Scale<br/>gdb_name: GDBName<br/>geometry_type<br/>fields: tuple"]
        DatasetCatalog["<b>DatasetCatalog</b><br/><br/>ELVEG_AND_STI<br/>...<br/><br/>static registry"]
        PipelineDef["<b>PipelineDefinition</b><br/>@dataclass frozen<br/><br/>gdb_name: GDBName<br/>scale: Scale<br/>datasets: dict"]
    end

    FieldDef -->|<b>used by</b>| FieldCatalog
    FieldDef -->|<b>contained in</b>| FieldUsage
    FieldUsageEnum -->|<b>used by</b>| FieldUsage
    FieldUsage -->|<b>tuple of</b>| DatasetDef
    DatasetDef -->|<b>registry of</b>| DatasetCatalog
    DatasetCatalog -->|<b>used by</b>| PipelineDef
    
    classDef schemaBox fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff,font-weight:bold
    
    class FieldDef,FieldUsage,DatasetDef,PipelineDef,FieldUsageEnum,FieldCatalog,DatasetCatalog schemaBox
```

### Organizers Layer

```mermaid
graph TB
    subgraph OrganizerClasses["Organizer Classes"]
        PathFactory["<b>path_factory.py</b><br/><br/>get_gdb_path<br/>get_feature_class_path<br/>get_feature_class_full_path"]
        
        ValidationResult["<b>ValidationResult</b><br/>@dataclass<br/><br/>dataset_name<br/>path<br/>warning_message<br/>error_message<br/>exists, has_rows<br/>missing_fields<br/>extra_fields<br/>wrong_datatypes<br/><br/>success, warning<br/>properties"]
        
        Validator["<b>validator.py</b><br/><br/>validate_dataset<br/>validate_pipeline"]
        
        FieldManager["<b>fieldManager.py</b><br/><br/>remove_none_geometry<br/>clean_columns<br/>prepare_final_dataset"]
    end

    PathFactory -.->|<b>used by</b>| Validator
    ValidationResult -->|<b>returned by</b>| Validator
    FieldManager -.->|<b>works with</b>| Validator
    
    classDef organizer fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff,font-weight:bold
    classDef result fill:#FF6B6B,stroke:#D32F2F,stroke-width:3px,color:#fff,font-weight:bold
    
    class PathFactory,Validator,FieldManager organizer
    class ValidationResult result
```

---

## Data Flow

### Pipeline Initialization & Validation

```mermaid
sequenceDiagram
    participant User as User Code
    participant Pipeline as Pipeline<br/>lookup
    participant DatasetDef as Dataset<br/>Definition
    participant PathFactory as Path<br/>Factory
    participant Validator as Validator
    participant FieldMgr1 as Field<br/>Manager<br/>Processing
    participant FieldMgr2 as Field<br/>Manager<br/>Output
    participant ArcPy as ArcPy

    User->>Pipeline: get_pipeline(GDBName.ROAD,<br/>Scale.N100)
    Pipeline-->>User: PipelineDefinition
    
    User->>DatasetDef: pipeline.getDataset<br/>ELVEG_AND_STI
    DatasetDef-->>User: DatasetDefinition
    
    User->>PathFactory: Construct runtime paths
    PathFactory->>ArcPy: Load GIS_FILES_ROOT
    ArcPy-->>PathFactory: File system path
    PathFactory-->>User: Feature class paths
    
    User->>Validator: validate_dataset<br/>FieldUsage.INPUT
    Validator->>ArcPy: Check existence<br/>row count, schema
    ArcPy-->>Validator: Feature class metadata
    Validator-->>User: ValidationResult
    
    rect rgb(76, 175, 80)
    Note over FieldMgr1: Processing Phase
    User->>FieldMgr1: clean_columns<br/>FieldUsage.PROCESSING
    FieldMgr1->>ArcPy: Delete unused fields
    ArcPy-->>FieldMgr1: Done
    FieldMgr1-->>User: Cleaned
    end
    
    rect rgb(156, 39, 176)
    Note over FieldMgr2: Output Phase
    User->>FieldMgr2: prepare_final_dataset
    FieldMgr2->>ArcPy: Remove null geometry<br/>Clean final columns
    ArcPy-->>FieldMgr2: Done
    FieldMgr2-->>User: Ready for output
    end
```

### Schema Catalog Lookup

```mermaid
graph LR
    Start["GDBName, Scale<br/>tuple"] 
    GetPipeline["get_pipeline<br/>lookup PIPELINES"]
    PipelineDef["PipelineDefinition<br/>contains datasets"]
    GetDataset["getDataset<br/>FeatureClassName lookup"]
    DatasetDef["DatasetDefinition<br/>contains fields"]
    GetField["getField<br/>ColumnName lookup"]
    FieldUsage["DatasetField<br/>name, type, usage"]
    
    Start -->|input| GetPipeline
    GetPipeline -->|returns| PipelineDef
    PipelineDef -->|lookup| GetDataset
    GetDataset -->|returns| DatasetDef
    DatasetDef -->|lookup| GetField
    GetField -->|returns| FieldUsage
    
    classDef input fill:#2196F3,stroke:#0D47A1,stroke-width:3px,color:#fff,font-weight:bold
    classDef operation fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff,font-weight:bold
    classDef schema fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff,font-weight:bold
    
    class Start input
    class GetPipeline,GetDataset,GetField operation
    class PipelineDef,DatasetDef,FieldUsage schema
```

---

## Key Components

### 1. Constants (`constants/`)

| File | Purpose | Key Exports |
|------|---------|-------------|
| `columns.py` | Column name enum | `ColumnName` (StrEnum) |
| `general.py` | Core enumerations | `Scale`, `FieldType`, `GeometryType` |
| `fileStructures.py` | Feature class & GDB names | `FeatureClassName`, `GDBName` |
| `domains.py` | Domain value lookups | `DomainObject`, `DomainScale`, `get_allowed_values()` |

**Note**: Enums enable type-safe lookups and prevent string-based errors.

### 2. Schemas (`schemas/`)

| File | Class/Function | Responsibility |
|------|---|---|
| `fields.py` | `FieldDefinition` | Immutable field metadata (name, type, system flag) |
| `fields.py` | `FieldCatalog` | Registry of all reusable field definitions |
| `datasets.py` | `FieldUsage` | Flag enum for INPUT/PROCESSING/OUTPUT stages |
| `datasets.py` | `DatasetField` | Field with usage and requiredness flags |
| `datasets.py` | `DatasetDefinition` | Immutable dataset schema with field lookup |
| `datasets.py` | `DatasetCatalog` | Registry of all known datasets |
| `pipelines.py` | `PipelineDefinition` | Target scale and its datasets |
| `pipelines.py` | `PIPELINES` dict | `(GDBName, Scale) -> PipelineDefinition` registry |
| `pipelines.py` | `get_pipeline()` | Lookup a pipeline by key; raises `KeyError` if missing |

**Design Principle**: All schema classes are frozen `@dataclass` instances to ensure immutability.

### 3. Organizers (`organizers/`)

| File | Function | Responsibility |
|------|----------|---|
| `path_factory.py` | `get_gdb_path()` | Build GDB path from `GIS_FILES_ROOT`, scale, and GDB name |
| `path_factory.py` | `get_feature_class_path()` | Append feature class name to GDB path |
| `path_factory.py` | `get_feature_class_full_path()` | One-shot function combining both above |
| `validator.py` | `ValidationResult` | Report existence, row count, schema, and type checks |
| `validator.py` | `validate_dataset()` | Check a single dataset against its definition |
| `validator.py` | `validate_pipeline()` | Validate all datasets in a pipeline; aggregate results |
| `fieldManager.py` | `remove_none_geometry()` | Delete rows with null geometry; timestamp and report |
| `fieldManager.py` | `clean_columns()` | Delete unregistered or unused fields; preserve system fields |
| `fieldManager.py` | `prepare_final_dataset()` | Combined cleanup for final output (remove geometry + clean cols) |

**Dependencies**:
- `path_factory.py` imports only constants and `paths.py` (external).
- `validator.py` requires `custom_tools.general_tools.validation` helpers and ArcPy.
- `fieldManager.py` requires ArcPy and accesses dataset paths and definitions.

### 4. Test Entry Point (`test.py`)

Manual ArcPy example that:
1. Imports pipeline and dataset definitions
2. Validates input stage
3. Copies dataset to output path
4. Redirects runtime dataset to the copy
5. Validates processing stage
6. Prepares final dataset

**Not an automated pytest test**; run as a script for manual validation.

---

## Usage Examples

### Example 1: Access Pipeline Definition

```python
from data_orchestrator_2.constants.fileStructures import GDBName
from data_orchestrator_2.constants.general import Scale
from data_orchestrator_2.constants.fileStructures import FeatureClassName
from data_orchestrator_2.schemas.pipelines import get_pipeline

# Look up pipeline
pipeline = get_pipeline(GDBName.ROAD, Scale.N100)
print(f"Pipeline: {pipeline.scale} / {pipeline.gdb_name}")

# Get dataset from pipeline
dataset_def = pipeline.getDataset(FeatureClassName.ELVEG_AND_STI)
print(f"Dataset: {dataset_def.name}, {len(dataset_def.fields)} fields")

# List all fields
for field in dataset_def.fields:
    print(f"  - {field.name}: {field.datatype} (required={field.required})")
```

### Example 2: Validate a Dataset

```python
from data_orchestrator_2.organizers.validator import validate_dataset
from data_orchestrator_2.schemas.datasets import FieldUsage
from data_orchestrator_2.organizers.path_factory import get_feature_class_full_path

# Build path
path = get_feature_class_full_path(
    scale=Scale.RAW_DATA,
    gdb_name=GDBName.ROAD,
    feature_class_name=FeatureClassName.ELVEG_AND_STI
)

# Validate
result = validate_dataset(
    dataset=dataset_def,
    path=path,
    usage=FieldUsage.INPUT
)

if result.success:
    print(f"✓ {result.dataset_name} is valid for input")
else:
    print(f"✗ {result.dataset_name}: {result.error_message}")
    print(f"  Missing fields: {result.missing_fields}")
    print(f"  Wrong types: {result.wrong_datatypes}")
```

### Example 3: Field Management

```python
from data_orchestrator_2.organizers.fieldManager import clean_columns, prepare_final_dataset

class MockDataset:
    """Mock dataset with path and definition."""
    def __init__(self, path, definition):
        self.path = path
        self.definition = definition

# Prepare final output
dataset_obj = MockDataset(path, dataset_def)
prepare_final_dataset(dataset_obj)
# Removes null-geometry rows and deletes non-OUTPUT fields
```

---

## Initialization Flow

When the `data_orchestrator_2` module is imported:

1. **Constants** are defined as frozen enums.
2. **Schemas** are loaded: field definitions, dataset catalog, pipeline registry.
3. **Organizers** functions are registered (no side effects).
4. **Test.py** does not run automatically; manual invocation required.

**No ArcPy imports at module level**: ArcPy is lazily imported by organizers and only when validation/cleanup is needed.

---

## Summary

| Layer | Role | Depends On | Side Effects |
|-------|------|-----------|---|
| **Constants** | Type-safe enumerations | Nothing | None |
| **Schemas** | Immutable catalog definitions | Constants | None |
| **Organizers** | Runtime operations | Schemas, Constants, ArcPy | File I/O, ArcPy mutations |
| **Test** | Manual example | All layers, ArcPy | Copies datasets, modifies features |

**Key Insight**: Catalog definitions (Constants + Schemas) have zero external dependencies and can be inspected without ArcPy. Runtime operations (Organizers) require ArcPy and configured paths.
