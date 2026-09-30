# Slice 0 evidence: every import contract broken once

**Status:** EVIDENCE, 2026-09-22. Produced by a throwaway harness (not kept) that wrote one
probe module per case into `src/ag`, ran `lint-imports` from the repository root, and removed
the probe. `.importlinter` holds twenty-four contracts over the eighteen rows of
`project_tree.md` §6; every one is shown BROKEN below by at least one probe, and the five
"allowed" probes show the exemptions (`ignore_imports`, the allowed importer) do what they
say. After the last probe was removed: `Contracts: 24 kept, 0 broken.`

Command for every case: `lint-imports` (import-linter 2.15, Python 3.13.15, the project
installed editable). "Every contract broken by this probe" lists the rows that fired, which is
how the redundancy the tree accepts on purpose (row 13 beside 6, 9, 10) shows up.

### Row 1: a lower layer imports a higher one

Probe: `src/ag/staging/probe_mod.py` = `import ag.runtime`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 1.

```
Row 1: the package stack; every package under ag has a layer
------------------------------------------------------------

ag.staging is not allowed to import ag.runtime:

- ag.staging.probe_mod -> ag.runtime (l.1)
```

### Row 1: independent siblings: lineage imports staging

Probe: `src/ag/lineage/probe_mod.py` = `import ag.staging`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 1, Row 9.

```
Row 1: the package stack; every package under ag has a layer
------------------------------------------------------------

ag.lineage is not allowed to import ag.staging:

- ag.lineage.probe_mod -> ag.staging (l.1)
```

### Row 1: exhaustive: a new top-level package with no layer

Probe: `src/ag/probe_pkg/__init__.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 1.

```
Row 1: the package stack; every package under ag has a layer
------------------------------------------------------------

The following modules are not listed as layers:

- ag.probe_pkg

(Since this contract is marked as 'exhaustive', every child of every container 
must be declared as a layer.)
```

### Row 2: helpers imports operations

Probe: `src/ag/generalization/helpers/probe_mod.py` = `import ag.generalization.operations`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 2.

```
Row 2: the layers inside ag.generalization
------------------------------------------

ag.generalization.helpers is not allowed to import ag.generalization.operations:

- ag.generalization.helpers.probe_mod -> ag.generalization.operations (l.1)
```

### Row 2: bottom five independent: tuning imports errors

Probe: `src/ag/generalization/tuning/probe_mod.py` = `import ag.generalization.errors`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 2.

```
Row 2: the layers inside ag.generalization
------------------------------------------

ag.generalization.tuning is not allowed to import ag.generalization.errors:

- ag.generalization.tuning.probe_mod -> ag.generalization.errors (l.1)
```

### Row 2: exhaustive: a new domain module with no layer

Probe: `src/ag/generalization/probe_mod.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 2.

```
Row 2: the layers inside ag.generalization
------------------------------------------

The following modules are not listed as layers:

- ag.generalization.probe_mod

(Since this contract is marked as 'exhaustive', every child of every container 
must be declared as a layer.)
```

### Row 3: core imports observability

Probe: `src/ag/core/probe_mod.py` = `import ag.observability`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 3.

```
Row 3: ag.core imports nothing else in ag
-----------------------------------------

ag.core is not allowed to import ag.observability:

-   ag.core.probe_mod -> ag.observability (l.1)
```

### Row 4: a port imports ag.core.pipeline

Probe: `src/ag/core/pipeline.py` = `"""Probe."""`; `src/ag/ports/probe_mod.py` = `import ag.core.pipeline`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 4.

```
Row 4: ag.ports imports four ag.core modules and nothing else in ag
-------------------------------------------------------------------

ag.ports is not allowed to import ag.core:

-   ag.ports.probe_mod -> ag.core.pipeline (l.1)
```

### Row 4: allowed: a port imports the four core modules

Probe: `src/ag/core/handles.py` = `"""Probe."""`; `src/ag/core/types.py` = `"""Probe."""`; `src/ag/core/injection.py` = `"""Probe."""`; `src/ag/core/errors.py` = `"""Probe."""`; `src/ag/ports/probe_mod.py` = `import ag.core.errors / import ag.core.handles / import ag.core.injection / import ag.core.types`

Expected: KEPT. Got: KEPT (4 ignored imports). as expected.
Every contract broken by this probe: none.

### Row 5: geometry_ops imports cartographic_ops

Probe: `src/ag/ports/geometry_ops.py` = `(appended) import ag.ports.cartographic_ops`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 5.

```
Row 5: cartographic_ops sits above the other port Protocols
-----------------------------------------------------------

ag.ports.geometry_ops is not allowed to import ag.ports.cartographic_ops:

- ag.ports.geometry_ops -> ag.ports.cartographic_ops (l.6)
```

### Row 5: sibling ports: table_ops imports graph_ops

Probe: `src/ag/ports/table_ops.py` = `(appended) import ag.ports.graph_ops`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 5.

```
Row 5: cartographic_ops sits above the other port Protocols
-----------------------------------------------------------

ag.ports.table_ops is not allowed to import ag.ports.graph_ops:

- ag.ports.table_ops -> ag.ports.graph_ops (l.6)
```

### Row 6: lineage imports an adapter package

Probe: `src/ag/lineage/probe_mod.py` = `import ag.adapters._shared`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 6.

```
Row 6: only a composition root imports ag.adapters
--------------------------------------------------

Illegal imports of protected package ag.adapters:

- ag.lineage.probe_mod -> ag.adapters._shared (l.1)
```

### Row 7: the storage adapter imports the networkx adapter

Probe: `src/ag/adapters/storage/probe_mod.py` = `import ag.adapters.networkx`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 7.

```
Row 7: adapter packages do not import each other
------------------------------------------------

ag.adapters.storage is not allowed to import ag.adapters.networkx:

- ag.adapters.storage.probe_mod -> ag.adapters.networkx (l.1)
```

### Row 8: runtime imports arcpy

Probe: `src/ag/runtime/probe_mod.py` = `import arcpy`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 8.

```
Row 8: a vendor library is imported only by its adapter
-------------------------------------------------------

ag is not allowed to import arcpy:

-   ag.runtime.probe_mod -> arcpy (l.1)
```

### Row 8: networkx outside its one module

Probe: `src/ag/adapters/networkx/probe_mod.py` = `import networkx`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 8.

```
Row 8: a vendor library is imported only by its adapter
-------------------------------------------------------

ag is not allowed to import networkx:

-   ag.adapters.networkx.probe_mod -> networkx (l.1)
```

### Row 8: shapely outside ag.adapters

Probe: `src/ag/staging/probe_mod.py` = `import shapely`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 8.

```
Row 8: a vendor library is imported only by its adapter
-------------------------------------------------------

ag is not allowed to import shapely:

-   ag.staging.probe_mod -> shapely (l.1)
```

### Row 8: allowed: arcpy in an ArcPy support module, networkx in graph_ops, boto3 under adapters

Probe: `src/ag/adapters/arcpy/support/probe_mod.py` = `import arcpy`; `src/ag/adapters/networkx/graph_ops.py` = `import networkx`; `src/ag/adapters/storage/probe_mod.py` = `import boto3`

Expected: KEPT. Got: KEPT (3 ignored imports). as expected.
Every contract broken by this probe: none.

### Row 9: generalization imports staging

Probe: `src/ag/generalization/helpers/probe_mod.py` = `import ag.staging`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 9, Row 13.

```
Row 9: only ag.runtime imports ag.staging
-----------------------------------------

Illegal imports of protected package ag.staging:

- ag.generalization.helpers.probe_mod -> ag.staging (l.1)
```

### Row 10: orchestrator imports lineage

Probe: `src/ag/orchestrator/probe_mod.py` = `import ag.lineage`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 10.

```
Row 10: only ag.runtime imports ag.lineage
------------------------------------------

Illegal imports of protected package ag.lineage:

- ag.orchestrator.probe_mod -> ag.lineage (l.1)
```

### Row 11: sources imports observability

Probe: `src/ag/generalization/sources.py` = `(appended) import ag.observability`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 11.

```
Row 11: sources and products import only ag.core
------------------------------------------------

ag.generalization.sources is not allowed to import ag.observability:

-   ag.generalization.sources -> ag.observability (l.6)
```

### Row 11: products imports ag.ports

Probe: `src/ag/generalization/products.py` = `(appended) import ag.ports`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 11.

```
Row 11: sources and products import only ag.core
------------------------------------------------

ag.generalization.products is not allowed to import ag.ports:

-   ag.generalization.products -> ag.ports (l.6)
```

### Row 12: an operation imports ag.core.data_objects

Probe: `src/ag/core/data_objects.py` = `"""Probe."""`; `src/ag/generalization/operations/probe_mod.py` = `import ag.core.data_objects`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 12.

```
Row 12: operations and helpers never see a DataObject (ADR-0003)
----------------------------------------------------------------

ag.generalization.operations is not allowed to import ag.core.data_objects:

-   ag.generalization.operations.probe_mod -> ag.core.data_objects (l.1)
```

### Row 12: indirect: a helper imports ag.core.locations, which imports ag.core.pipeline

Probe: `src/ag/core/pipeline.py` = `"""Probe."""`; `src/ag/core/locations.py` = `import ag.core.pipeline`; `src/ag/generalization/helpers/probe_mod.py` = `import ag.core.locations`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 12.

```
Row 12: operations and helpers never see a DataObject (ADR-0003)
----------------------------------------------------------------

ag.generalization.helpers is not allowed to import ag.core.pipeline:

-   ag.generalization.helpers.probe_mod -> ag.core.locations (l.1)
    ag.core.locations -> ag.core.pipeline (l.1)
```

### Row 13: a pipeline module imports ag.runtime

Probe: `src/ag/generalization/pipelines/probe_mod.py` = `import ag.runtime`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 1, Row 13.

```
Row 13: domain code never imports the framework above the ports
---------------------------------------------------------------

ag.generalization is not allowed to import ag.runtime:

-   ag.generalization.pipelines.probe_mod -> ag.runtime (l.1)
```

### Row 14a: observability imports ag.ports

Probe: `src/ag/observability/probe_mod.py` = `import ag.ports`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 14a.

```
Row 14a: ag.observability imports only stdlib and ag.core.types
---------------------------------------------------------------

ag.observability is not allowed to import ag.ports:

-   ag.observability.probe_mod -> ag.ports (l.1)
```

### Row 14a: observability imports a core module other than types

Probe: `src/ag/core/errors.py` = `"""Probe."""`; `src/ag/observability/probe_mod.py` = `import ag.core.errors`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 14a.

```
Row 14a: ag.observability imports only stdlib and ag.core.types
---------------------------------------------------------------

ag.observability is not allowed to import ag.core:

-   ag.observability.probe_mod -> ag.core.errors (l.1)
```

### Row 14a: allowed: observability imports ag.core.types

Probe: `src/ag/core/types.py` = `"""Probe."""`; `src/ag/observability/probe_mod.py` = `import ag.core.types`

Expected: KEPT. Got: KEPT (1 ignored import). as expected.
Every contract broken by this probe: none.

### Row 14b: a pipeline module imports the context accessor

Probe: `src/ag/observability/context.py` = `"""Probe."""`; `src/ag/generalization/pipelines/probe_mod.py` = `import ag.observability.context`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 14b.

```
Row 14b: no context accessor in ag.core or in pipelines
-------------------------------------------------------

ag.generalization.pipelines is not allowed to import ag.observability.context:

-   ag.generalization.pipelines.probe_mod -> ag.observability.context (l.1)
```

### Row 15: orchestrator imports a geoprocessing port

Probe: `src/ag/orchestrator/probe_mod.py` = `import ag.ports.geometry_ops`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 15.

```
Row 15: ag.orchestrator imports no pod-side code
------------------------------------------------

ag.orchestrator is not allowed to import ag.ports:

-   ag.orchestrator.probe_mod -> ag.ports.geometry_ops (l.1)
```

### Row 15: orchestrator imports the ArcPy adapter

Probe: `src/ag/orchestrator/probe_mod.py` = `import ag.adapters.arcpy`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 15.

```
Row 15: ag.orchestrator imports no pod-side code
------------------------------------------------

ag.orchestrator is not allowed to import ag.adapters.arcpy:

-   ag.orchestrator.probe_mod -> ag.adapters.arcpy (l.1)
```

### Row 15: allowed: orchestrator imports ports.archive, ports.cluster and the registry, which reaches operations and a port indirectly

Probe: `src/ag/ports/archive.py` = `"""Probe."""`; `src/ag/ports/cluster.py` = `"""Probe."""`; `src/ag/generalization/pipelines/probe_mod.py` = `import ag.generalization.operations.probe_mod`; `src/ag/generalization/operations/probe_mod.py` = `import ag.ports.geometry_ops`; `src/ag/orchestrator/probe_mod.py` = `import ag.generalization.registry / import ag.ports.archive / import ag.ports.cluster`; `src/ag/generalization/registry.py` = `(appended) import ag.generalization.pipelines.probe_mod`

Expected: KEPT. Got: KEPT (2 ignored imports). as expected.
Every contract broken by this probe: none.

### Row 16: two group modules of arcpy/geometry_ops, one importing the other

Probe: `src/ag/adapters/arcpy/geometry_ops/probe_a.py` = `import ag.adapters.arcpy.geometry_ops.probe_b`; `src/ag/adapters/arcpy/geometry_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: arcpy geometry_ops group modules are independent
--------------------------------------------------------

ag.adapters.arcpy.geometry_ops.probe_a is not allowed to import 
ag.adapters.arcpy.geometry_ops.probe_b:

- ag.adapters.arcpy.geometry_ops.probe_a -> 
ag.adapters.arcpy.geometry_ops.probe_b (l.1)
```

### Row 16: two group modules of arcpy/table_ops, one importing the other

Probe: `src/ag/adapters/arcpy/table_ops/probe_a.py` = `import ag.adapters.arcpy.table_ops.probe_b`; `src/ag/adapters/arcpy/table_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: arcpy table_ops group modules are independent
-----------------------------------------------------

ag.adapters.arcpy.table_ops.probe_a is not allowed to import 
ag.adapters.arcpy.table_ops.probe_b:

- ag.adapters.arcpy.table_ops.probe_a -> ag.adapters.arcpy.table_ops.probe_b 
(l.1)
```

### Row 16: two group modules of arcpy/cartographic_ops, one importing the other

Probe: `src/ag/adapters/arcpy/cartographic_ops/probe_a.py` = `import ag.adapters.arcpy.cartographic_ops.probe_b`; `src/ag/adapters/arcpy/cartographic_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: arcpy cartographic_ops group modules are independent
------------------------------------------------------------

ag.adapters.arcpy.cartographic_ops.probe_a is not allowed to import 
ag.adapters.arcpy.cartographic_ops.probe_b:

- ag.adapters.arcpy.cartographic_ops.probe_a -> 
ag.adapters.arcpy.cartographic_ops.probe_b (l.1)
```

### Row 16: two group modules of fakes/memory/geometry_ops, one importing the other

Probe: `src/ag/adapters/fakes/memory/geometry_ops/probe_a.py` = `import ag.adapters.fakes.memory.geometry_ops.probe_b`; `src/ag/adapters/fakes/memory/geometry_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: memory geometry_ops group modules are independent
---------------------------------------------------------

ag.adapters.fakes.memory.geometry_ops.probe_a is not allowed to import 
ag.adapters.fakes.memory.geometry_ops.probe_b:

- ag.adapters.fakes.memory.geometry_ops.probe_a -> 
ag.adapters.fakes.memory.geometry_ops.probe_b (l.1)
```

### Row 16: two group modules of fakes/memory/table_ops, one importing the other

Probe: `src/ag/adapters/fakes/memory/table_ops/probe_a.py` = `import ag.adapters.fakes.memory.table_ops.probe_b`; `src/ag/adapters/fakes/memory/table_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: memory table_ops group modules are independent
------------------------------------------------------

ag.adapters.fakes.memory.table_ops.probe_a is not allowed to import 
ag.adapters.fakes.memory.table_ops.probe_b:

- ag.adapters.fakes.memory.table_ops.probe_a -> 
ag.adapters.fakes.memory.table_ops.probe_b (l.1)
```

### Row 16: two group modules of fakes/memory/cartographic_ops, one importing the other

Probe: `src/ag/adapters/fakes/memory/cartographic_ops/probe_a.py` = `import ag.adapters.fakes.memory.cartographic_ops.probe_b`; `src/ag/adapters/fakes/memory/cartographic_ops/probe_b.py` = `"""Probe."""`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 16.

```
Row 16: memory cartographic_ops group modules are independent
-------------------------------------------------------------

ag.adapters.fakes.memory.cartographic_ops.probe_a is not allowed to import 
ag.adapters.fakes.memory.cartographic_ops.probe_b:

- ag.adapters.fakes.memory.cartographic_ops.probe_a -> 
ag.adapters.fakes.memory.cartographic_ops.probe_b (l.1)
```

### Row 17: arcpy: a support module imports a port package

Probe: `src/ag/adapters/arcpy/support/probe_mod.py` = `import ag.adapters.arcpy.geometry_ops`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 17.

```
Row 17: adapter layers: port packages, support, _base, session or store
-----------------------------------------------------------------------

ag.adapters.arcpy.support is not allowed to import 
ag.adapters.arcpy.geometry_ops:

- ag.adapters.arcpy.support.probe_mod -> ag.adapters.arcpy.geometry_ops (l.1)
```

### Row 17: memory: _base imports support

Probe: `src/ag/adapters/fakes/memory/_base.py` = `(appended) import ag.adapters.fakes.memory.support`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 17.

```
Row 17: adapter layers: port packages, support, _base, session or store
-----------------------------------------------------------------------

ag.adapters.fakes.memory._base is not allowed to import 
ag.adapters.fakes.memory.support:

- ag.adapters.fakes.memory._base -> ag.adapters.fakes.memory.support (l.7)
```

### Row 17: memory: the store imports _base (optional layer, present)

Probe: `src/ag/adapters/fakes/memory/store.py` = `import ag.adapters.fakes.memory._base`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 17.

```
Row 17: adapter layers: port packages, support, _base, session or store
-----------------------------------------------------------------------

ag.adapters.fakes.memory.store is not allowed to import 
ag.adapters.fakes.memory._base:

- ag.adapters.fakes.memory.store -> ag.adapters.fakes.memory._base (l.1)
```

### Row 17: arcpy: port packages import each other

Probe: `src/ag/adapters/arcpy/table_ops/probe_mod.py` = `import ag.adapters.arcpy.geometry_ops`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 17.

```
Row 17: adapter layers: port packages, support, _base, session or store
-----------------------------------------------------------------------

ag.adapters.arcpy.table_ops is not allowed to import 
ag.adapters.arcpy.geometry_ops:

- ag.adapters.arcpy.table_ops.probe_mod -> ag.adapters.arcpy.geometry_ops (l.1)
```

### Row 18: runtime.compose imports the fake (passes row 6)

Probe: `src/ag/runtime/compose.py` = `import ag.adapters.fakes`

Expected: BROKEN. Got: BROKEN. as expected.
Every contract broken by this probe: Row 18.

```
Row 18: only ag.runtime.local imports ag.adapters.fakes
-------------------------------------------------------

Illegal imports of protected package ag.adapters.fakes:

- ag.runtime.compose -> ag.adapters.fakes (l.1)
```

### Row 18: allowed: runtime.local imports the fake

Probe: `src/ag/runtime/local.py` = `(appended) import ag.adapters.fakes.memory`

Expected: KEPT. Got: KEPT. as expected.
Every contract broken by this probe: none.

### After the last probe was removed

`lint-imports`: Contracts: 24 kept, 0 broken.
