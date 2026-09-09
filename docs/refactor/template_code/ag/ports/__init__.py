"""TEMPLATE — not shipped. Target package: `src/ag/ports/`.

The system boundary. Six `Protocol`s, one value type, and the bundle they arrive in.

    changing attributes?              table_ops
    moving geometry?                  geometry_ops
    named generalization operator?    cartographic_ops
    graph algorithm over topology?    graph_ops
    bytes to object storage?          archive
    Kubernetes job lifecycle?         cluster

FLAT, AND IT STAYS FLAT. Six files are browsable and a `processing/` vs
`infrastructure/` split buys nothing at this size. Revisit past ~10.

ADDING A PORT requires a distinct external capability AND a foreseeable second
implementation. Otherwise it is a helper or an adapter detail. A distinct capability
that shares an existing conversation is a METHOD, not a file - which is the test
`TableOps.exists` passes and a `DescribeOps` would fail.

    ADR-0002   three geoprocessing ports rather than one or many
    ADR-0003   ScratchHandle, not DataObject, at the port boundary
    ADR-0004   Geometry as a value type; no cursor in the port
    ADR-0006   logging is not a port. Do not add a LogPort.
    ADR-0007   ports are Protocol, not ABC
    ADR-0008   Toolbox passed explicitly, not ambient
    ADR-0014   how @operation recognises the parameters the runtime injects

PORTS ARE `Protocol`, NOT `ABC`, so adapters satisfy them structurally and the
dependency arrow never reverses - an adapter imports the port, and the port knows
nothing of any adapter. Conformance is asserted by an `if TYPE_CHECKING:` assignment at
the bottom of each adapter module, plus the adapter x port matrix in `tests/static/`.

WHAT THIS PACKAGE IMPORTS: `ag.core.operations` (ScratchHandle only), `ag.core.types`,
`ag.core.injection`, and stdlib. Never an adapter, never an operation, never
`core.pipeline`, and never a vendor library.

------------------------------------------------------------------------------
THE RE-EXPORT BELOW is the operation-facing vocabulary, so an operation module opens
with one import rather than five. It is deliberately NOT everything:

    the six Protocols are absent. An adapter implements exactly one port, and its
    conformance assignment reads better naming the module it implements
    (`from ag.ports.geometry_ops import GeometryOps`). Leaving them out keeps the
    import at the head of an operation module a statement of what operations are
    allowed to know.

    `NOT_INJECTED` is present, because it appears in operation DEFINITIONS as the
    default for `tb` - exactly as `core.operations.INJECTED` does for `scratch`.
"""

from ag.ports.geometry import CRS as CRS
from ag.ports.geometry import Coordinate as Coordinate
from ag.ports.geometry import Geometry as Geometry
from ag.ports.geometry import GeometryKind as GeometryKind
from ag.ports.geometry import Ring as Ring
from ag.ports.geometry_ops import (
    And as And,
    Attr as Attr,
    DissolveOption as DissolveOption,
    DWithin as DWithin,
    EndCap as EndCap,
    Intersects as Intersects,
    JoinStyle as JoinStyle,
    Not as Not,
    Or as Or,
    Predicate as Predicate,
    Relation as Relation,
    Spatial as Spatial,
    VertexPosition as VertexPosition,
    Within as Within,
)
from ag.ports.table_ops import (
    Field as Field,
    FieldName as FieldName,
    FieldType as FieldType,
    Row as Row,
    Schema as Schema,
)
from ag.ports.toolbox import NOT_INJECTED as NOT_INJECTED, Toolbox as Toolbox

__all__ = [
    "NOT_INJECTED",
    "And",
    "Attr",
    "CRS",
    "Coordinate",
    "DWithin",
    "DissolveOption",
    "EndCap",
    "Field",
    "FieldName",
    "FieldType",
    "Geometry",
    "GeometryKind",
    "Intersects",
    "JoinStyle",
    "Not",
    "Or",
    "Predicate",
    "Relation",
    "Ring",
    "Row",
    "Schema",
    "Spatial",
    "Toolbox",
    "VertexPosition",
    "Within",
]
