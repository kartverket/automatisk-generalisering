"""TEMPLATE — NOT YET WRITTEN. Target package: `src/ag/ports/`.

This directory exists so the gap is visible. The template implements the declaration
model; it does not yet implement the port boundary, and a tree that silently omitted
`ports/` would read as "the port design is not real".

Six ports, one file each, flat — 03-architecture §2.1:

    GeometryOps        operations on spatial datasets          25-35 methods
    TableOps           schema, attributes, bulk row IO         10-15
    CartographicOps    named ICA generalization operators      8-12
    GraphOps           graph algorithms over abstract topology ~8
    ArchiveClient      object storage transport                2
    ClusterClient      Kubernetes job lifecycle                4-5

Plus `geometry.py` (the `Geometry` value type, ADR-0004) and `toolbox.py`.

The decisions already made, so that whoever writes these does not re-litigate them:

    ADR-0002   three geoprocessing ports rather than one or many
    ADR-0003   ScratchHandle, not DataObject, at the port boundary
    ADR-0004   Geometry as a value type; no cursor in the port
    ADR-0007   ports are Protocol, not ABC
    ADR-0008   Toolbox passed explicitly, not ambient

Vocabulary comes from OGC CQL2, OGC Simple Features and the ICA operator taxonomy,
never from arcpy's spelling — 03-architecture §2.2.

ONE THING TO CHANGE HERE WHEN THIS LANDS: `ag.core.operations.operation` currently
rejects any parameter that is not `In`, `Out`, `config` or `ScratchScope`. It must
admit `tb: Toolbox` as a fifth kind (02-runtime §2.4).
"""
