# Partition Validation - Architecture & Design

A lightweight architecture for feature type-specific partition boundary analysis using the Factory and Strategy patterns.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Layers](#architecture-layers)
3. [Module Dependencies](#module-dependencies)
4. [Class Hierarchy](#class-hierarchy)
5. [Data Flow](#data-flow)
6. [Design Patterns](#design-patterns)

---

## Overview

`partition_validation` analyzes how features (points, lines, polygons) interact with partition boundaries. Each feature type has a dedicated analyzer that:
- Detects specific issues (dangles, overlaps, containment)
- Returns type-specific metrics
- Can be tested independently

The **FeatureCheckerFactory** automatically selects the correct analyzer based on the feature geometry type.

---

## Architecture Layers

```mermaid
graph TB
    subgraph Control["🎯 Control Layer"]
        analyzer["partition_analyzer.py<br/>AnalysePartitionEdges<br/>AnalysePartitionBuffer<br/>WritePartitionAnalysisToFile"]
    end

    subgraph Factory["🏭 Factory Layer"]
        factory["feature_checker_factory.py<br/>FeatureCheckerFactory<br/>create()<br/>_detect_feature_type()"]
    end

    subgraph Strategy["📋 Strategy Layer"]
        base["feature_checker_base.py<br/>FeatureChecker<br/>analyze()<br/>_get_buffer_geometry()"]
        
        point["point_feature_checker.py<br/>PointFeatureChecker<br/>count_points_in_buffer()"]
        line["line_feature_checker.py<br/>LineFeatureChecker<br/>get_relevant_end_points()"]
        polygon["polygon_feature_checker.py<br/>PolygonFeatureChecker<br/>calculate_overlaps()"]
    end

    Control -->|uses| Factory
    Factory -->|creates| Strategy
    base -.->|extended by| point
    base -.->|extended by| line
    base -.->|extended by| polygon

    style Control fill:#E3F2FD,stroke:#1565C0,stroke-width:3px,color:#000
    style Factory fill:#F3E5F5,stroke:#6A1B9A,stroke-width:3px,color:#000
    style Strategy fill:#E0F2F1,stroke:#00695C,stroke-width:3px,color:#000
    
    style analyzer fill:#2196F3,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    style factory fill:#9C27B0,stroke:#4A148C,stroke-width:2px,color:#fff,font-weight:bold
    style base fill:#009688,stroke:#004D40,stroke-width:2px,color:#fff,font-weight:bold
    style point fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    style line fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    style polygon fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    
    linkStyle default stroke:#1565C0,stroke-width:3px
```

---

## Module Dependencies

```mermaid
graph LR
    arcpy["🔌 arcpy"]
    typing["🔤 analyze_typing.py<br/>AnalysisMetrics<br/>LogRecord"]
    
    analyzer["partition_analyzer.py"]
    factory["feature_checker_factory.py"]
    base["feature_checker_base.py"]
    
    point["point_feature_checker.py"]
    line["line_feature_checker.py"]
    polygon["polygon_feature_checker.py"]
    
    arcpy -->|geometry ops| base
    
    analyzer -->|uses| factory
    analyzer -->|uses| typing
    factory -->|imports| point
    factory -->|imports| line
    factory -->|imports| polygon
    factory -->|imports| base
    
    point -->|extends| base
    line -->|extends| base
    polygon -->|extends| base
    
    base -->|uses| arcpy
    
    point -->|returns| typing
    line -->|returns| typing
    polygon -->|returns| typing

    style analyzer fill:#2196F3,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    style factory fill:#9C27B0,stroke:#4A148C,stroke-width:2px,color:#fff,font-weight:bold
    style base fill:#FF6F00,stroke:#E65100,stroke-width:2px,color:#fff,font-weight:bold
    style point fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    style line fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    style polygon fill:#00897B,stroke:#00251A,stroke-width:2px,color:#fff,font-weight:bold
    style typing fill:#D32F2F,stroke:#B71C1C,stroke-width:2px,color:#fff,font-weight:bold
    style arcpy fill:#1565C0,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    
    linkStyle default stroke:#1565C0,stroke-width:3px
```

---

## Class Hierarchy

```mermaid
classDiagram
    class FeatureChecker {
        <<abstract>>
        -feature_layer: str
        -buffer_fc: str
        -temp_layer_name: str
        +analyze()* dict
        #_delete_layer(layer: str)
        #_get_buffer_geometry(buffer_fc: str)
    }
    
    class PointFeatureChecker {
        +analyze() dict
        -_count_points_in_buffer() int
    }
    
    class LineFeatureChecker {
        +analyze() dict
        -_get_relevant_end_points() defaultdict
    }
    
    class PolygonFeatureChecker {
        +analyze() dict
    }
    
    class FeatureCheckerFactory {
        +create(feature_layer, buffer_fc, feature_type) FeatureChecker$
        -_detect_feature_type(feature_layer) str$
    }
    
    FeatureChecker <|-- PointFeatureChecker
    FeatureChecker <|-- LineFeatureChecker
    FeatureChecker <|-- PolygonFeatureChecker
    
    FeatureCheckerFactory --> FeatureChecker : creates
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant partition_analyzer as partition_analyzer
    participant factory as FeatureCheckerFactory
    participant checker as FeatureChecker<br/>subclass
    participant arcpy as arcpy
    
    partition_analyzer->>factory: create(feature_layer, buffer_fc)
    
    factory->>arcpy: Describe(feature_layer)
    arcpy-->>factory: geometry_type
    
    factory->>factory: _detect_feature_type()
    factory->>checker: __init__(feature_layer, buffer_fc)
    factory-->>partition_analyzer: FeatureChecker instance
    
    partition_analyzer->>checker: analyze()
    
    checker->>arcpy: SearchCursor on features
    checker->>arcpy: geometry operations
    arcpy-->>checker: results
    
    checker-->>partition_analyzer: type-specific dict
```

---

## Design Patterns

### Factory Pattern
Encapsulates checker creation and auto-detection:
```python
checker = FeatureCheckerFactory.create(
    feature_layer=fc,
    buffer_fc=buffer
    # feature_type auto-detected
)
```

**Benefits:**
- Automatic type detection
- Central place to add new types
- Decouples creation from usage

### Strategy Pattern
Each checker implements a different analysis strategy:
```python
# Same interface, different algorithms
result_line = LineFeatureChecker(...).analyze()
result_point = PointFeatureChecker(...).analyze()
result_poly = PolygonFeatureChecker(...).analyze()
```

**Benefits:**
- Easy to test each strategy independently
- Easy to add new strategies
- Runtime algorithm selection

### Abstract Base Class
Defines the contract all strategies must follow:
```python
class FeatureChecker(ABC):
    @abstractmethod
    def analyze(self) -> dict[str, Any]:
        pass
```

**Benefits:**
- Enforces consistent interface
- Enables type hints
- Prevents incomplete implementations

---

## Feature Type Results

Each analyzer returns metrics specific to its feature type. All results conform to the flexible `AnalysisMetrics` TypedDict:

| Type | Metrics | Returns |
|------|---------|---------|
| **Line** | Dangle detection | `{"dangle_count": int, "feature_ids": list}` |
| **Point** | Containment count | `{"point_count": int}` |
| **Polygon** | Overlap analysis | `{"overlap_count": int, "overlap_area": float}` |

**Note:** `AnalysisMetrics` uses `total=False` to allow optional fields, enabling each feature type to return only its relevant metrics without requiring unused fields.

---

## Type System: `analyze_typing.py`

The module provides two TypedDict classes that define the structure of analysis data:

### AnalysisMetrics
```python
class AnalysisMetrics(TypedDict, total=False):
    # Point metrics
    point_count: int
    
    # Line metrics
    dangle_count: int
    feature_ids: list[Any]
    
    # Polygon metrics
    overlap_count: int
    overlap_area: float
```

**Key design:**
- `total=False` makes all fields optional
- Each feature checker returns only its relevant metrics
- Type-safe while remaining flexible
- Easy to add new metrics for new feature types

### LogRecord
```python
class LogRecord(TypedDict, total=False):
    caller: str
    timestamp: str
    buffer_distance: int
    input: dict[str, AnalysisMetrics]
    output: dict[str, AnalysisMetrics]
    difference: dict[str, int | float]
```

**Usage in partition_analyzer.py:**
- Wraps analysis results with metadata (caller, timestamp, buffer distance)
- Stores separate metrics for input and output feature classes
- Computed difference field for comparative analysis

---



```mermaid
graph LR
    A["1. Create Checker<br/>class MyTypeChecker<br/>extends FeatureChecker"]
    B["2. Implement<br/>analyze() method"]
    C["3. Register<br/>in Factory<br/>checker_map"]
    D["✅ Done!<br/>No other changes"]
    
    A --> B --> C --> D
    
    style A fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    style B fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    style C fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:#fff,font-weight:bold
    style D fill:#2E7D32,stroke:#1B5E20,stroke-width:2px,color:#fff,font-weight:bold
    
    linkStyle default stroke:#1565C0,stroke-width:3px
```

**Steps:**
1. Create `my_type_feature_checker.py`
2. Extend `FeatureChecker`
3. Implement `analyze()` method
4. Add to `checker_map` in factory
5. Done! No modifications to existing code needed.

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| **partition_analyzer.py** | Orchestrator & control flow | 106 |
| **feature_checker_base.py** | Abstract interface | 45 |
| **feature_checker_factory.py** | Factory & detection | 64 |
| **point_feature_checker.py** | Point analysis | 31 |
| **line_feature_checker.py** | Line analysis | 38 |
| **polygon_feature_checker.py** | Polygon analysis | 32 |

**Total: ~316 lines of focused, single-responsibility code**

---

## Usage Example

```python
from partition_validation.partition_analyzer import AnalysePartitionBuffer
from partition_validation.feature_checker_factory import FeatureCheckerFactory

# High-level orchestration
results = AnalysePartitionBuffer(
    partition_buffer="buffer_fc",
    input_fc="input_roads",      # Auto-detected as line features
    output_fc="output_polygons"  # Auto-detected as polygon features
)

# Or direct checker usage
checker = FeatureCheckerFactory.create(
    feature_layer="my_features",
    buffer_fc="partition_buffer"
)
metrics = checker.analyze()
```

---

## Design Principles

✅ **Single Responsibility** - Each class has one reason to change
✅ **Open/Closed** - Open for extension (new types), closed for modification
✅ **Liskov Substitution** - Any checker can replace another
✅ **Dependency Inversion** - Depend on abstractions, not concrete types
✅ **Type Safety** - Full type hints, Pyright strict mode
✅ **Testability** - Each component tested independently
