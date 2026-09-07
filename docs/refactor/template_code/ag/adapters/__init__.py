"""TEMPLATE — NOT YET WRITTEN. Target package: `src/ag/adapters/`.

The only place a vendor library may be imported — 03-architecture §4.1. `import arcpy`
appears in exactly one file (`arcpy/session.py`, lazily bound so the module stays
import-safe); `networkx` in one; `shapely` only below here. That is what makes
"declarations are constructible with no data and no arcpy" (02-runtime §2.6) true by
construction rather than by discipline.

    arcpy/       session, geometry_ops, table_ops, cartographic_ops, predicates,
                 geometry, errors
    networkx/    graph_ops
    storage/     the ArchiveClient implementations
    cluster/     the Kubernetes client
    fakes/       in-memory implementations of every port, for contract tests

An adapter may consume other ports — it is a client of those contracts, not of their
implementations (§4.3). An implementation that adapts nothing is not an adapter: our
own displacement algorithm is domain logic that satisfies a port, and belongs in a
top-level `cartography/`.
"""
