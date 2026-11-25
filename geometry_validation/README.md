# Geometry Validation - Architecture & Module Dependencies

A comprehensive guide to the `geometry_validation` module structure, class hierarchies, statistics collection, and validation workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Layers](#architecture-layers)
3. [Module Dependencies](#module-dependencies)
4. [Class Hierarchy & Relationships](#class-hierarchy--relationships)
5. [Data Flow](#data-flow)
6. [Key Components](#key-components)
7. [Validation Rules & Status](#validation-rules--status)
8. [Usage Examples](#usage-examples)

---

## Overview

`geometry_validation` provides a framework for collecting, validating, and tracking statistics from geometric feature classes across different geometry types and feature categories. The module separates concerns into four key layers:

- **Validation Status Layer**: Rule-based status evaluation with severity levels (SUCCESS, WARNING, ERROR)
- **Statistics Collection Layer**: Geometry-type-specific statistics collectors (Vector, Line, Polygon, Point)
- **Feature Statistics Layer**: Feature-specific statistics providers (Road, River, Landuse)
- **Orchestration Layer**: Validation orchestrator that combines statistics and status checks

The framework supports incremental validation runs, automatic diff calculation between runs, and structured result serialization to JSON.

---

## Architecture Layers

```mermaid
graph TB
    subgraph Validation["📋 Validation Status Layer"]
        severity["Severity enum<br/>SUCCESS, WARNING, ERROR"]
        rule["Rule dataclass<br/>key, operator, value, severity"]
        status["ValidationStatus<br/>Permanent & temporary rules<br/>status_update()"]
    end

    subgraph Statistics["📊 Statistics Collection Layer"]
        vector["VectorStatistics<br/>Base class<br/>exists, has_data<br/>object_count, vertex_count"]
        line["LineStatistics<br/>Line-specific metrics<br/>total_length, min/max/avg<br/>dangle counts"]
        polygon["PolygonStatistics<br/>Polygon-specific metrics<br/>total_area, min/max/avg"]
        point["PointStatistics<br/>Point-specific metrics"]
    end

    subgraph Features["🗺️ Feature Statistics Layer"]
        road["RoadStatistics<br/>Extends LineStatistics<br/>road_categories"]
        river["RiverStatistics<br/>Extends LineStatistics"]
        landuse["LanduseStatistics<br/>Extends PolygonStatistics<br/>landuse_categories"]
    end

    subgraph Orchestration["🔧 Orchestration Layer"]
        orchestrator["ValidatorOrchestrator<br/>Combines statistics & validation<br/>Manages validation runs<br/>calculate_diff()<br/>save_validation_results()"]
    end

    subgraph External["🔌 External"]
        arcpy["ArcPy<br/>Geometry operations"]
    end

    rule -->|uses| severity
    status -->|evaluates| rule
    
    vector -->|base class| line
    vector -->|base class| polygon
    vector -->|base class| point
    
    line -->|extends| road
    line -->|extends| river
    polygon -->|extends| landuse
    
    road -->|statistics provider| orchestrator
    river -->|statistics provider| orchestrator
    landuse -->|statistics provider| orchestrator
    
    status -->|validation engine| orchestrator
    vector -->|geometry access| arcpy
    line -->|geometry access| arcpy
    polygon -->|geometry access| arcpy
```

---

## Module Dependencies

### Complete Dependency Graph

```mermaid
graph LR
    subgraph Core["📋 CORE"]
        severity["<b>Severity</b><br/>(StrEnum)"]
        rule["<b>Rule</b><br/>(dataclass)"]
    end

    subgraph Validation["🔍 VALIDATION"]
        status["<b>ValidationStatus</b>"]
    end

    subgraph Stats["📊 STATISTICS"]
        vector["<b>VectorStatistics</b>"]
        line["<b>LineStatistics</b>"]
        polygon["<b>PolygonStatistics</b>"]
        point["<b>PointStatistics</b>"]
    end

    subgraph Features["🗺️ FEATURES"]
        road["<b>RoadStatistics</b>"]
        river["<b>RiverStatistics</b>"]
        landuse["<b>LanduseStatistics</b>"]
    end

    subgraph Orchestration["🎯 ORCHESTRATION"]
        orchestrator["<b>ValidatorOrchestrator</b>"]
    end

    subgraph External["🔌 EXTERNAL"]
        arcpy["<b>ArcPy</b>"]
        generalization["<b>generalization</b><br/>(arealdekke params)"]
    end

    severity -->|used by| rule
    rule -->|added to| status
    
    vector -->|base| line
    vector -->|base| polygon
    vector -->|base| point
    vector -->|uses| arcpy
    
    line -->|extends| road
    line -->|extends| river
    polygon -->|extends| landuse
    
    status -->|evaluates| orchestrator
    road -->|provides stats| orchestrator
    river -->|provides stats| orchestrator
    landuse -->|provides stats| orchestrator
    landuse -->|depends on| generalization
    
    classDef core fill:#2196F3,stroke:#0D47A1,stroke-width:3px,color:#fff,font-weight:bold
    classDef validation fill:#FF6B6B,stroke:#D32F2F,stroke-width:3px,color:#fff,font-weight:bold
    classDef stats fill:#4CAF50,stroke:#2E7D32,stroke-width:3px,color:#fff,font-weight:bold
    classDef features fill:#9C27B0,stroke:#6A1B9A,stroke-width:3px,color:#fff,font-weight:bold
    classDef orch fill:#FF9800,stroke:#E65100,stroke-width:3px,color:#fff,font-weight:bold
    classDef ext fill:#607D8B,stroke:#37474F,stroke-width:3px,color:#fff,font-weight:bold
    
    class severity,rule core
    class status validation
    class vector,line,polygon,point stats
    class road,river,landuse features
    class orchestrator orch
    class arcpy,generalization ext
```

---

## Class Hierarchy & Relationships

### Validation Status Layer

```mermaid
graph TB
    subgraph Enums["Enumerations"]
        Severity["<b>Severity</b> (StrEnum)<br/>SUCCESS<br/>WARNING<br/>ERROR"]
        Operators["<b>OPERATORS</b> dict<br/>eqn: equals new value<br/>eqd: equals diff<br/>neq: not equals<br/>gt: greater than<br/>lt: less than<br/>ratio_gt: ratio gt<br/>ratio_lt: ratio lt"]
    end
    
    subgraph DataClasses["Data Classes"]
        Rule["<b>Rule</b> @dataclass<br/><br/>key: str<br/>operator: str<br/>value: float | int | bool | list<br/>severity: Severity | list[Severity]<br/><br/>__post_init__()"]
    end
    
    subgraph StatusManagement["Status Management"]
        ValidationStatus["<b>ValidationStatus</b><br/><br/>permanent_rules: list[Rule]<br/>temporary_rules: list[Rule]<br/>STATUS_SEVERITY: tuple<br/><br/>add_permanent_rule()<br/>remove_permanent_rule()<br/>add_temporary_rule()<br/>remove_temporary_rules()<br/>status_update(stats: dict)<br/>_evaluate_rule()<br/>_get_message()<br/>_most_severe_status()"]
    end
    
    Severity -->|used by| Rule
    Operators -->|used by| ValidationStatus
    Rule -->|stored in| ValidationStatus
```

### Statistics Collection Hierarchy

```mermaid
classDiagram
    VectorStatistics <|-- LineStatistics
    VectorStatistics <|-- PolygonStatistics
    VectorStatistics <|-- PointStatistics
    LineStatistics <|-- RoadStatistics
    LineStatistics <|-- RiverStatistics
    PolygonStatistics <|-- LanduseStatistics

    class VectorStatistics {
        +list[Rule] RULES
        +get_stats(fc: str) dict
        +data_exists(data: str) bool
        +feature_class_has_data(fc: str) bool
        +get_geom_data(fc: str) tuple[int, int]
        +get_num_obj(fc: str) int
    }

    class LineStatistics {
        +list[Rule] RULES
        +get_stats(fc: str) dict
        +get_line_stats(fc: str) dict
    }

    class PolygonStatistics {
        +list[Rule] RULES
        +get_stats(fc: str) dict
        +get_poly_stats(fc: str) dict
    }

    class PointStatistics {
        +get_stats(fc: str) dict
    }

    class RoadStatistics {
        +list[Rule] RULES
        +get_stats(fc: str) dict
        +get_num_types(fc: str) dict
    }

    class RiverStatistics {
        +get_stats(fc: str) dict
    }

    class LanduseStatistics {
        +list[Rule] RULES
        +scale: str
        +__init__(scale: str)
        +get_stats(fc: str) dict
        +get_landuse_stats(fc: str) dict
    }

    class ValidatorOrchestrator {
        +stats_provider
        +validator: ValidationStatus
        +id: int
        +step: int
        +previous_path: Path | None
        +__init__(stats_provider)
        +save_validation_results(results: dict, output_dir: Path)
        +calculate_diff(previous: dict, current: dict) dict
    }
```

---

## Data Flow

### Statistics Collection Workflow

```mermaid
sequenceDiagram
    participant User as User Code
    participant Orchestrator as ValidatorOrchestrator
    participant StatsProvider as StatsProvider<br/>(e.g., RoadStatistics)
    participant Validator as ValidationStatus
    participant ArcPy as ArcPy
    participant FileSystem as File System

    User->>Orchestrator: new ValidatorOrchestrator(stats_provider)
    Orchestrator->>Validator: new ValidationStatus()
    Orchestrator->>Validator: add_permanent_rule(stats_provider.RULES)
    Validator-->>Orchestrator: Ready

    User->>Orchestrator: save_validation_results(results_dict)
    
    rect rgb(255, 107, 107)
    Note over Orchestrator: First Run
    Orchestrator->>FileSystem: Create output_dir
    Orchestrator->>FileSystem: Write validation_<id>_1.json
    Orchestrator->>Orchestrator: Set previous_path
    end
    
    rect rgb(76, 175, 80)
    Note over Orchestrator: Subsequent Run
    Orchestrator->>FileSystem: Read previous validation file
    Orchestrator->>Orchestrator: calculate_diff(previous, current)
    Orchestrator->>Validator: status_update(difference)
    Validator-->>Orchestrator: (status_counter, overall_status, messages)
    Orchestrator->>FileSystem: Write validation_<id>_<step>.json
    end
```

### Single Statistics Collection Example

```mermaid
sequenceDiagram
    participant User as User Code
    participant Stats as RoadStatistics
    participant Vector as VectorStatistics
    participant ArcPy as ArcPy

    User->>Stats: get_stats(feature_class_path)
    
    rect rgb(76, 175, 80)
    Note over Stats,Vector: Parent Statistics
    Stats->>Vector: super().get_stats(fc)
    Vector->>ArcPy: Exists(fc)
    ArcPy-->>Vector: true/false
    
    alt Feature class exists
        Vector->>ArcPy: GetCount(fc)
        ArcPy-->>Vector: count
        Vector->>ArcPy: SearchCursor[SHAPE@]
        ArcPy-->>Vector: geometry objects
        Vector->>Vector: Calculate object_count<br/>vertex_count, null_count
    else Feature class missing
        Vector-->>Vector: Return zeros
    end
    
    Vector-->>Stats: {exists, has_data, object_count, ...}
    end
    
    rect rgb(156, 39, 176)
    Note over Stats: Feature-Specific Stats
    Stats->>ArcPy: SearchCursor[vegkategori]
    ArcPy-->>Stats: road category values
    Stats->>Stats: Count by category
    Stats-->>Stats: {road_categories: {K1: n, ...}}
    end
    
    Stats-->>User: {exists, has_data, object_count, ..., road_categories}
```

### Validation Result Serialization

```mermaid
graph LR
    Start["statistics dict<br/>{key: value}"]
    FirstRun["First Run?"]
    ReadPrevious["Read previous<br/>validation file"]
    CalcDiff["calculate_diff<br/>(previous, current)"]
    StatusUpdate["status_update<br/>(difference)"]
    BuildPayload["Build JSON payload<br/>run, status, messages<br/>results, difference"]
    WriteFile["Write to<br/>validation_<id>_<step>.json"]
    UpdatePrevious["Set previous_path<br/>for next run"]
    
    Start -->|Input| FirstRun
    FirstRun -->|Yes| BuildPayload
    FirstRun -->|No| ReadPrevious
    ReadPrevious --> CalcDiff
    CalcDiff --> StatusUpdate
    StatusUpdate --> BuildPayload
    BuildPayload --> WriteFile
    WriteFile --> UpdatePrevious
```

---

## Key Components

### 1. Validation Status (`validationStatus.py`)

Provides rule-based validation with configurable severity levels.

| Class/Enum | Responsibility |
|---|---|
| `Severity` | Enum: SUCCESS, WARNING, ERROR |
| `Rule` | Dataclass: key, operator, value, severity for a single validation rule |
| `ValidationStatus` | Manages permanent/temporary rules, evaluates rules against statistics |

**Operators** (in `OPERATORS` dict):
- `eqn`: new value equals threshold
- `eqd`: diff equals threshold
- `neq`: not equal
- `gt`: greater than
- `lt`: less than
- `ratio_gt`: absolute ratio > threshold
- `ratio_lt`: absolute ratio < threshold

**Design Principle**: Rules are immutable and reusable across runs and feature classes.

### 2. Data Type Statistics (`dataTypeStatistics.py`)

Base class for all geometry-type-specific statistics collectors.

| Class | Key Methods | Statistics Collected |
|---|---|---|
| `VectorStatistics` | `get_stats()`, `data_exists()`, `get_num_obj()`, `get_geom_data()` | exists, has_data, object_count, vertex_count, null_count |

**Responsibilities**:
- Check feature class existence via `arcpy.Exists()`
- Count objects and vertices using ArcPy cursors
- Track null/missing geometries
- Define base RULES for all geometry types

### 3. Geometry Type Statistics (`geometryTypeStatistics.py`)

Specialized statistics for specific geometry types; extend `VectorStatistics`.

| Class | Extends | Key Methods | Metrics |
|---|---|---|---|
| `LineStatistics` | VectorStatistics | `get_line_stats()` | total_length, min/max/avg_length, dangle counts |
| `PolygonStatistics` | VectorStatistics | `get_poly_stats()` | total_area, min/max/avg_area |
| `PointStatistics` | VectorStatistics | (none) | Inherits from parent |

**Key Details**:
- `LineStatistics`: Detects dangle lines (endpoints with only one connection point)
- `PolygonStatistics`: Computes area statistics from `SHAPE@AREA` field
- Both use ArcPy `SearchCursor` for geometry access

### 4. Feature Type Statistics (`featureTypeStatistics.py`)

Domain-specific statistics for real feature types; extend geometry-type classes.

| Class | Extends | Domain-Specific Metrics | Scale Support |
|---|---|---|---|
| `RoadStatistics` | LineStatistics | road_categories (vegkategori field) | N100, N250, etc. |
| `RiverStatistics` | LineStatistics | (inherited only) | All scales |
| `LanduseStatistics` | PolygonStatistics | landuse_categories (arealdekke field) | Scale-aware via `__init__` |

**Dependencies**:
- `RoadStatistics`: Accesses `vegkategori` field
- `LanduseStatistics`: Imports `get_min_area()` from `generalization.n10.arealdekke` for scale-specific rules

### 5. Validator Orchestrator (`validatorOrchestrator.py`)

Coordinates statistics collection, validation, and multi-run result tracking.

| Attribute | Type | Purpose |
|---|---|---|
| `stats_provider` | StatsProvider | Instance of any stats class (e.g., RoadStatistics) |
| `validator` | ValidationStatus | Rule evaluation engine |
| `id` | int | Unique validation run session ID (Unix timestamp) |
| `step` | int | Current run number within session |
| `previous_path` | Path \| None | Path to previous validation result file |

| Method | Purpose |
|---|---|
| `__init__(stats_provider)` | Initialize with rules from `stats_provider.RULES` |
| `save_validation_results(results, output_dir)` | Save validated results to JSON; compute diff if repeat run |
| `calculate_diff(previous, current)` | Compute new/diff/ratio for each metric |

**Output Format**: JSON with structure:
```json
{
  "run": 1,
  "status": "SUCCESS|WARNING|ERROR",
  "status_counts": {"SUCCESS": n, "WARNING": n, "ERROR": n},
  "messages": {"key": "message text"},
  "results": {...},
  "difference": {"key": {"new": val, "diff": val, "ratio": val}}
}
```

---

## Validation Rules & Status

### Rule Definition & Evaluation

A `Rule` specifies:
- **key**: metric name (e.g., "exists", "object_count", "road_categories")
- **operator**: how to evaluate (eqn, gt, lt, ratio_gt, etc.)
- **value**: threshold or expected value (scalar or list for multi-level)
- **severity**: outcome for each level (SUCCESS, WARNING, ERROR)

### Rule Examples

```python
# Must exist (ERROR if missing)
Rule("exists", "eqn", True, Severity.ERROR)

# Object count ratio with three severity levels
Rule("object_count", "ratio", [0.3, 0.6],
     [Severity.SUCCESS, Severity.WARNING, Severity.ERROR])
     # If ratio > 0.6: ERROR
     # If 0.3 < ratio <= 0.6: WARNING
     # If ratio <= 0.3: SUCCESS
```

### Multi-Run Validation

Each call to `save_validation_results()`:
1. Checks if a previous run exists
2. Computes `diff` and `ratio` for each metric
3. Applies rules to differences (not raw values)
4. Assigns severity based on rule operators
5. Returns overall status (highest severity wins)

---

## Usage Examples

### Example 1: Validate Road Features Across Runs

```python
from geometry_validation.featureTypeStatistics import RoadStatistics
from geometry_validation.validatorOrchestrator import ValidatorOrchestrator
from pathlib import Path

# Create orchestrator with road statistics provider
road_stats = RoadStatistics()
orchestrator = ValidatorOrchestrator(road_stats)

# First run
results_1 = {
    "elveg": road_stats.get_stats("/path/to/elveg_fc"),
    "sti": road_stats.get_stats("/path/to/sti_fc")
}
orchestrator.save_validation_results(results_1, Path("./validation"))

# Second run (will compute diffs and validate changes)
results_2 = {
    "elveg": road_stats.get_stats("/path/to/elveg_fc"),
    "sti": road_stats.get_stats("/path/to/sti_fc")
}
orchestrator.save_validation_results(results_2, Path("./validation"))
# Output: validation_<timestamp>_2.json with status based on changes
```

### Example 2: Add Custom Temporary Rules

```python
from geometry_validation.validationStatus import Rule, Severity, ValidationStatus
from geometry_validation.featureTypeStatistics import LanduseStatistics

# Create landuse validator with scale awareness
landuse_stats = LanduseStatistics(scale="N100")
orchestrator = ValidatorOrchestrator(landuse_stats)

# Add a one-time rule (removed after next status_update)
strict_rule = Rule("total_area", "lt", 0.1, Severity.ERROR)
orchestrator.validator.add_temporary_rule(strict_rule)

# Validate
results = {"landuse": landuse_stats.get_stats("/path/to/landuse_fc")}
orchestrator.save_validation_results(results)
# Temporary rules are cleared automatically

# Next call uses only permanent rules
orchestrator.save_validation_results(results)
```

### Example 3: Extend Statistics for Custom Feature Type

```python
from geometry_validation.geometryTypeStatistics import LineStatistics
from geometry_validation.validationStatus import Rule, Severity

class TrailStatistics(LineStatistics):
    RULES = [
        Rule("trail_surface_types", "ratio",
             [0.2, 0.5],
             [Severity.SUCCESS, Severity.WARNING, Severity.ERROR])
    ] + LineStatistics.RULES
    
    def get_stats(self, fc: str) -> dict:
        r1 = super().get_stats(fc)  # Line stats
        r2 = self._get_trail_stats(fc)  # Custom
        return {**r1, **r2}
    
    def _get_trail_stats(self, fc: str) -> dict:
        # Custom logic using arcpy.da.SearchCursor
        from collections import Counter
        field = "surface_type"
        counts = Counter()
        with arcpy.da.SearchCursor(fc, [field]) as cursor:
            counts = Counter(row[0] for row in cursor)
        return {"trail_surface_types": dict(counts)}
```

---

## See Also

- [data_orchestrator_2/ARCHITECTURE.md](../data_orchestrator_2/ARCHITECTURE.md) — Pipeline schema definitions
